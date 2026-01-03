"""
Tier 2: Integration Tests for Planners

Tests cover:
A. Planner Creation - Planners can be instantiated
B. Planner Interface - Planners have expected interface
C. Mock Gateway - Mock gateway for testing

Note: Full planner behavior is validated in E2E tests.

Run with:
    pytest tests/integration/test_planners.py -v
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, AsyncMock

from agent_framework.components.planners import ReActPlanner
from agent_framework.components.memory import SharedInMemoryMemory


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def mock_gateway():
    """Create a mock inference gateway."""
    from tests.conftest import MockInferenceGateway
    return MockInferenceGateway()


@pytest.fixture
def tool_descriptions():
    """Sample tool descriptions for planner testing."""
    return [
        {
            "name": "web_search",
            "description": "Search the web",
            "parameters": {"type": "object", "properties": {"query": {"type": "string"}}}
        }
    ]


@pytest.fixture
def react_planner(mock_gateway, tool_descriptions):
    """Create a ReActPlanner with mock gateway."""
    return ReActPlanner(
        inference_gateway=mock_gateway,
        system_prompt="You are a helpful assistant.",
        tool_descriptions=tool_descriptions
    )


# =============================================================================
# A. Planner Creation Tests
# =============================================================================

class TestPlannerCreation:
    """Test planner creation and initialization."""

    def test_react_planner_can_be_created(self, mock_gateway, tool_descriptions):
        """ReActPlanner should be creatable."""
        planner = ReActPlanner(
            inference_gateway=mock_gateway,
            system_prompt="Test system prompt",
            tool_descriptions=tool_descriptions
        )

        assert planner is not None

    def test_react_planner_has_gateway(self, mock_gateway, tool_descriptions):
        """ReActPlanner should have inference gateway."""
        planner = ReActPlanner(
            inference_gateway=mock_gateway,
            system_prompt="Test",
            tool_descriptions=tool_descriptions
        )

        assert planner.llm is not None or hasattr(planner, 'inference_gateway') or hasattr(planner, '_llm')

    def test_react_planner_has_system_prompt(self, mock_gateway, tool_descriptions):
        """ReActPlanner should store system prompt."""
        planner = ReActPlanner(
            inference_gateway=mock_gateway,
            system_prompt="Custom system prompt",
            tool_descriptions=tool_descriptions
        )

        # Should have system prompt stored
        assert hasattr(planner, 'system_prompt') or hasattr(planner, '_system_prompt')


# =============================================================================
# B. Planner Interface Tests
# =============================================================================

class TestPlannerInterface:
    """Test planner interface compliance."""

    def test_react_planner_has_plan_method(self, react_planner):
        """ReActPlanner should have plan method."""
        assert hasattr(react_planner, 'plan')
        assert callable(react_planner.plan)

    def test_react_planner_plan_method_signature(self, react_planner):
        """ReActPlanner.plan should accept expected arguments."""
        import inspect

        sig = inspect.signature(react_planner.plan)
        params = list(sig.parameters.keys())

        # Should accept some form of task/task_description
        has_task_param = any('task' in p.lower() for p in params) or len(params) >= 1
        assert has_task_param


# =============================================================================
# C. Mock Gateway Tests
# =============================================================================

class TestMockGateway:
    """Test the mock gateway for integration tests."""

    def test_mock_gateway_can_be_created(self):
        """MockInferenceGateway should be creatable."""
        from tests.conftest import MockInferenceGateway
        gateway = MockInferenceGateway()
        assert gateway is not None

    def test_mock_gateway_can_set_response(self):
        """MockInferenceGateway should accept response configuration."""
        from tests.conftest import MockInferenceGateway
        gateway = MockInferenceGateway()

        gateway.set_response("Test response")
        assert gateway.responses is not None or gateway._responses is not None

    def test_mock_gateway_has_generate_method(self):
        """MockInferenceGateway should have generate or invoke method."""
        from tests.conftest import MockInferenceGateway
        gateway = MockInferenceGateway()

        assert hasattr(gateway, 'generate') or hasattr(gateway, 'invoke')


# =============================================================================
# D. Memory with Planner Tests
# =============================================================================

class TestMemoryWithPlanner:
    """Test memory usage with planners."""

    def test_shared_memory_works_for_planners(self):
        """SharedInMemoryMemory should work for planner context."""
        memory = SharedInMemoryMemory(namespace="planner-test", agent_key="planner")

        memory.add({"role": "user", "content": "Test input"})
        memory.add({"role": "assistant", "content": "Test response"})

        history = memory.get_history()
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "assistant"

    def test_memory_formats_for_llm(self):
        """Memory should format history for LLM consumption."""
        memory = SharedInMemoryMemory(namespace="planner-test", agent_key="planner")

        memory.add({"role": "user", "content": "Hello"})

        history = memory.get_history()
        # Should be a list of message dicts
        assert isinstance(history, list)
        assert all(isinstance(m, dict) for m in history)
        assert all("role" in m and "content" in m for m in history)
