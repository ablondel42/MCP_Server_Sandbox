"""CLI main entry point."""

import argparse
import json
import sys

from repo_context.logging_config import get_logger
from repo_context.storage import (
    close_connection,
)



from ..utils import get_connection_for_args
from repo_context.validation import run_full_workflow_validation
from repo_context.validation import run_symbol_workflow_validation



logger = get_logger("cli.main")

def cmd_validate_workflow(args: argparse.Namespace) -> int:
    """Run full workflow validation for a fixture.

    Args:
        args: Parsed command line arguments.

    Returns:
        Exit code (0 for success, 1 for failure).
    """

    conn = get_connection_for_args(args)
    try:
        repo_root = args.repo_root
        fixture_name = args.fixture_name or f"workflow:{repo_root.name}"
        result = run_full_workflow_validation(conn, repo_root, fixture_name)

        if args.json:
            output = {
                "name": result.name,
                "passed": result.passed,
                "checks": result.checks,
                "errors": result.errors,
                "details": result.details,
            }
            print(json.dumps(output, indent=2, sort_keys=True))
        else:
            print(f"\nWorkflow Validation: {result.name}")
            print(f"  Passed: {result.passed}")
            print(f"  Checks: {len(result.checks)}")
            print(f"  Errors: {len(result.errors)}")
            if result.errors:
                print("\nErrors:")
                for err in result.errors:
                    print(f"  - {err}")
        return 0 if result.passed else 1
    except Exception as exc:
        logger.exception("cmd_validate_workflow: Failed")
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        close_connection(conn)



def cmd_validate_symbol_workflow(args: argparse.Namespace) -> int:
    """Run symbol-focused workflow validation.

    Args:
        args: Parsed command line arguments.

    Returns:
        Exit code (0 for success, 1 for failure).
    """

    conn = get_connection_for_args(args)
    try:
        symbol_id = args.symbol_id
        result = run_symbol_workflow_validation(conn, symbol_id)

        if args.json:
            output = {
                "name": result.name,
                "passed": result.passed,
                "checks": result.checks,
                "errors": result.errors,
                "details": result.details,
            }
            print(json.dumps(output, indent=2, sort_keys=True))
        else:
            print(f"\nSymbol Workflow Validation: {result.name}")
            print(f"  Passed: {result.passed}")
            print(f"  Checks: {len(result.checks)}")
            print(f"  Errors: {len(result.errors)}")
            if result.errors:
                print("\nErrors:")
                for err in result.errors:
                    print(f"  - {err}")
        return 0 if result.passed else 1
    except Exception as exc:
        logger.exception("cmd_validate_symbol_workflow: Failed")
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        close_connection(conn)
