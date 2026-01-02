---
title: Hierarchical History Filtering
---

# Hierarchical History Filtering

## Overview

Hierarchical history filtering ensures each agent role (orchestrator, manager, worker) receives appropriate history context for prompt building, preventing token waste and confusion from irrelevant context. This system filters conversation history based on the agent's role and current context.

## Problem Statement

Without hierarchical filtering, all planners receive the entire history, causing:

1. **Token Waste**: Unnecessary context included in prompts
2. **Context Confusion**: Irrelevant history pollutes decision-making
3. **Completion Signal Pollution**: Previous turn's completion signals confuse new turns
4. **No Role Separation**: Orchestrators see raw execution traces; workers see all conversation history

## Solution: Role-Based Filtering

The framework provides `HistoryFilter` implementations that filter history based on agent role:

```
┌─────────────────────────────────────────────────────────────┐
│  ORCHESTRATOR                                                │
│  Filter: OrchestratorHistoryFilter                          │
│  Sees: Conversation summary (last 8 turns)                  │
│  Excludes: Raw execution traces, tool results, completion   │
│           signals from previous turns                       │
└─────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│  MANAGER                                                     │
│  Filter: ManagerHistoryFilter                               │
│  Sees: Previous phase synthesis summaries only              │
│  Excludes: Full conversation history, raw execution traces, │
│           completion signals from other phases              │
└─────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────────────┐
│  WORKER                                                      │
│  Filter: WorkerHistoryFilter                                │
│  Sees: Current turn execution traces only                   │
│  Excludes: Previous turn's history, completion signals from │
│           previous turns, other workers' traces             │
└─────────────────────────────────────────────────────────────┘
```

## HistoryFilter Interface

The framework provides a `HistoryFilter` abstract base class:

```python
from agent_framework.policies.base import HistoryFilter

class HistoryFilter(ABC):
    """Filters history for role-specific prompt building."""
    
    @abstractmethod
    def filter_for_prompt(
        self,
        history: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Filter history for prompt building."""
        pass
```

### Built-in Filter Implementations

#### OrchestratorHistoryFilter

**Purpose**: High-level conversation summary for orchestrator strategic planning.

**What it includes:**
- Conversation turns (`user_message`, `assistant_message`) only
- Limited to last N turns (default: 8, configurable)

**What it excludes:**
- Raw execution traces (`action`, `observation`)
- Detailed tool results
- Previous turn completion signals
- Phase-specific details

**Usage:**
```python
from agent_framework.policies.history_filters import OrchestratorHistoryFilter

filter = OrchestratorHistoryFilter(max_conversation_turns=10)
filtered = filter.filter_for_prompt(
    history,
    {"role": "orchestrator", "max_conversation_turns": 10}
)
```

#### ManagerHistoryFilter

**Purpose**: Phase-relevant context for manager planning.

**What it includes:**
- Previous phase synthesis summaries (if sequential phases)
- Only entries relevant to current phase context (filtered by `phase_id`)

**What it excludes:**
- Full conversation history (orchestrator handles that)
- Raw execution traces from workers
- Completion signals from other phases

**Usage:**
```python
from agent_framework.policies.history_filters import ManagerHistoryFilter

filter = ManagerHistoryFilter()
filtered = filter.filter_for_prompt(
    history,
    {"phase_id": 2, "previous_phase_id": 1}
)
```

#### WorkerHistoryFilter

**Purpose**: Current turn execution traces for worker agents.

**What it includes:**
- Current turn execution traces only (after last `task` marker)
- Execution trace types (`action`, `observation`, `global_observation`)
- Tool results from current execution

**What it excludes:**
- Previous turn's history
- Completion signals from previous turns
- Other workers' execution traces (unless global)

**Usage:**
```python
from agent_framework.policies.history_filters import WorkerHistoryFilter

filter = WorkerHistoryFilter()
filtered = filter.filter_for_prompt(
    history,
    {"role": "worker"}
)
```

#### DefaultHistoryFilter

**Purpose**: Backward compatibility - returns all history unchanged.

**Usage:**
```python
from agent_framework.policies.history_filters import DefaultHistoryFilter

filter = DefaultHistoryFilter()
filtered = filter.filter_for_prompt(history, {})
# Returns: all history (no filtering)
```

## Integration with Planners

Filters are automatically applied by planners with sensible defaults:

### StrategicPlanner (Orchestrator)

Uses `OrchestratorHistoryFilter` by default:

```python
from agent_framework.components.planners import StrategicPlanner

planner = StrategicPlanner(
    worker_keys=["worker1", "worker2"],
    # Automatically uses OrchestratorHistoryFilter()
    inference_gateway=gateway
)
```

### StrategicDecomposerPlanner (Manager)

Uses `ManagerHistoryFilter` by default:

```python
from agent_framework.components.planners import StrategicDecomposerPlanner

planner = StrategicDecomposerPlanner(
    # Automatically uses ManagerHistoryFilter()
    inference_gateway=gateway
)
```

### ReActPlanner (Worker)

Uses `WorkerHistoryFilter` by default:

```python
from agent_framework.components.planners import ReActPlanner

planner = ReActPlanner(
    # Automatically uses WorkerHistoryFilter()
    inference_gateway=gateway
)
```

## Custom Filter Configuration

You can provide a custom filter to any planner:

```python
from agent_framework.components.planners import StrategicPlanner
from agent_framework.policies.history_filters import OrchestratorHistoryFilter

# Custom filter with specific turn limit
custom_filter = OrchestratorHistoryFilter(max_conversation_turns=5)

planner = StrategicPlanner(
    worker_keys=["worker1", "worker2"],
    history_filter=custom_filter,
    inference_gateway=gateway
)
```

## Turn Boundary Scoping

Filters use turn boundaries marked by `{"type": "task"}` entries. The framework provides a helper method:

```python
def _find_last_task_marker(self, history: List[Dict[str, Any]]) -> int:
    """Find index of last 'task' entry (marks turn boundary)."""
    for i in range(len(history) - 1, -1, -1):
        if history[i].get("type") == "task":
            return i
    return -1
```

This ensures:
- **Completion Detection**: Only checks entries after last `task` marker
- **Worker Filtering**: Only includes current turn traces
- **Turn Isolation**: Previous turns don't pollute current context

## Message Type Constants

The framework uses constants for message types (defined in `agent_framework.constants`):

```python
# Conversation types
USER_MESSAGE = "user_message"
ASSISTANT_MESSAGE = "assistant_message"

# Execution trace types
TASK = "task"
ACTION = "action"
OBSERVATION = "observation"
ERROR = "error"

# Completion types
FINAL = "final"
SYNTHESIS = "synthesis"

# Type collections
CONVERSATION_TYPES = [USER_MESSAGE, ASSISTANT_MESSAGE]
EXECUTION_TRACE_TYPES = [TASK, ACTION, OBSERVATION, ERROR]
COMPLETION_TYPES = [FINAL, SYNTHESIS]
```

Filters use these constants to categorize and filter history entries.

## Benefits

1. **Token Efficiency**: Only relevant context included per role
2. **Context Clarity**: No noise from irrelevant history
3. **No Completion Pollution**: Turn-scoped filtering prevents false positives
4. **Hierarchical Clarity**: Each role sees appropriate level of detail
5. **Better Performance**: Smaller prompts = faster LLM calls
6. **Backward Compatible**: Default filters match existing behavior

## Completion Detection Integration

The completion detection system also uses turn-scoped history to prevent false positives:

```python
# In DefaultCompletionDetector
def is_complete(self, result, history, context):
    # Only check current turn for completion signals
    current_turn_history = self._get_current_turn_history(history)
    
    # Check for completion signals in current turn only
    for entry in reversed(current_turn_history[-self.check_history_depth:]):
        if entry.get("type") in COMPLETION_TYPES:
            return True
    return False
```

This ensures previous turn completions don't trigger premature termination.

## Architecture Flow

```
User Message
    │
    ▼
Orchestrator (OrchestratorHistoryFilter)
├─ Sees: Last 8 conversation turns only
├─ Plans: High-level strategic plan
└─ Delegates: To managers with phase context
    │
    ▼
Manager (ManagerHistoryFilter)
├─ Sees: Previous phase synthesis only (if sequential)
├─ Plans: Phase-specific execution plan
└─ Delegates: To workers with task context
    │
    ▼
Worker (WorkerHistoryFilter)
├─ Sees: Current turn execution traces only
├─ Executes: Tools and actions
└─ Returns: Results to manager
    │
    ▼
Manager Synthesizes
    │
    ▼
Orchestrator Receives Result
```

## Backward Compatibility

✅ **Fully backward compatible**

- Default filters match existing behavior
- Filters can be disabled by passing `DefaultHistoryFilter()` (returns all history)
- No breaking API changes
- Existing code continues to work without modification

## Creating Custom Filters

You can create custom filters by implementing the `HistoryFilter` interface:

```python
from agent_framework.policies.base import HistoryFilter
from typing import Any, Dict, List

class CustomHistoryFilter(HistoryFilter):
    """Custom filter for specific use case."""
    
    def filter_for_prompt(
        self,
        history: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        # Your custom filtering logic
        filtered = [
            e for e in history
            if self._should_include(e, context)
        ]
        return filtered
    
    def _should_include(self, entry: Dict[str, Any], context: Dict[str, Any]) -> bool:
        # Your custom inclusion logic
        return True
```

## Planner Filter Usage

The framework applies filters automatically to core planners:

| Planner | Filter Used | Status |
|---------|-------------|--------|
| `StrategicPlanner` | `OrchestratorHistoryFilter` | ✅ Automatic |
| `StrategicDecomposerPlanner` | `ManagerHistoryFilter` | ✅ Automatic |
| `ReActPlanner` | `WorkerHistoryFilter` | ✅ Automatic |
| `ChatPlanner` | Manual filtering (conversation types only) | ⚠️ Manual |
| `WorkerRouterPlanner` | Manual filtering (conversation types only) | ⚠️ Manual |
| `ManagerScriptPlanner` | Manual filtering (synthesis entries) | ⚠️ Manual |

**Core planners** (Strategic, StrategicDecomposer, ReAct) use the filter system automatically.  
**Router/chat planners** use manual filtering appropriate for their simpler routing needs.

## Summary

The hierarchical filtering system provides:

- **Role-appropriate context**: Each agent role sees only relevant history
- **Automatic application**: Default filters applied automatically by core planners
- **Customizable**: Can provide custom filters per planner
- **Turn-scoped**: Prevents pollution from previous turns
- **Efficient**: Reduces token usage and improves performance
- **Compatible**: Backward compatible with existing code

The framework handles all filtering automatically for core planners, but you can customize it as needed for your specific use cases.

