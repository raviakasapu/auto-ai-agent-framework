# Code Assistant Playbook

Pattern for building agent systems that analyze, refactor, and generate code.

## Use Cases

- Code review automation
- Refactoring assistance
- Documentation generation
- Test generation
- Bug analysis

## Agent Hierarchy

```
┌─────────────────────────────────────────────────────────────┐
│ CODE ORCHESTRATOR                                           │
│ - Understand developer intent                               │
│ - Route to analysis or modification managers                │
│ - Maintain codebase awareness                               │
└─────────────────────────────────────────────────────────────┘
         │
         ├──────────────────────────────────────────┐
         │                                          │
         ▼                                          ▼
┌─────────────────────────────┐    ┌─────────────────────────────┐
│ ANALYSIS MANAGER            │    │ MODIFICATION MANAGER        │
│ - Code review               │    │ - Refactoring               │
│ - Dependency analysis       │    │ - Code generation           │
│ - Documentation lookup      │    │ - Test writing              │
└─────────────────────────────┘    └─────────────────────────────┘
         │                                          │
         ▼                                          ▼
┌─────────────────────────────┐    ┌─────────────────────────────┐
│ Analysis Workers            │    │ Modification Workers        │
│ - glob_tool                 │    │ - write_file                │
│ - grep_tool                 │    │ - apply_patch               │
│ - read_file                 │    │ - run_tests                 │
│ - analyze_ast               │    │ - format_code               │
└─────────────────────────────┘    └─────────────────────────────┘
```

## Tool Categories

### Navigation Tools
- `glob_tool` — Find files by pattern
- `grep_tool` — Search file contents
- `read_file` — Read file contents
- `list_directory` — Directory exploration

### Analysis Tools
- `analyze_ast` — Parse and analyze AST
- `find_references` — Find symbol usages
- `analyze_dependencies` — Dependency graph
- `check_types` — Type checking

### Modification Tools
- `write_file` — Write file contents
- `apply_patch` — Apply diff patches
- `format_code` — Code formatting
- `run_linter` — Lint checking

### Execution Tools
- `run_tests` — Execute test suite
- `run_command` — Shell command execution
- `build_project` — Build verification

## Policy Patterns

### Sandbox Execution
```yaml
policies:
  execution:
    config:
      sandbox: true
      allowed_commands: [npm test, pytest, cargo test]
      timeout_seconds: 120
```

### Incremental Changes
```yaml
planning_prompt: |
  For any code modification:
  1. Read the current file first
  2. Make minimal, focused changes
  3. Run tests after modification
  4. Revert if tests fail
```

### HITL for Writes
```yaml
policies:
  hitl:
    config:
      enabled: true
      write_tools: [write_file, apply_patch]
      auto_approve_patterns:
        - "*.test.ts"      # Auto-approve test files
        - "*.spec.py"
```

## Context Services

### Codebase Index
- File tree structure
- Symbol definitions
- Cross-references

### Test Results Store
- Test execution history
- Coverage metrics
- Failure patterns

## Structured Output

```python
class RefactorResult(FinalResponse):
    operation: str = "refactor_complete"
    payload: dict = {
        "files_modified": ["src/utils.py", "src/main.py"],
        "changes": [
            {"file": "src/utils.py", "type": "rename_function", "old": "calc", "new": "calculate"},
            {"file": "src/main.py", "type": "update_import", "old": "calc", "new": "calculate"}
        ],
        "tests_passed": True,
        "test_count": 42
    }
    human_readable_summary: str = "Renamed calc → calculate in 2 files. All 42 tests pass."
```

## Implementation Notes

This playbook is a pattern guide. To implement:

1. Create navigation tools (glob, grep) using framework utilities
2. Design analysis workers with language-specific tools
3. Configure sandbox execution for safety
4. Set up HITL for production changes
5. Integrate with your test runner and CI pipeline

