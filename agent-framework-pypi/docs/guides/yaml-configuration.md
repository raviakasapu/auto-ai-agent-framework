# YAML Configuration Guide

This guide covers all configuration options available in the AI Agent Framework's YAML-based agent definitions.

## Configuration Schema Overview

Every agent configuration follows this structure:

```yaml
apiVersion: agent.framework/v2
kind: Agent | ManagerAgent

metadata:
  name: string
  description: string (optional)
  version: string (optional)

resources:
  inference_gateways: [...]
  tools: [...]
  subscribers: [...]

spec:
  policies: {...}
  planner: {...}
  memory: {...}
  tools: [...]
  subscribers: [...]
  workers: [...]  # ManagerAgent only
```

---

## Top-Level Fields

### `apiVersion` (required)

Specifies the configuration schema version.

```yaml
apiVersion: agent.framework/v2
```

**Valid values:** `agent.framework/v2`

---

### `kind` (required)

Specifies the type of agent to create.

```yaml
kind: Agent
# or
kind: ManagerAgent
```

| Value | Description |
|-------|-------------|
| `Agent` | Single worker agent with tools and planner |
| `ManagerAgent` | Orchestrator that delegates to worker agents |

---

### `metadata` (required)

Agent identification and documentation.

```yaml
metadata:
  name: ResearchWorker
  description: Research assistant that searches and takes notes
  version: 1.0.0
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Unique identifier for the agent |
| `description` | string | No | Human-readable description |
| `version` | string | No | Semantic version (e.g., "1.0.0") |

---

## Resources Section

Define reusable components that can be referenced in the spec.

### `inference_gateways`

LLM provider configurations.

```yaml
resources:
  inference_gateways:
    - name: openai-main
      type: OpenAIGateway
      config:
        model: ${OPENAI_MODEL:-gpt-4o-mini}
        api_key: ${OPENAI_API_KEY}
        temperature: 0.1
        use_function_calling: true
```

#### Available Gateway Types

| Type | Description | Required Config |
|------|-------------|-----------------|
| `OpenAIGateway` | OpenAI API | `api_key`, `model` |
| `AnthropicGateway` | Anthropic Claude | `api_key`, `model` |
| `MockGateway` | For testing | None |

#### OpenAIGateway Config Options

```yaml
config:
  api_key: ${OPENAI_API_KEY}           # Required
  model: gpt-4o-mini                    # Required
  temperature: 0.1                      # Optional (0.0-2.0)
  max_tokens: 4096                      # Optional
  use_function_calling: true            # Optional (default: false)
  timeout: 30                           # Optional (seconds)
```

---

### `tools`

Tool definitions for the agent.

```yaml
resources:
  tools:
    - name: web_search
      type: MockSearchTool
      config: {}

    - name: note_taker
      type: NoteTakerTool
      config:
        storage_path: /tmp/notes.json
```

#### Built-in Tool Types

| Type | Description | Config Options |
|------|-------------|----------------|
| `MockSearchTool` | Simulated web search | None |
| `NoteTakerTool` | Create and store notes | `storage_path` |
| `TaskManagerTool` | Create tasks | None |
| `ListTasksTool` | List existing tasks | None |
| `CompleteTaskTool` | Mark tasks complete | None |
| `WeatherLookupTool` | Get weather data | None |
| `CalculatorTool` | Math calculations | None |

---

### `subscribers`

Event subscribers for logging and monitoring.

```yaml
resources:
  subscribers:
    - name: logging
      type: PhoenixSubscriber
      config:
        level: INFO
        include_data: true
        max_payload_chars: 2000
```

#### Available Subscriber Types

| Type | Description | Config Options |
|------|-------------|----------------|
| `PhoenixSubscriber` | Arize Phoenix integration | `level`, `include_data`, `max_payload_chars` |
| `ConsoleSubscriber` | Console logging | `level` |

---

## Spec Section

The main agent behavior configuration.

### `policies`

Control agent behavior with presets or custom policies.

#### Using Presets (Recommended)

```yaml
spec:
  policies:
    $preset: simple
```

**Available Presets:**

| Preset | Best For | Features |
|--------|----------|----------|
| `simple` | Basic workers | Completion detection, loop prevention, 10 max iterations |
| `manager_with_followups` | Orchestrators | Follow-up phases, completion tracking |
| `with_hitl` | Human oversight | Human-in-the-loop approval for writes |
| `with_checkpoints` | Long tasks | Periodic state checkpointing |

#### Overriding Preset Values

```yaml
spec:
  policies:
    $preset: simple
    termination:
      type: DefaultTerminationPolicy
      config:
        max_iterations: 20  # Override default
        on_max_iterations: error
```

#### Full Custom Policy Configuration

```yaml
spec:
  policies:
    completion:
      type: DefaultCompletionDetector
      config:
        indicators: [completed, success, done, finished]
        check_response_validation: true
        check_history_depth: 10

    termination:
      type: DefaultTerminationPolicy
      config:
        max_iterations: 10
        check_completion: true
        terminal_tools: []
        on_max_iterations: error  # or "warn"

    loop_prevention:
      type: DefaultLoopPreventionPolicy
      config:
        enabled: true
        action_window: 5
        observation_window: 5
        repetition_threshold: 3

    hitl:
      type: DefaultHITLPolicy
      config:
        enabled: false
        scope: writes  # or "all"

    checkpoint:
      type: DefaultCheckpointPolicy
      config:
        enabled: false
        checkpoint_after_iterations: 5
```

---

### `planner`

Configures the planning/reasoning component.

#### ReActPlanner (Tool-using agents)

```yaml
spec:
  planner:
    type: ReActPlanner
    config:
      inference_gateway: openai-main
      use_function_calling: true
      max_iterations: 10
      system_prompt: |
        You are a helpful assistant.
        Use tools to accomplish tasks.
```

| Config Option | Type | Default | Description |
|---------------|------|---------|-------------|
| `inference_gateway` | string | Required | Reference to gateway in resources |
| `use_function_calling` | bool | false | Use OpenAI function calling |
| `max_iterations` | int | 10 | Max planning iterations |
| `system_prompt` | string | Required | System instructions |

#### WorkerRouterPlanner (For ManagerAgents)

```yaml
spec:
  planner:
    type: WorkerRouterPlanner
    config:
      inference_gateway: openai-orchestrator
      worker_keys: [research-worker, task-worker]
      default_worker: research-worker
      system_prompt: |
        Route requests to the appropriate worker.
        Return JSON: {"worker": "<key>", "reason": "..."}
```

| Config Option | Type | Default | Description |
|---------------|------|---------|-------------|
| `inference_gateway` | string | Required | Reference to gateway |
| `worker_keys` | list | Required | Available worker names |
| `default_worker` | string | Required | Fallback worker |
| `system_prompt` | string | Required | Routing instructions |

---

### `memory`

Configure agent memory and state sharing.

#### Using Presets (Recommended)

```yaml
spec:
  memory:
    $preset: worker
```

**Available Memory Presets:**

| Preset | Creates | Use For |
|--------|---------|---------|
| `standalone` | `InMemoryMemory` | Single isolated agents |
| `worker` | `SharedInMemoryMemory` | Worker agents in a team |
| `manager` | `HierarchicalSharedMemory` | Orchestrator agents |

Presets auto-derive:
- `namespace` from `JOB_ID` environment variable
- `agent_key` from `metadata.name`
- `subordinates` from `workers` list (manager preset)

#### Override Preset Defaults

```yaml
spec:
  memory:
    $preset: worker
    namespace: custom-namespace  # Override auto-derived value
```

#### Legacy Explicit Configuration

```yaml
spec:
  memory:
    type: SharedInMemoryMemory
    config:
      namespace: ${JOB_ID:-default}
      agent_key: my_agent
```

---

### `tools`

Reference tools from resources section.

```yaml
spec:
  tools: [web_search, note_taker, calculator]
```

---

### `subscribers`

Reference subscribers from resources section.

```yaml
spec:
  subscribers: [logging]
```

---

### `workers` (ManagerAgent only)

Define worker agents for orchestration.

```yaml
spec:
  workers:
    - name: research-worker
      config_path: configs/agents/research_worker.yaml

    - name: task-worker
      config_path: configs/agents/task_worker.yaml
```

---

## Environment Variable Substitution

Use `${VAR}` or `${VAR:-default}` syntax for environment variables.

```yaml
config:
  api_key: ${OPENAI_API_KEY}           # Required env var
  model: ${OPENAI_MODEL:-gpt-4o-mini}  # With default value
  namespace: ${JOB_ID:-default}        # With default
```

---

## Complete Examples

### Simple Worker Agent

```yaml
apiVersion: agent.framework/v2
kind: Agent

metadata:
  name: SimpleWorker
  description: Basic worker agent

resources:
  inference_gateways:
    - name: openai
      type: OpenAIGateway
      config:
        model: ${OPENAI_MODEL:-gpt-4o-mini}
        api_key: ${OPENAI_API_KEY}

  tools:
    - name: calculator
      type: CalculatorTool

spec:
  policies:
    $preset: simple

  planner:
    type: ReActPlanner
    config:
      inference_gateway: openai
      system_prompt: You are a helpful calculator assistant.

  memory:
    $preset: worker

  tools: [calculator]
```

### Manager with Workers

```yaml
apiVersion: agent.framework/v2
kind: ManagerAgent

metadata:
  name: Orchestrator

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
      worker_keys: [research, tasks]
      default_worker: research
      system_prompt: Route requests appropriately.

  memory:
    $preset: manager

  workers:
    - name: research
      config_path: configs/agents/research.yaml
    - name: tasks
      config_path: configs/agents/tasks.yaml
```

---

## Validation

The framework validates configurations at load time. Common errors:

| Error | Cause | Fix |
|-------|-------|-----|
| "Unknown component type" | Invalid type in registry | Check spelling of type names |
| "Missing required field" | Required config missing | Add the required field |
| "Policies are required" | No policies section | Add `policies: $preset: simple` |
| "Config file not found" | Invalid config_path | Check relative paths |
