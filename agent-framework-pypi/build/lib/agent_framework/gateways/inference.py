from __future__ import annotations

from typing import Dict, List, Union, Optional, Any
import os
import json
import time
import requests
from contextlib import nullcontext
try:  # Optional OpenTelemetry for tracing LLM calls
    from opentelemetry import trace  # type: ignore
    try:
        from opentelemetry.baggage import get_baggage  # type: ignore
    except Exception:  # pragma: no cover - optional
        get_baggage = None  # type: ignore
except Exception:  # pragma: no cover - optional
    trace = None  # type: ignore
    get_baggage = None  # type: ignore

from ..base import BaseInferenceGateway

_UNSET = object()


class MockInferenceGateway(BaseInferenceGateway):
    def invoke(self, prompt: Union[str, List[Dict]]) -> str:
        return "[MockInference] This is a plausible LLM response based on the prompt."


class OpenAIGateway(BaseInferenceGateway):
    """Minimal OpenAI Chat Completions gateway.

    Config (set via registry/factory):
      - model: str (e.g., "gpt-4o-mini" or "gpt-4-turbo")
      - api_key: optional (falls back to env OPENAI_API_KEY)
      - base_url: optional override (falls back to https://api.openai.com)
      - temperature: optional float
      - use_function_calling: optional bool (default False for backward compatibility)
    """

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: Optional[float] = _UNSET,
        use_function_calling: Optional[bool] = None,
        tool_choice: Optional[str] = None,
    ) -> None:
        self.model = model
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        if not self.api_key:
            raise RuntimeError("OpenAIGateway requires OPENAI_API_KEY or api_key in config")
        self.base_url = (base_url or os.getenv("OPENAI_BASE_URL") or "https://api.openai.com").rstrip("/")
        if temperature is _UNSET:
            self.temperature: Optional[float] = 0.0
        else:
            self.temperature = temperature
        self.use_function_calling = use_function_calling if use_function_calling is not None else False
        # tool_choice: "auto" (default), "required", or an object targeting a specific function
        self.tool_choice = (tool_choice or os.getenv("OPENAI_TOOL_CHOICE") or "auto")

    def invoke(
        self, 
        prompt: Union[str, List[Dict]], 
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> Union[str, Dict[str, Any]]:
        """Invoke OpenAI API with optional function calling support.
        
        Args:
            prompt: String or message list
            tools: Optional OpenAI tools schema (for function calling mode)
        
        Returns:
            - If function calling and tools provided: Dict with tool_calls or content
            - Otherwise: String response
        """
        url = f"{self.base_url}/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if isinstance(prompt, str):
            messages = [{"role": "user", "content": prompt}]
        else:
            messages = prompt
        
        payload = {
            "model": self.model,
            "messages": messages,
        }
        if self.temperature is not None:
            payload["temperature"] = self.temperature
        
        # Add tools if provided and function calling is enabled
        if self.use_function_calling and tools:
            payload["tools"] = tools
            # Let caller require tool calls if configured
            payload["tool_choice"] = self.tool_choice
        
        tracer = trace.get_tracer("agent-framework.llm") if trace is not None else None
        if tracer is not None:
            span_title = "llm.openai.chat_completions"
            try:
                actor_nm = get_baggage("actor.name") if get_baggage is not None else None  # type: ignore
                if actor_nm:
                    span_title = f"{span_title} ({actor_nm})"
            except Exception:
                pass
            with tracer.start_as_current_span(span_title) as span:  # type: ignore
                try:
                    # Emission controls to avoid redundant attributes
                    try:
                        _mode = os.getenv("PHOENIX_ATTR_MODE", "semantic").lower()
                    except Exception:
                        _mode = "semantic"
                    emit_semantic = _mode in {"semantic", "both"}
                    emit_legacy = _mode in {"legacy", "both"}
                    try:
                        emit_compact = os.getenv("PHOENIX_COMPACT_JSON", "false").lower() in {"1", "true", "yes"}
                    except Exception:
                        emit_compact = False
                    try:
                        emit_actor_in_llm = os.getenv("PHOENIX_EMIT_ACTOR_IN_LLM", "false").lower() in {"1", "true", "yes"}
                    except Exception:
                        emit_actor_in_llm = False

                    # Legacy llm.* attributes (optional)
                    if emit_legacy:
                        span.set_attribute("llm.provider", "openai")  # type: ignore[attr-defined]
                        span.set_attribute("llm.model", self.model)  # type: ignore[attr-defined]
                        span.set_attribute("llm.base_url", self.base_url)  # type: ignore[attr-defined]
                        if self.temperature is not None:
                            span.set_attribute("llm.temperature", float(self.temperature))  # type: ignore[attr-defined]
                        span.set_attribute("llm.use_function_calling", bool(self.use_function_calling))  # type: ignore[attr-defined]
                        span.set_attribute("llm.messages.count", len(messages))  # type: ignore[attr-defined]
                    # GenAI semantic-style attributes (preferred)
                    if emit_semantic:
                        span.set_attribute("gen_ai.system", "openai")  # type: ignore[attr-defined]
                        span.set_attribute("gen_ai.operation.name", "chat.completions")  # type: ignore[attr-defined]
                        span.set_attribute("gen_ai.request.model", self.model)  # type: ignore[attr-defined]
                        if self.temperature is not None:
                            span.set_attribute("gen_ai.request.temperature", float(self.temperature))  # type: ignore[attr-defined]
                        if tools:
                            span.set_attribute("gen_ai.request.tools.count", len(tools))  # type: ignore[attr-defined]
                    # Attach actor context when available
                    try:
                        actor_role = get_baggage("actor.role") if get_baggage is not None else None  # type: ignore
                        actor_name = get_baggage("actor.name") if get_baggage is not None else None  # type: ignore
                        if emit_actor_in_llm:
                            if actor_role:
                                span.set_attribute("actor.role", actor_role)  # type: ignore[attr-defined]
                            if actor_name:
                                span.set_attribute("actor.name", actor_name)  # type: ignore[attr-defined]
                        if emit_semantic:
                            if actor_role:
                                span.set_attribute("gen_ai.actor.role", actor_role)  # type: ignore[attr-defined]
                            if actor_name:
                                span.set_attribute("gen_ai.actor.name", actor_name)  # type: ignore[attr-defined]
                    except Exception:
                        pass
                    # Optionally capture prompt and tools
                    try:
                        max_chars = int(os.getenv("PHOENIX_MAX_ATTR_CHARS", "4000"))
                    except Exception:
                        max_chars = 4000
                    capture_bodies = os.getenv("PHOENIX_CAPTURE_LLM_BODIES", "true").lower() in {"1", "true", "yes"}
                    try:
                        emit_body_events = os.getenv("PHOENIX_BODY_EVENTS", "true").lower() in {"1", "true", "yes"}
                    except Exception:
                        emit_body_events = True
                    if capture_bodies:
                        try:
                            if isinstance(prompt, str):
                                prompt_text = prompt
                            else:
                                # Flatten messages to a readable transcript
                                parts = []
                                for m in messages:
                                    role = m.get("role", "")
                                    content = m.get("content", "")
                                    parts.append(f"{role}: {content}")
                                prompt_text = "\n".join(parts)
                            if prompt_text:
                                prompt_out = (prompt_text[:max_chars] + "...(truncated)") if len(prompt_text) > max_chars else prompt_text
                                if emit_legacy:
                                    span.set_attribute("llm.prompt", prompt_out)  # type: ignore[attr-defined]
                                if emit_semantic:
                                    span.set_attribute("gen_ai.prompt", prompt_out)  # type: ignore[attr-defined]
                                if emit_body_events:
                                    try:
                                        span.add_event("prompt", {"prompt.text": prompt_out})
                                    except Exception:
                                        pass
                        except Exception:
                            pass
                        if self.use_function_calling and tools:
                            try:
                                # Compact for machine use (optional)
                                if os.getenv("PHOENIX_COMPACT_JSON", "false").lower() in {"1", "true", "yes"}:
                                    compact_tools = json.dumps(tools)
                                    if emit_legacy:
                                        span.set_attribute("llm.tools_schema", compact_tools[:max_chars])  # type: ignore[attr-defined]
                                    if emit_semantic:
                                        span.set_attribute("gen_ai.request.tools.schema", compact_tools[:max_chars])  # type: ignore[attr-defined]
                                else:
                                    compact_tools = None  # type: ignore[assignment]
                            except Exception:
                                compact_tools = None  # type: ignore[assignment]
                            # Pretty for humans (optional) — also disabled when PHOENIX_DISABLE_PAYLOADS is true
                            try:
                                disable_payloads = os.getenv("PHOENIX_DISABLE_PAYLOADS", "false").lower() in {"1", "true", "yes"}
                                pretty_json = os.getenv("PHOENIX_PRETTY_JSON", "false").lower() in {"1", "true", "yes"}
                            except Exception:
                                disable_payloads = False
                                pretty_json = False
                            if pretty_json and not disable_payloads:
                                try:
                                    pretty_tools = json.dumps(tools, indent=2, ensure_ascii=False)
                                    if emit_semantic:
                                        span.set_attribute("gen_ai.request.tools.schema.pretty", pretty_tools[:max_chars])  # type: ignore[attr-defined]
                                    if emit_legacy:
                                        span.set_attribute("llm.tools_schema.pretty", pretty_tools[:max_chars])  # type: ignore[attr-defined]
                                    if emit_body_events:
                                        try:
                                            span.add_event("tools_schema", {"schema.pretty": pretty_tools[:max_chars]})
                                        except Exception:
                                            pass
                                except Exception:
                                    pass
                except Exception:
                    pass
                _t0 = time.perf_counter()
                resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=60)
                _t1 = time.perf_counter()
                try:
                    resp.raise_for_status()
                except requests.exceptions.HTTPError as e:
                    try:
                        span.set_attribute("error", True)  # type: ignore[attr-defined]
                        span.set_attribute("http.status_code", resp.status_code)  # type: ignore[attr-defined]
                        # keep response_text only on error
                        span.set_attribute("http.response_text", resp.text[:2000])  # type: ignore[attr-defined]
                        # semantic copy if enabled
                        if 'emit_semantic' in locals() and emit_semantic:
                            span.set_attribute("gen_ai.http.status_code", resp.status_code)  # type: ignore[attr-defined]
                    except Exception:
                        pass
                    # Log the error response for debugging
                    print(f"OpenAI API Error: {e}")
                    print(f"Response: {resp.text}")
                    print(f"Payload sent: {json.dumps(payload, indent=2)}")
                    raise
                data = resp.json()
                # Annotate response meta
                try:
                    # HTTP and latency
                    span.set_attribute("http.status_code", resp.status_code)  # type: ignore[attr-defined]
                    latency_ms = int((_t1 - _t0) * 1000)
                    if 'emit_legacy' in locals() and emit_legacy:
                        span.set_attribute("llm.latency_ms", latency_ms)  # type: ignore[attr-defined]
                    if 'emit_semantic' in locals() and emit_semantic:
                        span.set_attribute("gen_ai.latency_ms", latency_ms)  # type: ignore[attr-defined]
                    choice0 = data.get("choices", [{}])[0]  # type: ignore[index]
                    finish_reason = choice0.get("finish_reason")
                    if 'emit_legacy' in locals() and emit_legacy:
                        span.set_attribute("llm.finish_reason", str(finish_reason))  # type: ignore[attr-defined]
                    if 'emit_semantic' in locals() and emit_semantic:
                        span.set_attribute("gen_ai.response.finish_reason", str(finish_reason))  # type: ignore[attr-defined]
                    msg = choice0.get("message", {})
                    tool_calls = msg.get("tool_calls") if isinstance(msg, dict) else None
                    if tool_calls is not None:
                        if 'emit_legacy' in locals() and emit_legacy:
                            span.set_attribute("llm.tool_calls.count", len(tool_calls))  # type: ignore[attr-defined]
                        if 'emit_semantic' in locals() and emit_semantic:
                            span.set_attribute("gen_ai.response.tool_calls.count", len(tool_calls))  # type: ignore[attr-defined]
                        # Optional: pretty/clean representation and per-call events for readability
                        try:
                            # Config flags
                            pretty_json = os.getenv("PHOENIX_PRETTY_JSON", "true").lower() in {"1", "true", "yes"}
                            emit_events = os.getenv("PHOENIX_TOOL_CALL_EVENTS", "true").lower() in {"1", "true", "yes"}

                            def _truncate(s: str, n: int) -> str:
                                return (s[:n] + "...(truncated)") if len(s) > n else s

                            # Build a cleaned copy where function.arguments is parsed JSON (object), not a string
                            cleaned_calls = []
                            for tc in tool_calls:
                                try:
                                    if isinstance(tc, dict):
                                        c = dict(tc)
                                        func = c.get("function")
                                        if isinstance(func, dict) and isinstance(func.get("arguments"), str):
                                            try:
                                                func_args_obj = json.loads(func["arguments"])  # type: ignore[index]
                                            except Exception:
                                                func_args_obj = func["arguments"]
                                            # replace with parsed object for readability
                                            func = dict(func)
                                            func["arguments"] = func_args_obj
                                            c["function"] = func
                                        cleaned_calls.append(c)
                                except Exception:
                                    pass

                            if pretty_json:
                                try:
                                    pretty = json.dumps(cleaned_calls or tool_calls, indent=2, ensure_ascii=False)
                                except Exception:
                                    pretty = json.dumps(tool_calls)
                                if 'emit_semantic' in locals() and emit_semantic:
                                    span.set_attribute("gen_ai.response.tool_calls.pretty", _truncate(pretty, max_chars))  # type: ignore[attr-defined]
                                if 'emit_legacy' in locals() and emit_legacy:
                                    span.set_attribute("llm.tool_calls.pretty", _truncate(pretty, max_chars))  # type: ignore[attr-defined]
                            # Also keep compact JSON for downstream parsing if needed
                            if 'emit_compact' in locals() and emit_compact:
                                try:
                                    compact = json.dumps(cleaned_calls or tool_calls)
                                    if emit_semantic:
                                        span.set_attribute("gen_ai.response.tool_calls.json", _truncate(compact, max_chars))  # type: ignore[attr-defined]
                                    if emit_legacy:
                                        span.set_attribute("llm.tool_calls.json", _truncate(compact, max_chars))  # type: ignore[attr-defined]
                                except Exception:
                                    pass

                            # Emit one event per tool call for easier reading in UIs
                            if emit_events:
                                for tc in cleaned_calls or tool_calls:
                                    try:
                                        tc_id = (tc.get("id") if isinstance(tc, dict) else None) or ""
                                        func = tc.get("function") if isinstance(tc, dict) else None
                                        fname = func.get("name") if isinstance(func, dict) else None
                                        fargs = func.get("arguments") if isinstance(func, dict) else None
                                        # Ensure arguments is a readable string
                                        if not isinstance(fargs, str):
                                            try:
                                                fargs = json.dumps(fargs, indent=2, ensure_ascii=False)
                                            except Exception:
                                                fargs = str(fargs)
                                        fargs = _truncate(str(fargs), max_chars)
                                        span.add_event(
                                            "tool_call",
                                            {
                                                "tool_call.id": str(tc_id),
                                                "tool_call.function.name": str(fname or ""),
                                                "tool_call.function.arguments": fargs,
                                            },
                                        )
                                    except Exception:
                                        pass
                        except Exception:
                            pass
                    # token usage if provided
                    usage = data.get("usage", {})
                    if isinstance(usage, dict):
                        pt = usage.get("prompt_tokens")
                        ct = usage.get("completion_tokens")
                        tt = usage.get("total_tokens")
                        if pt is not None:
                            if 'emit_legacy' in locals() and emit_legacy:
                                span.set_attribute("llm.usage.prompt_tokens", int(pt))  # type: ignore[attr-defined]
                            if 'emit_semantic' in locals() and emit_semantic:
                                span.set_attribute("gen_ai.usage.input_tokens", int(pt))  # type: ignore[attr-defined]
                        if ct is not None:
                            if 'emit_legacy' in locals() and emit_legacy:
                                span.set_attribute("llm.usage.completion_tokens", int(ct))  # type: ignore[attr-defined]
                            if 'emit_semantic' in locals() and emit_semantic:
                                span.set_attribute("gen_ai.usage.output_tokens", int(ct))  # type: ignore[attr-defined]
                        if tt is not None:
                            if 'emit_legacy' in locals() and emit_legacy:
                                span.set_attribute("llm.usage.total_tokens", int(tt))  # type: ignore[attr-defined]
                            if 'emit_semantic' in locals() and emit_semantic:
                                span.set_attribute("gen_ai.usage.total_tokens", int(tt))  # type: ignore[attr-defined]
                        # Pricing calculation (env-configurable)
                        try:
                            input_price, output_price, source = _resolve_pricing("openai", self.model)
                            if 'emit_semantic' in locals() and emit_semantic:
                                span.set_attribute("gen_ai.cost.input_usd_per_1k", float(input_price))  # type: ignore[attr-defined]
                                span.set_attribute("gen_ai.cost.output_usd_per_1k", float(output_price))  # type: ignore[attr-defined]
                                span.set_attribute("gen_ai.cost.pricing_source", source)  # type: ignore[attr-defined]
                            cost_in = (float(pt or 0) / 1000.0) * float(input_price)
                            cost_out = (float(ct or 0) / 1000.0) * float(output_price)
                            if 'emit_semantic' in locals() and emit_semantic:
                                span.set_attribute("gen_ai.cost.input_usd", cost_in)  # type: ignore[attr-defined]
                                span.set_attribute("gen_ai.cost.output_usd", cost_out)  # type: ignore[attr-defined]
                                span.set_attribute("gen_ai.cost.total_usd", cost_in + cost_out)  # type: ignore[attr-defined]
                        except Exception:
                            pass
                    # Capture response content
                    if capture_bodies:
                        try:
                            content = msg.get("content") if isinstance(msg, dict) else None
                            if content:
                                out = (content[:max_chars] + "...(truncated)") if len(content) > max_chars else content
                                if 'emit_legacy' in locals() and emit_legacy:
                                    span.set_attribute("llm.response", out)  # type: ignore[attr-defined]
                                if 'emit_semantic' in locals() and emit_semantic:
                                    span.set_attribute("gen_ai.response.output_text", out)  # type: ignore[attr-defined]
                                if emit_body_events:
                                    try:
                                        span.add_event("response", {"response.text": out})
                                    except Exception:
                                        pass
                            if tool_calls and ('emit_legacy' in locals() and emit_legacy) and (os.getenv("PHOENIX_COMPACT_JSON", "false").lower() in {"1", "true", "yes"}):
                                try:
                                    # Preserve legacy attribute with compact JSON (optional)
                                    span.set_attribute("llm.tool_calls.json", json.dumps(tool_calls)[:max_chars])  # type: ignore[attr-defined]
                                except Exception:
                                    pass
                        except Exception:
                            pass
                except Exception:
                    pass
        else:
            resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=60)
            try:
                resp.raise_for_status()
            except requests.exceptions.HTTPError as e:
                # Log the error response for debugging
                print(f"OpenAI API Error: {e}")
                print(f"Response: {resp.text}")
                print(f"Payload sent: {json.dumps(payload, indent=2)}")
                raise
            data = resp.json()
        
        try:
            message = data["choices"][0]["message"]
            
            # Function calling mode: return structured response
            if self.use_function_calling and tools:
                return {
                    "content": message.get("content"),
                    "tool_calls": message.get("tool_calls"),
                    "finish_reason": data["choices"][0].get("finish_reason")
                }
            
            # Text-based mode: return content string
            return message.get("content", "")
        except Exception:
            return json.dumps(data)


class GoogleAIGateway(BaseInferenceGateway):
    """Google Generative AI (Gemini) gateway."""

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: Optional[float] = _UNSET,
        generation_config: Optional[Dict[str, Any]] = None,
        safety_settings: Optional[List[Dict[str, Any]]] = None,
        timeout: Optional[int] = None,
        use_function_calling: Optional[bool] = None,  # parity with OpenAI configs; not currently wired
        tool_choice: Optional[str] = None,
    ) -> None:
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY", "")
        if not self.api_key:
            raise RuntimeError("GoogleAIGateway requires GOOGLE_API_KEY or api_key in config")
        default_model = os.getenv("GOOGLE_MODEL") or "models/gemini-1.5-flash"
        self.model = model or default_model
        self.base_url = (base_url or os.getenv("GOOGLE_API_BASE_URL") or "https://generativelanguage.googleapis.com").rstrip("/")
        if temperature is _UNSET:
            self.temperature: Optional[float] = None
        else:
            self.temperature = temperature
        self.generation_config = (generation_config or {}).copy()
        if self.temperature is not None:
            self.generation_config.setdefault("temperature", self.temperature)
        self.safety_settings = safety_settings
        self.use_function_calling = use_function_calling if use_function_calling is not None else False
        self.tool_choice = tool_choice or "auto"
        try:
            env_timeout = int(os.getenv("GOOGLE_API_TIMEOUT", "60"))
        except Exception:
            env_timeout = 60
        self.timeout = timeout or env_timeout

    def _convert_content_to_parts(self, content: Any) -> List[Dict[str, str]]:
        parts: List[Dict[str, str]] = []
        if content is None:
            return parts
        if isinstance(content, str):
            if content:
                parts.append({"text": content})
            return parts
        if isinstance(content, list):
            for item in content:
                if isinstance(item, str):
                    if item:
                        parts.append({"text": item})
                elif isinstance(item, dict):
                    text = item.get("text") or item.get("content") or item.get("value")
                    if text:
                        parts.append({"text": str(text)})
                else:
                    parts.append({"text": str(item)})
            return parts
        if isinstance(content, dict):
            text = content.get("text") or content.get("content") or content.get("value")
            if text:
                parts.append({"text": str(text)})
            return parts
        parts.append({"text": str(content)})
        return parts

    def _build_google_messages(
        self, prompt: Union[str, List[Dict[str, Any]]]
    ) -> tuple[List[Dict[str, Any]], Optional[Dict[str, Any]], str]:
        system_chunks: List[str] = []
        contents: List[Dict[str, Any]] = []
        if isinstance(prompt, str):
            contents.append({"role": "user", "parts": [{"text": prompt}]})
            prompt_preview = prompt
        else:
            preview_lines: List[str] = []
            for message in prompt:
                if not isinstance(message, dict):
                    continue
                role = message.get("role", "user")
                parts = self._convert_content_to_parts(message.get("content"))
                if not parts:
                    continue
                snippet = " ".join(part.get("text", "") for part in parts).strip()
                if snippet:
                    preview_lines.append(f"{role}: {snippet}")
                if role == "system":
                    system_chunks.append(snippet)
                    continue
                google_role = "model" if role == "assistant" else "user"
                contents.append({"role": google_role, "parts": parts})
            prompt_preview = "\n".join(preview_lines)
        system_instruction = None
        if system_chunks:
            system_instruction = {
                "role": "system",
                "parts": [{"text": "\n\n".join(chunk for chunk in system_chunks if chunk)}],
            }
        return contents, system_instruction, prompt_preview

    def _extract_text_from_response(self, data: Dict[str, Any]) -> str:
        candidates = data.get("candidates")
        if not isinstance(candidates, list) or not candidates:
            return json.dumps(data)
        content = candidates[0].get("content", {})
        parts = content.get("parts", [])
        if not isinstance(parts, list):
            return json.dumps(data)
        texts: List[str] = []
        for part in parts:
            if isinstance(part, dict):
                text = part.get("text")
                if text:
                    texts.append(str(text))
        return "\n".join(texts) if texts else json.dumps(data)

    def invoke(
        self,
        prompt: Union[str, List[Dict[str, Any]]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        del tools  # Google Generative AI support for structured tool schemas TBD
        contents, system_instruction, prompt_preview = self._build_google_messages(prompt)
        payload: Dict[str, Any] = {"contents": contents}
        if system_instruction:
            payload["system_instruction"] = system_instruction
        if self.generation_config:
            payload["generationConfig"] = self.generation_config
        if self.safety_settings:
            payload["safetySettings"] = self.safety_settings

        headers = {"Content-Type": "application/json"}
        url = f"{self.base_url}/v1beta/models/{self.model}:generateContent?key={self.api_key}"

        tracer = trace.get_tracer("agent-framework.llm") if trace is not None else None
        span_cm = tracer.start_as_current_span("llm.google.generateContent") if tracer else nullcontext()
        with span_cm as span:  # type: ignore
            try:
                try:
                    attr_mode = os.getenv("PHOENIX_ATTR_MODE", "semantic").lower()
                except Exception:
                    attr_mode = "semantic"
                emit_semantic = attr_mode in {"semantic", "both"}
                emit_legacy = attr_mode in {"legacy", "both"}
                if span:
                    if emit_legacy:
                        span.set_attribute("llm.provider", "google")  # type: ignore[attr-defined]
                        span.set_attribute("llm.model", self.model)  # type: ignore[attr-defined]
                    if emit_semantic:
                        span.set_attribute("gen_ai.system", "google")  # type: ignore[attr-defined]
                        span.set_attribute("gen_ai.operation.name", "generateContent")  # type: ignore[attr-defined]
                        span.set_attribute("gen_ai.request.model", self.model)  # type: ignore[attr-defined]
                        if self.temperature is not None:
                            span.set_attribute("gen_ai.request.temperature", float(self.temperature))  # type: ignore[attr-defined]
                    try:
                        max_chars = int(os.getenv("PHOENIX_MAX_ATTR_CHARS", "4000"))
                    except Exception:
                        max_chars = 4000
                    prompt_out = (
                        (prompt_preview[:max_chars] + "...(truncated)")
                        if prompt_preview and len(prompt_preview) > max_chars
                        else prompt_preview
                    )
                    if prompt_out:
                        if emit_legacy:
                            span.set_attribute("llm.prompt", prompt_out)  # type: ignore[attr-defined]
                        if emit_semantic:
                            span.set_attribute("gen_ai.prompt", prompt_out)  # type: ignore[attr-defined]
                resp = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
                resp.raise_for_status()
                data = resp.json()
                if span:
                    span.set_attribute("http.status_code", resp.status_code)  # type: ignore[attr-defined]
                    usage = data.get("usageMetadata") or {}
                    prompt_tokens = usage.get("promptTokenCount")
                    completion_tokens = usage.get("candidatesTokenCount")
                    total_tokens = usage.get("totalTokenCount")
                    if prompt_tokens is not None:
                        if emit_legacy:
                            span.set_attribute("llm.usage.prompt_tokens", int(prompt_tokens))  # type: ignore[attr-defined]
                        if emit_semantic:
                            span.set_attribute("gen_ai.usage.input_tokens", int(prompt_tokens))  # type: ignore[attr-defined]
                    if completion_tokens is not None:
                        if emit_legacy:
                            span.set_attribute("llm.usage.completion_tokens", int(completion_tokens))  # type: ignore[attr-defined]
                        if emit_semantic:
                            span.set_attribute("gen_ai.usage.output_tokens", int(completion_tokens))  # type: ignore[attr-defined]
                    if total_tokens is not None:
                        if emit_legacy:
                            span.set_attribute("llm.usage.total_tokens", int(total_tokens))  # type: ignore[attr-defined]
                        if emit_semantic:
                            span.set_attribute("gen_ai.usage.total_tokens", int(total_tokens))  # type: ignore[attr-defined]
                    if emit_semantic:
                        try:
                            input_price, output_price, source = _resolve_pricing("google", self.model)
                            span.set_attribute("gen_ai.cost.input_usd_per_1k", float(input_price))  # type: ignore[attr-defined]
                            span.set_attribute("gen_ai.cost.output_usd_per_1k", float(output_price))  # type: ignore[attr-defined]
                            span.set_attribute("gen_ai.cost.pricing_source", source)  # type: ignore[attr-defined]
                            cost_in = (float(prompt_tokens or 0) / 1000.0) * float(input_price)
                            cost_out = (float(completion_tokens or 0) / 1000.0) * float(output_price)
                            span.set_attribute("gen_ai.cost.input_usd", cost_in)  # type: ignore[attr-defined]
                            span.set_attribute("gen_ai.cost.output_usd", cost_out)  # type: ignore[attr-defined]
                            span.set_attribute("gen_ai.cost.total_usd", cost_in + cost_out)  # type: ignore[attr-defined]
                        except Exception:
                            pass
                return self._extract_text_from_response(data)
            except requests.exceptions.HTTPError as exc:
                if span:
                    span.set_attribute("error", True)  # type: ignore[attr-defined]
                    if exc.response is not None:
                        span.set_attribute("http.status_code", exc.response.status_code)  # type: ignore[attr-defined]
                        span.set_attribute("http.response_text", exc.response.text[:2000])  # type: ignore[attr-defined]
                print(f"Google Generative AI Error: {exc}")
                if exc.response is not None:
                    print(f"Response: {exc.response.text}")
                print(f"Payload sent: {json.dumps(payload, indent=2)}")
                raise
            except Exception:
                if span:
                    span.set_attribute("error", True)  # type: ignore[attr-defined]
                raise


def _normalize_model_key(model: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in model).upper()


def _resolve_pricing(provider: str, model: str) -> tuple[float, float, str]:
    """Resolve per-1K token pricing from environment.

    Resolution order:
      1) LLM_PRICING_JSON (structure: {"provider": {"model": {"input_per_1k": x, "output_per_1k": y}}} or {"model": {...}})
      2) <PROVIDER>_PRICE_<MODEL>_INPUT_PER_1K / _OUTPUT_PER_1K
      3) LLM_PRICE_DEFAULT_INPUT_PER_1K / LLM_PRICE_DEFAULT_OUTPUT_PER_1K
    Returns (input_price, output_price, source_label)
    """
    # 1) JSON blob
    raw = os.getenv("LLM_PRICING_JSON")
    if raw:
        try:
            data = json.loads(raw)
            # nested: provider -> model
            if isinstance(data, dict):
                prov_map = data.get(provider) if provider in data else None
                if isinstance(prov_map, dict):
                    m = prov_map.get(model) or prov_map.get(_normalize_model_key(model))
                    if isinstance(m, dict):
                        return float(m.get("input_per_1k", 0.0)), float(m.get("output_per_1k", 0.0)), "env.json"
                # flat map by model
                m = data.get(model) or data.get(_normalize_model_key(model))
                if isinstance(m, dict):
                    return float(m.get("input_per_1k", 0.0)), float(m.get("output_per_1k", 0.0)), "env.json"
        except Exception:
            pass
    # 2) Provider/model-specific env vars
    prov = provider.upper()
    mk = _normalize_model_key(model)
    in_var = f"{prov}_PRICE_{mk}_INPUT_PER_1K"
    out_var = f"{prov}_PRICE_{mk}_OUTPUT_PER_1K"
    try:
        in_price = float(os.getenv(in_var)) if os.getenv(in_var) is not None else None
        out_price = float(os.getenv(out_var)) if os.getenv(out_var) is not None else None
        if in_price is not None and out_price is not None:
            return in_price, out_price, "env.vars"
    except Exception:
        pass
    # 3) Defaults
    try:
        default_in = float(os.getenv("LLM_PRICE_DEFAULT_INPUT_PER_1K", "0"))
        default_out = float(os.getenv("LLM_PRICE_DEFAULT_OUTPUT_PER_1K", "0"))
    except Exception:
        default_in = 0.0
        default_out = 0.0
    return default_in, default_out, "default"
