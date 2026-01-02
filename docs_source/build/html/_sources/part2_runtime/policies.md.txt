# Policies & Presets

This chapter covers the policy system that controls agent behavior.

## Philosophy

Instead of hardcoding behavior, the framework uses **policies** that can be configured or replaced. This enables:

- Different behavior per environment (dev vs prod)
- Easy testing with modified policies
- Custom business rules without code changes

## Policy Types

### CompletionDetector

Determines when a task is complete.

```python
from agent_framework.policies.base import CompletionDetector

class CompletionDetector(ABC):
    @abstractmethod
    def is_complete(
        self,
        result: Any,
        history: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> bool:
        """Return True if task is complete."""
        pass
```

**Default implementation**:

```python
from agent_framework.policies.default import DefaultCompletionDetector

detector = DefaultCompletionDetector(
    indicators=["completed", "success", "done"],
    check_final_response=True,
    check_operation_types=["display_message", "model_ops"],
    check_response_validation=True,
    check_history_depth=10,
)
```

**Turn-scoped detection**: The detector only checks the current turn's history (after the last `task` entry) to avoid false positives from previous completions.

### TerminationPolicy

Determines when to stop agent execution.

```python
from agent_framework.policies.base import TerminationPolicy

class TerminationPolicy(ABC):
    @abstractmethod
    def should_terminate(
        self,
        iteration: int,
        plan_outcome: Any,
        history: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """Return (should_stop, reason)."""
        pass
```

**Default implementation**:

```python
from agent_framework.policies.default import DefaultTerminationPolicy

policy = DefaultTerminationPolicy(
    max_iterations=10,
    require_terminal_tool=False,
    terminal_tools=["complete_task"],
    check_completion=True,
    on_max_iterations="error",  # or "return_partial"
)
```

### LoopPreventionPolicy

Detects and prevents repeated actions.

```python
from agent_framework.policies.base import LoopPreventionPolicy

class LoopPreventionPolicy(ABC):
    @abstractmethod
    def is_stagnant(
        self,
        current_action: Any,
        action_history: List[Any],
        observation_history: List[Any],
        context: Dict[str, Any]
    ) -> bool:
        """Return True if agent is stuck in a loop."""
        pass
```

**Default implementation**:

```python
from agent_framework.policies.default import DefaultLoopPreventionPolicy

policy = DefaultLoopPreventionPolicy(
    enabled=True,
    action_window=5,       # Track last 5 actions
    observation_window=5,  # Track last 5 observations
    repetition_threshold=3,
    check_completion_in_loop=True,
    on_stagnation="error",
)
```

**Smart detection**: Only triggers when BOTH actions AND observations repeat, allowing retries with different outcomes.

### HITLPolicy (Human-in-the-Loop)

Controls when human approval is required.

```python
from agent_framework.policies.base import HITLPolicy

class HITLPolicy(ABC):
    @abstractmethod
    def requires_approval(
        self,
        action: Any,
        context: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """Return (needs_approval, reason)."""
        pass
```

**Default implementation**:

```python
from agent_framework.policies.default import DefaultHITLPolicy

policy = DefaultHITLPolicy(
    enabled=True,
    scope="writes",  # "all", "writes", "none"
    write_tools=["add_column", "update_measure", "delete_table"],
)
```

### CheckpointPolicy

Controls when to save execution state.

```python
from agent_framework.policies.base import CheckpointPolicy

class CheckpointPolicy(ABC):
    @abstractmethod
    def should_checkpoint(
        self,
        iteration: int,
        action: Any,
        result: Any,
        context: Dict[str, Any]
    ) -> bool:
        """Return True if state should be checkpointed."""
        pass
```

**Default implementation**:

```python
from agent_framework.policies.default import DefaultCheckpointPolicy

policy = DefaultCheckpointPolicy(
    enabled=True,
    checkpoint_after_iterations=5,
    checkpoint_on_operations=["display_table"],
)
```

### FollowUpPolicy

Controls manager follow-up phases.

```python
from agent_framework.policies.default import DefaultFollowUpPolicy

policy = DefaultFollowUpPolicy(
    enabled=True,
    max_phases=5,
    check_completion=True,
    stop_on_completion=True,
)
```

## Policy Presets

Use presets for common configurations (see :doc:`policy-presets` for full reference):

```python
from agent_framework import get_preset

# Available presets
policies = get_preset("simple")
policies = get_preset("manager_with_followups")
policies = get_preset("with_hitl")
policies = get_preset("with_checkpoints")
```

### Preset: `simple`

```python
{
    "completion": DefaultCompletionDetector(
        indicators=["completed", "success", "done", "finished", "task complete"],
        check_response_validation=True,
        check_operation_types=["display_message", "model_ops", "display_table"],
        check_history_depth=10
    ),
    "termination": DefaultTerminationPolicy(
        max_iterations=10,
        check_completion=True,
        terminal_tools=[],
        on_max_iterations="error"
    ),
    "loop_prevention": DefaultLoopPreventionPolicy(
        enabled=True,
        action_window=5,
        observation_window=5,
        repetition_threshold=3,
        check_completion_in_loop=True,
        on_stagnation="error"
    ),
    "hitl": DefaultHITLPolicy(enabled=False),
    "checkpoint": DefaultCheckpointPolicy(enabled=False),
}
```

### Preset: `with_hitl`

```python
{
    # ... same completion/termination/loop_prevention ...
    "hitl": DefaultHITLPolicy(
        enabled=True,
        scope="writes"
    ),
    "checkpoint": DefaultCheckpointPolicy(enabled=False),
}
```

### Preset: `with_checkpoints`

```python
{
    # ... same completion/termination/loop_prevention ...
    "hitl": DefaultHITLPolicy(enabled=False),
    "checkpoint": DefaultCheckpointPolicy(
        enabled=True,
        checkpoint_after_iterations=5,
        checkpoint_on_operations=["display_table"]
    ),
}
```

## Using Policies

### With Agent

```python
from agent_framework import Agent, get_preset

agent = Agent(
    planner=planner,
    memory=memory,
    tools=tools,
    policies=get_preset("simple"),  # Required
)
```

### Custom Policies

```python
from agent_framework.policies.default import (
    DefaultCompletionDetector,
    DefaultTerminationPolicy,
    DefaultLoopPreventionPolicy,
)

policies = {
    "completion": DefaultCompletionDetector(
        indicators=["done", "complete", "finished"],
        check_history_depth=5,
    ),
    "termination": DefaultTerminationPolicy(
        max_iterations=20,
        on_max_iterations="return_partial",
    ),
    "loop_prevention": DefaultLoopPreventionPolicy(
        repetition_threshold=5,
    ),
}

agent = Agent(
    planner=planner,
    memory=memory,
    tools=tools,
    policies=policies,
)
```

## YAML Configuration

```yaml
policies:
  completion:
    type: DefaultCompletionDetector
    config:
      indicators: ["completed", "success", "done"]
      check_history_depth: 10
  termination:
    type: DefaultTerminationPolicy
    config:
      max_iterations: 15
      on_max_iterations: error
  loop_prevention:
    type: DefaultLoopPreventionPolicy
    config:
      enabled: true
      repetition_threshold: 3
  hitl:
    type: DefaultHITLPolicy
    config:
      enabled: false
```

Or use a preset:

```yaml
policies:
  $preset: simple
```

## Custom Policy Example

```python
from agent_framework.policies.base import CompletionDetector

class DomainCompletionDetector(CompletionDetector):
    """Completion detector for domain-specific signals."""
    
    def __init__(self, required_fields: list):
        self.required_fields = required_fields
    
    def is_complete(self, result, history, context) -> bool:
        if not isinstance(result, dict):
            return False
        
        # Check if all required fields are present
        for field in self.required_fields:
            if field not in result:
                return False
        
        # Check for explicit completion marker
        return result.get("status") == "complete"

# Register for YAML use
from deployment.registry import register_policy
register_policy("DomainCompletionDetector", DomainCompletionDetector)
```

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `REACT_HITL_ENABLE` | Enable HITL globally |
| `REACT_HITL_SCOPE` | HITL scope (all, writes, none) |

## Best Practices

1. **Start with presets** and customize as needed
2. **Use `simple` preset** for development
3. **Enable HITL** for production write operations
4. **Configure checkpoints** for long-running tasks
5. **Tune loop prevention** based on task complexity
6. **Log policy decisions** for debugging
