"""Pydantic models describing manager-generated execution scripts."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ScriptStep(BaseModel):
    name: str = Field(..., description="Human-readable step name")
    worker: str = Field(..., description="Manager worker key (e.g., model-structure-editor)")
    tool_name: str = Field(..., description="Tool name to execute within the worker")
    args: Dict[str, Any] = Field(default_factory=dict, description="Tool arguments")
    notes: Optional[str] = Field(None, description="Optional context for the worker")
    execution_mode: str = Field(
        ...,
        description="Execution mode hint: 'direct' for deterministic execution, 'guided' for delegated reasoning.",
        pattern="^(direct|guided)$",
    )


class ScriptPlan(BaseModel):
    thought: str = Field(..., description="Manager reasoning for script order")
    script: List[ScriptStep] = Field(..., description="Ordered tool calls")
