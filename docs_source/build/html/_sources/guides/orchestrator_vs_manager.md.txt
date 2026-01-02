# Orchestrator vs Manager: Key Differences

## Overview

Both Orchestrator and Managers are `ManagerAgent` instances, but they operate at different levels of the hierarchy with distinct roles, responsibilities, and behaviors.

## Hierarchy

```
User Request
    ↓
┌─────────────────────────────────────┐
│ ORCHESTRATOR (Top-Level)            │
│ - Strategic Planning                │
│ - Domain Routing                    │
└─────────────────────────────────────┘
    ↓ delegates to domain managers
┌─────────────────────────────────────┐
│ MANAGERS (Domain-Specific)          │
│ - Tactical Execution                │
│ - Worker Coordination               │
└─────────────────────────────────────┘
    ↓ delegates to worker agents
┌─────────────────────────────────────┐
│ WORKER AGENTS                       │
│ - Tool Execution                    │
│ - Task Completion                   │
└─────────────────────────────────────┘
```

## Orchestrator - Strategic Coordinator

### Role
- **Top-level coordinator** that routes user intent to specialized domain managers
- Creates **high-level strategic plans** with **phases**
- Makes **domain-level routing decisions**

### Configuration

**Planner:**
- **Type:** `StrategicPlanner`
- **Purpose:** Creates multi-phase execution plans
- **Model:** Typically uses more powerful models (e.g., `gpt-4o`) for strategic thinking

**Workers:**
- Domain Managers (not worker agents)
- Examples: `powerbi-analysis`, `powerbi-designer`, `math-manager`

**Planning Behavior:**
- Creates **phases** (not steps)
- Focuses on **outcome-focused phases** without tool names
- Uses **context** to avoid redundant actions
- Makes **worker selection** based on task type

**Example Plan Structure:**
```json
{
  "plan": {
    "phases": [
      {
        "name": "Analyze SQL Query",
        "worker": "powerbi-analysis",
        "goals": "Review the SQL query artifact to understand its logic and structure",
        "notes": "SQL query details are provided in metadata file"
      },
      {
        "name": "Synthesize M Query Changes",
        "worker": "powerbi-designer",
        "goals": "Translate the analyzed SQL logic into M Query",
        "notes": "Ensure M Query reflects equivalent logic"
      }
    ],
    "primary_worker": "powerbi-analysis",
    "rationale": "Analysis first, then translation"
  }
}
```

**Key Characteristics:**
- ✅ Creates **phases** (high-level, outcome-focused)
- ✅ Routes to **domain managers** (not worker agents)
- ✅ Uses **powerful LLM** for strategic thinking
- ✅ **No tool execution** - only planning and delegation
- ✅ **Broad scope** - handles all domains
- ✅ Focuses on **WHAT** needs to be done, not HOW

## Manager - Tactical Executor

### Role
- **Domain-specific coordinators** that execute orchestrator phases
- Creates **detailed execution steps** for worker agents
- Manages **sequential step execution** within their domain

### Configuration

**Planner:**
- **Type:** `StrategicDecomposerPlanner` or `WorkerRouterPlanner`
- **Purpose:** Breaks orchestrator phases into actionable steps
- **Model:** Typically uses efficient models (e.g., `gpt-4o-mini`) for tactical execution
- **Special:** Has `manager_worker_key` to identify which orchestrator phase is for this manager

**Workers:**
- Specialized Worker Agents (not other managers)
- Examples: `model-analysis`, `schema-editor`, `dax-specialist`

**Planning Behavior:**
- Creates **steps** (not phases) - detailed, actionable
- Incorporates **orchestrator phase input** + **previous manager outputs**
- Makes **worker selection** within domain specialization
- Executes steps **sequentially** with result passing

**Example Step Plan Structure:**
```json
{
  "phases": [
    {
      "name": "List SQL Sources",
      "worker": "model-analysis",
      "goals": "Identify all tables with SQL Server sources",
      "notes": "Need to find source tables before analysis"
    },
    {
      "name": "Extract SQL Query",
      "worker": "model-analysis",
      "goals": "Get the SQL query for the identified table",
      "notes": "Use previous step output"
    },
    {
      "name": "Analyze SQL Structure",
      "worker": "model-analysis",
      "goals": "Parse and analyze SQL query structure and logic",
      "notes": "Build on extracted query"
    }
  ],
  "primary_worker": "model-analysis",
  "rationale": "Sequential discovery → extraction → analysis"
}
```

**Key Characteristics:**
- ✅ Creates **steps** (detailed, actionable)
- ✅ Routes to **worker agents** (not other managers)
- ✅ Uses **efficient LLM** for tactical execution
- ✅ **Can execute manager-level tools** (discovery, validation)
- ✅ **Narrow scope** - handles one domain only
- ✅ Focuses on **HOW** to accomplish the orchestrator's phase
- ✅ **Synthesis capability** - formats worker results into user-friendly responses

## Key Behavioral Differences

| Aspect | Orchestrator | Manager |
|--------|-------------|---------|
| **Planning Level** | Strategic (high-level phases) | Tactical (detailed steps) |
| **Planning Term** | Creates **phases** | Creates **steps** |
| **Planner Type** | `StrategicPlanner` | `StrategicDecomposerPlanner` or `WorkerRouterPlanner` |
| **LLM Model** | More powerful (e.g., `gpt-4o`) | Efficient (e.g., `gpt-4o-mini`) |
| **Workers** | Domain Managers | Worker Agents |
| **Scope** | All domains | Single domain |
| **Tool Execution** | ❌ No | ✅ Yes (discovery, validation) |
| **Synthesis** | Optional | ✅ Yes (required) |
| **Context** | Data model context | Orchestrator phase + previous outputs |
| **Focus** | WHAT needs to be done | HOW to do it |

## Execution Flow Example

```
User: "Analyze SQL query and update the M Query"

┌─────────────────────────────────────────────────────────────┐
│ ORCHESTRATOR (Strategic Level)                              │
├─────────────────────────────────────────────────────────────┤
│ StrategicPlanner creates plan with 2 PHASES:                │
│                                                              │
│ Phase 1: "Analyze SQL Query"                                │
│   → Worker: powerbi-analysis                                 │
│   → Goals: "Review SQL query to understand logic"           │
│                                                              │
│ Phase 2: "Update M Query"                                   │
│   → Worker: powerbi-designer                                │
│   → Goals: "Translate SQL logic to M Query"                 │
└─────────────────────────────────────────────────────────────┘
    ↓ delegates Phase 1
┌─────────────────────────────────────────────────────────────┐
│ PBI ANALYSIS MANAGER (Tactical Level)                       │
├─────────────────────────────────────────────────────────────┤
│ StrategicDecomposerPlanner creates plan with 3 STEPS:       │
│                                                              │
│ Step 1: "List SQL Sources"                                  │
│   → Worker: model-analysis                                  │
│   → Goals: "Find tables with SQL Server sources"            │
│                                                              │
│ Step 2: "Extract SQL Query"                                │
│   → Worker: model-analysis                                  │
│   → Goals: "Get SQL query from metadata"                    │
│   → Input: Previous step output                             │
│                                                              │
│ Step 3: "Analyze SQL Structure"                             │
│   → Worker: model-analysis                                  │
│   → Goals: "Parse and understand SQL logic"                 │
│   → Input: Extracted query + previous results               │
└─────────────────────────────────────────────────────────────┘
    ↓ delegates Step 1, 2, 3 sequentially
┌─────────────────────────────────────────────────────────────┐
│ WORKER AGENTS (Execution Level)                             │
├─────────────────────────────────────────────────────────────┤
│ model-analysis executes tools:                              │
│   - list_sql_sources → returns table names                  │
│   - get_sql_query → returns SQL text                        │
│   - sql_analyzer → returns parsed structure                 │
└─────────────────────────────────────────────────────────────┘
    ↓ results flow back up
┌─────────────────────────────────────────────────────────────┐
│ PBI ANALYSIS MANAGER synthesizes results                    │
│ → "Found SQL query in table X, analyzed structure"          │
└─────────────────────────────────────────────────────────────┘
    ↓ orchestrator receives Phase 1 result
    ↓ delegates Phase 2 to PBI DESIGNER MANAGER
┌─────────────────────────────────────────────────────────────┐
│ PBI DESIGNER MANAGER receives:                              │
│ - Orchestrator Phase 2 input                                │
│ - Previous manager (Analysis) output                         │
└─────────────────────────────────────────────────────────────┘
```

## Code-Level Differences

### Orchestrator Planning
```python
# StrategicPlanner creates phases
plan = {
    "plan": {
        "phases": [
            {"name": "Phase 1", "worker": "powerbi-analysis", "goals": "..."},
            {"name": "Phase 2", "worker": "powerbi-designer", "goals": "..."}
        ]
    }
}
```

### Manager Planning
```python
# StrategicDecomposerPlanner creates steps
# Receives orchestrator phase and creates local steps
local_plan = {
    "phases": [  # Note: called "phases" in structure, but represents "steps"
        {"name": "Step 1", "worker": "model-analysis", "goals": "..."},
        {"name": "Step 2", "worker": "model-analysis", "goals": "..."}
    ]
}
```

## Synthesis

### Orchestrator
- Optional synthesis of manager results
- Higher-level summary across domains

### Manager
- **Required synthesis** of worker results
- Formats worker outputs into user-friendly responses
- Validates response completeness
- Domain-specific formatting

## Summary

**Orchestrator** = **Strategic Thinker**
- Sees the big picture
- Plans at high level (phases)
- Routes to domain managers
- Uses powerful LLM for complex reasoning

**Manager** = **Tactical Executor**
- Focuses on domain expertise
- Plans in detail (steps)
- Routes to worker agents
- Uses efficient LLM for execution
- Synthesizes worker results

Both are essential parts of a hierarchical AI system that balances strategic planning with efficient execution!

