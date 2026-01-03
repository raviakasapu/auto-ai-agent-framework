"""
Memory type key constants for consistent filtering and history management.

These constants standardize the type keys used in memory entries across
agents, managers, orchestrators, and synthesizers.
"""

# Conversation types (turn-level, high-level messages)
USER_MESSAGE = "user_message"
ASSISTANT_MESSAGE = "assistant_message"

# Execution trace types (task execution)
TASK = "task"
ACTION = "action"
OBSERVATION = "observation"
ERROR = "error"

# Completion types (signals task completion)
FINAL = "final"
SYNTHESIS = "synthesis"  # Standardized (replaces manager_synthesis)

# Planning types (strategic context)
STRATEGIC_PLAN = "strategic_plan"
SUGGESTED_PLAN = "suggested_plan"
SCRIPT_PLAN = "script_plan"
SCRIPT_INSTRUCTION = "script_instruction"

# Context types (injected context)
DIRECTOR_CONTEXT = "director_context"
INJECTED_CONTEXT = "injected_context"

# Global types (cross-agent communication)
GLOBAL_OBSERVATION = "global_observation"

# Delegation types (manager-worker communication)
DELEGATION = "delegation"

# Type collections for filtering

# Conversation layer: turn-level messages for orchestrator
CONVERSATION_TYPES = [USER_MESSAGE, ASSISTANT_MESSAGE]

# Execution layer: task execution traces for workers
EXECUTION_TRACE_TYPES = [TASK, ACTION, OBSERVATION, ERROR]

# Completion layer: signals that indicate task completion
COMPLETION_TYPES = [FINAL, SYNTHESIS]

# Turn markers: entries that mark the start of a new turn
TURN_MARKERS = [TASK]

# Planning layer: strategic planning context
PLANNING_TYPES = [STRATEGIC_PLAN, SUGGESTED_PLAN, SCRIPT_PLAN, SCRIPT_INSTRUCTION]

# Context layer: injected context
CONTEXT_TYPES = [DIRECTOR_CONTEXT, INJECTED_CONTEXT]

# Global layer: cross-agent communication
GLOBAL_TYPES = [GLOBAL_OBSERVATION, SYNTHESIS]

# Delegation layer: manager-worker communication
DELEGATION_TYPES = [DELEGATION]

