---
title: Structured Final Response
---

# Structured Final Response Pattern

## Overview

The **Structured Final Response** pattern enables agents to return machine-readable, actionable data instead of simple text strings. This pattern solves the problem of passing structured data from the agent's reasoning loop to external systems (like frontends) without fragile string parsing.

## The Problem

Without structured responses, agents return simple text:

```python
"I have successfully completed the task."
```

This is fine for chat logs but:
- ❌ Not machine-readable
- ❌ Requires brittle string parsing
- ❌ No clear contract between agent and application
- ❌ Difficult to trigger specific UI behaviors

## The Solution

The framework provides a `FinalResponse` class that agents can return with:

- **`operation`**: High-level command for the application (e.g., "display_message", "display_table")
- **`payload`**: JSON data to execute the operation
- **`human_readable_summary`**: Natural language text for chat display

```python
from agent_framework import FinalResponse

FinalResponse(
    operation="display_table",
    payload={
        "title": "Results",
        "headers": ["Column 1", "Column 2"],
        "rows": [["Value 1", "Value 2"]]
    },
    human_readable_summary="Found 1 result matching your query."
)
```

## Framework Type Definition

The `FinalResponse` class is defined in `agent_framework.base`:

```python
from pydantic import BaseModel, Field
from typing import Dict, Any

class FinalResponse(BaseModel):
    """
    Represents a final, structured response to the user or application.
    
    This is returned when the agent has completed its task and needs to communicate
    the result in a machine-readable format for frontend consumption.
    """
    operation: str = Field(
        ..., 
        description="The high-level operation the frontend should perform (e.g., 'display_message', 'update_file_tree', 'display_table')."
    )
    payload: Dict[str, Any] = Field(
        ..., 
        description="A JSON object containing the data needed to execute the operation."
    )
    human_readable_summary: str = Field(
        ..., 
        description="A natural language summary of the result for display in a chat log."
    )
```

## How Agents Return FinalResponse

### 1. From Planner's `plan()` Method

Planners can return `FinalResponse` directly from their `plan()` method:

```python
from agent_framework import BasePlanner, FinalResponse

class MyPlanner(BasePlanner):
    def plan(self, task_description: str, history: List[Dict[str, Any]]) -> Union[Action, List[Action], FinalResponse]:
        # ... reasoning ...
        
        if task_complete:
            return FinalResponse(
                operation="display_message",
                payload={"message": "Task completed successfully."},
                human_readable_summary="Task completed successfully."
            )
        
        # Otherwise return Action(s)
        return Action(tool_name="some_tool", tool_args={...})
```

### 2. From ReActPlanner LLM Output

The `ReActPlanner` can parse structured `final_response` from LLM JSON output:

```python
# LLM returns JSON like:
{
    "thought": "I have completed the task...",
    "final_response": {
        "operation": "display_table",
        "payload": {
            "headers": ["Name", "Value"],
            "rows": [["Item 1", "100"]]
        },
        "human_readable_summary": "Found 1 item."
    }
}

# ReActPlanner automatically converts this to FinalResponse
```

The planner supports both:
- **New format**: `{"final_response": {...}}`
- **Legacy format**: `{"final_answer": "..."}` (automatically converted to `FinalResponse`)

### 3. From Agent's `run()` Method

Agents return `FinalResponse` directly from `run()`:

```python
from agent_framework import Agent

agent = Agent(...)
result = await agent.run(task="Your task here")

# result is a FinalResponse object
print(result.operation)  # e.g., "display_message"
print(result.payload)    # Dict with operation data
print(result.human_readable_summary)  # Human-readable text
```

## Event Publishing

When an agent returns a `FinalResponse`, the framework automatically publishes an `agent_end` event with the structured data:

```python
# Framework automatically does this:
event_bus.publish("agent_end", {
    "result": final_response.model_dump(),
    "operation": final_response.operation,
    "payload": final_response.payload,
    "summary": final_response.human_readable_summary
})
```

## Common Operation Types

The framework doesn't prescribe specific operation types - you define them based on your application's needs. Common patterns include:

### 1. `display_message`

Simple text responses.

```python
FinalResponse(
    operation="display_message",
    payload={"message": "Task completed successfully."},
    human_readable_summary="Task completed successfully."
)
```

### 2. `display_table`

Structured tabular data.

```python
FinalResponse(
    operation="display_table",
    payload={
        "title": "Query Results",
        "headers": ["Column 1", "Column 2"],
        "rows": [
            ["Row 1 Col 1", "Row 1 Col 2"],
            ["Row 2 Col 1", "Row 2 Col 2"]
        ]
    },
    human_readable_summary="Found 2 results."
)
```

### 3. `display_data`

Structured JSON data (lists, objects, etc.).

```python
FinalResponse(
    operation="display_data",
    payload={
        "data": [
            {"id": 1, "name": "Item 1"},
            {"id": 2, "name": "Item 2"}
        ],
        "metadata": {"total": 2}
    },
    human_readable_summary="Retrieved 2 items."
)
```

### 4. Application-Specific Operations

Your implementation can define any operation types you need:

```python
# Example: File operations
FinalResponse(
    operation="update_file_tree",
    payload={
        "changed_files": ["path/to/file1", "path/to/file2"],
        "details": "Modified 2 files"
    },
    human_readable_summary="Successfully updated files."
)

# Example: Custom UI operations
FinalResponse(
    operation="show_visualization",
    payload={
        "chart_type": "bar",
        "data": {...}
    },
    human_readable_summary="Displaying chart visualization."
)
```

## Integration with Application

### Receiving FinalResponse

Applications can receive `FinalResponse` objects and handle them based on operation type:

```python
# Example: FastAPI endpoint
from agent_framework import Agent, FinalResponse

@app.post("/run")
async def run_agent(task: str):
    agent = Agent(...)
    result = await agent.run(task=task)  # Returns FinalResponse
    
    # Return structured response to frontend
    return {
        "operation": result.operation,
        "payload": result.payload,
        "summary": result.human_readable_summary
    }
```

### Handling Different Operations

Applications can route based on operation type:

```python
result = await agent.run(task="...")

if result.operation == "display_table":
    # Render table UI component
    render_table(result.payload)
elif result.operation == "display_message":
    # Show simple message
    show_message(result.human_readable_summary)
elif result.operation == "display_data":
    # Render structured data
    render_data(result.payload)
else:
    # Unknown operation - fallback to summary
    show_message(result.human_readable_summary)
```

## Prompt Engineering

To instruct LLMs to return structured responses, include this in your planner's system prompt:

```python
system_prompt = """
...
When your task is complete, return a JSON response with a "final_response" key:

{
    "thought": "I have completed the task...",
    "final_response": {
        "operation": "<operation_type>",
        "payload": { ...data... },
        "human_readable_summary": "Natural language summary"
    }
}

Common operation types:
- display_message: Simple text response
- display_table: Tabular data with headers and rows
- display_data: Structured JSON data
- [Add your custom operation types here]
"""
```

## Backward Compatibility

The framework maintains backward compatibility with legacy string responses:

1. **Legacy format support**: Planners can still return `{"final_answer": "..."}` which is automatically converted to `FinalResponse`
2. **Fallback behavior**: If no structured response is provided, the framework creates a default `FinalResponse` with `operation="display_message"`

## Benefits

✅ **Type Safety**: Pydantic validation ensures the contract is enforced  
✅ **Decoupling**: Agent doesn't need to know about application UI details  
✅ **Extensibility**: Add new operation types without framework changes  
✅ **Machine-Readable**: Structured data that applications can process  
✅ **Human-Friendly**: Always includes natural language summary for display  

## Summary

The `FinalResponse` pattern transforms agent outputs from "strings to parse" into "commands to execute", making the entire system more reliable, maintainable, and extensible. Applications can handle different operation types programmatically while still providing human-readable summaries for chat logs.

This is a framework capability that implementations can leverage to create rich, interactive agent experiences.
