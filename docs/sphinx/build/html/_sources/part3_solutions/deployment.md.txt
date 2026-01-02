# Deployment & Runtime Operations

This chapter covers deploying agents to production.

## Server Deployment

### FastAPI WebSocket Server

```python
import asyncio
import uuid
from fastapi import FastAPI, WebSocket
from agent_framework import BaseProgressHandler
from agent_framework.services.request_context import set_request_context, clear_request_context
from deployment.factory import AgentFactory

app = FastAPI()

class WebSocketHandler(BaseProgressHandler):
    def __init__(self, ws: WebSocket):
        self.ws = ws
    
    async def on_event(self, event_name: str, data: dict) -> None:
        await self.ws.send_json({
            "event": event_name,
            "data": data,
        })

@app.websocket("/ws/agent")
async def agent_websocket(ws: WebSocket):
    await ws.accept()
    
    while True:
        data = await ws.receive_json()
        task = data.get("task")
        config_path = data.get("config", "configs/agents/default.yaml")
        
        # Set up request context
        job_id = str(uuid.uuid4())
        set_request_context({"job_id": job_id, "JOB_ID": job_id})
        
        try:
            agent = AgentFactory.create_from_yaml(config_path)
            handler = WebSocketHandler(ws)
            result = await agent.run(task, progress_handler=handler)
            
            await ws.send_json({
                "event": "complete",
                "data": {"result": result},
            })
        except Exception as e:
            await ws.send_json({
                "event": "error",
                "data": {"error": str(e)},
            })
        finally:
            clear_request_context()
```

### REST API

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class TaskRequest(BaseModel):
    task: str
    config: str = "configs/agents/default.yaml"

class TaskResponse(BaseModel):
    result: dict
    job_id: str

@app.post("/run", response_model=TaskResponse)
async def run_agent(request: TaskRequest):
    job_id = str(uuid.uuid4())
    set_request_context({"job_id": job_id, "JOB_ID": job_id})
    
    try:
        agent = AgentFactory.create_from_yaml(request.config)
        result = await agent.run(request.task)
        return TaskResponse(result=result, job_id=job_id)
    finally:
        clear_request_context()
```

## Environment Variables

### Required

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI API key |

### Optional - LLM

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_MODEL` | `gpt-4o` | Default model |
| `OPENAI_STRATEGIC_MODEL` | `gpt-4o` | Strategic planning model |
| `OPENAI_TEMPERATURE` | `0.7` | Temperature |
| `GOOGLE_API_KEY` | — | Google AI key |

### Optional - Observability

| Variable | Default | Description |
|----------|---------|-------------|
| `PHOENIX_ENDPOINT` | `http://localhost:6006/v1/traces` | Phoenix URL |
| `PHOENIX_MAX_ATTR_CHARS` | `4000` | Max attribute length |
| `PHOENIX_CAPTURE_LLM_BODIES` | `true` | Include prompts/responses |
| `LLM_PRICING_JSON` | — | Token pricing config |

### Optional - Behavior

| Variable | Default | Description |
|----------|---------|-------------|
| `AGENT_REACT_INCLUDE_HISTORY` | `true` | Include history in prompts |
| `AGENT_REACT_MAX_HISTORY_MESSAGES` | `20` | Max history messages |
| `REACT_HITL_ENABLE` | `false` | Enable HITL globally |
| `REACT_HITL_SCOPE` | `writes` | HITL scope |
| `FRONTEND_EVENT_ALLOWLIST` | — | Event filter |

### Optional - Storage

| Variable | Default | Description |
|----------|---------|-------------|
| `JOB_STORE_DIR` | `./jobs` | Job store directory |
| `MODEL_DIR` | — | Model files directory |

## Docker Deployment

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install framework
COPY agent-framework-pypi/ ./agent-framework-pypi/
RUN pip install -e ./agent-framework-pypi

# Copy application
COPY . .

# Expose port
EXPOSE 8000

# Run server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  agent-server:
    build: .
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - PHOENIX_ENDPOINT=http://phoenix:6006/v1/traces
    volumes:
      - ./configs:/app/configs
      - ./jobs:/app/jobs
    depends_on:
      - phoenix
  
  phoenix:
    image: arizephoenix/phoenix:latest
    ports:
      - "6006:6006"
```

## Manifest & Docs Server

Generate and serve agent documentation:

### Generate Manifest

```bash
python generate_manifest.py \
  --config configs/agents/my_agent.yaml \
  --output docs/agent_manifest.json
```

### Serve Docs

```python
# docs_server/main.py
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import os

app = FastAPI()

MANIFEST_PATH = os.getenv("AGENT_MANIFEST_PATH", "docs/agent_manifest.json")
DOCS_DIR = os.getenv("AGENT_DOCS_DIR", "docs/sphinx/build/html")

@app.get("/manifest")
async def get_manifest():
    with open(MANIFEST_PATH) as f:
        return json.load(f)

app.mount("/reference", StaticFiles(directory=DOCS_DIR, html=True))
```

```bash
AGENT_MANIFEST_PATH=docs/agent_manifest.json \
AGENT_DOCS_DIR=docs/sphinx/build/html \
uvicorn docs_server.main:app --port 8002
```

## Health Checks

```python
@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.get("/ready")
async def ready():
    # Check dependencies
    checks = {
        "openai": check_openai_connection(),
        "phoenix": check_phoenix_connection(),
    }
    healthy = all(checks.values())
    return {
        "status": "ready" if healthy else "not_ready",
        "checks": checks,
    }
```

## Logging

```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Framework logger
from agent_framework.logging import get_logger
logger = get_logger()
logger.info("Agent started")
```

## Scaling

### Horizontal Scaling

```yaml
# kubernetes deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agent-server
spec:
  replicas: 3
  template:
    spec:
      containers:
        - name: agent
          image: my-agent:latest
          resources:
            requests:
              memory: "512Mi"
              cpu: "500m"
            limits:
              memory: "1Gi"
              cpu: "1000m"
```

### Connection Pooling

```python
# Share resources across requests
_agent_cache = {}

def get_agent(config_path: str):
    if config_path not in _agent_cache:
        _agent_cache[config_path] = AgentFactory.create_from_yaml(config_path)
    return _agent_cache[config_path]
```

## Best Practices

1. **Use environment variables** for configuration
2. **Enable health checks** for container orchestration
3. **Configure observability** (Phoenix/Langfuse)
4. **Set resource limits** in containers
5. **Use connection pooling** for shared resources
6. **Log structured data** for debugging
7. **Clear request context** in finally blocks

