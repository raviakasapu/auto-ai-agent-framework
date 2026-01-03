"""
History filtering implementations for hierarchical prompt building.

Each role (orchestrator, manager, worker) gets filtered history appropriate
for their level of abstraction.
"""

from typing import Any, Dict, List, Optional

from .base import HistoryFilter
from ..constants import (
    USER_MESSAGE,
    ASSISTANT_MESSAGE,
    SYNTHESIS,
    FINAL,
    TASK,
    ACTION,
    OBSERVATION,
    GLOBAL_OBSERVATION,
    CONVERSATION_TYPES,
    COMPLETION_TYPES,
    EXECUTION_TRACE_TYPES,
)


class OrchestratorHistoryFilter(HistoryFilter):
    """High-level conversation summary for orchestrator.
    
    Orchestrator sees:
    - Conversation turns (user_message, assistant_message) only
    - Limited to last N turns (default: 8)
    
    Orchestrator does NOT see:
    - Raw execution traces (action, observation)
    - Detailed tool results
    - Previous turn completion signals (they're in assistant messages)
    """
    
    def __init__(self, max_conversation_turns: int = 8):
        self.max_conversation_turns = max_conversation_turns
    
    def filter_for_prompt(
        self,
        history: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Filter to conversation turns only."""
        max_turns = context.get("max_conversation_turns", self.max_conversation_turns)
        
        # Only conversation turns (user_message, assistant_message)
        conversation = [
            e for e in history
            if e.get("type") in CONVERSATION_TYPES
        ]
        
        # Limit to last N turns
        return conversation[-max_turns:]


class ManagerHistoryFilter(HistoryFilter):
    """Phase-relevant context for managers.
    
    Manager sees:
    - Previous phase synthesis summaries (if sequential phases)
    - Only entries relevant to current phase context
    
    Manager does NOT see:
    - Full conversation history (orchestrator handles that)
    - Raw execution traces from workers
    - Completion signals from other phases
    """
    
    def filter_for_prompt(
        self,
        history: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Filter to phase-relevant context only."""
        # Managers don't need conversation history (orchestrator handles it)
        # Only include synthesis summaries from previous phases if sequential
        phase_id = context.get("phase_id")
        previous_phase_id = context.get("previous_phase_id")
        
        relevant = []
        
        # If we have phase context, only include synthesis from previous phase
        if previous_phase_id is not None:
            relevant = [
                e for e in history
                if e.get("type") == SYNTHESIS
                and e.get("phase_id") == previous_phase_id
            ]
        elif phase_id is not None and phase_id > 0:
            # Current phase > 0 means there was a previous phase
            # Include synthesis from phase_id - 1
            relevant = [
                e for e in history
                if e.get("type") == SYNTHESIS
                and e.get("phase_id") == phase_id - 1
            ]
        
        return relevant


class WorkerHistoryFilter(HistoryFilter):
    """Current turn execution traces for workers.
    
    Worker sees:
    - Current task marker
    - Current turn's execution traces (action, observation)
    - Relevant global observations
    
    Worker does NOT see:
    - Previous turn's history
    - Completion signals from previous turns
    - Other workers' execution traces (unless global)
    """
    
    def filter_for_prompt(
        self,
        history: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Filter to current turn execution traces only."""
        # Find current turn start
        last_task_idx = self._find_last_task_marker(history)
        if last_task_idx < 0:
            return []  # No current turn yet
        
        # Get current turn entries only (after last task marker)
        current_turn = history[last_task_idx + 1:]
        
        # Include execution traces (action, observation, global_observation)
        # Exclude completion signals (checked separately in completion detection)
        filtered = [
            e for e in current_turn
            if e.get("type") in EXECUTION_TRACE_TYPES + [GLOBAL_OBSERVATION]
        ]
        
        return filtered


class DefaultHistoryFilter(HistoryFilter):
    """Default filter that returns all history (backward compatibility)."""
    
    def filter_for_prompt(
        self,
        history: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Return all history unchanged."""
        return history

