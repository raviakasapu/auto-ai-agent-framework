# Pattern: Multi-Tool Agent

An agent with multiple tools and ReAct (Reasoning + Acting) planning for complex tasks.

## When to Use

- Tasks requiring multiple capabilities
- Research agents (search + notes)
- Data processing (read + transform + write)
- Any agent that needs to "think" about which tool to use

## Architecture

```
[User] --> [Agent] --> [Tool A: Search]
              |    --> [Tool B: Notes]
              |    --> [Tool C: Calculator]
              |
        [ReActPlanner]
              |
          [OpenAI]
```

## Complete YAML

Copy this file to `configs/agents/research_agent.yaml`:

```yaml
# =============================================================================
# MULTI-TOOL AGENT PATTERN
# =============================================================================
# An agent with multiple tools and ReAct planning.
# The LLM decides which tool to use based on the task.
# =============================================================================

apiVersion: agent.framework/v2
kind: Agent

metadata:
  name: ResearchAgent
  description: Research assistant with search, notes, and calculation capabilities
  version: 1.0.0

resources:
  # ---------------------------------------------------------------------------
  # Inference Gateway
  # ---------------------------------------------------------------------------
  inference_gateways:
    - name: openai
      type: OpenAIGateway
      config:
        model: ${OPENAI_MODEL:-gpt-4o-mini}
        api_key: ${OPENAI_API_KEY}
        temperature: 0.1
        use_function_calling: true

  # ---------------------------------------------------------------------------
  # Tools - Multiple capabilities
  # ---------------------------------------------------------------------------
  tools:
    - name: web_search
      type: MockSearchTool
      config: {}

    - name: note_taker
      type: NoteTakerTool
      config:
        storage_path: /tmp/research_notes.json

    - name: calculator
      type: CalculatorTool
      config: {}

  # ---------------------------------------------------------------------------
  # Observability (optional but recommended)
  # ---------------------------------------------------------------------------
  subscribers:
    - name: logging
      type: PhoenixSubscriber
      config:
        level: INFO

spec:
  # ---------------------------------------------------------------------------
  # Policies
  # ---------------------------------------------------------------------------
  policies:
    $preset: simple
    termination:
      type: DefaultTerminationPolicy
      config:
        max_iterations: 15
        on_max_iterations: error

  # ---------------------------------------------------------------------------
  # Planner - ReAct for multi-tool reasoning
  # ---------------------------------------------------------------------------
  planner:
    type: ReActPlanner
    config:
      inference_gateway: openai
      use_function_calling: true
      max_iterations: 15
      system_prompt: |
        You are a research assistant with the following capabilities:

        TOOLS AVAILABLE:
        - web_search: Search the web for information on any topic
        - note_taker: Save important findings with title and content
        - calculator: Perform mathematical calculations

        WORKFLOW:
        1. Understand what information the user needs
        2. Search for relevant information using web_search
        3. Save key findings using note_taker
        4. Perform any necessary calculations
        5. Provide a clear summary of your research

        GUIDELINES:
        - Be thorough but concise
        - Always cite your sources
        - Take notes on important findings before summarizing
        - Use calculator for any numerical analysis

  # ---------------------------------------------------------------------------
  # Memory
  # ---------------------------------------------------------------------------
  memory:
    $preset: standalone

  # ---------------------------------------------------------------------------
  # Tool References
  # ---------------------------------------------------------------------------
  tools: [web_search, note_taker, calculator]

  subscribers: [logging]
```

## Python Equivalent

```python
import asyncio
from agent_framework import Agent, EventBus, get_preset
from agent_framework.components.planners import ReActPlanner
from agent_framework.components.memory import InMemoryMemory
from agent_framework.gateways.inference import OpenAIGateway
from agent_framework.decorators import tool

@tool(name="web_search", description="Search the web for information")
def web_search(query: str) -> dict:
    """Search for information on the web."""
    return {
        "results": [f"Result for: {query}"],
        "human_readable_summary": f"Found information about {query}"
    }

@tool(name="note_taker", description="Save research notes")
def note_taker(title: str, content: str) -> dict:
    """Save a research note."""
    return {
        "saved": True,
        "title": title,
        "human_readable_summary": f"Saved note: {title}"
    }

@tool(name="calculator", description="Perform calculations")
def calculator(expression: str) -> str:
    """Evaluate a math expression."""
    return str(eval(expression))

tools = [web_search, note_taker, calculator]
gateway = OpenAIGateway(model="gpt-4o-mini", use_function_calling=True)

agent = Agent(
    name="ResearchAgent",
    planner=ReActPlanner(
        inference_gateway=gateway,
        tools=tools,
        system_prompt="You are a research assistant...",
    ),
    memory=InMemoryMemory(),
    tools=tools,
    policies=get_preset("simple"),
    event_bus=EventBus(),
)

async def main():
    result = await agent.run("Research Python web frameworks and summarize the top 3")
    print(result)

asyncio.run(main())
```

## System Prompt Template

Customize this template for your domain:

```yaml
system_prompt: |
  You are a [ROLE] assistant.

  TOOLS AVAILABLE:
  - [tool_1]: [Description and when to use]
  - [tool_2]: [Description and when to use]
  - [tool_3]: [Description and when to use]

  WORKFLOW:
  1. [First step]
  2. [Second step]
  3. [Continue as needed]
  4. Summarize findings

  GUIDELINES:
  - [Important rule 1]
  - [Important rule 2]
  - [Important rule 3]
```

## Customization Tips

| What to Change | How |
|----------------|-----|
| Add tools | Add to `resources.tools` AND `spec.tools` |
| Change model | Modify `config.model` in gateway |
| Increase iterations | Change `max_iterations` in both planner and termination |
| Enable logging | Add Phoenix or Logging subscriber |
| Share memory | Switch to `$preset: worker` with same `JOB_ID` |

## Common Tool Combinations

| Use Case | Tools |
|----------|-------|
| Research | web_search, note_taker, calculator |
| Task Management | create_task, list_tasks, complete_task |
| Data Analysis | query_database, calculate, visualize |
| Customer Support | search_kb, create_ticket, send_email |

## Next Steps

- Add orchestration: See [Manager + Workers](manager_workers.md)
- Add human approval: See [HITL Approval](hitl_approval.md)
- Share state: See [Shared Memory Team](shared_memory_team.md)
