---
title: Environment Variables
---

# Environment Variables

This guide lists the environment variables recognized by the AI Agent Framework, their purpose, allowed values, and defaults. Unless noted, omitting a variable uses the default behavior.

**Tip**: You can set variables in `.env`, shell, or process manager. The framework loads `.env` automatically when using the factory (see `deployment/factory.py`).

## LLM Providers

### OpenAI

- **OPENAI_API_KEY** (required)
  - Purpose: OpenAI API key for all OpenAI-backed planners/gateways.
  - Default: none (required for OpenAI gateways)

- **OPENAI_MODEL**
  - Purpose: Default lightweight model (e.g., for router/planners).
  - Default: `gpt-4o-mini`

- **OPENAI_STRATEGIC_MODEL**
  - Purpose: Model for strategic/orchestrator planning.
  - Default: `gpt-4o`

- **OPENAI_BASE_URL**
  - Purpose: Override OpenAI base URL (Azure/proxy).
  - Default: `https://api.openai.com`

- **OPENAI_TOOL_CHOICE**
  - Purpose: OpenAI `tool_choice` policy when function-calling (`auto`|`required`|`<object>`).
  - Default: `auto`

### Google Generative AI (Gemini)

- **GOOGLE_API_KEY** (required for GoogleAIGateway)
  - Purpose: Google Generative AI (Gemini) API key.
  - Default: none (required for Google gateways)

- **GOOGLE_MODEL**
  - Purpose: Default Gemini model for general planners/workers.
  - Default: `models/gemini-1.5-flash`

- **GOOGLE_STRATEGIC_MODEL**
  - Purpose: Gemini model for orchestrator/strategic planning configs.
  - Default: `models/gemini-1.5-pro`

- **GOOGLE_API_BASE_URL**
  - Purpose: Override the Google Generative AI base URL (self-hosted proxy).
  - Default: `https://generativelanguage.googleapis.com`

- **GOOGLE_API_TIMEOUT**
  - Purpose: HTTP timeout (seconds) for GoogleAIGateway requests.
  - Default: `60`

## Pricing (Optional)

Configure pricing for cost tracking in observability spans:

- **LLM_PRICING_JSON**
  - Purpose: Per-model pricing JSON used for cost attributes in spans.
  - Example: `{"openai":{"gpt-4o-mini":{"input_per_1k":0.15,"output_per_1k":0.60}}}`
  - Default: none

- **<PROVIDER>_PRICE_<MODEL>_INPUT_PER_1K** / **<PROVIDER>_PRICE_<MODEL>_OUTPUT_PER_1K**
  - Purpose: Per-model override via environment variable.
  - Example: `OPENAI_PRICE_GPT_4O_MINI_INPUT_PER_1K=0.15`
  - Default: none

- **LLM_PRICE_DEFAULT_INPUT_PER_1K** / **LLM_PRICE_DEFAULT_OUTPUT_PER_1K**
  - Purpose: Global defaults if per-model pricing absent.
  - Default: none

## Logging & Observability

### Logging

- **AGENT_LOG_LEVEL**
  - Purpose: Logging level for framework logs.
  - Values: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
  - Default: `INFO`

- **AGENT_LOG_ROUTER_DETAILS**
  - Purpose: Enable detailed router/planner logging.
  - Values: `true`|`false`
  - Default: `false`

- **AGENT_LOGGING_CONFIG**
  - Purpose: Path to logging configuration YAML file.
  - Default: `configs/logging/default.yaml`

- **AGENT_LOG_FORMAT**
  - Purpose: Custom log format string (optional, typically set by logging config).
  - Default: Set by logging configuration

### Phoenix (Arize) Tracing

The framework supports OpenTelemetry tracing with Phoenix for observability:

- **PHOENIX_ENDPOINT**
  - Purpose: Phoenix OTLP endpoint URL.
  - Default: `http://localhost:6006/v1/traces`

- **PHOENIX_CAPTURE_LLM_BODIES**
  - Purpose: Capture prompt/response bodies in spans (truncated).
  - Values: `true`|`false`
  - Default: `true`

- **PHOENIX_MAX_ATTR_CHARS**
  - Purpose: Maximum characters for span attributes before truncation.
  - Default: `4000`

- **PHOENIX_PRETTY_JSON**
  - Purpose: Pretty-print complex JSON attributes (e.g., tool_calls) for readability.
  - Values: `true`|`false`
  - Default: `true`

- **PHOENIX_TOOL_CALL_EVENTS**
  - Purpose: Emit one span event per tool call with parsed arguments for easy scanning.
  - Values: `true`|`false`
  - Default: `true`

- **PHOENIX_BODY_EVENTS**
  - Purpose: Emit span events for prompt, response, and tools schema bodies for easier reading.
  - Values: `true`|`false`
  - Default: `true`

- **PHOENIX_ATTR_MODE**
  - Purpose: Attribute naming mode for span attributes.
  - Values: `semantic`|`legacy`|`both`
    - `semantic` → emit only `gen_ai.*` attributes
    - `legacy` → emit only `llm.*` attributes
    - `both` → emit both sets (more verbose)
  - Default: `semantic`

- **PHOENIX_COMPACT_JSON**
  - Purpose: Also emit compact JSON attributes alongside pretty ones (e.g., `*.json`).
  - Values: `true`|`false`
  - Default: `false`

- **PHOENIX_EMIT_ACTOR_IN_LLM**
  - Purpose: Attach `actor.*` attributes directly on LLM spans (top-level baggage remains).
  - Values: `true`|`false`
  - Default: `false`

**Requirements**: Python packages `opentelemetry-sdk` and `opentelemetry-exporter-otlp` must be installed.

### Langfuse (Optional)

- **LANGFUSE_HOST**
  - Purpose: Langfuse API host URL.
  - Default: `https://cloud.langfuse.com`

- **LANGFUSE_PUBLIC_KEY**
  - Purpose: Langfuse public key (required if using Langfuse).
  - Default: none

- **LANGFUSE_SECRET_KEY**
  - Purpose: Langfuse secret key (required if using Langfuse).
  - Default: none

## ReAct Prompt Controls

Environment flags control how much context the ReAct planners include in prompts:

- **AGENT_REACT_INCLUDE_HISTORY**
  - Purpose: Include conversation turns (user/assistant) in prompts.
  - Values: `true`|`false`
  - Default: `true`

- **AGENT_REACT_INCLUDE_TRACES**
  - Purpose: Include execution traces: action/observation.
  - Values: `true`|`false`
  - Default: `true`

- **AGENT_REACT_INCLUDE_GLOBAL_UPDATES**
  - Purpose: Include `global_observation` entries from shared memory.
  - Values: `true`|`false`
  - Default: `true`

- **AGENT_REACT_MAX_HISTORY_MESSAGES**
  - Purpose: Tail cap for rendered history/traces (keeps N most recent lines).
  - Default: unlimited

- **AGENT_REACT_OBS_TRUNCATE_LEN**
  - Purpose: Truncate long observation/global_observation payloads.
  - Default: `1000`

**Notes**:
- Defaults preserve current behavior.
- Set `INCLUDE_*` to `false` to minimize prompts; e.g., turn ReAct into single-shot function-calling when desired.

## Router Prompt Controls

Environment flags for WorkerRouterPlanner:

- **AGENT_ROUTER_INCLUDE_HISTORY**
  - Purpose: Include conversation history in router prompts.
  - Values: `true`|`false`
  - Default: `true`

- **AGENT_ROUTER_MAX_HISTORY_MESSAGES**
  - Purpose: Maximum number of conversation messages to include.
  - Default: `20`

## Context Configuration

The framework uses a YAML-based context configuration system (`configs/context_config.yaml`) that controls:
- Truncation limits for various context types
- History inclusion settings (conversation, traces, global updates)
- Per-planner customization

**Configuration File**: `src/agent_framework/configs/context_config.yaml`

Environment variables take precedence over YAML config values.

### Global Truncation Limits

These ENV variables set truncation limits for all planners:

- **AGENT_STRATEGIC_PLAN_TRUNCATE_LEN**
  - Purpose: Maximum characters for strategic plan context.
  - Default: `2000`

- **AGENT_DIRECTOR_CONTEXT_TRUNCATE_LEN**
  - Purpose: Maximum characters for director context.
  - Default: `4000`

- **AGENT_DATA_MODEL_CONTEXT_TRUNCATE_LEN**
  - Purpose: Maximum characters for data model context.
  - Default: `6000`

- **AGENT_OBSERVATION_TRUNCATE_LEN**
  - Purpose: Maximum characters for observation content.
  - Default: `1500`

- **AGENT_TOOL_ARGS_TRUNCATE_LEN**
  - Purpose: Maximum characters for tool arguments display.
  - Default: `500`

- **AGENT_PREVIOUS_OUTPUT_TRUNCATE_LEN**
  - Purpose: Maximum characters for previous output content.
  - Default: `5000`

- **AGENT_MANIFEST_TRUNCATE_LEN**
  - Purpose: Maximum characters for manifest content.
  - Default: `6000`

### Global History Settings

- **AGENT_MAX_CONVERSATION_TURNS**
  - Purpose: Maximum number of conversation turns to include.
  - Default: `10`

- **AGENT_MAX_EXECUTION_TRACES**
  - Purpose: Maximum number of execution traces to include.
  - Default: `20`

- **AGENT_INCLUDE_CONVERSATION**
  - Purpose: Include conversation history in prompts.
  - Values: `true`|`false`
  - Default: `true`

- **AGENT_INCLUDE_TRACES**
  - Purpose: Include execution traces in prompts.
  - Values: `true`|`false`
  - Default: `true`

- **AGENT_INCLUDE_GLOBAL_UPDATES**
  - Purpose: Include global updates in prompts.
  - Values: `true`|`false`
  - Default: `true`

### Truncation Logging

- **AGENT_LOG_TRUNCATION**
  - Purpose: Log truncation events for debugging context sizes.
  - Values: `true`|`false`
  - Default: `true`

### Per-Planner Overrides (Strategic)

- **AGENT_ORCHESTRATOR_MAX_HISTORY_TURNS**
  - Purpose: Maximum conversation turns for strategic/orchestrator planner.
  - Default: `8`

- **STRATEGIC_INCLUDE_HISTORY_WITH_DIRECTOR**
  - Purpose: Include conversation history when director context is present.
  - Values: `true`|`false`
  - Default: `false`

### Per-Planner Overrides (Router)

- **AGENT_ROUTER_STRATEGIC_PLAN_TRUNCATE_LEN**
  - Purpose: Strategic plan truncation for router planner.
  - Default: `1000`

## HITL – Human-in-the-Loop

Require human approval before executing tools. Disabled by default.

- **REACT_HITL_ENABLE**
  - Purpose: Enable human-in-the-loop approval for tool execution.
  - Values: `true`|`false`
  - Default: `false`

- **REACT_HITL_SCOPE**
  - Purpose: Scope of tools requiring approval.
  - Values: `writes`|`all`
    - `writes` → only write operations require approval
    - `all` → all tools require approval
  - Default: `writes`

- **REACT_HITL_WRITES_LIST**
  - Purpose: Comma-separated list of tool names that require approval (overrides default write tools set).
  - Default: none (uses default write tools set)

**Behavior**:
- If a gated tool is selected, the worker returns a `FinalResponse`:
  - `operation`: `"await_approval"`
  - `payload.await_approval`: `true`
  - `payload.tool`: tool name (string)
  - `payload.args`: tool arguments (object)
  - `payload.message`: human-readable message (string)
  - `payload.reason`: reason for approval (string)
- Your implementation can render an approval card and re-run with approvals.

**Bypass (resume after approval)**:
- The worker checks a request-scoped `approvals` map and skips the gate for approved tools.
- Your implementation should pass approvals in the request context.

## Quick Recipes

### Minimal ReAct (no history, no traces)

```bash
AGENT_REACT_INCLUDE_HISTORY=false
AGENT_REACT_INCLUDE_TRACES=false
```

### HITL for writes only

```bash
REACT_HITL_ENABLE=true
REACT_HITL_SCOPE=writes
```

### Phoenix local server

```bash
PHOENIX_ENDPOINT=http://localhost:6006/v1/traces
PHOENIX_CAPTURE_LLM_BODIES=true
PHOENIX_MAX_ATTR_CHARS=4000
```

### OpenAI with custom model

```bash
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4o-mini
OPENAI_STRATEGIC_MODEL=gpt-4o
```

### Google Generative AI

```bash
GOOGLE_API_KEY=your-google-api-key
GOOGLE_MODEL=models/gemini-1.5-flash
GOOGLE_STRATEGIC_MODEL=models/gemini-1.5-pro
```

## Defaults Summary

- **HITL**: Disabled by default
- **ReAct prompts**: Include conversation, traces, global updates; truncate observations at 1000 chars
- **Router**: Includes up to 20 conversation turns
- **Phoenix**: Defaults to `localhost:6006`
- **OpenAI**: Defaults to `gpt-4o-mini` / `gpt-4o`
- **Google**: Defaults to `models/gemini-1.5-flash` / `models/gemini-1.5-pro`
- **Context Configuration**: Uses `configs/context_config.yaml` with ENV overrides
  - Strategic plan: 2000 chars
  - Director context: 4000 chars
  - Data model context: 6000 chars
  - Observations: 1500 chars
  - Tool args: 500 chars
  - Previous outputs: 5000 chars
  - Manifest: 6000 chars
  - Truncation logging: enabled

## Framework vs Implementation Variables

**Framework variables** (documented here):
- LLM provider configuration (OpenAI, Google)
- Pricing configuration
- Logging and observability (Phoenix, Langfuse)
- Planner prompt controls (ReAct, Router)
- HITL configuration

**Implementation variables** (not documented here):
- Server configuration (host, port, WebSocket)
- Frontend event filtering
- Backend API URLs
- Domain-specific model directories
- Implementation-specific feature flags

Your implementation may define additional environment variables for server configuration, frontend integration, and domain-specific features. These are outside the scope of the framework documentation.

