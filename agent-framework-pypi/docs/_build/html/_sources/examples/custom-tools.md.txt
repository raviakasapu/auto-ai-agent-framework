# Custom Tools Examples

This page provides examples of creating and using custom tools with the AI Agent Framework.

## Basic Custom Tool

A simple custom tool with Pydantic validation.

### Tool Implementation

```python
# tools/greeting_tool.py
from pydantic import BaseModel, Field
from agent_framework.core.types import Tool


class GreetingArgs(BaseModel):
    """Arguments for the greeting tool."""
    name: str = Field(description="Name of the person to greet")
    formal: bool = Field(default=False, description="Use formal greeting")


class GreetingTool(Tool):
    """A simple greeting tool."""

    name = "greeting"
    description = "Generates a greeting for a person"
    args_schema = GreetingArgs

    async def execute(self, name: str, formal: bool = False) -> dict:
        if formal:
            greeting = f"Good day, {name}. How may I assist you?"
        else:
            greeting = f"Hey {name}! What's up?"

        return {
            "greeting": greeting,
            "style": "formal" if formal else "casual"
        }
```

### Registry Registration

```python
# deployment/registry.py
from tools.greeting_tool import GreetingTool

TOOL_REGISTRY = {
    # ... existing tools ...
    "GreetingTool": GreetingTool,
}
```

### YAML Configuration

```yaml
# configs/agents/greeter.yaml
apiVersion: agent.framework/v2
kind: Agent

metadata:
  name: Greeter

resources:
  inference_gateways:
    - name: openai
      type: OpenAIGateway
      config:
        model: gpt-4o-mini
        api_key: ${OPENAI_API_KEY}
        use_function_calling: true

  tools:
    - name: greeting
      type: GreetingTool
      config: {}

spec:
  policies:
    $preset: simple

  planner:
    type: ReActPlanner
    config:
      inference_gateway: openai
      use_function_calling: true
      system_prompt: |
        You are a friendly assistant.
        Use the greeting tool to greet users.

  memory:
    $preset: standalone

  tools: [greeting]
```

---

## Configurable Tool

A tool that accepts configuration from YAML.

### Tool Implementation

```python
# tools/api_client_tool.py
from pydantic import BaseModel, Field
from agent_framework.core.types import Tool
import aiohttp


class APICallArgs(BaseModel):
    endpoint: str = Field(description="API endpoint path")
    method: str = Field(default="GET", description="HTTP method")


class APIClientTool(Tool):
    """Tool for making API calls to a configured endpoint."""

    name = "api_client"
    description = "Makes HTTP requests to a configured API"
    args_schema = APICallArgs

    def __init__(self, base_url: str, api_key: str = None, timeout: int = 30):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    async def execute(self, endpoint: str, method: str = "GET") -> dict:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method,
                    url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    data = await response.json()
                    return {
                        "status_code": response.status,
                        "data": data
                    }
        except Exception as e:
            return {
                "error": str(e),
                "status_code": 0
            }
```

### YAML Configuration

```yaml
resources:
  tools:
    - name: github_api
      type: APIClientTool
      config:
        base_url: https://api.github.com
        api_key: ${GITHUB_TOKEN}
        timeout: 60
```

---

## Database Tool

A tool for database operations with connection pooling.

### Tool Implementation

```python
# tools/database_tool.py
from pydantic import BaseModel, Field
from agent_framework.core.types import Tool
from typing import Optional, List, Dict, Any


class QueryArgs(BaseModel):
    query: str = Field(description="SQL query to execute")
    params: Optional[List[Any]] = Field(default=None, description="Query parameters")


class DatabaseTool(Tool):
    """Tool for executing database queries."""

    name = "database"
    description = "Executes SQL queries against the database"
    args_schema = QueryArgs

    def __init__(self, connection_string: str, max_rows: int = 100):
        self.connection_string = connection_string
        self.max_rows = max_rows
        self._pool = None

    async def _get_pool(self):
        if self._pool is None:
            import asyncpg
            self._pool = await asyncpg.create_pool(self.connection_string)
        return self._pool

    async def execute(
        self,
        query: str,
        params: Optional[List[Any]] = None
    ) -> Dict[str, Any]:
        try:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                if query.strip().upper().startswith("SELECT"):
                    rows = await conn.fetch(query, *(params or []))
                    return {
                        "rows": [dict(r) for r in rows[:self.max_rows]],
                        "count": len(rows),
                        "truncated": len(rows) > self.max_rows
                    }
                else:
                    result = await conn.execute(query, *(params or []))
                    return {"result": result}
        except Exception as e:
            return {"error": str(e)}
```

### YAML Configuration

```yaml
resources:
  tools:
    - name: db
      type: DatabaseTool
      config:
        connection_string: ${DATABASE_URL}
        max_rows: 50
```

---

## File System Tool

A tool for safe file operations.

### Tool Implementation

```python
# tools/filesystem_tool.py
from pydantic import BaseModel, Field
from agent_framework.core.types import Tool
from pathlib import Path
from typing import Optional
import os


class FileOperationArgs(BaseModel):
    operation: str = Field(description="Operation: read, write, list, exists")
    path: str = Field(description="File or directory path")
    content: Optional[str] = Field(default=None, description="Content for write")


class FileSystemTool(Tool):
    """Tool for file system operations with sandboxing."""

    name = "filesystem"
    description = "Performs safe file operations within allowed directories"
    args_schema = FileOperationArgs

    def __init__(self, allowed_paths: list, max_file_size: int = 1024 * 1024):
        self.allowed_paths = [Path(p).resolve() for p in allowed_paths]
        self.max_file_size = max_file_size

    def _is_path_allowed(self, path: Path) -> bool:
        resolved = path.resolve()
        return any(
            str(resolved).startswith(str(allowed))
            for allowed in self.allowed_paths
        )

    async def execute(
        self,
        operation: str,
        path: str,
        content: Optional[str] = None
    ) -> dict:
        file_path = Path(path)

        if not self._is_path_allowed(file_path):
            return {"error": f"Path not allowed: {path}"}

        try:
            if operation == "read":
                if not file_path.exists():
                    return {"error": f"File not found: {path}"}
                content = file_path.read_text()
                return {"content": content, "size": len(content)}

            elif operation == "write":
                if content is None:
                    return {"error": "Content required for write operation"}
                if len(content) > self.max_file_size:
                    return {"error": f"Content exceeds max size: {self.max_file_size}"}
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(content)
                return {"written": True, "path": str(file_path)}

            elif operation == "list":
                if not file_path.is_dir():
                    return {"error": f"Not a directory: {path}"}
                entries = list(file_path.iterdir())
                return {
                    "entries": [
                        {"name": e.name, "is_dir": e.is_dir()}
                        for e in entries
                    ]
                }

            elif operation == "exists":
                return {
                    "exists": file_path.exists(),
                    "is_file": file_path.is_file() if file_path.exists() else False,
                    "is_dir": file_path.is_dir() if file_path.exists() else False
                }

            else:
                return {"error": f"Unknown operation: {operation}"}

        except Exception as e:
            return {"error": str(e)}
```

### YAML Configuration

```yaml
resources:
  tools:
    - name: files
      type: FileSystemTool
      config:
        allowed_paths:
          - /tmp/agent_workspace
          - ${HOME}/agent_data
        max_file_size: 1048576  # 1MB
```

---

## External Service Tool

A tool that integrates with external services.

### Tool Implementation

```python
# tools/slack_tool.py
from pydantic import BaseModel, Field
from agent_framework.core.types import Tool
import aiohttp


class SlackMessageArgs(BaseModel):
    channel: str = Field(description="Slack channel ID or name")
    message: str = Field(description="Message to send")
    thread_ts: str = Field(default=None, description="Thread timestamp for replies")


class SlackTool(Tool):
    """Tool for sending Slack messages."""

    name = "slack"
    description = "Sends messages to Slack channels"
    args_schema = SlackMessageArgs

    def __init__(self, token: str, default_channel: str = None):
        self.token = token
        self.default_channel = default_channel

    async def execute(
        self,
        channel: str = None,
        message: str = "",
        thread_ts: str = None
    ) -> dict:
        channel = channel or self.default_channel
        if not channel:
            return {"error": "No channel specified"}

        payload = {
            "channel": channel,
            "text": message,
        }
        if thread_ts:
            payload["thread_ts"] = thread_ts

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://slack.com/api/chat.postMessage",
                    json=payload,
                    headers=headers
                ) as response:
                    data = await response.json()
                    if data.get("ok"):
                        return {
                            "success": True,
                            "ts": data.get("ts"),
                            "channel": data.get("channel")
                        }
                    else:
                        return {
                            "success": False,
                            "error": data.get("error")
                        }
        except Exception as e:
            return {"success": False, "error": str(e)}
```

### YAML Configuration

```yaml
resources:
  tools:
    - name: slack
      type: SlackTool
      config:
        token: ${SLACK_BOT_TOKEN}
        default_channel: "#general"
```

---

## Composite Tool

A tool that combines multiple operations.

### Tool Implementation

```python
# tools/research_tool.py
from pydantic import BaseModel, Field
from agent_framework.core.types import Tool
from typing import List, Dict, Any
import aiohttp
import asyncio


class ResearchArgs(BaseModel):
    topic: str = Field(description="Topic to research")
    sources: int = Field(default=3, description="Number of sources to check")


class ComprehensiveResearchTool(Tool):
    """Tool that searches multiple sources and aggregates results."""

    name = "research"
    description = "Searches multiple sources and provides aggregated research"
    args_schema = ResearchArgs

    def __init__(self, search_api_key: str):
        self.search_api_key = search_api_key

    async def _search_source(
        self,
        source: str,
        query: str,
        session: aiohttp.ClientSession
    ) -> Dict[str, Any]:
        # Simulated - replace with real API calls
        await asyncio.sleep(0.1)
        return {
            "source": source,
            "results": [f"Result about {query} from {source}"],
            "relevance": 0.85
        }

    async def execute(self, topic: str, sources: int = 3) -> dict:
        source_names = ["web", "academic", "news", "books", "patents"][:sources]

        async with aiohttp.ClientSession() as session:
            tasks = [
                self._search_source(source, topic, session)
                for source in source_names
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        successful = [r for r in results if isinstance(r, dict)]
        errors = [str(r) for r in results if isinstance(r, Exception)]

        return {
            "topic": topic,
            "sources_checked": len(source_names),
            "results": successful,
            "errors": errors if errors else None,
            "summary": f"Found information about '{topic}' from {len(successful)} sources"
        }
```

---

## Testing Custom Tools

### Unit Test

```python
import pytest
from tools.greeting_tool import GreetingTool


@pytest.mark.asyncio
async def test_greeting_tool_casual():
    tool = GreetingTool()
    result = await tool.execute(name="Alice", formal=False)

    assert "greeting" in result
    assert "Alice" in result["greeting"]
    assert result["style"] == "casual"


@pytest.mark.asyncio
async def test_greeting_tool_formal():
    tool = GreetingTool()
    result = await tool.execute(name="Dr. Smith", formal=True)

    assert "greeting" in result
    assert "Dr. Smith" in result["greeting"]
    assert result["style"] == "formal"
```

### Integration Test with Agent

```python
import pytest
from deployment.factory import create_agent_from_yaml


@pytest.mark.asyncio
async def test_agent_with_custom_tool():
    agent = create_agent_from_yaml("configs/agents/greeter.yaml")

    # Mock the gateway
    from unittest.mock import AsyncMock, MagicMock
    mock_gateway = MagicMock()
    mock_gateway.generate = AsyncMock(
        return_value='{"tool": "greeting", "name": "Alice", "formal": false}'
    )
    agent.planner.inference_gateway = mock_gateway

    result = await agent.run("Greet Alice casually")
    assert result is not None
```

---

## Best Practices

1. **Use Pydantic schemas** for input validation
2. **Return structured data** (dictionaries with consistent keys)
3. **Handle errors gracefully** - never raise exceptions, return error info
4. **Document parameters** with Field descriptions
5. **Make tools idempotent** when possible
6. **Add timeouts** for external calls
7. **Log important operations** for debugging
8. **Test thoroughly** with unit and integration tests
9. **Consider security** - validate inputs, sandbox file operations
10. **Keep tools focused** - one responsibility per tool
