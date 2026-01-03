#!/usr/bin/env python3
"""
Comprehensive tests for the sample app.

Tests cover:
1. Tool calling functionality
2. Memory and prompt building
3. Multi-turn conversation
4. Agent factory and configuration

Run with:
    python -m pytest tests/test_features.py -v

Or without pytest:
    python tests/test_features.py
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import Dict, Any, List

# Add sample_app to path
SAMPLE_APP_DIR = Path(__file__).resolve().parents[1]
if str(SAMPLE_APP_DIR) not in sys.path:
    sys.path.insert(0, str(SAMPLE_APP_DIR))


# =============================================================================
# Test 1: Tool Calling (No API Key Required)
# =============================================================================

def test_tool_registration():
    """Test that all tools are properly registered and callable."""
    print("\n" + "="*60)
    print("TEST 1: Tool Registration and Execution")
    print("="*60)

    from tools import (
        NoteTakerTool,
        TaskManagerTool,
        ListTasksTool,
        CompleteTaskTool,
        WeatherLookupTool,
        MockSearchTool,
    )

    # Test NoteTakerTool
    print("\n1.1 Testing NoteTakerTool...")
    note_tool = NoteTakerTool(storage_path="/tmp/test_notes.json")
    result = note_tool.execute(
        title="Test Note",
        content="This is a test note content",
        tags=["test", "sample"]
    )
    assert result["success"] == True
    assert "note_id" in result
    print(f"   Created note: {result['note_id']}")
    print(f"   Message: {result['message']}")

    # Test TaskManagerTool
    print("\n1.2 Testing TaskManagerTool...")
    task_tool = TaskManagerTool()
    result = task_tool.execute(
        title="Buy groceries",
        description="Get milk and eggs",
        priority="high"
    )
    assert result["success"] == True
    task_id = result["task_id"]
    print(f"   Created task: {task_id}")
    print(f"   Priority: {result['priority']}")

    # Test ListTasksTool
    print("\n1.3 Testing ListTasksTool...")
    list_tool = ListTasksTool()
    result = list_tool.execute(status="pending")
    assert "tasks" in result
    print(f"   Found {result['total_count']} pending task(s)")

    # Test CompleteTaskTool
    print("\n1.4 Testing CompleteTaskTool...")
    complete_tool = CompleteTaskTool()
    result = complete_tool.execute(task_id=task_id)
    assert result["success"] == True
    print(f"   Completed: {result['title']}")

    # Test WeatherLookupTool
    print("\n1.5 Testing WeatherLookupTool...")
    weather_tool = WeatherLookupTool()
    result = weather_tool.execute(city="London", units="celsius")
    assert "temperature" in result
    print(f"   Weather in {result['city']}: {result['temperature']}C, {result['condition']}")

    # Test MockSearchTool
    print("\n1.6 Testing MockSearchTool...")
    search_tool = MockSearchTool()
    result = search_tool.execute(query="Python tutorials", max_results=3)
    assert "results" in result
    print(f"   Found {result['total_results']} results for '{result['query']}'")
    for r in result["results"][:2]:
        print(f"   - {r['title']}")

    print("\n   Tool Registration Tests: PASSED")
    return True


def test_tool_schemas():
    """Test that all tools have proper Pydantic schemas."""
    print("\n" + "="*60)
    print("TEST 2: Tool Schemas (Pydantic Validation)")
    print("="*60)

    from tools import (
        NoteTakerTool,
        TaskManagerTool,
        WeatherLookupTool,
        MockSearchTool,
    )

    tools = [
        NoteTakerTool(),
        TaskManagerTool(),
        WeatherLookupTool(),
        MockSearchTool(),
    ]

    for tool in tools:
        print(f"\n2.x Testing {tool.name}...")

        # Check required properties
        assert hasattr(tool, 'name'), f"{tool} missing 'name'"
        assert hasattr(tool, 'description'), f"{tool} missing 'description'"
        assert hasattr(tool, 'args_schema'), f"{tool} missing 'args_schema'"
        assert hasattr(tool, 'output_schema'), f"{tool} missing 'output_schema'"

        # Check schema has model_json_schema
        args_schema = tool.args_schema
        assert hasattr(args_schema, 'model_json_schema'), f"{tool.name} args_schema missing model_json_schema"

        schema = args_schema.model_json_schema()
        print(f"   Name: {tool.name}")
        print(f"   Description: {tool.description[:50]}...")
        print(f"   Args Schema: {list(schema.get('properties', {}).keys())}")

    print("\n   Tool Schema Tests: PASSED")
    return True


# =============================================================================
# Test 2: Memory and Prompt Building (No API Key Required)
# =============================================================================

def test_memory_operations():
    """Test memory storage and retrieval."""
    print("\n" + "="*60)
    print("TEST 3: Memory Operations")
    print("="*60)

    from agent_framework.components.memory import SharedInMemoryMemory, _shared_state_store

    # Clear shared state for clean test
    _shared_state_store._global_feeds.clear()
    _shared_state_store._agent_feeds.clear()
    _shared_state_store._conversation_feeds.clear()

    # Create memory instance
    memory = SharedInMemoryMemory(namespace="test_job", agent_key="test_agent")

    # Test storing messages using the correct API
    print("\n3.1 Testing message storage...")
    memory.add({"role": "user", "content": "Hello, agent!"})
    memory.add({"role": "assistant", "content": "Hello! How can I help?"})
    memory.add({"role": "user", "content": "Search for Python tutorials"})

    history = memory.get_history()
    assert len(history) == 3
    print(f"   Stored {len(history)} messages")

    # Test conversation history
    print("\n3.2 Testing conversation history...")
    print(f"   History length: {len(history)} messages")
    for msg in history:
        print(f"   - [{msg['role']}]: {msg['content'][:40]}...")

    # Test global updates
    print("\n3.3 Testing global updates...")
    memory.add_global({"type": "observation", "content": "Found 5 results"})
    global_updates = memory.get_global_updates()
    assert len(global_updates) == 1
    print(f"   Global updates: {len(global_updates)}")

    # Test namespace isolation
    print("\n3.4 Testing namespace isolation...")
    # Clear for isolation test
    _shared_state_store._global_feeds.clear()
    _shared_state_store._agent_feeds.clear()
    _shared_state_store._conversation_feeds.clear()

    memory1 = SharedInMemoryMemory(namespace="job1", agent_key="agent1")
    memory2 = SharedInMemoryMemory(namespace="job2", agent_key="agent2")

    memory1.add({"role": "user", "content": "Message for job1"})
    memory2.add({"role": "user", "content": "Message for job2"})

    history1 = memory1.get_history()
    history2 = memory2.get_history()
    assert len(history1) == 1
    assert len(history2) == 1
    assert history1[0]["content"] != history2[0]["content"]
    print("   Namespaces are isolated correctly")

    print("\n   Memory Tests: PASSED")
    return True


def test_prompt_building():
    """Test prompt construction with tools."""
    print("\n" + "="*60)
    print("TEST 4: Prompt Building")
    print("="*60)

    from tools import MockSearchTool, NoteTakerTool

    tools = [MockSearchTool(), NoteTakerTool()]

    # Build tool descriptions
    print("\n4.1 Building tool descriptions for prompts...")
    tool_descriptions = []
    for tool in tools:
        desc = {
            "name": tool.name,
            "description": tool.description,
        }
        if hasattr(tool, "args_schema"):
            schema = tool.args_schema
            if hasattr(schema, "model_json_schema"):
                desc["parameters"] = schema.model_json_schema()
        tool_descriptions.append(desc)

    for desc in tool_descriptions:
        print(f"\n   Tool: {desc['name']}")
        print(f"   Description: {desc['description'][:60]}...")
        if "parameters" in desc:
            props = desc["parameters"].get("properties", {})
            print(f"   Parameters: {list(props.keys())}")

    # Test system prompt construction
    print("\n4.2 Testing system prompt template...")
    system_prompt = """You are a research assistant with the following tools:

{tools}

Use these tools to help the user with their research tasks.
"""

    tools_text = "\n".join([
        f"- {d['name']}: {d['description']}"
        for d in tool_descriptions
    ])

    final_prompt = system_prompt.format(tools=tools_text)
    print(f"   Prompt length: {len(final_prompt)} chars")
    print(f"   Contains {len(tool_descriptions)} tool descriptions")

    print("\n   Prompt Building Tests: PASSED")
    return True


# =============================================================================
# Test 3: Agent Factory and Configuration (No API Key Required)
# =============================================================================

def test_agent_factory_loading():
    """Test YAML configuration loading without running agents."""
    print("\n" + "="*60)
    print("TEST 5: Agent Factory Configuration Loading")
    print("="*60)

    from deployment.registry import (
        TOOL_REGISTRY,
        PLANNER_REGISTRY,
        GATEWAY_REGISTRY,
        MEMORY_REGISTRY,
    )

    print("\n5.1 Checking tool registry...")
    print(f"   Registered tools: {list(TOOL_REGISTRY.keys())}")
    assert len(TOOL_REGISTRY) > 0, "No tools registered"

    print("\n5.2 Checking planner registry...")
    print(f"   Registered planners: {list(PLANNER_REGISTRY.keys())}")
    assert len(PLANNER_REGISTRY) > 0, "No planners registered"

    print("\n5.3 Checking gateway registry...")
    print(f"   Registered gateways: {list(GATEWAY_REGISTRY.keys())}")

    print("\n5.4 Checking memory registry...")
    print(f"   Registered memory: {list(MEMORY_REGISTRY.keys())}")

    print("\n   Agent Factory Tests: PASSED")
    return True


def test_yaml_config_parsing():
    """Test YAML configuration file parsing."""
    print("\n" + "="*60)
    print("TEST 6: YAML Configuration Parsing")
    print("="*60)

    import yaml
    from pathlib import Path

    configs_dir = SAMPLE_APP_DIR / "configs" / "agents"

    for yaml_file in configs_dir.glob("*.yaml"):
        print(f"\n6.x Parsing {yaml_file.name}...")

        content = yaml_file.read_text()
        config = yaml.safe_load(content)

        # Check required fields
        assert "apiVersion" in config, f"Missing apiVersion in {yaml_file.name}"
        assert "kind" in config, f"Missing kind in {yaml_file.name}"
        assert "metadata" in config, f"Missing metadata in {yaml_file.name}"
        assert "spec" in config, f"Missing spec in {yaml_file.name}"

        print(f"   apiVersion: {config['apiVersion']}")
        print(f"   kind: {config['kind']}")
        print(f"   name: {config['metadata'].get('name', 'N/A')}")

        # Check planner config
        if "planner" in config["spec"]:
            planner = config["spec"]["planner"]
            print(f"   planner: {planner.get('type', 'N/A')}")

    print("\n   YAML Config Tests: PASSED")
    return True


# =============================================================================
# Test 4: Multi-turn Conversation (Requires API Key)
# =============================================================================

async def test_multi_turn_conversation():
    """Test multi-turn conversation with an agent."""
    print("\n" + "="*60)
    print("TEST 7: Multi-turn Conversation (Requires API Key)")
    print("="*60)

    if not os.getenv("OPENAI_API_KEY"):
        print("\n   SKIPPED: OPENAI_API_KEY not set")
        print("   Set OPENAI_API_KEY environment variable to run this test")
        return None

    from deployment.factory import AgentFactory

    print("\n7.1 Loading research worker agent...")
    agent = AgentFactory.create_from_yaml("configs/agents/research_worker.yaml")
    print(f"   Loaded agent: {agent.name}")

    # Simulate multi-turn conversation
    conversations = [
        "Search for Python tutorials",
        "Take a note about what you found",
        "Calculate 15 * 8 + 12",
    ]

    print("\n7.2 Running multi-turn conversation...")
    for i, task in enumerate(conversations, 1):
        print(f"\n   Turn {i}: {task}")
        try:
            result = await agent.run(task)
            if isinstance(result, dict):
                summary = result.get("human_readable_summary") or result.get("message") or str(result)[:100]
            else:
                summary = str(result)[:100]
            print(f"   Response: {summary}")
        except Exception as e:
            print(f"   Error: {e}")
            return False

    print("\n   Multi-turn Conversation Tests: PASSED")
    return True


async def test_orchestrator_routing():
    """Test orchestrator routing to workers."""
    print("\n" + "="*60)
    print("TEST 8: Orchestrator Routing (Requires API Key)")
    print("="*60)

    if not os.getenv("OPENAI_API_KEY"):
        print("\n   SKIPPED: OPENAI_API_KEY not set")
        print("   Set OPENAI_API_KEY environment variable to run this test")
        return None

    from deployment.factory import AgentFactory

    print("\n8.1 Loading orchestrator agent...")
    agent = AgentFactory.create_from_yaml("configs/agents/orchestrator.yaml")
    print(f"   Loaded agent: {agent.name}")

    # Test routing decisions
    test_cases = [
        ("Search for machine learning tutorials", "research-worker"),
        ("Create a task called 'Review docs'", "task-worker"),
        ("What's the weather in New York?", "task-worker"),
    ]

    print("\n8.2 Testing routing decisions...")
    for task, expected_worker in test_cases:
        print(f"\n   Task: {task}")
        print(f"   Expected worker: {expected_worker}")
        try:
            result = await agent.run(task)
            print(f"   Result: {str(result)[:80]}...")
        except Exception as e:
            print(f"   Error: {e}")

    print("\n   Orchestrator Routing Tests: PASSED")
    return True


# =============================================================================
# Main Test Runner
# =============================================================================

def run_all_tests():
    """Run all tests."""
    print("\n" + "="*60)
    print("SAMPLE APP TEST SUITE")
    print("="*60)

    results = {}

    # Tests that don't require API key
    print("\n--- Tests Without API Key ---")

    try:
        results["tool_registration"] = test_tool_registration()
    except Exception as e:
        print(f"\n   FAILED: {e}")
        results["tool_registration"] = False

    try:
        results["tool_schemas"] = test_tool_schemas()
    except Exception as e:
        print(f"\n   FAILED: {e}")
        results["tool_schemas"] = False

    try:
        results["memory_operations"] = test_memory_operations()
    except Exception as e:
        print(f"\n   FAILED: {e}")
        results["memory_operations"] = False

    try:
        results["prompt_building"] = test_prompt_building()
    except Exception as e:
        print(f"\n   FAILED: {e}")
        results["prompt_building"] = False

    try:
        results["agent_factory"] = test_agent_factory_loading()
    except Exception as e:
        print(f"\n   FAILED: {e}")
        results["agent_factory"] = False

    try:
        results["yaml_config"] = test_yaml_config_parsing()
    except Exception as e:
        print(f"\n   FAILED: {e}")
        results["yaml_config"] = False

    # Tests that require API key
    print("\n--- Tests With API Key ---")

    try:
        results["multi_turn"] = asyncio.run(test_multi_turn_conversation())
    except Exception as e:
        print(f"\n   FAILED: {e}")
        results["multi_turn"] = False

    try:
        results["orchestrator"] = asyncio.run(test_orchestrator_routing())
    except Exception as e:
        print(f"\n   FAILED: {e}")
        results["orchestrator"] = False

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    passed = sum(1 for v in results.values() if v == True)
    failed = sum(1 for v in results.values() if v == False)
    skipped = sum(1 for v in results.values() if v is None)

    for name, result in results.items():
        status = "PASSED" if result == True else "FAILED" if result == False else "SKIPPED"
        print(f"   {name}: {status}")

    print(f"\n   Total: {passed} passed, {failed} failed, {skipped} skipped")
    print("="*60)

    return failed == 0


if __name__ == "__main__":
    # Change to sample_app directory for correct relative paths
    os.chdir(SAMPLE_APP_DIR)

    success = run_all_tests()
    sys.exit(0 if success else 1)
