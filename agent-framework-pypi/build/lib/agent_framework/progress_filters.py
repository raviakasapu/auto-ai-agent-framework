from __future__ import annotations

import os
from typing import Iterable, Optional, Set, Tuple

DEFAULT_FRONTEND_EVENTS: Set[str] = {
    "connected",
    "request_start",
    "orchestrator_start",
    "orchestrator_phase_start",
    "orchestrator_phase_end",
    "orchestrator_end",
    "synthesis_start",
    "synthesis_end",
    "manager_start",
    "manager_script_planned",
    "manager_step_start",
    "manager_step_end",
    "manager_end",
    "delegation_planned",
    "delegation_chosen",
    "delegation_executed",
    "agent_start",
    "agent_end",
    "worker_tool_call",
    "worker_tool_result",
    "action_planned",
    "action_executed",
    "policy_denied",
    "error",
}


def normalize_event_names(events: Iterable[str]) -> Optional[Set[str]]:
    """
    Normalize a collection of event names for filtering.

    Returns:
        - None if "*" is present (treat as allow all)
        - Empty set if there were no usable entries
        - Otherwise a normalized set of names
    """
    normalized = {str(evt).strip() for evt in events if str(evt).strip()}
    if not normalized:
        return set()
    if "*" in normalized:
        return None
    return normalized


def resolve_frontend_allowlist() -> Tuple[bool, Optional[Set[str]]]:
    """
    Resolve optional FRONTEND_EVENT_ALLOWLIST override from environment.

    Returns:
        (has_override, normalized_events_or_none)
    """
    raw = os.getenv("FRONTEND_EVENT_ALLOWLIST")
    if raw is None:
        return False, None
    tokens = [part.strip() for part in raw.split(",")]
    return True, normalize_event_names(tokens)
