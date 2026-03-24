# QWEN.md

## Project Overview

**MCP Server Sandbox** is a local-first repository intelligence engine for safer AI-assisted code planning. The system scans a codebase, builds a structural graph using AST extraction, enriches it with LSP-based reference data, and exposes deterministic analysis tools through an MCP (Model Context Protocol) server. An AI agent uses these tools to inspect context, assess risk, and revise implementation plans before a human approves any code changes.

**Core value proposition:** Safer AI-assisted planning through deterministic pre-change checking and human approval gates before implementation.

---

## Architecture

The system follows a layered architecture:

```
Local repo
  -> Repository Scanner (file inventory)
  -> AST Extraction (structural graph)
  -> SQLite Graph Storage
  -> Context Builder (symbol-centered views)
  -> LSP Reference Enrichment
  -> Risk Engine (deterministic analysis)
  -> MCP Tools
  -> Agent
  -> Human approval
  -> Implementation
```

### Main Components

| Component | Purpose | Phase |
|-----------|---------|-------|
| **Repository Scanner** | Discovers supported files, ignores junk directories, persists file inventory | 02 |
| **AST Extraction** | Parses Python files, extracts modules/classes/callables, builds structural edges | 03 |
| **Graph Storage** | SQLite persistence for nodes and edges, upsert/cleanup/query operations | 04 |
| **Context Builder** | Assembles symbol-centered views with parent/children/edges/freshness/confidence | 05 |
| **LSP References** | Enriches graph with `references` edges via language server queries | 06 |
| **Risk Engine** | Deterministic risk analysis: facts, issues, scores, decisions | 07 |
| **MCP Server** | Exposes tools: `resolve_symbol`, `get_symbol_context`, `refresh_references`, `analyze_risk` | 08 |
| **Watch Mode** | Incremental graph updates on filesystem changes | 09 |
| **Workflow Layer** | Enforces plan->check->approve->implement sequence | 10 |

---

## Tech Stack

- **Language:** Python 3.14+
- **Database:** SQLite (local, zero-setup)
- **Package Management:** `pyproject.toml`
- **Models:** Dataclasses for canonical schema
- **AST:** Python `ast` module
- **LSP:** Minimal client (e.g., Pyright-based server)
- **Filesystem Watching:** `watchdog` library
- **MCP:** Model Context Protocol server

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
        common.py             # Position, Range
        repo.py               # RepoRecord
        file.py               # FileRecord
        node.py               # SymbolNode
        edge.py               # Edge
        context.py            # SymbolContext
        assessment.py         # Risk types
      storage/
        __init__.py
        db.py                 # SQLite initialization
        migrations.py         # Schema setup
        nodes.py              # Node persistence
        edges.py              # Edge persistence
        graph.py              # File-level graph replacement
      parsing/
        __init__.py
        scanner.py            # Repository scanning
        pathing.py            # Path normalization, module-path derivation
        hashing.py            # Content hashing
        ast_loader.py         # AST parsing
        naming.py             # Qualified names, IDs
        module_extractor.py   # Module node extraction
        class_extractor.py    # Class node extraction
        callable_extractor.py # Function/method extraction
        import_extractor.py   # Import edges
        inheritance_extractor.py
        ranges.py             # AST location normalization
        docstrings.py         # Doc summary extraction
        pipeline.py           # AST extraction orchestration
      graph/
        __init__.py
        queries.py            # Graph lookup helpers
        context.py            # SymbolContext assembly
        summaries.py          # Structural summaries
        freshness.py          # Freshness metadata
        confidence.py         # Confidence rollups
        references.py         # Reference stats/queries
        risk_engine.py        # Risk orchestration
        risk_facts.py         # Fact extraction
        risk_rules.py         # Issue detection
        risk_scoring.py       # Scoring/decision
        risk_targets.py       # Target normalization
        risk_types.py         # Risk contracts
      lsp/
        __init__.py
        client.py             # Minimal LSP client
        protocol.py           # LSP request/response helpers
        references.py         # Reference enrichment orchestration
        mapper.py             # Location-to-symbol mapping
        resolver.py           # Declaration position resolution
      mcp/
        __init__.py
        server.py             # MCP server setup
        tools.py              # Tool handlers
        schemas.py            # Input/output contracts
        errors.py             # Structured errors
        adapters.py           # Internal->tool payload mapping
      indexing/
        __init__.py
        watch.py              # Filesystem watcher
        events.py             # Event normalization
        incremental.py        # Changed-file reindex
        invalidation.py       # Reference invalidation
        scheduler.py          # Debounce/batching
      cli/
        __init__.py
        main.py               # CLI entry point
  tests/
    __init__.py
    test_smoke.py
    test_db_init.py
    test_models.py
    # ... phase-specific tests
```

---

## Building and Running

### Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -e .
```

### Development Commands

```bash
# Initialize database
repo-context init-db

# Scan a repository
repo-context scan-repo /path/to/repo

# View graph stats
repo-context graph-stats repo:project

# Inspect symbol context
repo-context show-context <node-id>

# Analyze symbol risk
repo-context analyze-symbol-risk <symbol-id>

# Start MCP server
repo-context serve-mcp

# Start watch mode
repo-context watch /path/to/repo
```

### Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_db_init.py

# Run with coverage
pytest --cov=src/repo_context
```

---

## Development Conventions

### Code Style

- **Type hints:** Use modern Python typing (3.14+)
- **Dataclasses:** Prefer for models and contracts
- **Functions:** Small, focused, single responsibility
- **Modules:** Keep under ~200 lines; split when growing
- **Naming:** Explicit over clever; `snake_case` for functions, `PascalCase` for classes

### Model Design

- **Canonical schema first:** All subsystems target the same models
- **IDs over names:** Stable identifiers for graph entities
- **Provenance matters:** Record `source` (e.g., `python-ast`, `lsp`, `derived`)
- **Confidence fields:** Track trustworthiness of data
- **Internal schema is truth:** Normalize LSP/AST data; do not use raw objects

### Database Rules

- **Always use parameterized queries** through SQLite helpers
- **Upsert by ID:** Use `ON CONFLICT(id) DO UPDATE`
- **File ownership:** Every node/edge tracks owning file for cleanup
- **Indexes:** Add indexes for `repo_id`, `file_id`, `qualified_name`, `from_id`, `to_id`
- **Transactions:** Wrap file-level operations in transactions

### Security & Safety

- **No secrets in code:** Use environment variables or config files
- **Validate all input:** MCP tool inputs must be validated
- **Fail closed:** When in doubt, deny access or block implementation
- **Deterministic outputs:** MCP tools return facts, not prose
- **Structured errors:** Use error codes (`invalid_input`, `symbol_not_found`, etc.)

### Testing Practices

- **Test persistence correctness:** Upsert, cleanup, replacement
- **Mock LSP in unit tests:** Do not depend on real language server
- **Scenario-based workflow tests:** Validate end-to-end behavior
- **Fixture strategy:** Use small realistic repo fixtures

---

## Phase Build Order

The system must be built in this exact sequence to avoid rework:

1. **Bootstrap** - Project setup, models, SQLite init, CLI shell
2. **Repo Scanner** - File inventory, path normalization, hashing
3. **AST Extraction** - Symbol extraction, structural edges
4. **Graph Storage** - Persistence, upsert, cleanup, queries
5. **Context Builder** - Symbol-centered context assembly
6. **LSP References** - Reference enrichment, location mapping
7. **Risk Engine** - Facts, issues, scoring, decisions
8. **MCP Server** - Tool exposure, input/output contracts
9. **Watch Mode** - Incremental updates on file changes
10. **Real Workflow** - Plan->check->approve->implement enforcement

**Build logic:**
- Phases 1-4: Build truth (scanning, extraction, storage)
- Phases 5-7: Build reasoning inputs (context, references, risk)
- Phase 8: Expose tools (MCP)
- Phase 9: Keep state fresh (watch mode)
- Phase 10: Turn into product workflow

---

## Key Design Principles

### MCP Server Design

- **Deterministic only:** Return facts, issue codes, scores, decisions
- **Narrow tools:** One tool, one job
- **Strict schemas:** Validate inputs, stable outputs
- **Structured errors:** Error codes, not string exceptions
- **No natural language:** Agent explains; server provides data

### Risk Engine Design

- **Facts first, scoring second:** Extract facts, derive issues, compute score
- **Reusable:** Works for single symbols, target sets, later plan wrappers
- **Honest about uncertainty:** Stale/low-confidence data increases caution
- **Deterministic:** Same graph state -> same risk output

### Reference Enrichment

- **Store `references`, derive `referenced_by`:** Single source of truth
- **Map to internal symbols:** LSP locations become graph edges
- **Honest confidence:** Exact containment = 0.9, module fallback = 0.7
- **Unavailable ≠ zero:** Mark `available=False` when never refreshed

### Watch Mode

- **Incremental by default:** Reindex changed files only
- **Debounce noisy events:** Batch multiple saves into one operation
- **Preserve valid state on parse failure:** Do not destroy graph on temp syntax errors
- **Invalidate references:** Mark stale when evidence file changes

### Workflow Enforcement

- **Planning ≠ Implementation:** Hard separation
- **Required tool usage:** Resolve, inspect, refresh, analyze before approval
- **Blocking conditions:** Unresolved targets, missing context, no approval
- **Agent rules:** Never implement before approval; never hide uncertainty

---

## Data Contracts

### SymbolNode (Base)

```python
@dataclass
class SymbolNode:
    id: str                    # sym:{repo_id}:{kind}:{qualified_name}
    repo_id: str
    file_id: str
    language: str
    kind: str                  # module, class, function, async_function, method, async_method
    name: str
    qualified_name: str        # app.services.auth.AuthService.login
    uri: str                   # file:///...
    range_json: Optional[str]
    selection_range_json: Optional[str]
    parent_id: Optional[str]
    visibility_hint: Optional[str]  # public, private_like, protected_like, module
    doc_summary: Optional[str]
    content_hash: str
    semantic_hash: str
    source: str                # python-ast, lsp, merged
    confidence: float
    payload_json: str          # Type-specific fields
    last_indexed_at: Optional[str]
```

### Edge

```python
@dataclass
class Edge:
    id: str                    # edge:{repo_id}:{kind}:{from_id}->{to_id}:{evidence}
    repo_id: str
    kind: str                  # contains, imports, inherits, references
    from_id: str
    to_id: str
    source: str                # python-ast, lsp, derived
    confidence: float
    evidence_file_id: Optional[str]
    evidence_uri: Optional[str]
    evidence_range_json: Optional[str]
    payload_json: str
    last_indexed_at: Optional[str]
```

### SymbolContext

```python
@dataclass
class SymbolContext:
    focus_symbol: dict
    parent: Optional[dict]
    children: list[dict]
    outgoing_edges: list[dict]
    incoming_edges: list[dict]
    reference_summary: dict    # reference_count, referencing_file_count, available
    structural_summary: dict   # kind, child_count, edge counts
    freshness: dict            # is_stale, timestamps
    confidence: dict           # overall_confidence, min values
```

### RiskResult

```python
@dataclass
class RiskResult:
    targets: list[RiskTarget]
    facts: RiskFacts
    issues: list[str]          # Issue codes
    risk_score: int            # 0-100
    decision: str              # safe_enough, review_required, high_risk
```

---

## MCP Tools

| Tool | Input | Output | Purpose |
|------|-------|--------|---------|
| `resolve_symbol` | repo_id, qualified_name, kind | symbol | Resolve human name to stable ID |
| `get_symbol_context` | symbol_id | SymbolContext | Full local context |
| `refresh_symbol_references` | symbol_id | reference_summary | LSP reference refresh |
| `get_symbol_references` | symbol_id | references list | Stored incoming references |
| `analyze_symbol_risk` | symbol_id | RiskResult | Single-symbol risk |
| `analyze_target_set_risk` | symbol_ids list | RiskResult | Multi-symbol risk |

---

## Common Mistakes to Avoid

### Architecture

- **Overengineering early:** Keep v1 simple; add complexity only when needed
- **Mixing domain logic into CLI:** CLI orchestrates; domain logic lives in modules
- **Skipping canonical models:** Do not use raw AST/LSP objects as schema
- **Building IDE features:** LSP is for references only, not hover/rename/completion

### Database

- **Forgetting cleanup on reindex:** Always replace file graph cleanly
- **Skipping indexes:** Graph queries need indexes on from_id, to_id, qualified_name
- **Raw SQL everywhere:** Use storage helpers; keep SQL in one place
- **Orphan nodes/edges:** Every entity must belong to a repo and file

### MCP

- **Making server "smart":** Deterministic facts, not conversational explanations
- **Leaking raw DB rows:** Adapt internal objects to stable tool payloads
- **Mixing refresh and read:** Reference refresh should be explicit, not hidden
- **Weak error contracts:** Use structured error codes, not string exceptions

### Risk Engine

- **Putting plan resolution in engine:** Engine works on resolved targets
- **Returning prose instead of structure:** Facts, issues, scores, decisions
- **Treating unavailable references as zero:** Unavailable is not zero
- **Scattering risk rules:** Keep all risk logic in one place

### Watch Mode

- **Full reindex on every save:** Defeats the purpose; use incremental updates
- **Trusting raw watcher events:** Normalize and debounce first
- **Deleting valid graph on syntax errors:** Preserve last valid state
- **Forgetting reference invalidation:** Structural refresh alone is insufficient

### Workflow

- **Treating approval as optional:** Hard gate; no exceptions
- **Letting agent code while "still planning":** Destroys guardrail model
- **Using MCP after plan is decided:** MCP should improve plan before approval
- **Hiding uncertainty from human:** User must know about stale/weak context

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

## References

- `build-plan-phases/00-quick-summary.md` - Phase overview
- `build-plan-phases/01-bootstrap.md` - Foundation setup
- `build-plan-phases/02-repo-scanner.md` - File inventory
- `build-plan-phases/03-ast-extraction.md` - Structural graph
- `build-plan-phases/04-graph-storage.md` - Persistence layer
- `build-plan-phases/05-context-builder.md` - Context assembly
- `build-plan-phases/06-lsp-references.md` - Reference enrichment
- `build-plan-phases/07-risk-engine.md` - Risk analysis
- `build-plan-phases/08-mcp-server.md` - Tool exposure
- `build-plan-phases/09-watch-mode.md` - Incremental updates
- `build-plan-phases/10-real-workflow.md` - End-to-end workflow
