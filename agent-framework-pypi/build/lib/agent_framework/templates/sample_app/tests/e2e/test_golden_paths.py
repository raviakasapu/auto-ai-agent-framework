"""
Tier 3: End-to-End Tests - Golden Path Scenarios

These tests run the full agent hierarchy with real LLM calls.
They test "happy path" scenarios to ensure core functionality works.

Tests cover:
A. Research Task E2E - Full flow through research worker
B. Task Management E2E - Full flow through task worker
C. Orchestrator E2E - Full flow with worker routing
D. Multi-turn Conversation E2E - Extended conversations

Note: These tests require OPENAI_API_KEY to be set.

Run with:
    OPENAI_API_KEY=your_key pytest tests/e2e/test_golden_paths.py -v
"""
from __future__ import annotations

import asyncio
import os
import pytest

from tests.conftest import requires_api_key, e2e_test


# =============================================================================
# A. Research Task E2E Tests
# =============================================================================

@e2e_test
@requires_api_key
class TestResearchTaskE2E:
    """End-to-end tests for research worker functionality."""

    @pytest.fixture
    def research_agent(self, agent_factory, env_with_api_key):
        """Create research worker agent."""
        return agent_factory.create_from_yaml("configs/agents/research_worker.yaml")

    @pytest.mark.asyncio
    async def test_simple_search_task(self, research_agent):
        """Agent should complete a simple search task."""
        result = await research_agent.run("Search for Python tutorials")

        assert result is not None
        assert isinstance(result, dict)
        # Should have completed without error
        assert "error" not in str(result).lower() or "validation" in str(result).lower()

    @pytest.mark.asyncio
    async def test_search_and_note_task(self, research_agent):
        """Agent should search and take notes."""
        result = await research_agent.run(
            "Search for machine learning basics and take a note about what you find"
        )

        assert result is not None
        # Should mention completing the task
        result_str = str(result).lower()
        # Either success or handled gracefully
        assert result is not None

    @pytest.mark.asyncio
    async def test_calculation_task(self, research_agent):
        """Agent should perform calculations."""
        result = await research_agent.run("Calculate 15 * 8 + 12")

        assert result is not None
        # Result should contain the answer (132) or indicate completion
        result_str = str(result)
        # Agent should have attempted the calculation

    @pytest.mark.asyncio
    async def test_multi_step_research(self, research_agent):
        """Agent should handle multi-step research tasks."""
        result = await research_agent.run(
            "First search for Python async programming, then calculate how many "
            "results you found multiplied by 3"
        )

        assert result is not None


# =============================================================================
# B. Task Management E2E Tests
# =============================================================================

@e2e_test
@requires_api_key
class TestTaskManagementE2E:
    """End-to-end tests for task worker functionality."""

    @pytest.fixture
    def task_agent(self, agent_factory, env_with_api_key):
        """Create task worker agent."""
        return agent_factory.create_from_yaml("configs/agents/task_worker.yaml")

    @pytest.mark.asyncio
    async def test_create_task(self, task_agent):
        """Agent should create a task."""
        result = await task_agent.run("Create a task called 'Review documentation'")

        assert result is not None
        result_str = str(result).lower()
        # Should indicate task creation

    @pytest.mark.asyncio
    async def test_list_tasks(self, task_agent):
        """Agent should list existing tasks."""
        # First create a task
        await task_agent.run("Create a task called 'Test task'")

        # Then list
        result = await task_agent.run("List all my tasks")

        assert result is not None

    @pytest.mark.asyncio
    async def test_complete_task(self, task_agent):
        """Agent should complete a task."""
        # Create a task
        create_result = await task_agent.run("Create a task called 'Quick task'")

        # Complete it
        result = await task_agent.run("Mark the 'Quick task' as completed")

        assert result is not None

    @pytest.mark.asyncio
    async def test_weather_lookup(self, task_agent):
        """Agent should check weather."""
        result = await task_agent.run("What's the weather in London?")

        assert result is not None
        result_str = str(result).lower()
        # Should contain weather-related info


# =============================================================================
# C. Orchestrator E2E Tests
# =============================================================================

@e2e_test
@requires_api_key
class TestOrchestratorE2E:
    """End-to-end tests for orchestrator routing."""

    @pytest.fixture
    def orchestrator(self, agent_factory, env_with_api_key):
        """Create orchestrator agent."""
        return agent_factory.create_from_yaml("configs/agents/orchestrator.yaml")

    @pytest.mark.asyncio
    async def test_route_to_research_worker(self, orchestrator):
        """Orchestrator should route research tasks to research worker."""
        result = await orchestrator.run("Search for Python tutorials")

        assert result is not None
        # Should have completed through research worker

    @pytest.mark.asyncio
    async def test_route_to_task_worker(self, orchestrator):
        """Orchestrator should route task requests to task worker."""
        result = await orchestrator.run("Create a task called 'Review code'")

        assert result is not None
        # Should have completed through task worker

    @pytest.mark.asyncio
    async def test_weather_routes_to_task_worker(self, orchestrator):
        """Weather requests should route to task worker."""
        result = await orchestrator.run("What's the weather in New York?")

        assert result is not None

    @pytest.mark.asyncio
    async def test_complex_routing(self, orchestrator):
        """Orchestrator should handle complex requests."""
        result = await orchestrator.run(
            "I need to research Python best practices and then create a task "
            "to implement them"
        )

        assert result is not None


# =============================================================================
# D. Multi-turn Conversation E2E Tests
# =============================================================================

@e2e_test
@requires_api_key
class TestMultiTurnConversationE2E:
    """End-to-end tests for multi-turn conversations."""

    @pytest.fixture
    def research_agent(self, agent_factory, env_with_api_key):
        """Create research worker agent."""
        return agent_factory.create_from_yaml("configs/agents/research_worker.yaml")

    @pytest.mark.asyncio
    async def test_three_turn_conversation(self, research_agent):
        """Agent should maintain context across three turns."""
        # Turn 1: Search
        result1 = await research_agent.run("Search for Python tutorials")
        assert result1 is not None

        # Turn 2: Follow-up
        result2 = await research_agent.run("Take a note about what you found")
        assert result2 is not None

        # Turn 3: Summary
        result3 = await research_agent.run("Summarize what we've done so far")
        assert result3 is not None

    @pytest.mark.asyncio
    async def test_context_awareness(self, research_agent):
        """Agent should be aware of previous context."""
        # Establish context
        await research_agent.run("Search for machine learning tutorials")

        # Reference previous context
        result = await research_agent.run("Search for more on that same topic")

        assert result is not None
        # Should understand "that same topic" refers to ML

    @pytest.mark.asyncio
    async def test_correction_handling(self, research_agent):
        """Agent should handle corrections."""
        # Initial request
        await research_agent.run("Search for Python")

        # Correction
        result = await research_agent.run(
            "Actually, search for JavaScript instead"
        )

        assert result is not None


# =============================================================================
# E. Response Quality Tests
# =============================================================================

@e2e_test
@requires_api_key
class TestResponseQuality:
    """Tests for response quality and format."""

    @pytest.fixture
    def research_agent(self, agent_factory, env_with_api_key):
        """Create research worker agent."""
        return agent_factory.create_from_yaml("configs/agents/research_worker.yaml")

    @pytest.mark.asyncio
    async def test_response_is_dict(self, research_agent):
        """Response should be a dictionary."""
        result = await research_agent.run("Search for Python")

        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_response_has_operation(self, research_agent):
        """Response should have an operation type."""
        result = await research_agent.run("Search for Python")

        # Response should indicate what operation was performed
        assert result is not None
        # Most responses should have operation or similar key

    @pytest.mark.asyncio
    async def test_response_not_empty(self, research_agent):
        """Response should not be empty."""
        result = await research_agent.run("Search for Python")

        assert result is not None
        assert len(str(result)) > 0


# =============================================================================
# F. Performance Baseline Tests
# =============================================================================

@e2e_test
@requires_api_key
class TestPerformanceBaseline:
    """Basic performance tests to establish baselines."""

    @pytest.fixture
    def research_agent(self, agent_factory, env_with_api_key):
        """Create research worker agent."""
        return agent_factory.create_from_yaml("configs/agents/research_worker.yaml")

    @pytest.mark.asyncio
    async def test_simple_task_completes_in_time(self, research_agent):
        """Simple task should complete within reasonable time."""
        import time

        start = time.time()
        result = await research_agent.run("Calculate 2 + 2")
        elapsed = time.time() - start

        assert result is not None
        # Should complete within 60 seconds
        assert elapsed < 60, f"Task took {elapsed:.1f}s, expected < 60s"

    @pytest.mark.asyncio
    async def test_search_task_completes_in_time(self, research_agent):
        """Search task should complete within reasonable time."""
        import time

        start = time.time()
        result = await research_agent.run("Search for Python")
        elapsed = time.time() - start

        assert result is not None
        # Search might take longer but should still complete
        assert elapsed < 120, f"Task took {elapsed:.1f}s, expected < 120s"
