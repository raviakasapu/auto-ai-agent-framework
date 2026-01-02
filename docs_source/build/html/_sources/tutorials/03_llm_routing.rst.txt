Add Natural Language Routing (7 minutes)
========================================

Goal
----
Use the LLM router planner so users can say “add 2 and 3”.

Step 1 — Switch Planner
-----------------------
Update ``configs/agents/calculator_agent.yaml``:

.. code-block:: yaml

   spec:
     planner:
       type: LLMRouterPlanner
       config:
         inference_gateway: mock-llm
         tool_specs:
           - tool: calculator
             args: [operation, num1, num2]

Step 2 — Try It
---------------

.. code-block:: python

   from deployment.factory import AgentFactory
   import asyncio

   async def main():
       agent = AgentFactory.create_from_yaml("configs/agents/calculator_agent.yaml")
       print(await agent.run("add 2 and 3"))

   asyncio.run(main())

Notes
-----
- Using ``MockInferenceGateway`` yields deterministic routing for tests
- Swap to a real LLM gateway in production (see Guides → Deployment Layer)
