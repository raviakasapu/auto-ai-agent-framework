# Testing Guide

This guide covers the testing approach and best practices for the AI Agent Framework.

## Test Structure

The framework uses a three-tier testing approach:

```
tests/
├── unit/           # Fast, isolated unit tests
├── integration/    # Component integration tests
└── e2e/            # End-to-end tests with real APIs
```

## Running Tests

### All Tests

```bash
pytest
```

### By Category

```bash
# Unit tests only
pytest tests/unit/

# Integration tests
pytest tests/integration/

# E2E tests (requires API key)
OPENAI_API_KEY=your-key pytest tests/e2e/
```

### With Coverage

```bash
pytest --cov=agent_framework --cov-report=html
```

## Unit Tests

Unit tests are fast, isolated tests that mock external dependencies.

### Example: Testing a Tool

```python
import pytest
from tools.calculator_tool import CalculatorTool


@pytest.mark.asyncio
async def test_calculator_addition():
    tool = CalculatorTool()
    result = await tool.execute(expression="2 + 2")
    assert result["result"] == 4


@pytest.mark.asyncio
async def test_calculator_handles_invalid_expression():
    tool = CalculatorTool()
    result = await tool.execute(expression="invalid")
    assert "error" in result
```

### Example: Testing an Agent with Mocks

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from deployment.factory import create_agent_from_yaml


@pytest.mark.asyncio
async def test_agent_calls_tool():
    agent = create_agent_from_yaml("configs/agents/calculator.yaml")

    # Mock the inference gateway
    mock_gateway = MagicMock()
    mock_gateway.generate = AsyncMock(
        return_value='{"tool": "calculator", "expression": "5 * 3"}'
    )
    agent.planner.inference_gateway = mock_gateway

    result = await agent.run("Calculate 5 times 3")
    assert result is not None
```

### Example: Testing Memory Presets

```python
import pytest
from agent_framework.components.memory_presets import (
    get_memory_preset,
    list_memory_presets,
)


def test_list_presets():
    presets = list_memory_presets()
    assert "standalone" in presets
    assert "worker" in presets
    assert "manager" in presets


def test_worker_preset_creates_shared_memory():
    from agent_framework.components.memory import SharedInMemoryMemory

    memory = get_memory_preset("worker", {"agent_name": "TestAgent"})
    assert isinstance(memory, SharedInMemoryMemory)
```

## Integration Tests

Integration tests verify that components work together correctly.

### Example: Agent Loop Test

```python
import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.mark.asyncio
async def test_agent_loop_executes_tools():
    from deployment.factory import create_agent_from_yaml

    agent = create_agent_from_yaml("configs/agents/task_worker.yaml")

    # Mock gateway to return tool call then completion
    responses = [
        '{"tool": "create_task", "title": "Test", "priority": "high"}',
        "Task created successfully. The task 'Test' has been added."
    ]
    mock_gateway = MagicMock()
    mock_gateway.generate = AsyncMock(side_effect=responses)
    agent.planner.inference_gateway = mock_gateway

    result = await agent.run("Create a high priority test task")
    assert "task" in result.lower() or "created" in result.lower()
```

### Example: Manager-Worker Integration

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import os


@pytest.mark.asyncio
async def test_manager_routes_to_worker():
    with patch.dict(os.environ, {"JOB_ID": "test-job"}):
        from deployment.factory import create_agent_from_yaml

        manager = create_agent_from_yaml("configs/agents/orchestrator.yaml")

        # Mock router to select research worker
        manager.planner.route = AsyncMock(return_value="research-worker")

        # Mock worker
        mock_worker = MagicMock()
        mock_worker.run = AsyncMock(return_value="Research complete")
        manager.workers["research-worker"] = mock_worker

        result = await manager.run("Search for Python frameworks")

        manager.planner.route.assert_called_once()
        mock_worker.run.assert_called_once()
```

## E2E Tests

End-to-end tests use real API calls and verify complete workflows.

### Skip Decorator

```python
import pytest
import os

SKIP_E2E = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="Requires OPENAI_API_KEY for E2E tests"
)
```

### Example: Real Agent Test

```python
import pytest
import os

SKIP_E2E = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="Requires OPENAI_API_KEY"
)


@SKIP_E2E
@pytest.mark.asyncio
async def test_calculator_e2e():
    from deployment.factory import create_agent_from_yaml

    agent = create_agent_from_yaml("configs/agents/calculator.yaml")
    result = await agent.run("What is 25% of 200?")

    assert "50" in result


@SKIP_E2E
@pytest.mark.asyncio
async def test_manager_e2e():
    os.environ["JOB_ID"] = "e2e-test"
    from deployment.factory import create_agent_from_yaml

    manager = create_agent_from_yaml("configs/agents/orchestrator.yaml")
    result = await manager.run("Search for machine learning")

    assert result is not None
    assert len(result) > 0
```

## Fixtures

### Common Fixtures

```python
# conftest.py
import pytest
import os


@pytest.fixture
def mock_env():
    """Set up test environment variables."""
    original = os.environ.copy()
    os.environ["JOB_ID"] = "test-job"
    os.environ["OPENAI_API_KEY"] = "test-key"
    yield
    os.environ.clear()
    os.environ.update(original)


@pytest.fixture
def mock_gateway():
    """Create a mock inference gateway."""
    from unittest.mock import AsyncMock, MagicMock

    gateway = MagicMock()
    gateway.generate = AsyncMock(return_value="Test response")
    return gateway
```

## Best Practices

1. **Isolate unit tests** - Mock all external dependencies
2. **Test edge cases** - Invalid inputs, timeouts, errors
3. **Use descriptive names** - `test_calculator_handles_division_by_zero`
4. **Keep tests fast** - Unit tests should run in milliseconds
5. **Mark slow tests** - Use `@pytest.mark.slow` for E2E tests
6. **Clean up state** - Reset memory and globals between tests
7. **Test both success and failure** - Verify error handling
8. **Use fixtures** - Share common setup code

## Test Coverage

The framework maintains high test coverage:

| Category | Tests | Coverage |
|----------|-------|----------|
| Unit | 103+ | Core components |
| Integration | 24+ | Component interactions |
| E2E | 43+ | Complete workflows |

Run coverage report:

```bash
pytest --cov=agent_framework --cov-report=term-missing
```
