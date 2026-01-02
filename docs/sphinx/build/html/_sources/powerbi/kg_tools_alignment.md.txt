# Knowledge Graph Tools Alignment

This document describes how Power BI tools align with the Knowledge Graph (KG) API endpoints. The Knowledge Graph service provides a structured backend for Power BI data model operations.

## Summary

All Power BI tools are now aligned with KG API endpoints. Tools use the `KGDataModelService` which provides methods that map to KG API endpoints.

## ✅ **ALIGNED** - SQL Tools

### `update_sql_query.py`
- **Status**: ✅ Aligned
- **KG Endpoint**: `PUT /kg/{job_id}/tables/{table}/sql`
- **Request Format**: `{"text": sql_text}` ✅
- **Implementation**: Calls `service.put_table_sql(table, sql_query)` correctly
- **Note**: Also calls `patch_table_mquery` to update M Query wrapper (good practice)

### `get_sql_query.py`
- **Status**: ✅ Aligned
- **KG Endpoint**: `GET /kg/{job_id}/tables/{table}/source` (via `get_table_source`)
- **Response**: Returns `m_query.expression` and `m_query.sql` ✅
- **Implementation**: Uses `service.get_table_source(table)` correctly

## ✅ **ALIGNED** - M-Query Tools

### `add_mquery.py`
- **Status**: ✅ Aligned
- **KG Endpoint**: `PUT /kg/{job_id}/tables/{table}/mquery`
- **Request Format**: `{"expression": "...", "sql": "..."}` ✅
- **Implementation**: Calls `service.put_table_mquery(table, expression=expression, sql=sql)` correctly

### `update_mquery.py`
- **Status**: ✅ Aligned
- **KG Endpoint**: `PATCH /kg/{job_id}/tables/{table}/mquery`
- **Request Format**: `{"expression": "...", "sql": "..."}` ✅
- **Implementation**: Calls `service.patch_table_mquery(table, expression=expression, sql=sql)` correctly

### `list_mquery.py`
- **Status**: ✅ Aligned
- **KG Endpoint**: `GET /kg/{job_id}/tables/{table}` (via `get_partition`)
- **Implementation**: Uses `service.get_partition(table)` to retrieve partition data with M Query expressions
- **Note**: Now uses KG partition endpoint for consistency

## ✅ **ALIGNED** - Partition Tools

### `update_partition_source.py`
- **Status**: ✅ Aligned
- **KG Endpoint**: `PATCH /kg/{job_id}/tables/{table}/partition`
- **Request Format**: `{"source": "...", "sqlQuery": "...", "mode": "...", ...}` ✅
- **Implementation**: 
  - Uses `service.patch_table_partition(table, updates)` correctly
  - Extracts SQL from M Query expression if present (via `_extract_sql_from_m_query()`)
  - Includes SQL in updates dict when available
  - Handles both M Query and SQL expressions

### `list_partitions.py`
- **Status**: ✅ Aligned
- **KG Endpoint**: `GET /kg/{job_id}/tables/{table}/partition` (via `get_partition`)
- **Implementation**: Uses `service.get_partition(table)` to retrieve partition data
- **Note**: Now uses KG partition endpoint exclusively

### `get_partition_source.py`
- **Status**: ✅ Aligned
- **KG Endpoint**: `GET /kg/{job_id}/tables/{table}/partition` (via `get_partition`)
- **Implementation**: Uses `service.get_partition(table)` to retrieve partition source expressions
- **Note**: Now uses KG partition endpoint exclusively

## 📋 **KG API Endpoint Reference**

### SQL Endpoints
- `GET /kg/{job_id}/tables/{table}/sql` → Returns `{"table": "...", "sql": "..."}`
- `PUT /kg/{job_id}/tables/{table}/sql` → Expects `{"text": "..."}`
- `PATCH /kg/{job_id}/tables/{table}/sql` → Expects `{"text": "..."}`

### M-Query Endpoints
- `GET /kg/{job_id}/tables/{table}/mquery` → Returns `{"table": "...", "m_query": {"id": "...", "expression": "..."}}`
- `PUT /kg/{job_id}/tables/{table}/mquery` → Expects `{"expression": "...", "sql": "..."}` (sql optional)
- `PATCH /kg/{job_id}/tables/{table}/mquery` → Expects `{"expression": "...", "sql": "..."}` (sql optional)

### Partition Endpoints
- `GET /kg/{job_id}/tables/{table}/partition` → Returns `{"partition": {"table_name": "...", "mode": "...", "source": "...", "sqlQuery": "..."}}`
- `PATCH /kg/{job_id}/tables/{table}/partition` → Expects `{"source": "...", "sqlQuery": "...", "mode": "...", ...}`

### Table/Source Endpoints
- `GET /kg/{job_id}/tables/{table}` → Returns `{"name": "...", "path": "...", "partitions": [...], "m_query": {...}}`
- `GET /kg/{job_id}/tables/{table}/source` → Returns `{"table": "...", "m_query": {...}, "source_table": {...}, "data_source": {...}}`
- `POST /kg/{job_id}/tables` → Expects `{"name": "...", "path": "...", "partitions": [...]}`
- `PATCH /kg/{job_id}/tables/{table}` → Expects `{"path": "...", "partitions": [...]}`

## Implementation Details

### Service Layer

All tools use `get_datamodel_service()` which returns either:
- **`KGDataModelService`**: When Knowledge Graph backend is available (uses KG API endpoints)
- **`DataModelService`**: Legacy service (uses JSON file operations)

Tools check for KG service methods using `hasattr()` and gracefully handle both backends.

### Partition Tools Pattern

Partition tools follow this pattern:

```python
from bi_tools.services.datamodel_service import get_datamodel_service

service = get_datamodel_service()

# Check for KG partition endpoint
if not hasattr(service, "get_partition"):
    raise ValueError("Knowledge Graph partition endpoint not available.")

# Use KG partition endpoint
partition_payload = service.get_partition(table)  # type: ignore[attr-defined]
partition_obj = (partition_payload or {}).get("partition")
```

### SQL Extraction

The `update_partition_source` tool extracts SQL from M Query expressions:

```python
def _extract_sql_from_m_query(self, expression: str) -> Optional[str]:
    """Extract SQL from Value.NativeQuery in M Query expression."""
    if not expression or "Value.NativeQuery" not in expression:
        return None
    import re
    m = re.search(r'Value\.NativeQuery\s*\([^,]+,\s*"([\s\S]*?)"', expression)
    return m.group(1) if m else None
```

The extracted SQL is included in the updates dict when updating partitions.

## Tool Locations

All Power BI tools are located in `bi_tools/tools/`:

- **SQL Tools**: `bi_tools/tools/sql/`
- **M Query Tools**: `bi_tools/tools/mquery/`
- **Partition Tools**: `bi_tools/tools/partition/`

## Service Implementation

The `KGDataModelService` (`bi_tools/services/kg_datamodel_service.py`) provides methods that map to KG API endpoints:

- `get_table_source()` → `GET /kg/{job_id}/tables/{table}/source`
- `put_table_sql()` → `PUT /kg/{job_id}/tables/{table}/sql`
- `put_table_mquery()` → `PUT /kg/{job_id}/tables/{table}/mquery`
- `patch_table_mquery()` → `PATCH /kg/{job_id}/tables/{table}/mquery`
- `get_partition()` → `GET /kg/{job_id}/tables/{table}/partition`
- `patch_table_partition()` → `PATCH /kg/{job_id}/tables/{table}/partition`

## Summary

✅ **All tools are aligned with KG API endpoints**
✅ **Partition tools use KG partition endpoints exclusively**
✅ **SQL extraction from M Query expressions is implemented**
✅ **Tools gracefully handle both KG and legacy backends**

The Power BI implementation provides a consistent interface to the Knowledge Graph service through the `KGDataModelService`, ensuring all tools work seamlessly with the KG backend.

