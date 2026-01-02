# Runtime Integration

This chapter covers the server-side integration: FastAPI endpoints, WebSocket handling, request context, and Phoenix tracing setup.

## Overview

The Power BI implementation uses:

- **FastAPI** for HTTP and WebSocket endpoints
- **`datamodel_context`** for request-scoped data model access
- **`set_request_context`** for async-safe job_id propagation
- **`AgentFactory`** for YAML-based agent loading
- **`FileJobStore`** for HITL pending actions

## Server Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        main.py                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  POST /run                                                  │
│    ├─ Set request context (job_id)                          │
│    ├─ Enter datamodel_context(job_id)                       │
│    ├─ Load orchestrator via AgentFactory                    │
│    ├─ Run agent with progress handler                       │
│    └─ Return result + events                                │
│                                                             │
│  POST /resume_job                                           │
│    ├─ Load pending action from FileJobStore                 │
│    ├─ Execute specific tool via SingleActionPlanner         │
│    └─ Clear pending action, return result                   │
│                                                             │
│  WS /ws/agent                                               │
│    ├─ Accept connection                                     │
│    ├─ For each message:                                     │
│    │   ├─ Set request context                               │
│    │   ├─ Enter datamodel_context                           │
│    │   ├─ Load/run agent with WebsocketProgressHandler      │
│    │   └─ Stream events to client                           │
│    └─ Keep connection open                                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## HTTP Endpoint: /run

```python
@app.post("/run")
async def run_agent(req: RunRequest):
    # Use job_id as model_id (they're the same thing)
    job_id = req.job_id or req.model_id
    
    if not job_id:
        return {"error": "Missing job_id or model_id in request"}, 400
    
    # CRITICAL: Set request context BEFORE loading agent
    # This ensures ${JOB_ID} in YAML configs expands correctly (async-safe)
    set_request_context({
        "job_id": job_id,      # lowercase for code access
        "JOB_ID": job_id,      # uppercase for YAML ${JOB_ID} expansion
        "user_id": "http_user"
    })
    
    # Apply optional approvals for HITL bypass
    if req.approvals:
        update_request_context(approvals=dict(req.approvals))
    
    try:
        # Use context manager for request-scoped data model access
        with datamodel_context(job_id):
            agent = AgentFactory.create_from_yaml("configs/agents/orchestrator.yaml")
            
            # Record user message in conversation history
            _shared_state_store.append_conversation_turn(job_id, "user", req.task)
            
            # Publish request_start for fresh Phoenix trace
            agent.event_bus.publish("request_start", {"job_id": job_id, "task": req.task})
            
            # Run agent
            handler = CollectorProgressHandler()
            result = await agent.run(req.task, progress_handler=handler)
            
            # Record assistant response
            summary = result.get("human_readable_summary", str(result))
            _shared_state_store.append_conversation_turn(job_id, "assistant", summary)
    finally:
        clear_request_context()
    
    return {
        "agent": agent.name,
        "task": req.task,
        "result": result,
        "events": handler.events,
        "memory": agent.memory.get_history(),
    }
```

### Key Points

1. **Request Context**: Set BEFORE loading agent for YAML variable expansion
2. **datamodel_context**: Context manager for request-scoped KG access
3. **Conversation History**: Record user/assistant messages for multi-turn
4. **Progress Handler**: Collects events for response

## WebSocket Endpoint: /ws/agent

```python
@app.websocket("/ws/agent")
async def ws_agent(ws: WebSocket):
    await ws.accept()
    
    # Send connection confirmation
    await ws.send_json({
        "event": "connected",
        "data": {"status": "ready"},
        "timestamp": int(time.time() * 1000)
    })
    
    while True:
        try:
            message = await ws.receive_json()
        except WebSocketDisconnect:
            break
        
        task = message.get("task")
        job_id = message.get("job_id") or message.get("model_id")
        
        # Set request context
        set_request_context({
            "job_id": job_id,
            "JOB_ID": job_id,
            "user_id": "ws_user"
        })
        
        try:
            with datamodel_context(job_id):
                agent = _load_agent(message.get("config_path"))
                
                # Record user message
                _shared_state_store.append_conversation_turn(job_id, "user", task)
                
                # Create streaming progress handler
                handler = WebsocketProgressHandler(ws)
                
                result = await agent.run(task, progress_handler=handler)
                
                # Send final completion
                await ws.send_json({
                    "event": "agent_end",
                    "result": result,
                    "level": "orchestrator",
                    "is_final": True,
                    "timestamp": int(time.time() * 1000)
                })
        except Exception as e:
            await ws.send_json({
                "event": "error",
                "data": {"error": str(e)},
                "timestamp": int(time.time() * 1000)
            })
        finally:
            clear_request_context()
```

### WebsocketProgressHandler

Streams filtered events to the frontend:

```python
class WebsocketProgressHandler(BaseProgressHandler):
    def __init__(self, ws: WebSocket, allowed_events: Optional[Iterable[str]] = None):
        self.ws = ws
        has_env_override, env_events = resolve_frontend_allowlist()
        if has_env_override:
            self.allowed_events = env_events
        elif allowed_events is not None:
            self.allowed_events = normalize_event_names(allowed_events)
        else:
            self.allowed_events = set(DEFAULT_FRONTEND_EVENTS)
    
    async def on_event(self, event_name: str, data: Dict[str, Any]) -> None:
        if event_name not in self.allowed_events:
            return
        try:
            await self.ws.send_json({
                "event": event_name,
                "data": data,
                "timestamp": int(time.time() * 1000)
            })
        except RuntimeError:
            pass  # WebSocket may be closed
```

## Resume Endpoints

### /resume_job (Stored Pending Action)

```python
@app.post("/resume_job")
async def resume_job(req: ResumeJobRequest):
    job = get_job_store().get_job(req.job_id)
    
    if not job or not job.pending_action:
        return {"error": "No pending action to resume"}, 400
    
    if not req.approve:
        get_job_store().clear_pending_action(req.job_id, new_status="paused")
        return {"message": "Pending action rejected. Job paused."}
    
    # Execute the pending action
    pa = job.pending_action
    
    set_request_context({"job_id": req.job_id, "JOB_ID": req.job_id})
    
    try:
        with datamodel_context(req.job_id):
            cfg_path = _resolve_worker_config(pa.worker)
            agent = AgentFactory.create_from_yaml(cfg_path)
            
            # Force single tool execution
            agent.planner = SingleActionPlanner(
                tool_name=pa.tool,
                tool_args=pa.args or {}
            )
            
            result = await agent.run(f"[RESUME_JOB] Execute {pa.tool}")
            
            get_job_store().clear_pending_action(req.job_id, new_status="running")
            
            return {"result": result}
    finally:
        clear_request_context()
```

### /resume (Ad-hoc Tool Execution)

For running specific tools without going through orchestrator:

```python
@app.post("/resume")
async def resume_agent(req: ResumeRequest):
    set_request_context({"job_id": req.job_id, "JOB_ID": req.job_id})
    
    if req.approvals:
        update_request_context(approvals=dict(req.approvals))
    
    try:
        with datamodel_context(req.job_id):
            cfg_path = req.config_path or _resolve_worker_config(req.worker)
            agent = AgentFactory.create_from_yaml(cfg_path)
            
            agent.planner = SingleActionPlanner(
                tool_name=req.tool,
                tool_args=req.args
            )
            
            result = await agent.run(f"[RESUME] Execute {req.tool}")
            
            return {"result": result}
    finally:
        clear_request_context()
```

## Data Model Context

The `datamodel_context` manager from `bi_tools.services.datamodel_service`:

```python
from bi_tools.services.datamodel_service import datamodel_context

# Context manager for request-scoped data model access
with datamodel_context(job_id):
    # All KG operations within this block use job_id
    agent = AgentFactory.create_from_yaml(...)
    result = await agent.run(task)
    # Tools automatically get job_id from context
```

### How It Works

1. Sets `job_id` in `contextvars` (async-safe)
2. Tools call `_get_current_job_id()` to get the current job
3. On exit, clears the context

## Phoenix Tracing Integration

Each request creates a root span:

```python
from opentelemetry import trace

tracer = trace.get_tracer("agent-framework.request")
root_span = tracer.start_span(f"🎯 {task[:60]}")
root_span.set_attribute("request.task", task)
root_span.set_attribute("request.job_id", job_id)

ctx = trace.set_span_in_context(root_span)
token = attach(ctx)

try:
    result = await agent.run(task)
finally:
    root_span.end()
    detach(token)
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENT_APP_HOST` | `127.0.0.1` | Server host |
| `AGENT_APP_PORT` | `8051` | Server port |
| `AGENT_APP_RELOAD` | `true` | Enable auto-reload |
| `AGENT_WS_ENABLED` | `false` | Enable WebSocket |
| `AGENT_WS_TOKEN` | — | Optional WS auth token |
| `FRONTEND_EVENT_ALLOWLIST` | — | Event filtering |

## Request Flow Diagram

```
Client Request
    │
    ▼
┌───────────────────────────────────────────────────┐
│ 1. set_request_context({job_id, JOB_ID})          │
│    - Sets contextvars for async-safe access       │
│    - Enables ${JOB_ID} expansion in YAML          │
└───────────────────────────────────────────────────┘
    │
    ▼
┌───────────────────────────────────────────────────┐
│ 2. with datamodel_context(job_id):                │
│    - Sets job_id for KG operations                │
│    - All tools get job_id automatically           │
└───────────────────────────────────────────────────┘
    │
    ▼
┌───────────────────────────────────────────────────┐
│ 3. AgentFactory.create_from_yaml(...)             │
│    - Loads agent with ${JOB_ID} expanded          │
│    - Initializes memory, planner, tools           │
│    - Creates EventBus with subscribers            │
└───────────────────────────────────────────────────┘
    │
    ▼
┌───────────────────────────────────────────────────┐
│ 4. agent.run(task, progress_handler=handler)      │
│    - Executes agent loop                          │
│    - Streams events to handler                    │
│    - Returns FinalResponse                        │
└───────────────────────────────────────────────────┘
    │
    ▼
┌───────────────────────────────────────────────────┐
│ 5. clear_request_context()                        │
│    - Cleans up for next request                   │
└───────────────────────────────────────────────────┘
    │
    ▼
Response
```

## Best Practices

1. **Always set context BEFORE loading agent** — Required for YAML expansion
2. **Use datamodel_context** — Ensures proper KG isolation
3. **Clear context in finally** — Prevents leakage
4. **Record conversation turns** — Enables multi-turn context
5. **Create root Phoenix span** — Proper trace hierarchy
6. **Handle WebSocket disconnect gracefully** — Keep server running

