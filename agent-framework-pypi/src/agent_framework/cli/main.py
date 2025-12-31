#!/usr/bin/env python3
"""
CLI for Agent Framework.

Provides commands to scaffold new projects and manage agents.

Usage:
    agent-framework init [project_name]    # Create a new sample project
    agent-framework --help                 # Show help
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path
from typing import Optional


def get_templates_dir() -> Path:
    """Get the path to the templates directory."""
    return Path(__file__).parent.parent / "templates"


def init_project(project_name: Optional[str] = None, target_dir: Optional[Path] = None) -> Path:
    """
    Initialize a new agent framework project from the sample app template.

    Args:
        project_name: Name for the new project directory. Defaults to 'agent_project'.
        target_dir: Directory to create project in. Defaults to current directory.

    Returns:
        Path to the created project directory.
    """
    project_name = project_name or "agent_project"
    target_dir = target_dir or Path.cwd()

    project_path = target_dir / project_name
    templates_dir = get_templates_dir() / "sample_app"

    if not templates_dir.exists():
        raise FileNotFoundError(
            f"Templates directory not found at {templates_dir}. "
            "Please reinstall the package."
        )

    if project_path.exists():
        raise FileExistsError(
            f"Directory '{project_path}' already exists. "
            "Please choose a different name or remove the existing directory."
        )

    # Copy template directory
    shutil.copytree(templates_dir, project_path)

    # Make run.py executable
    run_script = project_path / "run.py"
    if run_script.exists():
        run_script.chmod(run_script.stat().st_mode | 0o111)

    return project_path


def cmd_init(args: argparse.Namespace) -> int:
    """Handle the init command."""
    try:
        project_path = init_project(args.name)

        print(f"\n{'='*60}")
        print("Project created successfully!")
        print(f"{'='*60}")
        print(f"\nLocation: {project_path}")
        print("\nNext steps:")
        print(f"  1. cd {args.name or 'agent_project'}")
        print("  2. cp .env.example .env")
        print("  3. Edit .env and add your OPENAI_API_KEY")
        print("  4. python run.py")
        print("\nAvailable commands:")
        print("  python run.py                    # Interactive mode")
        print("  python run.py \"your task here\"   # Single task")
        print("  python run.py --test             # Run test scenarios")
        print(f"{'='*60}\n")

        return 0

    except FileExistsError as e:
        print(f"\nError: {e}", file=sys.stderr)
        return 1
    except FileNotFoundError as e:
        print(f"\nError: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"\nUnexpected error: {e}", file=sys.stderr)
        return 1


def cmd_version(args: argparse.Namespace) -> int:
    """Handle the version command."""
    try:
        from agent_framework import __version__
        print(f"agent-framework version {__version__}")
    except ImportError:
        print("agent-framework version unknown")
    return 0


def main(argv: Optional[list] = None) -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="agent-framework",
        description="CLI for Agent Framework - Build hierarchical agentic AI workflows",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  agent-framework init                  Create project in ./agent_project
  agent-framework init my_agents        Create project in ./my_agents
  agent-framework --version             Show version
        """
    )

    parser.add_argument(
        "--version", "-v",
        action="store_true",
        help="Show version and exit"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # init command
    init_parser = subparsers.add_parser(
        "init",
        help="Initialize a new agent framework project",
        description="Create a new project with sample agents, tools, and configurations."
    )
    init_parser.add_argument(
        "name",
        nargs="?",
        default="agent_project",
        help="Project name (default: agent_project)"
    )
    init_parser.set_defaults(func=cmd_init)

    args = parser.parse_args(argv)

    if args.version:
        return cmd_version(args)

    if not args.command:
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
