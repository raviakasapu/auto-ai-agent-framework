Power BI Dashboard Editor Implementation
========================================

This section provides a complete case study of a production implementation of the AI Agent Framework: 
a Power BI Dashboard Editor that enables natural language interaction with Power BI data models.

This is a **reference implementation** that demonstrates:

- Full FastAPI/WebSocket server integration
- Hierarchical agent architecture (Orchestrator → Manager → Worker)
- Domain-specific tools for Power BI model manipulation
- Knowledge Graph service integration
- Phoenix tracing and observability
- Human-in-the-Loop (HITL) approval flows

Use this section to understand how to build production-grade agent systems with the framework.

.. toctree::
   :maxdepth: 2

   runtime_integration
   agent_stack
   data_services
   tools_coverage
   observability_approvals
   implementation_status

