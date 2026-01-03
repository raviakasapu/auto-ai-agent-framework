# Pattern: Shared Memory Team

Workers that collaborate by sharing state through a common memory namespace. Each worker can see what others have done.

## When to Use

- Workers need to build on each other's work
- Pipeline processing (analyze -> transform -> validate)
- Collaborative research (gather -> synthesize -> report)
- Any workflow where context accumulates across agents

## Architecture

```
                    [Manager]
                   /    |    \
                  v     v     v
            [Worker A] [Worker B] [Worker C]
                  \     |     /
                   v    v    v
              +------------------+
              | Shared Memory    |
              | namespace: job_1 |
              +------------------+
              | Worker A traces  |
              | Worker B traces  |
              | Worker C traces  |
              | Global messages  |
              +------------------+
```

## Complete YAML - Manager with Shared Memory

Copy to `configs/agents/team_manager.yaml`:

```yaml
# =============================================================================
# SHARED MEMORY TEAM PATTERN - MANAGER
# =============================================================================
# Manager coordinates workers who share state via common namespace.
# Workers can see each other's work through shared memory.
# =============================================================================

apiVersion: agent.framework/v2
kind: ManagerAgent

metadata:
  name: TeamManager
  description: Coordinates a team of workers with shared memory
  version: 1.0.0

resources:
  inference_gateways:
    - name: openai-manager
      type: OpenAIGateway
      config:
        model: ${OPENAI_MODEL:-gpt-4o}
        api_key: ${OPENAI_API_KEY}

spec:
  policies:
    $preset: manager_with_followups

  planner:
    type: WorkerRouterPlanner
    config:
      inference_gateway: openai-manager
      worker_keys: [gatherer, analyzer, reporter]
      default_worker: gatherer
      system_prompt: |
        You coordinate a research team with shared memory.

        TEAM MEMBERS:
        - gatherer: Collects raw data and information
        - analyzer: Analyzes gathered data, finds patterns
        - reporter: Creates summaries and reports

        WORKFLOW:
        1. First, use gatherer to collect information
        2. Then, use analyzer to find patterns (can see gatherer's work)
        3. Finally, use reporter to summarize (can see all previous work)

        Return: {"worker": "<key>", "reason": "..."}

  # ---------------------------------------------------------------------------
  # Memory - Manager preset with subordinates visibility
  # The manager sees ALL worker traces in the shared namespace
  # ---------------------------------------------------------------------------
  memory:
    $preset: manager
    # subordinates auto-derived from workers list
    # namespace from JOB_ID ensures isolation between jobs

  workers:
    - name: gatherer
      config_path: configs/agents/gatherer_worker.yaml
    - name: analyzer
      config_path: configs/agents/analyzer_worker.yaml
    - name: reporter
      config_path: configs/agents/reporter_worker.yaml
```

## Complete YAML - Gatherer Worker

Copy to `configs/agents/gatherer_worker.yaml`:

```yaml
# =============================================================================
# SHARED MEMORY TEAM - GATHERER WORKER
# =============================================================================
# Collects information. Other workers can see gathered data.
# =============================================================================

apiVersion: agent.framework/v2
kind: Agent

metadata:
  name: GathererWorker
  description: Gathers raw data and information

resources:
  inference_gateways:
    - name: openai
      type: OpenAIGateway
      config:
        model: ${OPENAI_MODEL:-gpt-4o-mini}
        api_key: ${OPENAI_API_KEY}
        use_function_calling: true

  tools:
    - name: web_search
      type: MockSearchTool
      config: {}
    - name: note_taker
      type: NoteTakerTool
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
        You are a data gatherer. Your job is to:
        1. Search for relevant information
        2. Save key findings as notes

        Be thorough. Other team members will use your gathered data.

  # ---------------------------------------------------------------------------
  # Memory - Worker preset with shared namespace
  # All workers use $preset: worker to share the same namespace
  # The JOB_ID environment variable creates isolation between jobs
  # ---------------------------------------------------------------------------
  memory:
    $preset: worker
    # namespace: ${JOB_ID} - auto-derived
    # agent_key: GathererWorker - auto-derived from metadata.name

  tools: [web_search, note_taker]
```

## Complete YAML - Analyzer Worker

Copy to `configs/agents/analyzer_worker.yaml`:

```yaml
# =============================================================================
# SHARED MEMORY TEAM - ANALYZER WORKER
# =============================================================================
# Analyzes gathered data. Can see gatherer's work in shared memory.
# =============================================================================

apiVersion: agent.framework/v2
kind: Agent

metadata:
  name: AnalyzerWorker
  description: Analyzes gathered data and finds patterns

resources:
  inference_gateways:
    - name: openai
      type: OpenAIGateway
      config:
        model: ${OPENAI_MODEL:-gpt-4o-mini}
        api_key: ${OPENAI_API_KEY}
        use_function_calling: true

  tools:
    - name: calculator
      type: CalculatorTool
      config: {}
    - name: note_taker
      type: NoteTakerTool
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
        You are a data analyzer. Your job is to:
        1. Review the gathered information (available in context)
        2. Find patterns and insights
        3. Perform calculations if needed
        4. Save your analysis as notes

        Build on the gatherer's work. The reporter will use your analysis.

  memory:
    $preset: worker

  tools: [calculator, note_taker]
```

## Complete YAML - Reporter Worker

Copy to `configs/agents/reporter_worker.yaml`:

```yaml
# =============================================================================
# SHARED MEMORY TEAM - REPORTER WORKER
# =============================================================================
# Creates reports from team's work. Can see all previous work.
# =============================================================================

apiVersion: agent.framework/v2
kind: Agent

metadata:
  name: ReporterWorker
  description: Creates summaries and reports from team findings

resources:
  inference_gateways:
    - name: openai
      type: OpenAIGateway
      config:
        model: ${OPENAI_MODEL:-gpt-4o-mini}
        api_key: ${OPENAI_API_KEY}
        use_function_calling: true

  tools:
    - name: note_taker
      type: NoteTakerTool
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
        You are a report writer. Your job is to:
        1. Review all gathered data and analysis (available in context)
        2. Synthesize findings into a clear report
        3. Save the final report

        Create a comprehensive summary of the team's work.

  memory:
    $preset: worker

  tools: [note_taker]
```

## Running the Team

```python
import asyncio
import os
from deployment.factory import AgentFactory
from agent_framework.services.request_context import set_request_context

async def main():
    # Set job ID for memory namespace isolation
    job_id = "research_job_001"
    os.environ["JOB_ID"] = job_id
    set_request_context({"JOB_ID": job_id})

    # Load the team manager
    manager = AgentFactory.create_from_yaml("configs/agents/team_manager.yaml")

    # Run a multi-phase task
    result = await manager.run(
        "Research AI trends, analyze the data, and create a summary report"
    )

    print(result)

asyncio.run(main())
```

## How Memory Sharing Works

```python
# All workers share the same namespace
# Worker memory:
memory1 = SharedInMemoryMemory(namespace="job_001", agent_key="GathererWorker")
memory2 = SharedInMemoryMemory(namespace="job_001", agent_key="AnalyzerWorker")
memory3 = SharedInMemoryMemory(namespace="job_001", agent_key="ReporterWorker")

# Manager sees all subordinates:
manager_memory = HierarchicalSharedMemory(
    namespace="job_001",
    agent_key="TeamManager",
    subordinates=["GathererWorker", "AnalyzerWorker", "ReporterWorker"]
)

# When gatherer saves a note, analyzer can see it in history
# When analyzer creates analysis, reporter can see both gatherer and analyzer work
```

## Memory Visibility Matrix

| Agent | Sees Own | Sees Gatherer | Sees Analyzer | Sees Reporter |
|-------|----------|---------------|---------------|---------------|
| Gatherer | Yes | - | No | No |
| Analyzer | Yes | Yes (via shared) | - | No |
| Reporter | Yes | Yes (via shared) | Yes (via shared) | - |
| Manager | Yes | Yes | Yes | Yes |

## Customization Tips

| What to Change | How |
|----------------|-----|
| Isolate jobs | Set different `JOB_ID` for each request |
| Add global broadcast | Use `memory.add_global()` for team-wide messages |
| Limit history | Configure history filters in policies |
| Persist memory | Implement `BaseMessageStore` for database storage |

## Next Steps

- Add human approval: See [HITL Approval](hitl_approval.md)
- Add more hierarchy: See [Three-Tier Hierarchy](three_tier_hierarchy.md)
