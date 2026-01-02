Quickstart (5 minutes)
======================

This guide gets you from zero to running agent in 5 minutes.

Prerequisites
-------------

- Python 3.10+
- OpenAI API key (or other LLM provider)

Installation
------------

Create and activate a virtual environment::

   python3 -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate

Install the framework::

   # From PyPI
   pip install agentic-framework

   # Or from source
   pip install -e ./agent-framework-pypi

Set your API key::

   export OPENAI_API_KEY="sk-..."

Scaffold a Sample Project (Recommended)
---------------------------------------

The fastest way to get started is using the CLI to create a complete sample project::

   # Create a new project
   agent-framework init my_agent_project

   # Navigate to the project
   cd my_agent_project

   # Setup environment
   cp .env.example .env
   # Edit .env and add your OPENAI_API_KEY

   # Run the sample app
   python run.py                           # Interactive mode
   python run.py "Search for Python"       # Single task
   python run.py --test                    # Run test scenarios

The sample project includes:

- **Research Worker**: Web search, note-taking, calculations (ReActPlanner)
- **Task Worker**: Task CRUD, weather lookup (ReActPlanner)
- **Orchestrator**: Routes requests to workers (WorkerRouterPlanner)
- **YAML Configuration**: Full v2 agent schema with environment variables
- **Custom Tools**: 6 example tools demonstrating the BaseTool pattern

CLI Commands::

   agent-framework --help           # Show help
   agent-framework init             # Create project (default: agent_project)
   agent-framework init my_project  # Create with custom name
   agent-framework --version        # Show version

Your First Agent (From Scratch)
-------------------------------

Create a file ``my_first_agent.py``:

.. code-block:: python

   import asyncio
   from agent_framework import Agent
   from agent_framework.components.planners import StaticPlanner
   from agent_framework.components.memory import SimpleMemory
   from agent_framework.decorators import tool

   # 1. Define a tool
   @tool(name="greet", description="Greet someone by name")
   def greet(name: str) -> str:
       """Return a greeting for the given name."""
       return f"Hello, {name}! Welcome to the AI Agent Framework."

   # 2. Create agent components
   planner = StaticPlanner(tool_name="greet")
   memory = SimpleMemory()

   # 3. Build the agent
   agent = Agent(
       name="greeter",
       planner=planner,
       tools=[greet],
       memory=memory,
   )

   # 4. Run it
   async def main():
       result = await agent.run("Greet Alice")
       print(result)

   if __name__ == "__main__":
       asyncio.run(main())

Run it::

   python my_first_agent.py

You should see::

   Hello, Alice! Welcome to the AI Agent Framework.

Using YAML Configuration
------------------------

The framework supports declarative YAML configuration. Create ``my_agent.yaml``:

.. code-block:: yaml

   name: greeter
   type: Agent
   resources:
     tools:
       - name: greet
         type: GreetTool
   spec:
     planner:
       type: StaticPlanner
       config:
         tool_name: greet
     memory:
       type: SimpleMemory
     tools: [greet]

Load and run with the factory:

.. code-block:: python

   from deployment.factory import AgentFactory

   agent = AgentFactory.create_from_yaml("my_agent.yaml")
   result = await agent.run("Greet Bob")

Running the Test Suite
----------------------

To verify your installation::

   pytest tests/ -v

Project Structure
-----------------

Understanding the repository layout::

    project/
    ├── agent-framework-pypi/           # Pip-installable library
    │   └── src/agent_framework/        # Core package
    │       ├── base.py                 # BaseTool, BasePlanner, BaseMemory
    │       ├── core/                   # Agent, ManagerAgent
    │       ├── components/             # Planners, memories
    │       ├── gateways/               # LLM interfaces
    │       ├── policies/               # Behavioral policies
    │       └── decorators.py           # @tool decorator
    │
    ├── deployment/                     # YAML → Agent factory
    │   ├── factory.py                  # AgentFactory
    │   └── registry.py                 # Component registry
    │
    ├── configs/                        # YAML configurations
    │   ├── agents/                     # Agent configs
    │   └── tools/                      # Tool configs
    │
    └── docs/sphinx/                    # This documentation

Common Tasks
------------

**Run an existing agent:**

::

   from deployment.factory import AgentFactory
   agent = AgentFactory.create_from_yaml("configs/agents/my_agent.yaml")
   result = await agent.run("Your task")

**View agent configuration:**

::

   cat configs/agents/orchestrator.yaml

**Generate documentation:**

::

   cd docs/sphinx && make html

Next Steps
----------

- :doc:`conceptual_model` — Understand planners, tools, memory, policies
- :doc:`../part2_runtime/agents` — Deep dive into Agent and ManagerAgent
- :doc:`../tutorials/index` — Step-by-step tutorials

