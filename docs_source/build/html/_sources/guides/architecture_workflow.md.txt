# Framework Architecture & Workflow

This document describes the core architecture and execution workflow of the AI Agent Framework. It covers the generic framework capabilities that can be used to build any agentic application.

## High-Level Architecture

The framework supports a hierarchical agent architecture:

```
User Request
  ↓
Orchestrator (ManagerAgent)
  ├─ Uses: StrategicPlanner
  ├─ Workers: [domain_manager_1, domain_manager_2, ...]
  └─ Delegates to: Domain Managers
       ↓
Domain Manager (ManagerAgent)
  ├─ Uses: StrategicDecomposerPlanner or WorkerRouterPlanner
  ├─ Workers: [worker_1, worker_2, ...]
  └─ Delegates to:
       ├─ Worker Agent (Agent) - Tool execution
       └─ Worker Agent (Agent) - Tool execution
```

## Core Components

### Agent Types

| Component | Type | Planner | Memory | Role |
|-----------|------|---------|--------|------|
| Orchestrator | ManagerAgent | StrategicPlanner | BaseMemory | Creates multi-step plans, routes to domain managers |
| Domain Manager | ManagerAgent | StrategicDecomposerPlanner or WorkerRouterPlanner | BaseMemory | Decomposes plans, coordinates workers |
| Worker Agent | Agent | ReActPlanner or other | BaseMemory | Executes tools, completes tasks |

### Key Framework Classes

- **`Agent`** (`agent_framework.core.agent`): Policy-driven execution engine for tool execution
- **`ManagerAgent`** (`agent_framework.core.manager_v2`): Policy-driven manager with delegation and synthesis
- **`EventBus`** (`agent_framework.core.events`): Event publishing system for observability
- **`BaseMemory`**: Abstract memory interface for history management
- **`BasePlanner`**: Abstract planner interface for decision-making
- **`BaseTool`**: Abstract tool interface for domain operations

## Request Lifecycle

### Step 1: Request Initialization

The implementation (e.g., `main.py`) initializes the request:

```python
# Generate unique job_id
job_id = "req_12345"

# Set request context (async-safe with contextvars)
set_request_context({
    "job_id": job_id,
    "JOB_ID": job_id,  # For YAML expansion
    "user_id": user_id
})

# Store user message in conversation feed
message_store.append_conversation_turn(job_id, "user", user_message)
```

**Critical**: Uses `contextvars` (NOT `threading.local`) for async-safety in FastAPI/asyncio environments.

### Step 2: Agent Loading

Agents are loaded with memory configured to use the `job_id` namespace:

```yaml
memory:
  type: MessageStoreMemory  # or SharedInMemoryMemory
  namespace: ${JOB_ID}  # Expands to "req_12345"
  agent_key: orchestrator
```

All agents in the hierarchy share the same namespace for context propagation.

### Step 3: Orchestrator Planning

The orchestrator receives the task and plans execution:

```python
# Orchestrator.run(task="Analyze data model")
history = memory.get_history()  # Gets conversation + traces
decision = planner.plan(task, history)  # StrategicPlanner creates plan

# Returns Action(delegate, worker="domain_manager")
```

### Step 4: Manager Delegation

The domain manager receives the task and delegates to workers:

```python
# ManagerAgent.run(task="Analyze data model")
history = memory.get_history()  # Gets full context
decision = planner.plan(task, history)  # Routes to worker

# Returns Action(delegate, worker="worker_agent")
worker_result = await worker.run(task)
```

### Step 5: Worker Tool Execution

The worker agent executes tools:

```python
# Agent.run(task="List columns")
history = memory.get_history()  # Gets conversation + own traces
decision = planner.plan(task, history)  # ReActPlanner selects tools

# Returns [Action(tool="list_columns", args={...}), ...]
results = await _execute_actions(actions)  # Parallel execution supported
```

## Memory & Context Visibility

### Worker Agent Memory

Workers see:
- Conversation messages (user/assistant)
- Own execution traces (action/observation)
- Global updates (namespace-level)

### Manager Agent Memory

Managers see:
- Own delegation traces
- All team workers' execution traces
- Global updates

### Memory Implementations

- **`SharedInMemoryMemory`**: In-memory storage with namespace isolation
- **`MessageStoreMemory`**: Reads from `BaseMessageStore` interface
- **`HierarchicalMessageStoreMemory`**: Manager memory that aggregates subordinate traces

## Parallel Execution

### Parallel Tool Execution

Workers can execute multiple tools simultaneously:

```python
# Planner returns multiple actions
actions = [
    Action(tool="list_columns", args={"table": "Sales"}),
    Action(tool="list_columns", args={"table": "Customers"})
]

# Execute in parallel
results = await asyncio.gather(*[tool.execute(**args) for action in actions])

# Aggregate results
aggregated = _aggregate_parallel_results(actions, results)
```

The framework intelligently aggregates:
- **Homogeneous** (same tool): Merges results into unified structure
- **Heterogeneous** (mixed tools): Creates sections per tool type

### Parallel Manager Delegation

Orchestrators can delegate to multiple managers concurrently:

```python
# Strategic plan includes parallel_workers
plan = {
    "parallel_workers": ["manager_1", "manager_2"]
}

# Execute in parallel
results = await asyncio.gather(*[delegate(worker) for worker in workers])

# Aggregate at orchestrator level
aggregated = _aggregate_parallel_manager_results(actions, results)
```

## Synthesis

Managers can optionally synthesize worker results using an LLM:

```python
# ManagerAgent with synthesis_gateway configured
if self.synthesis_gateway:
    synthesized = await _synthesize_result(task, worker_key, result)
    return synthesized
```

Synthesis receives:
- Original user question
- Strategic plan from orchestrator
- Recent conversation history
- Worker execution results

## Stagnation Detection

The framework includes intelligent stagnation detection:

```python
# Tracks both actions and observations
action_history = deque(maxlen=5)  # Last 5 actions
observation_history = deque(maxlen=5)  # Last 5 observations

# Stagnation detected when:
# 1. Same action repeated 3+ times
# 2. AND same observation repeated 3+ times
```

**Benefits**:
- Allows retry with different approaches
- Allows same action if results change (progress)
- Only flags true stuck states

## Error Handling

Tool execution errors are handled gracefully:

```python
try:
    result = tool.execute(**args)
except Exception as e:
    # Convert to structured error
    error_dict = {
        "success": False,
        "error": True,
        "error_message": str(e),
        "error_type": type(e).__name__
    }
    # Add to memory as observation
    memory.add({"type": "error", "content": error_dict})
    # Planner sees error and can try different approach
```

## Request Context (Async-Safe)

The framework uses `contextvars` for request-scoped data:

```python
# Set at request start
set_request_context({
    "job_id": "req_12345",
    "JOB_ID": "req_12345",
    "strategic_plan": {...}
})

# Access from anywhere
job_id = get_from_context("job_id")
plan = get_from_context("strategic_plan")
```

**Why contextvars?**
- FastAPI/Starlette uses asyncio (not threads)
- Multiple async tasks can run in same thread
- `threading.local()` would cause cross-contamination
- `contextvars` provides proper async task isolation

## Event System

The framework publishes events for observability:

- **`agent_start`**: Worker agent begins
- **`agent_end`**: Worker agent completes
- **`manager_start`**: Manager begins
- **`manager_end`**: Manager completes
- **`action_planned`**: Tool call planned
- **`action_executed`**: Tool executed
- **`delegation_planned`**: Manager plans delegation
- **`delegation_chosen`**: Worker selected
- **`delegation_executed`**: Worker completed
- **`worker_tool_call`**: Tool call initiated (lightweight)
- **`worker_tool_result`**: Tool result available
- **`error`**: Error occurred

See [Event System](event_system.md) for details.

## Key Design Principles

### Context Propagation (Async-Safe)
- Uses `contextvars` for request-scoped data
- Conversation history stored at namespace level
- All agents access same namespace (`job_id`)
- Context propagated to `ThreadPoolExecutor` via `context.run()`

### Parallel Execution
- Workers can execute multiple tools simultaneously
- All results recorded to memory individually
- Results intelligently aggregated before returning
- Managers receive complete, unified data

### Memory Visibility
- **Workers**: See conversation + own traces + global updates
- **Managers**: See own traces + all team workers' traces + global updates
- **Orchestrators**: See conversation + own traces + global updates

### Policy-Driven Behavior
- Completion detection: Configurable policies
- Loop prevention: Tracks actions + observations
- HITL (Human-in-the-Loop): Optional approval gates
- Termination: Configurable max iterations

## Configuration

Agents are configured via YAML files:

```yaml
name: orchestrator
type: ManagerAgent
planner:
  type: StrategicPlanner
  config:
    model: gpt-4o
memory:
  type: MessageStoreMemory
  namespace: ${JOB_ID}
workers:
  - domain_manager_1
  - domain_manager_2
policies:
  completion: DefaultCompletionDetector
  follow_up: DefaultFollowUpPolicy
  loop_prevention: DefaultLoopPreventionPolicy
```

## Environment Variables

Framework-specific environment variables:

- **LLM Configuration**: `OPENAI_API_KEY`, `OPENAI_MODEL`, etc.
- **Observability**: `PHOENIX_ENDPOINT`, `PHOENIX_MAX_ATTR_CHARS`
- **ReAct Controls**: `AGENT_REACT_INCLUDE_HISTORY`, `AGENT_REACT_MAX_HISTORY_MESSAGES`
- **HITL**: `REACT_HITL_ENABLE`, `REACT_HITL_SCOPE`

See [Environment Variables](environment_variables.md) for complete list.

## Summary

The framework provides:

✅ **Hierarchical Agents**: Orchestrator → Manager → Worker  
✅ **Policy-Driven**: Configurable completion, loop prevention, HITL  
✅ **Parallel Execution**: Tools and managers can run concurrently  
✅ **Context-Aware**: Full conversation and execution history  
✅ **Async-Safe**: Uses `contextvars` for request isolation  
✅ **Observable**: Event system for monitoring and debugging  
✅ **Extensible**: Pluggable planners, tools, memory, policies  

