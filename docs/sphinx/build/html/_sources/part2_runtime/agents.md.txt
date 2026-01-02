# Agents & Manager Stack

This chapter covers the two agent types: `Agent` (worker) and `ManagerAgent` (orchestrator/manager).

## Agent (Worker Agent)

The `Agent` class is the core execution engine for tool-based operations.

### Constructor

```python
from agent_framework import Agent

agent = Agent(
    planner=planner,           # Required: BasePlanner instance
    memory=memory,             # Required: BaseMemory instance
    tools=tools,               # Required: List[BaseTool] or Dict[str, BaseTool]
    policies=policies,         # Required: Dict with completion, termination, loop_prevention
    event_bus=event_bus,       # Optional: EventBus instance
    name="my_agent",           # Optional: Agent name
    description="...",         # Optional: Description
    version="1.0.0",           # Optional: Version
)
```

### Required Policies

Policies are **required** and must be provided explicitly:

```python
from agent_framework import get_preset

# Option 1: Use a preset
policies = get_preset("simple")

# Option 2: Define explicitly
from agent_framework.policies.default import (
    DefaultCompletionDetector,
    DefaultTerminationPolicy,
    DefaultLoopPreventionPolicy,
)

policies = {
    "completion": DefaultCompletionDetector(),
    "termination": DefaultTerminationPolicy(max_iterations=10),
    "loop_prevention": DefaultLoopPreventionPolicy(),
}
```

### Running an Agent

```python
# Async execution
result = await agent.run(
    task="Your task description",
    progress_handler=handler,  # Optional: BaseProgressHandler
)
```

### Execution Loop

The agent follows this loop:

1. **Receive Task** — Add task to memory
2. **Get History** — Retrieve from memory
3. **Plan** — Planner decides next action(s)
4. **Execute** — Run tool(s)
5. **Observe** — Add result to memory
6. **Check Policies** — Completion, termination, loop prevention
7. **Repeat or Return** — Continue or return result

### Event Emission

The agent emits these events through the EventBus:

| Event | When |
|-------|------|
| `agent_start` | Agent begins execution |
| `action_planned` | Planner selects action(s) |
| `worker_tool_call` | Tool execution starts |
| `worker_tool_result` | Tool execution completes |
| `action_executed` | Action fully processed |
| `agent_end` | Agent returns result |
| `error` | Exception occurred |
| `policy_denied` | HITL policy denied action |

## ManagerAgent (Orchestrator/Manager)

The `ManagerAgent` class coordinates subordinate agents through delegation.

### Constructor

```python
from agent_framework import ManagerAgent

manager = ManagerAgent(
    planner=planner,           # Required: BasePlanner
    memory=memory,             # Required: BaseMemory
    workers=workers,           # Required: Dict[str, Agent or ManagerAgent]
    event_bus=event_bus,       # Optional: EventBus
    name="orchestrator",       # Optional: Name
    synthesis_gateway=gateway, # Optional: For result synthesis
    job_store=job_store,       # Optional: BaseJobStore for persistence
    policies=policies,         # Optional: Policy overrides
)
```

### Workers Dictionary

Workers are keyed by their identifier:

```python
workers = {
    "analyzer": analyzer_agent,    # Agent instance
    "designer": designer_agent,    # Agent instance
    "validator": validator_agent,  # Agent instance
}
```

### Delegation Flow

1. **Receive Task** — Manager receives task
2. **Strategic Plan** — Planner creates multi-phase plan
3. **Delegate** — Execute phases by calling worker agents
4. **Collect Results** — Gather worker outputs
5. **Synthesize** — Optionally combine results
6. **Return** — Return aggregated result

### Parallel Execution

ManagerAgent supports parallel delegation:

```python
# In strategic plan
{
    "phases": [
        {"name": "Analysis", "worker": "analyzer", "goals": "..."},
        {"name": "Validation", "worker": "validator", "goals": "..."}
    ],
    "parallel_workers": ["analyzer", "validator"]  # Execute in parallel
}
```

### Synthesis

With a `synthesis_gateway`, the manager can summarize worker results:

```python
manager = ManagerAgent(
    planner=planner,
    memory=memory,
    workers=workers,
    synthesis_gateway=OpenAIGateway(model="gpt-4o-mini"),
)
```

### Event Emission

| Event | When |
|-------|------|
| `manager_start` | Manager begins execution |
| `delegation_planned` | Planning to delegate |
| `delegation_chosen` | Worker selected |
| `delegation_executed` | Worker completed |
| `manager_script_planned` | Script plan created |
| `manager_step_start` | Script step begins |
| `manager_step_end` | Script step completes |
| `manager_end` | Manager returns result |
| `orchestrator_phase_start` | Orchestrator phase begins |
| `orchestrator_phase_end` | Orchestrator phase completes |

## Orchestrator vs Manager

Both use `ManagerAgent`, but at different hierarchy levels:

| Aspect | Orchestrator | Manager |
|--------|--------------|---------|
| **Level** | Top (user-facing) | Middle (domain-specific) |
| **Planner** | `StrategicPlanner` | `StrategicDecomposerPlanner` |
| **Workers** | Domain managers | Worker agents |
| **Planning** | Creates phases | Creates steps |
| **Model** | Powerful (gpt-4o) | Efficient (gpt-4o-mini) |

### Hierarchy Example

```
User Request
    ↓
Orchestrator (ManagerAgent + StrategicPlanner)
    ├── Creates phases
    ├── Workers: [analysis_manager, design_manager]
    └── Delegates to managers
         ↓
Analysis Manager (ManagerAgent + StrategicDecomposerPlanner)
    ├── Creates steps
    ├── Workers: [schema_reader, validator]
    └── Delegates to workers
         ↓
Schema Reader (Agent + ReActPlanner)
    ├── Executes tools
    └── Returns results
```

## Complete Example

```python
import asyncio
from agent_framework import Agent, ManagerAgent, EventBus, get_preset
from agent_framework.components.planners import StrategicPlanner, ReActPlanner
from agent_framework.components.memory import SharedInMemoryMemory
from agent_framework.gateways.inference import OpenAIGateway
from agent_framework.decorators import tool

# Define tools
@tool(name="list_items", description="List items in a category")
def list_items(category: str) -> list:
    return ["item1", "item2", "item3"]

@tool(name="analyze_item", description="Analyze a specific item")
def analyze_item(item: str) -> dict:
    return {"item": item, "status": "analyzed"}

# Create worker agents
event_bus = EventBus()
policies = get_preset("simple")

reader = Agent(
    name="reader",
    planner=ReActPlanner(
        inference_gateway=OpenAIGateway(),
        tools=[list_items],
    ),
    memory=SharedInMemoryMemory(namespace="job_123", agent_key="reader"),
    tools=[list_items],
    policies=policies,
    event_bus=event_bus,
)

analyzer = Agent(
    name="analyzer",
    planner=ReActPlanner(
        inference_gateway=OpenAIGateway(),
        tools=[analyze_item],
    ),
    memory=SharedInMemoryMemory(namespace="job_123", agent_key="analyzer"),
    tools=[analyze_item],
    policies=policies,
    event_bus=event_bus,
)

# Create manager
manager = ManagerAgent(
    name="analysis_manager",
    planner=StrategicPlanner(
        worker_keys=["reader", "analyzer"],
        inference_gateway=OpenAIGateway(model="gpt-4o"),
    ),
    memory=SharedInMemoryMemory(namespace="job_123", agent_key="manager"),
    workers={"reader": reader, "analyzer": analyzer},
    event_bus=event_bus,
)

# Run
async def main():
    result = await manager.run("Analyze all items in the 'products' category")
    print(result)

asyncio.run(main())
```

## Best Practices

1. **Use presets** for policies instead of defining from scratch
2. **Share EventBus** across the hierarchy for unified tracing
3. **Use SharedInMemoryMemory** with same namespace for context sharing
4. **Configure synthesis** for user-friendly manager responses
5. **Log events** during development for debugging

