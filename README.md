## Architecture overview

This system is a local-first repository intelligence engine for safer AI-assisted code planning.

The architecture is intentionally simple:

- the codebase is scanned and indexed locally
- structural and reference data are stored in a local SQLite database
- Python services read that database and compute context or risk
- an MCP server exposes those services as deterministic tools
- an AI agent calls those MCP tools before proposing or making changes
- a human approves the plan before implementation starts

The MCP layer is not the database and not the reasoning brain.
It is the tool access layer sitting on top of the local graph.

---

## Main components

### 1. Repository scanner

The scanner walks the local repository and finds supported source files.

Responsibilities:
- validate repo root
- ignore junk directories
- keep only supported files
- derive repo-relative paths
- derive file URIs
- derive module paths
- compute file hashes and metadata
- store `RepoRecord` and `FileRecord`

Output:
- local file inventory in SQLite

---

### 2. AST extraction layer

The AST layer parses Python files and extracts structural graph data.

Responsibilities:
- create module nodes
- create class nodes
- create function and method nodes
- create `contains` edges
- create `imports` edges
- create `inherits` edges
- store declaration ranges and symbol metadata

Output:
- structural graph stored in SQLite

---

### 3. Graph storage layer

The graph storage layer is the persistence and query foundation.

Responsibilities:
- upsert nodes
- upsert edges
- replace one file’s graph state cleanly
- query by node ID
- query by qualified name
- query incoming and outgoing edges
- query parent and child relationships

Output:
- durable local graph in SQLite

---

### 4. Context builder

The context builder reads graph data and assembles a useful symbol-centered view.

Responsibilities:
- load one symbol
- find parent symbol
- find child symbols
- load incoming and outgoing edges
- compute structural summary
- compute freshness summary
- compute confidence summary
- expose reference summary placeholder or actual values

Output:
- `SymbolContext`

---

### 5. LSP reference enrichment

This layer adds semantic usage information that AST alone cannot provide well enough.

Responsibilities:
- choose the best declaration position for a symbol
- ask the Python language server for references
- map returned locations back to internal symbols
- create `references` edges
- derive `referenced_by` through reverse queries
- compute reference counts and spread

Output:
- reference graph enrichment in SQLite

---

### 6. Risk engine

The risk engine turns graph facts into deterministic risk outputs.

Responsibilities:
- inspect targets
- inspect references
- inspect cross-file and cross-module impact
- inspect public-surface heuristics
- inspect inheritance involvement
- inspect freshness and confidence
- emit issue codes
- compute score
- compute decision

Output:
- machine-friendly risk result

---

### 7. MCP server

The MCP server exposes deterministic tools to an agent.

Responsibilities:
- register tools
- validate inputs
- call internal graph, context, reference, and risk services
- return structured outputs
- return structured errors

Output:
- a tool interface the agent can query safely

---

### 8. Watch mode

Watch mode keeps the local graph fresh while files change.

Responsibilities:
- observe file changes
- debounce noisy events
- update changed file metadata
- re-extract AST structure
- replace file graph
- invalidate stale references
- keep the graph fresh enough for later MCP calls

Output:
- fresher local SQLite graph over time

---

### 9. Agent workflow layer

This is not a database or server layer.
It is the real operating workflow.

Responsibilities:
- draft plan
- call MCP tools
- revise the plan from deterministic findings
- wait for human approval
- only then begin implementation

Output:
- safer human-gated coding workflow

---

## Data flow

The data flow should look like this:

1. Local repo files are scanned.
2. File records are stored in SQLite.
3. AST extraction builds structural nodes and edges.
4. Structural graph is stored in SQLite.
5. LSP enrichment adds `references` edges.
6. Context and risk services read from SQLite and compute higher-level outputs.
7. MCP tools expose those outputs to the agent.
8. The agent uses those outputs before proposing or making code changes.
9. The human approves before implementation.

Short version:

```text
Local repo
  -> Scanner
  -> AST extraction
  -> SQLite graph
  -> Context / LSP / Risk services
  -> MCP tools
  -> Agent
  -> Human approval
  -> Implementation
