# 10-Phase Summary Plan

## 01-bootstrap

### Phase goal and added functionalities

Goal:
- create the foundation of the whole project

Added functionalities:
- Python project setup
- repo structure
- config module
- canonical core models
- SQLite initialization
- base CLI
- minimal tests
- clear package boundaries for later layers

### Phase verifiable expected results

You should be able to verify that:

- the project installs and runs
- the SQLite database can be initialized
- base tables exist
- core dataclasses or canonical models exist
- CLI commands like `init-db` and `doctor` work
- tests run successfully
- no AST, LSP, graph enrichment, or MCP logic exists yet

### Phase mandatory tests to validate

- project import smoke test
- DB initialization test
- base table existence test
- model instantiation test
- config loading test
- CLI smoke test

### Phase traps to avoid

- overengineering too early
- mixing domain logic into CLI
- using raw external schemas as internal truth
- skipping canonical models
- adding parsing or LSP too soon

---

## 02-repo-scanner

### Phase goal and added functionalities

Goal:
- discover supported files in a repository and persist file inventory

Added functionalities:
- repo root validation
- ignored directory filtering
- Python file detection
- repo-relative path generation
- file URI generation
- Python module-path derivation
- file hashing
- file metadata collection
- repo and file persistence
- scan CLI command

### Phase verifiable expected results

You should be able to verify that:

- a repository path can be scanned
- ignored folders are skipped
- only `.py` files are stored
- each file gets a stable file record
- module paths are derived correctly
- hashes, size, and timestamps are stored
- repo and file records persist in SQLite

### Phase mandatory tests to validate

- valid repo scan test
- invalid repo path test
- ignored directory skip test
- supported extension filter test
- module-path derivation test
- URI generation test
- file hash stability test
- DB persistence test
- empty repo test

### Phase traps to avoid

- parsing code inside the scanner
- storing absolute paths as primary identity
- inconsistent module-path derivation
- duplicate ignore rules in different files
- non-deterministic scan ordering

---

## 03-ast-extraction

### Phase goal and added functionalities

Goal:
- convert Python files into structural graph-ready symbols and edges using AST

Added functionalities:
- AST loading
- module node extraction
- class node extraction
- top-level function extraction
- method extraction
- async callable extraction
- decorators extraction
- inheritance extraction
- import extraction
- doc summary extraction
- declaration range extraction
- selection range extraction
- structural `contains`, `imports`, and `inherits` edges
- persistence of extracted nodes and edges

### Phase verifiable expected results

You should be able to verify that:

- each Python file becomes one module node
- classes become class nodes
- top-level functions become callable nodes
- methods become method nodes
- async functions are classified correctly
- qualified names are deterministic
- `contains`, `imports`, and `inherits` edges are stored
- broken files fail cleanly without breaking the whole run

### Phase mandatory tests to validate

- module extraction test
- class extraction test
- top-level function extraction test
- method extraction test
- async callable extraction test
- qualified-name correctness test
- `contains` edge test
- `imports` edge test
- `inherits` edge test
- doc summary extraction test
- range extraction test
- parse failure handling test

### Phase traps to avoid

- trying to make AST semantic
- inconsistent naming rules
- pretending unresolved imports are resolved
- supporting nested functions halfway
- skipping range normalization

---

## 04-graph-storage

### Phase goal and added functionalities

Goal:
- make the graph durable, queryable, replaceable, and clean in SQLite

Added functionalities:
- node upsert
- edge upsert
- node lookup by ID
- node lookup by qualified name
- list nodes by file
- list nodes by repo
- outgoing edge queries
- incoming edge queries
- child lookup
- file-level graph replacement
- file-level cleanup
- graph stats query
- CLI graph inspection commands
- SQLite indexes for graph queries

### Phase verifiable expected results

You should be able to verify that:

- nodes and edges persist without duplication
- repeated indexing updates the same graph records
- stale file-owned graph data can be replaced cleanly
- graph queries return expected results
- stats can be computed quickly
- unresolved placeholder targets do not break graph retrieval

### Phase mandatory tests to validate

- node upsert test
- edge upsert test
- get node by ID test
- get node by qualified name test
- list child nodes test
- outgoing edge query test
- incoming edge query test
- replace file graph test
- graph stats test
- placeholder target tolerance test

### Phase traps to avoid

- forgetting cleanup on reindex
- hiding unresolved targets
- scattering SQL everywhere
- skipping indexes
- overbuilding abstractions for simple storage

---

## 05-context-builder

### Phase goal and added functionalities

Goal:
- assemble a symbol-centered view from stored graph data

Added functionalities:
- symbol lookup by ID
- symbol lookup by qualified name
- parent resolution
- child resolution
- incoming edge loading
- outgoing edge loading
- structural summary
- freshness summary
- confidence summary
- placeholder reference summary
- CLI context inspection

### Phase verifiable expected results

You should be able to verify that:

- one symbol can be resolved into a complete local context object
- module, class, and callable contexts have correct shapes
- parent and child relationships are returned correctly
- incoming and outgoing edges are attached
- structural summary exists
- freshness exists
- confidence exists
- reference summary placeholder exists even before LSP enrichment

### Phase mandatory tests to validate

- build module context test
- build class context test
- build method context test
- lookup by qualified name test
- freshness summary test
- confidence summary test
- unknown symbol handling test

### Phase traps to avoid

- returning raw rows instead of a context object
- expanding too deep into the graph
- mixing context assembly with risk evaluation
- hiding missing data
- forgetting freshness and confidence

---

## 06-lsp-reference-enrichment

### Phase goal and added functionalities

Goal:
- enrich the graph with LSP-based `references` information only

Added functionalities:
- minimal LSP client
- declaration position resolution
- reference lookup by symbol
- mapping LSP locations back to graph symbols
- smallest-containing-symbol mapping
- module fallback for unmapped usages
- `references` edge persistence
- reverse `referenced_by` queries
- reference summary stats
- context enrichment with real reference summary
- reference refresh commands

### Phase verifiable expected results

You should be able to verify that:

- a symbol’s best query position can be selected
- the LSP can return references for that symbol
- returned locations can be mapped to graph nodes
- `references` edges are stored
- reverse caller lookup works
- reference count, file count, and module count can be computed
- context can expose real reference summaries when available

### Phase mandatory tests to validate

- selection-range preference test
- smallest-containing-symbol mapping test
- module fallback mapping test
- reference edge creation test
- replace references for target test
- reference stats test
- context reference summary enrichment test
- unavailable-vs-zero reference distinction test

### Phase traps to avoid

- trying to support full LSP
- storing raw LSP locations as final truth
- duplicating `references` and `referenced_by` as separate truths
- pretending mapping confidence is always perfect
- returning zero when references were never refreshed

---

## 07-risk-engine

### Phase goal and added functionalities

Goal:
- build the reusable deterministic engine that turns graph facts into risk facts, issues, score, and decision

Added functionalities:
- normalized risk targets
- risk fact extraction
- reference-based impact analysis
- public-surface heuristics
- target-set spread analysis
- inheritance risk detection
- freshness risk detection
- confidence risk detection
- deterministic issue codes
- deterministic scoring
- deterministic decision output
- single-symbol and target-set risk analysis
- CLI risk inspection

### Phase verifiable expected results

You should be able to verify that:

- one symbol can be analyzed for risk
- multiple targets can be analyzed together
- risk facts are extracted consistently
- issue codes are deterministic
- score is deterministic
- decision is deterministic
- high-reference public symbols show higher risk
- local private helpers show lower risk

### Phase mandatory tests to validate

- low-risk private helper test
- public heavily referenced method test
- inheritance risk test
- multi-file target set test
- multi-module target set test
- stale symbol issue test
- low-confidence issue test
- score clamp test
- high-score decision test

### Phase traps to avoid

- putting plan-resolution logic inside the engine
- returning prose instead of structure
- treating unavailable references as zero
- scattering risk logic across the codebase
- overcomplicating scoring too early

---

## 08-mcp-server

### Phase goal and added functionalities

Goal:
- expose repository intelligence and risk capabilities as deterministic MCP tools

Added functionalities:
- MCP server startup
- tool registration
- input and output schemas
- structured error handling
- symbol resolution tool
- symbol context tool
- reference refresh tool
- reference lookup tool
- single-symbol risk tool
- target-set risk tool
- adapters from internal models to tool payloads
- server launch command

### Phase verifiable expected results

You should be able to verify that:

- the MCP server starts
- tools are registered and callable
- tool inputs are validated
- tool outputs are stable and structured
- errors are structured and machine-friendly
- the server exposes deterministic facts rather than natural-language analysis

### Phase mandatory tests to validate

- resolve symbol success test
- resolve symbol not found test
- get symbol context tool test
- refresh references tool test with fake LSP client
- get symbol references tool test
- analyze symbol risk tool test
- analyze target set risk tool test
- invalid input error-shape test
- internal error-shape test

### Phase traps to avoid

- making the server conversational or “smart”
- leaking raw DB rows directly through tools
- mixing refresh and read behavior invisibly
- weak error contracts
- giant generic all-in-one tools

---

## 09-watch-mode

### Phase goal and added functionalities

Goal:
- keep the graph fresh by reacting incrementally to filesystem changes

Added functionalities:
- filesystem watching
- raw event normalization
- debounce and batching
- create event handling
- modify event handling
- delete event handling
- incremental rescanning
- incremental AST refresh
- file-level graph replacement
- deletion cleanup
- reference invalidation
- parse-failure-safe behavior
- watch CLI command

### Phase verifiable expected results

You should be able to verify that:

- file creation adds new graph state
- file modification updates graph state
- file deletion removes graph state
- noisy save events collapse into one operation
- changed-file reference edges are invalidated
- temporary syntax errors do not destroy previous valid graph state
- the watch process can run continuously

### Phase mandatory tests to validate

- modify event reindex test
- create event add-file test
- delete event remove-file test
- ignored file event skip test
- event deduplication test
- changed-file reference invalidation test
- parse-failure preserves previous graph test
- rename-as-delete-plus-create test if supported

### Phase traps to avoid

- full repo reindex on every save
- trusting raw watcher events directly
- deleting valid graph state on temporary syntax errors
- forgetting reference invalidation
- overlapping concurrent SQLite writes
- overengineering a distributed local watcher system

---

## 10-real-workflow

### Phase goal and added functionalities

Goal:
- define and enforce the actual guarded human-in-the-loop workflow the whole system exists for

Added functionalities:
- separation between planning and implementation
- required symbol resolution before symbol-targeted changes
- required context inspection before implementation
- required risk checking for non-trivial changes
- plan revision based on deterministic findings
- explicit approval gate
- workflow states
- agent behavior rules
- optional workflow simulation support
- scenario-based workflow validation

### Phase verifiable expected results

You should be able to verify that:

- the agent drafts a plan before implementation
- MCP tools are used before non-trivial coding begins
- symbol-targeted requests require symbol resolution
- risk findings can revise the plan
- the workflow pauses at approval
- implementation cannot begin without approval
- unresolved or ambiguous targets block progress
- the workflow behaves consistently across scenarios

### Phase mandatory tests to validate

- symbol-targeted change requires resolution test
- non-trivial change requires risk check test
- workflow stops at awaiting-approval test
- unresolved or ambiguous target blocks implementation test
- approved workflow transitions to implementation test
- high-risk result does not auto-implement test
- plan revision uses risk findings test

### Phase traps to avoid

- treating approval as optional
- letting the agent code while “still planning”
- using MCP too late in the process
- hiding uncertainty from the human
- dumping raw tool output without revising the plan
- moving workflow intelligence into the MCP server

---

## Build order logic

The whole sequence should stay:

1. bootstrap
2. repo scanner
3. AST extraction
4. graph storage
5. context builder
6. LSP reference enrichment
7. risk engine
8. MCP server
9. watch mode
10. real workflow

If you skip that order, you usually create rework.

The blunt truth:
- phases 1 to 4 build truth
- phases 5 to 7 build reasoning inputs
- phase 8 exposes tools
- phase 9 keeps state fresh
- phase 10 turns it into the actual product workflow
