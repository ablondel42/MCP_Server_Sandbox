```md
# 05-context-builder.md

## Purpose

This phase builds the context builder.

Its job is to take stored graph data and assemble a useful symbol-centered view that an AI agent or later MCP tool can consume without manually stitching together raw rows.

The context builder does not create new graph truth.
It reads the graph and packages the relevant parts around a focus symbol.

This phase should produce structured context such as:
- the focus symbol
- the parent symbol
- child symbols
- incoming edges
- outgoing edges
- lightweight reference summaries when available later
- freshness signals
- confidence signals
- basic structural summaries

This phase does **not** call LSP yet.
It does **not** compute plan risk yet.
It does **not** expose MCP tools yet.

It is the first layer that turns stored graph data into something genuinely useful for decision-making.

---

## Why this phase matters

Raw nodes and edges are not enough for an AI agent.

Even if the graph is stored correctly, an agent still should not have to ask five separate low-level queries just to understand one symbol. The point of this phase is to give the system a reusable, deterministic way to say:

- what this symbol is
- where it lives
- what it contains
- what contains it
- what relationships touch it
- how trustworthy the context is
- whether the context may be stale

Without this phase, later MCP tools would either:
- expose low-level table-shaped data directly, or
- duplicate context assembly logic everywhere

Both are bad.

---

## Phase goals

By the end of this phase, you should have:

- symbol lookup by ID
- symbol lookup by qualified name
- assembled `SymbolContext`
- parent resolution
- child resolution
- outgoing edge resolution
- incoming edge resolution
- lightweight context summaries
- freshness metadata
- confidence metadata
- CLI commands to inspect one symbol context
- tests for context assembly

---

## Phase non-goals

Do **not** do any of this in phase 5:

- LSP reference fetching
- plan risk scoring
- MCP tool server implementation
- file watch mode
- semantic code explanation generation
- autonomous agent behavior

This phase is about assembling graph context, not evaluating plans.

---

## Inputs and outputs

## Inputs

This phase depends on phase 4.

It uses:
- stored nodes
- stored edges
- repo metadata
- file metadata

## Outputs

This phase produces:
- `SymbolContext` objects
- context summaries for CLI inspection
- helper functions for later MCP tools

---

## What “context” means here

Context is not just “the node row”.

For one symbol, useful context usually includes:

- the symbol itself
- its immediate parent
- its immediate children
- its incoming relationships
- its outgoing relationships
- a few small summary facts
- freshness
- confidence

That is enough to make the graph usable without yet turning it into a full reasoning engine.

---

## Context design principles

### Principle 1: The focus symbol is the anchor

Every context object should have one clear focus symbol.

### Principle 2: Keep the scope local

This phase should assemble immediate and near-local graph context, not giant recursive subgraphs.

### Principle 3: Do not invent meaning

The context builder should package existing graph facts.
It should not make speculative claims.

### Principle 4: Deterministic in, deterministic out

Given the same graph state, the same symbol context should be assembled every time.

### Principle 5: Shallow now, deeper later

A clean shallow context is more useful than a huge noisy blob.
Version 1 should avoid runaway expansion.

---

## Recommended package structure additions

Add these files:

```text
src/
  repo_context/
    graph/
      context.py
      summaries.py
      freshness.py
      confidence.py
```

### Why this split

- `context.py`: orchestrates assembly of symbol context
- `summaries.py`: computes lightweight structural summaries
- `freshness.py`: computes freshness flags
- `confidence.py`: computes confidence rollups

Do not cram everything into one giant file.

---

## Core responsibilities of the context builder

This phase should provide helpers that can answer:

- get a symbol by ID
- get a symbol by qualified name
- get the parent symbol
- get child symbols
- get outgoing edges
- get incoming edges
- assemble these into one structured object
- summarize counts
- attach freshness state
- attach confidence state

That is enough.

---

## Recommended `SymbolContext` shape

If phase 1 defined a minimal placeholder model, expand it now into something more useful.

Recommended shape:

```python
from dataclasses import dataclass, field
from typing import Optional, Any

@dataclass
class SymbolContext:
    focus_symbol: dict
    parent: Optional[dict] = None
    children: list[dict] = field(default_factory=list)
    outgoing_edges: list[dict] = field(default_factory=list)
    incoming_edges: list[dict] = field(default_factory=list)
    reference_summary: dict = field(default_factory=dict)
    structural_summary: dict = field(default_factory=dict)
    freshness: dict = field(default_factory=dict)
    confidence: dict = field(default_factory=dict)
```

### Why this shape works

It is:
- simple
- explicit
- JSON-friendly
- good enough for CLI now
- good enough for MCP later

Do not over-design it.

---

## Field commentary for `SymbolContext`

### `focus_symbol`

The main symbol being inspected.

What it does:
- anchors the whole context

Why it matters:
- everything else is relative to this symbol

### `parent`

Immediate parent symbol if one exists.

Examples:
- method -> class
- class -> module

Why it matters:
- structural placement matters for understanding code

### `children`

Immediate child symbols.

Examples:
- module children can be classes and top-level functions
- class children can be methods

Why it matters:
- useful for understanding symbol ownership and shape

### `outgoing_edges`

Edges that start from the focus symbol.

Examples:
- `contains`
- `inherits`
- later `references`

Why it matters:
- shows what the symbol points to or depends on

### `incoming_edges`

Edges that end at the focus symbol.

Examples:
- a `contains` edge from parent
- later `references` from callers

Why it matters:
- shows what depends on or contains the symbol

### `reference_summary`

A compact summary of reference facts.

For phase 5, this may be empty or minimal because LSP has not been added yet.

Why keep it now:
- it stabilizes the shape so later phases can enrich it without changing the whole contract

### `structural_summary`

Small aggregated facts about the symbol and its nearby graph.

Examples:
- child counts
- edge counts
- symbol kind
- module path

Why it matters:
- cheap quick understanding

### `freshness`

Metadata about whether the context may be stale.

Why it matters:
- stale context should later increase caution

### `confidence`

Metadata about how trustworthy the assembled context is.

Why it matters:
- not all graph data is equally strong

---

## Scope rules

Keep the context builder intentionally narrow.

### Include

- focus symbol
- immediate parent
- immediate children
- immediate incoming edges
- immediate outgoing edges
- small summaries

### Exclude

- whole recursive subtree
- transitive dependency explosion
- giant import trees
- giant reverse dependency trees
- freeform English analysis

Why:
- version 1 needs useful context, not graph spam

---

## Lookup entry points

You should support at least two entry paths.

### Entry point 1: by node ID

Recommended function:

```python
def build_symbol_context_by_id(conn, node_id: str) -> SymbolContext:
    ...
```

### Entry point 2: by qualified name

Recommended function:

```python
def build_symbol_context_by_qualified_name(conn, repo_id: str, qualified_name: str, kind: str | None = None) -> SymbolContext:
    ...
```

### Why both matter

- IDs are best for internal deterministic calls
- qualified names are convenient for humans and future tools

---

## Parent resolution

Parent lookup should use `parent_id` on the node first.

Why:
- simple
- direct
- cheaper than asking through edges

Recommended helper:

```python
def get_parent_symbol(conn, node: dict) -> dict | None:
    ...
```

### Good rule

If `parent_id` is missing, return `None`.
Do not try to infer a parent through fuzzy graph logic.

---

## Child resolution

Child lookup should primarily use `parent_id`.

Recommended helper:

```python
def get_child_symbols(conn, node_id: str) -> list[dict]:
    ...
```

### Why prefer `parent_id`

Because it is the most direct hierarchy representation.

You still store `contains` edges because:
- they are graph-explicit
- they help later graph traversal
- they are useful in incoming/outgoing edge views

But for children, `parent_id` is a clean direct lookup.

---

## Edge resolution

The context builder should expose immediate incoming and outgoing edges.

Recommended helpers:

```python
def get_outgoing_edges(conn, node_id: str, kind: str | None = None) -> list[dict]:
    ...

def get_incoming_edges(conn, node_id: str, kind: str | None = None) -> list[dict]:
    ...
```

### Why this matters

Some important context is not captured by parent-child structure alone.

Examples:
- `inherits`
- `imports`
- later `references`

So edge visibility belongs in the context object.

---

## Structural summary design

You should compute a small structural summary, not just dump lists.

Recommended fields:

```python
{
  "kind": "class",
  "qualified_name": "app.services.auth.AuthService",
  "child_count": 3,
  "outgoing_edge_count": 2,
  "incoming_edge_count": 1,
  "has_parent": true,
  "module_path": "app.services.auth"
}
```

### Why this is useful

It gives a quick understanding of the symbol without reading the full object lists.

---

## Freshness design

Freshness should be simple in v1.

Recommended helper:

```python
def build_freshness_summary(symbol: dict, children: list[dict], incoming_edges: list[dict], outgoing_edges: list[dict]) -> dict:
    ...
```

### Recommended output shape

```python
{
  "focus_last_indexed_at": "2026-03-23T20:10:00Z",
  "oldest_edge_last_indexed_at": "2026-03-23T20:10:00Z",
  "is_stale": false,
  "reason": None
}
```

### Simple initial rule

For phase 5, a practical stale rule is enough.

Example:
- if `last_indexed_at` is missing anywhere important -> stale
- otherwise not stale

You can improve this later.

### Important rule

Do not make freshness clever yet.
Make it honest.

---

## Confidence design

Confidence should summarize what the graph already knows.

Recommended helper:

```python
def build_confidence_summary(symbol: dict, children: list[dict], incoming_edges: list[dict], outgoing_edges: list[dict]) -> dict:
    ...
```

### Recommended output shape

```python
{
  "focus_symbol_confidence": 1.0,
  "min_edge_confidence": 0.75,
  "min_child_confidence": 1.0,
  "overall_confidence": 0.75
}
```

### Practical rule

A simple v1 rule is:
- overall confidence = minimum of focus symbol, child confidences, and edge confidences if present
- if no edges or children exist, use the focus symbol confidence

That is crude, but useful.

---

## Reference summary design

LSP references do not exist yet in phase 5, but you should still add the field now.

Recommended output for now:

```python
{
  "reference_count": 0,
  "referencing_file_count": 0,
  "available": false
}
```

### Why include this now

Because later phases can enrich the same context shape without breaking downstream code.

This is one of those small boring decisions that prevents dumb rewrites later.

---

## Recommended context builder flow

Use this sequence:

1. resolve focus symbol
2. resolve parent symbol
3. resolve child symbols
4. resolve outgoing edges
5. resolve incoming edges
6. build structural summary
7. build freshness summary
8. build confidence summary
9. build reference summary placeholder
10. assemble `SymbolContext`

This phase is mostly orchestration.

---

## Example `context.py` sketch

```python
from repo_context.graph.queries import (
    get_symbol,
    get_symbol_by_qualified_name,
    get_parent_symbol,
    get_child_symbols,
    get_outgoing_edges,
    get_incoming_edges,
)
from repo_context.graph.summaries import build_structural_summary
from repo_context.graph.freshness import build_freshness_summary
from repo_context.graph.confidence import build_confidence_summary

def build_symbol_context_by_id(conn, node_id: str) -> dict:
    focus = get_symbol(conn, node_id)
    if focus is None:
        raise ValueError(f"Unknown symbol ID: {node_id}")

    parent = get_parent_symbol(conn, focus)
    children = get_child_symbols(conn, node_id)
    outgoing_edges = get_outgoing_edges(conn, node_id)
    incoming_edges = get_incoming_edges(conn, node_id)

    structural_summary = build_structural_summary(
        focus_symbol=focus,
        parent=parent,
        children=children,
        incoming_edges=incoming_edges,
        outgoing_edges=outgoing_edges,
    )

    freshness = build_freshness_summary(
        symbol=focus,
        children=children,
        incoming_edges=incoming_edges,
        outgoing_edges=outgoing_edges,
    )

    confidence = build_confidence_summary(
        symbol=focus,
        children=children,
        incoming_edges=incoming_edges,
        outgoing_edges=outgoing_edges,
    )

    return {
        "focus_symbol": focus,
        "parent": parent,
        "children": children,
        "outgoing_edges": outgoing_edges,
        "incoming_edges": incoming_edges,
        "reference_summary": {
            "reference_count": 0,
            "referencing_file_count": 0,
            "available": False,
        },
        "structural_summary": structural_summary,
        "freshness": freshness,
        "confidence": confidence,
    }

def build_symbol_context_by_qualified_name(conn, repo_id: str, qualified_name: str, kind: str | None = None) -> dict:
    focus = get_symbol_by_qualified_name(conn, repo_id, qualified_name, kind=kind)
    if focus is None:
        raise ValueError(f"Unknown symbol qualified name: {qualified_name}")
    return build_symbol_context_by_id(conn, focus["id"])
```

This is enough for v1.

---

## Structural summary helper

Create `graph/summaries.py`.

Recommended function:

```python
def build_structural_summary(
    focus_symbol: dict,
    parent: dict | None,
    children: list[dict],
    incoming_edges: list[dict],
    outgoing_edges: list[dict],
) -> dict:
    ...
```

### Suggested output fields

- `kind`
- `name`
- `qualified_name`
- `has_parent`
- `child_count`
- `incoming_edge_count`
- `outgoing_edge_count`
- `child_kind_counts`
- optional `module_path` if derivable

### Example output

```python
{
  "kind": "class",
  "name": "AuthService",
  "qualified_name": "app.services.auth.AuthService",
  "has_parent": True,
  "child_count": 3,
  "incoming_edge_count": 1,
  "outgoing_edge_count": 2,
  "child_kind_counts": {
    "method": 3
  },
  "module_path": "app.services.auth"
}
```

### Why this matters

It is a cheap but useful abstraction over raw rows.

---

## Freshness helper

Create `graph/freshness.py`.

Recommended function:

```python
def build_freshness_summary(
    symbol: dict,
    children: list[dict],
    incoming_edges: list[dict],
    outgoing_edges: list[dict],
) -> dict:
    ...
```

### Recommended simple logic

Collect all relevant `last_indexed_at` timestamps from:
- focus symbol
- children
- incoming edges
- outgoing edges

Then:
- if any are missing, mark `is_stale=True`
- otherwise mark `is_stale=False`

Optional:
- record oldest timestamp
- record missing component count

### Example output

```python
{
  "focus_last_indexed_at": "2026-03-23T22:00:00Z",
  "oldest_related_last_indexed_at": "2026-03-23T22:00:00Z",
  "missing_timestamp_count": 0,
  "is_stale": False,
  "reason": None
}
```

This does not need to be smarter yet.

---

## Confidence helper

Create `graph/confidence.py`.

Recommended function:

```python
def build_confidence_summary(
    symbol: dict,
    children: list[dict],
    incoming_edges: list[dict],
    outgoing_edges: list[dict],
) -> dict:
    ...
```

### Recommended simple logic

Collect confidence values from:
- focus symbol
- children
- incoming edges
- outgoing edges

Compute:
- `focus_symbol_confidence`
- `min_child_confidence`
- `min_edge_confidence`
- `overall_confidence`

### Example output

```python
{
  "focus_symbol_confidence": 1.0,
  "min_child_confidence": 1.0,
  "min_edge_confidence": 0.75,
  "overall_confidence": 0.75
}
```

This is simple and honest.

---

## Context assembly rules by symbol kind

You can keep one generic context builder, but it is useful to understand expected shapes.

## Module context

Likely includes:
- no parent
- children = classes and top-level callables
- outgoing `imports` and `contains`
- incoming maybe little or none in AST-only mode

## Class context

Likely includes:
- parent = module
- children = methods
- outgoing `inherits` and `contains`
- incoming `contains`

## Callable context

Likely includes:
- parent = class or module
- children = none in v1
- incoming `contains`
- outgoing mostly none in AST-only mode until references exist later

Knowing these shapes helps testing and debugging.

---

## Query filtering helpers

It is useful to add small helpers now.

Examples:

```python
def filter_edges_by_kind(edges: list[dict], kind: str) -> list[dict]:
    ...

def filter_children_by_kind(children: list[dict], kind: str) -> list[dict]:
    ...
```

### Why this is useful

Later the MCP layer may want:
- only `inherits` edges
- only methods
- only classes
- only `references`

Do not overbuild it, but a tiny filter module is fine.

---

## CLI additions for this phase

Add a command like:

```text
repo-context show-context <node-id>
```

### What it should do

- resolve the symbol context
- print a readable structured view
- include focus symbol
- include parent
- include child IDs or names
- include incoming/outgoing edge counts
- include freshness and confidence summaries

### Optional second command

```text
repo-context show-context-by-name <repo-id> <qualified-name>
```

This is useful for manual testing.

---

## Example CLI output shape

A plain text or JSON output is fine.

Example JSON-ish output:

```json
{
  "focus_symbol": {
    "id": "sym:repo:project:class:app.services.auth.AuthService",
    "kind": "class",
    "qualified_name": "app.services.auth.AuthService"
  },
  "parent": {
    "id": "sym:repo:project:module:app.services.auth",
    "kind": "module"
  },
  "children": [
    {
      "id": "sym:repo:project:method:app.services.auth.AuthService.login",
      "kind": "method"
    }
  ],
  "structural_summary": {
    "child_count": 1,
    "incoming_edge_count": 1,
    "outgoing_edge_count": 2
  },
  "freshness": {
    "is_stale": false
  },
  "confidence": {
    "overall_confidence": 0.75
  }
}
```

This is plenty for phase 5.

---

## Error handling rules

If a symbol cannot be found:
- raise a clear domain error or return a structured not-found result
- do not silently return an empty context

Good options:
- `ValueError`
- custom `SymbolNotFoundError`

My recommendation:
- use a small custom error if you already have an errors module
- otherwise `ValueError` is acceptable for now

### Why this matters

Later MCP should be able to translate not-found conditions cleanly.

---

## Testing plan

This phase should have strong context-centric tests.

### `test_build_context_for_module`

Verify:
- focus symbol is the module
- parent is `None`
- children include expected top-level symbols
- structural summary is correct

### `test_build_context_for_class`

Verify:
- parent is the module
- children include methods
- outgoing edges include `inherits` and `contains` as expected

### `test_build_context_for_method`

Verify:
- parent is the class
- children are empty
- incoming `contains` edge exists

### `test_lookup_by_qualified_name`

Verify:
- symbol can be resolved by repo ID and qualified name
- resulting context matches expected focus symbol

### `test_freshness_summary`

Verify:
- missing timestamps produce stale context
- complete timestamps produce non-stale context

### `test_confidence_summary`

Verify:
- low-confidence edge lowers overall confidence
- strong focus symbol is still reported correctly

### `test_unknown_symbol_raises`

Verify:
- missing symbol ID results in a clear failure

---

## Suggested fixture usage

Reuse the same small AST fixtures from phase 3 and phase 4.

Especially useful:
- a file with a class and methods
- a file with top-level functions
- a class with bases
- imports in the module

That gives you enough graph structure to test meaningful context assembly.

---

## Acceptance checklist

Phase 5 is done when all of this is true:

- A symbol can be loaded by ID.
- A symbol can be loaded by qualified name.
- Parent lookup works.
- Child lookup works.
- Incoming edge lookup works.
- Outgoing edge lookup works.
- `SymbolContext` objects are assembled cleanly.
- Structural summary is included.
- Freshness summary is included.
- Confidence summary is included.
- Reference summary placeholder is included.
- CLI context inspection works.
- Tests pass.
- No LSP integration exists yet.
- No risk engine exists yet.
- No MCP server exists yet.

---

## Common mistakes to avoid

### Mistake 1: Returning raw SQL rows directly everywhere

The point of this phase is to build a reusable context object, not make every caller assemble pieces manually.

### Mistake 2: Expanding too deep

Do not recursively include the whole graph around a symbol.
That becomes noise fast.

### Mistake 3: Mixing evaluation with context assembly

This phase should expose graph facts, not risk judgments.

### Mistake 4: Forgetting freshness and confidence

Even a structurally correct context can be misleading if it is stale or low confidence.

### Mistake 5: Hiding missing data

If a parent or child is missing, return that honestly.
Do not paper over it.

### Mistake 6: Letting CLI formatting become the main API

The CLI is only a debug surface.
The real product of this phase is the structured context object.

---

## What phase 6 will depend on

The next phase will assume phase 5 already gives it:

- reliable symbol lookups
- reliable context assembly
- clear parent-child structure
- incoming and outgoing edge views
- freshness and confidence summaries

Phase 6 will add LSP-based `references`.
Those references will later slot naturally into:
- outgoing edges
- incoming edges
- reference summaries

That is why this phase should already include a placeholder `reference_summary` field.

---

## Final guidance

This phase is the first time the graph becomes comfortable to use.

Before this phase:
- you had stored graph data

After this phase:
- you have reusable symbol context

That is a big quality-of-life step.

Keep it shallow, deterministic, and honest:

- assemble only near-local context
- include summaries, not essays
- preserve freshness and confidence
- do not jump ahead to risk scoring

If you do that, phase 5 becomes the clean bridge between graph storage and all later agent-facing features.
```