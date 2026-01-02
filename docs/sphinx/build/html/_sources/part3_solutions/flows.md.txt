# Flow Orchestration

This chapter covers multi-agent flows and the FlowFactory.

## Overview

Flows coordinate multiple agents in a defined sequence or pattern.

## FlowFactory

The `FlowFactory` loads flow definitions and orchestrates execution:

```python
from agent_framework.flows.flow_factory import FlowFactory

# Load flow definition
flow = FlowFactory.load("flows/analysis_flow.yaml")

# Execute flow
result = await flow.execute(
    task="Analyze the data model",
    context={"job_id": "123"},
)
```

## Flow Definition

```yaml
# flows/analysis_flow.yaml
name: analysis_flow
description: "Complete data model analysis"

steps:
  - name: schema_analysis
    agent: configs/agents/schema_reader.yaml
    task: "List all tables and columns"
  
  - name: relationship_analysis
    agent: configs/agents/relationship_analyzer.yaml
    task: "Analyze relationships between tables"
    depends_on: [schema_analysis]
  
  - name: validation
    agent: configs/agents/validator.yaml
    task: "Validate model consistency"
    depends_on: [schema_analysis, relationship_analysis]

output:
  combine: true
  format: summary
```

## FlowStep

Each step defines an agent and its task:

```python
from agent_framework.flows.flow_factory import FlowStep

step = FlowStep(
    name="analyze",
    agent_config="configs/agents/analyzer.yaml",
    task="Analyze the data",
    depends_on=[],
)
```

### Step Properties

| Property | Type | Description |
|----------|------|-------------|
| `name` | string | Step identifier |
| `agent` | string | Path to agent YAML |
| `task` | string | Task description |
| `depends_on` | list | Previous step names |
| `condition` | string | Optional execution condition |
| `retry` | int | Retry count on failure |

## Dependency Management

Steps can depend on previous steps:

```yaml
steps:
  - name: step1
    agent: agent1.yaml
    task: "First step"
  
  - name: step2
    agent: agent2.yaml
    task: "Second step using {{step1.result}}"
    depends_on: [step1]
  
  - name: step3
    agent: agent3.yaml
    task: "Third step"
    depends_on: [step1, step2]  # Waits for both
```

## Parallel Execution

Steps without dependencies run in parallel:

```yaml
steps:
  - name: analysis_a
    agent: analyzer_a.yaml
    task: "Analyze category A"
  
  - name: analysis_b
    agent: analyzer_b.yaml
    task: "Analyze category B"
  
  - name: combine
    agent: combiner.yaml
    task: "Combine results"
    depends_on: [analysis_a, analysis_b]  # Runs after both complete
```

## Conditional Steps

```yaml
steps:
  - name: check
    agent: checker.yaml
    task: "Check data quality"
  
  - name: fix
    agent: fixer.yaml
    task: "Fix data issues"
    depends_on: [check]
    condition: "{{check.result.has_issues}}"
```

## Result Handling

### Accessing Step Results

```yaml
steps:
  - name: list_tables
    agent: reader.yaml
    task: "List tables"
  
  - name: analyze_tables
    agent: analyzer.yaml
    task: "Analyze tables: {{list_tables.result.tables}}"
    depends_on: [list_tables]
```

### Output Combination

```yaml
output:
  combine: true
  format: summary  # or "full", "json"
  include: [step1, step3]  # Only include these steps
```

## Programmatic Flows

Create flows in code:

```python
from agent_framework.flows.flow_factory import Flow, FlowStep

flow = Flow(
    name="my_flow",
    steps=[
        FlowStep(name="analyze", agent_config="analyzer.yaml", task="Analyze"),
        FlowStep(name="validate", agent_config="validator.yaml", task="Validate", depends_on=["analyze"]),
    ],
)

result = await flow.execute(task="Run analysis")
```

## Error Handling

```yaml
steps:
  - name: risky_step
    agent: risky.yaml
    task: "Perform risky operation"
    retry: 3
    on_error: continue  # or "fail", "skip"
  
  - name: next_step
    agent: next.yaml
    task: "Continue processing"
    depends_on: [risky_step]
```

## Flow Hooks

```python
flow = Flow(
    name="my_flow",
    steps=[...],
    on_step_start=lambda step: print(f"Starting: {step.name}"),
    on_step_complete=lambda step, result: print(f"Completed: {step.name}"),
    on_error=lambda step, error: print(f"Error in {step.name}: {error}"),
)
```

## Best Practices

1. **Define dependencies explicitly** for correct ordering
2. **Use parallel steps** when tasks are independent
3. **Handle errors gracefully** with retry and on_error
4. **Keep flows simple** — complex logic belongs in agents
5. **Pass context via templates** using `{{step.result}}`

