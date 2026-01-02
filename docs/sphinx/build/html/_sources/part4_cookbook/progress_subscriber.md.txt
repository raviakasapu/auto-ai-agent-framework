# Recipe: Progress Subscriber

Create custom event subscribers for real-time updates.

## Goal

Create a subscriber that sends events to a custom destination.

## Custom EventSubscriber

```python
from agent_framework import BaseEventSubscriber
from typing import Dict, Any
import httpx

class WebhookSubscriber(BaseEventSubscriber):
    """Send events to a webhook endpoint."""
    
    def __init__(self, webhook_url: str, auth_token: str = None):
        self.webhook_url = webhook_url
        self.auth_token = auth_token
        self.client = httpx.Client()
    
    def handle_event(self, event_name: str, data: Dict[str, Any]) -> None:
        headers = {"Content-Type": "application/json"}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        
        try:
            self.client.post(
                self.webhook_url,
                json={
                    "event": event_name,
                    "data": data,
                },
                headers=headers,
                timeout=5.0,
            )
        except Exception as e:
            # Log but don't fail
            print(f"Webhook failed: {e}")
```

## Custom ProgressHandler (Async)

```python
from agent_framework import BaseProgressHandler
from typing import Dict, Any
import aiohttp

class AsyncWebhookHandler(BaseProgressHandler):
    """Async progress handler for streaming updates."""
    
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
        self.session = None
    
    async def on_event(self, event_name: str, data: Dict[str, Any]) -> None:
        if self.session is None:
            self.session = aiohttp.ClientSession()
        
        try:
            await self.session.post(
                self.webhook_url,
                json={"event": event_name, "data": data},
            )
        except Exception as e:
            print(f"Async webhook failed: {e}")
```

## Filtering Subscriber

```python
class FilteredSubscriber(BaseEventSubscriber):
    """Only forward specific events."""
    
    def __init__(self, inner: BaseEventSubscriber, allowed_events: set):
        self.inner = inner
        self.allowed_events = allowed_events
    
    def handle_event(self, event_name: str, data: Dict[str, Any]) -> None:
        if event_name in self.allowed_events:
            self.inner.handle_event(event_name, data)
```

## Usage

```python
from agent_framework import EventBus

# Create event bus
event_bus = EventBus()

# Subscribe your handlers
webhook = WebhookSubscriber(
    webhook_url="https://your-webhook.example/events",
    auth_token="secret",
)
event_bus.subscribe(webhook)

# Use filtered subscriber
filtered = FilteredSubscriber(
    inner=webhook,
    allowed_events={"agent_start", "agent_end", "error"},
)
event_bus.subscribe(filtered)

# Pass event bus to agent
agent = Agent(
    ...,
    event_bus=event_bus,
)
```

## With Progress Handler

```python
from fastapi import WebSocket

async def run_with_progress(ws: WebSocket, task: str):
    handler = AsyncWebhookHandler("https://your-webhook.example")
    
    result = await agent.run(
        task,
        progress_handler=handler,
    )
    
    return result
```

## Key Points

- `BaseEventSubscriber.handle_event()` is synchronous
- `BaseProgressHandler.on_event()` is async
- Always handle exceptions (don't break agent execution)
- Use filtering to reduce noise
- Close resources properly

