Power BI Domain Example
=======================

This section demonstrates how to use the Agent Framework for Power BI model management.
It serves as a **reference implementation** showing how to build domain-specific tools
on top of the generic framework library.

.. note::
   **Library Structure:**
   
   - Generic framework code lives in ``agent-framework-pypi/src/agent_framework/``
   - Power BI specific code is in ``bi_tools/``
   
   This separation allows the framework to be reused for other domains while keeping
   Power BI specific logic isolated.

Overview
--------

Use the framework to:

- Read and write Power BI Tabular Model Definition Language (TMDL)
- Manage model relationships via natural language
- Execute DAX and SQL operations
- Synchronize with external Knowledge Graph services

Key Components
--------------

**bi_tools/services/**
   - ``DataModelService`` - Central data model CRUD operations
   - ``KGDataModelService`` - Knowledge Graph backed service

**bi_tools/tools/**
   - ``column/`` - Column management tools
   - ``measure/`` - DAX measure tools
   - ``relationship/`` - Relationship tools
   - ``table/`` - Table operations
   - ``sql/`` - SQL query tools
   - ``partition/`` - Partition management
   - ``mquery/`` - M Query tools

.. toctree::
   :maxdepth: 1

   setup
   tools
   flows
   agent_structure
   tool_access_restriction
   kg_tools_alignment
   howto/index
