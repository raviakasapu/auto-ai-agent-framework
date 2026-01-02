# Message Stores & Integrations

This chapter consolidates message store integration patterns.

## Overview

The message store pattern separates message persistence from the framework:

1. **Implementation** manages storage (database, file, etc.)
2. **Framework** reads via `BaseMessageStore` interface
3. **Memory** wraps the store for agent use

## Architecture

```
┌──────────────────────┐
│   Your Application   │
│  (manages storage)   │
└──────────┬───────────┘
           │ implements
           ▼
┌──────────────────────┐
│   BaseMessageStore   │
│   (abstract API)     │
└──────────┬───────────┘
           │ used by
           ▼
┌──────────────────────┐
│  MessageStoreMemory  │
│  (framework memory)  │
└──────────┬───────────┘
           │ passed to
           ▼
┌──────────────────────┐
│        Agent         │
└──────────────────────┘
```

## Implementing BaseMessageStore

```python
from agent_framework import BaseMessageStore
from typing import List, Dict, Any, Optional

class SQLMessageStore(BaseMessageStore):
    def __init__(self, connection):
        self.conn = connection
    
    def get_conversation_messages(
        self, location: str, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        query = """
            SELECT type, content, timestamp, metadata
            FROM messages
            WHERE location = ? AND type IN ('user_message', 'assistant_message')
            ORDER BY timestamp
        """
        if limit:
            query += f" LIMIT {limit}"
        
        rows = self.conn.execute(query, [location]).fetchall()
        return [dict(row) for row in rows]
    
    def get_agent_messages(
        self, location: str, agent_key: str, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        query = """
            SELECT type, content, timestamp, metadata
            FROM messages
            WHERE location = ? AND agent_key = ?
            ORDER BY timestamp
        """
        rows = self.conn.execute(query, [location, agent_key]).fetchall()
        return [dict(row) for row in rows]
    
    def get_global_messages(
        self, location: str, limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        query = """
            SELECT type, content, timestamp, metadata
            FROM messages
            WHERE location = ? AND is_global = TRUE
            ORDER BY timestamp
        """
        rows = self.conn.execute(query, [location]).fetchall()
        return [dict(row) for row in rows]
    
    def get_team_messages(
        self, location: str, agent_keys: List[str], limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        placeholders = ','.join(['?' for _ in agent_keys])
        query = f"""
            SELECT type, content, timestamp, metadata
            FROM messages
            WHERE location = ? AND agent_key IN ({placeholders})
            ORDER BY timestamp
        """
        rows = self.conn.execute(query, [location, *agent_keys]).fetchall()
        return [dict(row) for row in rows]
```

## Using MessageStoreMemory

```python
from agent_framework import MessageStoreMemory, Agent, get_preset
from agent_framework.components.planners import ReActPlanner
from agent_framework.gateways.inference import OpenAIGateway

# Create store
store = SQLMessageStore(db_connection)

# Create memory backed by store
memory = MessageStoreMemory(
    message_store=store,
    location="job_123",      # Job/request identifier
    agent_key="worker_1",    # This agent's identifier
)

# Create agent
agent = Agent(
    name="worker_1",
    planner=ReActPlanner(inference_gateway=OpenAIGateway(), tools=my_tools),
    memory=memory,
    tools=my_tools,
    policies=get_preset("simple"),
)

result = await agent.run("Process data")
```

## HierarchicalMessageStoreMemory

For managers that need subordinate visibility:

```python
from agent_framework import HierarchicalMessageStoreMemory

memory = HierarchicalMessageStoreMemory(
    message_store=store,
    location="job_123",
    agent_key="manager",
    subordinates=["worker_1", "worker_2", "worker_3"],
)

# get_history() returns:
# - Manager's own messages
# - All subordinates' messages  
# - Global messages
```

## Message Format Specification

All messages must include:

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Message type constant |
| `content` | any | Message content |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | string | ISO timestamp |
| `agent_key` | string | Agent identifier |
| `metadata` | dict | Additional metadata |
| `is_global` | bool | Broadcast to all agents |
| `phase_id` | int | Phase identifier |

### Type Constants

```python
from agent_framework.constants import (
    USER_MESSAGE,      # "user_message"
    ASSISTANT_MESSAGE, # "assistant_message"
    TASK,              # "task"
    ACTION,            # "action"
    OBSERVATION,       # "observation"
    ERROR,             # "error"
    FINAL,             # "final"
    SYNTHESIS,         # "synthesis"
    STRATEGIC_PLAN,    # "strategic_plan"
)
```

## Message Builder Utilities

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

# Create messages
user_msg = create_user_message("Hello", metadata={"user_id": "123"})
# {"type": "user_message", "content": "Hello", "metadata": {...}}

task = create_task_entry("Analyze data", agent_key="worker_1")
# {"type": "task", "content": "Analyze data", "agent_key": "worker_1"}

obs = create_observation({"result": "success"}, agent_key="worker_1")
# {"type": "observation", "content": {"result": "success"}, "agent_key": "worker_1"}
```

## Complete Integration Example

```python
import asyncio
from agent_framework import (
    Agent, ManagerAgent, EventBus,
    MessageStoreMemory, HierarchicalMessageStoreMemory,
    get_preset,
)
from agent_framework.components.planners import StrategicPlanner, ReActPlanner
from agent_framework.gateways.inference import OpenAIGateway
from agent_framework.decorators import tool

# Your message store implementation
class InMemoryStore:
    def __init__(self):
        self.messages = {}
    
    def _loc(self, location):
        if location not in self.messages:
            self.messages[location] = []
        return self.messages[location]
    
    def append(self, location: str, message: dict):
        self._loc(location).append(message)
    
    def get_conversation_messages(self, location, limit=None):
        return [m for m in self._loc(location) 
                if m.get("type") in ("user_message", "assistant_message")]
    
    def get_agent_messages(self, location, agent_key, limit=None):
        return [m for m in self._loc(location) 
                if m.get("agent_key") == agent_key]
    
    def get_global_messages(self, location, limit=None):
        return [m for m in self._loc(location) 
                if m.get("is_global")]
    
    def get_team_messages(self, location, agent_keys, limit=None):
        return [m for m in self._loc(location) 
                if m.get("agent_key") in agent_keys]

# Setup
store = InMemoryStore()
event_bus = EventBus()
job_id = "job_123"

# Add initial user message
store.append(job_id, {
    "type": "user_message",
    "content": "Analyze the data model",
})

# Create worker with MessageStoreMemory
@tool
def analyze(data: str) -> dict:
    return {"analysis": "complete", "items": 5}

worker = Agent(
    name="analyzer",
    planner=ReActPlanner(
        inference_gateway=OpenAIGateway(model="gpt-4o-mini"),
        tools=[analyze],
    ),
    memory=MessageStoreMemory(
        message_store=store,
        location=job_id,
        agent_key="analyzer",
    ),
    tools=[analyze],
    policies=get_preset("simple"),
    event_bus=event_bus,
)

# Create manager with HierarchicalMessageStoreMemory
manager = ManagerAgent(
    name="manager",
    planner=StrategicPlanner(
        worker_keys=["analyzer"],
        inference_gateway=OpenAIGateway(model="gpt-4o"),
    ),
    memory=HierarchicalMessageStoreMemory(
        message_store=store,
        location=job_id,
        agent_key="manager",
        subordinates=["analyzer"],
    ),
    workers={"analyzer": worker},
    event_bus=event_bus,
)

# Run
async def main():
    result = await manager.run("Analyze the data model")
    
    # Add assistant response to store
    store.append(job_id, {
        "type": "assistant_message",
        "content": result.get("human_readable_summary", str(result)),
    })
    
    print(result)

asyncio.run(main())
```

## Best Practices

1. **Implement all interface methods** — Framework may call any method
2. **Return chronological order** — Messages should be time-ordered
3. **Use agent_key consistently** — Same key for memory and messages
4. **Store metadata** — Useful for filtering and debugging
5. **Handle empty results** — Return empty lists, not None
6. **Use message builder** — Ensures correct format

