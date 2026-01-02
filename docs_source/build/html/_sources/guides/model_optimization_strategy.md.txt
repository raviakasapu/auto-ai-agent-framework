---
title: Model Optimization Strategy
---

# Model Optimization Strategy

## Overview

This guide describes how to optimize LLM model selection in the agent framework for cost-performance balance. The strategy involves:

- **Powerful models** (e.g., GPT-4o, GPT-5) for strategic planning (complex reasoning, multi-step planning)
- **Efficient models** (e.g., GPT-4o-mini) for task execution (routine operations, tool calling)

This approach typically reduces costs by 60-75% while maintaining high-quality strategic decision-making.

## Architecture

The framework supports configuring different inference gateways with different models:

```
┌─────────────────────────────────────────────────────┐
│           Orchestrator Agent                        │
│                                                     │
│  ┌──────────────────────────────────────────────┐  │
│  │  Strategic Planning                          │  │
│  │  Model: GPT-4o (or GPT-5)                   │  │
│  │  - Analyzes user intent                      │  │
│  │  - Creates multi-step plans                  │  │
│  │  - Chooses workers                           │  │
│  │  - Provides strategic context                │  │
│  └──────────────────────────────────────────────┘  │
│                                                     │
└─────────────────────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
    ┌─────────┐    ┌─────────┐    ┌──────────┐
    │ Worker  │    │ Worker  │    │ Manager  │
    │ Agent 1 │    │ Agent 2 │    │ Agent    │
    └─────────┘    └─────────┘    └──────────┘
         │                              │
    GPT-4o-mini                         │
    (task execution)                    │
                                        ▼
                        ┌───────────────────────────┐
                        │   Worker Agents           │
                        │  ┌─────────┐ ┌─────────┐ │
                        │  │ Worker  │ │ Worker  │ │
                        │  │ Agent 3 │ │ Agent 4 │ │
                        │  └─────────┘ └─────────┘ │
                        └───────────────────────────┘
                                  │
                             GPT-4o-mini
                             (task execution)
```

## Why This Works

### Strategic Planning Benefits from Powerful Models

- **Complex reasoning**: Understanding ambiguous user intent, breaking down problems
- **Multi-step planning**: Creating coherent execution strategies
- **Worker selection**: Choosing the right combination of specialized agents
- **Context synthesis**: Providing rich guidance to workers

### Task Execution Benefits from Efficient Models

- **Straightforward operations**: Well-defined tool calls (CRUD operations, queries)
- **Function calling**: OpenAI function calling makes tool selection reliable
- **Clear instructions**: Workers receive specific tasks from strategic layer
- **Cost savings**: Most tokens spent on execution, not planning

## Configuration

### Multiple Inference Gateways

The framework allows you to configure multiple inference gateways with different models in your agent YAML configuration:

```yaml
apiVersion: agent.framework/v2
kind: ManagerAgent

metadata:
  name: orchestrator

resources:
  inference_gateways:
    # Strategic planning gateway - uses more powerful model
    - name: openai-strategic
      type: OpenAIGateway
      config:
        model: ${OPENAI_STRATEGIC_MODEL:-gpt-4o}
        api_key: ${OPENAI_API_KEY}
        temperature: 0.7  # Optional: for creativity in planning
    
    # Task execution gateway - uses efficient model
    - name: openai-execution
      type: OpenAIGateway
      config:
        model: ${OPENAI_MODEL:-gpt-4o-mini}
        api_key: ${OPENAI_API_KEY}
        temperature: 0.0  # Optional: for deterministic execution

spec:
  planner:
    type: StrategicPlanner
    config:
      inference_gateway: openai-strategic  # Use powerful model for planning
```

### Environment Variables

Configure model selection via environment variables:

```bash
# Strategic Planning Model (for orchestrator's StrategicPlanner)
OPENAI_STRATEGIC_MODEL=gpt-4o
# Or when GPT-5 is available:
# OPENAI_STRATEGIC_MODEL=gpt-5

# Task Execution Model (for all workers and managers)
OPENAI_MODEL=gpt-4o-mini

# Your API key
OPENAI_API_KEY=sk-your-key-here
```

### Model Options

#### Strategic Planning Models

- `gpt-4o` - Recommended, excellent reasoning at moderate cost
- `gpt-5` - When available, best reasoning (higher cost)
- `gpt-4-turbo` - Good alternative to gpt-4o
- `o1-mini` or `o1-preview` - OpenAI's reasoning models (if needed)

#### Task Execution Models

- `gpt-4o-mini` - Recommended, fast and cost-effective
- `gpt-3.5-turbo` - Even cheaper, but less capable
- `gpt-4o` - If you want consistency across all agents

## Cost-Performance Analysis

### Token Usage Pattern (Typical Session)

```
User: "Find all items matching criteria X and create a summary report"

Orchestrator (Strategic Planning):
├─ Input: ~500 tokens (system prompt, task, available workers)
└─ Output: ~200 tokens (strategic plan JSON)
Total: ~700 tokens with GPT-4o

Workers (Task Execution):
├─ query_tool: ~300 tokens (gpt-4o-mini)
├─ list_items: ~400 tokens (gpt-4o-mini)
├─ python_interpreter: ~600 tokens (gpt-4o-mini)
└─ Final synthesis: ~800 tokens (gpt-4o-mini)
Total: ~2,100 tokens with GPT-4o-mini
```

### Cost Comparison (Approximate)

#### Option 1: GPT-4o for Everything
```
Strategic: 700 tokens × $0.005/1K = $0.0035
Tasks: 2,100 tokens × $0.005/1K = $0.0105
Total per session: ~$0.014
```

#### Option 2: GPT-4o Strategic + GPT-4o-mini Tasks (Recommended)
```
Strategic: 700 tokens × $0.005/1K = $0.0035
Tasks: 2,100 tokens × $0.00015/1K = $0.00032
Total per session: ~$0.0038
Cost savings: 73%
```

#### Option 3: GPT-4o-mini for Everything
```
Strategic: 700 tokens × $0.00015/1K = $0.0001
Tasks: 2,100 tokens × $0.00015/1K = $0.00032
Total per session: ~$0.00042
But: Lower quality strategic planning
```

## When to Use Different Models

### Use Powerful Models (GPT-4o/GPT-5) for Strategic Planning When:

- ✅ Complex multi-agent orchestration
- ✅ Ambiguous user requests requiring interpretation
- ✅ Multi-step workflows with dependencies
- ✅ Need to understand domain-specific context
- ✅ Selecting between many specialized workers

### Use Efficient Models (GPT-4o-mini) for Task Execution When:

- ✅ Well-defined tool operations (CRUD operations)
- ✅ Function calling for tool selection
- ✅ Direct questions with clear answers
- ✅ Simple transformations or lookups
- ✅ Following explicit instructions from planner

### Consider Powerful Models for All Layers When:

- ⚠️ Budget is not a primary concern
- ⚠️ Maximum quality needed for all operations
- ⚠️ Complex code generation requirements
- ⚠️ Advanced reasoning needed in execution layer

## Monitoring and Optimization

### Enable Model Tracking in Logs

Configure logging to track which models are being used:

```yaml
resources:
  subscribers:
    - name: logging
      type: LoggingSubscriber
      config:
        level: INFO
        include_data: true
        event_levels:
          action_planned: INFO  # See which model is being used
          delegation_planned: INFO  # See strategic plans
```

### Check Which Model Was Used

Look for log entries showing model usage:

```
[INFO] event=delegation_planned data={
    'worker': 'worker-agent',
    'context': 'Created by StrategicPlanner using gpt-4o'
}

[DEBUG] event=action_planned data={
    'action': 'query_tool',
    'model': 'gpt-4o-mini',  # Worker using cheaper model
    'gateway': 'openai-execution'
}
```

### Performance Metrics to Track

1. **Planning Quality**
   - Are plans coherent and efficient?
   - Correct worker selection rate
   - Average steps to completion

2. **Execution Quality**
   - Tool call success rate
   - Error frequency
   - Need for retries

3. **Cost Metrics**
   - Total tokens per session
   - Cost per successful task
   - Strategic vs. execution token ratio

## Advanced Configurations

### Different Models per Manager

You can configure different models for different manager agents:

```yaml
# configs/agents/specialized_manager.yaml
resources:
  inference_gateways:
    - name: openai-specialized
      type: OpenAIGateway
      config:
        # Use GPT-4o for complex synthesis tasks
        model: ${OPENAI_SPECIALIZED_MODEL:-gpt-4o}
        api_key: ${OPENAI_API_KEY}
```

```bash
# In .env
OPENAI_STRATEGIC_MODEL=gpt-4o      # Orchestrator planning
OPENAI_SPECIALIZED_MODEL=gpt-4o    # Specialized manager synthesis
OPENAI_MODEL=gpt-4o-mini           # All other workers
```

### Temperature Control

Configure different temperature settings for planning vs. execution:

```yaml
resources:
  inference_gateways:
    - name: openai-strategic
      type: OpenAIGateway
      config:
        model: gpt-4o
        temperature: 0.7  # For creativity in planning
    
    - name: openai-execution
      type: OpenAIGateway
      config:
        model: gpt-4o-mini
        temperature: 0.0  # For deterministic execution
```

### A/B Testing Setup

Test different strategic models:

```yaml
resources:
  inference_gateways:
    - name: openai-strategic-a
      type: OpenAIGateway
      config:
        model: gpt-4o
        api_key: ${OPENAI_API_KEY}
    
    - name: openai-strategic-b
      type: OpenAIGateway
      config:
        model: gpt-5  # When available
        api_key: ${OPENAI_API_KEY}

spec:
  planner:
    type: StrategicPlanner
    config:
      # Toggle between A and B via environment variable
      inference_gateway: ${STRATEGIC_VARIANT:-openai-strategic-a}
```

## Troubleshooting

### Issue: Strategic plans are low quality

**Solution**: Increase model capacity
```bash
OPENAI_STRATEGIC_MODEL=gpt-4o  # or gpt-5
```

### Issue: Task execution is slow/expensive

**Solution**: Ensure workers use efficient model
```yaml
# In worker configs
resources:
  inference_gateways:
    - name: openai-llm
      type: OpenAIGateway
      config:
        model: ${OPENAI_MODEL:-gpt-4o-mini}  # Use mini
```

### Issue: Inconsistent results

**Solution**: Add temperature control
```yaml
resources:
  inference_gateways:
    - name: openai-strategic
      type: OpenAIGateway
      config:
        model: gpt-4o
        temperature: 0.7  # For creativity in planning
    
    - name: openai-execution
      type: OpenAIGateway
      config:
        model: gpt-4o-mini
        temperature: 0.0  # For deterministic execution
```

## Summary

### What This Strategy Provides

1. ✅ Framework support for multiple inference gateways
2. ✅ Per-planner model configuration via YAML
3. ✅ Environment variable-based model selection
4. ✅ Temperature and other parameters per gateway

### Configuration Required

1. **Environment file**: Set `OPENAI_STRATEGIC_MODEL` and `OPENAI_MODEL`
2. **Agent configs**: Define multiple inference gateways in YAML
3. **Planner config**: Specify which gateway to use for planning

### Expected Results

- 📈 Better strategic planning (smarter task breakdown)
- 💰 Lower costs (60-75% reduction vs. all powerful models)
- ⚡ Same execution speed (efficient models are fast)
- 🎯 Better worker selection (powerful models understand context better)

## Next Steps

1. Configure multiple inference gateways in your orchestrator YAML
2. Set environment variables for model selection
3. Test with complex queries and verify plan quality
4. Monitor cost savings and adjust models as needed
5. Fine-tune temperature and other parameters per use case
