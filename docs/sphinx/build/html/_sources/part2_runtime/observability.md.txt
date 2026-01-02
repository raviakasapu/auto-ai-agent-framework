# Observability & Streaming

This chapter covers the event system, tracing, and real-time streaming.

## EventBus

The `EventBus` is the central event publishing mechanism:

```python
from agent_framework import EventBus

event_bus = EventBus()

# Subscribe handlers
event_bus.subscribe(logging_subscriber)
event_bus.subscribe(phoenix_subscriber)

# Publish events
event_bus.publish("agent_start", {
    "agent_name": "worker_1",
    "task": "List tables",
})
```

## Event Types

### Agent Events

| Event | When | Key Data |
|-------|------|----------|
| `agent_start` | Agent begins | agent_name, task |
| `agent_end` | Agent completes | agent_name, result, summary |
| `action_planned` | Tool selected | tool_name, args |
| `action_executed` | Tool completed | tool_name, result |
| `worker_tool_call` | Tool call starts | tool_name, args |
| `worker_tool_result` | Tool call ends | tool_name, result |

### Manager Events

| Event | When | Key Data |
|-------|------|----------|
| `manager_start` | Manager begins | manager_name, task |
| `manager_end` | Manager completes | manager_name, result |
| `delegation_planned` | Planning delegation | manager_name, worker |
| `delegation_chosen` | Worker selected | manager_name, worker_name |
| `delegation_executed` | Worker completed | manager_name, result |
| `manager_script_planned` | Script created | manager_name, script |
| `manager_step_start` | Step begins | step_name, worker |
| `manager_step_end` | Step completes | step_name, result |

### Orchestrator Events

| Event | When | Key Data |
|-------|------|----------|
| `orchestrator_phase_start` | Phase begins | phase_name, worker |
| `orchestrator_phase_end` | Phase completes | phase_name, result |

### Other Events

| Event | When | Key Data |
|-------|------|----------|
| `error` | Exception occurred | error_message, error_type |
| `policy_denied` | HITL denied action | tool_name, reason |

## Event Subscribers

### BaseEventSubscriber

Create custom subscribers:

```python
from agent_framework import BaseEventSubscriber

class MySubscriber(BaseEventSubscriber):
    def handle_event(self, event_name: str, data: dict) -> None:
        print(f"Event: {event_name}, Data: {data}")

event_bus.subscribe(MySubscriber())
```

### LoggingSubscriber

```python
from agent_framework.observability.subscribers import LoggingSubscriber

subscriber = LoggingSubscriber(
    level="INFO",
    include_data=True,
    truncate_payload=200,
)
```

### PhoenixSubscriber

Exports traces to Arize Phoenix via OpenTelemetry:

```python
from agent_framework.observability.subscribers import PhoenixSubscriber

subscriber = PhoenixSubscriber(
    service_name="my_agent_service",
    endpoint="http://localhost:6006/v1/traces",
)
```

**Span hierarchy**:
```
root_request
├── manager:{name}
│   ├── delegation:{worker}
│   │   ├── agent:{name}
│   │   │   ├── action:{tool}
│   │   │   │   └── tool.{tool_name}
│   │   │   └── llm.openai.chat_completions
│   │   └── ...
│   └── ...
└── ...
```

**Attributes captured**:
- LLM usage (tokens, cost, latency)
- Tool inputs/outputs
- Actor context (role, name)
- Error details

### LangfuseSubscriber

```python
from agent_framework.observability.subscribers import LangfuseSubscriber

subscriber = LangfuseSubscriber(
    public_key="pk-...",
    secret_key="sk-...",
    host="https://cloud.langfuse.com",
)
```

## Progress Handlers

For real-time streaming to clients:

```python
from agent_framework import BaseProgressHandler

class WebSocketProgressHandler(BaseProgressHandler):
    def __init__(self, websocket):
        self.ws = websocket
    
    async def on_event(self, event_name: str, data: dict) -> None:
        await self.ws.send_json({
            "event": event_name,
            "data": data,
            "timestamp": time.time(),
        })

# Pass to agent.run()
handler = WebSocketProgressHandler(websocket)
result = await agent.run(task, progress_handler=handler)
```

## Event Filtering

Filter events for frontend consumption:

```python
from agent_framework.progress_filters import (
    DEFAULT_FRONTEND_EVENTS,
    resolve_frontend_allowlist,
)

# Default events sent to frontend
print(DEFAULT_FRONTEND_EVENTS)
# {'agent_start', 'agent_end', 'action_planned', 'action_executed', ...}

# Custom filtering
ALLOWED = {"agent_start", "agent_end", "error"}

class FilteredHandler(BaseProgressHandler):
    async def on_event(self, event_name: str, data: dict) -> None:
        if event_name in ALLOWED:
            await self.send(event_name, data)
```

### Environment Variable

```bash
# Allow all events
FRONTEND_EVENT_ALLOWLIST="*"

# Custom list
FRONTEND_EVENT_ALLOWLIST="agent_start,agent_end,error"
```

## Phoenix Configuration

| Variable | Purpose | Default |
|----------|---------|---------|
| `PHOENIX_ENDPOINT` | Phoenix collector URL | `http://localhost:6006/v1/traces` |
| `PHOENIX_MAX_ATTR_CHARS` | Max attribute length | `4000` |
| `PHOENIX_CAPTURE_LLM_BODIES` | Include prompts/responses | `true` |
| `PHOENIX_PRETTY_JSON` | Pretty-print JSON | `false` |
| `PHOENIX_COMPACT_JSON` | Compact JSON format | `true` |

## LLM Pricing

Configure token pricing for cost tracking:

```bash
# JSON format
LLM_PRICING_JSON='{
  "gpt_4o": {"input": 2.50, "output": 10.00},
  "gpt_4o_mini": {"input": 0.15, "output": 0.60}
}'

# Or legacy format
LLM_PRICING_INPUT_USD_PER_1K=0.15
LLM_PRICING_OUTPUT_USD_PER_1K=0.60
```

## Complete Example

```python
import asyncio
from agent_framework import Agent, EventBus, get_preset
from agent_framework.components.planners import ReActPlanner
from agent_framework.components.memory import SimpleMemory
from agent_framework.gateways.inference import OpenAIGateway
from agent_framework.observability.subscribers import PhoenixSubscriber, LoggingSubscriber
from agent_framework.decorators import tool

# Set up event bus with subscribers
event_bus = EventBus()
event_bus.subscribe(LoggingSubscriber(level="INFO"))
event_bus.subscribe(PhoenixSubscriber(
    service_name="demo_agent",
    endpoint="http://localhost:6006/v1/traces",
))

@tool
def calculate(expression: str) -> str:
    return str(eval(expression))

# Create agent with event bus
agent = Agent(
    name="calculator",
    planner=ReActPlanner(
        inference_gateway=OpenAIGateway(),
        tools=[calculate],
    ),
    memory=SimpleMemory(),
    tools=[calculate],
    policies=get_preset("simple"),
    event_bus=event_bus,  # Pass event bus
)

async def main():
    result = await agent.run("Calculate 2 + 2")
    print(result)

asyncio.run(main())
```

## Viewing Traces

### Phoenix UI

```bash
# Start Phoenix
docker run -p 6006:6006 arizephoenix/phoenix

# Open browser
open http://localhost:6006
```

### Langfuse

Log in to your Langfuse dashboard to view traces.

## Best Practices

1. **Share EventBus** across agent hierarchy for unified traces
2. **Use PhoenixSubscriber** in production for observability
3. **Filter events** for frontend to reduce noise
4. **Configure pricing** for accurate cost tracking
5. **Enable pretty JSON** only in development (performance impact)
6. **Log events** at appropriate levels

