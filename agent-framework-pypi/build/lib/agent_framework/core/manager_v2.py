"""
ManagerAgent class v2 - Policy-driven manager with configurable delegation and follow-ups.

This version replaces all hardcoded behavior with configurable policies.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from ..base import BasePlanner, BaseMemory, BaseProgressHandler, Action, FinalResponse, BaseTool, BaseJobStore
from .events import EventBus
from .event_payloads import (
    build_action_executed_event,
    build_action_planned_event,
    build_delegation_event,
    build_error_event,
    build_manager_end_event,
    build_manager_script_planned_event,
    build_manager_start_event,
    build_segment_event,
)
from ..services.request_context import update_request_context
from ..services.request_context import get_from_context as _get_ctx
from ..services.context_builder import ContextBuilder
from ..policies.base import (
    CompletionDetector,
    FollowUpPolicy,
    LoopPreventionPolicy,
)
from ..policies.default import (
    DefaultCompletionDetector,
    DefaultFollowUpPolicy,
    DefaultLoopPreventionPolicy,
)
from ..utils.script_args import normalize_script_args
from ..constants import (
    SYNTHESIS,
    TASK,
    ACTION,
    OBSERVATION,
    ERROR,
    FINAL,
    STRATEGIC_PLAN,
    SCRIPT_PLAN,
    DELEGATION,
    GLOBAL_OBSERVATION,
    DIRECTOR_CONTEXT,
)
from pydantic import ValidationError


class ManagerAgent:
    """Policy-driven manager with configurable delegation and follow-ups."""
    
    def __init__(
        self,
        planner: BasePlanner,
        memory: BaseMemory,
        workers: List[Any] | Dict[str, Any],
        policies: Dict[str, Any],  # REQUIRED - no defaults
        tools: Optional[List[BaseTool] | Dict[str, BaseTool]] = None,
        event_bus: Optional[EventBus] = None,
        name: str | None = None,
        description: str | None = None,
        version: str | None = None,
        synthesis_gateway: Optional[Any] = None,
        synthesis_prompt: Optional[str] = None,
        synthesizer_agent: Optional[Any] = None,
        job_store: Optional[BaseJobStore] = None,
    ) -> None:
        from agent_framework.logging import get_logger
        
        if not policies:
            raise ValueError("Policies are required for ManagerAgent.")
        
        # Validate required policies
        required_policies = ["completion", "follow_up", "loop_prevention"]
        for policy_name in required_policies:
            if policy_name not in policies:
                raise ValueError(f"Required policy '{policy_name}' not provided.")
        
        # Initialize components
        self.planner = planner
        self.memory = memory
        if isinstance(workers, dict):
            self.workers: Dict[str, Any] = dict(workers)
        else:
            self.workers = {f"worker{i}": w for i, w in enumerate(workers)}
        if isinstance(tools, dict):
            self.tools: Dict[str, BaseTool] = tools
        elif tools:
            self.tools = {t.name: t for t in tools}
        else:
            self.tools = {}
        self.event_bus = event_bus or EventBus()
        self.name = name or "ManagerAgent"
        self.description = description or "A manager agent."
        self.version = version or "2.0.0"
        self.synthesis_gateway = synthesis_gateway
        self.synthesis_prompt = synthesis_prompt or self._default_synthesis_prompt()
        self.synthesizer_agent = synthesizer_agent  # Optional separate synthesizer agent
        self.job_store = job_store  # Optional job persistence store
        self._context_builder: Optional[ContextBuilder] = None
        
        # Initialize policies (REQUIRED)
        self.completion_detector: CompletionDetector = policies["completion"]
        self.follow_up_policy: FollowUpPolicy = policies["follow_up"]
        self.loop_prevention: LoopPreventionPolicy = policies["loop_prevention"]
        
        self.logger = get_logger()
    
    def _default_synthesis_prompt(self) -> str:
        return """You are a manager analyzing worker results to provide higher-level insights.

Your role:
1. Synthesize raw data into meaningful patterns
2. Identify relationships and correlations
3. Assess quality and completeness
4. Provide actionable recommendations
5. Reorganize information for clarity

Return a final_response JSON with your analysis."""

    async def run(
        self,
        task: str,
        progress_handler: Optional[BaseProgressHandler] = None,
        strategic_plan: Optional[Dict[str, Any]] = None,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute task with policy-driven behavior control."""
        self.memory.add({"type": TASK, "content": task})
        
        # Get job_id from context (implementation-specific)
        job_id: Optional[str] = None
        try:
            job_id = _get_ctx("JOB_ID") or _get_ctx("job_id")
            # Create job in store if job_store is provided
            if job_id and self.job_store:
                self.job_store.create_job(str(job_id))
        except Exception:
            pass
        
        # If strategic plan provided, add to memory for context
        if strategic_plan:
            self.memory.add({"type": STRATEGIC_PLAN, "content": strategic_plan})
            update_request_context(strategic_plan=strategic_plan)
            # Persist plan in job store if provided
            try:
                if job_id and self.job_store:
                    if str(self.name).lower().startswith("orchestrator"):
                        self.job_store.update_orchestrator_plan(str(job_id), dict(strategic_plan))
                    else:
                        self.job_store.update_manager_plan(str(job_id), str(self.name), dict(strategic_plan))
            except Exception:
                pass
        builder = None
        if job_id:
            builder = ContextBuilder(str(job_id))
            self._context_builder = builder

        context_text = None
        manifest_text = None
        if builder:
            worker_descriptions = self._describe_workers()
            if self._is_orchestrator():
                context_text = builder.build_orchestrator_context(task, worker_descriptions)
                try:
                    manifest_text = builder.get_schema_manifest()
                    if manifest_text and len(manifest_text) > builder.MANAGER_MANIFEST_LIMIT:
                        manifest_text = manifest_text[: builder.MANAGER_MANIFEST_LIMIT]
                except Exception:
                    manifest_text = None
            else:
                context_text, manifest_summary = builder.build_manager_context(
                    context or task,
                    worker_descriptions,
                )
                manifest_text = manifest_summary or builder.get_schema_manifest()
        elif context:
            context_text = context

        self._inject_context(context_text, manifest_text)
        plan_summary = None
        manager_tools = None
        if not self._is_orchestrator():
            plan_summary = self._summarize_plan_for_events(strategic_plan)
            manager_tools = self._describe_manager_tools()
        start_data = build_manager_start_event(
            task=task,
            workers=list(self.workers.keys()),
            has_plan=strategic_plan is not None,
            manager_name=self.name,
            manager_version=self.version,
            prompt=context_text,
            orchestrator_plan=plan_summary,
            manager_tools=manager_tools,
        )
        self.event_bus.publish("manager_start", start_data)
        if progress_handler:
            await progress_handler.on_event("manager_start", start_data)

        if not self.workers:
            msg = "No workers available for delegation"
            return await self._create_error_response(msg, progress_handler)
        
        # Build context for policies
        try:
            job_id = _get_ctx("JOB_ID") or _get_ctx("job_id")
        except Exception:
            job_id = None

        policy_context = {
            "task": task,
            "manager_name": self.name,
            "job_id": job_id,
            "strategic_plan": strategic_plan
        }

        # Ask manager's planner to decide
        decision = self.planner.plan(task, self.memory.get_history())
        
        # Check if decision includes strategic plan from director
        if isinstance(decision, Action):
            worker_strategic_plan = decision.tool_args.get("strategic_plan")
            worker_context = decision.tool_args.get("original_task")
            if worker_strategic_plan:
                strategic_plan = worker_strategic_plan
                context = worker_context or task

        # Handle FinalResponse from planner
        if isinstance(decision, FinalResponse):
            return await self._handle_final_response(decision, progress_handler)

        # Handle parallel delegation
        if isinstance(decision, list):
            return await self._handle_parallel_delegation(
                decision, task, progress_handler, strategic_plan, context, policy_context
            )

        # Handle single delegation
        if not isinstance(decision, Action):
            return await self._create_error_response(
                "Planner did not return an actionable decision",
                progress_handler
            )

        action_key = decision.tool_name

        # Check if it's a worker
        if action_key in self.workers:
            return await self._delegate_with_follow_ups(
                action_key,
                task,
                progress_handler,
                decision.tool_args,
                strategic_plan,
                context,
                policy_context
            )

        # Check if it's a manager tool
        if action_key in self.tools:
            return await self._execute_manager_tool(decision, progress_handler)

        # Fallback: invalid action
        return await self._create_error_response(
            f"Invalid action: '{action_key}' is not a known worker or manager tool.",
            progress_handler
        )

    async def _delegate_with_follow_ups(
        self,
        worker_key: str,
        task: str,
        progress_handler: Optional[BaseProgressHandler],
        tool_args: Dict[str, Any],
        strategic_plan: Optional[Dict[str, Any]],
        context: Optional[str],
        policy_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Delegate to worker with configurable follow-ups."""
        
        script_steps: Optional[List[Dict[str, Any]]] = None
        script_metadata: Dict[str, Any] = {}
        if isinstance(tool_args, dict):
            maybe_script = tool_args.get("script")
            if isinstance(maybe_script, list):
                script_steps = maybe_script
            script_metadata = tool_args.get("script_metadata") or {}

        if script_steps:
            return await self._execute_script_plan(
                script_steps,
                task,
                progress_handler,
                script_metadata,
                strategic_plan,
                context,
            )

        # Fallback: try to get strategic plan from tool_args if not provided
        if not strategic_plan and isinstance(tool_args, dict):
            strategic_plan = tool_args.get("strategic_plan")
        
        # Extract phases from strategic plan
        # Supports both:
        # - Orchestrator phases: {"plan": {"phases": [...]}}
        # - Manager local steps: {"phases": [...]} (from StrategicDecomposerPlanner)
        phases = self._extract_phases(strategic_plan)
        
        # CRITICAL: If phases/steps exist, execute ALL sequentially in order
        # Each phase/step gets: orchestrator phase goals + previous step output
        # Ignore primary_worker override - use each phase's assigned worker and goals
        if phases and len(phases) > 0:
            return await self._execute_phases_sequentially(
                phases, task, progress_handler, tool_args, strategic_plan, context, policy_context
            )

        # Execute primary worker
        primary_result = await self._delegate_to_worker_parallel(
            worker_key, task, progress_handler, tool_args, strategic_plan, context
        )
        
        # Check for approval request
        if isinstance(primary_result, dict) and primary_result.get("operation") == "await_approval":
            return await self._handle_approval_request(primary_result, progress_handler)
        
        # Check completion before follow-ups
        if self.completion_detector.is_complete(primary_result, [], policy_context):
            self.logger.info("Task completed in primary worker. Skipping follow-ups.")
            return await self._finalize_result(primary_result, progress_handler)
        
        # Check if follow-ups should proceed
        completed_phases = 1  # Primary phase completed
        if not self.follow_up_policy.should_follow_up(
            primary_result, phases, completed_phases, policy_context
        ):
            return await self._finalize_result(primary_result, progress_handler)
        
        # Execute follow-up phases
        workers_run = [worker_key]
        results_run = [primary_result]
        
        for phase in phases[1:]:  # Skip first phase (already done)
            # Check if we should continue
            if not self.follow_up_policy.should_follow_up(
                results_run[-1], phases, completed_phases, policy_context
            ):
                break
            
            # Check completion after each phase
            if self.completion_detector.is_complete(
                results_run[-1], [], policy_context
            ):
                self.logger.info("Task completed in follow-up phase. Stopping.")
                break
            
            phase_worker = phase.get("worker")
            if phase_worker not in self.workers:
                continue
            
            # Execute phase
            phase_result = await self._delegate_to_worker_parallel(
                phase_worker, task, progress_handler, {}, strategic_plan, context
            )
            
            workers_run.append(phase_worker)
            results_run.append(phase_result)
            completed_phases += 1
            
            # Check for approval
            if isinstance(phase_result, dict) and phase_result.get("operation") == "await_approval":
                return await self._handle_approval_request(phase_result, progress_handler)
        
        # Aggregate results
        aggregated = self._aggregate_parallel_manager_results(
            [Action(tool_name=w, tool_args={}) for w in workers_run],
            results_run
        )
        
        # Optional synthesis
        final_result = aggregated
        if self.synthesis_gateway:
            synthesized = await self._synthesize_result(task, "sequential", aggregated)
            if synthesized:
                final_result = synthesized
        
        return await self._finalize_result(final_result, progress_handler)

    async def _execute_phases_sequentially(
        self,
        phases: List[Dict[str, Any]],
        task: str,
        progress_handler: Optional[BaseProgressHandler],
        tool_args: Dict[str, Any],
        strategic_plan: Optional[Dict[str, Any]],
        context: Optional[str],
        policy_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute all phases/steps sequentially in order, using each phase's/step's worker and goals.
        
        This ensures orchestrator always runs phases sequentially as planned, and managers
        run steps sequentially as planned, regardless of primary_worker override.
        Each phase/step executes with its assigned worker and goals.
        """
        workers_run: List[str] = []
        results_run: List[Dict[str, Any]] = []
        
        # Determine if this is manager steps (local plan) or orchestrator phases
        # Orchestrator plans come from StrategicPlanner and are passed directly as plan_data (flat structure)
        # Manager plans come from StrategicDecomposerPlanner and also have flat structure
        # Check manager name to distinguish: orchestrator runs phases, managers run steps
        is_manager_steps = self.name and isinstance(self.name, str) and "orchestrator" not in self.name.lower()
        term = "step" if is_manager_steps else "phase"
        term_capitalized = "Step" if is_manager_steps else "Phase"
        
        # Execute each phase/step sequentially in order
        previous_result: Optional[Dict[str, Any]] = None
        total_segments = len(phases)
        for idx, phase in enumerate(phases):
            phase_worker = phase.get("worker", "").strip()
            if not phase_worker or phase_worker not in self.workers:
                self.logger.warning(f"Skipping {term} {idx + 1}/{len(phases)} '{phase.get('name', 'unnamed')}': worker '{phase_worker}' not found in workers")
                continue
            
            # Extract task from phase/step goals, fallback to original task
            phase_task = phase.get("goals", "").strip()
            if not phase_task:
                phase_task = task
            
            # For subsequent phases/steps, combine orchestrator phase/step input with previous step output
            if idx > 0 and previous_result:
                previous_summary = self._format_previous_result(previous_result)
                phase_task = f"{phase_task}\n\n---\n\nPrevious {term_capitalized} Output:\n{previous_summary}"
            
            phase_name = phase.get("name", f"{term_capitalized} {idx + 1}")
            self.logger.info(f"Executing {term} {idx + 1}/{len(phases)}: '{phase_name}' -> worker: {phase_worker}")

            if is_manager_steps:
                step_item = {
                    "name": phase_name,
                    "worker": phase_worker,
                    "tool_name": phase.get("tool_name"),
                    "args": phase.get("args", {}),
                    "notes": phase.get("notes"),
                    "goals": phase_task,
                }
                start_event = build_segment_event(
                    actor_role="manager",
                    actor_name=self.name,
                    actor_version=self.version,
                    index_key="step_index",
                    total_key="total_steps",
                    item_key="step",
                    index=idx,
                    total=total_segments,
                    item=step_item,
                )
                start_event_name = "manager_step_start"
            else:
                phase_item = {
                    "name": phase_name,
                    "worker": phase_worker,
                    "goals": phase_task,
                    "notes": phase.get("notes"),
                }
                extra = {"strategic_plan": strategic_plan} if strategic_plan else None
                start_event = build_segment_event(
                    actor_role="manager",
                    actor_name=self.name,
                    actor_version=self.version,
                    index_key="phase_index",
                    total_key="total_phases",
                    item_key="phase",
                    index=idx,
                    total=total_segments,
                    item=phase_item,
                    extra=extra,
                )
                start_event_name = "orchestrator_phase_start"
            self.event_bus.publish(start_event_name, start_event)
            if progress_handler:
                await progress_handler.on_event(start_event_name, start_event)
            
            # Execute phase/step with phase-specific task
            # Store phase/step index in request context:
            # - Orchestrator phases: Manager's StrategicDecomposerPlanner needs to select correct orchestrator phase
            # - Manager steps: Workers might need to know which step they're executing (for nested ManagerAgents or context)
            from ..services.request_context import update_request_context
            if is_manager_steps:
                # Manager steps: Store as manager_step_index
                update_request_context(
                    manager_step_index=idx,  # 0-based index
                    manager_total_steps=len(phases)
                )
            else:
                # Orchestrator phases: Store as orchestrator_phase_index
                update_request_context(
                    orchestrator_phase_index=idx,  # 0-based index
                    orchestrator_total_phases=len(phases)
                )
            
            # Pass tool_args only to first phase/step
            phase_tool_args = tool_args if idx == 0 else {}
            
            # Create worker-specific strategic plan containing only the current step
            # Workers should not see all orchestrator phases or all manager steps - only their specific task
            # Update request context with worker-specific plan so workers' planners see only their task
            from ..services.request_context import update_request_context
            if is_manager_steps:
                # Manager steps: Create a plan with only the current step
                worker_strategic_plan = {
                    "primary_worker": phase_worker,
                    "task_type": "execution",
                    "phases": [
                        {
                            "name": phase.get("name", f"Step {idx + 1}"),
                            "worker": phase_worker,
                            "goals": phase_task,
                            "notes": phase.get("notes", "")
                        }
                    ],
                    "rationale": f"Executing manager step {idx + 1}/{len(phases)}: {phase.get('name', 'unnamed')}"
                }
                # Update context with worker-specific plan (will be restored after delegation)
                update_request_context(strategic_plan=worker_strategic_plan)
            else:
                # Orchestrator phases: Workers shouldn't receive orchestrator plan
                # Clear strategic_plan from context for workers (they only need the task)
                update_request_context(strategic_plan=None)
                worker_strategic_plan = None
            
            try:
                phase_result = await self._delegate_to_worker_parallel(
                    phase_worker, phase_task, progress_handler, 
                    phase_tool_args,
                    worker_strategic_plan, context  # Pass worker-specific plan, not full orchestrator plan
                )
            finally:
                # Restore original strategic_plan in context after delegation
                # This ensures subsequent steps/workers don't see previous worker's plan
                if is_manager_steps:
                    # Restore manager's local plan (if any)
                    if strategic_plan:
                        update_request_context(strategic_plan=strategic_plan)
                    else:
                        update_request_context(strategic_plan=None)
                else:
                    # Restore orchestrator plan for next phase
                    if strategic_plan:
                        update_request_context(strategic_plan=strategic_plan)
                    else:
                        update_request_context(strategic_plan=None)
            
            workers_run.append(phase_worker)
            results_run.append(phase_result)
            
            result_status = self._result_status(phase_result)
            result_summary = self._summarize_result(phase_result)
            if is_manager_steps:
                step_item = {
                    "name": phase_name,
                    "worker": phase_worker,
                    "tool_name": phase.get("tool_name"),
                }
                end_event = build_segment_event(
                    actor_role="manager",
                    actor_name=self.name,
                    actor_version=self.version,
                    index_key="step_index",
                    total_key="total_steps",
                    item_key="step",
                    index=idx,
                    total=total_segments,
                    item=step_item,
                    result=phase_result,
                    status=result_status,
                    result_summary=result_summary,
                )
                end_event_name = "manager_step_end"
            else:
                phase_item = {
                    "name": phase_name,
                    "worker": phase_worker,
                }
                end_event = build_segment_event(
                    actor_role="manager",
                    actor_name=self.name,
                    actor_version=self.version,
                    index_key="phase_index",
                    total_key="total_phases",
                    item_key="phase",
                    index=idx,
                    total=total_segments,
                    item=phase_item,
                    result=phase_result,
                    status=result_status,
                    result_summary=result_summary,
                )
                end_event_name = "orchestrator_phase_end"
            self.event_bus.publish(end_event_name, end_event)
            if progress_handler:
                await progress_handler.on_event(end_event_name, end_event)

            # Store result for next phase/step
            previous_result = phase_result
            
            # Check for approval request
            if isinstance(phase_result, dict) and phase_result.get("operation") == "await_approval":
                return await self._handle_approval_request(phase_result, progress_handler)
            
            # For sequential phases/steps, continue to next phase (don't stop early)
            # Only stop if we've executed all phases/steps
        
        # Clear phase/step index from context after all phases/steps complete
        from ..services.request_context import update_request_context
        if is_manager_steps:
            update_request_context(manager_step_index=None, manager_total_steps=None)
        else:
            update_request_context(orchestrator_phase_index=None, orchestrator_total_phases=None)
        
        # Aggregate all phase results
        aggregated = self._aggregate_parallel_manager_results(
            [Action(tool_name=w, tool_args={}) for w in workers_run],
            results_run
        )
        
        # Invoke synthesizer agent (if configured) to create detailed summaries for next manager
        if self.synthesizer_agent:
            synthesized_output = await self._invoke_synthesizer_agent(
                task, workers_run, results_run, strategic_plan, context, progress_handler
            )
            if synthesized_output:
                # Store synthesized output in shared memory for next manager access
                # Add phase_id metadata if available for hierarchical filtering
                phase_index = _get_ctx("orchestrator_phase_index")
                synthesis_entry = {
                    "type": SYNTHESIS,
                    "from_manager": self.name,
                    "content": synthesized_output,
                    "timestamp": None  # Will be set by store
                }
                if phase_index is not None:
                    synthesis_entry["phase_id"] = phase_index
                add_global_method = getattr(self.memory, "add_global", None)
                if callable(add_global_method):
                    add_global_method(synthesis_entry)
                synthesizer_final = synthesized_output.get("full_result")
                if isinstance(synthesizer_final, FinalResponse):
                    synthesizer_final = synthesizer_final.model_dump()
                if isinstance(synthesizer_final, dict):
                    return await self._finalize_result(synthesizer_final, progress_handler)
        
        # Optional synthesis (existing gateway-based synthesis for user-facing response)
        final_result = aggregated
        if self.synthesis_gateway:
            synthesized = await self._synthesize_result(task, "sequential", aggregated)
            if synthesized:
                final_result = synthesized
        
        return await self._finalize_result(final_result, progress_handler)

    def _format_previous_result(self, result: Dict[str, Any]) -> str:
        """Format previous phase result for passing to next phase."""
        if not isinstance(result, dict):
            return str(result)
        
        # Extract human-readable summary if available
        summary = result.get("human_readable_summary") or result.get("summary")
        if summary:
            formatted = f"{summary}"
        else:
            formatted = ""
        
        # Include operation and payload info if available
        operation = result.get("operation")
        payload = result.get("payload")
        
        if operation:
            formatted += f"\nOperation: {operation}"
        
        # Include key payload information
        if isinstance(payload, dict):
            # Try to extract meaningful information from payload
            if "message" in payload:
                formatted += f"\nMessage: {payload['message']}"
            elif "data" in payload:
                data = payload["data"]
                if isinstance(data, (list, dict)):
                    import json
                    formatted += f"\nData: {json.dumps(data, indent=2)[:500]}"
                else:
                    formatted += f"\nData: {str(data)[:500]}"
        
        # Fallback: format the whole result if no structured info
        if not formatted.strip():
            import json
            try:
                formatted = json.dumps(result, indent=2)[:1000]
            except Exception:
                formatted = str(result)[:1000]
        
        return formatted.strip()

    def _summarize_result(self, result: Any) -> str:
        if isinstance(result, dict):
            for key in ("human_readable_summary", "summary", "message"):
                value = result.get(key)
                if value:
                    return str(value)[:500]
            payload = result.get("payload")
            if isinstance(payload, dict):
                for key in ("summary", "message"):
                    value = payload.get(key)
                    if value:
                        return str(value)[:500]
            return str(result)[:500]
        return str(result)[:500]

    def _result_status(self, result: Any) -> str:
        if isinstance(result, dict):
            if result.get("operation") == "await_approval":
                return "pending"
            if result.get("error") or result.get("success") is False or result.get("error_message"):
                return "failed"
            payload = result.get("payload")
            if isinstance(payload, dict) and (payload.get("error") or payload.get("success") is False):
                return "failed"
        return "success"

    async def _execute_script_plan(
        self,
        script_steps: List[Dict[str, Any]],
        task: str,
        progress_handler: Optional[BaseProgressHandler],
        script_metadata: Dict[str, Any],
        strategic_plan: Optional[Dict[str, Any]],
        context: Optional[str],
    ) -> Dict[str, Any]:
        """Execute a manager-level script by chunking steps by worker and running sequentially."""
        if not script_steps:
            return await self._create_error_response(
                "Script plan contained no steps to execute",
                progress_handler,
            )

        validation_error = self._validate_script_steps(script_steps)
        if validation_error:
            return await self._create_error_response(validation_error, progress_handler)

        goal = script_metadata.get("goal") or task
        self.memory.add({
            "type": SCRIPT_PLAN,
            "content": {
                "goal": goal,
                "steps": script_steps,
                "metadata": script_metadata,
            },
        })

        script_event_metadata = dict(script_metadata)
        script_event_metadata.setdefault("goal", goal)
        script_event_metadata["total_steps"] = len(script_steps)
        planned_event = build_manager_script_planned_event(
            manager_name=self.name,
            manager_version=self.version,
            script_steps=script_steps,
            script_metadata=script_event_metadata,
        )
        self.event_bus.publish("manager_script_planned", planned_event)
        if progress_handler:
            await progress_handler.on_event("manager_script_planned", planned_event)

        segments = self._group_script_segments(script_steps)
        if not segments:
            return await self._create_error_response(
                "Script plan did not map to any known workers",
                progress_handler,
            )

        workers_run: List[str] = []
        results_run: List[Dict[str, Any]] = []
        aggregate_steps: List[Dict[str, Any]] = []
        overall_status = "SUCCESS"

        for seg_idx, segment in enumerate(segments):
            worker_key = segment.get("worker")
            if not worker_key or worker_key not in self.workers:
                return await self._create_error_response(
                    f"Script step targets unknown worker '{worker_key}'",
                    progress_handler,
                )

            worker = self.workers[worker_key]
            segment_task = segment["steps"][0].get("name") or segment["steps"][0].get("description") or goal
            segment_mode = segment.get("mode") or "direct"
            segment_metadata = {
                **script_metadata,
                "segment_index": seg_idx,
                "total_segments": len(segments),
                "execution_mode": segment_mode,
            }
            segment_args: Dict[str, Any] = {
                "script_metadata": segment_metadata,
                "original_task": segment_task,
            }
            if segment_mode == "guided":
                segment_args["suggested_plan"] = segment["steps"]
            else:
                segment_args["script"] = segment["steps"]

            chunk_result = await self._delegate_to_worker_parallel(
                worker_key,
                segment_task,
                progress_handler,
                segment_args,
                None,
                context,
            )

            if isinstance(chunk_result, dict) and chunk_result.get("operation") == "await_approval":
                return await self._handle_approval_request(chunk_result, progress_handler)

            workers_run.append(worker_key)
            results_run.append(chunk_result)
            aggregate_steps.extend(self._extract_script_step_results(chunk_result, worker_key))

            chunk_status = self._get_script_chunk_status(chunk_result)
            if chunk_status == "FAILED":
                overall_status = "FAILED"
                break

        summary = f"Executed {len(aggregate_steps)} scripted step(s) ({overall_status})"
        aggregated = {
            "operation": "display_message",
            "payload": {
                "message": summary,
                "overall_status": overall_status,
                "script_goal": goal,
                "script_steps": aggregate_steps,
                "worker_results": results_run,
            },
            "human_readable_summary": summary,
        }
        if script_metadata.get("thought"):
            aggregated["payload"]["script_thought"] = script_metadata["thought"]
        if script_metadata.get("notes"):
            aggregated["payload"]["script_notes"] = script_metadata["notes"]

        # Invoke synthesizer agent for downstream managers (if configured)
        if self.synthesizer_agent and workers_run:
            synthesized_output = await self._invoke_synthesizer_agent(
                task,
                workers_run,
                results_run,
                strategic_plan,
                context,
                progress_handler,
            )
            if synthesized_output:
                # Add phase_id metadata if available for hierarchical filtering
                phase_index = _get_ctx("orchestrator_phase_index")
                synthesis_entry = {
                    "type": SYNTHESIS,
                    "from_manager": self.name,
                    "content": synthesized_output,
                    "timestamp": None,
                }
                if phase_index is not None:
                    synthesis_entry["phase_id"] = phase_index
                add_global_method = getattr(self.memory, "add_global", None)
                if callable(add_global_method):
                    add_global_method(synthesis_entry)
                synthesizer_final = synthesized_output.get("full_result")
                if isinstance(synthesizer_final, FinalResponse):
                    synthesizer_final = synthesizer_final.model_dump()
                if isinstance(synthesizer_final, dict):
                    return await self._finalize_result(synthesizer_final, progress_handler)

        final_result = aggregated
        if self.synthesis_gateway:
            synthesized = await self._synthesize_result(task, "script", aggregated)
            if synthesized:
                final_result = synthesized

        return await self._finalize_result(final_result, progress_handler)

    def _group_script_segments(self, script_steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Group consecutive script steps by worker to minimize delegations."""
        segments: List[Dict[str, Any]] = []
        current_worker: Optional[str] = None
        current_mode: str = "direct"
        for step in script_steps:
            if not isinstance(step, dict):
                continue
            worker_key = str(step.get("worker") or step.get("worker_key") or "").strip()
            if not worker_key:
                continue
            mode_hint = step.get("execution_mode") or step.get("mode") or step.get("guided_reasoning")
            normalized_mode = self._normalize_execution_mode(mode_hint) or "direct"
            if segments and worker_key == current_worker and normalized_mode == current_mode:
                segments[-1]["steps"].append(step)
            else:
                segments.append({"worker": worker_key, "mode": normalized_mode, "steps": [step]})
                current_worker = worker_key
                current_mode = normalized_mode
        return segments

    def _normalize_execution_mode(self, value: Any) -> Optional[str]:
        """Normalize execution mode hints into 'direct' or 'guided'."""
        if value is None:
            return None
        if isinstance(value, bool):
            return "guided" if value else "direct"
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"guided", "guided_reasoning", "plan", "guided-mode"}:
                return "guided"
            if lowered in {"direct", "script", "sequential"}:
                return "direct"
        return None

    def _extract_script_step_results(self, worker_result: Any, worker_key: str) -> List[Dict[str, Any]]:
        """Pull normalized script step summaries out of a worker result."""
        if not isinstance(worker_result, dict):
            return []
        payload = worker_result.get("payload", {}) if isinstance(worker_result.get("payload"), dict) else {}
        steps = payload.get("script_steps") or worker_result.get("script_steps")
        if not isinstance(steps, list):
            script_exec = worker_result.get("script_execution")
            if isinstance(script_exec, dict):
                steps = script_exec.get("script_steps") or script_exec.get("steps")
        normalized: List[Dict[str, Any]] = []
        if isinstance(steps, list):
            for entry in steps:
                if not isinstance(entry, dict):
                    continue
                rec = dict(entry)
                rec.setdefault("worker", worker_key)
                normalized.append(rec)
        return normalized

    def _get_script_chunk_status(self, worker_result: Any) -> str:
        """Determine status for a script chunk based on worker result."""
        if isinstance(worker_result, dict):
            payload = worker_result.get("payload", {})
            status = payload.get("overall_status") or worker_result.get("overall_status")
            if isinstance(status, str):
                return status.upper()
        return "SUCCESS"

    def _validate_script_steps(self, script_steps: List[Dict[str, Any]]) -> Optional[str]:
        """Ensure each script step targets a known worker/tool and satisfies required args."""
        for idx, step in enumerate(script_steps, 1):
            if not isinstance(step, dict):
                return f"Script step {idx} is not a valid object"
            worker_key = str(step.get("worker") or step.get("worker_key") or "").strip()
            if not worker_key:
                return f"Script step {idx} is missing a worker"
            worker = self.workers.get(worker_key)
            if not worker:
                return f"Script step {idx} references unknown worker '{worker_key}'"

            execution_mode = str(step.get("execution_mode") or step.get("mode") or "").strip().lower()
            if execution_mode == "guided":
                continue

            tool_name = step.get("tool_name") or step.get("tool")
            if not tool_name:
                return f"Script step {idx} is missing tool_name"

            tools_map = getattr(worker, "tools", None)
            if not isinstance(tools_map, dict) or tool_name not in tools_map:
                return f"Script step {idx} references unknown tool '{tool_name}' for worker '{worker_key}'"

            tool = tools_map[tool_name]
            args = normalize_script_args(tool_name, step.get("args") or {})
            step["args"] = args
            schema = getattr(tool, "args_schema", None)
            if schema:
                try:
                    schema.model_validate(args)
                except ValidationError as ve:
                    return (
                        f"Script step {idx} ({worker_key}.{tool_name}) has invalid args: "
                        f"{ve.errors()[0].get('msg', str(ve)) if hasattr(ve, 'errors') else str(ve)}"
                    )
        return None

    def _extract_phases(self, strategic_plan: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract phases from strategic plan."""
        if not strategic_plan:
            return []
        
        if not isinstance(strategic_plan, dict):
            return []
        
        # Try different plan structures
        # Structure 1: strategic_plan = {"plan": {"phases": [...]}}
        plan_obj = strategic_plan.get("plan")
        if isinstance(plan_obj, dict):
            phases = plan_obj.get("phases")
            if isinstance(phases, list) and len(phases) > 0:
                return phases
        
        # Structure 2: strategic_plan = {"phases": [...]}
        phases = strategic_plan.get("phases")
        if isinstance(phases, list) and len(phases) > 0:
            return phases
        
        # Structure 3: strategic_plan itself is the plan object with phases
        if "phases" in strategic_plan and isinstance(strategic_plan.get("phases"), list):
            phases = strategic_plan.get("phases")
            if phases is not None and len(phases) > 0:
                return phases
        return []

    async def _handle_parallel_delegation(
        self,
        actions: List[Action],
        task: str,
        progress_handler: Optional[BaseProgressHandler],
        strategic_plan: Optional[Dict[str, Any]],
        context: Optional[str],
        policy_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Handle parallel delegation to multiple workers."""
        # Filter to valid Actions targeting known workers
        valid_actions: List[Action] = [
            a for a in actions 
            if isinstance(a, Action) and a.tool_name in self.workers
        ]
        if not valid_actions:
            return await self._create_error_response(
                "Planner returned no valid worker actions",
                progress_handler
            )

        # Ensure strategic context propagated
        if strategic_plan:
            update_request_context(strategic_plan=strategic_plan)
        if context:
            update_request_context(director_context=context)

        # Delegate to multiple workers in parallel
        import asyncio as aio

        async def run_one(action: Action):
            return await self._delegate_to_worker_parallel(
                action.tool_name,
                task,
                progress_handler,
                action.tool_args,
                strategic_plan,
                context,
            )

        results = await aio.gather(*(run_one(a) for a in valid_actions), return_exceptions=False)

        # If any worker requests approval, bubble it up immediately
        for r in results:
            if isinstance(r, dict) and r.get("operation") == "await_approval":
                try:
                    job_id = _get_ctx("JOB_ID") or _get_ctx("job_id")
                    payload = r.get("payload", {}) if isinstance(r.get("payload"), dict) else {}
                    tool = payload.get("tool")
                    args = payload.get("args", {})
                    worker_key = valid_actions[0].tool_name if valid_actions else None
                    if job_id and tool and worker_key and self.job_store:
                        self.job_store.save_pending_action(
                            str(job_id), worker=str(worker_key), tool=str(tool),
                            args=dict(args or {}), manager=str(self.name)
                        )
                except Exception:
                    pass
                return await self._handle_approval_request(r, progress_handler)

        # Aggregate results
        aggregated = self._aggregate_parallel_manager_results(valid_actions, results)

        # Optional synthesis
        final_result = aggregated
        if self.synthesis_gateway:
            try:
                synthesized = await self._synthesize_result(task, "parallel", aggregated)
                if synthesized:
                    final_result = synthesized
            except Exception as e:
                self.logger.warning(f"Synthesis failed: {e}")

        return await self._finalize_result(final_result, progress_handler)

    async def _delegate_to_worker_parallel(
        self,
        worker_key: str,
        task: str,
        progress_handler: Optional[BaseProgressHandler],
        tool_args: Dict[str, Any],
        strategic_plan: Optional[Dict[str, Any]],
        context: Optional[str],
    ) -> Dict[str, Any]:
        """Lightweight delegation used for parallel fan-out without emitting manager_end per worker."""
        # Extract strategic plan from tool_args if present, otherwise use parameter
        worker_strategic_plan = tool_args.get("strategic_plan") if tool_args else None
        worker_context = tool_args.get("original_task") if tool_args else None
        script_steps = tool_args.get("script") if tool_args else None
        if script_steps is not None and not isinstance(script_steps, list):
            script_steps = None
        script_metadata = (tool_args.get("script_metadata") if tool_args else {}) or {}
        suggested_plan = tool_args.get("suggested_plan") if tool_args else None
        if suggested_plan is not None and not isinstance(suggested_plan, list):
            suggested_plan = None

        # Use tool_args strategic_plan if provided, otherwise fall back to parameter
        if worker_strategic_plan:
            strategic_plan = worker_strategic_plan
        # If no strategic_plan in tool_args but we have it as parameter, use parameter
        elif not strategic_plan:
            # strategic_plan parameter already set, no need to override
            pass
        if worker_context:
            context = worker_context or task

        # Log delegation
        delegation_metadata = {
            "has_strategic_plan": worker_strategic_plan is not None,
            "has_script": bool(script_steps),
            "has_guided_plan": bool(suggested_plan),
            "parallel": True,
        }
        planned_event = build_delegation_event(
            manager_name=self.name,
            manager_version=self.version,
            worker_key=worker_key,
            worker_agent_name=getattr(self.workers.get(worker_key), "name", worker_key),
            metadata=delegation_metadata,
        )
        self.event_bus.publish("delegation_planned", planned_event)
        if progress_handler:
            await progress_handler.on_event("delegation_planned", planned_event)

        worker = self.workers.get(worker_key)
        if not worker:
            msg = f"Worker not found: {worker_key}"
            err = {
                "operation": "display_message",
                "payload": {"message": msg, "error": True},
                "human_readable_summary": msg,
            }
            error_event = build_error_event(
                actor_role="manager",
                actor_name=self.name,
                actor_version=self.version,
                message=msg,
            )
            self.event_bus.publish("error", error_event)
            if progress_handler:
                await progress_handler.on_event("error", error_event)
            return err

        worker_agent_name = getattr(worker, "name", worker_key)
        chosen_event = build_delegation_event(
            manager_name=self.name,
            manager_version=self.version,
            worker_key=worker_key,
            worker_agent_name=worker_agent_name,
            metadata={"parallel": True},
        )
        self.event_bus.publish("delegation_chosen", chosen_event)
        if progress_handler:
            await progress_handler.on_event("delegation_chosen", chosen_event)

        # Dispatch based on worker type and script mode
        worker_context_bundle = self._build_worker_execution_context(
            worker_key=worker_key,
            worker_task=task,
            director_context=context,
            script_steps=script_steps,
            script_metadata=script_metadata,
            suggested_plan=suggested_plan,
        )
        if script_steps:
            if isinstance(worker, ManagerAgent):
                return await self._create_error_response(
                    f"Cannot execute script steps with manager worker '{worker_key}'",
                    progress_handler,
                )
            enriched_metadata = dict(script_metadata)
            enriched_metadata.setdefault("goal", script_metadata.get("goal") or task)
            result = await worker.run(
                task=task,
                progress_handler=progress_handler,
                script=script_steps,
                script_metadata=enriched_metadata,
                execution_context=worker_context_bundle,
            )
        elif suggested_plan:
            if isinstance(worker, ManagerAgent):
                return await self._create_error_response(
                    f"Cannot provide suggested plan to manager worker '{worker_key}'",
                    progress_handler,
                )
            result = await worker.run(
                task=task,
                progress_handler=progress_handler,
                suggested_plan=suggested_plan,
                script_metadata=script_metadata,
                execution_context=worker_context_bundle,
            )
        elif isinstance(worker, ManagerAgent):
            result = await worker.run(
                task=task,
                progress_handler=progress_handler,
                strategic_plan=strategic_plan,
                context=context,
            )
        else:
            result = await worker.run(
                task=task,
                progress_handler=progress_handler,
                execution_context=worker_context_bundle,
            )
        if isinstance(result, FinalResponse):
            result = result.model_dump()
        elif not isinstance(result, dict):
            result = {
                "operation": "display_message",
                "payload": {"message": str(result)},
                "human_readable_summary": str(result),
            }

        self.memory.add({"type": DELEGATION, "worker": worker_key, "task": task})
        self.memory.add({"type": OBSERVATION, "content": result})
        
        # Broadcast for parallel/sibling visibility
        try:
            add_global_method = getattr(self.memory, "add_global", None)
            if callable(add_global_method):
                add_global_method({
                    "type": GLOBAL_OBSERVATION,
                    "from_worker": worker_key,
                    "summary": result.get("human_readable_summary") if isinstance(result, dict) else None,
                    "content": result,
                    "parallel": True,
                })
        except Exception:
            pass

        executed_event = build_delegation_event(
            manager_name=self.name,
            manager_version=self.version,
            worker_key=worker_key,
            worker_agent_name=worker_agent_name,
            metadata={"parallel": True},
            result=result,
        )
        self.event_bus.publish("delegation_executed", executed_event)
        if progress_handler:
            await progress_handler.on_event("delegation_executed", executed_event)

        return result

    def _is_orchestrator(self) -> bool:
        try:
            return str(self.name).strip().lower() == "orchestrator"
        except Exception:
            return False

    def _describe_workers(self) -> List[Dict[str, str]]:
        descriptions: List[Dict[str, str]] = []
        for key, worker in self.workers.items():
            desc = getattr(worker, "description", "") or getattr(worker, "name", "")
            descriptions.append({"name": str(key), "description": str(desc)})
        return descriptions

    def _summarize_plan_for_events(self, plan: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Extract lightweight phase summaries from orchestrator or manager plans."""
        if not isinstance(plan, dict):
            return None
        plan_data = plan.get("plan") if isinstance(plan.get("plan"), dict) else plan
        if not isinstance(plan_data, dict):
            return None
        phases = plan_data.get("phases")
        if not isinstance(phases, list):
            return None
        summarized: List[Dict[str, Any]] = []
        for idx, phase in enumerate(phases):
            if not isinstance(phase, dict):
                continue
            summarized.append({
                "index": idx,
                "name": phase.get("name"),
                "worker": phase.get("worker"),
                "goals": phase.get("goals"),
                "notes": phase.get("notes"),
            })
        if not summarized:
            return None
        summary: Dict[str, Any] = {"phases": summarized}
        for key in ("task_type", "rationale", "primary_worker"):
            value = plan_data.get(key)
            if value:
                summary[key] = value
        return summary

    def _describe_manager_tools(self) -> Optional[List[Dict[str, str]]]:
        """Return lightweight metadata for manager tools."""
        if not self.tools:
            return None
        tools_out: List[Dict[str, str]] = []
        for tool in self.tools.values():
            name = getattr(tool, "name", None) or tool.__class__.__name__
            desc = getattr(tool, "description", "") or ""
            tools_out.append({"name": str(name), "description": str(desc)})
        return tools_out or None

    def _inject_context(self, context_text: Optional[str], manifest_text: Optional[str]) -> None:
        if context_text:
            self.memory.add({"type": DIRECTOR_CONTEXT, "content": context_text})
            update_request_context(director_context=context_text)
            update_request_context(context=context_text)
            try:
                snippet = context_text if len(context_text) <= 500 else context_text[:500] + "..."
                self.logger.info("Manager %s loaded director_context (%d chars): %s", self.name, len(context_text), snippet)
            except Exception:
                pass
        if manifest_text:
            update_request_context(data_model_context=manifest_text)
            try:
                length = len(manifest_text)
                snippet = manifest_text if length <= 500 else manifest_text[:500] + "..."
                self.logger.info("Manager %s loaded data_model_context (%d chars) snippet: %s", self.name, length, snippet)
            except Exception:
                pass

    def _ensure_context_builder(self) -> Optional[ContextBuilder]:
        if self._context_builder:
            return self._context_builder
        try:
            job_id = _get_ctx("JOB_ID") or _get_ctx("job_id")
            if job_id:
                self._context_builder = ContextBuilder(str(job_id))
        except Exception:
            return self._context_builder
        return self._context_builder

    def _build_worker_execution_context(
        self,
        worker_key: str,
        worker_task: str,
        director_context: Optional[str],
        script_steps: Optional[List[Dict[str, Any]]] = None,
        script_metadata: Optional[Dict[str, Any]] = None,
        suggested_plan: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Assemble the just-in-time context package passed to worker agents."""
        manager_goal = director_context or worker_task
        if self._context_builder:
            bundle = self._context_builder.build_worker_execution_context(
                manager_goal=manager_goal,
                script_steps=script_steps,
                suggested_plan=suggested_plan,
            )
            bundle.setdefault("worker_key", worker_key)
            bundle.setdefault("script_metadata", script_metadata)
            return bundle

        assembled_context = "\n".join(
            [
                "== Manager Goal ==",
                manager_goal,
                "",
                "== Worker Task ==",
                worker_task,
            ]
        ).strip()
        return {
            "manager_goal": manager_goal,
            "worker_task": worker_task,
            "script_steps": script_steps,
            "script_metadata": script_metadata,
            "suggested_plan": suggested_plan,
            "assembled_context": assembled_context,
            "worker_key": worker_key,
        }

    def _aggregate_parallel_manager_results(
        self,
        actions: List[Action],
        results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Aggregate results from multiple parallel manager delegations."""
        sections: List[Dict[str, Any]] = []
        worker_summaries: List[str] = []
        for action, result in zip(actions, results):
            result_summary = result.get("human_readable_summary") or result.get("summary") or ""
            sections.append({
                "worker": action.tool_name,
                "operation": result.get("operation"),
                "summary": result_summary,
                "result": result,
            })
            # Collect meaningful summaries from worker results (not just delegation status)
            if result_summary:
                worker_summaries.append(result_summary[:200])  # Truncate for summary
        
        # Build summary from actual worker results, not delegation status
        # This provides meaningful context for orchestrator instead of completion-sounding language
        if worker_summaries:
            # Use actual worker summaries - more informative for conversation history
            summary = " | ".join(worker_summaries) if len(worker_summaries) <= 3 else \
                     " | ".join(worker_summaries[:2]) + f" ... and {len(worker_summaries) - 2} more"
        else:
            # Fallback if no summaries available
            summary = f"Executed {len(results)} parallel manager delegations: " + \
                     ", ".join([a.tool_name for a in actions])

        return {
            "operation": "display_message",
            "payload": {
                "message": summary,
                "sections": sections,
            },
            "human_readable_summary": summary,
        }

    async def _finalize_result(
        self,
        result: Dict[str, Any],
        progress_handler: Optional[BaseProgressHandler]
    ) -> Dict[str, Any]:
        """Finalize and return result."""
        end_data = build_manager_end_event(
            manager_name=self.name,
            manager_version=self.version,
            result=result,
        )
        end_data["level"] = "manager"
        self.event_bus.publish("manager_end", end_data)
        if progress_handler:
            await progress_handler.on_event("manager_end", end_data)
        return result

    async def _handle_final_response(
        self,
        final_response: FinalResponse,
        progress_handler: Optional[BaseProgressHandler]
    ) -> Dict[str, Any]:
        """Handle FinalResponse from planner."""
        final_dict = final_response.model_dump()
        self.memory.add({"type": FINAL, "content": final_response.human_readable_summary})
        
        end_data = build_manager_end_event(
            manager_name=self.name,
            manager_version=self.version,
            result=final_dict,
        )
        end_data["level"] = "manager"
        self.event_bus.publish("manager_end", end_data)
        if progress_handler:
            await progress_handler.on_event("manager_end", end_data)
        return final_dict

    async def _create_error_response(
        self,
        message: str,
        progress_handler: Optional[BaseProgressHandler]
    ) -> Dict[str, Any]:
        """Create error response."""
        error_response = {
            "operation": "display_message",
            "payload": {"message": message, "error": True},
            "human_readable_summary": message
        }
        error_event = build_error_event(
            actor_role="manager",
            actor_name=self.name,
            actor_version=self.version,
            message=message,
        )
        self.event_bus.publish("error", error_event)
        if progress_handler:
            await progress_handler.on_event("error", error_event)
        end_data = build_manager_end_event(
            manager_name=self.name,
            manager_version=self.version,
            result=error_response,
            status="error",
            error_message=message,
        )
        end_data["level"] = "manager"
        self.event_bus.publish("manager_end", end_data)
        if progress_handler:
            await progress_handler.on_event("manager_end", end_data)
        return error_response

    async def _handle_approval_request(
        self,
        approval_result: Dict[str, Any],
        progress_handler: Optional[BaseProgressHandler]
    ) -> Dict[str, Any]:
        """Handle approval request from worker."""
        try:
            job_id = _get_ctx("JOB_ID") or _get_ctx("job_id")
            payload = approval_result.get("payload", {}) if isinstance(approval_result.get("payload"), dict) else {}
            tool = payload.get("tool")
            args = payload.get("args", {})
            if job_id and tool and self.job_store:
                self.job_store.save_pending_action(
                    str(job_id), worker="unknown", tool=str(tool),
                    args=dict(args or {}), manager=str(self.name)
                )
        except Exception:
            pass
        
        end_data = build_manager_end_event(
            manager_name=self.name,
            manager_version=self.version,
            result=approval_result,
            status="pending",
        )
        end_data["level"] = "manager"
        self.event_bus.publish("manager_end", end_data)
        if progress_handler:
            await progress_handler.on_event("manager_end", end_data)
        return approval_result

    async def _execute_manager_tool(
        self,
        action: Action,
        progress_handler: Optional[BaseProgressHandler]
    ) -> Dict[str, Any]:
        """Execute a manager tool."""
        tool = self.tools[action.tool_name]
        
        planned_data = build_action_planned_event(
            actor_role="manager",
            actor_name=self.name,
            actor_version=self.version,
            tool_name=action.tool_name,
            args=action.tool_args,
            tool_description=getattr(tool, "description", ""),
            metadata={"manager_tool": True},
        )
        self.event_bus.publish("action_planned", planned_data)
        if progress_handler:
            await progress_handler.on_event("action_planned", planned_data)

        try:
            import asyncio as aio
            import contextvars
            loop = aio.get_event_loop()
            ctx = contextvars.copy_context()
            
            def run_tool():
                return tool.execute(**action.tool_args)
            
            result = await loop.run_in_executor(None, ctx.run, run_tool)
            
            executed_data = build_action_executed_event(
                actor_role="manager",
                actor_name=self.name,
                actor_version=self.version,
                tool_name=tool.name,
                args=action.tool_args,
                result=result,
                tool_label=tool.name,
                metadata={"manager_tool": True},
            )
            self.event_bus.publish("action_executed", executed_data)
            if progress_handler:
                await progress_handler.on_event("action_executed", executed_data)

            final_response = FinalResponse(
                operation="display_message",
                payload={"message": str(result)},
                human_readable_summary=f"Executed {tool.name}, result: {str(result)[:100]}...",
            )
            
            return await self._finalize_result(final_response.model_dump(), progress_handler)

        except Exception as e:
            msg = f"Manager tool {tool.name} failed: {e}"
            return await self._create_error_response(msg, progress_handler)

    async def _synthesize_result(
        self,
        original_task: str,
        worker_key: str,
        worker_result: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Synthesize worker result with manager-level intelligence."""
        if not self.synthesis_gateway:
            return None
        
        import json
        from ..services.request_context import get_from_context
        
        strategic_plan = get_from_context("strategic_plan")
        history = self.memory.get_history()
        user_messages = [
            h.get("content", "") for h in history 
            if h.get("type") == "user_message"
        ]
        original_user_message = user_messages[-1] if user_messages else original_task
        
        result_summary = json.dumps(worker_result, indent=2)[:2000]
        strategic_plan_text = "Not provided"
        if strategic_plan:
            if isinstance(strategic_plan, dict):
                strategic_plan_text = json.dumps(strategic_plan, indent=2)[:500]
            else:
                strategic_plan_text = str(strategic_plan)[:500]
        
        messages = [
            {"role": "system", "content": self.synthesis_prompt},
            {"role": "user", "content": f"""
STRATEGIC CONTEXT:
==================
Original User Question: {original_user_message}

Strategic Plan from Orchestrator:
{strategic_plan_text}

TASK EXECUTION:
===============
Manager Task: {original_task}
Delegated to Worker: {worker_key}

Worker Result:
{result_summary}

SYNTHESIS REQUEST:
==================
Analyze this result in the context of the user's ORIGINAL question and the strategic plan.

Return JSON with "final_response" containing:
{{
  "final_response": {{
    "operation": "display_table|display_message|model_ops",
    "payload": {{ ... reorganized/enhanced data aligned with user intent ... }},
    "human_readable_summary": "Your context-aware synthesis with strategic insights"
  }}
}}
"""}
        ]
        
        response = self.synthesis_gateway.invoke(messages)
        
        try:
            import re
            match = re.search(r'\{[\s\S]*"final_response"[\s\S]*\}', response)
            if match:
                parsed = json.loads(match.group(0))
                if "final_response" in parsed:
                    return parsed["final_response"]
        except Exception:
            pass
        
        return None
    
    async def _invoke_synthesizer_agent(
        self,
        task: str,
        workers_run: List[str],
        results_run: List[Dict[str, Any]],
        strategic_plan: Optional[Dict[str, Any]],
        context: Optional[str],
        progress_handler: Optional[BaseProgressHandler],
    ) -> Optional[Dict[str, Any]]:
        """Invoke synthesizer agent to create detailed summaries for next manager.
        
        This collects all worker agent outputs and uses a separate, more powerful
        synthesizer agent to create detailed, structured summaries that the next
        manager can use for planning.
        """
        if not self.synthesizer_agent:
            return None
        
        try:
            import json
            from ..services.request_context import get_from_context
            builder = self._ensure_context_builder()

            orchestrator_plan = get_from_context("strategic_plan")
            latest_request = builder.latest_user_message() if builder else None

            technical_payload = {
                "manager": self.name,
                "manager_task": task,
                "orchestrator_plan": orchestrator_plan,
                "worker_results": results_run,
            }

            context_text = None
            if builder:
                context_text = builder.build_synthesizer_context(
                    latest_request or task,
                    technical_payload,
                )
            else:
                context_text = json.dumps(technical_payload, indent=2)

            synthesizer_task = f"""You are a synthesis specialist. Combine the technical outcome below into a structured summary for the next agent.

{context_text}

Requirements:
1. Include ALL actual data from worker results (tables, IDs, SQL, DAX, payloads).
2. Produce structured output the next manager can ingest without re-querying data.
3. Highlight actionable follow-ups tied to the user's request.
Return JSON with summary + actual_data fields."""

            self.logger.info(f"Invoking synthesizer agent for {self.name} to create detailed summary for next manager")
            synthesized_result = await self.synthesizer_agent.run(
                task=synthesizer_task,
                progress_handler=progress_handler
            )
            
            if isinstance(synthesized_result, dict):
                summary = synthesized_result.get("human_readable_summary") or synthesized_result.get("summary") or str(synthesized_result)
                payload = synthesized_result.get("payload", {})
                actual_data = payload if payload else synthesized_result
                synthesis_result = {
                    "type": SYNTHESIS,
                    "from_manager": self.name,
                    "synthesized_summary": summary,
                    "actual_data": actual_data,
                    "full_result": synthesized_result,
                    "worker_results": results_run,
                }
                # Add phase_id metadata if available for hierarchical filtering
                phase_index = _get_ctx("orchestrator_phase_index")
                if phase_index is not None:
                    synthesis_result["phase_id"] = phase_index
                return synthesis_result
            
            return None
            
        except Exception as e:
            self.logger.warning(f"Failed to invoke synthesizer agent: {e}")
            return None
