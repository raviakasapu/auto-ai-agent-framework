---
title: Message Store Format
---

# Message Store Format Specification

## Overview

Implementations must prepare message stores in the format specified below. The framework reads messages directly from the store using a location reference. The implementation manages the store structure and persistence.

## Location Reference

The location is a string identifier that the implementation uses to locate messages in the store. Examples:
- `job_id`: `"job_123"` 
- `namespace`: `"namespace/agent-run"`
- `store_path`: `"/path/to/messages.db"`
- `database_key`: `"messages:job_123"`

The implementation determines what the location represents.

## Expected Message Format

All messages must be dictionaries with the following structure:

```python
{
    "type": str,           # REQUIRED: One of the type constants (see below)
    "content": Any,        # REQUIRED for most types (see individual types below)
    "timestamp": float,    # OPTIONAL but RECOMMENDED: Creation timestamp
    "turn_id": str,        # OPTIONAL: Conversation turn identifier
    # ... type-specific fields (see individual types below)
}
```

**Note**: Some message types (like `action` and `delegation`) use different required fields instead of `content`. See individual type specifications below.

## Message Types

### Conversation Types

#### `user_message`

High-level user message in a conversation turn.

```python
{
    "type": "user_message",
    "content": "List all tables in the model",
    "timestamp": 1234567890.0,
    "turn_id": "turn_1"
}
```

**Required fields**: `type`, `content`  
**Optional fields**: `timestamp`, `turn_id`, other metadata

#### `assistant_message`

High-level assistant response in a conversation turn.

```python
{
    "type": "assistant_message",
    "content": "Found 5 tables: ...",
    "timestamp": 1234567891.0,
    "turn_id": "turn_1"
}
```

**Required fields**: `type`, `content`  
**Optional fields**: `timestamp`, `turn_id`, other metadata

### Execution Trace Types

#### `task`

Marks the start of a new execution turn. Used by hierarchical filtering to scope history.

```python
{
    "type": "task",
    "content": "List all tables",
    "timestamp": 1234567890.0,
    "turn_id": "turn_1"
}
```

**Required fields**: `type`, `content`  
**Optional fields**: `timestamp`, `turn_id`, other metadata

#### `action`

Tool/action invocation. **Note**: This type uses `tool` and `args` fields instead of `content`.

```python
{
    "type": "action",
    "tool": "list_tables",
    "args": {"schema": "public"},
    "timestamp": 1234567890.5,
    "turn_id": "turn_1"
}
```

**Required fields**: `type`, `tool`, `args`  
**Optional fields**: `timestamp`, `turn_id`, other metadata

#### `observation`

Tool result or observation.

```python
{
    "type": "observation",
    "content": {"tables": ["users", "orders", ...]},
    "timestamp": 1234567891.0,
    "turn_id": "turn_1"
}
```

**Required fields**: `type`, `content`  
**Optional fields**: `timestamp`, `turn_id`, other metadata

#### `error`

Error message or exception.

```python
{
    "type": "error",
    "content": "Connection failed",
    "error_type": "ConnectionError",
    "timestamp": 1234567891.5,
    "turn_id": "turn_1"
}
```

**Required fields**: `type`, `content`  
**Optional fields**: `error_type`, `timestamp`, `turn_id`, other metadata

### Completion Types

#### `final`

Final response/completion signal.

```python
{
    "type": "final",
    "content": "Task completed successfully",
    "timestamp": 1234567892.0,
    "turn_id": "turn_1"
}
```

**Required fields**: `type`, `content`  
**Optional fields**: `timestamp`, `turn_id`, other metadata

#### `synthesis`

Manager synthesis of worker results.

```python
{
    "type": "synthesis",
    "content": {...synthesized_data...},
    "from_manager": "powerbi-analysis",
    "phase_id": 0,
    "timestamp": 1234567892.0,
    "turn_id": "turn_1"
}
```

**Required fields**: `type`, `content`, `from_manager`  
**Optional fields**: `phase_id`, `timestamp`, `turn_id`, other metadata

### Planning Types

#### `strategic_plan`

Orchestrator/manager strategic plan. The plan is stored in the `content` field.

```python
{
    "type": "strategic_plan",
    "content": {
        "primary_worker": "powerbi-analysis",
        "task_type": "analysis",
        "phases": [...]
    },
    "timestamp": 1234567890.0,
    "turn_id": "turn_1"
}
```

**Required fields**: `type`, `content` (plan dictionary)  
**Optional fields**: `timestamp`, `turn_id`, other metadata

#### `script_plan`

Script-based plan with steps. The plan is stored in the `content` field.

```python
{
    "type": "script_plan",
    "content": {
        "goal": "Create measures",
        "steps": [...]
    },
    "timestamp": 1234567890.0,
    "turn_id": "turn_1"
}
```

**Required fields**: `type`, `content` (plan dictionary)  
**Optional fields**: `timestamp`, `turn_id`, other metadata

### Delegation Types

#### `delegation`

Manager delegating task to worker. **Note**: This type uses `worker` and `task` fields instead of `content`.

```python
{
    "type": "delegation",
    "worker": "powerbi-analysis",
    "task": "List all tables",
    "timestamp": 1234567890.5,
    "turn_id": "turn_1"
}
```

**Required fields**: `type`, `worker`, `task`  
**Optional fields**: `timestamp`, `turn_id`, other metadata

### Global Types

#### `global_observation`

Cross-agent broadcast observation.

```python
{
    "type": "global_observation",
    "content": {...observation_data...},
    "from_worker": "schema_worker",
    "summary": "Found 10 tables",
    "timestamp": 1234567891.0,
    "turn_id": "turn_1"
}
```

**Required fields**: `type`, `content`  
**Optional fields**: `from_worker`, `summary`, `timestamp`, `turn_id`, other metadata

### Context Types

#### `director_context`

Injected context from context builder.

```python
{
    "type": "director_context",
    "content": "...context text...",
    "timestamp": 1234567890.0,
    "turn_id": "turn_1"
}
```

**Required fields**: `type`, `content`  
**Optional fields**: `timestamp`, `turn_id`, other metadata

## Store Organization

The implementation can organize messages however it prefers, but must provide the following views through `BaseMessageStore`:

1. **Conversation Messages**: Messages with `type` in `["user_message", "assistant_message"]`
2. **Agent Messages**: Execution traces (`task`, `action`, `observation`, etc.) for a specific `agent_key`
3. **Global Messages**: Messages with `type` in `["global_observation", "synthesis"]`
4. **Team Messages**: Messages from multiple agents (for managers viewing subordinates)

## Implementation Example

```python
from agent_framework import BaseMessageStore, MessageStoreMemory
from agent_framework.constants import USER_MESSAGE, ASSISTANT_MESSAGE, TASK
from typing import List, Dict, Any, Optional

class DatabaseMessageStore(BaseMessageStore):
    """Example: Database-backed message store."""
    
    def __init__(self, db_connection):
        self.db = db_connection
    
    def get_conversation_messages(self, location: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get conversation messages (user_message, assistant_message)."""
        query = """
            SELECT type, content, timestamp, turn_id
            FROM messages
            WHERE location = ? AND type IN ('user_message', 'assistant_message')
            ORDER BY timestamp ASC
        """
        if limit:
            query += f" LIMIT {limit}"
        rows = self.db.execute(query, (location,)).fetchall()
        return [dict(row) for row in rows]
    
    def get_agent_messages(self, location: str, agent_key: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get execution traces for a specific agent."""
        query = """
            SELECT type, content, timestamp, turn_id, tool, args
            FROM messages
            WHERE location = ? AND agent_key = ?
              AND type IN ('task', 'action', 'observation', 'error', 'final', 'delegation')
            ORDER BY timestamp ASC
        """
        if limit:
            query += f" LIMIT {limit}"
        rows = self.db.execute(query, (location, agent_key)).fetchall()
        return [dict(row) for row in rows]
    
    def get_global_messages(self, location: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get global/broadcast messages."""
        query = """
            SELECT type, content, timestamp, turn_id, from_worker, from_manager, summary
            FROM messages
            WHERE location = ? AND type IN ('global_observation', 'synthesis')
            ORDER BY timestamp ASC
        """
        if limit:
            query += f" LIMIT {limit}"
        rows = self.db.execute(query, (location,)).fetchall()
        return [dict(row) for row in rows]
    
    def get_team_messages(self, location: str, agent_keys: List[str], limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get messages from multiple agents."""
        placeholders = ','.join(['?'] * len(agent_keys))
        query = f"""
            SELECT type, content, timestamp, turn_id, agent_key
            FROM messages
            WHERE location = ? AND agent_key IN ({placeholders})
            ORDER BY timestamp ASC
        """
        if limit:
            query += f" LIMIT {limit}"
        rows = self.db.execute(query, (location, *agent_keys)).fetchall()
        return [dict(row) for row in rows]

# Usage in implementation:
message_store = DatabaseMessageStore(db_connection)
location = "job_123"  # Your location identifier

memory = MessageStoreMemory(
    message_store=message_store,
    location=location,
    agent_key="orchestrator"
)

# Framework will read messages from the store via memory.get_history()
from agent_framework import ManagerAgent

agent = ManagerAgent(
    planner=planner,
    memory=memory,  # Framework reads from your store
    workers=workers,
    policies=policies
)
```

## Message Type Constants

All type constants are available in `agent_framework.constants`:

```python
from agent_framework.constants import (
    # Conversation types
    USER_MESSAGE,          # "user_message"
    ASSISTANT_MESSAGE,     # "assistant_message"
    
    # Execution trace types
    TASK,                  # "task"
    ACTION,                # "action"
    OBSERVATION,           # "observation"
    ERROR,                 # "error"
    
    # Completion types
    FINAL,                 # "final"
    SYNTHESIS,             # "synthesis"
    
    # Planning types
    STRATEGIC_PLAN,        # "strategic_plan"
    SUGGESTED_PLAN,        # "suggested_plan"
    SCRIPT_PLAN,           # "script_plan"
    
    # Delegation types
    DELEGATION,            # "delegation"
    
    # Global types
    GLOBAL_OBSERVATION,    # "global_observation"
    
    # Context types
    DIRECTOR_CONTEXT,      # "director_context"
    INJECTED_CONTEXT,      # "injected_context"
)
```

## Message Builder Utilities

The framework provides utilities to create properly formatted messages. It's recommended to use these instead of manually constructing message dictionaries:

```python
from agent_framework.utils.message_builder import (
    create_user_message,
    create_assistant_message,
    create_task_entry,
    create_action_entry,
    create_observation_entry,
    create_error_entry,
    create_final_entry,
    create_synthesis_entry,
    create_strategic_plan_entry,
    create_delegation_entry,
    create_global_observation_entry,
    create_director_context_entry,
)

# Example: Create a user message
user_msg = create_user_message(
    content="List all tables",
    timestamp=1234567890.0,
    turn_id="turn_1"
)

# Example: Create an action entry
action_msg = create_action_entry(
    tool_name="list_tables",
    tool_args={"schema": "public"},
    timestamp=1234567890.5,
    turn_id="turn_1"
)

# Example: Create a delegation entry
delegation_msg = create_delegation_entry(
    worker="powerbi-analysis",
    task="List all tables",
    timestamp=1234567890.5,
    turn_id="turn_1"
)
```

See the [Message Store Integration guide](message_store_integration.md) for more details on using message builder utilities.

## Implementation Checklist

1. ✅ Implement `BaseMessageStore` interface with all 4 required methods
2. ✅ Organize messages in your store (database, file, etc.)
3. ✅ Ensure messages have required fields for each type:
   - Most types: `type` and `content`
   - `action`: `type`, `tool`, `args`
   - `delegation`: `type`, `worker`, `task`
   - `synthesis`: `type`, `content`, `from_manager`
4. ✅ Use type constants from `agent_framework.constants` (don't use string literals)
5. ✅ Provide location reference when creating `MessageStoreMemory`
6. ✅ Test that `get_history()` returns messages in expected format

## Important Notes

### Field Requirements

- **`type` and `content`**: Required for most message types
- **`action` entries**: Use `tool` and `args` fields instead of `content`
- **`delegation` entries**: Use `worker` and `task` fields instead of `content`
- **`synthesis` entries**: Require `from_manager` in addition to `content`

### Ordering

Messages should be returned in chronological order (by timestamp or insertion order). This ensures the framework processes history in the correct sequence.

### Type Validation

Framework expects exact type strings from constants - don't use variations or custom types. Always import and use constants from `agent_framework.constants`.

### Missing Fields

Optional fields can be omitted, but required fields must be present. The framework may fail if required fields are missing.

### Location Format

Implementation determines what location represents (job_id, namespace, path, etc.). The framework only uses it as an identifier to query your store.

### Content Types

The `content` field can be any serializable type:
- Strings for simple messages
- Dictionaries for structured data (plans, observations, etc.)
- Lists for collections
- The framework handles serialization internally
