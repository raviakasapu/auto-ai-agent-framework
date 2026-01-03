"""Mock Search Tool - Returns canned search responses for testing."""
from __future__ import annotations

from pydantic import BaseModel, Field

from ...base import BaseTool


class MockSearchArgs(BaseModel):
    query: str = Field(..., description="The search query to look up.")
    region: str = Field("us-en", description="Locale/region for the mock search.")


class MockSearchOutput(BaseModel):
    summary: str = Field(..., description="High-level textual summary of results.")
    query: str = Field(..., description="Echo of the input query.")
    region: str = Field(..., description="Echo of the search region used.")


class MockSearchTool(BaseTool):
    _name = "mock_search"
    _description = "Returns a canned response for a given query."

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def args_schema(self):
        return MockSearchArgs

    @property
    def output_schema(self):
        return MockSearchOutput

    def execute(self, query: str, region: str = "us-en") -> dict:
        out = MockSearchOutput(
            summary="Mock search result: AI Agents are modular frameworks.",
            query=query,
            region=region,
        )
        return out.model_dump()


