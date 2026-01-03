# Pattern: Three-Tier Hierarchy

A complete orchestrator -> manager -> worker architecture for complex enterprise systems.

## When to Use

- Large-scale enterprise applications
- Multiple business domains with specialized teams
- Complex workflows requiring strategic planning
- Systems needing both high-level coordination and deep specialization

## Architecture

```
                           [User Request]
                                 |
                                 v
                    +------------------------+
                    |     ORCHESTRATOR       |
                    |   (StrategicPlanner)   |
                    |                        |
                    | Creates phases:        |
                    | 1. Analysis Phase      |
                    | 2. Processing Phase    |
                    | 3. Reporting Phase     |
                    +------------------------+
                         /              \
                        v                v
         +------------------+    +------------------+
         | ANALYSIS MANAGER |    | REPORTING MANAGER|
         | (Decomposer)     |    | (Decomposer)     |
         |                  |    |                  |
         | Creates steps:   |    | Creates steps:   |
         | 1. Gather data   |    | 1. Compile       |
         | 2. Validate      |    | 2. Format        |
         +------------------+    +------------------+
              /        \               /        \
             v          v             v          v
      +---------+  +---------+  +---------+  +---------+
      | Gatherer|  |Validator|  |Compiler |  |Formatter|
      | (ReAct) |  | (ReAct) |  | (ReAct) |  | (ReAct) |
      +---------+  +---------+  +---------+  +---------+
```

## File Structure

```
configs/agents/
├── orchestrator.yaml           # Top-level orchestrator
├── managers/
│   ├── analysis_manager.yaml   # Analysis domain manager
│   └── reporting_manager.yaml  # Reporting domain manager
└── workers/
    ├── gatherer.yaml           # Data gathering worker
    ├── validator.yaml          # Validation worker
    ├── compiler.yaml           # Report compilation worker
    └── formatter.yaml          # Report formatting worker
```

## Complete YAML - Orchestrator

Copy to `configs/agents/orchestrator.yaml`:

```yaml
# =============================================================================
# THREE-TIER HIERARCHY - ORCHESTRATOR (TOP LEVEL)
# =============================================================================
# Strategic planner that creates high-level phases.
# Delegates to domain managers who coordinate workers.
# =============================================================================

apiVersion: agent.framework/v2
kind: ManagerAgent

metadata:
  name: EnterpriseOrchestrator
  description: Top-level orchestrator for complex enterprise workflows
  version: 1.0.0

resources:
  inference_gateways:
    - name: openai-strategic
      type: OpenAIGateway
      config:
        model: ${OPENAI_STRATEGIC_MODEL:-gpt-4o}
        api_key: ${OPENAI_API_KEY}
        temperature: 0.3

  subscribers:
    - name: phoenix
      type: PhoenixSubscriber
      config:
        level: INFO
        include_data: true

spec:
  policies:
    $preset: manager_with_followups
    termination:
      type: DefaultTerminationPolicy
      config:
        max_iterations: 10
        on_max_iterations: error

  # ---------------------------------------------------------------------------
  # Planner - Strategic planner for high-level phases
  # ---------------------------------------------------------------------------
  planner:
    type: StrategicPlanner
    config:
      inference_gateway: openai-strategic
      manager_keys: [analysis-manager, reporting-manager]
      planning_prompt: |
        You are a strategic orchestrator for an enterprise system.

        AVAILABLE MANAGERS:
        - analysis-manager: Data gathering, validation, analysis tasks
        - reporting-manager: Report compilation, formatting, delivery

        PLANNING APPROACH:
        1. Analyze the user's request
        2. Create a strategic plan with phases
        3. Each phase delegates to the appropriate manager
        4. Synthesize results across phases

        OUTPUT FORMAT:
        {
          "phases": [
            {
              "name": "Phase Name",
              "manager": "manager-key",
              "goals": "What this phase should accomplish",
              "inputs": "What the manager needs to know"
            }
          ],
          "success_criteria": "How to know the task is complete"
        }

        EXAMPLE:
        User: "Analyze Q4 sales data and create a summary report"
        Plan:
        {
          "phases": [
            {
              "name": "Data Analysis",
              "manager": "analysis-manager",
              "goals": "Gather and validate Q4 sales data, identify trends",
              "inputs": "Focus on Q4, include regional breakdowns"
            },
            {
              "name": "Report Generation",
              "manager": "reporting-manager",
              "goals": "Create executive summary with visualizations",
              "inputs": "Use analysis results, format for executives"
            }
          ],
          "success_criteria": "Complete analysis and formatted report delivered"
        }

  memory:
    $preset: manager

  workers:
    - name: analysis-manager
      config_path: configs/agents/managers/analysis_manager.yaml
    - name: reporting-manager
      config_path: configs/agents/managers/reporting_manager.yaml

  subscribers: [phoenix]
```

## Complete YAML - Analysis Manager

Copy to `configs/agents/managers/analysis_manager.yaml`:

```yaml
# =============================================================================
# THREE-TIER HIERARCHY - ANALYSIS MANAGER (MIDDLE TIER)
# =============================================================================
# Decomposes analysis phases into executable steps for workers.
# =============================================================================

apiVersion: agent.framework/v2
kind: ManagerAgent

metadata:
  name: AnalysisManager
  description: Manages data gathering and analysis workers
  version: 1.0.0

resources:
  inference_gateways:
    - name: openai-manager
      type: OpenAIGateway
      config:
        model: ${OPENAI_MODEL:-gpt-4o-mini}
        api_key: ${OPENAI_API_KEY}
        temperature: 0.2

spec:
  policies:
    $preset: manager_with_followups
    termination:
      type: DefaultTerminationPolicy
      config:
        max_iterations: 8

  # ---------------------------------------------------------------------------
  # Planner - Decomposes phases into steps
  # ---------------------------------------------------------------------------
  planner:
    type: StrategicDecomposerPlanner
    config:
      inference_gateway: openai-manager
      worker_keys: [gatherer, validator]
      manager_worker_key: analysis-manager
      decomposition_prompt: |
        You manage a data analysis team.

        WORKERS:
        - gatherer: Collects raw data from sources
        - validator: Validates data quality and accuracy

        DECOMPOSITION:
        Break the phase goals into sequential steps.
        Each step should be assigned to one worker.

        OUTPUT FORMAT:
        {
          "steps": [
            {
              "name": "Step Name",
              "worker": "worker-key",
              "instruction": "Specific task for the worker",
              "depends_on": []
            }
          ]
        }

  memory:
    $preset: manager

  workers:
    - name: gatherer
      config_path: configs/agents/workers/gatherer.yaml
    - name: validator
      config_path: configs/agents/workers/validator.yaml
```

## Complete YAML - Reporting Manager

Copy to `configs/agents/managers/reporting_manager.yaml`:

```yaml
# =============================================================================
# THREE-TIER HIERARCHY - REPORTING MANAGER (MIDDLE TIER)
# =============================================================================

apiVersion: agent.framework/v2
kind: ManagerAgent

metadata:
  name: ReportingManager
  description: Manages report compilation and formatting workers
  version: 1.0.0

resources:
  inference_gateways:
    - name: openai-manager
      type: OpenAIGateway
      config:
        model: ${OPENAI_MODEL:-gpt-4o-mini}
        api_key: ${OPENAI_API_KEY}
        temperature: 0.2

spec:
  policies:
    $preset: manager_with_followups
    termination:
      type: DefaultTerminationPolicy
      config:
        max_iterations: 8

  planner:
    type: StrategicDecomposerPlanner
    config:
      inference_gateway: openai-manager
      worker_keys: [compiler, formatter]
      manager_worker_key: reporting-manager
      decomposition_prompt: |
        You manage a reporting team.

        WORKERS:
        - compiler: Compiles data into report structure
        - formatter: Formats reports for presentation

        Break the phase goals into steps for your workers.

  memory:
    $preset: manager

  workers:
    - name: compiler
      config_path: configs/agents/workers/compiler.yaml
    - name: formatter
      config_path: configs/agents/workers/formatter.yaml
```

## Complete YAML - Worker Examples

### Gatherer Worker

Copy to `configs/agents/workers/gatherer.yaml`:

```yaml
# =============================================================================
# THREE-TIER HIERARCHY - GATHERER WORKER
# =============================================================================

apiVersion: agent.framework/v2
kind: Agent

metadata:
  name: GathererWorker
  description: Gathers data from various sources

resources:
  inference_gateways:
    - name: openai
      type: OpenAIGateway
      config:
        model: ${OPENAI_MODEL:-gpt-4o-mini}
        api_key: ${OPENAI_API_KEY}
        use_function_calling: true

  tools:
    - name: query_database
      type: DatabaseQueryTool
      config: {}
    - name: fetch_api
      type: APIFetchTool
      config: {}
    - name: read_file
      type: FileReadTool
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
      inference_gateway: openai
      use_function_calling: true
      system_prompt: |
        You are a data gatherer. Use your tools to collect requested data.
        - query_database: Run SQL queries
        - fetch_api: Call external APIs
        - read_file: Read local files

        Be thorough and report all data found.

  memory:
    $preset: worker

  tools: [query_database, fetch_api, read_file]
```

### Validator Worker

Copy to `configs/agents/workers/validator.yaml`:

```yaml
apiVersion: agent.framework/v2
kind: Agent

metadata:
  name: ValidatorWorker
  description: Validates data quality

resources:
  inference_gateways:
    - name: openai
      type: OpenAIGateway
      config:
        model: ${OPENAI_MODEL:-gpt-4o-mini}
        api_key: ${OPENAI_API_KEY}
        use_function_calling: true

  tools:
    - name: check_schema
      type: SchemaValidatorTool
      config: {}
    - name: check_nulls
      type: NullCheckerTool
      config: {}
    - name: validate_ranges
      type: RangeValidatorTool
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
        You are a data validator. Check data quality:
        - check_schema: Validate against expected schema
        - check_nulls: Find missing/null values
        - validate_ranges: Verify values are within expected ranges

        Report all validation issues found.

  memory:
    $preset: worker

  tools: [check_schema, check_nulls, validate_ranges]
```

### Compiler & Formatter Workers

```yaml
# configs/agents/workers/compiler.yaml
apiVersion: agent.framework/v2
kind: Agent
metadata:
  name: CompilerWorker
  description: Compiles data into report structure
resources:
  inference_gateways:
    - name: openai
      type: OpenAIGateway
      config:
        model: ${OPENAI_MODEL:-gpt-4o-mini}
        api_key: ${OPENAI_API_KEY}
        use_function_calling: true
  tools:
    - name: aggregate_data
      type: DataAggregatorTool
    - name: create_summary
      type: SummaryTool
spec:
  policies:
    $preset: simple
  planner:
    type: ReActPlanner
    config:
      inference_gateway: openai
      use_function_calling: true
      system_prompt: Compile data into structured report sections.
  memory:
    $preset: worker
  tools: [aggregate_data, create_summary]
```

```yaml
# configs/agents/workers/formatter.yaml
apiVersion: agent.framework/v2
kind: Agent
metadata:
  name: FormatterWorker
  description: Formats reports for presentation
resources:
  inference_gateways:
    - name: openai
      type: OpenAIGateway
      config:
        model: ${OPENAI_MODEL:-gpt-4o-mini}
        api_key: ${OPENAI_API_KEY}
        use_function_calling: true
  tools:
    - name: format_markdown
      type: MarkdownFormatterTool
    - name: create_chart
      type: ChartGeneratorTool
spec:
  policies:
    $preset: simple
  planner:
    type: ReActPlanner
    config:
      inference_gateway: openai
      use_function_calling: true
      system_prompt: Format compiled reports for presentation.
  memory:
    $preset: worker
  tools: [format_markdown, create_chart]
```

## Running the Three-Tier System

```python
import asyncio
import os
from deployment.factory import AgentFactory
from agent_framework.services.request_context import set_request_context
from agent_framework import EventBus
from agent_framework.observability.subscribers import PhoenixSubscriber

async def main():
    # Set job context
    job_id = "enterprise_job_001"
    os.environ["JOB_ID"] = job_id
    set_request_context({"JOB_ID": job_id})

    # Load orchestrator (managers and workers load recursively)
    orchestrator = AgentFactory.create_from_yaml(
        "configs/agents/orchestrator.yaml"
    )

    # Run complex task
    result = await orchestrator.run(
        "Analyze Q4 2024 sales data for all regions, "
        "validate the numbers, and create an executive summary report"
    )

    print("=" * 60)
    print("FINAL RESULT")
    print("=" * 60)
    print(result)

asyncio.run(main())
```

## Tracing the Hierarchy

With Phoenix enabled, you'll see spans like:

```
root_request
├── orchestrator:EnterpriseOrchestrator
│   ├── phase:Data Analysis
│   │   └── manager:AnalysisManager
│   │       ├── step:Gather Data
│   │       │   └── agent:GathererWorker
│   │       │       ├── action:query_database
│   │       │       └── action:fetch_api
│   │       └── step:Validate
│   │           └── agent:ValidatorWorker
│   │               └── action:check_schema
│   └── phase:Report Generation
│       └── manager:ReportingManager
│           ├── step:Compile
│           │   └── agent:CompilerWorker
│           └── step:Format
│               └── agent:FormatterWorker
```

## Model Recommendations by Tier

| Tier | Role | Recommended Model | Reasoning |
|------|------|-------------------|-----------|
| Orchestrator | Strategic planning | gpt-4o | Complex reasoning, fewer calls |
| Manager | Decomposition | gpt-4o-mini | Moderate complexity, more calls |
| Worker | Tool execution | gpt-4o-mini | Simple tasks, many calls |

## Customization Tips

| What to Change | How |
|----------------|-----|
| Add new domain | Create new manager + workers, add to orchestrator |
| Parallel phases | Set `"parallel_managers": ["mgr1", "mgr2"]` in plan |
| Share state | All agents use same `JOB_ID` namespace |
| Add synthesis | Set `synthesis_gateway` on managers/orchestrator |

## Best Practices

1. **Keep workers focused** - One domain per worker
2. **Managers decompose** - Break phases into concrete steps
3. **Orchestrator strategizes** - High-level phases only
4. **Share EventBus** - Unified observability across all tiers
5. **Use memory presets** - `worker` for workers, `manager` for managers
6. **Test each tier** - Verify workers, then managers, then orchestrator

## When NOT to Use

- Simple single-domain tasks (use [Multi-Tool Agent](multi_tool_agent.md))
- Two domains only (use [Manager + Workers](manager_workers.md))
- Cost-sensitive applications (more tiers = more LLM calls)
