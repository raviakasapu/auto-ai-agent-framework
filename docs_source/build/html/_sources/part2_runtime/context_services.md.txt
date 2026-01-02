# Context & Services

This chapter covers request context management and pluggable services.

## Request Context

The framework uses Python's `contextvars` for async-safe request-scoped data.

### Why contextvars?

In async applications (FastAPI, Starlette), multiple requests run concurrently in the same thread. Using `threading.local()` would cause data leakage between requests. `contextvars` provides proper isolation per async task.

### API

```python
from agent_framework.services.request_context import (
    set_request_context,
    get_request_context,
    get_from_context,
    update_request_context,
    clear_request_context,
)

# Set context at request start
set_request_context({
    "job_id": "req_12345",
    "JOB_ID": "req_12345",  # For YAML expansion
    "user_id": "user_abc",
})

# Read values
job_id = get_from_context("job_id")
user_id = get_from_context("user_id", default="anonymous")

# Get all context
ctx = get_request_context()

# Update context
update_request_context(strategic_plan={"phases": [...]})

# Clear when done
clear_request_context()
```

### Usage Pattern

```python
from fastapi import FastAPI, WebSocket
from agent_framework.services.request_context import set_request_context, clear_request_context
import uuid

app = FastAPI()

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    
    # Generate unique job ID
    job_id = str(uuid.uuid4())
    
    # Set request context (async-safe)
    set_request_context({
        "job_id": job_id,
        "JOB_ID": job_id,
    })
    
    try:
        # Process request...
        result = await agent.run(task)
    finally:
        # Clean up
        clear_request_context()
```

### Thread Pool Propagation

When using `ThreadPoolExecutor` for sync operations, propagate context:

```python
import contextvars
from concurrent.futures import ThreadPoolExecutor

def sync_tool_execution():
    # This runs in a thread
    job_id = get_from_context("job_id")  # Works!
    return do_work(job_id)

# The framework handles this automatically:
ctx = contextvars.copy_context()
executor = ThreadPoolExecutor()
future = executor.submit(lambda: ctx.run(sync_tool_execution))
```

## Context Builder

The `ContextBuilder` service constructs context for prompts:

```python
from agent_framework.services.context_builder import ContextBuilder

builder = ContextBuilder()

# Register a data service
from my_app.services import MyDataService
builder.register_datamodel_service(MyDataService)

# Build context for a task
context = builder.build_context(
    job_id="job_123",
    include_schema=True,
    include_relationships=True,
)
```

### Registering Services

```python
from agent_framework.services.context_builder import (
    register_datamodel_service,
    get_datamodel_service,
)

# Register your service
register_datamodel_service(my_data_service)

# Retrieve it later
service = get_datamodel_service()
result = service.get_schema()
```

## Policy Engine

The policy engine enforces tool-level access control:

```python
from agent_framework.services.policy import (
    PolicyEngine,
    register_policy_datamodel_service,
)

# Register policy service
register_policy_datamodel_service(my_policy_service)

# Engine checks policies before tool execution
engine = PolicyEngine()
allowed, reason = engine.check_action(
    tool_name="delete_table",
    args={"table": "users"},
    context={"user_role": "viewer"},
)

if not allowed:
    raise PermissionError(reason)
```

### Tool Deny Policies

Configure tools that should be denied:

```python
from agent_framework.services.policy import PolicyEngine

engine = PolicyEngine(
    deny_policies=[
        {"tool": "delete_*", "role": "viewer"},
        {"tool": "drop_database", "role": "*"},
    ]
)
```

## Services in YAML

Services are configured in the deployment layer:

```yaml
# configs/agents/my_agent.yaml
services:
  context_builder:
    type: ContextBuilder
    config:
      data_service: my_data_service
  policy_engine:
    type: PolicyEngine
    config:
      deny_policies:
        - tool: "delete_*"
          role: viewer
```

## Best Practices

1. **Always use contextvars** for request-scoped data in async code
2. **Set context early** at request entry point
3. **Clear context** in finally blocks
4. **Register services** before agent creation
5. **Use policy engine** for access control
6. **Propagate context** to thread pools explicitly

## Complete Example

```python
import asyncio
import uuid
from fastapi import FastAPI, WebSocket
from agent_framework import Agent, get_preset
from agent_framework.services.request_context import (
    set_request_context,
    clear_request_context,
    get_from_context,
)
from agent_framework.services.context_builder import register_datamodel_service
from agent_framework.components.planners import ReActPlanner
from agent_framework.components.memory import SharedInMemoryMemory
from agent_framework.gateways.inference import OpenAIGateway
from agent_framework.decorators import tool

app = FastAPI()

# Register your data service
class MyDataService:
    def get_schema(self):
        return {"tables": ["users", "orders"]}

register_datamodel_service(MyDataService())

# Define a tool that uses context
@tool(name="get_job_id", description="Get current job ID")
def get_job_id() -> str:
    """Returns the current job ID from context."""
    job_id = get_from_context("job_id", default="unknown")
    return f"Current job: {job_id}"

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    
    while True:
        data = await ws.receive_json()
        task = data.get("task")
        
        # Set up request context
        job_id = str(uuid.uuid4())
        set_request_context({
            "job_id": job_id,
            "JOB_ID": job_id,
        })
        
        try:
            # Create agent with context-aware memory
            memory = SharedInMemoryMemory(
                namespace=job_id,
                agent_key="worker",
            )
            
            agent = Agent(
                name="context_demo",
                planner=ReActPlanner(
                    inference_gateway=OpenAIGateway(),
                    tools=[get_job_id],
                ),
                memory=memory,
                tools=[get_job_id],
                policies=get_preset("simple"),
            )
            
            result = await agent.run(task)
            await ws.send_json({"result": result})
            
        finally:
            clear_request_context()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

