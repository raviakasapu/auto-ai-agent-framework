Add a Custom Tool (8 minutes)
=============================

Goal
----
Create a calculator tool with validated inputs and add it to your agent.

Step 1 — Implement the Tool
---------------------------
Create ``examples/calculator_tool.py`` (or any module in your app):

.. code-block:: python

   from typing import Any, Dict
   from pydantic import BaseModel, Field
   from agent_framework import BaseTool

   class CalculatorInput(BaseModel):
       operation: str = Field(..., description="add|subtract|multiply|divide")
       num1: float
       num2: float

   class CalculatorOutput(BaseModel):
       result: float
       operation: str

   class CalculatorTool(BaseTool):
       """Basic arithmetic operations with Pydantic validation."""
       name = "calculator"
       description = "Basic arithmetic"
       input_schema = CalculatorInput
       output_schema = CalculatorOutput

       def execute(self, **kwargs) -> Dict[str, Any]:
           data = self.input_schema(**kwargs)
           op = data.operation.lower()
           if op == "add":
               res = data.num1 + data.num2
           elif op == "subtract":
               res = data.num1 - data.num2
           elif op == "multiply":
               res = data.num1 * data.num2
           elif op == "divide":
               if data.num2 == 0:
                   raise ValueError("division by zero")
               res = data.num1 / data.num2
           else:
               raise ValueError(f"unknown op: {op}")
           return {"result": res, "operation": op}

Step 2 — Register the Tool
--------------------------
Declarative option (recommended): create ``configs/tools/calculator.yaml`` referencing the class path.

.. code-block:: yaml

   name: CalculatorTool
   class: examples.calculator_tool.CalculatorTool

Dynamic option: call ``register_tool("CalculatorTool", CalculatorTool)`` at startup via ``deployment.registry``.

.. code-block:: python

   from deployment.registry import register_tool
   from examples.calculator_tool import CalculatorTool

   register_tool("CalculatorTool", CalculatorTool)

Step 3 — Reference in YAML
--------------------------
Update or create ``configs/agents/calculator_agent.yaml``:

.. code-block:: yaml

   apiVersion: agent.framework/v1
   kind: Agent
   metadata:
     name: CalculatorAgent
     description: Performs arithmetic
   resources:
     inference_gateways:
       - name: mock-llm
         type: MockInferenceGateway
         config: {}
     tools:
       - name: calculator
         type: CalculatorTool
         config: {}
   spec:
     planner:
       type: StaticPlanner
       config:
         # always call calculator directly
     memory:
       type: InMemoryMemory
       config: {}
     tools:
       - calculator

Step 4 — Run
------------

.. code-block:: python

   from deployment.factory import AgentFactory
   import asyncio

   async def main():
       agent = AgentFactory.create_from_yaml("configs/agents/calculator_agent.yaml")
       print(await agent.run("Add 2 and 3"))

   asyncio.run(main())

Next
----
- Switch to LLM routing to accept natural language (next tutorial)
