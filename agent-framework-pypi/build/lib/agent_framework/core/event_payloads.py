from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional


def _actor(role: str, name: str, version: Optional[str] = None) -> Dict[str, Any]:
    actor: Dict[str, Any] = {"role": role, "name": name}
    if version:
        actor["version"] = version
    return actor


def _normalize_result(result: Any, summary_hint: Optional[str] = None) -> Dict[str, Any]:
    raw = result
    if hasattr(result, "model_dump"):
        try:
            raw = result.model_dump()
        except Exception:
            raw = result
    elif isinstance(result, dict):
        raw = dict(result)

    summary = summary_hint
    operation = None
    payload = None
    if isinstance(raw, dict):
        operation = raw.get("operation")
        payload = raw.get("payload")
        for key in ("human_readable_summary", "summary", "message"):
            val = raw.get(key)
            if val:
                summary = str(val)
                break
    else:
        summary = str(raw) if raw is not None else summary_hint

    return {
        "operation": operation,
        "payload": payload,
        "summary": summary,
        "data": raw,
    }


def _infer_status(result: Any, default: str = "success") -> str:
    if isinstance(result, dict):
        if result.get("operation") == "await_approval" or result.get("pending") is True:
            return "pending"
        if (
            result.get("error")
            or result.get("success") is False
            or result.get("error_message")
        ):
            return "error"
        payload = result.get("payload")
        if isinstance(payload, dict) and (
            payload.get("error") or payload.get("success") is False
        ):
            return "error"
    return default


def build_manager_start_event(
    *,
    task: str,
    workers: Iterable[str],
    has_plan: bool,
    manager_name: str,
    manager_version: Optional[str],
    prompt: Optional[str] = None,
    orchestrator_plan: Optional[Dict[str, Any]] = None,
    manager_tools: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "actor": _actor("manager", manager_name, manager_version),
        "task": {"description": task, "has_plan": bool(has_plan)},
        "workers": list(workers),
        "manager_name": manager_name,
        "manager_version": manager_version,
        "has_plan": bool(has_plan),
    }
    context: Dict[str, Any] = {}
    if prompt:
        context["prompt"] = prompt
    if orchestrator_plan:
        context["orchestrator_plan"] = orchestrator_plan
    if manager_tools:
        context["tools"] = manager_tools
    if context:
        payload["context"] = context
    return payload


def build_manager_end_event(
    *,
    manager_name: str,
    manager_version: Optional[str],
    result: Any,
    status: Optional[str] = None,
    error_message: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    normalized = _normalize_result(result)
    resolved_status = status or _infer_status(normalized["data"], default="success")
    payload: Dict[str, Any] = {
        "actor": _actor("manager", manager_name, manager_version),
        "status": resolved_status,
        "result": normalized["data"],
        "result_detail": normalized,
        "summary": normalized["summary"],
        "operation": normalized["operation"],
        "payload": normalized["payload"],
        "manager_name": manager_name,
        "manager_version": manager_version,
    }
    if error_message:
        payload["error"] = {"message": error_message}
    if metadata:
        payload["metadata"] = metadata
    return payload


def build_agent_start_event(
    *,
    task: str,
    agent_name: str,
    agent_version: Optional[str],
    prompt: Optional[str] = None,
    manager_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "actor": _actor("agent", agent_name, agent_version),
        "task": {"description": task},
        "agent_name": agent_name,
        "agent_version": agent_version,
    }
    context: Dict[str, Any] = {}
    if prompt:
        context["prompt"] = prompt
    if manager_context:
        context["manager_context"] = manager_context
    if context:
        payload["context"] = context
    return payload


def build_agent_end_event(
    *,
    agent_name: str,
    agent_version: Optional[str],
    result: Any,
    status: Optional[str] = None,
    error_message: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    normalized = _normalize_result(result)
    resolved_status = status or _infer_status(normalized["data"], default="success")
    payload: Dict[str, Any] = {
        "actor": _actor("agent", agent_name, agent_version),
        "status": resolved_status,
        "result": normalized["data"],
        "result_detail": normalized,
        "summary": normalized["summary"],
        "operation": normalized["operation"],
        "payload": normalized["payload"],
        "agent_name": agent_name,
        "agent_version": agent_version,
    }
    if error_message:
        payload["error"] = {"message": error_message}
    if metadata:
        payload["metadata"] = metadata
    return payload


def build_action_planned_event(
    *,
    actor_role: str,
    actor_name: str,
    actor_version: Optional[str],
    tool_name: str,
    args: Dict[str, Any],
    tool_label: Optional[str] = None,
    tool_description: Optional[str] = None,
    thought: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    action = {
        "tool_name": tool_name,
        "args": args,
        "label": tool_label,
        "description": tool_description,
    }
    payload: Dict[str, Any] = {
        "actor": _actor(actor_role, actor_name, actor_version),
        "action": action,
        "agent_name": actor_name,
    }
    payload["tool"] = tool_name
    payload["tool_name"] = tool_name
    if thought:
        payload["thought"] = thought
    if metadata:
        payload["metadata"] = metadata
    return payload


def build_action_executed_event(
    *,
    actor_role: str,
    actor_name: str,
    actor_version: Optional[str],
    tool_name: str,
    args: Dict[str, Any],
    result: Any,
    execution_time_ms: Optional[int] = None,
    tool_label: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    normalized = _normalize_result(result)
    payload: Dict[str, Any] = {
        "actor": _actor(actor_role, actor_name, actor_version),
        "action": {
            "tool_name": tool_name,
            "args": args,
            "label": tool_label,
        },
        "result": normalized["data"],
        "result_detail": normalized,
        "summary": normalized["summary"],
        "agent_name": actor_name,
    }
    payload["tool"] = tool_name
    payload["tool_name"] = tool_name
    if execution_time_ms is not None:
        payload["execution_time_ms"] = execution_time_ms
    if metadata:
        payload["metadata"] = metadata
    return payload


def build_worker_tool_call_event(
    *,
    worker_name: str,
    worker_version: Optional[str],
    call_id: str,
    tool_name: str,
    tool_label: Optional[str],
    tool_description: Optional[str],
    args: Dict[str, Any],
    action_index: int,
) -> Dict[str, Any]:
    return {
        "actor": _actor("agent", worker_name, worker_version),
        "call_id": call_id,
        "tool_name": tool_name,
        "tool_label": tool_label,
        "tool_description": tool_description,
        "args": args,
        "worker_name": worker_name,
        "agent_name": worker_name,
        "action_index": action_index,
    }


def build_worker_tool_result_event(
    *,
    worker_name: str,
    worker_version: Optional[str],
    call_id: str,
    tool_name: str,
    tool_label: Optional[str],
    tool_description: Optional[str],
    args: Dict[str, Any],
    result_payload: Any,
    success: bool,
    summary: Optional[str],
    error_message: Optional[str],
    action_index: int,
    execution_time_ms: Optional[int] = None,
) -> Dict[str, Any]:
    event_payload: Dict[str, Any] = {
        "actor": _actor("agent", worker_name, worker_version),
        "call_id": call_id,
        "tool_name": tool_name,
        "tool_label": tool_label,
        "tool_description": tool_description,
        "args": args,
        "worker_name": worker_name,
        "agent_name": worker_name,
        "action_index": action_index,
        "result": {
            "success": success,
            "summary": summary,
            "error": error_message,
            "data": result_payload,
        },
    }
    if execution_time_ms is not None:
        event_payload["execution_time_ms"] = execution_time_ms
    return event_payload


def build_policy_denied_event(
    *,
    actor_name: str,
    actor_version: Optional[str],
    tool_name: str,
    reason: Optional[str],
) -> Dict[str, Any]:
    return {
        "actor": _actor("agent", actor_name, actor_version),
        "tool": tool_name,
        "reason": reason,
        "agent_name": actor_name,
    }


def build_delegation_event(
    *,
    manager_name: str,
    manager_version: Optional[str],
    worker_key: str,
    worker_agent_name: Optional[str],
    metadata: Optional[Dict[str, Any]] = None,
    result: Any = None,
    status: Optional[str] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "actor": _actor("manager", manager_name, manager_version),
        "worker": {
            "key": worker_key,
            "name": worker_agent_name or worker_key,
        },
        "manager_name": manager_name,
        "manager_version": manager_version,
    }
    if metadata:
        payload["metadata"] = metadata
    if result is not None:
        normalized = _normalize_result(result)
        payload["result"] = normalized["data"]
        payload["result_detail"] = normalized
        payload["status"] = status or _infer_status(normalized["data"])
    return payload


def build_manager_script_planned_event(
    *,
    manager_name: str,
    manager_version: Optional[str],
    script_steps: List[Dict[str, Any]],
    script_metadata: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "actor": _actor("manager", manager_name, manager_version),
        "script": script_steps,
        "script_metadata": script_metadata,
        "manager_name": manager_name,
        "manager_version": manager_version,
    }


def build_segment_event(
    *,
    actor_role: str,
    actor_name: str,
    actor_version: Optional[str],
    index_key: str,
    total_key: str,
    item_key: str,
    index: int,
    total: int,
    item: Dict[str, Any],
    result: Any = None,
    status: Optional[str] = None,
    result_summary: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "actor": _actor(actor_role, actor_name, actor_version),
        index_key: index,
        total_key: total,
        item_key: item,
        "manager_name": actor_name if actor_role == "manager" else actor_name,
    }
    if extra:
        payload.update(extra)
    if result is not None:
        normalized = _normalize_result(result, summary_hint=result_summary)
        payload["result"] = {
            "status": status or _infer_status(normalized["data"]),
            "summary": result_summary or normalized["summary"],
            "data": normalized["data"],
        }
        payload["result_detail"] = normalized
    return payload


def build_error_event(
    *,
    actor_role: str,
    actor_name: str,
    actor_version: Optional[str],
    message: str,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "actor": _actor(actor_role, actor_name, actor_version),
        "message": message,
    }
    if details:
        payload["details"] = details
    if actor_role == "manager":
        payload["manager_name"] = actor_name
        payload["manager_version"] = actor_version
    else:
        payload["agent_name"] = actor_name
        payload["agent_version"] = actor_version
    return payload
