---
title: Message Store Implementation Guide
---

# Message Store Implementation Guide

## Overview

Implementations create message stores in their preferred format (database, file system, etc.) and the framework reads messages directly from the store. This separates storage concerns from framework logic.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  IMPLEMENTATION LAYER                                       │
│                                                             │
│  ┌──────────────┐    ┌──────────────────┐                 │
│  │ Your Store   │───▶│ BaseMessageStore │                 │
│  │ (DB/File/...)│    │ Implementation   │                 │
│  └──────────────┘    └──────────────────┘                 │
│         │                      │                            │
│         │                      │ location reference         │
│         │                      ▼                            │
│         │            ┌──────────────────────┐              │
│         │            │ MessageStoreMemory   │              │
│         │            │ (Framework)          │              │
│         │            └──────────────────────┘              │
│         │                      │                            │
│         └──────────────────────┼──────────────────────────┘
│                                │                            │
└────────────────────────────────┼────────────────────────────┘
                                 ▼
┌─────────────────────────────────────────────────────────────┐
│  FRAMEWORK LAYER                                            │
│                                                             │
│  ┌──────────────────────┐                                  │
│  │ ManagerAgent/Agent   │                                  │
│  │ memory.get_history() │───▶ Reads from MessageStore     │
│  └──────────────────────┘                                  │
└─────────────────────────────────────────────────────────────┘
```

## Step 1: Import Required Framework Classes

All necessary classes are exported from the framework's main package:

```python
from agent_framework import (
    # Base interface you'll implement
    BaseMessageStore,
    
    # Memory implementations
    MessageStoreMemory,
    HierarchicalMessageStoreMemory,
    
    # Agents you'll use
    ManagerAgent,
    Agent,
)

# Message builder utilities
from agent_framework.utils.message_builder import (
    create_user_message,
    create_assistant_message,
)

# Constants (optional, but recommended)
from agent_framework.constants import (
    USER_MESSAGE,
    ASSISTANT_MESSAGE,
    TASK,
    ACTION,
    OBSERVATION,
)
```

## Step 2: Implement BaseMessageStore

You must implement all four methods of the `BaseMessageStore` interface. The framework will call these methods via `MessageStoreMemory.get_history()`.

```python
from agent_framework import BaseMessageStore
from typing import List, Dict, Any, Optional
import sqlite3
import json

class DatabaseMessageStore(BaseMessageStore):
    """Example implementation: SQLite-backed message store."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Create tables for storing messages."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                location TEXT NOT NULL,
                agent_key TEXT,
                type TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp REAL,
                turn_id TEXT,
                tool TEXT,
                args TEXT,
                from_worker TEXT,
                from_manager TEXT,
                summary TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_location_type ON messages(location, type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_location_agent ON messages(location, agent_key)")
        conn.commit()
        conn.close()
    
    def get_conversation_messages(
        self,
        location: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get conversation messages (user_message, assistant_message).
        
        This is called by MessageStoreMemory.get_history() to retrieve
        conversation-level messages.
        
        Args:
            location: Your location identifier (e.g., job_id, namespace)
            limit: Optional limit (not currently used by framework, but provided for future use)
            
        Returns:
            List of message dicts with type in ["user_message", "assistant_message"]
            Must be ordered chronologically.
        """
        conn = sqlite3.connect(self.db_path)
        query = """
            SELECT type, content, timestamp, turn_id
            FROM messages
            WHERE location = ? AND type IN ('user_message', 'assistant_message')
            ORDER BY timestamp ASC
        """
        if limit:
            query += f" LIMIT {limit}"
        rows = conn.execute(query, (location,)).fetchall()
        conn.close()
        
        return [
            {
                "type": row[0],
                "content": json.loads(row[1]) if isinstance(row[1], str) else row[1],
                "timestamp": row[2],
                "turn_id": row[3]
            }
            for row in rows
        ]
    
    def get_agent_messages(
        self,
        location: str,
        agent_key: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get execution trace messages for a specific agent.
        
        This is called by MessageStoreMemory.get_history() to retrieve
        execution traces (task, action, observation, etc.) for the specified agent.
        
        Args:
            location: Your location identifier
            agent_key: The agent identifier (e.g., "orchestrator", "worker-1")
            limit: Optional limit (not currently used by framework)
            
        Returns:
            List of message dicts with type in execution trace types
            (task, action, observation, error, final, delegation)
            Must be ordered chronologically.
        """
        conn = sqlite3.connect(self.db_path)
        query = """
            SELECT type, content, timestamp, turn_id, tool, args
            FROM messages
            WHERE location = ? AND agent_key = ?
              AND type IN ('task', 'action', 'observation', 'error', 'final', 'delegation')
            ORDER BY timestamp ASC
        """
        if limit:
            query += f" LIMIT {limit}"
        rows = conn.execute(query, (location, agent_key)).fetchall()
        conn.close()
        
        return [
            {
                "type": row[0],
                "content": json.loads(row[1]) if isinstance(row[1], str) else row[1],
                "timestamp": row[2],
                "turn_id": row[3],
                "tool": row[4],
                "args": json.loads(row[5]) if row[5] else None
            }
            for row in rows
        ]
    
    def get_global_messages(
        self,
        location: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get global/broadcast messages (global_observation, synthesis).
        
        This is called by MessageStoreMemory.get_history() to retrieve
        global messages that are visible to all agents.
        
        Args:
            location: Your location identifier
            limit: Optional limit (not currently used by framework)
            
        Returns:
            List of message dicts with type in ["global_observation", "synthesis"]
            Must be ordered chronologically.
        """
        conn = sqlite3.connect(self.db_path)
        query = """
            SELECT type, content, timestamp, turn_id, from_worker, from_manager, summary
            FROM messages
            WHERE location = ? AND type IN ('global_observation', 'synthesis')
            ORDER BY timestamp ASC
        """
        if limit:
            query += f" LIMIT {limit}"
        rows = conn.execute(query, (location,)).fetchall()
        conn.close()
        
        return [
            {
                "type": row[0],
                "content": json.loads(row[1]) if isinstance(row[1], str) else row[1],
                "timestamp": row[2],
                "turn_id": row[3],
                "from_worker": row[4],
                "from_manager": row[5],
                "summary": row[6]
            }
            for row in rows
        ]
    
    def get_team_messages(
        self,
        location: str,
        agent_keys: List[str],
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get messages from multiple agents (for managers viewing subordinates).
        
        This is called by HierarchicalMessageStoreMemory.get_history() to retrieve
        messages from subordinate agents.
        
        Args:
            location: Your location identifier
            agent_keys: List of agent identifiers to retrieve messages from
            limit: Optional limit (not currently used by framework)
            
        Returns:
            List of message dicts from all specified agents
            Must be ordered chronologically.
        """
        if not agent_keys:
            return []
            
        conn = sqlite3.connect(self.db_path)
        placeholders = ','.join(['?'] * len(agent_keys))
        query = f"""
            SELECT type, content, timestamp, turn_id, agent_key
            FROM messages
            WHERE location = ? AND agent_key IN ({placeholders})
            ORDER BY timestamp ASC
        """
        if limit:
            query += f" LIMIT {limit}"
        rows = conn.execute(query, (location, *agent_keys)).fetchall()
        conn.close()
        
        return [
            {
                "type": row[0],
                "content": json.loads(row[1]) if isinstance(row[1], str) else row[1],
                "timestamp": row[2],
                "turn_id": row[3],
                "agent_key": row[4]
            }
            for row in rows
        ]
    
    # Helper method (NOT part of BaseMessageStore interface)
    def write_message(self, location: str, message: Dict[str, Any], agent_key: Optional[str] = None):
        """Helper method to write messages to your store.
        
        This is NOT part of the BaseMessageStore interface - it's just a convenience
        method for your implementation to use when storing messages.
        """
        conn = sqlite3.connect(self.db_path)
        content_value = json.dumps(message.get("content")) if not isinstance(message.get("content"), str) else message.get("content")
        conn.execute("""
            INSERT INTO messages 
            (location, agent_key, type, content, timestamp, turn_id, tool, args, from_worker, from_manager, summary)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            location,
            agent_key or message.get("agent_key"),
            message.get("type"),
            content_value,
            message.get("timestamp"),
            message.get("turn_id"),
            message.get("tool"),
            json.dumps(message.get("args")) if message.get("args") else None,
            message.get("from_worker"),
            message.get("from_manager"),
            message.get("summary")
        ))
        conn.commit()
        conn.close()
```

## Step 3: How MessageStoreMemory Reads from Your Store

The framework's `MessageStoreMemory.get_history()` method calls your store methods in this order:

1. **`get_conversation_messages(location)`** - Retrieves user_message and assistant_message entries
2. **`get_agent_messages(location, agent_key)`** - Retrieves execution traces for the specific agent
3. **`get_global_messages(location)`** - Retrieves global_observation and synthesis entries

The messages are combined in this order and returned to the framework. **Important**: Your methods should return messages in chronological order (by timestamp or insertion order).

For `HierarchicalMessageStoreMemory`, the order is:
1. Conversation messages
2. Manager's own agent messages
3. Subordinate team messages (via `get_team_messages`)
4. Global messages

## Step 4: Use MessageStoreMemory with Agents

Create memory that reads from your store and pass it to agents:

```python
from agent_framework import ManagerAgent, MessageStoreMemory
from agent_framework.components.planners import StrategicPlanner
from agent_framework.gateways.inference import OpenAIGateway
from agent_framework.policies.presets import get_preset

# Create your message store implementation
message_store = DatabaseMessageStore("messages.db")

# Create memory that reads from your store
location = "job_123"  # Your location identifier
memory = MessageStoreMemory(
    message_store=message_store,
    location=location,
    agent_key="orchestrator"  # The agent key for this memory instance
)

# Create planner and other components
llm_gateway = OpenAIGateway(model="gpt-4o", api_key="...")
planner = StrategicPlanner(
    inference_gateway=llm_gateway,
    system_prompt="You are an orchestrator...",
)

# Create agent with policies
policies = get_preset("manager")

# Create manager agent - framework will read from your store
agent = ManagerAgent(
    planner=planner,
    memory=memory,  # Framework reads via memory.get_history()
    workers={...},
    policies=policies
)

# Run agent - framework reads messages from your store automatically
result = await agent.run(
    task="List all tables in the model",
    progress_handler=progress_handler
)
```

## Step 5: Writing Messages to Your Store

The framework reads from the store, but **does not write**. You are responsible for writing messages to your store. Use message builder utilities to create properly formatted messages:

```python
from agent_framework.utils.message_builder import (
    create_user_message,
    create_assistant_message,
)
import time

# When user sends message
user_msg = create_user_message(
    content=user_input,
    timestamp=time.time(),
    turn_id=f"turn_{turn_number}"
)
message_store.write_message(location="job_123", message=user_msg)

# When assistant completes (after agent.run() returns)
summary = result.get("human_readable_summary") or str(result)
assistant_msg = create_assistant_message(
    content=summary,
    timestamp=time.time(),
    turn_id=f"turn_{turn_number}"
)
message_store.write_message(location="job_123", message=assistant_msg)
```

**Note**: The `write_message()` method shown above is a helper method for your implementation - it's not part of the `BaseMessageStore` interface. You can implement message storage however you prefer.

## Complete Example: API Endpoint Integration

Here's a complete example showing how to integrate message store in a FastAPI endpoint:

```python
from fastapi import FastAPI
from agent_framework import (
    ManagerAgent,
    MessageStoreMemory,
    BaseMessageStore,
)
from agent_framework.components.planners import StrategicPlanner
from agent_framework.gateways.inference import OpenAIGateway
from agent_framework.policies.presets import get_preset
from agent_framework.utils.message_builder import (
    create_user_message,
    create_assistant_message,
)
import time

app = FastAPI()

# Initialize your message store
message_store = DatabaseMessageStore("messages.db")

@app.post("/run")
async def run_agent(request: RunRequest):
    job_id = request.job_id
    
    # 1. PREPARE: Store user message in your store
    user_msg = create_user_message(
        content=request.task,
        timestamp=time.time(),
        turn_id=f"turn_{int(time.time())}"
    )
    message_store.write_message(job_id, user_msg)
    
    # 2. CREATE: Memory that reads from your store
    memory = MessageStoreMemory(
        message_store=message_store,
        location=job_id,
        agent_key="orchestrator"
    )
    
    # 3. CREATE: Agent (framework will read from your store)
    llm_gateway = OpenAIGateway(model="gpt-4o", api_key="...")
    planner = StrategicPlanner(
        inference_gateway=llm_gateway,
        system_prompt="You are an orchestrator...",
    )
    agent = ManagerAgent(
        planner=planner,
        memory=memory,  # Framework reads via memory.get_history()
        workers={...},
        policies=get_preset("manager")
    )
    
    # 4. RUN: Framework handles everything else
    # - Reads messages from your store via memory.get_history()
    # - Creates runtime messages internally (task, action, observation, etc.)
    # - Processes task and returns result
    result = await agent.run(task=request.task, progress_handler=handler)
    
    # 5. STORE: Save assistant response
    assistant_msg = create_assistant_message(
        content=result.get("human_readable_summary") or str(result),
        timestamp=time.time(),
        turn_id=f"turn_{int(time.time())}"
    )
    message_store.write_message(job_id, assistant_msg)
    
    return result
```

## Hierarchical Memory for Managers

For managers that need to see subordinate agent messages, use `HierarchicalMessageStoreMemory`:

```python
from agent_framework import HierarchicalMessageStoreMemory

# Create hierarchical memory for a manager
memory = HierarchicalMessageStoreMemory(
    message_store=message_store,
    location=job_id,
    agent_key="manager-1",
    subordinates=["worker-1", "worker-2"]  # Manager can see these workers' messages
)

agent = ManagerAgent(
    planner=planner,
    memory=memory,
    workers={...},
    policies=policies
)
```

When using `HierarchicalMessageStoreMemory`, your `get_team_messages()` method will be called with the list of subordinate agent keys.

## Runtime Messages

**Important**: The framework will call `memory.add()` during execution, but `MessageStoreMemory.add()` is a **no-op** (does nothing). The framework reads messages via `get_history()`, which calls your store methods.

If you need runtime message storage (messages created during agent execution), you have several options:

1. **Option A**: Store them yourself when framework calls `memory.add()`
   - Override or wrap `MessageStoreMemory` to intercept `add()` calls
   - Write messages to your store when the framework calls `add()`

2. **Option B**: Use `SharedInMemoryMemory` for runtime messages
   - Use `MessageStoreMemory` for initial history (conversation messages)
   - Use `SharedInMemoryMemory` for runtime messages created during execution
   - Combine both when reading history

3. **Option C**: Hybrid approach
   - Read from store for initial history
   - Use in-memory storage for runtime messages
   - Your implementation manages combining both sources

For most use cases, Option A or B is recommended. The framework's runtime messages (task, action, observation, etc.) are typically ephemeral and don't need persistence unless you have specific requirements.

## Key Points

1. **Framework reads, you write**: Framework only reads via `get_history()` → calls your store methods. You write messages to your store.

2. **Location is yours**: You decide what location represents (job_id, namespace, path, etc.). The framework only uses it as an identifier.

3. **Format must match**: Messages must have `type` and `content` fields (or type-specific fields like `tool`/`args` for action entries) matching framework constants. See the [Message Store Format](message_store_format.md) guide.

4. **Interface contract**: Implement all 4 methods of `BaseMessageStore`. The framework will call them in a specific order via `get_history()`.

5. **Organize freely**: Your store structure is your choice - framework only sees the interface you provide. Use any storage backend (SQLite, PostgreSQL, files, etc.).

6. **Chronological ordering**: Messages must be returned in chronological order (by timestamp or insertion order).

7. **Agent key matters**: Each `MessageStoreMemory` instance is associated with an `agent_key`. Your `get_agent_messages()` method filters by this key.

## Implementation Checklist

- [ ] Implement all 4 methods of `BaseMessageStore`
- [ ] Ensure messages are returned in chronological order
- [ ] Use type constants from `agent_framework.constants` (don't use string literals)
- [ ] Test that `get_history()` returns messages in expected format
- [ ] Handle JSON serialization/deserialization if storing structured content
- [ ] Implement helper methods for writing messages (not part of interface, but useful)
- [ ] Test with actual `ManagerAgent` or `Agent` instances

## See Also

- [Message Store Integration](message_store_integration.md) - High-level integration guide
- [Message Store Format](message_store_format.md) - Complete message format specification
- `agent_framework.constants` - All message type constants
- `agent_framework.utils.message_builder` - Utilities for creating properly formatted messages
