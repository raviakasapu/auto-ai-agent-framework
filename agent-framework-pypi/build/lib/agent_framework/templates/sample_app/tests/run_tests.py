#!/usr/bin/env python3
"""
Comprehensive Test Runner for the AI Agent Framework Sample App.

This script provides a convenient way to run different test tiers
with appropriate configurations.

Usage:
    # Run all unit tests (no API key needed)
    python tests/run_tests.py --unit

    # Run integration tests (no API key needed)
    python tests/run_tests.py --integration

    # Run E2E tests (requires API key)
    OPENAI_API_KEY=your_key python tests/run_tests.py --e2e

    # Run all tests
    OPENAI_API_KEY=your_key python tests/run_tests.py --all

    # Run specific test file
    python tests/run_tests.py --file tests/unit/test_tools.py

    # Run with verbose output
    python tests/run_tests.py --unit -v
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


# Change to sample_app directory
SAMPLE_APP_DIR = Path(__file__).resolve().parents[1]
os.chdir(SAMPLE_APP_DIR)
sys.path.insert(0, str(SAMPLE_APP_DIR))


def run_pytest(args: list[str], verbose: bool = False) -> int:
    """Run pytest with given arguments."""
    cmd = [sys.executable, "-m", "pytest"]

    if verbose:
        cmd.append("-v")

    cmd.extend(args)

    print(f"\n{'='*60}")
    print(f"Running: {' '.join(cmd)}")
    print(f"{'='*60}\n")

    result = subprocess.run(cmd, cwd=SAMPLE_APP_DIR)
    return result.returncode


def run_unit_tests(verbose: bool = False) -> int:
    """Run Tier 1 unit tests."""
    print("\n" + "="*60)
    print("TIER 1: UNIT TESTS")
    print("(No API key required)")
    print("="*60)

    return run_pytest(["tests/unit/", "-x"], verbose)


def run_integration_tests(verbose: bool = False) -> int:
    """Run Tier 2 integration tests."""
    print("\n" + "="*60)
    print("TIER 2: INTEGRATION TESTS")
    print("(Mocked LLM calls)")
    print("="*60)

    return run_pytest(["tests/integration/", "-x"], verbose)


def run_e2e_tests(verbose: bool = False) -> int:
    """Run Tier 3 E2E tests."""
    if not os.getenv("OPENAI_API_KEY"):
        print("\n" + "="*60)
        print("ERROR: OPENAI_API_KEY not set")
        print("E2E tests require an API key.")
        print("Set with: export OPENAI_API_KEY=your_key")
        print("="*60)
        return 1

    print("\n" + "="*60)
    print("TIER 3: END-TO-END TESTS")
    print("(Real LLM calls - may take longer)")
    print("="*60)

    return run_pytest(["tests/e2e/", "-x"], verbose)


def run_all_tests(verbose: bool = False) -> int:
    """Run all test tiers."""
    print("\n" + "="*60)
    print("RUNNING ALL TESTS")
    print("="*60)

    # Unit tests
    result = run_unit_tests(verbose)
    if result != 0:
        print("\nUnit tests failed. Stopping.")
        return result

    # Integration tests
    result = run_integration_tests(verbose)
    if result != 0:
        print("\nIntegration tests failed. Stopping.")
        return result

    # E2E tests (only if API key available)
    if os.getenv("OPENAI_API_KEY"):
        result = run_e2e_tests(verbose)
        if result != 0:
            print("\nE2E tests failed.")
            return result
    else:
        print("\n" + "="*60)
        print("SKIPPING E2E TESTS (no API key)")
        print("="*60)

    print("\n" + "="*60)
    print("ALL TESTS PASSED!")
    print("="*60)

    return 0


def run_quick_tests(verbose: bool = False) -> int:
    """Run quick sanity check tests."""
    print("\n" + "="*60)
    print("QUICK SANITY CHECK")
    print("="*60)

    # Run just the tool registration and schema tests
    return run_pytest([
        "tests/unit/test_tools.py::TestToolSuccessCases",
        "tests/unit/test_tools.py::TestToolSchemas",
        "tests/unit/test_memory.py::TestInMemoryMemory",
        "-x"
    ], verbose)


def print_test_summary():
    """Print summary of available test tiers."""
    print("""
AI Agent Framework Test Suite
=============================

Test Tiers:
-----------

TIER 1: Unit Tests (tests/unit/)
  - Tool execution and validation
  - Memory operations and isolation
  - Factory and configuration loading
  - No API key required
  - Fast execution (~seconds)

TIER 2: Integration Tests (tests/integration/)
  - Planner behavior with mocked LLMs
  - Agent loop execution
  - Component interactions
  - No API key required
  - Medium execution (~seconds)

TIER 3: E2E Tests (tests/e2e/)
  - Full agent execution with real LLM
  - Golden path scenarios
  - Robustness and edge cases
  - Requires OPENAI_API_KEY
  - Slower execution (~minutes)

Usage:
------
  python tests/run_tests.py --unit          # Run unit tests
  python tests/run_tests.py --integration   # Run integration tests
  python tests/run_tests.py --e2e           # Run E2E tests (needs API key)
  python tests/run_tests.py --all           # Run all tests
  python tests/run_tests.py --quick         # Quick sanity check
  python tests/run_tests.py --file <path>   # Run specific test file

Options:
--------
  -v, --verbose    Verbose output
  --help           Show this message
""")


def main():
    parser = argparse.ArgumentParser(
        description="Run AI Agent Framework tests",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument("--unit", action="store_true",
                        help="Run Tier 1 unit tests")
    parser.add_argument("--integration", action="store_true",
                        help="Run Tier 2 integration tests")
    parser.add_argument("--e2e", action="store_true",
                        help="Run Tier 3 E2E tests (requires API key)")
    parser.add_argument("--all", action="store_true",
                        help="Run all tests")
    parser.add_argument("--quick", action="store_true",
                        help="Run quick sanity check")
    parser.add_argument("--file", type=str,
                        help="Run specific test file")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Verbose output")
    parser.add_argument("--summary", action="store_true",
                        help="Print test summary and exit")

    args = parser.parse_args()

    if args.summary or len(sys.argv) == 1:
        print_test_summary()
        return 0

    if args.file:
        return run_pytest([args.file], args.verbose)

    if args.quick:
        return run_quick_tests(args.verbose)

    if args.all:
        return run_all_tests(args.verbose)

    if args.unit:
        return run_unit_tests(args.verbose)

    if args.integration:
        return run_integration_tests(args.verbose)

    if args.e2e:
        return run_e2e_tests(args.verbose)

    # Default: show summary
    print_test_summary()
    return 0


if __name__ == "__main__":
    sys.exit(main())
