Write a TMDL File
=================

Use ``TMDLWriterTool`` to append or replace contents.

.. code-block:: python

   from deployment.factory import AgentFactory
   import asyncio

   async def main():
       agent = AgentFactory.create_from_yaml("configs/agents/schema_editor_router.yaml")
       out = await agent.run(
           tool="write_tmdl",
           args={
               "model_dir": "${MODEL_DIR}",
               "path": "model.tmdl",
               "content": "// appended by test\n"
           }
       )
       print(out)

   asyncio.run(main())

Warning: back up the model directory in CI to keep diffs clean.


