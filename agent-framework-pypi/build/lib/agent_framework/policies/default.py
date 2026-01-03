"""
Default policy implementations for Framework v2.

These provide sensible defaults that can be configured via YAML.
"""

from typing import Any, Dict, List, Optional, Tuple
from ..base import FinalResponse
from ..constants import TASK
from .base import (
    CompletionDetector,
    TerminationPolicy,
    LoopPreventionPolicy,
    HITLPolicy,
    CheckpointPolicy,
    FollowUpPolicy,
)


class DefaultCompletionDetector(CompletionDetector):
    """Default completion detection using configurable patterns."""
    
    def __init__(
        self,
        indicators: Optional[List[str]] = None,
        check_final_response: bool = True,
        check_operation_types: Optional[List[str]] = None,
        check_response_validation: bool = True,
        check_history_depth: int = 10,
    ):
        self.indicators = indicators or [
            "completed", "success", "done", "finished", "task complete"
        ]
        self.check_final_response = check_final_response
        self.check_operation_types = check_operation_types or [
            "display_message", "model_ops", "display_table"
        ]
        self.check_response_validation = check_response_validation
        self.check_history_depth = check_history_depth
    
    def is_complete(
        self,
        result: Any,
        history: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> bool:
        """Check if result indicates completion.
        
        IMPORTANT: Only checks the CURRENT turn's history to avoid false positives
        from previous turn completions. A new turn starts with a "task" entry.
        """
        # Check result structure
        if isinstance(result, dict):
            # Check for explicit completion flag (from complete_task tool)
            if result.get("completed") is True:
                return True
            
            # Check response_validation.complete
            if self.check_response_validation:
                validation = result.get("response_validation", {})
                if validation.get("complete") is True:
                    return True
            
            # Check operation type
            operation = result.get("operation")
            if operation in self.check_operation_types:
                summary = result.get("human_readable_summary", "").lower()
                if any(ind in summary for ind in self.indicators):
                    return True
            
            # Check for completion indicators in message/summary fields
            message = result.get("message", "").lower()
            summary = result.get("summary", "").lower()
            final_result = result.get("final_result", "").lower()
            if any(ind in msg for msg in [message, summary, final_result] for ind in self.indicators):
                return True
        
        # CRITICAL: Only check history for the CURRENT turn (entries after the last "task" entry)
        # This prevents false completion detection from previous turn completions
        current_turn_history = self._get_current_turn_history(history)
        
        for entry in reversed(current_turn_history[-self.check_history_depth:]):
            # Check if last action was complete_task
            if entry.get("type") == "action" and entry.get("tool") == "complete_task":
                return True
            
            if entry.get("type") == "final":
                content = str(entry.get("content", "")).lower()
                if any(ind in content for ind in self.indicators):
                    return True
            
            # Check observation content for completion signals
            if entry.get("type") == "observation":
                content = str(entry.get("content", "")).lower()
                if isinstance(entry.get("content"), dict):
                    if entry.get("content", {}).get("completed") is True:
                        return True
                if any(ind in content for ind in self.indicators):
                    return True
        
        return False
    
    def _get_current_turn_history(self, history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract only the current turn's history (entries after the last 'task' entry).
        
        This prevents completion signals from previous turns being incorrectly detected
        as completion for the current turn.
        """
        if not history:
            return []
        
        # Find the index of the last "task" entry (marks start of current turn)
        last_task_idx = -1
        for i in range(len(history) - 1, -1, -1):
            if history[i].get("type") == TASK:
                last_task_idx = i
                break
        
        # If no task found, return all history (fallback)
        if last_task_idx < 0:
            return history
        
        # Return only entries after the last task (current turn)
        return history[last_task_idx + 1:]


class DefaultTerminationPolicy(TerminationPolicy):
    """Configurable termination policy."""
    
    def __init__(
        self,
        max_iterations: Optional[int] = None,
        require_terminal_tool: bool = False,
        terminal_tools: Optional[List[str]] = None,
        check_completion: bool = True,
        completion_detector: Optional[CompletionDetector] = None,
        on_max_iterations: str = "error",  # "error" or "return_partial"
    ):
        self.max_iterations = max_iterations
        self.require_terminal_tool = require_terminal_tool
        self.terminal_tools = set(terminal_tools or [])
        self.check_completion = check_completion
        self.completion_detector = completion_detector or DefaultCompletionDetector()
        self.on_max_iterations = on_max_iterations
    
    def should_terminate(
        self,
        iteration: int,
        plan_outcome: Any,
        history: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> bool:
        """Check if execution should terminate."""
        # Max iterations check
        if self.max_iterations and iteration > self.max_iterations:
            return True
        
        # FinalResponse always terminates
        if isinstance(plan_outcome, FinalResponse):
            return True
        
        # Terminal tool check (if required)
        if self.require_terminal_tool:
            from ..base import Action
            if isinstance(plan_outcome, Action):
                if plan_outcome.tool_name in self.terminal_tools:
                    return True
            elif isinstance(plan_outcome, list):
                # Check if any action is a terminal tool
                if any(isinstance(a, Action) and a.tool_name in self.terminal_tools 
                       for a in plan_outcome):
                    return True
        
        # Completion detection (if enabled)
        # NOTE: Only check completion from history if planner is NOT planning new actions
        # If planner is returning Actions, that means task is NOT complete yet
        # Completion should be checked AFTER actions are executed, not before
        # This prevents premature termination when planner is actively working
        if self.check_completion:
            from ..base import Action
            # Don't check completion if planner is planning new actions
            # Only check if planner returned None or we're in a special state
            if not isinstance(plan_outcome, (Action, list, FinalResponse)):
                # Planner didn't return actions - check if last observation indicates completion
                last_obs = next(
                    (h.get("content") for h in reversed(history) 
                     if h.get("type") == "observation"),
                    None
                )
                if last_obs and self.completion_detector.is_complete(
                    last_obs, history, context
                ):
                    return True
        
        return False


class DefaultLoopPreventionPolicy(LoopPreventionPolicy):
    """Configurable loop prevention."""
    
    def __init__(
        self,
        enabled: bool = True,
        action_window: int = 5,
        observation_window: int = 5,
        repetition_threshold: int = 3,
        check_completion_in_loop: bool = True,
        completion_detector: Optional[CompletionDetector] = None,
        on_stagnation: str = "error",  # "error" or "warn_and_continue"
    ):
        self.enabled = enabled
        self.action_window = action_window
        self.observation_window = observation_window
        self.repetition_threshold = repetition_threshold
        self.check_completion_in_loop = check_completion_in_loop
        self.completion_detector = completion_detector or DefaultCompletionDetector()
        self.on_stagnation = on_stagnation
    
    def detect_stagnation(
        self,
        action_history: List[Tuple],
        observation_history: List[Any],
        context: Dict[str, Any]
    ) -> Optional[str]:
        """Detect stagnation in execution."""
        if not self.enabled:
            return None
        
        # Check if task is complete but agent continues (highest priority)
        if self.check_completion_in_loop and observation_history:
            last_obs = observation_history[-1]
            # Convert string observations back to dict if possible
            obs_to_check = last_obs
            if isinstance(last_obs, str):
                try:
                    import json
                    obs_to_check = json.loads(last_obs)
                except:
                    pass
            
            if self.completion_detector.is_complete(obs_to_check, [], context):
                return "Task appears complete but agent continues execution"
        
        if len(action_history) < self.repetition_threshold:
            return None
        
        # Check for repeated actions
        recent_actions = list(action_history)[-self.repetition_threshold:]
        if len(set(recent_actions)) == 1:
            # Check for repeated observations
            if len(observation_history) >= self.repetition_threshold:
                recent_obs = list(observation_history)[-self.repetition_threshold:]
                # Normalize observations for comparison
                obs_strs = [str(obs) for obs in recent_obs]
                if len(set(obs_strs)) == 1:
                    action_desc = str(recent_actions[0]) if recent_actions else "unknown"
                    return (
                        f"Stagnation: Same action pattern repeated {self.repetition_threshold} "
                        f"times with identical results. Action: {action_desc}"
                    )
        
        return None


class DefaultHITLPolicy(HITLPolicy):
    """Configurable HITL policy."""
    
    def __init__(
        self,
        enabled: bool = False,
        scope: str = "writes",  # "writes" or "all"
        write_tools: Optional[List[str]] = None,
    ):
        self.enabled = enabled
        self.scope = scope.lower()
        self.write_tools = set(write_tools or [
            "add_table", "add_column", "add_relationship", "update_relationship",
            "rename_column", "add_measure", "remove_column", "remove_relationship",
            "remove_measure", "update_measure", "update_partition_source", "update_sql_query"
        ])
    
    def requires_approval(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        context: Dict[str, Any]
    ) -> bool:
        """Check if approval is required."""
        if not self.enabled:
            return False
        
        # Check if already approved
        approvals = context.get("approvals", {})
        if approvals.get(tool_name):
            return False
        
        # Check if tool was already executed (bypass)
        job_id = context.get("job_id") or context.get("JOB_ID")
        if job_id:
            try:
                from ...state.job_store import get_job_store
                import json
                sig = f"{tool_name}:{json.dumps(tool_args, sort_keys=True, default=str)}"
                if get_job_store().has_executed_action(str(job_id), sig):
                    return False
            except Exception:
                pass
        
        # Check scope
        if self.scope == "all":
            return True
        elif self.scope == "writes":
            return tool_name in self.write_tools
        
        return False
    
    def create_approval_request(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create approval request payload."""
        return {
            "operation": "await_approval",
            "payload": {
                "await_approval": True,
                "tool": tool_name,
                "args": tool_args,
                "message": f"Approval required to execute tool '{tool_name}'.",
                "reason": f"HITL enabled (scope={self.scope})"
            },
            "human_readable_summary": f"Approval required: {tool_name}"
        }


class DefaultCheckpointPolicy(CheckpointPolicy):
    """Configurable checkpoint policy for intermediate results."""
    
    def __init__(
        self,
        enabled: bool = False,
        checkpoint_after_iterations: Optional[int] = None,
        checkpoint_on_operations: Optional[List[str]] = None,
        checkpoint_on_tools: Optional[List[str]] = None,
    ):
        self.enabled = enabled
        self.checkpoint_after_iterations = checkpoint_after_iterations
        self.checkpoint_on_operations = set(checkpoint_on_operations or [])
        self.checkpoint_on_tools = set(checkpoint_on_tools or [])
    
    def should_checkpoint(
        self,
        result: Any,
        iteration: int,
        context: Dict[str, Any]
    ) -> bool:
        """Check if checkpoint should occur."""
        if not self.enabled:
            return False
        
        # Check iteration-based checkpoint
        if (self.checkpoint_after_iterations and 
            iteration >= self.checkpoint_after_iterations):
            return True
        
        # Check operation-based checkpoint
        if isinstance(result, dict):
            operation = result.get("operation")
            if operation in self.checkpoint_on_operations:
                return True
        
        # Check tool-based checkpoint
        last_tool = context.get("last_tool")
        if last_tool and last_tool in self.checkpoint_on_tools:
            return True
        
        return False
    
    def create_checkpoint_response(
        self,
        result: Any,
        context: Dict[str, Any]
    ) -> FinalResponse:
        """Create checkpoint response."""
        if isinstance(result, dict):
            return FinalResponse(
                operation=result.get("operation", "display_message"),
                payload={
                    **result.get("payload", {}),
                    "checkpoint": True,
                    "message": "Intermediate result - review before continuing"
                },
                human_readable_summary=result.get(
                    "human_readable_summary", 
                    "Intermediate checkpoint"
                )
            )
        else:
            return FinalResponse(
                operation="display_message",
                payload={
                    "message": str(result),
                    "checkpoint": True
                },
                human_readable_summary="Intermediate checkpoint"
            )


class DefaultFollowUpPolicy(FollowUpPolicy):
    """Configurable follow-up policy."""
    
    def __init__(
        self,
        enabled: bool = True,
        max_phases: Optional[int] = None,
        check_completion: bool = True,
        completion_detector: Optional[CompletionDetector] = None,
        stop_on_completion: bool = True,
    ):
        self.enabled = enabled
        self.max_phases = max_phases
        self.check_completion = check_completion
        self.completion_detector = completion_detector or DefaultCompletionDetector()
        self.stop_on_completion = stop_on_completion
    
    def should_follow_up(
        self,
        primary_result: Dict[str, Any],
        phases: List[Dict[str, Any]],
        completed_phases: int,
        context: Dict[str, Any]
    ) -> bool:
        """Check if follow-ups should continue."""
        if not self.enabled:
            return False
        
        # Check if task is already complete
        if self.stop_on_completion and self.check_completion:
            if self.completion_detector.is_complete(primary_result, [], context):
                return False
        
        # Check max phases
        if self.max_phases is not None:
            remaining_phases = len(phases) - completed_phases
            if remaining_phases > self.max_phases:
                return False
        
        # Check if more phases exist
        return completed_phases < len(phases)

