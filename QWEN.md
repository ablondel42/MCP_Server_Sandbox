# QWEN.md

## Project Overview

**MCP Server Sandbox** is a local-first repository intelligence engine for safer AI-assisted code planning. The system scans a codebase, builds a structural graph using AST extraction, enriches it with LSP-based reference data, computes deterministic risk analysis, and exposes all capabilities through an MCP (Model Context Protocol) server. An AI agent uses these tools to inspect context, assess risk, and revise implementation plans before a human approves any code changes.

**Core value proposition:** Safer AI-assisted planning through deterministic pre-change checking and human approval gates before implementation.

**Current Status:** Phases 0-8 complete. Phases 9-10 pending.

---

## Architecture

The system follows a layered architecture:

```
Local repo
  -> Repository Scanner (file inventory) ✅ Phase 02
  -> AST Extraction (structural graph) ✅ Phase 03
  -> SQLite Graph Storage ✅ Phase 04
  -> Context Builder (symbol-centered views) ✅ Phase 05
  -> LSP Reference Enrichment ✅ Phase 06
  -> Risk Engine (deterministic analysis) ✅ Phase 07
  -> MCP Server (tool exposure) ✅ Phase 08
  -> Watch Mode (incremental updates) ⏳ Phase 09
  -> Workflow Layer (plan->check->approve->implement) ⏳ Phase 10
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
| **Watch Mode** | Incremental graph updates on filesystem changes | 09 | ⏳ Pending |
| **Workflow Layer** | Enforces plan->check->approve->implement sequence | 10 | ⏳ Pending |

---

## Tech Stack

- **Language:** Python 3.11+
- **Database:** SQLite (local, zero-setup)
- **Package Management:** `pyproject.toml` with setuptools
- **Models:** Pydantic v2 for validation, dataclasses for canonical schema
- **AST:** Python `ast` module
- **LSP:** `lsprotocol==2023.0.1`, pyright (external)
- **MCP:** `mcp>=1.2.0` (FastMCP)
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
        migrations.py         # Schema setup (5 tables, 13 indexes)
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
        risk_rules.py         # Issue detection (10 issue codes)
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
      validation/
        __init__.py
        exceptions.py         # Validation exception types
        validators.py         # Field validators
      cli/
        __init__.py
        main.py               # CLI entry point (17 commands)
  tests/
    __init__.py
    test_*.py                 # 343 unit and integration tests
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

### Development Commands

```bash
# Initialize database
rc init-db

# Health check
rc doctor

# Full pipeline: init + scan + extract-ast + LSP references
rc run full /path/to/repo

# Scan repository only
rc run scan /path/to/repo

# Repository scan (standalone)
rc scan-repo /path/to/repo

# AST extraction
rc extract-ast /path/to/repo

# Graph statistics
rc graph-stats repo:test

# Find symbols
rc find-symbol repo:test ClassName --kind class

# Get symbol context
rc symbol-context repo:test sym:repo:test:class:MyClass

# Symbol references
rc symbol-references repo:test MyClass --direction incoming

# Risk analysis (single symbol)
rc risk-symbol sym:repo:test:function:my_func

# Risk analysis (multiple symbols)
rc risk-targets sym:repo:test:function:func1 sym:repo:test:function:func2

# Start MCP server
rc serve-mcp [--db-path PATH] [--debug]

# Run all tests
pytest

# Run specific test file
pytest tests/test_risk_engine.py

# Run with verbose output
pytest -v
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

### Indexes (13+)

- `idx_nodes_repo_id`, `idx_nodes_file_id`, `idx_nodes_qualified_name`, `idx_nodes_parent_id`, `idx_nodes_kind`
- `idx_edges_repo_id`, `idx_edges_from_id`, `idx_edges_to_id`, `idx_edges_kind`, `idx_edges_evidence_file_id`
- `idx_files_repo_id`
- `idx_index_runs_repo_id`, `idx_index_runs_status`

---

## Risk Engine

### Issue Codes (10)

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

### Error Handling

- Use `logger.exception("message")` for errors with traceback
- Include function name prefix in error messages: `"cmd_name: Failed to do something"`
- Let exceptions bubble to main() wrapper for CLI commands
- MCP tools return structured error results, never raw exceptions

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
9. **Watch Mode** ⏳ - Incremental updates on file changes
10. **Real Workflow** ⏳ - Plan->check->approve->implement enforcement

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

### STDIO Safety

- MCP servers using stdio transport must **never write to stdout**
- All logging goes to stderr via `print(..., file=sys.stderr)` or project logger
- Writing to stdout corrupts JSON-RPC messages and breaks the server

### Freshness Policy

- Read-only tools must not auto-refresh implicitly
- Unrefreshed references ≠ zero references (availability=False)
- Explicit refresh state tracked in `reference_refresh` table

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
