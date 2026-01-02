Power BI Setup (TMDL Model)
===========================

Goal
----
Point the Agent Framework to an unpacked Power BI model and enable tools to read/write TMDL and manage
relationships.

Model Directory
---------------
- The framework expects an unpacked PBIT/PBIX model directory with this structure::

    Model/
      ├─ tables/
      ├─ relationships.tmdl
      ├─ model.tmdl
      ├─ database.tmdl
      └─ cultures/

- This repo ships an example under ``pbit_data/Model`` you can use for testing.

Environment Variables
---------------------
Set the model directory for tools and examples::

    # from repo root
    export MODEL_DIR="/absolute/path/to/bi-report-migration/Tableau/Bi-Migrator-FE/pbit_data/Model"

Run Demo Server
---------------
Start the FastAPI demo that exposes an endpoint to run the agent::

    # optional; run from repo root
    uvicorn tests.simple_app:app --reload --port 8011

Then call it (example adds a relationship)::

    curl -s -X POST http://127.0.0.1:8011/run \
      -H 'Content-Type: application/json' \
      -d '{
            "task": "Create a relationship between \'SALES\'[CustomerId] and \'CUSTOMERS\'[Id]",
            "config_path": "configs/agents/schema_editor_router.yaml"
          }'

Docs Server
-----------
Generate the agent manifest and launch the docs UI::

    # from repo root
    python generate_manifest.py \
      --config configs/agents/schema_editor_router.yaml \
      --output docs/agent_manifest.json

    AGENT_MANIFEST_PATH=docs/agent_manifest.json \
    AGENT_DOCS_DIR=docs/sphinx/build/html \
    uvicorn docs_server.main:app --reload --port 8002

Open:

- Manifest: http://127.0.0.1:8002/
- Sphinx Reference: http://127.0.0.1:8002/reference/
