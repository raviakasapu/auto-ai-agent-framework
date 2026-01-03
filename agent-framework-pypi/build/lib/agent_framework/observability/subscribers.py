from __future__ import annotations

import json
import os
import uuid
from typing import Any, Dict, Optional

from ..base import BaseEventSubscriber

# Optional Langfuse SDK import
try:  # pragma: no cover - optional dependency
    from langfuse import Langfuse  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    Langfuse = None  # type: ignore

# Optional OpenTelemetry dependency for Phoenix
try:  # pragma: no cover - optional dependency
    from opentelemetry import trace  # type: ignore
    from opentelemetry.context import attach, detach  # type: ignore
    try:
        from opentelemetry.baggage import set_baggage, get_baggage  # type: ignore
    except Exception:  # pragma: no cover - optional
        set_baggage = None  # type: ignore
        get_baggage = None  # type: ignore
    from opentelemetry.sdk.resources import Resource  # type: ignore
    from opentelemetry.sdk.trace import TracerProvider  # type: ignore
    from opentelemetry.sdk.trace.export import BatchSpanProcessor  # type: ignore
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    trace = None  # type: ignore
    Resource = None  # type: ignore
    TracerProvider = None  # type: ignore
    BatchSpanProcessor = None  # type: ignore
    OTLPSpanExporter = None  # type: ignore


def _sanitize_for_json(data: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure metadata is JSON serializable."""
    sanitized: Dict[str, Any] = {}
    for key, value in data.items():
        try:
            json.dumps(value)
            sanitized[key] = value
        except TypeError:
            sanitized[key] = repr(value)
    return sanitized


def _truncate_str(s: str, limit_env: str = "PHOENIX_MAX_ATTR_CHARS", default: int = 4000) -> str:
    try:
        max_len = int(os.getenv(limit_env, str(default)))
    except Exception:
        max_len = default
    if len(s) <= max_len:
        return s
    return s[:max_len] + "...(truncated)"


class LangfuseSubscriber(BaseEventSubscriber):
    """Publish agent events to Langfuse."""

    def __init__(
        self,
        host: Optional[str] = None,
        public_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        trace_id: Optional[str] = None,
        trace_name: str = "agent-run",
        flush_each_event: bool = False,
    ) -> None:
        if Langfuse is None:
            raise ImportError(
                "LangfuseSubscriber requires the 'langfuse' package. "
                "Install it with 'pip install langfuse'."
            )

        resolved_host = host or os.getenv("LANGFUSE_HOST") or "https://cloud.langfuse.com"
        resolved_public = public_key or os.getenv("LANGFUSE_PUBLIC_KEY")
        resolved_secret = secret_key or os.getenv("LANGFUSE_SECRET_KEY")
        if not resolved_public or not resolved_secret:
            raise RuntimeError(
                "LangfuseSubscriber needs LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY "
                "environment variables or explicit config values."
            )

        self._client = Langfuse(
            public_key=resolved_public,
            secret_key=resolved_secret,
            host=resolved_host,
        )
        self._trace = self._client.trace(
            id=trace_id or uuid.uuid4().hex,
            name=trace_name,
        )
        self._flush_each_event = flush_each_event

    def handle_event(self, event_name: str, data: Dict[str, Any]) -> None:
        payload = _sanitize_for_json(data)
        try:
            self._client.event(
                trace_id=self._trace.id,
                name=event_name,
                metadata=payload,
            )
            if self._flush_each_event:
                self._client.flush()
        except Exception as exc:  # pragma: no cover - defensive logging
            print(f"[LangfuseSubscriber] Failed to emit event '{event_name}': {exc}")


class PhoenixSubscriber(BaseEventSubscriber):
    """Export agent events to Arize Phoenix via OTLP HTTP."""

    def __init__(
        self,
        endpoint: Optional[str] = None,
        service_name: str = "agent-framework",
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = 10,
        flush_each_event: bool = False,
    ) -> None:
        if None in (Resource, TracerProvider, BatchSpanProcessor, OTLPSpanExporter):
            raise ImportError(
                "PhoenixSubscriber requires 'opentelemetry-sdk' and "
                "'opentelemetry-exporter-otlp'. Install them with "
                "'pip install opentelemetry-sdk opentelemetry-exporter-otlp'."
            )

        # Use environment variable or default Phoenix endpoint
        resolved_endpoint = endpoint or os.getenv("PHOENIX_ENDPOINT", "http://localhost:6006/v1/traces")
        
        resource = Resource.create({"service.name": service_name})
        provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter(
            endpoint=resolved_endpoint,
            headers=headers or {},
            timeout=timeout,
        )
        processor = BatchSpanProcessor(exporter)
        provider.add_span_processor(processor)

        # Try to set as the global provider so other tracers (e.g., main.py) use this exporter
        try:  # be tolerant if already set elsewhere
            if trace is not None:
                # Only set if current provider is not already a TracerProvider instance
                current = trace.get_tracer_provider()
                # Some SDKs return a proxy before first set; safe to call set once
                trace.set_tracer_provider(provider)  # type: ignore[arg-type]
        except Exception:
            # If global provider was already set, keep using our local provider for spans we create
            pass
        
        # Always use the global provider/tracer to keep hierarchy consistent across subscribers
        if trace is not None:
            self._provider = trace.get_tracer_provider()
            self._tracer = trace.get_tracer("agent-framework.observability")
        else:  # fallback (should not happen if imports succeeded)
            self._provider = provider
            self._tracer = provider.get_tracer("agent-framework.observability")
        self._flush_each_event = flush_each_event
        # Readability/options
        try:
            # Default to false to avoid noisy pretty attributes unless explicitly enabled
            self._pretty_json = os.getenv("PHOENIX_PRETTY_JSON", "false").lower() in {"1", "true", "yes"}
        except Exception:
            self._pretty_json = False
        try:
            self._compact_json = os.getenv("PHOENIX_COMPACT_JSON", "false").lower() in {"1", "true", "yes"}
        except Exception:
            self._compact_json = False
        # Global switch to disable payload/body attributes entirely
        try:
            self._disable_payloads = os.getenv("PHOENIX_DISABLE_PAYLOADS", "false").lower() in {"1", "true", "yes"}
        except Exception:
            self._disable_payloads = False
        
        # Maintain hierarchical, long‑lived spans keyed by lifecycle events
        # Simple stacks to match start/end pairs (supports nested managers/agents)
        from collections import defaultdict
        self._agent_stack: list[tuple[Any, Any]] = []  # (span, token)
        self._manager_stack: list[tuple[Any, Any]] = []
        self._delegation_stacks: Dict[str, list[tuple[Any, Any]]] = defaultdict(list)  # worker -> stack
        self._action_stacks: Dict[str, list[tuple[Any, Any]]] = defaultdict(list)  # tool_name -> stack
        self._multi_step_stacks: Dict[int, list[tuple[Any, Any]]] = defaultdict(list)  # step_idx -> stack

    def clear_stacks(self) -> None:
        """Clear all span stacks to start a fresh trace.
        
        Call this at the beginning of each new request to ensure traces don't leak across requests.
        """
        # End any open spans before clearing
        for st in self._agent_stack:
            try:
                span, token = st
                if span:
                    span.end()
                if token:
                    detach(token)
            except Exception:
                pass
        
        for st in self._manager_stack:
            try:
                span, token = st
                if span:
                    span.end()
                if token:
                    detach(token)
            except Exception:
                pass
        
        for stack in self._delegation_stacks.values():
            for st in stack:
                try:
                    span, token = st
                    if span:
                        span.end()
                    if token:
                        detach(token)
                except Exception:
                    pass
        
        for stack in self._action_stacks.values():
            for st in stack:
                try:
                    span, token = st
                    if span:
                        span.end()
                    if token:
                        detach(token)
                except Exception:
                    pass
        
        for stack in self._multi_step_stacks.values():
            for st in stack:
                try:
                    span, token = st
                    if span:
                        span.end()
                    if token:
                        detach(token)
                except Exception:
                    pass
        
        # Clear all stacks
        self._agent_stack.clear()
        self._manager_stack.clear()
        self._delegation_stacks.clear()
        self._action_stacks.clear()
        self._multi_step_stacks.clear()

    def handle_event(self, event_name: str, data: Dict[str, Any]) -> None:
        # Clear stacks at start of each request to ensure fresh traces
        if event_name == "request_start":
            self.clear_stacks()
            return
        
        attributes = _sanitize_for_json(data or {})

        # Helper functions for start/end of long‑lived spans
        def _start_span(name: str, role: Optional[str] = None, actor_name: Optional[str] = None) -> tuple[Any, Any]:
            span = self._tracer.start_span(name)
            # attach span to current context to make children inherit it
            ctx = trace.set_span_in_context(span) if trace is not None else None  # type: ignore
            if ctx is not None and set_baggage is not None:
                try:
                    if role:
                        ctx = set_baggage("actor.role", role, context=ctx)  # type: ignore
                    if actor_name:
                        ctx = set_baggage("actor.name", actor_name, context=ctx)  # type: ignore
                except Exception:
                    pass
            token = attach(ctx) if ctx is not None else None  # type: ignore
            # store initial attributes on start
            try:
                span.set_attribute("agent.event_name", name)
                if attributes and not self._disable_payloads:
                    # Compact JSON payload
                    payload_compact = json.dumps(attributes)
                    span.set_attribute("agent.payload_json", _truncate_str(payload_compact))
                    # Pretty payload for readability
                    if self._pretty_json:
                        try:
                            payload_pretty = json.dumps(attributes, indent=2, ensure_ascii=False)
                            span.set_attribute("agent.payload.pretty", _truncate_str(payload_pretty))
                        except Exception:
                            pass
            except Exception:
                pass
            return span, token

        def _end_span(span_token: tuple[Any, Any] | None) -> None:
            if not span_token:
                return
            span, token = span_token
            try:
                if span is not None:
                    span.end()
            finally:
                if token is not None:
                    try:
                        detach(token)
                    except Exception:
                        pass

        # Route by event to build hierarchy
        if event_name == "agent_start":
            agent_name = str(attributes.get("agent_name", "agent"))
            st = _start_span(f"agent:{agent_name}", role="agent", actor_name=agent_name)
            self._agent_stack.append(st)
        elif event_name == "agent_end":
            st = self._agent_stack.pop() if self._agent_stack else None
            # Add agent result to span attributes before closing
            try:
                if st and not self._disable_payloads:
                    span, _ = st
                    agent_name = str(attributes.get("agent_name", "agent"))
                    span.set_attribute("agent.name", agent_name)  # type: ignore[attr-defined]
                    
                    # Always add result if available
                    result = attributes.get("result")
                    if result is not None:
                        _res_obj = _sanitize_for_json({"result": result})
                        # Always add result summary
                        try:
                            if isinstance(result, dict):
                                result_summary = str(result.get("human_readable_summary") or 
                                                    result.get("summary") or 
                                                    result.get("message") or
                                                    str(result)[:200])
                            else:
                                result_summary = str(result)[:200]
                            span.set_attribute("agent.result_summary", _truncate_str(result_summary))  # type: ignore[attr-defined]
                        except Exception:
                            pass
                        # Compact JSON (optional)
                        if self._compact_json:
                            try:
                                span.set_attribute("agent.result_json", _truncate_str(json.dumps(_res_obj)))  # type: ignore[attr-defined]
                            except Exception:
                                pass
                        # Pretty for humans (optional)
                        if self._pretty_json:
                            try:
                                _pretty = json.dumps(_res_obj, indent=2, ensure_ascii=False)
                                span.set_attribute("agent.result.pretty", _truncate_str(_pretty))  # type: ignore[attr-defined]
                            except Exception:
                                pass
                    
                    # Also add operation and payload if available
                    if attributes.get("operation"):
                        span.set_attribute("agent.operation", str(attributes.get("operation")))  # type: ignore[attr-defined]
                    if attributes.get("summary"):
                        span.set_attribute("agent.summary", _truncate_str(str(attributes.get("summary"))))  # type: ignore[attr-defined]
            except Exception as e:
                # Log but don't fail - observability should be non-blocking
                try:
                    import logging
                    logging.debug(f"Phoenix subscriber error in agent_end: {e}")
                except:
                    pass
            _end_span(st)
        elif event_name == "manager_start":
            manager_name = str(attributes.get("manager_name", "manager"))
            st = _start_span(f"manager:{manager_name}", role="manager", actor_name=manager_name)
            self._manager_stack.append(st)
        elif event_name == "manager_end":
            st = self._manager_stack.pop() if self._manager_stack else None
            # Add manager result to span attributes before closing
            try:
                if st and attributes.get("result") is not None and not self._disable_payloads:
                    span, _ = st
                    _res_obj = _sanitize_for_json({"result": attributes.get("result")})
                    # Always add result summary
                    try:
                        result_summary = str(attributes.get("result", {}).get("human_readable_summary") or 
                                            attributes.get("result", {}).get("summary") or 
                                            str(attributes.get("result"))[:200])
                        span.set_attribute("manager.result_summary", _truncate_str(result_summary))  # type: ignore[attr-defined]
                    except Exception:
                        pass
                    # Compact JSON (optional)
                    if self._compact_json:
                        try:
                            span.set_attribute("manager.result_json", _truncate_str(json.dumps(_res_obj)))  # type: ignore[attr-defined]
                        except Exception:
                            pass
                    # Pretty for humans (optional)
                    if self._pretty_json:
                        try:
                            _pretty = json.dumps(_res_obj, indent=2, ensure_ascii=False)
                            span.set_attribute("manager.result.pretty", _truncate_str(_pretty))  # type: ignore[attr-defined]
                        except Exception:
                            pass
            except Exception:
                pass
            _end_span(st)
        elif event_name == "delegation_chosen":
            worker = str(attributes.get("worker", "worker"))
            worker_agent_name = str(attributes.get("worker_agent_name", worker))
            st = _start_span(f"delegation:{worker}", role="agent", actor_name=worker_agent_name)
            try:
                span, _ = st
                span.set_attribute("worker.name", worker)  # type: ignore[attr-defined]
                if worker_agent_name:
                    span.set_attribute("worker.agent_name", worker_agent_name)  # type: ignore[attr-defined]
            except Exception:
                pass
            self._delegation_stacks[worker].append(st)
        elif event_name == "delegation_executed":
            worker = str(attributes.get("worker", "worker"))
            stack = self._delegation_stacks.get(worker, [])
            st = stack.pop() if stack else None
            # Add delegation result to span attributes before closing
            try:
                if st and attributes.get("result") is not None and not self._disable_payloads:
                    span, _ = st
                    _res_obj = _sanitize_for_json({"result": attributes.get("result")})
                    # Always add result summary
                    try:
                        result_summary = str(attributes.get("result", {}).get("human_readable_summary") or 
                                            attributes.get("result", {}).get("summary") or 
                                            str(attributes.get("result"))[:200])
                        span.set_attribute("delegation.result_summary", _truncate_str(result_summary))  # type: ignore[attr-defined]
                    except Exception:
                        pass
                    # Compact JSON (optional)
                    if self._compact_json:
                        try:
                            span.set_attribute("delegation.result_json", _truncate_str(json.dumps(_res_obj)))  # type: ignore[attr-defined]
                        except Exception:
                            pass
                    # Pretty for humans (optional)
                    if self._pretty_json:
                        try:
                            _pretty = json.dumps(_res_obj, indent=2, ensure_ascii=False)
                            span.set_attribute("delegation.result.pretty", _truncate_str(_pretty))  # type: ignore[attr-defined]
                        except Exception:
                            pass
            except Exception:
                pass
            _end_span(st)
        elif event_name == "action_planned":
            tool = str(attributes.get("tool_name") or attributes.get("tool") or "tool")
            st = _start_span(f"action:{tool}")
            # Attach tool args on the action span for visibility
            try:
                span, _ = st
                span.set_attribute("tool.name", tool)  # type: ignore[attr-defined]
                if ("args" in attributes) and (not self._disable_payloads):
                    _args_obj = _sanitize_for_json(attributes.get("args", {}))
                    # Compact JSON for programmatic parsing (optional)
                    if self._compact_json:
                        try:
                            span.set_attribute("tool.args_json", _truncate_str(json.dumps(_args_obj)))  # type: ignore[attr-defined]
                        except Exception:
                            pass
                    # Pretty JSON for human readability (optional)
                    if self._pretty_json:
                        try:
                            _pretty = json.dumps(_args_obj, indent=2, ensure_ascii=False)
                            span.set_attribute("tool.args.pretty", _truncate_str(_pretty))  # type: ignore[attr-defined]
                        except Exception:
                            pass
            except Exception:
                pass
            self._action_stacks[tool].append(st)
        elif event_name == "action_executed":
            tool = str(attributes.get("tool_name") or attributes.get("tool") or "tool")
            stack = self._action_stacks.get(tool, [])
            st = stack.pop() if stack else None
            # Always record result summary before closing (if not disabled)
            try:
                if st and attributes.get("result") is not None and not self._disable_payloads:
                    span, _ = st
                    _res_obj = _sanitize_for_json({"result": attributes.get("result")})
                    # Always add result summary (even if pretty_json is disabled)
                    try:
                        result_summary = str(attributes.get("result", {}).get("human_readable_summary") or 
                                            attributes.get("result", {}).get("summary") or 
                                            str(attributes.get("result"))[:200])
                        span.set_attribute("tool.result_summary", _truncate_str(result_summary))  # type: ignore[attr-defined]
                    except Exception:
                        pass
                    # Compact JSON (optional)
                    if self._compact_json:
                        try:
                            span.set_attribute("tool.result_json", _truncate_str(json.dumps(_res_obj)))  # type: ignore[attr-defined]
                        except Exception:
                            pass
                    # Pretty for humans (optional)
                    if self._pretty_json:
                        try:
                            _pretty = json.dumps(_res_obj, indent=2, ensure_ascii=False)
                            span.set_attribute("tool.result.pretty", _truncate_str(_pretty))  # type: ignore[attr-defined]
                        except Exception:
                            pass
            except Exception:
                pass
            _end_span(st)
        elif event_name == "multi_step_start":
            step_idx = int(attributes.get("step", 0))
            total_steps = int(attributes.get("total_steps", 0))
            step_action = str(attributes.get("action", "step"))
            step_worker = str(attributes.get("worker", "worker"))
            st = _start_span(f"step_{step_idx}:{step_action}", role="step", actor_name=step_worker)
            try:
                span, _ = st
                span.set_attribute("step.index", step_idx)  # type: ignore[attr-defined]
                span.set_attribute("step.total", total_steps)  # type: ignore[attr-defined]
                span.set_attribute("step.action", step_action)  # type: ignore[attr-defined]
                span.set_attribute("step.worker", step_worker)  # type: ignore[attr-defined]
                if ("context" in attributes) and (not self._disable_payloads):
                    raw_ctx = attributes.get("context")
                    # Always store a truncated string version
                    span.set_attribute("step.context", _truncate_str(str(raw_ctx)))  # type: ignore[attr-defined]
                    # If context looks like JSON and pretty_json enabled, emit a pretty attribute
                    if self._pretty_json:
                        try:
                            if isinstance(raw_ctx, str):
                                parsed = json.loads(raw_ctx)
                            else:
                                parsed = raw_ctx
                            pretty_ctx = json.dumps(parsed, indent=2, ensure_ascii=False)
                            span.set_attribute("step.context.pretty", _truncate_str(pretty_ctx))  # type: ignore[attr-defined]
                        except Exception:
                            pass
            except Exception:
                pass
            self._multi_step_stacks[step_idx].append(st)
        elif event_name in ("multi_step_complete", "multi_step_error"):
            step_idx = int(attributes.get("step", 0))
            stack = self._multi_step_stacks.get(step_idx, [])
            st = stack.pop() if stack else None
            # Record success/error status
            try:
                if st:
                    span, _ = st
                    if event_name == "multi_step_error":
                        span.set_attribute("step.error", True)  # type: ignore[attr-defined]
                        if "error" in attributes:
                            span.set_attribute("step.error_message", _truncate_str(str(attributes.get("error"))))  # type: ignore[attr-defined]
                    else:
                        span.set_attribute("step.success", True)  # type: ignore[attr-defined]
            except Exception:
                pass
            _end_span(st)
        else:
            # Fallback: create a short child span to capture event payload
            with self._tracer.start_as_current_span(event_name) as span:
                try:
                    span.set_attribute("agent.event_name", event_name)
                    if attributes and not self._disable_payloads:
                        # Compact JSON
                        payload_compact = json.dumps(attributes)
                        span.set_attribute("agent.payload_json", _truncate_str(payload_compact))
                        # Pretty for readability
                        if self._pretty_json:
                            try:
                                payload_pretty = json.dumps(attributes, indent=2, ensure_ascii=False)
                                span.set_attribute("agent.payload.pretty", _truncate_str(payload_pretty))
                            except Exception:
                                pass
                except Exception:
                    pass

        if self._flush_each_event:
            try:
                self._provider.force_flush()
            except Exception as exc:  # pragma: no cover - defensive logging
                print(f"[PhoenixSubscriber] force_flush failed for '{event_name}': {exc}")
