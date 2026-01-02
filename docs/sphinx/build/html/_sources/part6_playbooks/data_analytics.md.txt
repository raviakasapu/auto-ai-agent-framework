# Data Analytics Playbook

Pattern for building agent systems that interact with data models, BI tools, and analytics platforms.

## Use Cases

- Power BI model management
- Tableau dashboard authoring
- Looker LookML editing
- dbt model generation
- Data catalog navigation

## Agent Hierarchy

```
┌─────────────────────────────────────────────────────────────┐
│ ANALYTICS ORCHESTRATOR                                      │
│ - Natural language intent clarification                     │
│ - Route to analysis or authoring managers                   │
│ - Maintain data model awareness                             │
└─────────────────────────────────────────────────────────────┘
         │
         ├──────────────────────────────────────────┐
         │                                          │
         ▼                                          ▼
┌─────────────────────────────┐    ┌─────────────────────────────┐
│ ANALYSIS MANAGER            │    │ AUTHORING MANAGER           │
│ - Schema exploration        │    │ - Metric creation           │
│ - Query analysis            │    │ - Relationship editing      │
│ - Validation                │    │ - Schema modifications      │
└─────────────────────────────┘    └─────────────────────────────┘
         │                                          │
         ▼                                          ▼
┌─────────────────────────────┐    ┌─────────────────────────────┐
│ Read-only Workers           │    │ Write-capable Workers       │
│ - list_tables               │    │ - add_measure               │
│ - get_column_stats          │    │ - update_relationship       │
│ - validate_query            │    │ - modify_schema             │
└─────────────────────────────┘    └─────────────────────────────┘
```

## Tool Categories

### Schema Tools
- `list_tables` / `list_columns` / `list_relationships`
- `get_table_metadata` / `get_column_stats`
- `schema_diff` / `validate_schema`

### Query Tools
- `get_query_definition` / `analyze_query`
- `validate_query_syntax` / `optimize_query`
- `execute_query` (with HITL)

### Metric Tools
- `list_measures` / `get_measure_expression`
- `add_measure` / `update_measure` / `remove_measure`
- `validate_measure` / `format_measure`

### Connection Tools
- `list_data_sources` / `get_connection_string`
- `test_connection` / `refresh_metadata`

## Policy Patterns

### Access Control
```yaml
# Analysis workers: read-only tools
analysis_worker:
  tools: [list_tables, list_columns, validate_query]

# Authoring workers: read + write tools
authoring_worker:
  tools: [list_tables, add_measure, update_measure]
```

### HITL for Writes
```yaml
policies:
  hitl:
    type: DefaultHITLPolicy
    config:
      enabled: true
      scope: writes
      write_tools:
        - add_measure
        - update_relationship
        - modify_schema
```

### Validation Before Write
```yaml
# In planning prompt
"Before any write operation, always validate:
1. Check existing schema for conflicts
2. Validate syntax (DAX/SQL/M Query)
3. Confirm no breaking changes"
```

## Context Services

### Data Model Service
- Provides current schema state
- Request-scoped via context manager
- Caches metadata for efficiency

### Manifest Export
Generate AI-optimized summaries:

```text
=== Analytics Model Manifest ===
Tables: 12 (5 facts, 7 dimensions)
Measures: 45
Relationships: 11

TABLES:
- FactSales (fact, 15 columns, 12 measures)
- DimCustomer (dimension, 8 columns)
...
```

### Schema Awareness in Prompts
Include manifest in orchestrator prompt:

```yaml
planning_prompt: |
  You have access to the current data model:
  
  {{ MODEL_MANIFEST }}
  
  Use this to avoid redundant operations and 
  ensure compatibility with existing schema.
```

## Reference Implementation

For a complete example, see the [Power BI Dashboard Editor Implementation](/powerbi_impl/index):

- [Runtime Integration](/powerbi_impl/runtime_integration) — FastAPI, context setup
- [Agent Stack](/powerbi_impl/agent_stack) — Full hierarchy configuration
- [Data Services](/powerbi_impl/data_services) — KG integration
- [Tool Coverage](/powerbi_impl/tools_coverage) — Complete tool inventory
- [Observability](/powerbi_impl/observability_approvals) — Tracing and HITL flows

