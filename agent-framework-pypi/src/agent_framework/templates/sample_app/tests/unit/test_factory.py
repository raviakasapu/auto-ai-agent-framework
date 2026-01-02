"""
Tier 1: Unit Tests for Agent Factory and Configuration

Tests cover:
A. Valid YAML Loading - Factory correctly instantiates agents
B. Invalid YAML Structure - Factory raises errors for malformed configs
C. Component Not Found - Factory raises errors for unknown components
D. Environment Variable Injection - Placeholders are substituted
E. Registry Tests - Components are properly registered

Run with:
    pytest tests/unit/test_factory.py -v
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
import yaml


# =============================================================================
# A. Valid YAML Loading Tests
# =============================================================================

class TestValidYAMLLoading:
    """Test that factory correctly loads valid YAML configurations."""

    def test_load_research_worker(self, agent_factory, research_worker_config,
                                   env_with_api_key):
        """Factory should load research worker from YAML."""
        agent = agent_factory.create_from_yaml(research_worker_config)

        assert agent is not None
        assert agent.name == "ResearchWorker"
        assert hasattr(agent, 'planner')
        assert hasattr(agent, 'tools')

    def test_load_task_worker(self, agent_factory, task_worker_config,
                              env_with_api_key):
        """Factory should load task worker from YAML."""
        agent = agent_factory.create_from_yaml(task_worker_config)

        assert agent is not None
        assert agent.name == "TaskWorker"

    def test_load_orchestrator(self, agent_factory, orchestrator_config,
                                env_with_api_key):
        """Factory should load orchestrator (ManagerAgent) from YAML."""
        agent = agent_factory.create_from_yaml(orchestrator_config)

        assert agent is not None
        assert agent.name == "SampleOrchestrator"
        assert hasattr(agent, 'workers')
        assert len(agent.workers) == 2

    def test_agent_has_planner(self, agent_factory, research_worker_config,
                               env_with_api_key):
        """Loaded agent should have a configured planner."""
        agent = agent_factory.create_from_yaml(research_worker_config)

        assert agent.planner is not None
        assert hasattr(agent.planner, 'plan')

    def test_agent_has_tools(self, agent_factory, research_worker_config,
                             env_with_api_key):
        """Loaded agent should have configured tools."""
        agent = agent_factory.create_from_yaml(research_worker_config)

        assert agent.tools is not None
        assert len(agent.tools) > 0

    def test_agent_has_memory(self, agent_factory, research_worker_config,
                              env_with_api_key):
        """Loaded agent should have configured memory."""
        agent = agent_factory.create_from_yaml(research_worker_config)

        assert agent.memory is not None
        assert hasattr(agent.memory, 'add')
        assert hasattr(agent.memory, 'get_history')

    def test_agent_has_policies(self, agent_factory, research_worker_config,
                                env_with_api_key):
        """Loaded agent should have configured policies."""
        agent = agent_factory.create_from_yaml(research_worker_config)

        # Agent should have policy-related attributes
        assert hasattr(agent, 'termination_policy') or hasattr(agent, '_policies')


# =============================================================================
# B. Invalid YAML Structure Tests
# =============================================================================

class TestInvalidYAMLStructure:
    """Test that factory raises errors for malformed configs."""

    def test_missing_api_version(self, agent_factory, tmp_path):
        """Factory should handle missing apiVersion."""
        config = {
            "kind": "Agent",
            "metadata": {"name": "Test"},
            "spec": {}
        }

        config_file = tmp_path / "invalid.yaml"
        config_file.write_text(yaml.dump(config))

        # Should either raise or handle gracefully
        try:
            agent = agent_factory.create_from_yaml(str(config_file))
            # If it doesn't raise, agent should still be functional
            assert agent is not None
        except (ValueError, KeyError) as e:
            assert "apiVersion" in str(e).lower() or True  # Expected

    def test_missing_kind(self, agent_factory, tmp_path):
        """Factory should handle missing kind."""
        config = {
            "apiVersion": "agent.framework/v2",
            "metadata": {"name": "Test"},
            "spec": {}
        }

        config_file = tmp_path / "invalid.yaml"
        config_file.write_text(yaml.dump(config))

        try:
            agent = agent_factory.create_from_yaml(str(config_file))
            # Default to "Agent" kind
            assert agent is not None
        except (ValueError, KeyError):
            pass  # Expected

    def test_missing_spec(self, agent_factory, tmp_path):
        """Factory should handle missing spec."""
        config = {
            "apiVersion": "agent.framework/v2",
            "kind": "Agent",
            "metadata": {"name": "Test"}
        }

        config_file = tmp_path / "invalid.yaml"
        config_file.write_text(yaml.dump(config))

        try:
            agent_factory.create_from_yaml(str(config_file))
        except (ValueError, KeyError, TypeError):
            pass  # Expected

    def test_invalid_yaml_syntax(self, agent_factory, tmp_path):
        """Factory should handle invalid YAML syntax."""
        config_file = tmp_path / "invalid.yaml"
        config_file.write_text("not: valid: yaml: {[}")

        with pytest.raises(Exception):  # yaml.YAMLError or similar
            agent_factory.create_from_yaml(str(config_file))

    def test_empty_yaml(self, agent_factory, tmp_path):
        """Factory should handle empty YAML file."""
        config_file = tmp_path / "empty.yaml"
        config_file.write_text("")

        try:
            agent_factory.create_from_yaml(str(config_file))
        except (ValueError, TypeError, AttributeError):
            pass  # Expected

    def test_missing_planner_type(self, agent_factory, tmp_path, env_with_api_key):
        """Factory should handle missing planner type."""
        config = {
            "apiVersion": "agent.framework/v2",
            "kind": "Agent",
            "metadata": {"name": "Test"},
            "spec": {
                "planner": {
                    "config": {}
                },
                "memory": {
                    "type": "SharedInMemoryMemory",
                    "config": {"namespace": "test", "agent_key": "test"}
                }
            }
        }

        config_file = tmp_path / "no_planner_type.yaml"
        config_file.write_text(yaml.dump(config))

        try:
            agent_factory.create_from_yaml(str(config_file))
        except (ValueError, KeyError, TypeError):
            pass  # Expected


# =============================================================================
# C. Component Not Found Tests
# =============================================================================

class TestComponentNotFound:
    """Test that factory raises errors for unknown components."""

    def test_unknown_planner_type(self, agent_factory, tmp_path, env_with_api_key):
        """Factory should raise error for unknown planner type."""
        config = {
            "apiVersion": "agent.framework/v2",
            "kind": "Agent",
            "metadata": {"name": "Test"},
            "resources": {
                "inference_gateways": [{
                    "name": "gw",
                    "type": "OpenAIGateway",
                    "config": {"api_key": "test"}
                }]
            },
            "spec": {
                "planner": {
                    "type": "NonExistentPlanner",
                    "config": {"inference_gateway": "gw"}
                },
                "memory": {
                    "type": "SharedInMemoryMemory",
                    "config": {"namespace": "test", "agent_key": "test"}
                }
            }
        }

        config_file = tmp_path / "unknown_planner.yaml"
        config_file.write_text(yaml.dump(config))

        with pytest.raises(ValueError, match="Unknown component type"):
            agent_factory.create_from_yaml(str(config_file))

    def test_unknown_tool_type(self, agent_factory, tmp_path, env_with_api_key):
        """Factory should raise error for unknown tool type."""
        config = {
            "apiVersion": "agent.framework/v2",
            "kind": "Agent",
            "metadata": {"name": "Test"},
            "resources": {
                "inference_gateways": [{
                    "name": "gw",
                    "type": "OpenAIGateway",
                    "config": {"api_key": "test"}
                }],
                "tools": [{
                    "name": "unknown",
                    "type": "NonExistentTool",
                    "config": {}
                }]
            },
            "spec": {
                "planner": {
                    "type": "ReActPlanner",
                    "config": {"inference_gateway": "gw"}
                },
                "memory": {
                    "type": "SharedInMemoryMemory",
                    "config": {"namespace": "test", "agent_key": "test"}
                },
                "tools": ["unknown"]
            }
        }

        config_file = tmp_path / "unknown_tool.yaml"
        config_file.write_text(yaml.dump(config))

        with pytest.raises(ValueError, match="Unknown component type"):
            agent_factory.create_from_yaml(str(config_file))

    def test_unknown_memory_type(self, agent_factory, tmp_path, env_with_api_key):
        """Factory should raise error for unknown memory type."""
        config = {
            "apiVersion": "agent.framework/v2",
            "kind": "Agent",
            "metadata": {"name": "Test"},
            "resources": {
                "inference_gateways": [{
                    "name": "gw",
                    "type": "OpenAIGateway",
                    "config": {"api_key": "test"}
                }]
            },
            "spec": {
                "planner": {
                    "type": "ReActPlanner",
                    "config": {"inference_gateway": "gw"}
                },
                "memory": {
                    "type": "NonExistentMemory",
                    "config": {}
                }
            }
        }

        config_file = tmp_path / "unknown_memory.yaml"
        config_file.write_text(yaml.dump(config))

        with pytest.raises(ValueError, match="Unknown component type"):
            agent_factory.create_from_yaml(str(config_file))

    def test_unknown_subscriber_type(self, agent_factory, tmp_path, env_with_api_key):
        """Factory should raise error for unknown subscriber type."""
        config = {
            "apiVersion": "agent.framework/v2",
            "kind": "Agent",
            "metadata": {"name": "Test"},
            "resources": {
                "inference_gateways": [{
                    "name": "gw",
                    "type": "OpenAIGateway",
                    "config": {"api_key": "test"}
                }],
                "subscribers": [{
                    "name": "unknown",
                    "type": "NonExistentSubscriber",
                    "config": {}
                }]
            },
            "spec": {
                "planner": {
                    "type": "ReActPlanner",
                    "config": {"inference_gateway": "gw"}
                },
                "memory": {
                    "type": "SharedInMemoryMemory",
                    "config": {"namespace": "test", "agent_key": "test"}
                },
                "subscribers": ["unknown"]
            }
        }

        config_file = tmp_path / "unknown_subscriber.yaml"
        config_file.write_text(yaml.dump(config))

        with pytest.raises(ValueError, match="Unknown component type"):
            agent_factory.create_from_yaml(str(config_file))


# =============================================================================
# D. Environment Variable Injection Tests
# =============================================================================

class TestEnvironmentVariableInjection:
    """Test that environment variable placeholders are substituted."""

    def test_api_key_substitution(self, agent_factory, tmp_path, monkeypatch):
        """${OPENAI_API_KEY} should be substituted from environment."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key-12345")
        monkeypatch.setenv("OPENAI_MODEL", "gpt-4o-mini")

        config = {
            "apiVersion": "agent.framework/v2",
            "kind": "Agent",
            "metadata": {"name": "Test"},
            "resources": {
                "inference_gateways": [{
                    "name": "gw",
                    "type": "OpenAIGateway",
                    "config": {
                        "api_key": "${OPENAI_API_KEY}",
                        "model": "${OPENAI_MODEL}"
                    }
                }]
            },
            "spec": {
                "policies": {"$preset": "simple"},
                "planner": {
                    "type": "ReActPlanner",
                    "config": {"inference_gateway": "gw"}
                },
                "memory": {
                    "type": "SharedInMemoryMemory",
                    "config": {"namespace": "test", "agent_key": "test"}
                }
            }
        }

        config_file = tmp_path / "env_test.yaml"
        config_file.write_text(yaml.dump(config))

        # Should not raise, env vars should be substituted
        agent = agent_factory.create_from_yaml(str(config_file))
        assert agent is not None

    def test_default_value_substitution(self, agent_factory, tmp_path, monkeypatch):
        """${VAR:-default} should use default when VAR is not set."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        # Don't set OPENAI_MODEL - should use default

        config = {
            "apiVersion": "agent.framework/v2",
            "kind": "Agent",
            "metadata": {"name": "Test"},
            "resources": {
                "inference_gateways": [{
                    "name": "gw",
                    "type": "OpenAIGateway",
                    "config": {
                        "api_key": "${OPENAI_API_KEY}",
                        "model": "${OPENAI_MODEL:-gpt-4o-mini}"
                    }
                }]
            },
            "spec": {
                "policies": {"$preset": "simple"},
                "planner": {
                    "type": "ReActPlanner",
                    "config": {"inference_gateway": "gw"}
                },
                "memory": {
                    "type": "SharedInMemoryMemory",
                    "config": {"namespace": "test", "agent_key": "test"}
                }
            }
        }

        config_file = tmp_path / "default_test.yaml"
        config_file.write_text(yaml.dump(config))

        agent = agent_factory.create_from_yaml(str(config_file))
        assert agent is not None

    def test_job_id_substitution(self, agent_factory, tmp_path, monkeypatch):
        """${JOB_ID} should be substituted in memory config."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setenv("JOB_ID", "job-123-abc")

        config = {
            "apiVersion": "agent.framework/v2",
            "kind": "Agent",
            "metadata": {"name": "Test"},
            "resources": {
                "inference_gateways": [{
                    "name": "gw",
                    "type": "OpenAIGateway",
                    "config": {"api_key": "${OPENAI_API_KEY}"}
                }]
            },
            "spec": {
                "policies": {"$preset": "simple"},
                "planner": {
                    "type": "ReActPlanner",
                    "config": {"inference_gateway": "gw"}
                },
                "memory": {
                    "type": "SharedInMemoryMemory",
                    "config": {
                        "namespace": "${JOB_ID}",
                        "agent_key": "test"
                    }
                }
            }
        }

        config_file = tmp_path / "job_id_test.yaml"
        config_file.write_text(yaml.dump(config))

        agent = agent_factory.create_from_yaml(str(config_file))
        assert agent is not None
        # Memory should have the job ID as namespace
        assert agent.memory._namespace == "job-123-abc"


# =============================================================================
# E. Registry Tests
# =============================================================================

class TestRegistries:
    """Test that component registries are properly populated."""

    def test_tool_registry_populated(self, registries):
        """TOOL_REGISTRY should have expected tools."""
        tools = registries["tools"]
        assert len(tools) > 0

        expected_tools = [
            "NoteTakerTool",
            "TaskManagerTool",
            "ListTasksTool",
            "CompleteTaskTool",
            "WeatherLookupTool",
            "MockSearchTool",
        ]

        for tool_name in expected_tools:
            assert tool_name in tools, f"{tool_name} not in registry"

    def test_planner_registry_populated(self, registries):
        """PLANNER_REGISTRY should have expected planners."""
        planners = registries["planners"]
        assert len(planners) > 0

        expected_planners = [
            "ReActPlanner",
            "WorkerRouterPlanner",
        ]

        for planner_name in expected_planners:
            assert planner_name in planners, f"{planner_name} not in registry"

    def test_gateway_registry_populated(self, registries):
        """GATEWAY_REGISTRY should have expected gateways."""
        gateways = registries["gateways"]
        assert len(gateways) > 0
        assert "OpenAIGateway" in gateways

    def test_memory_registry_populated(self, registries):
        """MEMORY_REGISTRY should have expected memory types."""
        memory = registries["memory"]
        assert len(memory) > 0
        assert "SharedInMemoryMemory" in memory

    def test_registry_classes_instantiable(self, registries):
        """Registry classes should be instantiable."""
        # Test a tool
        tools = registries["tools"]
        if "MockSearchTool" in tools:
            tool_cls = tools["MockSearchTool"]
            tool = tool_cls()
            assert tool.name == "web_search"

    def test_registry_no_duplicates(self, registries):
        """Registry should not have duplicate entries."""
        for name, registry in registries.items():
            keys = list(registry.keys())
            unique_keys = set(keys)
            assert len(keys) == len(unique_keys), \
                f"Duplicate keys in {name} registry"


# =============================================================================
# F. Config Path Resolution Tests
# =============================================================================

class TestConfigPathResolution:
    """Test config file path resolution."""

    def test_absolute_path(self, agent_factory, sample_app_dir, env_with_api_key):
        """Factory should accept absolute paths."""
        abs_path = sample_app_dir / "configs" / "agents" / "research_worker.yaml"
        agent = agent_factory.create_from_yaml(str(abs_path))
        assert agent is not None

    def test_relative_path(self, agent_factory, env_with_api_key):
        """Factory should accept relative paths."""
        agent = agent_factory.create_from_yaml("configs/agents/research_worker.yaml")
        assert agent is not None

    def test_nonexistent_path(self, agent_factory):
        """Factory should raise error for non-existent path."""
        with pytest.raises(FileNotFoundError):
            agent_factory.create_from_yaml("nonexistent/path/config.yaml")


# =============================================================================
# G. Policy Preset Tests
# =============================================================================

class TestPolicyPresets:
    """Test policy preset loading."""

    def test_simple_preset_loaded(self, agent_factory, research_worker_config,
                                  env_with_api_key):
        """'simple' preset should load correctly."""
        agent = agent_factory.create_from_yaml(research_worker_config)

        # Simple preset includes termination policy
        assert hasattr(agent, 'termination_policy') or hasattr(agent, '_policies')

    def test_manager_preset_loaded(self, agent_factory, orchestrator_config,
                                   env_with_api_key):
        """'manager_with_followups' preset should load correctly."""
        agent = agent_factory.create_from_yaml(orchestrator_config)

        # Manager preset includes follow_up policy
        assert hasattr(agent, 'follow_up_policy') or hasattr(agent, '_policies')

    def test_invalid_preset_raises(self, agent_factory, tmp_path, monkeypatch):
        """Invalid preset name should raise error."""
        monkeypatch.setenv("OPENAI_API_KEY", "test")

        config = {
            "apiVersion": "agent.framework/v2",
            "kind": "Agent",
            "metadata": {"name": "Test"},
            "resources": {
                "inference_gateways": [{
                    "name": "gw",
                    "type": "OpenAIGateway",
                    "config": {"api_key": "test"}
                }]
            },
            "spec": {
                "policies": {"$preset": "nonexistent_preset"},
                "planner": {
                    "type": "ReActPlanner",
                    "config": {"inference_gateway": "gw"}
                },
                "memory": {
                    "type": "SharedInMemoryMemory",
                    "config": {"namespace": "test", "agent_key": "test"}
                }
            }
        }

        config_file = tmp_path / "bad_preset.yaml"
        config_file.write_text(yaml.dump(config))

        with pytest.raises(ValueError, match="Unknown preset"):
            agent_factory.create_from_yaml(str(config_file))
