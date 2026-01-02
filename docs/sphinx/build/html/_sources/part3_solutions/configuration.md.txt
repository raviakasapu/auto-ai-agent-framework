# Declarative Configuration & AgentFactory

This chapter covers YAML-based agent configuration and the factory pattern.

## Overview

The framework supports two configuration approaches:

1. **Programmatic** — Create agents in Python code
2. **Declarative** — Define agents in YAML files, load via factory

## YAML Configuration Structure

```yaml
# configs/agents/my_agent.yaml
name: my_agent
type: Agent  # or ManagerAgent

# Resources: tools, gateways, etc.
resources:
  tools:
    - name: calculator
      type: CalculatorTool
      config: {}
  gateways:
    - name: openai-main
      type: OpenAIGateway
      config:
        model: gpt-4o
        temperature: 0.7

# Agent specification
spec:
  planner:
    type: ReActPlanner
    config:
      inference_gateway: openai-main
      include_history: true
  memory:
    type: SharedInMemoryMemory
    config:
      namespace: ${JOB_ID}
      agent_key: my_agent
  tools: [calculator]
  policies:
    preset: simple
```

## AgentFactory

The factory loads YAML and creates agent instances:

```python
from deployment.factory import AgentFactory

# Load from YAML file
agent = AgentFactory.create_from_yaml("configs/agents/my_agent.yaml")

# Run the agent
result = await agent.run("Calculate 2 + 2")
```

### Factory Features

- **Component resolution** — Resolves `type` to registered classes
- **Variable expansion** — Expands `${VAR}` from environment/context
- **Preset loading** — Loads policy presets by name
- **Resource wiring** — Connects tools, gateways, memory

## Component Registration

Register custom components for YAML use:

```python
from deployment.registry import (
    register_tool,
    register_planner,
    register_memory,
    register_gateway,
    register_policy,
)

# Register a tool
from my_tools import MyCustomTool
register_tool("MyCustomTool", MyCustomTool)

# Register a planner
from my_planners import MyPlanner
register_planner("MyPlanner", MyPlanner)
```

## Configuration Sections

### Resources

Define reusable components:

```yaml
resources:
  tools:
    - name: calculator
      type: CalculatorTool
      config: {}
    - name: search
      type: SearchTool
      config:
        api_key: ${SEARCH_API_KEY}
  
  gateways:
    - name: openai-strategic
      type: OpenAIGateway
      config:
        model: gpt-4o
    - name: openai-worker
      type: OpenAIGateway
      config:
        model: gpt-4o-mini
```

### Planner

Configure the planner type and settings:

```yaml
spec:
  planner:
    type: ReActPlanner
    config:
      inference_gateway: openai-worker
      include_history: true
      max_history_messages: 20
      system_prompt: |
        You are a helpful assistant with access to tools.
        Always explain your reasoning.
```

### Memory

Configure memory storage:

```yaml
spec:
  memory:
    type: SharedInMemoryMemory
    config:
      namespace: ${JOB_ID}
      agent_key: my_agent

# Or use MessageStoreMemory
spec:
  memory:
    type: MessageStoreMemory
    config:
      location: ${JOB_ID}
      agent_key: my_agent
```

### Policies

Use presets or configure individually:

```yaml
# Using a preset
spec:
  policies:
    preset: simple

# Or configure each policy
spec:
  policies:
    completion:
      type: DefaultCompletionDetector
      config:
        indicators: ["done", "complete"]
    termination:
      type: DefaultTerminationPolicy
      config:
        max_iterations: 15
    loop_prevention:
      type: DefaultLoopPreventionPolicy
      config:
        repetition_threshold: 3
```

### Tools List

Reference tools from resources:

```yaml
spec:
  tools: [calculator, search, analyzer]
```

## Manager Agent Configuration

```yaml
name: orchestrator
type: ManagerAgent

resources:
  gateways:
    - name: openai-strategic
      type: OpenAIGateway
      config:
        model: gpt-4o

spec:
  planner:
    type: StrategicPlanner
    config:
      inference_gateway: openai-strategic
      planning_prompt: |
        Create a strategic plan for the task.
  
  memory:
    type: SharedInMemoryMemory
    config:
      namespace: ${JOB_ID}
      agent_key: orchestrator
  
  # Workers are other agents
  workers:
    - analysis_manager
    - design_manager
  
  # Optional synthesis
  synthesis_gateway: openai-strategic
```

## Variable Expansion

YAML supports environment and context variables:

```yaml
config:
  api_key: ${OPENAI_API_KEY}        # From environment
  namespace: ${JOB_ID}              # From request context
  model_dir: ${MODEL_DIR:/default}  # With default value
```

### Setting Context Variables

```python
from agent_framework.services.request_context import set_request_context

# Before loading agent
set_request_context({
    "JOB_ID": "job_12345",
    "USER_ID": "user_abc",
})

agent = AgentFactory.create_from_yaml("my_agent.yaml")
```

## Configuration Inheritance

Agents can reference shared configurations:

```yaml
# configs/shared/base_worker.yaml
type: Agent
spec:
  policies:
    preset: simple
  memory:
    type: SharedInMemoryMemory
    config:
      namespace: ${JOB_ID}

# configs/agents/specific_worker.yaml
extends: shared/base_worker.yaml
name: specific_worker
resources:
  tools:
    - name: my_tool
      type: MyTool
spec:
  tools: [my_tool]
```

## Agent Config Schema

Reference for all configuration options:

| Section | Key | Type | Description |
|---------|-----|------|-------------|
| `name` | — | string | Agent identifier |
| `type` | — | string | `Agent` or `ManagerAgent` |
| `resources.tools` | `name` | string | Tool identifier |
| `resources.tools` | `type` | string | Registered tool class |
| `resources.tools` | `config` | object | Tool constructor args |
| `resources.gateways` | `name` | string | Gateway identifier |
| `resources.gateways` | `type` | string | Gateway class |
| `resources.gateways` | `config` | object | Gateway constructor args |
| `spec.planner` | `type` | string | Planner class |
| `spec.planner` | `config` | object | Planner constructor args |
| `spec.memory` | `type` | string | Memory class |
| `spec.memory` | `config` | object | Memory constructor args |
| `spec.tools` | — | list | Tool names to include |
| `spec.policies` | `preset` | string | Preset name |
| `spec.workers` | — | list | Worker agent names (ManagerAgent) |

## Best Practices

1. **Use environment variables** for secrets
2. **Use `${JOB_ID}`** for request-scoped namespaces
3. **Define gateways in resources** for reuse
4. **Use presets** for standard policy configurations
5. **Keep configs in version control** for reproducibility
6. **Validate configs** before deployment

