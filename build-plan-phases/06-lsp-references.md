```md
# 06-lsp-reference-enrichment.md

## Purpose

This phase adds selective LSP enrichment to the stored graph.

The goal is not to turn the system into a full IDE.
The goal is to add the single highest-value semantic relationship for version 1:

- `references`

This phase takes the structural graph built from AST and enriches it with reference information returned by a language server. Those reference locations are then mapped back to the internal graph so the system can answer questions like:

- where is this symbol used
- how many places reference it
- how many files reference it
- how many modules reference it
- what symbol contains the usage site

This phase is intentionally narrow.
It should not implement rename, hover, completion, diagnostics, or every other LSP feature.

---

## Why this phase matters

AST tells you what exists.
LSP helps tell you where it is used.

That is a big jump in usefulness.

Without references:
- the graph knows structure, but not dependency pressure
- the agent can inspect symbols, but not blast radius
- plan review is weaker because usage spread is unknown

With references:
- you get much better breakage signals
- you can build `referenced_by` queries cheaply
- later risk evaluation becomes much more useful

This is why LSP is worth adding even if only for one feature.

---

## Phase goals

By the end of this phase, you should have:

- a minimal LSP integration layer
- the ability to locate a symbol declaration position
- the ability to request `references` for a symbol
- mapping from LSP locations back to internal graph symbols when possible
- persisted `references` edges
- derived `referenced_by` queries from reverse lookup
- reference counts
- referencing file counts
- referencing module counts
- optional refresh behavior for references
- tests for mapping and enrichment

---

## Phase non-goals

Do **not** do any of this in phase 6:

- hover support
- rename support
- diagnostics support
- code actions
- semantic tokens
- completion
- full workspace symbol search
- plan risk scoring
- MCP server work
- watch mode

This phase is only about reference enrichment.

---

## Why LSP is being used selectively

This project already has a structural graph from AST.
That means the language server is not the source of truth for everything.

That is good.

The LSP layer should only provide what AST cannot easily provide well enough in v1:
- symbol references

That keeps the system simpler and avoids overcommitting to a huge LSP implementation.

---

## Inputs and outputs

## Inputs

This phase depends on earlier phases and uses:

- stored nodes
- stored edges
- symbol ranges and selection ranges
- file URIs
- repo root
- a working Python language server process

## Outputs

This phase produces:

- `references` edges
- reference summary stats
- reverse `referenced_by` query support
- enriched symbol context helpers
- refresh utilities for selected symbols

---

## Core idea

For a chosen target symbol:

1. find its declaration location
2. pick the best position to ask LSP about, usually `selection_range.start`
3. ask the language server for references
4. get back a list of document locations
5. map each usage location back to the smallest internal symbol that contains it
6. create a `references` edge from the containing symbol to the target symbol
7. persist those edges
8. derive `referenced_by` by reverse-querying the same edges

That is the whole job of this phase.

---

## Architecture additions

Add these files:

```text
src/
  repo_context/
    lsp/
      __init__.py
      client.py
      protocol.py
      references.py
      mapper.py
      resolver.py
    graph/
      references.py
```

### Why this split

- `client.py`: low-level language-server communication
- `protocol.py`: request and response helpers
- `references.py`: orchestration for finding references
- `mapper.py`: map LSP locations back to graph symbols
- `resolver.py`: choose declaration positions and target documents
- `graph/references.py`: graph-level reference stats and reverse lookups

Keep the transport and the graph mapping separate.

---

## LSP design principles

### Principle 1: LSP enriches the graph, it does not replace it

The graph already exists.
LSP only adds a high-value relationship.

### Principle 2: Always map back to internal graph identity

Raw LSP locations are not enough.
You want graph edges between stable node IDs.

### Principle 3: Be honest about uncertainty

Sometimes mapping will be fuzzy or impossible.
Record confidence instead of pretending every match is perfect.

### Principle 4: Reverse lookup should be derived

Store `references`.
Derive `referenced_by` by querying reverse direction.
Do not create two competing truths.

---

## Minimal LSP concepts you need

You do not need the whole LSP protocol surface.

For this phase, the useful concepts are basically:

- `TextDocumentIdentifier`
- `Position`
- `Range`
- `Location`
- `ReferenceParams`

That is enough for one request type:
- find references

---

## What the LSP client should do

The minimal LSP client should be able to:

- start or connect to a Python language server
- open or track text documents if needed
- send a references request for one symbol position
- return the resulting locations
- shut down cleanly

### Important rule

Keep the client minimal.
Do not let it become an IDE framework.

---

## Choosing a language server

You have options like:
- Pyright-based servers
- Jedi-based setups
- pylsp

For v1, pick one working Python LSP and stick to it.

The exact server matters less than the contract:
- given a file URI and position, return references

Do not spend too much time comparing language servers unless one clearly breaks your use case.

---

## Declaration resolution

Before asking for references, you need the best position for the target symbol.

### Best rule

Use:
- `selection_range.start` if present

Fallback:
- `range.start`

### Why

The symbol name location is usually a better anchor for reference lookup than the start of the whole declaration block.

### Recommended helper in `resolver.py`

```python
def get_reference_query_position(symbol: dict) -> dict:
    ...
```

Expected behavior:
- prefer `selection_range_json`
- fallback to `range_json`
- fail clearly if neither exists

---

## Example reference request shape

The conceptual request looks like this:

```json
{
  "textDocument": {
    "uri": "file:///workspace/project/app/services/auth.py"
  },
  "position": {
    "line": 20,
    "character": 8
  },
  "context": {
    "includeDeclaration": false
  }
}
```

### Why `includeDeclaration` should be false

Because you usually want usage sites, not the declaration itself.
That keeps the reference graph cleaner.

---

## Location mapping problem

This is the hardest part of the phase.

The LSP returns locations.
Your graph stores symbols.
You need to map each location to the symbol that contains that usage site.

That means:
- identify the file
- find graph nodes in that file
- choose the smallest node range that contains the usage
- if none contain it, fall back to the module node

This gives you a useful `from_id`.

The target symbol is already known.
That gives you the `to_id`.

So one usage becomes one `references` edge:
- `from_id` = symbol containing the usage
- `to_id` = referenced target symbol

---

## Mapping strategy

Use a practical rule:

1. convert the LSP `uri` to a repo-relative file path or matching file record
2. load all nodes for that file
3. check which node ranges contain the usage range
4. pick the smallest containing node
5. if no symbol contains it, use the module node for the file
6. record confidence based on match quality

### Why smallest containing node

If a usage sits inside a method, you want the method, not the whole file.
That makes reference edges much more useful.

---

## Range containment helper

Create this in `lsp/mapper.py`.

```python
def range_contains(outer: dict, inner: dict) -> bool:
    os = outer["start"]
    oe = outer["end"]
    ins = inner["start"]
    ine = inner["end"]

    return (
        (os["line"], os["character"]) <= (ins["line"], ins["character"]) and
        (oe["line"], oe["character"]) >= (ine["line"], ine["character"])
    )
```

### Why this matters

This is the core primitive for mapping usage locations to internal symbols.

---

## Smallest-containing-symbol helper

```python
def pick_smallest_containing_symbol(symbols_in_file: list[dict], usage_range: dict) -> dict | None:
    containing = [
        symbol for symbol in symbols_in_file
        if symbol.get("range_json") and range_contains(symbol["range_json"], usage_range)
    ]

    if not containing:
        return None

    containing.sort(
        key=lambda symbol: (
            symbol["range_json"]["end"]["line"] - symbol["range_json"]["start"]["line"],
            symbol["range_json"]["end"]["character"] - symbol["range_json"]["start"]["character"],
        )
    )

    return containing
```

### Important note

This is not mathematically perfect, but it is good enough for v1.
Do not overcomplicate it.

---

## Module fallback strategy

Sometimes no function or method range will contain the usage.

Examples:
- top-level executable code
- weird formatting or partial mapping issues
- unresolved range edge cases

In that case:
- fall back to the module node for that file

### Why this is okay

A module-level reference edge is still more useful than losing the reference entirely.

### Confidence rule

If you fall back to module-level containment:
- reduce confidence slightly

Example:
- exact symbol containment: `0.9`
- module fallback: `0.7`

---

## `references` edge model

Use the existing `Edge` shape with:

- `kind = "references"`
- `from_id = containing symbol`
- `to_id = referenced target symbol`
- `source = "lsp"`

Recommended example:

```python
{
  "id": "edge:repo:project:references:symA->symB:44:15",
  "repo_id": "repo:project",
  "kind": "references",
  "from_id": "sym:repo:project:function:app.tasks.run_job",
  "to_id": "sym:repo:project:function:app.services.jobs.execute_job",
  "source": "lsp",
  "confidence": 0.9,
  "evidence_file_id": "file:app/tasks.py",
  "evidence_uri": "file:///workspace/project/app/tasks.py",
  "evidence_range_json": {
    "start": {"line": 44, "character": 15},
    "end": {"line": 44, "character": 26}
  },
  "payload_json": {},
  "last_indexed_at": "2026-03-23T22:00:00Z"
}
```

---

## Edge ID rule for references

A good ID should include:
- repo
- kind
- from symbol
- to symbol
- evidence anchor

Example:

```text
edge:{repo_id}:references:{from_id}->{to_id}:{line}:{character}
```

### Why this works

It avoids collisions when:
- one symbol references another multiple times
- different usage sites exist in the same file

---

## Reference enrichment flow

The enrichment logic for one target symbol should look like this:

1. load target symbol
2. resolve declaration position
3. call the LSP for references
4. for each returned location:
   - resolve file record
   - get file symbols
   - map to smallest containing symbol
   - build a `references` edge
5. replace old reference edges for that target if needed
6. persist new reference edges
7. return summary stats

---

## Refresh strategy

You need a policy for updating references.

There are two valid options.

## Option A: On-demand refresh per symbol

When a caller asks for references of a symbol:
- fetch or recompute them on demand

Pros:
- cheaper initially
- easier to implement

Cons:
- inconsistent freshness across symbols

## Option B: Enrich during indexing

When indexing or reindexing a file or repo:
- refresh references for touched symbols

Pros:
- more consistent graph state

Cons:
- more expensive and more orchestration complexity

My blunt recommendation for v1:
- start with Option A
- add broader refresh later if needed

This keeps the system cheaper and simpler.

---

## Replacement strategy for references

When refreshing references for one target symbol, avoid duplicate old edges.

Recommended helper:
- delete previous `references` edges where `to_id = target_symbol_id`
- insert fresh ones

### Why `to_id`

Because the enrichment is for “who references this target”.
That makes replacement by `to_id` practical.

### Important caveat

If later you enrich references from both directions or in batches, revisit this.
For v1, replacement by target symbol is fine.

---

## Example enrichment function sketch

```python
def enrich_references_for_symbol(conn, lsp_client, target_symbol: dict) -> dict:
    position = get_reference_query_position(target_symbol)
    locations = lsp_client.find_references(
        uri=target_symbol["uri"],
        position=position,
        include_declaration=False,
    )

    new_edges = []

    for location in locations:
        file_record = resolve_file_by_uri(conn, location["uri"])
        if file_record is None:
            continue

        symbols_in_file = list_nodes_for_file(conn, file_record["id"])
        usage_range = location["range"]

        source_symbol = pick_smallest_containing_symbol(symbols_in_file, usage_range)
        confidence = 0.9

        if source_symbol is None:
            source_symbol = find_module_node_for_file(symbols_in_file)
            confidence = 0.7

        if source_symbol is None:
            continue

        edge = build_reference_edge(
            repo_id=target_symbol["repo_id"],
            from_symbol_id=source_symbol["id"],
            to_symbol_id=target_symbol["id"],
            evidence_file_id=file_record["id"],
            evidence_uri=location["uri"],
            evidence_range=usage_range,
            confidence=confidence,
        )
        new_edges.append(edge)

    replace_reference_edges_for_target(conn, target_symbol["id"], new_edges)

    return build_reference_stats(conn, target_symbol["id"])
```

This is enough for a v1 contract.

---

## File resolution helper

You need a clean way to map a LSP URI back to a stored file record.

Recommended helper in `resolver.py` or `mapper.py`:

```python
def resolve_file_by_uri(conn, uri: str):
    ...
```

### Expected behavior

- find the stored `FileRecord` with the same `uri`
- return `None` if not found

### Important rule

Do not use fuzzy path matching if exact URI matching works.
Stay strict where possible.

---

## Module lookup helper

When symbol containment fails, you need a module fallback.

Recommended helper:

```python
def find_module_node_for_file(symbols_in_file: list[dict]) -> dict | None:
    ...
```

Expected behavior:
- return the node with `kind == "module"` if present
- otherwise return `None`

---

## Graph-level reference queries

Add `graph/references.py`.

Recommended functions:

```python
def list_reference_edges_for_target(conn, target_id: str) -> list[dict]:
    ...

def list_referenced_by(conn, target_id: str) -> list[dict]:
    ...

def list_references_from_symbol(conn, source_id: str) -> list[dict]:
    ...

def build_reference_stats(conn, target_id: str) -> dict:
    ...
```

### Why both `list_reference_edges_for_target` and `list_referenced_by`

They may initially look similar, but one can return edges and the other can return source symbols or a richer caller-oriented view if you want later.
The separation is useful.

---

## Reference stats design

You want cheap summary facts.

Recommended output shape:

```python
{
  "reference_count": 14,
  "referencing_file_count": 6,
  "referencing_module_count": 4,
  "available": True,
  "last_refreshed_at": "2026-03-23T22:10:00Z"
}
```

### How to compute it

From `references` edges where `to_id = target_symbol_id`:
- count edges
- count unique `evidence_file_id`
- count unique source module parents or module-qualified names

### Why this matters

These stats are exactly the kind of signal the risk engine will use later.

---

## Updating `SymbolContext`

Phase 5 already created a `reference_summary` placeholder.

Now phase 6 should enrich it.

When building symbol context:
- fetch reference stats if available
- include them in `reference_summary`

Example:

```python
{
  "reference_count": 14,
  "referencing_file_count": 6,
  "referencing_module_count": 4,
  "available": True,
  "last_refreshed_at": "2026-03-23T22:10:00Z"
}
```

### Important rule

If references have never been enriched for the symbol:
- return `available = False`
- do not fake zero as if it were fresh truth

That distinction matters.

---

## Confidence rules for reference edges

Use simple confidence rules.

Suggested v1 rules:

- exact containing symbol match: `0.9`
- module fallback match: `0.7`
- weird partial match: `0.5`

### Why confidence matters here

LSP returns locations, but your graph mapping adds interpretation.
That interpretation is not always perfect.

Be honest about that.

---

## Handling duplicate reference locations

Language servers may return duplicate or near-duplicate results in some cases.

You should deduplicate by:
- target symbol
- source symbol
- evidence URI
- evidence start position

### Why

You want one stored edge per concrete usage site, not noisy duplicates.

---

## Handling self references

Sometimes a symbol may reference itself or appear in contexts that map back to itself.

You have two options:

## Option A: keep self references

Pros:
- honest
- fully preserves returned data

Cons:
- can add noise

## Option B: filter self references

Pros:
- cleaner stats in some cases

Cons:
- may hide useful recursion or self-usage patterns

My recommendation:
- keep them for now
- only filter later if you find they hurt more than they help

Just be consistent.

---

## CLI additions for this phase

Add commands like:

### `refresh-references`

```text
repo-context refresh-references <node-id>
```

What it does:
- refreshes references for one target symbol
- prints counts

### `show-references`

```text
repo-context show-references <node-id>
```

What it does:
- shows incoming `references` edges targeting the symbol

### `show-referenced-by`

```text
repo-context show-referenced-by <node-id>
```

What it does:
- shows source symbols that reference the target

### Why this matters

Before MCP exists, this is the cheapest way to verify enrichment behavior.

---

## Testing plan

This phase needs more careful tests because LSP can be annoying.

### Strategy

Mock or fake the LSP client for most tests.
Do not make all tests depend on a real language server process.

You can still add one integration test later if you want.

---

## Core tests

### `test_get_reference_query_position_prefers_selection_range`

Verify:
- `selection_range` is preferred over `range`

### `test_map_location_to_smallest_containing_symbol`

Verify:
- a usage inside a method maps to the method, not the module

### `test_module_fallback_when_no_symbol_contains_usage`

Verify:
- top-level or unmapped usage falls back to the module node

### `test_build_reference_edge`

Verify:
- edge fields are built correctly
- `kind` is `references`
- `from_id` and `to_id` are correct

### `test_replace_reference_edges_for_target`

Verify:
- old target-specific references are removed
- new ones are inserted cleanly

### `test_reference_stats`

Verify:
- edge count
- unique file count
- unique module count

### `test_context_includes_reference_summary_when_available`

Verify:
- symbol context now exposes enriched stats

### `test_context_marks_reference_summary_unavailable_when_not_refreshed`

Verify:
- it distinguishes unavailable from zero

---

## Suggested test fixtures

Use small repos where references are obvious.

Example:

```text
tests/fixtures/
  references_case/
    app/
      services.py
      api.py
      tasks.py
```

### Example shape

#### `services.py`

```python
def execute_job(job_id: str) -> None:
    pass
```

#### `api.py`

```python
from app.services import execute_job

def handle_request(job_id: str) -> None:
    execute_job(job_id)
```

#### `tasks.py`

```python
from app.services import execute_job

def run_job(job_id: str) -> None:
    execute_job(job_id)
```

This should later produce:
- target symbol: `execute_job`
- references from `handle_request`
- references from `run_job`

That is a great starter case.

---

## Acceptance checklist

Phase 6 is done when all of this is true:

- A symbol’s declaration position can be resolved for LSP queries.
- A minimal LSP client can request references.
- Returned locations can be mapped back to internal symbols.
- `references` edges can be persisted.
- Duplicate old references for a target can be replaced cleanly.
- `referenced_by` can be derived from reverse lookup.
- Reference stats can be computed.
- Symbol context can expose reference summary when available.
- Symbol context can distinguish unavailable references from zero references.
- CLI commands for refreshing and viewing references work.
- Tests pass.
- No risk engine exists yet.
- No MCP server exists yet.

---

## Common mistakes to avoid

### Mistake 1: Trying to support all of LSP

Do not build an IDE.
Build one useful enrichment layer.

### Mistake 2: Treating raw LSP locations as final truth

You want graph edges between stable symbol IDs, not a pile of unconnected coordinates.

### Mistake 3: Storing both `references` and `referenced_by` as separate truths

That is duplication and future inconsistency.
Store one direction, derive the reverse.

### Mistake 4: Pretending mapping confidence is always perfect

Range containment is practical, not magic.
Use confidence scores honestly.

### Mistake 5: Returning zero references when references were never fetched

That is misleading.
Use `available = False` when no enrichment exists yet.

### Mistake 6: Overcomplicating refresh behavior

Start with on-demand refresh per symbol.
You can scale later.

---

## What phase 7 will depend on

The next phase will assume phase 6 already gives it:

- reference counts
- referencing file counts
- referencing module counts
- `referenced_by` queries
- confidence-aware reference edges

Phase 7 will turn those graph facts into a deterministic plan-risk assessment.
That is why this phase matters so much.

---

## Final guidance

This phase is where the graph stops being only structural and starts becoming operationally useful.

Before phase 6:
- you know what exists

After phase 6:
- you know where at least some important things are used

That is a huge upgrade for planning safety.

Keep the LSP layer narrow and disciplined:

- one feature
- one mapping path
- one stored relationship
- one reverse derivation rule

If you do that, you get most of the value without drowning in protocol complexity.
```