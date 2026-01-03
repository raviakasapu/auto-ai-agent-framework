"""
Base policy interfaces for Framework v2.

All policies are abstract base classes that define the contract
for configurable behavior in the framework.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

from ..base import FinalResponse


class CompletionDetector(ABC):
    """Detects if a task is complete based on result/history."""
    
    @abstractmethod
    def is_complete(
        self,
        result: Any,
        history: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> bool:
        """
        Determine if task is complete.
        
        Args:
            result: Current result from tool/agent
            history: Execution history
            context: Additional context (task, job_id, etc.)
        
        Returns:
            True if task appears complete
        """
        pass


class TerminationPolicy(ABC):
    """Determines when to stop agent execution."""
    
    @abstractmethod
    def should_terminate(
        self,
        iteration: int,
        plan_outcome: Any,  # Action, List[Action], or FinalResponse
        history: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> bool:
        """
        Determine if execution should terminate.
        
        Args:
            iteration: Current iteration number
            plan_outcome: Result from planner (Action, List[Action], or FinalResponse)
            history: Execution history
            context: Additional context
        
        Returns:
            True if execution should stop
        """
        pass


class LoopPreventionPolicy(ABC):
    """Detects and prevents infinite loops."""
    
    @abstractmethod
    def detect_stagnation(
        self,
        action_history: List[Tuple],
        observation_history: List[Any],
        context: Dict[str, Any]
    ) -> Optional[str]:
        """
        Detect if agent is stuck in a loop.
        
        Args:
            action_history: Recent action signatures
            observation_history: Recent observation results
            context: Additional context
        
        Returns:
            Reason string if stagnation detected, None otherwise
        """
        pass


class HITLPolicy(ABC):
    """Human-in-the-Loop approval policy."""
    
    @abstractmethod
    def requires_approval(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        context: Dict[str, Any]
    ) -> bool:
        """
        Check if tool execution requires human approval.
        
        Args:
            tool_name: Name of tool to execute
            tool_args: Tool arguments
            context: Additional context (job_id, approvals, etc.)
        
        Returns:
            True if approval is required
        """
        pass
    
    @abstractmethod
    def create_approval_request(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create approval request payload.
        
        Args:
            tool_name: Name of tool requiring approval
            tool_args: Tool arguments
            context: Additional context
        
        Returns:
            Dict with approval request structure
        """
        pass


class CheckpointPolicy(ABC):
    """Policy for intermediate checkpoints - presenting results to user."""
    
    @abstractmethod
    def should_checkpoint(
        self,
        result: Any,
        iteration: int,
        context: Dict[str, Any]
    ) -> bool:
        """
        Determine if execution should pause to present intermediate results.
        
        Args:
            result: Current result
            iteration: Current iteration number
            context: Additional context
        
        Returns:
            True if checkpoint should occur
        """
        pass
    
    @abstractmethod
    def create_checkpoint_response(
        self,
        result: Any,
        context: Dict[str, Any]
    ) -> FinalResponse:
        """
        Create checkpoint response to present to user.
        
        Args:
            result: Current result
            context: Additional context
        
        Returns:
            FinalResponse for checkpoint
        """
        pass


class FollowUpPolicy(ABC):
    """Determines if manager should execute follow-up phases."""
    
    @abstractmethod
    def should_follow_up(
        self,
        primary_result: Dict[str, Any],
        phases: List[Dict[str, Any]],
        completed_phases: int,
        context: Dict[str, Any]
    ) -> bool:
        """
        Determine if manager should continue with follow-up phases.
        
        Args:
            primary_result: Result from primary worker
            phases: List of remaining phases
            completed_phases: Number of phases already completed
            context: Additional context
        
        Returns:
            True if follow-ups should continue
        """
        pass


class HistoryFilter(ABC):
    """Filters history for role-specific prompt building.
    
    Different roles need different levels of detail:
    - Orchestrator: High-level conversation summary only
    - Manager: Phase context + previous synthesis summaries
    - Worker: Current turn execution traces only
    """
    
    @abstractmethod
    def filter_for_prompt(
        self,
        history: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Filter history for prompt building.
        
        Args:
            history: Full history from memory
            context: Additional context (role, phase_id, etc.)
        
        Returns:
            Filtered history appropriate for the role
        """
        pass
    
    def _find_last_task_marker(self, history: List[Dict[str, Any]]) -> int:
        """
        Find index of last 'task' entry (marks turn boundary).
        
        Returns:
            Index of last task entry, or -1 if not found
        """
        from ..constants import TASK
        for i in range(len(history) - 1, -1, -1):
            if history[i].get("type") == TASK:
                return i
        return -1

