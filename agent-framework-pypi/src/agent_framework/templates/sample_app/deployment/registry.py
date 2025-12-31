"""
Registry for component discovery and loading.

Components are registered via YAML config files in the configs/ directory.
Each YAML file specifies a name and class path for the component.
"""
from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import Dict, List, Type

import yaml


_CONFIG_ROOT = Path(__file__).resolve().parents[1] / "configs"

# Additional config directories registered by applications
_ADDITIONAL_CONFIG_ROOTS: List[Path] = []


def register_config_root(config_root: Path) -> None:
    """
    Register an additional config directory for component discovery.

    Example:
        from deployment.registry import register_config_root
        from pathlib import Path

        register_config_root(Path("custom_tools/configs"))
    """
    if config_root not in _ADDITIONAL_CONFIG_ROOTS:
        _ADDITIONAL_CONFIG_ROOTS.append(config_root)


def _load_component_configs(category: str) -> Dict[str, Type]:
    """Load component configs from all registered config roots."""
    registry: Dict[str, Type] = {}

    # Collect all config directories to search
    directories = [_CONFIG_ROOT / category]
    for root in _ADDITIONAL_CONFIG_ROOTS:
        directories.append(root / category)

    for directory in directories:
        if not directory.exists():
            continue
        for path in sorted(directory.glob("*.yaml")):
            try:
                data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            except Exception:
                continue
            name = data.get("name")
            if not name:
                continue
            target = data.get("class")
            module_name = data.get("module")
            if not target:
                continue
            if module_name and "." not in target:
                dotted = f"{module_name}.{target}"
            else:
                dotted = target
            try:
                module_path, class_name = dotted.rsplit(".", 1)
                module = import_module(module_path)
                registry[name] = getattr(module, class_name)
            except Exception as exc:
                # Log warning but don't fail - allow partial loading
                print(f"Warning: Failed to load component '{name}' from {path}: {exc}")
                continue
    return registry


def register_tool(name: str, tool_class: Type) -> None:
    """Dynamically register a tool class."""
    TOOL_REGISTRY[name] = tool_class


def register_planner(name: str, planner_class: Type) -> None:
    """Dynamically register a planner class."""
    PLANNER_REGISTRY[name] = planner_class


def register_gateway(name: str, gateway_class: Type) -> None:
    """Dynamically register an inference gateway class."""
    GATEWAY_REGISTRY[name] = gateway_class


# Load default registries
PLANNER_REGISTRY = _load_component_configs("planners")
MEMORY_REGISTRY = _load_component_configs("memory")
TOOL_REGISTRY = _load_component_configs("tools")
SUBSCRIBER_REGISTRY = _load_component_configs("subscribers")
PROMPT_REGISTRY = _load_component_configs("prompt_managers")
GATEWAY_REGISTRY = _load_component_configs("gateways")
POLICY_REGISTRY = _load_component_configs("policies")
