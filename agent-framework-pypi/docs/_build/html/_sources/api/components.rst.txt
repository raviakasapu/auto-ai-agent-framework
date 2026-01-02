Components API Reference
========================

This section documents the component classes for memory, planners, and gateways.

Memory
------

InMemoryMemory
~~~~~~~~~~~~~~

.. autoclass:: agent_framework.components.memory.InMemoryMemory
   :members:
   :undoc-members:
   :show-inheritance:

SharedInMemoryMemory
~~~~~~~~~~~~~~~~~~~~

.. autoclass:: agent_framework.components.memory.SharedInMemoryMemory
   :members:
   :undoc-members:
   :show-inheritance:

HierarchicalSharedMemory
~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: agent_framework.components.memory.HierarchicalSharedMemory
   :members:
   :undoc-members:
   :show-inheritance:

Memory Presets
~~~~~~~~~~~~~~

.. automodule:: agent_framework.components.memory_presets
   :members:
   :undoc-members:

Planners
--------

ReActPlanner
~~~~~~~~~~~~

.. autoclass:: agent_framework.planners.react_planner.ReActPlanner
   :members:
   :undoc-members:
   :show-inheritance:

WorkerRouterPlanner
~~~~~~~~~~~~~~~~~~~

.. autoclass:: agent_framework.planners.router_planner.WorkerRouterPlanner
   :members:
   :undoc-members:
   :show-inheritance:

Inference Gateways
------------------

OpenAIGateway
~~~~~~~~~~~~~

.. autoclass:: agent_framework.gateways.openai_gateway.OpenAIGateway
   :members:
   :undoc-members:
   :show-inheritance:

AnthropicGateway
~~~~~~~~~~~~~~~~

.. autoclass:: agent_framework.gateways.anthropic_gateway.AnthropicGateway
   :members:
   :undoc-members:
   :show-inheritance:

MockGateway
~~~~~~~~~~~

.. autoclass:: agent_framework.gateways.mock_gateway.MockGateway
   :members:
   :undoc-members:
   :show-inheritance:
