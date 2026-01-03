"""
GlobTool - Find files matching a pattern using glob syntax.
"""

from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field

from ...base import BaseTool


class GlobToolArgs(BaseModel):
    """Arguments for GlobTool."""
    pattern: str = Field(..., description="Glob pattern (e.g., '**/*.py', 'configs/**/*.yaml')")
    root_dir: Optional[str] = Field(None, description="Root directory to search from (default: current working directory)")
    recursive: bool = Field(True, description="Enable recursive search")


class GlobTool(BaseTool):
    """Find files matching a pattern using glob syntax."""
    
    @property
    def name(self) -> str:
        return "glob"
    
    @property
    def description(self) -> str:
        return "Find files matching a pattern using glob syntax. Supports recursive patterns with **."
    
    @property
    def args_schema(self) -> type[BaseModel]:
        return GlobToolArgs
    
    @property
    def output_schema(self) -> Optional[type[BaseModel]]:
        return None
    
    def execute(
        self,
        pattern: str,
        root_dir: Optional[str] = None,
        recursive: bool = True
    ) -> dict:
        """
        Execute glob search and return matching files.
        
        Args:
            pattern: Glob pattern (e.g., '**/*.py', '*.yaml')
            root_dir: Root directory to search from
            recursive: Enable recursive search
        
        Returns:
            Dict with matches and metadata
        """
        try:
            root = Path(root_dir) if root_dir else Path.cwd()
            
            # Normalize pattern for recursive search
            if recursive and "**" not in pattern:
                # Make pattern recursive if not already
                pattern = f"**/{pattern}"
            
            # Execute glob
            matches = list(root.glob(pattern))
            
            # Convert to relative paths
            relative_matches = [
                str(m.relative_to(root)) if m.is_relative_to(root) else str(m)
                for m in matches
            ]
            
            return {
                "success": True,
                "pattern": pattern,
                "root_dir": str(root),
                "matches": relative_matches,
                "count": len(relative_matches),
                "absolute_paths": [str(m) for m in matches]
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "pattern": pattern,
                "root_dir": str(root_dir) if root_dir else str(Path.cwd()),
                "matches": [],
                "count": 0
            }

