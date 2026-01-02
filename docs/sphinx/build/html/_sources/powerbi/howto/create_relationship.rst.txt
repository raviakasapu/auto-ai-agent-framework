Create a Relationship
=====================

Goal
----
Create a relationship between two columns in the TMDL model using the agent.

Prerequisites
-------------
- ``MODEL_DIR`` exported to your ``Model/`` folder
- ``configs/agents/schema_editor_router.yaml`` available

Natural Language (Recommended)
------------------------------
.. code-block:: bash

   curl -s -X POST http://127.0.0.1:8011/run \
     -H 'Content-Type: application/json' \
     -d '{
           "task": "Create a relationship between \'SALES\'[CustomerId] and \'CUSTOMERS\'[Id]",
           "config_path": "configs/agents/schema_editor_router.yaml"
         }'

Deterministic Call (Python)
---------------------------
.. code-block:: python

   from deployment.factory import AgentFactory
   import asyncio

   async def main():
       agent = AgentFactory.create_from_yaml("configs/agents/schema_editor_router.yaml")
       out = await agent.run(
           tool="add_relationship",
           args={
               "model_dir": "${MODEL_DIR}",
               "from_table": "SALES",
               "from_column": "CustomerId",
               "to_table": "CUSTOMERS",
               "to_column": "Id"
           }
       )
       print(out)

   asyncio.run(main())

Result
------
Expect ``{"success": true, "relationship_id": "..."}`` and a new block in ``Model/relationships.tmdl``.


