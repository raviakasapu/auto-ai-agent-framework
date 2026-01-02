Generate Manifest and Serve Docs
================================

Manifest
--------
.. code-block:: bash

   # from repo root
   python generate_manifest.py \
     --config configs/agents/schema_editor_router.yaml \
     --output docs/agent_manifest.json

Serve Docs
----------
.. code-block:: bash

   AGENT_MANIFEST_PATH=docs/agent_manifest.json \
   AGENT_DOCS_DIR=docs/sphinx/build/html \
   uvicorn docs_server.main:app --reload --port 8002

Open:

- Manifest: http://127.0.0.1:8002/
- Reference: http://127.0.0.1:8002/reference/

