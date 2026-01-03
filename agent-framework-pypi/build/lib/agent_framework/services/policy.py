from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Tuple
from pathlib import Path
import threading

import yaml


# Pluggable data model service getter for policy evaluation
_policy_datamodel_getter: Optional[Callable[[], Any]] = None


def register_policy_datamodel_service(getter: Callable[[], Any]) -> None:
    """
    Register a function that returns the data model service for policy evaluation.
    
    Applications should call this to enable policy checks that require data model access.
    """
    global _policy_datamodel_getter
    _policy_datamodel_getter = getter


def _get_policy_datamodel_service() -> Any:
    """Get data model service for policy checks if registered."""
    if _policy_datamodel_getter:
        return _policy_datamodel_getter()
    return None


class PolicyEngine:
    """Lightweight, process-scoped policy engine for tool pre-execution checks.

    Loads YAML policy files and evaluates deny rules against the current action
    (tool_name + tool_args). Designed to be fast and simple.
    """

    _instance_lock = threading.Lock()
    _instance: Optional["PolicyEngine"] = None

    def __init__(self, policy_paths: Optional[List[str]] = None) -> None:
        self._policies: List[Dict[str, Any]] = []
        self._loaded_paths: List[str] = []
        if policy_paths:
            for p in policy_paths:
                self._load_path(p)

    @classmethod
    def get(cls) -> "PolicyEngine":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    # Default path: powerbi policy
                    default_paths = ["configs/policies/powerbi.yaml"]
                    cls._instance = PolicyEngine(default_paths)
        return cls._instance

    def _load_path(self, path_str: str) -> None:
        path = Path(path_str)
        if not path.exists():
            return
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            if isinstance(data, dict):
                self._policies.append(data)
                self._loaded_paths.append(path_str)
        except Exception:
            # Keep engine robust even if a policy file is malformed
            pass

    def evaluate(self, tool_name: str, tool_args: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Evaluate deny rules. Returns (allowed, message_if_denied)."""
        for pol in self._policies:
            deny_rules = pol.get("deny", []) or []
            for rule in deny_rules:
                if rule.get("tool") != tool_name:
                    continue
                when: Dict[str, Any] = rule.get("when", {}) or {}
                if self._conditions_met(when, tool_name, tool_args):
                    msg = rule.get("message") or "Action denied by policy"
                    return False, msg
        return True, None

    def _conditions_met(self, conds: Dict[str, Any], tool_name: str, tool_args: Dict[str, Any]) -> bool:
        # All conditions must be satisfied
        for key, expected in conds.items():
            if key == "endpoint_is_measure":
                actual = self._endpoint_is_measure(tool_name, tool_args)
                if bool(actual) != bool(expected):
                    return False
            elif key == "missing_columns":
                actual = self._missing_columns(tool_name, tool_args)
                if bool(actual) != bool(expected):
                    return False
            else:
                # Unknown condition keys default to not satisfied
                return False
        return True

    def _endpoint_is_measure(self, tool_name: str, tool_args: Dict[str, Any]) -> bool:
        """Detect if the provided endpoint refers to a measure (not a column)."""
        try:
            svc = _get_policy_datamodel_service()
            if not svc:
                return False
            def is_measure(table: Optional[str], column: Optional[str]) -> bool:
                if not table or not column:
                    return False
                t = svc.get_table(table)
                if not t:
                    return False
                measures = {m.get("name") for m in (t.get("measures", []) or [])}
                return column in measures

            if tool_name == "add_relationship":
                ft = tool_args.get("from_table")
                fc = tool_args.get("from_column")
                tt = tool_args.get("to_table")
                tc = tool_args.get("to_column")
                return is_measure(ft, fc) or is_measure(tt, tc)

            if tool_name == "update_relationship":
                ft = tool_args.get("from_table")
                fc = tool_args.get("from_column")
                tt = tool_args.get("to_table")
                tc = tool_args.get("to_column")
                return (is_measure(ft, fc) if (ft and fc) else False) or (is_measure(tt, tc) if (tt and tc) else False)
        except Exception:
            return False
        return False

    def _missing_columns(self, tool_name: str, tool_args: Dict[str, Any]) -> bool:
        """Detect if referenced columns are missing in their respective tables.

        True when any provided (table, column) pair does not refer to an existing column.
        """
        try:
            svc = _get_policy_datamodel_service()
            if not svc:
                return False

            def col_missing(table: Optional[str], column: Optional[str]) -> bool:
                if not table or not column:
                    return False
                t = svc.get_table(table)
                if not t:
                    return True
                cols = {c.get("name") for c in (t.get("columns", []) or [])}
                return column not in cols

            if tool_name == "add_relationship":
                return (col_missing(tool_args.get("from_table"), tool_args.get("from_column")) or
                        col_missing(tool_args.get("to_table"), tool_args.get("to_column")))

            if tool_name == "update_relationship":
                missing_left = False
                missing_right = False
                if tool_args.get("from_table") and tool_args.get("from_column"):
                    missing_left = col_missing(tool_args.get("from_table"), tool_args.get("from_column"))
                if tool_args.get("to_table") and tool_args.get("to_column"):
                    missing_right = col_missing(tool_args.get("to_table"), tool_args.get("to_column"))
                return missing_left or missing_right
        except Exception:
            return False
        return False
