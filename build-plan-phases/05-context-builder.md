# 05 Symbol Context - Exact Implementation Checklist


## Objective


Implement phase 5 of the repository indexing pipeline.


Phase 5 must assemble deterministic symbol context from the stored graph so later phases can reason about one symbol and its immediate surroundings without re-reading raw AST or inventing ad-hoc queries.


Phase 5 must provide:
- symbol context assembly for one node
- structural parent and child lookup
- lexical parent and child lookup
- outgoing structural edge lookup
- incoming structural edge lookup
- file and module context hints
- deterministic structural summaries
- freshness metadata for context assembly
- context assembly tests


Phase 5 must not provide:
- LSP enrichment
- `references` edges
- reverse reference derivation
- risk scoring
- MCP tools
- watch mode
- natural-language summaries
- semantic call graph logic
- closure-capture analysis


***


## Consistency Rules


These rules are mandatory.


- [ ] Reuse the existing phase 1, phase 2, phase 3, phase 03b, and phase 4 models, naming style, storage helpers, and query helpers.
- [ ] Do not rebuild raw SQL graph lookups in the context layer if phase 4 already exposes them cleanly.
- [ ] Do not conflate structural hierarchy with lexical hierarchy.
- [ ] Do not guess missing graph facts.
- [ ] Keep context assembly deterministic.
- [ ] Keep context assembly machine-friendly.
- [ ] Keep context assembly boring and predictable.
- [ ] Return structured fields, not prose explanations.


***


## Required Inputs


Phase 5 must consume these existing inputs:


- [ ] persisted nodes from phase 4
- [ ] persisted edges from phase 4
- [ ] graph query helpers from phase 4
- [ ] SQLite connection from the storage layer


Do not add new mandatory infrastructure for this phase.


***


## Required Outputs


Phase 5 must produce these capabilities:


- [ ] build context for one symbol by `node_id`
- [ ] include focus symbol payload
- [ ] include structural parent payload if present
- [ ] include structural child payloads
- [ ] include lexical parent payload if present
- [ ] include lexical child payloads
- [ ] include incoming structural edges
- [ ] include outgoing structural edges
- [ ] include same-file sibling hints
- [ ] include basic structural summary
- [ ] include freshness metadata
- [ ] expose one reusable context builder API
- [ ] support tests for normal, nested, and edge-case symbols


Do not add reference summaries yet.
Do not add risk summaries yet.


***


## Required File Layout


Use this file layout.


Existing files may already exist. Reuse them.


- [ ] `src/repo_context/context/__init__.py`
- [ ] `src/repo_context/context/models.py`
- [ ] `src/repo_context/context/builders.py`
- [ ] `src/repo_context/context/summaries.py`
- [ ] `src/repo_context/context/freshness.py`


If your project already uses slightly different names, keep the existing style and map responsibilities clearly.


Do not create extra context packages unless strictly necessary.


***


## Context Design Rules


Apply these rules exactly.


- [ ] context is assembled from stored graph state only
- [ ] context for one symbol must be deterministic for the same DB state
- [ ] focus symbol must always be included
- [ ] structural relationships and lexical relationships must be represented separately
- [ ] ordering of children and edges must be deterministic
- [ ] context must be narrow enough to stay inspectable
- [ ] context must not contain generated explanation text


Do not turn context assembly into reasoning.


***


## Context Model


Define one stable context model.


### Required top-level fields


- [ ] `focus_symbol`
- [ ] `structural_parent`
- [ ] `structural_children`
- [ ] `lexical_parent`
- [ ] `lexical_children`
- [ ] `incoming_edges`
- [ ] `outgoing_edges`
- [ ] `file_siblings`
- [ ] `structural_summary`
- [ ] `freshness`
- [ ] `confidence`


### Important rule


`structural_parent` and `lexical_parent` are different fields and must remain different after phase 03b.


### Recommended model shape


```python
@dataclass
class SymbolContext:
    focus_symbol: dict
    structural_parent: dict | None
    structural_children: list[dict]
    lexical_parent: dict | None
    lexical_children: list[dict]
    incoming_edges: list[dict]
    outgoing_edges: list[dict]
    file_siblings: list[dict]
    structural_summary: dict
    freshness: dict
    confidence: dict
```


***


## Ordering Rules


Apply these rules exactly.


- [ ] structural children ordered by `kind`, then `name`, then `id`
- [ ] lexical children ordered by `kind`, then `name`, then `id`
- [ ] file siblings ordered by `kind`, then `qualified_name`, then `id`
- [ ] incoming edges ordered by `kind`, then `from_id`, then `id`
- [ ] outgoing edges ordered by `kind`, then `to_id`, then `id`


Do not leave ordering implicit.


***


## Symbol Adaptation Rules


Phase 5 must adapt stored nodes and edges into stable context-facing payloads.


### Required symbol payload fields


- [ ] `id`
- [ ] `repo_id`
- [ ] `file_id`
- [ ] `kind`
- [ ] `name`
- [ ] `qualified_name`
- [ ] `parent_id`
- [ ] `scope`
- [ ] `lexical_parent_id`
- [ ] `visibility_hint`
- [ ] `uri`
- [ ] `range`
- [ ] `selection_range`


### Required edge payload fields


- [ ] `id`
- [ ] `kind`
- [ ] `from_id`
- [ ] `to_id`
- [ ] `evidence_file_id`
- [ ] `evidence_uri`
- [ ] `evidence_range`
- [ ] `confidence`


Do not leak raw SQLite rows to context consumers.


***


## Step 1 - Define Context Models


### Files to modify


- [ ] `src/repo_context/context/models.py`


### Implement


- [ ] `SymbolContext`
- [ ] any small helper models if needed


### Exact behavior


- [ ] model must represent both structural and lexical relationships
- [ ] model must not include reference-summary fields yet
- [ ] model must not include risk fields yet


### Done when


- [ ] one stable context object exists for downstream phases


***


## Step 2 - Add Node and Edge Adapters


### Files to modify


- [ ] `src/repo_context/context/builders.py`
- [ ] or a small adapter helper module if your style already uses one


### Implement


- [ ] node-to-context-symbol adapter
- [ ] edge-to-context-edge adapter


### Exact behavior


- [ ] adapt node fields into stable payloads
- [ ] adapt edge fields into stable payloads
- [ ] preserve `scope` and `lexical_parent_id`
- [ ] deserialize JSON-backed fields consistently


### Do not do


- [ ] do not return raw node or edge storage rows
- [ ] do not invent summary text in adapters


### Done when


- [ ] all context outputs use one stable adapter path


***


## Step 3 - Focus Symbol Lookup


### Files to modify


- [ ] `src/repo_context/context/builders.py`


### Implement


- [ ] `build_symbol_context(conn, node_id)`


### Exact behavior


- [ ] fetch symbol by ID using phase 4 graph queries
- [ ] if symbol does not exist, return `None` or raise deterministic not-found error according to project style
- [ ] use stored graph state only


### Do not do


- [ ] do not rebuild the symbol from AST
- [ ] do not guess fallback symbols


### Done when


- [ ] context assembly starts from one stable stored symbol


***


## Step 4 - Structural Parent and Child Assembly


### Files to modify


- [ ] `src/repo_context/context/builders.py`


### Implement


- [ ] fetch structural parent using `parent_id`
- [ ] fetch structural children using phase 4 structural child helper


### Exact behavior


- [ ] if `parent_id` is null, structural parent is `None`
- [ ] structural children must be deterministic and adapted
- [ ] structural relationships must not use `lexical_parent_id`


### Do not do


- [ ] do not substitute lexical parent when structural parent is missing


### Done when


- [ ] structural hierarchy is assembled correctly and explicitly


***


## Step 5 - Lexical Parent and Child Assembly


### Files to modify


- [ ] `src/repo_context/context/builders.py`


### Implement


- [ ] fetch lexical parent using `lexical_parent_id`
- [ ] fetch lexical children using phase 4 lexical child helper


### Exact behavior


- [ ] if `lexical_parent_id` is null, lexical parent is `None`
- [ ] lexical children must be deterministic and adapted
- [ ] lexical relationships must not use structural `parent_id`


### Important rule


For nested functions introduced in phase 03b, lexical context is the main reason they are useful.
Do not bury this relationship.


### Done when


- [ ] nested symbols expose lexical context cleanly


***


## Step 6 - Edge Assembly


### Files to modify


- [ ] `src/repo_context/context/builders.py`


### Implement


- [ ] fetch outgoing edges using phase 4 edge queries
- [ ] fetch incoming edges using phase 4 edge queries


### Exact behavior


- [ ] include only stored edges from phase 4
- [ ] do not synthesize reverse edges
- [ ] do not include future `references` edges in this phase


### Allowed edge kinds


Whatever structural edge kinds phase 3 and 03b already persist, including:
- [ ] containment-like edges
- [ ] inheritance-like edges
- [ ] import-like edges
- [ ] `SCOPE_PARENT` if retained in context views


### Optional rule


You may exclude `SCOPE_PARENT` from general incoming/outgoing edge lists if you already expose lexical fields separately, but the rule must be explicit and consistent.


### Done when


- [ ] edge context is stable and based only on persisted graph facts


***


## Step 7 - File Sibling Hints


### Files to modify


- [ ] `src/repo_context/context/builders.py`


### Implement


- [ ] collect other symbols in the same file as the focus symbol
- [ ] exclude the focus symbol itself
- [ ] optionally cap the list to a deterministic small count if needed


### Exact behavior


- [ ] siblings must come from same `file_id`
- [ ] siblings must be ordered deterministically
- [ ] list must remain small enough for inspection


### Recommended v1 rule


- [ ] include all same-file symbols if fixture sizes are small
- [ ] otherwise cap deterministically, for example first 50 after ordering


### Done when


- [ ] context can show nearby file-level structural neighbors without inventing narrative


***


## Step 8 - Structural Summary


### Files to modify


- [ ] `src/repo_context/context/summaries.py`


### Implement


- [ ] `build_structural_summary(context)`


### Required summary fields


- [ ] `has_structural_parent`
- [ ] `structural_child_count`
- [ ] `has_lexical_parent`
- [ ] `lexical_child_count`
- [ ] `incoming_edge_count`
- [ ] `outgoing_edge_count`
- [ ] `same_file_sibling_count`
- [ ] `scope`
- [ ] `is_local_declaration`
- [ ] `is_nested_declaration`


### Exact rules


- [ ] `is_local_declaration` must be true for `local_function`, `local_async_function`, and classes with `scope = "function"`
- [ ] `is_nested_declaration` must be true when `lexical_parent_id` is not null


### Do not do


- [ ] do not add explanation prose
- [ ] do not add risk scores


### Done when


- [ ] context includes a compact machine-friendly structural summary


***


## Step 9 - Freshness Metadata


### Files to modify


- [ ] `src/repo_context/context/freshness.py`


### Implement


- [ ] helper to assemble freshness metadata from stored rows only


### Required freshness fields


- [ ] `node_last_indexed_at`
- [ ] `edge_snapshot_last_indexed_at`
- [ ] `has_incoming_edges`
- [ ] `has_outgoing_edges`
- [ ] `context_source = "graph_only"`


### Exact behavior


- [ ] node freshness uses focus symbol `last_indexed_at`
- [ ] edge freshness uses latest relevant stored edge timestamp if edges exist
- [ ] no LSP freshness fields yet


### Done when


- [ ] context consumers can tell this is graph-derived context only


***


## Step 10 - Confidence Metadata


### Files to modify


- [ ] `src/repo_context/context/builders.py`
- [ ] or `src/repo_context/context/summaries.py`


### Implement


- [ ] simple confidence block derived from stored data completeness


### Required confidence fields


- [ ] `focus_symbol_confidence`
- [ ] `edge_confidence_min`
- [ ] `edge_confidence_max`
- [ ] `contains_placeholder_targets`
- [ ] `graph_only = true`


### Exact behavior


- [ ] symbol confidence comes from stored node confidence
- [ ] edge confidence summary comes from included incoming and outgoing edges
- [ ] placeholder target presence must be true if any edge endpoint uses unresolved placeholder IDs


### Do not do


- [ ] do not invent probabilistic reasoning here


### Done when


- [ ] context consumers get an honest confidence summary


***


## Step 11 - Builder Assembly Flow


### Files to modify


- [ ] `src/repo_context/context/builders.py`


### Implement


Assemble context in this exact order:


1. [ ] fetch focus symbol
2. [ ] fetch structural parent
3. [ ] fetch structural children
4. [ ] fetch lexical parent
5. [ ] fetch lexical children
6. [ ] fetch outgoing edges
7. [ ] fetch incoming edges
8. [ ] fetch file siblings
9. [ ] build structural summary
10. [ ] build freshness
11. [ ] build confidence
12. [ ] return stable `SymbolContext`


### Do not do


- [ ] do not perform recursive graph traversal in v1
- [ ] do not mix context assembly with persistence mutation


### Done when


- [ ] one small deterministic assembly path exists


***


## Step 12 - Graph Query Integration


### Files to verify


- [ ] `src/repo_context/graph/queries.py`
- [ ] `src/repo_context/context/builders.py`


### Implement


Verify context assembly uses phase 4 helpers for:
- [ ] symbol lookup by ID
- [ ] structural parent lookup
- [ ] structural child lookup
- [ ] lexical parent lookup
- [ ] lexical child lookup
- [ ] edge lookup
- [ ] file symbol listing


### Do not do


- [ ] do not duplicate SQL already owned by phase 4
- [ ] do not let context layer become the new storage layer


### Done when


- [ ] context assembly is layered cleanly on graph persistence


***


## Step 13 - Placeholder Target Handling


### Files to verify


- [ ] context builder
- [ ] confidence helper


### Implement


Ensure context assembly behaves correctly when included edges point to placeholder target IDs such as:
- [ ] `external_or_unresolved:...`
- [ ] `unresolved_base:...`


### Exact behavior


- [ ] context assembly must not crash
- [ ] such edges may still appear in incoming or outgoing edge payloads
- [ ] confidence metadata must surface placeholder presence honestly


### Do not do


- [ ] do not create fake symbols for placeholder targets in this phase


### Done when


- [ ] unresolved edge endpoints remain explicit and harmless


***


## Step 14 - Tests


### Files to create or modify


- [ ] phase 5 tests under `tests/`


### Implement these tests


- [ ] `test_build_symbol_context_for_module_function`
- [ ] `test_build_symbol_context_for_method`
- [ ] `test_build_symbol_context_for_local_function`
- [ ] `test_build_symbol_context_for_local_class`
- [ ] `test_structural_and_lexical_parents_are_distinct`
- [ ] `test_file_siblings_are_deterministic`
- [ ] `test_context_handles_placeholder_targets`
- [ ] `test_structural_summary_flags_local_declarations`
- [ ] `test_missing_symbol_returns_none_or_not_found`
- [ ] end-to-end context test if project style already supports fixture pipelines


### Exact test assertions


#### `test_build_symbol_context_for_module_function`
- [ ] focus symbol is correct
- [ ] structural parent is correct or `None`
- [ ] structural children are correct
- [ ] lexical parent is `None`


#### `test_build_symbol_context_for_method`
- [ ] focus symbol is correct
- [ ] structural parent is class
- [ ] lexical parent is class only if that is how phase 03b stores method lexical parent; otherwise follow stored truth consistently
- [ ] edges are included deterministically


#### `test_build_symbol_context_for_local_function`
- [ ] focus symbol kind is `local_function`
- [ ] lexical parent is containing function or method
- [ ] lexical children are included correctly
- [ ] structural and lexical relationships are not silently merged


#### `test_build_symbol_context_for_local_class`
- [ ] focus symbol kind is `class`
- [ ] scope is `function`
- [ ] lexical parent is containing function or method


#### `test_structural_and_lexical_parents_are_distinct`
- [ ] one fixture demonstrates different `parent_id` and `lexical_parent_id`
- [ ] both fields remain available in context


#### `test_file_siblings_are_deterministic`
- [ ] same file siblings are stable across repeated runs
- [ ] ordering is deterministic


#### `test_context_handles_placeholder_targets`
- [ ] unresolved placeholder edge targets do not break context assembly
- [ ] confidence block reports placeholder presence


#### `test_structural_summary_flags_local_declarations`
- [ ] local function sets `is_local_declaration = true`
- [ ] nested declaration sets `is_nested_declaration = true`


#### `test_missing_symbol_returns_none_or_not_found`
- [ ] missing symbol path is deterministic and explicit


### Do not do


- [ ] do not rely only on smoke tests
- [ ] do not bring in LSP or references yet


### Done when


- [ ] context assembly behavior is covered for normal and nested declarations


***


## Step 15 - End-to-End Fixture Validation


### Files to use


- [ ] reuse phase 3, phase 03b, and phase 4 fixture repos


### Implement


For at least one fixture repo:


- [ ] scan files using phase 2
- [ ] extract nodes and edges using phase 3 and phase 03b
- [ ] persist graph using phase 4
- [ ] build symbol context using phase 5
- [ ] assert exact expected context fields and counts


### Do not do


- [ ] do not involve LSP
- [ ] do not involve MCP
- [ ] do not involve risk engine


### Done when


- [ ] phases 2 through 5 work together on a real fixture flow


***


## Step 16 - Final Verification


Before marking phase 5 complete, verify all of the following:


- [ ] one symbol context can be built deterministically
- [ ] focus symbol is always included
- [ ] structural parent lookup works
- [ ] structural child lookup works
- [ ] lexical parent lookup works
- [ ] lexical child lookup works
- [ ] structural and lexical relationships remain distinct
- [ ] outgoing edges are included deterministically
- [ ] incoming edges are included deterministically
- [ ] file siblings are included deterministically
- [ ] structural summary is correct
- [ ] freshness metadata is present
- [ ] confidence metadata is present
- [ ] placeholder targets do not break context assembly
- [ ] tests pass
- [ ] no LSP enrichment exists
- [ ] no risk engine logic exists
- [ ] no MCP logic exists


Do not mark phase 5 done until every box above is true.


***


## Required Execution Order


Implement in this order and do not skip ahead:


- [ ] Step 1 define context models
- [ ] Step 2 add node and edge adapters
- [ ] Step 3 focus symbol lookup
- [ ] Step 4 structural parent and child assembly
- [ ] Step 5 lexical parent and child assembly
- [ ] Step 6 edge assembly
- [ ] Step 7 file sibling hints
- [ ] Step 8 structural summary
- [ ] Step 9 freshness metadata
- [ ] Step 10 confidence metadata
- [ ] Step 11 builder assembly flow
- [ ] Step 12 graph query integration
- [ ] Step 13 placeholder target handling
- [ ] Step 14 tests
- [ ] Step 15 end-to-end fixture validation
- [ ] Step 16 final verification


***


## Phase 5 Done Definition


Phase 5 is complete only when all of these are true:


- [ ] phase 1, phase 2, phase 3, phase 03b, and phase 4 contracts remain intact
- [ ] context assembly is deterministic
- [ ] structural and lexical relationships are both preserved correctly
- [ ] local nested declarations can be inspected through context
- [ ] placeholder edge targets remain explicit and harmless
- [ ] tests pass
- [ ] no out-of-scope features were added
