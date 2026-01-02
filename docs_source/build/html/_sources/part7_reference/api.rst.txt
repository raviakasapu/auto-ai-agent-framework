API Reference
=============

For complete API documentation, see the auto-generated reference:

:doc:`/api/index`

Public API Summary
------------------

The following classes and functions are exported from ``agent_framework``:

Core Agents
^^^^^^^^^^^

.. list-table::
   :widths: 30 70
   :header-rows: 1

   * - Class
     - Description
   * - ``Agent``
     - Policy-driven worker agent
   * - ``ManagerAgent``
     - Orchestrator/manager with delegation
   * - ``EventBus``
     - Event publishing system

Base Classes
^^^^^^^^^^^^

.. list-table::
   :widths: 30 70
   :header-rows: 1

   * - Class
     - Description
   * - ``BaseTool``
     - Abstract tool interface
   * - ``BasePlanner``
     - Abstract planner interface
   * - ``BaseMemory``
     - Abstract memory interface
   * - ``BaseInferenceGateway``
     - Abstract LLM gateway interface
   * - ``BaseEventSubscriber``
     - Sync event subscriber
   * - ``BaseProgressHandler``
     - Async progress handler
   * - ``BaseMessageStore``
     - Abstract message store interface
   * - ``BaseJobStore``
     - Abstract job persistence interface

Data Classes
^^^^^^^^^^^^

.. list-table::
   :widths: 30 70
   :header-rows: 1

   * - Class
     - Description
   * - ``Action``
     - Tool invocation request
   * - ``FinalResponse``
     - Structured completion response

Decorators
^^^^^^^^^^

.. list-table::
   :widths: 30 70
   :header-rows: 1

   * - Decorator
     - Description
   * - ``@tool``
     - Convert function to tool
   * - ``FunctionalTool``
     - Wrapper for decorated functions

Memory Implementations
^^^^^^^^^^^^^^^^^^^^^^

.. list-table::
   :widths: 30 70
   :header-rows: 1

   * - Class
     - Description
   * - ``MessageStoreMemory``
     - Reads from BaseMessageStore
   * - ``HierarchicalMessageStoreMemory``
     - Manager memory with subordinate visibility

Policies
^^^^^^^^

.. list-table::
   :widths: 30 70
   :header-rows: 1

   * - Function
     - Description
   * - ``get_preset(name)``
     - Get policy preset by name

Import Example
--------------

.. code-block:: python

   from agent_framework import (
       # Core
       Agent,
       ManagerAgent,
       EventBus,
       
       # Base Classes
       BaseTool,
       BasePlanner,
       BaseMemory,
       BaseInferenceGateway,
       BaseEventSubscriber,
       BaseProgressHandler,
       BaseMessageStore,
       BaseJobStore,
       
       # Data Classes
       Action,
       FinalResponse,
       
       # Decorators
       tool,
       FunctionalTool,
       
       # Memory
       MessageStoreMemory,
       HierarchicalMessageStoreMemory,
       
       # Policies
       get_preset,
   )

