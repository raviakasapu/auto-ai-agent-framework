Legacy Guides
=============

.. note::

   This section contains legacy documentation that has been reorganized into the main documentation structure.
   Please use the links below to find the updated content.

Content Mapping
---------------

**Getting Started**
   All getting started content is now in **Part 1: Orientation**:
   
   - :doc:`../part1_orientation/quickstart` — Installation and first agent
   - :doc:`../part1_orientation/conceptual_model` — Core concepts and mental model
   - :doc:`../part1_orientation/overview` — Framework overview

**Building Agents**
   Agent development guides are in **Part 2: Runtime Building Blocks**:
   
   - :doc:`../part2_runtime/agents` — Agent and ManagerAgent deep dive
   - :doc:`../part2_runtime/planners` — All planner types
   - :doc:`../part2_runtime/tools` — Tool development
   - :doc:`../part2_runtime/memory` — Memory implementations
   - :doc:`../part2_runtime/policies` — Behavioral policies

**Configuration & Deployment**
   Configuration topics are in **Part 3: Building Solutions**:
   
   - :doc:`../part3_solutions/configuration` — YAML configuration
   - :doc:`../part3_solutions/deployment` — Deployment and operations
   - :doc:`../part3_solutions/message_stores` — Message store integration
   - :doc:`../part3_solutions/flows` — Flow orchestration

**Extensibility**
   Extension recipes are in **Part 4: Extensibility Cookbook**:
   
   - :doc:`../part4_cookbook/custom_tool` — Creating custom tools
   - :doc:`../part4_cookbook/custom_planner` — Creating custom planners
   - :doc:`../part4_cookbook/progress_subscriber` — Event subscribers

**Operations**
   Operational guides are in **Part 5: Operating the Framework**:
   
   - :doc:`../part5_operations/monitoring` — Phoenix tracing and observability
   - :doc:`../part5_operations/troubleshooting` — Common issues

**Reference**
   Reference material is in **Part 7: Reference**:
   
   - :doc:`../part7_reference/env_variables` — Environment variables
   - :doc:`../part7_reference/message_format` — Message format specification
   - :doc:`../part7_reference/migration` — Version migration guide

**Power BI Implementation**
   For the Power BI reference implementation, see:
   
   - :doc:`../powerbi_impl/index` — Complete case study

Additional Topics
-----------------

The following guides contain specialized content referenced from the main documentation:

.. toctree::
   :maxdepth: 1
   :caption: Architecture Deep Dives

   hierarchical_filtering
   architecture_workflow
   phoenix_tracing
   event_system
   async_safety

.. toctree::
   :maxdepth: 1
   :caption: Strategy Guides

   strategic_planning_architecture
   model_optimization_strategy
   tool_choice_mechanism
   structured_final_response
   orchestrator_vs_manager

.. toctree::
   :maxdepth: 1
   :caption: Message Store Reference

   message_store_integration
   message_store_format
   message_store_implementation

.. toctree::
   :maxdepth: 1
   :caption: Utility & Tools

   utility_tools
   environment_variables
