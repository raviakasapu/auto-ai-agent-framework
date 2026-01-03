Part 8: Common Patterns
=======================

Copy-paste-ready YAML configurations for common agent architectures. Each pattern includes complete, working YAML that you can adopt directly into your project.

How to Use These Patterns
-------------------------

1. **Copy** the YAML configuration to your ``configs/agents/`` directory
2. **Customize** the metadata, system prompts, and tool references
3. **Register** any custom tools in your deployment registry
4. **Run** using the AgentFactory

.. code-block:: python

   from deployment.factory import AgentFactory

   agent = AgentFactory.create_from_yaml("configs/agents/my_agent.yaml")
   result = await agent.run("Your task here")

Pattern Index
-------------

.. list-table::
   :header-rows: 1
   :widths: 25 50 25

   * - Pattern
     - Use Case
     - Complexity
   * - :doc:`minimal_agent`
     - Simplest possible agent with one tool
     - Beginner
   * - :doc:`multi_tool_agent`
     - Agent with multiple tools and ReAct planning
     - Beginner
   * - :doc:`manager_workers`
     - Manager routing tasks to 2 specialized workers
     - Intermediate
   * - :doc:`shared_memory_team`
     - Workers collaborating via shared memory
     - Intermediate
   * - :doc:`hitl_approval`
     - Human-in-the-loop approval for write operations
     - Intermediate
   * - :doc:`three_tier_hierarchy`
     - Orchestrator -> Manager -> Workers architecture
     - Advanced

.. toctree::
   :maxdepth: 1
   :hidden:

   minimal_agent
   multi_tool_agent
   manager_workers
   shared_memory_team
   hitl_approval
   three_tier_hierarchy
