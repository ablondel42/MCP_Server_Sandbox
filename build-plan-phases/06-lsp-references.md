# 06 LSP Reference Enrichment - Exact Implementation Checklist


## Objective


Implement phase 6 of the repository indexing pipeline.


Phase 6 must add one and only one LSP-based semantic enrichment to the stored graph:


- `references`


Phase 6 must use a Python language server to find usage locations for a chosen target symbol, map those usage locations back to internal graph symbols, and persist `references` edges between stable node IDs. The Language Server Protocol defines `textDocument/references` and its `ReferenceContext.includeDeclaration` flag, which is the exact feature surface needed here. [web:531]


Phase 6 must provide:
- minimal LSP client support for references
- declaration position resolution for one target symbol
- reference location retrieval from LSP
- mapping from returned locations back to internal graph symbols
- persisted `references` edges
- reverse `referenced_by` queries derived from stored `references` edges
- reference summary stats
- CLI commands for refresh and inspection
- tests for mapping, replacement, and stats
- compatibility with nested-scope symbols introduced in phase 03b


Phase 6 must not provide:
- hover
- rename
- diagnostics
- completion
- code actions
- semantic tokens
- workspace symbols
- risk scoring
- MCP tools
- watch mode


***


## Consistency Rules


These rules are mandatory.


- [ ] Reuse the existing phase 1 through phase 5 models, graph storage, graph query helpers, naming rules, nested-scope rules, and context builder contracts.
- [ ] Do not invent a second semantic graph separate from the existing nodes and edges tables.
- [ ] Reuse the existing `Edge` storage model and persist `references` as normal graph edges.
- [ ] Store only `references` edges as truth.
- [ ] Derive `referenced_by` by reverse lookup from stored `references` edges.
- [ ] Do not store both `references` and `referenced_by` as separate persisted truths.
- [ ] Keep the LSP layer narrow and disciplined.
- [ ] Keep mapping confidence explicit.
- [ ] Keep refresh behavior deterministic.
- [ ] Keep unavailable references distinct from zero references.
- [ ] Respect structural vs lexical parent distinctions introduced by phase 03b.
- [ ] Do not silently flatten nested-scope usage mapping to module scope when a narrower containing symbol exists.


***


## Required Inputs


Phase 6 must consume these existing inputs:


- [ ] stored nodes from phase 4
- [ ] stored edges from phase 4
- [ ] symbol `range_json`
- [ ] symbol `selection_range_json`
- [ ] symbol `uri`
- [ ] symbol `scope`
- [ ] symbol `lexical_parent_id`
- [ ] repository root
- [ ] a working Python language server process
- [ ] the phase 5 context builder


Do not add new mandatory protocol features beyond what this phase needs.


***


## Required Outputs


Phase 6 must produce these capabilities:


- [ ] resolve the best declaration query position for a symbol
- [ ] call the language server for references of that symbol
- [ ] receive reference locations
- [ ] map each usage location to the smallest containing internal symbol when possible
- [ ] support nested-scope symbols during mapping
- [ ] fall back to the module node when no smaller containing symbol exists
- [ ] build `references` edges
- [ ] persist `references` edges
- [ ] replace stale reference edges for one target symbol
- [ ] list reference edges for one target symbol
- [ ] derive `referenced_by` from stored reverse lookup
- [ ] compute reference stats
- [ ] enrich phase 5 `SymbolContext.reference_summary`
- [ ] expose CLI refresh and inspection commands


Do not add any other LSP-powered graph enrichment in this phase.


***


## Required File Layout


Create or extend these files:


- [ ] `src/repo_context/lsp/__init__.py`
- [ ] `src/repo_context/lsp/client.py`
- [ ] `src/repo_context/lsp/protocol.py`
- [ ] `src/repo_context/lsp/references.py`
- [ ] `src/repo_context/lsp/mapper.py`
- [ ] `src/repo_context/lsp/resolver.py`
- [ ] `src/repo_context/graph/references.py`


Reuse existing files if they already exist.


Do not create a generic full-IDE abstraction layer.


***


## LSP Scope Rules


Apply these scope rules exactly.


### Allowed LSP concepts


- [ ] `TextDocumentIdentifier`
- [ ] `Position`
- [ ] `Range`
- [ ] `Location`
- [ ] `ReferenceParams`
- [ ] `textDocument/references`


### Forbidden LSP concepts in phase 6


- [ ] hover
- [ ] rename
- [ ] diagnostics
- [ ] completion
- [ ] code actions
- [ ] semantic tokens
- [ ] workspace symbol search
- [ ] any protocol feature not required for `references`


Do not expand protocol scope.


***


## Edge Truth Rules


Apply these rules exactly.


- [ ] every semantic usage found in this phase must be stored as one `references` edge
- [ ] `kind` must be `references`
- [ ] `from_id` must be the internal symbol that contains the usage site
- [ ] `to_id` must be the target symbol being referenced
- [ ] `source` must be `lsp`
- [ ] `referenced_by` must never be stored as a separate edge kind
- [ ] reverse lookup must be derived from `references`


***


## Query Position Rules


Apply these rules exactly for LSP requests.


- [ ] prefer `selection_range_json.start` as the LSP query position
- [ ] if `selection_range_json` is missing, use `range_json.start`
- [ ] if both are missing, fail clearly
- [ ] do not guess positions from symbol names or text search


The LSP `references` request should use `includeDeclaration = false`, because the protocol supports that flag and it avoids treating the declaration site as a usage site when the server respects it. Some Python LSP implementations had bugs around this flag, so the behavior must be tested rather than assumed blindly. [web:531][web:533][web:706]


***


## Mapping Rules


Apply these rules exactly for mapping LSP locations to internal graph symbols.


- [ ] resolve the file by exact URI match
- [ ] load all nodes for that file
- [ ] identify which node ranges contain the usage location
- [ ] choose the smallest containing node
- [ ] prefer local and nested declarations when they are the true smallest containing node
- [ ] if no node contains the usage, fall back to the module node for that file
- [ ] if no module node exists, skip the location
- [ ] assign confidence based on mapping quality
- [ ] do not fabricate resolved symbols when mapping fails


The smallest-containing-range strategy is consistent with range-containment lookup patterns used in LSIF, where innermost covering ranges are preferred over broader ones. [web:704][web:532]


***


## Nested Scope Mapping Rules


Apply these rules exactly.


- [ ] nested functions and local classes introduced in phase 03b are valid `from_id` mapping targets
- [ ] a usage inside a nested function must map to that nested function when its stored range is the smallest containing symbol
- [ ] a usage inside a local class method must map to that method when its range is the smallest containing symbol
- [ ] lexical parent relationships are not used as direct mapping keys, but nested symbols must remain eligible through normal range containment
- [ ] do not collapse nested usages to outer functions when the nested declaration is a more precise match
- [ ] do not collapse local function usages to module node unless all narrower containment fails


This phase still maps by stored ranges, not by full scope-aware name binding.
That is good enough for v1.


***


## Confidence Rules


Apply these confidence rules exactly.


- [ ] exact containing symbol match confidence = `0.9`
- [ ] module fallback match confidence = `0.7`
- [ ] weird partial or degraded match confidence = `0.5` only if such a case is implemented explicitly
- [ ] do not assign `1.0` confidence to mapped LSP references in v1
- [ ] do not hide low-confidence mappings


If no degraded partial-match mode is implemented, only use `0.9` and `0.7`.


***


## Duplicate Handling Rules


Apply these rules exactly.


- [ ] deduplicate reference edges by:
  - target symbol ID
  - source symbol ID
  - evidence URI
  - evidence start line
  - evidence start character
- [ ] keep one stored edge per concrete usage site
- [ ] do not store duplicated edges returned by the language server


***


## Self Reference Rules


Apply these rules exactly.


- [ ] keep self references in v1
- [ ] do not filter out self references
- [ ] store them the same way as other reference edges


Do not add self-reference filtering in this phase.


***


## Refresh Rules


Apply these rules exactly.


- [ ] use on-demand refresh per target symbol in v1
- [ ] do not implement full repo-wide reference refresh orchestration in this phase
- [ ] when refreshing one target symbol, replace old `references` edges for that target
- [ ] replacement must be performed by `to_id = target_symbol_id`


Do not add background refresh behavior.


***


## Availability Rules


Apply these rules exactly.


- [ ] “never refreshed” must remain distinct from “refreshed and found zero references”
- [ ] stored edge absence alone is not enough to mean zero references
- [ ] reference availability must be tracked explicitly per target symbol
- [ ] context summaries must use explicit availability truth, not inferred emptiness


This is critical because empty edge rows can mean either “no usages” or “not enriched yet,” and those are not the same thing. [web:531]


***


## Required Reference Refresh Metadata


You need explicit refresh-state tracking for target symbols.


### Recommended storage


Use one of these two approaches:


- [ ] a small `reference_refresh` table keyed by `target_symbol_id`
- [ ] or a deterministic target-scoped metadata record in existing storage if the project already has a clean metadata table


### Minimum required fields


- [ ] `target_symbol_id`
- [ ] `available`
- [ ] `last_refreshed_at`
- [ ] optional `refresh_status`
- [ ] optional `error_code`


### Rule


Do not infer availability only from presence or absence of `references` edges.
Track it explicitly.


***


## Step 1 - Minimal LSP Client


### File


- [ ] `src/repo_context/lsp/client.py`


### Implement


Add a minimal client that can:


- [ ] start or connect to one Python language server
- [ ] send a `textDocument/references` request
- [ ] receive and return reference locations
- [ ] shut down cleanly


### Required public behavior


- [ ] one method to find references for one `(uri, position, include_declaration)` input
- [ ] return a list of LSP locations in a normalized Python structure
- [ ] raise a clear failure on protocol or server errors


### Do not do


- [ ] do not add hover support
- [ ] do not add rename support
- [ ] do not turn this into an editor framework


### Done when


- [ ] the project can ask one Python language server for references of one symbol position


***


## Step 2 - LSP Protocol Helpers


### File


- [ ] `src/repo_context/lsp/protocol.py`


### Implement


Add tiny helpers for request and response shapes.


### Required behavior


- [ ] build a `textDocument/references` request payload
- [ ] normalize returned locations into a consistent internal dict shape
- [ ] preserve `uri` and `range` exactly
- [ ] support `includeDeclaration=False`


### Do not do


- [ ] do not add helpers for unrelated LSP request types


### Done when


- [ ] request and response shaping is not duplicated across the LSP modules


***


## Step 3 - Declaration Query Position Resolver


### File


- [ ] `src/repo_context/lsp/resolver.py`


### Implement


- [ ] `get_reference_query_position(symbol)`


### Exact behavior


- [ ] if `selection_range_json` exists, return its `start`
- [ ] else if `range_json` exists, return its `start`
- [ ] else raise a clear failure
- [ ] return the position in the existing zero-based line and character shape already used by the project


### Do not do


- [ ] do not guess positions by parsing source text
- [ ] do not guess positions from symbol name length


### Done when


- [ ] one deterministic function resolves the LSP query position for any symbol with stored ranges


***


## Step 4 - File Resolution by URI


### File


- [ ] `src/repo_context/lsp/resolver.py` or `src/repo_context/lsp/mapper.py`


### Implement


- [ ] `resolve_file_by_uri(conn, uri)`


### Exact behavior


- [ ] look up a stored file record by exact `uri`
- [ ] return the matching file record
- [ ] return `None` if no stored file matches


### Do not do


- [ ] do not use fuzzy path matching if exact URI match works
- [ ] do not guess file ownership from partial path fragments


### Done when


- [ ] every LSP location can be mapped to a stored file record using strict URI matching when the file is known


***


## Step 5 - Range Containment Helper


### File


- [ ] `src/repo_context/lsp/mapper.py`


### Implement


- [ ] `range_contains(outer, inner)`


### Exact behavior


- [ ] return `True` only when `outer.start <= inner.start` and `outer.end >= inner.end`
- [ ] compare positions by `(line, character)`
- [ ] assume the project’s stored ranges are zero-based
- [ ] work with the exact internal range shape already used in the project


### Do not do


- [ ] do not convert to one-based lines here
- [ ] do not use string comparison for positions


### Done when


- [ ] the project has one deterministic primitive for testing containment of one range inside another


***


## Step 6 - Smallest Containing Symbol Picker


### File


- [ ] `src/repo_context/lsp/mapper.py`


### Implement


- [ ] `pick_smallest_containing_symbol(symbols_in_file, usage_range)`


### Exact behavior


- [ ] consider only symbols with a non-empty `range_json`
- [ ] keep only symbols whose `range_json` contains `usage_range`
- [ ] if none match, return `None`
- [ ] if matches exist, return the smallest containing symbol
- [ ] determine “smallest” by deterministic range-span ordering
- [ ] prefer a narrower symbol over a broader one when both contain the usage
- [ ] use deterministic tie-breaking, such as narrower span first, then deeper lexical nesting if available, then `id`


### Important rule


If both an outer function and a nested local function contain the usage, the nested local function must win if its range is narrower.


### Do not do


- [ ] do not return a list
- [ ] do not use nondeterministic tie-breaking


### Done when


- [ ] a usage inside a method maps to the method instead of the class or module when all relevant ranges exist
- [ ] a usage inside a local function maps to the local function instead of the outer function when both ranges contain it


***


## Step 7 - Module Fallback Helper


### File


- [ ] `src/repo_context/lsp/resolver.py` or `src/repo_context/lsp/mapper.py`


### Implement


- [ ] `find_module_node_for_file(symbols_in_file)`


### Exact behavior


- [ ] return the node whose `kind == "module"`
- [ ] if no module node exists, return `None`


### Do not do


- [ ] do not guess a module node from qualified name string patterns
- [ ] do not fabricate a missing module node


### Done when


- [ ] unmapped usage sites can fall back cleanly to the file’s module node


***


## Step 8 - Reference Edge Builder


### File


- [ ] `src/repo_context/lsp/references.py`


### Implement


Add a helper to build one `references` edge.


### Required edge fields


- [ ] deterministic `id`
- [ ] `repo_id`
- [ ] `kind="references"`
- [ ] `from_id`
- [ ] `to_id`
- [ ] `source="lsp"`
- [ ] `confidence`
- [ ] `evidence_file_id`
- [ ] `evidence_uri`
- [ ] `evidence_range_json`
- [ ] `payload_json`
- [ ] `last_indexed_at`


### Exact edge ID rule


Use:
- [ ] `edge:{repo_id}:references:{from_id}->{to_id}:{line}:{character}`


Where:
- [ ] `line` and `character` come from `evidence_range_json.start`


### Recommended payload fields


- [ ] mapping mode such as `exact_symbol` or `module_fallback`
- [ ] target symbol kind
- [ ] source symbol kind
- [ ] optional source symbol scope


### Do not do


- [ ] do not use random IDs
- [ ] do not omit evidence anchor from the ID


### Done when


- [ ] every concrete usage site can become one stable `references` edge


***


## Step 9 - Replace Reference Edges for Target


### File


- [ ] `src/repo_context/lsp/references.py` or `src/repo_context/graph/references.py`


### Implement


- [ ] `replace_reference_edges_for_target(conn, target_symbol_id, edges, refresh_metadata)`


### Exact behavior


- [ ] start a transaction
- [ ] delete existing edges where `kind = "references"` and `to_id = target_symbol_id`
- [ ] insert the new reference edges
- [ ] update explicit refresh metadata for the target
- [ ] commit on success
- [ ] rollback on failure
- [ ] re-raise the original failure after rollback


### Do not do


- [ ] do not replace all references edges globally
- [ ] do not replace by `from_id`
- [ ] do not leave stale target-specific references behind


### Done when


- [ ] one target symbol’s references can be refreshed cleanly without duplicating or mixing old edges


***


## Step 10 - Reference Enrichment Orchestrator


### File


- [ ] `src/repo_context/lsp/references.py`


### Implement


- [ ] `enrich_references_for_symbol(conn, lsp_client, target_symbol)`


### Exact behavior


Perform these steps in this exact order:


- [ ] resolve query position from target symbol
- [ ] call LSP references with `includeDeclaration=False`
- [ ] normalize returned locations
- [ ] for each location:
  - [ ] resolve file by exact URI
  - [ ] if file cannot be resolved, skip location
  - [ ] load all nodes for that file
  - [ ] map usage range to smallest containing symbol
  - [ ] if no containing symbol exists, fall back to module node
  - [ ] if no module node exists, skip location
  - [ ] assign confidence based on exact match or module fallback
  - [ ] build one `references` edge
- [ ] deduplicate new edges
- [ ] replace existing references for the target symbol
- [ ] return reference stats for the target symbol


### Do not do


- [ ] do not store raw LSP locations as final truth
- [ ] do not create edges to placeholder target IDs here
- [ ] do not keep old target-specific edges after refresh


### Done when


- [ ] one target symbol can be enriched on demand from declaration position to stored reference edges


***


## Step 11 - Graph Reference Queries


### File


- [ ] `src/repo_context/graph/references.py`


### Implement


- [ ] `list_reference_edges_for_target(conn, target_id)`
- [ ] `list_referenced_by(conn, target_id)`
- [ ] `list_references_from_symbol(conn, source_id)`
- [ ] `build_reference_stats(conn, target_id)`
- [ ] `get_reference_refresh_state(conn, target_id)`


### Exact behavior


#### `list_reference_edges_for_target`
- [ ] return stored edges where `kind = "references"` and `to_id = target_id`
- [ ] order deterministically by evidence URI, line, character, then edge ID


#### `list_referenced_by`
- [ ] derive reverse usage view from `references` edges targeting `target_id`
- [ ] return the source symbols or a stable caller-oriented structure using stored `from_id`
- [ ] do not persist reverse edges


#### `list_references_from_symbol`
- [ ] return stored `references` edges where `from_id = source_id`
- [ ] order deterministically


#### `get_reference_refresh_state`
- [ ] return explicit refresh metadata for target symbol if present
- [ ] return unavailable state if missing


#### `build_reference_stats`
- [ ] compute `reference_count`
- [ ] compute unique `referencing_file_count`
- [ ] compute unique `referencing_module_count`
- [ ] include `available`
- [ ] include `last_refreshed_at`


### Exact `build_reference_stats` rules


- [ ] `reference_count` = total number of `references` edges for the target
- [ ] `referencing_file_count` = count of unique `evidence_file_id` values for those edges
- [ ] `referencing_module_count` = count of unique module identities derived from source symbols
- [ ] `available = True` only when explicit refresh metadata says this target has been refreshed successfully
- [ ] `last_refreshed_at` = refresh metadata timestamp, not guessed emptiness
- [ ] if references have never been refreshed for the target, return:
  - [ ] `available = False`
  - [ ] do not pretend zero counts are fresh truth


### Module identity rule


When computing `referencing_module_count`:
- [ ] derive the source module from stored graph relations, not from string splitting of qualified names
- [ ] nested functions and methods must count toward their containing module correctly


### Do not do


- [ ] do not compute reverse truth separately
- [ ] do not treat “never refreshed” as the same thing as “zero references”


### Done when


- [ ] the graph can answer direct and reverse reference questions from stored `references` edges only


***


## Step 12 - Update `SymbolContext` Reference Summary


### Files to modify


- [ ] phase 5 context builder code


### Implement


When building a symbol context:


- [ ] fetch reference stats for the focus symbol if available
- [ ] populate `reference_summary` from stored stats when available
- [ ] keep `reference_summary.available = False` if no enrichment exists for that symbol


### Required `reference_summary` fields


- [ ] `reference_count`
- [ ] `referencing_file_count`
- [ ] `referencing_module_count`
- [ ] `available`
- [ ] `last_refreshed_at`


### Exact behavior


- [ ] if the symbol has never had references refreshed, `available` must be `False`
- [ ] if references have been refreshed and zero edges were found, `available` must be `True` and counts may be zero
- [ ] do not collapse these two states into one


### Do not do


- [ ] do not fake zero references when enrichment never ran
- [ ] do not force a live LSP call during normal context building in phase 6


### Done when


- [ ] `SymbolContext.reference_summary` distinguishes unavailable from refreshed-zero correctly


***


## Step 13 - CLI Commands


### Files to modify


- [ ] existing CLI module from earlier phases


### Implement


Add these commands.


### Command 1
- [ ] `repo-context refresh-references <node-id>`


### Required behavior
- [ ] load the target symbol by node ID
- [ ] refresh references for that symbol using the LSP client
- [ ] print resulting stats
- [ ] print whether the refresh used exact-symbol mapping only or included module fallback cases if that is available in stats


### Command 2
- [ ] `repo-context show-references <node-id>`


### Required behavior
- [ ] show stored incoming `references` edges for the target symbol
- [ ] print source symbol ID, source kind, evidence file, and evidence location at minimum


### Command 3
- [ ] `repo-context show-referenced-by <node-id>`


### Required behavior
- [ ] show source symbols that reference the target symbol
- [ ] use reverse lookup derived from stored `references` edges


### Do not do


- [ ] do not trigger unrelated LSP features
- [ ] do not hide whether data is fresh or unavailable when printing stats


### Done when


- [ ] references can be refreshed and inspected from CLI without direct SQL


***


## Step 14 - LSP Availability Handling


### Files to verify


- [ ] `src/repo_context/lsp/client.py`
- [ ] CLI handlers
- [ ] enrichment orchestrator


### Implement


Apply these exact failure rules:


- [ ] if the language server is unavailable, raise a clear failure
- [ ] if one target symbol cannot be enriched, do not corrupt previously stored references for other targets
- [ ] if refresh fails before replacement commit, preserve old stored references for that target
- [ ] surface LSP failures clearly in CLI output


### Do not do


- [ ] do not silently convert LSP failure into zero references
- [ ] do not delete old edges before a refresh unless replacement is handled transactionally


### Done when


- [ ] LSP failures are visible and do not destroy valid existing graph state


***


## Step 15 - Tests


### Files to create or modify


- [ ] phase 6 tests under `tests/`


### Test strategy


- [ ] use a fake or mocked LSP client for most tests
- [ ] do not require a real language server for the full core test suite


### Implement these tests


- [ ] `test_get_reference_query_position_prefers_selection_range`
- [ ] `test_map_location_to_smallest_containing_symbol`
- [ ] `test_map_location_inside_local_function_prefers_local_function`
- [ ] `test_module_fallback_when_no_symbol_contains_usage`
- [ ] `test_build_reference_edge`
- [ ] `test_replace_reference_edges_for_target`
- [ ] `test_reference_stats`
- [ ] `test_reference_stats_distinguish_unavailable_from_zero`
- [ ] `test_context_includes_reference_summary_when_available`
- [ ] `test_context_marks_reference_summary_unavailable_when_not_refreshed`


### Exact test assertions


#### `test_get_reference_query_position_prefers_selection_range`
- [ ] when `selection_range_json` exists, its start is used
- [ ] when `selection_range_json` is missing, `range_json.start` is used
- [ ] when both are missing, a clear failure is raised


#### `test_map_location_to_smallest_containing_symbol`
- [ ] a usage inside a method maps to the method
- [ ] it does not map to the broader class or module when narrower containment exists


#### `test_map_location_inside_local_function_prefers_local_function`
- [ ] a usage inside a nested local function maps to that local function
- [ ] it does not map to the outer function when both contain the usage
- [ ] mapping confidence is exact-symbol confidence


#### `test_module_fallback_when_no_symbol_contains_usage`
- [ ] if no symbol contains the usage, the module node is returned
- [ ] confidence is lowered to module fallback value


#### `test_build_reference_edge`
- [ ] edge kind is `references`
- [ ] `from_id` is correct
- [ ] `to_id` is correct
- [ ] `source` is `lsp`
- [ ] evidence fields are correct
- [ ] ID includes evidence anchor


#### `test_replace_reference_edges_for_target`
- [ ] old references edges for one target are removed
- [ ] new references edges for that target are inserted
- [ ] unrelated targets remain untouched
- [ ] refresh metadata is updated transactionally


#### `test_reference_stats`
- [ ] total reference count is correct
- [ ] unique file count is correct
- [ ] unique module count is correct
- [ ] availability state is correct


#### `test_reference_stats_distinguish_unavailable_from_zero`
- [ ] never-refreshed target returns `available = False`
- [ ] refreshed target with zero references returns `available = True`
- [ ] these two cases are not collapsed


#### `test_context_includes_reference_summary_when_available`
- [ ] symbol context includes refreshed reference stats
- [ ] `available = True`


#### `test_context_marks_reference_summary_unavailable_when_not_refreshed`
- [ ] symbol context returns `available = False`
- [ ] it does not pretend that zero references are known truth


### Do not do


- [ ] do not rely only on integration tests with a real LSP process
- [ ] do not leave mapping behavior untested


### Done when


- [ ] reference enrichment behavior is covered by deterministic tests


***


## Step 16 - Fixture Validation


### Files to use


- [ ] add a small `references_case` fixture repo under `tests/fixtures/` if not already present


### Minimum fixture shape


- [ ] one target function declaration in one file
- [ ] one reference to that target in a second file
- [ ] one reference to that target in a third file
- [ ] one nested local function calling the target in at least one fixture file


### Implement


For at least one fixture repo:


- [ ] scan files using phase 2
- [ ] extract structural graph using phase 3 and phase 03b
- [ ] persist graph using phase 4
- [ ] build context using phase 5
- [ ] enrich references using phase 6 with mocked or fake LSP output
- [ ] assert exact stored edges and stats


### Do not do


- [ ] do not require a real LSP server for this fixture validation path


### Done when


- [ ] phases 2 through 6 work together on a deterministic reference-enrichment flow


***


## Step 17 - Final Verification


Before marking phase 6 complete, verify all of the following:


- [ ] a symbol’s declaration query position can be resolved
- [ ] a minimal LSP client can request references
- [ ] returned locations can be mapped back to internal symbols
- [ ] smallest-containing-symbol mapping works
- [ ] nested local function mapping works
- [ ] module fallback works
- [ ] `references` edges can be persisted
- [ ] duplicate old references for a target can be replaced cleanly
- [ ] explicit refresh metadata exists
- [ ] `referenced_by` can be derived from reverse lookup
- [ ] reference stats can be computed
- [ ] symbol context exposes reference summary when available
- [ ] symbol context distinguishes unavailable references from refreshed zero references
- [ ] CLI commands for refreshing and viewing references work
- [ ] tests pass
- [ ] no risk engine exists
- [ ] no MCP server exists


Do not mark phase 6 done until every box above is true.


***


## Required Execution Order


Implement in this order and do not skip ahead:


- [ ] Step 1 minimal LSP client
- [ ] Step 2 LSP protocol helpers
- [ ] Step 3 declaration query position resolver
- [ ] Step 4 file resolution by URI
- [ ] Step 5 range containment helper
- [ ] Step 6 smallest containing symbol picker
- [ ] Step 7 module fallback helper
- [ ] Step 8 reference edge builder
- [ ] Step 9 replace reference edges for target
- [ ] Step 10 reference enrichment orchestrator
- [ ] Step 11 graph reference queries
- [ ] Step 12 update `SymbolContext` reference summary
- [ ] Step 13 CLI commands
- [ ] Step 14 LSP availability handling
- [ ] Step 15 tests
- [ ] Step 16 fixture validation
- [ ] Step 17 final verification


***


## Phase 6 Done Definition


Phase 6 is complete only when all of these are true:


- [ ] phase 1 through phase 5 contracts remain intact
- [ ] one narrow LSP feature is implemented: `references`
- [ ] raw LSP locations are mapped back to stable internal symbol IDs
- [ ] nested local declarations remain valid mapping targets
- [ ] `references` edges are the only stored semantic usage truth
- [ ] reverse usage is derived, not duplicated
- [ ] unavailable references are distinct from zero references
- [ ] CLI inspection works
- [ ] tests pass
- [ ] no out-of-scope LSP features were added
