```md
# 04-graph-storage.md

## Purpose

This phase turns the extracted symbols and structural relationships into a reliable stored graph.

The AST phase already produced:
- nodes
- edges
- structural hierarchy
- file ownership
- qualified names

Now the goal is to make that data durable, queryable, updatable, and clean.

This phase is about graph storage, not graph intelligence.

It should give you:
- stable node and edge persistence
- upsert behavior
- lookup helpers
- file-level cleanup
- repo-level queries
- the minimum query surface needed for later context building, LSP mapping, and risk evaluation

This phase does **not** do LSP enrichment yet.
It does **not** compute plan risk yet.
It does **not** expose MCP tools yet.

---

## Why this phase matters

Without reliable graph storage, the extraction work is temporary and fragile.

If this layer is weak:
- repeated scans create duplicates
- deleted symbols stay forever
- file updates leave stale edges behind
- later context queries become inconsistent
- LSP mapping has no stable graph to enrich
- risk analysis becomes noisy or wrong

The graph does not need to be fancy here.
It just needs to be correct, inspectable, and predictable.

---

## Phase goals

By the end of this phase, you should have:

- stable storage for nodes and edges in SQLite
- upsert logic for nodes
- upsert logic for edges
- lookup by node ID
- lookup by qualified name
- listing nodes by file
- listing nodes by repo
- listing edges by repo
- listing outgoing edges by node
- listing incoming edges by node
- file-level cleanup for stale nodes and edges
- a basic graph query layer
- CLI commands to inspect graph state
- tests for graph persistence and cleanup

---

## Phase non-goals

Do **not** do any of this in phase 4:

- LSP `references`
- `referenced_by` derivation
- rich symbol context assembly
- risk scoring
- MCP server registration
- watch mode
- semantic call graph logic

This phase is storage and retrieval only.

---

## What already exists from previous phases

This phase assumes you already have:

- phase 1: models, DB bootstrap, CLI shell
- phase 2: repository scanning and file records
- phase 3: AST extraction that produces nodes and structural edges

Phase 4 makes those outputs durable and queryable.

---

## What “graph storage” means here

Do not overcomplicate the word “graph”.

In this phase, “graph storage” just means:

- store nodes in one table
- store edges in one table
- provide simple directional queries
- preserve source, confidence, evidence, and ownership
- handle updates without leaving junk behind

That is enough for v1.

You do **not** need:
- a graph database
- a graph query language
- a graph visualization backend
- fancy traversal engines

SQLite is enough.

---

## Design principles

### Principle 1: SQLite is the source of stored graph truth

In-memory extraction results are temporary.
SQLite is the persistent state.

### Principle 2: Upserts must be deterministic

Re-indexing the same file without changes should not create duplicate nodes or duplicate edges.

### Principle 3: File ownership must be respected

Every node belongs to a file.
Every edge must either belong to a file through evidence or be cleanly attributable.

That makes cleanup possible.

### Principle 4: Cleanup is part of correctness

If a file changes, stale nodes and stale edges from the old extraction must be removable.
Otherwise the graph rots.

### Principle 5: Queries should be boring

You only need simple graph queries at this stage:
- direct lookups
- incoming edges
- outgoing edges
- parent-child retrieval
- file-scoped lists
- repo-scoped lists

---

## Graph storage responsibilities

This phase should provide:

- persistence repositories for nodes and edges
- cleanup helpers
- normalized serialization and deserialization
- graph lookup helpers
- basic integrity rules

It should **not** provide:
- interpretation
- plan assessment
- English explanations
- agent-oriented narratives

---

## Recommended package structure additions

Add these files:

```text
src/
  repo_context/
    storage/
      nodes.py
      edges.py
      graph.py
    graph/
      __init__.py
      queries.py
      filters.py
```

### Why this split

- `storage/nodes.py`: low-level node persistence
- `storage/edges.py`: low-level edge persistence
- `storage/graph.py`: file-level cleanup and small transactional helpers
- `graph/queries.py`: graph-oriented retrieval helpers
- `graph/filters.py`: reusable filtering utilities if needed

Keep storage and query concerns close but not mashed together.

---

## Database schema expectations

This phase assumes your SQLite schema already contains `nodes` and `edges`.

Recommended `nodes` table:

```sql
CREATE TABLE IF NOT EXISTS nodes (
  id TEXT PRIMARY KEY,
  repo_id TEXT NOT NULL,
  file_id TEXT NOT NULL,
  language TEXT NOT NULL,
  kind TEXT NOT NULL,
  name TEXT NOT NULL,
  qualified_name TEXT NOT NULL,
  uri TEXT NOT NULL,
  range_json TEXT,
  selection_range_json TEXT,
  parent_id TEXT,
  visibility_hint TEXT,
  doc_summary TEXT,
  content_hash TEXT NOT NULL,
  semantic_hash TEXT NOT NULL,
  source TEXT NOT NULL,
  confidence REAL NOT NULL,
  payload_json TEXT NOT NULL,
  last_indexed_at TEXT
);
```

Recommended `edges` table:

```sql
CREATE TABLE IF NOT EXISTS edges (
  id TEXT PRIMARY KEY,
  repo_id TEXT NOT NULL,
  kind TEXT NOT NULL,
  from_id TEXT NOT NULL,
  to_id TEXT NOT NULL,
  source TEXT NOT NULL,
  confidence REAL NOT NULL,
  evidence_file_id TEXT,
  evidence_uri TEXT,
  evidence_range_json TEXT,
  payload_json TEXT NOT NULL,
  last_indexed_at TEXT
);
```

### Recommended indexes

Add indexes now.
SQLite still benefits from them.

```sql
CREATE INDEX IF NOT EXISTS idx_nodes_repo_id ON nodes(repo_id);
CREATE INDEX IF NOT EXISTS idx_nodes_file_id ON nodes(file_id);
CREATE INDEX IF NOT EXISTS idx_nodes_qualified_name ON nodes(qualified_name);
CREATE INDEX IF NOT EXISTS idx_nodes_parent_id ON nodes(parent_id);
CREATE INDEX IF NOT EXISTS idx_nodes_kind ON nodes(kind);

CREATE INDEX IF NOT EXISTS idx_edges_repo_id ON edges(repo_id);
CREATE INDEX IF NOT EXISTS idx_edges_from_id ON edges(from_id);
CREATE INDEX IF NOT EXISTS idx_edges_to_id ON edges(to_id);
CREATE INDEX IF NOT EXISTS idx_edges_kind ON edges(kind);
CREATE INDEX IF NOT EXISTS idx_edges_evidence_file_id ON edges(evidence_file_id);
```

### Why these indexes matter

Later phases will often query:
- node by qualified name
- children by parent ID
- outgoing edges by `from_id`
- incoming edges by `to_id`
- file-owned graph records by `file_id`

So index them now.

---

## Node persistence design

The node storage layer should own:

- insert or update node
- bulk insert or update nodes
- fetch node by ID
- fetch node by qualified name
- list nodes by file
- list nodes by repo
- delete nodes by file
- delete nodes by repo if needed later

### Recommended functions in `storage/nodes.py`

```python
def upsert_node(conn, node) -> None:
    ...

def upsert_nodes(conn, nodes: list) -> None:
    ...

def get_node_by_id(conn, node_id: str):
    ...

def get_node_by_qualified_name(conn, repo_id: str, qualified_name: str, kind: str | None = None):
    ...

def list_nodes_for_file(conn, file_id: str) -> list:
    ...

def list_nodes_for_repo(conn, repo_id: str) -> list:
    ...

def list_child_nodes(conn, parent_id: str) -> list:
    ...

def delete_nodes_for_file(conn, file_id: str) -> None:
    ...
```

---

## Edge persistence design

The edge storage layer should own:

- insert or update edge
- bulk insert or update edges
- fetch edge by ID
- list edges by repo
- list outgoing edges by node
- list incoming edges by node
- list edges by file evidence
- delete edges by file evidence

### Recommended functions in `storage/edges.py`

```python
def upsert_edge(conn, edge) -> None:
    ...

def upsert_edges(conn, edges: list) -> None:
    ...

def get_edge_by_id(conn, edge_id: str):
    ...

def list_edges_for_repo(conn, repo_id: str) -> list:
    ...

def list_outgoing_edges(conn, from_id: str, kind: str | None = None) -> list:
    ...

def list_incoming_edges(conn, to_id: str, kind: str | None = None) -> list:
    ...

def list_edges_for_file(conn, file_id: str) -> list:
    ...

def delete_edges_for_file(conn, file_id: str) -> None:
    ...
```

---

## Serialization strategy

Your models likely contain nested data such as:
- ranges
- selection ranges
- payloads
- evidence ranges

These should be serialized to JSON strings for storage.

### Good rule

Serialization should happen in one place, not copied all over the codebase.

Recommended pattern:
- domain model in Python
- storage adapter converts it to row values
- row loader converts back to Python structures

### Why this matters

If serialization is duplicated in five files, bugs multiply fast.

---

## Suggested node row mapping

Use explicit mapping functions.

Example:

```python
import json
from dataclasses import asdict, is_dataclass

def _json_dump(value) -> str | None:
    if value is None:
        return None
    if is_dataclass(value):
        return json.dumps(asdict(value), sort_keys=True)
    return json.dumps(value, sort_keys=True)

def node_to_row(node: dict) -> dict:
    return {
        "id": node["id"],
        "repo_id": node["repo_id"],
        "file_id": node["file_id"],
        "language": node["language"],
        "kind": node["kind"],
        "name": node["name"],
        "qualified_name": node["qualified_name"],
        "uri": node["uri"],
        "range_json": _json_dump(node.get("range_json")),
        "selection_range_json": _json_dump(node.get("selection_range_json")),
        "parent_id": node.get("parent_id"),
        "visibility_hint": node.get("visibility_hint"),
        "doc_summary": node.get("doc_summary"),
        "content_hash": node["content_hash"],
        "semantic_hash": node["semantic_hash"],
        "source": node["source"],
        "confidence": node["confidence"],
        "payload_json": _json_dump(node.get("payload_json", {})),
        "last_indexed_at": node.get("last_indexed_at"),
    }
}
```

### Important note

If your in-memory nodes are dataclasses instead of dicts, that is fine.
The important thing is to keep storage mapping explicit.

---

## Suggested edge row mapping

```python
def edge_to_row(edge: dict) -> dict:
    return {
        "id": edge["id"],
        "repo_id": edge["repo_id"],
        "kind": edge["kind"],
        "from_id": edge["from_id"],
        "to_id": edge["to_id"],
        "source": edge["source"],
        "confidence": edge["confidence"],
        "evidence_file_id": edge.get("evidence_file_id"),
        "evidence_uri": edge.get("evidence_uri"),
        "evidence_range_json": _json_dump(edge.get("evidence_range_json")),
        "payload_json": _json_dump(edge.get("payload_json", {})),
        "last_indexed_at": edge.get("last_indexed_at"),
    }
}
```

---

## Upsert strategy

Use SQLite upserts.

### Why upserts matter

When you re-index a file:
- the same node ID should update, not duplicate
- the same edge ID should update, not duplicate

### Recommended SQL pattern

```sql
INSERT INTO nodes (...)
VALUES (...)
ON CONFLICT(id) DO UPDATE SET
  repo_id = excluded.repo_id,
  file_id = excluded.file_id,
  language = excluded.language,
  kind = excluded.kind,
  name = excluded.name,
  qualified_name = excluded.qualified_name,
  uri = excluded.uri,
  range_json = excluded.range_json,
  selection_range_json = excluded.selection_range_json,
  parent_id = excluded.parent_id,
  visibility_hint = excluded.visibility_hint,
  doc_summary = excluded.doc_summary,
  content_hash = excluded.content_hash,
  semantic_hash = excluded.semantic_hash,
  source = excluded.source,
  confidence = excluded.confidence,
  payload_json = excluded.payload_json,
  last_indexed_at = excluded.last_indexed_at;
```

Do the same pattern for edges.

### Important rule

Use `id` as the main conflict key.
Do not rely only on qualified name uniqueness.

---

## Cleanup strategy

This is one of the most important parts of the phase.

When a file is re-extracted, the system must be able to remove stale graph state tied to the old version of that file.

### What should be cleaned for a file

At minimum:
- nodes owned by that file
- edges whose evidence belongs to that file

### Why `evidence_file_id` matters

Without file-level evidence ownership, cleanup becomes much harder.

### Recommended file refresh sequence

When reprocessing one file:

1. delete edges for that file
2. delete nodes for that file
3. insert fresh nodes
4. insert fresh edges
5. commit transaction

### Why delete then insert

This is often simpler and safer than trying to diff all previous nodes and edges for one file.

For v1, boring wins.

---

## `storage/graph.py` helper

Create one helper to refresh graph state for a file.

Recommended function:

```python
def replace_file_graph(conn, file_id: str, nodes: list, edges: list) -> None:
    ...
```

### Expected behavior

- begin transaction
- delete old file-owned edges
- delete old file-owned nodes
- insert fresh nodes
- insert fresh edges
- commit

### Why this function matters

Later the AST pipeline and LSP enrichment pipeline can both reuse it or build on the same pattern.

---

## Query layer design

This phase should add a simple graph query layer.

The query layer should not be “smart”.
It should just make retrieval less repetitive.

### Recommended functions in `graph/queries.py`

```python
def get_symbol(conn, node_id: str):
    ...

def get_symbol_by_qualified_name(conn, repo_id: str, qualified_name: str, kind: str | None = None):
    ...

def get_parent_symbol(conn, node):
    ...

def get_child_symbols(conn, node_id: str):
    ...

def get_outgoing_edges(conn, node_id: str, kind: str | None = None):
    ...

def get_incoming_edges(conn, node_id: str, kind: str | None = None):
    ...

def get_symbols_for_file(conn, file_id: str):
    ...

def get_repo_graph_stats(conn, repo_id: str):
    ...
```

### Why this matters

Later phases like context assembly and risk assessment should not write raw SQL over and over.

---

## Suggested graph stats query

A tiny summary helper is useful now.

Example output:

```json
{
  "repo_id": "repo:project",
  "node_count": 188,
  "edge_count": 344,
  "module_count": 12,
  "class_count": 25,
  "callable_count": 151
}
```

### Why this is useful

- quick sanity check after indexing
- easy CLI reporting
- simple debugging

---

## Parent-child traversal rules

Because the graph is layered, the basic hierarchy should already be queryable now.

Expected examples:

- module -> classes
- module -> top-level functions
- class -> methods

This can be derived either from:
- `parent_id` on nodes
- `contains` edges

### Recommendation

Support both, but prefer node `parent_id` for direct parent lookup and `contains` edges for explicit structural graph semantics.

Why:
- `parent_id` is efficient for hierarchy
- `contains` edges keep the graph model explicit

That dual representation is acceptable here because they serve slightly different needs.

---

## Integrity expectations

This phase should enforce a few practical integrity rules.

### Rule 1: Every node must belong to a repo and file

No orphan nodes.

### Rule 2: Every edge must belong to a repo

No repo-less edges.

### Rule 3: Edge endpoints should usually exist

For placeholders like unresolved imports or unresolved bases, the target may be a synthetic placeholder ID instead of a real node.
That is okay.

### Rule 4: File cleanup must not leave file-owned junk behind

After replacing a file graph, old nodes and old evidence-owned edges for that file should be gone.

---

## Placeholder target strategy

Not every edge target will be a real stored node yet.

Examples:
- unresolved import target
- unresolved base class
- external dependency symbol

That is fine.

### Good rule

Use clearly synthetic target IDs like:

- `external_or_unresolved:app.core.security`
- `unresolved_base:BaseService`

Do not try to fake these as real nodes unless you actually model them.

### Why this matters

Honest unresolved targets are better than fake resolved ones.

---

## CLI additions for this phase

Add a few inspection-oriented CLI commands.

### Suggested commands

#### `graph-stats`

Usage:
```text
repo-context graph-stats <repo-id>
```

What it does:
- prints counts of nodes and edges by kind

#### `list-nodes`

Usage:
```text
repo-context list-nodes <repo-id>
```

What it does:
- lists stored nodes, maybe with optional filters

#### `list-edges`

Usage:
```text
repo-context list-edges <repo-id>
```

What it does:
- lists stored edges, maybe with optional filters

#### `show-node`

Usage:
```text
repo-context show-node <node-id>
```

What it does:
- prints one node and maybe its immediate parent/children summary

### Why this matters

Before MCP exists, the CLI is your cheapest debugging tool.

---

## Recommended implementation sequence

Build phase 4 in this order:

1. add DB indexes
2. write node row mappers
3. write edge row mappers
4. implement node upsert and fetch helpers
5. implement edge upsert and fetch helpers
6. implement file-level delete helpers
7. implement `replace_file_graph`
8. implement graph query helpers
9. add CLI inspection commands
10. write tests around replacement and retrieval

Do not jump straight to fancy query helpers before the persistence layer is solid.

---

## Example node repository sketch

```python
def upsert_node(conn, node: dict) -> None:
    row = node_to_row(node)
    conn.execute(
        """
        INSERT INTO nodes (
            id, repo_id, file_id, language, kind, name, qualified_name, uri,
            range_json, selection_range_json, parent_id, visibility_hint,
            doc_summary, content_hash, semantic_hash, source, confidence,
            payload_json, last_indexed_at
        ) VALUES (
            :id, :repo_id, :file_id, :language, :kind, :name, :qualified_name, :uri,
            :range_json, :selection_range_json, :parent_id, :visibility_hint,
            :doc_summary, :content_hash, :semantic_hash, :source, :confidence,
            :payload_json, :last_indexed_at
        )
        ON CONFLICT(id) DO UPDATE SET
            repo_id = excluded.repo_id,
            file_id = excluded.file_id,
            language = excluded.language,
            kind = excluded.kind,
            name = excluded.name,
            qualified_name = excluded.qualified_name,
            uri = excluded.uri,
            range_json = excluded.range_json,
            selection_range_json = excluded.selection_range_json,
            parent_id = excluded.parent_id,
            visibility_hint = excluded.visibility_hint,
            doc_summary = excluded.doc_summary,
            content_hash = excluded.content_hash,
            semantic_hash = excluded.semantic_hash,
            source = excluded.source,
            confidence = excluded.confidence,
            payload_json = excluded.payload_json,
            last_indexed_at = excluded.last_indexed_at
        """,
        row,
    )
```

That is enough.
Do not overabstract this away too early.

---

## Example edge repository sketch

```python
def upsert_edge(conn, edge: dict) -> None:
    row = edge_to_row(edge)
    conn.execute(
        """
        INSERT INTO edges (
            id, repo_id, kind, from_id, to_id, source, confidence,
            evidence_file_id, evidence_uri, evidence_range_json,
            payload_json, last_indexed_at
        ) VALUES (
            :id, :repo_id, :kind, :from_id, :to_id, :source, :confidence,
            :evidence_file_id, :evidence_uri, :evidence_range_json,
            :payload_json, :last_indexed_at
        )
        ON CONFLICT(id) DO UPDATE SET
            repo_id = excluded.repo_id,
            kind = excluded.kind,
            from_id = excluded.from_id,
            to_id = excluded.to_id,
            source = excluded.source,
            confidence = excluded.confidence,
            evidence_file_id = excluded.evidence_file_id,
            evidence_uri = excluded.evidence_uri,
            evidence_range_json = excluded.evidence_range_json,
            payload_json = excluded.payload_json,
            last_indexed_at = excluded.last_indexed_at
        """,
        row,
    )
```

---

## Example file graph replacement sketch

```python
def replace_file_graph(conn, file_id: str, nodes: list[dict], edges: list[dict]) -> None:
    try:
        conn.execute("BEGIN")
        conn.execute("DELETE FROM edges WHERE evidence_file_id = ?", (file_id,))
        conn.execute("DELETE FROM nodes WHERE file_id = ?", (file_id,))

        for node in nodes:
            upsert_node(conn, node)

        for edge in edges:
            upsert_edge(conn, edge)

        conn.commit()
    except Exception:
        conn.rollback()
        raise
```

### Important note

This is a simple v1 strategy.
It is not fancy, but it is easy to reason about.

---

## Query examples

### Get node by ID

```sql
SELECT * FROM nodes WHERE id = ?;
```

### Get node by qualified name

```sql
SELECT * FROM nodes
WHERE repo_id = ? AND qualified_name = ?
LIMIT 1;
```

### Get child nodes

```sql
SELECT * FROM nodes
WHERE parent_id = ?
ORDER BY kind, name;
```

### Get outgoing edges

```sql
SELECT * FROM edges
WHERE from_id = ?
ORDER BY kind, to_id;
```

### Get incoming edges

```sql
SELECT * FROM edges
WHERE to_id = ?
ORDER BY kind, from_id;
```

### Get file-owned nodes

```sql
SELECT * FROM nodes
WHERE file_id = ?
ORDER BY kind, qualified_name;
```

These are enough for now.

---

## Testing plan

This phase needs more than smoke tests.
It needs persistence correctness tests.

### `test_upsert_node`

Verify:
- inserting a node works
- reinserting same ID updates instead of duplicating

### `test_upsert_edge`

Verify:
- inserting an edge works
- reinserting same ID updates instead of duplicating

### `test_get_node_by_id`

Verify:
- lookup returns the right node

### `test_get_node_by_qualified_name`

Verify:
- lookup works for a known repo and qualified name

### `test_list_child_nodes`

Verify:
- module returns classes and top-level functions
- class returns methods

### `test_list_outgoing_and_incoming_edges`

Verify:
- directional queries return expected edges

### `test_replace_file_graph`

Verify:
- old file-owned nodes are removed
- old file-owned edges are removed
- new nodes and edges are inserted
- unrelated files remain untouched

### `test_graph_stats`

Verify:
- counts match inserted data

### `test_placeholder_targets_do_not_break_queries`

Verify:
- unresolved targets in `to_id` do not crash graph queries

---

## Suggested fixture usage

Reuse your phase 3 fixtures.

Good test shape:
1. scan fixture repo
2. extract AST nodes and edges
3. persist them
4. query them
5. assert exact results

That gives you end-to-end confidence without yet involving LSP or MCP.

---

## Acceptance checklist

Phase 4 is done when all of this is true:

- Nodes can be inserted and updated without duplication.
- Edges can be inserted and updated without duplication.
- Nodes can be queried by ID.
- Nodes can be queried by qualified name.
- Child nodes can be listed by parent.
- Outgoing edges can be listed by source node.
- Incoming edges can be listed by target node.
- File-owned graph data can be replaced cleanly.
- Graph stats can be computed.
- SQLite indexes exist.
- CLI graph inspection commands work.
- Tests pass.
- No LSP enrichment exists yet.
- No plan risk engine exists yet.
- No MCP server exists yet.

---

## Common mistakes to avoid

### Mistake 1: Treating storage like business logic

Storage should persist and retrieve data.
It should not become the risk engine or context builder.

### Mistake 2: Forgetting cleanup

If file replacement leaves old nodes or edges around, the graph becomes untrustworthy fast.

### Mistake 3: Hiding unresolved targets

Placeholder targets are fine.
Fake resolution is not.

### Mistake 4: Overengineering a graph abstraction

You do not need a giant repository pattern hierarchy here.
Simple explicit functions are better.

### Mistake 5: No indexes

SQLite is fine, but without indexes some common queries will get worse fast as the repo grows.

### Mistake 6: Mixing raw SQL everywhere

Keep query logic grouped in storage and graph query modules.
Do not scatter SQL across CLI and parsing code.

---

## What phase 5 will depend on

The next phase will assume phase 4 already gives it:

- stable stored nodes
- stable stored edges
- direct lookup helpers
- directional edge queries
- child lookup
- clean replacement behavior

Phase 5 will start assembling symbol context from this stored graph.
If the graph storage layer is unreliable, context assembly will be unreliable too.

---

## Final guidance

This phase is not glamorous.

That is fine.

You are not trying to prove the system is intelligent here.
You are trying to prove the graph is:

- durable
- queryable
- replaceable
- clean

That is the real job of phase 4.

If you finish this phase and the graph feels boring but trustworthy, you did it right.
```