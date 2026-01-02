---
title: Strategic Planning Architecture
---

# Strategic Planning Architecture

## Overview

The framework provides a **Strategic Planning** pattern that enables orchestrators to create multi-step execution plans upfront, reducing redundant LLM calls and improving context passing through the agent hierarchy.

## The Problem with Simple Routing

Without strategic planning, each level in the hierarchy makes routing decisions independently:

```
User: "Add relationship, then validate"
    ↓
Orchestrator: "Route to worker-A" → route
    ↓
Manager: "Route to worker-B" → route  
    ↓
Worker: "What exactly do I do?" → re-plan everything
```

**Issues:**
- ❌ Multiple LLM calls just for routing
- ❌ No real planning until worker level
- ❌ Workers must reinvent the plan
- ❌ No context passing between levels

## Strategic Planning Solution

With `StrategicPlanner`, the orchestrator creates a complete execution plan upfront:

```
User: "Add relationship between Sales and Customers, then validate"
    ↓
Orchestrator (StrategicPlanner):
  - Analyzes task deeply
  - Creates multi-step plan:
      Step 1: Verify tables exist
      Step 2: Find key columns
      Step 3: Create relationship
      Step 4: Validate model
  - Identifies primary worker
  - Delegates with full plan + context
    ↓
Manager (receives strategic plan):
  - Uses plan to execute steps systematically
  - Each step has clear context
  - Synthesizes results
    ↓
Workers: Execute focused actions with clear context
    ↓
User ← Synthesized, analyzed result
```

**Benefits:**
- ✅ Single planning LLM call at orchestrator level
- ✅ Rich context passing to managers and workers
- ✅ Better reasoning at each level
- ✅ Traceable plans in logs

## Framework Components

### 1. StrategicPlanner

The `StrategicPlanner` creates execution plans and delegates to managers with full context.

```python
from agent_framework.components.planners import StrategicPlanner
from agent_framework.gateways.inference import OpenAIGateway

planner = StrategicPlanner(
    worker_keys=["worker-a", "worker-b", "worker-c"],
    inference_gateway=OpenAIGateway(model="gpt-4"),
    planning_prompt="Your custom planning prompt..."
)

# Planner analyzes task and creates plan
result = planner.plan(task="Complex multi-step task", history=[])

# Returns Action with strategic_plan embedded in tool_args
# result = Action(
#     tool_name="primary_worker",
#     tool_args={
#         "strategic_plan": {
#             "phases": [...],
#             "primary_worker": "worker-a",
#             "rationale": "..."
#         },
#         "original_task": "Complex multi-step task"
#     }
# )
```

**How it works:**
1. Analyzes the task using LLM
2. Creates a structured plan with phases/steps
3. Identifies primary worker(s)
4. Returns `Action` with plan embedded in `tool_args`

### 2. Plan Structure

The strategic plan is a dictionary with this structure:

```python
{
    "phases": [  # or "steps" for legacy format
        {
            "name": "Phase name",
            "worker": "worker-key",
            "goals": "What to achieve",
            "notes": "Additional context"
        },
        ...
    ],
    "primary_worker": "worker-key",
    "rationale": "Why this plan will succeed",
    "parallel_workers": ["worker-1", "worker-2"]  # Optional
}
```

### 3. ManagerAgent Integration

`ManagerAgent` automatically extracts and uses strategic plans:

```python
from agent_framework import ManagerAgent

manager = ManagerAgent(
    planner=manager_planner,
    memory=memory,
    workers={"worker-a": worker_a, "worker-b": worker_b},
    policies=policies
)

# When orchestrator delegates with strategic plan:
# 1. StrategicPlanner returns Action with strategic_plan in tool_args
# 2. ManagerAgent.run() automatically extracts it:
result = await manager.run(task="...")

# Inside ManagerAgent:
# - Extracts strategic_plan from Action.tool_args
# - Adds plan to memory as STRATEGIC_PLAN entry
# - Passes plan to workers via context
# - Workers can access plan to understand overall goal
```

**Manager behavior:**
- Automatically extracts `strategic_plan` from `Action.tool_args`
- Adds plan to memory as `{"type": "strategic_plan", "content": plan}`
- Makes plan available to workers via context
- Workers can use plan to understand the overall objective

### 4. StrategicDecomposerPlanner (Optional)

For managers that need to decompose orchestrator phases into worker-specific steps:

```python
from agent_framework.components.planners import StrategicDecomposerPlanner

manager_planner = StrategicDecomposerPlanner(
    worker_keys=["local-worker-1", "local-worker-2"],
    inference_gateway=llm_gateway,
    manager_worker_key="manager-name"
)

# This planner:
# - Reads strategic plan from orchestrator (via context or history)
# - Decomposes high-level phases into concrete worker steps
# - Creates detailed execution plan for local workers
```

## Usage Pattern

### Orchestrator with StrategicPlanner

```python
from agent_framework import ManagerAgent
from agent_framework.components.planners import StrategicPlanner
from agent_framework.gateways.inference import OpenAIGateway

# Create orchestrator with strategic planner
orchestrator = ManagerAgent(
    planner=StrategicPlanner(
        worker_keys=["manager-a", "manager-b"],
        inference_gateway=OpenAIGateway(model="gpt-4"),
        planning_prompt="Create detailed execution plans..."
    ),
    memory=memory,
    workers={"manager-a": manager_a, "manager-b": manager_b},
    policies=policies
)

# Run orchestrator
result = await orchestrator.run(task="Complex multi-step task")
```

### Manager Receives Strategic Plan

The manager automatically receives and uses the strategic plan:

```python
# Manager doesn't need special setup
manager = ManagerAgent(
    planner=manager_planner,  # Can be any planner
    memory=memory,
    workers={...},
    policies=policies
)

# When called by orchestrator with strategic plan:
# - Plan is extracted from Action.tool_args
# - Added to memory automatically
# - Available to workers via context
result = await manager.run(task="...")
```

### Worker Access to Strategic Plan

Workers can access the strategic plan via memory or context:

```python
# In worker's planner or tools:
history = memory.get_history()

# Find strategic plan in history
strategic_plan = None
for entry in reversed(history):
    if entry.get("type") == "strategic_plan":
        strategic_plan = entry.get("content")
        break

# Use plan to understand overall objective
if strategic_plan:
    phases = strategic_plan.get("phases", [])
    current_phase = phases[current_phase_index]
    # Execute with context from plan
```

## Plan Format

### Orchestrator Format (StrategicPlanner)

```json
{
  "plan": {
    "phases": [
      {
        "name": "Phase 1",
        "worker": "manager-a",
        "goals": "Verify prerequisites",
        "notes": "Check system state"
      },
      {
        "name": "Phase 2",
        "worker": "manager-b",
        "goals": "Execute main operation",
        "notes": "Use validated inputs"
      }
    ],
    "primary_worker": "manager-a",
    "rationale": "Sequential execution ensures data integrity",
    "task_type": "analysis"
  }
}
```

### Manager Format (StrategicDecomposerPlanner)

```json
{
  "phases": [
    {
      "name": "Step 1",
      "worker": "local-worker-1",
      "goals": "Execute specific operation",
      "notes": "Context from orchestrator phase"
    },
    {
      "name": "Step 2",
      "worker": "local-worker-2",
      "goals": "Validate results",
      "notes": "Build on step 1 output"
    }
  ],
  "primary_worker": "local-worker-1",
  "rationale": "Local execution plan based on orchestrator phase"
}
```

## Comparison with Simple Routing

| Feature | Simple Routing | Strategic Planning |
|---------|----------------|-------------------|
| Planning | None (just routes) | Deep multi-step planning |
| LLM Calls | 2-3 (routing cascade) | 1 (upfront planning) |
| Context | None | Rich, step-by-step |
| Best For | Simple tasks | Complex workflows |
| Traceability | Low | High (visible plan) |

## Benefits

✅ **Single Planning LLM Call**: Orchestrator plans everything upfront, eliminating redundant routing calls

✅ **Rich Context Passing**: Workers receive the full strategic context, not just task descriptions

✅ **Better Reasoning**: Each level focuses on its responsibility:
- **Orchestrator**: Strategic thinking & planning
- **Manager**: Tactical execution & synthesis  
- **Worker**: Operational execution

✅ **Traceable Plans**: Logs show the complete plan and execution progress

✅ **Flexibility**: Works with any planner at manager/worker levels

## When to Use

**Use `StrategicPlanner` when:**
- Tasks are complex with multiple steps
- You need context passing between agent levels
- You want to reduce LLM calls
- Tasks have dependencies between steps

**Use simple routing when:**
- Tasks are simple and single-step
- No context passing needed
- Minimal overhead is required

## Configuration Example

```python
from agent_framework.components.planners import StrategicPlanner
from agent_framework.gateways.inference import OpenAIGateway

strategic_planner = StrategicPlanner(
    worker_keys=["manager-1", "manager-2"],
    inference_gateway=OpenAIGateway(model="gpt-4"),
    planning_prompt="""
    You are a strategic planner. Analyze tasks and create execution plans.
    
    Return JSON with:
    {
      "plan": {
        "phases": [
          {"name": "...", "worker": "...", "goals": "...", "notes": "..."}
        ],
        "primary_worker": "...",
        "rationale": "..."
      }
    }
    """,
    history_filter=OrchestratorHistoryFilter()  # Optional: filter history
)
```

## Summary

`StrategicPlanner` transforms the orchestrator from a simple router into an intelligent planner that:
- Creates comprehensive execution plans upfront
- Passes rich context to managers and workers
- Reduces redundant LLM calls
- Enables better hierarchical reasoning
- Provides traceable execution paths

This is a framework capability that enables more efficient and intelligent agent hierarchies.
