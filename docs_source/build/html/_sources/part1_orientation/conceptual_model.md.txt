# Conceptual Model

This chapter explains the mental model of the framework before diving into code. Understanding these concepts will make everything else click.

## Core Philosophy

The framework follows a **policy-driven, event-based architecture**:

1. **Planners decide** what to do next
2. **Tools execute** domain operations
3. **Memory persists** context and history
4. **Policies control** behavior (completion, loops, HITL)
5. **Events enable** observability and streaming

## The Agent Loop

Every agent follows this execution loop:

```
┌─────────────────────────────────────────────┐
│                 AGENT LOOP                  │
├─────────────────────────────────────────────┤
│                                             │
│  1. Receive Task                            │
│       ↓                                     │
│  2. Get History from Memory                 │
│       ↓                                     │
│  3. Planner.plan(task, history)             │
│       ↓                                     │
│  ┌─────────────────────────────────────┐    │
│  │ Returns one of:                     │    │
│  │ • Action → execute tool             │    │
│  │ • List[Action] → parallel execution │    │
│  │ • FinalResponse → done, return      │    │
│  └─────────────────────────────────────┘    │
│       ↓                                     │
│  4. Execute Action(s)                       │
│       ↓                                     │
│  5. Add Result to Memory                    │
│       ↓                                     │
│  6. Check Completion Policy                 │
│       ↓                                     │
│  ┌─────────────────────────────────────┐    │
│  │ If complete → return result         │    │
│  │ If not → go to step 2               │    │
│  └─────────────────────────────────────┘    │
│                                             │
└─────────────────────────────────────────────┘
```

## Core Components

### 1. Planner

**What it does**: Decides the next action(s) based on task and history.

**Base class**: `BasePlanner`

**Return types**:
- `Action` — Single tool to execute
- `List[Action]` — Multiple tools to execute in parallel
- `FinalResponse` — Task complete, return structured result

**Implementations**:
| Planner | Description |
|---------|-------------|
| `StaticPlanner` | Always returns the same tool |
| `ReActPlanner` | LLM-based reasoning with tool selection |
| `StrategicPlanner` | Multi-phase planning for orchestrators |
| `StrategicDecomposerPlanner` | Step-by-step planning for managers |
| `WorkerRouterPlanner` | Routes to worker agents |
| `ChatPlanner` | Conversational responses |

### 2. Tool

**What it does**: Executes a specific operation (API call, calculation, file read, etc.)

**Base class**: `BaseTool`

**Properties**:
- `name` — Unique identifier
- `description` — Human-readable explanation (used by LLM)
- `args_schema` — Pydantic model for input validation
- `output_schema` — Optional Pydantic model for output

**Creation methods**:

```python
# Method 1: @tool decorator (recommended)
@tool(name="add", description="Add two numbers")
def add(a: int, b: int) -> int:
    return a + b

# Method 2: Class-based (for complex tools)
class MyTool(BaseTool):
    @property
    def name(self) -> str:
        return "my_tool"
    
    @property
    def description(self) -> str:
        return "Does something useful"
    
    @property
    def args_schema(self) -> Type[BaseModel]:
        return MyArgsModel
    
    def execute(self, **kwargs) -> Any:
        # Implementation
        pass
```

### 3. Memory

**What it does**: Stores conversation history and execution traces.

**Base class**: `BaseMemory`

**Methods**:
- `add(message)` — Add a message to history
- `get_history()` — Retrieve all history

**Implementations**:
| Memory | Description |
|--------|-------------|
| `SimpleMemory` | In-memory list (development) |
| `SharedInMemoryMemory` | Namespace-isolated shared memory |
| `MessageStoreMemory` | Reads from `BaseMessageStore` |
| `HierarchicalMessageStoreMemory` | Manager memory with subordinate visibility |

### 4. Gateway (LLM Provider)

**What it does**: Abstracts LLM API calls.

**Base class**: `BaseInferenceGateway`

**Method**: `invoke(prompt) → str`

**Implementations**:
| Gateway | Provider |
|---------|----------|
| `OpenAIGateway` | OpenAI (GPT-4, etc.) |
| `GoogleAIGateway` | Google Generative AI |
| `MockGateway` | Testing/development |

### 5. Policy

**What it does**: Controls agent behavior at runtime.

**Policy types**:
| Policy | Purpose |
|--------|---------|
| `CompletionDetector` | Determines when task is complete |
| `TerminationPolicy` | Max iterations, timeout |
| `LoopPreventionPolicy` | Detects repeated actions |
| `HITLPolicy` | Human-in-the-loop approval |
| `CheckpointPolicy` | Save/restore execution state |

**Using presets**:
```python
from agent_framework import get_preset

# Get default policies
policies = get_preset("default")
# Returns: completion_detector, termination_policy, loop_prevention_policy, ...
```

### 6. EventBus

**What it does**: Publishes events for observability and streaming.

**Core events**:
- `agent_start` / `agent_end`
- `action_planned` / `action_executed`
- `manager_start` / `manager_end`
- `delegation_chosen` / `delegation_executed`
- `error` / `policy_denied`

**Subscribers**:
- `LoggingSubscriber` — Logs events
- `PhoenixSubscriber` — OpenTelemetry traces
- `LangfuseSubscriber` — Langfuse integration

## Hierarchical Architecture

The framework supports multi-level agent hierarchies:

```
User Request
    ↓
┌─────────────────────────────────────┐
│ ORCHESTRATOR (ManagerAgent)         │
│ - StrategicPlanner                  │
│ - Creates multi-phase plans         │
│ - Delegates to domain managers      │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ MANAGER (ManagerAgent)              │
│ - StrategicDecomposerPlanner        │
│ - Breaks phases into steps          │
│ - Delegates to worker agents        │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ WORKER (Agent)                      │
│ - ReActPlanner                      │
│ - Executes tools                    │
│ - Returns results                   │
└─────────────────────────────────────┘
```

### Agent vs ManagerAgent

| Aspect | Agent | ManagerAgent |
|--------|-------|--------------|
| **Purpose** | Execute tools | Coordinate subordinates |
| **Planner** | ReActPlanner, StaticPlanner | StrategicPlanner, WorkerRouterPlanner |
| **Execution** | Runs tools directly | Delegates to other agents |
| **Synthesis** | None | Aggregates subordinate results |

## Data Flow

### Action

The `Action` dataclass represents a tool invocation:

```python
@dataclass
class Action:
    tool_name: str              # Which tool to call
    tool_args: Dict[str, Any]   # Arguments for the tool
```

### FinalResponse

The `FinalResponse` model represents task completion:

```python
class FinalResponse(BaseModel):
    operation: str              # Frontend operation (e.g., "display_message")
    payload: Dict[str, Any]     # Data for the operation
    human_readable_summary: str # Chat-friendly summary
```

## Message Types

History entries use standardized types (from `agent_framework.constants`):

| Type | Description | Example |
|------|-------------|---------|
| `user_message` | User input | "List all tables" |
| `assistant_message` | Assistant response | "Found 5 tables..." |
| `task` | Task assignment | "Analyze the model" |
| `action` | Tool call | {"tool": "list_tables", "args": {...}} |
| `observation` | Tool result | {"tables": [...]} |
| `error` | Error occurred | {"error": "Connection failed"} |
| `final` | Completion signal | {"summary": "Done"} |
| `synthesis` | Manager summary | {"aggregated": "..."} |

## Configuration

Agents can be configured:

1. **Programmatically** — Python code
2. **Declaratively** — YAML files with factory pattern

```yaml
# configs/agents/my_agent.yaml
name: my_agent
type: Agent
resources:
  tools:
    - name: calculator
      type: CalculatorTool
spec:
  planner:
    type: ReActPlanner
    config:
      inference_gateway: openai-main
  memory:
    type: SimpleMemory
  tools: [calculator]
```

## What's Next?

Now that you understand the mental model:

- **[Part 2: Runtime Building Blocks](../part2_runtime/index.rst)** — Deep dive into each component
- **[Tutorials](../tutorials/index.rst)** — Hands-on exercises
- **[Part 3: Building Solutions](../part3_solutions/index.rst)** — Configuration, flows, deployment

