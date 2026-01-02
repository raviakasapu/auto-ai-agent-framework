# Tools & Decorators

This chapter covers tool creation: the `@tool` decorator, `FunctionalTool`, and class-based tools.

## The @tool Decorator

The recommended way to create tools is with the `@tool` decorator:

```python
from agent_framework import tool

@tool(name="add", description="Add two numbers")
def add(a: int, b: int) -> int:
    """Add two numbers and return the sum."""
    return a + b
```

### Features

- **Auto-generates** Pydantic `args_schema` from type hints
- **Uses docstring** as description if not provided
- **Parses docstring** for parameter descriptions
- **Returns** `FunctionalTool` instance (implements `BaseTool`)

### Usage Patterns

```python
# Minimal - uses function name and docstring
@tool
def multiply(x: float, y: float) -> float:
    """Multiply two numbers."""
    return x * y

# With custom name and description
@tool(name="calculator_add", description="Perform addition")
def add(a: float, b: float) -> float:
    return a + b

# With custom schema
from pydantic import BaseModel

class SearchArgs(BaseModel):
    query: str
    limit: int = 10
    include_metadata: bool = False

@tool(name="search", args_schema=SearchArgs)
def search(query: str, limit: int = 10, include_metadata: bool = False) -> list:
    """Search for items matching query."""
    return [f"result_{i}" for i in range(limit)]
```

### Docstring Parsing

The decorator extracts parameter descriptions from docstrings:

```python
@tool
def greet(name: str, formal: bool = False) -> str:
    """Generate a greeting message.
    
    name: The name of the person to greet
    formal: Whether to use formal greeting style
    """
    if formal:
        return f"Good day, {name}."
    return f"Hello, {name}!"

# args_schema will have descriptions for 'name' and 'formal'
```

## FunctionalTool Class

The `@tool` decorator creates `FunctionalTool` instances internally. You can also use it directly:

```python
from agent_framework import FunctionalTool

def my_function(x: int, y: int) -> int:
    """Add numbers."""
    return x + y

tool = FunctionalTool(
    func=my_function,
    name="custom_add",
    description="Custom addition tool",
)
```

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `name` | `str` | Tool identifier |
| `description` | `str` | Human-readable description (used by LLM) |
| `args_schema` | `Type[BaseModel]` | Pydantic model for input validation |
| `output_schema` | `Type[BaseModel]` | Optional output validation model |

### Methods

```python
# Execute with validation
result = tool.execute(x=1, y=2)

# Direct call (same as execute)
result = tool(x=1, y=2)
```

## Class-Based Tools

For complex tools requiring state or dependencies, use class-based tools:

```python
from agent_framework import BaseTool
from pydantic import BaseModel
from typing import Type, Optional, Any

class DatabaseQueryArgs(BaseModel):
    query: str
    timeout: int = 30

class DatabaseQueryOutput(BaseModel):
    rows: list
    count: int

class DatabaseQueryTool(BaseTool):
    def __init__(self, connection_string: str):
        self._connection = self._connect(connection_string)
    
    @property
    def name(self) -> str:
        return "database_query"
    
    @property
    def description(self) -> str:
        return "Execute a SQL query against the database"
    
    @property
    def args_schema(self) -> Type[BaseModel]:
        return DatabaseQueryArgs
    
    @property
    def output_schema(self) -> Optional[Type[BaseModel]]:
        return DatabaseQueryOutput
    
    def execute(self, query: str, timeout: int = 30) -> dict:
        rows = self._connection.execute(query, timeout=timeout)
        return {"rows": rows, "count": len(rows)}
    
    def _connect(self, conn_str: str):
        # Connection logic
        pass
```

### When to Use Class-Based Tools

| Use Case | Decorator | Class-Based |
|----------|-----------|-------------|
| Simple functions | ✅ | ❌ |
| Stateless operations | ✅ | ❌ |
| Requires initialization | ❌ | ✅ |
| Needs dependencies (DB, API) | ❌ | ✅ |
| Complex output schema | ❌ | ✅ |
| Requires cleanup | ❌ | ✅ |

## Tool Registration

Tools are registered for use with the factory:

```python
from deployment.registry import register_tool

# Register a decorated tool
@tool(name="my_tool", description="...")
def my_tool(x: int) -> int:
    return x * 2

register_tool("MyTool", my_tool)

# Register a class-based tool
register_tool("DatabaseQueryTool", DatabaseQueryTool)
```

### YAML Configuration

Reference registered tools in YAML:

```yaml
resources:
  tools:
    - name: my_tool
      type: MyTool
      config: {}
    - name: db_query
      type: DatabaseQueryTool
      config:
        connection_string: ${DATABASE_URL}
```

## Tool Output Patterns

### Simple Return

```python
@tool
def calculate(expression: str) -> str:
    return str(eval(expression))
```

### Structured Return

```python
@tool
def list_tables() -> dict:
    return {
        "tables": ["users", "orders", "products"],
        "count": 3,
        "human_readable_summary": "Found 3 tables"
    }
```

### Error Handling

```python
@tool
def risky_operation(data: str) -> dict:
    try:
        result = process(data)
        return {"success": True, "result": result}
    except Exception as e:
        return {
            "success": False,
            "error": True,
            "error_message": str(e),
            "error_type": type(e).__name__
        }
```

## Best Practices

1. **Always use type hints** — Required for schema generation
2. **Write clear docstrings** — Used by LLM for tool selection
3. **Return structured data** — Include `human_readable_summary` for display
4. **Handle errors gracefully** — Return error dicts instead of raising
5. **Keep tools focused** — One tool, one responsibility
6. **Validate inputs** — Use Pydantic models for complex inputs

## Built-in Utility Tools

The framework includes generic utility tools:

| Tool | Description | Location |
|------|-------------|----------|
| `CalculatorTool` | Basic arithmetic | `agent_framework.tools.utility` |
| `GlobTool` | Find files by pattern | `agent_framework.tools.utility` |
| `GrepTool` | Search file contents | `agent_framework.tools.utility` |

```python
from agent_framework.tools.utility import CalculatorTool, GlobTool, GrepTool

calculator = CalculatorTool()
glob_tool = GlobTool()
grep_tool = GrepTool()
```

## Complete Example

```python
from agent_framework import Agent, tool, get_preset
from agent_framework.components.planners import ReActPlanner
from agent_framework.components.memory import SimpleMemory
from agent_framework.gateways.inference import OpenAIGateway

# Define tools with @tool decorator
@tool(name="get_weather", description="Get current weather for a city")
def get_weather(city: str) -> dict:
    """Get current weather information.
    
    city: Name of the city to get weather for
    """
    # Mock implementation
    return {
        "city": city,
        "temperature": 72,
        "condition": "sunny",
        "human_readable_summary": f"It's 72°F and sunny in {city}"
    }

@tool(name="get_forecast", description="Get 5-day weather forecast")
def get_forecast(city: str, days: int = 5) -> dict:
    """Get weather forecast.
    
    city: Name of the city
    days: Number of days to forecast (max 7)
    """
    return {
        "city": city,
        "forecast": [{"day": i, "temp": 70 + i} for i in range(days)],
        "human_readable_summary": f"{days}-day forecast for {city}"
    }

# Create agent with tools
agent = Agent(
    name="weather_agent",
    planner=ReActPlanner(
        inference_gateway=OpenAIGateway(),
        tools=[get_weather, get_forecast],
    ),
    memory=SimpleMemory(),
    tools=[get_weather, get_forecast],
    policies=get_preset("simple"),
)

# Run
result = await agent.run("What's the weather in Seattle?")
```

