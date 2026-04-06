# QWEN.md

## Project Overview

**MCP Server Sandbox** is a local-first repository intelligence engine for safer AI-assisted code planning. The system scans a codebase, builds a structural graph using AST extraction, enriches it with LSP-based reference data, computes deterministic risk analysis, and exposes all capabilities through an MCP (Model Context Protocol) server. An AI agent uses these tools to inspect context, assess risk, and revise implementation plans before a human approves any code changes.

**Core value proposition:** Safer AI-assisted planning through deterministic pre-change checking and human approval gates before implementation.

**Current Status:** Phases 0-9 complete. Phase 10 (workflow layer) pending.

**Test status:** 364 tests pass, 0 warnings.

---

## Architecture

The system follows a layered architecture:

```
Local repo
  -> Repository Scanner (file inventory)        ✅ Phase 02
  -> AST Extraction (structural graph)          ✅ Phase 03
  -> SQLite Graph Storage                       ✅ Phase 04
  -> Context Builder (symbol-centered views)    ✅ Phase 05
  -> LSP Reference Enrichment                   ✅ Phase 06
  -> Risk Engine (deterministic analysis)       ✅ Phase 07
  -> MCP Server (tool exposure)                 ✅ Phase 08
  -> Watch Mode (incremental updates)           ✅ Phase 09
  -> Workflow Layer (plan→check→approve→impl)   ⏳ Phase 10
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
| **LSP References** | Enriches graph with `references` edges via language server queries | 06 | ✅ Complete |
| **Risk Engine** | Deterministic risk analysis: facts, issues, scores, decisions | 07 | ✅ Complete |
| **MCP Server** | Exposes 6 tools: resolve, context, refresh refs, get refs, risk (single/multi) | 08 | ✅ Complete |
| **Watch Mode** | Filesystem watching, debounce, incremental reindex, reference invalidation | 09 | ✅ Complete |
| **Workflow Layer** | Enforces plan→check→approve→implement sequence | 10 | ⏳ Pending |

---

## Tech Stack

- **Language:** Python 3.11+
- **Database:** SQLite (local, zero-setup)
- **Package Management:** `pyproject.toml` with setuptools
- **Models:** Pydantic v2 for validation, dataclasses for canonical schema
- **AST:** Python `ast` module
- **LSP:** `lsprotocol==2023.0.1`, pyright (external)
- **MCP:** `mcp>=1.2.0` (FastMCP)
- **Filesystem Watch:** `watchdog>=3.0.0`
- **Testing:** pytest

---

## Project Structure

```text
MCP_Server_Sandbox/
  build-plan-phases/          # Detailed phase specifications (00-10)
  QWEN.md                     # This file
  README.md                   # Architecture overview
  pyproject.toml              # Package config
  repo_context.db             # Local SQLite database (git-ignored)
  src/
    repo_context/
      __init__.py
      config.py               # App config (db_path, ignored_dirs, extensions)
      constants.py            # Constants and edge kind constants
      logging_config.py       # Structured logging setup
      models/
        __init__.py
        common.py             # Position, Range, to_json, from_json
        repo.py               # RepoRecord
        file.py               # FileRecord
        node.py               # SymbolNode
        edge.py               # Edge
        context.py            # SymbolContext
        assessment.py         # PlanAssessment
      storage/
        __init__.py
        db.py                 # SQLite connection helpers
        migrations.py         # Schema setup (5+ tables, 22 indexes)
        repos.py              # RepoRecord persistence
        files.py              # FileRecord persistence
        nodes.py              # SymbolNode persistence
        edges.py              # Edge persistence
        graph.py              # File graph replacement operations
        reference_refresh.py  # LSP refresh state tracking
      graph/
        __init__.py
        queries.py            # Graph query operations
        filters.py            # Graph filtering utilities
        references.py         # Reference graph queries
        risk_types.py         # RiskTarget, RiskFacts, RiskResult
        risk_targets.py       # Target normalization, public-surface heuristic
        risk_facts.py         # Fact extraction (refs, inheritance, freshness, confidence)
        risk_rules.py         # Issue detection (11 issue codes)
        risk_scoring.py       # Score weights + decision logic
        risk_engine.py        # Main entry points
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
      lsp/
        __init__.py
        client.py             # Pyright LSP client (stdio)
        protocol.py           # LSP protocol helpers
        resolver.py           # Position resolution
        mapper.py             # Range containment, symbol mapping
        references.py         # Reference enrichment orchestration
      mcp/
        __init__.py
        server.py             # FastMCP server wiring
        tools.py              # 6 MCP tool handlers
        schemas.py            # Pydantic input/output schemas
        errors.py             # Structured error helpers
        adapters.py           # Internal → tool payload adapters
      indexing/
        __init__.py
        watch.py              # Watchdog setup + event routing
        events.py             # FileChangeEvent, normalize_event
        scheduler.py          # EventScheduler with debounce
        incremental.py        # reindex_changed_file, handle_deleted_file, process_event_batch
        invalidation.py       # mark_symbols_in_file_stale, invalidate_reference_summaries_for_file
      validation/
        __init__.py
        exceptions.py         # Validation exception types
        validators.py         # Field validators
      cli/
        __init__.py
        main.py               # CLI entry point (20 commands)
  tests/
    __init__.py
    test_*.py                 # 364 unit and integration tests
    fixtures/                 # Test fixtures
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

### CLI Commands

```bash
# Initialize database
rc init-db [--db-path PATH]

# Health check (tables, indexes)
rc doctor [--db-path PATH]

# Full pipeline: init + scan + extract-ast + LSP references
rc run full /path/to/repo [--db-path PATH]

# Repository scan only
rc scan-repo /path/to/repo [--db-path PATH] [--json]

# AST extraction only
rc extract-ast /path/to/repo [--db-path PATH] [--json]

# Graph statistics
rc graph-stats repo:test [--db-path PATH] [--json]

# Find symbols by name pattern
rc find-symbol repo:test ClassName [--kind KIND] [--limit N] [--db-path PATH] [--json]

# Get full symbol context
rc symbol-context repo:test sym:repo:test:class:MyClass [--db-path PATH] [--by-name] [--json]

# Get symbol references
rc symbol-references repo:test MyClass [--direction incoming|outgoing|both] [--db-path PATH] [--json]

# Refresh LSP references
rc refresh-references SYMBOL_ID [--db-path PATH] [--verbose]

# Show stored references
rc show-references SYMBOL_ID [--db-path PATH] [--json]

# Show symbols that reference this symbol
rc show-referenced-by SYMBOL_ID [--db-path PATH] [--json]

# List all nodes
rc list-nodes repo:test [--db-path PATH] [--json]

# Show details for a specific node
rc show-node SYMBOL_ID [--db-path PATH] [--json]

# Risk analysis (single symbol)
rc risk-symbol SYMBOL_ID [--db-path PATH] [--json]

# Risk analysis (multiple symbols)
rc risk-targets SYMBOL1 SYMBOL2 [--db-path PATH] [--json]

# Start MCP server on stdio
rc serve-mcp [--db-path PATH] [--debug]

# Watch repository for file changes (incremental updates)
rc watch /path/to/repo [--debounce-ms MS] [--verbose] [--db-path PATH]
```

### Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_watch_mode.py

# Run with verbose output
pytest -v

# Run with coverage (if installed)
pytest --cov=repo_context
```

---

## MCP Tools

| Tool | Purpose | Input | Output |
|------|---------|-------|--------|
| `resolve_symbol_tool` | Resolve symbol by repo_id + qualified_name | repo_id, qualified_name, kind?, file_id? | symbol payload |
| `get_symbol_context_tool` | Get full symbol context | symbol_id | context with relationships |
| `refresh_symbol_references_tool` | Refresh LSP references | symbol_id | reference summary |
| `get_symbol_references_tool` | Get stored references (read-only) | symbol_id | references + summary |
| `analyze_symbol_risk_tool` | Single symbol risk analysis | symbol_id | risk result |
| `analyze_target_set_risk_tool` | Multi-symbol risk analysis | symbol_ids (list) | risk result |

### Tool Output Contract

All tools return JSON with:
- Success: `{"ok": true, "data": {...}, "error": null}`
- Error: `{"ok": false, "data": null, "error": {"code": "...", "message": "...", "details": {...}}}`

### Error Codes

`invalid_input`, `symbol_not_found`, `ambiguous_symbol`, `references_unavailable`, `lsp_failure`, `stale_context`, `internal_error`

---

## Database Schema

### Tables (6)

1. **repos** - Repository metadata
2. **files** - File inventory
3. **nodes** - Symbol nodes (modules, classes, functions, methods)
4. **edges** - Relationships (`contains`, `imports`, `inherits`, `SCOPE_PARENT`, `references`)
5. **index_runs** - Indexing operation tracking
6. **reference_refresh** - LSP refresh state per symbol

### Indexes (22)

- `idx_nodes_repo_id`, `idx_nodes_file_id`, `idx_nodes_qualified_name`, `idx_nodes_parent_id`, `idx_nodes_kind`
- `idx_edges_repo_id`, `idx_edges_from_id`, `idx_edges_to_id`, `idx_edges_kind`, `idx_edges_evidence_file_id`
- `idx_files_repo_id`
- `idx_index_runs_repo_id`, `idx_index_runs_status`
- Additional LSP and reference-related indexes

---

## Risk Engine

### Issue Codes (11)

| Issue | Weight | Trigger |
|-------|--------|---------|
| `stale_context` | +20 | Symbol has missing/old `last_indexed_at` |
| `low_confidence_match` | +20 | Symbol or edge confidence < 0.8 |
| `high_reference_count` | +30 | 15+ references (availability=True) |
| `moderate_reference_count` | +15 | 5-14 references (availability=True) |
| `cross_file_impact` | +20 | References from multiple files |
| `cross_module_impact` | +25 | References from multiple modules |
| `public_surface_change` | +20 | Public API symbol affected |
| `inheritance_risk` | +15 | Inheritance edges involved |
| `multi_file_change` | +15 | Targets span multiple files |
| `multi_module_change` | +20 | Targets span multiple modules |
| `reference_data_unavailable` | +15 | References never refreshed |

### Decision Thresholds

- **0-29:** `safe_enough`
- **30-69:** `review_required`
- **70-100:** `high_risk`

### Override Rules

- `stale_context` → at least `review_required`
- `low_confidence_match` + another issue → at least `review_required`
- `reference_data_unavailable` + (public_surface OR cross_module OR inheritance) → at least `review_required`
- Local scope mitigation: `-10` if `touches_local_scope_only` and no `public_surface_change`

---

## Watch Mode

### Event Flow

```
Filesystem change
  -> Watchdog event
  -> normalize_event() → FileChangeEvent
  -> EventScheduler.submit() (dedup by path)
  -> Debounce window (default 500ms)
  -> collapse_events() (created+modified→create, deleted wins)
  -> process_event_batch() (one file at a time)
  -> reindex_changed_file() or handle_deleted_file()
  -> invalidate_reference_summaries_for_file()
  -> mark_symbols_in_file_stale()
  -> Per-file summary returned
```

### Event Collapse Rules

- Repeated `modified` events → one `modified`
- `created` + `modified` → one effective create
- Latest `deleted` wins over earlier create or modify
- One final path processed once per batch

### Parse Failure Policy

- Keep previous valid graph state unchanged
- Do not invalidate previously valid graph state
- Return `status = "parse_failed"` summary
- Log the parse failure

### Reference Invalidation Policy

- Remove `references` edges where `evidence_file_id = changed_file_id`
- Mark reference availability for symbols declared in that file as unavailable
- Do not auto-trigger LSP refresh on every save

---

## Development Conventions

### Code Style

- **Type hints:** Use modern Python typing (`str | None`, `list[str]`)
- **Pydantic v2:** Used for input validation in MCP schemas
- **Dataclasses:** Prefer for models and contracts
- **Functions:** Small, focused, single responsibility
- **Modules:** Keep under ~200 lines; split when growing
- **Naming:** `snake_case` for functions, `PascalCase` for classes
- **Imports:** All imports at top of file; never inside functions or classes

### Logging

- Use `from repo_context.logging_config import get_logger`
- Logger: `logger = get_logger("module.name")`
- **STDIO servers must never write to stdout** - use `file=sys.stderr` or logger
- Log format includes: `%(asctime)s [%(levelname)s] %(name)s:%(lineno)d (%(funcName)s): %(message)s`
- Use `logger.exception("message")` for errors with traceback
- Include function name prefix in error messages: `"cmd_name: Failed to do something"`

### Error Handling

- Let exceptions bubble to main() wrapper for CLI commands
- MCP tools return structured error results, never raw exceptions
- Use `print(f"Error: ...", file=sys.stderr)` for user-facing CLI errors

### Model Design

- **Canonical schema first:** All subsystems target the same models
- **IDs over names:** Stable identifiers (e.g., `file:{path}`, `repo:{name}`, `sym:{repo}:{kind}:{qualified_name}`)
- **Provenance matters:** Record `source` (e.g., `python-ast`, `lsp`, `derived`)
- **Confidence fields:** Track trustworthiness of data
- **No mutable defaults:** Use `field(default_factory=list)` or `field(default_factory=dict)`

### Testing Practices

- **Test persistence correctness:** Upsert, cleanup, replacement
- **Use temporary directories:** Never write to default DB path in tests
- **Scenario-based tests:** Validate end-to-end behavior
- **Fixture strategy:** Use small realistic repo fixtures
- **Test edge cases:** Empty repos, invalid paths, ignored directories, nested functions
- **Integration tests:** Test MCP server via real JSON-RPC over stdio
- **No return values in test functions:** Use `assert` instead of `return 0`/`return 1`

### Database Rules

- **Always use parameterized queries** through SQLite helpers
- **Upsert by ID:** Use `ON CONFLICT(id) DO UPDATE`
- **File ownership:** Every node/edge tracks owning file for cleanup
- **Transactions:** Wrap file-level operations in transactions
- **No concurrent writes:** Single-writer expectation for v1

---

## Phase Build Order

The system must be built in this exact sequence to avoid rework:

1. **Bootstrap** ✅ - Project setup, models, SQLite init, CLI shell
2. **Repo Scanner** ✅ - File inventory, path normalization, hashing
3. **AST Extraction** ✅ - Symbol extraction, structural edges
4. **Graph Storage** ✅ - Persistence, upsert, cleanup, queries
5. **Context Builder** ✅ - Symbol-centered context assembly
6. **LSP References** ✅ - Reference enrichment, location mapping
7. **Risk Engine** ✅ - Facts, issues, scoring, decisions
8. **MCP Server** ✅ - Tool exposure, input/output contracts
9. **Watch Mode** ✅ - Incremental updates on file changes
10. **Real Workflow** ⏳ - Plan→check→approve→implement enforcement

---

## Key Design Principles

### Determinism

- Same repo state → same tool outputs
- No LLM reasoning inside the server
- No hidden auto-refresh behavior
- All outputs machine-friendly and JSON-serializable

### Separation of Concerns

- **Scanner** discovers files, doesn't parse AST
- **AST extraction** builds graph, doesn't store or query
- **Storage** persists data, doesn't compute context
- **Context builder** assembles views, doesn't do risk analysis
- **Risk engine** computes scores, doesn't generate text
- **MCP server** exposes tools, doesn't implement business logic
- **Watch mode** keeps graph fresh, doesn't touch MCP

### STDIO Safety

- MCP servers using stdio transport must **never write to stdout**
- All logging goes to stderr via `print(..., file=sys.stderr)` or project logger
- Writing to stdout corrupts JSON-RPC messages and breaks the server

### Freshness Policy

- Read-only tools must not auto-refresh implicitly
- Unrefreshed references ≠ zero references (availability=False)
- Explicit refresh state tracked in `reference_refresh` table
- Watch mode invalidates stale references, doesn't auto-refresh

### Watch Mode Coexistence

- Watch mode runs as a separate process from the MCP server by default
- Single-writer SQLite expectation
- Not coupled to MCP server lifecycle
- MCP can function without watch mode running

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
- **Edges don't have file_id:** Use subqueries on nodes to find file-owned edges

### Watch Mode

- **Concurrent DB writes:** One worker only in v1, sequential processing
- **Auto-refreshing references:** Don't trigger expensive LSP on every save
- **Destroying valid state on parse failure:** Keep previous graph intact
- **Ignoring debounce:** Noisy editor saves will overwhelm without it

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

---

## References

- `build-plan-phases/00-quick-summary.md` - Phase overview
- `build-plan-phases/01-bootstrap.md` - Foundation setup (✅ Complete)
- `build-plan-phases/02-repo-scanner.md` - File inventory (✅ Complete)
- `build-plan-phases/03-ast-extraction.md` - Structural graph (✅ Complete)
- `build-plan-phases/03b-nesting-support.md` - Nested function support (✅ Complete)
- `build-plan-phases/04-graph-storage.md` - Persistence layer (✅ Complete)
- `build-plan-phases/05-context-builder.md` - Context assembly (✅ Complete)
- `build-plan-phases/06-lsp-references.md` - Reference enrichment (✅ Complete)
- `build-plan-phases/07-risk-engine.md` - Risk analysis (✅ Complete)
- `build-plan-phases/08-mcp-server.md` - Tool exposure (✅ Complete)
- `build-plan-phases/09-watch-mode.md` - Incremental updates (✅ Complete)
- `build-plan-phases/10-real-workflow.md` - End-to-end workflow (⏳ Next)
