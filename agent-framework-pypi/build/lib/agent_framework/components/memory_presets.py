"""
Memory Presets for Framework v2.

Presets provide simplified memory configurations that auto-derive
namespace and agent_key from the agent context.

Usage in YAML:
    memory:
      $preset: worker

Available presets:
    - standalone: Isolated memory for single agents (InMemoryMemory)
    - worker: Shared memory for worker agents (SharedInMemoryMemory)
    - manager: Hierarchical memory that sees subordinates (HierarchicalSharedMemory)
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Callable

from .memory import InMemoryMemory, SharedInMemoryMemory, HierarchicalSharedMemory


def _get_namespace(context: Dict[str, Any]) -> str:
    """Get namespace from context, falling back to 'default'."""
    # Try context first, then environment
    namespace = context.get("namespace")
    if not namespace:
        namespace = context.get("JOB_ID") or context.get("job_id")
    if not namespace:
        namespace = os.getenv("JOB_ID", "default")
    return namespace


def _get_agent_key(context: Dict[str, Any]) -> str:
    """Get agent_key from context, falling back to agent name."""
    agent_key = context.get("agent_key")
    if not agent_key:
        agent_key = context.get("agent_name", "agent")
    # Normalize to lowercase with underscores
    return agent_key.lower().replace("-", "_").replace(" ", "_")


def _create_standalone(context: Dict[str, Any]) -> InMemoryMemory:
    """Create isolated in-memory storage for standalone agents."""
    return InMemoryMemory(
        agent_key=_get_agent_key(context)
    )


def _create_worker(context: Dict[str, Any]) -> SharedInMemoryMemory:
    """Create shared memory for worker agents."""
    return SharedInMemoryMemory(
        namespace=_get_namespace(context),
        agent_key=_get_agent_key(context)
    )


def _create_manager(context: Dict[str, Any]) -> HierarchicalSharedMemory:
    """Create hierarchical memory for manager agents that sees subordinates."""
    subordinates = context.get("subordinates", [])
    # Normalize subordinate keys
    subordinates = [s.lower().replace("-", "_").replace(" ", "_") for s in subordinates]

    return HierarchicalSharedMemory(
        namespace=_get_namespace(context),
        agent_key=_get_agent_key(context),
        subordinates=subordinates
    )


# Preset registry: name -> factory function
MEMORY_PRESETS: Dict[str, Callable[[Dict[str, Any]], Any]] = {
    "standalone": _create_standalone,
    "worker": _create_worker,
    "manager": _create_manager,
}


def get_memory_preset(preset_name: str, context: Optional[Dict[str, Any]] = None) -> Any:
    """
    Get a memory instance from a preset.

    Args:
        preset_name: Name of the preset (standalone, worker, manager)
        context: Optional context dict with:
            - agent_name: Name of the agent (used to derive agent_key)
            - namespace or JOB_ID: Namespace for shared memory
            - subordinates: List of subordinate agent names (for manager preset)

    Returns:
        Memory instance configured according to the preset

    Raises:
        ValueError: If preset_name is not recognized

    Example:
        >>> memory = get_memory_preset("worker", {"agent_name": "ResearchWorker"})
        >>> memory = get_memory_preset("manager", {
        ...     "agent_name": "Orchestrator",
        ...     "subordinates": ["research-worker", "task-worker"]
        ... })
    """
    if preset_name not in MEMORY_PRESETS:
        available = list(MEMORY_PRESETS.keys())
        raise ValueError(f"Unknown memory preset: '{preset_name}'. Available: {available}")

    context = context or {}
    factory = MEMORY_PRESETS[preset_name]
    return factory(context)


def list_memory_presets() -> List[str]:
    """List available memory preset names."""
    return list(MEMORY_PRESETS.keys())


# Preset descriptions for documentation/help
PRESET_DESCRIPTIONS = {
    "standalone": "Isolated memory for single agents. Each agent has private history.",
    "worker": "Shared memory for worker agents. Sees own messages + global updates.",
    "manager": "Hierarchical memory for managers. Sees own + subordinate messages + global updates.",
}


def describe_preset(preset_name: str) -> str:
    """Get description for a preset."""
    return PRESET_DESCRIPTIONS.get(preset_name, "No description available.")
