# Recipe: Custom Inference Gateway

Create a gateway for a new LLM provider.

## Goal

Add support for a custom or self-hosted LLM.

## Implementation

```python
from agent_framework import BaseInferenceGateway
from typing import Union, List, Dict, Any
import httpx

class OllamaGateway(BaseInferenceGateway):
    """Gateway for Ollama local LLM server."""
    
    def __init__(
        self,
        model: str = "llama2",
        base_url: str = "http://localhost:11434",
        temperature: float = 0.7,
    ):
        self.model = model
        self.base_url = base_url
        self.temperature = temperature
        self.client = httpx.Client(timeout=120.0)
    
    def invoke(
        self,
        prompt: Union[str, List[Dict[str, Any]]]
    ) -> str:
        # Convert messages list to string if needed
        if isinstance(prompt, list):
            prompt_text = self._messages_to_text(prompt)
        else:
            prompt_text = prompt
        
        response = self.client.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt_text,
                "stream": False,
                "options": {
                    "temperature": self.temperature,
                },
            },
        )
        response.raise_for_status()
        
        data = response.json()
        return data.get("response", "")
    
    def _messages_to_text(self, messages: List[Dict[str, Any]]) -> str:
        """Convert OpenAI-style messages to plain text."""
        parts = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            parts.append(f"{role.upper()}: {content}")
        return "\n".join(parts)
```

## With Streaming Support

```python
class OllamaStreamingGateway(BaseInferenceGateway):
    """Ollama gateway with streaming support."""
    
    def __init__(self, model: str = "llama2", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url
    
    def invoke(self, prompt: Union[str, List[Dict[str, Any]]]) -> str:
        prompt_text = self._to_text(prompt)
        
        # Stream and collect
        full_response = []
        with httpx.stream(
            "POST",
            f"{self.base_url}/api/generate",
            json={"model": self.model, "prompt": prompt_text, "stream": True},
            timeout=120.0,
        ) as response:
            for line in response.iter_lines():
                if line:
                    data = json.loads(line)
                    full_response.append(data.get("response", ""))
        
        return "".join(full_response)
    
    def _to_text(self, prompt):
        if isinstance(prompt, str):
            return prompt
        return "\n".join(f"{m['role']}: {m['content']}" for m in prompt)
```

## With Tracing

```python
from opentelemetry import trace

class TracedGateway(BaseInferenceGateway):
    """Gateway with OpenTelemetry tracing."""
    
    def __init__(self, inner: BaseInferenceGateway, service_name: str = "llm"):
        self.inner = inner
        self.tracer = trace.get_tracer(service_name)
    
    def invoke(self, prompt: Union[str, List[Dict[str, Any]]]) -> str:
        with self.tracer.start_as_current_span("llm.invoke") as span:
            span.set_attribute("llm.model", getattr(self.inner, "model", "unknown"))
            
            try:
                result = self.inner.invoke(prompt)
                span.set_attribute("llm.response_length", len(result))
                return result
            except Exception as e:
                span.record_exception(e)
                raise
```

## Registration

```python
from deployment.registry import register_gateway

register_gateway("OllamaGateway", OllamaGateway)
register_gateway("OllamaStreamingGateway", OllamaStreamingGateway)
```

## YAML Usage

```yaml
resources:
  gateways:
    - name: ollama-local
      type: OllamaGateway
      config:
        model: llama2
        base_url: http://localhost:11434
        temperature: 0.7

spec:
  planner:
    type: ReActPlanner
    config:
      inference_gateway: ollama-local
```

## Key Points

- Implement `invoke(prompt) -> str`
- Handle both string and message list formats
- Set appropriate timeouts for LLM calls
- Add tracing for observability
- Register for YAML usage

