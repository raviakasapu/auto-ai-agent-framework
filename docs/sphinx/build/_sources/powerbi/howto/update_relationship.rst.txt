Update a Relationship
=====================

Deactivate / Activate
---------------------
.. code-block:: bash

   curl -s -X POST http://127.0.0.1:8011/run \
     -H 'Content-Type: application/json' \
     -d '{
           "task": "Deactivate relationship id: abc123",
           "config_path": "configs/agents/schema_editor_router.yaml"
         }'

Change Cardinality or Filter Direction
--------------------------------------
.. code-block:: bash

   curl -s -X POST http://127.0.0.1:8011/run \
     -H 'Content-Type: application/json' \
     -d '{
           "task": "Update relationship abc123 to use bothDirections filtering",
           "config_path": "configs/agents/schema_editor_router.yaml"
         }'

Notes
-----
- The tool validates the id exists and writes changes back to ``relationships.tmdl``.

