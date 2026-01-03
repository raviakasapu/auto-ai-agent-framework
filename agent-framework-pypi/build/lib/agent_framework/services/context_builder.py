from __future__ import annotations

"""ContextBuilder - assembles role-specific context bundles for agents."""

from typing import Any, Callable, Dict, List, Optional, Tuple
import json

from agent_framework.components.memory import _shared_state_store


# Pluggable data model service getter - applications can register their own
_datamodel_service_getter: Optional[Callable[[str], Any]] = None


def register_datamodel_service(getter: Callable[[str], Any]) -> None:
    """
    Register a function that returns a data model service for a given job_id.
    
    Applications should call this to provide their domain-specific data model service.
    
    Example:
        from bi_tools.services.datamodel_service import get_datamodel_service
        from agent_framework.services.context_builder import register_datamodel_service
        
        register_datamodel_service(get_datamodel_service)
    """
    global _datamodel_service_getter
    _datamodel_service_getter = getter


def _get_datamodel_service(job_id: str) -> Any:
    """Get data model service if registered, otherwise return None."""
    if _datamodel_service_getter:
        return _datamodel_service_getter(job_id)
    return None


class ContextBuilder:
    """Builds orchestrator, manager, worker, and synthesizer context packages."""

    ORCHESTRATOR_HISTORY_TURNS = 8
    MANAGER_MANIFEST_LIMIT = 6000
    WORKER_SCRIPT_LIMIT = 4000

    def __init__(self, job_id: str) -> None:
        self.job_id = str(job_id)
        self._manifest_cache: Optional[str] = None

    # ---- Public builders ----
    def build_orchestrator_context(
        self,
        latest_request: str,
        available_managers: List[Dict[str, str]],
    ) -> str:
        """Executive briefing for orchestrators (no detailed schema)."""
        managers_block = self._format_catalog(available_managers, fallback="No managers configured.")
        conversation_summary = self._conversation_summary(self.ORCHESTRATOR_HISTORY_TURNS)
        parts = [
            "== Available Managers ==",
            managers_block,
            "",
            "== Conversation Summary ==",
            conversation_summary or "No prior conversation.",
            "",
            "== Current User Request ==",
            latest_request.strip() or "(empty request)",
        ]
        return "\n".join(parts).strip()

    def build_manager_context(
        self,
        phase_goal: str,
        worker_descriptions: List[Dict[str, str]],
        previous_outcome: Optional[str] = None,
    ) -> Tuple[str, Optional[str]]:
        """Project blueprint for managers. Returns (context_text, full_manifest)."""
        manifest_text = self.get_schema_manifest()
        manifest_display = (manifest_text or "Manifest unavailable.")[: self.MANAGER_MANIFEST_LIMIT]
        workers_block = self._format_catalog(worker_descriptions, fallback="No workers configured.")
        parts = [
            "== Director Goal ==",
            phase_goal.strip() or "(no goal provided)",
            "",
            "== Data Model Manifest ==",
            manifest_display,
            "",
            "== Available Workers & Tools ==",
            workers_block,
        ]
        if previous_outcome:
            parts.extend(["", "== Previous Phase Outcome ==", previous_outcome])
        return "\n".join(parts).strip(), manifest_text

    def build_worker_execution_context(
        self,
        manager_goal: str,
        script_steps: Optional[List[Dict[str, Any]]] = None,
        suggested_plan: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Work order for workers (goal + script or suggested plan)."""
        def _format_block(title: str, payload: Optional[List[Dict[str, Any]]]) -> str:
            if not payload:
                return ""
            try:
                block = json.dumps(payload, indent=2)
            except Exception:
                block = str(payload)
            if len(block) > self.WORKER_SCRIPT_LIMIT:
                block = block[: self.WORKER_SCRIPT_LIMIT] + "\n... (truncated)"
            return "\n".join(["", f"== {title} ==", block])

        parts = [
            "== Manager Goal ==",
            manager_goal.strip() or "(unspecified)",
        ]
        script_block = _format_block("Script to Execute", script_steps)
        plan_block = _format_block("Manager Suggested Plan", suggested_plan)
        if script_block:
            parts.append(script_block)
        if plan_block:
            parts.append(plan_block)
        assembled = "\n".join(parts).strip()
        return {
            "manager_goal": manager_goal,
            "script_steps": script_steps,
            "suggested_plan": suggested_plan,
            "assembled_context": assembled,
        }

    def build_synthesizer_context(
        self,
        latest_request: str,
        technical_result: Any,
    ) -> str:
        """Press-release style context for synthesizer agents."""
        if isinstance(technical_result, dict):
            try:
                result_text = json.dumps(technical_result, indent=2)
            except Exception:
                result_text = str(technical_result)
        else:
            result_text = str(technical_result)
        return "\n".join(
            [
                "== User Request ==",
                latest_request.strip() or "(empty)",
                "",
                "== Technical Outcome ==",
                result_text,
            ]
        ).strip()

    # ---- Helpers ----
    def get_schema_manifest(self) -> Optional[str]:
        """Fetch and cache schema manifest."""
        if self._manifest_cache:
            return self._manifest_cache
        try:
            service = _get_datamodel_service(self.job_id)
            if service:
                getter = getattr(service, "get_schema_manifest", None)
                if callable(getter):
                    manifest = getter()
                    if manifest:
                        self._manifest_cache = manifest
                        return manifest
        except Exception:
            return self._manifest_cache
        return self._manifest_cache

    def _conversation_summary(self, limit: int) -> str:
        turns = _shared_state_store.list_conversation(self.job_id) or []
        if not turns:
            return ""
        selected = turns[-limit:]
        lines: List[str] = []
        for turn in selected:
            role = str(turn.get("role", "user")).upper()
            content = str(turn.get("content", ""))
            lines.append(f"{role}: {content}")
        return "\n".join(lines)

    def _format_catalog(self, entries: List[Dict[str, str]], fallback: str) -> str:
        if not entries:
            return fallback
        lines: List[str] = []
        for entry in entries:
            name = entry.get("name") or entry.get("worker") or "unknown"
            desc = entry.get("description") or entry.get("details") or ""
            lines.append(f"- {name}: {desc}".strip())
        return "\n".join(lines)

    def latest_user_message(self) -> Optional[str]:
        """Return the most recent user turn content."""
        turns = _shared_state_store.list_conversation(self.job_id) or []
        for turn in reversed(turns):
            if str(turn.get("role", "")).lower() == "user":
                return str(turn.get("content", "")).strip()
        return None
