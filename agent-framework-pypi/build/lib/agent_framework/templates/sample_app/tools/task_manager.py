"""
Task Manager Tools - Create, list, and complete tasks.

Demonstrates multiple tools sharing state and CRUD operations.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field

from agent_framework.base import BaseTool


# Shared task storage (module-level singleton for demo)
_TASK_STORAGE: Dict[str, Dict[str, Any]] = {}
_STORAGE_PATH = Path("tasks.json")


def _load_tasks() -> Dict[str, Dict[str, Any]]:
    """Load tasks from storage."""
    global _TASK_STORAGE
    if _STORAGE_PATH.exists():
        try:
            _TASK_STORAGE = json.loads(_STORAGE_PATH.read_text())
        except Exception:
            _TASK_STORAGE = {}
    return _TASK_STORAGE


def _save_tasks() -> None:
    """Save tasks to storage."""
    _STORAGE_PATH.write_text(json.dumps(_TASK_STORAGE, indent=2))


# ============================================================================
# Create Task Tool
# ============================================================================

class TaskManagerArgs(BaseModel):
    """Arguments for creating a task."""
    title: str = Field(..., description="Title of the task")
    description: Optional[str] = Field(None, description="Detailed description of the task")
    priority: str = Field("medium", description="Priority: low, medium, high")
    due_date: Optional[str] = Field(None, description="Due date in YYYY-MM-DD format")


class TaskManagerOutput(BaseModel):
    """Output from creating a task."""
    success: bool
    task_id: str
    title: str
    priority: str
    message: str


class TaskManagerTool(BaseTool):
    """
    Tool for creating tasks.

    Demonstrates:
    - Write tool with validation
    - Priority levels
    - Due date handling
    """

    _name = "create_task"
    _description = "Create a new task with title, description, priority (low/medium/high), and optional due date."

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def args_schema(self):
        return TaskManagerArgs

    @property
    def output_schema(self):
        return TaskManagerOutput

    def execute(
        self,
        title: str,
        description: Optional[str] = None,
        priority: str = "medium",
        due_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new task."""
        _load_tasks()

        # Validate priority
        priority = priority.lower()
        if priority not in ("low", "medium", "high"):
            priority = "medium"

        # Generate ID
        import uuid
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        created_at = datetime.now().isoformat()

        task = {
            "id": task_id,
            "title": title,
            "description": description or "",
            "priority": priority,
            "due_date": due_date,
            "status": "pending",
            "created_at": created_at,
            "completed_at": None,
        }

        _TASK_STORAGE[task_id] = task
        _save_tasks()

        output = TaskManagerOutput(
            success=True,
            task_id=task_id,
            title=title,
            priority=priority,
            message=f"Task '{title}' created with {priority} priority.",
        )
        return output.model_dump()


# ============================================================================
# List Tasks Tool
# ============================================================================

class ListTasksArgs(BaseModel):
    """Arguments for listing tasks."""
    status: Optional[str] = Field(None, description="Filter by status: pending, completed, all")
    priority: Optional[str] = Field(None, description="Filter by priority: low, medium, high")


class ListTasksOutput(BaseModel):
    """Output from listing tasks."""
    total_count: int
    tasks: List[Dict[str, Any]]
    message: str


class ListTasksTool(BaseTool):
    """
    Tool for listing tasks with optional filters.

    Demonstrates:
    - Read-only tool
    - Filtering and querying
    """

    _name = "list_tasks"
    _description = "List all tasks with optional filters for status (pending/completed/all) and priority (low/medium/high)."

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def args_schema(self):
        return ListTasksArgs

    @property
    def output_schema(self):
        return ListTasksOutput

    def execute(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List tasks with optional filters."""
        _load_tasks()

        tasks = list(_TASK_STORAGE.values())

        # Apply filters
        if status and status != "all":
            tasks = [t for t in tasks if t.get("status") == status]
        if priority:
            tasks = [t for t in tasks if t.get("priority") == priority.lower()]

        # Sort by priority (high > medium > low) then by created_at
        priority_order = {"high": 0, "medium": 1, "low": 2}
        tasks.sort(key=lambda t: (priority_order.get(t.get("priority", "medium"), 1), t.get("created_at", "")))

        output = ListTasksOutput(
            total_count=len(tasks),
            tasks=tasks,
            message=f"Found {len(tasks)} task(s).",
        )
        return output.model_dump()


# ============================================================================
# Complete Task Tool
# ============================================================================

class CompleteTaskArgs(BaseModel):
    """Arguments for completing a task."""
    task_id: str = Field(..., description="ID of the task to complete")


class CompleteTaskOutput(BaseModel):
    """Output from completing a task."""
    success: bool
    task_id: str
    title: str
    message: str


class CompleteTaskTool(BaseTool):
    """
    Tool for marking a task as completed.

    Demonstrates:
    - Update operation
    - Error handling for missing items
    """

    _name = "complete_task"
    _description = "Mark a task as completed by its task_id."

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

    def execute(self, task_id: str) -> Dict[str, Any]:
        """Mark a task as completed."""
        _load_tasks()

        if task_id not in _TASK_STORAGE:
            return CompleteTaskOutput(
                success=False,
                task_id=task_id,
                title="",
                message=f"Task '{task_id}' not found.",
            ).model_dump()

        task = _TASK_STORAGE[task_id]
        task["status"] = "completed"
        task["completed_at"] = datetime.now().isoformat()
        _save_tasks()

        return CompleteTaskOutput(
            success=True,
            task_id=task_id,
            title=task["title"],
            message=f"Task '{task['title']}' marked as completed.",
        ).model_dump()
