# Power BI Agent Structure

This document describes the Power BI implementation's agent hierarchy and configuration. This is an example implementation using the framework.

## Hierarchical Structure

```
User
  ↓
Orchestrator (ManagerAgent)
  ├─ Uses: StrategicPlanner
  ├─ Workers: [react, math, powerbi]
  └─ Delegates to: pbi_manager (for Power BI tasks)
       ↓
pbi_manager (ManagerAgent)
  ├─ Uses: StrategicDecomposerPlanner
  ├─ Workers: [reader, editor, dax, validator]
  └─ Delegates to:
       ├─ schema_reader (Agent) - READ-ONLY queries
       ├─ schema_editor (Agent) - WRITE-ONLY modifications
       ├─ dax_specialist (Agent) - DAX measures/calculations
       └─ validator (Agent) - Model validation
```

## Agent Configurations

### Top Level

#### Orchestrator
**File:** `configs/agents/orchestrator.yaml`  
**Type:** ManagerAgent  
**Planner:** StrategicPlanner  
**Workers:**
- `react` → `configs/agents/react_assistant.yaml`
- `math` → `configs/agents/math_assistant.yaml`
- `powerbi` → `configs/agents/pbi_designer_manager.yaml`

**Role:** Routes user requests to appropriate domain managers

### Power BI Domain

#### pbi_manager
**File:** `configs/agents/pbi_designer_manager.yaml`  
**Type:** ManagerAgent  
**Planner:** StrategicDecomposerPlanner  
**Workers:**
- `reader` → `configs/agents/pbi/schema_reader.yaml` ✅ READ-ONLY
- `editor` → `configs/agents/pbi/schema_editor.yaml` ✅ WRITE-ONLY
- `dax` → `configs/agents/pbi/dax_specialist.yaml`
- `validator` → `configs/agents/pbi/validator.yaml`

**Role:** Orchestrates Power BI data model operations with read/write separation

**Key Feature:** Manager synthesis with expert analysis

### Power BI Workers

#### schema_reader ✅ **ACTIVE**
**File:** `configs/agents/pbi/schema_reader.yaml`  
**Type:** Agent  
**Planner:** ReActPlanner (with function calling)  
**Tools (READ-ONLY):**
- `list_tables`
- `list_columns`
- `list_relationships`
- `list_measures`
- `list_calculated_columns`

**Role:** READ-ONLY schema queries - no modification capabilities

**Security:** Cannot modify anything - principle of least privilege

#### schema_editor ✅ **ACTIVE**
**File:** `configs/agents/pbi/schema_editor.yaml`  
**Type:** Agent  
**Planner:** ReActPlanner (with function calling)  
**Tools (WRITE-ONLY):**
- **Add:** `add_column`, `add_relationship`, `add_measure`
- **Update:** `update_relationship`, `rename_column`
- **Remove:** `remove_column`, `remove_relationship`, `remove_measure`

**Role:** WRITE-ONLY modifications - no query capabilities

**Security:** Cannot read/list - must be intentional about modifications

#### dax_specialist
**File:** `configs/agents/pbi/dax_specialist.yaml`  
**Type:** Agent  
**Planner:** ReActPlanner  
**Tools:**
- `add_measure` - Create DAX measures
- `list_columns` - Check available columns
- `list_measures` - List existing measures

**Role:** DAX expert for measures and calculations

#### validator
**File:** `configs/agents/pbi/validator.yaml`  
**Type:** Agent  
**Planner:** SingleActionPlanner  
**Tools:**
- `validate_relationships` - Audit data model integrity

**Role:** Quality control and validation

## Architecture: Read/Write Separation

### Previous: Combined Agent
❌ `schema_combined` - had BOTH read and write tools (13 tools total)
- Problem: Violates least privilege principle
- Problem: Query operations had unnecessary write access

### Current: Separated Agents
✅ `schema_reader` - READ-ONLY (5 tools)  
✅ `schema_editor` - WRITE-ONLY (8 tools)

**Benefits:**
- 🔒 Security: Read operations cannot modify
- 🎯 Clarity: Intent is explicit in routing
- ⚡ Performance: Smaller tool sets = faster LLM decisions
- 🛡️ Safety: Modifications require explicit routing to editor

## Tool Organization

### Modular Structure

```
bi_tools/tools/
├── relationship/
│   ├── add_relationship.py
│   ├── update_relationship.py
│   ├── remove_relationship.py
│   ├── list_relationships.py
│   ├── validate_relationships.py
│   └── cleanup_relationship_format.py
├── table/
│   └── list_tables.py
├── column/
│   ├── add_column.py
│   ├── remove_column.py
│   ├── rename_column.py
│   ├── list_columns.py
│   └── list_calculated_columns.py
├── measure/
│   ├── add_measure.py
│   ├── remove_measure.py
│   └── list_measures.py
└── utility/
    ├── calculator.py
    └── python_interpreter.py
```

## Key Features

### 1. Hierarchical Delegation
- Orchestrator → Manager → Worker → Tool
- Each level has specific responsibilities
- Clear separation of concerns

### 2. Shared Memory
- All agents share conversation history via `MessageStoreMemory`
- Namespace: `${JOB_ID}` (per-request isolation)
- Context propagation through hierarchy

### 3. Phoenix Tracing
- Hierarchical span tracking
- Full observability of delegation chains
- Metrics: tokens, costs, latency

### 4. Manager Synthesis
- pbi_manager adds expert analysis layer
- Pattern detection (star schema, snowflake)
- Best practice recommendations

### 5. Async-Safe Context
- Uses `contextvars` for request isolation
- Thread-safe for concurrent users
- Proper context propagation to thread pools

## Configuration Guidelines

### When to Edit:

1. **Add New Tool:**
   - Create tool file in appropriate `bi_tools/tools/` subdirectory
   - Create YAML config in `configs/tools/`
   - Add to appropriate worker agent YAML (reader or editor)

2. **Add New Worker:**
   - Create worker agent YAML in `configs/agents/pbi/`
   - Add to `pbi_designer_manager.yaml` workers list
   - Update strategic planner prompt

3. **Change Planner:**
   - Modify `planner.type` in agent YAML
   - Update `planner.config` with appropriate settings

### What NOT to Change:

❌ Don't create duplicate agent configs (use existing ones)  
❌ Don't bypass the manager hierarchy (always delegate through managers)  
❌ Don't mix read/write tools in same agent (use separation)

## Summary

**Active Agent Configs:** 6 total
- 1 Orchestrator
- 1 PBI Manager
- 4 PBI Workers (schema_reader, schema_editor, dax, validator)

**Tools:** Modular tools across 5 categories

**Architecture:** Clean hierarchical delegation with shared memory and full observability

**Status:** ✅ Production-ready, confusion-free structure

