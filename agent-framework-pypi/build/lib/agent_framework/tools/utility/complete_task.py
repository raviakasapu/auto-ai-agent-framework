"""Complete Task Tool - Signals task completion to the agent framework."""
from __future__ import annotations

from typing import Any, Dict

from pydantic import BaseModel, Field

from ...base import BaseTool


class CompleteTaskArgs(BaseModel):
    summary: str = Field(..., description="Brief summary of what was accomplished")
    final_result: str = Field(..., description="The final result to return to the user")


class CompleteTaskOutput(BaseModel):
    completed: bool
    summary: str
    final_result: str
    operation: str = Field("display_message", description="Structured operation for frontend handling.")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Structured payload sent to the frontend.")
    human_readable_summary: str = Field(..., description="Chat-friendly summary (mirrors return-to-user contract).")


class CompleteTaskTool(BaseTool):
    _name = "complete_task"
    _description = "Call this when the task is complete to return results to the user and stop execution."

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def args_schema(self):
        return CompleteTaskArgs

    @property
    def output_schema(self):
        return CompleteTaskOutput

    def execute(self, summary: str, final_result: str) -> dict:
        """Mark task as complete and return results."""
        summary_field = summary
        human_summary = summary or final_result
        payload_message = final_result or summary
        return CompleteTaskOutput(
            completed=True,
            summary=summary_field,
            final_result=final_result,
            payload={"message": payload_message},
            human_readable_summary=human_summary
        ).model_dump()
