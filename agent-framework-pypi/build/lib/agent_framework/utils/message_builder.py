"""
Message builder utilities for creating framework-compatible memory entries.

This module provides helper functions for implementations to create properly
formatted message entries that the framework expects for hierarchical filtering
and history management.

Expected Message Format
=======================
All messages must be dictionaries with at minimum:
- "type": str - One of the type constants from agent_framework.constants
- "content": Any - The actual content of the message

Optional metadata fields:
- "timestamp": float - When the message was created
- "turn_id": Optional[str] - Which conversation turn this belongs to
- "phase_id": Optional[int] - Which phase (for managers)
- "from_manager": Optional[str] - Which manager created this
- "from_worker": Optional[str] - Which worker created this
- Other type-specific fields (see individual builder functions)
"""

from __future__ import annotations

from typing import Any, Dict, Optional
import time

from ..constants import (
    # Conversation types
    USER_MESSAGE,
    ASSISTANT_MESSAGE,
    # Execution trace types
    TASK,
    ACTION,
    OBSERVATION,
    ERROR,
    GLOBAL_OBSERVATION,
    # Completion types
    FINAL,
    SYNTHESIS,
    # Planning types
    STRATEGIC_PLAN,
    SUGGESTED_PLAN,
    SCRIPT_PLAN,
    # Context types
    DIRECTOR_CONTEXT,
    INJECTED_CONTEXT,
    # Delegation types
    DELEGATION,
)


def create_user_message(
    content: str,
    timestamp: Optional[float] = None,
    turn_id: Optional[str] = None,
    **extra_metadata: Any
) -> Dict[str, Any]:
    """Create a user message entry.
    
    Args:
        content: The user's message content
        timestamp: Optional timestamp (defaults to current time)
        turn_id: Optional turn identifier
        **extra_metadata: Additional metadata fields
        
    Returns:
        Formatted message dict with type="user_message"
    """
    msg = {
        "type": USER_MESSAGE,
        "content": content,
        "timestamp": timestamp or time.time(),
    }
    if turn_id:
        msg["turn_id"] = turn_id
    msg.update(extra_metadata)
    return msg


def create_assistant_message(
    content: str,
    timestamp: Optional[float] = None,
    turn_id: Optional[str] = None,
    **extra_metadata: Any
) -> Dict[str, Any]:
    """Create an assistant message entry.
    
    Args:
        content: The assistant's response content
        timestamp: Optional timestamp (defaults to current time)
        turn_id: Optional turn identifier
        **extra_metadata: Additional metadata fields
        
    Returns:
        Formatted message dict with type="assistant_message"
    """
    msg = {
        "type": ASSISTANT_MESSAGE,
        "content": content,
        "timestamp": timestamp or time.time(),
    }
    if turn_id:
        msg["turn_id"] = turn_id
    msg.update(extra_metadata)
    return msg


def create_task_entry(
    content: str,
    timestamp: Optional[float] = None,
    turn_id: Optional[str] = None,
    **extra_metadata: Any
) -> Dict[str, Any]:
    """Create a task entry (marks start of new execution turn).
    
    Args:
        content: The task description
        timestamp: Optional timestamp (defaults to current time)
        turn_id: Optional turn identifier
        **extra_metadata: Additional metadata fields
        
    Returns:
        Formatted message dict with type="task"
    """
    msg = {
        "type": TASK,
        "content": content,
        "timestamp": timestamp or time.time(),
    }
    if turn_id:
        msg["turn_id"] = turn_id
    msg.update(extra_metadata)
    return msg


def create_action_entry(
    tool_name: str,
    tool_args: Dict[str, Any],
    timestamp: Optional[float] = None,
    turn_id: Optional[str] = None,
    **extra_metadata: Any
) -> Dict[str, Any]:
    """Create an action entry (tool/action invocation).
    
    Args:
        tool_name: Name of the tool/action being invoked
        tool_args: Arguments passed to the tool
        timestamp: Optional timestamp (defaults to current time)
        turn_id: Optional turn identifier
        **extra_metadata: Additional metadata fields
        
    Returns:
        Formatted message dict with type="action"
    """
    msg = {
        "type": ACTION,
        "tool": tool_name,
        "args": tool_args,
        "timestamp": timestamp or time.time(),
    }
    if turn_id:
        msg["turn_id"] = turn_id
    msg.update(extra_metadata)
    return msg


def create_observation_entry(
    content: Any,
    timestamp: Optional[float] = None,
    turn_id: Optional[str] = None,
    **extra_metadata: Any
) -> Dict[str, Any]:
    """Create an observation entry (tool result/observation).
    
    Args:
        content: The observation content (can be any serializable type)
        timestamp: Optional timestamp (defaults to current time)
        turn_id: Optional turn identifier
        **extra_metadata: Additional metadata fields
        
    Returns:
        Formatted message dict with type="observation"
    """
    msg = {
        "type": OBSERVATION,
        "content": content,
        "timestamp": timestamp or time.time(),
    }
    if turn_id:
        msg["turn_id"] = turn_id
    msg.update(extra_metadata)
    return msg


def create_error_entry(
    content: str,
    error_type: Optional[str] = None,
    timestamp: Optional[float] = None,
    turn_id: Optional[str] = None,
    **extra_metadata: Any
) -> Dict[str, Any]:
    """Create an error entry.
    
    Args:
        content: Error message or description
        error_type: Optional error type classification
        timestamp: Optional timestamp (defaults to current time)
        turn_id: Optional turn identifier
        **extra_metadata: Additional metadata fields
        
    Returns:
        Formatted message dict with type="error"
    """
    msg = {
        "type": ERROR,
        "content": content,
        "timestamp": timestamp or time.time(),
    }
    if error_type:
        msg["error_type"] = error_type
    if turn_id:
        msg["turn_id"] = turn_id
    msg.update(extra_metadata)
    return msg


def create_final_entry(
    content: str,
    timestamp: Optional[float] = None,
    turn_id: Optional[str] = None,
    **extra_metadata: Any
) -> Dict[str, Any]:
    """Create a final/completion entry.
    
    Args:
        content: Final response or completion message
        timestamp: Optional timestamp (defaults to current time)
        turn_id: Optional turn identifier
        **extra_metadata: Additional metadata fields
        
    Returns:
        Formatted message dict with type="final"
    """
    msg = {
        "type": FINAL,
        "content": content,
        "timestamp": timestamp or time.time(),
    }
    if turn_id:
        msg["turn_id"] = turn_id
    msg.update(extra_metadata)
    return msg


def create_strategic_plan_entry(
    plan: Dict[str, Any],
    timestamp: Optional[float] = None,
    turn_id: Optional[str] = None,
    **extra_metadata: Any
) -> Dict[str, Any]:
    """Create a strategic plan entry.
    
    Args:
        plan: The strategic plan dictionary
        timestamp: Optional timestamp (defaults to current time)
        turn_id: Optional turn identifier
        **extra_metadata: Additional metadata fields
        
    Returns:
        Formatted message dict with type="strategic_plan"
    """
    msg = {
        "type": STRATEGIC_PLAN,
        "content": plan,
        "timestamp": timestamp or time.time(),
    }
    if turn_id:
        msg["turn_id"] = turn_id
    msg.update(extra_metadata)
    return msg


def create_delegation_entry(
    worker: str,
    task: str,
    timestamp: Optional[float] = None,
    turn_id: Optional[str] = None,
    **extra_metadata: Any
) -> Dict[str, Any]:
    """Create a delegation entry (manager delegating to worker).
    
    Args:
        worker: Name/key of the worker being delegated to
        task: Task description being delegated
        timestamp: Optional timestamp (defaults to current time)
        turn_id: Optional turn identifier
        **extra_metadata: Additional metadata fields
        
    Returns:
        Formatted message dict with type="delegation"
    """
    msg = {
        "type": DELEGATION,
        "worker": worker,
        "task": task,
        "timestamp": timestamp or time.time(),
    }
    if turn_id:
        msg["turn_id"] = turn_id
    msg.update(extra_metadata)
    return msg


def create_synthesis_entry(
    content: Any,
    from_manager: str,
    phase_id: Optional[int] = None,
    timestamp: Optional[float] = None,
    turn_id: Optional[str] = None,
    **extra_metadata: Any
) -> Dict[str, Any]:
    """Create a synthesis entry (manager synthesizing worker results).
    
    Args:
        content: The synthesized content
        from_manager: Name of the manager performing synthesis
        phase_id: Optional phase identifier
        timestamp: Optional timestamp (defaults to current time)
        turn_id: Optional turn identifier
        **extra_metadata: Additional metadata fields
        
    Returns:
        Formatted message dict with type="synthesis"
    """
    msg = {
        "type": SYNTHESIS,
        "content": content,
        "from_manager": from_manager,
        "timestamp": timestamp or time.time(),
    }
    if phase_id is not None:
        msg["phase_id"] = phase_id
    if turn_id:
        msg["turn_id"] = turn_id
    msg.update(extra_metadata)
    return msg


def create_global_observation_entry(
    content: Any,
    from_worker: Optional[str] = None,
    summary: Optional[str] = None,
    timestamp: Optional[float] = None,
    turn_id: Optional[str] = None,
    **extra_metadata: Any
) -> Dict[str, Any]:
    """Create a global observation entry (cross-agent broadcast).
    
    Args:
        content: The observation content
        from_worker: Optional worker name that created this
        summary: Optional human-readable summary
        timestamp: Optional timestamp (defaults to current time)
        turn_id: Optional turn identifier
        **extra_metadata: Additional metadata fields
        
    Returns:
        Formatted message dict with type="global_observation"
    """
    msg = {
        "type": GLOBAL_OBSERVATION,
        "content": content,
        "timestamp": timestamp or time.time(),
    }
    if from_worker:
        msg["from_worker"] = from_worker
    if summary:
        msg["summary"] = summary
    if turn_id:
        msg["turn_id"] = turn_id
    msg.update(extra_metadata)
    return msg


def create_director_context_entry(
    content: str,
    timestamp: Optional[float] = None,
    turn_id: Optional[str] = None,
    **extra_metadata: Any
) -> Dict[str, Any]:
    """Create a director context entry (injected context from context builder).
    
    Args:
        content: The context content
        timestamp: Optional timestamp (defaults to current time)
        turn_id: Optional turn identifier
        **extra_metadata: Additional metadata fields
        
    Returns:
        Formatted message dict with type="director_context"
    """
    msg = {
        "type": DIRECTOR_CONTEXT,
        "content": content,
        "timestamp": timestamp or time.time(),
    }
    if turn_id:
        msg["turn_id"] = turn_id
    msg.update(extra_metadata)
    return msg


def prepare_history_from_job_data(
    job_data: Dict[str, Any],
    message_format: str = "framework"
) -> List[Dict[str, Any]]:
    """Convert job store data into framework-compatible history format.
    
    This is a template/example function. Implementations should adapt this
    to their specific job store format.
    
    Args:
        job_data: Dictionary containing job data from job store
        message_format: Format identifier (for extensibility)
        
    Returns:
        List of properly formatted message entries
        
    Example:
        >>> job_data = {
        ...     "conversation": [
        ...         {"role": "user", "content": "List tables"},
        ...         {"role": "assistant", "content": "Found 5 tables"}
        ...     ],
        ...     "execution_traces": [
        ...         {"type": "task", "content": "List tables"},
        ...         {"type": "action", "tool": "list_tables", "args": {}}
        ...     ]
        ... }
        >>> history = prepare_history_from_job_data(job_data)
    """
    history = []
    
    # Convert conversation turns
    conversation = job_data.get("conversation", [])
    for turn in conversation:
        if turn.get("role") == "user":
            history.append(create_user_message(
                content=turn.get("content", ""),
                timestamp=turn.get("timestamp"),
                turn_id=turn.get("turn_id")
            ))
        elif turn.get("role") == "assistant":
            history.append(create_assistant_message(
                content=turn.get("content", ""),
                timestamp=turn.get("timestamp"),
                turn_id=turn.get("turn_id")
            ))
    
    # Convert execution traces
    traces = job_data.get("execution_traces", [])
    for trace in traces:
        trace_type = trace.get("type")
        if trace_type == TASK:
            history.append(create_task_entry(
                content=trace.get("content", ""),
                timestamp=trace.get("timestamp"),
                turn_id=trace.get("turn_id")
            ))
        elif trace_type == ACTION:
            history.append(create_action_entry(
                tool_name=trace.get("tool", ""),
                tool_args=trace.get("args", {}),
                timestamp=trace.get("timestamp"),
                turn_id=trace.get("turn_id")
            ))
        elif trace_type == OBSERVATION:
            history.append(create_observation_entry(
                content=trace.get("content"),
                timestamp=trace.get("timestamp"),
                turn_id=trace.get("turn_id")
            ))
        # Add other trace types as needed...
    
    return history


# Export all message builder functions for discoverability
__all__ = [
    # Message builder functions
    "create_user_message",
    "create_assistant_message",
    "create_task_entry",
    "create_action_entry",
    "create_observation_entry",
    "create_error_entry",
    "create_final_entry",
    "create_strategic_plan_entry",
    "create_delegation_entry",
    "create_synthesis_entry",
    "create_global_observation_entry",
    "create_director_context_entry",
    "prepare_history_from_job_data",
    # Available message types (for discovery)
    "AVAILABLE_MESSAGE_TYPES",
    "get_message_type_info",
]


# Discovery helpers for implementations
AVAILABLE_MESSAGE_TYPES = {
    # Conversation types
    "user_message": {
        "constant": USER_MESSAGE,
        "builder": create_user_message,
        "description": "High-level user message in a conversation turn",
        "required_fields": ["content"],
        "optional_fields": ["timestamp", "turn_id"],
    },
    "assistant_message": {
        "constant": ASSISTANT_MESSAGE,
        "builder": create_assistant_message,
        "description": "High-level assistant response in a conversation turn",
        "required_fields": ["content"],
        "optional_fields": ["timestamp", "turn_id"],
    },
    # Execution trace types
    "task": {
        "constant": TASK,
        "builder": create_task_entry,
        "description": "Marks the start of a new execution turn",
        "required_fields": ["content"],
        "optional_fields": ["timestamp", "turn_id"],
    },
    "action": {
        "constant": ACTION,
        "builder": create_action_entry,
        "description": "Tool/action invocation",
        "required_fields": ["tool_name", "tool_args"],
        "optional_fields": ["timestamp", "turn_id"],
    },
    "observation": {
        "constant": OBSERVATION,
        "builder": create_observation_entry,
        "description": "Tool result or observation",
        "required_fields": ["content"],
        "optional_fields": ["timestamp", "turn_id"],
    },
    "error": {
        "constant": ERROR,
        "builder": create_error_entry,
        "description": "Error message or exception",
        "required_fields": ["content"],
        "optional_fields": ["error_type", "timestamp", "turn_id"],
    },
    # Completion types
    "final": {
        "constant": FINAL,
        "builder": create_final_entry,
        "description": "Final response/completion signal",
        "required_fields": ["content"],
        "optional_fields": ["timestamp", "turn_id"],
    },
    "synthesis": {
        "constant": SYNTHESIS,
        "builder": create_synthesis_entry,
        "description": "Manager synthesis of worker results",
        "required_fields": ["content", "from_manager"],
        "optional_fields": ["phase_id", "timestamp", "turn_id"],
    },
    # Planning types
    "strategic_plan": {
        "constant": STRATEGIC_PLAN,
        "builder": create_strategic_plan_entry,
        "description": "Orchestrator/manager strategic plan",
        "required_fields": ["plan"],
        "optional_fields": ["timestamp", "turn_id"],
    },
    # Delegation types
    "delegation": {
        "constant": DELEGATION,
        "builder": create_delegation_entry,
        "description": "Manager delegating task to worker",
        "required_fields": ["worker", "task"],
        "optional_fields": ["timestamp", "turn_id"],
    },
    # Global types
    "global_observation": {
        "constant": GLOBAL_OBSERVATION,
        "builder": create_global_observation_entry,
        "description": "Cross-agent broadcast observation",
        "required_fields": ["content"],
        "optional_fields": ["from_worker", "summary", "timestamp", "turn_id"],
    },
    # Context types
    "director_context": {
        "constant": DIRECTOR_CONTEXT,
        "builder": create_director_context_entry,
        "description": "Injected context from context builder",
        "required_fields": ["content"],
        "optional_fields": ["timestamp", "turn_id"],
    },
}


def get_message_type_info(message_type: str) -> Optional[Dict[str, Any]]:
    """Get information about a message type, including its builder function.
    
    Args:
        message_type: Name of the message type (e.g., "user_message", "task")
        
    Returns:
        Dictionary with type information, or None if type doesn't exist
        
    Example:
        >>> info = get_message_type_info("user_message")
        >>> print(info["description"])
        >>> builder = info["builder"]
        >>> msg = builder(content="Hello")
    """
    return AVAILABLE_MESSAGE_TYPES.get(message_type)
