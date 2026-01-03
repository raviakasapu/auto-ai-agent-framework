from __future__ import annotations

import json
from typing import Dict, Any

from ..core.agent import Agent


def generate_manifest(agent: Agent) -> Dict[str, Any]:
    """Inspect an agent instance and generate a manifest-like description.

    Returns a dict suitable for JSON/YAML serialization.
    """
    tool_manifests = []
    for tool_name, tool in agent.tools.items():
        # Pydantic JSON schema for inputs
        try:
            input_schema = tool.args_schema.model_json_schema()  # pydantic v2
        except Exception:
            input_schema = {}
        parameters = input_schema.get("properties", {})
        required = input_schema.get("required", [])

        # Output schema (if provided)
        returns: Dict[str, Any]
        try:
            if getattr(tool, "output_schema", None):
                returns = tool.output_schema.model_json_schema()  # type: ignore[attr-defined]
            else:
                returns = {"type": "string", "description": "Tool textual output."}
        except Exception:
            returns = {"type": "string", "description": "Tool textual output."}

        tool_manifest = {
            "name": tool.name,
            "description": tool.description,
            "parameters": parameters,
            "required": required,
            "returns": returns,
        }
        tool_manifests.append(tool_manifest)

    manifest = {
        "agent_name": getattr(agent, "name", "Agent"),
        "description": getattr(agent, "description", "An AI agent."),
        "version": getattr(agent, "version", "0.1.0"),
        "tools": tool_manifests,
    }
    return manifest


def save_manifest(agent: Agent, filepath: str) -> None:
    data = generate_manifest(agent)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
