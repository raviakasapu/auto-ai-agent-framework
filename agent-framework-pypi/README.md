# Auto AI Agent Framework

> A reusable Python library for building hierarchical agentic AI workflows with declarative YAML configuration.

[![PyPI version](https://badge.fury.io/py/auto-ai-agent-framework.svg)](https://badge.fury.io/py/auto-ai-agent-framework)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

- **🏗️ Hierarchical Agents**: Build Director → Manager → Worker agent teams
- **🔌 Pluggable Design**: Register domain-specific tools and services
- **📝 Declarative Config**: Define agents in YAML
- **🎯 Multiple Planners**: ReAct, Router, Strategic, Chat, and more
- **📊 Observability**: Built-in event system and OpenTelemetry support
- **🔧 Extensible**: Easy to add custom tools, planners, and gateways

## Installation

```bash
pip install auto-ai-agent-framework
```

With optional dependencies:

```bash
# Google AI (Gemini) support
pip install auto-ai-agent-framework[google]

# Observability (OpenTelemetry)
pip install auto-ai-agent-framework[observability]

# All extras
pip install auto-ai-agent-framework[all]
```

## Quick Start

### 1. Create a Simple Agent

```python
from agent_framework import Agent, BaseTool
from agent_framework.gateways.inference import OpenAIGateway
from agent_framework.components.planners import ChatPlanner
from agent_framework.components.memory import InMemoryMemory

# Create components
gateway = OpenAIGateway(model="gpt-4o-mini", api_key="your-key")
planner = ChatPlanner(inference_gateway=gateway)
memory = InMemoryMemory()

# Create and run agent
agent = Agent(
    name="Assistant",
    planner=planner,
    memory=memory,
    tools=[],
)

result = agent.run("Hello! Tell me about AI agents.")
print(result)
```

### 2. Create a Custom Tool

```python
from agent_framework import BaseTool
from pydantic import BaseModel, Field

class CalculatorArgs(BaseModel):
    expression: str = Field(..., description="Math expression to evaluate")

class CalculatorOutput(BaseModel):
    result: float

class CalculatorTool(BaseTool):
    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return "Evaluates mathematical expressions"

    @property
    def args_schema(self):
        return CalculatorArgs

    @property
    def output_schema(self):
        return CalculatorOutput

    def execute(self, expression: str) -> dict:
        result = eval(expression)  # In production, use a safe evaluator
        return {"result": result}
```

### 3. Hierarchical Agent Teams

```python
from agent_framework import ManagerAgent

# Create a manager that delegates to workers
manager = ManagerAgent(
    name="ProjectManager",
    planner=router_planner,
    workers={
        "researcher": research_agent,
        "writer": writing_agent,
    },
)

result = manager.run("Research AI trends and write a summary")
```

## Core Concepts

| Component | Description |
|-----------|-------------|
| **Agent** | Executes tasks using tools and a planner |
| **ManagerAgent** | Orchestrates multiple worker agents |
| **BaseTool** | Base class for creating tools |
| **BasePlanner** | Base class for planning strategies |
| **EventBus** | Pub/sub system for observability |

## Planners

| Planner | Use Case |
|---------|----------|
| `ChatPlanner` | Conversational AI |
| `ReActPlanner` | Iterative reasoning (Thought → Action → Observation) |
| `LLMRouterPlanner` | Tool selection via LLM |
| `WorkerRouterPlanner` | Route to worker agents |
| `StrategicPlanner` | Multi-step planning |

## Architecture

```
┌─────────────────────────────────────┐
│           ManagerAgent              │
│    (Orchestrator / Director)        │
├─────────────────────────────────────┤
│ • Planner (routes to workers)       │
│ • Workers[] (other agents)          │
│ • EventBus (observability)          │
└──────────────┬──────────────────────┘
               │ delegates to
    ┌──────────┴──────────┐
    ▼                     ▼
┌─────────┐         ┌─────────┐
│  Agent  │         │  Agent  │
│ Worker A│         │ Worker B│
├─────────┤         ├─────────┤
│ • Tools │         │ • Tools │
│ • Memory│         │ • Memory│
└─────────┘         └─────────┘
```

## Getting Started with a Sample Project

The package includes a CLI to scaffold a complete sample application:

```bash
# Create a new project
agent-framework init my_agent_project

# Navigate to the project
cd my_agent_project

# Setup environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# Run interactive mode
python run.py

# Run a single task
python run.py "Search for Python tutorials"

# Run all test scenarios
python run.py --test
```

### Sample Project Features

The scaffolded project demonstrates all framework features:

| Feature | Description |
|---------|-------------|
| **Research Worker** | Web search, note-taking, calculations (ReActPlanner) |
| **Task Worker** | Task CRUD operations, weather lookup (ReActPlanner) |
| **Orchestrator** | Routes requests to appropriate workers (WorkerRouterPlanner) |
| **YAML Configuration** | Full v2 agent schema with environment variable support |
| **Custom Tools** | 6 example tools showing the BaseTool pattern |
| **Context Management** | Truncation, history limits, ENV overrides |

### Project Structure

```
my_agent_project/
├── configs/
│   ├── agents/           # Agent YAML definitions
│   ├── tools/            # Tool registrations
│   ├── planners/         # Planner registrations
│   ├── gateways/         # Inference gateway registrations
│   └── ...               # Memory, policies, subscribers
├── deployment/
│   ├── factory.py        # AgentFactory for YAML-based creation
│   └── registry.py       # Component discovery
├── tools/                # Custom tool implementations
├── run.py               # Main entry point
├── .env.example         # Environment template
└── README.md            # Detailed documentation
```

### CLI Commands

```bash
# Show help
agent-framework --help

# Create new project (default name: agent_project)
agent-framework init

# Create project with custom name
agent-framework init my_custom_project

# Show version
agent-framework --version
```

## Documentation

- [Full Documentation](https://auto-ai-agent-framework.vercel.app/)
- [API Reference](https://auto-ai-agent-framework.vercel.app/api)
- [Examples](https://github.com/akasa-ai/agentic-framework/tree/main/examples)
- [Environment Variables](https://auto-ai-agent-framework.vercel.app/guides/environment_variables)

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please read our [Contributing Guide](CONTRIBUTING.md) for details.
