Framework Guide
===============

The AI Agent Framework is a **reusable Python library** for building agentic AI systems.
This guide provides an overview of core concepts, architecture, and how to get started.

Library Architecture
--------------------

The framework is split into two parts:

**Generic Library** (``agent-framework-pypi/src/agent_framework/``)
   Pip-installable package containing reusable components:
   
   - ``Agent``, ``ManagerAgent`` - Core agent classes
   - ``BaseTool``, ``BasePlanner``, ``BaseMemory`` - Base classes for extension
   - ``EventBus`` - Observability and event system
   - Policy system for behavior control
   - LLM gateways (OpenAI, Google AI)

**Application Code** (e.g., ``bi_tools/``)
   Domain-specific implementations:
   
   - Custom tools for your domain
   - Domain services and data models
   - Application-specific configurations

Core Concepts
-------------

- **Agent**: A stateful decision-maker that processes input, plans steps, invokes tools, and produces results.
- **Tools**: Typed operations the agent can invoke. Inherit from ``BaseTool``.
- **Memory**: Conversation and long-term context stores.
- **Planner**: Strategy for selecting the next action (ReAct, Router, Strategic, etc.).
- **Policy**: Behavior control (completion detection, termination, HITL, loop prevention).
- **Events**: Structured traces for observability and debugging.

Quick Start
-----------

.. code-block:: python

   from agent_framework import Agent, ManagerAgent, BaseTool
   from agent_framework.gateways.inference import OpenAIGateway
   from deployment.factory import AgentFactory

   # Create agent from YAML
   agent = AgentFactory.create_from_yaml("configs/agents/my_agent.yaml")
   
   # Run the agent
   result = agent.run("Your task here")

Creating Custom Tools
---------------------

1. **Define the tool class**:

.. code-block:: python

   from agent_framework import BaseTool
   from pydantic import BaseModel

   class MyTool(BaseTool):
       @property
       def name(self): return "my_tool"
       
       @property
       def description(self): return "Does something useful"
       
       def execute(self, **kwargs):
           return {"result": "success"}

2. **Register via YAML** (``configs/tools/my_tool.yaml``):

.. code-block:: yaml

   name: MyTool
   class: my_app.tools.MyTool

3. **Or register dynamically**:

.. code-block:: python

   from deployment.registry import register_tool
   register_tool("MyTool", MyTool)

Configuration (YAML)
--------------------

- **Tools**: Names map to registered implementations
- **Model**: LLM provider and parameters
- **Memory**: Conversation history, shared state
- **Policies**: Behavior control settings
- **Environment**: Secrets via env vars

Deploy and Serve
----------------

- **API Server**: Expose endpoints that run agents
- **Manifest**: Generate machine-readable tool descriptions
- **Docs**: Serve Sphinx HTML alongside the manifest

References
----------

- :doc:`guides/library_architecture` - Detailed library architecture
- :doc:`guides/quickstart` - 5-minute quickstart
- :doc:`guides/creating_a_custom_tool` - Tool creation guide
- :doc:`tutorials/index` - Step-by-step tutorials
- :doc:`api/index` - API Reference
