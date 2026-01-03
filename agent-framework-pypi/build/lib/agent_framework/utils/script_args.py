"""Helpers for normalizing script arguments emitted by planners."""
from __future__ import annotations

from typing import Dict, Any, Optional


ALIAS_MAP: Dict[str, Dict[str, str]] = {
    "add_table": {"table_name": "table"},
    "sql_analyzer": {
        "analysis_mode": "analysis_level",
        "analysis_type": "analysis_level",
        "detail_level": "analysis_level",
        "analysis_detail": "analysis_level",
        "mode": "analysis_level",
    },
}

SQL_ANALYSIS_LEVELS: Dict[str, str] = {
    "summary": "summary",
    "brief": "summary",
    "overview": "summary",
    "quick": "summary",
    "highlevel": "summary",
    "high-level": "summary",
    "comprehensive": "comprehensive",
    "detailed": "comprehensive",
    "detail": "comprehensive",
    "full": "comprehensive",
    "deep": "comprehensive",
    "complete": "comprehensive",
}


def _normalize_sql_analysis_level(raw_value: Optional[Any]) -> str:
    if raw_value is None:
        return "comprehensive"
    normalized = str(raw_value).strip().lower()
    if not normalized:
        return "comprehensive"
    return SQL_ANALYSIS_LEVELS.get(normalized, "comprehensive")


def normalize_script_args(tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Map common planner aliases to real tool args."""
    if not args:
        return args
    normalized = dict(args)
    alias_map = ALIAS_MAP.get(tool_name)
    if not alias_map:
        alias_map = {}
    for alias, target in alias_map.items():
        if alias in normalized and target not in normalized:
            normalized[target] = normalized.pop(alias)
    if tool_name == "sql_analyzer":
        normalized["analysis_level"] = _normalize_sql_analysis_level(normalized.get("analysis_level"))
    return normalized
