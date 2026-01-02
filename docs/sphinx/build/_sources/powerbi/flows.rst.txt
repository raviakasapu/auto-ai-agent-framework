Power BI Agent Flows
====================

Chat‑Driven Relationship Creation
---------------------------------
1. User: "Create a relationship between ``'SALES'[CustomerId]`` and ``'CUSTOMERS'[Id]``"
2. Planner: LLMRouterPlanner selects ``AddRelationshipTool``
3. Tool: validates tables/columns, appends a block to ``Model/relationships.tmdl``
4. Result: JSON with ``success``, ``relationship_id``

Update an Existing Relationship
-------------------------------
1. User: "Deactivate relationship id: ``abc123``"
2. Planner: Routes to ``UpdateRelationshipTool`` with parsed args
3. Tool: modifies relationship properties and writes back to TMDL
4. Result: JSON with change summary

Read/Write TMDL Directly
------------------------
- ``TMDLReaderTool``: read any TMDL file for inspection in the UI or logs
- ``TMDLWriterTool``: append/replace content when performing advanced operations

End‑to‑End via API
------------------
Use the demo server to send tasks to the agent::

   curl -s -X POST http://127.0.0.1:8011/run \
     -H 'Content-Type: application/json' \
     -d '{
           "task": "Update relationship xyz789 to use bothDirections filtering",
           "config_path": "configs/agents/schema_editor_router.yaml"
         }'

