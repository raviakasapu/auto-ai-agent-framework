"""
Test suite for the AI Agent Framework sample app.

Tests cover:
- Tool registration and execution
- Tool schema validation (Pydantic)
- Memory operations (SharedInMemoryMemory)
- Prompt building with tool descriptions
- Agent factory and component registries
- YAML configuration parsing
- Multi-turn conversation (requires API key)
- Orchestrator routing (requires API key)

Run all tests:
    python tests/test_features.py

Run with pytest:
    python -m pytest tests/test_features.py -v

See TESTING.md for detailed documentation.
"""

from .test_features import (
    test_tool_registration,
    test_tool_schemas,
    test_memory_operations,
    test_prompt_building,
    test_agent_factory_loading,
    test_yaml_config_parsing,
    test_multi_turn_conversation,
    test_orchestrator_routing,
    run_all_tests,
)

__all__ = [
    "test_tool_registration",
    "test_tool_schemas",
    "test_memory_operations",
    "test_prompt_building",
    "test_agent_factory_loading",
    "test_yaml_config_parsing",
    "test_multi_turn_conversation",
    "test_orchestrator_routing",
    "run_all_tests",
]
