# AI Agent Framework (Overview)

A modular, extensible, and observable **Python library** for building agentic AI systems with declarative YAML configuration.

## Key Features

- **Reusable Library**: Import `agent_framework` as a pip package into any application
- **Pluggable Design**: Register domain-specific tools and services at runtime
- **Clean Separation**: Generic library (`agent-framework-pypi/src/agent_framework/`) vs. domain code (`bi_tools/`)
- **Declarative Config**: YAML-based agent definitions with factory pattern
- **Observability**: EventBus, OpenTelemetry integration, structured logging
- **Tool Decorators**: Author production-ready tools with the `@tool` decorator

## Architecture

```
agent-framework-pypi/src/agent_framework/   # GENERIC LIBRARY (pip-installable)
├── core/           # Agent, ManagerAgent, EventBus
├── components/     # Planners, Memory implementations
├── gateways/       # LLM providers (OpenAI, Google)
├── policies/       # Behavior control policies
├── services/       # Request context, pluggable services
└── tools/utility/  # Generic tools (calculator, etc.)

bi_tools/           # DOMAIN-SPECIFIC (Power BI example)
├── services/       # DataModelService, KG integration
└── tools/          # Column, Measure, Relationship tools

deployment/         # Factory and registry
configs/            # YAML configurations
```

## Quickstart

```bash
# Install the framework
pip install agentic-framework

# Create a sample project with CLI
agent-framework init my_agent_project

# Navigate and setup
cd my_agent_project
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# Run the sample app
python run.py                    # Interactive mode
python run.py "Search for Python" # Single task
python run.py --test             # Run test scenarios
```

### CLI Commands

```bash
agent-framework --help           # Show help
agent-framework init             # Create project (default: agent_project)
agent-framework init my_project  # Create project with custom name
agent-framework --version        # Show version
```

## Using as a Library

```python
from agent_framework import Agent, ManagerAgent, BaseTool, EventBus, get_preset
from agent_framework.gateways.inference import OpenAIGateway
from agent_framework.components.planners import ReActPlanner

# Create agent programmatically or via factory
from deployment.factory import AgentFactory
agent = AgentFactory.create_from_yaml("configs/agents/my_agent.yaml")
result = agent.run("Your task here")
```

## Registering Domain Tools

```python
from deployment.registry import register_tool
from my_app.tools import MyCustomTool

register_tool("MyCustomTool", MyCustomTool)
```

## Manifest + Docs Server

```bash
# Generate manifest
python generate_manifest.py --config configs/agents/research_assistant.yaml --output docs/agent_manifest.json

# Serve docs
AGENT_MANIFEST_PATH=docs/agent_manifest.json \
AGENT_DOCS_DIR=docs/sphinx/build/html \
uvicorn docs_server.main:app --reload
```

## Directory Structure

| Directory | Purpose |
|-----------|---------|
| `agent-framework-pypi/src/agent_framework/` | Generic library (pip-installable) |
| `bi_tools/` | Domain-specific tools and services |
| `deployment/` | Factory & registry |
| `configs/` | YAML component configs |
| `flows/` (optional) | High-level flow YAMLs loaded by ``FlowFactory`` |
| `docs/sphinx/` | Sphinx documentation |
| `docs_server/` | Manifest + docs server |
| `tests/` | Test suite |

**Note:** Use `agent-framework init` to scaffold a sample project with examples.
