"""
GrepTool - Search for text patterns in files using regex.
"""

import re
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field

from ...base import BaseTool


class GrepToolArgs(BaseModel):
    """Arguments for GrepTool."""
    pattern: str = Field(..., description="Regex pattern to search for")
    files: List[str] = Field(..., description="List of file paths to search")
    case_sensitive: bool = Field(False, description="Case-sensitive search")
    include_line_numbers: bool = Field(True, description="Include line numbers in results")
    context_lines: int = Field(0, description="Number of context lines before/after match")


class GrepTool(BaseTool):
    """Search for text patterns in files using regex."""
    
    @property
    def name(self) -> str:
        return "grep"
    
    @property
    def description(self) -> str:
        return "Search for text patterns in files using regex. Returns matches with line numbers and optional context."
    
    @property
    def args_schema(self) -> type[BaseModel]:
        return GrepToolArgs
    
    @property
    def output_schema(self) -> Optional[type[BaseModel]]:
        return None
    
    def execute(
        self,
        pattern: str,
        files: List[str],
        case_sensitive: bool = False,
        include_line_numbers: bool = True,
        context_lines: int = 0
    ) -> dict:
        """
        Execute grep search and return matches.
        
        Args:
            pattern: Regex pattern to search for
            files: List of file paths to search
            case_sensitive: Case-sensitive search
            include_line_numbers: Include line numbers in results
            context_lines: Number of context lines before/after match
        
        Returns:
            Dict with matches and metadata
        """
        regex_flags = 0 if case_sensitive else re.IGNORECASE
        try:
            regex = re.compile(pattern, regex_flags)
        except re.error as e:
            return {
                "success": False,
                "error": f"Invalid regex pattern: {e}",
                "pattern": pattern,
                "files_searched": 0,
                "results": []
            }
        
        matches = []
        files_with_matches = 0
        total_matches = 0
        
        for file_path in files:
            path = Path(file_path)
            if not path.exists():
                matches.append({
                    "file": str(path),
                    "error": "File not found"
                })
                continue
            
            if not path.is_file():
                matches.append({
                    "file": str(path),
                    "error": "Path is not a file"
                })
                continue
            
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                
                file_matches = []
                for i, line in enumerate(lines, 1):
                    match_obj = regex.search(line)
                    if match_obj:
                        match_info = {
                            "line": line.rstrip('\n\r'),
                            "match": match_obj.group()
                        }
                        
                        if include_line_numbers:
                            match_info["line_number"] = i
                        
                        # Add context if requested
                        if context_lines > 0:
                            start = max(0, i - context_lines - 1)
                            end = min(len(lines), i + context_lines)
                            match_info["context"] = [
                                {
                                    "line": j + 1,
                                    "content": lines[j].rstrip('\n\r')
                                }
                                for j in range(start, end)
                            ]
                        
                        file_matches.append(match_info)
                        total_matches += 1
                
                if file_matches:
                    matches.append({
                        "file": str(path),
                        "matches": file_matches,
                        "count": len(file_matches)
                    })
                    files_with_matches += 1
            except Exception as e:
                matches.append({
                    "file": str(path),
                    "error": str(e)
                })
        
        return {
            "success": True,
            "pattern": pattern,
            "files_searched": len(files),
            "files_with_matches": files_with_matches,
            "total_matches": total_matches,
            "results": matches
        }

