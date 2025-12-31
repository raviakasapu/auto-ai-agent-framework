"""
Sample Tools for the AI Agent Framework Demo.

These tools demonstrate how to create domain-specific tools
that integrate with the framework's planner and agent system.
"""

from .note_taker import NoteTakerTool
from .task_manager import TaskManagerTool, ListTasksTool, CompleteTaskTool
from .weather import WeatherLookupTool
from .search import MockSearchTool

__all__ = [
    "NoteTakerTool",
    "TaskManagerTool",
    "ListTasksTool",
    "CompleteTaskTool",
    "WeatherLookupTool",
    "MockSearchTool",
]
