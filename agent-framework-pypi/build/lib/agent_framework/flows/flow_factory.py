from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from deployment.factory import AgentFactory, resolve_config_path


@dataclass
class FlowStep:
    name: str
    agent_key: str
    task: Optional[str]
    task_template: Optional[str]
    description: Optional[str]
    metadata: Dict[str, Any]

    def build_task(self, params: Optional[Dict[str, Any]] = None) -> str:
        if self.task_template:
            return self.task_template.format(**(params or {}))
        if self.task:
            return self.task
        raise ValueError(f"Flow step '{self.name}' does not define a task or task_template")


class Flow:
    def __init__(
        self,
        name: str,
        description: Optional[str],
        agents: Dict[str, Any],
        orchestrator_key: str,
        steps: Dict[str, FlowStep],
        metadata: Dict[str, Any],
    ) -> None:
        if orchestrator_key not in agents:
            raise ValueError(f"Orchestrator '{orchestrator_key}' not present in flow agents")
        self.name = name
        self.description = description
        self.agents = agents
        self.orchestrator_key = orchestrator_key
        self.steps = steps
        self.metadata = metadata

    @property
    def orchestrator(self) -> Any:
        return self.agents[self.orchestrator_key]

    def list_steps(self) -> Dict[str, FlowStep]:
        return dict(self.steps)

    async def run(
        self,
        step_name: str,
        params: Optional[Dict[str, Any]] = None,
        progress_handler: Any = None,
    ) -> Any:
        if step_name not in self.steps:
            raise ValueError(f"Unknown flow step '{step_name}'")
        step = self.steps[step_name]
        agent = self.agents.get(step.agent_key)
        if not agent:
            raise ValueError(f"Agent '{step.agent_key}' not found for step '{step_name}'")
        task = step.build_task(params)
        return await agent.run(task, progress_handler=progress_handler)


class FlowFactory:
    @staticmethod
    def create_from_yaml(filepath: str) -> Flow:
        path = FlowFactory._resolve_path(filepath)
        text = path.read_text(encoding="utf-8")
        text = os.path.expandvars(text)
        raw = yaml.safe_load(text) or {}
        if raw.get("kind") != "Flow":
            raise ValueError("Unsupported flow schema. Expected kind: Flow")

        metadata = raw.get("metadata", {})
        spec = raw.get("spec") or {}

        agents = FlowFactory._load_agents(spec.get("agents", {}))
        orchestrator = spec.get("orchestrator")
        if not orchestrator:
            raise ValueError("Flow spec must define an 'orchestrator' agent key")

        steps = FlowFactory._load_steps(spec.get("steps", []))
        return Flow(
            name=metadata.get("name", path.stem),
            description=metadata.get("description"),
            agents=agents,
            orchestrator_key=orchestrator,
            steps=steps,
            metadata=metadata,
        )

    @staticmethod
    def _resolve_path(filepath: str) -> Path:
        candidate = Path(filepath)
        if candidate.exists():
            return candidate
        if candidate.is_absolute():
            raise FileNotFoundError(f"Flow file not found: {filepath}")
        sdk_root = Path(__file__).resolve().parents[2]
        for base in (Path.cwd(), sdk_root, sdk_root / "flows"):
            resolved = (base / candidate).resolve()
            if resolved.exists():
                return resolved
        raise FileNotFoundError(f"Flow file not found: {filepath}")

    @staticmethod
    def _load_agents(agents_spec: Dict[str, Any]) -> Dict[str, Any]:
        agents: Dict[str, Any] = {}
        for key, value in agents_spec.items():
            if isinstance(value, dict):
                config_path = value.get("config")
            else:
                config_path = value
            if not config_path:
                raise ValueError(f"Agent '{key}' missing config path")
            resolved = resolve_config_path(str(config_path))
            agent = AgentFactory.create_from_yaml(str(resolved))
            agents[key] = agent
        return agents

    @staticmethod
    def _load_steps(steps_spec: Any) -> Dict[str, FlowStep]:
        steps: Dict[str, FlowStep] = {}
        for item in steps_spec or []:
            name = item.get("name")
            if not name:
                raise ValueError("Flow step is missing 'name'")
            agent_key = item.get("agent")
            if not agent_key:
                raise ValueError(f"Flow step '{name}' missing 'agent' reference")
            step = FlowStep(
                name=name,
                agent_key=agent_key,
                task=item.get("task"),
                task_template=item.get("task_template"),
                description=item.get("description"),
                metadata=item.get("metadata", {}),
            )
            steps[name] = step
        return steps
