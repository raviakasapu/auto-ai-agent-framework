AI Agent Framework Documentation
=================================

A production-ready framework for building multi-agent AI systems with YAML-based configuration,
hierarchical memory, and policy-driven behavior control.

.. toctree::
   :maxdepth: 2
   :caption: Getting Started

   getting-started
   quickstart

.. toctree::
   :maxdepth: 2
   :caption: Configuration Guides

   guides/yaml-configuration
   guides/agent-types
   guides/memory-presets
   guides/policy-presets
   guides/tools
   guides/planners

.. toctree::
   :maxdepth: 2
   :caption: Examples

   examples/single-agent
   examples/multi-agent
   examples/custom-tools

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   api/core
   api/components
   api/policies

.. toctree::
   :maxdepth: 1
   :caption: Development

   testing
   contributing


Key Features
------------

* **YAML-Based Configuration**: Define agents declaratively without code changes
* **Multi-Agent Orchestration**: Manager-worker patterns with automatic routing
* **Memory Presets**: Simplified memory configuration with ``$preset: worker``
* **Policy Presets**: Pre-configured behavior policies for common use cases
* **Hierarchical Memory**: Shared state across agent teams with isolation
* **Comprehensive Testing**: 170+ tests across unit, integration, and E2E tiers


Quick Example
-------------

.. code-block:: yaml

   apiVersion: agent.framework/v2
   kind: Agent

   metadata:
     name: ResearchWorker

   spec:
     policies:
       $preset: simple

     planner:
       type: ReActPlanner
       config:
         inference_gateway: openai

     memory:
       $preset: worker

     tools: [web_search, note_taker]


Installation
------------

.. code-block:: bash

   pip install agent-framework


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
