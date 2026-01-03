from __future__ import annotations

import contextvars
from typing import Any, Dict, Optional

# Use contextvars instead of threading.local() for async/await compatibility
# This ensures proper isolation across concurrent async tasks (e.g., WebSocket connections)
_request_context: contextvars.ContextVar[Dict[str, Any]] = contextvars.ContextVar(
    '_request_context',
    default={}
)


def set_request_context(context: Dict[str, Any]) -> None:
    """Set the context for the current request (async-safe)."""
    _request_context.set(dict(context))


def get_request_context() -> Dict[str, Any]:
    """Get the context for the current request (async-safe)."""
    return _request_context.get()


def get_from_context(key: str, default: Optional[Any] = None) -> Any:
    """Get a specific value from the current request context (async-safe)."""
    return _request_context.get().get(key, default)


def update_request_context(**kwargs) -> None:
    """Update the current request context with new key-value pairs (async-safe)."""
    current = _request_context.get()
    updated = {**current, **kwargs}
    _request_context.set(updated)


def clear_request_context() -> None:
    """Clear the context for the current request (async-safe)."""
    _request_context.set({})
