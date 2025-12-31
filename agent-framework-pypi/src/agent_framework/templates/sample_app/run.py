#!/usr/bin/env python3
"""
Sample App Runner

Demonstrates the AI Agent Framework with:
- Research worker (web search, note taking, calculations)
- Task worker (task management, weather lookup)
- Orchestrator (routes to appropriate worker)

Usage:
    python run.py                    # Interactive mode
    python run.py "search for python tutorials"  # Single task
    python run.py --config research  # Use specific worker directly
    python run.py --test             # Run all test scenarios

Environment variables:
    OPENAI_API_KEY          - Required for LLM inference
    OPENAI_MODEL            - Model for workers (default: gpt-4o-mini)
    OPENAI_STRATEGIC_MODEL  - Model for orchestrator (default: gpt-4o)
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any

# Add sample_app to path for local imports (tools, deployment)
SAMPLE_APP_DIR = Path(__file__).resolve().parent
if str(SAMPLE_APP_DIR) not in sys.path:
    sys.path.insert(0, str(SAMPLE_APP_DIR))


def load_env():
    """Load environment variables from .env file."""
    env_file = SAMPLE_APP_DIR / ".env"

    if env_file.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(env_file)
            print(f"Loaded environment from: {env_file}")
        except ImportError:
            print("Warning: python-dotenv not installed, using system environment")
    else:
        print("Warning: No .env file found, using system environment")


def check_api_key():
    """Check if OpenAI API key is set."""
    if not os.getenv("OPENAI_API_KEY"):
        print("\nError: OPENAI_API_KEY not set!")
        print("   Set it in your environment or create a .env file:")
        print("   OPENAI_API_KEY=sk-your-key-here")
        sys.exit(1)
    print("OpenAI API key configured")


class ConsoleProgressHandler:
    """Simple progress handler that prints events to console."""

    async def on_event(self, event_name: str, data: Dict[str, Any]) -> None:
        """Handle agent events."""
        if event_name == "agent_start":
            print(f"\nAgent started: {data.get('agent_name', 'Unknown')}")
        elif event_name == "agent_end":
            print(f"\nAgent completed")
        elif event_name == "tool_start":
            tool = data.get("tool_name", "unknown")
            args = data.get("tool_args", {})
            print(f"  Calling tool: {tool}")
            if args:
                # Truncate long args for display
                args_str = str(args)[:100]
                if len(str(args)) > 100:
                    args_str += "..."
                print(f"     Args: {args_str}")
        elif event_name == "tool_end":
            result = data.get("result", {})
            if isinstance(result, dict):
                summary = result.get("message") or result.get("description") or str(result)[:100]
            else:
                summary = str(result)[:100]
            print(f"  Result: {summary}")
        elif event_name == "llm_start":
            print(f"  Thinking...")
        elif event_name == "error":
            print(f"  Error: {data.get('error', 'Unknown error')}")


async def run_agent(config_name: str, task: str) -> Dict[str, Any]:
    """Run an agent with the given configuration and task."""
    from deployment.factory import AgentFactory

    # Map config names to paths
    config_paths = {
        "orchestrator": "configs/agents/orchestrator.yaml",
        "research": "configs/agents/research_worker.yaml",
        "task": "configs/agents/task_worker.yaml",
    }

    config_path = config_paths.get(config_name, config_name)

    print(f"\nLoading agent from: {config_path}")
    agent = AgentFactory.create_from_yaml(config_path)

    print(f"Task: {task}")
    handler = ConsoleProgressHandler()

    result = await agent.run(task, progress_handler=handler)

    return result


def run_interactive():
    """Run in interactive mode."""
    print("\n" + "="*60)
    print("AI Agent Framework - Sample App")
    print("="*60)
    print("\nCommands:")
    print("  Type a task to execute (routed by orchestrator)")
    print("  /research <task>  - Use research worker directly")
    print("  /task <task>      - Use task worker directly")
    print("  /quit             - Exit")
    print("="*60)

    while True:
        try:
            user_input = input("\n> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nGoodbye!")
            break

        if not user_input:
            continue

        if user_input.lower() in ("/quit", "/exit", "quit", "exit"):
            print("Goodbye!")
            break

        # Parse command
        if user_input.startswith("/research "):
            config = "research"
            task = user_input[10:].strip()
        elif user_input.startswith("/task "):
            config = "task"
            task = user_input[6:].strip()
        else:
            config = "orchestrator"
            task = user_input

        try:
            result = asyncio.run(run_agent(config, task))
            print("\n" + "-"*40)
            print("Final Result:")
            if isinstance(result, dict):
                summary = result.get("human_readable_summary") or result.get("message") or str(result)
                print(f"   {summary}")
            else:
                print(f"   {result}")
        except Exception as e:
            print(f"\nError: {e}")
            import traceback
            traceback.print_exc()


async def run_tests():
    """Run test scenarios to validate the framework."""
    print("\n" + "="*60)
    print("Running Test Scenarios")
    print("="*60)

    test_cases = [
        # Research worker tests
        ("research", "Search for Python tutorials"),
        ("research", "Calculate 25 * 4 + 10"),
        ("research", "Take a note titled 'Test Note' with content 'This is a test'"),

        # Task worker tests
        ("task", "Create a task called 'Buy groceries' with high priority"),
        ("task", "List all pending tasks"),
        ("task", "What's the weather in London?"),

        # Orchestrator tests (routing)
        ("orchestrator", "Search for machine learning tutorials"),
        ("orchestrator", "Create a task to review documents"),
    ]

    results = []
    for config, task in test_cases:
        print(f"\n{'='*40}")
        print(f"Test: [{config}] {task}")
        print("="*40)

        try:
            result = await run_agent(config, task)
            success = True
            message = "PASSED"
        except Exception as e:
            result = {"error": str(e)}
            success = False
            message = f"FAILED: {e}"

        results.append({
            "config": config,
            "task": task,
            "success": success,
            "result": result,
        })
        print(f"\n-> {message}")

    # Summary
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    passed = sum(1 for r in results if r["success"])
    failed = len(results) - passed
    print(f"   Passed: {passed}")
    print(f"   Failed: {failed}")
    print(f"   Total:  {len(results)}")

    if failed > 0:
        print("\nFailed tests:")
        for r in results:
            if not r["success"]:
                print(f"   - [{r['config']}] {r['task']}")
                print(f"     Error: {r['result'].get('error', 'Unknown')}")

    return results


def main():
    """Main entry point."""
    load_env()
    check_api_key()

    # Parse arguments
    args = sys.argv[1:]

    if not args:
        # Interactive mode
        run_interactive()
    elif args[0] == "--test":
        # Test mode
        asyncio.run(run_tests())
    elif args[0] == "--config" and len(args) >= 3:
        # Specific config with task
        config = args[1]
        task = " ".join(args[2:])
        result = asyncio.run(run_agent(config, task))
        print(f"\nResult: {result}")
    else:
        # Single task (use orchestrator)
        task = " ".join(args)
        result = asyncio.run(run_agent("orchestrator", task))
        print(f"\nResult: {result}")


if __name__ == "__main__":
    main()
