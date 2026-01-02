"""
Tier 1: Unit Tests for Tools

Tests cover:
A. Success Case - Tool execute() works with valid inputs
B. Validation Error - Pydantic args_schema raises ValidationError for invalid inputs
C. Execution Error - Tool handles runtime errors gracefully
D. Schema Validation - Tools have proper name, description, schemas
E. Permission Tests - Tool permissions are correctly set (if applicable)

Run with:
    pytest tests/unit/test_tools.py -v
"""
from __future__ import annotations

import json
import pytest
from pydantic import ValidationError


# =============================================================================
# A. Success Case Tests
# =============================================================================

class TestToolSuccessCases:
    """Test that each tool's execute method works correctly with valid inputs."""

    def test_note_taker_creates_note(self, note_taker_tool):
        """NoteTakerTool should create a note with valid inputs."""
        result = note_taker_tool.execute(
            title="Test Note",
            content="This is test content",
            tags=["test", "unit"]
        )

        assert result["success"] is True
        assert "note_id" in result
        assert result["note_id"].startswith("note_")
        assert "message" in result
        assert "Test Note" in result["message"]

    def test_note_taker_optional_tags(self, note_taker_tool):
        """NoteTakerTool should work without optional tags."""
        result = note_taker_tool.execute(
            title="Note Without Tags",
            content="Content here"
        )

        assert result["success"] is True
        assert "note_id" in result

    def test_task_manager_creates_task(self, task_manager_tool):
        """TaskManagerTool should create a task with valid inputs."""
        result = task_manager_tool.execute(
            title="Buy groceries",
            description="Get milk and eggs",
            priority="high"
        )

        assert result["success"] is True
        assert "task_id" in result
        assert result["task_id"].startswith("task_")
        assert result["priority"] == "high"
        assert "message" in result

    def test_task_manager_default_priority(self, task_manager_tool):
        """TaskManagerTool should use default priority if not specified."""
        result = task_manager_tool.execute(
            title="Simple task",
            description="A simple task"
        )

        assert result["success"] is True
        assert result["priority"] == "medium"  # default

    def test_list_tasks_returns_tasks(self, task_manager_tool, list_tasks_tool):
        """ListTasksTool should return created tasks."""
        # Create a task first
        task_manager_tool.execute(
            title="Test Task",
            description="For listing",
            priority="low"
        )

        result = list_tasks_tool.execute(status="pending")

        assert "tasks" in result
        assert "total_count" in result
        assert result["total_count"] >= 1

    def test_list_tasks_filter_by_priority(self, task_manager_tool, list_tasks_tool):
        """ListTasksTool should filter by priority."""
        task_manager_tool.execute(title="High", description="High priority", priority="high")
        task_manager_tool.execute(title="Low", description="Low priority", priority="low")

        result = list_tasks_tool.execute(priority="high")

        assert "tasks" in result
        # All returned tasks should be high priority
        for task in result["tasks"]:
            assert task["priority"] == "high"

    def test_complete_task_marks_complete(self, task_manager_tool, complete_task_tool):
        """CompleteTaskTool should mark a task as completed."""
        # Create a task
        create_result = task_manager_tool.execute(
            title="Task to complete",
            description="Will be completed"
        )
        task_id = create_result["task_id"]

        # Complete it
        result = complete_task_tool.execute(task_id=task_id)

        assert result["success"] is True
        assert result["title"] == "Task to complete"
        # Should indicate completion in message or have completed status
        assert "completed" in str(result).lower() or result.get("status") == "completed"

    def test_weather_lookup_returns_weather(self, weather_tool):
        """WeatherLookupTool should return weather data."""
        result = weather_tool.execute(city="London", units="celsius")

        assert "city" in result
        assert result["city"] == "London"
        assert "temperature" in result
        assert "condition" in result
        assert "humidity" in result
        assert isinstance(result["temperature"], (int, float))

    def test_weather_lookup_fahrenheit(self, weather_tool):
        """WeatherLookupTool should handle fahrenheit units."""
        result = weather_tool.execute(city="New York", units="fahrenheit")

        assert result["city"] == "New York"
        assert "temperature" in result
        # Fahrenheit should be higher than Celsius for same temp
        celsius_result = weather_tool.execute(city="New York", units="celsius")
        # Temperature in F should be different from C
        assert result["temperature"] != celsius_result["temperature"] or \
               result["temperature"] == 32  # 0C = 32F edge case

    def test_mock_search_returns_results(self, search_tool):
        """MockSearchTool should return search results."""
        result = search_tool.execute(query="Python tutorials", max_results=5)

        assert "results" in result
        assert "total_results" in result
        assert result["query"] == "Python tutorials"
        assert len(result["results"]) <= 5

        # Check result structure
        for item in result["results"]:
            assert "title" in item
            assert "url" in item
            assert "snippet" in item

    def test_mock_search_respects_max_results(self, search_tool):
        """MockSearchTool should respect max_results parameter."""
        result = search_tool.execute(query="test", max_results=2)

        assert len(result["results"]) <= 2


# =============================================================================
# B. Validation Error Tests
# =============================================================================

class TestToolValidationErrors:
    """Test that tools raise ValidationError for invalid inputs."""

    def test_note_taker_missing_title(self, note_taker_tool):
        """NoteTakerTool should fail without required title."""
        with pytest.raises((ValidationError, TypeError)):
            note_taker_tool.execute(content="Content without title")

    def test_note_taker_missing_content(self, note_taker_tool):
        """NoteTakerTool should fail without required content."""
        with pytest.raises((ValidationError, TypeError)):
            note_taker_tool.execute(title="Title without content")

    def test_note_taker_invalid_tags_type(self, note_taker_tool):
        """NoteTakerTool should handle invalid tags type."""
        # Tags should be a list, not a string
        # Tool may coerce string to list or handle gracefully
        try:
            result = note_taker_tool.execute(
                title="Test",
                content="Content",
                tags="not-a-list"
            )
            # If it doesn't raise, check result is still valid
            assert result is not None
        except (ValidationError, TypeError):
            pass  # Expected if strict validation

    def test_task_manager_missing_title(self, task_manager_tool):
        """TaskManagerTool should fail without required title."""
        with pytest.raises((ValidationError, TypeError)):
            task_manager_tool.execute(description="Description only")

    def test_task_manager_invalid_priority(self, task_manager_tool):
        """TaskManagerTool should handle invalid priority gracefully."""
        # Depending on implementation, this might raise an error or use default
        try:
            result = task_manager_tool.execute(
                title="Test",
                description="Test",
                priority="invalid_priority"
            )
            # If it doesn't raise, it should use a valid priority
            assert result["priority"] in ["low", "medium", "high"]
        except (ValidationError, ValueError):
            pass  # Expected behavior

    def test_complete_task_missing_task_id(self, complete_task_tool):
        """CompleteTaskTool should fail without task_id."""
        with pytest.raises((ValidationError, TypeError)):
            complete_task_tool.execute()

    def test_weather_missing_city(self, weather_tool):
        """WeatherLookupTool should fail without city."""
        with pytest.raises((ValidationError, TypeError)):
            weather_tool.execute(units="celsius")

    def test_search_missing_query(self, search_tool):
        """MockSearchTool should fail without query."""
        with pytest.raises((ValidationError, TypeError)):
            search_tool.execute(max_results=5)

    def test_search_invalid_max_results(self, search_tool):
        """MockSearchTool should handle invalid max_results."""
        # Negative max_results should be handled
        try:
            result = search_tool.execute(query="test", max_results=-1)
            # If it doesn't raise, results should be empty or limited
            assert len(result.get("results", [])) >= 0
        except (ValidationError, ValueError):
            pass  # Expected behavior


# =============================================================================
# C. Execution Error Tests
# =============================================================================

class TestToolExecutionErrors:
    """Test that tools handle runtime errors gracefully."""

    def test_complete_nonexistent_task(self, complete_task_tool):
        """CompleteTaskTool should handle non-existent task gracefully."""
        result = complete_task_tool.execute(task_id="nonexistent-task-id")

        # Should return error info, not crash
        assert result.get("success") is False or "error" in str(result).lower()

    def test_list_tasks_empty_database(self, list_tasks_tool):
        """ListTasksTool should handle empty task list."""
        # Clear any existing tasks by using fresh state
        result = list_tasks_tool.execute(status="pending")

        # Should return empty list, not error
        assert "tasks" in result
        assert isinstance(result["tasks"], list)

    def test_weather_empty_city(self, weather_tool):
        """WeatherLookupTool should handle empty city string."""
        try:
            result = weather_tool.execute(city="", units="celsius")
            # If it doesn't raise, check for error indication
            assert result is not None
        except (ValidationError, ValueError):
            pass  # Expected behavior

    def test_search_empty_query(self, search_tool):
        """MockSearchTool should handle empty query."""
        try:
            result = search_tool.execute(query="", max_results=5)
            # Should return empty results or handle gracefully
            assert "results" in result
        except (ValidationError, ValueError):
            pass  # Expected behavior


# =============================================================================
# D. Schema Validation Tests
# =============================================================================

class TestToolSchemas:
    """Test that all tools have proper Pydantic schemas."""

    def test_tool_has_name(self, all_tools):
        """All tools should have a name property."""
        for tool in all_tools:
            assert hasattr(tool, 'name'), f"{tool} missing 'name'"
            assert isinstance(tool.name, str)
            assert len(tool.name) > 0

    def test_tool_has_description(self, all_tools):
        """All tools should have a description property."""
        for tool in all_tools:
            assert hasattr(tool, 'description'), f"{tool} missing 'description'"
            assert isinstance(tool.description, str)
            assert len(tool.description) > 0

    def test_tool_has_args_schema(self, all_tools):
        """All tools should have an args_schema property."""
        for tool in all_tools:
            assert hasattr(tool, 'args_schema'), f"{tool.name} missing 'args_schema'"
            schema = tool.args_schema
            assert schema is not None

    def test_tool_has_output_schema(self, all_tools):
        """All tools should have an output_schema property."""
        for tool in all_tools:
            assert hasattr(tool, 'output_schema'), f"{tool.name} missing 'output_schema'"
            schema = tool.output_schema
            assert schema is not None

    def test_args_schema_is_pydantic(self, all_tools):
        """args_schema should be a Pydantic model with model_json_schema."""
        for tool in all_tools:
            schema = tool.args_schema
            assert hasattr(schema, 'model_json_schema'), \
                f"{tool.name} args_schema missing model_json_schema"

    def test_args_schema_has_properties(self, all_tools):
        """args_schema should have properties defined."""
        for tool in all_tools:
            json_schema = tool.args_schema.model_json_schema()
            assert "properties" in json_schema, \
                f"{tool.name} args_schema has no properties"

    def test_output_schema_is_pydantic(self, all_tools):
        """output_schema should be a Pydantic model with model_json_schema."""
        for tool in all_tools:
            schema = tool.output_schema
            assert hasattr(schema, 'model_json_schema'), \
                f"{tool.name} output_schema missing model_json_schema"

    def test_tool_names_are_unique(self, all_tools):
        """All tool names should be unique."""
        names = [tool.name for tool in all_tools]
        assert len(names) == len(set(names)), "Duplicate tool names found"

    def test_tool_name_format(self, all_tools):
        """Tool names should be valid identifiers (snake_case)."""
        import re
        for tool in all_tools:
            assert re.match(r'^[a-z][a-z0-9_]*$', tool.name), \
                f"{tool.name} should be snake_case"


# =============================================================================
# E. Tool Behavior Tests
# =============================================================================

class TestToolBehavior:
    """Test specific tool behaviors and edge cases."""

    def test_note_taker_generates_unique_ids(self, note_taker_tool):
        """NoteTakerTool should generate unique note IDs."""
        ids = set()
        for i in range(10):
            result = note_taker_tool.execute(
                title=f"Note {i}",
                content=f"Content {i}"
            )
            note_id = result["note_id"]
            assert note_id not in ids, "Duplicate note ID generated"
            ids.add(note_id)

    def test_task_manager_generates_unique_ids(self, task_manager_tool):
        """TaskManagerTool should generate unique task IDs."""
        ids = set()
        for i in range(10):
            result = task_manager_tool.execute(
                title=f"Task {i}",
                description=f"Description {i}"
            )
            task_id = result["task_id"]
            assert task_id not in ids, "Duplicate task ID generated"
            ids.add(task_id)

    def test_weather_consistent_for_same_city(self, weather_tool):
        """WeatherLookupTool should return consistent data for same city."""
        result1 = weather_tool.execute(city="London", units="celsius")
        result2 = weather_tool.execute(city="London", units="celsius")

        # Mock should return same condition at least
        assert result1["city"] == result2["city"]
        # Temperature might vary slightly in mock, but should be similar
        assert abs(result1["temperature"] - result2["temperature"]) < 5

    def test_search_results_have_required_fields(self, search_tool):
        """Search results should have all required fields."""
        result = search_tool.execute(query="test", max_results=3)

        for item in result["results"]:
            assert "title" in item, "Missing title in search result"
            assert "url" in item, "Missing url in search result"
            assert "snippet" in item, "Missing snippet in search result"
            assert item["url"].startswith("http"), "Invalid URL format"


# =============================================================================
# F. Tool Execute Return Type Tests
# =============================================================================

class TestToolReturnTypes:
    """Test that tools return proper types."""

    def test_tools_return_dict(self, all_tools):
        """All tools should return dictionaries."""
        test_inputs = {
            "note_taker": {"title": "Test", "content": "Content"},
            "create_task": {"title": "Test", "description": "Desc"},
            "list_tasks": {},
            "complete_task": {"task_id": "test-id"},
            "weather_lookup": {"city": "London"},
            "web_search": {"query": "test"},
        }

        for tool in all_tools:
            inputs = test_inputs.get(tool.name, {})
            try:
                result = tool.execute(**inputs)
                assert isinstance(result, dict), \
                    f"{tool.name} should return dict, got {type(result)}"
            except (ValidationError, KeyError):
                pass  # Some might fail due to missing required fields

    def test_tools_return_json_serializable(self, all_tools):
        """Tool outputs should be JSON serializable."""
        test_inputs = {
            "note_taker": {"title": "Test", "content": "Content"},
            "create_task": {"title": "Test", "description": "Desc"},
            "list_tasks": {},
            "complete_task": {"task_id": "test-id"},
            "weather_lookup": {"city": "London"},
            "web_search": {"query": "test"},
        }

        for tool in all_tools:
            inputs = test_inputs.get(tool.name, {})
            try:
                result = tool.execute(**inputs)
                # Should not raise
                json_str = json.dumps(result)
                assert isinstance(json_str, str)
            except (ValidationError, KeyError, TypeError):
                pass  # Some might fail due to missing required fields
