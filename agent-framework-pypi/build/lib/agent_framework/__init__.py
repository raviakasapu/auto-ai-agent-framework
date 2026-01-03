# Agent Framework - Reusable Library for Agentic Architectures
#
# This module provides the public API for the framework.
# Import core components from here for application use.

__version__ = "0.3.0"

from agent_framework.base import (
    BaseTool,
    BasePlanner,
    BaseMemory,
    BasePromptManager,
    BaseInferenceGateway,
    BaseEventSubscriber,
    BaseProgressHandler,
    BaseMessageStore,
    BaseJobStore,
    Action,
    FinalResponse,
)

from agent_framework.core.agent import Agent
from agent_framework.core.manager_v2 import ManagerAgent
from agent_framework.core.events import EventBus

from agent_framework.components.message_store_memory import (
    MessageStoreMemory,
    HierarchicalMessageStoreMemory,
)

from agent_framework.policies.presets import get_preset

from agent_framework.decorators import tool, FunctionalTool

# Public API
__all__ = [
    # Version
    "__version__",
    # Decorators
    "tool",
    "FunctionalTool",
    # Base Classes
    "BaseTool",
    "BasePlanner",
    "BaseMemory",
    "BasePromptManager",
    "BaseInferenceGateway",
    "BaseEventSubscriber",
    "BaseProgressHandler",
    "BaseMessageStore",
    "BaseJobStore",
    "Action",
    "FinalResponse",
    # Core Agents
    "Agent",
    "ManagerAgent",
    # Memory Implementations
    "MessageStoreMemory",
    "HierarchicalMessageStoreMemory",
    # Events
    "EventBus",
    # Policies
    "get_preset",
]
