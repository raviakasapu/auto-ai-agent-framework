# Tools Guide

Tools provide agents with capabilities to interact with external systems, perform computations, and take actions.

## Overview

Tools are defined in the `resources` section and referenced in the `spec.tools` list:

```yaml
resources:
  tools:
    - name: calculator
      type: CalculatorTool
      config: {}
    - name: web_search
      type: MockSearchTool
      config: {}

spec:
  tools: [calculator, web_search]
```

---

## Built-in Tools

### CalculatorTool

Performs mathematical calculations.

```yaml
- name: calculator
  type: CalculatorTool
  config: {}
```

**Parameters:**
| Field | Type | Description |
|-------|------|-------------|
| `expression` | string | Mathematical expression to evaluate |

**Example Usage:**
```
Calculate: 42 * 17 + 123
```

---

### MockSearchTool

Simulates web search (for testing/development).

```yaml
- name: web_search
  type: MockSearchTool
  config: {}
```

**Parameters:**
| Field | Type | Description |
|-------|------|-------------|
| `query` | string | Search query |

**Note:** Returns mock results. Replace with real search implementation in production.

---

### NoteTakerTool

Creates and stores notes.

```yaml
- name: note_taker
  type: NoteTakerTool
  config:
    storage_path: /tmp/notes.json
```

**Config Options:**
| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `storage_path` | string | `/tmp/notes.json` | File path for note storage |

**Parameters:**
| Field | Type | Description |
|-------|------|-------------|
| `title` | string | Note title |
| `content` | string | Note content |

---

### TaskManagerTool

Creates new tasks.

```yaml
- name: create_task
  type: TaskManagerTool
  config: {}
```

**Parameters:**
| Field | Type | Description |
|-------|------|-------------|
| `title` | string | Task title |
| `description` | string | Task description |
| `priority` | string | Priority level (low, medium, high) |

---

### ListTasksTool

Lists existing tasks.

```yaml
- name: list_tasks
  type: ListTasksTool
  config: {}
```

**Parameters:**
| Field | Type | Description |
|-------|------|-------------|
| `status` | string | Filter by status (optional) |
| `priority` | string | Filter by priority (optional) |

---

### CompleteTaskTool

Marks a task as completed.

```yaml
- name: complete_task
  type: CompleteTaskTool
  config: {}
```

**Parameters:**
| Field | Type | Description |
|-------|------|-------------|
| `task_id` | string | ID of task to complete |

---

### WeatherLookupTool

Retrieves weather information.

```yaml
- name: weather_lookup
  type: WeatherLookupTool
  config: {}
```

**Parameters:**
| Field | Type | Description |
|-------|------|-------------|
| `location` | string | City or location name |

---

## Creating Custom Tools

### Using the `@tool` Decorator

The quickest way to ship a tool is with the decorator, which converts any type-hinted function into a fully fledged tool:

```python
from agent_framework import tool

@tool(name="add", description="Add two numbers")
def add(a: int, b: int) -> int:
    """Add two numbers and return the sum."""
    return a + b
```

**Why use it?**

- Auto-generates a Pydantic `args_schema` from type hints
- Uses the docstring as the description and parameter metadata
- Returns a `FunctionalTool` instance behind the scenes

Docstrings can include inline parameter docs:

```python
@tool
def greet(name: str, formal: bool = False) -> str:
    """Generate a greeting message.

    name: The name of the person to greet
    formal: Whether to use formal greeting style
    """
    return f"Good day, {name}." if formal else f"Hello, {name}!"
```

### `FunctionalTool`

Use `FunctionalTool` directly when you need to wrap existing callables:

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

### Class-Based Tools

Use classes when you need initialization logic, dependencies, or custom output schemas.

```python
from pydantic import BaseModel, Field
from agent_framework.core.types import Tool


class MyToolArgs(BaseModel):
    param1: str = Field(description="First parameter")
    param2: int = Field(default=10, description="Second parameter")


class MyCustomTool(Tool):
    name = "my_custom_tool"
    description = "Does something useful"
    args_schema = MyToolArgs

    async def execute(self, param1: str, param2: int = 10) -> dict:
        result = f"Processed {param1} with {param2}"
        return {"result": result, "status": "success"}
```

When to choose class-based tools:

| Use Case | Decorator | Class-based |
|----------|-----------|-------------|
| Stateless utility | ✅ | ❌ |
| Needs configuration (DB/API) | ❌ | ✅ |
| Custom output schema | ❌ | ✅ |
| Requires cleanup hooks | ❌ | ✅ |

### Registering Custom Tools

Register classes so the factory can resolve them from YAML:

```python
from deployment.registry import register_tool
from tools.custom_tools import MyCustomTool

register_tool("MyCustomTool", MyCustomTool)
```

You can also modify `TOOL_REGISTRY` directly inside `deployment/registry.py` if you prefer static registration.

### Using in YAML

```yaml
resources:
  tools:
    - name: my_tool
      type: MyCustomTool
      config: {}

spec:
  tools: [my_tool]
```

---

## Tool Configuration

### Config Options

Tools can accept configuration via the `config` field:

```yaml
- name: database_tool
  type: DatabaseTool
  config:
    connection_string: ${DATABASE_URL}
    timeout: 30
    max_retries: 3
```

### Environment Variables

Use `${VAR}` or `${VAR:-default}` for configuration:

```yaml
- name: api_tool
  type: APITool
  config:
    api_key: ${API_KEY}
    base_url: ${API_URL:-https://api.example.com}
```

---

## Tool Patterns

### Read-Only Tools

Tools that only retrieve information:

```python
class ReadOnlyTool(Tool):
    name = "data_reader"
    description = "Reads data without modification"

    async def execute(self, query: str) -> dict:
        data = await self.fetch_data(query)
        return {"data": data}
```

### Write Tools

Tools that modify state (consider HITL policy):

```python
class WriteTool(Tool):
    name = "data_writer"
    description = "Writes data to storage"

    async def execute(self, key: str, value: str) -> dict:
        await self.store_data(key, value)
        return {"status": "written", "key": key}
```

### Composite Tools

Tools that combine multiple operations:

```python
class CompositeSearchTool(Tool):
    name = "smart_search"
    description = "Search and summarize results"

    async def execute(self, query: str) -> dict:
        results = await self.search(query)
        summary = await self.summarize(results)
        return {"results": results, "summary": summary}
```

---

## Output Patterns

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

Providing a `human_readable_summary` (or similar field) makes it easier for planners to describe results to users.

### Error Objects

Return structured errors rather than raising whenever possible so policies can decide how to proceed:

```python
@tool
def risky_operation(data: str) -> dict:
    try:
        result = process(data)
        return {"success": True, "result": result}
    except Exception as exc:
        return {
            "success": False,
            "error": True,
            "error_message": str(exc),
            "error_type": type(exc).__name__,
        }
```

---

## Error Handling

### Tool Errors

Return errors in a structured format:

```python
class SafeTool(Tool):
    async def execute(self, **kwargs) -> dict:
        try:
            result = await self.do_work(**kwargs)
            return {"success": True, "result": result}
        except ValueError as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            return {"success": False, "error": f"Unexpected error: {e}"}
```

### Validation

Use Pydantic for input validation:

```python
class StrictToolArgs(BaseModel):
    email: str = Field(pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$')
    count: int = Field(ge=1, le=100)


class StrictTool(Tool):
    args_schema = StrictToolArgs
    # Pydantic validates inputs automatically
```

---

## Complete Example

### Custom API Tool

```python
# tools/api_tool.py
import aiohttp
from pydantic import BaseModel, Field
from agent_framework.core.types import Tool


class APICallArgs(BaseModel):
    endpoint: str = Field(description="API endpoint path")
    method: str = Field(default="GET", description="HTTP method")
    data: dict = Field(default={}, description="Request body")


class APITool(Tool):
    """Tool for making API calls."""

    name = "api_call"
    description = "Makes HTTP requests to an API"
    args_schema = APICallArgs

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key

    async def execute(
        self,
        endpoint: str,
        method: str = "GET",
        data: dict = None
    ) -> dict:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        async with aiohttp.ClientSession() as session:
            async with session.request(
                method,
                url,
                headers=headers,
                json=data
            ) as response:
                result = await response.json()
                return {
                    "status_code": response.status,
                    "data": result
                }
```

### Registry Entry

```python
# deployment/registry.py
from tools.api_tool import APITool

TOOL_REGISTRY = {
    "APITool": APITool,
    # ...
}
```

### YAML Configuration

```yaml
resources:
  tools:
    - name: github_api
      type: APITool
      config:
        base_url: https://api.github.com
        api_key: ${GITHUB_TOKEN}

spec:
  tools: [github_api]
```

---

### Agent Wiring Example

```python
from agent_framework import Agent, tool, get_preset
from agent_framework.components.planners import ReActPlanner
from agent_framework.components.memory import SimpleMemory
from agent_framework.gateways.inference import OpenAIGateway

@tool(name="get_weather", description="Get current weather for a city")
def get_weather(city: str) -> dict:
    return {
        "city": city,
        "temperature": 72,
        "condition": "sunny",
        "human_readable_summary": f"It's 72°F and sunny in {city}",
    }

@tool(name="get_forecast", description="Get 5-day weather forecast")
def get_forecast(city: str, days: int = 5) -> dict:
    return {
        "city": city,
        "forecast": [{"day": i, "temp": 70 + i} for i in range(days)],
        "human_readable_summary": f"{days}-day forecast for {city}",
    }

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

result = await agent.run("What's the weather in Seattle?")
```

---

## Best Practices

1. **Single responsibility** - Each tool should do one thing well
2. **Clear descriptions** - Help the LLM understand when to use the tool
3. **Structured responses** - Return consistent JSON structures
4. **Error handling** - Always handle and report errors gracefully
5. **Validation** - Use Pydantic schemas for input validation
6. **Idempotency** - Design write operations to be safely retriable
7. **Timeouts** - Set appropriate timeouts for external calls
8. **Logging** - Log tool executions for debugging
