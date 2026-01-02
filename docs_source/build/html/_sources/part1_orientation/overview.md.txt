# Product Overview & Capabilities

## What is the AI Agent Framework?

The **AI Agent Framework** is a production-grade Python library for building hierarchical, policy-driven AI agent systems. It provides:

- **Pip-installable package** (`agent_framework`) with a clean namespace
- **Hierarchical agent architecture** with Orchestrator → Manager → Worker patterns
- **Pluggable design** for tools, planners, memory, and LLM providers
- **Declarative YAML configuration** with factory pattern
- **Built-in observability** via EventBus, OpenTelemetry, and Phoenix tracing
- **Policy-driven behavior** for completion detection, loop prevention, and HITL

## Key Differentiators

| Feature | Description |
|---------|-------------|
| **Reusable Library** | Import `agent_framework` into any Python application |
| **Clean Separation** | Generic framework vs. domain-specific tools |
| **Zero-Boilerplate Tools** | `@tool` decorator for instant tool creation |
| **Policy Presets** | `get_preset("default")` for common behavior patterns |
| **Message Store Memory** | Agents read/write from external stores |
| **Structured Responses** | `FinalResponse` for machine-readable outputs |
| **Multi-Model Support** | OpenAI, Google AI, Anthropic gateways |

## Target Personas

- **Application Developers**: Building AI-powered features with minimal boilerplate
- **AI Engineers**: Creating domain-specific agent workflows
- **Platform Teams**: Deploying observable, scalable agent systems

## Architecture at a Glance

```
agent-framework-pypi/src/agent_framework/   # FRAMEWORK LIBRARY
├── core/           # Agent, ManagerAgent, EventBus
├── components/     # Planners, Memory implementations
├── gateways/       # LLM providers (OpenAI, Google)
├── policies/       # Behavior control policies
├── services/       # Request context, pluggable services
├── observability/  # Phoenix, Langfuse subscribers
└── tools/utility/  # Generic tools (calculator, glob, grep)

deployment/         # Factory and registry (application-side)
configs/            # YAML configurations
```

## Public API

The framework exports a clean public API:

```python
from agent_framework import (
    # Core Agents
    Agent,                # Worker agent with policy-driven loop
    ManagerAgent,         # Orchestrator/manager with delegation
    EventBus,             # Event publishing system
    
    # Base Classes (for extension)
    BaseTool,
    BasePlanner,
    BaseMemory,
    BaseInferenceGateway,
    BaseEventSubscriber,
    BaseProgressHandler,
    BaseMessageStore,
    BaseJobStore,
    
    # Data Classes
    Action,               # Tool invocation request
    FinalResponse,        # Structured completion response
    
    # Decorators
    tool,                 # @tool decorator
    FunctionalTool,       # Wrapper for decorated functions
    
    # Memory
    MessageStoreMemory,
    HierarchicalMessageStoreMemory,
    
    # Policies
    get_preset,           # Get policy preset by name
)
```

## Installation

```bash
# From PyPI (production)
pip install agentic-framework

# From source (development)
pip install -e ./agent-framework-pypi
```

## Getting Started with a Sample Project

The fastest way to get started is using the CLI to scaffold a complete sample application:

```bash
# Create a new project
agent-framework init my_agent_project

# Navigate to the project
cd my_agent_project

# Setup environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# Run the sample app
python run.py                    # Interactive mode
python run.py "Search for Python tutorials"  # Single task
python run.py --test             # Run all test scenarios
```

### Sample Project Features

The scaffolded project demonstrates:

| Feature | Description |
|---------|-------------|
| **Research Worker** | Web search, note-taking, calculations (ReActPlanner) |
| **Task Worker** | Task CRUD, weather lookup (ReActPlanner) |
| **Orchestrator** | Routes to workers (WorkerRouterPlanner) |
| **YAML Config** | Full v2 agent schema with environment variables |
| **Custom Tools** | 6 example tools showing the BaseTool pattern |

### CLI Commands

```bash
agent-framework --help           # Show help
agent-framework init             # Create project (default: agent_project)
agent-framework init my_project  # Create with custom name
agent-framework --version        # Show version
```

## Quick Example

```python
from agent_framework import Agent, Action, FinalResponse
from agent_framework.components.planners import StaticPlanner
from agent_framework.decorators import tool

# Define a tool with the @tool decorator
@tool(name="calculator", description="Perform arithmetic")
def calculator(expression: str) -> str:
    """Evaluate a math expression."""
    return str(eval(expression))

# Create a simple agent
planner = StaticPlanner(tool_name="calculator")
agent = Agent(
    name="math_agent",
    planner=planner,
    tools=[calculator],
)

# Run the agent
result = await agent.run("Calculate 2 + 2")
print(result)  # "4"
```

## What's Next?

- **[Quickstart](quickstart.rst)** — Get running in 5 minutes
- **[Conceptual Model](conceptual_model.md)** — Understand the mental model
- **[Part 2: Runtime Building Blocks](../part2_runtime/index.rst)** — Deep dive into components

