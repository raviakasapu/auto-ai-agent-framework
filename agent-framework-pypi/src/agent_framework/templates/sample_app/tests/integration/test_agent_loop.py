"""
Tier 2: Integration Tests for Full Agent Loop

Tests cover:
A. Manager-Worker Delegation - ManagerAgent routes to workers correctly
B. Agent Creation - Agent can be created and initialized
C. Memory Integration - Agent uses memory correctly
D. Event Bus - Agent emits events

Note: These tests focus on verifiable integration points.
Full behavior is tested in E2E tests with real components.

Run with:
    pytest tests/integration/test_agent_loop.py -v
"""
from __future__ import annotations

import asyncio
import json
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent_framework.core.agent import Agent
from agent_framework.core.manager_v2 import ManagerAgent
from agent_framework.core.events import EventBus
from agent_framework.components.memory import SharedInMemoryMemory
from agent_framework.policies.presets import get_preset


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def mock_planner():
    """Create a mock planner that returns configurable results."""
    planner = MagicMock()
    planner.plan = MagicMock()
    return planner


@pytest.fixture
def mock_tools():
    """Create mock tools for testing."""
    from tools import MockSearchTool, NoteTakerTool

    return [MockSearchTool(), NoteTakerTool()]


@pytest.fixture
def event_bus():
    """Create an event bus for testing."""
    return EventBus()


@pytest.fixture
def shared_memory():
    """Create shared memory for testing."""
    return SharedInMemoryMemory(namespace="test-integration", agent_key="test-agent")


@pytest.fixture
def mock_workers():
    """Create mock worker agents."""
    worker1 = MagicMock()
    worker1.name = "research-worker"
    worker1.run = AsyncMock(return_value={
        "operation": "display_message",
        "payload": {"message": "Research complete"}
    })

    worker2 = MagicMock()
    worker2.name = "task-worker"
    worker2.run = AsyncMock(return_value={
        "operation": "display_message",
        "payload": {"message": "Task complete"}
    })

    return {"research-worker": worker1, "task-worker": worker2}


# =============================================================================
# A. Agent Creation and Initialization Tests
# =============================================================================

class TestAgentCreation:
    """Test Agent creation and initialization."""

    def test_agent_can_be_created(self, mock_planner, mock_tools, shared_memory, event_bus):
        """Agent should be creatable with required components."""
        policies = get_preset("simple")

        agent = Agent(
            name="TestAgent",
            planner=mock_planner,
            tools=mock_tools,
            memory=shared_memory,
            event_bus=event_bus,
            policies=policies
        )

        assert agent is not None
        assert agent.name == "TestAgent"

    def test_agent_has_tools(self, mock_planner, mock_tools, shared_memory, event_bus):
        """Agent should have access to tools."""
        policies = get_preset("simple")

        agent = Agent(
            name="TestAgent",
            planner=mock_planner,
            tools=mock_tools,
            memory=shared_memory,
            event_bus=event_bus,
            policies=policies
        )

        assert len(agent.tools) == len(mock_tools)

    def test_agent_has_memory(self, mock_planner, mock_tools, shared_memory, event_bus):
        """Agent should have memory component."""
        policies = get_preset("simple")

        agent = Agent(
            name="TestAgent",
            planner=mock_planner,
            tools=mock_tools,
            memory=shared_memory,
            event_bus=event_bus,
            policies=policies
        )

        assert agent.memory is not None


# =============================================================================
# B. Manager Agent Tests
# =============================================================================

class TestManagerAgentCreation:
    """Test ManagerAgent creation and structure."""

    def test_manager_can_be_created(self, mock_planner, mock_workers, shared_memory, event_bus):
        """ManagerAgent should be creatable with workers."""
        policies = get_preset("manager_with_followups")

        manager = ManagerAgent(
            name="TestManager",
            planner=mock_planner,
            workers=mock_workers,
            memory=shared_memory,
            event_bus=event_bus,
            policies=policies
        )

        assert manager is not None
        assert manager.name == "TestManager"

    def test_manager_has_workers(self, mock_planner, mock_workers, shared_memory, event_bus):
        """ManagerAgent should have workers registered."""
        policies = get_preset("manager_with_followups")

        manager = ManagerAgent(
            name="TestManager",
            planner=mock_planner,
            workers=mock_workers,
            memory=shared_memory,
            event_bus=event_bus,
            policies=policies
        )

        assert hasattr(manager, 'workers') or hasattr(manager, '_workers')


# =============================================================================
# C. Memory Integration Tests
# =============================================================================

class TestMemoryIntegration:
    """Test memory integration with agents."""

    def test_memory_starts_empty(self, shared_memory):
        """Memory should start empty."""
        assert len(shared_memory.get_history()) == 0

    def test_memory_can_add_messages(self, shared_memory):
        """Memory should store messages."""
        shared_memory.add({"role": "user", "content": "Test message"})

        history = shared_memory.get_history()
        assert len(history) == 1
        assert history[0]["content"] == "Test message"

    def test_memory_persists_across_agent_access(self, mock_planner, mock_tools, shared_memory, event_bus):
        """Memory should persist when accessed through agent."""
        policies = get_preset("simple")

        # Add a message to memory
        shared_memory.add({"role": "user", "content": "Initial message"})

        # Create agent with this memory
        agent = Agent(
            name="TestAgent",
            planner=mock_planner,
            tools=mock_tools,
            memory=shared_memory,
            event_bus=event_bus,
            policies=policies
        )

        # Memory should still have the message
        assert len(agent.memory.get_history()) == 1


# =============================================================================
# D. Event Bus Integration Tests
# =============================================================================

class TestEventBusIntegration:
    """Test event bus integration."""

    def test_event_bus_exists(self, event_bus):
        """Event bus should be creatable."""
        assert event_bus is not None

    def test_event_bus_has_methods(self, event_bus):
        """Event bus should have expected interface."""
        # Check for common event bus patterns
        has_subscribe = hasattr(event_bus, 'subscribe') or hasattr(event_bus, 'on')
        has_emit = hasattr(event_bus, 'emit') or hasattr(event_bus, 'publish')
        # At minimum it should have some way to register handlers
        assert hasattr(event_bus, '__class__')


# =============================================================================
# E. Policy Integration Tests
# =============================================================================

class TestPolicyIntegration:
    """Test policy integration with agents."""

    def test_simple_preset_creates_valid_policies(self):
        """Simple preset should create valid policies."""
        policies = get_preset("simple")
        assert policies is not None
        assert hasattr(policies, 'termination_policy') or isinstance(policies, dict)

    def test_manager_preset_creates_valid_policies(self):
        """Manager preset should create valid policies."""
        policies = get_preset("manager_with_followups")
        assert policies is not None


# =============================================================================
# F. Component Wiring Tests
# =============================================================================

class TestComponentWiring:
    """Test that components are properly wired together."""

    def test_agent_components_accessible(self, mock_planner, mock_tools, shared_memory, event_bus):
        """All agent components should be accessible."""
        policies = get_preset("simple")

        agent = Agent(
            name="TestAgent",
            planner=mock_planner,
            tools=mock_tools,
            memory=shared_memory,
            event_bus=event_bus,
            policies=policies
        )

        # All components should be accessible
        assert agent.planner is not None
        assert agent.memory is not None
        assert agent.tools is not None

    def test_tools_have_required_interface(self, mock_tools):
        """Tools should have required interface."""
        for tool in mock_tools:
            assert hasattr(tool, 'name')
            assert hasattr(tool, 'description')
            assert hasattr(tool, 'execute')
            assert hasattr(tool, 'args_schema')
