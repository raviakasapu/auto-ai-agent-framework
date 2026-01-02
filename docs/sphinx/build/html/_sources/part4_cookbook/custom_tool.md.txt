# Recipe: Custom Tool

Create domain-specific tools for your agents.

## Goal

Create a tool that integrates with an external API.

## Method 1: @tool Decorator (Simple)

```python
from agent_framework import tool
import httpx

@tool(name="fetch_weather", description="Get current weather for a city")
def fetch_weather(city: str, units: str = "celsius") -> dict:
    """Fetch weather data from external API.
    
    city: Name of the city
    units: Temperature units (celsius or fahrenheit)
    """
    response = httpx.get(
        f"https://api.weather.example/v1/current",
        params={"city": city, "units": units}
    )
    data = response.json()
    
    return {
        "city": city,
        "temperature": data["temp"],
        "condition": data["condition"],
        "human_readable_summary": f"{city}: {data['temp']}° {data['condition']}"
    }
```

## Method 2: Class-Based (With State)

```python
from agent_framework import BaseTool
from pydantic import BaseModel
from typing import Type, Optional, Any
import httpx

class WeatherArgs(BaseModel):
    city: str
    units: str = "celsius"

class WeatherOutput(BaseModel):
    city: str
    temperature: float
    condition: str
    human_readable_summary: str

class WeatherTool(BaseTool):
    def __init__(self, api_key: str, base_url: str = "https://api.weather.example"):
        self.api_key = api_key
        self.base_url = base_url
        self.client = httpx.Client(
            headers={"Authorization": f"Bearer {api_key}"}
        )
    
    @property
    def name(self) -> str:
        return "fetch_weather"
    
    @property
    def description(self) -> str:
        return "Get current weather for a city"
    
    @property
    def args_schema(self) -> Type[BaseModel]:
        return WeatherArgs
    
    @property
    def output_schema(self) -> Optional[Type[BaseModel]]:
        return WeatherOutput
    
    def execute(self, city: str, units: str = "celsius") -> dict:
        response = self.client.get(
            f"{self.base_url}/v1/current",
            params={"city": city, "units": units}
        )
        data = response.json()
        
        return {
            "city": city,
            "temperature": data["temp"],
            "condition": data["condition"],
            "human_readable_summary": f"{city}: {data['temp']}° {data['condition']}"
        }
```

## Registration

```python
from deployment.registry import register_tool

# Decorator-based
register_tool("FetchWeather", fetch_weather)

# Class-based
register_tool("WeatherTool", WeatherTool)
```

## YAML Usage

```yaml
resources:
  tools:
    - name: weather
      type: WeatherTool
      config:
        api_key: ${WEATHER_API_KEY}
        base_url: https://api.weather.example

spec:
  tools: [weather]
```

## Error Handling

```python
@tool(name="safe_fetch", description="Fetch with error handling")
def safe_fetch(url: str) -> dict:
    try:
        response = httpx.get(url, timeout=10)
        response.raise_for_status()
        return {
            "success": True,
            "data": response.json(),
            "human_readable_summary": "Data fetched successfully"
        }
    except httpx.TimeoutException:
        return {
            "success": False,
            "error": True,
            "error_message": "Request timed out",
            "error_type": "TimeoutError"
        }
    except Exception as e:
        return {
            "success": False,
            "error": True,
            "error_message": str(e),
            "error_type": type(e).__name__
        }
```

## Key Points

- Use `@tool` for simple, stateless tools
- Use class-based for stateful tools or dependencies
- Always include `human_readable_summary` in output
- Handle errors gracefully (return error dict, don't raise)
- Register for YAML usage

