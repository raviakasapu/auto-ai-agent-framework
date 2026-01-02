# Tool Access Restriction Strategy

## Problem

Workers have tools defined in their YAML configs. When a manager uses a worker, the worker has access to ALL its tools. This creates a security/access control issue:

- **`pbi-analysis-manager`** should only do read-only analysis
- **`dax-specialist`** has both read tools (list_measures, get_measure_expression) AND write tools (add_measure, update_measure)
- When `pbi-analysis-manager` uses `dax-specialist`, it could potentially use write tools

## Solution: Separate Worker Configs

### Approach: Create Read-Only Worker Variants

For workers that need different access levels based on manager context, create separate worker configs:

1. **`dax_analyzer.yaml`** - Read-only DAX analysis (used by `pbi-analysis-manager`)
   - Tools: list_measures, get_measure_expression, validate_dax, convert_dax (analysis mode)
   - NO write tools (add_measure, update_measure)

2. **`dax_editor.yaml`** - Read+Write DAX operations (used by `pbi-designer-manager`)
   - Tools: All read tools + add_measure, update_measure

### Current Worker Assignments

#### pbi-analysis-manager (ALL READ-ONLY):
- `model-structure-analyzer` → Read-only tools only
- `sql-analyzer` → Read-only tools only
- `validator` → Validation tools only (read-only)
- `dax-analyzer` → **Uses `dax_analyzer.yaml`** (read-only, no write tools)
- `mquery-analyzer` → Read-only tools only

#### pbi-designer-manager (READ+WRITE):
- `model-structure-editor` → Read+Write tools
- `model-structure-analyzer` → Read-only tools (for discovery)
- `dax-editor` → **Uses `dax_editor.yaml`** (read+write tools)
- `validator` → Validation tools (read-only)
- `sql-analyzer` → Read-only tools (for analysis)
- `mquery-analyzer` → Read-only tools (for analysis)

## Alternative Solutions (Not Implemented)

### Option 2: PolicyEngine-Based Restriction

Use `PolicyEngine` to deny write tools when called from analysis manager context:

```yaml
# configs/policies/powerbi.yaml
deny:
  - tool: add_measure
    when:
      manager_type: "analysis"  # Would need to pass context
    message: "Write operations not allowed in analysis mode"
```

**Limitations:**
- Requires passing manager context to PolicyEngine
- Not currently supported in framework
- Would need framework changes

### Option 3: Tool Filtering at Worker Load Time

Filter tools when loading worker for specific manager:

```python
# In AgentFactory
if manager_type == "analysis":
    # Remove write tools from worker
    worker.tools = {k: v for k, v in worker.tools.items() 
                    if k not in WRITE_TOOLS}
```

**Limitations:**
- Requires framework changes
- Less explicit than separate configs
- Harder to maintain

### Option 4: System Prompt Instructions

Instruct worker via system prompt to only use read tools:

```yaml
system_prompt: |
  You are in ANALYSIS MODE. Do NOT use write tools (add_measure, update_measure).
```

**Limitations:**
- Not enforceable (LLM could still use write tools)
- Not secure
- Relies on LLM compliance

## Recommended Approach: Separate Configs

**Pros:**
- ✅ Explicit and clear
- ✅ No framework changes needed
- ✅ Enforced at tool registration level
- ✅ Easy to verify (just check tools list)
- ✅ Type-safe (can't accidentally use wrong worker)

**Cons:**
- ⚠️ Some code duplication (but minimal - just tool lists)
- ⚠️ Need to maintain two configs

## Implementation Status

✅ **Implemented:**
- Created `dax_analyzer.yaml` (read-only)
- Updated `pbi-analysis-manager` to use `dax_analyzer.yaml`
- `pbi-designer-manager` uses `dax_editor.yaml` (read+write)

## Verification

To verify tool access is correctly restricted:

1. Check worker configs:
   ```bash
   # Analysis worker should NOT have write tools
   grep -E "add_measure|update_measure" configs/agents/pbi/dax_analyzer.yaml
   # Should return nothing
   
   # Designer worker SHOULD have write tools
   grep -E "add_measure|update_measure" configs/agents/pbi/dax_editor.yaml
   # Should return tool definitions
   ```

2. Check manager worker assignments:
   ```bash
   # Analysis manager should use dax_analyzer
   grep "dax-analyzer" configs/agents/pbi_analysis_manager.yaml
   
   # Designer manager should use dax-editor
   grep "dax-editor" configs/agents/pbi_designer_manager.yaml
   ```

## Future Considerations

If we need more granular control in the future:

1. **Tool-level permissions** - Add permission metadata to tools
2. **Context-aware PolicyEngine** - Pass manager context to PolicyEngine
3. **Dynamic tool filtering** - Filter tools based on manager type at load time

For now, separate configs provide the cleanest, most explicit solution.

