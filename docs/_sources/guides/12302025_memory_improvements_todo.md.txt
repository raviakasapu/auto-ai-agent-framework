# Memory & Context System Improvements TODO

This document tracks identified issues and improvements for the memory management and context handling systems.

## Completed

### ~~Issue #1: Threading Lock Doesn't Work with Async~~ ✅ FIXED
- **Severity**: HIGH
- **Status**: FIXED
- **File**: `memory.py:18`
- **Fix**: Replaced `threading.RLock()` with `asyncio.Lock()` for proper async context isolation

### ~~Issue #2: Context Mismatch in Async Environments~~ ✅ FIXED
- **Severity**: HIGH
- **Status**: FIXED
- **File**: `memory.py:43-50`
- **Fix**: Async-safe locking now prevents cross-job data leakage

### ~~Issue #6: Context Truncation Without Warning~~ ✅ FIXED
- **Severity**: MEDIUM
- **Status**: FIXED
- **Files**: All planners (StrategicPlanner, WorkerRouterPlanner, ReActPlanner, StrategicDecomposerPlanner, ManagerScriptPlanner)
- **Fix**: Implemented YAML-based Context Configuration system:
  - Created `src/agent_framework/configs/context_config.yaml` with configurable truncation limits
  - Created `src/agent_framework/services/context_config.py` for loading config with ENV overrides
  - Updated all planners to use `ContextConfig.truncate_with_logging()` method
  - Truncation now logs: field name, planner, original size, truncated size, chars removed
  - Adds `[TRUNCATED: N chars removed]` marker to truncated content
  - All limits configurable via YAML or ENV variables (see `docs_source/source/guides/environment_variables.md`)

---

## Remaining Issues

### Issue #3: Conversation Turn Ordering and Potential Duplication
- **Severity**: MEDIUM
- **Files**: `memory.py:28-52`, `context_builder.py:171-181`
- **Problem**: History is appended in order: conversation → agent traces → global updates. When multiple planners access history, they might see duplicated context as each builds separate message lists from the same history.
- **Risk**: Can cause redundant context but not usually breaking
- **Suggested Fix**:
  - Add deduplication layer before prompt assembly
  - Or track which entries have been consumed per planner

### Issue #4: Missing History Filtering in Some Planners
- **Severity**: MEDIUM
- **Files**: `planners.py:519-528` (WorkerRouterPlanner), `planners.py:1850-1910` (ManagerScriptPlanner)
- **Problem**:
  - `WorkerRouterPlanner` manually filters history without using a HistoryFilter
  - `ManagerScriptPlanner` does NOT filter history at all
  - Both append raw history without respecting role-based boundaries
- **Suggested Fix**: Refactor these planners to use the standard `HistoryFilter` classes

### Issue #5: Task Duplication in Function Calling Mode
- **Severity**: LOW
- **File**: `planners.py:1151-1158`
- **Problem**: Logic checks if ANY observation exists in `filtered_history` to decide whether to add task message. This is fragile and tightly coupled to `WorkerHistoryFilter` behavior.
- **Suggested Fix**: Make the check more explicit or document the dependency

### Issue #7: Observation Truncation Loses Information
- **Severity**: MEDIUM
- **File**: `planners.py:869-872`
- **Problem**:
  ```python
  if len(content_s) > self._obs_truncate_len:
      content_s = content_s[: self._obs_truncate_len] + "... (truncated)"
  ```
  - Default 1000 chars may cut off important structured data
  - Large query results, tables, or JSON may be meaningfully incomplete
- **Suggested Fix**:
  - Add structured truncation (e.g., keep first/last N items for lists)
  - Log truncation events with original size
  - Consider smart truncation that preserves structure

### Issue #8: Inconsistent History Filtering Across Planners
- **Severity**: MEDIUM
- **Files**: `planners.py` (multiple locations)
- **Problem**: Different planners apply different filters or no filter:
  | Planner | Uses HistoryFilter? |
  |---------|---------------------|
  | StrategicPlanner | ✅ OrchestratorHistoryFilter |
  | ReActPlanner | ✅ WorkerHistoryFilter |
  | StrategicDecomposerPlanner | ✅ ManagerHistoryFilter |
  | WorkerRouterPlanner | ❌ Manual filtering |
  | ManagerScriptPlanner | ❌ No filtering |
  | ChatPlanner | ❌ No filtering |
- **Suggested Fix**: Standardize all planners to use `HistoryFilter` classes

### Issue #9: Strategic Plan Context Injection Not Validated
- **Severity**: MEDIUM
- **Files**: `planners.py:273-288`, `planners.py:1395-1401`
- **Problem**:
  ```python
  director_context = get_from_context("director_context") or get_from_context("context")
  # Appended without validation
  if director_context:
      context_parts.append(f"DIRECTOR CONTEXT:\n{str(director_context)[:4000]}")
  ```
  - No validation that context is actually set correctly
  - No error handling if context structure is unexpected
  - `str(director_context)` may produce unreadable output for complex objects
  - Undocumented fallback: `get_from_context("context")`
- **Suggested Fix**:
  - Add type checking for expected context structure
  - Log warnings when context is missing or malformed
  - Document the fallback behavior

### Issue #10: Memory Ordering Not Chronological
- **Severity**: LOW
- **File**: `memory.py:62-79` (MessageStoreMemory.get_history)
- **Problem**:
  ```python
  history = []
  history.extend(conversation)   # All user/assistant turns FIRST
  history.extend(agent_msgs)     # Then ALL action/observation
  history.extend(global_msgs)    # Then ALL global updates
  return history
  ```
  - Real execution is interleaved, but memory returns grouped blocks
  - A follow-up user message appears BEFORE the actions that preceded it
- **Suggested Fix**:
  - Add timestamps to all entries
  - Sort by timestamp in `get_history()`
  - Or document this as expected behavior if intentional

---

## Priority Recommendations

### High Priority (Fix Soon)
1. ~~**Issue #6: Context Truncation**~~ ✅ FIXED - Implemented YAML-based ContextConfig with ENV overrides
2. **Issue #8: Inconsistent Filtering** - Violates hierarchy model, causes confusion

### Medium Priority (Fix When Possible)
3. **Issue #4: Missing Filters** - Planners should use standard filters
4. **Issue #7: Observation Truncation** - Add smarter truncation (logging now implemented)
5. **Issue #9: Context Validation** - Add error handling

### Low Priority (Nice to Have)
6. **Issue #3: Turn Ordering** - HistoryFilters mitigate this
7. **Issue #5: Task Duplication** - Currently works, just fragile
8. **Issue #10: Chronological Ordering** - Consider if needed

---

## Environment Variables (Implemented)

The following environment variables have been implemented in the Context Configuration system.
See `docs_source/source/guides/environment_variables.md` for full documentation.

| Variable | Purpose | Default |
|----------|---------|---------|
| `AGENT_STRATEGIC_PLAN_TRUNCATE_LEN` | Strategic plan truncation | 2000 |
| `AGENT_DIRECTOR_CONTEXT_TRUNCATE_LEN` | Director context truncation | 4000 |
| `AGENT_DATA_MODEL_CONTEXT_TRUNCATE_LEN` | Data model context truncation | 6000 |
| `AGENT_OBSERVATION_TRUNCATE_LEN` | Observation truncation | 1500 |
| `AGENT_TOOL_ARGS_TRUNCATE_LEN` | Tool args truncation | 500 |
| `AGENT_PREVIOUS_OUTPUT_TRUNCATE_LEN` | Previous output truncation | 5000 |
| `AGENT_MANIFEST_TRUNCATE_LEN` | Manifest truncation | 6000 |
| `AGENT_LOG_TRUNCATION` | Log truncation events | true |
| `AGENT_MAX_CONVERSATION_TURNS` | Max conversation turns | 10 |
| `AGENT_MAX_EXECUTION_TRACES` | Max execution traces | 20 |

**Configuration File**: `src/agent_framework/configs/context_config.yaml`

---

## Related Documentation

- [Memory & Message Stores](../part2_runtime/memory.md)
- [Async Safety Guide](async_safety.md)
- [Hierarchical History Filtering](hierarchical_filtering.md)
- [Environment Variables](environment_variables.md)
