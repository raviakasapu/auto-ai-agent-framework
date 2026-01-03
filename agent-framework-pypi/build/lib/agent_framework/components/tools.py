"""
DEPRECATED: Legacy monolithic tools file.

All tools have been refactored into modular structure under framework/tools/.
This file re-exports them for backward compatibility with existing tests.

For new code, import from agent_framework.tools directly:
    from agent_framework.tools.relationship import AddRelationshipTool
    from agent_framework.tools.column import ListColumnsTool
    etc.
"""

# Re-export all tools from modular structure for backward compatibility
from agent_framework.tools.relationship import (
    AddRelationshipTool,
    UpdateRelationshipTool,
    RemoveRelationshipTool,
    ListRelationshipsTool,
    ValidateRelationshipTool,
    CleanupRelationshipFormatTool,
)

from agent_framework.tools.table import ListTablesTool, AddTableTool

from agent_framework.tools.column import (
    AddColumnTool,
    RemoveColumnTool,
    RenameColumnTool,
    ListColumnsTool,
    ListCalculatedColumnsTool,
)

from agent_framework.tools.measure import (
    AddMeasureTool,
    RemoveMeasureTool,
    ListMeasuresTool,
)

from agent_framework.tools.tmdl import (
    TMDLReaderTool,
    TMDLWriterTool,
    TMDLValidateTool,
)

from agent_framework.tools.utility import (
    MockSearchTool,
    CompleteTaskTool,
    CalculatorTool,
    MathQATool,
)

__all__ = [
    # Relationship tools
    "AddRelationshipTool",
    "UpdateRelationshipTool",
    "RemoveRelationshipTool",
    "ListRelationshipsTool",
    "ValidateRelationshipTool",
    "CleanupRelationshipFormatTool",
    # Table tools
    "ListTablesTool",
    "AddTableTool",
    # Column tools
    "AddColumnTool",
    "RemoveColumnTool",
    "RenameColumnTool",
    "ListColumnsTool",
    "ListCalculatedColumnsTool",
    # Measure tools
    "AddMeasureTool",
    "RemoveMeasureTool",
    "ListMeasuresTool",
    # TMDL tools
    "TMDLReaderTool",
    "TMDLWriterTool",
    "TMDLValidateTool",
    # Utility tools
    "MockSearchTool",
    "CompleteTaskTool",
    "CalculatorTool",
    "MathQATool",
]
