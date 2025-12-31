"""
Mock Search Tool - Simulates web search results.

Demonstrates a read-only research tool.
"""
from __future__ import annotations

from typing import Dict, Any, List

from pydantic import BaseModel, Field

from agent_framework.base import BaseTool


class MockSearchArgs(BaseModel):
    """Arguments for search."""
    query: str = Field(..., description="Search query")
    max_results: int = Field(5, description="Maximum number of results to return")


class SearchResult(BaseModel):
    """A single search result."""
    title: str
    url: str
    snippet: str


class MockSearchOutput(BaseModel):
    """Output from search."""
    query: str
    total_results: int
    results: List[SearchResult]


class MockSearchTool(BaseTool):
    """
    Mock search tool for demonstration.

    Demonstrates:
    - List output with nested objects
    - Query processing
    - Simulated external service
    """

    _name = "web_search"
    _description = "Search the web for information. Returns a list of relevant results with titles, URLs, and snippets."

    # Mock search results database
    _MOCK_RESULTS = {
        "python": [
            SearchResult(
                title="Python.org - Official Website",
                url="https://python.org",
                snippet="Python is a programming language that lets you work quickly and integrate systems effectively."
            ),
            SearchResult(
                title="Python Tutorial - W3Schools",
                url="https://w3schools.com/python",
                snippet="Learn Python programming with tutorials and examples. Python is easy to learn."
            ),
            SearchResult(
                title="Python Documentation",
                url="https://docs.python.org",
                snippet="Official Python documentation with library reference and language specification."
            ),
        ],
        "machine learning": [
            SearchResult(
                title="Machine Learning - Wikipedia",
                url="https://wikipedia.org/wiki/Machine_learning",
                snippet="Machine learning is a branch of AI that enables systems to learn from data."
            ),
            SearchResult(
                title="Machine Learning Course - Coursera",
                url="https://coursera.org/ml",
                snippet="Stanford's machine learning course by Andrew Ng. Learn supervised and unsupervised learning."
            ),
        ],
        "ai agent": [
            SearchResult(
                title="AI Agents Explained",
                url="https://example.com/ai-agents",
                snippet="AI agents are autonomous systems that perceive their environment and take actions."
            ),
            SearchResult(
                title="Building AI Agents with LLMs",
                url="https://example.com/llm-agents",
                snippet="Learn how to build AI agents using large language models and the ReAct pattern."
            ),
        ],
    }

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

    def execute(
        self,
        query: str,
        max_results: int = 5,
    ) -> Dict[str, Any]:
        """Perform mock search."""
        query_lower = query.lower()

        # Find matching results
        results: List[SearchResult] = []

        for key, key_results in self._MOCK_RESULTS.items():
            if key in query_lower:
                results.extend(key_results)

        # If no specific matches, return generic results
        if not results:
            results = [
                SearchResult(
                    title=f"Search results for: {query}",
                    url=f"https://search.example.com?q={query.replace(' ', '+')}",
                    snippet=f"Found various results related to '{query}'. Click to explore more."
                ),
                SearchResult(
                    title=f"Learn more about {query}",
                    url=f"https://learn.example.com/{query.replace(' ', '-')}",
                    snippet=f"Comprehensive guide and resources about {query}."
                ),
            ]

        # Limit results
        results = results[:max_results]

        output = MockSearchOutput(
            query=query,
            total_results=len(results),
            results=results,
        )
        return output.model_dump()
