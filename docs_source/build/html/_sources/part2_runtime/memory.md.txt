# Memory & Message Stores

This chapter covers memory implementations and the message store pattern.

```{note}
Looking for preset-based configuration? See :doc:`memory-presets` for details on `$preset: standalone|worker|manager`.
```

## Async-Safe Memory

All memory implementations use **async methods** with `asyncio.Lock()` for proper async context isolation. This prevents race conditions when multiple coroutines access memory concurrently.

```{important}
**Breaking Change**: All memory methods are now async and must be awaited.
```

## BaseMemory Interface

All memory implementations inherit from `BaseMemory`:

```python
from agent_framework import BaseMemory

class BaseMemory(ABC):
    @abstractmethod
    async def add(self, message: Dict[str, Any]) -> None:
        """Add a message to history (async)."""
        pass

    @abstractmethod
    async def get_history(self) -> List[Dict[str, Any]]:
        """Retrieve all history (async)."""
        pass
```

## Memory Implementations

### InMemoryMemory

In-memory storage for single-agent development:

```python
from agent_framework.components.memory import InMemoryMemory

memory = InMemoryMemory()

# All memory operations must be awaited
await memory.add({"type": "user_message", "content": "Hello"})
history = await memory.get_history()
```

### SharedInMemoryMemory

Namespace-isolated shared memory for multi-agent systems:

```python
from agent_framework.components.memory import SharedInMemoryMemory

# Same namespace = shared context
memory1 = SharedInMemoryMemory(namespace="job_123", agent_key="worker_1")
memory2 = SharedInMemoryMemory(namespace="job_123", agent_key="worker_2")

# Worker 1 adds a message (async)
await memory1.add({"type": "observation", "content": "Found 5 tables"})

# Worker 2 can see it (same namespace)
history = await memory2.get_history()  # Contains the message from worker_1

# Broadcast to all agents in namespace
await memory1.add_global({"type": "global_observation", "content": "Shared update"})
```

### MessageStoreMemory

Reads from an external `BaseMessageStore` (database, API, etc.):

```python
from agent_framework import MessageStoreMemory, BaseMessageStore

class MyMessageStore(BaseMessageStore):
    def get_conversation_messages(self, location: str, limit: int = None):
        # Fetch from database
        return self.db.query(...)

    def get_agent_messages(self, location: str, agent_key: str, limit: int = None):
        # Fetch agent-specific messages
        return self.db.query(...)

    def get_global_messages(self, location: str, limit: int = None):
        # Fetch global/broadcast messages
        return self.db.query(...)

    def get_team_messages(self, location: str, agent_keys: list, limit: int = None):
        # Fetch messages from multiple agents
        return self.db.query(...)

# Create memory backed by store
store = MyMessageStore()
memory = MessageStoreMemory(
    message_store=store,
    location="job_123",
    agent_key="worker_1",
)

# Memory operations are async
history = await memory.get_history()
```

### HierarchicalMessageStoreMemory

For managers that need visibility into subordinate agents:

```python
from agent_framework import HierarchicalMessageStoreMemory

memory = HierarchicalMessageStoreMemory(
    message_store=store,
    location="job_123",
    agent_key="manager",
    subordinates=["worker_1", "worker_2", "worker_3"],
)

# get_history() returns (async):
# - Manager's own messages
# - All subordinates' messages
# - Global messages
history = await memory.get_history()
```

## Async-Safe SharedStateStore

The underlying `SharedStateStore` uses `asyncio.Lock()` for thread-safe async operations:

```python
import asyncio

class SharedStateStore:
    """Process-wide, async-safe store for hierarchical, namespaced agent memory."""

    def __init__(self) -> None:
        self._global_feeds = defaultdict(list)
        self._agent_feeds = defaultdict(lambda: defaultdict(list))
        self._conversation_feeds = defaultdict(list)
        self._lock = asyncio.Lock()  # Async-safe lock

    async def append_agent_msg(self, namespace: str, agent_key: str, msg: Dict) -> None:
        async with self._lock:
            self._agent_feeds[namespace][agent_key].append(dict(msg))

    async def list_agent_msgs(self, namespace: str, agent_key: str) -> List[Dict]:
        async with self._lock:
            return list(self._agent_feeds.get(namespace, {}).get(agent_key, []))
```

This prevents race conditions when multiple concurrent coroutines access the same namespace.

## Message Format

Messages follow a standard format (see `agent_framework.constants`):

### Conversation Types

```python
# User input
{"type": "user_message", "content": "List all tables", "timestamp": "..."}

# Assistant response
{"type": "assistant_message", "content": "Found 5 tables...", "timestamp": "..."}
```

### Execution Trace Types

```python
# Task assignment
{"type": "task", "content": "Analyze the model", "agent_key": "worker_1"}

# Tool call
{"type": "action", "tool": "list_tables", "args": {}, "agent_key": "worker_1"}

# Tool result
{"type": "observation", "content": {"tables": [...]}, "agent_key": "worker_1"}

# Error
{"type": "error", "content": {"error_message": "..."}, "agent_key": "worker_1"}
```

### Completion Types

```python
# Task complete
{"type": "final", "content": {"summary": "..."}, "agent_key": "worker_1"}

# Manager synthesis
{"type": "synthesis", "content": "Aggregated results...", "phase_id": 1}
```

### Planning Types

```python
# Strategic plan
{"type": "strategic_plan", "content": {"phases": [...]}}

# Suggested plan for worker
{"type": "suggested_plan", "content": {"steps": [...]}}

# Script instruction
{"type": "script_instruction", "content": {"step": "..."}}
```

## BaseMessageStore Interface

Implement this interface for custom storage:

```python
from agent_framework import BaseMessageStore
from typing import List, Dict, Any, Optional

class DatabaseMessageStore(BaseMessageStore):
    def __init__(self, db_connection):
        self.db = db_connection

    def get_conversation_messages(
        self,
        location: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get user_message and assistant_message entries."""
        query = """
            SELECT * FROM messages
            WHERE location = ? AND type IN ('user_message', 'assistant_message')
            ORDER BY timestamp
        """
        if limit:
            query += f" LIMIT {limit}"
        return self.db.execute(query, [location]).fetchall()

    def get_agent_messages(
        self,
        location: str,
        agent_key: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get execution traces for a specific agent."""
        query = """
            SELECT * FROM messages
            WHERE location = ? AND agent_key = ?
            ORDER BY timestamp
        """
        return self.db.execute(query, [location, agent_key]).fetchall()

    def get_global_messages(
        self,
        location: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get global/broadcast messages."""
        query = """
            SELECT * FROM messages
            WHERE location = ? AND is_global = TRUE
            ORDER BY timestamp
        """
        return self.db.execute(query, [location]).fetchall()

    def get_team_messages(
        self,
        location: str,
        agent_keys: List[str],
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get messages from multiple agents."""
        placeholders = ','.join(['?' for _ in agent_keys])
        query = f"""
            SELECT * FROM messages
            WHERE location = ? AND agent_key IN ({placeholders})
            ORDER BY timestamp
        """
        return self.db.execute(query, [location, *agent_keys]).fetchall()
```

## Message Builder Utilities

Use the message builder for consistent formatting:

```python
from agent_framework.utils.message_builder import (
    create_user_message,
    create_assistant_message,
    create_task_entry,
    create_observation,
    create_action,
    create_error,
    create_final,
)

# Create properly formatted messages
user_msg = create_user_message("List all tables")
task = create_task_entry("Analyze the model", agent_key="worker_1")
observation = create_observation({"tables": [...]}, agent_key="worker_1")
```

## Memory in YAML Configuration

Configure memory in agent YAML:

```yaml
# Simple memory
memory:
  type: InMemoryMemory

# Shared memory with namespace
memory:
  type: SharedInMemoryMemory
  config:
    namespace: ${JOB_ID}
    agent_key: worker_1

# Message store memory
memory:
  type: MessageStoreMemory
  config:
    location: ${JOB_ID}
    agent_key: worker_1
```

## Hierarchical Visibility

Different agent roles see different history:

| Role | Sees |
|------|------|
| **Worker** | Conversation + own traces + global |
| **Manager** | Own traces + all subordinates + global |
| **Orchestrator** | Conversation + own traces + global |

### History Filtering

The framework includes filters for each role:

```python
from agent_framework.policies.history_filters import (
    OrchestratorHistoryFilter,
    ManagerHistoryFilter,
    WorkerHistoryFilter,
)

# Orchestrator: conversation only
orch_filter = OrchestratorHistoryFilter(max_conversation_turns=10)

# Manager: synthesis from previous phases
manager_filter = ManagerHistoryFilter()

# Worker: current turn traces only
worker_filter = WorkerHistoryFilter()
```

## Migration Guide

If upgrading from a previous version, update all memory calls to use `await`:

```python
# Before (sync)
memory.add({"type": "task", "content": "..."})
history = memory.get_history()

# After (async)
await memory.add({"type": "task", "content": "..."})
history = await memory.get_history()
```

For custom memory implementations:

```python
# Before
class MyMemory(BaseMemory):
    def add(self, message):
        self.store.append(message)

    def get_history(self):
        return list(self.store)

# After
class MyMemory(BaseMemory):
    async def add(self, message):
        self.store.append(message)

    async def get_history(self):
        return list(self.store)
```

## Best Practices

1. **Always await memory operations** - `add()` and `get_history()` are async
2. **Use SharedInMemoryMemory** for multi-agent development
3. **Implement BaseMessageStore** for production persistence
4. **Use consistent namespaces** across agent hierarchy
5. **Include agent_key** in all execution trace messages
6. **Use message builder** for consistent formatting
7. **Configure HierarchicalMessageStoreMemory** for managers

## Complete Example

```python
import asyncio
from agent_framework import Agent, MessageStoreMemory, BaseMessageStore, get_preset
from agent_framework.components.planners import ReActPlanner
from agent_framework.gateways.inference import OpenAIGateway
from agent_framework.decorators import tool

# Custom message store
class InMemoryMessageStore(BaseMessageStore):
    def __init__(self):
        self.messages = {}

    def _get_location(self, location: str):
        if location not in self.messages:
            self.messages[location] = []
        return self.messages[location]

    def append(self, location: str, message: dict):
        self._get_location(location).append(message)

    def get_conversation_messages(self, location, limit=None):
        msgs = [m for m in self._get_location(location)
                if m.get("type") in ("user_message", "assistant_message")]
        return msgs[-limit:] if limit else msgs

    def get_agent_messages(self, location, agent_key, limit=None):
        msgs = [m for m in self._get_location(location)
                if m.get("agent_key") == agent_key]
        return msgs[-limit:] if limit else msgs

    def get_global_messages(self, location, limit=None):
        msgs = [m for m in self._get_location(location)
                if m.get("is_global")]
        return msgs[-limit:] if limit else msgs

    def get_team_messages(self, location, agent_keys, limit=None):
        msgs = [m for m in self._get_location(location)
                if m.get("agent_key") in agent_keys]
        return msgs[-limit:] if limit else msgs

# Create store and memory
store = InMemoryMessageStore()
memory = MessageStoreMemory(
    message_store=store,
    location="job_123",
    agent_key="worker_1",
)

# Create agent
@tool
def greet(name: str) -> str:
    return f"Hello, {name}!"

agent = Agent(
    name="greeter",
    planner=ReActPlanner(
        inference_gateway=OpenAIGateway(),
        tools=[greet],
    ),
    memory=memory,
    tools=[greet],
    policies=get_preset("simple"),
)

# Run (agent.run is already async)
async def main():
    result = await agent.run("Greet Alice")
    print(result)

asyncio.run(main())
```
