```md
# 01-bootstrap.md

## Purpose

This phase creates the foundation of the project.

The goal is to establish:

- the Python package layout
- the core schema models
- the SQLite initialization layer
- the CLI entry point
- the development rules and boundaries

This phase does **not** parse repositories, talk to a language server, build graph context, or expose MCP tools yet.

The whole point is to make later phases easier and less fragile.

---

## Why this phase matters

This project combines several parts that can get messy fast:

- AST-based structure extraction
- LSP-based reference enrichment
- a layered graph with modules, classes, and callables
- deterministic risk evaluation
- an MCP server used by an AI agent before code changes

If phase 1 is vague, every later phase will drift.

The boring truth is:

- bad naming now becomes bad graph IDs later
- weak schema design now becomes storage pain later
- sloppy package boundaries now become rewrite fuel later

So this phase is about getting the backbone right.

---

## Phase goals

By the end of this phase, you should have:

- a runnable Python project
- a stable folder structure
- core dataclass models
- a working SQLite bootstrap
- a minimal CLI
- a minimal test suite
- clear boundaries for future subsystems

---

## Phase non-goals

Do **not** do any of this in phase 1:

- repository scanning
- AST parsing
- symbol extraction
- LSP integration
- graph context building
- risk scoring
- MCP tool registration
- file watching
- fancy summaries
- AI-generated explanations

If you start doing those now, you are skipping the foundation step.

---

## System boundaries to lock now

Even though most subsystems are not implemented yet, you should define the package boundaries now.

Future subsystems:

- `models`: canonical data contracts
- `storage`: SQLite and persistence logic
- `cli`: local developer entry points
- `parsing`: repository scanning and AST extraction
- `graph`: graph storage helpers and context assembly
- `lsp`: reference enrichment
- `indexing`: full and incremental indexing orchestration
- `mcp`: tool server for the agent

Important rule:

- `models` should contain structure, not behavior-heavy orchestration
- `storage` should not know AST internals
- `cli` should not contain core business logic
- `lsp` should enrich the graph, not define the graph
- `mcp` should expose deterministic tools, not become the source of truth

That separation is what keeps the system modular enough to support other languages later.

---

## Recommended repository structure

Use this exact starting layout:

```text
repo-context-mcp/
  01-bootstrap.md
  pyproject.toml
  .gitignore
  src/
    repo_context/
      __init__.py
      config.py
      models/
        __init__.py
        common.py
        repo.py
        file.py
        node.py
        edge.py
        context.py
        assessment.py
      storage/
        __init__.py
        db.py
        migrations.py
      cli/
        __init__.py
        main.py
  tests/
    __init__.py
    test_smoke.py
    test_db_init.py
    test_models.py
```

### Why this structure

- `models/` gives you one canonical schema layer
- `storage/` isolates SQLite setup and future repositories
- `cli/` gives you a developer-facing entry point before MCP exists
- `tests/` forces early discipline

Do not add random utility folders yet.
Keep it tight.

---

## Tech choices

## Python version

Use Python 3.11 or newer.

Why:

- modern typing is better
- dataclasses are easy and solid
- future AST and async tooling will be simpler
- you avoid older version noise

## Package management

Use a plain `pyproject.toml`.

Do not overcomplicate packaging in phase 1.

## Model strategy

Use dataclasses first.

Why:

- cheap
- readable
- easy to inspect
- easy to refactor
- enough for an internal canonical schema

You can add Pydantic later at the MCP boundary if you really want stronger validation there.

## Database choice

Use SQLite.

Why:

- local
- zero setup
- cheap
- inspectable
- enough for files, nodes, edges, and index runs

Do not use a graph database in v1.

---

## Development rules

These rules start in phase 1 and continue through the project.

### Rule 1: Canonical schema first

All later subsystems must target the same models.

If the graph, AST layer, LSP layer, and MCP layer all invent their own shapes, the project will rot.

### Rule 2: IDs over names

Names are for humans.
IDs are for systems.

Every important entity should have a stable ID.

### Rule 3: Provenance matters

Every node and edge should later record where it came from.

Examples:
- `python-ast`
- `lsp`
- `derived`

So the model design should already leave room for `source`.

### Rule 4: Confidence matters

Some data is direct and strong.
Some data is inferred and weaker.

The schema should already include confidence-friendly fields.

### Rule 5: Internal schema is the source of truth

Do not make raw LSP objects your database schema.
Do not make AST node objects your database schema.

Normalize everything into your own models.

### Rule 6: Keep the server deterministic

Later, MCP should return:
- facts
- issue codes
- scores
- decisions

The AI agent can explain those facts in natural language.
The server should not pretend to be an LLM.

### Rule 7: Keep it inspectable

You should be able to:
- open the database
- inspect rows
- understand state
- debug problems without guessing

---

## Initial config strategy

Create a small `config.py` now.

It should centralize:

- database path
- default ignored directories
- default file extensions
- app name
- debug mode

Example:

```python
from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class AppConfig:
    app_name: str = "repo-context-mcp"
    db_path: Path = Path("repo_context.db")
    debug: bool = True
    ignored_dirs: tuple[str, ...] = (
        ".git",
        ".venv",
        "venv",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "build",
        "dist",
        "node_modules",
    )
    supported_extensions: tuple[str, ...] = (".py",)
```

### Why this exists

Even in phase 1, you want one place for app-level defaults.
Otherwise later code will hardcode these values in multiple modules.

---

## Canonical models

This section defines the core schema objects you should implement in phase 1.

These models should exist now even if many fields are not fully used until later phases.

---

## Model: Position

A `Position` represents a single location in a file.

### Schema

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Position:
    line: int
    character: int
```

### Field commentary

#### `line`

Zero-based line number.

What it does:
- points to a line inside a file

Why it matters:
- required for ranges
- required for declaration mapping
- compatible with later LSP integration

#### `character`

Zero-based character offset within the line.

What it does:
- points to a column position inside the line

Why it matters:
- needed for precise selection ranges
- needed for mapping LSP reference locations later

### Notes

Internally, store positions in zero-based form.
Later, AST extraction should convert Python AST line data into this normalized form.

---

## Model: Range

A `Range` represents a span in a file.

### Schema

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Range:
    start: Position
    end: Position
```

### Field commentary

#### `start`

The first position in the span.

What it does:
- marks where the declaration or evidence starts

Why it matters:
- needed for source slicing
- needed for LSP requests later

#### `end`

The last position in the span.

What it does:
- marks where the declaration or evidence ends

Why it matters:
- needed to know the full extent of a symbol or reference

---

## Model: RepoRecord

Represents one repository tracked by the system.

### Schema

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class RepoRecord:
    id: str
    root_path: str
    name: str
    default_language: str
    created_at: str
    last_indexed_at: Optional[str] = None
```

### Field commentary

#### `id`

Stable repository identifier.

What it does:
- uniquely identifies the repository inside the system

Why it matters:
- files, nodes, edges, and index runs all need repo ownership

#### `root_path`

Canonical repository root path.

What it does:
- tells the system where the repo lives on disk

Why it matters:
- later file discovery and module-path derivation depend on it

#### `name`

Human-friendly repository name.

What it does:
- makes CLI output and logs readable

Why it matters:
- helpful in multi-repo support later

#### `default_language`

Primary language of the repo.

What it does:
- records the main language adapter expected for the repo

Why it matters:
- version 1 starts with Python, but the architecture should support more languages later

#### `created_at`

Creation timestamp.

What it does:
- records when the repo record was created

Why it matters:
- basic metadata and debugging

#### `last_indexed_at`

Last successful indexing timestamp.

What it does:
- records freshness

Why it matters:
- later risk evaluation should be able to detect stale context

---

## Model: FileRecord

Represents one tracked source file.

### Schema

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class FileRecord:
    id: str
    repo_id: str
    file_path: str
    uri: str
    module_path: str
    language: str
    content_hash: str
    size_bytes: int
    last_modified_at: str
    last_indexed_at: Optional[str] = None
```

### Field commentary

#### `id`

Stable file identifier.

What it does:
- uniquely identifies the file record

Why it matters:
- nodes and edges can later refer back to the owning file

#### `repo_id`

Owning repository ID.

What it does:
- links the file to its repository

Why it matters:
- prevents collisions across repositories

#### `file_path`

Repository-relative file path.

What it does:
- identifies the file inside the repo

Why it matters:
- the scanner and storage layer should use this as the main local file identity

#### `uri`

LSP-compatible file URI.

What it does:
- gives the external document identity used by language-server requests later

Why it matters:
- LSP works with URIs, not repo-relative paths

#### `module_path`

Import-like Python module path.

What it does:
- gives the logical module identity for the file

Why it matters:
- useful later for imports, structure, and graph queries

#### `language`

Language of the file.

What it does:
- identifies which parser or adapter should handle it

Why it matters:
- needed for future multi-language support

#### `content_hash`

Hash of the file contents.

What it does:
- changes when file content changes

Why it matters:
- needed later for incremental indexing

#### `size_bytes`

File size in bytes.

What it does:
- records file size metadata

Why it matters:
- useful for stats and sanity checks

#### `last_modified_at`

Filesystem modification timestamp.

What it does:
- stores when the file was last changed on disk

Why it matters:
- later helps decide whether reindexing is needed

#### `last_indexed_at`

Last successful indexing timestamp for this file.

What it does:
- stores freshness of indexed data for the file

Why it matters:
- lets the system detect stale file-level context later

---

## Model: SymbolNode

This is the base model for anything the graph can reason about.

It is the parent idea behind:
- module nodes
- class nodes
- callable nodes

### Schema

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class SymbolNode:
    id: str
    repo_id: str
    file_id: str
    language: str
    kind: str
    name: str
    qualified_name: str
    uri: str
    range_json: Optional[str]
    selection_range_json: Optional[str]
    parent_id: Optional[str]
    visibility_hint: Optional[str]
    doc_summary: Optional[str]
    content_hash: str
    semantic_hash: str
    source: str
    confidence: float
    payload_json: str
    last_indexed_at: Optional[str] = None
```

### Why store some fields as JSON strings in phase 1

In the raw dataclass, you can choose to keep `Range` objects directly in memory.
But for database insertion later, it is practical to already think in terms of serialized storage for:
- `range`
- `selection_range`
- extra payload

That is why the model above is storage-friendly.

If you prefer a cleaner in-memory shape, you can define a domain model and a DB row model separately.
That is actually cleaner, but also slightly more work.

For phase 1, either approach is acceptable.
Just be consistent.

### Field commentary

#### `id`

Stable symbol ID.

What it does:
- uniquely identifies the symbol in the graph

Why it matters:
- graph edges should point to IDs, not names

#### `repo_id`

Owning repository ID.

What it does:
- links the symbol to its repo

Why it matters:
- prevents ID ambiguity across repos

#### `file_id`

Owning file ID.

What it does:
- records which file contains the symbol declaration

Why it matters:
- useful for file cleanup and graph traversal

#### `language`

Source language.

What it does:
- identifies the language adapter that produced the symbol

Why it matters:
- future-proofing for multi-language support

#### `kind`

Symbol kind.

Version 1 likely values:
- `module`
- `class`
- `function`
- `async_function`
- `method`
- `async_method`

What it does:
- describes what the symbol is

Why it matters:
- graph queries and risk logic depend on kind

#### `name`

Local declared name.

What it does:
- stores the simple human-facing symbol name

Why it matters:
- good for display and search

#### `qualified_name`

Full logical path-like name.

Example:
`app.services.auth.AuthService.login`

What it does:
- provides a more stable and unique identity than `name`

Why it matters:
- direct names collide easily
- qualified names are much better for lookups

#### `uri`

File URI where the symbol lives.

What it does:
- points to the document containing the symbol

Why it matters:
- needed for LSP operations later

#### `range_json`

Serialized full declaration range.

What it does:
- stores the whole span of the declaration

Why it matters:
- needed for source slicing and range containment later

#### `selection_range_json`

Serialized focused range for the name token or the most relevant symbol location.

What it does:
- stores the smaller “jump here” span

Why it matters:
- best location for later LSP reference requests

#### `parent_id`

ID of the enclosing parent symbol.

Examples:
- method parent is a class
- class parent is a module

What it does:
- encodes hierarchy

Why it matters:
- the graph is layered, so parent-child structure matters

#### `visibility_hint`

Best-effort visibility classification.

Likely future values:
- `public`
- `protected_like`
- `private_like`
- `module`

What it does:
- stores a heuristic visibility label

Why it matters:
- useful later for risk assessment

#### `doc_summary`

Short description from a docstring or comment.

What it does:
- stores a compact human-readable purpose hint

Why it matters:
- helps the agent quickly understand symbol intent later

#### `content_hash`

Hash of the raw source declaration.

What it does:
- changes when the declaration text changes

Why it matters:
- useful for incremental updates later

#### `semantic_hash`

Hash of the meaningful normalized content.

What it does:
- aims to change only when structure or signature meaning changes

Why it matters:
- lets you distinguish cosmetic changes from meaningful ones later

#### `source`

Where the node came from.

Examples:
- `python-ast`
- `lsp`
- `merged`

What it does:
- records provenance

Why it matters:
- useful for debugging and trust

#### `confidence`

Trust score for the node.

What it does:
- indicates how trustworthy the data is

Why it matters:
- low-confidence data should increase caution later

#### `payload_json`

Extra structured data stored as JSON.

What it does:
- stores symbol-type-specific fields without bloating the base schema

Why it matters:
- useful for module-specific, class-specific, or callable-specific metadata

#### `last_indexed_at`

Last successful indexing time.

What it does:
- stores freshness

Why it matters:
- later the agent should know if the node may be stale

---

## Model: Edge

Represents a relationship between two nodes.

### Schema

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class Edge:
    id: str
    repo_id: str
    kind: str
    from_id: str
    to_id: str
    source: str
    confidence: float
    evidence_file_id: Optional[str]
    evidence_uri: Optional[str]
    evidence_range_json: Optional[str]
    payload_json: str
    last_indexed_at: Optional[str] = None
```

### Field commentary

#### `id`

Stable edge identifier.

What it does:
- uniquely identifies the relationship

Why it matters:
- useful for updates, deduplication, and traceability

#### `repo_id`

Owning repository.

What it does:
- ties the relationship to one repo

Why it matters:
- avoids cross-repo confusion

#### `kind`

Relationship type.

Version 1 planned types:
- `contains`
- `imports`
- `inherits`
- `references`

What it does:
- tells the graph what the relationship means

Why it matters:
- different edges have different planning implications

#### `from_id`

Source node ID.

What it does:
- marks where the edge starts

Why it matters:
- the graph is directional

#### `to_id`

Target node ID.

What it does:
- marks where the edge ends

Why it matters:
- needed for traversal, dependency checks, and reverse queries

#### `source`

Where the relationship came from.

Examples:
- `python-ast`
- `lsp`
- `derived`

What it does:
- records provenance

Why it matters:
- some relationships are stronger than others

#### `confidence`

Trust score for the relationship.

What it does:
- records how reliable the edge is

Why it matters:
- useful later in risk scoring

#### `evidence_file_id`

File that contains the evidence for the relationship.

What it does:
- records the supporting file

Why it matters:
- useful for debugging and traceability

#### `evidence_uri`

File URI for the evidence.

What it does:
- stores an LSP-friendly document reference

Why it matters:
- helpful later for reference edges from LSP

#### `evidence_range_json`

Serialized evidence range.

What it does:
- stores the location of the supporting usage or declaration

Why it matters:
- useful later when mapping references

#### `payload_json`

Extra edge-specific metadata.

What it does:
- stores relationship-specific extra details

Why it matters:
- keeps the base edge schema stable

#### `last_indexed_at`

Last update timestamp.

What it does:
- stores freshness

Why it matters:
- later stale edges should be detectable

---

## Model: SymbolContext

This is the assembled graph context that will later be returned by the MCP layer.

You should define it now even if phase 1 does not populate it yet.

### Schema

```python
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class SymbolContext:
    focus_symbol_id: str
    parent_symbol_id: Optional[str] = None
    child_symbol_ids: list[str] = field(default_factory=list)
    outgoing_edge_ids: list[str] = field(default_factory=list)
    incoming_edge_ids: list[str] = field(default_factory=list)
    reference_count: int = 0
    referencing_file_count: int = 0
    freshness_status: str = "unknown"
    confidence_score: float = 0.0
```

### Why define it now

Because later the graph layer and MCP layer should both target the same context shape.

### Field commentary

#### `focus_symbol_id`
The primary symbol the context is about.

#### `parent_symbol_id`
Immediate parent symbol if one exists.

#### `child_symbol_ids`
Immediate children of the symbol.

#### `outgoing_edge_ids`
IDs of edges starting from the focus symbol.

#### `incoming_edge_ids`
IDs of edges ending at the focus symbol.

#### `reference_count`
Total number of reference edges found later.

#### `referencing_file_count`
Number of unique files referencing the symbol later.

#### `freshness_status`
Quick freshness label such as `fresh`, `stale`, or `unknown`.

#### `confidence_score`
Overall confidence in the assembled context.

---

## Model: PlanAssessment

This is the deterministic assessment shape the MCP layer will later return.

Define it now so everything aims at one stable contract.

### Schema

```python
from dataclasses import dataclass, field

@dataclass
class PlanAssessment:
    plan_summary: str
    target_symbols: list[str] = field(default_factory=list)
    resolved_symbols: list[str] = field(default_factory=list)
    unresolved_targets: list[str] = field(default_factory=list)
    facts_json: str = "{}"
    issues: list[str] = field(default_factory=list)
    risk_score: int = 0
    decision: str = "unknown"
```

### Field commentary

#### `plan_summary`

Short description of the planned change.

What it does:
- anchors the assessment to the user or agent intent

Why it matters:
- a risk score without a plan description is useless

#### `target_symbols`

Symbols the plan intends to touch.

What it does:
- stores the requested targets

Why it matters:
- later risk evaluation starts from these

#### `resolved_symbols`

Targets successfully mapped to graph nodes.

What it does:
- stores known targets

Why it matters:
- helps distinguish known context from unknown context

#### `unresolved_targets`

Plan targets that could not be mapped.

What it does:
- records missing context

Why it matters:
- unresolved targets should later increase caution

#### `facts_json`

Serialized structured facts used to compute the assessment.

What it does:
- stores deterministic reasoning inputs

Why it matters:
- the server later should compute facts, not vibes

#### `issues`

List of issue codes.

Examples later:
- `high_reference_count`
- `cross_module_impact`
- `public_surface_change`

What it does:
- records the main triggered concerns

Why it matters:
- the agent can later explain these in natural language

#### `risk_score`

Numeric risk score.

What it does:
- represents overall risk severity

Why it matters:
- useful for thresholds and tool responses later

#### `decision`

Deterministic decision label.

Example later:
- `safe_enough`
- `review_required`
- `blocked_missing_context`

What it does:
- gives a simple actionable output

Why it matters:
- the server should later make deterministic recommendations

---

## Serialization helpers

You should create tiny helpers in `models/common.py` or a nearby utility file.

Example:

```python
import json
from dataclasses import asdict, is_dataclass

def to_json(value) -> str:
    if is_dataclass(value):
        return json.dumps(asdict(value), sort_keys=True)
    return json.dumps(value, sort_keys=True)

def from_json(data: str):
    return json.loads(data)
```

### Why this matters

You will later store:
- ranges
- selection ranges
- symbol payloads
- edge payloads
- plan facts

So you want a consistent serialization habit from the start.

---

## Database bootstrap

Phase 1 should create the SQLite database and initialize the base tables.

Do **not** wait until later.
Storage shape is part of the foundation.

### Database file

Default:
- `repo_context.db`

### Minimal tables to create now

- `repos`
- `files`
- `nodes`
- `edges`
- `index_runs`

Optional later:
- `plan_assessments`

### Schema

```sql
CREATE TABLE IF NOT EXISTS repos (
  id TEXT PRIMARY KEY,
  root_path TEXT NOT NULL,
  name TEXT NOT NULL,
  default_language TEXT NOT NULL,
  created_at TEXT NOT NULL,
  last_indexed_at TEXT
);

CREATE TABLE IF NOT EXISTS files (
  id TEXT PRIMARY KEY,
  repo_id TEXT NOT NULL,
  file_path TEXT NOT NULL,
  uri TEXT NOT NULL,
  module_path TEXT NOT NULL,
  language TEXT NOT NULL,
  content_hash TEXT NOT NULL,
  size_bytes INTEGER NOT NULL,
  last_modified_at TEXT NOT NULL,
  last_indexed_at TEXT
);

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

CREATE TABLE IF NOT EXISTS index_runs (
  id TEXT PRIMARY KEY,
  repo_id TEXT NOT NULL,
  mode TEXT NOT NULL,
  status TEXT NOT NULL,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  changed_files_json TEXT NOT NULL,
  stats_json TEXT NOT NULL,
  errors_json TEXT NOT NULL
);
```

### Why these tables already exist in phase 1

Because the rest of the system will depend on them.
You do not want AST extraction or LSP code inventing storage shape later.

---

## Storage module responsibilities

In phase 1, `storage/db.py` should do only a few things:

- open a SQLite connection
- set practical connection options
- run migrations
- expose a helper to get a connection

### Example structure

```python
import sqlite3
from pathlib import Path

def get_connection(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn
```

Then `storage/migrations.py` should hold the schema SQL and a simple initializer:

```python
def initialize_database(conn):
    ...
```

### Important rule

Do not mix query logic and migration logic in the same giant file.

---

## CLI bootstrap

You need a tiny CLI now so you can test the app locally without MCP.

### Initial commands

Phase 1 only needs something like:

- `init-db`
- `doctor`

### Example expectations

#### `init-db`

What it does:
- creates the SQLite DB
- runs schema initialization
- prints success or failure

#### `doctor`

What it does:
- checks whether the DB exists
- checks whether the base tables exist
- prints a small health report

### Why this matters

The CLI is the cheapest way to validate system setup before adding parsing or MCP.

---

## Suggested `pyproject.toml`

Keep it simple.

Example:

```toml
[project]
name = "repo-context-mcp"
version = "0.1.0"
description = "Python-first repository context engine for safer AI-assisted code planning"
requires-python = ">=3.11"

[project.scripts]
repo-context = "repo_context.cli.main:main"

[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"
```

If you want dev dependencies, keep them minimal.

Example tools:
- `pytest`
- `ruff`

Do not stuff phase 1 with too much tooling.

---

## Suggested `.gitignore`

```gitignore
__pycache__/
*.pyc
.pytest_cache/
.ruff_cache/
.mypy_cache/
.venv/
venv/
repo_context.db
dist/
build/
```

---

## Basic test plan

You need a very small test suite now.

### `test_smoke.py`

Checks:
- package imports
- CLI main can load

### `test_db_init.py`

Checks:
- DB file is created
- all expected base tables exist

### `test_models.py`

Checks:
- dataclass instances can be created
- JSON serialization helpers work
- required fields behave as expected

### Why tests matter already

Because phase 1 is where you lock contracts.
If the contracts drift, later AI-generated code will drift too.

---

## Recommended first implementation order

Do this in this exact order:

1. Create folder structure.
2. Create `pyproject.toml`.
3. Create `config.py`.
4. Create canonical model files.
5. Create JSON serialization helpers.
6. Create SQLite connection helper.
7. Create migration initializer.
8. Create CLI entry point with `init-db` and `doctor`.
9. Add smoke tests.
10. Run everything locally until it is boring and stable.

Do **not** skip around.

---

## Acceptance checklist

Phase 1 is done when all of this is true:

- The package installs.
- `repo-context init-db` creates a SQLite database.
- `repo-context doctor` reports healthy setup.
- Core models exist in code.
- Base tables exist in the database.
- Tests pass.
- No AST code exists yet.
- No LSP code exists yet.
- No MCP server exists yet.
- The structure is clean enough that phase 2 can begin without reorganizing the repo.

---

## Common mistakes to avoid

### Mistake 1: Building parser code too early

Do not start AST extraction in bootstrap.
That belongs to phase 2 or 3.

### Mistake 2: Letting SQLite shape the domain model

The database is storage.
The model is the domain.
Keep them aligned, but do not think the database schema is the whole system.

### Mistake 3: Using raw LSP shapes as your canonical models

You want LSP-compatible fields later, not an LSP-owned architecture.

### Mistake 4: Overengineering validation

You do not need a huge framework stack just to define basic models.

### Mistake 5: Making the CLI smart

The phase 1 CLI should be tiny.
It is just a setup and sanity-check tool.

### Mistake 6: Skipping tests because “nothing interesting happens yet”

This phase is exactly where tests matter because the contracts are being set.

---

## What phase 2 will depend on

The next phase will assume phase 1 already provides:

- a stable project layout
- a canonical model layer
- a SQLite DB bootstrap
- serialization helpers
- a working CLI shell
- a tested base

If those are weak, phase 2 will start inventing incompatible paths and shapes.

---

## Final guidance

Phase 1 should feel almost boring.

That is good.

You are not trying to prove the system is smart yet.
You are making sure the project has a skeleton that later AST extraction, LSP reference enrichment, graph context building, deterministic risk assessment, and MCP exposure can safely hang on.

If phase 1 feels flashy, you probably did too much.
If phase 1 feels stable, inspectable, and a little boring, you did it right.
```