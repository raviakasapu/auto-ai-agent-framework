"""
Agent class v2 - Policy-driven execution engine.

This version replaces all hardcoded behavior with configurable policies.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from collections import deque
import time
import uuid
import json

from ..base import Action, FinalResponse, BasePlanner, BaseTool, BaseMemory, BaseProgressHandler
from .events import EventBus
from .event_payloads import (
    build_action_executed_event,
    build_action_planned_event,
    build_agent_end_event,
    build_agent_start_event,
    build_error_event,
    build_policy_denied_event,
    build_worker_tool_call_event,
    build_worker_tool_result_event,
)
from ..policies.base import (
    CompletionDetector,
    TerminationPolicy,
    LoopPreventionPolicy,
    HITLPolicy,
    CheckpointPolicy,
)
from ..policies.default import (
    DefaultCompletionDetector,
    DefaultTerminationPolicy,
    DefaultLoopPreventionPolicy,
    DefaultHITLPolicy,
    DefaultCheckpointPolicy,
)
from ..services.request_context import update_request_context
from ..constants import (
    TASK,
    ACTION,
    OBSERVATION,
    ERROR,
    FINAL,
    SUGGESTED_PLAN,
    SCRIPT_INSTRUCTION,
    INJECTED_CONTEXT,
)
from pydantic import ValidationError


class Agent:
    """Policy-driven agent with explicit behavior control."""
    
    def __init__(
        self,
        planner: BasePlanner,
        memory: BaseMemory,
        tools: List[BaseTool] | Dict[str, BaseTool],
        policies: Dict[str, Any],  # REQUIRED - no defaults
        event_bus: Optional[EventBus] = None,
        name: str | None = None,
        description: str | None = None,
        version: str | None = None,
    ) -> None:
        from agent_framework.logging import get_logger
        
        if not policies:
            raise ValueError("Policies are required. Use preset or define explicitly.")
        
        # Validate required policies
        required_policies = ["completion", "termination", "loop_prevention"]
        for policy_name in required_policies:
            if policy_name not in policies:
                raise ValueError(f"Required policy '{policy_name}' not provided.")
        
        # Initialize components
        self.planner = planner
        self.memory = memory
        if isinstance(tools, dict):
            self.tools: Dict[str, BaseTool] = tools
        else:
            self.tools = {t.name: t for t in tools}
        self.event_bus = event_bus or EventBus()
        self.name = name or "Agent"
        self.description = description or "An AI agent."
        self.version = version or "2.0.0"
        
        # Initialize policies (REQUIRED)
        self.completion_detector: CompletionDetector = policies["completion"]
        self.termination_policy: TerminationPolicy = policies["termination"]
        self.loop_prevention: LoopPreventionPolicy = policies["loop_prevention"]
        self.hitl_policy: HITLPolicy = policies.get("hitl", DefaultHITLPolicy(enabled=False))
        self.checkpoint_policy: CheckpointPolicy = policies.get("checkpoint", DefaultCheckpointPolicy(enabled=False))
        
        self.logger = get_logger()

    async def run(
        self,
        task: str,
        progress_handler: Optional[BaseProgressHandler] = None,
        script: Optional[List[Dict[str, Any]]] = None,
        script_metadata: Optional[Dict[str, Any]] = None,
        execution_context: Optional[Dict[str, Any]] = None,
        suggested_plan: Optional[List[Dict[str, Any]]] = None,
    ) -> Any:
        """Execute task with policy-driven behavior control."""
        normalized_exec_context = self._normalize_execution_context(execution_context)
        # Start event
        start_data = build_agent_start_event(
            task=task,
            agent_name=self.name,
            agent_version=self.version,
            prompt=(normalized_exec_context or {}).get("assembled_context") if normalized_exec_context else None,
            manager_context=normalized_exec_context,
        )
        self.event_bus.publish("agent_start", start_data)
        if progress_handler:
            await progress_handler.on_event("agent_start", start_data)

        self.memory.add({"type": TASK, "content": task})
        if script:
            self.memory.add({
                "type": SCRIPT_INSTRUCTION,
                "content": {
                    "metadata": script_metadata or {},
                    "steps": script,
                },
            })
        planner_task = task
        if suggested_plan and not script:
            plan_text = self._format_suggested_plan(suggested_plan)
            self.memory.add({"type": SUGGESTED_PLAN, "content": suggested_plan})
            planner_task = self._augment_task_with_plan(task, plan_text)

        ctx_for_application = normalized_exec_context if normalized_exec_context is not None else execution_context
        self._apply_execution_context(ctx_for_application)

        # Build context for policies
        try:
            from ..services.request_context import get_from_context as _get_ctx
            job_id = _get_ctx("JOB_ID") or _get_ctx("job_id")
            approvals = _get_ctx("approvals") or {}
        except Exception:
            job_id = None
            approvals = {}
        
        policy_context = {
            "task": task,
            "agent_name": self.name,
            "job_id": job_id,
            "approvals": approvals
        }

        # Script execution mode bypasses planner/LLM reasoning
        if script:
            return await self._run_script_mode(
                task,
                script,
                script_metadata or {},
                progress_handler,
                policy_context,
            )

        # Iterative plan-act-observe loop
        iteration_count = 0
        action_history = deque(maxlen=self.loop_prevention.action_window)
        observation_history = deque(maxlen=self.loop_prevention.observation_window)

        while True:
            iteration_count += 1
            
            # Check if last action was complete_task (before planning new actions)
            # FIX: Skip on iteration 1 - on first iteration, we haven't executed anything
            # for THIS task yet. Any completed observations are from PREVIOUS agent runs
            # in the same job and should not cause early termination.
            if iteration_count > 1 and self.memory.get_history():
                last_action = next(
                    (entry for entry in reversed(self.memory.get_history()) if entry.get("type") == "action"),
                    None
                )
                if last_action and last_action.get("tool") == "complete_task":
                    # Last action was complete_task - check if we have a final result
                    last_obs = next(
                        (entry for entry in reversed(self.memory.get_history()) if entry.get("type") == "observation"),
                        None
                    )
                    if last_obs:
                        obs_content = last_obs.get("content")
                        if isinstance(obs_content, dict) and obs_content.get("completed") is True:
                            # Extract final response from observation
                            if "operation" in obs_content and "payload" in obs_content:
                                final_response = FinalResponse(
                                    operation=obs_content.get("operation", "display_message"),
                                    payload=obs_content.get("payload", {}),
                                    human_readable_summary=obs_content.get("human_readable_summary") or obs_content.get("summary", "Task completed.")
                                )
                                return await self._handle_final_response(final_response, progress_handler)
            
            # Plan next action
            plan_outcome = self.planner.plan(planner_task, self.memory.get_history())
            
            # Check termination policy (includes max_iterations, FinalResponse, completion)
            if self.termination_policy.should_terminate(
                iteration_count, plan_outcome, self.memory.get_history(), policy_context
            ):
                if isinstance(plan_outcome, FinalResponse):
                    return await self._handle_final_response(plan_outcome, progress_handler)
                else:
                    # Termination policy detected completion via other means
                    return await self._create_completion_response(
                        "Task completed (detected by termination policy).",
                        progress_handler
                    )
            
            # Normalize to list of actions
            actions = [plan_outcome] if isinstance(plan_outcome, Action) else plan_outcome
            
            # Check if planner is trying to plan complete_task again (shouldn't happen, but safety check)
            if any(isinstance(a, Action) and a.tool_name == "complete_task" for a in actions):
                # If we already executed complete_task, don't execute it again
                if any(entry.get("tool") == "complete_task" for entry in self.memory.get_history() if entry.get("type") == "action"):
                    return await self._create_completion_response(
                        "Task already completed. Stopping execution.",
                        progress_handler
                    )
            
            # Check loop prevention BEFORE execution (to catch repeated planning)
            stagnation_reason = self.loop_prevention.detect_stagnation(
                list(action_history),
                list(observation_history),
                policy_context
            )
            if stagnation_reason:
                return await self._create_error_response(
                    f"Loop detected: {stagnation_reason}",
                    progress_handler,
                    stagnation=True
                )
            
            # Create action signature for loop prevention
            def make_hashable(obj):
                """Convert an object to a hashable representation."""
                if isinstance(obj, dict):
                    return tuple(sorted((k, make_hashable(v)) for k, v in obj.items()))
                elif isinstance(obj, list):
                    return tuple(make_hashable(item) for item in obj)
                elif isinstance(obj, set):
                    return tuple(sorted(make_hashable(item) for item in obj))
                else:
                    return obj
            
            action_signature = tuple(
                (a.tool_name, make_hashable(a.tool_args) if isinstance(a.tool_args, dict) else make_hashable(a.tool_args))
                for a in actions
            )
            action_history.append(action_signature)
            
            # Emit action_planned events
            for action in actions:
                tool_obj = self.tools.get(action.tool_name)
                tool_description = getattr(tool_obj, "description", "") if tool_obj else ""
                tool_label = self._tool_label(tool_obj, action.tool_name)
                planned_data = build_action_planned_event(
                    actor_role="agent",
                    actor_name=self.name,
                    actor_version=self.version,
                    tool_name=action.tool_name,
                    args=action.tool_args,
                    tool_label=tool_label,
                    tool_description=tool_description,
                )
                self.event_bus.publish("action_planned", planned_data)
                if progress_handler:
                    await progress_handler.on_event("action_planned", planned_data)

            # Check HITL before execution
            for action in actions:
                if self.hitl_policy.requires_approval(
                    action.tool_name,
                    action.tool_args,
                    policy_context
                ):
                    approval_request = self.hitl_policy.create_approval_request(
                        action.tool_name,
                        action.tool_args,
                        policy_context
                    )
                    return await self._handle_approval_request(approval_request, progress_handler)

            # Execute actions
            results = await self._execute_actions(actions, progress_handler, policy_context)
            
            # Check for execution errors
            if any(isinstance(r, Exception) for r in results):
                return await self._handle_execution_errors(results, progress_handler)
            
            # Record actions and observations
            for action, result in zip(actions, results):
                self.memory.add({
                    "type": ACTION,
                    "tool": action.tool_name,
                    "args": action.tool_args
                })
                
                # Format observation
                if isinstance(result, dict) and result.get("error"):
                    error_obs = (
                        f"❌ ERROR: Tool '{action.tool_name}' failed!\n"
                        f"Error: {result.get('error_message', 'Unknown error')}"
                    )
                    self.memory.add({"type": OBSERVATION, "content": error_obs})
                    observation_history.append(error_obs)
                else:
                    self.memory.add({"type": OBSERVATION, "content": result})
                    observation_history.append(str(result))
                
                # Special handling: complete_task tool should immediately terminate
                if action.tool_name == "complete_task":
                    # Extract final response from complete_task result if available
                    if isinstance(result, dict):
                        # Check for completion flag (primary indicator)
                        if result.get("completed") is True:
                            # Check if result already has FinalResponse structure
                            if "operation" in result and "payload" in result:
                                final_response = FinalResponse(
                                    operation=result.get("operation", "display_message"),
                                    payload=result.get("payload", {}),
                                    human_readable_summary=result.get("human_readable_summary") or result.get("summary", "Task completed.")
                                )
                            else:
                                # Convert tool results to appropriate FinalResponse format
                                from ..utils.result_formatter import (
                                    convert_get_tool_result_to_message
                                )
                                final_response = convert_get_tool_result_to_message(
                                    action.tool_name,
                                    result,
                                    action.tool_args
                                )
                            # CRITICAL: Return immediately to stop the loop - this prevents any further iterations
                            return await self._handle_final_response(final_response, progress_handler)
            
            # Check completion after observation (this is the right place to check)
            last_result = results[-1] if results else None
            if last_result and self.completion_detector.is_complete(
                last_result, self.memory.get_history(), policy_context
            ):
                # Convert tool results to appropriate FinalResponse format
                last_action = actions[-1] if actions else None
                if last_action:
                    from ..utils.result_formatter import (
                        should_convert_to_display_table,
                        should_convert_to_display_message,
                        convert_list_tool_result_to_display_table,
                        convert_get_tool_result_to_message,
                        convert_any_tool_result
                    )
                    # Try specific converters first
                    if should_convert_to_display_table(last_action.tool_name):
                        final_response = convert_list_tool_result_to_display_table(
                            last_action.tool_name,
                            last_result if isinstance(last_result, dict) else {},
                            last_action.tool_args
                        )
                        return await self._handle_final_response(final_response, progress_handler)
                    elif should_convert_to_display_message(last_action.tool_name) and isinstance(last_result, dict):
                        final_response = convert_get_tool_result_to_message(
                            last_action.tool_name,
                            last_result,
                            last_action.tool_args
                        )
                        return await self._handle_final_response(final_response, progress_handler)
                    else:
                        # Try generic converter for any tool result
                        try:
                            final_response = convert_any_tool_result(
                                last_action.tool_name,
                                last_result,
                                last_action.tool_args
                            )
                            return await self._handle_final_response(final_response, progress_handler)
                        except Exception:
                            # If conversion fails, fall through to default
                            pass
                
                # Task complete - create final response
                return await self._create_completion_response(
                    "Task completed successfully.",
                    progress_handler,
                    result=last_result
                )
            
            # Check loop prevention AFTER execution (to catch repeated actions with same results)
            stagnation_reason = self.loop_prevention.detect_stagnation(
                list(action_history),
                list(observation_history),
                policy_context
            )
            if stagnation_reason:
                return await self._create_error_response(
                    f"Loop detected: {stagnation_reason}",
                    progress_handler,
                    stagnation=True
                )
            
            # Check for checkpoint after execution
            if last_result and self.checkpoint_policy.should_checkpoint(
                last_result,
                iteration_count,
                {"last_tool": actions[-1].tool_name if actions else None, **policy_context}
            ):
                checkpoint_response = self.checkpoint_policy.create_checkpoint_response(
                    last_result,
                    policy_context
                )
                return await self._handle_checkpoint(checkpoint_response, progress_handler)
            
            # Check for approval requests (from tools)
            awaiting = next(
                (r for r in results if isinstance(r, dict) and r.get("await_approval")),
                None
            )
            if awaiting:
                return await self._handle_approval_request(awaiting, progress_handler)

    async def _handle_final_response(
        self,
        final_response: FinalResponse,
        progress_handler: Optional[BaseProgressHandler]
    ) -> Dict[str, Any]:
        """Handle FinalResponse from planner."""
        self.memory.add({"type": FINAL, "content": final_response.human_readable_summary})
        
        end_data = build_agent_end_event(
            agent_name=self.name,
            agent_version=self.version,
            result=final_response.model_dump(),
        )
        end_data["level"] = "worker"
        self.event_bus.publish("agent_end", end_data)
        if progress_handler:
            await progress_handler.on_event("agent_end", end_data)
        
        return final_response.model_dump()

    async def _create_completion_response(
        self,
        message: str,
        progress_handler: Optional[BaseProgressHandler],
        result: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Create completion response."""
        if result and isinstance(result, dict):
            # Use result structure if available
            final_response = FinalResponse(
                operation=result.get("operation", "display_message"),
                payload=result.get("payload", {"message": message}),
                human_readable_summary=result.get("human_readable_summary", message)
            )
        else:
            final_response = FinalResponse(
                operation="display_message",
                payload={"message": message},
                human_readable_summary=message
            )
        
        return await self._handle_final_response(final_response, progress_handler)

    async def _create_error_response(
        self,
        message: str,
        progress_handler: Optional[BaseProgressHandler],
        stagnation: bool = False
    ) -> Dict[str, Any]:
        """Create error response."""
        self.memory.add({"type": ERROR, "content": message})
        
        error_response = FinalResponse(
            operation="display_message",
            payload={"message": message, "error": True, "stagnation": stagnation},
            human_readable_summary=message
        )
        
        end_data = build_agent_end_event(
            agent_name=self.name,
            agent_version=self.version,
            result=error_response.model_dump(),
            status="error",
            error_message=message,
        )
        end_data["level"] = "worker"
        self.event_bus.publish("agent_end", end_data)
        if progress_handler:
            await progress_handler.on_event("agent_end", end_data)
        
        return error_response.model_dump()

    def _normalize_execution_context(self, execution_context: Optional[Any]) -> Optional[Dict[str, Any]]:
        """Normalize execution context payloads to a dict structure."""
        if execution_context is None:
            return None
        if isinstance(execution_context, dict):
            return execution_context
        if isinstance(execution_context, str):
            return {"assembled_context": execution_context}
        try:
            return {"assembled_context": str(execution_context)}
        except Exception:
            return {"assembled_context": "Context provided but could not be serialized."}

    def _apply_execution_context(self, execution_context: Optional[Any]) -> None:
        """Persist injected execution context for planners and tools."""
        normalized = self._normalize_execution_context(execution_context)
        if not normalized:
            return
        try:
            self.memory.add({"type": INJECTED_CONTEXT, "content": normalized})
        except Exception:
            pass

        assembled = normalized.get("assembled_context")
        if assembled:
            update_request_context(worker_context=assembled, context=assembled, director_context=assembled)

        manifest_text = normalized.get("schema_manifest")
        if manifest_text:
            update_request_context(data_model_context=manifest_text)

        director_goal = normalized.get("director_goal")
        if director_goal:
            update_request_context(director_goal=director_goal)

    def _format_suggested_plan(self, suggested_plan: List[Dict[str, Any]]) -> str:
        """Serialize suggested plans for planner context."""
        try:
            return json.dumps(suggested_plan, indent=2)
        except Exception:
            return str(suggested_plan)

    def _augment_task_with_plan(self, task: str, plan_text: str) -> str:
        """Append suggested-plan instructions to the planner task text."""
        base_task = task.strip() or "(no task provided)"
        plan_block = plan_text.strip()
        sections = [base_task]
        if plan_block:
            sections.extend(["", "== Manager Suggested Plan ==", plan_block])
        return "\n".join(sections).strip()

    async def _run_script_mode(
        self,
        task: str,
        script: List[Dict[str, Any]],
        script_metadata: Dict[str, Any],
        progress_handler: Optional[BaseProgressHandler],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute a scripted list of tool calls sequentially."""
        if not script:
            return await self._create_error_response(
                "Script execution requested but no steps were provided",
                progress_handler,
            )

        overall_status = "SUCCESS"
        step_records: List[Dict[str, Any]] = []
        goal_text = script_metadata.get("goal") or task
        thought = script_metadata.get("thought")

        for idx, raw_step in enumerate(script, 1):
            worker_hint = raw_step.get("worker") or raw_step.get("worker_key")
            tool_name = raw_step.get("tool_name") or raw_step.get("tool")
            args = raw_step.get("args") or {}
            step_name = raw_step.get("name") or raw_step.get("description") or f"Step {idx}"
            notes = raw_step.get("notes")

            if not tool_name:
                overall_status = "FAILED"
                step_records.append({
                    "index": idx,
                    "name": step_name,
                    "worker": worker_hint,
                    "tool": None,
                    "status": "failed",
                    "error": "Missing tool_name in script step",
                })
                break

            planned_data = build_action_planned_event(
                actor_role="agent",
                actor_name=self.name,
                actor_version=self.version,
                tool_name=tool_name,
                args=args,
                metadata={"script": True},
            )
            planned_data.update({
                "script_step": step_name,
                "script_index": idx,
                "script_goal": goal_text,
            })
            self.event_bus.publish("action_planned", planned_data)
            if progress_handler:
                await progress_handler.on_event("action_planned", planned_data)
            self.memory.add({
                "type": ACTION,
                "tool": tool_name,
                "step": step_name,
                "script": True,
                "args": args,
            })

            action = Action(tool_name=tool_name, tool_args=args)
            results = await self._execute_actions([action], progress_handler, context)
            result = results[0] if results else None

            failure = self._is_script_step_failure(result)
            if isinstance(result, Exception):
                result_payload: Any = {"error": str(result)}
            else:
                result_payload = result
            self.memory.add({
                "type": OBSERVATION,
                "content": result_payload,
                "step": step_name,
                "script": True,
            })

            step_records.append({
                "index": idx,
                "name": step_name,
                "worker": worker_hint,
                "tool": tool_name,
                "notes": notes,
                "status": "failed" if failure else "success",
                "args": args,
                "result": result_payload,
            })

            if failure:
                overall_status = "FAILED"
                break

        summary = f"Executed {len(step_records)} scripted step(s) ({overall_status})"
        payload = {
            "message": summary,
            "overall_status": overall_status,
            "script_goal": goal_text,
            "script_steps": step_records,
        }
        if thought:
            payload["script_thought"] = thought
        if script_metadata.get("notes"):
            payload["script_notes"] = script_metadata["notes"]

        script_response = {
            "operation": "display_message",
            "payload": payload,
            "human_readable_summary": summary,
        }
        return await self._create_completion_response(summary, progress_handler, script_response)

    def _is_script_step_failure(self, result: Any) -> bool:
        """Determine if a scripted tool call failed."""
        if isinstance(result, Exception):
            return True
        if isinstance(result, dict):
            if result.get("error") or result.get("success") is False:
                return True
            payload = result.get("payload")
            if isinstance(payload, dict) and (payload.get("error") or payload.get("success") is False):
                return True
        return False


    async def _handle_execution_errors(
        self,
        results: List[Any],
        progress_handler: Optional[BaseProgressHandler]
    ) -> Dict[str, Any]:
        """Handle execution errors."""
        error_msgs = [str(r) for r in results if isinstance(r, Exception)]
        msg = f"Errors during execution: {'; '.join(error_msgs)}"
        err_data = build_error_event(
            actor_role="agent",
            actor_name=self.name,
            actor_version=self.version,
            message=msg,
        )
        self.event_bus.publish("error", err_data)
        if progress_handler:
            await progress_handler.on_event("error", err_data)
        self.memory.add({"type": ERROR, "content": msg})
        
        return await self._create_error_response(msg, progress_handler)

    async def _handle_approval_request(
        self,
        approval_request: Dict[str, Any],
        progress_handler: Optional[BaseProgressHandler]
    ) -> Dict[str, Any]:
        """Handle approval request."""
        # Convert to FinalResponse if needed
        if isinstance(approval_request, dict) and "operation" in approval_request:
            final_response = FinalResponse(
                operation=approval_request["operation"],
                payload=approval_request.get("payload", approval_request),
                human_readable_summary=approval_request.get("human_readable_summary", "Awaiting approval")
            )
        else:
            final_response = FinalResponse(
                operation="await_approval",
                payload=approval_request,
                human_readable_summary=approval_request.get("message", "Awaiting approval")
            )
        
        end_data = build_agent_end_event(
            agent_name=self.name,
            agent_version=self.version,
            result=final_response.model_dump(),
            status="pending",
        )
        end_data["level"] = "worker"
        self.event_bus.publish("agent_end", end_data)
        if progress_handler:
            await progress_handler.on_event("agent_end", end_data)
        
        return final_response.model_dump()

    async def _handle_checkpoint(
        self,
        checkpoint_response: FinalResponse,
        progress_handler: Optional[BaseProgressHandler]
    ) -> Dict[str, Any]:
        """Handle checkpoint response."""
        end_data = build_agent_end_event(
            agent_name=self.name,
            agent_version=self.version,
            result=checkpoint_response.model_dump(),
            metadata={"checkpoint": True},
        )
        end_data["checkpoint"] = True
        end_data["level"] = "worker"
        self.event_bus.publish("agent_end", end_data)
        if progress_handler:
            await progress_handler.on_event("agent_end", end_data)
        
        return checkpoint_response.model_dump()

    async def _execute_actions(
        self,
        actions: List[Action],
        progress_handler: Optional[BaseProgressHandler],
        context: Dict[str, Any]
    ) -> List[Any]:
        """
        Execute a list of actions in parallel using asyncio.gather.
        
        Args:
            actions: List of Action objects to execute
            progress_handler: Optional progress handler for emitting events
            context: Execution context (for job store, etc.)
            
        Returns:
            List of results (or Exceptions if execution failed)
        """
        # Validate and prepare all tools
        tool_calls = []
        for action in actions:
            tool = self.tools.get(action.tool_name)
            if not tool:
                available = ", ".join(sorted(self.tools.keys()))
                tool_calls.append(Exception(f"Tool not found: {action.tool_name}. Available: [{available}]"))
                continue
            
            # Validate args using Pydantic schema
            tool_kwargs: Dict[str, Any] = action.tool_args
            if getattr(tool, "args_schema", None):
                try:
                    model = tool.args_schema.model_validate(tool_kwargs)
                    tool_kwargs = model.model_dump()
                except ValidationError as ve:
                    tool_calls.append(Exception(f"Validation failed for {tool.name}: {ve}"))
                    continue
            
            tool_calls.append((tool, tool_kwargs))
        
        # Execute all tools in parallel
        async def execute_tool(item, action_idx):
            """Helper to execute a single tool and emit events"""
            if isinstance(item, Exception):
                return item
            
            tool, kwargs = item
            action = actions[action_idx]
            
            try:
                call_id = str(uuid.uuid4())
                tool_label = self._tool_label(tool, tool.name)

                async def _publish_worker_tool_result(
                    result_payload: Any,
                    *,
                    success_override: Optional[bool] = None,
                    error_message: Optional[str] = None,
                    execution_time_ms: Optional[int] = None,
                ) -> None:
                    success = self._is_success_result(result_payload) if success_override is None else success_override
                    summary = self._summarize_result(result_payload)
                    event_payload = build_worker_tool_result_event(
                        worker_name=self.name,
                        worker_version=self.version,
                        call_id=call_id,
                        tool_name=tool.name,
                        tool_label=tool_label,
                        tool_description=getattr(tool, "description", ""),
                        args=kwargs,
                        result_payload=result_payload,
                        success=success,
                        summary=summary,
                        error_message=error_message,
                        action_index=action_idx,
                        execution_time_ms=execution_time_ms,
                    )
                    self.event_bus.publish("worker_tool_result", event_payload)
                    if progress_handler:
                        await progress_handler.on_event("worker_tool_result", event_payload)

                call_event = build_worker_tool_call_event(
                    worker_name=self.name,
                    worker_version=self.version,
                    call_id=call_id,
                    tool_name=tool.name,
                    tool_label=tool_label,
                    tool_description=getattr(tool, "description", ""),
                    args=kwargs,
                    action_index=action_idx,
                )
                self.event_bus.publish("worker_tool_call", call_event)
                if progress_handler:
                    await progress_handler.on_event("worker_tool_call", call_event)

                # Central policy evaluation before running tool
                try:
                    from ..services.policy import PolicyEngine
                    allowed, deny_msg = PolicyEngine.get().evaluate(action.tool_name, kwargs)
                except Exception:
                    allowed, deny_msg = True, None
                if not allowed:
                    # Emit policy_denied event and short-circuit via error path
                    policy_event = build_policy_denied_event(
                        actor_name=self.name,
                        actor_version=self.version,
                        tool_name=tool.name,
                        reason=deny_msg,
                    )
                    self.event_bus.publish("policy_denied", policy_event)
                    if progress_handler:
                        await progress_handler.on_event("policy_denied", policy_event)
                    await _publish_worker_tool_result(
                        {
                            "error": True,
                            "error_message": deny_msg,
                            "policy_denied": True,
                            "tool": tool.name,
                        },
                        success_override=False,
                        error_message=deny_msg,
                        execution_time_ms=0,
                    )
                    return Exception(f"Policy denied for {tool.name}: {deny_msg}")

                # Execute tool (synchronous tools run in thread pool to avoid blocking)
                import asyncio as aio
                loop = aio.get_event_loop()

                # Optional OTel span around tool execution for Phoenix hierarchy
                tracer = None
                try:
                    from opentelemetry import trace  # type: ignore
                    tracer = trace.get_tracer("agent-framework.tool")
                except Exception:
                    tracer = None

                # CRITICAL: Capture context before executor to ensure it propagates to thread
                import contextvars
                ctx = contextvars.copy_context()
                
                # Create a proper callable for executor that preserves context
                def run_tool():
                    return tool.execute(**kwargs)

                execution_time_ms: Optional[int] = None

                if tracer is not None:
                    with tracer.start_as_current_span(f"tool.{tool.name}") as span:  # type: ignore
                        try:
                            span.set_attribute("tool.name", tool.name)  # type: ignore[attr-defined]
                            # Capture structured input (args) as proper JSON
                            import json as _json
                            import os
                            try:
                                args_json = _json.dumps(kwargs, default=str)
                                span.set_attribute("tool.input.args_json", args_json)  # type: ignore[attr-defined]
                                # Also add pretty version if enabled
                                try:
                                    if os.getenv("PHOENIX_PRETTY_JSON", "false").lower() in {"1", "true", "yes"}:
                                        args_pretty = _json.dumps(kwargs, indent=2, ensure_ascii=False, default=str)
                                        max_chars = int(os.getenv("PHOENIX_MAX_ATTR_CHARS", "4000"))
                                        span.set_attribute("tool.input.args.pretty", args_pretty[:max_chars])  # type: ignore[attr-defined]
                                except Exception:
                                    pass
                            except Exception:
                                # Fallback to string if JSON serialization fails
                                span.set_attribute("tool.input.args", str(kwargs))  # type: ignore[attr-defined]
                        except Exception:
                            pass
                        start_ts = time.perf_counter()
                        # Run in executor with explicit context propagation
                        result = await loop.run_in_executor(None, ctx.run, run_tool)
                        end_ts = time.perf_counter()
                        execution_time_ms = int((end_ts - start_ts) * 1000)
                        try:
                            span.set_attribute("tool.latency_ms", execution_time_ms)  # type: ignore[attr-defined]
                            # Capture structured output (result)
                            try:
                                import os
                                max_chars = int(os.getenv("PHOENIX_MAX_ATTR_CHARS", "4000"))
                                if isinstance(result, dict):
                                    # Extract summary for quick reference
                                    result_summary = str(result.get("human_readable_summary") or 
                                                        result.get("summary") or 
                                                        result.get("message") or
                                                        str(result)[:200])
                                    span.set_attribute("tool.output.result_summary", result_summary[:max_chars])  # type: ignore[attr-defined]
                                    # Also add full result as JSON if not too large
                                    try:
                                        result_json = _json.dumps(result, default=str)
                                        if len(result_json) <= max_chars:
                                            span.set_attribute("tool.output.result_json", result_json)  # type: ignore[attr-defined]
                                        # Pretty version if enabled
                                        if os.getenv("PHOENIX_PRETTY_JSON", "false").lower() in {"1", "true", "yes"}:
                                            result_pretty = _json.dumps(result, indent=2, ensure_ascii=False, default=str)
                                            span.set_attribute("tool.output.result.pretty", result_pretty[:max_chars])  # type: ignore[attr-defined]
                                    except Exception:
                                        pass
                                else:
                                    # Non-dict result - convert to string
                                    result_str = str(result)
                                    span.set_attribute("tool.output.result", result_str[:max_chars])  # type: ignore[attr-defined]
                            except Exception:
                                pass
                        except Exception:
                            pass
                else:
                    start_ts = time.perf_counter()
                    # Run in executor with explicit context propagation
                    result = await loop.run_in_executor(None, ctx.run, run_tool)
                    end_ts = time.perf_counter()
                    execution_time_ms = int((end_ts - start_ts) * 1000)
                
                await _publish_worker_tool_result(result, execution_time_ms=execution_time_ms)

                # Emit action_executed event
                executed_data = build_action_executed_event(
                    actor_role="agent",
                    actor_name=self.name,
                    actor_version=self.version,
                    tool_name=tool.name,
                    args=action.tool_args,
                    result=result,
                    execution_time_ms=execution_time_ms,
                    tool_label=self._tool_label(tool, tool.name),
                )
                self.event_bus.publish("action_executed", executed_data)
                if progress_handler:
                    await progress_handler.on_event("action_executed", executed_data)

                # Record successful execution signature to job store for future HITL bypass
                try:
                    # Treat as success unless explicit error structure
                    is_error = isinstance(result, dict) and (
                        result.get("error") or 
                        result.get("success") is False or 
                        result.get("error_message")
                    )
                    if not is_error:
                        job_id = context.get("job_id")
                        if job_id:
                            import json as _json
                            sig = f"{tool.name}:{_json.dumps(kwargs, sort_keys=True, default=str)}"
                            from ..state.job_store import get_job_store
                            get_job_store().add_executed_action(str(job_id), sig)
                except Exception:
                    pass

                return result
            except Exception as e:
                # Emit error event but don't crash - return structured error
                error_message = str(e)
                err_data = build_error_event(
                    actor_role="agent",
                    actor_name=self.name,
                    actor_version=self.version,
                    message=f"Tool {tool.name} failed: {error_message}",
                    details={"tool": tool.name},
                )
                self.event_bus.publish("error", err_data)
                if progress_handler:
                    await progress_handler.on_event("error", err_data)
                
                error_payload = {
                    "success": False,
                    "error": True,
                    "error_message": error_message,
                    "error_type": type(e).__name__,
                    "tool": tool.name,
                    "message": f"❌ ERROR: {error_message}"
                }
                await _publish_worker_tool_result(error_payload, success_override=False, error_message=error_message)
                
                # Return structured error dict that the planner can understand
                return error_payload
        
        # Execute all tools concurrently
        import asyncio as aio
        results = await aio.gather(
            *[execute_tool(item, idx) for idx, item in enumerate(tool_calls)],
            return_exceptions=True
        )
        
        return list(results)

    def _is_success_result(self, result: Any) -> bool:
        if isinstance(result, dict):
            if result.get("error") or result.get("success") is False or result.get("error_message"):
                return False
            payload = result.get("payload")
            if isinstance(payload, dict) and (payload.get("error") or payload.get("success") is False):
                return False
        return True

    def _summarize_result(self, result: Any) -> str:
        if isinstance(result, dict):
            for key in ("human_readable_summary", "summary", "message", "status"):
                value = result.get(key)
                if value:
                    return str(value)[:500]
            payload = result.get("payload")
            if isinstance(payload, dict):
                for key in ("message", "summary"):
                    value = payload.get(key)
                    if value:
                        return str(value)[:500]
            return str(result)[:500]
        return str(result)[:500]

    def _tool_label(self, tool: Optional[BaseTool], fallback: Optional[str] = None) -> str:
        label = None
        if tool is not None:
            for attr in ("display_name", "short_description"):
                candidate = getattr(tool, attr, None)
                if isinstance(candidate, str) and candidate.strip():
                    label = candidate.strip()
                    break
        if label:
            return label

        name = getattr(tool, "name", None) if tool is not None else None
        if not name:
            name = fallback
        if isinstance(name, str) and name.strip():
            cleaned = name.replace("_", " ").replace("-", " ").strip()
            if cleaned:
                return " ".join(word.capitalize() for word in cleaned.split())
        return fallback or "Tool"
    
    def _aggregate_parallel_results(self, actions: List[Action], results: List[Any]) -> Dict[str, Any]:
        """Aggregate results from multiple parallel tool executions.
        
        This method is kept for backward compatibility with terminal tools logic,
        but in v2, termination is handled by policies.
        """
        # Group actions by tool type
        from collections import defaultdict
        tool_groups = defaultdict(list)
        for idx, action in enumerate(actions):
            tool_groups[action.tool_name].append((action, results[idx]))
        
        # Check if all tools are the same type
        unique_tools = list(tool_groups.keys())
        is_homogeneous = len(unique_tools) == 1
        
        if is_homogeneous:
            tool_name = unique_tools[0]
            
            # Handle list_columns specially
            if tool_name == "list_columns":
                all_tables_data = []
                total_columns = 0
                
                for action, result in zip(actions, results):
                    if isinstance(result, dict):
                        table_name = result.get("table") or action.tool_args.get("table", "Unknown")
                        columns = result.get("columns", [])
                        total_columns += len(columns)
                        all_tables_data.append({
                            "table": table_name,
                            "columns": columns,
                            "count": len(columns)
                        })
                
                rows = []
                for table_data in all_tables_data:
                    for col in table_data["columns"]:
                        rows.append([
                            table_data["table"],
                            col.get("name", ""),
                            col.get("dataType", "")
                        ])
                
                return {
                    "operation": "display_table",
                    "payload": {
                        "title": f"Columns from {len(all_tables_data)} Tables",
                        "headers": ["Table", "Column Name", "Data Type"],
                        "rows": rows
                    },
                    "summary": f"Found {total_columns} columns across {len(all_tables_data)} tables"
                }
            
            # Other homogeneous tools
            else:
                return {
                    "operation": "display_message",
                    "payload": {
                        "message": f"Executed {len(actions)} {tool_name} calls in parallel",
                        "results": [r for r in results if not isinstance(r, Exception)]
                    },
                    "summary": f"Completed {len(actions)} {tool_name} executions"
                }
        
        # Heterogeneous tools
        else:
            return {
                "operation": "display_message",
                "payload": {
                    "message": f"Executed {len(actions)} parallel tool calls",
                    "results": [r for r in results if not isinstance(r, Exception)]
                },
                "summary": f"Completed {len(actions)} parallel tool executions"
            }
