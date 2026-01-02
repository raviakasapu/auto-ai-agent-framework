# Planners & Gateways

This chapter covers planner implementations and LLM gateways.

## BasePlanner Interface

All planners implement the `BasePlanner` interface:

```python
from agent_framework import BasePlanner, Action, FinalResponse

class BasePlanner(ABC):
    @abstractmethod
    def plan(
        self, 
        task_description: str, 
        history: List[Dict[str, Any]]
    ) -> Union[Action, List[Action], FinalResponse]:
        """Plan the next step(s) for the agent."""
        pass
```

### Return Types

| Return Type | Meaning |
|-------------|---------|
| `Action` | Execute one tool, then re-plan |
| `List[Action]` | Execute multiple tools in parallel, then re-plan |
| `FinalResponse` | Task complete, stop execution |

## Planner Implementations

### StaticPlanner

Always returns the same action based on keyword matching:

```python
from agent_framework.components.planners import StaticPlanner

planner = StaticPlanner(keywords=["search", "find"])
# If task contains "search" or "find" → Action(tool_name="mock_search")
# Otherwise → FinalResponse
```

**Use case**: Testing, deterministic workflows.

### SingleActionPlanner

Always returns a specific configured action:

```python
from agent_framework.components.planners import SingleActionPlanner

planner = SingleActionPlanner(
    tool_name="list_tables",
    tool_args={"schema": "public"},
    terminal=True,  # Stop after execution
)
```

**Use case**: Single-tool agents, terminal actions.

### LLMRouterPlanner

Routes tasks to tools using LLM:

```python
from agent_framework.components.planners import LLMRouterPlanner
from agent_framework.gateways.inference import OpenAIGateway

planner = LLMRouterPlanner(
    inference_gateway=OpenAIGateway(model="gpt-4o-mini"),
    tool_specs=[
        {"tool": "list_tables", "args": ["schema"]},
        {"tool": "add_column", "args": ["table", "column", "type"]},
    ],
    system_prompt="Route the task to the appropriate tool.",
)
```

**Use case**: Simple tool selection without ReAct loop.

### ReActPlanner

Full Reasoning + Acting loop with LLM:

```python
from agent_framework.components.planners import ReActPlanner
from agent_framework.gateways.inference import OpenAIGateway
from agent_framework.decorators import tool

@tool
def calculator(expression: str) -> str:
    return str(eval(expression))

planner = ReActPlanner(
    inference_gateway=OpenAIGateway(model="gpt-4o"),
    tools=[calculator],
    system_prompt="You are a helpful assistant with access to tools.",
    include_history=True,
    max_history_messages=20,
)
```

**Features**:
- OpenAI function calling format
- History filtering for context
- Automatic schema generation from tools
- Supports parallel tool calls

**Use case**: Worker agents that need reasoning.

### ChatPlanner

Conversational responses without tools:

```python
from agent_framework.components.planners import ChatPlanner

planner = ChatPlanner(
    inference_gateway=OpenAIGateway(model="gpt-4o-mini"),
    system_prompt="You are a helpful chat assistant.",
)
# Always returns FinalResponse with chat message
```

**Use case**: Chat-only agents, off-topic handling.

### StrategicPlanner

Creates multi-phase strategic plans for orchestrators:

```python
from agent_framework.components.planners import StrategicPlanner

planner = StrategicPlanner(
    worker_keys=["analysis_manager", "design_manager"],
    inference_gateway=OpenAIGateway(model="gpt-4o"),
    planning_prompt="Create a strategic plan for the task.",
)
```

**Output format**:
```json
{
  "plan": {
    "phases": [
      {"name": "Analyze", "worker": "analysis_manager", "goals": "..."},
      {"name": "Design", "worker": "design_manager", "goals": "..."}
    ],
    "primary_worker": "analysis_manager",
    "rationale": "..."
  }
}
```

**Use case**: Top-level orchestrators.

### StrategicDecomposerPlanner

Breaks orchestrator phases into actionable steps:

```python
from agent_framework.components.planners import StrategicDecomposerPlanner

planner = StrategicDecomposerPlanner(
    worker_keys=["reader", "analyzer", "validator"],
    inference_gateway=OpenAIGateway(model="gpt-4o-mini"),
    manager_worker_key="analysis_manager",  # Identifies this manager
)
```

**Use case**: Domain managers.

### WorkerRouterPlanner

Routes to workers with explicit delegation:

```python
from agent_framework.components.planners import WorkerRouterPlanner

planner = WorkerRouterPlanner(
    worker_keys=["reader", "writer"],
    inference_gateway=OpenAIGateway(model="gpt-4o-mini"),
)
```

**Use case**: Simple manager delegation.

### ManagerScriptPlanner

Creates detailed script plans for workers:

```python
from agent_framework.components.planners import ManagerScriptPlanner

planner = ManagerScriptPlanner(
    inference_gateway=OpenAIGateway(model="gpt-4o-mini"),
    worker_key="data_processor",
)
```

**Use case**: Script-based worker execution.

## History Filtering

Planners use history filters to select relevant context:

| Planner | Filter | Purpose |
|---------|--------|---------|
| `StrategicPlanner` | `OrchestratorHistoryFilter` | Conversation only |
| `StrategicDecomposerPlanner` | `ManagerHistoryFilter` | Previous phase synthesis |
| `ReActPlanner` | `WorkerHistoryFilter` | Current turn traces |

## Inference Gateways

### BaseInferenceGateway

```python
from agent_framework import BaseInferenceGateway

class BaseInferenceGateway(ABC):
    @abstractmethod
    def invoke(self, prompt: Union[str, List[Dict[str, Any]]]) -> str:
        """Send prompt to LLM and return response."""
        pass
```

### OpenAIGateway

```python
from agent_framework.gateways.inference import OpenAIGateway

gateway = OpenAIGateway(
    model="gpt-4o",
    temperature=0.7,
    max_tokens=4096,
    api_key="sk-...",  # Or use OPENAI_API_KEY env var
)

# Simple invocation
response = gateway.invoke("What is 2+2?")

# With messages list
response = gateway.invoke([
    {"role": "system", "content": "You are helpful."},
    {"role": "user", "content": "Hello!"},
])
```

**Features**:
- Automatic retry with backoff
- Cost tracking per call
- Token usage metrics
- OpenTelemetry tracing integration

### GoogleAIGateway

```python
from agent_framework.gateways.inference import GoogleAIGateway

gateway = GoogleAIGateway(
    model="gemini-1.5-pro",
    api_key="...",  # Or use GOOGLE_API_KEY env var
)
```

### MockGateway

```python
from agent_framework.gateways.inference import MockGateway

gateway = MockGateway(
    responses=["Response 1", "Response 2"],
    # Cycles through responses
)
```

**Use case**: Testing without API calls.

## YAML Configuration

```yaml
spec:
  planner:
    type: ReActPlanner
    config:
      inference_gateway: openai-main
      system_prompt: "You are a helpful assistant."
      include_history: true
      max_history_messages: 20

# Gateway defined in resources
resources:
  gateways:
    - name: openai-main
      type: OpenAIGateway
      config:
        model: gpt-4o
        temperature: 0.7
```

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `OPENAI_API_KEY` | OpenAI API key |
| `OPENAI_MODEL` | Default model name |
| `GOOGLE_API_KEY` | Google AI API key |
| `AGENT_REACT_INCLUDE_HISTORY` | Enable history in ReAct prompts |
| `AGENT_REACT_MAX_HISTORY_MESSAGES` | Max messages in ReAct history |
| `AGENT_LOG_ROUTER_DETAILS` | Log router planner details |

## Custom Planner Example

```python
from agent_framework import BasePlanner, Action, FinalResponse

class PriorityPlanner(BasePlanner):
    """Routes to tools based on task priority keywords."""
    
    def __init__(self, high_priority_tool: str, default_tool: str):
        self.high_priority_tool = high_priority_tool
        self.default_tool = default_tool
    
    def plan(self, task_description: str, history: list) -> Action:
        task_lower = task_description.lower()
        
        if any(kw in task_lower for kw in ["urgent", "critical", "asap"]):
            return Action(
                tool_name=self.high_priority_tool,
                tool_args={"task": task_description, "priority": "high"}
            )
        
        return Action(
            tool_name=self.default_tool,
            tool_args={"task": task_description}
        )

# Register for YAML use
from deployment.registry import register_planner
register_planner("PriorityPlanner", PriorityPlanner)
```

## Best Practices

1. **Match planner to agent role**:
   - Orchestrator → `StrategicPlanner`
   - Manager → `StrategicDecomposerPlanner`
   - Worker → `ReActPlanner`

2. **Configure appropriate models**:
   - Strategic planning → `gpt-4o` (powerful)
   - Tactical execution → `gpt-4o-mini` (efficient)

3. **Use history filtering** to keep prompts focused

4. **Enable tracing** for debugging with Phoenix

5. **Test with MockGateway** before using real LLMs

