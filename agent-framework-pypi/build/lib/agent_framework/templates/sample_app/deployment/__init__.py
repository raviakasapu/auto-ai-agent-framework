"""
Deployment module for the Sample App.

Provides factory and registry for creating agents from YAML configurations.
"""

from .factory import AgentFactory
from .registry import (
    PLANNER_REGISTRY,
    MEMORY_REGISTRY,
    TOOL_REGISTRY,
    SUBSCRIBER_REGISTRY,
    GATEWAY_REGISTRY,
    POLICY_REGISTRY,
    register_tool,
    register_planner,
    register_gateway,
    register_config_root,
)

__all__ = [
    "AgentFactory",
    "PLANNER_REGISTRY",
    "MEMORY_REGISTRY",
    "TOOL_REGISTRY",
    "SUBSCRIBER_REGISTRY",
    "GATEWAY_REGISTRY",
    "POLICY_REGISTRY",
    "register_tool",
    "register_planner",
    "register_gateway",
    "register_config_root",
]
