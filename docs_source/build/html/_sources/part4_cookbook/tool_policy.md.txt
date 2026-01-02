# Recipe: Tool Policy

Implement access control for tools.

## Goal

Control which tools can be executed based on context.

## HITL Policy

```python
from agent_framework.policies.base import HITLPolicy
from typing import Any, Dict, Tuple, Optional

class RoleBasedHITLPolicy(HITLPolicy):
    """Require approval based on user role and tool category."""
    
    def __init__(
        self,
        enabled: bool = True,
        admin_bypass: bool = True,
        write_tools: list = None,
        dangerous_tools: list = None,
    ):
        self.enabled = enabled
        self.admin_bypass = admin_bypass
        self.write_tools = set(write_tools or [
            "add_column", "update_column", "delete_column",
            "add_table", "delete_table",
        ])
        self.dangerous_tools = set(dangerous_tools or [
            "delete_database", "drop_schema", "execute_raw_sql",
        ])
    
    def requires_approval(
        self,
        action: Any,
        context: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        if not self.enabled:
            return False, None
        
        tool_name = getattr(action, "tool_name", str(action))
        user_role = context.get("user_role", "viewer")
        
        # Admin bypass
        if self.admin_bypass and user_role == "admin":
            return False, None
        
        # Dangerous tools always need approval
        if tool_name in self.dangerous_tools:
            return True, f"Tool '{tool_name}' requires admin approval"
        
        # Write tools need approval for non-editors
        if tool_name in self.write_tools and user_role not in ("admin", "editor"):
            return True, f"Tool '{tool_name}' requires editor role"
        
        return False, None
```

## Policy Engine Integration

```python
from agent_framework.services.policy import PolicyEngine

class CustomPolicyEngine:
    """Custom policy engine with deny rules."""
    
    def __init__(self, deny_rules: list = None):
        self.deny_rules = deny_rules or []
    
    def check_action(
        self,
        tool_name: str,
        args: dict,
        context: dict
    ) -> Tuple[bool, Optional[str]]:
        for rule in self.deny_rules:
            if self._matches_rule(tool_name, args, context, rule):
                return False, rule.get("message", "Action denied by policy")
        return True, None
    
    def _matches_rule(self, tool_name, args, context, rule) -> bool:
        # Match tool pattern
        tool_pattern = rule.get("tool", "*")
        if tool_pattern != "*" and not self._pattern_match(tool_pattern, tool_name):
            return False
        
        # Match role
        role_pattern = rule.get("role", "*")
        user_role = context.get("user_role", "anonymous")
        if role_pattern != "*" and user_role != role_pattern:
            return False
        
        return True
    
    def _pattern_match(self, pattern: str, value: str) -> bool:
        if pattern.endswith("*"):
            return value.startswith(pattern[:-1])
        return pattern == value

# Usage
engine = CustomPolicyEngine(deny_rules=[
    {"tool": "delete_*", "role": "viewer", "message": "Viewers cannot delete"},
    {"tool": "execute_raw_sql", "role": "*", "message": "Raw SQL is disabled"},
])
```

## Using with Agent

```python
from agent_framework import Agent, get_preset
from agent_framework.policies.default import DefaultHITLPolicy

# Custom HITL
custom_hitl = RoleBasedHITLPolicy(
    enabled=True,
    write_tools=["add_column", "delete_column"],
    dangerous_tools=["execute_raw_sql"],
)

# Get preset and override HITL
policies = get_preset("simple")
policies["hitl"] = custom_hitl

agent = Agent(
    planner=planner,
    memory=memory,
    tools=tools,
    policies=policies,
)

# Set context with user role
from agent_framework.services.request_context import set_request_context
set_request_context({"user_role": "viewer"})

# This will require approval for write tools
result = await agent.run("Add column 'email' to users table")
```

## YAML Configuration

```yaml
policies:
  hitl:
    type: RoleBasedHITLPolicy
    config:
      enabled: true
      admin_bypass: true
      write_tools:
        - add_column
        - delete_column
        - update_column
      dangerous_tools:
        - execute_raw_sql
        - drop_table
```

## Key Points

- Inherit from `HITLPolicy` for HITL integration
- Return `(needs_approval: bool, reason: Optional[str])`
- Check context for user role/permissions
- Configure tool categories (write, dangerous)
- Register for YAML usage

