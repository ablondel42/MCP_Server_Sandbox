# QWEN.md

## Project Overview

**MCP Server Sandbox** is a local-first repository intelligence engine for safer AI-assisted code planning. The system scans a codebase, builds a structural graph using AST extraction, enriches it with LSP-based reference data, and exposes deterministic analysis tools through an MCP (Model Context Protocol) server. An AI agent uses these tools to inspect context, assess risk, and revise implementation plans before a human approves any code changes.

**Core value proposition:** Safer AI-assisted planning through deterministic pre-change checking and human approval gates before implementation.

**Current Status:** Phase 5 (Context Builder) complete. Phases 1-5 implemented.

---

## Architecture

The system follows a layered architecture:

```
Local repo
  -> Repository Scanner (file inventory) [DONE]
  -> AST Extraction (structural graph) [DONE]
  -> SQLite Graph Storage [DONE]
  -> Context Builder (symbol-centered views) [DONE]
  -> LSP Reference Enrichment [TODO]
  -> Risk Engine (deterministic analysis) [TODO]
  -> MCP Tools [TODO]
  -> Agent
  -> Human approval
  -> Implementation
```

### Main Components

| Component | Purpose | Phase | Status |
|-----------|---------|-------|--------|
| **Repository Scanner** | Discovers Python files, ignores junk directories, persists file inventory | 02 | ✅ Complete |
| **AST Extraction** | Parses Python files, extracts modules/classes/callables, builds structural edges | 03 | ✅ Complete |
| **Graph Storage** | SQLite persistence for nodes and edges, upsert/cleanup/query operations | 04 | ✅ Complete |
| **Context Builder** | Assembles symbol-centered views with parent/children/edges/freshness/confidence | 05 | ✅ Complete |
| **LSP References** | Enriches graph with `references` edges via language server queries | 06 | ⏳ Pending |
| **Risk Engine** | Deterministic risk analysis: facts, issues, scores, decisions | 07 | ⏳ Pending |
| **MCP Server** | Exposes tools: `resolve_symbol`, `get_symbol_context`, `refresh_references`, `analyze_risk` | 08 | ⏳ Pending |
| **Watch Mode** | Incremental graph updates on filesystem changes | 09 | ⏳ Pending |
| **Workflow Layer** | Enforces plan->check->approve->implement sequence | 10 | ⏳ Pending |

---

## Tech Stack

- **Language:** Python 3.11+
- **Database:** SQLite (local, zero-setup)
- **Package Management:** `pyproject.toml`
- **Models:** Dataclasses for canonical schema
- **AST:** Python `ast` module
- **LSP:** Minimal client (Phase 6+)
- **Filesystem Watching:** `watchdog` library (Phase 9+)
- **MCP:** Model Context Protocol server (Phase 8+)

---

## Project Structure

```text
MCP_Server_Sandbox/
  build-plan-phases/          # Detailed phase specifications
  QWEN.md                     # This file
  README.md                   # Architecture overview
  pyproject.toml              # Package config
  src/
    repo_context/
      __init__.py
      config.py               # App config (db_path, ignored_dirs, extensions)
      models/
        __init__.py
        common.py             # Position, Range, to_json, from_json
        repo.py               # RepoRecord
        file.py               # FileRecord
        node.py               # SymbolNode
        edge.py               # Edge
        context.py            # SymbolContext
        assessment.py         # PlanAssessment
        edge_constants.py     # Edge kind constants
      storage/
        __init__.py
        db.py                 # SQLite connection helpers
        migrations.py         # Schema setup (5 tables, 13 indexes)
        repos.py              # RepoRecord persistence
        files.py              # FileRecord persistence
        nodes.py              # SymbolNode persistence
        edges.py              # Edge persistence
        graph.py              # File graph replacement operations
      graph/
        __init__.py
        queries.py            # Graph query operations
        filters.py            # Graph filtering utilities
      context/
        __init__.py
        builders.py           # Symbol context assembly
        summaries.py          # Structural summary and confidence builders
        freshness.py          # Freshness metadata builder
        helpers.py            # Context helper functions
      parsing/
        __init__.py
        scanner.py            # Repository scanning
        pathing.py            # Path normalization, module-path derivation
        hashing.py            # Content hashing (SHA-256)
        ast_loader.py         # AST loading and parsing
        naming.py             # Symbol ID and qualified name builders
        ranges.py             # Zero-based range conversion
        docstrings.py         # Docstring summary extraction
        module_extractor.py   # Module node extraction
        class_extractor.py    # Class node extraction
        callable_extractor.py # Function/method extraction
        import_extractor.py   # Import edge extraction
        inheritance_extractor.py  # Inheritance edge extraction
        scope_tracker.py      # Lexical scope tracking for nested functions
        pipeline.py           # Per-file extraction orchestration
      cli/
        __init__.py
        main.py               # CLI entry point
  tests/
    __init__.py
    test_smoke.py             # Import and config tests
    test_db_init.py           # Database initialization tests
    test_models.py            # Model instantiation and JSON tests
    test_cli.py               # CLI command tests
    test_scanner.py           # Scanner tests
    test_ast_extraction.py    # AST extraction tests
    test_graph_storage.py     # Graph storage tests
    test_graph_queries.py     # Graph query tests
    test_context_builder.py   # Context builder tests
    test_context_freshness.py # Context freshness tests
    test_context_summaries.py # Context summary tests
    test_hashing.py           # Hashing tests
    test_pathing.py           # Path normalization tests
    fixtures/                 # Test fixtures
      simple_package/
      inheritance_case/
      async_case/
      decorators_case/
      nested_functions_case/
```

---

## Building and Running

### Setup

```bash
# Create virtual environment (if not exists)
python -m venv .venv
source .venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -e .
```

### Development Commands

```bash
# Initialize database
repo-context init-db

# Initialize database at custom path
repo-context init-db --db-path /path/to/custom.db

# Health check
repo-context doctor

# Health check at custom path
repo-context doctor --db-path /path/to/custom.db

# Scan a repository (Phase 2)
repo-context scan-repo /path/to/repo

# Scan with custom database path
repo-context scan-repo /path/to/repo --db-path /path/to/db.db

# Scan with JSON output
repo-context scan-repo /path/to/repo --json

# Extract AST from scanned repository (Phase 3)
repo-context extract-ast /path/to/repo

# Extract AST with custom database path
repo-context extract-ast /path/to/repo --db-path /path/to/db.db

# Extract AST with JSON output
repo-context extract-ast /path/to/repo --json

# Show graph statistics
repo-context graph-stats repo:test

# Find symbols by name pattern
repo-context find-symbol repo:test ClassName

# Find symbols with kind filter
repo-context find-symbol repo:test Service --kind class

# Get symbol context
repo-context symbol-context repo:test sym:repo:test:class:MyClass

# Get symbol context by name
repo-context symbol-context repo:test MyClass --by-name

# Get symbol references
repo-context symbol-references repo:test MyClass --direction incoming

# List all nodes in a repository
repo-context list-nodes repo:test

# Show details for a specific node
repo-context show-node sym:repo:test:class:MyClass

# Run all tests
pytest

# Run specific test file
pytest tests/test_context_builder.py

# Run with verbose output
pytest -v
```

---

## Development Conventions

### Code Style

- **Type hints:** Use modern Python typing (`Optional[str]`, `str | None`)
- **Dataclasses:** Prefer for models and contracts
- **Functions:** Small, focused, single responsibility
- **Modules:** Keep under ~200 lines; split when growing
- **Naming:** Explicit over clever; `snake_case` for functions, `PascalCase` for classes
- **Imports:** All imports at top of file; never inside functions or classes

### Model Design

- **Canonical schema first:** All subsystems target the same models
- **IDs over names:** Stable identifiers for graph entities (e.g., `file:{path}`, `repo:{name}`, `sym:{repo}:{kind}:{qualified_name}`)
- **Provenance matters:** Record `source` (e.g., `python-ast`, `lsp`, `derived`)
- **Confidence fields:** Track trustworthiness of data
- **Internal schema is truth:** Normalize LSP/AST data; do not use raw objects
- **No mutable defaults:** Use `field(default_factory=list)` or `field(default_factory=dict)`

### Database Rules

- **Always use parameterized queries** through SQLite helpers
- **Upsert by ID:** Use `ON CONFLICT(id) DO UPDATE`
- **File ownership:** Every node/edge tracks owning file for cleanup
- **Indexes:** Add indexes for `repo_id`, `file_id`, `qualified_name`, `from_id`, `to_id`
- **Transactions:** Wrap file-level operations in transactions

### FileRecord Contract

All fields must be present:
- `id: str` - Format: `file:{repo_relative_path}`
- `repo_id: str` - From repo record
- `file_path: str` - Repo-relative, POSIX-style
- `uri: str` - Valid `file://` URI
- `module_path: str` - Derived from filesystem (e.g., `app.services.auth`)
- `language: str` - Exactly `python`
- `content_hash: str` - SHA-256 with `sha256:` prefix
- `size_bytes: int` - From filesystem
- `last_modified_at: str` - ISO 8601 UTC string
- `last_indexed_at: str | None` - Set during scan

### SymbolNode Contract

Key fields:
- `id: str` - Format: `sym:{repo_id}:{kind}:{qualified_name}`
- `kind: str` - One of: `module`, `class`, `function`, `async_function`, `method`, `async_method`, `local_function`, `local_async_function`
- `qualified_name: str` - Full logical path (e.g., `app.services.auth.AuthService.login`)
- `parent_id: str | None` - Structural parent symbol ID
- `lexical_parent_id: str | None` - Lexical parent for nested declarations
- `scope: str` - One of: `module`, `class`, `function`
- `range_json: str | None` - Full declaration range (zero-based)
- `selection_range_json: str | None` - Name-focused range (zero-based)
- `payload_json: str` - Type-specific metadata

### Edge Contract

Key fields:
- `id: str` - Deterministic ID
- `kind: str` - One of: `contains`, `imports`, `inherits`, `SCOPE_PARENT`
- `from_id: str` - Source node ID
- `to_id: str` - Target node ID
- `source: str` - `python-ast` for Phase 3
- `confidence: float` - 1.0 for structural, 0.8 for imports, 0.75 for inheritance

### SymbolContext Contract (Phase 5)

Key fields:
- `focus_symbol: dict` - The symbol being inspected
- `structural_parent: dict | None` - Containing symbol in code hierarchy
- `structural_children: list[dict]` - Directly contained symbols
- `lexical_parent: dict | None` - Enclosing scope for nested declarations
- `lexical_children: list[dict]` - Lexically nested symbols
- `incoming_edges: list[dict]` - Relationships where others reference this symbol
- `outgoing_edges: list[dict]` - Relationships where this symbol references others
- `file_siblings: list[dict]` - Other symbols in same source file
- `structural_summary: dict` - Statistics about structural relationships
- `freshness: dict` - Timestamps indicating when context was last updated
- `confidence: dict` - Trust scores for context data reliability

### Security & Safety

- **No secrets in code:** Use environment variables or config files
- **Validate all input:** CLI inputs must be validated
- **Fail closed:** When in doubt, deny access or block implementation
- **Deterministic outputs:** CLI tools return facts, not prose
- **Structured errors:** Use error codes (`invalid_input`, `symbol_not_found`, etc.)

### Testing Practices

- **Test persistence correctness:** Upsert, cleanup, replacement
- **Use temporary directories:** Never write to default DB path in tests
- **Scenario-based tests:** Validate end-to-end behavior
- **Fixture strategy:** Use small realistic repo fixtures
- **Test edge cases:** Empty repos, invalid paths, ignored directories, nested functions

---

## Phase Build Order

The system must be built in this exact sequence to avoid rework:

1. **Bootstrap** ✅ - Project setup, models, SQLite init, CLI shell
2. **Repo Scanner** ✅ - File inventory, path normalization, hashing
3. **AST Extraction** ✅ - Symbol extraction, structural edges
4. **Graph Storage** ✅ - Persistence, upsert, cleanup, queries
5. **Context Builder** ✅ - Symbol-centered context assembly
6. **LSP References** ⏳ - Reference enrichment, location mapping
7. **Risk Engine** ⏳ - Facts, issues, scoring, decisions
8. **MCP Server** ⏳ - Tool exposure, input/output contracts
9. **Watch Mode** ⏳ - Incremental updates on file changes
10. **Real Workflow** ⏳ - Plan->check->approve->implement enforcement

**Build logic:**
- Phases 1-2: Build file inventory
- Phases 3-4: Build structural graph truth (current state)
- Phase 5: Build context assembly (symbol-centered views)
- Phases 6-7: Build reasoning inputs (context, references, risk)
- Phase 8: Expose tools (MCP)
- Phase 9: Keep state fresh (watch mode)
- Phase 10: Turn into product workflow

---

## Database Schema

### Tables (5)

1. **repos** - Repository metadata
2. **files** - File inventory
3. **nodes** - Symbol nodes (modules, classes, functions, methods)
4. **edges** - Relationships between nodes (`contains`, `imports`, `inherits`, `SCOPE_PARENT`)
5. **index_runs** - Indexing operation tracking

### Indexes (13)

- `idx_nodes_repo_id`, `idx_nodes_file_id`, `idx_nodes_qualified_name`, `idx_nodes_parent_id`, `idx_nodes_kind`
- `idx_edges_repo_id`, `idx_edges_from_id`, `idx_edges_to_id`, `idx_edges_kind`, `idx_edges_evidence_file_id`
- `idx_files_repo_id`
- `idx_index_runs_repo_id`, `idx_index_runs_status`

---

## CLI Commands

| Command | Description | Options |
|---------|-------------|---------|
| `init-db` | Initialize SQLite database | `--db-path PATH` |
| `doctor` | Health check (tables, indexes) | `--db-path PATH` |
| `scan-repo` | Scan repository for Python files (Phase 2) | `--db-path PATH`, `--json` |
| `extract-ast` | Extract AST and build structural graph (Phase 3) | `--db-path PATH`, `--json` |
| `graph-stats` | Show graph statistics for a repository | `--db-path PATH`, `--json` |
| `find-symbol` | Find symbols by name pattern | `--db-path PATH`, `--kind KIND`, `--limit N`, `--json` |
| `symbol-context` | Get full context for a symbol | `--db-path PATH`, `--by-name`, `--json` |
| `symbol-references` | Get incoming/outgoing edges for a symbol | `--db-path PATH`, `--by-name`, `--direction incoming|outgoing|both`, `--json` |
| `list-nodes` | List all nodes in a repository | `--db-path PATH`, `--json` |
| `show-node` | Show details for a specific node | `--db-path PATH`, `--json` |

---

## Key Design Principles

### Scanner Design

- **Deterministic output:** Same repo → same file list (sorted by `file_path`)
- **Exact directory matching:** Ignore `.git`, not `.github`
- **POSIX-style paths:** Always use forward slashes internally
- **Module derivation:** Drop `.py`, drop trailing `__init__`, join with dots

### AST Extraction Design

- **Structural only:** No semantic analysis in Phase 3
- **Nested functions tracked:** Phase 03b added `local_function`/`local_async_function` kinds with `lexical_parent_id`
- **Unresolved targets explicit:** `external_or_unresolved:{name}` for imports, `unresolved_base:{name}` for inheritance
- **Zero-based ranges:** All line numbers converted from AST one-based to zero-based
- **SCOPE_PARENT edges:** Track lexical scope relationships for nested declarations

### Context Builder Design (Phase 5)

- **Stored graph only:** Context assembled from persisted nodes/edges, not raw AST
- **Dual hierarchy:** Structural (`parent_id`) and lexical (`lexical_parent_id`) relationships kept separate
- **Deterministic ordering:** Children, edges, and siblings ordered by kind, name, id
- **Machine-friendly:** Structured data, no prose explanations
- **No LSP yet:** Reference summaries added in Phase 6

### Serialization

- **JSON helpers:** `to_json()` and `from_json()` in `models/common.py`
- **Sorted keys:** JSON output uses `sort_keys=True` for determinism
- **Dataclass support:** `to_json()` handles dataclasses via `asdict()`

### Hashing

- **SHA-256:** All content hashes use SHA-256
- **Prefix format:** All hashes prefixed with `sha256:`
- **Binary reading:** Files hashed as bytes, not text

### Symbol ID Format

- **Module:** `sym:{repo_id}:module:{module_path}`
- **Class:** `sym:{repo_id}:class:{qualified_name}`
- **Callable:** `sym:{repo_id}:{kind}:{qualified_name}`
- **Local function:** `sym:{repo_id}:local_function:{qualified_name}`

### Edge ID Format

- **Contains:** `edge:{repo_id}:contains:{from_id}->{to_id}`
- **Imports:** `edge:{repo_id}:imports:{from_id}->{to_id}:{lineno}`
- **Inherits:** `edge:{repo_id}:inherits:{from_id}->unresolved_base:{base_name}`
- **SCOPE_PARENT:** `edge:{repo_id}:SCOPE_PARENT:{from_id}->{to_id}`

---

## Common Mistakes to Avoid

### Architecture

- **Overengineering early:** Keep v1 simple; add complexity only when needed
- **Mixing domain logic into CLI:** CLI orchestrates; domain logic lives in modules
- **Skipping canonical models:** Do not use raw AST/LSP objects as schema
- **Building IDE features:** LSP is for references only, not hover/rename/completion

### Database

- **Forgetting cleanup on reindex:** Always replace file graph cleanly
- **Skipping indexes:** Graph queries need indexes on `from_id`, `to_id`, `qualified_name`
- **Raw SQL everywhere:** Use storage helpers; keep SQL in one place
- **Orphan nodes/edges:** Every entity must belong to a repo and file

### Scanner

- **Fuzzy directory matching:** Use exact name matching for ignored dirs
- **Absolute paths as identity:** Always use repo-relative paths
- **Non-deterministic ordering:** Always sort results by `file_path`
- **Hardcoding ignore rules:** Use `AppConfig.ignored_dirs` and `AppConfig.supported_extensions`

### AST Extraction

- **Ignoring nested functions:** Phase 03b added support for `local_function`/`local_async_function`
- **One-based line numbers:** Always convert to zero-based
- **Inventing semantic resolution:** Keep imports and bases as unresolved placeholders
- **Inconsistent ID formats:** Use the exact ID format specified

### Context Builder

- **Conflating hierarchies:** Keep `structural_parent` and `lexical_parent` separate
- **Non-deterministic ordering:** Always sort children, edges, siblings
- **Adding reasoning:** Context assembly is not risk analysis
- **Premature LSP:** Reference summaries come in Phase 6

---

## When Stuck

1. **Check the phase specification:** Read the relevant `build-plan-phases/XX-*.md` file
2. **Ask clarifying questions:** Do not guess on ambiguous requirements
3. **Propose a short plan:** 1-3 steps; get confirmation before large changes
4. **Security-critical areas:** Always explain risks and wait for confirmation
5. **Command failures:** State environment issues up front; propose next steps

**Do not:**
- Skip quality gates (typecheck, lint, tests)
- Compromise security checks to "make it work"
- Make large refactors without explicit approval
- Assume patterns; copy from existing code

---

## Git Branches

- **main:** Primary development branch
- **phase-5-context-builder:** Branch at commit e01b42a for Phase 5 work
- **backup-pre-phase5-reset-9b9f852:** Backup branch preserving work after Phase 5

---

## References

- `build-plan-phases/00-quick-summary.md` - Phase overview
- `build-plan-phases/01-bootstrap.md` - Foundation setup (✅ Complete)
- `build-plan-phases/02-repo-scanner.md` - File inventory (✅ Complete)
- `build-plan-phases/03-ast-extraction.md` - Structural graph (✅ Complete)
- `build-plan-phases/03b-nesting-support.md` - Nested function support (✅ Complete)
- `build-plan-phases/04-graph-storage.md` - Persistence layer (✅ Complete)
- `build-plan-phases/05-context-builder.md` - Context assembly (✅ Complete)
- `build-plan-phases/06-lsp-references.md` - Reference enrichment (⏳ Next)
- `build-plan-phases/07-risk-engine.md` - Risk analysis
- `build-plan-phases/08-mcp-server.md` - Tool exposure
- `build-plan-phases/09-watch-mode.md` - Incremental updates
- `build-plan-phases/10-real-workflow.md` - End-to-end workflow
