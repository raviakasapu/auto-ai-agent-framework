AI Agent Framework Documentation
================================

The PyPI package no longer carries its own copy of the documentation.  
All authoritative guides live in the root ``docs_source/`` Sphinx project.

Quick link
----------

- Hosted Sphinx site: https://akasa-ai.github.io/agentic-framework/

Local build instructions
------------------------

.. code-block:: bash

   cd docs_source
   make html

Why consolidate?
----------------

Keeping a single Sphinx project avoids drift between repos, ensures every guide
is updated once, and keeps policy/memory/planner references in sync with code.

Package-specific notes (installation, changelog, etc.) now live directly in
``README.md`` and ``CHANGELOG.md`` at the project root.
