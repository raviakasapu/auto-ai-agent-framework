---
title: Tool Choice Mechanism
---

# Tool Choice Mechanism: How Agents Select Tools

## Overview

This guide explains how the framework's `ReActPlanner` enables LLM agents to decide which tools to call. The process involves multiple layers: tool descriptions, system prompts, OpenAI function calling, and LLM reasoning.

## Architecture Flow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Tool Descriptions (YAML Config)                          │
│    - name: "search_database"                                │
│    - description: "Search the database for records..."       │
│    - args: ["query", "limit"]                                │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Tools Schema Builder (ReActPlanner)                      │
│    - Converts descriptions to OpenAI function schema         │
│    - Includes parameter types, required fields               │
│    - Uses Pydantic schemas if tool objects available        │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. System Prompt + Context                                   │
│    - System prompt: "You are a data analysis specialist..." │
│    - Strategic plan (if available)                           │
│    - Task description                                        │
│    - History (previous actions/observations)                 │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. OpenAI Function Calling API (OpenAIGateway)               │
│    - Receives: messages, tools schema, tool_choice           │
│    - LLM reasons about which tool(s) to call                 │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. LLM Response                                              │
│    - Returns: tool_calls array with selected tools           │
│    - Each tool_call includes: name, arguments                │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. Planner Converts to Actions (ReActPlanner)               │
│    - Converts tool_calls to Action objects                   │
│    - Truncates if exceeding max_parallel_tool_calls         │
└─────────────────────────────────────────────────────────────┘
```

## Step-by-Step Process

### Step 1: Tool Descriptions Configuration

Tool descriptions are provided in the agent's YAML configuration:

```yaml
spec:
  planner:
    type: ReActPlanner
    config:
      tool_descriptions:
        - name: search_database
          description: "Search the database for records matching a query."
          args: ["query", "limit"]
        - name: get_record_details
          description: "Get detailed information about a specific record by ID."
          args: ["record_id"]
        - name: analyze_data
          description: "Analyze data and return statistical summary."
          args: ["data", "analysis_type"]
```

**Key Elements:**
- **name**: Tool identifier (must match tool registry)
- **description**: Natural language description that LLM uses to understand tool purpose
- **args**: Parameter names (help LLM understand what arguments are needed)

### Step 2: Building Tools Schema

The `ReActPlanner` converts tool descriptions into OpenAI function calling schema via `_build_tools_schema()`:

**If tool objects are available** (with Pydantic schemas):
```python
# Uses tool.args_schema.model_json_schema() for accurate types
tools_schema.append({
    "type": "function",
    "function": {
        "name": desc["name"],
        "description": desc["description"],
        "parameters": {
            "type": "object",
            "properties": schema["properties"],  # From Pydantic
            "required": schema["required"],       # From Pydantic
        },
    },
})
```

**Fallback** (config-only, string-typed):
```python
tools_schema.append({
    "type": "function",
    "function": {
        "name": desc["name"],
        "description": desc["description"],
        "parameters": {
            "type": "object",
            "properties": {a: {"type": "string"} for a in desc["args"]},
            "required": desc["args"],
        },
    },
})
```

**Example Output:**
```json
[
  {
    "type": "function",
    "function": {
      "name": "search_database",
      "description": "Search the database for records matching a query.",
      "parameters": {
        "type": "object",
        "properties": {
          "query": {"type": "string"},
          "limit": {"type": "integer"}
        },
        "required": ["query", "limit"]
      }
    }
  }
]
```

### Step 3: Building Messages with Context

The planner builds messages via `_build_function_calling_messages()` that include:

1. **System Prompt:**
   ```python
   messages = [
       {
           "role": "system",
           "content": f"{self.system_prompt}\n{plan_block}"
       }
   ]
   ```

2. **Strategic Plan (if available):**
   ```python
   strategic_plan = get_from_context("strategic_plan")
   if strategic_plan:
       plan_block = f"\nSTRATEGIC PLAN:\n{json.dumps(strategic_plan, indent=2)[:1500]}\n"
   ```

3. **History (previous actions/observations):**
   ```python
   for entry in filtered_history:
       if entry["type"] == "action":
           messages.append({
               "role": "assistant",
               "content": f"Calling tool: {tool_name} with args: {json.dumps(args)}"
           })
       elif entry["type"] == "observation":
           messages.append({
               "role": "user",
               "content": f"Tool result: {observation_content}"
           })
   ```

4. **Current Task:**
   ```python
   messages.append({
       "role": "user",
       "content": task  # e.g., "Find all records matching criteria X"
   })
   ```

### Step 4: System Prompt Guidance

The system prompt provides explicit guidance on tool usage:

```yaml
spec:
  planner:
    config:
      system_prompt: |
        You are a data analysis specialist. Your role is to analyze and query data:
        - Search databases for records
        - Retrieve detailed information
        - Analyze patterns and statistics
        
        Workflow:
        1. Use search_database to find relevant records
        2. For each record, use get_record_details to retrieve full information
        3. Use analyze_data to compute statistics
        4. Return structured analysis report with findings
```

**Key Functions:**
- **Guides tool selection:** Explicit workflow tells LLM which tools to use and in what order
- **Sets constraints:** Role definition prevents misuse
- **Provides context:** Explains the agent's role and responsibilities

### Step 5: OpenAI Function Calling

The `OpenAIGateway` sends the request to OpenAI API:

```python
payload = {
    "model": "gpt-4o-mini",
    "messages": messages,  # System prompt + history + task
    "tools": tools_schema,  # Function definitions
    "tool_choice": "auto"   # or "required" or specific tool name
}
```

**Tool Choice Modes:**
- **`"auto"`** (default): LLM decides whether to call a tool or respond with text
- **`"required"`**: LLM must call a tool (cannot respond with text)
- **`"none"`**: LLM cannot call tools (text-only response)
- **`{"type": "function", "function": {"name": "specific_tool"}}`**: Force specific tool

**LLM Decision Process:**
1. Reads system prompt (understands role and workflow)
2. Reads task description (understands what to do)
3. Reads history (sees what was already done)
4. Reads tools schema (sees available tools and their descriptions)
5. **Reasons:** "To analyze data, I should first search for records, then get details, then analyze"
6. **Selects tools:** Returns `tool_calls` array with selected tools

### Step 6: LLM Response Processing

The `ReActPlanner` processes the LLM response:

```python
def _plan_with_function_calling(self, task_description, history):
    # Call LLM
    response = self.llm.invoke(messages, tools=tools_schema)
    
    # LLM returns structured response
    if isinstance(response, dict):
        tool_calls = response.get("tool_calls")
        if tool_calls:
            # Convert tool calls to Actions
            actions = []
            for tool_call in tool_calls:
                func = tool_call.get("function", {})
                tool_name = func.get("name")
                args_str = func.get("arguments", "{}")
                tool_args = json.loads(args_str)
                
                actions.append(Action(tool_name=tool_name, tool_args=tool_args))
            
            # Limit parallel calls
            if self.max_parallel_tool_calls:
                actions = actions[:self.max_parallel_tool_calls]
            
            return actions  # Return list for parallel execution
```

**Example LLM Response:**
```json
{
  "tool_calls": [
    {
      "id": "call_123",
      "type": "function",
      "function": {
        "name": "search_database",
        "arguments": "{\"query\": \"active users\", \"limit\": 10}"
      }
    },
    {
      "id": "call_124",
      "type": "function",
      "function": {
        "name": "list_tables",
        "arguments": "{}"
      }
    }
  ]
}
```

## Factors Influencing Tool Choice

### 1. **Tool Descriptions** (Primary Factor)
- **Clear descriptions** → Better tool selection
- **Vague descriptions** → LLM may select wrong tool
- **Example:**
  - Good: `"Search the database for records matching a query."`
  - Bad: `"Searches stuff."`

### 2. **System Prompt** (Strong Guidance)
- **Explicit workflows** guide tool selection
- **Role definition** sets context
- **Constraints** prevent misuse
- **Example:**
  ```
  Workflow:
  1. Use search_database to find relevant records
  2. For each record, use get_record_details...
  ```

### 3. **Task Description** (Direct Input)
- **Clear task** → Better tool selection
- **Vague task** → LLM may need to explore
- **Example:**
  - Clear: `"Find all active users and analyze their activity"`
  - Vague: `"Check users"`

### 4. **History** (Context Learning)
- **Previous actions** show what was already done
- **Observations** show results
- **LLM learns** from past tool calls
- **Example:**
  ```
  Action: search_database with {"query": "active users", "limit": 10}
  Observation: Found 10 records: [user1, user2, ...]
  → LLM knows records exist, can now call get_record_details
  ```

### 5. **Strategic Plan** (High-Level Context)
- **Orchestrator phases** provide context
- **Manager steps** guide workflow
- **Example:**
  ```
  STRATEGIC PLAN:
  {
    "phases": [
      {"worker": "data-analysis", "goals": "Analyze user activity patterns"}
    ]
  }
  → LLM understands it's part of a larger analysis workflow
  ```

### 6. **Tool Availability** (Constraint)
- **Only available tools** can be selected
- **Missing tools** → LLM cannot call them
- **Example:**
  - If `create_record` is not in `tool_descriptions`, LLM cannot call it

## Example: Complete Tool Selection Flow

### Scenario: "Find and analyze active users"

**Step 1: Configuration**
```yaml
tool_descriptions:
  - name: search_database
    description: "Search the database for records matching a query."
  - name: get_record_details
    description: "Get detailed information about a specific record by ID."
  - name: analyze_data
    description: "Analyze data and return statistical summary."
```

**Step 2: System Prompt**
```
You are a data analysis specialist.
Workflow:
1. Use search_database to find relevant records
2. For each record, use get_record_details to retrieve full information
3. Use analyze_data to compute statistics
```

**Step 3: LLM Receives**
- Messages: System prompt + task "Find and analyze active users"
- Tools schema: [search_database, get_record_details, analyze_data, ...]

**Step 4: LLM Reasons**
```
"I need to find and analyze active users. According to the workflow:
1. First, I should search for active users using search_database
2. Then I can get details for each user
3. Then analyze the data

Let me start with search_database to see what users exist."
```

**Step 5: LLM Returns**
```json
{
  "tool_calls": [
    {
      "function": {
        "name": "search_database",
        "arguments": "{\"query\": \"active users\", \"limit\": 10}"
      }
    }
  ]
}
```

**Step 6: Planner Converts**
```python
Action(tool_name="search_database", tool_args={"query": "active users", "limit": 10})
```

**Step 7: Tool Executes**
- `search_database` returns: `[{"id": "user1", "name": "Alice"}, ...]`

**Step 8: Next Cycle**
- LLM sees observation: "Found 10 active users: [user1, user2, ...]"
- LLM reasons: "Now I should get details for each user"
- LLM returns: `get_record_details` calls for each user

## Parallel Tool Selection

**How it works:**
- LLM can return multiple `tool_calls` in a single response
- Planner converts all to Actions
- Agent executes them in parallel (up to `max_parallel_tool_calls`)

**Example:**
```json
{
  "tool_calls": [
    {"function": {"name": "search_database", "arguments": "{\"query\": \"users\"}"}},
    {"function": {"name": "list_tables", "arguments": "{}"}},
    {"function": {"name": "get_schema", "arguments": "{\"table\": \"users\"}"}}
  ]
}
```

**Result:**
- All 3 tools execute in parallel
- Results are observed together
- Next planning cycle uses all results

## Configuration Options

### Enabling Function Calling

```yaml
spec:
  planner:
    type: ReActPlanner
    config:
      use_function_calling: true  # Enable OpenAI function calling
      max_parallel_tool_calls: 3   # Limit parallel tool execution
```

### Tool Choice Control

Configure via `OpenAIGateway`:

```yaml
resources:
  inference_gateways:
    - name: openai-llm
      type: OpenAIGateway
      config:
        model: gpt-4o-mini
        tool_choice: "auto"  # or "required", "none", or specific tool
```

Or via environment variable:
```bash
OPENAI_TOOL_CHOICE=auto  # or required, none
```

## Key Takeaways

1. **Tool descriptions are critical** - Clear descriptions lead to better tool selection
2. **System prompts guide selection** - Explicit workflows help LLM choose correctly
3. **LLM reasons about tools** - It's not random; LLM understands tool purposes
4. **History influences selection** - LLM learns from previous tool calls
5. **Parallel selection is possible** - LLM can select multiple tools at once
6. **Tool choice is configurable** - Can force specific tools or require tool calls
7. **Pydantic schemas improve accuracy** - When tool objects are available, types are more precise

## Framework Components

- **ReActPlanner**: Builds tool schemas, constructs messages, processes LLM responses
- **OpenAIGateway**: Sends function calling requests to OpenAI API
- **BaseTool**: Provides `args_schema` for accurate parameter types
- **Action**: Represents a tool call to be executed

The framework handles all the complexity of converting tool descriptions to function schemas, building context-aware messages, and processing LLM tool selections automatically.

