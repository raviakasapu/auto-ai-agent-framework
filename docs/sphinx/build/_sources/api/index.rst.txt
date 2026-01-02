API Reference
=============

This reference documents the public API of the Agent Framework library.

Framework (Generic Library)
---------------------------

Core Classes
~~~~~~~~~~~~

.. automodule:: agent_framework.base
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: agent_framework.core.agent
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: agent_framework.core.manager_v2
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: agent_framework.core.events
   :members:
   :undoc-members:
   :show-inheritance:

Decorators
~~~~~~~~~~

.. automodule:: agent_framework.decorators
   :members:
   :undoc-members:
   :show-inheritance:

Planners
~~~~~~~~

.. automodule:: agent_framework.components.planners
   :members:
   :undoc-members:
   :show-inheritance:

Memory
~~~~~~

.. automodule:: agent_framework.components.memory
   :members:
   :undoc-members:
   :show-inheritance:

Message Store Memory
~~~~~~~~~~~~~~~~~~~~

.. automodule:: agent_framework.components.message_store_memory
   :members:
   :undoc-members:
   :show-inheritance:

Gateways
~~~~~~~~

.. automodule:: agent_framework.gateways.inference
   :members:
   :undoc-members:
   :show-inheritance:

Policies
~~~~~~~~

.. automodule:: agent_framework.policies.base
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: agent_framework.policies.presets
   :members:
   :undoc-members:
   :show-inheritance:

Services
~~~~~~~~

.. automodule:: agent_framework.services.request_context
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: agent_framework.services.context_builder
   :members:
   :undoc-members:
   :show-inheritance:

Observability
~~~~~~~~~~~~~

.. automodule:: agent_framework.observability.subscribers
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: agent_framework.logging
   :members:
   :undoc-members:
   :show-inheritance:

Progress Filters
~~~~~~~~~~~~~~~~

.. automodule:: agent_framework.progress_filters
   :members:
   :undoc-members:
   :show-inheritance:

Prompt Managers
~~~~~~~~~~~~~~~

.. automodule:: agent_framework.prompt_managers.managers
   :members:
   :undoc-members:
   :show-inheritance:

Flows
~~~~~

.. automodule:: agent_framework.flows.flow_factory
   :members:
   :undoc-members:
   :show-inheritance:

Utilities
~~~~~~~~~

.. automodule:: agent_framework.utils.manifest_generator
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: agent_framework.utils.message_builder
   :members:
   :undoc-members:
   :show-inheritance:

Deployment Layer
----------------

.. automodule:: deployment.registry
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: deployment.factory
   :members:
   :undoc-members:
   :show-inheritance:

BI Tools (Domain Example)
-------------------------

These modules demonstrate how to extend the framework for a specific domain (Power BI).

Services
~~~~~~~~

.. automodule:: bi_tools.services.datamodel_service
   :members:
   :undoc-members:
   :show-inheritance:

Tools
~~~~~

Domain-specific tools are organized by category:

- ``bi_tools.tools.column`` - Column operations
- ``bi_tools.tools.measure`` - DAX measure operations
- ``bi_tools.tools.relationship`` - Relationship management
- ``bi_tools.tools.table`` - Table operations
- ``bi_tools.tools.sql`` - SQL query operations
- ``bi_tools.tools.partition`` - Partition management
- ``bi_tools.tools.mquery`` - M Query operations
- ``bi_tools.tools.metadata`` - Metadata access
- ``bi_tools.tools.model`` - Model operations
