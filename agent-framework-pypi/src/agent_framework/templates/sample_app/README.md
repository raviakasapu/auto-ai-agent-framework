# AI Agent Framework - Sample App

A complete example demonstrating the AI Agent Framework with:
- **Workers**: Specialized agents with ReAct planning
- **Orchestrator**: Routes tasks to appropriate workers
- **Tools**: Domain-specific tools for research and task management
- **YAML Configuration**: Declarative agent definitions
- **Context Management**: Configurable truncation and history

## Quick Start

### 1. Setup Environment

```bash
cd examples/sample_app

# Create virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r ../../requirements.txt
pip install python-dotenv

# Configure API key
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

### 2. Run the App

```bash
# Interactive mode
python run.py

# Single task (uses orchestrator)
python run.py "Search for Python tutorials"

# Specific worker
python run.py --config research "Take notes on machine learning"
python run.py --config task "Create a task called 'Review docs'"

# Run all test scenarios
python run.py --test
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Orchestrator                           │
│                  (WorkerRouterPlanner)                      │
│                                                             │
│  Analyzes task → Routes to appropriate worker               │
└─────────────────────────┬───────────────────────────────────┘
                          │
           ┌──────────────┴──────────────┐
           │                             │
           ▼                             ▼
┌─────────────────────┐     ┌─────────────────────┐
│   Research Worker   │     │    Task Worker      │
│   (ReActPlanner)    │     │   (ReActPlanner)    │
│                     │     │                     │
│ Tools:              │     │ Tools:              │
│ - web_search        │     │ - create_task       │
│ - note_taker        │     │ - list_tasks        │
│ - calculator        │     │ - complete_task     │
│                     │     │ - weather_lookup    │
└─────────────────────┘     └─────────────────────┘
```

## Directory Structure

```
sample_app/
├── configs/
│   ├── agents/           # Agent YAML configurations
│   │   ├── orchestrator.yaml
│   │   ├── research_worker.yaml
│   │   └── task_worker.yaml
│   ├── tools/            # Tool registrations
│   ├── planners/         # Planner registrations
│   ├── gateways/         # Inference gateway registrations
│   ├── memory/           # Memory registrations
│   ├── subscribers/      # Event subscriber registrations
│   └── policies/         # Policy registrations
├── deployment/
│   ├── factory.py        # Agent factory
│   └── registry.py       # Component registry
├── tools/
│   ├── note_taker.py     # Note taking tool
│   ├── task_manager.py   # Task CRUD tools
│   ├── weather.py        # Mock weather tool
│   └── search.py         # Mock search tool
├── tests/                # Test files
├── run.py               # Main entry point
├── .env.example         # Environment template
└── README.md            # This file
```

## Configuration

### Agent YAML Schema (v2)

```yaml
apiVersion: agent.framework/v2
kind: Agent  # or ManagerAgent for orchestrator

metadata:
  name: MyAgent
  description: Agent description
  version: 1.0.0

resources:
  inference_gateways:
    - name: openai-gateway
      type: OpenAIGateway
      config:
        model: ${OPENAI_MODEL:-gpt-4o-mini}
        api_key: ${OPENAI_API_KEY}

  tools:
    - name: my_tool
      type: MyToolClass
      config: {}

  subscribers:
    - name: logging
      type: LoggingSubscriber

spec:
  policies:
    $preset: simple  # Use preset policies
    termination:
      type: DefaultTerminationPolicy
      config:
        max_iterations: 10

  planner:
    type: ReActPlanner
    config:
      inference_gateway: openai-gateway
      use_function_calling: true
      system_prompt: |
        Your custom system prompt here...

  memory:
    type: SharedInMemoryMemory
    config:
      namespace: ${JOB_ID:-default}
      agent_key: my_agent

  tools: [my_tool]
  subscribers: [logging]
```

### Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `OPENAI_API_KEY` | OpenAI API key | (required) |
| `OPENAI_MODEL` | Model for workers | gpt-4o-mini |
| `OPENAI_STRATEGIC_MODEL` | Model for orchestrator | gpt-4o |
| `AGENT_STRATEGIC_PLAN_TRUNCATE_LEN` | Strategic plan truncation | 2000 |
| `AGENT_DIRECTOR_CONTEXT_TRUNCATE_LEN` | Director context truncation | 4000 |
| `AGENT_OBSERVATION_TRUNCATE_LEN` | Observation truncation | 1500 |
| `AGENT_MAX_CONVERSATION_TURNS` | Max conversation turns | 10 |
| `AGENT_LOG_TRUNCATION` | Log truncation events | true |
| `AGENT_REACT_INCLUDE_HISTORY` | Include conversation history | true |
| `AGENT_REACT_INCLUDE_TRACES` | Include execution traces | true |
| `AGENT_LOG_LEVEL` | Logging level | INFO |

## Creating Custom Tools

Tools must implement the `BaseTool` interface:

```python
from pydantic import BaseModel, Field
from agent_framework.base import BaseTool

class MyToolArgs(BaseModel):
    """Input schema for the tool."""
    param1: str = Field(..., description="First parameter")
    param2: int = Field(10, description="Optional parameter with default")

class MyToolOutput(BaseModel):
    """Output schema for the tool."""
    result: str
    success: bool

class MyTool(BaseTool):
    _name = "my_tool"
    _description = "Description of what this tool does."

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def args_schema(self):
        return MyToolArgs

    @property
    def output_schema(self):
        return MyToolOutput

    def execute(self, param1: str, param2: int = 10) -> dict:
        # Tool implementation
        result = f"Processed {param1} with {param2}"
        return MyToolOutput(result=result, success=True).model_dump()
```

Then register in `configs/tools/my_tool.yaml`:

```yaml
name: MyTool
class: tools.my_tool.MyTool
```

## Testing the Framework

The sample app exercises:

1. **ReAct Planner**: Workers use iterative reasoning
2. **Router Planner**: Orchestrator routes to workers
3. **Function Calling**: OpenAI tool/function calling
4. **Memory**: Shared memory with async-safe operations
5. **Context Config**: Truncation with logging
6. **Event System**: Progress events for monitoring
7. **Policies**: Termination and iteration limits

Run the test suite:

```bash
python run.py --test
```

## Troubleshooting

### "OPENAI_API_KEY not set"
- Copy `.env.example` to `.env`
- Add your OpenAI API key

### "Unknown component type"
- Check tool/planner registration in `configs/`
- Verify class path in YAML matches actual module

### "Module not found"
- Ensure you're running from the `sample_app` directory
- Check that the framework is properly installed

## License

MIT License - See repository root for details.
