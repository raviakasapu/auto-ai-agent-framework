# Async Safety with Context Variables

The framework uses `contextvars` for async-safe request-scoped data storage, ensuring proper isolation for concurrent async requests.

## Why Context Variables?

### The Problem with `threading.local()`

In async Python (FastAPI, asyncio), `threading.local()` doesn't work correctly:

```python
# BROKEN with asyncio:
_thread_locals = threading.local()

async def handle_request_A():
    _thread_locals.job_id = "job_A"  # Set in thread-local
    await agent.run()  # Suspends, yields control

async def handle_request_B():
    _thread_locals.job_id = "job_B"  # OVERWRITES job_A!
    await agent.run()  # Both requests see "job_B" ❌
```

**Why it fails:**
- FastAPI runs multiple async requests in the **same thread** (event loop)
- `threading.local()` is per-thread, **not** per-async-task
- When one task suspends (await), another task can overwrite the same thread-local data

### The Solution: `contextvars`

The framework uses `contextvars.ContextVar` for async-safe isolation:

```python
# FIXED with contextvars:
_current_job_id = contextvars.ContextVar('_current_job_id', default=None)

async def handle_request_A():
    _current_job_id.set("job_A")  # Isolated to this async context
    await agent.run()  # Still sees "job_A" ✅

async def handle_request_B():
    _current_job_id.set("job_B")  # Isolated to this async context
    await agent.run()  # Still sees "job_B" ✅
```

**Why it works:**
- `contextvars` maintains separate storage **per async context**
- Each async task gets its own isolated copy
- Context is automatically propagated through `await` boundaries

## Framework Implementation

### Request Context Service

The framework provides `request_context.py` for async-safe request-scoped data:

```python
from agent_framework.services.request_context import (
    set_request_context,
    get_from_context,
    update_request_context,
    clear_request_context
)

# Set at request start
set_request_context({
    "job_id": "req_12345",
    "JOB_ID": "req_12345",  # For YAML expansion
    "user_id": "user_789"
})

# Access from anywhere
job_id = get_from_context("job_id")
plan = get_from_context("strategic_plan")

# Update during execution
update_request_context(strategic_plan=plan)

# Clear at request end
clear_request_context()
```

### Implementation Details

The framework uses `contextvars.ContextVar` internally:

```python
# agent_framework/services/request_context.py
_request_context: contextvars.ContextVar[Dict[str, Any]] = contextvars.ContextVar(
    '_request_context',
    default={}
)

def set_request_context(context: Dict[str, Any]) -> None:
    """Set the context for the current request (async-safe)."""
    _request_context.set(dict(context))

def get_from_context(key: str, default: Optional[Any] = None) -> Any:
    """Get a specific value from the current request context (async-safe)."""
    return _request_context.get().get(key, default)
```

## Context Propagation

### Through Async Boundaries

Context variables are automatically propagated through `await` boundaries:

```python
async def process_request():
    set_request_context({"job_id": "req_123"})
    
    # Context propagates through await
    result = await agent.run(task)  # Can access job_id ✅
    await save_result(result)  # Can still access job_id ✅

async def save_result(result):
    job_id = get_from_context("job_id")  # ✅ Available
    # Save to database...
```

### To Thread Pool Executors

When using `ThreadPoolExecutor` for synchronous tool execution, context must be explicitly propagated:

```python
import contextvars

# Copy context before executor
ctx = contextvars.copy_context()

# Run in executor with context
result = await loop.run_in_executor(None, ctx.run, tool.execute, **args)
```

The framework handles this automatically in `Agent._execute_actions()`.

## Best Practices

### 1. Always Use `contextvars` in Async Code

```python
# ❌ DON'T use threading.local() in async code
_thread_locals = threading.local()

# ✅ DO use contextvars
_request_context = contextvars.ContextVar('_request_context', default={})
```

### 2. Set Context Early

Set request context before any async operations:

```python
# ✅ GOOD: Set context before agent operations
set_request_context({"job_id": job_id})
result = await agent.run(task)

# ❌ BAD: Set context after operations start
result = await agent.run(task)
set_request_context({"job_id": job_id})  # Too late!
```

### 3. Capture Variables in Async Loops

When iterating in async loops, capture loop variables:

```python
# ❌ BAD: Variable can change mid-execution
while True:
    job_id = await get_message()
    result = await process(job_id)  # job_id can change!

# ✅ GOOD: Capture in local scope
while True:
    job_id = await get_message()
    current_job_id = job_id  # Capture
    result = await process(current_job_id)  # Safe!
```

### 4. Keep Operations in Context Scope

Keep related operations within the same context scope:

```python
# ✅ GOOD: All operations in context
with datamodel_context(job_id):
    result = await agent.run(task)
    # Send response here ← job_id guaranteed correct

# ❌ BAD: Operations outside context
with datamodel_context(job_id):
    result = await agent.run(task)
# Send response here ← job_id might be wrong!
```

## YAML Variable Expansion

The framework's YAML expansion uses request context for dynamic values:

```yaml
memory:
  type: MessageStoreMemory
  namespace: ${JOB_ID}  # Expands from request context
```

**Resolution Order:**
1. **Request context** (contextvars) - for per-request vars like `JOB_ID`
2. **Environment variables** - for global config like `OPENAI_API_KEY`

This ensures each async request gets its own namespace without interference.

## Concurrent Request Isolation

With `contextvars`, concurrent requests are properly isolated:

```
Time 0: Request A (job_id: req_123) starts
Time 1: Request A sets context → "req_123"
Time 2: Request B (job_id: req_456) starts
Time 3: Request B sets context → "req_456"
Time 4: Request A tool executes → uses "req_123" ✅
Time 5: Request B tool executes → uses "req_456" ✅
Time 6: Request A completes → logs to "req_123" ✅
Time 7: Request B completes → logs to "req_456" ✅
```

Each request maintains its own isolated context throughout execution.

## Common Pitfalls

### ❌ Using `threading.local()` in Async Code

```python
# This will cause cross-contamination in async environments
_thread_locals = threading.local()
_thread_locals.job_id = "req_123"  # ❌ Not async-safe
```

### ❌ Setting Context After Operations Start

```python
# Context set too late
result = await agent.run(task)
set_request_context({"job_id": job_id})  # ❌ Agent already ran
```

### ❌ Not Propagating Context to Executors

```python
# Context lost in thread pool
result = await loop.run_in_executor(None, tool.execute, **args)  # ❌ No context
```

The framework handles executor context propagation automatically.

## Summary

The framework ensures async-safety by:

- ✅ Using `contextvars.ContextVar` for request-scoped data
- ✅ Automatically propagating context through `await` boundaries
- ✅ Explicitly propagating context to `ThreadPoolExecutor` threads
- ✅ Providing `request_context` service for easy access
- ✅ Supporting YAML variable expansion from request context

**Key Takeaway:** Always use `contextvars` (not `threading.local()`) for request-scoped data in async Python applications.

