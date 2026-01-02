---
title: Message Store Integration
---

# Message Store Integration

## Overview

The framework reads messages directly from message stores prepared by implementations. The implementation:

1. **Creates and manages the message store** (database, file, etc.)
2. **Implements `BaseMessageStore` interface** to provide message access
3. **Passes a location reference** to the framework
4. **Framework reads messages** from the store automatically

This separates storage concerns from framework logic, allowing implementations to use their preferred storage backend (SQLite, PostgreSQL, files, etc.).

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

All necessary classes are exported from the framework:

```python
# Core framework imports
from agent_framework import (
    # Base interfaces you'll implement
    BaseMessageStore,
    BaseJobStore,
    
    # Agents you'll use
    ManagerAgent,
    Agent,
    
    # Memory implementations
    MessageStoreMemory,
    HierarchicalMessageStoreMemory,
    
    # Types and utilities
    Action,
    FinalResponse,
)

# Message type constants
from agent_framework.constants import (
    USER_MESSAGE,
    ASSISTANT_MESSAGE,
    TASK,
    ACTION,
    OBSERVATION,
    ERROR,
    FINAL,
    SYNTHESIS,
    STRATEGIC_PLAN,
    DELEGATION,
    GLOBAL_OBSERVATION,
)

# Message builder utilities
from agent_framework.utils.message_builder import (
    create_user_message,
    create_assistant_message,
    create_task_entry,
    create_action_entry,
    create_observation_entry,
    create_final_entry,
    AVAILABLE_MESSAGE_TYPES,
    get_message_type_info,
)

# For creating agents
from agent_framework.components.planners import StrategicPlanner, ReActPlanner
from agent_framework.gateways.inference import OpenAIGateway
from agent_framework.policies.presets import get_preset
```

## Step 2: Implement BaseMessageStore

Create your message store implementation. The framework requires you to implement four methods:

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
    
    def get_conversation_messages(self, location: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get conversation messages (user_message, assistant_message).
        
        Args:
            location: Location reference (e.g., job_id, namespace, or store path)
            limit: Optional limit on number of messages to return
            
        Returns:
            List of message dicts in framework format, ordered chronologically
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
                "content": row[1],
                "timestamp": row[2],
                "turn_id": row[3]
            }
            for row in rows
        ]
    
    def get_agent_messages(self, location: str, agent_key: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get execution trace messages for a specific agent.
        
        Args:
            location: Location reference (e.g., job_id, namespace, or store path)
            agent_key: Identifier for the agent (e.g., "orchestrator", "worker-1")
            limit: Optional limit on number of messages to return
            
        Returns:
            List of message dicts in framework format (task, action, observation, etc.)
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
                "content": row[1],
                "timestamp": row[2],
                "turn_id": row[3],
                "tool": row[4],
                "args": json.loads(row[5]) if row[5] else None
            }
            for row in rows
        ]
    
    def get_global_messages(self, location: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get global/broadcast messages (global_observation, synthesis, etc.).
        
        Args:
            location: Location reference (e.g., job_id, namespace, or store path)
            limit: Optional limit on number of messages to return
            
        Returns:
            List of global message dicts in framework format
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
                "content": row[1],
                "timestamp": row[2],
                "turn_id": row[3],
                "from_worker": row[4],
                "from_manager": row[5],
                "summary": row[6]
            }
            for row in rows
        ]
    
    def get_team_messages(self, location: str, agent_keys: List[str], limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get messages from multiple agents (for managers viewing subordinates).
        
        Args:
            location: Location reference (e.g., job_id, namespace, or store path)
            agent_keys: List of agent identifiers
            limit: Optional limit on number of messages to return per agent
            
        Returns:
            List of message dicts from the specified agents
        """
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
                "content": row[1],
                "timestamp": row[2],
                "turn_id": row[3],
                "agent_key": row[4]
            }
            for row in rows
        ]
    
    def write_message(self, location: str, message: Dict[str, Any], agent_key: Optional[str] = None):
        """Helper method to write messages to your store (not part of BaseMessageStore interface)."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO messages 
            (location, agent_key, type, content, timestamp, turn_id, tool, args, from_worker, from_manager, summary)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            location,
            agent_key or message.get("agent_key"),
            message.get("type"),
            json.dumps(message.get("content")),
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

## Step 3: Discover Available Message Types

The framework provides utilities to discover available message types and their formats.

### Option 1: Use Message Builder Functions (Recommended)

```python
from agent_framework.utils.message_builder import (
    create_user_message,
    create_assistant_message,
    create_task_entry,
    # ... all available functions are exported
)

# List all available message types
from agent_framework.utils.message_builder import AVAILABLE_MESSAGE_TYPES

for msg_type, info in AVAILABLE_MESSAGE_TYPES.items():
    print(f"{msg_type}: {info['description']}")
    print(f"  Required fields: {info['required_fields']}")
    print(f"  Optional fields: {info['optional_fields']}")
    print(f"  Builder function: {info['builder'].__name__}")
```

### Option 2: Use Type Constants

```python
from agent_framework.constants import (
    USER_MESSAGE,
    ASSISTANT_MESSAGE,
    TASK,
    ACTION,
    OBSERVATION,
    # ... all constants are available
)

# Use constants when manually creating messages
message = {
    "type": USER_MESSAGE,
    "content": "List tables",
    "timestamp": time.time()
}
```

### Option 3: Get Type Information Programmatically

```python
from agent_framework.utils.message_builder import get_message_type_info

info = get_message_type_info("user_message")
if info:
    builder = info["builder"]
    msg = builder(content="Hello")
```

## Step 4: Prepare Messages Using Message Builders

Use message builder utilities to create properly formatted messages:

```python
from agent_framework.utils.message_builder import (
    create_user_message,
    create_assistant_message,
)
import time

# Store user message
user_msg = create_user_message(
    content="List all tables in the model",
    timestamp=time.time(),
    turn_id=f"turn_{int(time.time())}"
)
message_store.write_message(job_id, user_msg)

# Store assistant response after agent completes
summary = result.get("human_readable_summary") or str(result)
assistant_msg = create_assistant_message(
    content=summary,
    timestamp=time.time(),
    turn_id=f"turn_{int(time.time())}"
)
message_store.write_message(job_id, assistant_msg)
```

## Step 5: Pass Store to Framework

Create memory that reads from your store and use it with agents:

```python
from agent_framework import ManagerAgent, MessageStoreMemory
from agent_framework.components.planners import StrategicPlanner
from agent_framework.gateways.inference import OpenAIGateway
from agent_framework.policies.presets import get_preset

# Create your message store
message_store = DatabaseMessageStore("messages.db")

# Create memory that reads from your store
location = "job_123"  # Your location identifier
memory = MessageStoreMemory(
    message_store=message_store,
    location=location,
    agent_key="orchestrator"
)

# Create planner
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
    memory=memory,  # Framework reads messages from your store via get_history()
    workers={...},
    policies=policies
)

# Run agent - framework handles everything else
result = await agent.run(
    task="List all tables in the model",
    progress_handler=progress_handler
)
```

## Complete Flow Example

Here's a complete example showing the full integration:

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

## Framework Responsibilities

The framework automatically creates runtime messages during execution:

- **Task entries** (`TASK`) - When `agent.run()` is called
- **Action entries** (`ACTION`) - When tools are invoked
- **Observation entries** (`OBSERVATION`) - When tools return results
- **Delegation entries** (`DELEGATION`) - When managers delegate to workers
- **Synthesis entries** (`SYNTHESIS`) - When managers synthesize results
- **Final entries** (`FINAL`) - When task completes

**Important**: The framework calls `memory.add()` during execution, but `MessageStoreMemory.add()` is a no-op. If you need runtime message storage, you have two options:

1. **Store them yourself**: Hook into `memory.add()` calls to persist messages to your store
2. **Use hybrid approach**: Use `MessageStoreMemory` for initial history, use `SharedInMemoryMemory` for runtime messages

## Key Points

1. **Separation of Concerns**
   - Implementation: Prepares and manages message store
   - Framework: Reads messages and processes tasks

2. **Interface Contract**
   - Implement all 4 methods of `BaseMessageStore`
   - Return messages in framework's expected format
   - Use constants from `agent_framework.constants`

3. **Message Format**
   - All messages must have `"type"` and `"content"` fields
   - Type must match constants (e.g., `USER_MESSAGE`, `TASK`)
   - Use message builder utilities to ensure correct format

4. **Framework Independence**
   - Framework doesn't know about your store structure
   - Framework only sees the interface you provide
   - You can use any storage backend (SQLite, PostgreSQL, files, etc.)

5. **Location Reference**
   - You decide what location represents (job_id, namespace, path, etc.)
   - Framework uses it to query your store via the interface

6. **Read-Only for Framework**
   - Framework reads from your store via `get_history()`
   - Framework doesn't write to your store
   - You handle all message persistence

## Verification Checklist

✅ **Framework Classes Accessible**
- `BaseMessageStore` - ✅ Exported from `agent_framework`
- `MessageStoreMemory` - ✅ Exported from `agent_framework`
- `ManagerAgent`, `Agent` - ✅ Exported
- All constants - ✅ Available from `agent_framework.constants`
- All message builders - ✅ Available from `agent_framework.utils.message_builder`

✅ **Implementation Can Prepare Store**
- You implement `BaseMessageStore` interface
- You store messages in your preferred format (DB, file, etc.)
- You use message builder utilities to create properly formatted messages

✅ **Implementation Passes Store**
- Create `MessageStoreMemory` with your store and location
- Pass to `ManagerAgent` or `Agent` as `memory` parameter

✅ **Framework Handles Rest**
- Framework reads messages via `memory.get_history()` → calls your store methods
- Framework creates runtime messages internally (task, action, observation, etc.)
- Framework processes task and returns results
- Framework doesn't write to your store - you handle persistence
