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

1. Agent receives a task
2. Planner reasons about the task
3. Planner selects and calls tools
4. Tool results are added to memory
5. Planner continues until completion or termination

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

---

## Best Practices

1. **Start simple** - Use Agent until you need orchestration
2. **One responsibility per worker** - Keep workers focused
3. **Use appropriate memory presets** - `worker` for workers, `manager` for managers
4. **Match policy presets** - `simple` for workers, `manager_with_followups` for managers
5. **Clear routing instructions** - Make router prompts explicit about which worker handles what
6. **Test workers independently** - Ensure each worker works before combining
