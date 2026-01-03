# Changelog

All notable changes to the AI Agent Framework will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2025-01-02

### Added

- **Part 8: Common Patterns** - New documentation section with copy-paste-ready YAML configurations:
  - Minimal Agent - Simplest possible agent with one tool
  - Multi-Tool Agent - ReAct agent with multiple tools
  - Manager + Workers - Manager routing to specialized workers
  - Shared Memory Team - Workers collaborating via shared memory
  - HITL Approval - Human-in-the-loop for write operations
  - Three-Tier Hierarchy - Orchestrator → Manager → Workers architecture

- **Documentation Overhaul**:
  - Comprehensive testing guide with multi-tier strategy (unit, integration, E2E)
  - Memory presets documentation (`$preset: worker`, `$preset: manager`)
  - Policy presets documentation (`$preset: simple`, `$preset: with_hitl`)
  - Troubleshooting guide with common issues and solutions
  - Environment variables reference

- **CLI Scaffolding**:
  - `agent-framework init` command to create new projects
  - Sample app template with complete YAML configurations

### Changed

- Documentation restructured into 8 parts for better navigation
- Improved YAML configuration guide with complete examples
- Enhanced sample app with comprehensive test suite

### Fixed

- Documentation build process now correctly syncs to deployment folder

## [0.2.0] - 2024-12-20

### Added

- **Message Store Memory** - `MessageStoreMemory` and `HierarchicalMessageStoreMemory` for external storage
- **Policy Presets** - `get_preset()` function for quick policy configuration
- **@tool Decorator** - Zero-boilerplate tool creation with automatic schema generation
- **Phoenix/OpenTelemetry Tracing** - Full observability with cost and usage tracking
- **ManagerAgent** - Hierarchical agent orchestration with worker routing
- **Strategic Planner** - Multi-phase planning for complex workflows
- **HITL Policy** - Human-in-the-loop approval for sensitive operations

### Changed

- Memory interface now fully async (`async def add()`, `async def get_history()`)
- Policies are now required for Agent instantiation
- Improved context truncation with configurable limits

## [0.1.0] - 2024-11-15

### Added

- Initial release of AI Agent Framework
- Core `Agent` class with ReAct planning loop
- `BaseTool`, `BasePlanner`, `BaseMemory` abstract interfaces
- `InMemoryMemory` and `SharedInMemoryMemory` implementations
- `ReActPlanner` and `ChatPlanner` implementations
- `OpenAIGateway` for LLM integration
- `EventBus` for observability
- YAML configuration support with `AgentFactory`
- Sample application demonstrating framework usage

---

## Version History Summary

| Version | Date | Highlights |
|---------|------|------------|
| 0.3.0 | 2025-01-02 | Common Patterns docs, CLI scaffolding, testing guide |
| 0.2.0 | 2024-12-20 | Message stores, policy presets, @tool decorator, Phoenix tracing |
| 0.1.0 | 2024-11-15 | Initial release |
