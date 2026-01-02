# Planners Guide

Planners are the reasoning engine of agents. They analyze tasks, decide on actions, and coordinate tool usage.

## Overview

The planner is configured in the `spec.planner` section:

```yaml
spec:
  planner:
    type: ReActPlanner
    config:
      inference_gateway: openai
      use_function_calling: true
      system_prompt: |
        You are a helpful assistant.
```

---

## Available Planners

| Planner | Use Case | Agent Type |
|---------|----------|------------|
| `ReActPlanner` | Tool-using agents | Agent |
| `WorkerRouterPlanner` | Task routing | ManagerAgent |

---

## ReActPlanner

Implements the ReAct (Reasoning + Acting) pattern for tool-using agents.

### Configuration

```yaml
spec:
  planner:
    type: ReActPlanner
    config:
      inference_gateway: openai
      use_function_calling: true
      max_iterations: 10
      system_prompt: |
        You are a helpful research assistant.
        Use the available tools to complete tasks.
        Always verify your findings before responding.
```

### Config Options

| Option | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| `inference_gateway` | string | Yes | - | Reference to gateway in resources |
| `use_function_calling` | bool | No | false | Use OpenAI function calling |
| `max_iterations` | int | No | 10 | Maximum reasoning iterations |
| `system_prompt` | string | Yes | - | System instructions for the LLM |

### How It Works

1. **Observe**: Receives task and current context
2. **Think**: Reasons about what action to take
3. **Act**: Selects and calls a tool
4. **Observe**: Receives tool result
5. **Repeat**: Until task is complete or max iterations

### Function Calling Mode

When `use_function_calling: true`:
- Uses OpenAI's native function calling
- Tools are passed as function definitions
- More reliable tool parameter extraction

When `use_function_calling: false`:
- Uses text-based tool selection
- Parses tool calls from LLM output
- Works with any LLM provider

### Example

```yaml
apiVersion: agent.framework/v2
kind: Agent

metadata:
  name: ResearchAgent

resources:
  inference_gateways:
    - name: openai
      type: OpenAIGateway
      config:
        model: gpt-4o-mini
        api_key: ${OPENAI_API_KEY}
        use_function_calling: true

  tools:
    - name: web_search
      type: MockSearchTool
      config: {}

spec:
  policies:
    $preset: simple

  planner:
    type: ReActPlanner
    config:
      inference_gateway: openai
      use_function_calling: true
      max_iterations: 10
      system_prompt: |
        You are a research assistant.
        1. Search for information using web_search
        2. Analyze and summarize findings
        3. Provide clear, factual responses

  memory:
    $preset: worker

  tools: [web_search]
```

---

## WorkerRouterPlanner

Routes tasks to appropriate worker agents in a ManagerAgent.

### Configuration

```yaml
spec:
  planner:
    type: WorkerRouterPlanner
    config:
      inference_gateway: openai-orchestrator
      worker_keys: [research-worker, task-worker]
      default_worker: research-worker
      system_prompt: |
        You are a task router. Analyze requests and route them:

        Available workers:
        - research-worker: Information search and research
        - task-worker: Task creation and management

        Return JSON: {"worker": "<key>", "reason": "..."}
```

### Config Options

| Option | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| `inference_gateway` | string | Yes | - | Reference to gateway |
| `worker_keys` | list | Yes | - | List of available worker names |
| `default_worker` | string | Yes | - | Fallback worker |
| `system_prompt` | string | Yes | - | Routing instructions |

### How It Works

1. **Analyze**: Reviews the incoming task
2. **Route**: Selects the best worker for the task
3. **Delegate**: Passes task to selected worker
4. **Collect**: Gathers worker response
5. **Follow-up**: May initiate additional phases

### Routing Response Format

The planner should return JSON:

```json
{
  "worker": "research-worker",
  "reason": "Task requires information lookup"
}
```

### Example

```yaml
apiVersion: agent.framework/v2
kind: ManagerAgent

metadata:
  name: Orchestrator

resources:
  inference_gateways:
    - name: openai
      type: OpenAIGateway
      config:
        model: gpt-4o
        api_key: ${OPENAI_API_KEY}

spec:
  policies:
    $preset: manager_with_followups

  planner:
    type: WorkerRouterPlanner
    config:
      inference_gateway: openai
      worker_keys: [research, tasks, weather]
      default_worker: research
      system_prompt: |
        You route requests to specialized workers:

        Workers:
        - research: Web search, information gathering, note-taking
        - tasks: Create tasks, list tasks, mark complete
        - weather: Weather lookups for any location

        Analyze the user request and select the best worker.
        If unclear, use the default (research).

        Response format: {"worker": "<key>", "reason": "..."}

  memory:
    $preset: manager

  workers:
    - name: research
      config_path: configs/agents/research_worker.yaml
    - name: tasks
      config_path: configs/agents/task_worker.yaml
    - name: weather
      config_path: configs/agents/weather_worker.yaml
```

---

## Inference Gateways

Planners require an inference gateway for LLM access.

### OpenAIGateway

```yaml
resources:
  inference_gateways:
    - name: openai
      type: OpenAIGateway
      config:
        api_key: ${OPENAI_API_KEY}
        model: gpt-4o-mini
        temperature: 0.1
        max_tokens: 4096
        use_function_calling: true
        timeout: 30
```

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `api_key` | string | Required | OpenAI API key |
| `model` | string | Required | Model name |
| `temperature` | float | 0.7 | Sampling temperature |
| `max_tokens` | int | 4096 | Maximum response tokens |
| `use_function_calling` | bool | false | Enable function calling |
| `timeout` | int | 30 | Request timeout (seconds) |

### AnthropicGateway

```yaml
resources:
  inference_gateways:
    - name: anthropic
      type: AnthropicGateway
      config:
        api_key: ${ANTHROPIC_API_KEY}
        model: claude-3-opus-20240229
        temperature: 0.1
        max_tokens: 4096
```

### MockGateway

For testing without API calls:

```yaml
resources:
  inference_gateways:
    - name: mock
      type: MockGateway
      config: {}
```

---

## System Prompts

### Best Practices

1. **Be specific** about the agent's role and capabilities
2. **List available tools** and when to use them
3. **Define output format** expectations
4. **Include constraints** and guardrails

### ReActPlanner Prompt Template

```yaml
system_prompt: |
  You are a [ROLE] assistant.

  Your capabilities:
  - [Tool 1]: [When to use]
  - [Tool 2]: [When to use]

  Guidelines:
  1. [Important instruction]
  2. [Another instruction]

  When complete, provide a clear summary of your findings.
```

### WorkerRouterPlanner Prompt Template

```yaml
system_prompt: |
  You are a task router for a multi-agent system.

  Available workers:
  - [worker-1]: [Capabilities and use cases]
  - [worker-2]: [Capabilities and use cases]

  Routing rules:
  1. [Rule for selecting worker-1]
  2. [Rule for selecting worker-2]
  3. Default to [default-worker] if unclear

  Response format: {"worker": "<key>", "reason": "..."}
```

---

## Advanced Patterns

### Chain of Thought

Encourage step-by-step reasoning:

```yaml
system_prompt: |
  Think step by step:
  1. Understand the task
  2. Plan your approach
  3. Execute using tools
  4. Verify results
  5. Summarize findings
```

### Few-Shot Examples

Include examples in the prompt:

```yaml
system_prompt: |
  You are a calculator assistant.

  Example:
  User: What is 15% of 200?
  Assistant: I'll use the calculator.
  [Uses calculator: 200 * 0.15 = 30]
  The answer is 30.

  Now help with the user's request.
```

### Safety Guardrails

Add constraints:

```yaml
system_prompt: |
  Guidelines:
  - Never reveal sensitive information
  - Verify data before reporting
  - Ask for clarification if the request is ambiguous
  - Refuse harmful or unethical requests
```

---

## Complete Examples

### Research Agent with ReActPlanner

```yaml
apiVersion: agent.framework/v2
kind: Agent

metadata:
  name: ThoroughResearcher

resources:
  inference_gateways:
    - name: openai
      type: OpenAIGateway
      config:
        model: gpt-4o
        api_key: ${OPENAI_API_KEY}
        temperature: 0.1
        use_function_calling: true

  tools:
    - name: web_search
      type: MockSearchTool
      config: {}
    - name: note_taker
      type: NoteTakerTool
      config:
        storage_path: /tmp/research_notes.json

spec:
  policies:
    $preset: simple
    termination:
      type: DefaultTerminationPolicy
      config:
        max_iterations: 15

  planner:
    type: ReActPlanner
    config:
      inference_gateway: openai
      use_function_calling: true
      max_iterations: 15
      system_prompt: |
        You are a thorough research assistant.

        Available tools:
        - web_search: Search for information on any topic
        - note_taker: Save important findings with title and content

        Research process:
        1. Search for information on the topic
        2. Take notes on key findings
        3. Search for additional details if needed
        4. Synthesize your notes into a comprehensive summary

        Always cite your sources and distinguish facts from opinions.

  memory:
    $preset: worker

  tools: [web_search, note_taker]
```

### Multi-Domain Manager

```yaml
apiVersion: agent.framework/v2
kind: ManagerAgent

metadata:
  name: UniversalAssistant

resources:
  inference_gateways:
    - name: openai
      type: OpenAIGateway
      config:
        model: gpt-4o
        api_key: ${OPENAI_API_KEY}

spec:
  policies:
    $preset: manager_with_followups

  planner:
    type: WorkerRouterPlanner
    config:
      inference_gateway: openai
      worker_keys: [research, tasks, calculator]
      default_worker: research
      system_prompt: |
        You are a universal assistant router.

        Workers and their specialties:
        - research: Web search, information gathering, note-taking
          Use for: "search for", "find information about", "research"
        - tasks: Task management, scheduling, to-do lists
          Use for: "create a task", "list my tasks", "mark as done"
        - calculator: Mathematical calculations
          Use for: Numbers, math, calculations, percentages

        Analyze the user's intent and route to the best worker.
        If the request spans multiple domains, route to the primary domain.

        Response: {"worker": "<key>", "reason": "brief explanation"}

  memory:
    $preset: manager

  workers:
    - name: research
      config_path: configs/agents/research_worker.yaml
    - name: tasks
      config_path: configs/agents/task_worker.yaml
    - name: calculator
      config_path: configs/agents/calculator_worker.yaml
```

---

## Best Practices

1. **Match planner to agent type** - ReActPlanner for Agent, WorkerRouterPlanner for ManagerAgent
2. **Use function calling** when available for more reliable tool use
3. **Write clear system prompts** that guide the LLM effectively
4. **Set appropriate max_iterations** based on task complexity
5. **Use lower temperatures** (0.1-0.3) for more deterministic behavior
6. **Test prompts thoroughly** before production deployment
7. **Include examples** in prompts for complex tasks
