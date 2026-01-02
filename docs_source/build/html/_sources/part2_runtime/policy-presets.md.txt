# Policy Presets Guide

Policy presets provide pre-configured behavior policies for common agent patterns. They control termination, completion detection, loop prevention, human-in-the-loop, and checkpointing.

## Overview

Instead of configuring each policy manually:

```yaml
# Verbose explicit configuration
spec:
  policies:
    completion:
      type: DefaultCompletionDetector
      config:
        indicators: [completed, success, done]
    termination:
      type: DefaultTerminationPolicy
      config:
        max_iterations: 10
        check_completion: true
    loop_prevention:
      type: DefaultLoopPreventionPolicy
      config:
        enabled: true
```

Use presets for common patterns:

```yaml
# Preset-based configuration
spec:
  policies:
    $preset: simple
```

## Available Presets

| Preset | Best For | Key Features |
|--------|----------|--------------|
| `simple` | Basic workers | Completion detection, loop prevention, 10 max iterations |
| `manager_with_followups` | Orchestrators | Follow-up phases, completion tracking |
| `with_hitl` | Human oversight | Human-in-the-loop approval for write operations |
| `with_checkpoints` | Long tasks | Periodic state checkpointing |

---

## Simple Preset

The default preset for worker agents with sensible defaults.

```yaml
spec:
  policies:
    $preset: simple
```

**Included Policies:**

| Policy | Configuration |
|--------|---------------|
| `completion` | Detects completion indicators in responses |
| `termination` | 10 max iterations, errors on max |
| `loop_prevention` | Detects stagnation and repetition |
| `hitl` | Disabled |
| `checkpoint` | Disabled |

**Default Configuration:**

```yaml
completion:
  indicators: [completed, success, done, finished, task complete]
  check_response_validation: true
  check_operation_types: [display_message, model_ops, display_table]
  check_history_depth: 10

termination:
  max_iterations: 10
  check_completion: true
  terminal_tools: []
  on_max_iterations: error

loop_prevention:
  enabled: true
  action_window: 5
  observation_window: 5
  repetition_threshold: 3
  check_completion_in_loop: true
  on_stagnation: error
```

---

## Manager with Followups Preset

For manager/orchestrator agents that coordinate worker agents.

```yaml
spec:
  policies:
    $preset: manager_with_followups
```

**Included Policies:**

| Policy | Configuration |
|--------|---------------|
| `completion` | Detects completion indicators |
| `follow_up` | Enables multi-phase follow-up |
| `loop_prevention` | Basic stagnation detection |

**Default Configuration:**

```yaml
completion:
  indicators: [completed, success, done]
  check_response_validation: true

follow_up:
  enabled: true
  max_phases: 5
  check_completion: true
  stop_on_completion: true

loop_prevention:
  enabled: true
```

**Use Cases:**
- Multi-worker orchestration
- Tasks requiring multiple rounds of worker coordination
- Aggregation and synthesis workflows

---

## With HITL Preset

For workflows requiring human approval before certain operations.

```yaml
spec:
  policies:
    $preset: with_hitl
```

**Included Policies:**

| Policy | Configuration |
|--------|---------------|
| `completion` | Detects completion indicators |
| `termination` | 15 max iterations |
| `loop_prevention` | Repetition detection |
| `hitl` | Enabled for write operations |
| `checkpoint` | Disabled |

**Default Configuration:**

```yaml
completion:
  indicators: [completed, success, done]
  check_response_validation: true

termination:
  max_iterations: 15
  check_completion: true

loop_prevention:
  enabled: true
  repetition_threshold: 3

hitl:
  enabled: true
  scope: writes  # Requires approval for write operations
```

**Scope Options:**
- `writes`: Approval required for write/modify operations
- `all`: Approval required for all tool calls

---

## With Checkpoints Preset

For long-running tasks that benefit from periodic state saving.

```yaml
spec:
  policies:
    $preset: with_checkpoints
```

**Included Policies:**

| Policy | Configuration |
|--------|---------------|
| `completion` | Detects completion indicators |
| `termination` | 20 max iterations |
| `loop_prevention` | Basic stagnation detection |
| `hitl` | Disabled |
| `checkpoint` | Enabled every 5 iterations |

**Default Configuration:**

```yaml
completion:
  indicators: [completed, success, done]

termination:
  max_iterations: 20
  check_completion: true

loop_prevention:
  enabled: true

checkpoint:
  enabled: true
  checkpoint_after_iterations: 5
  checkpoint_on_operations: [display_table]
```

---

## Overriding Preset Values

Override specific policies while keeping preset defaults:

```yaml
spec:
  policies:
    $preset: simple
    # Override termination policy
    termination:
      type: DefaultTerminationPolicy
      config:
        max_iterations: 20
        on_max_iterations: warn  # Warn instead of error
```

---

## Policy Types Reference

### DefaultCompletionDetector

Detects when an agent has completed its task.

```yaml
completion:
  type: DefaultCompletionDetector
  config:
    indicators: [completed, success, done, finished]
    check_response_validation: true
    check_operation_types: [display_message, model_ops]
    check_history_depth: 10
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `indicators` | list | See above | Words indicating completion |
| `check_response_validation` | bool | true | Check for validation markers |
| `check_operation_types` | list | [] | Operation types to check |
| `check_history_depth` | int | 10 | Messages to scan |

---

### DefaultTerminationPolicy

Controls when agent execution stops.

```yaml
termination:
  type: DefaultTerminationPolicy
  config:
    max_iterations: 10
    check_completion: true
    terminal_tools: []
    on_max_iterations: error
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `max_iterations` | int | 10 | Maximum loop iterations |
| `check_completion` | bool | true | Stop on completion detection |
| `terminal_tools` | list | [] | Tools that signal termination |
| `on_max_iterations` | string | "error" | Action on max: "error" or "warn" |

---

### DefaultLoopPreventionPolicy

Prevents agent from getting stuck in loops.

```yaml
loop_prevention:
  type: DefaultLoopPreventionPolicy
  config:
    enabled: true
    action_window: 5
    observation_window: 5
    repetition_threshold: 3
    check_completion_in_loop: true
    on_stagnation: error
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | bool | true | Enable loop detection |
| `action_window` | int | 5 | Actions to compare |
| `observation_window` | int | 5 | Observations to compare |
| `repetition_threshold` | int | 3 | Repeats before stagnation |
| `check_completion_in_loop` | bool | true | Check for completion in loop |
| `on_stagnation` | string | "error" | Action: "error" or "warn" |

---

### DefaultHITLPolicy

Human-in-the-loop approval for operations.

```yaml
hitl:
  type: DefaultHITLPolicy
  config:
    enabled: false
    scope: writes
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | bool | false | Enable HITL |
| `scope` | string | "writes" | "writes" or "all" |

---

### DefaultCheckpointPolicy

Periodic state checkpointing.

```yaml
checkpoint:
  type: DefaultCheckpointPolicy
  config:
    enabled: false
    checkpoint_after_iterations: 5
    checkpoint_on_operations: []
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | bool | false | Enable checkpointing |
| `checkpoint_after_iterations` | int | 5 | Iterations between checkpoints |
| `checkpoint_on_operations` | list | [] | Operations that trigger checkpoint |

---

### DefaultFollowUpPolicy

Multi-phase follow-up for manager agents.

```yaml
follow_up:
  type: DefaultFollowUpPolicy
  config:
    enabled: true
    max_phases: 5
    check_completion: true
    stop_on_completion: true
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | bool | true | Enable follow-up phases |
| `max_phases` | int | 5 | Maximum follow-up phases |
| `check_completion` | bool | true | Check completion each phase |
| `stop_on_completion` | bool | true | Stop on task completion |

---

## Complete Examples

### Worker with Custom Termination

```yaml
apiVersion: agent.framework/v2
kind: Agent

metadata:
  name: LongRunningWorker

spec:
  policies:
    $preset: simple
    termination:
      type: DefaultTerminationPolicy
      config:
        max_iterations: 30
        on_max_iterations: warn

  planner:
    type: ReActPlanner
    config:
      inference_gateway: openai
      system_prompt: You are a thorough researcher.

  memory:
    $preset: worker

  tools: [web_search, note_taker]
```

### Manager with Follow-ups

```yaml
apiVersion: agent.framework/v2
kind: ManagerAgent

metadata:
  name: Orchestrator

spec:
  policies:
    $preset: manager_with_followups

  planner:
    type: WorkerRouterPlanner
    config:
      inference_gateway: openai
      worker_keys: [research, tasks]
      default_worker: research

  memory:
    $preset: manager

  workers:
    - name: research
      config_path: configs/agents/research.yaml
    - name: tasks
      config_path: configs/agents/tasks.yaml
```

### Agent with Human Approval

```yaml
apiVersion: agent.framework/v2
kind: Agent

metadata:
  name: CriticalWriter

spec:
  policies:
    $preset: with_hitl
    hitl:
      type: DefaultHITLPolicy
      config:
        enabled: true
        scope: all  # Require approval for ALL operations

  planner:
    type: ReActPlanner
    config:
      inference_gateway: openai
      system_prompt: You handle critical data operations.

  memory:
    $preset: standalone

  tools: [data_writer, data_deleter]
```

---

## Programmatic Usage

```python
from agent_framework.policies.presets import get_preset, list_presets

# List available presets
presets = list_presets()
# ['simple', 'manager_with_followups', 'with_hitl', 'with_checkpoints']

# Get a preset's policy configuration
policies = get_preset("simple")
# Returns dict with completion, termination, loop_prevention, hitl, checkpoint
```

---

## Best Practices

1. **Start with `simple`** for most worker agents
2. **Use `manager_with_followups`** for orchestrators
3. **Override sparingly** - presets are designed for common cases
4. **Increase `max_iterations`** for complex tasks, not as default
5. **Enable `hitl`** for production systems with critical operations
6. **Use `checkpoints`** for long-running tasks that may need recovery
