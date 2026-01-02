"""
Pytest configuration and shared fixtures for the AI Agent Framework test suite.

This module provides:
- Shared fixtures for tools, memory, agents
- Mock LLM gateway for deterministic testing
- Test utilities and helpers
- Environment setup/teardown

Usage:
    pytest tests/ -v
    pytest tests/unit/ -v --no-header
    pytest tests/integration/ -v -k "planner"
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add sample_app to path
SAMPLE_APP_DIR = Path(__file__).resolve().parents[1]
if str(SAMPLE_APP_DIR) not in sys.path:
    sys.path.insert(0, str(SAMPLE_APP_DIR))

# Change to sample_app directory for config resolution
os.chdir(SAMPLE_APP_DIR)


# =============================================================================
# Environment Fixtures
# =============================================================================

@pytest.fixture(scope="session")
def sample_app_dir() -> Path:
    """Return the sample app directory path."""
    return SAMPLE_APP_DIR


@pytest.fixture(autouse=True)
def reset_shared_state():
    """Reset shared memory state before each test."""
    from agent_framework.components.memory import _shared_state_store
    _shared_state_store._global_feeds.clear()
    _shared_state_store._agent_feeds.clear()
    _shared_state_store._conversation_feeds.clear()
    yield
    # Cleanup after test
    _shared_state_store._global_feeds.clear()
    _shared_state_store._agent_feeds.clear()
    _shared_state_store._conversation_feeds.clear()


@pytest.fixture
def env_with_api_key(monkeypatch):
    """Set up environment with API key.

    Uses real API key from environment if available (for E2E tests),
    otherwise sets a mock key (for unit/integration tests that don't need real LLM).
    """
    # Use real API key if available, otherwise use mock
    real_key = os.environ.get("OPENAI_API_KEY")
    if real_key and not real_key.startswith("test-"):
        # Real API key exists, use it
        monkeypatch.setenv("OPENAI_API_KEY", real_key)
    else:
        # No real key, use mock for unit/integration tests
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-12345")

    monkeypatch.setenv("OPENAI_MODEL", os.environ.get("OPENAI_MODEL", "gpt-4o-mini"))
    monkeypatch.setenv("JOB_ID", "test-job-123")
    yield


# =============================================================================
# Tool Fixtures
# =============================================================================

@pytest.fixture
def note_taker_tool():
    """Create a NoteTakerTool instance."""
    from tools import NoteTakerTool
    return NoteTakerTool(storage_path="/tmp/test_notes.json")


@pytest.fixture
def task_manager_tool():
    """Create a TaskManagerTool instance."""
    from tools import TaskManagerTool
    return TaskManagerTool()


@pytest.fixture
def list_tasks_tool():
    """Create a ListTasksTool instance."""
    from tools import ListTasksTool
    return ListTasksTool()


@pytest.fixture
def complete_task_tool():
    """Create a CompleteTaskTool instance."""
    from tools import CompleteTaskTool
    return CompleteTaskTool()


@pytest.fixture
def weather_tool():
    """Create a WeatherLookupTool instance."""
    from tools import WeatherLookupTool
    return WeatherLookupTool()


@pytest.fixture
def search_tool():
    """Create a MockSearchTool instance."""
    from tools import MockSearchTool
    return MockSearchTool()


@pytest.fixture
def all_tools(note_taker_tool, task_manager_tool, list_tasks_tool,
              complete_task_tool, weather_tool, search_tool):
    """Return all sample tools as a list."""
    return [
        note_taker_tool,
        task_manager_tool,
        list_tasks_tool,
        complete_task_tool,
        weather_tool,
        search_tool,
    ]


# =============================================================================
# Memory Fixtures
# =============================================================================

@pytest.fixture
def shared_memory():
    """Create a SharedInMemoryMemory instance."""
    from agent_framework.components.memory import SharedInMemoryMemory
    return SharedInMemoryMemory(namespace="test-namespace", agent_key="test-agent")


@pytest.fixture
def in_memory():
    """Create an InMemoryMemory instance."""
    from agent_framework.components.memory import InMemoryMemory
    return InMemoryMemory(agent_key="test-agent")


@pytest.fixture
def hierarchical_memory():
    """Create a HierarchicalSharedMemory instance."""
    from agent_framework.components.memory import HierarchicalSharedMemory
    return HierarchicalSharedMemory(
        namespace="test-namespace",
        agent_key="manager",
        subordinates=["worker1", "worker2"]
    )


# =============================================================================
# Mock LLM Gateway
# =============================================================================

class MockLLMResponse:
    """A configurable mock LLM response."""

    def __init__(
        self,
        content: str = "",
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        function_call: Optional[Dict[str, Any]] = None,
        finish_reason: str = "stop"
    ):
        self.content = content
        self.tool_calls = tool_calls or []
        self.function_call = function_call
        self.finish_reason = finish_reason


class MockInferenceGateway:
    """
    A mock inference gateway for testing planners without real API calls.

    Configure responses using set_response() or set_responses() for multi-turn.
    """

    def __init__(self, default_response: Optional[str] = None):
        self.responses: List[MockLLMResponse] = []
        self.call_count = 0
        self.call_history: List[Dict[str, Any]] = []
        self.default_response = default_response or '{"action": "complete", "result": "Done"}'

    def set_response(self, response: MockLLMResponse | str | dict):
        """Set a single response."""
        if isinstance(response, str):
            response = MockLLMResponse(content=response)
        elif isinstance(response, dict):
            response = MockLLMResponse(content=json.dumps(response))
        self.responses = [response]

    def set_responses(self, responses: List[MockLLMResponse | str | dict]):
        """Set multiple responses for multi-turn conversations."""
        self.responses = []
        for r in responses:
            if isinstance(r, str):
                self.responses.append(MockLLMResponse(content=r))
            elif isinstance(r, dict):
                self.responses.append(MockLLMResponse(content=json.dumps(r)))
            else:
                self.responses.append(r)

    def set_tool_call_response(self, tool_name: str, arguments: Dict[str, Any]):
        """Set a response that triggers a tool call."""
        tool_call = {
            "id": f"call_{tool_name}_{self.call_count}",
            "type": "function",
            "function": {
                "name": tool_name,
                "arguments": json.dumps(arguments)
            }
        }
        self.responses = [MockLLMResponse(tool_calls=[tool_call])]

    async def generate(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Mock generate method matching the real gateway interface."""
        self.call_history.append({
            "messages": messages,
            "tools": tools,
            "kwargs": kwargs
        })

        if self.responses:
            response = self.responses[min(self.call_count, len(self.responses) - 1)]
        else:
            response = MockLLMResponse(content=self.default_response)

        self.call_count += 1

        result = {
            "content": response.content,
            "finish_reason": response.finish_reason,
        }

        if response.tool_calls:
            result["tool_calls"] = response.tool_calls
        if response.function_call:
            result["function_call"] = response.function_call

        return result

    def reset(self):
        """Reset call history and count."""
        self.call_count = 0
        self.call_history = []


@pytest.fixture
def mock_gateway():
    """Create a MockInferenceGateway instance."""
    return MockInferenceGateway()


@pytest.fixture
def mock_gateway_with_tool_call():
    """Create a mock gateway pre-configured for a tool call."""
    gateway = MockInferenceGateway()
    gateway.set_tool_call_response("web_search", {"query": "Python tutorials"})
    return gateway


# =============================================================================
# Agent Fixtures
# =============================================================================

@pytest.fixture
def agent_factory():
    """Return the AgentFactory class."""
    from deployment.factory import AgentFactory
    return AgentFactory


@pytest.fixture
def research_worker_config() -> str:
    """Return path to research worker config."""
    return "configs/agents/research_worker.yaml"


@pytest.fixture
def task_worker_config() -> str:
    """Return path to task worker config."""
    return "configs/agents/task_worker.yaml"


@pytest.fixture
def orchestrator_config() -> str:
    """Return path to orchestrator config."""
    return "configs/agents/orchestrator.yaml"


# =============================================================================
# Registry Fixtures
# =============================================================================

@pytest.fixture
def registries():
    """Return all component registries."""
    from deployment.registry import (
        TOOL_REGISTRY,
        PLANNER_REGISTRY,
        GATEWAY_REGISTRY,
        MEMORY_REGISTRY,
        SUBSCRIBER_REGISTRY,
        POLICY_REGISTRY,
    )
    return {
        "tools": TOOL_REGISTRY,
        "planners": PLANNER_REGISTRY,
        "gateways": GATEWAY_REGISTRY,
        "memory": MEMORY_REGISTRY,
        "subscribers": SUBSCRIBER_REGISTRY,
        "policies": POLICY_REGISTRY,
    }


# =============================================================================
# Async Test Helpers
# =============================================================================

@pytest.fixture
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


def run_async(coro):
    """Helper to run async code in sync context."""
    return asyncio.get_event_loop().run_until_complete(coro)


# =============================================================================
# Test Data Fixtures
# =============================================================================

@pytest.fixture
def sample_messages() -> List[Dict[str, Any]]:
    """Sample conversation messages for testing."""
    return [
        {"role": "user", "content": "Hello, I need help with research"},
        {"role": "assistant", "content": "I'd be happy to help! What topic?"},
        {"role": "user", "content": "Find information about Python async"},
        {"role": "assistant", "content": "Let me search for that..."},
    ]


@pytest.fixture
def valid_yaml_config() -> Dict[str, Any]:
    """A valid agent configuration dictionary."""
    return {
        "apiVersion": "agent.framework/v2",
        "kind": "Agent",
        "metadata": {
            "name": "TestAgent",
            "description": "A test agent",
            "version": "1.0.0"
        },
        "resources": {
            "inference_gateways": [
                {
                    "name": "test-gateway",
                    "type": "MockInferenceGateway",
                    "config": {}
                }
            ],
            "tools": [
                {
                    "name": "search",
                    "type": "MockSearchTool",
                    "config": {}
                }
            ]
        },
        "spec": {
            "policies": {"$preset": "simple"},
            "planner": {
                "type": "ReActPlanner",
                "config": {
                    "inference_gateway": "test-gateway"
                }
            },
            "memory": {
                "type": "SharedInMemoryMemory",
                "config": {
                    "namespace": "test",
                    "agent_key": "test"
                }
            },
            "tools": ["search"]
        }
    }


@pytest.fixture
def invalid_yaml_config() -> Dict[str, Any]:
    """An invalid agent configuration (missing required fields)."""
    return {
        "kind": "Agent",
        # Missing apiVersion, metadata, spec
    }


# =============================================================================
# Performance/Thread Safety Helpers
# =============================================================================

class ThreadSafetyTester:
    """Helper class for testing thread safety of components."""

    def __init__(self, target_func, num_threads: int = 10, iterations: int = 100):
        self.target_func = target_func
        self.num_threads = num_threads
        self.iterations = iterations
        self.errors: List[Exception] = []
        self.results: List[Any] = []
        self._lock = threading.Lock()

    def run(self):
        """Run the thread safety test."""
        threads = []

        def worker():
            for _ in range(self.iterations):
                try:
                    result = self.target_func()
                    with self._lock:
                        self.results.append(result)
                except Exception as e:
                    with self._lock:
                        self.errors.append(e)

        for _ in range(self.num_threads):
            t = threading.Thread(target=worker)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        return len(self.errors) == 0


@pytest.fixture
def thread_safety_tester():
    """Factory fixture for ThreadSafetyTester."""
    def _create(target_func, num_threads=10, iterations=100):
        return ThreadSafetyTester(target_func, num_threads, iterations)
    return _create


# =============================================================================
# Skip Markers
# =============================================================================

requires_api_key = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="Requires OPENAI_API_KEY environment variable"
)

slow_test = pytest.mark.slow
integration_test = pytest.mark.integration
e2e_test = pytest.mark.e2e
