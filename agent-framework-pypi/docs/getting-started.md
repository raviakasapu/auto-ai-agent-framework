# Getting Started

This guide will help you get the AI Agent Framework installed and running your first agent.

## Prerequisites

- Python 3.9 or higher
- pip package manager
- An OpenAI API key (for using OpenAI models)

## Installation

### From PyPI (Recommended)

```bash
pip install agent-framework
```

### From Source

```bash
git clone https://github.com/your-org/agent-framework.git
cd agent-framework
pip install -e .
```

### Development Installation

For development with test dependencies:

```bash
pip install -e ".[dev]"
```

## Environment Setup

Create a `.env` file in your project root:

```bash
# Required for OpenAI-based agents
OPENAI_API_KEY=your-api-key-here
OPENAI_MODEL=gpt-4o-mini

# Optional: Job isolation for memory namespacing
JOB_ID=my-job-123
```

## Project Structure

A typical agent project has this structure:

```
my-agent-project/
├── configs/
│   └── agents/
│       ├── orchestrator.yaml      # Manager agent config
│       ├── research_worker.yaml   # Worker agent config
│       └── task_worker.yaml       # Another worker config
├── tools/
│   ├── __init__.py
│   └── custom_tools.py            # Custom tool implementations
├── deployment/
│   └── factory.py                 # Agent factory
├── main.py                        # Entry point
└── .env                           # Environment variables
```

## Your First Agent

### 1. Create an Agent Configuration

Create `configs/agents/my_agent.yaml`:

```yaml
apiVersion: agent.framework/v2
kind: Agent

metadata:
  name: MyFirstAgent
  description: A simple assistant agent

resources:
  inference_gateways:
    - name: openai
      type: OpenAIGateway
      config:
        model: ${OPENAI_MODEL:-gpt-4o-mini}
        api_key: ${OPENAI_API_KEY}
        temperature: 0.1
        use_function_calling: true

  tools:
    - name: calculator
      type: CalculatorTool
      config: {}

spec:
  policies:
    $preset: simple

  planner:
    type: ReActPlanner
    config:
      inference_gateway: openai
      use_function_calling: true
      system_prompt: |
        You are a helpful assistant with access to a calculator.
        Use the calculator tool to perform mathematical operations.

  memory:
    $preset: worker

  tools: [calculator]
```

### 2. Create the Entry Point

Create `main.py`:

```python
import asyncio
from dotenv import load_dotenv
from deployment.factory import create_agent_from_yaml

load_dotenv()

async def main():
    # Load agent from YAML config
    agent = create_agent_from_yaml("configs/agents/my_agent.yaml")

    # Run a task
    result = await agent.run("What is 42 * 17 + 123?")
    print(f"Result: {result}")

if __name__ == "__main__":
    asyncio.run(main())
```

### 3. Run Your Agent

```bash
python main.py
```

## Next Steps

- [Quickstart Guide](quickstart.md) - More examples and patterns
- [YAML Configuration Guide](guides/yaml-configuration.md) - Complete configuration reference
- [Agent Types](guides/agent-types.md) - Single vs Manager agents
- [Memory Presets](guides/memory-presets.md) - Memory configuration options
- [Policy Presets](guides/policy-presets.md) - Behavior control options
