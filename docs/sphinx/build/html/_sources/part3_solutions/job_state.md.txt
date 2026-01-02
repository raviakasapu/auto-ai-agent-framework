# Scripts, Job State & Approvals

This chapter covers script plans, job persistence, and the approval lifecycle.

## ScriptPlan

Managers can create script plans for workers:

```python
from agent_framework.models.script import ScriptPlan

plan = ScriptPlan(
    goal="Analyze table structure",
    notes="Use schema reader tools",
    steps=[
        {"name": "list_tables", "tool": "list_tables", "args": {}},
        {"name": "get_columns", "tool": "list_columns", "args": {"table": "{{list_tables.result[0]}}"}},
    ],
)
```

### ScriptPlan Fields

| Field | Type | Description |
|-------|------|-------------|
| `goal` | string | What the script achieves |
| `notes` | string | Context for execution |
| `steps` | list | Ordered steps to execute |
| `thought` | string | Manager's reasoning |

## BaseJobStore

Abstract interface for job persistence:

```python
from agent_framework import BaseJobStore

class BaseJobStore(ABC):
    @abstractmethod
    def create_job(self, job_id: str) -> Any:
        """Create a new job entry."""
        pass
    
    @abstractmethod
    def update_orchestrator_plan(self, job_id: str, plan: dict) -> None:
        """Store orchestrator's strategic plan."""
        pass
    
    @abstractmethod
    def update_manager_plan(self, job_id: str, manager: str, plan: dict) -> None:
        """Store a manager's execution plan."""
        pass
    
    @abstractmethod
    def save_pending_action(
        self, job_id: str, *,
        worker: str, tool: str, args: dict,
        manager: str = None, resume_token: str = None
    ) -> None:
        """Save action awaiting approval."""
        pass
    
    @abstractmethod
    def clear_pending_action(self, job_id: str, *, new_status: str = None) -> None:
        """Clear pending action after approval/denial."""
        pass
```

## FileJobStore

Built-in file-based implementation:

```python
from agent_framework.state.job_store import FileJobStore

store = FileJobStore(base_dir="./job_data")

# Create job
store.create_job("job_123")

# Store plan
store.update_orchestrator_plan("job_123", {
    "phases": [
        {"name": "Analyze", "worker": "analyzer"},
    ]
})

# Check action execution
store.add_executed_action("job_123", "list_tables:{}")
if store.has_executed_action("job_123", "list_tables:{}"):
    print("Already executed")
```

### Job Structure

```python
class Job:
    id: str
    status: str  # "active", "completed", "paused"
    orchestrator_plan: Optional[dict]
    manager_plans: Dict[str, dict]
    pending_action: Optional[PendingAction]
    executed_actions: Set[str]
    approvals: Dict[str, bool]
    created_at: datetime
    updated_at: datetime
```

### PendingAction

```python
class PendingAction:
    worker: str
    tool: str
    args: Dict[str, Any]
    manager: Optional[str]
    resume_token: Optional[str]
    created_at: datetime
```

## Approval Lifecycle

### 1. Action Requires Approval

When HITL policy requires approval:

```python
# Agent checks HITL policy
needs_approval, reason = hitl_policy.requires_approval(action, context)

if needs_approval:
    # Save pending action
    job_store.save_pending_action(
        job_id,
        worker="schema_editor",
        tool="add_column",
        args={"table": "users", "column": "email"},
        resume_token=str(uuid.uuid4()),
    )
    
    # Return pending status
    return {"status": "pending_approval", "action": action}
```

### 2. User Approves/Denies

```python
# In your API endpoint
@app.post("/jobs/{job_id}/approve")
async def approve_action(job_id: str, approved: bool):
    if approved:
        # Clear pending and continue
        job_store.clear_pending_action(job_id, new_status="approved")
        # Resume execution...
    else:
        job_store.clear_pending_action(job_id, new_status="denied")
        return {"status": "denied"}
```

### 3. Resume Execution

```python
# Resume with the pending action
job = job_store.get_job(job_id)
if job.pending_action and job.status == "approved":
    action = Action(
        tool_name=job.pending_action.tool,
        tool_args=job.pending_action.args,
    )
    result = await agent.execute_action(action)
```

## Resume Tokens

Resume tokens enable stateless resumption:

```python
# Generate token when pausing
resume_token = str(uuid.uuid4())
job_store.save_pending_action(
    job_id,
    worker="editor",
    tool="update_column",
    args={...},
    resume_token=resume_token,
)

# Resume using token
@app.post("/resume/{resume_token}")
async def resume(resume_token: str):
    job = find_job_by_resume_token(resume_token)
    # Continue execution...
```

## Executed Actions Tracking

Prevent duplicate execution:

```python
# Create action signature
signature = f"{tool_name}:{json.dumps(args, sort_keys=True)}"

# Check before executing
if job_store.has_executed_action(job_id, signature):
    return {"status": "already_executed"}

# Execute and record
result = tool.execute(**args)
job_store.add_executed_action(job_id, signature)
```

## Custom Job Store

Implement for your storage backend:

```python
from agent_framework import BaseJobStore

class DatabaseJobStore(BaseJobStore):
    def __init__(self, db_connection):
        self.db = db_connection
    
    def create_job(self, job_id: str) -> Any:
        self.db.execute(
            "INSERT INTO jobs (id, status) VALUES (?, ?)",
            [job_id, "active"]
        )
        return {"id": job_id, "status": "active"}
    
    def update_orchestrator_plan(self, job_id: str, plan: dict) -> None:
        self.db.execute(
            "UPDATE jobs SET orchestrator_plan = ? WHERE id = ?",
            [json.dumps(plan), job_id]
        )
    
    # ... implement other methods
```

## Using Job Store with ManagerAgent

```python
from agent_framework import ManagerAgent

manager = ManagerAgent(
    planner=planner,
    memory=memory,
    workers=workers,
    job_store=FileJobStore("./jobs"),  # Pass job store
)

# Job state is automatically managed
result = await manager.run(task)
```

## Best Practices

1. **Use job stores** for production deployments
2. **Generate unique job IDs** per request
3. **Store execution signatures** to prevent duplicates
4. **Use resume tokens** for stateless APIs
5. **Clean up old jobs** periodically
6. **Log state transitions** for debugging

