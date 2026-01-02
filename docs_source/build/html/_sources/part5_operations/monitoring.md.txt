# Monitoring & Observability

This chapter covers monitoring, tracing, and metrics for production deployments.

## Phoenix Integration

Phoenix provides OpenTelemetry-based tracing:

### Setup

```python
from agent_framework.observability.subscribers import PhoenixSubscriber
from agent_framework import EventBus

event_bus = EventBus()
phoenix = PhoenixSubscriber(
    service_name="my_agent_service",
    endpoint="http://localhost:6006/v1/traces",
)
event_bus.subscribe(phoenix)
```

### Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `PHOENIX_ENDPOINT` | `http://localhost:6006/v1/traces` | Phoenix collector URL |
| `PHOENIX_MAX_ATTR_CHARS` | `4000` | Max attribute size |
| `PHOENIX_CAPTURE_LLM_BODIES` | `true` | Include prompts/responses |
| `PHOENIX_PRETTY_JSON` | `false` | Pretty-print JSON |
| `PHOENIX_COMPACT_JSON` | `true` | Compact JSON |

### Span Hierarchy

```
root_request (API endpoint)
└── manager:orchestrator
    ├── delegation:analysis_manager
    │   └── agent:analyzer
    │       ├── action:list_tables
    │       │   └── tool.list_tables
    │       └── llm.openai.chat_completions
    └── delegation:design_manager
        └── agent:designer
            └── ...
```

### Attributes Captured

**LLM Spans**:
- `gen_ai.system`: Provider (openai, google)
- `gen_ai.request.model`: Model name
- `gen_ai.usage.input_tokens`: Input tokens
- `gen_ai.usage.output_tokens`: Output tokens
- `gen_ai.cost.total_usd`: Total cost
- `gen_ai.latency_ms`: Latency in milliseconds

**Tool Spans**:
- `tool.name`: Tool identifier
- `tool.latency_ms`: Execution time
- `tool.input.args_json`: Input arguments
- `tool.output.result_summary`: Result summary

## Cost Tracking

Configure token pricing:

```bash
# JSON format (recommended)
LLM_PRICING_JSON='{
  "gpt_4o": {"input": 2.50, "output": 10.00},
  "gpt_4o_mini": {"input": 0.15, "output": 0.60}
}'

# Or per-model environment variables
LLM_PRICING_INPUT_USD_PER_1K=0.15
LLM_PRICING_OUTPUT_USD_PER_1K=0.60
```

## Event Stream

### Default Frontend Events

```python
DEFAULT_FRONTEND_EVENTS = {
    "connected",
    "request_start",
    "orchestrator_start", "orchestrator_phase_start", "orchestrator_phase_end", "orchestrator_end",
    "synthesis_start", "synthesis_end",
    "manager_start", "manager_script_planned", "manager_step_start", "manager_step_end", "manager_end",
    "delegation_planned", "delegation_chosen", "delegation_executed",
    "agent_start", "agent_end",
    "worker_tool_call", "worker_tool_result",
    "action_planned", "action_executed",
    "policy_denied", "error",
}
```

### Filtering

```bash
# Allow all events
FRONTEND_EVENT_ALLOWLIST="*"

# Custom subset
FRONTEND_EVENT_ALLOWLIST="agent_start,agent_end,error"
```

## Logging

### Framework Logger

```python
from agent_framework.logging import get_logger

logger = get_logger()
logger.info("Agent started", extra={"job_id": "123"})
```

### Structured Logging

```python
import logging
import json

class JSONFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "message": record.getMessage(),
            "extra": getattr(record, "extra", {}),
        })

# Configure
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logging.getLogger("agent_framework").addHandler(handler)
```

## Langfuse Integration

```python
from agent_framework.observability.subscribers import LangfuseSubscriber

langfuse = LangfuseSubscriber(
    public_key="pk-...",
    secret_key="sk-...",
    host="https://cloud.langfuse.com",
)
event_bus.subscribe(langfuse)
```

## Health Checks

```python
from fastapi import FastAPI
import httpx

app = FastAPI()

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.get("/ready")
async def ready():
    checks = {}
    
    # Check LLM
    try:
        resp = httpx.get("https://api.openai.com/v1/models", timeout=5)
        checks["openai"] = resp.status_code == 200
    except:
        checks["openai"] = False
    
    # Check Phoenix
    try:
        resp = httpx.get("http://localhost:6006/health", timeout=5)
        checks["phoenix"] = resp.status_code == 200
    except:
        checks["phoenix"] = False
    
    healthy = all(checks.values())
    return {"status": "ready" if healthy else "not_ready", "checks": checks}
```

## Metrics

### Custom Metrics

```python
from prometheus_client import Counter, Histogram

agent_runs = Counter("agent_runs_total", "Total agent runs", ["agent_name", "status"])
run_duration = Histogram("agent_run_duration_seconds", "Agent run duration")

class MetricsSubscriber(BaseEventSubscriber):
    def handle_event(self, event_name: str, data: dict) -> None:
        if event_name == "agent_end":
            agent_name = data.get("agent_name", "unknown")
            status = "success" if not data.get("error") else "error"
            agent_runs.labels(agent_name=agent_name, status=status).inc()
```

## Dashboard Queries

### Phoenix Queries

```sql
-- Token usage by model
SELECT 
    attributes['gen_ai.request.model'] as model,
    SUM(attributes['gen_ai.usage.total_tokens']) as total_tokens,
    SUM(attributes['gen_ai.cost.total_usd']) as total_cost
FROM spans
WHERE name LIKE 'llm.%'
GROUP BY model

-- Slowest tools
SELECT 
    attributes['tool.name'] as tool,
    AVG(attributes['tool.latency_ms']) as avg_latency,
    COUNT(*) as executions
FROM spans
WHERE name LIKE 'tool.%'
GROUP BY tool
ORDER BY avg_latency DESC
```

## Best Practices

1. **Enable Phoenix** for production tracing
2. **Configure pricing** for accurate cost tracking
3. **Filter frontend events** to reduce noise
4. **Use structured logging** for analysis
5. **Implement health checks** for orchestration
6. **Monitor token usage** to control costs

