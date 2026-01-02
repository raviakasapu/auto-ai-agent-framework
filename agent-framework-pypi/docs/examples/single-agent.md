# Single Agent Examples

This page provides complete, working examples of single-agent configurations.

## Calculator Agent

A simple agent that performs mathematical calculations.

### Configuration

```yaml
# configs/agents/calculator.yaml
apiVersion: agent.framework/v2
kind: Agent

metadata:
  name: Calculator
  description: Mathematical calculation assistant
  version: 1.0.0

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
      max_iterations: 5
      system_prompt: |
        You are a calculator assistant.
        Use the calculator tool to solve mathematical problems.
        Show your work and explain the calculation.

  memory:
    $preset: standalone

  tools: [calculator]
```

### Usage

```python
import asyncio
from deployment.factory import create_agent_from_yaml

async def main():
    agent = create_agent_from_yaml("configs/agents/calculator.yaml")

    # Simple calculation
    result = await agent.run("What is 15% of 250?")
    print(result)

    # Complex expression
    result = await agent.run("Calculate (45 * 12) + (30 / 5) - 17")
    print(result)

asyncio.run(main())
```

---

## Research Agent

An agent that searches for information and takes notes.

### Configuration

```yaml
# configs/agents/research_worker.yaml
apiVersion: agent.framework/v2
kind: Agent

metadata:
  name: ResearchWorker
  description: Research assistant that searches and takes notes
  version: 1.0.0

resources:
  inference_gateways:
    - name: openai-worker
      type: OpenAIGateway
      config:
        model: ${OPENAI_MODEL:-gpt-4o-mini}
        api_key: ${OPENAI_API_KEY}
        temperature: 0.1
        use_function_calling: true

  tools:
    - name: web_search
      type: MockSearchTool
      config: {}
    - name: note_taker
      type: NoteTakerTool
      config:
        storage_path: /tmp/research_notes.json

  subscribers:
    - name: logging
      type: PhoenixSubscriber
      config:
        level: INFO
        include_data: true
        max_payload_chars: 2000

spec:
  policies:
    $preset: simple
    termination:
      type: DefaultTerminationPolicy
      config:
        max_iterations: 10
        check_completion: true
        on_max_iterations: error

  planner:
    type: ReActPlanner
    config:
      inference_gateway: openai-worker
      use_function_calling: true
      max_iterations: 10
      system_prompt: |
        You are a research assistant. Your job is to:
        1. Search for information using web_search
        2. Take notes on important findings using note_taker
        3. Provide a summary of your research

        Be thorough and cite your sources.

  memory:
    $preset: worker

  tools: [web_search, note_taker]

  subscribers: [logging]
```

### Usage

```python
import asyncio
from deployment.factory import create_agent_from_yaml

async def main():
    agent = create_agent_from_yaml("configs/agents/research_worker.yaml")

    result = await agent.run(
        "Research the benefits of Python for data science. "
        "Take notes on the key points."
    )
    print(result)

asyncio.run(main())
```

---

## Task Management Agent

An agent for creating and managing tasks.

### Configuration

```yaml
# configs/agents/task_worker.yaml
apiVersion: agent.framework/v2
kind: Agent

metadata:
  name: TaskWorker
  description: Task management assistant
  version: 1.0.0

resources:
  inference_gateways:
    - name: openai-worker
      type: OpenAIGateway
      config:
        model: ${OPENAI_MODEL:-gpt-4o-mini}
        api_key: ${OPENAI_API_KEY}
        temperature: 0.1
        use_function_calling: true

  tools:
    - name: create_task
      type: TaskManagerTool
      config: {}
    - name: list_tasks
      type: ListTasksTool
      config: {}
    - name: complete_task
      type: CompleteTaskTool
      config: {}
    - name: weather_lookup
      type: WeatherLookupTool
      config: {}

spec:
  policies:
    $preset: simple
    termination:
      type: DefaultTerminationPolicy
      config:
        max_iterations: 8
        check_completion: true
        on_max_iterations: error

  planner:
    type: ReActPlanner
    config:
      inference_gateway: openai-worker
      use_function_calling: true
      max_iterations: 8
      system_prompt: |
        You are a task management assistant. Your job is to help users:
        1. Create new tasks with titles, descriptions, and priorities
        2. List existing tasks (optionally filtered by status or priority)
        3. Mark tasks as completed
        4. Check weather (for planning outdoor tasks)

        When creating tasks:
        - Ask for clarification if the task description is unclear
        - Suggest appropriate priority levels based on urgency
        - Confirm task creation with the user

        Be helpful and organized.

  memory:
    $preset: worker

  tools: [create_task, list_tasks, complete_task, weather_lookup]
```

### Usage

```python
import asyncio
from deployment.factory import create_agent_from_yaml

async def main():
    agent = create_agent_from_yaml("configs/agents/task_worker.yaml")

    # Create a task
    result = await agent.run(
        "Create a high-priority task to review the quarterly report"
    )
    print(result)

    # List tasks
    result = await agent.run("List all my tasks")
    print(result)

asyncio.run(main())
```

---

## Weather Agent

A simple single-tool agent for weather lookups.

### Configuration

```yaml
# configs/agents/weather.yaml
apiVersion: agent.framework/v2
kind: Agent

metadata:
  name: WeatherAgent
  description: Weather lookup assistant

resources:
  inference_gateways:
    - name: openai
      type: OpenAIGateway
      config:
        model: ${OPENAI_MODEL:-gpt-4o-mini}
        api_key: ${OPENAI_API_KEY}
        use_function_calling: true

  tools:
    - name: weather
      type: WeatherLookupTool
      config: {}

spec:
  policies:
    $preset: simple

  planner:
    type: ReActPlanner
    config:
      inference_gateway: openai
      use_function_calling: true
      max_iterations: 3
      system_prompt: |
        You are a weather assistant.
        Use the weather tool to look up weather for any location.
        Provide the current conditions and any relevant advice.

  memory:
    $preset: standalone

  tools: [weather]
```

---

## Agent with Observability

An agent with Phoenix/Arize logging enabled.

### Configuration

```yaml
# configs/agents/observable_agent.yaml
apiVersion: agent.framework/v2
kind: Agent

metadata:
  name: ObservableAgent
  description: Agent with full observability

resources:
  inference_gateways:
    - name: openai
      type: OpenAIGateway
      config:
        model: ${OPENAI_MODEL:-gpt-4o-mini}
        api_key: ${OPENAI_API_KEY}
        use_function_calling: true

  tools:
    - name: calculator
      type: CalculatorTool
      config: {}

  subscribers:
    - name: phoenix
      type: PhoenixSubscriber
      config:
        level: DEBUG
        include_data: true
        max_payload_chars: 5000

spec:
  policies:
    $preset: simple

  planner:
    type: ReActPlanner
    config:
      inference_gateway: openai
      use_function_calling: true
      system_prompt: You are a calculator assistant.

  memory:
    $preset: standalone

  tools: [calculator]

  subscribers: [phoenix]
```

---

## Agent with Custom Termination

An agent with extended iteration limits for complex tasks.

### Configuration

```yaml
# configs/agents/complex_researcher.yaml
apiVersion: agent.framework/v2
kind: Agent

metadata:
  name: ComplexResearcher
  description: Agent for complex research tasks

resources:
  inference_gateways:
    - name: openai
      type: OpenAIGateway
      config:
        model: gpt-4o
        api_key: ${OPENAI_API_KEY}
        use_function_calling: true

  tools:
    - name: web_search
      type: MockSearchTool
      config: {}
    - name: note_taker
      type: NoteTakerTool
      config:
        storage_path: /tmp/complex_notes.json

spec:
  policies:
    $preset: simple
    # Override termination for complex tasks
    termination:
      type: DefaultTerminationPolicy
      config:
        max_iterations: 25
        check_completion: true
        on_max_iterations: warn  # Warn instead of error
    # More sensitive loop detection
    loop_prevention:
      type: DefaultLoopPreventionPolicy
      config:
        enabled: true
        action_window: 8
        observation_window: 8
        repetition_threshold: 4
        on_stagnation: warn

  planner:
    type: ReActPlanner
    config:
      inference_gateway: openai
      use_function_calling: true
      max_iterations: 25
      system_prompt: |
        You are a thorough research assistant for complex topics.

        Process:
        1. Break down the research topic into sub-questions
        2. Search for information on each sub-question
        3. Take detailed notes on findings
        4. Cross-reference and verify information
        5. Synthesize into a comprehensive report

        Be thorough - it's better to over-research than under-research.

  memory:
    $preset: worker

  tools: [web_search, note_taker]
```

---

## Testing Single Agents

### Unit Test Example

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_calculator_agent():
    from deployment.factory import create_agent_from_yaml

    agent = create_agent_from_yaml("configs/agents/calculator.yaml")

    # Mock the gateway for unit testing
    mock_gateway = MagicMock()
    mock_gateway.generate = AsyncMock(return_value="The result is 37.5")
    agent.planner.inference_gateway = mock_gateway

    result = await agent.run("What is 15% of 250?")
    assert "37.5" in result or "result" in result.lower()
```

### E2E Test Example

```python
import pytest
import os

@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="Requires OPENAI_API_KEY"
)
@pytest.mark.asyncio
async def test_calculator_e2e():
    from deployment.factory import create_agent_from_yaml

    agent = create_agent_from_yaml("configs/agents/calculator.yaml")
    result = await agent.run("What is 100 divided by 4?")
    assert "25" in result
```
