# Troubleshooting

Common issues and solutions.

## Agent Not Completing

### Symptom
Agent runs but never returns a result.

### Causes & Solutions

**1. Completion not detected**
```python
# Check completion detector configuration
detector = DefaultCompletionDetector(
    indicators=["completed", "done", "success"],
    check_history_depth=10,
)

# Ensure tools return completion indicators
@tool
def my_tool(x: str) -> dict:
    return {
        "result": x,
        "human_readable_summary": "Task completed successfully"  # Include this!
    }
```

**2. Max iterations reached**
```python
# Increase max iterations
termination = DefaultTerminationPolicy(
    max_iterations=20,  # Default is 10
)
```

**3. Loop detected**
```python
# Tune loop prevention
loop_prevention = DefaultLoopPreventionPolicy(
    repetition_threshold=5,  # Allow more retries
)
```

## Previous Turn Completion Detected

### Symptom
Agent immediately returns, detecting completion from previous turn.

### Solution
The `DefaultCompletionDetector` now only checks current turn history:

```python
# This is handled automatically
# The detector finds the last "task" entry and only checks history after it
```

If you have a custom detector, implement turn-scoping:

```python
def _get_current_turn_history(self, history):
    for i in range(len(history) - 1, -1, -1):
        if history[i].get("type") == "task":
            return history[i + 1:]
    return history
```

## Tool Not Found

### Symptom
```
Error: Tool 'my_tool' not found
```

### Solution
Ensure tool is registered and included:

```python
# 1. Register the tool
register_tool("MyTool", MyTool)

# 2. Include in agent config
agent = Agent(
    tools=[my_tool],  # Tool instance here
    ...
)
```

In YAML:
```yaml
resources:
  tools:
    - name: my_tool
      type: MyTool

spec:
  tools: [my_tool]  # Reference by name
```

## Context Not Available

### Symptom
```
get_from_context("job_id") returns None
```

### Solution
Set context before agent execution:

```python
from agent_framework.services.request_context import set_request_context

# Set BEFORE creating agent
set_request_context({
    "job_id": "123",
    "JOB_ID": "123",  # For YAML expansion
})

agent = AgentFactory.create_from_yaml("config.yaml")
result = await agent.run(task)
```

## LLM Timeout

### Symptom
```
httpx.ReadTimeout: timed out
```

### Solution
```python
gateway = OpenAIGateway(
    model="gpt-4o",
    timeout=120,  # Increase timeout
)
```

Or in environment:
```bash
OPENAI_TIMEOUT=120
```

## Memory Not Shared

### Symptom
Agents don't see each other's history.

### Solution
Use same namespace:

```python
# Same namespace = shared context
memory1 = SharedInMemoryMemory(namespace="job_123", agent_key="worker_1")
memory2 = SharedInMemoryMemory(namespace="job_123", agent_key="worker_2")
```

For managers, use hierarchical memory:

```python
memory = HierarchicalMessageStoreMemory(
    message_store=store,
    location="job_123",
    agent_key="manager",
    subordinates=["worker_1", "worker_2"],
)
```

## Events Not Received

### Symptom
Phoenix/WebSocket not receiving events.

### Solution

**1. Ensure EventBus is shared**
```python
event_bus = EventBus()
event_bus.subscribe(phoenix_subscriber)

# Pass to ALL agents in hierarchy
orchestrator = ManagerAgent(event_bus=event_bus, ...)
worker = Agent(event_bus=event_bus, ...)
```

**2. Check event allowlist**
```bash
# Allow all events
FRONTEND_EVENT_ALLOWLIST="*"
```

## Policies Not Provided

### Symptom
```
ValueError: Required policy 'completion' not provided.
```

### Solution
Policies are required. Use a preset:

```python
from agent_framework import get_preset

agent = Agent(
    planner=planner,
    memory=memory,
    tools=tools,
    policies=get_preset("simple"),  # Required!
)
```

## YAML Variable Not Expanded

### Symptom
```yaml
namespace: ${JOB_ID}  # Stays as literal "${JOB_ID}"
```

### Solution
Set context before loading:

```python
from agent_framework.services.request_context import set_request_context

set_request_context({
    "JOB_ID": "job_123",  # Must match variable name
})

agent = AgentFactory.create_from_yaml("config.yaml")
```

## Debug Logging

Enable detailed logging:

```python
import logging

# Enable framework debug logs
logging.getLogger("agent_framework").setLevel(logging.DEBUG)

# Enable HTTP debug logs
logging.getLogger("httpx").setLevel(logging.DEBUG)
```

Or via environment:
```bash
LOG_LEVEL=DEBUG
```

## Phoenix Connection Failed

### Symptom
```
Connection refused: http://localhost:6006
```

### Solution

**1. Start Phoenix**
```bash
docker run -p 6006:6006 arizephoenix/phoenix
```

**2. Check endpoint**
```bash
PHOENIX_ENDPOINT=http://your-phoenix-server:6006/v1/traces
```

**3. Disable if not needed**
```python
# Don't subscribe Phoenix if not available
if os.getenv("PHOENIX_ENDPOINT"):
    event_bus.subscribe(PhoenixSubscriber(...))
```

## Getting Help

1. **Check logs** — Enable DEBUG level
2. **Check Phoenix traces** — Look for errors in spans
3. **Verify configuration** — Ensure all required fields
4. **Check environment** — Verify env vars are set
5. **Test isolation** — Run minimal example

