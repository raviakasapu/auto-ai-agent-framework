Create a New Agent (10 minutes)
===============================

Outcome
-------
- A minimal agent defined in YAML
- Runs via Python and exposes a FastAPI endpoint
- Appears in the Docs Server manifest

Prerequisites
-------------
- Python 3.11+
- ``pip install -e ./agent-framework-pypi``
- ``pip install -r requirements.txt``
  
Step 1 — Create YAML
---------------------
Create ``configs/agents/hello_calc.yaml``:

.. code-block:: yaml

   apiVersion: agent.framework/v1
   kind: Agent
   metadata:
     name: HelloCalc
     description: Minimal calculator agent
     version: 1.0.0
   resources:
     inference_gateways:
       - name: mock-llm
         type: MockInferenceGateway
         config: {}
     tools:
       - name: mock_search
         type: MockSearchTool
         config: {}
   spec:
     planner:
       type: StaticPlanner
       config: {}
     memory:
       type: InMemoryMemory
       config: {}
     tools:
       - mock_search

Step 2 — Run the Agent
-----------------------

.. code-block:: python

   from deployment.factory import AgentFactory
   import asyncio

   async def main():
       agent = AgentFactory.create_from_yaml("configs/agents/hello_calc.yaml")
       result = await agent.run(query="hello", region="us-en")
       print(result)

   asyncio.run(main())

Step 3 — Generate Manifest and Open Docs
----------------------------------------

.. code-block:: bash

   # from repo root
   python generate_manifest.py \
     --config configs/agents/hello_calc.yaml \
     --output docs/agent_manifest.json

   AGENT_MANIFEST_PATH=docs/agent_manifest.json \
   AGENT_DOCS_DIR=docs/sphinx/build/html \
   uvicorn docs_server.main:app --reload --port 8002

Open:

- Manifest: http://127.0.0.1:8002/
- Sphinx Reference: http://127.0.0.1:8002/reference/

Next Steps
----------
- Add your own tool (next tutorial)
- Switch to LLM routing
- Deploy the API server
