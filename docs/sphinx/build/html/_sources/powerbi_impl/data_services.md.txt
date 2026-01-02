# Data & Context Services

This chapter covers the data layer: DataModelService, KnowledgeGraphClient, and context management.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Tool Execution                           │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              KGDataModelService                             │
│              (bi_tools/services/kg_datamodel_service.py)    │
│              - Wraps KnowledgeGraphClient                   │
│              - Provides tool-friendly API                   │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              KnowledgeGraphClient                           │
│              (bi_tools/gateways/knowledge_graph_client.py)  │
│              - HTTP client to KG service                    │
│              - CRUD operations on data model                │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              Knowledge Graph Service (External)             │
│              - Stores Power BI data model                   │
│              - Provides graph-based access                  │
└─────────────────────────────────────────────────────────────┘
```

## DataModelService

Located at `bi_tools/services/datamodel_service.py`.

### Purpose

- Central API for data model operations
- Request-scoped via `datamodel_context`
- Used by tools to read/write model data

### Context Manager

```python
from bi_tools.services.datamodel_service import datamodel_context

# Request-scoped context
with datamodel_context(job_id):
    # All tools in this block use job_id
    result = await agent.run(task)
```

### Implementation

```python
import contextvars
from contextlib import contextmanager

# Async-safe storage
_current_job_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    '_current_job_id',
    default=None
)

def _get_current_job_id() -> Optional[str]:
    return _current_job_id.get()

def _set_current_job_id(job_id: str) -> None:
    _current_job_id.set(job_id)

def _clear_current_job_id() -> None:
    _current_job_id.set(None)

@contextmanager
def datamodel_context(job_id: str):
    """Context manager for request-scoped data model operations."""
    previous = _get_current_job_id()
    _set_current_job_id(job_id)
    try:
        yield
    finally:
        if previous:
            _set_current_job_id(previous)
        else:
            _clear_current_job_id()
```

### Usage in Tools

```python
from bi_tools.services.datamodel_service import get_datamodel_service

class ListTablesTool(BaseTool):
    def execute(self) -> dict:
        service = get_datamodel_service()
        tables = service.get_tables()  # Uses current job_id from context
        return {"tables": tables}
```

## KnowledgeGraphClient

Located at `bi_tools/gateways/knowledge_graph_client.py`.

### Purpose

- HTTP client to Knowledge Graph service
- CRUD operations on data model entities
- Manifest export for AI context

### API Methods

```python
class KnowledgeGraphClient:
    def __init__(self, base_url: str = None, api_key: str = None):
        self.base_url = base_url or os.getenv("KG_SERVICE_URL")
        self.api_key = api_key or os.getenv("KG_API_KEY")
    
    # Job operations
    def job_summary(self, job_id: str) -> dict
    def sync_pull(self, job_id: str, clean_job: bool = False) -> None
    
    # Table operations
    def get_tables(self, job_id: str) -> list
    def get_table(self, job_id: str, table: str) -> dict
    
    # Column operations
    def get_columns(self, job_id: str, table: str) -> list
    def add_column(self, job_id: str, table: str, column: dict) -> dict
    
    # Measure operations
    def get_measures(self, job_id: str, table: str) -> list
    def add_measure(self, job_id: str, table: str, measure: dict) -> dict
    def update_measure(self, job_id: str, table: str, measure_id: str, updates: dict) -> dict
    
    # Relationship operations
    def get_relationships(self, job_id: str) -> list
    def add_relationship(self, job_id: str, relationship: dict) -> dict
    
    # Partition operations
    def get_partitions(self, job_id: str, table: str) -> list
    def get_partition_source(self, job_id: str, table: str, partition: str) -> str
    
    # SQL operations
    def get_sql_query(self, job_id: str, table: str, partition: str) -> str
    def update_sql_query(self, job_id: str, table: str, partition: str, sql: str) -> dict
    
    # Manifest export
    def export_model_manifest(self, job_id: str) -> str
```

### Manifest Export

The `export_model_manifest` method returns an AI-optimized summary:

```text
=== Power BI Model Schema Manifest ===

Job ID: 019a3b4d-852b-4838-9564-e657afc7cc35

STATISTICS:
  - Tables: 12
  - Columns: 156
  - Measures: 23
  - Relationships: 8

TABLES:
  - FactInternetSales (type: fact, columns: 18, measures: 5)
    Key Columns: [SalesOrderNumber, SalesOrderLineNumber]
  - DimCustomer (type: dimension, columns: 12, measures: 0)
    Key Columns: [CustomerKey]
  ...

RELATIONSHIPS:
  - FactInternetSales.CustomerKey → DimCustomer.CustomerKey (active, many-to-one)
  - FactInternetSales.ProductKey → DimProduct.ProductKey (active, many-to-one)
  ...
```

## KGDataModelService

Located at `bi_tools/services/kg_datamodel_service.py`.

### Purpose

- Wraps `KnowledgeGraphClient` for tool use
- Auto-resolves `job_id` from context
- Provides simplified API

### Implementation

```python
class KGDataModelService:
    def __init__(self, kg_client: KnowledgeGraphClient = None):
        self.kg = kg_client or KnowledgeGraphClient()
    
    def _get_job_id(self) -> str:
        job_id = _get_current_job_id()
        if not job_id:
            raise ValueError("No job_id in context. Use datamodel_context().")
        return job_id
    
    def get_tables(self) -> list:
        return self.kg.get_tables(self._get_job_id())
    
    def get_columns(self, table: str) -> list:
        return self.kg.get_columns(self._get_job_id(), table)
    
    def add_measure(self, table: str, measure: dict) -> dict:
        return self.kg.add_measure(self._get_job_id(), table, measure)
    
    # ... other methods
```

## Service Registration

Register services for use by tools:

```python
from agent_framework.services.context_builder import register_datamodel_service
from bi_tools.services.kg_datamodel_service import KGDataModelService

# At application startup
service = KGDataModelService()
register_datamodel_service(service)
```

### Retrieving Service

```python
from agent_framework.services.context_builder import get_datamodel_service

# In a tool
service = get_datamodel_service()
tables = service.get_tables()
```

## Metadata Files

The KG service stores metadata artifacts:

| File | Description |
|------|-------------|
| `report_sql.json` | Raw SQL extracted from legacy report |
| `metric_mapping_golden_record.json` | Metric mappings |
| `report_parameters.json` | Report parameters |
| `settings.json` | Project settings |
| `source_report_formatted.json` | Source report structure |

Access via tools:

```python
# list_metadata_files tool
files = service.list_metadata_files()

# get_metadata_file tool
content = service.get_metadata_file("report_sql.json")
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `KG_SERVICE_URL` | `http://localhost:8080` | KG service URL |
| `KG_API_KEY` | — | KG service API key |

## Best Practices

1. **Always use `datamodel_context`** — Ensures proper job_id propagation
2. **Register service at startup** — Before loading agents
3. **Use KGDataModelService** — Auto-resolves job_id
4. **Handle missing context** — Raise clear errors
5. **Use manifest for AI context** — Optimized for LLM consumption

