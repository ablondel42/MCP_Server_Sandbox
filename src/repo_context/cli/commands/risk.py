"""CLI main entry point."""

import argparse
import json

from repo_context.config import get_config
from repo_context.logging_config import get_logger
from repo_context.storage import (
    get_connection,
    close_connection,
)
from repo_context.graph import (
    analyze_symbol_risk,
    analyze_target_set_risk,
)

logger = get_logger("cli.main")





def cmd_risk_symbol(args: argparse.Namespace) -> int:
    """Analyze risk for a single symbol.

    Args:
        args: Parsed command line arguments.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    config = get_config()
    db_path = args.db_path if args.db_path else config.db_path
    symbol_id = args.symbol_id

    try:
        conn = get_connection(db_path)
        try:
            result = analyze_symbol_risk(conn, symbol_id)

            logger.info("Symbol risk analyzed", extra={
                "symbol_id": symbol_id,
                "risk_score": result.risk_score,
                "decision": result.decision,
                "issues": len(result.issues)
            })

            if args.json:
                output = {
                    "symbol_id": symbol_id,
                    "risk_score": result.risk_score,
                    "decision": result.decision,
                    "issues": result.issues,
                    "facts": {
                        "target_count": result.facts.target_count,
                        "symbol_kinds": list(result.facts.symbol_kinds),
                        "reference_counts": result.facts.reference_counts,
                        "touches_public_surface": result.facts.touches_public_surface,
                        "cross_file_impact": result.facts.cross_file_impact,
                        "cross_module_impact": result.facts.cross_module_impact,
                        "inheritance_involved": result.facts.inheritance_involved,
                        "stale_symbols": result.facts.stale_symbols,
                        "low_confidence_symbols": result.facts.low_confidence_symbols,
                    },
                }
                print(json.dumps(output, indent=2))
            else:
                print(f"\nRisk Analysis: {symbol_id}")
                print("=" * 60)
                print(f"Risk Score: {result.risk_score}/100")
                print(f"Decision: {result.decision}")
                if result.issues:
                    print(f"\nIssues ({len(result.issues)}):")
                    for issue in result.issues:
                        print(f"  - {issue}")
                else:
                    print("\nIssues: (none)")

            return 0
        finally:
            close_connection(conn)
    except Exception:
        logger.exception("cmd_risk_symbol: Failed to analyze symbol risk")
        raise



def cmd_risk_targets(args: argparse.Namespace) -> int:
    """Analyze risk for multiple symbols.

    Args:
        args: Parsed command line arguments.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    config = get_config()
    db_path = args.db_path if args.db_path else config.db_path
    symbol_ids = args.symbol_ids

    try:
        conn = get_connection(db_path)
        try:
            result = analyze_target_set_risk(conn, symbol_ids)

            logger.info("Target set risk analyzed", extra={
                "symbol_count": len(symbol_ids),
                "risk_score": result.risk_score,
                "decision": result.decision,
                "issues": len(result.issues)
            })

            if args.json:
                output = {
                    "symbols": symbol_ids,
                    "risk_score": result.risk_score,
                    "decision": result.decision,
                    "issues": result.issues,
                    "facts": {
                        "target_count": result.facts.target_count,
                        "symbol_kinds": list(result.facts.symbol_kinds),
                        "touches_public_surface": result.facts.touches_public_surface,
                        "cross_file_impact": result.facts.cross_file_impact,
                        "cross_module_impact": result.facts.cross_module_impact,
                        "inheritance_involved": result.facts.inheritance_involved,
                        "stale_symbols": result.facts.stale_symbols,
                    },
                }
                print(json.dumps(output, indent=2))
            else:
                print(f"\nRisk Analysis: {len(symbol_ids)} symbol(s)")
                print("=" * 60)
                print(f"Risk Score: {result.risk_score}/100")
                print(f"Decision: {result.decision}")
                if result.issues:
                    print(f"\nIssues ({len(result.issues)}):")
                    for issue in result.issues:
                        print(f"  - {issue}")
                else:
                    print("\nIssues: (none)")

            return 0
        finally:
            close_connection(conn)
    except Exception:
        logger.exception("cmd_risk_targets: Failed to analyze target set risk")
        raise
