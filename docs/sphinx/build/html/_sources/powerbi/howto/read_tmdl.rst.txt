Read a TMDL File
================

Use ``TMDLReaderTool`` to read model files for inspection.

.. code-block:: python

   from deployment.factory import AgentFactory
   import asyncio

   async def main():
       agent = AgentFactory.create_from_yaml("configs/agents/schema_editor_router.yaml")
       text = await agent.run(tool="read_tmdl", args={"model_dir": "${MODEL_DIR}", "path": "relationships.tmdl"})
       print(text)

   asyncio.run(main())

Tip: use this to preview changes during testing.


