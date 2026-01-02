# Power BI Tools

These domain-specific tools are located in **`bi_tools/tools/`** and operate on Power BI data models.

> **Note:** These tools demonstrate how to extend the generic framework with domain-specific functionality.

## Tool Categories

### Column Tools (`bi_tools/tools/column/`)
| Tool | Purpose |
|------|---------|
| `AddColumnTool` | Add a new column to a table |
| `ListColumnsTool` | List columns in a table |
| `ListCalculatedColumnsTool` | List calculated columns |
| `RenameColumnTool` | Rename a column |
| `RemoveColumnTool` | Remove a column |
| `UpdateCalculatedColumnTool` | Update calculated column expression |

### Measure Tools (`bi_tools/tools/measure/`)
| Tool | Purpose |
|------|---------|
| `AddMeasureTool` | Add a DAX measure |
| `ListMeasuresTool` | List measures in a table |
| `GetMeasureExpressionTool` | Get measure DAX expression ✨ |
| `UpdateMeasureTool` | Update measure expression ✨ |
| `RemoveMeasureTool` | Remove a measure |
| `ValidateDAXTool` | Validate DAX syntax |
| `ConvertDAXTool` | Convert DAX expressions |

**New Tools Added (v2.3)**:
- **`GetMeasureExpressionTool`**: Retrieve the DAX formula for a specific measure
- **`UpdateMeasureTool`**: Edit existing DAX measure expressions or rename measures

### Relationship Tools (`bi_tools/tools/relationship/`)
| Tool | Purpose |
|------|---------|
| `AddRelationshipTool` | Create a relationship between columns |
| `ListRelationshipsTool` | List all relationships |
| `UpdateRelationshipTool` | Modify relationship properties |
| `RemoveRelationshipTool` | Remove a relationship |
| `ValidateRelationshipsTool` | Validate relationship integrity |

### Table Tools (`bi_tools/tools/table/`)
| Tool | Purpose |
|------|---------|
| `AddTableTool` | Add a new table |
| `ListTablesTool` | List all tables in the model |

### SQL Tools (`bi_tools/tools/sql/`)
| Tool | Purpose |
|------|---------|
| `GetSqlQueryTool` | Get SQL source query |
| `UpdateSqlQueryTool` | Update SQL query |
| `ListSqlSourcesTool` | List SQL sources |
| `ValidateSqlTool` | Validate SQL syntax |
| `PrepareSqlTool` | Prepare SQL for execution |
| `SqlAnalyzerTool` | Analyze SQL structure |

### Partition Tools (`bi_tools/tools/partition/`) ✨
| Tool | Purpose |
|------|---------|
| `ListPartitionsTool` | List all partitions with their source type (M Query, SQL, etc.) |
| `GetPartitionSourceTool` | Retrieve M Query, SQL, or other source expression for a partition |
| `UpdatePartitionSourceTool` | Update M Query, SQL, or other source expressions for partitions |

**Features**:
- ✅ Full M Query support (view and edit Power Query expressions)
- ✅ Full SQL support (view and edit SQL queries in DirectQuery scenarios)
- ✅ Auto-detects source type (M Query, SQL, Expression)
- ✅ Validates table and partition existence

### Other Tools
- **M Query Tools** (`bi_tools/tools/mquery/`) - Power Query M operations
- **Metadata Tools** (`bi_tools/tools/metadata/`) - Model metadata access
- **Model Tools** (`bi_tools/tools/model/`) - Schema sync and diff

## Example Usage

```python
from deployment.factory import AgentFactory

# Create agent from YAML config
agent = AgentFactory.create_from_yaml("configs/agents/schema_editor.yaml")

# Run with natural language
result = agent.run(
    "Create a relationship between 'SALES'[CustomerId] and 'CUSTOMERS'[Id]"
)
print(result)
```

## Code Locations

| Location | Description |
|----------|-------------|
| `bi_tools/tools/` | Tool implementations |
| `bi_tools/services/` | DataModelService, KGDataModelService |
| `configs/tools/` | YAML tool registration configs |
| `configs/agents/` | Agent YAML configurations |
