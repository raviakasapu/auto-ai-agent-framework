# Pattern: Minimal Agent

The simplest possible agent configuration. Use this as a starting point for any new agent.

## When to Use

- Learning the framework
- Single-purpose agents (calculator, greeter, lookup)
- Quick prototypes

## Architecture

```
[User] --> [Agent] --> [Single Tool]
              |
        [StaticPlanner]
```

## Complete YAML

Copy this file to `configs/agents/minimal_agent.yaml`:

```yaml
# =============================================================================
# MINIMAL AGENT PATTERN
# =============================================================================
# The simplest possible agent: one tool, static planning, in-memory storage.
# Perfect for learning or single-purpose utilities.
# =============================================================================

apiVersion: agent.framework/v2
kind: Agent

metadata:
  name: MinimalAgent
  description: A minimal agent with a single tool
  version: 1.0.0

resources:
  # ---------------------------------------------------------------------------
  # Inference Gateway - LLM connection
  # ---------------------------------------------------------------------------
  inference_gateways:
    - name: openai
      type: OpenAIGateway
      config:
        model: ${OPENAI_MODEL:-gpt-4o-mini}
        api_key: ${OPENAI_API_KEY}

  # ---------------------------------------------------------------------------
  # Tools - Agent capabilities
  # ---------------------------------------------------------------------------
  tools:
    - name: calculator
      type: CalculatorTool
      config: {}

spec:
  # ---------------------------------------------------------------------------
  # Policies - Use simple preset for basic agents
  # ---------------------------------------------------------------------------
  policies:
    $preset: simple

  # ---------------------------------------------------------------------------
  # Planner - Static planner always calls the same tool
  # ---------------------------------------------------------------------------
  planner:
    type: StaticPlanner
    config:
      tool_name: calculator

  # ---------------------------------------------------------------------------
  # Memory - Standalone in-memory (no sharing needed)
  # ---------------------------------------------------------------------------
  memory:
    $preset: standalone

  # ---------------------------------------------------------------------------
  # Tool References - Must match names in resources.tools
  # ---------------------------------------------------------------------------
  tools: [calculator]
```

## Python Equivalent

```python
import asyncio
from agent_framework import Agent, get_preset
from agent_framework.components.planners import StaticPlanner
from agent_framework.components.memory import InMemoryMemory
from agent_framework.decorators import tool

@tool(name="calculator", description="Evaluate math expressions")
def calculator(expression: str) -> str:
    """Evaluate a mathematical expression."""
    return str(eval(expression))

agent = Agent(
    name="MinimalAgent",
    planner=StaticPlanner(tool_name="calculator"),
    memory=InMemoryMemory(),
    tools=[calculator],
    policies=get_preset("simple"),
)

async def main():
    result = await agent.run("Calculate 25 * 4")
    print(result)

asyncio.run(main())
```

## Running the Agent

```bash
# Set environment variable
export OPENAI_API_KEY="sk-..."

# Load and run
python -c "
from deployment.factory import AgentFactory
import asyncio

agent = AgentFactory.create_from_yaml('configs/agents/minimal_agent.yaml')
result = asyncio.run(agent.run('Calculate 100 / 4'))
print(result)
"
```

## Customization Tips

| What to Change | How |
|----------------|-----|
| Tool | Replace `CalculatorTool` with your tool type |
| Model | Change `gpt-4o-mini` to `gpt-4o` for complex tasks |
| Planner | Switch to `ReActPlanner` for multi-step reasoning |
| Memory | Use `$preset: worker` if this agent joins a team |

## Next Steps

- Add more tools: See [Multi-Tool Agent](multi_tool_agent.md)
- Add reasoning: Switch to `ReActPlanner`
- Join a team: See [Manager + Workers](manager_workers.md)
