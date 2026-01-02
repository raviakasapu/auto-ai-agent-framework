# Observability & Approvals

This chapter covers Phoenix tracing, WebSocket event streaming, and HITL approval flows.

## Phoenix Integration

### Subscriber Configuration

All agents include the Phoenix subscriber:

```yaml
resources:
  subscribers:
    - name: phoenix
      type: PhoenixSubscriber
      config:
        endpoint: ${PHOENIX_ENDPOINT:-http://localhost:6006/v1/traces}
        service_name: orchestrator
```

### Span Hierarchy

```
🎯 User Task (root_request)
└── manager:orchestrator
    ├── delegation:powerbi-analysis
    │   └── manager:pbi_analysis_manager
    │       ├── manager_step_start: List Tables
    │       ├── delegation:model-structure-analyzer
    │       │   └── agent:ModelStructureAnalyzer
    │       │       ├── action:list_tables
    │       │       │   └── tool.list_tables
    │       │       │       ├── tool.input.args_json: {}
    │       │       │       ├── tool.output.result_summary: Found 12 tables
    │       │       │       └── tool.latency_ms: 45
    │       │       └── llm.openai.chat_completions
    │       │           ├── gen_ai.request.model: gpt-4o-mini
    │       │           ├── gen_ai.usage.input_tokens: 1250
    │       │           ├── gen_ai.usage.output_tokens: 89
    │       │           └── gen_ai.cost.total_usd: 0.0023
    │       └── manager_step_end: List Tables
    └── synthesis
        └── llm.openai.chat_completions
```

### Captured Attributes

**LLM Spans:**
- `gen_ai.system`: `openai`
- `gen_ai.request.model`: `gpt-4o-mini`
- `gen_ai.usage.input_tokens`: `1250`
- `gen_ai.usage.output_tokens`: `89`
- `gen_ai.cost.total_usd`: `0.0023`
- `gen_ai.latency_ms`: `892`

**Tool Spans:**
- `tool.name`: `list_tables`
- `tool.input.args_json`: `{"table": "FactSales"}`
- `tool.output.result_summary`: `Found 12 tables`
- `tool.latency_ms`: `45`

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PHOENIX_ENDPOINT` | `http://localhost:6006/v1/traces` | Phoenix collector |
| `PHOENIX_MAX_ATTR_CHARS` | `4000` | Max attribute length |
| `PHOENIX_CAPTURE_LLM_BODIES` | `true` | Include prompts/responses |
| `PHOENIX_PRETTY_JSON` | `false` | Pretty-print JSON |

## WebSocket Event Streaming

### Default Allowed Events

```python
DEFAULT_FRONTEND_EVENTS = {
    "connected",
    "request_start",
    
    # Orchestrator events
    "orchestrator_start", "orchestrator_phase_start", 
    "orchestrator_phase_end", "orchestrator_end",
    
    # Manager events
    "manager_start", "manager_script_planned",
    "manager_step_start", "manager_step_end", "manager_end",
    
    # Delegation events
    "delegation_planned", "delegation_chosen", "delegation_executed",
    
    # Agent events
    "agent_start", "agent_end",
    
    # Tool events
    "worker_tool_call", "worker_tool_result",
    "action_planned", "action_executed",
    
    # Synthesis events
    "synthesis_start", "synthesis_end",
    
    # Error/policy events
    "policy_denied", "error",
}
```

### Event Filtering

```bash
# Allow all events
FRONTEND_EVENT_ALLOWLIST="*"

# Custom subset
FRONTEND_EVENT_ALLOWLIST="agent_start,agent_end,error,worker_tool_result"
```

### WebSocket Message Format

```json
{
  "event": "worker_tool_result",
  "data": {
    "agent_name": "ModelStructureAnalyzer",
    "tool_name": "list_tables",
    "result": {
      "tables": [...],
      "count": 12,
      "human_readable_summary": "Found 12 tables"
    },
    "actor": {
      "role": "agent",
      "name": "ModelStructureAnalyzer"
    }
  },
  "timestamp": 1705315245123
}
```

### Final Response Format

```json
{
  "event": "agent_end",
  "result": {
    "operation": "display_table",
    "payload": {
      "tables": [...]
    },
    "human_readable_summary": "Found 12 tables in the data model"
  },
  "level": "orchestrator",
  "is_final": true,
  "timestamp": 1705315246789
}
```

## Human-in-the-Loop (HITL)

### Configuration

```yaml
# In agent config
policies:
  hitl:
    type: DefaultHITLPolicy
    config:
      enabled: true
      scope: writes
      write_tools:
        - add_column
        - update_measure
        - add_relationship
```

### Approval Flow

```
1. Agent plans write action
   └── HITL policy checks: requires_approval?
   
2. If approval required:
   └── Save to FileJobStore as pending_action
   └── Return pending status to frontend
   
3. Frontend displays approval UI
   └── User approves or denies
   
4. POST /resume_job with approve=true/false
   └── If approved: Execute pending action
   └── If denied: Clear pending, mark paused
```

### FileJobStore

```python
from agent_framework.state.job_store import get_job_store

# Check pending action
job = get_job_store().get_job(job_id)
if job.pending_action:
    action = job.pending_action
    # action.worker, action.tool, action.args
```

### Pending Action Structure

```python
class PendingAction(BaseModel):
    worker: str           # Worker agent name
    tool: str             # Tool to execute
    args: Dict[str, Any]  # Tool arguments
    manager: Optional[str]  # Parent manager
    resume_token: Optional[str]  # For stateless resume
    created_at: datetime
```

### Resume Endpoints

**POST /resume_job** — Execute stored pending action:

```python
@app.post("/resume_job")
async def resume_job(req: ResumeJobRequest):
    job = get_job_store().get_job(req.job_id)
    
    if not req.approve:
        get_job_store().clear_pending_action(req.job_id, new_status="paused")
        return {"message": "Pending action rejected"}
    
    # Execute the pending action
    pa = job.pending_action
    agent = load_worker(pa.worker)
    agent.planner = SingleActionPlanner(tool_name=pa.tool, tool_args=pa.args)
    result = await agent.run(f"Execute {pa.tool}")
    
    get_job_store().clear_pending_action(req.job_id, new_status="running")
    return {"result": result}
```

**POST /resume** — Ad-hoc tool execution:

```python
@app.post("/resume")
async def resume_agent(req: ResumeRequest):
    # Bypass orchestrator, run specific tool
    agent = load_worker(req.worker)
    agent.planner = SingleActionPlanner(tool_name=req.tool, tool_args=req.args)
    result = await agent.run(f"Execute {req.tool}")
    return {"result": result}
```

### Approvals in Request

```python
# Pass approvals to bypass HITL for specific tools
RunRequest(
    task="Add a measure",
    job_id="123",
    approvals={"add_measure": True}
)
```

Approvals are stored in request context:

```python
if req.approvals:
    update_request_context(approvals=dict(req.approvals))
```

## Logging

### Subscriber Configuration

```yaml
subscribers:
  - name: logging
    type: LoggingSubscriber
    config:
      level: DEBUG
      include_data: true
      max_payload_chars: 10000
      event_levels:
        action_planned: INFO
        action_executed: INFO
        delegation_planned: INFO
        manager_start: INFO
        error: ERROR
```

### Log Output

```
INFO:agent_framework:📋 manager_start - Orchestrator
INFO:agent_framework:📋 delegation_planned - powerbi-analysis
DEBUG:agent_framework:📋 manager_script_planned - Script: [list_tables, complete_task]
INFO:agent_framework:📋 action_executed - list_tables → 12 tables
INFO:agent_framework:📋 agent_end - ModelStructureAnalyzer: Task completed
```

## Debugging

### Debug Endpoints

```python
@app.get("/debug/conversation/{job_id}")
async def debug_conversation(job_id: str):
    """View conversation history for a job."""
    return {
        "conversation_history": _shared_state_store.list_conversation(job_id),
        "agent_execution_traces": _shared_state_store.list_agent_msgs(job_id, "orchestrator"),
        "global_updates": _shared_state_store.list_global_updates(job_id),
    }

@app.get("/debug/namespaces")
async def debug_namespaces():
    """List all active job namespaces."""
    return {
        "conversation_namespaces": list(_shared_state_store._conversation_feeds.keys()),
        "agent_namespaces": list(_shared_state_store._agent_feeds.keys()),
    }
```

## Summary

The Power BI implementation provides:

- ✅ **Phoenix tracing**: Full span hierarchy with LLM/tool metrics
- ✅ **WebSocket streaming**: Filtered real-time events to frontend
- ✅ **HITL approvals**: Pending action storage and resume flows
- ✅ **Structured logging**: Configurable per-event levels
- ✅ **Debug endpoints**: Conversation and namespace inspection

