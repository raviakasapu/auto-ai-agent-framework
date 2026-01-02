Run the Agent API Server
========================

Start Demo Server
-----------------
.. code-block:: bash

   # from repo root
   export MODEL_DIR=/absolute/path/to/pbit_data/Model
   uvicorn tests.simple_app:app --reload --port 8011

Test a Request
--------------
.. code-block:: bash

   curl -s -X POST http://127.0.0.1:8011/run \
     -H 'Content-Type: application/json' \
     -d '{
           "task": "Create a relationship between \'SALES\'[CustomerId] and \'CUSTOMERS\'[Id]",
           "config_path": "configs/agents/schema_editor_router.yaml"
         }'

Expected: JSON with success and a relationship id.

