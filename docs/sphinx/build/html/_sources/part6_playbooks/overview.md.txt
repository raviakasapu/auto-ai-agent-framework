# Domain Playbooks Overview

This section provides architectural patterns for building agent systems across different verticals.

## What is a Domain Playbook?

A Domain Playbook is a recipe for structuring agents, tools, and policies for a specific use case:

- **Agent Hierarchy**: How to structure orchestrator, managers, and workers
- **Tool Categories**: What types of tools the domain requires
- **Policy Patterns**: Common HITL, validation, and access control needs
- **Integration Points**: External services and data sources

## Pattern Template

Each playbook follows this structure:

```
┌─────────────────────────────────────────────────────────────┐
│ ORCHESTRATOR                                                │
│ - Intent clarification                                      │
│ - Strategic planning                                        │
│ - Worker routing                                            │
└─────────────────────────────────────────────────────────────┘
         │
         ├──────────────────────────────────────────┐
         │                                          │
         ▼                                          ▼
┌─────────────────────────────┐    ┌─────────────────────────────┐
│ DOMAIN MANAGER (Read)       │    │ DOMAIN MANAGER (Write)      │
│ - Analysis tasks            │    │ - Authoring tasks           │
│ - Read-only workers         │    │ - Write-capable workers     │
└─────────────────────────────┘    └─────────────────────────────┘
         │                                          │
         ▼                                          ▼
┌─────────────────────────────┐    ┌─────────────────────────────┐
│ SPECIALIZED WORKERS         │    │ SPECIALIZED WORKERS         │
│ - Domain-specific tools     │    │ - Domain-specific tools     │
│ - ReAct planning            │    │ - HITL for writes           │
└─────────────────────────────┘    └─────────────────────────────┘
```

## Available Playbooks

| Playbook | Description | Reference Implementation |
|----------|-------------|-------------------------|
| [Data Analytics](data_analytics.md) | BI dashboards, data models | [Power BI Implementation](/powerbi_impl/index) |
| [Document Processing](document_processing.md) | Document analysis, extraction | — |
| [Code Assistant](code_assistant.md) | Code analysis, refactoring | — |

## Cross-Cutting Concerns

All playbooks share these framework capabilities:

### Observability
- Phoenix tracing for all spans
- Hierarchical event streaming
- LLM cost tracking

### Multi-Turn Context
- SharedInMemoryMemory for context sharing
- MessageStoreMemory for persistence
- Hierarchical history filtering

### Access Control
- Separate read/write workers
- HITL policies for writes
- Tool-level permissions

### Structured Output
- FinalResponse contract
- Machine-readable operation + payload
- Human-readable summary

## Building Your Own Playbook

1. **Identify the domain** — What problem space?
2. **Define operations** — Read vs write capabilities
3. **Design tool set** — Domain-specific actions
4. **Structure hierarchy** — Orchestrator → Manager → Worker
5. **Configure policies** — HITL, termination, follow-ups
6. **Set up context** — Data services and manifests
7. **Wire observability** — Phoenix + event streaming

