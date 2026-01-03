AI Agent Framework Documentation
================================

**Version 2.2** — A production-grade Python library for building hierarchical, policy-driven AI agent systems.

The framework ships as the ``agent_framework`` pip package and includes:

- 🧱 **Pip-installable library** with clean ``agent_framework`` namespace
- 🛠️ **@tool decorator** and ``FunctionalTool`` for zero-boilerplate tool creation
- 🧠 **Policy presets** (``get_preset``) for completion, termination, and loop prevention
- 📦 **Message store memory** so agents read/write from external stores
- 📡 **Phoenix/OpenTelemetry tracing** with usage, cost, and actor metadata
- 🎯 **Hierarchical agents** with Orchestrator → Manager → Worker patterns

Quick Links
-----------

- :doc:`part1_orientation/quickstart` — Get started in 5 minutes
- :doc:`part1_orientation/conceptual_model` — Understand the mental model
- :doc:`part2_runtime/agents` — Deep dive into Agent and ManagerAgent
- :doc:`part4_cookbook/index` — "How do I...?" recipes
- :doc:`part8_patterns/index` — Copy-paste YAML patterns for common architectures

.. toctree::
   :maxdepth: 2
   :caption: Part 1: Orientation

   part1_orientation/index

.. toctree::
   :maxdepth: 2
   :caption: Part 2: Runtime Building Blocks

   part2_runtime/index

.. toctree::
   :maxdepth: 2
   :caption: Part 3: Building Solutions

   part3_solutions/index

.. toctree::
   :maxdepth: 2
   :caption: Part 4: Extensibility Cookbook

   part4_cookbook/index

.. toctree::
   :maxdepth: 2
   :caption: Part 5: Operating the Framework

   part5_operations/index

.. toctree::
   :maxdepth: 2
   :caption: Part 6: Domain Playbooks

   part6_playbooks/index

.. toctree::
   :maxdepth: 2
   :caption: Part 7: Reference

   part7_reference/index
   api/index

.. toctree::
   :maxdepth: 2
   :caption: Part 8: Common Patterns

   part8_patterns/index

.. toctree::
   :maxdepth: 2
   :caption: Power BI Implementation

   powerbi_impl/index

.. toctree::
   :maxdepth: 1
   :caption: Tutorials

   tutorials/index

.. toctree::
   :maxdepth: 1
   :caption: Legacy Guides

   guides/index

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
