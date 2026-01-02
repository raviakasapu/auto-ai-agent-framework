# Environment Variables

Complete reference for framework environment variables.

## LLM Configuration

### OpenAI

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | — | OpenAI API key (required) |
| `OPENAI_MODEL` | `gpt-4o` | Default model |
| `OPENAI_STRATEGIC_MODEL` | `gpt-4o` | Strategic planning model |
| `OPENAI_TEMPERATURE` | `0.7` | Temperature |
| `OPENAI_MAX_TOKENS` | `4096` | Max output tokens |
| `OPENAI_TIMEOUT` | `60` | Request timeout (seconds) |

### Google AI

| Variable | Default | Description |
|----------|---------|-------------|
| `GOOGLE_API_KEY` | — | Google AI API key |
| `GOOGLE_MODEL` | `gemini-1.5-pro` | Model name |
| `GOOGLE_STRATEGIC_MODEL` | `gemini-1.5-pro` | Strategic model |

### Pricing

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PRICING_JSON` | — | JSON pricing config |
| `LLM_PRICING_INPUT_USD_PER_1K` | `0.15` | Input token cost |
| `LLM_PRICING_OUTPUT_USD_PER_1K` | `0.60` | Output token cost |

**JSON format example:**
```json
{
  "gpt_4o": {"input": 2.50, "output": 10.00},
  "gpt_4o_mini": {"input": 0.15, "output": 0.60}
}
```

## Observability

### Phoenix

| Variable | Default | Description |
|----------|---------|-------------|
| `PHOENIX_ENDPOINT` | `http://localhost:6006/v1/traces` | Phoenix collector URL |
| `PHOENIX_MAX_ATTR_CHARS` | `4000` | Max attribute length |
| `PHOENIX_CAPTURE_LLM_BODIES` | `true` | Include prompts/responses |
| `PHOENIX_PRETTY_JSON` | `false` | Pretty-print JSON |
| `PHOENIX_COMPACT_JSON` | `true` | Compact JSON format |

### Langfuse

| Variable | Default | Description |
|----------|---------|-------------|
| `LANGFUSE_PUBLIC_KEY` | — | Langfuse public key |
| `LANGFUSE_SECRET_KEY` | — | Langfuse secret key |
| `LANGFUSE_HOST` | `https://cloud.langfuse.com` | Langfuse host |

### Logging

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Logging level |

## Agent Behavior

### ReAct Planner

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENT_REACT_INCLUDE_HISTORY` | `true` | Include history in prompts |
| `AGENT_REACT_MAX_HISTORY_MESSAGES` | `20` | Max history messages |
| `AGENT_LOG_ROUTER_DETAILS` | `false` | Log router planner details |

### HITL (Human-in-the-Loop)

| Variable | Default | Description |
|----------|---------|-------------|
| `REACT_HITL_ENABLE` | `false` | Enable HITL globally |
| `REACT_HITL_SCOPE` | `writes` | Scope: `all`, `writes`, `none` |

### Event Filtering

| Variable | Default | Description |
|----------|---------|-------------|
| `FRONTEND_EVENT_ALLOWLIST` | — | Comma-separated events, or `*` for all |

## Storage

| Variable | Default | Description |
|----------|---------|-------------|
| `JOB_STORE_DIR` | `./jobs` | Job store directory |
| `MODEL_DIR` | — | Model files directory |

## Usage Examples

### Development

```bash
# .env file
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
LOG_LEVEL=DEBUG
PHOENIX_ENDPOINT=http://localhost:6006/v1/traces
```

### Production

```bash
# .env file
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o
OPENAI_STRATEGIC_MODEL=gpt-4o

# Pricing
LLM_PRICING_JSON='{"gpt_4o":{"input":2.5,"output":10.0}}'

# Observability
PHOENIX_ENDPOINT=http://phoenix.internal:6006/v1/traces
PHOENIX_MAX_ATTR_CHARS=8000

# Security
REACT_HITL_ENABLE=true
REACT_HITL_SCOPE=writes

# Events
FRONTEND_EVENT_ALLOWLIST=agent_start,agent_end,error
```

### Docker Compose

```yaml
services:
  agent:
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - PHOENIX_ENDPOINT=http://phoenix:6006/v1/traces
      - REACT_HITL_ENABLE=true
```

