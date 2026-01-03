from __future__ import annotations

from typing import Any, Dict, List, Union, Optional, Tuple
import json
import os
import re
import logging

from ..base import Action, FinalResponse, BasePlanner
from ..base import BaseInferenceGateway
from ..logging import get_logger
import logging
from ..services.request_context import get_from_context
from ..models.script import ScriptPlan
from ..constants import (
    SYNTHESIS,
    USER_MESSAGE,
    ASSISTANT_MESSAGE,
    TASK,
    ACTION,
    FINAL,
    OBSERVATION,
    GLOBAL_OBSERVATION,
)
from ..policies.history_filters import OrchestratorHistoryFilter
from ..policies.base import HistoryFilter
from pydantic import ValidationError


class StaticPlanner(BasePlanner):
    """A deterministic planner for testing the framework mechanics.

    Rules (very simple):

    - If the task contains words like 'search' or 'find', return an Action
      that targets the 'mock_search' tool with the full task as query.
    - Otherwise, return a FinalResponse with a canned message.
    """

    def __init__(self, keywords: List[str] | None = None) -> None:
        self.keywords = ["search", "find"] if keywords is None else [k.lower() for k in keywords]

    def plan(self, task_description: str, history: List[Dict[str, Any]]) -> Union[Action, List[Action], FinalResponse]:
        task_l = task_description.lower()
        if any(k in task_l for k in self.keywords):
            return Action(tool_name="mock_search", tool_args={"query": task_description})
        return FinalResponse(
            operation="display_message",
            payload={"message": "No action needed. Task handled by planner."},
            human_readable_summary="No action needed. Task handled by planner."
        )


class SingleActionPlanner(BasePlanner):
    """Always returns a single configured Action regardless of the task.

    Useful to drive a specific tool via YAML without LLM parsing.
    Sets the configured tool as a terminal tool so the Agent stops after one execution.
    """

    def __init__(self, tool_name: str, tool_args: dict, terminal: bool = True) -> None:
        self._tool = tool_name
        self._args = tool_args or {}
        # Mark this tool as terminal so Agent.run converts its result into a FinalResponse and stops
        self.terminal_tools = [tool_name] if terminal else []

    def plan(self, task_description: str, history: List[Dict[str, Any]]):
        return Action(tool_name=self._tool, tool_args=self._args)


class LLMRouterPlanner(BasePlanner):
    """LLM-backed router that maps a natural-language task to a single tool call.

    Config:
      - inference_gateway: BaseInferenceGateway (resolved via registry/factory)
      - tool_specs: list of { tool: str, args: list[str] } describing allowed tools and their arg names
      - default_model_dir: optional fallback for model_dir when not provided by LLM
      - system_prompt: optional steering text
    Output JSON expected:
      {"tool": "add_relationship", "args": {"model_dir": "/...", ...}}
    """

    def __init__(
        self,
        inference_gateway: BaseInferenceGateway,
        tool_specs: List[Dict[str, Any]],
        default_model_dir: Optional[str] = None,
        system_prompt: Optional[str] = None,
        log_details: Optional[bool] = None,
    ) -> None:
        self.llm = inference_gateway
        self.tool_specs = tool_specs or []
        self.default_model_dir = default_model_dir or os.environ.get("MODEL_DIR")
        self.system_prompt = system_prompt or (
            "You are a router that returns a strict JSON object with fields 'tool' and 'args'."
        )
        env_flag = os.environ.get("AGENT_LOG_ROUTER_DETAILS", "false").lower() in {"1", "true", "yes"}
        self.log_details = log_details if log_details is not None else env_flag
        self.logger = get_logger()

    def plan(self, task_description: str, history: List[Dict[str, Any]]) -> Union[Action, FinalResponse]:
        prompt = self._build_prompt(task_description)
        raw = self.llm.invoke(prompt)
        if self.log_details and self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug("LLMRouterPlanner.prompt=%s", prompt)
            self.logger.debug("LLMRouterPlanner.raw_response=%s", raw)
        data = self._try_parse_json(raw)
        if not data:
            # Fallback to heuristics
            action = self._heuristic_route(task_description)
            if action:
                if self.log_details and self.logger.isEnabledFor(logging.DEBUG):
                    self.logger.debug("LLMRouterPlanner.heuristic_action=%s", action)
                return action
            return FinalResponse(
                operation="display_message",
                payload={"message": "Unable to route request to a known tool.", "error": True},
                human_readable_summary="Unable to route request to a known tool."
            )
        tool = data.get("tool")
        args = data.get("args", {})
        # Ensure model_dir is present if needed
        if "model_dir" in self._expected_args(tool) and not args.get("model_dir"):
            if self.default_model_dir:
                args["model_dir"] = self.default_model_dir
        if self.log_details and self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug("LLMRouterPlanner.parsed_action tool=%s args=%s", tool, args)
        return Action(tool_name=tool, tool_args=args)

    def _build_prompt(self, task: str) -> str:
        specs_str = "\n".join(
            [f"- {spec.get('tool')}: args={spec.get('args', [])}" for spec in self.tool_specs]
        )
        return (
            f"{self.system_prompt}\n"
            f"Allowed tools and their arguments:\n{specs_str}\n"
            f"Return ONLY JSON like {{\"tool\": \"name\", \"args\": {{...}}}}.\n"
            f"User task: {task}\n"
        )

    def _try_parse_json(self, text: str) -> Optional[Dict[str, Any]]:
        # Extract first JSON object
        try:
            m = re.search(r"\{[\s\S]*\}", text)
            if not m:
                return None
            return json.loads(m.group(0))
        except Exception:
            return None

    def _expected_args(self, tool: Optional[str]) -> List[str]:
        for spec in self.tool_specs:
            if spec.get("tool") == tool:
                return spec.get("args", [])
        return []

    def _heuristic_route(self, task: str) -> Optional[Action]:
        t = task.lower()
        # Update by id
        m = re.search(r"(id|rel(ationship)?\s*id)\s*[:=\s]*([a-z0-9]+)", t)
        if "update" in t or "deactivate" in t or "activate" in t or m:
            rel_id = m.group(3) if m else None
            args: Dict[str, Any] = {}
            if self.default_model_dir:
                args["model_dir"] = self.default_model_dir
            if rel_id:
                args["id"] = rel_id
            if "deactivate" in t:
                args["is_active"] = False
            if "activate" in t:
                args["is_active"] = True
            if args:
                return Action(tool_name="update_relationship", tool_args=args)
        # List tables
        if "list" in t and "table" in t:
            args: Dict[str, Any] = {}
            if self.default_model_dir:
                args["model_dir"] = self.default_model_dir
            return Action(tool_name="list_tables", tool_args=args)
        # Add relationship: parse 'Table'[Column] patterns
        pairs = re.findall(r"'([^']+)'\s*\[([^\]]+)\]", task)
        if len(pairs) >= 2:
            (ft, fc), (tt, tc) = pairs[0], pairs[1]
            args = {"from_table": ft, "from_column": fc, "to_table": tt, "to_column": tc}
            if self.default_model_dir:
                args["model_dir"] = self.default_model_dir
            return Action(tool_name="add_relationship", tool_args=args)
        return None


class StrategicPlanner(BasePlanner):
    """Strategic planning layer that creates execution plans and delegates with context.
    
    Unlike WorkerRouterPlanner which just classifies and routes, StrategicPlanner:
    1. Analyzes the task deeply
    2. Creates a multi-step execution plan
    3. Provides rich context to managers
    4. Tracks plan execution across delegations
    
    This enables true hierarchical intelligence where:
    - Director: Strategic thinking & planning
    - Manager: Tactical execution & synthesis
    - Worker: Operational execution
    """
    
    def __init__(
        self,
        worker_keys: List[str],
        inference_gateway: Optional[Any] = None,
        planning_prompt: Optional[str] = None,
        history_filter: Optional[HistoryFilter] = None,
        **kwargs
    ) -> None:
        self.worker_keys = worker_keys or []
        self.llm = inference_gateway
        self.planning_prompt = planning_prompt or self._default_planning_prompt()
        self.history_filter = history_filter or OrchestratorHistoryFilter()
        self.logger = get_logger()
    
    def _parse_script_response(self, response: Union[str, Dict[str, Any], ScriptPlan]) -> Optional[ScriptPlan]:
        if isinstance(response, ScriptPlan):
            return response
        if isinstance(response, dict):
            try:
                return ScriptPlan.model_validate(response)
            except ValidationError:
                try:
                    return ScriptPlan.model_validate_json(json.dumps(response))
                except ValidationError:
                    return None
        text = response if isinstance(response, str) else str(response)
        match = re.search(r"\{[\s\S]*\"script\"[\s\S]*\}", text)
        if not match:
            return None
        json_text = match.group(0)
        try:
            return ScriptPlan.model_validate_json(json_text)
        except ValidationError as ve:
            self.logger.debug("ManagerScriptPlanner: script validation error %s", ve)
            return None

    def _default_planning_prompt(self) -> str:
        return """You are a strategic planner creating execution plans for complex tasks.

Your role:
1. Analyze the user's request deeply
2. Break it into concrete, sequential steps
3. Identify which workers/specialists are needed
4. Provide rich context for each step

Return JSON:
{
  "plan": {
    "steps": [
      {"action": "...", "worker": "...", "context": "..."},
      ...
    ],
    "rationale": "Why this plan will succeed",
    "primary_worker": "worker_key"
  }
}"""
    
    def plan(self, task_description: str, history: List[Dict[str, Any]]) -> Union[Action, FinalResponse]:
        """Create strategic plan and delegate to primary worker with full context."""
        # Build planning prompt with conversation history and optional director/data model context
        workers_list = ", ".join(self.worker_keys)

        messages = [{"role": "system", "content": self.planning_prompt}]

        # Inject contextual blocks if present (director_context and/or data_model_context)
        try:
            from ..services.request_context import get_from_context as _ctx
            director_context = _ctx("director_context") or _ctx("context")
        except Exception:
            director_context = None
        try:
            from ..services.request_context import get_from_context as _ctx2
            data_model_context = _ctx2("data_model_context")
        except Exception:
            data_model_context = None

        context_parts = []
        if director_context:
            context_parts.append(f"DIRECTOR CONTEXT:\n{str(director_context)[:4000]}")
        if data_model_context:
            context_parts.append(f"DATA MODEL CONTEXT:\n{str(data_model_context)[:4000]}")
        if context_parts:
            messages.append({"role": "system", "content": "\n\n".join(context_parts)})
        
        # Filter history using hierarchical filter (orchestrator gets conversation summary only)
        import os as _os
        include_conv = True
        if director_context:
            try:
                include_conv = str(_os.getenv("STRATEGIC_INCLUDE_HISTORY_WITH_DIRECTOR", "false")).lower() in {"1", "true", "yes"}
            except Exception:
                include_conv = False
        
        if include_conv:
            # Use history filter to get appropriate history for orchestrator role
            filter_context = {"role": "orchestrator", "max_conversation_turns": 8}
            filtered_history = self.history_filter.filter_for_prompt(history, filter_context)
            
            # Build messages from filtered conversation history only
            for entry in filtered_history:
                entry_type = entry.get("type")
                if entry_type == USER_MESSAGE:
                    messages.append({"role": "user", "content": entry.get("content", "")})
                elif entry_type == ASSISTANT_MESSAGE:
                    messages.append({"role": "assistant", "content": entry.get("content", "")})
        
        # Add current task
        messages.append({"role": "user", "content": f"""
Task: {task_description}
Available workers: [{workers_list}]

Create a strategic plan to accomplish this task.
Identify the primary worker and provide context for execution.
"""})
        
        # Get strategic plan from LLM
        response = self.llm.invoke(messages)
        
        # Parse plan
        import json
        import re
        try:
            match = re.search(r'\{[\s\S]*"plan"[\s\S]*\}', response)
            if match:
                parsed = json.loads(match.group(0))
                plan_data = parsed.get("plan", {})
                
                # Extract parallel workers (optional) or fall back to primary worker
                parallel_workers = plan_data.get("parallel_workers")
                # Also allow top-level parallel_workers for backward compatibility
                if not parallel_workers:
                    top_level_parallel = parsed.get("parallel_workers")
                    if isinstance(top_level_parallel, list):
                        parallel_workers = top_level_parallel
                if isinstance(parallel_workers, list):
                    # Filter to known workers and ensure uniqueness
                    valid = [w for w in parallel_workers if isinstance(w, str) and w in self.worker_keys]
                    valid = list(dict.fromkeys(valid))  # de-dupe, preserve order
                else:
                    valid = []
                # Primary worker fallback
                primary_worker = plan_data.get("primary_worker", (valid[0] if valid else self.worker_keys[0]))

                # Heuristic override: route modification/validation of Power BI artifacts to powerbi-designer
                try:
                    task_type = str(plan_data.get("task_type", "")).lower()
                    td = (task_description or "").lower()
                    wants_edit = any(k in task_type for k in ("modification", "validate", "validation"))
                    # Edit-intent verbs and BI artifact nouns
                    edit_verbs = [
                        "improve", "optimiz", "fix", "update", "modify", "change", "create", "add",
                        "remove", "rename", "refactor", "rewrite", "validate", "repair", "enhance", "speed"
                    ]
                    bi_nouns = [
                        "dax", "measure", "formula", "relationship", "relationships", "table", "column",
                        "partition", "model", "semantic model", "calculated column", "calculated table"
                    ]
                    inferred_edit = any(v in td for v in edit_verbs) and any(n in td for n in bi_nouns)
                    if (wants_edit or inferred_edit) and ("powerbi-designer" in self.worker_keys):
                        primary_worker = "powerbi-designer"
                except Exception:
                    pass
                
                # Log the strategic plan for visibility
                # Check both "steps" (legacy/default format) and "phases" (orchestrator format)
                steps_or_phases = plan_data.get("steps", []) or plan_data.get("phases", [])
                self.logger.info(
                    "StrategicPlanner created plan: %d phases, primary_worker=%s, rationale=%s",
                    len(steps_or_phases),
                    primary_worker,
                    plan_data.get("rationale", "")[:100]
                )
                
                # Return Actions: parallel (if requested) or single primary
                if valid and len(valid) > 1:
                    actions: List[Action] = []
                    for worker in valid:
                        actions.append(
                            Action(
                                tool_name=worker,
                                tool_args={
                                    "strategic_plan": plan_data,
                                    "original_task": task_description
                                }
                            )
                        )
                    return actions
                else:
                    return Action(
                        tool_name=primary_worker,
                        tool_args={
                            "strategic_plan": plan_data,
                            "original_task": task_description
                        }
                    )
        except Exception as e:
            self.logger.warning(f"Failed to parse strategic plan: {e}, falling back to simple routing")
        
        # Fallback: simple routing
        return Action(tool_name=self.worker_keys[0], tool_args={})


class WorkerRouterPlanner(BasePlanner):
    """Orchestrator-level router that maps a natural-language task to a worker key.

    Behavior:
      - If explicit rules are provided, apply simple heuristic matching first.
      - Else, if an inference gateway is configured, ask the LLM to pick a worker from
        the provided list of worker_keys and return JSON: {"worker": "<key>", "reason": "..."}.
      - If no decision can be made, return a FinalResponse with a graceful fallback message.

    Config:
      - worker_keys: list[str] valid worker identifiers (must match ManagerAgent workers)
      - rules: list[ { worker: str, include: ["keyword"...], exclude: ["keyword"...] } ]
      - inference_gateway: optional BaseInferenceGateway for LLM-based routing
      - default_worker: optional str used when LLM picks invalid or no match
      - system_prompt: optional str steering text for LLM classification
      - log_details: optional bool to emit DEBUG logs
    """

    def __init__(
        self,
        worker_keys: List[str],
        rules: Optional[List[Dict[str, Any]]] = None,
        inference_gateway: Optional[BaseInferenceGateway] = None,
        default_worker: Optional[str] = None,
        system_prompt: Optional[str] = None,
        log_details: Optional[bool] = None,
    ) -> None:
        self.worker_keys = worker_keys or []
        self.rules = rules or []
        self.llm = inference_gateway
        self.default_worker = default_worker
        self.system_prompt = system_prompt or (
            "You are a strict classifier. Choose the best worker key for the task from the provided options and return only JSON {\"worker\": \"<key>\", \"reason\": \"...\"}."
        )
        env_flag = os.environ.get("AGENT_LOG_ROUTER_DETAILS", "false").lower() in {"1", "true", "yes"}
        self.log_details = log_details if log_details is not None else env_flag
        self.logger = get_logger()

        # Optional env-based history controls for router prompts
        self._include_history: bool = os.getenv("AGENT_ROUTER_INCLUDE_HISTORY", "true").lower() in {"1", "true", "yes"}
        try:
            self._max_history: int = int(os.getenv("AGENT_ROUTER_MAX_HISTORY_MESSAGES", "20"))
        except Exception:
            self._max_history = 20

    def plan(self, task_description: str, history: List[Dict[str, Any]]) -> Union[Action, FinalResponse]:
        # 1) Apply heuristic rules first
        worker = self._apply_rules(task_description)
        if worker:
            if self.log_details and self.logger.isEnabledFor(logging.DEBUG):
                self.logger.debug("WorkerRouterPlanner.rules_selected worker=%s", worker)
            return Action(tool_name=worker, tool_args={})

        # 2) Ask LLM to pick a worker
        if self.llm and self.worker_keys:
            prompt = self._build_prompt(task_description, history)
            raw = self.llm.invoke(prompt)
            if self.log_details and self.logger.isEnabledFor(logging.DEBUG):
                self.logger.debug("WorkerRouterPlanner.prompt=%s", prompt)
                self.logger.debug("WorkerRouterPlanner.raw_response=%s", raw)
            worker = self._parse_worker(raw)
            if worker and worker in self.worker_keys:
                return Action(tool_name=worker, tool_args={})
            if self.default_worker and self.default_worker in self.worker_keys:
                return Action(tool_name=self.default_worker, tool_args={})

        # 3) Fallback: graceful final response from orchestrator
        return FinalResponse(
            operation="display_message",
            payload={"message": "I'm not sure which capability should handle this. Could you clarify what you want to do?"},
            human_readable_summary="I'm not sure which capability should handle this. Could you clarify what you want to do?"
        )

    def _apply_rules(self, task: str) -> Optional[str]:
        t = task.lower()
        for rule in self.rules:
            worker = rule.get("worker")
            if not worker:
                continue
            include: List[str] = [s.lower() for s in rule.get("include", [])]
            exclude: List[str] = [s.lower() for s in rule.get("exclude", [])]
            if include and not any(k in t for k in include):
                continue
            if exclude and any(k in t for k in exclude):
                continue
            if self.worker_keys and worker not in self.worker_keys:
                continue
            return worker
        return None

    def _build_prompt(self, task: str, history: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        options = ", ".join(self.worker_keys)
        
        # Include strategic plan/context if available to improve routing
        strategic_plan = get_from_context("strategic_plan")
        director_context = get_from_context("context") or ""
        plan_block = ""
        if strategic_plan:
            try:
                import json as _json
                plan_block = f"\nSTRATEGIC PLAN (from orchestrator/manager):\n{_json.dumps(strategic_plan, indent=2)[:800]}\n"
            except Exception:
                plan_block = f"\nSTRATEGIC PLAN (from orchestrator/manager):\n{str(strategic_plan)[:800]}\n"
        if director_context:
            plan_block += f"\nDIRECTOR CONTEXT: {director_context}\n"

        messages = [
            {"role": "system", "content": f"{self.system_prompt}\n{plan_block}"}
        ]
        
        # Add conversation history for context (optional, capped)
        if self._include_history:
            convo_msgs: List[Dict[str, str]] = []
            for entry in history:
                t = entry.get("type")
                if t == USER_MESSAGE:
                    convo_msgs.append({"role": "user", "content": entry.get("content", "")})
                elif t == ASSISTANT_MESSAGE:
                    convo_msgs.append({"role": "assistant", "content": entry.get("content", "")})
            if self._max_history and self._max_history > 0:
                convo_msgs = convo_msgs[-self._max_history:]
            messages.extend(convo_msgs)
        
        # Add current task
        user_prompt = (
            f"Available workers: [{options}]\n\n"
            f"User task: {task}\n\n"
            f"Which worker should handle this task? Return JSON: {{\"worker\": \"<worker_key>\", \"reason\": \"...\"}}"
        )
        messages.append({"role": "user", "content": user_prompt})
        
        return messages

    def _parse_worker(self, text: str) -> Optional[str]:
        try:
            m = re.search(r"\{[\s\S]*\}", text)
            if not m:
                return None
            obj = json.loads(m.group(0))
            val = obj.get("worker")
            if isinstance(val, str):
                return val
            return None
        except Exception:
            return None


class ChatPlanner(BasePlanner):
    """Conversational planner that generates natural language responses using an LLM.

    This planner is designed for chat-style agents that don't use tools, but instead
    engage in conversation with the user. It builds a message history and asks the
    LLM to generate an assistant response.

    Config:
      - inference_gateway: BaseInferenceGateway (required)
      - system_prompt: optional str defining the assistant's persona
      - max_history_messages: optional int limiting context window (default: 20)
    """

    def __init__(
        self,
        inference_gateway: BaseInferenceGateway,
        system_prompt: Optional[str] = None,
        max_history_messages: Optional[int] = None,
    ) -> None:
        self.llm = inference_gateway
        self.system_prompt = system_prompt or "You are a helpful AI assistant."
        self.max_history = max_history_messages or 20

    def plan(self, task_description: str, history: List[Dict[str, Any]]) -> Union[Action, FinalResponse]:
        # Build message list from history
        messages: List[Dict[str, str]] = [{"role": "system", "content": self.system_prompt}]
        
        # Extract recent conversation turns from memory
        for entry in history[-self.max_history:]:
            entry_type = entry.get("type")
            content = entry.get("content", "")
            # Handle new conversation message types
            if entry_type == USER_MESSAGE:
                messages.append({"role": "user", "content": content})
            elif entry_type == ASSISTANT_MESSAGE:
                messages.append({"role": "assistant", "content": content})
            # Handle legacy message types for backward compatibility
            elif entry_type == TASK:
                messages.append({"role": "user", "content": content})
            elif entry_type == FINAL:
                messages.append({"role": "assistant", "content": content})
        
        # Add current user message
        messages.append({"role": "user", "content": task_description})
        
        # Get LLM response
        response = self.llm.invoke(messages)
        return FinalResponse(
            operation="display_message",
            payload={"message": response},
            human_readable_summary=response
        )


class ReActPlanner(BasePlanner):
    """ReAct (Reasoning + Acting) planner for iterative tool use.

    Implements the ReAct pattern: Thought → Action → Observation loop.
    The planner reasons about the task, selects a tool, observes the result,
    and continues until the task is complete.

    Config:
      - inference_gateway: BaseInferenceGateway (required)
      - tool_descriptions: list[dict] with {name, description, args} for each tool
      - max_iterations: optional int limiting loop iterations (default: 5)
      - system_prompt: optional str defining reasoning style
    """

    def __init__(
        self,
        inference_gateway: BaseInferenceGateway,
        tool_descriptions: List[Dict[str, Any]],
        max_iterations: Optional[int] = None,
        system_prompt: Optional[str] = None,
        terminal_tools: Optional[List[str]] = None,
        use_llm_termination: Optional[bool] = None,
        use_function_calling: Optional[bool] = None,
        max_parallel_tool_calls: Optional[int] = None,
        history_filter: Optional[HistoryFilter] = None,
    ) -> None:
        self.llm = inference_gateway
        self.tool_descriptions = tool_descriptions or []
        # Optional: actual tool objects injected later by factory for introspection
        self._tool_objects: Optional[Dict[str, Any]] = None
        self.max_iterations = max_iterations or 15  # Increased default for parallel execution
        self.system_prompt = system_prompt or (
            "You are an AI agent using the ReAct pattern. "
            "Think step-by-step, choose actions (tools), observe results, and continue until complete. "
            "Return JSON: {\"thought\": \"...\", \"action\": \"tool_name\", \"args\": {...}} or "
            "{\"thought\": \"...\", \"final_answer\": \"...\"}."
        )
        self.logger = get_logger()
        self.terminal_tools = list(terminal_tools or [])
        self.use_llm_termination = use_llm_termination if use_llm_termination is not None else True
        self.use_function_calling = use_function_calling if use_function_calling is not None else False
        # Limit parallel tool calls (function-calling mode)
        self.max_parallel_tool_calls: Optional[int] = max_parallel_tool_calls
        # Store LLM's termination signal from most recent plan() call
        self._last_is_final_step: Optional[bool] = None

        # Env-driven prompt controls (defaults preserve existing behavior)
        def _flag(name: str, default: bool) -> bool:
            val = os.getenv(name)
            if val is None:
                return default
            return str(val).lower() in {"1", "true", "yes"}

        def _int(name: str, default: Optional[int]) -> Optional[int]:
            try:
                val = os.getenv(name)
                if val is None or str(val).strip() == "":
                    return default
                return int(str(val).strip())
            except Exception:
                return default

        # Whether to include any prior history items (conversation turns)
        self._include_history: bool = _flag("AGENT_REACT_INCLUDE_HISTORY", True)
        # Whether to include execution traces (action/observation, global_observation)
        self._include_traces: bool = _flag("AGENT_REACT_INCLUDE_TRACES", True)
        # Whether to include global updates in prompts
        self._include_global_updates: bool = _flag("AGENT_REACT_INCLUDE_GLOBAL_UPDATES", True)
        # Cap the number of history entries appended (None = unlimited)
        self._max_history: Optional[int] = _int("AGENT_REACT_MAX_HISTORY_MESSAGES", None)
        # Truncate observation/global_observation payloads when rendering (applies to text + function-calling)
        self._obs_truncate_len: int = _int("AGENT_REACT_OBS_TRUNCATE_LEN", 1000) or 1000
        # History filter for hierarchical filtering (worker gets current turn only)
        from ..policies.history_filters import WorkerHistoryFilter
        self.history_filter = history_filter or WorkerHistoryFilter()

    def plan(self, task_description: str, history: List[Dict[str, Any]]) -> Union[Action, List[Action], FinalResponse]:
        # Note: max_iterations check moved to Agent.run() for accurate parallel action counting
        # The agent tracks actual iterations, not individual actions
        
        # Function calling mode
        if self.use_function_calling:
            return self._plan_with_function_calling(task_description, history)
        
        # Text-based mode (original)
        return self._plan_with_text_parsing(task_description, history)
    
    def _plan_with_text_parsing(self, task_description: str, history: List[Dict[str, Any]]) -> Union[Action, FinalResponse]:
        """Original text-based ReAct planning with JSON parsing."""
        # Build ReAct prompt with history
        prompt = self._build_react_prompt(task_description, history)
        raw = self.llm.invoke(prompt)
        
        self.logger.debug("ReActPlanner.raw_response=%s", raw)
        
        # Parse LLM response
        # First try to extract JSON from markdown if present
        json_str = self._extract_json_from_markdown(raw)
        decision = self._parse_react_response(json_str)
        
        # Handle JSON parsing errors with feedback to memory for next iteration
        if "_parse_error" in decision:
            error_msg = decision["_parse_error"]
            self.logger.warning(f"JSON parse error detected: {error_msg}")
            
            # Add parse error hint to memory for next iteration
            # This creates a feedback loop: Agent → Error → Hint → Agent tries again
            parse_error_hint = (
                f"⚠️ JSON PARSE ERROR: Your previous response had malformed JSON: {error_msg}\n"
                f"IMPORTANT: When using python_interpreter with complex code:\n"
                f"1. Keep code simple and on fewer lines\n"
                f"2. Avoid nested quotes in JSON\n"
                f"3. Use simpler variable names\n"
                f"4. Or use final_answer to return results directly\n"
                f"Please try again with simpler formatting."
            )
            
            # This will be picked up in the next iteration via memory/history
            # The agent loop will call plan() again with this hint in history
            return FinalResponse(
                operation="display_message",
                payload={
                    "message": parse_error_hint,
                    "error": True,
                    "parse_error": True,
                    "hint": "Retry with simpler code formatting"
                },
                human_readable_summary=f"JSON parse error - need to retry with simpler formatting"
            )
        
        # Check for new structured final_response format
        if "final_response" in decision:
            try:
                final_resp_data = decision["final_response"]
                return FinalResponse(
                    operation=final_resp_data.get("operation", "display_message"),
                    payload=final_resp_data.get("payload", {}),
                    human_readable_summary=final_resp_data.get("human_readable_summary", "Task completed.")
                )
            except Exception as e:
                self.logger.warning(f"Failed to parse final_response: {e}, falling back to legacy format")
        
        # Legacy support: simple final_answer string (or dict, convert if needed)
        if decision.get("final_answer"):
            final_answer = decision["final_answer"]
            
            # If final_answer is a dict/list, convert to readable string
            if isinstance(final_answer, (dict, list)):
                import json
                final_answer = json.dumps(final_answer, indent=2)
            elif not isinstance(final_answer, str):
                final_answer = str(final_answer)
            
            return FinalResponse(
                operation="display_message",
                payload={"message": final_answer},
                human_readable_summary=final_answer
            )
        
        # Capture LLM's termination signal (if provided)
        self._last_is_final_step = decision.get("is_final_step")
        
        tool_name = decision.get("action")
        tool_args = decision.get("args", {})
        # Normalize args: support dicts and positional lists by mapping to expected arg names
        expected = self._expected_args_for_tool(tool_name)
        if tool_args is None:
            tool_args = {}
        if isinstance(tool_args, list):
            mapped: Dict[str, Any] = {}
            for i, val in enumerate(tool_args):
                if i < len(expected):
                    mapped[expected[i]] = val
            tool_args = mapped
        if not isinstance(tool_args, dict):
            tool_args = {}
        # Provide/override MODEL_DIR when expected and value is missing, placeholder, or invalid
        if "model_dir" in expected:
            env_model_dir = os.environ.get("MODEL_DIR")
            md = tool_args.get("model_dir")
            placeholder_vals = {"model_dir", "<model_dir>", "${model_dir}", "${MODEL_DIR}"}
            needs_inject = (
                md is None
                or (isinstance(md, str) and md.strip() in placeholder_vals)
            )
            # If provided but not a directory, prefer env
            if not needs_inject and isinstance(md, str):
                try:
                    import os as _os
                    if not _os.path.isdir(md):
                        needs_inject = True
                except Exception:
                    needs_inject = True
            if needs_inject and env_model_dir:
                tool_args["model_dir"] = env_model_dir
        # Coerce precision to int when provided as string
        if "precision" in expected and isinstance(tool_args.get("precision"), str):
            try:
                tool_args["precision"] = int(tool_args["precision"]) 
            except Exception:
                tool_args.pop("precision", None)
        if tool_name:
            return Action(tool_name=tool_name, tool_args=tool_args)
        
        # Fallback if parsing fails
        return FinalResponse(
            operation="display_message",
            payload={"message": "Unable to determine next action.", "error": True},
            human_readable_summary="Unable to determine next action."
        )

    def _build_react_prompt(self, task: str, history: List[Dict[str, Any]]) -> str:
        # Filter history using hierarchical filter (worker gets current turn only)
        filter_context = {"role": "worker"}
        filtered_history = self.history_filter.filter_for_prompt(history, filter_context)
        
        tools_str = "\n".join([
            f"- {t['name']}: {t.get('description', '')} (args: {t.get('args', [])})"
            for t in self.tool_descriptions
        ])
        
        # Inject strategic plan/context if available
        strategic_plan = get_from_context("strategic_plan")
        director_context = get_from_context("context") or ""
        plan_block = ""
        if strategic_plan:
            try:
                import json as _json
                plan_block = f"\nSTRATEGIC PLAN (from orchestrator/manager):\n{_json.dumps(strategic_plan, indent=2)[:1500]}\n"
            except Exception:
                plan_block = f"\nSTRATEGIC PLAN (from orchestrator/manager):\n{str(strategic_plan)[:1500]}\n"
        if director_context:
            plan_block += f"\nDIRECTOR CONTEXT: {director_context}\n"

        # Build gated history string from filtered history
        history_lines: List[str] = []
        if self._include_history or self._include_traces:
            for entry in filtered_history:
                t = entry.get("type")
                if t in (USER_MESSAGE, ASSISTANT_MESSAGE):
                    if not self._include_history:
                        continue
                    role = "User" if t == USER_MESSAGE else "Assistant"
                    history_lines.append(f"{role}: {entry.get('content', '')}")
                elif t == ACTION:
                    if not self._include_traces:
                        continue
                    history_lines.append(f"Action: {entry.get('tool')} with {entry.get('args')}")
                elif t in (OBSERVATION, GLOBAL_OBSERVATION):
                    if not self._include_traces:
                        continue
                    if t == GLOBAL_OBSERVATION and not self._include_global_updates:
                        continue
                    content = entry.get("content", "")
                    if isinstance(content, dict):
                        try:
                            import json as _json
                            content = _json.dumps(content)
                        except Exception:
                            content = str(content)
                    content_s = str(content)
                    if len(content_s) > self._obs_truncate_len:
                        content_s = content_s[: self._obs_truncate_len] + "... (truncated)"
                    history_lines.append(f"Observation: {content_s}")

        # Apply max history cap (keep tail)
        if isinstance(self._max_history, int) and self._max_history > 0:
            history_lines = history_lines[-self._max_history:]

        history_str = "\n" + "\n".join(history_lines) if history_lines else ""
        
        # Add termination guidance if enabled
        termination_guidance = ""
        if self.use_llm_termination:
            termination_guidance = (
                "\n\nIMPORTANT: Include 'is_final_step' in your JSON response:\n"
                "- Set 'is_final_step': true if this action will COMPLETE the user's request (e.g., pure informational queries like 'list tables')\n"
                "- Set 'is_final_step': false if more steps are needed AFTER this action (e.g., verification before modification)\n"
                "- Omit 'is_final_step' only if uncertain (defaults to legacy terminal_tools behavior)"
            )
        
        return (
            f"{self.system_prompt}\n\n"
            f"{plan_block}"
            f"Available tools:\n{tools_str}\n\n"
            f"Task: {task}\n"
            f"{history_str}\n\n"
            f"What should I do next? (Return JSON with thought/action/args or thought/final_answer)"
            f"{termination_guidance}"
        )

    def _parse_react_response(self, text: str) -> Dict[str, Any]:
        try:
            m = re.search(r"\{[\s\S]*\}", text)
            if not m:
                self.logger.warning("No JSON found in response")
                return {}
            
            json_str = m.group(0)
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON parsing failed: {e}")
            self.logger.debug(f"Failed JSON string: {text[:500]}...")
            # Return error indicator for recovery
            return {"_parse_error": str(e), "_raw_response": text[:1000]}

    def _expected_args_for_tool(self, tool_name: Optional[str]) -> List[str]:
        # Prefer introspection of actual tool args schema when available
        if self._tool_objects and tool_name and tool_name in self._tool_objects:
            tool_obj = self._tool_objects.get(tool_name)
            try:
                schema = tool_obj.args_schema.model_json_schema()  # type: ignore[attr-defined]
                return list((schema.get("properties") or {}).keys())
            except Exception:
                pass
        for desc in self.tool_descriptions:
            if desc.get("name") == tool_name:
                return desc.get("args", [])
        return []
    
    def _extract_json_from_markdown(self, text: str) -> str:
        """Extract JSON from markdown code blocks (```json...``` or ```...```)."""
        if not isinstance(text, str):
            return text
        
        # Try to extract from ```json ... ``` blocks
        json_match = re.search(r'```(?:json)?\s*(\{[\s\S]*?\})\s*```', text, re.DOTALL)
        if json_match:
            return json_match.group(1)
        
        # Try to extract any JSON object from the text
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            return json_match.group(0)
        
        # Return as-is if no JSON found
        return text

    def should_terminate(self, tool_name: str, result: Any, task: str, history: List[Dict[str, Any]]) -> bool:
        """Optional termination hint for Agent: return True to stop after this action.
        
        Note: With the new final_response pattern, the planner returns FinalResponse directly
        when complete, so this method is rarely needed. It exists for legacy terminal_tools
        configuration and explicit LLM is_final_step signals.
        
        Priority order:
        1. LLM's explicit is_final_step signal (text-based mode with use_llm_termination=True)
        2. Fallback to terminal_tools list (legacy behavior)
        """
        # Priority 1: Check if LLM explicitly signaled this is the final step (text-based mode)
        if self.use_llm_termination and self._last_is_final_step is not None:
            should_stop = self._last_is_final_step
            self.logger.debug(
                "ReActPlanner.should_terminate: LLM signaled is_final_step=%s for tool=%s",
                should_stop, tool_name
            )
            # Reset signal after use
            self._last_is_final_step = None
            return should_stop
        
        # Priority 2: Fallback to terminal_tools list (legacy behavior)
        try:
            if tool_name in set(self.terminal_tools or []):
                self.logger.debug(
                    "ReActPlanner.should_terminate: tool=%s in terminal_tools, stopping",
                    tool_name
                )
                return True
        except Exception:
            pass
        
        return False
    
    def _plan_with_function_calling(self, task_description: str, history: List[Dict[str, Any]]) -> Union[Action, List[Action], FinalResponse]:
        """Function calling mode: use OpenAI tools API for structured tool selection.
        
        Supports parallel execution when LLM returns multiple tool_calls.
        """
        # Build conversation messages
        messages = self._build_function_calling_messages(task_description, history)
        
        # Build OpenAI tools schema
        tools_schema = self._build_tools_schema()
        
        # Call LLM with tools
        response = self.llm.invoke(messages, tools=tools_schema)
        
        self.logger.debug("ReActPlanner.function_calling_response=%s", response)
        
        # Handle response
        if isinstance(response, dict):
            # Check for tool calls
            tool_calls = response.get("tool_calls")
            if tool_calls and len(tool_calls) > 0:
                # Log ALL tool calls from LLM (before truncation)
                tool_names_requested = [tc.get("function", {}).get("name", "unknown") for tc in tool_calls]
                self.logger.info(
                    "ReActPlanner: LLM requested %d tool calls: %s",
                    len(tool_calls),
                    tool_names_requested
                )
                
                # Convert ALL tool calls to Actions (enables parallel execution!)
                actions = []
                for tool_call in tool_calls:
                    func = tool_call.get("function", {})
                    tool_name = func.get("name")
                    args_str = func.get("arguments", "{}")
                    
                    try:
                        tool_args = json.loads(args_str)
                    except Exception:
                        tool_args = {}
                    
                    # Apply model_dir injection if needed
                    tool_args = self._inject_model_dir(tool_name, tool_args)
                    
                    actions.append(Action(tool_name=tool_name, tool_args=tool_args))
                
                # Optionally limit number of tool calls (e.g., force single-step)
                original_count = len(actions)
                if isinstance(self.max_parallel_tool_calls, int) and self.max_parallel_tool_calls > 0:
                    if original_count > self.max_parallel_tool_calls:
                        self.logger.warning(
                            "ReActPlanner: LLM requested %d tool calls but max_parallel_tool_calls=%d. "
                            "Truncating to first %d: %s (dropped: %s)",
                            original_count,
                            self.max_parallel_tool_calls,
                            self.max_parallel_tool_calls,
                            [a.tool_name for a in actions[:self.max_parallel_tool_calls]],
                            [a.tool_name for a in actions[self.max_parallel_tool_calls:]]
                        )
                    actions = actions[: self.max_parallel_tool_calls]

                # Return single action or list based on count
                if len(actions) == 1:
                    return actions[0]  # Single action (backward compatible)
                else:
                    self.logger.info(
                        "ReActPlanner: Executing %d parallel tool calls: %s",
                        len(actions),
                        [a.tool_name for a in actions]
                    )
                    return actions  # Parallel execution!
            
            # No tool calls, check for content (final answer)
            content = response.get("content")
            if content:
                # Try to parse as structured final_response if it's JSON
                try:
                    # Extract JSON from markdown code blocks if present
                    json_str = self._extract_json_from_markdown(content)
                    content_data = json.loads(json_str)
                    
                    if isinstance(content_data, dict) and "final_response" in content_data:
                        final_resp = content_data["final_response"]
                        return FinalResponse(
                            operation=final_resp.get("operation", "display_message"),
                            payload=final_resp.get("payload", {}),
                            human_readable_summary=final_resp.get("human_readable_summary", "Task completed.")
                        )
                except Exception as e:
                    self.logger.debug(f"Failed to parse content as final_response JSON: {e}")
                
                # Legacy: simple text response
                return FinalResponse(
                    operation="display_message",
                    payload={"message": content},
                    human_readable_summary=content
                )
        
        # Fallback
        return FinalResponse(
            operation="display_message",
            payload={"message": "Unable to determine next action.", "error": True},
            human_readable_summary="Unable to determine next action."
        )
    
    def _build_function_calling_messages(self, task: str, history: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Build message list for function calling mode."""
        # Filter history using hierarchical filter (worker gets current turn only)
        filter_context = {"role": "worker"}
        filtered_history = self.history_filter.filter_for_prompt(history, filter_context)
        
        # Inject strategic plan/context if available
        strategic_plan = get_from_context("strategic_plan")
        director_context = get_from_context("context") or ""
        plan_block = ""
        if strategic_plan:
            try:
                import json as _json
                plan_block = f"\nSTRATEGIC PLAN (from orchestrator/manager):\n{_json.dumps(strategic_plan, indent=2)[:1500]}\n"
            except Exception:
                plan_block = f"\nSTRATEGIC PLAN (from orchestrator/manager):\n{str(strategic_plan)[:1500]}\n"
        if director_context:
            plan_block += f"\nDIRECTOR CONTEXT: {director_context}\n"

        messages: List[Dict[str, str]] = [
            {"role": "system", "content": f"{self.system_prompt}\n{plan_block}"}
        ]

        # Build gated history messages from filtered history then cap
        history_msgs: List[Dict[str, str]] = []
        if self._include_history or self._include_traces:
            for entry in filtered_history:
                t = entry.get("type")
                if t in (USER_MESSAGE, ASSISTANT_MESSAGE):
                    if not self._include_history:
                        continue
                    role = "user" if t == USER_MESSAGE else "assistant"
                    history_msgs.append({"role": role, "content": entry.get("content", "")})
                elif t == ACTION:
                    if not self._include_traces:
                        continue
                    tool_name = entry.get("tool")
                    args = entry.get("args", {})
                    history_msgs.append({
                        "role": "assistant",
                        "content": f"Calling tool: {tool_name} with args: {json.dumps(args)}"
                    })
                elif t in (OBSERVATION, GLOBAL_OBSERVATION):
                    if not self._include_traces:
                        continue
                    if t == GLOBAL_OBSERVATION and not self._include_global_updates:
                        continue
                    content = entry.get("content", "")
                    if isinstance(content, str):
                        s = content
                    else:
                        try:
                            s = json.dumps(content)
                        except Exception:
                            s = str(content)
                    if len(s) > self._obs_truncate_len:
                        s = s[: self._obs_truncate_len] + "... (truncated)"
                    history_msgs.append({"role": "user", "content": f"Tool result: {s}"})

        if isinstance(self._max_history, int) and self._max_history > 0:
            history_msgs = history_msgs[-self._max_history:]

        messages.extend(history_msgs)
        
        # Only add task as final message if this is the first iteration (no tool results yet)
        # Re-adding task after tool results confuses the LLM into thinking more work is needed
        has_tool_results = any(
            entry.get("type") in (OBSERVATION, GLOBAL_OBSERVATION) 
            for entry in filtered_history
        )
        if not has_tool_results:
            messages.append({"role": "user", "content": task})
        
        return messages
    
    def _build_tools_schema(self) -> List[Dict[str, Any]]:
        """Build OpenAI tools schema.
        
        If actual tool objects are available, derive JSON Schema from their
        Pydantic args_schema (types + required). Otherwise, fall back to the
        config-provided arg names as string-typed required fields.
        """
        tools_schema: List[Dict[str, Any]] = []

        def _prune_properties(props: Dict[str, Any]) -> Dict[str, Any]:
            pruned: Dict[str, Any] = {}
            for key, spec in (props or {}).items():
                if not isinstance(spec, dict):
                    pruned[key] = {"type": "string"}
                    continue
                entry: Dict[str, Any] = {}
                t = spec.get("type")
                if isinstance(t, str):
                    entry["type"] = t
                elif isinstance(t, list):
                    # pick a reasonable type if union
                    entry["type"] = next((x for x in t if isinstance(x, str)), "string")
                else:
                    entry["type"] = "string"
                
                # For array types, preserve the items field (required for OpenAI function calling)
                if entry.get("type") == "array" and "items" in spec:
                    entry["items"] = spec["items"]
                
                if spec.get("description"):
                    entry["description"] = spec.get("description")
                if isinstance(spec.get("enum"), list):
                    entry["enum"] = spec["enum"]
                pruned[key] = entry
            return pruned

        if self._tool_objects:
            for desc in self.tool_descriptions:
                name = desc.get("name")
                description = desc.get("description", "")
                tool_obj = self._tool_objects.get(name)
                if tool_obj and getattr(tool_obj, "args_schema", None):
                    try:
                        schema = tool_obj.args_schema.model_json_schema()  # type: ignore[attr-defined]
                        properties = _prune_properties(schema.get("properties", {}))
                        required = schema.get("required", []) or []
                        tools_schema.append({
                            "type": "function",
                            "function": {
                                "name": name,
                                "description": description,
                                "parameters": {
                                    "type": "object",
                                    "properties": properties,
                                    "required": required,
                                },
                            },
                        })
                        continue
                    except Exception:
                        pass

        # Fallback to config-only schema (string-typed)
        for desc in self.tool_descriptions:
            name = desc.get("name")
            description = desc.get("description", "")
            args = desc.get("args", []) or []
            properties = {a: {"type": "string", "description": f"Parameter: {a}"} for a in args}
            tools_schema.append({
                "type": "function",
                "function": {
                    "name": name,
                    "description": description,
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        "required": args,
                    },
                },
            })

        return tools_schema

    # Public hook for factory to inject tool objects
    def configure_tools(self, tools: Dict[str, Any]) -> None:
        try:
            if isinstance(tools, dict):
                self._tool_objects = dict(tools)
            else:
                # Accept list-like input as well
                self._tool_objects = {getattr(t, "name", f"tool{i}"): t for i, t in enumerate(tools)}  # type: ignore
        except Exception:
            self._tool_objects = None
    
    def _inject_model_dir(self, tool_name: Optional[str], tool_args: Dict[str, Any]) -> Dict[str, Any]:
        """Inject MODEL_DIR environment variable if needed.
        
        Matches the validation logic from text-based mode (lines 396-414).
        """
        expected = self._expected_args_for_tool(tool_name)
        if "model_dir" in expected:
            env_model_dir = os.environ.get("MODEL_DIR")
            md = tool_args.get("model_dir")
            placeholder_vals = {"model_dir", "<model_dir>", "${model_dir}", "${MODEL_DIR}"}
            
            needs_inject = (
                md is None
                or (isinstance(md, str) and md.strip() in placeholder_vals)
            )
            
            # Validate directory existence (same as text-based mode)
            if not needs_inject and isinstance(md, str):
                try:
                    import os as _os
                    if not _os.path.isdir(md):
                        needs_inject = True
                        self.logger.debug(
                            "ReActPlanner._inject_model_dir: '%s' is not a valid directory, using env MODEL_DIR",
                            md
                        )
                except Exception:
                    needs_inject = True
            
            if needs_inject and env_model_dir:
                tool_args["model_dir"] = env_model_dir
                self.logger.debug(
                    "ReActPlanner._inject_model_dir: Injected MODEL_DIR='%s' for tool=%s",
                    env_model_dir, tool_name
                )
        
        return tool_args


class MathPlanner(BasePlanner):
    """Heuristic planner for math Q&A and calculations.

    Routes tasks to either the 'calculator' tool (arithmetic/numeric queries)
    or the 'math_qa' tool (conceptual math questions and formulas).
    """

    def __init__(self) -> None:
        from ..logging import get_logger
        self.logger = get_logger()

    def plan(self, task_description: str, history: List[Dict[str, Any]]) -> Union[Action, FinalResponse]:
        t = (task_description or "").strip().lower()
        is_calc = self._looks_like_calculation(t)
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(f"MathPlanner decision is_calc={is_calc} task='{task_description}'")
        if is_calc:
            return Action(tool_name="calculator", tool_args={"expression": task_description})
        return Action(tool_name="math_qa", tool_args={"question": task_description})

    def _looks_like_calculation(self, t: str) -> bool:
        if not t:
            return False
        # Contains digits with math operators or caret/power words
        if any(op in t for op in ["+", "-", "*", "×", "x", "/", "÷", "%", "^"]):
            if any(ch.isdigit() for ch in t):
                return True
        keywords = [
            "plus", "minus", "times", "multiplied by", "divided by", "over", "mod", "modulo",
            "remainder", "percent of", "% of", "power of", "raised to", "squared", "cubed",
            "sqrt", "square root", "log", "ln", "sin", "cos", "tan", "calculate", "compute", "evaluate",
        ]
        if any(k in t for k in keywords):
            return True
        # Numbers present with query verbs often imply calc
        if re.search(r"\b\d+(?:[\.\d]*)?\b", t):
            if any(k in t for k in ["calculate", "compute", "evaluate", "what is", "what's", "solve"]):
                return True
        return False


class StrategicDecomposerPlanner(BasePlanner):
    """Hybrid planner that can create steps or decompose orchestrator phases into
    worker-specific steps for a domain manager (e.g., PBI Manager).

    Behavior:
    - Reads a strategic plan from request context (set by an upstream orchestrator)
    - If inference_gateway is provided: Uses LLM to create steps based on orchestrator phase + previous manager outputs
    - Otherwise: Maps high-level phases to local workers using simple heuristics (decomposition)
    - Returns an Action targeting the primary local worker with the plan containing steps

    Config:
      - worker_keys: list[str] of local workers (e.g., ["schema", "dax", "validator"])
      - default_worker: optional fallback (default: first worker)
      - inference_gateway: optional BaseInferenceGateway for LLM-based step creation
      - planning_prompt: optional str custom prompt for step creation
      - manager_worker_key: optional str to identify which orchestrator phase is for this manager
    """

    def __init__(
        self,
        worker_keys: List[str],
        default_worker: Optional[str] = None,
        inference_gateway: Optional[Any] = None,
        planning_prompt: Optional[str] = None,
        manager_worker_key: Optional[str] = None,
        history_filter: Optional[HistoryFilter] = None,
    ) -> None:
        self.worker_keys = worker_keys or []
        self.default_worker = default_worker or (self.worker_keys[0] if self.worker_keys else "")
        self.llm = inference_gateway
        self.planning_prompt = planning_prompt or self._default_planning_prompt()
        self.manager_worker_key = manager_worker_key  # e.g., "powerbi-analysis", "powerbi-designer"
        from ..policies.history_filters import ManagerHistoryFilter
        self.history_filter = history_filter or ManagerHistoryFilter()
        self.logger = get_logger()
    
    def _default_planning_prompt(self) -> str:
        return """You are a manager planner creating execution steps for a domain-specific task.

Your role:
1. Analyze the orchestrator phase input and any previous manager outputs
2. Break the task into concrete, sequential steps for your domain workers
3. Identify which local workers/specialists are needed for each step
4. Ensure steps build on previous outputs when available

Available workers: {worker_keys}

Return JSON:
{{
  "phases": [
    {{"name": "<step name>", "worker": "<worker_key>", "goals": "<what to achieve>", "notes": "<key context>"}},
    ...
  ],
  "primary_worker": "<worker_key>",
  "rationale": "Why this step plan will succeed"
}}"""

    def plan(self, task_description: str, history: List[Dict[str, Any]]) -> Union[Action, FinalResponse]:
        # Pull upstream strategic plan from context or history
        upstream = get_from_context("strategic_plan")
        if not upstream:
            # Try to locate in history (manager added it earlier)
            try:
                upstream = next((h.get("content") for h in reversed(history) if h.get("type") == "strategic_plan"), None)
            except Exception:
                upstream = None

        # Debug logging
        # Normalize plan data
        plan_obj: Dict[str, Any] = {}
        if isinstance(upstream, dict):
            plan_obj = upstream.get("plan") or upstream
        else:
            plan_obj = {}

        phases_in = []
        if isinstance(plan_obj, dict):
            phases_in = plan_obj.get("phases") or []
        
        # Log when no phases found (this is the issue reported)
        if not phases_in:
            has_context = upstream is not None
            has_history = any(h.get("type") == "strategic_plan" for h in history)
            self.logger.debug(
                "StrategicDecomposerPlanner: No orchestrator phase found (manager_worker_key=%s, phases_in=%d), using decomposition. upstream_from_context=%s, upstream_from_history=%s",
                self.manager_worker_key,
                len(phases_in),
                has_context,
                has_history
            )
            if upstream:
                try:
                    import json as _json
                    upstream_preview = _json.dumps(upstream, indent=2)[:300] if isinstance(upstream, dict) else str(upstream)[:300]
                    self.logger.debug("StrategicDecomposerPlanner: upstream structure preview=%s", upstream_preview)
                except Exception:
                    pass

        # Extract orchestrator phase assigned to this manager
        orchestrator_phase = None
        if self.manager_worker_key and phases_in:
            # Find phase(s) where worker matches this manager's worker key
            matching_phases = [p for p in phases_in if str(p.get("worker", "")).strip() == self.manager_worker_key]
            if matching_phases:
                # Use phase index from request context to select the correct phase
                phase_index = get_from_context("orchestrator_phase_index")
                if phase_index is not None and isinstance(phase_index, int) and 0 <= phase_index < len(matching_phases):
                    orchestrator_phase = matching_phases[phase_index]
                    self.logger.debug(
                        "StrategicDecomposerPlanner: Using phase index %d/%d for manager_worker_key=%s, phase='%s'",
                        phase_index + 1,
                        len(matching_phases),
                        self.manager_worker_key,
                        orchestrator_phase.get("name", "unnamed")
                    )
                else:
                    # Fallback: use first matching phase if index not available or invalid
                    orchestrator_phase = matching_phases[0]
                    if phase_index is not None:
                        self.logger.warning(
                            "StrategicDecomposerPlanner: Invalid phase_index=%s (expected 0-%d), using first phase",
                            phase_index,
                            len(matching_phases) - 1
                        )
                
                # Combine task_description with orchestrator phase info
                if orchestrator_phase.get("goals"):
                    task_description = orchestrator_phase.get("goals", task_description)

        # Filter history using hierarchical filter (manager gets phase-relevant context only)
        phase_index = get_from_context("orchestrator_phase_index")
        filter_context = {
            "role": "manager",
            "phase_id": phase_index,
            "previous_phase_id": phase_index - 1 if phase_index is not None and phase_index > 0 else None,
        }
        filtered_history = self.history_filter.filter_for_prompt(history, filter_context)
        
        # Extract previous manager outputs from filtered history
        # Priority: synthesized outputs from synthesizer agent > regular manager outputs
        previous_outputs = []
        synthesized_outputs = []
        
        for entry in reversed(filtered_history):
            if not isinstance(entry, dict):
                continue
                
            entry_type = entry.get("type", "")
            
            # Look for synthesized outputs first (from synthesizer agent)
            # These are stored as global updates with type="synthesis"
            if entry_type == SYNTHESIS:
                content = entry.get("content", {})
                if isinstance(content, dict):
                    # Build comprehensive output including both summary and actual data
                    output_parts = []
                    
                    # Add synthesized summary
                    synthesized_summary = content.get("synthesized_summary")
                    if not synthesized_summary:
                        # Try to get from full_result
                        full_result = content.get("full_result", {})
                        if isinstance(full_result, dict):
                            synthesized_summary = full_result.get("human_readable_summary") or full_result.get("summary")
                    
                    if synthesized_summary:
                        output_parts.append(f"Summary: {synthesized_summary}")
                    
                    # Add actual data (structured data for planning)
                    actual_data = content.get("actual_data") or content.get("payload")
                    if actual_data:
                        import json
                        try:
                            data_str = json.dumps(actual_data, indent=2) if isinstance(actual_data, dict) else str(actual_data)
                            output_parts.append(f"Actual Data:\n{data_str}")
                        except Exception:
                            output_parts.append(f"Actual Data: {str(actual_data)}")
                    
                    # Add worker results for context
                    worker_results = content.get("worker_results", [])
                    if worker_results:
                        import json
                        try:
                            results_str = json.dumps(worker_results, indent=2)
                            output_parts.append(f"Worker Results:\n{results_str}")
                        except Exception:
                            pass
                    
                    if output_parts:
                        synthesized_outputs.append("\n\n".join(output_parts))
                elif isinstance(content, str):
                    synthesized_outputs.append(content)
            
            # Also collect regular manager outputs as fallback
            if entry_type in [FINAL, ASSISTANT_MESSAGE, "manager_result"]:
                content = entry.get("content", {})
                if isinstance(content, dict):
                    summary = content.get("human_readable_summary") or content.get("summary", "")
                    if summary:
                        previous_outputs.append(str(summary))
                elif isinstance(content, str):
                    previous_outputs.append(content)
            
            # Limit to avoid token overflow (prioritize synthesized)
            if synthesized_outputs:
                if len(synthesized_outputs) >= 2:
                    break
            else:
                if len(previous_outputs) >= 3:
                    break
        
        # Prefer synthesized outputs, fall back to regular outputs
        final_previous_outputs = synthesized_outputs if synthesized_outputs else previous_outputs

        # If LLM is available and we have orchestrator phase, create steps using LLM
        # Reuse StrategicPlanner's pattern but with manager-specific context
        if self.llm and orchestrator_phase:
            self.logger.info(
                "StrategicDecomposerPlanner using LLM to create steps: manager_worker_key=%s, orchestrator_phase=%s, has_synthesized_outputs=%s",
                self.manager_worker_key,
                orchestrator_phase.get("name", "unnamed"),
                len(synthesized_outputs) > 0
            )
            llm_result = self._create_steps_with_llm(
                task_description, orchestrator_phase, final_previous_outputs, plan_obj, history
            )
            if llm_result:
                return llm_result
            # If LLM creation failed, fall through to decomposition
            self.logger.warning("LLM step creation failed, falling back to decomposition")
        elif not self.llm:
            self.logger.debug("StrategicDecomposerPlanner: No LLM configured, using decomposition")
        elif not orchestrator_phase:
            self.logger.debug(
                "StrategicDecomposerPlanner: No orchestrator phase found (manager_worker_key=%s, phases_in=%d), using decomposition",
                self.manager_worker_key,
                len(phases_in)
            )

        # Fallback: Decompose orchestrator phases using heuristics (original behavior)
        phases_out: List[Dict[str, Any]] = []
        def _pick_worker(name: str, goals: str, notes: str) -> str:
            text = f"{name} {goals} {notes}".lower()
            if any(k in text for k in ["validate", "lint", "integrity", "consistency"]):
                return "validator" if "validator" in self.worker_keys else self.default_worker
            if any(k in text for k in ["dax", "measure", "measures", "calculation", "kpi"]):
                return "dax" if "dax" in self.worker_keys else self.default_worker
            # Default for schema-related analysis/editing
            return "schema" if "schema" in self.worker_keys else self.default_worker

        for ph in phases_in:
            name = str((ph or {}).get("name", "Phase")).strip()
            goals = str((ph or {}).get("goals", "")).strip()
            notes = str((ph or {}).get("notes", "")).strip()
            worker = (ph or {}).get("worker")
            if worker not in self.worker_keys:
                worker = _pick_worker(name, goals, notes)
            phases_out.append({
                "name": name,
                "worker": worker,
                "goals": goals,
                "notes": notes,
            })

        if not phases_out:
            # Fallback: single schema phase
            primary = self.default_worker or (self.worker_keys[0] if self.worker_keys else "")
            phases_out = [{
                "name": "Execute Task",
                "worker": primary or "schema",
                "goals": task_description,
                "notes": "Generated by StrategicDecomposerPlanner (no upstream plan found)",
            }]

        primary_worker = phases_out[0].get("worker") or self.default_worker
        if primary_worker not in self.worker_keys and self.worker_keys:
            primary_worker = self.worker_keys[0]

        # Compose a local plan object for downstream workers
        local_plan = {
            "primary_worker": primary_worker,
            "task_type": (plan_obj.get("task_type") if isinstance(plan_obj, dict) else "analysis") or "analysis",
            "phases": phases_out,
            "rationale": (plan_obj.get("rationale") if isinstance(plan_obj, dict) else "") or "Decomposed upstream plan for domain execution.",
        }

        # Log and return as Action to the primary worker; manager will run follow-ups
        try:
            if self.logger.isEnabledFor(logging.DEBUG):
                import json as _json
                self.logger.debug("StrategicDecomposerPlanner.local_plan=%s", _json.dumps(local_plan, indent=2)[:800])
        except Exception:
            pass

        return Action(
            tool_name=str(primary_worker),
            tool_args={
                "strategic_plan": local_plan,
                "original_task": task_description,
            },
        )
    
    def _create_steps_with_llm(
        self,
        task_description: str,
        orchestrator_phase: Dict[str, Any],
        previous_outputs: List[str],
        plan_obj: Dict[str, Any],
        history: List[Dict[str, Any]],
    ) -> Optional[Action]:
        """Create steps using LLM - reuses StrategicPlanner's pattern with manager-specific context."""
        workers_list = ", ".join(self.worker_keys)
        
        self.logger.info(
            "StrategicDecomposerPlanner._create_steps_with_llm: Invoking LLM with orchestrator_phase=%s, previous_outputs=%d",
            orchestrator_phase.get("name", "unnamed"),
            len(previous_outputs)
        )
        
        # Replace {worker_keys} placeholder (use replace to avoid KeyError with JSON braces in prompt)
        prompt = self.planning_prompt.replace("{worker_keys}", workers_list)
        messages = [{"role": "system", "content": prompt}]
        
        # Build context similar to StrategicPlanner but with manager-specific info
        context_parts = []
        
        # Add orchestrator phase context (manager-specific)
        phase_name = orchestrator_phase.get("name", "")
        phase_goals = orchestrator_phase.get("goals", task_description)
        phase_notes = orchestrator_phase.get("notes", "")
        context_parts.append(f"ORCHESTRATOR PHASE:\nName: {phase_name}\nGoals: {phase_goals}")
        if phase_notes:
            context_parts.append(f"Notes: {phase_notes}")
        
        # Add previous manager outputs (manager-specific) - include actual data
        if previous_outputs:
            context_parts.append("\nPREVIOUS MANAGER OUTPUTS (INCLUDES ACTUAL DATA):")
            context_parts.append("IMPORTANT: The following outputs contain ACTUAL DATA from previous manager analysis.")
            context_parts.append("Use this data directly in your step planning - do not assume data needs to be re-queried.")
            for idx, output in enumerate(reversed(previous_outputs), 1):
                # Include full output (may contain actual data) - don't truncate too much
                context_parts.append(f"\nPrevious Manager Output {idx}:\n{str(output)[:5000]}")
        
        # Add data model context (same as StrategicPlanner)
        try:
            from ..services.request_context import get_from_context as _ctx
            data_model_context = _ctx("data_model_context")
            if data_model_context:
                context_parts.append(f"\nDATA MODEL CONTEXT:\n{str(data_model_context)[:2000]}")
        except Exception:
            pass
        
        if context_parts:
            messages.append({"role": "system", "content": "\n\n".join(context_parts)})
        
        # Add task (same pattern as StrategicPlanner)
        messages.append({
            "role": "user",
            "content": f"""
Task: {task_description}
Available workers: [{workers_list}]

Create a step-by-step plan to accomplish this task using your domain workers.

IMPORTANT: Previous manager outputs above include ACTUAL DATA (tables, columns, SQL queries, DAX expressions, etc.).
- Use this actual data directly in your step planning
- Reference specific data values in your step goals (e.g., "Use the SQL query from previous output")
- Do not plan steps that re-query data that's already provided
- Build steps that work with the actual data provided

Ensure steps build on previous outputs when available.
Return JSON with phases array (use "phases" not "steps").
""",
        })
        
        # Reuse StrategicPlanner's LLM invocation and parsing pattern
        response = self.llm.invoke(messages)
        
        # Parse using same pattern as StrategicPlanner
        import json
        import re
        try:
            # Look for "phases" instead of "plan" for manager steps
            match = re.search(r'\{[\s\S]*"phases"[\s\S]*\}', response)
            if not match:
                # Fallback: try to find any JSON with plan
                match = re.search(r'\{[\s\S]*"plan"[\s\S]*\}', response)
            
            if match:
                parsed = json.loads(match.group(0))
                # Support both "phases" (manager format) and "plan.phases" (orchestrator format)
                plan_data = parsed.get("plan", {}) if "plan" in parsed and "phases" not in parsed else parsed
                phases_out = plan_data.get("phases", []) or plan_data.get("steps", [])
                
                if phases_out and isinstance(phases_out, list):
                    # Validate and correct workers (same as StrategicPlanner)
                    for ph in phases_out:
                        worker = ph.get("worker", "")
                        if worker and worker not in self.worker_keys:
                            ph["worker"] = self._pick_worker(
                                ph.get("name", ""),
                                ph.get("goals", ""),
                                ph.get("notes", "")
                            )
                    
                    primary_worker = plan_data.get("primary_worker") or (phases_out[0].get("worker") if phases_out else self.default_worker)
                    if primary_worker not in self.worker_keys:
                        primary_worker = self.default_worker
                    
                    local_plan = {
                        "primary_worker": primary_worker,
                        "task_type": plan_obj.get("task_type", "analysis") if isinstance(plan_obj, dict) else "analysis",
                        "phases": phases_out,
                        "rationale": plan_data.get("rationale", "Created steps based on orchestrator phase input and previous outputs."),
                    }
                    
                    self.logger.info(
                        "StrategicDecomposerPlanner created %d steps via LLM, primary_worker=%s",
                        len(phases_out),
                        primary_worker
                    )
                    
                    return Action(
                        tool_name=str(primary_worker),
                        tool_args={
                            "strategic_plan": local_plan,
                            "original_task": task_description,
                        },
                    )
        except Exception as e:
            self.logger.warning(f"Failed to parse step plan: {e}, falling back to decomposition")
        
        # Fallback: return single step (will be handled by decomposition logic below)
        return None
    
    def _pick_worker(self, name: str, goals: str, notes: str) -> str:
        """Pick worker based on heuristics."""
        text = f"{name} {goals} {notes}".lower()
        if any(k in text for k in ["validate", "lint", "integrity", "consistency"]):
            return "validator" if "validator" in self.worker_keys else self.default_worker
        if any(k in text for k in ["dax", "measure", "measures", "calculation", "kpi"]):
            return "dax" if "dax" in self.worker_keys else self.default_worker
        return "schema" if "schema" in self.worker_keys else self.default_worker


class ManagerScriptPlanner(BasePlanner):
    """LLM-backed planner that creates explicit tool-call scripts for managers.

    The manager remains the planner while workers become deterministic executors.
    This planner inspects the director goal (orchestrator phase) plus previous
    manager outputs and returns a JSON script describing the exact worker/tool
    calls required to accomplish the goal.
    """

    def __init__(
        self,
        worker_specs: List[Dict[str, Any]],
        default_worker: Optional[str] = None,
        inference_gateway: Optional[Any] = None,
        planning_prompt: Optional[str] = None,
        manager_worker_key: Optional[str] = None,
    ) -> None:
        self.worker_specs = self._normalize_worker_specs(worker_specs)
        self.worker_keys = [spec["worker"] for spec in self.worker_specs if spec.get("worker")]
        self.default_worker = default_worker or (self.worker_keys[0] if self.worker_keys else "")
        self.llm = inference_gateway
        self.planning_prompt = planning_prompt or self._default_planning_prompt()
        self.manager_worker_key = manager_worker_key
        self.logger = get_logger()
        self.fallback = StrategicDecomposerPlanner(
            worker_keys=self.worker_keys,
            default_worker=self.default_worker,
            inference_gateway=inference_gateway,
            manager_worker_key=manager_worker_key,
        )

    def _parse_script_response(self, response: Union[str, Dict[str, Any], ScriptPlan]) -> Optional[ScriptPlan]:
        if isinstance(response, ScriptPlan):
            return response
        if isinstance(response, dict):
            try:
                return ScriptPlan.model_validate(response)
            except ValidationError:
                try:
                    return ScriptPlan.model_validate_json(json.dumps(response))
                except ValidationError:
                    return None
        text = response if isinstance(response, str) else str(response)
        match = re.search(r"\{[\s\S]*\"script\"[\s\S]*\}", text)
        if not match:
            return None
        try:
            return ScriptPlan.model_validate_json(match.group(0))
        except ValidationError as ve:
            self.logger.debug("ManagerScriptPlanner: script validation error %s", ve)
            return None

    def _normalize_worker_specs(self, specs: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        normalized: List[Dict[str, Any]] = []
        if not specs:
            return normalized
        for spec in specs:
            if not isinstance(spec, dict):
                continue
            worker = spec.get("worker") or spec.get("name")
            if not worker:
                continue
            normalized.append({
                "worker": worker,
                "description": spec.get("description", ""),
                "tools": spec.get("tools", []),
            })
        return normalized

    def plan(self, task_description: str, history: List[Dict[str, Any]]) -> Union[Action, FinalResponse]:
        if not self.llm:
            self.logger.warning("ManagerScriptPlanner has no inference gateway, falling back to StrategicDecomposer")
            return self.fallback.plan(task_description, history)

        orchestrator_phase, goal_text = self._select_orchestrator_phase(task_description, history)
        previous_outputs = self._collect_previous_outputs(history)

        worker_catalog = self._build_worker_catalog()
        prompt = self.planning_prompt.replace("{worker_catalog}", worker_catalog)

        context_sections = [f"Director Goal: {goal_text}"]
        if orchestrator_phase:
            phase_name = orchestrator_phase.get("name")
            phase_notes = orchestrator_phase.get("notes")
            if phase_name:
                context_sections.append(f"Phase Name: {phase_name}")
            if phase_notes:
                context_sections.append(f"Director Notes: {phase_notes}")
        if previous_outputs:
            context_sections.append("Previous Manager Outputs (actual data):")
            for idx, output in enumerate(previous_outputs, 1):
                context_sections.append(f"Output {idx}:\n{output}")

        messages = [
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": "\n\n".join(context_sections) + "\n\nReturn strict JSON with fields 'thought' and 'script'.",
            },
        ]

        self.logger.info("ManagerScriptPlanner invoking LLM for script generation (worker_key=%s)", self.manager_worker_key)
        response = self.llm.invoke(messages)
        plan_model = self._parse_script_response(response)
        if not plan_model:
            self.logger.warning("ManagerScriptPlanner: unable to parse script response, falling back")
            return self.fallback.plan(task_description, history)

        script_steps = [step.model_dump() for step in plan_model.script]
        script_steps = self._normalize_script_workers(script_steps)
        primary_worker = script_steps[0]["worker"] if script_steps else self.default_worker
        if primary_worker not in self.worker_keys and self.worker_keys:
            primary_worker = self.default_worker or self.worker_keys[0]

        metadata = {
            "goal": goal_text,
            "thought": plan_model.thought,
        }
        if orchestrator_phase and orchestrator_phase.get("notes"):
            metadata["notes"] = orchestrator_phase.get("notes")

        self.logger.info("ManagerScriptPlanner produced script with %d step(s)", len(script_steps))
        return Action(
            tool_name=primary_worker,
            tool_args={
                "script": self._strip_guided_tool_args(script_steps),
                "script_metadata": metadata,
                "original_task": goal_text,
            },
        )

    def _strip_guided_tool_args(self, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove tool_name/args from guided steps so workers reason autonomously."""
        sanitized: List[Dict[str, Any]] = []
        for step in steps:
            if not isinstance(step, dict):
                continue
            mode = str(step.get("execution_mode") or "").strip().lower()
            if mode == "guided":
                stripped = dict(step)
                stripped.pop("tool_name", None)
                stripped.pop("args", None)
                sanitized.append(stripped)
            else:
                sanitized.append(step)
        return sanitized

    def _normalize_script_workers(self, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Ensure each script step references a known worker."""
        if not steps:
            return steps
        normalized: List[Dict[str, Any]] = []
        fallback_worker = self.default_worker or (self.worker_keys[0] if self.worker_keys else "")
        for idx, step in enumerate(steps, 1):
            worker = step.get("worker")
            if worker in self.worker_keys:
                normalized.append(step)
                continue
            if not fallback_worker:
                self.logger.warning(
                    "ManagerScriptPlanner: step %d references unknown worker '%s' and no fallback is available",
                    idx,
                    worker,
                )
                continue
            fixed = dict(step)
            fixed["worker"] = fallback_worker
            self.logger.warning(
                "ManagerScriptPlanner: step %d referenced unknown worker '%s'. Reassigning to fallback worker '%s'.",
                idx,
                worker,
                fallback_worker,
            )
            normalized.append(fixed)
        return normalized

    def _select_orchestrator_phase(
        self,
        fallback_task: str,
        history: List[Dict[str, Any]],
    ) -> Tuple[Optional[Dict[str, Any]], str]:
        from ..services.request_context import get_from_context

        upstream = get_from_context("strategic_plan")
        if not upstream:
            upstream = next((h.get("content") for h in reversed(history) if h.get("type") == "strategic_plan"), None)

        plan_obj = upstream.get("plan") if isinstance(upstream, dict) else {}
        if not isinstance(plan_obj, dict):
            plan_obj = upstream if isinstance(upstream, dict) else {}
        phases_in = plan_obj.get("phases") if isinstance(plan_obj, dict) else []
        orchestrator_phase = None

        if self.manager_worker_key and isinstance(phases_in, list):
            matching = [p for p in phases_in if str(p.get("worker", "")).strip() == self.manager_worker_key]
            phase_index = get_from_context("orchestrator_phase_index")
            if matching:
                if isinstance(phase_index, int) and 0 <= phase_index < len(matching):
                    orchestrator_phase = matching[phase_index]
                else:
                    orchestrator_phase = matching[0]

        goal_text = orchestrator_phase.get("goals") if orchestrator_phase else fallback_task
        if not goal_text:
            goal_text = fallback_task
        return orchestrator_phase, goal_text

    def _collect_previous_outputs(self, history: List[Dict[str, Any]]) -> List[str]:
        synthesized_outputs: List[str] = []
        regular_outputs: List[str] = []
        for entry in reversed(history):
            if not isinstance(entry, dict):
                continue
            entry_type = entry.get("type")
            if entry_type == SYNTHESIS:
                content = entry.get("content", {})
                if isinstance(content, dict):
                    summary = content.get("synthesized_summary")
                    if not summary:
                        full_result = content.get("full_result", {})
                        if isinstance(full_result, dict):
                            summary = full_result.get("human_readable_summary") or full_result.get("summary")
                    actual_data = content.get("actual_data") or content.get("payload")
                    output_parts = []
                    if summary:
                        output_parts.append(summary)
                    if actual_data:
                        try:
                            import json as _json
                            output_parts.append(_json.dumps(actual_data, indent=2)[:5000])
                        except Exception:
                            output_parts.append(str(actual_data)[:5000])
                    if output_parts:
                        synthesized_outputs.append("\n\n".join(output_parts))
            elif entry_type in {"final", "assistant_message", "manager_result"}:
                content = entry.get("content", {})
                if isinstance(content, dict):
                    summary = content.get("human_readable_summary") or content.get("summary")
                    if summary:
                        regular_outputs.append(summary)
                elif isinstance(content, str):
                    regular_outputs.append(content)
            if len(synthesized_outputs) >= 2:
                break
            if not synthesized_outputs and len(regular_outputs) >= 3:
                break
        return synthesized_outputs if synthesized_outputs else regular_outputs

    def _build_worker_catalog(self) -> str:
        lines: List[str] = []
        for spec in self.worker_specs:
            worker = spec.get("worker")
            if not worker:
                continue
            lines.append(f"- {worker}: {spec.get('description', '').strip()}")
            tools = spec.get("tools") or []
            if tools:
                tool_lines = []
                for tool in tools:
                    name = tool.get("name") or tool.get("tool_name")
                    if not name:
                        continue
                    desc = tool.get("description", "")
                    args = tool.get("args")
                    if args:
                        args_str = ", ".join(args) if isinstance(args, list) else str(args)
                        tool_lines.append(f"    • {name}({args_str}): {desc}")
                    else:
                        tool_lines.append(f"    • {name}: {desc}")
                if tool_lines:
                    lines.extend(tool_lines)
        return "\n".join(lines)

    def _default_planning_prompt(self) -> str:
        return (
            "You are a tactical Power BI manager. Your director gives you one goal at a time.\n"
            "You must respond with a STRICT JSON object containing a 'thought' string and a 'script' array.\n\n"
            "Each script entry must include: name, worker (from the list below), tool_name (exact tool), args (object), "
            "and MAY include execution_mode when needed.\n"
            "Workers and their tools:\n{worker_catalog}\n\n"
            "Rules:\n"
            "1. Think like a programmer writing a script.\n"
            "2. Ensure prerequisites are satisfied before any dependent tool (e.g., gather data before validation).\n"
            "3. Keep the script minimal and ordered. No speculative or redundant calls.\n"
            "4. Only use the tools listed for each worker.\n"
            "5. Choose an execution mode per step:\n"
            "   • 'direct' (default) when every argument is concrete and the worker can run it deterministically.\n"
            "   • 'guided' when the worker must reason, fill placeholders, or iterate on freshly retrieved data. "
            "Provide the best available hints in args, but expect the worker to adapt.\n"
            "6. Never delegate planning blindly – if you set execution_mode='guided', explain why in the step notes.\n\n"
            "Example output:\n"
            "{\n"
            "  \"thought\": \"List current relationships, then add the requested one.\",\n"
            "  \"script\": [\n"
            "    {\"name\": \"List relationships\", \"worker\": \"schema\", \"tool_name\": \"list_relationships\", \"args\": {}, \"execution_mode\": \"direct\"},\n"
            "    {\"name\": \"Count columns per table\", \"worker\": \"schema\", \"tool_name\": \"list_columns\", \"args\": {\"table\": \"<table_from_previous>\"}, \"execution_mode\": \"guided\", \"notes\": \"Worker must iterate over each table returned earlier.\"}\n"
            "  ]\n"
            "}\n"
        )
