# Quickstart Guide

This guide provides practical examples to get you productive quickly with the AI Agent Framework.

## Single Agent Examples

### Calculator Agent

A simple agent with mathematical capabilities:

```yaml
apiVersion: agent.framework/v2
kind: Agent

metadata:
  name: CalculatorAgent

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

spec:
  policies:
    $preset: simple

  planner:
    type: ReActPlanner
    config:
      inference_gateway: openai
      use_function_calling: true
      system_prompt: |
        You are a calculator assistant.
        Use the calculator tool to solve math problems.

  memory:
    $preset: standalone

  tools: [calculator]
```

### Research Agent

An agent that can search and take notes:

```yaml
apiVersion: agent.framework/v2
kind: Agent

metadata:
  name: ResearchAgent

resources:
  inference_gateways:
    - name: openai
      type: OpenAIGateway
      config:
        model: ${OPENAI_MODEL:-gpt-4o-mini}
        api_key: ${OPENAI_API_KEY}
        use_function_calling: true

  tools:
    - name: web_search
      type: MockSearchTool
      config: {}
    - name: note_taker
      type: NoteTakerTool
      config:
        storage_path: /tmp/notes.json

spec:
  policies:
    $preset: simple

  planner:
    type: ReActPlanner
    config:
      inference_gateway: openai
      use_function_calling: true
      system_prompt: |
        You are a research assistant.
        1. Use web_search to find information
        2. Use note_taker to save important findings
        Always summarize your research at the end.

  memory:
    $preset: worker

  tools: [web_search, note_taker]
```

## Multi-Agent System

### Manager-Worker Architecture

Create a system where a manager routes tasks to specialized workers.

#### Manager (Orchestrator)

```yaml
# configs/agents/orchestrator.yaml
apiVersion: agent.framework/v2
kind: ManagerAgent

metadata:
  name: Orchestrator
  description: Routes tasks to appropriate workers

resources:
  inference_gateways:
    - name: openai-orchestrator
      type: OpenAIGateway
      config:
        model: ${OPENAI_MODEL:-gpt-4o-mini}
        api_key: ${OPENAI_API_KEY}

spec:
  policies:
    $preset: manager_with_followups

  planner:
    type: WorkerRouterPlanner
    config:
      inference_gateway: openai-orchestrator
      worker_keys: [research-worker, task-worker]
      default_worker: research-worker
      system_prompt: |
        You are a task router. Route requests to the appropriate worker:
        - research-worker: For search and information gathering
        - task-worker: For task management and weather queries

        Return JSON: {"worker": "<key>", "reason": "..."}

  memory:
    $preset: manager

  workers:
    - name: research-worker
      config_path: configs/agents/research_worker.yaml
    - name: task-worker
      config_path: configs/agents/task_worker.yaml
```

#### Research Worker

```yaml
# configs/agents/research_worker.yaml
apiVersion: agent.framework/v2
kind: Agent

metadata:
  name: ResearchWorker

resources:
  inference_gateways:
    - name: openai-worker
      type: OpenAIGateway
      config:
        model: ${OPENAI_MODEL:-gpt-4o-mini}
        api_key: ${OPENAI_API_KEY}
        use_function_calling: true

  tools:
    - name: web_search
      type: MockSearchTool
      config: {}
    - name: note_taker
      type: NoteTakerTool
      config:
        storage_path: /tmp/research_notes.json

spec:
  policies:
    $preset: simple

  planner:
    type: ReActPlanner
    config:
      inference_gateway: openai-worker
      use_function_calling: true
      system_prompt: |
        You are a research assistant.
        Search for information and take notes on findings.

  memory:
    $preset: worker

  tools: [web_search, note_taker]
```

#### Task Worker

```yaml
# configs/agents/task_worker.yaml
apiVersion: agent.framework/v2
kind: Agent

metadata:
  name: TaskWorker

resources:
  inference_gateways:
    - name: openai-worker
      type: OpenAIGateway
      config:
        model: ${OPENAI_MODEL:-gpt-4o-mini}
        api_key: ${OPENAI_API_KEY}
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

spec:
  policies:
    $preset: simple

  planner:
    type: ReActPlanner
    config:
      inference_gateway: openai-worker
      use_function_calling: true
      system_prompt: |
        You are a task manager.
        Create, list, and complete tasks as requested.

  memory:
    $preset: worker

  tools: [create_task, list_tasks, complete_task]
```

## Running Agents

### Single Agent

```python
import asyncio
from deployment.factory import create_agent_from_yaml

async def main():
    agent = create_agent_from_yaml("configs/agents/research_worker.yaml")
    result = await agent.run("Search for Python best practices")
    print(result)

asyncio.run(main())
```

### Manager with Workers

```python
import asyncio
from deployment.factory import create_agent_from_yaml

async def main():
    manager = create_agent_from_yaml("configs/agents/orchestrator.yaml")

    # Manager routes to appropriate worker
    result = await manager.run("Research AI frameworks and create a task to evaluate them")
    print(result)

asyncio.run(main())
```

## Testing Your Agents

### Unit Tests

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

def test_agent_config_loads():
    """Verify config loads without errors."""
    from deployment.factory import create_agent_from_yaml
    agent = create_agent_from_yaml("configs/agents/my_agent.yaml")
    assert agent is not None

@pytest.mark.asyncio
async def test_agent_with_mock_gateway():
    """Test agent with mocked LLM."""
    from deployment.factory import create_agent_from_yaml

    agent = create_agent_from_yaml("configs/agents/my_agent.yaml")

    # Mock the inference gateway
    agent.planner.inference_gateway = MagicMock()
    agent.planner.inference_gateway.generate = AsyncMock(
        return_value="Task completed successfully."
    )

    result = await agent.run("Test task")
    assert "completed" in result.lower()
```

### E2E Tests (with real API)

```python
import pytest
import os

@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="Requires OPENAI_API_KEY"
)
@pytest.mark.asyncio
async def test_real_agent():
    """E2E test with real API."""
    from deployment.factory import create_agent_from_yaml

    agent = create_agent_from_yaml("configs/agents/my_agent.yaml")
    result = await agent.run("What is 2 + 2?")
    assert "4" in result

```

## Common Patterns

### Environment Variable Substitution

```yaml
config:
  api_key: ${OPENAI_API_KEY}              # Required
  model: ${OPENAI_MODEL:-gpt-4o-mini}     # With default
  namespace: ${JOB_ID:-default}           # For job isolation
```

### Custom Tool Registration

```python
# tools/custom_tools.py
from agent_framework.core.types import Tool

class MyCustomTool(Tool):
    name = "my_tool"
    description = "Does something custom"

    async def execute(self, **kwargs):
        # Implementation
        return {"result": "success"}

# Register in factory
TOOL_REGISTRY["MyCustomTool"] = MyCustomTool
```

### Adding Observability

```yaml
resources:
  subscribers:
    - name: logging
      type: PhoenixSubscriber
      config:
        level: INFO
        include_data: true
        max_payload_chars: 2000

spec:
  subscribers: [logging]
```

## Next Steps

- [YAML Configuration Guide](guides/yaml-configuration.md) - Full configuration reference
- [Memory Presets](guides/memory-presets.md) - Memory configuration options
- [Policy Presets](guides/policy-presets.md) - Behavior policies
- [Tools Guide](guides/tools.md) - Built-in and custom tools
