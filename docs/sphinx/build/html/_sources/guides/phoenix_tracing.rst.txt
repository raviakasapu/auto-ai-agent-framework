Phoenix Tracing (Arize)
=======================

This guide documents how the framework integrates with OpenTelemetry and Arize Phoenix, how spans are organized hierarchically, and how we enrich spans with LLM/tool metrics for aggregation (tokens, latency, cost).

Overview
--------

- Provider/Exporter: OpenTelemetry with OTLP HTTP exporter to Phoenix
- Global tracer provider is set so all tracers export to Phoenix
- Hierarchical spans reflect Manager → Delegation → Agent → Action → Tool/LLM
- Attributes include LLM usage/cost, latency, and optional prompt/response bodies

Key Files
---------

- Phoenix subscriber: ``agent_framework/observability/subscribers.py``
- Manager/Agent events: ``agent_framework/core/manager_v2.py``, ``agent_framework/core/agent.py``
- LLM gateway (OpenAI): ``agent_framework/gateways/inference.py``
- Factory wiring (subscribers and worker propagation): ``deployment/factory.py``
- API root request span: ``main.py``

What Gets Traced
----------------

- Request root: a top-level span per ``/run`` request
- Manager spans: ``manager:{name}`` with actor context
- Delegations: ``delegation:{worker}`` child spans
- Agent spans: ``agent:{name}``
- Actions: long-lived spans from planning to execution with args/results
- Tools: ``tool.<name>`` child spans around actual tool execution with latency
- LLM calls: ``llm.openai.chat_completions`` spans with usage, latency, cost

Provider Initialization
-----------------------

- PhoenixSubscriber constructs an OTLP HTTP exporter and a ``TracerProvider``
- It sets the provider as the global tracer provider to unify all tracers
- Manager and workers share the same Phoenix subscriber instance for a single trace

Span Hierarchy
--------------

- ``agent_start/agent_end`` → opens/closes ``agent:{name}``
- ``manager_start/manager_end`` → opens/closes ``manager:{name}``
- ``delegation_chosen/delegation_executed`` → opens/closes ``delegation:{worker}``
- ``action_planned/action_executed`` → opens/closes ``action:{tool}``
- Tools run inside ``tool.<name>`` child spans
- LLM calls run inside ``llm.openai.chat_completions`` spans and inherit actor context

Attributes & Metrics
--------------------

We set both legacy ``llm.*`` and GenAI-style ``gen_ai.*`` attributes.

- GenAI request/response
  - ``gen_ai.system`` (e.g., ``openai``)
  - ``gen_ai.operation.name`` (e.g., ``chat.completions``)
  - ``gen_ai.request.model``, ``gen_ai.request.temperature``
  - ``gen_ai.prompt`` (optional, truncated)
  - ``gen_ai.response.output_text`` (optional, truncated)
  - ``gen_ai.response.finish_reason``
  - ``gen_ai.response.tool_calls.{count,json}``
- Usage & latency
  - ``gen_ai.usage.input_tokens``
  - ``gen_ai.usage.output_tokens``
  - ``gen_ai.usage.total_tokens``
  - ``gen_ai.latency_ms``
  - ``http.status_code`` (and error text on failures)
- Cost
  - ``gen_ai.cost.{input_usd_per_1k,output_usd_per_1k,pricing_source}``
  - ``gen_ai.cost.{input_usd,output_usd,total_usd}``
- Actor context
  - ``gen_ai.actor.role`` (``manager``|``agent``)
  - ``gen_ai.actor.name`` (e.g., ``Orchestrator``, ``PBI_Manager``)
- Tools (on tool spans)
  - ``tool.name`` - Tool identifier
  - ``tool.latency_ms`` - Execution latency in milliseconds
  - ``tool.input.args_json`` - Tool arguments as compact JSON string
  - ``tool.input.args.pretty`` - Pretty-printed JSON arguments (if ``PHOENIX_PRETTY_JSON=true``)
  - ``tool.input.args`` - Fallback string representation if JSON serialization fails
  - ``tool.output.result_summary`` - Quick summary extracted from result (human_readable_summary, summary, or message) or first 200 chars
  - ``tool.output.result_json`` - Full result as compact JSON (only if size <= ``PHOENIX_MAX_ATTR_CHARS``)
  - ``tool.output.result.pretty`` - Pretty-printed JSON result (if ``PHOENIX_PRETTY_JSON=true``)
  - ``tool.output.result`` - String representation for non-dict results

Configuration
-------------

- Phoenix endpoint
  - ``PHOENIX_ENDPOINT`` (default ``http://localhost:6006/v1/traces``)
- Capture size & bodies
  - ``PHOENIX_MAX_ATTR_CHARS`` (default: ``4000``) - Maximum characters for attributes before truncation
  - ``PHOENIX_CAPTURE_LLM_BODIES`` (``true``/``false``, default: ``true``) - Include prompt/response in LLM spans
  - ``PHOENIX_PRETTY_JSON`` (``true``/``false``, default: ``false``) - Enable pretty-printed JSON for tool args/results
- Pricing (per-1K tokens)
  - Option 1 (recommended): Single JSON blob via ``LLM_PRICING_JSON``
    - Flat per model (model key normalized as underscores):

      .. code-block:: json

         {"gpt_4o_mini": {"input_per_1k": 0.15, "output_per_1k": 0.6}}

    - Nested by provider (natural model name preserved):

      .. code-block:: json

         {"openai": {"gpt-4o-mini": {"input_per_1k": 0.15, "output_per_1k": 0.6}}}

  - Option 2: Per-model env vars (model name normalized to uppercase with non-alphanumeric → ``_``)
    - ``<PROVIDER>_PRICE_<MODEL>_INPUT_PER_1K`` / ``<PROVIDER>_PRICE_<MODEL>_OUTPUT_PER_1K``
  - Option 3: Global defaults
    - ``LLM_PRICE_DEFAULT_INPUT_PER_1K`` / ``LLM_PRICE_DEFAULT_OUTPUT_PER_1K``

Example YAML Wiring
-------------------

.. code-block:: yaml

   resources:
     subscribers:
       - name: phoenix
         type: PhoenixSubscriber
         config:
           endpoint: ${PHOENIX_ENDPOINT:-http://localhost:6006/v1/traces}
           service_name: orchestrator
   spec:
     subscribers: [logging, phoenix]

Complete Data Structure Reference
----------------------------------

For a complete reference of all spans, attributes, and data structures, see the detailed documentation below.

Span Hierarchy
~~~~~~~~~~~~~~

The complete hierarchy from root to leaf:

.. code-block:: text

   🎯 Root Request Span (task name)
   ├── manager:{manager_name}
   │   ├── delegation:{worker}
   │   │   ├── agent:{agent_name}
   │   │   │   ├── action:{tool_name}
   │   │   │   │   ├── tool.{tool_name}
   │   │   │   │   └── llm.openai.chat_completions (if LLM called)
   │   │   │   └── [other action spans]
   │   │   └── [other agent spans]
   │   └── [other delegation spans]
   └── [other manager spans]

Event-to-Span Mapping
~~~~~~~~~~~~~~~~~~~~~

| Event Name | Span Name | Span Type | Lifecycle |
|-----------|-----------|-----------|-----------|
| ``request_start`` | (clears stacks) | N/A | N/A |
| ``manager_start`` | ``manager:{name}`` | Long-lived | Start |
| ``manager_end`` | ``manager:{name}`` | Long-lived | End |
| ``delegation_chosen`` | ``delegation:{worker}`` | Long-lived | Start |
| ``delegation_executed`` | ``delegation:{worker}`` | Long-lived | End |
| ``agent_start`` | ``agent:{name}`` | Long-lived | Start |
| ``agent_end`` | ``agent:{name}`` | Long-lived | End |
| ``action_planned`` | ``action:{tool}`` | Long-lived | Start |
| ``action_executed`` | ``action:{tool}`` | Long-lived | End |
| ``multi_step_start`` | ``step_{idx}:{action}`` | Long-lived | Start |
| ``multi_step_complete`` | ``step_{idx}:{action}`` | Long-lived | End |
| ``multi_step_error`` | ``step_{idx}:{action}`` | Long-lived | End |
| Tool execution | ``tool.{name}`` | Short-lived | Auto |
| LLM invocation | ``llm.openai.chat_completions`` or ``llm.google.generateContent`` | Short-lived | Auto |
| Other events | ``{event_name}`` | Short-lived | Auto |

Manager Spans
~~~~~~~~~~~~~

**Span Name**: ``manager:{manager_name}``

**Lifecycle Events**:
- Start: ``manager_start``
- End: ``manager_end``

**Start Attributes**:
- ``agent.event_name``: ``"manager_start"``
- ``agent.payload_json``: Compact JSON payload
- ``agent.payload.pretty``: Pretty JSON payload (if ``PHOENIX_PRETTY_JSON=true``)

**End Attributes**:
- ``manager.result_summary``: Truncated result summary
- ``manager.result_json``: Compact JSON (if ``PHOENIX_COMPACT_JSON=true``)
- ``manager.result.pretty``: Pretty JSON (if ``PHOENIX_PRETTY_JSON=true``)

**Baggage**:
- ``actor.role``: ``"manager"``
- ``actor.name``: ``{manager_name}``

Delegation Spans
~~~~~~~~~~~~~~~~

**Span Name**: ``delegation:{worker}``

**Lifecycle Events**:
- Start: ``delegation_chosen``
- End: ``delegation_executed``

**Start Attributes**:
- ``agent.event_name``: ``"delegation_chosen"``
- ``agent.payload_json``: Compact JSON payload
- ``worker.name``: Worker identifier
- ``worker.agent_name``: Agent name for worker

**End Attributes**:
- ``delegation.result_summary``: Truncated result summary
- ``delegation.result_json``: Compact JSON (if enabled)
- ``delegation.result.pretty``: Pretty JSON (if enabled)

Agent Spans
~~~~~~~~~~~

**Span Name**: ``agent:{agent_name}``

**Lifecycle Events**:
- Start: ``agent_start``
- End: ``agent_end``

**Start Attributes**:
- ``agent.event_name``: ``"agent_start"``
- ``agent.payload_json``: Compact JSON payload

**End Attributes**:
- ``agent.name``: Agent name
- ``agent.result_summary``: Truncated result summary
- ``agent.result_json``: Compact JSON (if enabled)
- ``agent.result.pretty``: Pretty JSON (if enabled)
- ``agent.operation``: Operation name (if present)
- ``agent.summary``: Summary text (if present)

Action Spans
~~~~~~~~~~~~

**Span Name**: ``action:{tool_name}``

**Lifecycle Events**:
- Start: ``action_planned``
- End: ``action_executed``

**Start Attributes**:
- ``agent.event_name``: ``"action_planned"``
- ``tool.name``: Tool name
- ``tool.args_json``: Compact JSON args (if enabled)
- ``tool.args.pretty``: Pretty JSON args (if enabled)

**End Attributes**:
- ``tool.result_summary``: Truncated result summary
- ``tool.result_json``: Compact JSON (if enabled)
- ``tool.result.pretty``: Pretty JSON (if enabled)

Tool Spans
~~~~~~~~~~

**Span Name**: ``tool.{tool_name}``

**Lifecycle**: Automatic (context manager, short-lived)

**Attributes**:
- ``tool.name``: Tool instance name
- ``tool.input.args_json``: Compact JSON of input arguments
- ``tool.input.args.pretty``: Pretty JSON (if ``PHOENIX_PRETTY_JSON=true``)
- ``tool.input.args``: Fallback string if JSON fails
- ``tool.latency_ms``: Execution time in milliseconds
- ``tool.output.result_summary``: Summary of result
- ``tool.output.result_json``: Full result as JSON (if size <= MAX_CHARS)
- ``tool.output.result.pretty``: Pretty JSON (if enabled)
- ``tool.output.result``: String result for non-dict

LLM Spans
~~~~~~~~~

**Span Name**: ``llm.openai.chat_completions`` or ``llm.google.generateContent``

**Lifecycle**: Automatic (context manager, short-lived)

**Semantic Attributes** (``gen_ai.*``):
- ``gen_ai.system``: Provider identifier (``"openai"`` or ``"google"``)
- ``gen_ai.operation.name``: Operation type (``"chat.completions"`` or ``"generateContent"``)
- ``gen_ai.request.model``: Model name
- ``gen_ai.request.temperature``: Temperature setting (if set)
- ``gen_ai.request.tools.count``: Number of tools provided
- ``gen_ai.request.tools.schema``: Compact tools schema (if enabled)
- ``gen_ai.request.tools.schema.pretty``: Pretty tools schema (if enabled)
- ``gen_ai.actor.role``: Actor role (from baggage)
- ``gen_ai.actor.name``: Actor name (from baggage)
- ``gen_ai.prompt``: User prompt/messages (truncated)
- ``gen_ai.latency_ms``: API call latency
- ``gen_ai.response.finish_reason``: Why generation stopped
- ``gen_ai.response.tool_calls.count``: Number of tool calls
- ``gen_ai.response.tool_calls.json``: Compact JSON (if enabled)
- ``gen_ai.response.tool_calls.pretty``: Pretty JSON with parsed args (if enabled)
- ``gen_ai.response.output_text``: Response text (if present)
- ``gen_ai.usage.input_tokens``: Input tokens
- ``gen_ai.usage.output_tokens``: Output tokens
- ``gen_ai.usage.total_tokens``: Total tokens
- ``gen_ai.cost.input_usd_per_1k``: Price per 1K input tokens
- ``gen_ai.cost.output_usd_per_1k``: Price per 1K output tokens
- ``gen_ai.cost.pricing_source``: Pricing source (``"env.json"``, ``"env.vars"``, or ``"default"``)
- ``gen_ai.cost.input_usd``: Cost for input tokens
- ``gen_ai.cost.output_usd``: Cost for output tokens
- ``gen_ai.cost.total_usd``: Total cost
- ``http.status_code``: HTTP response code
- ``error``: Error indicator (if HTTP error)
- ``http.response_text``: Error response text (errors only)

**Legacy Attributes** (``llm.*``, if ``PHOENIX_ATTR_MODE=legacy`` or ``both``):
- ``llm.provider``: Provider identifier
- ``llm.model``: Model name
- ``llm.base_url``: API base URL
- ``llm.temperature``: Temperature setting
- ``llm.use_function_calling``: Function calling enabled
- ``llm.messages.count``: Number of messages
- ``llm.prompt``: User prompt (truncated)
- ``llm.tools_schema``: Compact tools schema (if enabled)
- ``llm.tools_schema.pretty``: Pretty tools schema (if enabled)
- ``llm.latency_ms``: API call latency
- ``llm.finish_reason``: Finish reason
- ``llm.tool_calls.count``: Number of tool calls
- ``llm.tool_calls.json``: Compact JSON (if enabled)
- ``llm.tool_calls.pretty``: Pretty JSON (if enabled)
- ``llm.response``: Response text
- ``llm.usage.prompt_tokens``: Input tokens
- ``llm.usage.completion_tokens``: Output tokens
- ``llm.usage.total_tokens``: Total tokens

**Span Events** (if ``PHOENIX_BODY_EVENTS=true``):
- ``prompt``: User prompt text
- ``response``: LLM response text
- ``tools_schema``: Pretty tools schema

**Span Events** (if ``PHOENIX_TOOL_CALL_EVENTS=true``):
- ``tool_call``: One event per tool call with ``tool_call.id``, ``tool_call.function.name``, ``tool_call.function.arguments``

Multi-Step Spans
~~~~~~~~~~~~~~~~

**Span Name**: ``step_{step_idx}:{step_action}``

**Lifecycle Events**:
- Start: ``multi_step_start``
- End: ``multi_step_complete`` or ``multi_step_error``

**Attributes**:
- ``agent.event_name``: Event name
- ``agent.payload_json``: Compact JSON payload
- ``step.index``: Step number (0-based)
- ``step.total``: Total steps
- ``step.action``: Action description
- ``step.worker``: Worker identifier
- ``step.context``: Context data (truncated)
- ``step.context.pretty``: Pretty JSON context (if enabled)
- ``step.success``: Success indicator
- ``step.error``: Error indicator
- ``step.error_message``: Error message (if error)

Baggage/Context Propagation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Baggage is propagated via OpenTelemetry context to maintain actor context across spans.

**Baggage Keys**:
- ``actor.role``: Role identifier (``"manager"``, ``"agent"``, ``"step"``)
- ``actor.name``: Actor name (manager_name, agent_name, worker_name)

Baggage can be read in child spans using:

.. code-block:: python

   from opentelemetry.baggage import get_baggage
   actor_name = get_baggage("actor.name")
   actor_role = get_baggage("actor.role")

If ``PHOENIX_EMIT_ACTOR_IN_LLM=true``, actor info is duplicated as span attributes.

Additional Configuration
~~~~~~~~~~~~~~~~~~~~~~~~

- ``PHOENIX_COMPACT_JSON`` (``true``/``false``, default: ``false``): Also emit compact JSON copies
- ``PHOENIX_TOOL_CALL_EVENTS`` (``true``/``false``, default: ``true``): Emit span events for each tool call
- ``PHOENIX_BODY_EVENTS`` (``true``/``false``, default: ``true``): Emit span events for prompt/response/tools_schema
- ``PHOENIX_ATTR_MODE`` (``semantic``, ``legacy``, or ``both``, default: ``semantic``): Attribute style
- ``PHOENIX_EMIT_ACTOR_IN_LLM`` (``true``/``false``, default: ``false``): Duplicate actor baggage as LLM span attributes
- ``PHOENIX_DISABLE_PAYLOADS`` (``true``/``false``, default: ``false``): Disable all payload/body attributes

Replication Notes
-----------------

1. Create a subscriber that sets the OTel ``TracerProvider`` and OTLP exporter
2. Set the provider globally via ``trace.set_tracer_provider``
3. Use long-lived spans for lifecycle events (start/end pairs)
4. Propagate the subscriber to nested agents/workers so they share the trace
5. Wrap LLM/tool calls in child spans and set numeric attributes for usage/latency/cost
6. Optionally include prompt/response text (truncated) via env flags

Implementation Notes
--------------------

- The framework keeps both ``llm.*`` (legacy) and ``gen_ai.*`` (semantic-style) attributes for compatibility
- Pricing is purely env-driven (no provider calls); this avoids network in tracing path
- If you add additional LLM providers/gateways, reuse the same attribute names
- Root request spans are typically created by implementations after agent loads and ``request_start`` event is published
