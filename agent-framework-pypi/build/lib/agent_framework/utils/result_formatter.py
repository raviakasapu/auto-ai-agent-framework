"""
Helper functions to convert tool results to FinalResponse format.

This ensures consistent formatting for frontend consumption.
"""

from typing import Any, Dict, List
from ..base import FinalResponse


def convert_list_tool_result_to_display_table(
    tool_name: str,
    tool_result: Dict[str, Any],
    tool_args: Dict[str, Any] = None
) -> FinalResponse:
    """
    Convert list tool results to display_table format.
    
    Args:
        tool_name: Name of the tool (e.g., "list_measures", "list_tables")
        tool_result: The result dict from the tool
        tool_args: Optional tool arguments for context
        
    Returns:
        FinalResponse with display_table operation
    """
    tool_args = tool_args or {}
    
    if tool_name == "list_tables" and isinstance(tool_result, dict):
        tables = tool_result.get("tables", [])
        return FinalResponse(
            operation="display_table",
            payload={
                "title": "Data Model Tables",
                "headers": ["Table Name"],
                "rows": [[t] for t in tables]
            },
            human_readable_summary=f"Found {len(tables)} tables in the model."
        )
    
    elif tool_name == "list_columns" and isinstance(tool_result, dict):
        columns = tool_result.get("columns", [])
        table_name = tool_result.get("table") or tool_args.get("table", "Unknown")
        return FinalResponse(
            operation="display_table",
            payload={
                "title": f"Columns in {table_name}",
                "headers": ["Column Name", "Data Type"],
                "rows": [[c.get("name", ""), c.get("dataType", "")] for c in columns]
            },
            human_readable_summary=f"Found {len(columns)} columns in {table_name} table."
        )
    
    elif tool_name == "list_measures" and isinstance(tool_result, dict):
        measures = tool_result.get("measures", [])
        # Handle both formats: [{table, name}] or [{table, measure}]
        rows = []
        for m in measures:
            if isinstance(m, dict):
                table = m.get("table", "")
                measure_name = m.get("name") or m.get("measure", "")
                rows.append([table, measure_name])
        
        return FinalResponse(
            operation="display_table",
            payload={
                "title": "Measures in Model",
                "headers": ["Table", "Measure"],
                "rows": rows
            },
            human_readable_summary=f"Found {len(measures)} measures in the model."
        )
    
    elif tool_name == "list_relationships" and isinstance(tool_result, dict):
        rels = tool_result.get("relationships", [])
        rows = []
        for r in rels:
            if isinstance(r, dict):
                rows.append([
                    r.get("id", ""),
                    r.get("fromColumn", ""),
                    r.get("toColumn", ""),
                    str(r.get("isActive", "")),
                    r.get("fromCardinality", "")
                ])
        
        return FinalResponse(
            operation="display_table",
            payload={
                "title": "Model Relationships",
                "headers": ["ID", "From", "To", "Active", "Cardinality"],
                "rows": rows
            },
            human_readable_summary=f"Found {len(rels)} relationships in the model."
        )
    
    elif tool_name == "list_calculated_columns" and isinstance(tool_result, dict):
        calc_cols = tool_result.get("calculated_columns", [])
        rows = []
        for c in calc_cols:
            if isinstance(c, dict):
                rows.append([c.get("table", ""), c.get("name", "")])
        
        if not rows:
            return FinalResponse(
                operation="display_message",
                payload={"message": "No calculated columns found in the model."},
                human_readable_summary="No calculated columns found."
            )
        
        return FinalResponse(
            operation="display_table",
            payload={
                "title": "Calculated Columns",
                "headers": ["Table", "Column Name"],
                "rows": rows
            },
            human_readable_summary=f"Found {len(calc_cols)} calculated columns in the model."
        )
    
    elif tool_name == "list_partitions" and isinstance(tool_result, dict):
        partitions = tool_result.get("partitions", [])
        rows = []
        for p in partitions:
            if isinstance(p, dict):
                rows.append([
                    p.get("table", ""),
                    p.get("name", ""),
                    p.get("mode", ""),
                    p.get("source_type", ""),
                    "Yes" if p.get("has_query") else "No"
                ])
        
        if not rows:
            table_filter = tool_args.get("table", "")
            scope = f"table '{table_filter}'" if table_filter else "all tables"
            return FinalResponse(
                operation="display_message",
                payload={"message": f"No partitions found in {scope}."},
                human_readable_summary=f"No partitions found in {scope}."
            )
        
        return FinalResponse(
            operation="display_table",
            payload={
                "title": "Partitions",
                "headers": ["Table", "Partition Name", "Mode", "Source Type", "Has Query"],
                "rows": rows
            },
            human_readable_summary=f"Found {len(partitions)} partition(s)."
        )
    
    elif tool_name == "list_sql_sources" and isinstance(tool_result, dict):
        sql_sources = tool_result.get("sql_sources", [])
        rows = []
        for s in sql_sources:
            if isinstance(s, dict):
                rows.append([
                    s.get("table", ""),
                    s.get("partition", "") or "-",
                    s.get("mode", "") or "-",
                    s.get("server", "") or "-",
                    s.get("database", "") or "-",
                    s.get("source_table", "") or "-",
                    s.get("schema", "") or "-",
                    "Yes" if s.get("has_custom_query") else "No"
                ])
        
        if not rows:
            return FinalResponse(
                operation="display_message",
                payload={"message": "No SQL sources found in the model."},
                human_readable_summary="No SQL sources found."
            )
        
        return FinalResponse(
            operation="display_table",
            payload={
                "title": "SQL Sources",
                "headers": ["Table", "Partition", "Mode", "Server", "Database", "Source Table", "Schema", "Custom Query"],
                "rows": rows
            },
            human_readable_summary=f"Found {len(sql_sources)} SQL source(s)."
        )
    
    elif tool_name == "list_mquery" and isinstance(tool_result, dict):
        entries = tool_result.get("entries", [])
        rows = []
        for e in entries:
            if isinstance(e, dict):
                rows.append([
                    e.get("table", ""),
                    e.get("scope", ""),
                    e.get("partition_name", "") or "-",
                    e.get("mode", "") or "-",
                    (e.get("expression", "") or "")[:100] + ("..." if len(e.get("expression", "")) > 100 else "")
                ])
        
        if not rows:
            return FinalResponse(
                operation="display_message",
                payload={"message": "No M Query expressions found."},
                human_readable_summary="No M Query expressions found."
            )
        
        return FinalResponse(
            operation="display_table",
            payload={
                "title": "M Query Expressions",
                "headers": ["Table", "Scope", "Partition", "Mode", "Expression (preview)"],
                "rows": rows
            },
            human_readable_summary=f"Found {len(entries)} M Query expression(s)."
        )
    
    elif tool_name == "validate_relationships" and isinstance(tool_result, dict):
        issues = tool_result.get("issues", [])
        total = tool_result.get("total_relationships", 0)
        valid = tool_result.get("valid_relationships", 0)
        invalid = tool_result.get("invalid_relationships", 0)
        
        if not issues:
            return FinalResponse(
                operation="display_message",
                payload={
                    "message": f"✅ All {total} relationship(s) are valid.",
                    "success": True
                },
                human_readable_summary=f"✅ Validation passed: All {total} relationship(s) are valid."
            )
        
        # Convert issues to table format
        rows = []
        for issue in issues:
            if isinstance(issue, dict):
                rows.append([
                    issue.get("id", ""),
                    issue.get("severity", ""),
                    issue.get("issue_type", ""),
                    issue.get("message", ""),
                    issue.get("from_table", "") or "-",
                    issue.get("to_table", "") or "-"
                ])
        
        return FinalResponse(
            operation="display_table",
            payload={
                "title": f"Relationship Validation Results ({valid} valid, {invalid} invalid)",
                "headers": ["ID", "Severity", "Issue Type", "Message", "From Table", "To Table"],
                "rows": rows
            },
            human_readable_summary=tool_result.get("summary", f"Found {len(issues)} issue(s) in {total} relationship(s).")
        )
    
    elif tool_name == "schema_diff" and isinstance(tool_result, dict):
        table = tool_result.get("table", "")
        new_cols = tool_result.get("new_columns", [])
        missing_cols = tool_result.get("missing_columns", [])
        type_mismatches = tool_result.get("type_mismatches", [])
        
        # Combine all differences into one table
        rows = []
        for col in new_cols:
            if isinstance(col, dict):
                rows.append([
                    col.get("name", ""),
                    "NEW",
                    "-",
                    col.get("proposed_type", "") or "-"
                ])
        for col in missing_cols:
            if isinstance(col, dict):
                rows.append([
                    col.get("name", ""),
                    "MISSING",
                    col.get("current_type", "") or "-",
                    "-"
                ])
        for col in type_mismatches:
            if isinstance(col, dict):
                rows.append([
                    col.get("name", ""),
                    "TYPE MISMATCH",
                    col.get("current_type", "") or "-",
                    col.get("proposed_type", "") or "-"
                ])
        
        if not rows:
            return FinalResponse(
                operation="display_message",
                payload={
                    "message": f"✅ Schema for '{table}' matches proposed schema.",
                    "success": True
                },
                human_readable_summary=f"✅ Schema for '{table}' matches proposed schema."
            )
        
        return FinalResponse(
            operation="display_table",
            payload={
                "title": f"Schema Differences for {table}",
                "headers": ["Column Name", "Status", "Current Type", "Proposed Type"],
                "rows": rows
            },
            human_readable_summary=tool_result.get("message", f"Found {len(rows)} difference(s) in schema.")
        )
    
    elif tool_name == "get_measure_expression" and isinstance(tool_result, dict):
        table = tool_result.get("table", "")
        measure_name = tool_result.get("measure_name", "")
        expression = tool_result.get("dax_expression", "")
        has_expression = tool_result.get("has_expression", False)
        
        if not has_expression:
            return FinalResponse(
                operation="display_message",
                payload={
                    "message": tool_result.get("message", f"Measure '{measure_name}' has no expression."),
                    "warning": True
                },
                human_readable_summary=tool_result.get("message", f"Measure '{measure_name}' has no expression.")
            )
        
        return FinalResponse(
            operation="display_message",
            payload={
                "title": f"DAX Expression: {table}.{measure_name}",
                "message": expression,
                "code_block": True
            },
            human_readable_summary=tool_result.get("message", f"Retrieved DAX expression for {measure_name}.")
        )
    
    elif tool_name == "get_partition_source" and isinstance(tool_result, dict):
        table = tool_result.get("table", "")
        partition_name = tool_result.get("partition_name", "")
        expression = tool_result.get("expression", "")
        source_type = tool_result.get("source_type", "")
        
        return FinalResponse(
            operation="display_message",
            payload={
                "title": f"Partition Source: {table}.{partition_name} ({source_type})",
                "message": expression,
                "code_block": True
            },
            human_readable_summary=f"Retrieved {source_type} expression for partition {partition_name}."
        )
    
    elif tool_name == "get_sql_query" and isinstance(tool_result, dict):
        table = tool_result.get("table", "")
        partition_name = tool_result.get("partition_name", "")
        sql_query = tool_result.get("sql_query", "")
        connection_info = tool_result.get("connection_info", {})
        
        info_lines = []
        if connection_info:
            info_lines.append(f"Server: {connection_info.get('server', 'N/A')}")
            info_lines.append(f"Database: {connection_info.get('database', 'N/A')}")
        
        return FinalResponse(
            operation="display_message",
            payload={
                "title": f"SQL Query: {table}.{partition_name}",
                "message": "\n".join(info_lines + [""] + [sql_query]) if info_lines else sql_query,
                "code_block": True
            },
            human_readable_summary=f"Retrieved SQL query for {table}.{partition_name}."
        )
    
    elif tool_name == "extract_sql_connection" and isinstance(tool_result, dict):
        table = tool_result.get("table", "")
        partition_name = tool_result.get("partition_name", "")
        connection = tool_result.get("connection", {})
        
        rows = []
        if isinstance(connection, dict):
            rows.append(["Server", connection.get("server", "N/A")])
            rows.append(["Database", connection.get("database", "N/A")])
            rows.append(["Schema", connection.get("schema", "N/A")])
            rows.append(["Auth Type", connection.get("auth_type", "N/A")])
        
        return FinalResponse(
            operation="display_table",
            payload={
                "title": f"SQL Connection Info: {table}.{partition_name}",
                "headers": ["Property", "Value"],
                "rows": rows
            },
            human_readable_summary=f"Extracted SQL connection information for {table}.{partition_name}."
        )
    
    # Handle error results
    if isinstance(tool_result, dict) and tool_result.get("error"):
        return FinalResponse(
            operation="display_message",
            payload={
                "message": tool_result.get("error_message", "An error occurred"),
                "error": True
            },
            human_readable_summary=tool_result.get("error_message", "An error occurred")
        )
    
    # Fallback: return as display_message
    return FinalResponse(
        operation="display_message",
        payload={"message": str(tool_result)},
        human_readable_summary="Query completed."
    )


def should_convert_to_display_table(tool_name: str) -> bool:
    """Check if a tool result should be converted to display_table format."""
    return tool_name in [
        "list_tables",
        "list_columns", 
        "list_measures",
        "list_relationships",
        "list_calculated_columns",
        "list_partitions",
        "list_sql_sources",
        "list_mquery",
        "validate_relationships",
        "schema_diff",
        "extract_sql_connection"
    ]


def should_convert_to_display_message(tool_name: str) -> bool:
    """Check if a tool result should be converted to display_message format."""
    return tool_name in [
        "get_measure_expression",
        "get_partition_source",
        "get_sql_query",
        "validate_dax",
        "validate_sql",
        "validate_mquery",
        "complete_task"
    ]


def convert_any_tool_result(
    tool_name: str,
    tool_result: Any,
    tool_args: Dict[str, Any] = None
) -> FinalResponse:
    """
    Convert any tool result to appropriate FinalResponse format.
    
    This is a comprehensive converter that handles:
    - List/query tools → display_table
    - Get/retrieve tools → display_message (with code blocks if applicable)
    - Validation tools → display_table or display_message
    - Error results → display_message with error flag
    - Unknown formats → display_message fallback
    
    Args:
        tool_name: Name of the tool
        tool_result: The result from the tool (dict, list, string, etc.)
        tool_args: Optional tool arguments for context
        
    Returns:
        FinalResponse with appropriate operation and formatted payload
    """
    tool_args = tool_args or {}
    
    # Handle non-dict results
    if not isinstance(tool_result, dict):
        if isinstance(tool_result, list):
            # List of items - try to format as table
            if tool_result and isinstance(tool_result[0], dict):
                # List of dicts - extract keys as headers
                headers = list(tool_result[0].keys())
                rows = [[str(item.get(k, "")) for k in headers] for item in tool_result]
                return FinalResponse(
                    operation="display_table",
                    payload={
                        "title": f"Results ({len(tool_result)} items)",
                        "headers": headers,
                        "rows": rows
                    },
                    human_readable_summary=f"Found {len(tool_result)} item(s)."
                )
            else:
                # Simple list - single column
                return FinalResponse(
                    operation="display_table",
                    payload={
                        "title": "Results",
                        "headers": ["Item"],
                        "rows": [[str(item)] for item in tool_result]
                    },
                    human_readable_summary=f"Found {len(tool_result)} item(s)."
                )
        else:
            # String or other simple type
            return FinalResponse(
                operation="display_message",
                payload={"message": str(tool_result)},
                human_readable_summary=str(tool_result)
            )
    
    # Handle dict results - use specific converters
    if should_convert_to_display_table(tool_name):
        return convert_list_tool_result_to_display_table(tool_name, tool_result, tool_args)
    
    # Handle get/retrieve tools
    if should_convert_to_display_message(tool_name):
        return convert_get_tool_result_to_message(tool_name, tool_result, tool_args)
    
    # Try generic conversion for dict results
    if isinstance(tool_result, dict):
        # Check if it's already a FinalResponse-like structure
        if "operation" in tool_result and "payload" in tool_result:
            return FinalResponse(
                operation=tool_result.get("operation", "display_message"),
                payload=tool_result.get("payload", {}),
                human_readable_summary=tool_result.get("human_readable_summary", "Task completed.")
            )
        
        # Try to infer table format from dict keys
        if len(tool_result) > 0:
            # Check if it looks like a list result (has a list field)
            for key, value in tool_result.items():
                if isinstance(value, list) and len(value) > 0:
                    if isinstance(value[0], dict):
                        # List of dicts - convert to table
                        headers = list(value[0].keys())
                        rows = [[str(item.get(k, "")) for k in headers] for item in value]
                        return FinalResponse(
                            operation="display_table",
                            payload={
                                "title": key.replace("_", " ").title(),
                                "headers": headers,
                                "rows": rows
                            },
                            human_readable_summary=f"Found {len(value)} {key}."
                        )
    
    # Final fallback
    return FinalResponse(
        operation="display_message",
        payload={"message": str(tool_result)},
        human_readable_summary="Task completed."
    )


def convert_get_tool_result_to_message(
    tool_name: str,
    tool_result: Dict[str, Any],
    tool_args: Dict[str, Any] = None
) -> FinalResponse:
    """Convert get/retrieve tool results to display_message format."""
    tool_args = tool_args or {}
    
    if tool_name == "get_measure_expression":
        table = tool_result.get("table", "")
        measure_name = tool_result.get("measure_name", "")
        expression = tool_result.get("dax_expression", "")
        has_expression = tool_result.get("has_expression", False)
        
        if not has_expression:
            return FinalResponse(
                operation="display_message",
                payload={
                    "message": tool_result.get("message", f"Measure '{measure_name}' has no expression."),
                    "warning": True
                },
                human_readable_summary=tool_result.get("message", f"Measure '{measure_name}' has no expression.")
            )
        
        return FinalResponse(
            operation="display_message",
            payload={
                "title": f"DAX Expression: {table}.{measure_name}",
                "message": expression,
                "code_block": True
            },
            human_readable_summary=tool_result.get("message", f"Retrieved DAX expression for {measure_name}.")
        )
    
    elif tool_name == "get_partition_source":
        table = tool_result.get("table", "")
        partition_name = tool_result.get("partition_name", "")
        expression = tool_result.get("expression", "")
        source_type = tool_result.get("source_type", "")
        
        return FinalResponse(
            operation="display_message",
            payload={
                "title": f"Partition Source: {table}.{partition_name} ({source_type})",
                "message": expression,
                "code_block": True
            },
            human_readable_summary=f"Retrieved {source_type} expression for partition {partition_name}."
        )
    
    elif tool_name == "get_sql_query":
        table = tool_result.get("table", "")
        partition_name = tool_result.get("partition_name", "")
        sql_query = tool_result.get("sql_query", "")
        connection_info = tool_result.get("connection_info", {})
        
        info_lines = []
        if connection_info:
            info_lines.append(f"Server: {connection_info.get('server', 'N/A')}")
            info_lines.append(f"Database: {connection_info.get('database', 'N/A')}")
        
        return FinalResponse(
            operation="display_message",
            payload={
                "title": f"SQL Query: {table}.{partition_name}",
                "message": "\n".join(info_lines + [""] + [sql_query]) if info_lines else sql_query,
                "code_block": True
            },
            human_readable_summary=f"Retrieved SQL query for {table}.{partition_name}."
        )
    
    elif tool_name == "complete_task":
        summary = tool_result.get("summary", "")
        final_result = tool_result.get("final_result", "")
        
        message = summary
        if final_result and final_result != summary:
            message = f"{summary}\n\n{final_result}"
        
        return FinalResponse(
            operation="display_message",
            payload={"message": message},
            human_readable_summary=summary or "Task completed."
        )
    
    # Default for get tools
    message = tool_result.get("message") or str(tool_result)
    return FinalResponse(
        operation="display_message",
        payload={"message": message},
        human_readable_summary=message
    )

