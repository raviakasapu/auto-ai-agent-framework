# Tool Implementation Coverage

This chapter details each tool namespace in `bi_tools/tools/` and their usage.

## Tool Organization

```
bi_tools/tools/
├── column/           # Column operations
├── measure/          # DAX measure operations
├── relationship/     # Relationship management
├── table/            # Table operations
├── sql/              # SQL analysis and modification
├── mquery/           # M Query operations
├── partition/        # Partition source management
├── metadata/         # Metadata file access
├── model/            # Schema sync and diff
├── validation/       # Validation operations
└── utility/          # Python interpreter
```

## Column Tools

**Location:** `bi_tools/tools/column/`

| Tool | Type | Description |
|------|------|-------------|
| `list_columns` | Read | List columns in a table with types and sources |
| `list_calculated_columns` | Read | List calculated columns with expressions |
| `add_column` | Write | Add a new column to a table |
| `rename_column` | Write | Rename a column |
| `remove_column` | Write | Remove a column |
| `update_calculated_column` | Write | Update calculated column expression |

### Example: ListColumnsTool

```python
class ListColumnsTool(BaseTool):
    @property
    def name(self) -> str:
        return "list_columns"
    
    @property
    def description(self) -> str:
        return "List columns in a table with data types and source information."
    
    @property
    def args_schema(self) -> Type[BaseModel]:
        class Args(BaseModel):
            table: str = Field(..., description="Table name")
        return Args
    
    def execute(self, table: str) -> dict:
        service = get_datamodel_service()
        columns = service.get_columns(table)
        
        return {
            "table": table,
            "columns": columns,
            "count": len(columns),
            "human_readable_summary": f"Found {len(columns)} columns in {table}"
        }
```

## Measure Tools

**Location:** `bi_tools/tools/measure/`

| Tool | Type | Description |
|------|------|-------------|
| `list_measures` | Read | List measures in a table |
| `get_measure_expression` | Read | Get DAX expression for a measure |
| `add_measure` | Write | Add a new measure |
| `update_measure` | Write | Update measure expression |
| `remove_measure` | Write | Remove a measure |
| `validate_dax` | Read | Validate DAX syntax |
| `convert_dax` | Read | Convert/optimize DAX expressions |

### Example: GetMeasureExpressionTool

```python
class GetMeasureExpressionTool(BaseTool):
    @property
    def name(self) -> str:
        return "get_measure_expression"
    
    @property
    def description(self) -> str:
        return "Get the DAX expression for a measure."
    
    @property
    def args_schema(self) -> Type[BaseModel]:
        class Args(BaseModel):
            table: str = Field(..., description="Table containing the measure")
            measure_id: str = Field(..., description="Measure ID (format: table::name)")
        return Args
    
    def execute(self, table: str, measure_id: str) -> dict:
        service = get_datamodel_service()
        measure = service.get_measure(table, measure_id)
        
        return {
            "table": table,
            "measure_id": measure_id,
            "name": measure.get("name"),
            "expression": measure.get("expression"),
            "human_readable_summary": f"Retrieved expression for {measure_id}"
        }
```

## Relationship Tools

**Location:** `bi_tools/tools/relationship/`

| Tool | Type | Description |
|------|------|-------------|
| `list_relationships` | Read | List all relationships with IDs |
| `add_relationship` | Write | Create a new relationship |
| `update_relationship` | Write | Modify relationship properties |
| `remove_relationship` | Write | Remove a relationship |
| `validate_relationships` | Read | Validate relationship integrity |
| `cleanup_relationship_format` | Read | Normalize relationship payload |

## Table Tools

**Location:** `bi_tools/tools/table/`

| Tool | Type | Description |
|------|------|-------------|
| `list_tables` | Read | List all tables with metadata |
| `add_table` | Write | Create a new table |

## SQL Tools

**Location:** `bi_tools/tools/sql/`

| Tool | Type | Description |
|------|------|-------------|
| `list_sql_sources` | Read | List tables using SQL sources |
| `get_sql_query` | Read | Extract SQL from partition |
| `update_sql_query` | Write | Update SQL query |
| `validate_sql` | Read | Validate SQL syntax |
| `prepare_sql` | Read | Normalize SQL for comparison |
| `sql_analyzer` | Read | Structured SQL analysis via sqlglot |
| `extract_sql_connection` | Read | Extract connection info from M Query |

### Example: SQLAnalyzerTool

```python
class SQLAnalyzerTool(BaseTool):
    """Analyzes SQL using sqlglot AST."""
    
    @property
    def args_schema(self) -> Type[BaseModel]:
        class Args(BaseModel):
            sql_query: str = Field(..., description="SQL query to analyze")
            dialect: str = Field(default="tsql", description="SQL dialect")
            analysis_level: str = Field(default="detailed", description="Level of analysis")
        return Args
    
    def execute(self, sql_query: str, dialect: str = "tsql", analysis_level: str = "detailed") -> dict:
        import sqlglot
        
        try:
            parsed = sqlglot.parse_one(sql_query, dialect=dialect)
            
            # Extract tables
            tables = [str(t) for t in parsed.find_all(sqlglot.exp.Table)]
            
            # Extract columns
            columns = [str(c) for c in parsed.find_all(sqlglot.exp.Column)]
            
            # Extract joins
            joins = [str(j) for j in parsed.find_all(sqlglot.exp.Join)]
            
            return {
                "success": True,
                "tables": tables,
                "columns": columns,
                "joins": joins,
                "human_readable_summary": f"Analyzed SQL: {len(tables)} tables, {len(columns)} columns"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "human_readable_summary": f"SQL analysis failed: {e}"
            }
```

## M Query Tools

**Location:** `bi_tools/tools/mquery/`

| Tool | Type | Description |
|------|------|-------------|
| `list_mquery` | Read | List M Query expressions per partition |
| `add_mquery` | Write | Add M Query expression |
| `update_mquery` | Write | Update M Query expression |
| `validate_mquery` | Read | Validate M Query syntax |

## Partition Tools

**Location:** `bi_tools/tools/partition/`

| Tool | Type | Description |
|------|------|-------------|
| `list_partitions` | Read | List partitions with source types |
| `get_partition_source` | Read | Get partition source expression |
| `update_partition_source` | Write | Update partition source |

## Metadata Tools

**Location:** `bi_tools/tools/metadata/`

| Tool | Type | Description |
|------|------|-------------|
| `list_metadata` | Read | List available metadata files |
| `get_metadata_content` | Read | Read metadata file contents |

## Model Tools

**Location:** `bi_tools/tools/model/`

| Tool | Type | Description |
|------|------|-------------|
| `schema_diff` | Read | Compare proposed vs current schema |
| `sync_table_schema` | Write | Sync table schema |
| `import_datamodel` | Write | Import data model |

## Utility Tools

**Location:** `bi_tools/tools/utility/`

| Tool | Type | Description |
|------|------|-------------|
| `python_interpreter` | Read | Execute Python code for analysis |

### PythonInterpreterTool

```python
class PythonInterpreterTool(BaseTool):
    """Executes Python code in a sandboxed environment."""
    
    BLOCKED_OPERATIONS = {
        "import os", "import sys", "import subprocess",
        "exec(", "eval(", "__import__", "open(",
    }
    
    ALLOWED_IMPORTS = {"collections", "json"}
    
    def execute(self, code: str) -> dict:
        # Security check
        for blocked in self.BLOCKED_OPERATIONS:
            if blocked in code:
                return {"error": f"Blocked operation: {blocked}"}
        
        # Create safe namespace
        safe_namespace = {
            "__builtins__": {
                "len": len, "str": str, "int": int, "float": float,
                "list": list, "dict": dict, "sum": sum, "min": min, "max": max,
                "print": print, "range": range, "enumerate": enumerate,
            }
        }
        
        # Add allowed imports
        for module in self.ALLOWED_IMPORTS:
            safe_namespace[module] = __import__(module)
        
        # Execute
        output = []
        exec(code, safe_namespace)
        
        return {
            "success": True,
            "output": "\n".join(output),
            "human_readable_summary": "Python code executed successfully"
        }
```

## YAML Registration

Tools are registered via YAML:

```yaml
# configs/tools/list_tables.yaml
name: list_tables
type: ListTablesTool
config: {}
```

And referenced in agent configs:

```yaml
resources:
  tools:
    - name: list_tables
      type: ListTablesTool
      config: {}

spec:
  tools: [list_tables, list_columns, list_measures]
```

## Worker Tool Assignments

### Model Structure Analyzer (Read-Only)

```yaml
tools:
  - list_tables
  - list_columns
  - list_relationships
  - list_partitions
  - get_partition_source
  - list_measures
  - complete_task
```

### DAX Analyzer (Read-Only)

```yaml
tools:
  - list_measures
  - get_measure_expression
  - validate_dax
  - convert_dax
  - complete_task
```

### DAX Editor (Read+Write)

```yaml
tools:
  - list_measures
  - get_measure_expression
  - add_measure
  - update_measure
  - remove_measure
  - validate_dax
  - complete_task
```

## Best Practices

1. **Return structured data** — Include `human_readable_summary`
2. **Handle errors gracefully** — Return error dict, don't raise
3. **Use Pydantic schemas** — For input validation
4. **Separate read/write tools** — Enable access control
5. **Log execution** — Phoenix captures tool spans automatically

