# 05 Context Builder - Exact Implementation Checklist

## Objective

Implement phase 5 of the repository indexing pipeline.

Phase 5 must read the stored graph from phase 4 and assemble a deterministic, symbol-centered context object that later CLI commands, internal tooling, and MCP tools can consume without manually stitching together raw nodes and edges. Deterministic, structured code context is valuable specifically because it is stable and machine-readable rather than heuristic or freeform. [news.ycombinator](https://news.ycombinator.com/item?id=46715705)

Phase 5 must provide:
- symbol lookup by ID
- symbol lookup by qualified name
- parent resolution
- child resolution
- incoming edge resolution
- outgoing edge resolution
- `SymbolContext` assembly
- structural summaries
- freshness summaries
- confidence summaries
- CLI context inspection

Phase 5 must not provide:
- LSP reference fetching
- risk scoring
- MCP tool server implementation
- watch mode
- recursive graph expansion
- semantic explanation generation
- autonomous agent behavior

***

## Consistency Rules

These rules are mandatory.

- [ ] Reuse the existing phase 1, phase 2, phase 3, and phase 4 models, query helpers, naming rules, and serialization style.
- [ ] Reuse the existing `SymbolContext` model if phase 1 already defined it, and only expand it to the required shape instead of replacing it with a new incompatible contract.
- [ ] Do not rename existing node or edge fields.
- [ ] Do not move storage logic into the context builder.
- [ ] Do not move context assembly logic into CLI handlers.
- [ ] Keep context assembly deterministic.
- [ ] Keep the context scope shallow and local.
- [ ] Keep missing data explicit instead of inventing meaning.
- [ ] Keep the output JSON-friendly and stable.

***

## Required Inputs

Phase 5 must consume these existing inputs:

- [ ] stored nodes from phase 4
- [ ] stored edges from phase 4
- [ ] repo metadata already stored in the system
- [ ] file metadata already stored in the system
- [ ] graph query helpers from phase 4

Do not add new required infrastructure for this phase.

***

## Required Outputs

Phase 5 must produce these capabilities:

- [ ] build symbol context by node ID
- [ ] build symbol context by qualified name
- [ ] return a `SymbolContext` object with a stable field shape
- [ ] include the focus symbol
- [ ] include the immediate parent if it exists
- [ ] include immediate children
- [ ] include immediate incoming edges
- [ ] include immediate outgoing edges
- [ ] include a reference summary placeholder
- [ ] include a structural summary
- [ ] include a freshness summary
- [ ] include a confidence summary
- [ ] expose context inspection from CLI

Do not add recursive subgraph expansion in this phase.

***

## Required File Layout

Create or extend these files:

- [ ] `src/repo_context/graph/context.py`
- [ ] `src/repo_context/graph/summaries.py`
- [ ] `src/repo_context/graph/freshness.py`
- [ ] `src/repo_context/graph/confidence.py`

Reuse existing files if they already exist.

Do not add extra context-related packages unless strictly necessary.

***

## Required `SymbolContext` Contract

Use one stable context shape.

If phase 1 already defined `SymbolContext`, expand it to this exact structure without changing field meaning:

- [ ] `focus_symbol`
- [ ] `parent`
- [ ] `children`
- [ ] `outgoing_edges`
- [ ] `incoming_edges`
- [ ] `reference_summary`
- [ ] `structural_summary`
- [ ] `freshness`
- [ ] `confidence`

### Exact field rules

#### `focus_symbol`
- [ ] must contain the resolved focus node
- [ ] must never be `None` in a successful context build

#### `parent`
- [ ] must contain the immediate parent node if `parent_id` exists
- [ ] must be `None` if no parent exists

#### `children`
- [ ] must contain only immediate child nodes
- [ ] must default to an empty list if there are no children

#### `outgoing_edges`
- [ ] must contain only immediate edges whose `from_id` is the focus symbol ID
- [ ] must default to an empty list if none exist

#### `incoming_edges`
- [ ] must contain only immediate edges whose `to_id` is the focus symbol ID
- [ ] must default to an empty list if none exist

#### `reference_summary`
- [ ] must exist even though LSP references do not exist yet
- [ ] must use a placeholder shape in phase 5

#### `structural_summary`
- [ ] must contain small aggregated structural facts
- [ ] must not contain freeform English analysis

#### `freshness`
- [ ] must contain timestamp-based freshness metadata
- [ ] must not claim freshness certainty that the stored data cannot support

#### `confidence`
- [ ] must contain confidence rollups derived from stored confidence values
- [ ] must not invent confidence values

***

## Scope Rules

Apply these scope rules exactly.

### Include

- [ ] focus symbol
- [ ] immediate parent
- [ ] immediate children
- [ ] immediate incoming edges
- [ ] immediate outgoing edges
- [ ] small deterministic summaries

### Exclude

- [ ] recursive parent traversal
- [ ] recursive child traversal
- [ ] transitive dependency expansion
- [ ] giant import trees
- [ ] reverse dependency trees beyond immediate edges
- [ ] freeform reasoning text

Do not exceed immediate local graph context in version 1.

***

## Entry Points

Implement exactly these entry points.

### Build by ID

- [ ] `build_symbol_context_by_id(conn, node_id)`

### Build by qualified name

- [ ] `build_symbol_context_by_qualified_name(conn, repo_id, qualified_name, kind=None)`

### Exact behavior

#### `build_symbol_context_by_id`
- [ ] resolve the focus symbol by node ID
- [ ] raise a clear error if the symbol does not exist
- [ ] assemble the full `SymbolContext`

#### `build_symbol_context_by_qualified_name`
- [ ] resolve the focus symbol by repo ID and qualified name
- [ ] apply optional kind filter if provided
- [ ] raise a clear error if the symbol does not exist
- [ ] delegate to `build_symbol_context_by_id` using the resolved node ID

Do not add other entry points in this phase.

***

## Error Handling Rules

Apply these rules exactly.

- [ ] if a symbol is not found, raise a clear domain-level error or `ValueError`
- [ ] do not return an empty fake context for a missing symbol
- [ ] do not silently swallow lookup failures

If the project already has a shared errors module, use a small custom not-found error.
If not, use `ValueError` consistently.

***

## Parent Resolution Rules

Parent lookup must follow these rules exactly.

- [ ] use `parent_id` from the focus node as the primary parent lookup source
- [ ] if `parent_id` is `None` or missing, return `None`
- [ ] if `parent_id` exists, fetch that node directly
- [ ] do not infer parent through `contains` edges if `parent_id` is missing

This phase must treat `parent_id` as the parent lookup source of truth.

***

## Child Resolution Rules

Child lookup must follow these rules exactly.

- [ ] use `parent_id` on stored nodes as the primary child lookup mechanism
- [ ] return only immediate children where `parent_id = focus_symbol.id`
- [ ] order results deterministically
- [ ] do not recursively fetch grandchildren

This phase may still expose `contains` edges in edge views, but child lookup itself must use `parent_id`.

***

## Edge Resolution Rules

Immediate edge lookup must follow these rules exactly.

- [ ] outgoing edges must be all edges where `from_id = focus_symbol.id`
- [ ] incoming edges must be all edges where `to_id = focus_symbol.id`
- [ ] results must be ordered deterministically
- [ ] optional kind filters may be supported only through existing phase 4 query helpers

Do not expand edge traversal beyond one hop.

***

## Step 1 - Verify or Expand `SymbolContext`

### Files to modify

- [ ] the existing `SymbolContext` model from phase 1, if present

### Implement

Ensure the `SymbolContext` model supports these exact fields:

- [ ] `focus_symbol`
- [ ] `parent`
- [ ] `children`
- [ ] `outgoing_edges`
- [ ] `incoming_edges`
- [ ] `reference_summary`
- [ ] `structural_summary`
- [ ] `freshness`
- [ ] `confidence`

### Required behavior

- [ ] use empty list defaults for child and edge lists
- [ ] use empty dict defaults for summary fields
- [ ] keep the model JSON-friendly
- [ ] preserve backwards compatibility with earlier phases if the model already exists

### Do not do

- [ ] do not create a second competing context model
- [ ] do not add speculative fields not used by phase 5

### Done when

- [ ] one stable `SymbolContext` contract exists and matches phase 5 requirements

***

## Step 2 - Context Builder Orchestration

### File

- [ ] `src/repo_context/graph/context.py`

### Implement

- [ ] `build_symbol_context_by_id(conn, node_id)`
- [ ] `build_symbol_context_by_qualified_name(conn, repo_id, qualified_name, kind=None)`

### Exact build order

For `build_symbol_context_by_id`:

- [ ] resolve focus symbol
- [ ] resolve parent symbol
- [ ] resolve child symbols
- [ ] resolve outgoing edges
- [ ] resolve incoming edges
- [ ] build structural summary
- [ ] build freshness summary
- [ ] build confidence summary
- [ ] create reference summary placeholder
- [ ] assemble and return `SymbolContext`

### Do not do

- [ ] do not perform recursive traversal
- [ ] do not perform semantic interpretation
- [ ] do not call LSP

### Done when

- [ ] one function can build a complete local symbol context deterministically

***

## Step 3 - Structural Summary Helper

### File

- [ ] `src/repo_context/graph/summaries.py`

### Implement

- [ ] `build_structural_summary(focus_symbol, parent, children, incoming_edges, outgoing_edges)`

### Required output fields

- [ ] `kind`
- [ ] `name`
- [ ] `qualified_name`
- [ ] `has_parent`
- [ ] `child_count`
- [ ] `incoming_edge_count`
- [ ] `outgoing_edge_count`
- [ ] `child_kind_counts`
- [ ] `module_path` when derivable

### Exact field rules

#### `kind`
- [ ] copy from focus symbol kind

#### `name`
- [ ] copy from focus symbol name

#### `qualified_name`
- [ ] copy from focus symbol qualified name

#### `has_parent`
- [ ] `True` if parent is not `None`
- [ ] `False` otherwise

#### `child_count`
- [ ] equal to length of `children`

#### `incoming_edge_count`
- [ ] equal to length of `incoming_edges`

#### `outgoing_edge_count`
- [ ] equal to length of `outgoing_edges`

#### `child_kind_counts`
- [ ] aggregate counts by child `kind`
- [ ] return empty dict if there are no children

#### `module_path`
- [ ] if focus symbol kind is `module`, use its own qualified name
- [ ] if focus symbol kind is `class`, derive from its parent module if available, otherwise derive from qualified name conservatively
- [ ] if focus symbol kind is callable, derive from module parent if callable parent is module, or from class parent’s module if callable parent is class
- [ ] if it cannot be derived safely, set to `None`

### Do not do

- [ ] do not add prose summaries
- [ ] do not compute recursive metrics

### Done when

- [ ] one small summary object gives a quick structural view of the focus symbol

***

## Step 4 - Freshness Summary Helper

### File

- [ ] `src/repo_context/graph/freshness.py`

### Implement

- [ ] `build_freshness_summary(symbol, children, incoming_edges, outgoing_edges)`

### Required output fields

- [ ] `focus_last_indexed_at`
- [ ] `oldest_related_last_indexed_at`
- [ ] `missing_timestamp_count`
- [ ] `is_stale`
- [ ] `reason`

### Exact logic

- [ ] collect `last_indexed_at` from the focus symbol
- [ ] collect `last_indexed_at` from all children
- [ ] collect `last_indexed_at` from all incoming edges
- [ ] collect `last_indexed_at` from all outgoing edges
- [ ] count how many of those timestamps are missing
- [ ] if any timestamp is missing, set `is_stale = True`
- [ ] if no timestamps are missing, set `is_stale = False`
- [ ] if timestamps exist, compute the oldest related timestamp
- [ ] if no related timestamps exist beyond the focus symbol, use the focus timestamp as the oldest related timestamp
- [ ] if `is_stale = True`, set a simple explicit reason
- [ ] if `is_stale = False`, set `reason = None`

### Do not do

- [ ] do not implement age thresholds yet
- [ ] do not invent advanced freshness scoring

### Done when

- [ ] freshness is honest, deterministic, and based only on stored timestamps

***

## Step 5 - Confidence Summary Helper

### File

- [ ] `src/repo_context/graph/confidence.py`

### Implement

- [ ] `build_confidence_summary(symbol, children, incoming_edges, outgoing_edges)`

### Required output fields

- [ ] `focus_symbol_confidence`
- [ ] `min_child_confidence`
- [ ] `min_edge_confidence`
- [ ] `overall_confidence`

### Exact logic

- [ ] read confidence from the focus symbol
- [ ] collect confidence from all children
- [ ] collect confidence from all incoming edges
- [ ] collect confidence from all outgoing edges
- [ ] `focus_symbol_confidence` must equal focus symbol confidence
- [ ] `min_child_confidence` must equal the minimum child confidence if children exist, otherwise equal focus symbol confidence
- [ ] `min_edge_confidence` must equal the minimum edge confidence across incoming and outgoing edges if edges exist, otherwise equal focus symbol confidence
- [ ] `overall_confidence` must equal the minimum of:
  - focus symbol confidence
  - all child confidences, if any
  - all edge confidences, if any

### Do not do

- [ ] do not invent weighted formulas in this phase
- [ ] do not ignore low-confidence edges

### Done when

- [ ] confidence is summarized deterministically from existing stored values only

***

## Step 6 - Reference Summary Placeholder

### File

- [ ] `src/repo_context/graph/context.py` or a tiny helper module if preferred

### Implement

Always include a placeholder `reference_summary` in every built context.

### Required placeholder fields

- [ ] `reference_count`
- [ ] `referencing_file_count`
- [ ] `available`

### Exact placeholder values for phase 5

- [ ] `reference_count = 0`
- [ ] `referencing_file_count = 0`
- [ ] `available = False`

### Do not do

- [ ] do not infer references from imports
- [ ] do not fake reference counts

### Done when

- [ ] every `SymbolContext` contains a stable reference summary field even before LSP exists

***

## Step 7 - Lookup Reuse

### Files to verify

- [ ] `src/repo_context/graph/context.py`
- [ ] phase 4 graph query helpers

### Implement

Use phase 4 helpers for all low-level reads.

### Exact reuse rules

- [ ] use existing node lookup by ID
- [ ] use existing node lookup by qualified name
- [ ] use existing parent lookup helper if available
- [ ] use existing child lookup helper if available
- [ ] use existing outgoing edge lookup helper
- [ ] use existing incoming edge lookup helper

### Do not do

- [ ] do not duplicate raw SQL in the context builder if phase 4 already provides the query helper
- [ ] do not bypass the graph query layer unnecessarily

### Done when

- [ ] context assembly is orchestration on top of phase 4, not a duplicate storage layer

***

## Step 8 - Context Assembly by Symbol Kind

### File

- [ ] `src/repo_context/graph/context.py`

### Implement

Use one generic context builder, but verify behavior for each expected symbol kind.

### Exact expected behavior for module symbols

- [ ] `parent` must be `None`
- [ ] `children` may include classes and top-level callables
- [ ] `outgoing_edges` may include `contains` and `imports`
- [ ] `incoming_edges` may be empty or small in AST-only mode

### Exact expected behavior for class symbols

- [ ] `parent` must be the module
- [ ] `children` may include direct methods
- [ ] `outgoing_edges` may include `contains` and `inherits`
- [ ] `incoming_edges` should include a `contains` edge from the module when stored

### Exact expected behavior for callable symbols

- [ ] `parent` must be either module or class
- [ ] `children` must be empty in v1
- [ ] `incoming_edges` should include a `contains` edge from the parent when stored
- [ ] `outgoing_edges` may be empty in AST-only mode

### Do not do

- [ ] do not create separate incompatible context contracts for different symbol kinds

### Done when

- [ ] the generic builder returns structurally correct local context for modules, classes, and callables

***

## Step 9 - Optional Filter Helpers

### File

- [ ] `src/repo_context/graph/filters.py`

### Implement

Add only tiny reusable filters if needed.

Allowed helpers:
- [ ] `filter_edges_by_kind(edges, kind)`
- [ ] `filter_children_by_kind(children, kind)`

### Exact behavior

- [ ] preserve input order
- [ ] return only elements whose `kind` matches the filter
- [ ] return empty list if nothing matches

### Do not do

- [ ] do not build a custom query language
- [ ] do not move core context assembly here

### Done when

- [ ] small repeated filtering logic is not duplicated

***

## Step 10 - CLI Context Inspection

### Files to modify

- [ ] existing CLI module from earlier phases

### Implement

Add these commands.

### Command 1
- [ ] `repo-context show-context <node-id>`

### Required behavior
- [ ] resolve the symbol context by node ID
- [ ] print the full structured context in a readable format
- [ ] include focus symbol
- [ ] include parent
- [ ] include child identities
- [ ] include incoming and outgoing edge counts
- [ ] include freshness summary
- [ ] include confidence summary

### Command 2
- [ ] `repo-context show-context-by-name <repo-id> <qualified-name>`

### Required behavior
- [ ] resolve the symbol context by repo ID and qualified name
- [ ] support optional kind filter only if your CLI style already supports optional arguments cleanly
- [ ] print the full structured context in a readable format

### Output rule

- [ ] JSON output is acceptable
- [ ] plain readable structured text is acceptable
- [ ] output must be deterministic

### Do not do

- [ ] do not add MCP-like transport behavior
- [ ] do not hide core context fields from the output

### Done when

- [ ] one symbol context can be inspected manually from CLI without direct SQL

***

## Step 11 - Missing Data Behavior

### Files to verify

- [ ] `src/repo_context/graph/context.py`
- [ ] helper modules

### Implement

Apply these exact missing-data rules.

- [ ] if parent does not exist, use `None`
- [ ] if children do not exist, use empty list
- [ ] if incoming edges do not exist, use empty list
- [ ] if outgoing edges do not exist, use empty list
- [ ] if `module_path` cannot be derived safely, use `None`
- [ ] if freshness cannot prove completeness, mark stale honestly
- [ ] if confidence values are missing unexpectedly, fail clearly or handle consistently according to existing project conventions

### Do not do

- [ ] do not fabricate parent nodes
- [ ] do not fabricate missing edges
- [ ] do not hide stale status

### Done when

- [ ] incomplete graph state is represented honestly instead of being papered over

***

## Step 12 - Tests

### Files to create or modify

- [ ] phase 5 tests under `tests/`

### Implement these tests

- [ ] `test_build_context_for_module`
- [ ] `test_build_context_for_class`
- [ ] `test_build_context_for_method`
- [ ] `test_lookup_by_qualified_name`
- [ ] `test_freshness_summary`
- [ ] `test_confidence_summary`
- [ ] `test_unknown_symbol_raises`
- [ ] CLI context inspection tests if CLI tests already exist in project style

### Exact test assertions

#### `test_build_context_for_module`
- [ ] focus symbol is the module
- [ ] parent is `None`
- [ ] children include expected top-level symbols
- [ ] structural summary fields are correct

#### `test_build_context_for_class`
- [ ] focus symbol is the class
- [ ] parent is the module
- [ ] children include expected methods
- [ ] outgoing edges include expected structural edges
- [ ] structural summary fields are correct

#### `test_build_context_for_method`
- [ ] focus symbol is the method
- [ ] parent is the class
- [ ] children is empty
- [ ] incoming `contains` edge exists if stored
- [ ] structural summary fields are correct

#### `test_lookup_by_qualified_name`
- [ ] symbol resolves correctly by repo ID and qualified name
- [ ] resulting context focus symbol matches expected node

#### `test_freshness_summary`
- [ ] missing timestamps produce `is_stale = True`
- [ ] complete timestamps produce `is_stale = False`
- [ ] missing timestamp count is correct

#### `test_confidence_summary`
- [ ] low-confidence edge lowers `overall_confidence`
- [ ] focus symbol confidence is preserved
- [ ] minimum child confidence is correct
- [ ] minimum edge confidence is correct

#### `test_unknown_symbol_raises`
- [ ] unknown node ID raises clear failure
- [ ] unknown qualified name raises clear failure

### Do not do

- [ ] do not rely only on smoke tests
- [ ] do not leave freshness and confidence untested

### Done when

- [ ] context assembly behavior is covered by focused deterministic tests

***

## Step 13 - End-to-End Fixture Validation

### Files to use

- [ ] reuse phase 3 and phase 4 fixture repos

### Implement

For at least one fixture repo:

- [ ] scan files using phase 2
- [ ] extract nodes and edges using phase 3
- [ ] persist graph using phase 4
- [ ] build symbol context using phase 5
- [ ] assert exact expected context fields

### Do not do

- [ ] do not involve LSP
- [ ] do not involve MCP

### Done when

- [ ] phases 2 through 5 work together on at least one real fixture path

***

## Step 14 - Final Verification

Before marking phase 5 complete, verify all of the following:

- [ ] a symbol can be loaded by ID
- [ ] a symbol can be loaded by qualified name
- [ ] parent lookup works
- [ ] child lookup works
- [ ] incoming edge lookup works
- [ ] outgoing edge lookup works
- [ ] `SymbolContext` objects assemble correctly
- [ ] structural summary is included
- [ ] freshness summary is included
- [ ] confidence summary is included
- [ ] reference summary placeholder is included
- [ ] CLI context inspection works
- [ ] tests pass
- [ ] no LSP integration exists
- [ ] no risk engine exists
- [ ] no MCP server exists

Do not mark phase 5 done until every box above is true.

***

## Required Execution Order

Implement in this order and do not skip ahead:

- [ ] Step 1 verify or expand `SymbolContext`
- [ ] Step 2 context builder orchestration
- [ ] Step 3 structural summary helper
- [ ] Step 4 freshness summary helper
- [ ] Step 5 confidence summary helper
- [ ] Step 6 reference summary placeholder
- [ ] Step 7 lookup reuse
- [ ] Step 8 context assembly by symbol kind
- [ ] Step 9 optional filter helpers
- [ ] Step 10 CLI context inspection
- [ ] Step 11 missing data behavior
- [ ] Step 12 tests
- [ ] Step 13 end-to-end fixture validation
- [ ] Step 14 final verification

***

## Phase 5 Done Definition

Phase 5 is complete only when all of these are true:

- [ ] phase 1 through phase 4 contracts remain intact
- [ ] symbol context can be built deterministically from stored graph data
- [ ] context remains shallow and local
- [ ] summaries are included and correct
- [ ] freshness is explicit
- [ ] confidence is explicit
- [ ] reference summary placeholder exists
- [ ] CLI inspection works
- [ ] tests pass
- [ ] no out-of-scope features were added
