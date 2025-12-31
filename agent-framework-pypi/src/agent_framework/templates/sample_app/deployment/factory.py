"""
Factory for creating agents from YAML configurations.

Supports the agent.framework/v2 schema with:
- Agent: Single worker agent with planner and tools
- ManagerAgent: Orchestrator with multiple workers
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Type, Optional

import yaml

from agent_framework.core.agent import Agent
from agent_framework.core.manager_v2 import ManagerAgent
from agent_framework.core.events import EventBus
from agent_framework.policies.presets import get_preset

from .registry import (
    PLANNER_REGISTRY,
    MEMORY_REGISTRY,
    TOOL_REGISTRY,
    SUBSCRIBER_REGISTRY,
    PROMPT_REGISTRY,
    GATEWAY_REGISTRY,
    POLICY_REGISTRY,
)


# Environment loading
_ENV_LOADED = False


def _load_env_once() -> None:
    """Load .env file once."""
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    try:
        from dotenv import load_dotenv
    except ImportError:
        _ENV_LOADED = True
        return

    candidates = [
        Path(os.getenv("ENV_FILE", "")),
        Path(__file__).resolve().parents[1] / ".env",
        Path.cwd() / ".env",
    ]

    for p in candidates:
        if p and p.exists():
            load_dotenv(dotenv_path=str(p), override=False)
            break
    _ENV_LOADED = True


def _expand_env_vars(yaml_text: str) -> str:
    """
    Expand environment variables in YAML text.
    Supports ${VAR} and ${VAR:-default} syntax.
    """
    from agent_framework.services.request_context import get_from_context

    def replacer(match):
        var_expr = match.group(1)
        if ':-' in var_expr:
            var_name, default_value = var_expr.split(':-', 1)
            var_name = var_name.strip()
            default_value = default_value.strip()
            value = get_from_context(var_name)
            if value is None:
                value = os.getenv(var_name)
            return value if value is not None else default_value
        else:
            var_name = var_expr.strip()
            value = get_from_context(var_name)
            if value is None:
                value = os.getenv(var_name)
            return value if value is not None else match.group(0)

    pattern = r'\$\{([^}]+)\}'
    return re.sub(pattern, replacer, yaml_text)


def resolve_config_path(filepath: str) -> Path:
    """Resolve config path relative to sample_app directory."""
    candidate = Path(filepath)
    if candidate.exists():
        return candidate
    if candidate.is_absolute():
        raise FileNotFoundError(f"Config file not found: {filepath}")

    sample_app_root = Path(__file__).resolve().parents[1]
    search_roots = [Path.cwd(), sample_app_root]
    subdirs = [Path('.'), Path('configs/agents')]

    for base in search_roots:
        for sub in subdirs:
            resolved = (base / sub / candidate).resolve()
            if resolved.exists():
                return resolved

    raise FileNotFoundError(f"Config file not found: {filepath}")


def _instantiate_from_registry(type_name: str, params: Dict[str, Any]) -> Any:
    """Instantiate a component from the registries."""
    aggregated: Dict[str, Type] = {}
    aggregated.update(PLANNER_REGISTRY)
    aggregated.update(MEMORY_REGISTRY)
    aggregated.update(TOOL_REGISTRY)
    aggregated.update(SUBSCRIBER_REGISTRY)
    aggregated.update(PROMPT_REGISTRY)
    aggregated.update(GATEWAY_REGISTRY)
    aggregated.update(POLICY_REGISTRY)

    cls = aggregated.get(type_name)
    if not cls:
        raise ValueError(f"Unknown component type '{type_name}' in registries")
    try:
        return cls(**(params or {}))
    except TypeError:
        return cls()


def _load_policies(spec: Dict[str, Any], resources_by_name: Dict[str, Any]) -> Dict[str, Any]:
    """Load policies from spec, supporting presets."""
    policies_spec = spec.get("policies", {})

    if "$preset" in policies_spec:
        preset_name = policies_spec["$preset"]
        policies = get_preset(preset_name)

        for key, value in policies_spec.items():
            if key != "$preset":
                if isinstance(value, dict) and "type" in value:
                    p_type = value["type"]
                    policy_params = value.get("config", {})
                    policies[key] = _instantiate_from_registry(p_type, policy_params)
                else:
                    policies[key] = value
        return policies

    policies = {}
    for key, value in policies_spec.items():
        if isinstance(value, dict) and "type" in value:
            p_type = value["type"]
            policy_params = value.get("config", {})
            policies[key] = _instantiate_from_registry(p_type, policy_params)
        else:
            policies[key] = value
    return policies


class AgentFactory:
    """Factory for creating agents from YAML configurations."""

    @classmethod
    def create_from_yaml(cls, config_path: str) -> Any:
        """
        Create an agent from a YAML configuration file.

        Args:
            config_path: Path to the YAML configuration file

        Returns:
            Agent or ManagerAgent instance
        """
        _load_env_once()

        path = resolve_config_path(config_path)
        yaml_text = path.read_text(encoding="utf-8")
        yaml_text = _expand_env_vars(yaml_text)
        config = yaml.safe_load(yaml_text) or {}

        kind = config.get("kind", "Agent")
        metadata = config.get("metadata", {})
        resources = config.get("resources", {})
        spec = config.get("spec", {})

        # Build resources
        resources_by_name: Dict[str, Any] = {}

        # Inference gateways
        for gw_spec in resources.get("inference_gateways", []):
            name = gw_spec["name"]
            gw_type = gw_spec["type"]
            gw_config = gw_spec.get("config", {})
            resources_by_name[name] = _instantiate_from_registry(gw_type, gw_config)

        # Tools
        for tool_spec in resources.get("tools", []):
            name = tool_spec["name"]
            tool_type = tool_spec["type"]
            tool_config = tool_spec.get("config", {})
            resources_by_name[name] = _instantiate_from_registry(tool_type, tool_config)

        # Subscribers
        for sub_spec in resources.get("subscribers", []):
            name = sub_spec["name"]
            sub_type = sub_spec["type"]
            sub_config = sub_spec.get("config", {})
            resources_by_name[name] = _instantiate_from_registry(sub_type, sub_config)

        # Build policies
        policies = _load_policies(spec, resources_by_name)

        # Build planner
        planner_spec = spec.get("planner", {})
        planner_type = planner_spec.get("type")
        planner_config = planner_spec.get("config", {})

        # Resolve gateway references
        if "inference_gateway" in planner_config:
            gw_name = planner_config["inference_gateway"]
            planner_config["inference_gateway"] = resources_by_name.get(gw_name)

        # Resolve tool descriptions for planner
        tool_names = spec.get("tools", [])
        tool_objects = [resources_by_name[t] for t in tool_names if t in resources_by_name]
        tool_descriptions = []
        for tool in tool_objects:
            desc = {
                "name": tool.name,
                "description": tool.description,
            }
            if hasattr(tool, "args_schema"):
                schema = tool.args_schema
                if hasattr(schema, "model_json_schema"):
                    desc["parameters"] = schema.model_json_schema()
            tool_descriptions.append(desc)

        planner_config["tool_descriptions"] = tool_descriptions

        # Handle worker_keys for router planners
        if "worker_keys" in planner_config:
            pass  # Already set
        elif kind == "ManagerAgent":
            workers_spec = spec.get("workers", [])
            planner_config["worker_keys"] = [w["name"] for w in workers_spec]

        planner = _instantiate_from_registry(planner_type, planner_config)

        # Build memory
        memory_spec = spec.get("memory", {})
        memory_type = memory_spec.get("type", "SharedInMemoryMemory")
        memory_config = memory_spec.get("config", {})
        memory = _instantiate_from_registry(memory_type, memory_config)

        # Build event bus and subscribers
        event_bus = EventBus()
        subscriber_names = spec.get("subscribers", [])
        for name in subscriber_names:
            if name in resources_by_name:
                event_bus.subscribe(resources_by_name[name])

        # Create agent
        if kind == "ManagerAgent":
            # Load workers
            workers: Dict[str, Any] = {}
            workers_spec = spec.get("workers", [])
            for w_spec in workers_spec:
                w_name = w_spec["name"]
                w_config_path = w_spec.get("config_path")
                if w_config_path:
                    workers[w_name] = cls.create_from_yaml(w_config_path)
                else:
                    raise ValueError(f"Worker '{w_name}' missing config_path")

            agent = ManagerAgent(
                name=metadata.get("name", "Manager"),
                planner=planner,
                workers=workers,
                memory=memory,
                event_bus=event_bus,
                policies=policies,
            )
        else:
            agent = Agent(
                name=metadata.get("name", "Agent"),
                planner=planner,
                tools=tool_objects,
                memory=memory,
                event_bus=event_bus,
                policies=policies,
            )

        return agent
