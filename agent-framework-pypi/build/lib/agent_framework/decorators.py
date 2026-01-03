"""
Tool Decorator - Simplify tool creation with a decorator pattern.

This module provides a ``@tool`` decorator that converts regular Python
functions into framework-compatible tools with automatic schema generation.

Example::

    from agent_framework import tool

    @tool(name="add_numbers", description="Add two numbers together")
    def add(a: int, b: int) -> int:
        \"\"\"Add two numbers and return the sum.\"\"\"
        return a + b

    # Or with minimal configuration (uses function name and docstring)
    @tool
    def multiply(x: float, y: float) -> float:
        \"\"\"Multiply two numbers and return the product.\"\"\"
        return x * y
"""
from __future__ import annotations

import inspect
from functools import wraps
from typing import Any, Callable, Dict, Optional, Type, Union, get_type_hints

from pydantic import BaseModel, Field, create_model

from agent_framework.base import BaseTool


class FunctionalTool(BaseTool):
    """
    A tool implementation that wraps a regular Python function.
    
    This is used internally by the @tool decorator to create BaseTool-compatible
    instances from decorated functions.
    """
    
    def __init__(
        self,
        func: Callable[..., Any],
        name: Optional[str] = None,
        description: Optional[str] = None,
        args_schema: Optional[Type[BaseModel]] = None,
        output_schema: Optional[Type[BaseModel]] = None,
    ):
        self._func = func
        self._name = name or func.__name__
        self._description = description or func.__doc__ or f"Execute {self._name}"
        self._args_schema = args_schema or self._generate_args_schema(func)
        self._output_schema = output_schema
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def description(self) -> str:
        return self._description
    
    @property
    def args_schema(self) -> Type[BaseModel]:
        return self._args_schema
    
    @property
    def output_schema(self) -> Optional[Type[BaseModel]]:
        return self._output_schema
    
    def execute(self, **kwargs) -> Any:
        """Execute the wrapped function with validated arguments."""
        # Validate args through the schema
        validated = self._args_schema(**kwargs)
        # Extract values as dict and call the function
        return self._func(**validated.model_dump())
    
    def _generate_args_schema(self, func: Callable[..., Any]) -> Type[BaseModel]:
        """
        Generate a Pydantic model from function signature and type hints.
        
        Handles:
        - Type annotations for each parameter
        - Default values
        - Docstring parameter descriptions (Google/NumPy style)
        """
        sig = inspect.signature(func)
        
        # Try to get type hints (may fail for some edge cases)
        try:
            hints = get_type_hints(func)
        except Exception:
            hints = {}
        
        # Parse docstring for parameter descriptions
        param_descriptions = self._parse_docstring_params(func.__doc__ or "")
        
        # Build field definitions for Pydantic model
        field_definitions: Dict[str, Any] = {}
        
        for param_name, param in sig.parameters.items():
            # Skip *args and **kwargs
            if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
                continue
            
            # Get type annotation (default to Any)
            param_type = hints.get(param_name, Any)
            
            # Get default value
            if param.default is inspect.Parameter.empty:
                # Required field
                default = ...
            else:
                default = param.default
            
            # Get description from docstring
            field_desc = param_descriptions.get(param_name, f"Parameter {param_name}")
            
            # Create field definition: (type, default_or_field)
            if default is ...:
                field_definitions[param_name] = (param_type, Field(..., description=field_desc))
            else:
                field_definitions[param_name] = (param_type, Field(default=default, description=field_desc))
        
        # Create dynamic Pydantic model
        model_name = f"{self._name.title().replace('_', '')}Args"
        return create_model(model_name, **field_definitions)
    
    def _parse_docstring_params(self, docstring: str) -> Dict[str, str]:
        """
        Parse parameter descriptions from a docstring.
        
        Supports simple patterns like:
        - Google style: `arg_name: Description here`
        - NumPy style: `arg_name : type\n    Description here`
        """
        descriptions: Dict[str, str] = {}
        
        if not docstring:
            return descriptions
        
        lines = docstring.split('\n')
        current_param = None
        current_desc = []
        
        for line in lines:
            stripped = line.strip()
            
            # Check for parameter definition patterns
            # Google style: "param_name: description" or "param_name (type): description"
            if ':' in stripped and not stripped.startswith(':'):
                parts = stripped.split(':', 1)
                param_part = parts[0].strip()
                desc_part = parts[1].strip() if len(parts) > 1 else ""
                
                # Extract param name (remove type annotation in parentheses)
                if '(' in param_part:
                    param_name = param_part.split('(')[0].strip()
                else:
                    param_name = param_part
                
                # Check if it looks like a parameter name (simple identifier)
                if param_name.isidentifier() and not param_name in ('Args', 'Returns', 'Raises', 'Example', 'Note'):
                    if current_param:
                        descriptions[current_param] = ' '.join(current_desc).strip()
                    current_param = param_name
                    current_desc = [desc_part] if desc_part else []
                    continue
            
            # Continuation of current parameter description
            if current_param and stripped and not stripped.endswith(':'):
                current_desc.append(stripped)
        
        # Don't forget the last parameter
        if current_param:
            descriptions[current_param] = ' '.join(current_desc).strip()
        
        return descriptions
    
    def __call__(self, **kwargs) -> Any:
        """Allow the tool to be called directly like a function."""
        return self.execute(**kwargs)
    
    def __repr__(self) -> str:
        return f"<FunctionalTool name={self._name!r}>"


def tool(
    func: Optional[Callable[..., Any]] = None,
    *,
    name: Optional[str] = None,
    description: Optional[str] = None,
    args_schema: Optional[Type[BaseModel]] = None,
    output_schema: Optional[Type[BaseModel]] = None,
) -> Union[FunctionalTool, Callable[[Callable[..., Any]], FunctionalTool]]:
    """
    Decorator to convert a Python function into a framework-compatible tool.
    
    The decorator automatically:
    - Generates an args_schema from function type hints
    - Uses the function's docstring as the description
    - Creates a BaseTool-compatible instance
    
    Can be used with or without parentheses::

        @tool
        def my_func(x: int) -> int:
            \"\"\"My description.\"\"\"
            return x * 2

        @tool(name="custom_name", description="Custom description")
        def another_func(x: int) -> int:
            return x * 3
    
    Args:
        func: The function to wrap (when used without parentheses)
        name: Optional custom name for the tool (defaults to function name)
        description: Optional description (defaults to function docstring)
        args_schema: Optional custom Pydantic model for arguments
        output_schema: Optional Pydantic model for output validation
    
    Returns:
        FunctionalTool instance that implements BaseTool interface
    
    Example::

        from agent_framework import tool
        from pydantic import BaseModel

        # Simple usage - auto-generates everything
        @tool
        def greet(name: str, formal: bool = False) -> str:
            \"\"\"Generate a greeting message.

            name: The name of the person to greet
            formal: Whether to use formal greeting
            \"\"\"
            if formal:
                return f"Good day, {name}."
            return f"Hello, {name}!"

        # Usage with custom schema
        class CalculatorArgs(BaseModel):
            a: float
            b: float
            operation: str = "add"

        @tool(name="calculator", args_schema=CalculatorArgs)
        def calc(a: float, b: float, operation: str = "add") -> float:
            \"\"\"Perform basic arithmetic operations.\"\"\"
            ops = {"add": a + b, "sub": a - b, "mul": a * b, "div": a / b}
            return ops.get(operation, a + b)

        # The tool can now be used with the agent framework
        result = greet.execute(name="Alice", formal=True)
        # Or called directly:
        result = greet(name="Bob")
    """
    def decorator(fn: Callable[..., Any]) -> FunctionalTool:
        return FunctionalTool(
            func=fn,
            name=name,
            description=description,
            args_schema=args_schema,
            output_schema=output_schema,
        )
    
    # Handle both @tool and @tool(...) syntax
    if func is not None:
        # Called without parentheses: @tool
        return decorator(func)
    else:
        # Called with parentheses: @tool(...) 
        return decorator
