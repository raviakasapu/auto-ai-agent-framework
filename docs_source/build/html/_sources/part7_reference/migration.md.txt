# Migration Guide

Migrating between framework versions.

## v1 to v2

### Breaking Changes

#### 1. Policies are Required

**Before (v1):**
```python
agent = Agent(
    planner=planner,
    memory=memory,
    tools=tools,
)
```

**After (v2):**
```python
from agent_framework import get_preset

agent = Agent(
    planner=planner,
    memory=memory,
    tools=tools,
    policies=get_preset("simple"),  # Required!
)
```

#### 2. FinalResponse for Completion

**Before (v1):**
```python
# Planner returned dict
return {"completed": True, "result": "..."}
```

**After (v2):**
```python
from agent_framework import FinalResponse

return FinalResponse(
    operation="display_message",
    payload={"message": "..."},
    human_readable_summary="Task completed"
)
```

#### 3. @tool Decorator

**Before (v1):**
```python
class MyTool(BaseTool):
    # ... lots of boilerplate
```

**After (v2):**
```python
from agent_framework import tool

@tool(name="my_tool", description="...")
def my_tool(x: int) -> int:
    return x * 2
```

#### 4. Message Type Constants

**Before (v1):**
```python
{"type": "manager_synthesis", "content": "..."}
```

**After (v2):**
```python
from agent_framework.constants import SYNTHESIS

{"type": SYNTHESIS, "content": "..."}
```

#### 5. Job Store Injection

**Before (v1):**
```python
# Global function
from agent_framework.state.job_store import get_job_store
store = get_job_store()
```

**After (v2):**
```python
from agent_framework import ManagerAgent

manager = ManagerAgent(
    ...,
    job_store=my_job_store,  # Inject dependency
)
```

### Migration Steps

1. **Add policies to all agents**
   ```python
   policies = get_preset("simple")
   ```

2. **Update planners to return FinalResponse**
   ```python
   return FinalResponse(
       operation="display_message",
       payload={...},
       human_readable_summary="..."
   )
   ```

3. **Convert tools to @tool decorator**
   ```python
   @tool(name="...", description="...")
   def my_tool(...):
       ...
   ```

4. **Use constants for message types**
   ```python
   from agent_framework.constants import TASK, OBSERVATION, FINAL
   ```

5. **Inject job stores**
   ```python
   manager = ManagerAgent(..., job_store=store)
   ```

## v2.0 to v2.1

### New Features

- `MessageStoreMemory` for external stores
- `HierarchicalMessageStoreMemory` for managers
- Message builder utilities
- History filters per role

### Migration

1. **Consider MessageStoreMemory**
   ```python
   from agent_framework import MessageStoreMemory
   
   memory = MessageStoreMemory(
       message_store=your_store,
       location="job_123",
       agent_key="worker",
   )
   ```

2. **Use message builder**
   ```python
   from agent_framework.utils.message_builder import create_user_message
   
   msg = create_user_message("Hello")
   ```

## v2.1 to v2.2

### New Features

- Pip-installable package (`auto-ai-agent-framework`)
- Policy presets (`get_preset`)
- Enhanced observability
- Async-safe context (`contextvars`)

### Migration

1. **Install from PyPI**
   ```bash
   pip install auto-ai-agent-framework
   ```

2. **Use presets**
   ```python
   from agent_framework import get_preset
   policies = get_preset("simple")
   ```

3. **Use contextvars for context**
   ```python
   from agent_framework.services.request_context import set_request_context
   set_request_context({"job_id": "..."})
   ```

## v2.x Feature Summary

### v2.2 Highlights

- **Pip-installable library**: Install with `pip install auto-ai-agent-framework` or `pip install -e ./agent-framework-pypi`
- **@tool decorator**: Author tools with regular Python functions, schemas inferred from type hints
- **Policy presets**: `get_preset(...)` for easy policy configuration
- **Message store integrations**: `MessageStoreMemory` and `HierarchicalMessageStoreMemory`
- **Observability upgrades**: Phoenix/OpenTelemetry spans with cost, usage, actor context

### v2.0 Highlights

- **ChatPlanner**: Conversational AI for chat-style agents
- **ReActPlanner**: Iterative reasoning with Thought → Action → Observation loop
- **WorkerRouterPlanner**: Intent classification and worker delegation
- **Enhanced ManagerAgent**: Planner-driven delegation with named workers
- **Hierarchical orchestration**: Multi-level agent teams

### Planner Ecosystem

| Planner | Use Case | Returns |
|---------|----------|---------|
| StaticPlanner | Rule-based routing | Action or Final |
| ChatPlanner | Conversational AI | FinalResponse |
| LLMRouterPlanner | Tool selection | Action (tool) |
| ReActPlanner | Iterative reasoning | Action or Final |
| WorkerRouterPlanner | Intent classification | Action (worker) |
| StrategicPlanner | Phase-based planning | Action (manager) |
| StrategicDecomposerPlanner | Step-by-step | Action (worker) |

## Checking Your Version

```python
import agent_framework
print(agent_framework.__version__)
```

## Getting Help

- Check documentation for your version
- Review CHANGELOG for breaking changes
- Test migrations in development first

