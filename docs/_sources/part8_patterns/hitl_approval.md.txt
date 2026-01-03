# Pattern: Human-in-the-Loop Approval

Agents that require human approval before executing write/destructive operations.

## When to Use

- Production systems with data modification
- High-stakes operations (delete, update, send)
- Compliance requirements
- Building trust with new agent deployments
- Any operation that cannot be easily undone

## Architecture

```
[User Request]
      |
      v
  [Agent]
      |
      v
[Plan: delete_record]
      |
      v
+------------------+
| HITL Policy      |
| Is write tool?   |-----> YES -----> [Pause & Request Approval]
+------------------+                           |
      |                                        v
      NO                              [Human Reviews]
      |                                   /        \
      v                              APPROVE     DENY
[Execute Immediately]                   |          |
                                        v          v
                                   [Execute]   [Abort]
```

## Complete YAML - Agent with HITL

Copy to `configs/agents/safe_data_agent.yaml`:

```yaml
# =============================================================================
# HITL APPROVAL PATTERN
# =============================================================================
# Agent that requires human approval for write operations.
# Read operations execute immediately; writes pause for approval.
# =============================================================================

apiVersion: agent.framework/v2
kind: Agent

metadata:
  name: SafeDataAgent
  description: Data agent with human approval for modifications
  version: 1.0.0

resources:
  inference_gateways:
    - name: openai
      type: OpenAIGateway
      config:
        model: ${OPENAI_MODEL:-gpt-4o-mini}
        api_key: ${OPENAI_API_KEY}
        use_function_calling: true

  # ---------------------------------------------------------------------------
  # Tools - Mix of read (safe) and write (needs approval)
  # ---------------------------------------------------------------------------
  tools:
    # READ OPERATIONS - Execute immediately
    - name: list_records
      type: ListRecordsTool
      config: {}

    - name: get_record
      type: GetRecordTool
      config: {}

    - name: search_records
      type: SearchRecordsTool
      config: {}

    # WRITE OPERATIONS - Require approval
    - name: create_record
      type: CreateRecordTool
      config: {}

    - name: update_record
      type: UpdateRecordTool
      config: {}

    - name: delete_record
      type: DeleteRecordTool
      config: {}

  subscribers:
    - name: logging
      type: PhoenixSubscriber
      config:
        level: INFO

spec:
  # ---------------------------------------------------------------------------
  # Policies - Enable HITL for write operations
  # ---------------------------------------------------------------------------
  policies:
    $preset: with_hitl
    # The with_hitl preset includes:
    # - hitl.enabled: true
    # - hitl.scope: "writes"

    # Override HITL configuration if needed:
    hitl:
      type: DefaultHITLPolicy
      config:
        enabled: true
        scope: writes
        # Specify which tools require approval
        write_tools:
          - create_record
          - update_record
          - delete_record

    termination:
      type: DefaultTerminationPolicy
      config:
        max_iterations: 10

  planner:
    type: ReActPlanner
    config:
      inference_gateway: openai
      use_function_calling: true
      system_prompt: |
        You are a data management assistant.

        READ OPERATIONS (immediate):
        - list_records: List all records
        - get_record: Get a specific record by ID
        - search_records: Search records by criteria

        WRITE OPERATIONS (require approval):
        - create_record: Create a new record
        - update_record: Update an existing record
        - delete_record: Delete a record

        Always confirm the user's intent before suggesting write operations.
        Provide clear explanations of what changes will be made.

  memory:
    $preset: standalone

  tools:
    - list_records
    - get_record
    - search_records
    - create_record
    - update_record
    - delete_record

  subscribers: [logging]
```

## Handling Approvals in Code

```python
import asyncio
from agent_framework import Agent, BaseProgressHandler, get_preset
from deployment.factory import AgentFactory

class ApprovalHandler(BaseProgressHandler):
    """Handle HITL approval requests."""

    async def on_event(self, event_name: str, data: dict) -> None:
        if event_name == "policy_denied":
            # HITL policy paused execution
            tool_name = data.get("tool_name")
            tool_args = data.get("tool_args")
            reason = data.get("reason")

            print(f"\n{'='*50}")
            print(f"APPROVAL REQUIRED")
            print(f"{'='*50}")
            print(f"Tool: {tool_name}")
            print(f"Arguments: {tool_args}")
            print(f"Reason: {reason}")
            print(f"{'='*50}")

            # In a real app, this would be async user input
            # or a webhook to a Slack/Teams approval flow
            approval = input("Approve? (yes/no): ").strip().lower()

            if approval == "yes":
                # Signal approval (implementation depends on your setup)
                data["approved"] = True
            else:
                data["approved"] = False
                print("Operation denied by human.")

async def main():
    agent = AgentFactory.create_from_yaml("configs/agents/safe_data_agent.yaml")

    handler = ApprovalHandler()

    result = await agent.run(
        "Delete record ID 12345",
        progress_handler=handler
    )

    print(result)

asyncio.run(main())
```

## WebSocket Approval Flow

For web applications:

```python
from fastapi import FastAPI, WebSocket
from agent_framework import BaseProgressHandler

app = FastAPI()

class WebSocketApprovalHandler(BaseProgressHandler):
    def __init__(self, websocket: WebSocket):
        self.ws = websocket
        self.pending_approval = None

    async def on_event(self, event_name: str, data: dict) -> None:
        if event_name == "policy_denied":
            # Send approval request to frontend
            await self.ws.send_json({
                "type": "approval_required",
                "tool": data.get("tool_name"),
                "args": data.get("tool_args"),
                "reason": data.get("reason"),
            })

            # Wait for response
            response = await self.ws.receive_json()
            data["approved"] = response.get("approved", False)

        elif event_name in ["agent_start", "agent_end", "action_executed"]:
            # Forward progress events to frontend
            await self.ws.send_json({
                "type": "progress",
                "event": event_name,
                "data": data
            })

@app.websocket("/agent")
async def agent_websocket(websocket: WebSocket):
    await websocket.accept()

    agent = AgentFactory.create_from_yaml("configs/agents/safe_data_agent.yaml")
    handler = WebSocketApprovalHandler(websocket)

    # Receive task from frontend
    message = await websocket.receive_json()
    task = message.get("task")

    # Run with approval handler
    result = await agent.run(task, progress_handler=handler)

    await websocket.send_json({
        "type": "complete",
        "result": result
    })
```

## HITL Scope Options

```yaml
hitl:
  type: DefaultHITLPolicy
  config:
    enabled: true
    scope: writes      # Only write tools
    # scope: all       # ALL tool calls require approval
    # scope: none      # Disabled (same as enabled: false)

    # Explicit tool list (overrides scope)
    write_tools:
      - delete_record
      - update_record
      - send_email
      - execute_query
```

## Environment Variables

```bash
# Global HITL toggle
REACT_HITL_ENABLE=true

# Global scope
REACT_HITL_SCOPE=writes  # or "all" or "none"
```

## Custom HITL Policy

```python
from agent_framework.policies.base import HITLPolicy
from typing import Tuple, Optional, Any, Dict

class CustomHITLPolicy(HITLPolicy):
    """Custom approval logic based on business rules."""

    def __init__(self, high_risk_threshold: float = 1000.0):
        self.threshold = high_risk_threshold

    def requires_approval(
        self,
        action: Any,
        context: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        tool_name = action.tool_name
        tool_args = action.tool_args

        # Always approve reads
        if tool_name.startswith("get_") or tool_name.startswith("list_"):
            return False, None

        # Approve low-value transactions
        if tool_name == "transfer_funds":
            amount = tool_args.get("amount", 0)
            if amount < self.threshold:
                return False, None
            return True, f"Transfer of ${amount} exceeds ${self.threshold} threshold"

        # Require approval for all deletes
        if tool_name.startswith("delete_"):
            return True, "Delete operations require approval"

        return False, None

# Register for YAML use
from deployment.registry import register_policy
register_policy("CustomHITLPolicy", CustomHITLPolicy)
```

## Customization Tips

| What to Change | How |
|----------------|-----|
| Add more write tools | Add to `write_tools` list |
| Approve all calls | Set `scope: all` |
| Disable HITL | Set `enabled: false` or use `$preset: simple` |
| Custom logic | Implement `HITLPolicy` subclass |
| Async approval | Use progress handler with async wait |

## Best Practices

1. **Start strict** - Enable HITL for all writes initially
2. **Log approvals** - Track who approved what and when
3. **Timeout approvals** - Don't let pending approvals block forever
4. **Provide context** - Show tool args clearly in approval UI
5. **Allow bulk approve** - For repetitive safe operations

## Next Steps

- Add hierarchy: See [Three-Tier Hierarchy](three_tier_hierarchy.md)
- Share state: See [Shared Memory Team](shared_memory_team.md)
