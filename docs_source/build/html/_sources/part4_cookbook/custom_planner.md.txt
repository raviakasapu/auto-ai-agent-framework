# Recipe: Custom Planner

Create a custom planner for specialized decision-making.

## Goal

Create a planner that routes tasks based on domain-specific rules.

## Implementation

```python
from agent_framework import BasePlanner, Action, FinalResponse
from typing import List, Dict, Any, Union

class PriorityPlanner(BasePlanner):
    """Routes tasks based on priority keywords."""
    
    def __init__(
        self,
        high_priority_tool: str,
        normal_tool: str,
        chat_tool: str = None,
    ):
        self.high_priority_tool = high_priority_tool
        self.normal_tool = normal_tool
        self.chat_tool = chat_tool
        
        self.priority_keywords = ["urgent", "critical", "asap", "emergency"]
        self.chat_keywords = ["hello", "hi", "help", "what is"]
    
    def plan(
        self,
        task_description: str,
        history: List[Dict[str, Any]]
    ) -> Union[Action, List[Action], FinalResponse]:
        task_lower = task_description.lower()
        
        # Check for chat/greeting
        if self.chat_tool and any(kw in task_lower for kw in self.chat_keywords):
            return Action(
                tool_name=self.chat_tool,
                tool_args={"message": task_description}
            )
        
        # Check for priority
        is_priority = any(kw in task_lower for kw in self.priority_keywords)
        
        if is_priority:
            return Action(
                tool_name=self.high_priority_tool,
                tool_args={
                    "task": task_description,
                    "priority": "high"
                }
            )
        
        return Action(
            tool_name=self.normal_tool,
            tool_args={"task": task_description}
        )
```

## Registration

```python
from deployment.registry import register_planner

register_planner("PriorityPlanner", PriorityPlanner)
```

## YAML Usage

```yaml
spec:
  planner:
    type: PriorityPlanner
    config:
      high_priority_tool: urgent_processor
      normal_tool: standard_processor
      chat_tool: chat_responder
```

## Testing

```python
import pytest
from my_planners import PriorityPlanner

def test_priority_routing():
    planner = PriorityPlanner(
        high_priority_tool="urgent",
        normal_tool="normal",
    )
    
    # High priority
    action = planner.plan("URGENT: Process this now", [])
    assert action.tool_name == "urgent"
    assert action.tool_args["priority"] == "high"
    
    # Normal priority
    action = planner.plan("Process this when you can", [])
    assert action.tool_name == "normal"
```

## Key Points

- Inherit from `BasePlanner`
- Return `Action`, `List[Action]`, or `FinalResponse`
- Register for YAML usage
- Keep logic simple and testable

