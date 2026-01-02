# Agent & Policy Stack

This chapter details the Power BI agent hierarchy: orchestrator, managers, and workers.

## Architecture Overview

```
User Request
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│ ORCHESTRATOR (ManagerAgent)                                 │
│ configs/agents/orchestrator.yaml                            │
│                                                             │
│ Planner: StrategicPlanner                                   │
│ Model: gpt-5.1 (strategic)                                  │
│ Workers: [powerbi-chat, powerbi-analysis, powerbi-designer] │
└─────────────────────────────────────────────────────────────┘
    │
    ├─────────────────────────────────────────────────────────┐
    │                                                         │
    ▼                                                         ▼
┌─────────────────────────────────┐  ┌─────────────────────────────────┐
│ PBI Analysis Manager            │  │ PBI Designer Manager            │
│ pbi_analysis_manager.yaml       │  │ pbi_designer_manager.yaml       │
│                                 │  │                                 │
│ Planner: ManagerScriptPlanner   │  │ Planner: ManagerScriptPlanner   │
│ Model: gpt-4o-mini              │  │ Model: gpt-4o-mini              │
│ Workers:                        │  │ Workers:                        │
│  - model-structure-analyzer     │  │  - model-structure-editor       │
│  - sql-analyzer                 │  │  - dax-editor                   │
│  - validator                    │  │  - mquery-editor                │
│  - dax-analyzer                 │  │  - sql-editor                   │
│  - mquery-analyzer              │  │  - validator                    │
└─────────────────────────────────┘  └─────────────────────────────────┘
    │                                         │
    ▼                                         ▼
┌─────────────────────────────────┐  ┌─────────────────────────────────┐
│ WORKER AGENTS (Agent)           │  │ WORKER AGENTS (Agent)           │
│ ReActPlanner + Domain Tools     │  │ ReActPlanner + Domain Tools     │
└─────────────────────────────────┘  └─────────────────────────────────┘
```

## Orchestrator

**File:** `configs/agents/orchestrator.yaml`

### Configuration Highlights

```yaml
apiVersion: agent.framework/v2
kind: ManagerAgent

metadata:
  name: Orchestrator
  description: Top-level orchestrator that routes user intent to specialized workers.

resources:
  inference_gateways:
    # Strategic planning - powerful model
    - name: openai-strategic
      type: OpenAIGateway
      config:
        model: ${OPENAI_STRATEGIC_MODEL:-gpt-5.1}

spec:
  policies:
    $preset: manager_with_followups
    follow_up:
      config:
        max_phases: 10

  planner:
    type: StrategicPlanner
    config:
      inference_gateway: openai-strategic
      worker_keys: [powerbi-chat, powerbi-analysis, powerbi-designer]
      planning_prompt: |
        You are Clarifier + Orchestrator...
        
        Available workers:
        - powerbi-chat: General-purpose chat (NOT data model questions)
        - powerbi-analysis: Read-only analysis of the CURRENT data model
        - powerbi-designer: Model authoring (tables, columns, measures, DAX)
        
        WORKER SELECTION RUBRIC:
        - powerbi-chat → Off-topic, general Power BI concepts
        - powerbi-analysis → ALL data model questions
        - powerbi-designer → Any authoring or change

  memory:
    type: SharedInMemoryMemory
    config:
      namespace: ${JOB_ID}
      agent_key: orchestrator

  workers:
    - name: powerbi-chat
      agent_config_path: configs/agents/chat_assistant.yaml
    - name: powerbi-analysis
      agent_config_path: configs/agents/pbi_analysis_manager.yaml
    - name: powerbi-designer
      agent_config_path: configs/agents/pbi_designer_manager.yaml
```

### Key Features

1. **Strategic Planning**: Uses `StrategicPlanner` with powerful model
2. **Data Model Context**: Receives KG manifest for informed planning
3. **Worker Routing**: Routes to chat, analysis, or designer managers
4. **Proportional Planning**: Matches plan complexity to question complexity

## PBI Analysis Manager

**File:** `configs/agents/pbi_analysis_manager.yaml`

### Configuration Highlights

```yaml
kind: ManagerAgent

metadata:
  name: PBI_Analysis_Manager
  description: "Comprehensive analysis manager for Power BI models"

spec:
  planner:
    type: ManagerScriptPlanner
    config:
      default_worker: model-structure-analyzer
      manager_worker_key: powerbi-analysis
      inference_gateway: openai-manager
      worker_specs:
        - worker: model-structure-analyzer
          description: "Read-only model structure explorer"
          tools:
            - name: list_tables
            - name: list_columns
            - name: list_relationships
            - name: list_partitions
            - name: get_partition_source
            - name: list_measures
        - worker: sql-analyzer
          description: "SQL analysis specialist"
          tools:
            - name: list_sql_sources
            - name: get_sql_query
            - name: sql_analyzer
            - name: validate_sql
        - worker: validator
          description: "Model validation expert"
          tools:
            - name: validate_relationships
            - name: validate_dax
            - name: validate_mquery
        - worker: dax-analyzer
          description: "Read-only DAX analysis"
          tools:
            - name: list_measures
            - name: get_measure_expression
            - name: validate_dax
        - worker: mquery-analyzer
          description: "Read-only M Query analyst"
          tools:
            - name: list_mquery
            - name: validate_mquery

  synthesizer_agent: configs/agents/pbi/synthesizer_agent.yaml

  workers:
    - name: model-structure-analyzer
      agent_config_path: configs/agents/pbi/model_structure_analyzer.yaml
    - name: sql-analyzer
      agent_config_path: configs/agents/pbi/sql_analyzer.yaml
    - name: validator
      agent_config_path: configs/agents/pbi/validator.yaml
    - name: dax-analyzer
      agent_config_path: configs/agents/pbi/dax_analyzer.yaml
    - name: mquery-analyzer
      agent_config_path: configs/agents/pbi/mquery_analyzer.yaml
```

### Key Features

1. **Script Planning**: Creates deterministic tool scripts for workers
2. **Worker Catalog**: Explicit tool specs for each worker
3. **Read-Only Workers**: Analysis workers have no write tools
4. **Synthesizer**: Separate agent for result aggregation

## Worker Agents

### Model Structure Analyzer

**File:** `configs/agents/pbi/model_structure_analyzer.yaml`

```yaml
kind: Agent

metadata:
  name: ModelStructureAnalyzer
  description: Read-only analysis of Power BI model structure

spec:
  policies:
    $preset: simple
    termination:
      config:
        max_iterations: 10
        terminal_tools: [complete_task]

  planner:
    type: ReActPlanner
    config:
      inference_gateway: openai-structure
      use_function_calling: true
      max_parallel_tool_calls: 3
      terminal_tools: [complete_task]
      system_prompt: |
        You are a Power BI model structure analyzer.
        
        IMMEDIATE COMPLETION RULE:
        Once you receive a tool result that answers the user's question,
        IMMEDIATELY call complete_task.
        
        SIMPLE TASK PATTERNS (1 tool + complete_task):
        - "list tables" → list_tables → complete_task
        - "list columns for X" → list_columns(table=X) → complete_task
        - "show relationships" → list_relationships → complete_task

  tools:
    - list_tables
    - list_columns
    - list_relationships
    - list_partitions
    - list_measures
    - complete_task
```

### DAX Analyzer (Read-Only)

**File:** `configs/agents/pbi/dax_analyzer.yaml`

```yaml
kind: Agent

metadata:
  name: DAXAnalyzer
  description: Read-only DAX analysis and optimization advisor

spec:
  planner:
    type: ReActPlanner
    config:
      system_prompt: |
        You are a DAX analysis expert.
        Focus on reading and analyzing measures, NOT modifying.

  # READ-ONLY tools only - no add_measure or update_measure
  tools:
    - list_measures
    - get_measure_expression
    - validate_dax
    - convert_dax
    - complete_task
```

### DAX Editor (Read+Write)

**File:** `configs/agents/pbi/dax_editor.yaml`

```yaml
kind: Agent

metadata:
  name: DAXEditor
  description: DAX authoring with read+write capabilities

spec:
  tools:
    - list_measures
    - get_measure_expression
    - add_measure         # Write capability
    - update_measure      # Write capability
    - remove_measure      # Write capability
    - validate_dax
    - convert_dax
    - complete_task
```

## Tool Access Restriction

The implementation uses **separate worker configurations** for access control:

| Manager | Worker | Access |
|---------|--------|--------|
| `pbi-analysis` | `dax-analyzer` | Read-only |
| `pbi-designer` | `dax-editor` | Read+write |
| `pbi-analysis` | `model-structure-analyzer` | Read-only |
| `pbi-designer` | `model-structure-editor` | Read+write |

This ensures that the analysis manager cannot accidentally modify the data model.

## Policies

### Orchestrator Policies

```yaml
policies:
  $preset: manager_with_followups
  follow_up:
    type: DefaultFollowUpPolicy
    config:
      enabled: true
      max_phases: 10
      stop_on_completion: true
```

### Worker Policies

```yaml
policies:
  $preset: simple
  termination:
    type: DefaultTerminationPolicy
    config:
      max_iterations: 10
      terminal_tools: [complete_task]
      on_max_iterations: error
```

## Memory Configuration

All agents share the same namespace for context propagation:

```yaml
memory:
  type: SharedInMemoryMemory
  config:
    namespace: ${JOB_ID}        # Same for all agents
    agent_key: <unique_key>     # Different per agent
```

This enables:
- Conversation history sharing
- Global updates visibility
- Cross-agent context awareness

## Subscribers

All agents include Phoenix for observability:

```yaml
subscribers:
  - name: phoenix
    type: PhoenixSubscriber
    config:
      endpoint: ${PHOENIX_ENDPOINT:-http://localhost:6006/v1/traces}
      service_name: <agent_name>
```

## Summary

The Power BI implementation demonstrates:

- ✅ **Hierarchical agents**: Orchestrator → Manager → Worker
- ✅ **Strategic planning**: Powerful model for routing
- ✅ **Script planning**: Deterministic worker execution
- ✅ **Access control**: Separate read/write workers
- ✅ **Shared memory**: Context propagation via namespace
- ✅ **Observability**: Phoenix tracing on all agents

