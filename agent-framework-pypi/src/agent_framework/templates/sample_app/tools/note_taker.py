"""
Note Taker Tool - Creates and stores notes.

Demonstrates a simple write tool with persistent storage.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field

from agent_framework.base import BaseTool


class NoteTakerArgs(BaseModel):
    """Arguments for creating a note."""
    title: str = Field(..., description="Title of the note")
    content: str = Field(..., description="Content of the note")
    tags: Optional[List[str]] = Field(None, description="Optional tags for categorization")


class NoteTakerOutput(BaseModel):
    """Output from creating a note."""
    success: bool
    note_id: str
    title: str
    message: str
    created_at: str


class NoteTakerTool(BaseTool):
    """
    Tool for creating and storing notes.

    This is a write tool that demonstrates:
    - Pydantic schema for inputs/outputs
    - Persistent storage (JSON file)
    - Timestamping and ID generation
    """

    _name = "note_taker"
    _description = "Create and store a note with a title, content, and optional tags."

    def __init__(self, storage_path: Optional[str] = None) -> None:
        self._storage_path = Path(storage_path) if storage_path else Path("notes.json")
        self._notes: Dict[str, Dict[str, Any]] = {}
        self._load_notes()

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def args_schema(self):
        return NoteTakerArgs

    @property
    def output_schema(self):
        return NoteTakerOutput

    def _load_notes(self) -> None:
        """Load notes from storage file."""
        if self._storage_path.exists():
            try:
                self._notes = json.loads(self._storage_path.read_text())
            except Exception:
                self._notes = {}

    def _save_notes(self) -> None:
        """Save notes to storage file."""
        self._storage_path.write_text(json.dumps(self._notes, indent=2))

    def _generate_id(self) -> str:
        """Generate a unique note ID."""
        import uuid
        return f"note_{uuid.uuid4().hex[:8]}"

    def execute(
        self,
        title: str,
        content: str,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Create a new note."""
        note_id = self._generate_id()
        created_at = datetime.now().isoformat()

        note = {
            "id": note_id,
            "title": title,
            "content": content,
            "tags": tags or [],
            "created_at": created_at,
        }

        self._notes[note_id] = note
        self._save_notes()

        output = NoteTakerOutput(
            success=True,
            note_id=note_id,
            title=title,
            message=f"Note '{title}' created successfully.",
            created_at=created_at,
        )
        return output.model_dump()
