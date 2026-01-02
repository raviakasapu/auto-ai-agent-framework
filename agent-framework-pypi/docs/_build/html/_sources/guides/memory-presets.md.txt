# Memory Presets Guide

Memory presets simplify agent memory configuration by providing pre-configured options that automatically derive values from the agent context.

## Overview

Instead of explicitly configuring memory type and parameters:

```yaml
# Legacy explicit configuration
memory:
  type: SharedInMemoryMemory
  config:
    namespace: ${JOB_ID:-default}
    agent_key: research_worker
```

You can use presets:

```yaml
# Preset-based configuration
memory:
  $preset: worker
  # namespace and agent_key auto-derived
```

## Available Presets

| Preset | Memory Type | Use Case |
|--------|-------------|----------|
| `standalone` | `InMemoryMemory` | Isolated single agents |
| `worker` | `SharedInMemoryMemory` | Worker agents in a team |
| `manager` | `HierarchicalSharedMemory` | Orchestrator agents |

---

## Standalone Preset

Use for agents that don't need to share state with other agents.

```yaml
spec:
  memory:
    $preset: standalone
```

**Creates:** `InMemoryMemory`

**Behavior:**
- Private message history
- No access to other agents' data
- Isolated state per agent instance

**Auto-derived values:**
- `agent_key`: From `metadata.name` (normalized to lowercase with underscores)

**Best for:**
- Single-purpose utility agents
- Agents that run independently
- Testing and development

---

## Worker Preset

Use for worker agents that participate in multi-agent systems.

```yaml
spec:
  memory:
    $preset: worker
```

**Creates:** `SharedInMemoryMemory`

**Behavior:**
- Shared namespace with other workers
- Sees own messages + global updates
- Can read shared state set by other agents

**Auto-derived values:**
- `namespace`: From `JOB_ID` environment variable (defaults to "default")
- `agent_key`: From `metadata.name` (normalized)

**Best for:**
- Worker agents under a manager
- Agents that need to share context
- Parallel task execution

---

## Manager Preset

Use for orchestrator agents that manage worker agents.

```yaml
spec:
  memory:
    $preset: manager
```

**Creates:** `HierarchicalSharedMemory`

**Behavior:**
- Full visibility into subordinate agent state
- Sees own messages + subordinate messages + global updates
- Can coordinate based on worker progress

**Auto-derived values:**
- `namespace`: From `JOB_ID` environment variable
- `agent_key`: From `metadata.name`
- `subordinates`: From `workers` list in spec

**Best for:**
- Orchestrator/manager agents
- Agents that route to workers
- Coordination and aggregation tasks

---

## Auto-Derivation Rules

### Namespace

Priority order:
1. Explicit `namespace` in memory config
2. `JOB_ID` from context
3. `JOB_ID` environment variable
4. Default: `"default"`

```yaml
# Uses JOB_ID from environment
memory:
  $preset: worker

# Override with explicit namespace
memory:
  $preset: worker
  namespace: my-custom-namespace
```

### Agent Key

Derived from `metadata.name` with normalization:
- Converted to lowercase
- Hyphens replaced with underscores
- Spaces replaced with underscores

```yaml
metadata:
  name: Research-Worker  # -> agent_key: "research_worker"

metadata:
  name: TaskManager      # -> agent_key: "taskmanager"
```

### Subordinates (Manager only)

Auto-derived from the `workers` list:

```yaml
spec:
  workers:
    - name: research-worker    # -> subordinate: "research_worker"
    - name: task-worker        # -> subordinate: "task_worker"

  memory:
    $preset: manager
    # subordinates: ["research_worker", "task_worker"] (auto-derived)
```

---

## Override Preset Defaults

You can override any auto-derived value:

```yaml
spec:
  memory:
    $preset: worker
    namespace: custom-job-123     # Override auto-derived namespace
```

---

## Memory Type Reference

### InMemoryMemory (standalone)

```python
class InMemoryMemory:
    """Isolated in-memory storage."""

    def add_message(self, role: str, content: str) -> None: ...
    def get_messages(self, limit: int = 100) -> List[Dict]: ...
    def clear(self) -> None: ...
    def set_state(self, key: str, value: Any) -> None: ...
    def get_state(self, key: str) -> Optional[Any]: ...
```

### SharedInMemoryMemory (worker)

```python
class SharedInMemoryMemory:
    """Shared memory for worker agents."""

    # All InMemoryMemory methods plus:
    def get_shared_state(self, key: str) -> Optional[Any]: ...
    def set_shared_state(self, key: str, value: Any) -> None: ...
```

### HierarchicalSharedMemory (manager)

```python
class HierarchicalSharedMemory:
    """Hierarchical memory that sees subordinate state."""

    # All SharedInMemoryMemory methods plus:
    def get_subordinate_messages(self, subordinate: str) -> List[Dict]: ...
    def get_all_subordinate_messages(self) -> Dict[str, List[Dict]]: ...
```

---

## Complete Examples

### Standalone Agent

```yaml
apiVersion: agent.framework/v2
kind: Agent

metadata:
  name: CalculatorBot

spec:
  policies:
    $preset: simple

  planner:
    type: ReActPlanner
    config:
      inference_gateway: openai
      system_prompt: You are a calculator.

  memory:
    $preset: standalone  # Isolated, no sharing

  tools: [calculator]
```

### Worker in Team

```yaml
apiVersion: agent.framework/v2
kind: Agent

metadata:
  name: ResearchWorker

spec:
  policies:
    $preset: simple

  planner:
    type: ReActPlanner
    config:
      inference_gateway: openai
      system_prompt: You are a research assistant.

  memory:
    $preset: worker  # Shares with team via JOB_ID namespace

  tools: [web_search, note_taker]
```

### Manager with Workers

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
      worker_keys: [research-worker, task-worker]
      default_worker: research-worker

  memory:
    $preset: manager  # Sees all subordinate state

  workers:
    - name: research-worker
      config_path: configs/agents/research_worker.yaml
    - name: task-worker
      config_path: configs/agents/task_worker.yaml
```

---

## Programmatic Usage

```python
from agent_framework.components.memory_presets import (
    get_memory_preset,
    list_memory_presets,
    describe_preset,
)

# List available presets
presets = list_memory_presets()
# ['standalone', 'worker', 'manager']

# Get preset description
desc = describe_preset("worker")
# "Shared memory for worker agents. Sees own messages + global updates."

# Create memory from preset
memory = get_memory_preset("worker", {
    "agent_name": "ResearchWorker",
    "namespace": "my-job-123",
})

# For manager preset
memory = get_memory_preset("manager", {
    "agent_name": "Orchestrator",
    "subordinates": ["research-worker", "task-worker"],
})
```

---

## Best Practices

1. **Use presets** instead of explicit configuration for cleaner configs
2. **Set JOB_ID** environment variable for multi-agent job isolation
3. **Let agent_key auto-derive** from metadata.name for consistency
4. **Use manager preset** only for ManagerAgent kinds
5. **Use worker preset** for all agents in a multi-agent team
6. **Use standalone preset** for isolated utility agents
