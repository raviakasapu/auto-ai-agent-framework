# Pattern: Manager + Workers

A manager agent that routes tasks to specialized worker agents. This is the most common pattern for multi-domain assistants.

## When to Use

- Tasks spanning multiple domains (research + tasks + weather)
- When you want specialized workers with focused capabilities
- Multi-tenant systems with different skill sets
- Any system where routing improves accuracy

## Architecture

```
                    [User Request]
                          |
                          v
              +-------------------+
              |  ManagerAgent     |
              | (WorkerRouter)    |
              +-------------------+
                   /         \
                  v           v
     +----------------+   +----------------+
     | ResearchWorker |   |  TaskWorker    |
     | (ReActPlanner) |   | (ReActPlanner) |
     +----------------+   +----------------+
           |                    |
     [search, notes]      [tasks, weather]
```

## Complete YAML - Manager

Copy to `configs/agents/assistant_manager.yaml`:

```yaml
# =============================================================================
# MANAGER + WORKERS PATTERN - MANAGER
# =============================================================================
# Routes user requests to the appropriate specialized worker.
# =============================================================================

apiVersion: agent.framework/v2
kind: ManagerAgent

metadata:
  name: AssistantManager
  description: Routes requests to research or task management workers
  version: 1.0.0

resources:
  inference_gateways:
    - name: openai-router
      type: OpenAIGateway
      config:
        model: ${OPENAI_MODEL:-gpt-4o}
        api_key: ${OPENAI_API_KEY}
        temperature: 0.2

  subscribers:
    - name: logging
      type: PhoenixSubscriber
      config:
        level: INFO

spec:
  # ---------------------------------------------------------------------------
  # Policies - Manager preset handles follow-up phases
  # ---------------------------------------------------------------------------
  policies:
    $preset: manager_with_followups
    termination:
      type: DefaultTerminationPolicy
      config:
        max_iterations: 5
        on_max_iterations: error

  # ---------------------------------------------------------------------------
  # Planner - Routes to workers based on task analysis
  # ---------------------------------------------------------------------------
  planner:
    type: WorkerRouterPlanner
    config:
      inference_gateway: openai-router
      worker_keys: [research-worker, task-worker]
      default_worker: research-worker
      system_prompt: |
        You are a request router for a multi-agent assistant.

        AVAILABLE WORKERS:
        - research-worker: Web search, note-taking, calculations, research tasks
        - task-worker: Create tasks, list tasks, complete tasks, weather lookups

        ROUTING RULES:
        - "search for...", "find information about...", "research..." -> research-worker
        - "calculate...", "what is X * Y" -> research-worker
        - "create a task...", "add to my todo..." -> task-worker
        - "list my tasks", "show todos" -> task-worker
        - "what's the weather..." -> task-worker
        - Default to research-worker if unclear

        RESPONSE FORMAT:
        Return JSON only: {"worker": "<worker_key>", "reason": "brief explanation"}

        EXAMPLES:
        Input: "Search for Python tutorials"
        Output: {"worker": "research-worker", "reason": "Research/search request"}

        Input: "Create a task to buy groceries"
        Output: {"worker": "task-worker", "reason": "Task creation request"}

  # ---------------------------------------------------------------------------
  # Memory - Manager preset sees all subordinate messages
  # ---------------------------------------------------------------------------
  memory:
    $preset: manager

  # ---------------------------------------------------------------------------
  # Workers - Reference worker config files
  # ---------------------------------------------------------------------------
  workers:
    - name: research-worker
      config_path: configs/agents/research_worker.yaml

    - name: task-worker
      config_path: configs/agents/task_worker.yaml

  subscribers: [logging]
```

## Complete YAML - Research Worker

Copy to `configs/agents/research_worker.yaml`:

```yaml
# =============================================================================
# MANAGER + WORKERS PATTERN - RESEARCH WORKER
# =============================================================================

apiVersion: agent.framework/v2
kind: Agent

metadata:
  name: ResearchWorker
  description: Handles research, search, and calculation tasks
  version: 1.0.0

resources:
  inference_gateways:
    - name: openai-worker
      type: OpenAIGateway
      config:
        model: ${OPENAI_MODEL:-gpt-4o-mini}
        api_key: ${OPENAI_API_KEY}
        temperature: 0.1
        use_function_calling: true

  tools:
    - name: web_search
      type: MockSearchTool
      config: {}

    - name: note_taker
      type: NoteTakerTool
      config: {}

    - name: calculator
      type: CalculatorTool
      config: {}

spec:
  policies:
    $preset: simple
    termination:
      type: DefaultTerminationPolicy
      config:
        max_iterations: 10

  planner:
    type: ReActPlanner
    config:
      inference_gateway: openai-worker
      use_function_calling: true
      system_prompt: |
        You are a research assistant. Your capabilities:
        - web_search: Search for information
        - note_taker: Save important findings
        - calculator: Perform calculations

        Be thorough, cite sources, and summarize findings clearly.

  memory:
    $preset: worker

  tools: [web_search, note_taker, calculator]
```

## Complete YAML - Task Worker

Copy to `configs/agents/task_worker.yaml`:

```yaml
# =============================================================================
# MANAGER + WORKERS PATTERN - TASK WORKER
# =============================================================================

apiVersion: agent.framework/v2
kind: Agent

metadata:
  name: TaskWorker
  description: Handles task management and weather lookups
  version: 1.0.0

resources:
  inference_gateways:
    - name: openai-worker
      type: OpenAIGateway
      config:
        model: ${OPENAI_MODEL:-gpt-4o-mini}
        api_key: ${OPENAI_API_KEY}
        temperature: 0.1
        use_function_calling: true

  tools:
    - name: create_task
      type: TaskManagerTool
      config: {}

    - name: list_tasks
      type: ListTasksTool
      config: {}

    - name: complete_task
      type: CompleteTaskTool
      config: {}

    - name: weather_lookup
      type: WeatherLookupTool
      config: {}

spec:
  policies:
    $preset: simple
    termination:
      type: DefaultTerminationPolicy
      config:
        max_iterations: 10

  planner:
    type: ReActPlanner
    config:
      inference_gateway: openai-worker
      use_function_calling: true
      system_prompt: |
        You are a task management assistant. Your capabilities:
        - create_task: Create new tasks with title and description
        - list_tasks: List existing tasks
        - complete_task: Mark a task as complete
        - weather_lookup: Get weather for a location

        Be helpful and confirm actions taken.

  memory:
    $preset: worker

  tools: [create_task, list_tasks, complete_task, weather_lookup]
```

## Running the System

```python
import asyncio
from deployment.factory import AgentFactory

async def main():
    # Load the manager (workers are loaded automatically)
    manager = AgentFactory.create_from_yaml("configs/agents/assistant_manager.yaml")

    # Test routing to research worker
    result1 = await manager.run("Search for Python web frameworks")
    print("Research:", result1)

    # Test routing to task worker
    result2 = await manager.run("Create a task to review documentation")
    print("Task:", result2)

asyncio.run(main())
```

## Adding a Third Worker

To add a new worker (e.g., email):

1. Create `configs/agents/email_worker.yaml`
2. Update manager's `worker_keys`:
   ```yaml
   worker_keys: [research-worker, task-worker, email-worker]
   ```
3. Update manager's `system_prompt` with routing rules
4. Add worker reference:
   ```yaml
   workers:
     - name: email-worker
       config_path: configs/agents/email_worker.yaml
   ```

## Customization Tips

| What to Change | How |
|----------------|-----|
| Add worker | Add to `worker_keys`, update prompt, add to `workers` |
| Change default | Modify `default_worker` in planner config |
| Use larger model for routing | Change manager's gateway to `gpt-4o` |
| Share state | Ensure all workers use same `JOB_ID` namespace |

## Next Steps

- Share state between workers: See [Shared Memory Team](shared_memory_team.md)
- Add human approval: See [HITL Approval](hitl_approval.md)
- Add another management layer: See [Three-Tier Hierarchy](three_tier_hierarchy.md)
