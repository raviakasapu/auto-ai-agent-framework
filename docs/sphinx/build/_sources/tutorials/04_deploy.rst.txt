Deploy the Agent API (5 minutes)
================================

FastAPI Server
--------------
Create ``examples/calculator_server.py``:

.. code-block:: python

   from fastapi import FastAPI
   from pydantic import BaseModel
   from deployment.factory import AgentFactory
   import asyncio

   app = FastAPI(title="Calculator Agent API")
   agent = None

   @app.on_event("startup")
   async def startup():
       global agent
       agent = AgentFactory.create_from_yaml("configs/agents/calculator_agent.yaml")

   class Request(BaseModel):
       operation: str
       num1: float
       num2: float

   @app.post("/calculate")
   async def calculate(req: Request):
       return await agent.run(operation=req.operation, num1=req.num1, num2=req.num2)

Run
---

.. code-block:: bash

   # from repo root
   uvicorn examples.calculator_server:app --reload --port 8010

Test
----

.. code-block:: bash

   curl -s -X POST http://127.0.0.1:8010/calculate \
     -H 'Content-Type: application/json' \
     -d '{"operation":"add","num1":10,"num2":5}'

Next
----
- Add auth, logging, rate limiting
- Containerize with Docker and deploy
