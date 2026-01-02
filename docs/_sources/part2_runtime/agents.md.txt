# Agent Types Guide

The AI Agent Framework supports two types of agents: single worker agents and manager agents that orchestrate workers.

## Agent Types Overview

| Type | Kind | Use Case |
|------|------|----------|
| Agent | `Agent` | Single worker with tools and planner |
| ManagerAgent | `ManagerAgent` | Orchestrator that routes to worker agents |

---

## Agent (Single Worker)

A single agent with direct access to tools and a planner for reasoning.

### Configuration

```yaml
apiVersion: agent.framework/v2
kind: Agent

metadata:
  name: ResearchWorker
  description: Research assistant with search and note capabilities

resources:
  inference_gateways:
    - name: openai
      type: OpenAIGateway
      config:
        model: ${OPENAI_MODEL:-gpt-4o-mini}
        api_key: ${OPENAI_API_KEY}
        use_function_calling: true

  tools:
    - name: web_search
      type: MockSearchTool
      config: {}
    - name: note_taker
      type: NoteTakerTool
      config:
        storage_path: /tmp/notes.json

spec:
  policies:
    $preset: simple

  planner:
    type: ReActPlanner
    config:
      inference_gateway: openai
      use_function_calling: true
      system_prompt: |
        You are a research assistant.
        Use tools to find and save information.

  memory:
    $preset: worker

  tools: [web_search, note_taker]
```

### Key Components

| Component | Description |
|-----------|-------------|
| `planner` | ReActPlanner for reasoning and tool selection |
| `tools` | List of tools the agent can use |
| `memory` | Agent's memory (standalone or shared) |
| `policies` | Behavior control (termination, completion, etc.) |

### Execution Flow

1. **Receive task** — The task is added to memory so it becomes part of history
2. **Collect history** — Memory provides a filtered view of relevant conversation/tool traces
3. **Plan** — The planner chooses the next action(s) to take
4. **Execute** — Selected tools run with validated arguments
5. **Observe** — Tool results are appended to memory
6. **Evaluate policies** — Completion, termination, and loop prevention policies run
7. **Repeat or return** — Continue looping until policies decide to return a `FinalResponse`

### Python API

#### Constructor

```python
from agent_framework import Agent

agent = Agent(
    planner=planner,           # BasePlanner instance
    memory=memory,             # BaseMemory instance
    tools=tools,               # Sequence or dict of BaseTool
    policies=policies,         # Completion/termination/loop prevention policies
    event_bus=event_bus,       # Optional EventBus
    name="my_agent",
    description="Optional description",
    version="1.0.0",
)
```

#### Required Policies

Policies are always required. Use presets for convenience or wire explicit classes:

```python
from agent_framework import get_preset
policies = get_preset("simple")

# or configure manually
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

#### Running an Agent

```python
result = await agent.run(
    task="Summarize the latest company update",
    progress_handler=handler,  # Optional BaseProgressHandler
)
```

#### Event Emission

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

---

## ManagerAgent (Orchestrator)

A manager agent that routes tasks to specialized worker agents.

### Configuration

```yaml
apiVersion: agent.framework/v2
kind: ManagerAgent

metadata:
  name: Orchestrator
  description: Routes tasks to appropriate workers

resources:
  inference_gateways:
    - name: openai-orchestrator
      type: OpenAIGateway
      config:
        model: ${OPENAI_MODEL:-gpt-4o-mini}
        api_key: ${OPENAI_API_KEY}

spec:
  policies:
    $preset: manager_with_followups

  planner:
    type: WorkerRouterPlanner
    config:
      inference_gateway: openai-orchestrator
      worker_keys: [research-worker, task-worker]
      default_worker: research-worker
      system_prompt: |
        You are a task router. Analyze requests and route to the appropriate worker:
        - research-worker: For search, research, and information gathering
        - task-worker: For task management and scheduling

        Return JSON: {"worker": "<key>", "reason": "..."}

  memory:
    $preset: manager

  workers:
    - name: research-worker
      config_path: configs/agents/research_worker.yaml
    - name: task-worker
      config_path: configs/agents/task_worker.yaml
```

### Key Components

| Component | Description |
|-----------|-------------|
| `planner` | WorkerRouterPlanner for routing decisions |
| `workers` | List of worker agent configurations |
| `memory` | HierarchicalSharedMemory (sees worker state) |
| `policies` | Typically includes follow-up policy |

### Execution Flow

1. Manager receives a task
2. Router planner analyzes the task
3. Router selects appropriate worker
4. Worker executes the task
5. Manager may initiate follow-up phases
6. Manager aggregates results

### Python API

#### Constructor

```python
from agent_framework import ManagerAgent

manager = ManagerAgent(
    planner=planner,
    memory=memory,
    workers=workers,               # Dict[str, Agent or ManagerAgent]
    event_bus=event_bus,
    name="orchestrator",
    synthesis_gateway=gateway,     # Optional for result synthesis
    job_store=job_store,           # Optional persistence
    policies=policies,             # Optional overrides
)
```

#### Workers Dictionary

```python
workers = {
    "analyzer": analyzer_agent,
    "designer": designer_agent,
    "validator": validator_agent,
}
```

#### Delegation Flow

1. **Receive task** — Manager captures the initial request
2. **Strategic plan** — Planner generates phases or steps
3. **Delegate** — Executes each phase by calling the selected worker
4. **Collect results** — Aggregates worker outputs
5. **Synthesize** — Optional summarization before returning to the caller

#### Parallel Execution

```python
{
    "phases": [
        {"name": "Analysis", "worker": "analyzer", "goals": "..."},
        {"name": "Validation", "worker": "validator", "goals": "..."}
    ],
    "parallel_workers": ["analyzer", "validator"]
}
```

#### Synthesis

Provide a `synthesis_gateway` to re-write worker output for end users:

```python
manager = ManagerAgent(
    planner=planner,
    memory=memory,
    workers=workers,
    synthesis_gateway=OpenAIGateway(model="gpt-4o-mini"),
)
```

#### Event Emission

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

---

## Comparison

| Feature | Agent | ManagerAgent |
|---------|-------|--------------|
| Direct tool access | Yes | No |
| Routes to workers | No | Yes |
| Planner type | ReActPlanner | WorkerRouterPlanner |
| Memory preset | `standalone` or `worker` | `manager` |
| Policy preset | `simple` | `manager_with_followups` |
| Complexity | Lower | Higher |

---

## When to Use Each Type

### Use Agent when:

- Task requires direct tool usage
- Single-purpose functionality
- No need for task delegation
- Simpler execution flow preferred

**Examples:**
- Calculator agent
- Weather lookup agent
- Note-taking agent
- Single-domain research agent

### Use ManagerAgent when:

- Task requires multiple skill domains
- Parallel execution of subtasks
- Complex multi-step workflows
- Need for task routing/delegation

**Examples:**
- Research + task management system
- Multi-domain assistant
- Parallel data processing
- Workflow orchestration

---

## Architecture Patterns

### Pattern 1: Single Agent

```
[User] -> [Agent] -> [Tools]
```

Simple, direct execution.

### Pattern 2: Manager with Workers

```
[User] -> [Manager] -> [Router] -> [Worker A] -> [Tools A]
                               -> [Worker B] -> [Tools B]
```

Hierarchical delegation.

### Pattern 3: Shared Memory Team

```
[User] -> [Manager] -> [Worker A] -> [Shared Memory]
                   -> [Worker B] -> [Shared Memory]
                                      ^
                   [Manager sees all] <-+
```

Workers share state, manager has visibility.

---

## Orchestrator vs Manager

Both are `ManagerAgent` instances but typically operate at different layers of the hierarchy:

| Aspect | Orchestrator | Manager |
|--------|--------------|---------|
| **Level** | Top (user-facing) | Middle (domain-specific) |
| **Planner** | `StrategicPlanner` | `StrategicDecomposerPlanner` or scripted planner |
| **Workers** | Domain managers | Worker agents |
| **Planning** | Creates phases | Creates executable steps |
| **Model choice** | Larger models (e.g., `gpt-4o`) | Efficient models (e.g., `gpt-4o-mini`) |

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

---

## Complete Examples

### Standalone Calculator Agent

```yaml
apiVersion: agent.framework/v2
kind: Agent

metadata:
  name: Calculator
  description: Math calculation agent

resources:
  inference_gateways:
    - name: openai
      type: OpenAIGateway
      config:
        model: gpt-4o-mini
        api_key: ${OPENAI_API_KEY}
        use_function_calling: true

  tools:
    - name: calculator
      type: CalculatorTool
      config: {}

spec:
  policies:
    $preset: simple

  planner:
    type: ReActPlanner
    config:
      inference_gateway: openai
      use_function_calling: true
      system_prompt: |
        You are a calculator. Use the calculator tool
        to solve mathematical problems.

  memory:
    $preset: standalone

  tools: [calculator]
```

### Multi-Worker System

**Manager (orchestrator.yaml):**

```yaml
apiVersion: agent.framework/v2
kind: ManagerAgent

metadata:
  name: AssistantOrchestrator

resources:
  inference_gateways:
    - name: openai
      type: OpenAIGateway
      config:
        model: gpt-4o
        api_key: ${OPENAI_API_KEY}

spec:
  policies:
    $preset: manager_with_followups

  planner:
    type: WorkerRouterPlanner
    config:
      inference_gateway: openai
      worker_keys: [research, tasks, weather]
      default_worker: research
      system_prompt: |
        Route requests to the appropriate specialist:
        - research: Information lookup and research
        - tasks: Task creation and management
        - weather: Weather queries

  memory:
    $preset: manager

  workers:
    - name: research
      config_path: configs/agents/research_worker.yaml
    - name: tasks
      config_path: configs/agents/task_worker.yaml
    - name: weather
      config_path: configs/agents/weather_worker.yaml
```

**Worker (research_worker.yaml):**

```yaml
apiVersion: agent.framework/v2
kind: Agent

metadata:
  name: ResearchWorker

resources:
  inference_gateways:
    - name: openai
      type: OpenAIGateway
      config:
        model: gpt-4o-mini
        api_key: ${OPENAI_API_KEY}
        use_function_calling: true

  tools:
    - name: web_search
      type: MockSearchTool
      config: {}

spec:
  policies:
    $preset: simple

  planner:
    type: ReActPlanner
    config:
      inference_gateway: openai
      use_function_calling: true
      system_prompt: |
        You are a research specialist.
        Search for information and provide summaries.

  memory:
    $preset: worker

  tools: [web_search]
```

### Programmatic Stack Example

```python
import asyncio
from agent_framework import Agent, ManagerAgent, EventBus, get_preset
from agent_framework.components.planners import StrategicPlanner, ReActPlanner
from agent_framework.components.memory import SharedInMemoryMemory
from agent_framework.gateways.inference import OpenAIGateway
from agent_framework.decorators import tool

@tool(name="list_items", description="List items in a category")
def list_items(category: str) -> list:
    return ["item1", "item2", "item3"]

@tool(name="analyze_item", description="Analyze a specific item")
def analyze_item(item: str) -> dict:
    return {"item": item, "status": "analyzed"}

event_bus = EventBus()
policies = get_preset("simple")
shared_namespace = "job_123"

reader = Agent(
    name="reader",
    planner=ReActPlanner(
        inference_gateway=OpenAIGateway(),
        tools=[list_items],
    ),
    memory=SharedInMemoryMemory(namespace=shared_namespace, agent_key="reader"),
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
    memory=SharedInMemoryMemory(namespace=shared_namespace, agent_key="analyzer"),
    tools=[analyze_item],
    policies=policies,
    event_bus=event_bus,
)

manager = ManagerAgent(
    name="analysis_manager",
    planner=StrategicPlanner(
        worker_keys=["reader", "analyzer"],
        inference_gateway=OpenAIGateway(model="gpt-4o"),
    ),
    memory=SharedInMemoryMemory(namespace=shared_namespace, agent_key="manager"),
    workers={"reader": reader, "analyzer": analyzer},
    event_bus=event_bus,
)

async def main():
    result = await manager.run("Analyze all items in the 'products' category")
    print(result)

asyncio.run(main())
```

---

## Best Practices

1. **Start simple** — Build a single Agent before introducing orchestration
2. **One responsibility per worker** — Keep workers narrowly focused for predictable routing
3. **Use memory presets** — `worker` for workers, `manager` for orchestrators so state is derived consistently
4. **Match policy presets** — `simple` for workers, `manager_with_followups` or custom presets for managers
5. **Share the EventBus** — Route all agents through the same `EventBus` for unified tracing and observability
6. **Coordinate namespaces** — Use the same `JOB_ID` when workers need to collaborate via shared memory
7. **Configure synthesis** — Provide a `synthesis_gateway` so managers can rewrite worker output for end users
8. **Test workers independently** — Validate each worker agent before composing the team, then log emitted events while debugging
