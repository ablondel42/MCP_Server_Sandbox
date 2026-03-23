<!-- MCP Server Sandbox -->

# PROJECT: Repo Context MCP

Python-first repository context engine for AI-assisted planning, impact analysis, and safer code changes.

This project builds a structured graph of a Python repository, enriches that graph with selected language-server relationships, and exposes the result through an MCP server so an AI agent can inspect real repository context before editing code.

The point of this project is not “autonomous coding”.
The point is “safer planning before edits”.

The intended workflow is:

1. User and AI agent create a plan.
2. The plan is refined until it is specific enough to evaluate.
3. The agent calls MCP tools to inspect the repository graph.
4. The agent calls a plan-risk tool to estimate whether the plan may break things.
5. The agent updates the plan if the graph reveals risk or missing context.
6. The user approves or rejects the revised plan.
7. Only after approval does implementation proceed.

This project starts with Python only.
The architecture is modular so additional languages can be added later without rewriting the core graph model.

---

# 1. Product intent

## 1.1 Problem

AI coding agents often reason from too little context.
They may understand one file but not:
- what other modules depend on it,
- how often a symbol is referenced,
- whether a change crosses architectural boundaries,
- whether the targeted function is a widely used entry point.

That leads to risky refactors, false confidence, and dumb breakage.

## 1.2 Solution

Build a repository context engine that can answer questions like:
- What symbols exist in this repo?
- Where is this symbol declared?
- What contains it?
- What imports it?
- What inherits from it?
- Where is it referenced?
- How risky is it to change?

Then expose those answers through MCP so an AI agent can query them during planning.

## 1.3 Version 1 scope

Version 1 includes:
- Python only
- AST-based structural extraction
- Layered graph with modules, classes, and callables
- Structural edges like `contains`, `imports`, and `inherits`
- LSP-based `references` enrichment
- Derived `referenced_by`
- Deterministic risk evaluation from graph facts
- MCP tools for indexing, symbol lookup, context lookup, and plan assessment

Version 1 excludes:
- perfect semantic analysis
- full call graph resolution
- every LSP feature
- every language
- autonomous edits without user approval
- graph databases
- large generated English explanation systems inside the server

---

# 2. Core principles

## 2.1 Keep the graph honest

Do not invent certainty.
Every node and edge should carry provenance and confidence.

## 2.2 Keep the MCP deterministic

The MCP server should compute facts, issue codes, and scores.
The AI agent should explain, revise the plan, and ask for approval.

## 2.3 Keep LSP narrow

Use LSP only for the highest-value relationship in version 1:
- `references`

Do not expand into full IDE emulation too early.

## 2.4 Keep the schema canonical

Your internal schema is the source of truth.
It should be LSP-compatible in locations and ranges, but not limited to raw LSP shapes.

## 2.5 Keep the workflow human-gated

The agent must never silently proceed on risky structural work.
The user should stay in the loop.

---

# 3. High-level architecture

The system has six major layers:

1. Repository scanner
2. AST parser and symbol extractor
3. Graph storage
4. LSP reference enricher
5. Context builder and risk engine
6. MCP server

Conceptually:

- The scanner finds files.
- The AST extractor builds the structural graph.
- The graph storage persists nodes and edges.
- The LSP enricher adds `references` edges.
- The context builder assembles useful symbol context.
- The risk engine evaluates planned changes.
- The MCP server exposes all of this to the agent.

---

# 4. Architecture in detail

## 4.1 Repository scanner

Purpose:
Find Python files and basic file metadata.

Inputs:
- repository root path

Outputs:
- file records
- module paths
- content hashes
- modification timestamps

Responsibilities:
- walk repo directories
- ignore junk folders
- identify Python source files
- compute stable relative paths
- derive import-like module paths where possible

Good ignored folders:
- `.git`
- `.venv`
- `venv`
- `__pycache__`
- `build`
- `dist`
- `.mypy_cache`
- `.pytest_cache`
- `.ruff_cache`
- `node_modules`

## 4.2 AST extractor

Purpose:
Extract structure from Python files.

Inputs:
- file path
- file content

Outputs:
- module node
- class nodes
- callable nodes
- structural edges

Responsibilities:
- parse AST
- extract classes
- extract functions
- extract async functions
- extract methods
- extract imports
- extract base classes
- extract decorators
- collect source ranges
- build qualified names

AST is your structural truth in version 1.

## 4.3 Graph storage

Purpose:
Persist the normalized graph.

Inputs:
- nodes
- edges
- file metadata
- indexing runs

Outputs:
- queryable graph state

Responsibilities:
- insert and update nodes
- insert and update edges
- remove stale nodes and edges
- support queries by ID, qualified name, parent, child, incoming edges, outgoing edges

Use SQLite first.

## 4.4 LSP enricher

Purpose:
Add `references` edges for selected symbols.

Inputs:
- declaration location of symbol
- open documents
- minimal project state for the language server

Outputs:
- `references` edges
- confidence and evidence data

Responsibilities:
- open or synchronize relevant documents
- locate the symbol declaration position
- request references for the symbol
- map returned locations back to internal symbols when possible
- store `references` edges
- allow `referenced_by` queries by reversing those edges

Important:
This layer enriches the graph.
It does not replace the graph.

## 4.5 Context builder

Purpose:
Assemble a useful view of one symbol.

Inputs:
- symbol ID or qualified name

Outputs:
- symbol context object

Responsibilities:
- fetch symbol
- fetch parent
- fetch children
- fetch incoming edges
- fetch outgoing edges
- fetch nearby structural info
- fetch reference stats
- attach freshness and confidence

## 4.6 Risk engine

Purpose:
Turn graph facts into a pre-change assessment.

Inputs:
- plan summary
- targeted symbols or files

Outputs:
- plan assessment object

Responsibilities:
- resolve target symbols
- inspect graph context
- inspect references
- count reference spread
- detect cross-module impact
- detect public-surface impact
- compute risk score
- emit issue codes
- emit a decision

Important:
This is deterministic logic, not embedded AI.

## 4.7 MCP server

Purpose:
Expose graph and risk tools to the agent.

Responsibilities:
- accept tool calls
- validate inputs
- run graph queries
- return structured JSON
- expose deterministic assessments

Initial MCP tools:
- `index_repo`
- `repo_status`
- `get_symbol`
- `get_symbol_context`
- `get_symbol_references`
- `evaluate_plan_risk`

---

# 5. Layered graph model

The graph mirrors the real codebase.

## 5.1 Module layer

A module node represents one Python file.

Examples:
- `app/services/auth.py`
- `core/config.py`

Why this exists:
- files are real repository boundaries
- imports happen here
- many risky changes cross module boundaries

## 5.2 Class layer

A class node represents one Python class.

Why this exists:
- classes group methods and behavior
- inheritance is a real structural relationship
- public API often lives here

## 5.3 Callable layer

A callable node represents:
- top-level function
- async function
- method
- async method

Why this exists:
- callables are frequent change targets
- references to callables are high-value signals
- signature changes are risky

---

# 6. Relationship model

Version 1 keeps relationships deliberately narrow.

## 6.1 `contains`

Meaning:
A structural parent owns a structural child.

Examples:
- module contains class
- module contains function
- class contains method

## 6.2 `imports`

Meaning:
A module imports a module or symbol.

## 6.3 `inherits`

Meaning:
A class derives from another class or named base.

## 6.4 `references`

Meaning:
A symbol uses another symbol.
This is enriched via LSP.

## 6.5 `referenced_by`

Meaning:
Reverse view of `references`.

Rule:
Do not store this separately at first.
Query it by reversing `references`.

---

# 7. Canonical schema strategy

Your internal schema should be:
- stable,
- simple,
- queryable,
- LSP-compatible where useful,
- not locked to Python implementation details.

The best shape is:

- common location primitives
- canonical nodes
- canonical edges
- optional language-specific payloads
- deterministic assessments

This lets you add another language later by writing a new extractor and optional enricher without rewriting the graph or MCP tools.

---

# 8. Data models with full commentary

This section defines the core schemas and explains every field.

---

# 8.1 Position

A `Position` is a single point inside a file.

Use it for:
- the start of a span
- the end of a span
- a cursor-like declaration position for LSP requests

Suggested schema:

```json
{
  "line": 0,
  "character": 0
}
```

### Fields

#### `line`
Zero-based line number.

Meaning:
The line within the file.

Used for:
- declaration matching
- LSP requests
- evidence location
- source slicing

Mapping notes:
- Python AST line numbers are usually one-based.
- LSP positions are typically zero-based.
- You should normalize internally to one convention and convert at boundaries.
- Best practical choice: store zero-based internally for LSP compatibility.

#### `character`
Zero-based character offset within the line.

Meaning:
The column position within the line.

Used for:
- precise span matching
- declaration targeting
- mapping LSP locations to internal symbols

Mapping notes:
- Python AST gives column offsets.
- These can map fairly directly with care.

---

# 8.2 Range

A `Range` is a start and end position.

Suggested schema:

```json
{
  "start": { "line": 10, "character": 4 },
  "end": { "line": 18, "character": 22 }
}
```

### Fields

#### `start`
The first position in the span.

Meaning:
Where the declaration or evidence begins.

Used for:
- locating declarations
- building source slices
- matching LSP results

#### `end`
The last position in the span.

Meaning:
Where the declaration or evidence ends.

Used for:
- declaration extent
- precise slicing
- overlap checks

---

# 8.3 RepoRecord

Represents one indexed repository.

Suggested schema:

```json
{
  "id": "repo:main",
  "root_path": "/workspace/project",
  "name": "project",
  "default_language": "python",
  "created_at": "2026-03-23T20:00:00Z",
  "last_indexed_at": "2026-03-23T20:10:00Z"
}
```

### Fields

#### `id`
Stable repository ID.

Purpose:
Anchor every node and edge to one repo.

#### `root_path`
Absolute or canonical repository root path.

Purpose:
Used by scanner and module-path derivation.

#### `name`
Human-friendly repository name.

Purpose:
Display and debugging.

#### `default_language`
Main language of the repository for version 1.

Purpose:
Useful later for multi-language support.

#### `created_at`
Timestamp of when the repo record was first created.

Purpose:
Basic metadata.

#### `last_indexed_at`
Timestamp of last successful indexing run.

Purpose:
Freshness.

---

# 8.4 FileRecord

Represents one source file tracked by the indexer.

Suggested schema:

```json
{
  "id": "file:app/services/auth.py",
  "repo_id": "repo:main",
  "file_path": "app/services/auth.py",
  "uri": "file:///workspace/project/app/services/auth.py",
  "module_path": "app.services.auth",
  "language": "python",
  "content_hash": "sha256:...",
  "size_bytes": 4211,
  "last_modified_at": "2026-03-23T20:05:00Z",
  "last_indexed_at": "2026-03-23T20:10:00Z"
}
```

### Fields

#### `id`
Stable file ID.

Purpose:
Lets other records reference this file directly.

#### `repo_id`
Owning repository.

Purpose:
Namespace isolation.

#### `file_path`
Repository-relative file path.

Purpose:
Primary filesystem identity inside the repo.

#### `uri`
LSP-compatible file URI.

Purpose:
Used at the LSP boundary.

#### `module_path`
Import-like Python module path.

Purpose:
Useful for dependency reasoning.

#### `language`
Language of the file.

Purpose:
Future-proofing and adapter routing.

#### `content_hash`
Hash of file content.

Purpose:
Change detection and incremental indexing.

#### `size_bytes`
Approximate file size.

Purpose:
Useful for stats and some heuristics.

#### `last_modified_at`
Filesystem modification time.

Purpose:
Freshness and update detection.

#### `last_indexed_at`
Last successful indexing time for this file.

Purpose:
Staleness detection.

---

# 8.5 SymbolNode

Base schema for all graph symbols.

Suggested schema:

```json
{
  "id": "sym:repo:method:app.services.auth.AuthService.login",
  "repo_id": "repo:main",
  "file_id": "file:app/services/auth.py",
  "language": "python",
  "kind": "method",
  "name": "login",
  "qualified_name": "app.services.auth.AuthService.login",
  "uri": "file:///workspace/project/app/services/auth.py",
  "range": {
    "start": { "line": 20, "character": 4 },
    "end": { "line": 38, "character": 18 }
  },
  "selection_range": {
    "start": { "line": 20, "character": 8 },
    "end": { "line": 20, "character": 13 }
  },
  "parent_id": "sym:repo:class:app.services.auth.AuthService",
  "visibility_hint": "public",
  "doc_summary": "Authenticate a user and return a session.",
  "content_hash": "sha256:...",
  "semantic_hash": "sha256:...",
  "source": "python-ast",
  "confidence": 0.96,
  "last_indexed_at": "2026-03-23T20:10:00Z"
}
```

### Fields

#### `id`
Stable symbol ID.

Purpose:
Graph identity.

Construction idea:
`repo + kind + qualified_name`

Why it matters:
Names collide.
IDs should not.

#### `repo_id`
Owning repository.

Purpose:
Namespace separation.

#### `file_id`
Owning file.

Purpose:
Fast lookup and cleanup on file changes.

#### `language`
Source language.

Purpose:
Future adapter support.

#### `kind`
Symbol kind.

Version 1 allowed kinds:
- `module`
- `class`
- `function`
- `async_function`
- `method`
- `async_method`

Purpose:
Tells the graph and agent what the symbol is.

#### `name`
Simple local name.

Examples:
- `AuthService`
- `login`

Purpose:
Human readability and direct lookup.

#### `qualified_name`
Full logical path-like name.

Examples:
- `app.services.auth.AuthService`
- `app.services.auth.AuthService.login`

Purpose:
Stable lookup and disambiguation.

#### `uri`
LSP-compatible file URI.

Purpose:
Used when talking to the language server.

#### `range`
Full declaration span.

Purpose:
Represents the entire symbol block.

Used for:
- source slicing
- declaration matching
- editor jumps
- overlap checks

#### `selection_range`
Small span around the declaration name token.

Purpose:
Represents the most useful pinpoint location.

Used for:
- LSP declaration/reference starting position
- UI focus
- precise symbol matching

#### `parent_id`
Parent symbol ID if any.

Examples:
- method -> class
- class -> module
- function -> module

Purpose:
Hierarchy.

#### `visibility_hint`
Best-effort visibility classification.

Version 1 suggested values:
- `public`
- `protected_like`
- `private_like`
- `module`

Meaning:
Python does not enforce visibility, so this is only a hint.

Heuristic idea:
- starts with `__` and not magic method -> `private_like`
- starts with `_` -> `protected_like`
- top-level exported-looking symbol -> `public`

Purpose:
Useful for risk scoring.

#### `doc_summary`
Short summary from docstring if present.

Purpose:
Quick semantic hint for the agent.

Rule:
Keep it short.
Do not generate long summaries here in version 1.

#### `content_hash`
Hash of raw declaration source.

Purpose:
Detect any text change.

#### `semantic_hash`
Hash of normalized meaningful features.

Purpose:
Detect important structural changes rather than whitespace-only changes.

Possible inputs:
- name
- kind
- parent
- signature
- decorators
- base classes

#### `source`
Where this node came from.

Examples:
- `python-ast`
- `merged`

Purpose:
Provenance.

#### `confidence`
Numeric confidence score.

Purpose:
Represents how trustworthy the node data is.

Typical values:
- 1.0 for direct AST declaration extraction
- lower values for inferred or merged data

#### `last_indexed_at`
Last successful indexing timestamp.

Purpose:
Freshness.

---

# 8.6 ModuleNode

A `ModuleNode` extends `SymbolNode`.

Suggested schema:

```json
{
  "kind": "module",
  "file_path": "app/services/auth.py",
  "module_path": "app.services.auth",
  "package_path": "app.services",
  "imported_modules": ["app.models.user", "app.core.security"],
  "imported_symbols": ["User", "hash_password"],
  "top_level_symbol_ids": [
    "sym:repo:class:app.services.auth.AuthService",
    "sym:repo:function:app.services.auth.build_auth_payload"
  ]
}
```

### Fields

#### `file_path`
Repo-relative file path.

Purpose:
Main local identifier for the file.

#### `module_path`
Import-like module path.

Purpose:
Dependency reasoning and display.

#### `package_path`
Parent package path if applicable.

Purpose:
Useful for package-level grouping.

#### `imported_modules`
Module names imported by this file.

Purpose:
Quick dependency view.

#### `imported_symbols`
Named imported symbols.

Purpose:
Dependency and context hints before deeper semantic resolution.

#### `top_level_symbol_ids`
IDs of top-level symbols declared in the file.

Purpose:
Fast file outline queries.

---

# 8.7 ClassNode

A `ClassNode` extends `SymbolNode`.

Suggested schema:

```json
{
  "kind": "class",
  "base_names": ["BaseService"],
  "decorators": ["dataclass"],
  "method_ids": [
    "sym:repo:method:app.services.auth.AuthService.login"
  ]
}
```

### Fields

#### `base_names`
Names of bases declared in the class definition.

Purpose:
Inheritance reasoning.

Note:
These may not all resolve perfectly in version 1.
That is okay.
Store the names anyway.

#### `decorators`
Decorator names attached to the class.

Purpose:
Behavior hints.

Examples:
- `dataclass`
- framework-specific decorators

#### `method_ids`
Child method IDs.

Purpose:
Fast access to class members.

---

# 8.8 CallableNode

A `CallableNode` extends `SymbolNode`.

Suggested schema:

```json
{
  "parameters": [
    {
      "name": "user_id",
      "kind": "positional_or_keyword",
      "annotation": "str",
      "default_value_hint": null
    },
    {
      "name": "password",
      "kind": "positional_or_keyword",
      "annotation": "str",
      "default_value_hint": null
    }
  ],
  "return_annotation": "Session",
  "decorators": ["classmethod"],
  "is_async": false,
  "is_method": true,
  "is_generator": false
}
```

### Fields

#### `parameters`
Ordered list of parameter records.

Purpose:
Represents function signature inputs.

Why it matters:
Signature changes are a major breakage risk.

#### `return_annotation`
Declared return annotation if present.

Purpose:
Signature understanding.

#### `decorators`
Callable decorators.

Purpose:
Behavior modifiers.

#### `is_async`
Whether callable is async.

Purpose:
Behavior and risk hints.

#### `is_method`
Whether callable belongs to a class.

Purpose:
Context and ownership.

#### `is_generator`
Whether callable appears to be a generator.

Purpose:
Behavior hint.

---

# 8.9 ParameterRecord

Represents one parameter in a callable.

Suggested schema:

```json
{
  "name": "user_id",
  "kind": "positional_or_keyword",
  "annotation": "str",
  "default_value_hint": null
}
```

### Fields

#### `name`
Parameter name.

Purpose:
Signature surface.

#### `kind`
Parameter kind.

Suggested values:
- `positional_only`
- `positional_or_keyword`
- `var_positional`
- `keyword_only`
- `var_keyword`

Purpose:
Detect signature semantics.

#### `annotation`
String form of parameter annotation if present.

Purpose:
Type hint visibility.

#### `default_value_hint`
String hint of default value if safely derivable.

Purpose:
Useful for understanding optionality.

Important:
Keep this lightweight.
Do not overbuild expression serialization in version 1.

---

# 8.10 Edge

Represents one graph relationship.

Suggested schema:

```json
{
  "id": "edge:repo:references:symA->symB:44:15",
  "repo_id": "repo:main",
  "kind": "references",
  "from_id": "sym:repo:function:app.tasks.run_job",
  "to_id": "sym:repo:function:app.services.jobs.execute_job",
  "source": "lsp",
  "confidence": 0.91,
  "evidence_file_id": "file:app/tasks.py",
  "evidence_uri": "file:///workspace/project/app/tasks.py",
  "evidence_range": {
    "start": { "line": 44, "character": 15 },
    "end": { "line": 44, "character": 26 }
  },
  "payload": {},
  "last_indexed_at": "2026-03-23T20:10:00Z"
}
```

### Fields

#### `id`
Stable edge ID.

Purpose:
Deduplication and updates.

Construction idea:
`repo + kind + from_id + to_id + evidence anchor`

#### `repo_id`
Owning repository.

Purpose:
Namespace separation.

#### `kind`
Relationship type.

Version 1 values:
- `contains`
- `imports`
- `inherits`
- `references`

Purpose:
Defines semantic meaning of the edge.

#### `from_id`
Source node ID.

Purpose:
Directionality.

#### `to_id`
Target node ID.

Purpose:
Dependency and impact queries.

#### `source`
Where the edge came from.

Examples:
- `python-ast`
- `lsp`
- `derived`

Purpose:
Trust and debugging.

#### `confidence`
Trust score for the relationship.

Purpose:
Risk scoring and explanation.

#### `evidence_file_id`
File where evidence was observed.

Purpose:
Traceability.

#### `evidence_uri`
LSP-compatible file URI for evidence.

Purpose:
External compatibility.

#### `evidence_range`
Location of usage or declaration supporting the edge.

Purpose:
Traceability and matching.

#### `payload`
Optional relationship-specific metadata.

Purpose:
Extension without schema churn.

#### `last_indexed_at`
Freshness timestamp.

Purpose:
Staleness detection.

---

# 8.11 IndexRun

Represents one indexing execution.

Suggested schema:

```json
{
  "id": "run:2026-03-23T20:10:00Z",
  "repo_id": "repo:main",
  "mode": "full",
  "status": "success",
  "started_at": "2026-03-23T20:09:30Z",
  "finished_at": "2026-03-23T20:10:00Z",
  "changed_files": ["app/services/auth.py"],
  "stats": {
    "file_count": 22,
    "node_count": 188,
    "edge_count": 344
  },
  "errors": []
}
```

### Fields

#### `id`
Unique run ID.

Purpose:
Auditability.

#### `repo_id`
Owning repo.

Purpose:
Scoping.

#### `mode`
Index mode.

Values:
- `full`
- `incremental`

Purpose:
Operational context.

#### `status`
Run result status.

Values:
- `running`
- `success`
- `failed`
- `partial`

Purpose:
Operational visibility.

#### `started_at`
Start time.

Purpose:
Tracing.

#### `finished_at`
End time.

Purpose:
Tracing and duration.

#### `changed_files`
Files considered changed in this run.

Purpose:
Debugging incremental updates.

#### `stats`
Counts for nodes, edges, files.

Purpose:
Monitoring and validation.

#### `errors`
Collected indexing errors.

Purpose:
Observability and troubleshooting.

---

# 8.12 SymbolContext

This is the assembled object returned to the agent.

Suggested schema:

```json
{
  "focus_symbol": {},
  "parent": {},
  "children": [],
  "outgoing_edges": [],
  "incoming_edges": [],
  "reference_summary": {
    "reference_count": 14,
    "referencing_file_count": 6
  },
  "freshness": {
    "last_indexed_at": "2026-03-23T20:10:00Z",
    "is_stale": false
  },
  "confidence": {
    "node_confidence": 0.96,
    "edge_confidence_min": 0.83
  }
}
```

### Fields

#### `focus_symbol`
The main symbol requested.

Purpose:
Anchor of the response.

#### `parent`
Immediate parent symbol if any.

Purpose:
Hierarchy.

#### `children`
Immediate child symbols.

Purpose:
Structure.

#### `outgoing_edges`
Edges starting from the focus symbol.

Purpose:
Dependency and impact reasoning.

#### `incoming_edges`
Edges targeting the focus symbol.

Purpose:
Dependency and impact reasoning.

#### `reference_summary`
Aggregated reference facts.

Purpose:
Fast risk hints.

#### `freshness`
Freshness metadata.

Purpose:
Trust and caution.

#### `confidence`
Confidence summary for the assembled context.

Purpose:
Honest uncertainty reporting.

---

# 8.13 PlanAssessment

Deterministic output of the risk engine.

Suggested schema:

```json
{
  "plan_summary": "Refactor AuthService.login to split validation and token creation.",
  "target_symbols": [
    "sym:repo:method:app.services.auth.AuthService.login"
  ],
  "resolved_symbols": [
    "sym:repo:method:app.services.auth.AuthService.login"
  ],
  "unresolved_targets": [],
  "facts": {
    "reference_counts": {
      "sym:repo:method:app.services.auth.AuthService.login": 14
    },
    "referencing_module_counts": {
      "sym:repo:method:app.services.auth.AuthService.login": 6
    },
    "touches_public_surface": true,
    "cross_module_impact": true,
    "low_confidence_symbols": [],
    "stale_symbols": []
  },
  "issues": [
    "high_reference_count",
    "cross_module_impact",
    "public_surface_change"
  ],
  "risk_score": 78,
  "decision": "review_required"
}
```

### Fields

#### `plan_summary`
Human-readable summary of the intended change.

Purpose:
Anchor the assessment to the actual plan.

#### `target_symbols`
Symbols the user or agent intends to modify.

Purpose:
Input intent.

#### `resolved_symbols`
Targets successfully mapped to known graph nodes.

Purpose:
Operational clarity.

#### `unresolved_targets`
Requested targets that could not be mapped.

Purpose:
Missing context signal.

#### `facts`
Machine-friendly assessment facts.

Purpose:
Explainable deterministic reasoning.

#### `issues`
Issue codes triggered by the facts.

Purpose:
Compact explanation surface for the agent.

#### `risk_score`
Numeric risk score.

Purpose:
Thresholding and ranking.

#### `decision`
Server-side decision.

Suggested values:
- `safe_enough`
- `review_required`
- `blocked_missing_context`

Purpose:
Simple action guidance.

Important:
The server should not pretend this is perfect truth.
It is a deterministic recommendation.

---

# 9. Mapping schemas to Python AST

This section shows how to extract and map fields from Python AST.

Use the built-in `ast` module.

Important Python AST notes:
- `lineno` is usually one-based
- `col_offset` is column offset
- many modern nodes also expose `end_lineno` and `end_col_offset`
- docstrings can be extracted with helper functions
- function, class, import, and async nodes have distinct AST node types

---

# 9.1 Basic helpers

```python
import ast
from pathlib import Path
from typing import Optional

def to_zero_based_line(line: Optional[int]) -> Optional[int]:
    if line is None:
        return None
    return line - 1

def make_position(line: Optional[int], col: Optional[int]) -> dict | None:
    if line is None or col is None:
        return None
    return {
        "line": to_zero_based_line(line),
        "character": col,
    }

def make_range(node: ast.AST) -> dict | None:
    if not hasattr(node, "lineno") or not hasattr(node, "col_offset"):
        return None
    start = make_position(getattr(node, "lineno", None), getattr(node, "col_offset", None))
    end = make_position(getattr(node, "end_lineno", None), getattr(node, "end_col_offset", None))
    if start is None or end is None:
        return None
    return {"start": start, "end": end}

def get_doc_summary(node: ast.AST) -> str | None:
    raw = ast.get_docstring(node)
    if not raw:
        return None
    first = raw.strip().split("\n\n").strip()
    return first or None
```

What these helpers do:
- normalize line numbers
- build LSP-like positions
- build full ranges
- extract short doc summaries

---

# 9.2 Mapping file to ModuleNode

Input:
- file path
- file source
- parsed AST tree

Example snippet:

```python
def derive_module_path(repo_root: Path, file_path: Path) -> str:
    relative = file_path.relative_to(repo_root)
    no_suffix = relative.with_suffix("")
    parts = list(no_suffix.parts)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)

def extract_module_node(repo_id: str, file_id: str, repo_root: Path, file_path: Path, tree: ast.Module) -> dict:
    module_path = derive_module_path(repo_root, file_path)
    range_obj = {
        "start": {"line": 0, "character": 0},
        "end": {"line": max(0, len(Path(file_path).read_text().splitlines()) - 1), "character": 0},
    }
    return {
        "id": f"sym:{repo_id}:module:{module_path}",
        "repo_id": repo_id,
        "file_id": file_id,
        "language": "python",
        "kind": "module",
        "name": module_path.split(".")[-1] if module_path else file_path.stem,
        "qualified_name": module_path,
        "uri": file_path.resolve().as_uri(),
        "range": range_obj,
        "selection_range": range_obj,
        "parent_id": None,
        "visibility_hint": "module",
        "doc_summary": get_doc_summary(tree),
        "content_hash": "",
        "semantic_hash": "",
        "source": "python-ast",
        "confidence": 1.0,
        "last_indexed_at": "",
        "file_path": str(file_path.relative_to(repo_root)),
        "module_path": module_path,
        "package_path": ".".join(module_path.split(".")[:-1]) if "." in module_path else "",
        "imported_modules": [],
        "imported_symbols": [],
        "top_level_symbol_ids": [],
    }
```

Mapped fields:
- `module_path` from path
- `uri` from resolved file path
- `doc_summary` from module docstring
- `kind="module"`
- `range` from full file span
- imports filled later by walking AST body

---

# 9.3 Mapping class declarations to ClassNode

Relevant AST node:
- `ast.ClassDef`

Example snippet:

```python
def get_name_selection_range(node: ast.AST) -> dict | None:
    if not hasattr(node, "lineno") or not hasattr(node, "col_offset"):
        return None
    line = to_zero_based_line(node.lineno)
    start = {"line": line, "character": node.col_offset}
    end = {"line": line, "character": node.col_offset + len(getattr(node, "name", ""))}
    return {"start": start, "end": end}

def extract_class_node(repo_id: str, file_id: str, file_uri: str, module_path: str, parent_id: str, node: ast.ClassDef) -> dict:
    qn = f"{module_path}.{node.name}" if module_path else node.name
    base_names = [ast.unparse(base) for base in node.bases] if node.bases else []
    decorators = [ast.unparse(d) for d in node.decorator_list] if node.decorator_list else []

    return {
        "id": f"sym:{repo_id}:class:{qn}",
        "repo_id": repo_id,
        "file_id": file_id,
        "language": "python",
        "kind": "class",
        "name": node.name,
        "qualified_name": qn,
        "uri": file_uri,
        "range": make_range(node),
        "selection_range": get_name_selection_range(node),
        "parent_id": parent_id,
        "visibility_hint": "private_like" if node.name.startswith("_") else "public",
        "doc_summary": get_doc_summary(node),
        "content_hash": "",
        "semantic_hash": "",
        "source": "python-ast",
        "confidence": 1.0,
        "last_indexed_at": "",
        "base_names": base_names,
        "decorators": decorators,
        "method_ids": [],
    }
```

Mapped fields:
- `name` from `node.name`
- `base_names` from `node.bases`
- `decorators` from `node.decorator_list`
- `range` from node location metadata
- `doc_summary` from class docstring

---

# 9.4 Mapping functions and methods to CallableNode

Relevant AST nodes:
- `ast.FunctionDef`
- `ast.AsyncFunctionDef`

Example snippet:

```python
def extract_parameters(args: ast.arguments) -> list[dict]:
    params = []

    for a in getattr(args, "posonlyargs", []):
        params.append({
            "name": a.arg,
            "kind": "positional_only",
            "annotation": ast.unparse(a.annotation) if a.annotation else None,
            "default_value_hint": None,
        })

    for a in args.args:
        params.append({
            "name": a.arg,
            "kind": "positional_or_keyword",
            "annotation": ast.unparse(a.annotation) if a.annotation else None,
            "default_value_hint": None,
        })

    if args.vararg:
        params.append({
            "name": args.vararg.arg,
            "kind": "var_positional",
            "annotation": ast.unparse(args.vararg.annotation) if args.vararg.annotation else None,
            "default_value_hint": None,
        })

    for a in args.kwonlyargs:
        params.append({
            "name": a.arg,
            "kind": "keyword_only",
            "annotation": ast.unparse(a.annotation) if a.annotation else None,
            "default_value_hint": None,
        })

    if args.kwarg:
        params.append({
            "name": args.kwarg.arg,
            "kind": "var_keyword",
            "annotation": ast.unparse(args.kwarg.annotation) if args.kwarg.annotation else None,
            "default_value_hint": None,
        })

    return params

def extract_callable_node(
    repo_id: str,
    file_id: str,
    file_uri: str,
    module_path: str,
    parent_id: str,
    parent_qualified_name: str,
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    is_method: bool
) -> dict:
    qn_parent = parent_qualified_name if parent_qualified_name else module_path
    qn = f"{qn_parent}.{node.name}" if qn_parent else node.name
    decorators = [ast.unparse(d) for d in node.decorator_list] if node.decorator_list else []
    is_async = isinstance(node, ast.AsyncFunctionDef)

    return {
        "id": f"sym:{repo_id}:{'async_method' if is_async and is_method else 'async_function' if is_async else 'method' if is_method else 'function'}:{qn}",
        "repo_id": repo_id,
        "file_id": file_id,
        "language": "python",
        "kind": "async_method" if is_async and is_method else "async_function" if is_async else "method" if is_method else "function",
        "name": node.name,
        "qualified_name": qn,
        "uri": file_uri,
        "range": make_range(node),
        "selection_range": get_name_selection_range(node),
        "parent_id": parent_id,
        "visibility_hint": "private_like" if node.name.startswith("_") and not (node.name.startswith("__") and node.name.endswith("__")) else "public",
        "doc_summary": get_doc_summary(node),
        "content_hash": "",
        "semantic_hash": "",
        "source": "python-ast",
        "confidence": 1.0,
        "last_indexed_at": "",
        "parameters": extract_parameters(node.args),
        "return_annotation": ast.unparse(node.returns) if node.returns else None,
        "decorators": decorators,
        "is_async": is_async,
        "is_method": is_method,
        "is_generator": any(isinstance(n, (ast.Yield, ast.YieldFrom)) for n in ast.walk(node)),
    }
```

Mapped fields:
- `kind` from AST node type and nesting
- `parameters` from `node.args`
- `return_annotation` from `node.returns`
- `decorators` from `node.decorator_list`
- `is_generator` from presence of `Yield` nodes

---

# 9.5 Mapping imports to `imports` edges

Relevant AST nodes:
- `ast.Import`
- `ast.ImportFrom`

Example snippet:

```python
def extract_import_edges(repo_id: str, from_module_id: str, file_id: str, file_uri: str, tree: ast.Module) -> list[dict]:
    edges = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                target = alias.name
                edges.append({
                    "id": f"edge:{repo_id}:imports:{from_module_id}->{target}:{getattr(node, 'lineno', 0)}",
                    "repo_id": repo_id,
                    "kind": "imports",
                    "from_id": from_module_id,
                    "to_id": f"external_or_unresolved:{target}",
                    "source": "python-ast",
                    "confidence": 0.8,
                    "evidence_file_id": file_id,
                    "evidence_uri": file_uri,
                    "evidence_range": make_range(node),
                    "payload": {"alias": alias.asname},
                    "last_indexed_at": "",
                })
        elif isinstance(node, ast.ImportFrom):
            module_name = node.module or ""
            for alias in node.names:
                edges.append({
                    "id": f"edge:{repo_id}:imports:{from_module_id}->{module_name}.{alias.name}:{getattr(node, 'lineno', 0)}",
                    "repo_id": repo_id,
                    "kind": "imports",
                    "from_id": from_module_id,
                    "to_id": f"external_or_unresolved:{module_name}.{alias.name}",
                    "source": "python-ast",
                    "confidence": 0.8,
                    "evidence_file_id": file_id,
                    "evidence_uri": file_uri,
                    "evidence_range": make_range(node),
                    "payload": {"alias": alias.asname, "module": module_name, "level": node.level},
                    "last_indexed_at": "",
                })
    return edges
```

Important note:
In version 1, many imports may remain unresolved.
That is okay.
Store them honestly with lower confidence or unresolved target placeholders.

---

# 9.6 Mapping class inheritance to `inherits` edges

Relevant AST field:
- `ClassDef.bases`

Example snippet:

```python
def extract_inherits_edges(repo_id: str, class_node: dict, file_id: str, file_uri: str, class_ast: ast.ClassDef) -> list[dict]:
    edges = []
    for base in class_ast.bases:
        base_name = ast.unparse(base)
        edges.append({
            "id": f"edge:{repo_id}:inherits:{class_node['id']}->{base_name}",
            "repo_id": repo_id,
            "kind": "inherits",
            "from_id": class_node["id"],
            "to_id": f"unresolved_base:{base_name}",
            "source": "python-ast",
            "confidence": 0.7,
            "evidence_file_id": file_id,
            "evidence_uri": file_uri,
            "evidence_range": make_range(base),
            "payload": {"base_name": base_name},
            "last_indexed_at": "",
        })
    return edges
```

Important:
You can later improve base resolution.
Do not block version 1 on perfect inheritance resolution.

---

# 10. Mapping schemas to LSP

Version 1 only uses LSP for `references`.

Inputs you need from your graph:
- file URI
- declaration position or selection range
- symbol identity for the declaration

Outputs you want from LSP:
- list of usage locations
- each location mapped to your internal symbol graph if possible

---

# 10.1 Minimal LSP data you care about

For version 1, the useful LSP shapes are basically:

- `TextDocumentIdentifier`
- `Position`
- `Location`
- `ReferenceParams`

Minimal conceptual request:

```json
{
  "textDocument": { "uri": "file:///workspace/project/app/services/auth.py" },
  "position": { "line": 20, "character": 8 },
  "context": { "includeDeclaration": false }
}
```

Minimal conceptual response:

```json
[
  {
    "uri": "file:///workspace/project/app/api/routes.py",
    "range": {
      "start": { "line": 44, "character": 15 },
      "end": { "line": 44, "character": 20 }
    }
  }
]
```

---

# 10.2 Picking the right LSP position

For a symbol reference lookup, use `selection_range.start` if available.

Why:
- it points closer to the actual symbol name token
- that is usually better than the whole declaration range start

Fallback:
- use `range.start`

---

# 10.3 Mapping LSP locations back to internal symbols

This is one of the trickiest parts.

Goal:
When the LSP returns a reference location, decide which internal symbol contains that usage.

Good practical strategy:
1. convert returned `uri` to repo-relative file path
2. find all nodes in that file
3. choose the smallest node range that contains the reference range
4. if none contain it, attach the edge to the module node as a fallback
5. record lower confidence if matching is fuzzy

Example snippet:

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

def pick_smallest_containing_symbol(symbols_in_file: list[dict], usage_range: dict) -> dict | None:
    containing = [s for s in symbols_in_file if s.get("range") and range_contains(s["range"], usage_range)]
    if not containing:
        return None
    containing.sort(
        key=lambda s: (
            (s["range"]["end"]["line"] - s["range"]["start"]["line"]),
            (s["range"]["end"]["character"] - s["range"]["start"]["character"])
        )
    )
    return containing
```

This is not perfect.
It is still good enough for version 1.

---

# 10.4 Building `references` edges from LSP locations

Example snippet:

```python
def build_reference_edge(
    repo_id: str,
    from_symbol_id: str,
    to_symbol_id: str,
    evidence_file_id: str,
    evidence_uri: str,
    evidence_range: dict,
    confidence: float = 0.9
) -> dict:
    anchor = f"{evidence_range['start']['line']}:{evidence_range['start']['character']}"
    return {
        "id": f"edge:{repo_id}:references:{from_symbol_id}->{to_symbol_id}:{anchor}",
        "repo_id": repo_id,
        "kind": "references",
        "from_id": from_symbol_id,
        "to_id": to_symbol_id,
        "source": "lsp",
        "confidence": confidence,
        "evidence_file_id": evidence_file_id,
        "evidence_uri": evidence_uri,
        "evidence_range": evidence_range,
        "payload": {},
        "last_indexed_at": "",
    }
```

Meaning:
- `from_id` is the symbol containing the usage site
- `to_id` is the referenced target symbol

Then `referenced_by` is simply the reverse query:
- find all `references` where `to_id = target`

---

# 11. Database schema

Use SQLite first.

Suggested tables:

## 11.1 `repos`

```sql
CREATE TABLE repos (
  id TEXT PRIMARY KEY,
  root_path TEXT NOT NULL,
  name TEXT NOT NULL,
  default_language TEXT NOT NULL,
  created_at TEXT NOT NULL,
  last_indexed_at TEXT
);
```

## 11.2 `files`

```sql
CREATE TABLE files (
  id TEXT PRIMARY KEY,
  repo_id TEXT NOT NULL,
  file_path TEXT NOT NULL,
  uri TEXT NOT NULL,
  module_path TEXT NOT NULL,
  language TEXT NOT NULL,
  content_hash TEXT NOT NULL,
  size_bytes INTEGER NOT NULL,
  last_modified_at TEXT NOT NULL,
  last_indexed_at TEXT,
  UNIQUE(repo_id, file_path)
);
```

## 11.3 `nodes`

```sql
CREATE TABLE nodes (
  id TEXT PRIMARY KEY,
  repo_id TEXT NOT NULL,
  file_id TEXT NOT NULL,
  language TEXT NOT NULL,
  kind TEXT NOT NULL,
  name TEXT NOT NULL,
  qualified_name TEXT NOT NULL,
  uri TEXT NOT NULL,
  range_json TEXT NOT NULL,
  selection_range_json TEXT,
  parent_id TEXT,
  visibility_hint TEXT,
  doc_summary TEXT,
  content_hash TEXT NOT NULL,
  semantic_hash TEXT NOT NULL,
  source TEXT NOT NULL,
  confidence REAL NOT NULL,
  payload_json TEXT NOT NULL,
  last_indexed_at TEXT,
  UNIQUE(repo_id, qualified_name, kind)
);
```

## 11.4 `edges`

```sql
CREATE TABLE edges (
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

## 11.5 `index_runs`

```sql
CREATE TABLE index_runs (
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

## 11.6 Optional `plan_assessments`

```sql
CREATE TABLE plan_assessments (
  id TEXT PRIMARY KEY,
  repo_id TEXT NOT NULL,
  plan_summary TEXT NOT NULL,
  input_json TEXT NOT NULL,
  output_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);
```

---

# 12. Suggested Python models

For version 1, simple dataclasses or Pydantic models are both fine.

If you want less magic and fewer moving parts, dataclasses are enough.
If you want validation and JSON serialization convenience, Pydantic is nice.

Good practical advice:
- use dataclasses first if you want low complexity
- use Pydantic if you know you’ll heavily serialize MCP payloads

---

# 13. MCP tool design

The MCP server should expose deterministic tools, not vague narratives.

## 13.1 `index_repo`

Purpose:
Scan and index a repository.

Input:
- `repo_path`

Output:
- repo metadata
- counts
- status

## 13.2 `repo_status`

Purpose:
Return index freshness and basic stats.

Input:
- `repo_id`

Output:
- file count
- node count
- edge count
- last indexed time
- stale indicators

## 13.3 `get_symbol`

Purpose:
Lookup one symbol by ID or qualified name.

Input:
- `symbol_id` or `qualified_name`

Output:
- one symbol node

## 13.4 `get_symbol_context`

Purpose:
Return assembled context.

Input:
- `symbol_id`

Output:
- `SymbolContext`

## 13.5 `get_symbol_references`

Purpose:
Return reference edges and summary.

Input:
- `symbol_id`
- optional refresh flag

Output:
- reference edges
- counts
- freshness
- confidence

## 13.6 `evaluate_plan_risk`

Purpose:
Return deterministic assessment for a proposed plan.

Input:
- plan summary
- target symbols or files

Output:
- `PlanAssessment`

Important:
The server should emit:
- facts
- issue codes
- score
- decision

The agent can turn that into prose.

---

# 14. Risk engine design

Version 1 risk logic should stay simple.

## 14.1 Useful facts

Compute:
- number of references
- number of referencing files
- number of referencing modules
- whether symbol looks public
- whether target is module, class, function, or method
- whether graph data is stale
- whether confidence is low
- whether change crosses module boundaries
- whether unresolved targets exist

## 14.2 Useful issue codes

Suggested starter codes:
- `unresolved_target`
- `stale_context`
- `low_confidence_match`
- `high_reference_count`
- `cross_module_impact`
- `public_surface_change`
- `signature_change_risk`
- `inheritance_risk`

## 14.3 Suggested decisions

- `safe_enough`
- `review_required`
- `blocked_missing_context`

## 14.4 Simple scoring idea

Example:
- unresolved target: +40
- stale context: +20
- low confidence: +20
- public surface: +15
- cross module: +15
- high references: +20
- inheritance involved: +10

Clamp to 0-100.

Then:
- 0-29 -> `safe_enough`
- 30-69 -> `review_required`
- 70+ -> `blocked_missing_context` or high review gate depending on unresolved context

Keep it simple.
Do not pretend this score is scientific.

---

# 15. Project structure

```text
repo-context-mcp/
  README.md
  pyproject.toml
  src/
    repo_context/
      __init__.py
      config.py
      models/
        common.py
        repo.py
        file.py
        node.py
        edge.py
        context.py
        assessment.py
      storage/
        db.py
        migrations.py
        repos.py
        files.py
        nodes.py
        edges.py
        index_runs.py
        plan_assessments.py
      parsing/
        scanner.py
        ast_loader.py
        module_extractor.py
        class_extractor.py
        callable_extractor.py
        import_extractor.py
        inheritance_extractor.py
        naming.py
        hashing.py
      lsp/
        client.py
        protocol.py
        references.py
        mapper.py
      graph/
        builder.py
        queries.py
        context.py
        risk.py
      indexing/
        full_index.py
        incremental_index.py
        watcher.py
      mcp/
        server.py
        tool_registry.py
        tools/
          index_repo.py
          repo_status.py
          get_symbol.py
          get_symbol_context.py
          get_symbol_references.py
          evaluate_plan_risk.py
      cli/
        main.py
  tests/
    fixtures/
      simple_package/
      inheritance_case/
      references_case/
      async_case/
    test_scanner.py
    test_ast_extraction.py
    test_import_edges.py
    test_inheritance_edges.py
    test_reference_mapping.py
    test_context_builder.py
    test_risk_engine.py
    test_mcp_tools.py
```

---

# 16. Build plan in phases

Build this one phase at a time.
Do not ask AI to generate the whole repo in one shot.

## Phase 1: Bootstrap

Goal:
Create the project skeleton and core models.

Tasks:
- initialize Python package
- add dependency management
- create folder structure
- define core models
- define SQLite schema
- create basic CLI
- create test setup

Done when:
- project installs
- DB initializes
- imports are stable
- tests run

## Phase 2: Repository scanner

Goal:
Find and track Python files.

Tasks:
- scan repo
- ignore junk folders
- build file records
- derive module paths
- compute hashes

Done when:
- scanner returns stable file inventory
- file records persist to DB

## Phase 3: AST extraction

Goal:
Extract module, class, and callable nodes.

Tasks:
- parse files with AST
- extract module nodes
- extract class nodes
- extract callable nodes
- extract imports
- extract inheritance names
- compute ranges and selection ranges
- derive qualified names

Done when:
- you can populate the graph with structural nodes and edges

## Phase 4: Graph storage

Goal:
Persist normalized nodes and edges.

Tasks:
- implement repositories
- upsert files
- upsert nodes
- upsert edges
- delete stale file-owned data
- query by ID and qualified name

Done when:
- graph survives restarts
- incremental cleanup works

## Phase 5: Context builder

Goal:
Assemble useful symbol context.

Tasks:
- symbol lookup
- parent lookup
- child lookup
- incoming edge lookup
- outgoing edge lookup
- context assembly
- confidence and freshness summary

Done when:
- `get_symbol_context` works locally via CLI

## Phase 6: LSP references

Goal:
Enrich the graph with `references`.

Tasks:
- implement minimal LSP client
- resolve declaration positions
- request references
- map usage locations back to graph nodes
- write `references` edges
- support reverse `referenced_by` queries

Done when:
- selected symbols return references from LSP enrichment

## Phase 7: Risk engine

Goal:
Turn graph facts into deterministic assessments.

Tasks:
- implement issue detection
- implement simple score model
- emit facts
- emit issue codes
- emit decision

Done when:
- `evaluate_plan_risk` works locally via CLI

## Phase 8: MCP server

Goal:
Expose the system to the agent.

Tasks:
- register MCP tools
- validate inputs
- return JSON results
- expose all initial tools

Done when:
- external agent can call the tools

## Phase 9: Watch mode

Goal:
Support incremental graph refresh.

Tasks:
- watch files
- debounce
- reparse changed files
- delete stale symbols and edges
- refresh affected LSP references

Done when:
- saving a file updates graph state without full reindex

## Phase 10: Real workflow validation

Goal:
Use the system in the intended plan-review loop.

Workflow:
1. draft plan
2. refine plan
3. inspect target symbols
4. evaluate plan risk
5. revise plan if needed
6. ask user approval
7. only then implement

Done when:
- the workflow prevents obvious bad edits on real repos

---

# 17. Testing strategy

You need tests earlier than you think.

## 17.1 Scanner tests
Check:
- ignored folders
- module path derivation
- file hashing
- stable relative paths

## 17.2 AST extraction tests
Check:
- module extraction
- class extraction
- method extraction
- async extraction
- decorators
- docstrings
- ranges

## 17.3 Edge tests
Check:
- `contains`
- `imports`
- `inherits`

## 17.4 LSP mapping tests
Check:
- declaration selection positions
- usage location mapping
- fallback to module when no containing symbol exists
- confidence downgrades on fuzzy matches

## 17.5 Context tests
Check:
- parent/child relationships
- incoming/outgoing edges
- assembled summaries

## 17.6 Risk tests
Check:
- unresolved targets
- many references
- public symbol changes
- cross-module spread
- stale graph state

## 17.7 MCP tests
Check:
- valid tool responses
- invalid input handling
- JSON serialization
- deterministic outputs

---

# 18. Practical implementation advice

## 18.1 Start with one repo fixture
Do not test against giant real projects first.
Make tiny fixture repos where you know the expected graph.

## 18.2 Keep unresolved data explicit
If you cannot resolve an import or base class, store it as unresolved.
Do not fake a resolved edge.

## 18.3 Prefer IDs over names in storage
Names are for people.
IDs are for systems.

## 18.4 Keep LSP refresh optional
Do not force LSP refresh on every single request at first.
Allow cached references with optional refresh.

## 18.5 Do not overbuild English output
The server should return compact structured truth.
The agent can talk.

---

# 19. Things to avoid

- do not start with multiple languages
- do not force raw LSP shapes to become your full database model
- do not store both `references` and `referenced_by` as independent truth
- do not build a graph database before you feel real pain
- do not let the agent proceed on risky plans without approval
- do not hide stale data
- do not overinvest in pretty explanations before graph correctness

---

# 20. MVP definition

Version 1 is successful if:

- one Python repo can be indexed
- modules, classes, and callables are extracted correctly
- `contains`, `imports`, and `inherits` edges exist
- selected symbols can be enriched with `references`
- reverse `referenced_by` queries work
- symbol context is available through MCP
- plan risk can be evaluated deterministically
- the agent uses this before implementation
- the user remains the approval gate

That is enough to be genuinely useful.

---

# 21. Final build advice

Ask AI to generate this project phase by phase.

Best order:
1. models and DB schema
2. scanner
3. AST extractor
4. graph storage
5. context builder
6. LSP reference enrichment
7. risk engine
8. MCP tools
9. watch mode
10. polish

Do not ask for:
“build the whole product”
That is how you get a nice-looking broken mess.

Ask for:
“implement Phase 1 using the README contract”
then
“implement Phase 2”
and so on.

The more strictly you define the schema and responsibilities first, the less garbage the AI will invent.
```