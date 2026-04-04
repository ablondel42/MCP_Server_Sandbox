"""MCP tool adapters.

Maps internal objects to tool-facing payloads.
"""

import json


def adapt_node(node: dict) -> dict:
    """Adapt a node dict to a symbol payload.

    Args:
        node: Node dict from database query.

    Returns:
        Symbol payload dict for tool output.
    """
    payload_json = node.get("payload_json", "{}")
    if isinstance(payload_json, dict):
        payload = payload_json
    elif isinstance(payload_json, str):
        payload = json.loads(payload_json) if payload_json else {}
    else:
        payload = {}

    return {
        "id": node["id"],
        "qualified_name": node["qualified_name"],
        "kind": node["kind"],
        "scope": node.get("scope", "module"),
        "file_id": node["file_id"],
        "file_path": payload.get("file_path"),
        "module_path": payload.get("module_path"),
        "lexical_parent_id": node.get("lexical_parent_id"),
    }


def adapt_edge(edge: dict) -> dict:
    """Adapt an edge dict to a reference payload.

    Args:
        edge: Edge dict from database query.

    Returns:
        Reference payload dict for tool output.
    """
    return {
        "from_id": edge["from_id"],
        "to_id": edge["to_id"],
        "evidence_file_id": edge.get("evidence_file_id"),
        "evidence_uri": edge.get("evidence_uri"),
        "confidence": edge.get("confidence"),
        "evidence_range_json": edge.get("evidence_range_json"),
    }


def adapt_context(ctx) -> dict:
    """Adapt a SymbolContext to a context payload.

    Args:
        ctx: SymbolContext dataclass instance.

    Returns:
        Context payload dict for tool output.
    """
    return {
        "focus_symbol": ctx.focus_symbol,
        "structural_parent": ctx.structural_parent,
        "structural_children": ctx.structural_children,
        "lexical_parent": ctx.lexical_parent,
        "lexical_children": ctx.lexical_children,
        "incoming_edges": ctx.incoming_edges,
        "outgoing_edges": ctx.outgoing_edges,
        "reference_summary": ctx.reference_summary,
        "structural_summary": ctx.structural_summary,
        "freshness": ctx.freshness,
        "confidence": ctx.confidence,
    }


def adapt_risk_result(result) -> dict:
    """Adapt a RiskResult to a risk payload.

    Args:
        result: RiskResult dataclass instance.

    Returns:
        Risk payload dict for tool output.
    """
    return {
        "targets": [
            {
                "symbol_id": t.symbol_id,
                "qualified_name": t.qualified_name,
                "kind": t.kind,
                "scope": t.scope,
                "file_id": t.file_id,
                "file_path": t.file_path,
                "module_path": t.module_path,
                "visibility_hint": t.visibility_hint,
                "lexical_parent_id": t.lexical_parent_id,
            }
            for t in result.targets
        ],
        "facts": {
            "target_count": result.facts.target_count,
            "symbol_ids": result.facts.symbol_ids,
            "symbol_kinds": list(result.facts.symbol_kinds),
            "reference_counts": result.facts.reference_counts,
            "reference_availability": result.facts.reference_availability,
            "referencing_file_counts": result.facts.referencing_file_counts,
            "referencing_module_counts": result.facts.referencing_module_counts,
            "touches_public_surface": result.facts.touches_public_surface,
            "touches_local_scope_only": result.facts.touches_local_scope_only,
            "target_spans_multiple_files": result.facts.target_spans_multiple_files,
            "target_spans_multiple_modules": result.facts.target_spans_multiple_modules,
            "cross_file_impact": result.facts.cross_file_impact,
            "cross_module_impact": result.facts.cross_module_impact,
            "inheritance_involved": result.facts.inheritance_involved,
            "stale_symbols": result.facts.stale_symbols,
            "low_confidence_symbols": result.facts.low_confidence_symbols,
            "low_confidence_edges": result.facts.low_confidence_edges,
            "extra": result.facts.extra,
        },
        "issues": result.issues,
        "risk_score": result.risk_score,
        "decision": result.decision,
    }
