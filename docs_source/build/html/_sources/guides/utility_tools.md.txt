# Framework Utility Tools

The framework provides generic utility tools that can be used by any agent. These tools are domain-agnostic and useful for common operations.

## Available Utility Tools

### GlobTool

**Purpose**: Find files matching patterns using glob syntax.

**Location**: `agent_framework.tools.utility.GlobTool`

**Arguments**:
- `pattern` (str, required): Glob pattern (e.g., `**/*.py`, `configs/**/*.yaml`)
- `root_dir` (str, optional): Root directory to search from (default: current directory)
- `recursive` (bool, optional): Enable recursive search (default: `true`)

**Example Usage**:
```python
# Find all Python files recursively
glob(pattern="**/*.py")

# Find YAML configs in specific directory
glob(pattern="configs/**/*.yaml", root_dir="/path/to/project")

# Find files in current directory only (non-recursive)
glob(pattern="*.py", recursive=False)
```

**Use Cases**:
- Finding configuration files
- Locating source code files
- Discovering project structure
- File system exploration

### GrepTool

**Purpose**: Search for text patterns in files using regex.

**Location**: `agent_framework.tools.utility.GrepTool`

**Arguments**:
- `pattern` (str, required): Regex pattern to search for
- `files` (List[str], required): List of file paths to search
- `case_sensitive` (bool, optional): Case-sensitive search (default: `false`)
- `include_line_numbers` (bool, optional): Include line numbers in results (default: `true`)
- `context_lines` (int, optional): Number of context lines before/after match (default: `0`)

**Example Usage**:
```python
# Search for function definitions
grep(
    pattern="def\\s+\\w+",
    files=["src/main.py", "src/utils.py"],
    include_line_numbers=True
)

# Case-insensitive search with context
grep(
    pattern="TODO|FIXME",
    files=["**/*.py"],  # Note: Use glob first to get file list
    case_sensitive=False,
    context_lines=2
)
```

**Use Cases**:
- Code analysis and search
- Finding specific patterns in codebases
- Debugging and investigation
- Text pattern matching

## Adding Utility Tools to Agents

### Step 1: Add to Resources Section

In your agent YAML config, add them to the `resources.tools` section:

```yaml
resources:
  tools:
    - name: glob
      type: GlobTool
      config: {}
    - name: grep
      type: GrepTool
      config: {}
```

### Step 2: Reference in Spec

Then reference them in the `spec.tools` list:

```yaml
spec:
  tools: [glob, grep, ...other_tools...]
```

### Step 3: Add Tool Descriptions (for ReActPlanner)

If using `ReActPlanner`, add tool descriptions to help the LLM understand when to use them:

```yaml
spec:
  planner:
    type: ReActPlanner
    config:
      tool_descriptions:
        - name: glob
          description: "Find files matching a pattern using glob syntax (e.g., '**/*.py', 'configs/**/*.yaml'). Supports recursive patterns with **."
          args: ["pattern", "root_dir", "recursive"]
        - name: grep
          description: "Search for text patterns in files using regex. Returns matching lines with line numbers and optional context."
          args: ["pattern", "files", "case_sensitive", "include_line_numbers", "context_lines"]
```

## Complete Example

Here's a complete example of adding utility tools to an agent:

```yaml
apiVersion: agent.framework/v2
kind: Agent

metadata:
  name: CodeAnalyzer
  description: Agent for analyzing codebases

resources:
  tools:
    - name: glob
      type: GlobTool
      config: {}
    - name: grep
      type: GrepTool
      config: {}

spec:
  planner:
    type: ReActPlanner
    config:
      tool_descriptions:
        - name: glob
          description: "Find files matching a pattern using glob syntax. Supports recursive patterns with **."
          args: ["pattern", "root_dir", "recursive"]
        - name: grep
          description: "Search for text patterns in files using regex. Returns matching lines with line numbers."
          args: ["pattern", "files", "case_sensitive", "include_line_numbers", "context_lines"]
  
  tools: [glob, grep]
```

## When to Use These Tools

### GlobTool
- ✅ Finding configuration files
- ✅ Discovering project structure
- ✅ Locating source code files
- ✅ File system exploration
- ✅ Pattern-based file discovery

### GrepTool
- ✅ Code analysis and search
- ✅ Finding specific patterns in codebases
- ✅ Debugging and investigation
- ✅ Text pattern matching
- ✅ Searching across multiple files

## Integration with Other Tools

These utility tools work well with other framework tools:

1. **Use GlobTool first** to find files, then **GrepTool** to search within them:
   ```python
   # Step 1: Find Python files
   files = glob(pattern="**/*.py")
   
   # Step 2: Search for patterns in those files
   results = grep(pattern="def\\s+\\w+", files=files["matches"])
   ```

2. **Combine with domain-specific tools** for comprehensive analysis:
   - Use `glob` to find config files
   - Use domain tools to parse/analyze those files
   - Use `grep` to search for specific patterns

## Framework Location

All utility tools are located in:
- **Module**: `agent_framework.tools.utility`
- **Exports**: Available from `agent_framework.tools`

```python
from agent_framework.tools import GlobTool, GrepTool
from agent_framework.tools.utility import GlobTool, GrepTool
```

## Other Utility Tools

The framework also provides other utility tools:
- **CalculatorTool**: Mathematical calculations
- **MathQATool**: Math problem solving
- **CompleteTaskTool**: Task completion signaling
- **MockSearchTool**: Testing and development

See the framework documentation for details on these tools.

