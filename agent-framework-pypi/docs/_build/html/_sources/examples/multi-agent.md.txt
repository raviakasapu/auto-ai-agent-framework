# Multi-Agent Examples

This page provides complete examples of multi-agent systems with managers and workers.

## Basic Manager-Worker System

A simple orchestrator with two specialized workers.

### Directory Structure

```
configs/agents/
├── orchestrator.yaml
├── research_worker.yaml
└── task_worker.yaml
```

### Orchestrator Configuration

```yaml
# configs/agents/orchestrator.yaml
apiVersion: agent.framework/v2
kind: ManagerAgent

metadata:
  name: Orchestrator
  description: Routes tasks to appropriate workers
  version: 1.0.0

resources:
  inference_gateways:
    - name: openai-orchestrator
      type: OpenAIGateway
      config:
        model: ${OPENAI_MODEL:-gpt-4o-mini}
        api_key: ${OPENAI_API_KEY}

  subscribers:
    - name: logging
      type: PhoenixSubscriber
      config:
        level: INFO
        include_data: true
        max_payload_chars: 2000

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
        You are a task router. Analyze requests and route them appropriately.

        Available workers:
        - research-worker: For searching, researching, and taking notes
        - task-worker: For creating tasks, listing tasks, and task management

        Route research/search/notes requests to research-worker.
        Route task/todo/schedule requests to task-worker.

        Return JSON: {"worker": "<key>", "reason": "..."}

  memory:
    $preset: manager

  workers:
    - name: research-worker
      config_path: configs/agents/research_worker.yaml
    - name: task-worker
      config_path: configs/agents/task_worker.yaml

  subscribers: [logging]
```

### Research Worker Configuration

```yaml
# configs/agents/research_worker.yaml
apiVersion: agent.framework/v2
kind: Agent

metadata:
  name: ResearchWorker
  description: Research and note-taking specialist

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

spec:
  policies:
    $preset: simple

  planner:
    type: ReActPlanner
    config:
      inference_gateway: openai-worker
      use_function_calling: true
      max_iterations: 10
      system_prompt: |
        You are a research specialist. Your job is to:
        1. Search for information using web_search
        2. Take notes on important findings using note_taker
        3. Provide clear summaries

  memory:
    $preset: worker

  tools: [web_search, note_taker]
```

### Task Worker Configuration

```yaml
# configs/agents/task_worker.yaml
apiVersion: agent.framework/v2
kind: Agent

metadata:
  name: TaskWorker
  description: Task management specialist

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

spec:
  policies:
    $preset: simple

  planner:
    type: ReActPlanner
    config:
      inference_gateway: openai-worker
      use_function_calling: true
      max_iterations: 8
      system_prompt: |
        You are a task management specialist. Help users:
        1. Create new tasks with appropriate priorities
        2. List and filter existing tasks
        3. Mark tasks as completed

  memory:
    $preset: worker

  tools: [create_task, list_tasks, complete_task]
```

### Usage

```python
import asyncio
from deployment.factory import create_agent_from_yaml

async def main():
    # Load the orchestrator (workers are loaded automatically)
    manager = create_agent_from_yaml("configs/agents/orchestrator.yaml")

    # Research request -> routes to research-worker
    result = await manager.run("Search for Python web frameworks and take notes")
    print("Research result:", result)

    # Task request -> routes to task-worker
    result = await manager.run("Create a task to review the Python research")
    print("Task result:", result)

asyncio.run(main())
```

---

## Three-Worker System

An extended example with three specialized workers.

### Orchestrator

```yaml
# configs/agents/universal_orchestrator.yaml
apiVersion: agent.framework/v2
kind: ManagerAgent

metadata:
  name: UniversalOrchestrator
  description: Routes to research, task, and calculator workers

resources:
  inference_gateways:
    - name: openai
      type: OpenAIGateway
      config:
        model: gpt-4o
        api_key: ${OPENAI_API_KEY}

spec:
  policies:
    $preset: manager_with_followups

  planner:
    type: WorkerRouterPlanner
    config:
      inference_gateway: openai
      worker_keys: [research, tasks, calculator]
      default_worker: research
      system_prompt: |
        You are a universal assistant router.

        Available workers:
        - research: Web search, information gathering, note-taking
          Keywords: search, find, research, look up, information
        - tasks: Task creation, listing, completion
          Keywords: task, todo, create, list, complete, done
        - calculator: Mathematical calculations
          Keywords: calculate, math, numbers, percentage, sum

        Analyze the request and route to the appropriate worker.

        Response: {"worker": "<key>", "reason": "..."}

  memory:
    $preset: manager

  workers:
    - name: research
      config_path: configs/agents/research_worker.yaml
    - name: tasks
      config_path: configs/agents/task_worker.yaml
    - name: calculator
      config_path: configs/agents/calculator_worker.yaml
```

### Calculator Worker

```yaml
# configs/agents/calculator_worker.yaml
apiVersion: agent.framework/v2
kind: Agent

metadata:
  name: CalculatorWorker
  description: Mathematical calculation specialist

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
      max_iterations: 5
      system_prompt: |
        You are a calculator specialist.
        Use the calculator tool for all mathematical operations.
        Show your work and explain the calculation.

  memory:
    $preset: worker

  tools: [calculator]
```

---

## Shared Memory Example

Demonstrating state sharing between workers.

### Orchestrator with Shared State

```yaml
# configs/agents/stateful_orchestrator.yaml
apiVersion: agent.framework/v2
kind: ManagerAgent

metadata:
  name: StatefulOrchestrator

resources:
  inference_gateways:
    - name: openai
      type: OpenAIGateway
      config:
        model: gpt-4o
        api_key: ${OPENAI_API_KEY}

spec:
  policies:
    $preset: manager_with_followups

  planner:
    type: WorkerRouterPlanner
    config:
      inference_gateway: openai
      worker_keys: [researcher, analyzer]
      default_worker: researcher
      system_prompt: |
        Route between workers:
        - researcher: Gathers information and stores in shared state
        - analyzer: Reads shared state and provides analysis

        For research requests, use researcher.
        For analysis of existing research, use analyzer.

        Response: {"worker": "<key>", "reason": "..."}

  memory:
    $preset: manager

  workers:
    - name: researcher
      config_path: configs/agents/stateful_researcher.yaml
    - name: analyzer
      config_path: configs/agents/stateful_analyzer.yaml
```

### Python Usage with Shared State

```python
import asyncio
import os
from deployment.factory import create_agent_from_yaml

async def main():
    # Set JOB_ID for consistent namespace across workers
    os.environ["JOB_ID"] = "shared-job-123"

    manager = create_agent_from_yaml("configs/agents/stateful_orchestrator.yaml")

    # First request: research and store in shared state
    result = await manager.run("Research machine learning frameworks")
    print("Research:", result)

    # Second request: analyze the stored research
    result = await manager.run("Analyze the research we just gathered")
    print("Analysis:", result)

asyncio.run(main())
```

---

## Follow-Up Phases Example

Manager that coordinates multiple follow-up phases.

### Configuration

```yaml
# configs/agents/iterative_manager.yaml
apiVersion: agent.framework/v2
kind: ManagerAgent

metadata:
  name: IterativeManager
  description: Coordinates multi-phase work

resources:
  inference_gateways:
    - name: openai
      type: OpenAIGateway
      config:
        model: gpt-4o
        api_key: ${OPENAI_API_KEY}

spec:
  policies:
    $preset: manager_with_followups
    follow_up:
      type: DefaultFollowUpPolicy
      config:
        enabled: true
        max_phases: 5
        check_completion: true
        stop_on_completion: true

  planner:
    type: WorkerRouterPlanner
    config:
      inference_gateway: openai
      worker_keys: [research, synthesis]
      default_worker: research
      system_prompt: |
        You manage a two-phase process:
        1. Research phase: Gather information
        2. Synthesis phase: Combine and summarize

        Route initial research requests to "research".
        Route synthesis requests to "synthesis".

        The system will automatically follow up after each phase.

        Response: {"worker": "<key>", "reason": "..."}

  memory:
    $preset: manager

  workers:
    - name: research
      config_path: configs/agents/research_worker.yaml
    - name: synthesis
      config_path: configs/agents/synthesis_worker.yaml
```

---

## Testing Multi-Agent Systems

### Unit Test

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

@pytest.mark.asyncio
async def test_orchestrator_routing():
    from deployment.factory import create_agent_from_yaml

    with patch.dict('os.environ', {'JOB_ID': 'test-job'}):
        manager = create_agent_from_yaml("configs/agents/orchestrator.yaml")

    # Mock the router planner
    manager.planner.route = AsyncMock(return_value="research-worker")

    # Mock the worker
    mock_worker = MagicMock()
    mock_worker.run = AsyncMock(return_value="Research complete")
    manager.workers["research-worker"] = mock_worker

    result = await manager.run("Search for Python frameworks")

    manager.planner.route.assert_called()
    mock_worker.run.assert_called()
```

### Integration Test

```python
import pytest
import os

@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="Requires OPENAI_API_KEY"
)
@pytest.mark.asyncio
async def test_manager_worker_integration():
    os.environ["JOB_ID"] = "integration-test"

    from deployment.factory import create_agent_from_yaml

    manager = create_agent_from_yaml("configs/agents/orchestrator.yaml")

    # Test routing to research worker
    result = await manager.run("Search for AI frameworks")
    assert result is not None
    assert len(result) > 0

    # Test routing to task worker
    result = await manager.run("Create a task to review AI frameworks")
    assert result is not None
```

### E2E Test

```python
import pytest
import os

@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="Requires OPENAI_API_KEY"
)
@pytest.mark.asyncio
async def test_full_workflow():
    """Test a complete research-to-task workflow."""
    os.environ["JOB_ID"] = "e2e-test"

    from deployment.factory import create_agent_from_yaml

    manager = create_agent_from_yaml("configs/agents/orchestrator.yaml")

    # Step 1: Research
    research_result = await manager.run(
        "Research Python testing frameworks"
    )
    assert "pytest" in research_result.lower() or "test" in research_result.lower()

    # Step 2: Create task based on research
    task_result = await manager.run(
        "Create a task to evaluate the testing frameworks"
    )
    assert "task" in task_result.lower() or "created" in task_result.lower()
```

---

## Best Practices

1. **Clear routing rules** - Make worker responsibilities explicit in the router prompt
2. **Consistent memory presets** - Use `worker` for workers, `manager` for managers
3. **Shared JOB_ID** - Set JOB_ID environment variable for memory namespace isolation
4. **Independent workers** - Each worker should be testable in isolation
5. **Appropriate iteration limits** - Workers may need fewer iterations than standalone agents
6. **Logging** - Enable subscribers for debugging multi-agent interactions
