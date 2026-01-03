"""
AI Agent Framework Tools - Generic Utility Tools

The framework includes only generic utility tools.
Domain-specific tools should be created in your application.

Example of creating a domain-specific tool:

    from agent_framework import BaseTool
    from pydantic import BaseModel
    
    class MyToolArgs(BaseModel):
        query: str
    
    class MyTool(BaseTool):
        @property
        def name(self): return "my_tool"
        
        @property
        def args_schema(self): return MyToolArgs
        
        def execute(self, **kwargs):
            return {"result": "success"}
"""

# Utility tools only - generic, domain-agnostic
from .utility import (
    MockSearchTool,
    CompleteTaskTool,
    CalculatorTool,
    MathQATool,
    GlobTool,
    GrepTool,
)

__all__ = [
    # Utility tools
    "MockSearchTool",
    "CompleteTaskTool",
    "CalculatorTool",
    "MathQATool",
    "GlobTool",
    "GrepTool",
]
