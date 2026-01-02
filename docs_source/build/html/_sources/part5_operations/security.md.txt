# Security & Guardrails

This chapter covers security controls, access policies, and guardrails.

## Human-in-the-Loop (HITL)

### Configuration

```python
from agent_framework.policies.default import DefaultHITLPolicy

hitl = DefaultHITLPolicy(
    enabled=True,
    scope="writes",  # "all", "writes", "none"
    write_tools=["add_column", "delete_table", "update_measure"],
)

policies = get_preset("simple")
policies["hitl"] = hitl
```

### Environment Variables

```bash
REACT_HITL_ENABLE=true
REACT_HITL_SCOPE=writes
```

### Approval Flow

1. Agent plans action requiring approval
2. Action saved to job store as pending
3. User receives approval request
4. User approves/denies
5. Agent resumes or stops

```python
# Check pending actions
job = job_store.get_job(job_id)
if job.pending_action:
    # Present to user for approval
    action = job.pending_action
    print(f"Approve {action.tool}({action.args})?")
```

## Tool Access Policies

### Role-Based Access

```python
from agent_framework.policies.base import HITLPolicy

class RoleBasedPolicy(HITLPolicy):
    def __init__(self, role_permissions: dict):
        self.role_permissions = role_permissions
    
    def requires_approval(self, action, context):
        user_role = context.get("user_role", "viewer")
        tool_name = action.tool_name
        
        allowed_tools = self.role_permissions.get(user_role, [])
        
        if tool_name not in allowed_tools:
            return True, f"Role '{user_role}' cannot use '{tool_name}'"
        
        return False, None

# Configuration
policy = RoleBasedPolicy({
    "admin": ["*"],
    "editor": ["add_column", "update_column", "list_tables"],
    "viewer": ["list_tables", "get_column_details"],
})
```

### Separate Worker Configurations

For strict separation, create worker variants:

```yaml
# configs/agents/pbi/dax_analyzer.yaml (READ-ONLY)
name: dax_analyzer
resources:
  tools:
    - name: list_measures
    - name: get_measure_expression
    - name: validate_dax
spec:
  tools: [list_measures, get_measure_expression, validate_dax]

# configs/agents/pbi/dax_editor.yaml (READ+WRITE)
name: dax_editor
resources:
  tools:
    - name: list_measures
    - name: get_measure_expression
    - name: add_measure
    - name: update_measure
spec:
  tools: [list_measures, get_measure_expression, add_measure, update_measure]
```

## Input Validation

### Pydantic Schemas

```python
from pydantic import BaseModel, Field, validator

class SafeQueryArgs(BaseModel):
    query: str = Field(..., max_length=10000)
    timeout: int = Field(default=30, ge=1, le=300)
    
    @validator("query")
    def no_dangerous_keywords(cls, v):
        dangerous = ["DROP", "DELETE", "TRUNCATE", "ALTER"]
        for kw in dangerous:
            if kw in v.upper():
                raise ValueError(f"Query contains forbidden keyword: {kw}")
        return v
```

### Tool-Level Validation

```python
@tool(name="safe_query", args_schema=SafeQueryArgs)
def safe_query(query: str, timeout: int = 30) -> dict:
    # Query is already validated by Pydantic
    return execute_safe_query(query, timeout)
```

## Rate Limiting

```python
from collections import defaultdict
from datetime import datetime, timedelta

class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window = timedelta(seconds=window_seconds)
        self.requests = defaultdict(list)
    
    def is_allowed(self, key: str) -> bool:
        now = datetime.now()
        cutoff = now - self.window
        
        # Clean old requests
        self.requests[key] = [
            t for t in self.requests[key] if t > cutoff
        ]
        
        if len(self.requests[key]) >= self.max_requests:
            return False
        
        self.requests[key].append(now)
        return True

# Usage
limiter = RateLimiter(max_requests=100, window_seconds=60)

@app.post("/run")
async def run_agent(request: TaskRequest):
    user_id = request.user_id
    
    if not limiter.is_allowed(user_id):
        raise HTTPException(429, "Rate limit exceeded")
    
    # Process request...
```

## Secrets Management

### Environment Variables

```bash
# Use environment variables for secrets
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql://...
```

### Secret Injection

```yaml
# Reference environment variables in YAML
resources:
  gateways:
    - name: openai
      type: OpenAIGateway
      config:
        api_key: ${OPENAI_API_KEY}  # Expanded from environment
```

### Never Log Secrets

```python
import logging

class SecretFilter(logging.Filter):
    def filter(self, record):
        # Redact API keys
        if hasattr(record, "msg"):
            record.msg = self._redact(record.msg)
        return True
    
    def _redact(self, msg):
        import re
        # Redact OpenAI keys
        msg = re.sub(r"sk-[a-zA-Z0-9]{32,}", "sk-***REDACTED***", str(msg))
        return msg

logging.getLogger().addFilter(SecretFilter())
```

## Audit Logging

```python
class AuditSubscriber(BaseEventSubscriber):
    def __init__(self, audit_log_path: str):
        self.log_file = open(audit_log_path, "a")
    
    def handle_event(self, event_name: str, data: dict) -> None:
        if event_name in ("action_planned", "action_executed", "policy_denied"):
            audit_entry = {
                "timestamp": datetime.now().isoformat(),
                "event": event_name,
                "tool": data.get("tool_name"),
                "user": data.get("context", {}).get("user_id"),
                "result": "success" if event_name == "action_executed" else "pending",
            }
            self.log_file.write(json.dumps(audit_entry) + "\n")
            self.log_file.flush()
```

## Environment Variable Reference

| Variable | Purpose |
|----------|---------|
| `REACT_HITL_ENABLE` | Enable HITL globally |
| `REACT_HITL_SCOPE` | HITL scope (all/writes/none) |
| `JOB_STORE_DIR` | Job persistence directory |
| `FRONTEND_EVENT_ALLOWLIST` | Event filtering |

## Best Practices

1. **Enable HITL** for write operations in production
2. **Use role-based policies** for multi-tenant deployments
3. **Validate all inputs** with Pydantic schemas
4. **Never log secrets** — use redaction filters
5. **Implement rate limiting** to prevent abuse
6. **Audit all actions** for compliance
7. **Separate worker configs** for strict access control

