# Event System

The framework includes a comprehensive event system for observability and progress tracking. Events are published through the `EventBus` and can be subscribed to by various subscribers (logging, Phoenix, Langfuse, custom handlers).

## EventBus

The `EventBus` is the central event publishing mechanism:

```python
from agent_framework.core.events import EventBus

event_bus = EventBus()

# Subscribe a handler
event_bus.subscribe(logging_subscriber)
event_bus.subscribe(phoenix_subscriber)

# Publish an event
event_bus.publish("agent_start", {
    "actor": {"role": "agent", "name": "worker_1"},
    "task": {"description": "List columns"},
    "agent_name": "worker_1"
})
```

## Event Types

The framework publishes the following events:

### Agent Events

- **`agent_start`**: Worker agent begins execution
  - Published by: `Agent.run()`
  - Contains: task, agent name, version, context

- **`agent_end`**: Worker agent completes execution
  - Published by: `Agent.run()`
  - Contains: result, status, summary

### Manager Events

- **`manager_start`**: Manager begins execution
  - Published by: `ManagerAgent.run()`
  - Contains: task, workers, strategic plan, manager name

- **`manager_end`**: Manager completes execution
  - Published by: `ManagerAgent.run()`
  - Contains: result, status, summary

- **`manager_script_planned`**: Manager creates execution script
  - Published by: `ManagerAgent._execute_script_plan()`
  - Contains: script steps, metadata

- **`manager_step_start`**: Individual script step begins
  - Published by: `ManagerAgent._execute_script_plan()`
  - Contains: step index, step details

- **`manager_step_end`**: Individual script step completes
  - Published by: `ManagerAgent._execute_script_plan()`
  - Contains: step index, result, status

- **`orchestrator_phase_start`**: Orchestrator phase begins
  - Published by: `ManagerAgent` (when orchestrator)
  - Contains: phase index, phase details, strategic plan

- **`orchestrator_phase_end`**: Orchestrator phase completes
  - Published by: `ManagerAgent` (when orchestrator)
  - Contains: phase index, result, status

### Delegation Events

- **`delegation_planned`**: Manager plans to delegate to worker
  - Published by: `ManagerAgent._delegate_to_worker()`
  - Contains: manager name, worker key, metadata

- **`delegation_chosen`**: Worker selected for delegation
  - Published by: `ManagerAgent._delegate_to_worker()`
  - Contains: manager name, worker key, worker name

- **`delegation_executed`**: Worker delegation completes
  - Published by: `ManagerAgent._delegate_to_worker()`
  - Contains: manager name, worker key, result, status

### Action Events

- **`action_planned`**: Tool call planned by planner
  - Published by: `Agent._execute_actions()`
  - Contains: tool name, args, actor info

- **`action_executed`**: Tool execution completes
  - Published by: `Agent._execute_actions()`
  - Contains: tool name, args, result, execution time

- **`worker_tool_call`**: Tool call initiated (lightweight)
  - Published by: `Agent._execute_actions()`
  - Contains: call_id, tool name, args, worker name

- **`worker_tool_result`**: Tool result available
  - Published by: `Agent._execute_actions()`
  - Contains: call_id, tool name, result, success, summary

### Policy Events

- **`policy_denied`**: Tool execution denied by policy
  - Published by: `Agent._execute_actions()`
  - Contains: tool name, reason, actor info

### Error Events

- **`error`**: Error occurred during execution
  - Published by: `Agent.run()`, `ManagerAgent.run()`
  - Contains: message, details, actor info

## Event Payload Structure

All events follow a consistent structure with actor information:

```python
{
    "actor": {
        "role": "agent" | "manager",
        "name": "agent_name",
        "version": "2.0.0"  # optional
    },
    # Event-specific fields
    "task": {...},
    "result": {...},
    "status": "success" | "error" | "pending",
    # ...
}
```

### Actor Information

Every event includes actor information:
- **`role`**: `"agent"` for workers, `"manager"` for managers
- **`name`**: Agent or manager name
- **`version`**: Optional version string

### Status Values

Events may include a `status` field:
- **`success`**: Operation completed successfully
- **`error`**: Operation failed
- **`pending`**: Operation awaiting approval (HITL)

## Event Subscribers

The framework provides built-in subscribers:

### LoggingSubscriber

Logs events to Python logging:

```python
from agent_framework.core.events import LoggingSubscriber

subscriber = LoggingSubscriber(
    level="INFO",
    include_data=True,
    max_payload_chars=2000
)
event_bus.subscribe(subscriber)
```

### PhoenixSubscriber

Sends events to Phoenix (OpenTelemetry):

```python
from agent_framework.observability.subscribers import PhoenixSubscriber

subscriber = PhoenixSubscriber(
    endpoint="http://localhost:6006/v1/traces",
    service_name="orchestrator"
)
event_bus.subscribe(subscriber)
```

### LangfuseSubscriber

Sends events to Langfuse:

```python
from agent_framework.observability.subscribers import LangfuseSubscriber

subscriber = LangfuseSubscriber(
    api_key="...",
    project="..."
)
event_bus.subscribe(subscriber)
```

### Custom Subscribers

Implement `BaseEventSubscriber`:

```python
from agent_framework.base import BaseEventSubscriber

class CustomSubscriber(BaseEventSubscriber):
    def handle_event(self, event_name: str, data: Dict[str, Any]) -> None:
        # Custom handling
        print(f"Event: {event_name}, Data: {data}")

event_bus.subscribe(CustomSubscriber())
```

## Progress Handlers

For async progress tracking, use `BaseProgressHandler`:

```python
from agent_framework.base import BaseProgressHandler

class WebSocketProgressHandler(BaseProgressHandler):
    async def on_event(self, event_name: str, data: Dict[str, Any]) -> None:
        await websocket.send_json({
            "event": event_name,
            "data": data,
            "timestamp": time.time()
        })

# Pass to agent.run()
result = await agent.run(task, progress_handler=handler)
```

## Event Flow Example

```
User Request
  ↓
request_start (published by implementation)
  ↓
agent_start (Agent.run())
  ↓
manager_start (ManagerAgent.run())
  ↓
delegation_planned
  ↓
delegation_chosen
  ↓
agent_start (Worker Agent.run())
  ↓
action_planned
  ↓
worker_tool_call
  ↓
worker_tool_result
  ↓
action_executed
  ↓
agent_end (Worker Agent)
  ↓
delegation_executed
  ↓
manager_end
  ↓
agent_end (Orchestrator)
```

## Event Filtering

Implementations can filter events for frontend consumption:

```python
# Example: Filter events for WebSocket
ALLOWED_EVENTS = {
    "agent_start", "agent_end",
    "manager_start", "manager_end",
    "delegation_chosen", "delegation_executed",
    "action_planned", "action_executed",
    "error"
}

class FilteredProgressHandler(BaseProgressHandler):
    async def on_event(self, event_name: str, data: Dict[str, Any]) -> None:
        if event_name in ALLOWED_EVENTS:
            await websocket.send_json({"event": event_name, "data": data})
```

## Observability Integration

Events are automatically captured by observability subscribers:

- **Phoenix**: Creates OpenTelemetry spans from events
- **Langfuse**: Tracks LLM calls and tool executions
- **Logging**: Structured logs for debugging

See [Phoenix Tracing](phoenix_tracing.rst) for details on observability integration.

## Best Practices

1. **Subscribe Early**: Subscribe to event bus before agent execution
2. **Error Handling**: Subscribers should handle errors gracefully
3. **Event Filtering**: Filter events at subscriber level, not publisher
4. **Async Safety**: Use `BaseProgressHandler` for async event handling
5. **Payload Size**: Keep event payloads reasonable (use summaries for large data)

