# Message Format Specification

Complete reference for message formats used by the framework.

## Message Structure

All messages must include:

```python
{
    "type": str,        # Required: Message type constant
    "content": Any,     # Required: Message content
    "timestamp": str,   # Optional: ISO timestamp
    "agent_key": str,   # Optional: Agent identifier
    "metadata": dict,   # Optional: Additional metadata
}
```

## Type Constants

Import from `agent_framework.constants`:

```python
from agent_framework.constants import (
    # Conversation
    USER_MESSAGE,           # "user_message"
    ASSISTANT_MESSAGE,      # "assistant_message"
    
    # Execution Trace
    TASK,                   # "task"
    ACTION,                 # "action"
    OBSERVATION,            # "observation"
    ERROR,                  # "error"
    
    # Completion
    FINAL,                  # "final"
    SYNTHESIS,              # "synthesis"
    
    # Planning
    STRATEGIC_PLAN,         # "strategic_plan"
    SUGGESTED_PLAN,         # "suggested_plan"
    SCRIPT_PLAN,            # "script_plan"
    DIRECTOR_CONTEXT,       # "director_context"
    INJECTED_CONTEXT,       # "injected_context"
    DELEGATION,             # "delegation"
)
```

## Message Types

### user_message

User input in conversation.

```python
{
    "type": "user_message",
    "content": "List all tables in the model",
    "timestamp": "2024-01-15T10:30:00Z",
    "metadata": {
        "user_id": "user_123"
    }
}
```

### assistant_message

Assistant response to user.

```python
{
    "type": "assistant_message",
    "content": "Found 5 tables: Users, Orders, Products, Categories, Reviews",
    "timestamp": "2024-01-15T10:30:05Z"
}
```

### task

Task assignment to agent.

```python
{
    "type": "task",
    "content": "Analyze the data model structure",
    "agent_key": "analyzer",
    "timestamp": "2024-01-15T10:30:00Z"
}
```

### action

Tool invocation request.

```python
{
    "type": "action",
    "tool": "list_tables",
    "args": {"schema": "public"},
    "agent_key": "analyzer",
    "timestamp": "2024-01-15T10:30:01Z"
}
```

### observation

Tool execution result.

```python
{
    "type": "observation",
    "content": {
        "tables": ["Users", "Orders", "Products"],
        "count": 3,
        "human_readable_summary": "Found 3 tables"
    },
    "agent_key": "analyzer",
    "timestamp": "2024-01-15T10:30:02Z"
}
```

### error

Error during execution.

```python
{
    "type": "error",
    "content": {
        "error_message": "Connection refused",
        "error_type": "ConnectionError",
        "tool": "database_query"
    },
    "agent_key": "analyzer",
    "timestamp": "2024-01-15T10:30:02Z"
}
```

### final

Task completion signal.

```python
{
    "type": "final",
    "content": {
        "operation": "display_message",
        "payload": {"message": "Analysis complete"},
        "human_readable_summary": "Successfully analyzed 3 tables"
    },
    "agent_key": "analyzer",
    "timestamp": "2024-01-15T10:30:03Z"
}
```

### synthesis

Manager aggregation of worker results.

```python
{
    "type": "synthesis",
    "content": "Combined analysis from 3 workers: found 5 tables, 25 columns, 3 relationships",
    "phase_id": 1,
    "from_manager": "analysis_manager",
    "timestamp": "2024-01-15T10:30:10Z",
    "is_global": true
}
```

### strategic_plan

Orchestrator's execution plan.

```python
{
    "type": "strategic_plan",
    "content": {
        "refined_intent": "Analyze model structure and validate relationships",
        "plan": {
            "phases": [
                {"name": "Analyze", "worker": "analyzer", "goals": "..."},
                {"name": "Validate", "worker": "validator", "goals": "..."}
            ],
            "primary_worker": "analyzer",
            "rationale": "Analysis before validation"
        }
    },
    "timestamp": "2024-01-15T10:30:00Z"
}
```

### suggested_plan

Plan suggested to worker.

```python
{
    "type": "suggested_plan",
    "content": {
        "steps": [
            {"name": "List tables", "tool": "list_tables"},
            {"name": "Get columns", "tool": "list_columns"}
        ]
    },
    "agent_key": "analyzer",
    "timestamp": "2024-01-15T10:30:00Z"
}
```

## Type Collections

For filtering:

```python
from agent_framework.constants import (
    CONVERSATION_TYPES,      # [USER_MESSAGE, ASSISTANT_MESSAGE]
    EXECUTION_TRACE_TYPES,   # [TASK, ACTION, OBSERVATION, ERROR]
    COMPLETION_TYPES,        # [FINAL, SYNTHESIS]
    PLANNING_TYPES,          # [STRATEGIC_PLAN, SUGGESTED_PLAN, SCRIPT_PLAN]
)
```

## Message Builder

Use utilities for consistent formatting:

```python
from agent_framework.utils.message_builder import (
    create_user_message,
    create_assistant_message,
    create_task_entry,
    create_action,
    create_observation,
    create_error,
    create_final,
)

# Examples
msg = create_user_message("Hello", metadata={"user_id": "123"})
task = create_task_entry("Analyze data", agent_key="worker_1")
obs = create_observation({"result": "success"}, agent_key="worker_1")
```

## Validation

Messages are validated by the framework. Ensure:

1. `type` is a valid constant
2. `content` is appropriate for the type
3. `agent_key` is provided for execution traces
4. `timestamp` is ISO format if provided

