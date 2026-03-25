# 04 Graph Storage - Exact Implementation Checklist


## Objective


Implement phase 4 of the repository indexing pipeline.


Phase 4 must take the nodes and edges produced by phase 3 and phase 03b and make them durable, queryable, replaceable, and inspectable in SQLite.


Phase 4 must provide:
- stable node persistence
- stable edge persistence
- deterministic upserts
- lookup helpers
- file-level graph replacement
- repo-level graph queries
- CLI inspection commands
- persistence and cleanup tests
- storage compatibility with nested-scope symbols


Phase 4 must not provide:
- LSP enrichment
- `references` edges
- reverse reference derivation
- symbol context assembly
- risk scoring
- MCP tools
- watch mode
- semantic call graph logic


***


## Consistency Rules


These rules are mandatory.


- [ ] Reuse the existing phase 1, phase 2, phase 3, and phase 03b models, database schema style, naming style, serialization style, and storage patterns.
- [ ] Do not invent a parallel persistence model for nodes or edges.
- [ ] Do not rename existing database columns.
- [ ] Do not change the schema contract unless phase 03b compatibility or this phase explicitly requires it.
- [ ] Do not move graph logic into CLI code.
- [ ] Do not scatter raw SQL across unrelated modules.
- [ ] Keep JSON serialization behavior consistent with earlier phases.
- [ ] Keep all persistence behavior deterministic.
- [ ] Keep graph storage boring and predictable.
- [ ] Preserve both structural parent relationships and lexical parent relationships without conflating them.


***


## Required Inputs


Phase 4 must consume these existing inputs:


- [ ] nodes produced by phase 3 and phase 03b
- [ ] edges produced by phase 3 and phase 03b
- [ ] SQLite connection from the existing storage layer
- [ ] existing `nodes` table
- [ ] existing `edges` table
- [ ] existing CLI shell from earlier phases


Do not add new mandatory infrastructure for this phase.


***


## Required Outputs


Phase 4 must produce these capabilities:


- [ ] upsert a node by stable ID
- [ ] upsert multiple nodes by stable ID
- [ ] upsert an edge by stable ID
- [ ] upsert multiple edges by stable ID
- [ ] fetch node by node ID
- [ ] fetch node by qualified name
- [ ] fetch edge by edge ID
- [ ] list nodes for one file
- [ ] list nodes for one repo
- [ ] list child nodes by structural `parent_id`
- [ ] list lexical child nodes by `lexical_parent_id`
- [ ] list edges for one repo
- [ ] list outgoing edges by `from_id`
- [ ] list incoming edges by `to_id`
- [ ] list edges for one file via `evidence_file_id`
- [ ] delete nodes for one file
- [ ] delete edges for one file
- [ ] replace one file graph transactionally
- [ ] compute basic graph stats for one repo
- [ ] inspect graph state from CLI


Do not add higher-level context assembly in this phase.


***


## Required File Layout


Use this file layout.


Existing files may already exist from phase 3. Reuse them.


- [ ] `src/repo_context/storage/nodes.py`
- [ ] `src/repo_context/storage/edges.py`
- [ ] `src/repo_context/storage/graph.py`
- [ ] `src/repo_context/graph/__init__.py`
- [ ] `src/repo_context/graph/queries.py`
- [ ] `src/repo_context/graph/filters.py`


If `storage/nodes.py` and `storage/edges.py` already exist, extend them instead of replacing them.


Do not create extra graph packages unless strictly necessary.


***


## Schema Rules


Apply these rules exactly.


### Nodes table


Phase 4 assumes a `nodes` table exists with these columns:


- [ ] `id`
- [ ] `repo_id`
- [ ] `file_id`
- [ ] `language`
- [ ] `kind`
- [ ] `name`
- [ ] `qualified_name`
- [ ] `uri`
- [ ] `range_json`
- [ ] `selection_range_json`
- [ ] `parent_id`
- [ ] `scope`
- [ ] `lexical_parent_id`
- [ ] `visibility_hint`
- [ ] `doc_summary`
- [ ] `content_hash`
- [ ] `semantic_hash`
- [ ] `source`
- [ ] `confidence`
- [ ] `payload_json`
- [ ] `last_indexed_at`


### Edges table


Phase 4 assumes an `edges` table exists with these columns:


- [ ] `id`
- [ ] `repo_id`
- [ ] `kind`
- [ ] `from_id`
- [ ] `to_id`
- [ ] `source`
- [ ] `confidence`
- [ ] `evidence_file_id`
- [ ] `evidence_uri`
- [ ] `evidence_range_json`
- [ ] `payload_json`
- [ ] `last_indexed_at`


Do not rename these columns.


***


## Required Indexes


Ensure these indexes exist.


### Node indexes


- [ ] index on `nodes(repo_id)`
- [ ] index on `nodes(file_id)`
- [ ] index on `nodes(qualified_name)`
- [ ] index on `nodes(parent_id)`
- [ ] index on `nodes(lexical_parent_id)`
- [ ] index on `nodes(kind)`


### Edge indexes


- [ ] index on `edges(repo_id)`
- [ ] index on `edges(from_id)`
- [ ] index on `edges(to_id)`
- [ ] index on `edges(kind)`
- [ ] index on `edges(evidence_file_id)`


If these indexes already exist from earlier phases, do not recreate them differently.


***


## Storage Responsibilities


Apply these boundaries exactly.


### `storage/nodes.py`


This module must own:
- [ ] node row mapping
- [ ] node upsert
- [ ] bulk node upsert
- [ ] node fetch by ID
- [ ] node fetch by qualified name
- [ ] node listing by file
- [ ] node listing by repo
- [ ] structural child node listing by `parent_id`
- [ ] lexical child node listing by `lexical_parent_id`
- [ ] file-level node deletion


### `storage/edges.py`


This module must own:
- [ ] edge row mapping
- [ ] edge upsert
- [ ] bulk edge upsert
- [ ] edge fetch by ID
- [ ] edge listing by repo
- [ ] outgoing edge listing
- [ ] incoming edge listing
- [ ] file-level edge listing
- [ ] file-level edge deletion


### `storage/graph.py`


This module must own:
- [ ] file graph replacement transaction
- [ ] small transactional graph helpers only


### `graph/queries.py`


This module must own:
- [ ] graph-oriented read helpers
- [ ] structural parent and child lookup helpers
- [ ] lexical parent and child lookup helpers
- [ ] no raw persistence mutation logic


### `graph/filters.py`


This module may own:
- [ ] optional reusable filtering helpers
- [ ] callable-kind helper sets
- [ ] no required complex logic for v1


Do not move business logic or risk logic into these modules.


***


## Serialization Rules


Apply these rules exactly.


- [ ] all nested structured fields must be serialized to JSON strings before storage
- [ ] all JSON serialization must happen in explicit row-mapping helpers
- [ ] all row-loading logic must deserialize JSON consistently
- [ ] `range_json` must store serialized range data
- [ ] `selection_range_json` must store serialized selection range data
- [ ] `payload_json` must store serialized payload data
- [ ] `evidence_range_json` must store serialized evidence range data


Do not duplicate JSON conversion logic in many files.


***


## Parent Semantics Rules


Apply these rules exactly.


- [ ] `parent_id` is the structural parent relationship already used by the project
- [ ] `lexical_parent_id` is the immediate lexical declaration parent added for phase 03b
- [ ] structural parent and lexical parent are not automatically the same thing
- [ ] graph queries must not silently substitute one for the other
- [ ] nested-scope queries must use `lexical_parent_id`
- [ ] hierarchy queries that are explicitly structural must use `parent_id`


Do not collapse both parent concepts into one helper.
That will create confusing bugs later.


***


## Duplicate Symbol Identity Rules


Apply these rules exactly.


- [ ] persistence conflict key for nodes remains `id`
- [ ] persistence conflict key for edges remains `id`
- [ ] `qualified_name` is not assumed globally unique after phase 03b
- [ ] same-scope duplicate declarations may share visible `qualified_name` if symbol IDs are internally disambiguated upstream
- [ ] storage must preserve distinct rows for distinct node IDs even if visible qualified names match


Do not treat `qualified_name` as a replacement for stable symbol identity.


***


## Step 1 - Add or Verify Indexes


### Files to modify


- [ ] existing migration or DB initialization module from earlier phases


### Implement


- [ ] verify the six required node indexes exist
- [ ] verify the five required edge indexes exist
- [ ] add missing indexes with `CREATE INDEX IF NOT EXISTS`


### Do not do


- [ ] do not change table definitions unless the schema is actually missing required columns for phase 03b compatibility
- [ ] do not add speculative indexes not used by this phase


### Done when


- [ ] all required graph indexes exist in SQLite


***


## Step 2 - Node Row Mapping


### File


- [ ] `src/repo_context/storage/nodes.py`


### Implement


Add explicit row mapping helpers for nodes.


### Required behavior


- [ ] convert in-memory node representation to DB row values
- [ ] serialize `range_json` to JSON string or `None`
- [ ] serialize `selection_range_json` to JSON string or `None`
- [ ] serialize `payload_json` to JSON string
- [ ] persist `scope` as scalar field
- [ ] persist `lexical_parent_id` as scalar field
- [ ] preserve scalar fields exactly
- [ ] support deterministic JSON serialization


### Also implement


- [ ] row-to-node conversion helper
- [ ] deserialize JSON fields back into Python structures
- [ ] load `scope` and `lexical_parent_id` consistently


### Do not do


- [ ] do not inline JSON dumping in every query function
- [ ] do not leave row mapping implicit


### Done when


- [ ] node storage uses one explicit mapping path in both directions


***


## Step 3 - Edge Row Mapping


### File


- [ ] `src/repo_context/storage/edges.py`


### Implement


Add explicit row mapping helpers for edges.


### Required behavior


- [ ] convert in-memory edge representation to DB row values
- [ ] serialize `evidence_range_json` to JSON string or `None`
- [ ] serialize `payload_json` to JSON string
- [ ] preserve scalar fields exactly
- [ ] support deterministic JSON serialization


### Also implement


- [ ] row-to-edge conversion helper
- [ ] deserialize JSON fields back into Python structures


### Do not do


- [ ] do not inline JSON dumping in every edge query
- [ ] do not leave row mapping implicit


### Done when


- [ ] edge storage uses one explicit mapping path in both directions


***


## Step 4 - Node Upsert


### File


- [ ] `src/repo_context/storage/nodes.py`


### Implement


- [ ] `upsert_node(conn, node)`


### Exact behavior


- [ ] insert node if `id` does not exist
- [ ] update node if `id` already exists
- [ ] use `ON CONFLICT(id) DO UPDATE`
- [ ] update all persisted columns on conflict
- [ ] use node `id` as the only conflict key


### Do not do


- [ ] do not use qualified name as the conflict key
- [ ] do not create duplicate rows for the same node ID


### Done when


- [ ] reinserting the same node ID updates the row instead of duplicating it


***


## Step 5 - Bulk Node Upsert


### File


- [ ] `src/repo_context/storage/nodes.py`


### Implement


- [ ] `upsert_nodes(conn, nodes)`


### Exact behavior


- [ ] call node upsert logic for every node
- [ ] support inserting or updating multiple nodes in one operation
- [ ] preserve deterministic behavior


### Do not do


- [ ] do not silently skip bad rows


### Done when


- [ ] multiple nodes can be persisted reliably in one call


***


## Step 6 - Node Read Helpers


### File


- [ ] `src/repo_context/storage/nodes.py`


### Implement


- [ ] `get_node_by_id(conn, node_id)`
- [ ] `get_node_by_qualified_name(conn, repo_id, qualified_name, kind=None)`
- [ ] `list_nodes_for_file(conn, file_id)`
- [ ] `list_nodes_for_repo(conn, repo_id)`
- [ ] `list_child_nodes(conn, parent_id)`
- [ ] `list_lexical_children(conn, lexical_parent_id)`


### Exact behavior


#### `get_node_by_id`
- [ ] return one node or `None`


#### `get_node_by_qualified_name`
- [ ] filter by `repo_id`
- [ ] filter by `qualified_name`
- [ ] if `kind` is provided, include `kind` filter
- [ ] if multiple rows match, return `None` or raise a deterministic ambiguity error according to project style
- [ ] do not silently guess among duplicate rows


#### `list_nodes_for_file`
- [ ] return all nodes with matching `file_id`
- [ ] order by `kind`, then `qualified_name`, then `id`


#### `list_nodes_for_repo`
- [ ] return all nodes with matching `repo_id`
- [ ] order by `kind`, then `qualified_name`, then `id`


#### `list_child_nodes`
- [ ] return all nodes with matching structural `parent_id`
- [ ] order by `kind`, then `name`, then `id`


#### `list_lexical_children`
- [ ] return all nodes with matching `lexical_parent_id`
- [ ] order by `kind`, then `name`, then `id`


### Do not do


- [ ] do not return raw SQLite rows to callers
- [ ] do not leave ordering nondeterministic
- [ ] do not pretend `qualified_name` is always unique after phase 03b


### Done when


- [ ] node retrieval is deterministic and returns deserialized structures


***


## Step 7 - Delete Nodes for File


### File


- [ ] `src/repo_context/storage/nodes.py`


### Implement


- [ ] `delete_nodes_for_file(conn, file_id)`


### Exact behavior


- [ ] delete all node rows where `file_id = ?`


### Do not do


- [ ] do not delete nodes for other files
- [ ] do not combine edge deletion inside this function


### Done when


- [ ] all nodes owned by one file can be removed cleanly


***


## Step 8 - Edge Upsert


### File


- [ ] `src/repo_context/storage/edges.py`


### Implement


- [ ] `upsert_edge(conn, edge)`


### Exact behavior


- [ ] insert edge if `id` does not exist
- [ ] update edge if `id` already exists
- [ ] use `ON CONFLICT(id) DO UPDATE`
- [ ] update all persisted columns on conflict
- [ ] use edge `id` as the only conflict key


### Do not do


- [ ] do not use `from_id` plus `to_id` as conflict key
- [ ] do not create duplicate rows for the same edge ID


### Done when


- [ ] reinserting the same edge ID updates the row instead of duplicating it


***


## Step 9 - Bulk Edge Upsert


### File


- [ ] `src/repo_context/storage/edges.py`


### Implement


- [ ] `upsert_edges(conn, edges)`


### Exact behavior


- [ ] call edge upsert logic for every edge
- [ ] support inserting or updating multiple edges in one operation
- [ ] preserve deterministic behavior


### Do not do


- [ ] do not silently skip bad rows


### Done when


- [ ] multiple edges can be persisted reliably in one call


***


## Step 10 - Edge Read Helpers


### File


- [ ] `src/repo_context/storage/edges.py`


### Implement


- [ ] `get_edge_by_id(conn, edge_id)`
- [ ] `list_edges_for_repo(conn, repo_id)`
- [ ] `list_outgoing_edges(conn, from_id, kind=None)`
- [ ] `list_incoming_edges(conn, to_id, kind=None)`
- [ ] `list_edges_for_file(conn, file_id)`


### Exact behavior


#### `get_edge_by_id`
- [ ] return one edge or `None`


#### `list_edges_for_repo`
- [ ] return all edges with matching `repo_id`
- [ ] order by `kind`, then `from_id`, then `to_id`, then `id`


#### `list_outgoing_edges`
- [ ] filter by `from_id`
- [ ] if `kind` is provided, also filter by `kind`
- [ ] order by `kind`, then `to_id`, then `id`


#### `list_incoming_edges`
- [ ] filter by `to_id`
- [ ] if `kind` is provided, also filter by `kind`
- [ ] order by `kind`, then `from_id`, then `id`


#### `list_edges_for_file`
- [ ] filter by `evidence_file_id`
- [ ] order by `kind`, then `from_id`, then `to_id`, then `id`


### Do not do


- [ ] do not return raw SQLite rows to callers
- [ ] do not leave ordering nondeterministic


### Done when


- [ ] edge retrieval is deterministic and returns deserialized structures


***


## Step 11 - Delete Edges for File


### File


- [ ] `src/repo_context/storage/edges.py`


### Implement


- [ ] `delete_edges_for_file(conn, file_id)`


### Exact behavior


- [ ] delete all edge rows where `evidence_file_id = ?`


### Do not do


- [ ] do not delete edges for other files
- [ ] do not combine node deletion inside this function


### Done when


- [ ] all file-evidence-owned edges for one file can be removed cleanly


***


## Step 12 - Replace File Graph


### File


- [ ] `src/repo_context/storage/graph.py`


### Implement


- [ ] `replace_file_graph(conn, file_id, nodes, edges)`


### Exact behavior


- [ ] begin a transaction
- [ ] delete edges for `file_id`
- [ ] delete nodes for `file_id`
- [ ] insert fresh nodes
- [ ] insert fresh edges
- [ ] commit on success
- [ ] rollback on failure
- [ ] re-raise the original failure after rollback


### Required ordering


- [ ] edge deletion must happen before node deletion
- [ ] node insertion must happen before edge insertion


### Do not do


- [ ] do not try to diff old and new file graphs in v1
- [ ] do not perform partial commits inside replacement


### Done when


- [ ] one file graph can be fully replaced without leaving stale file-owned graph state behind


***


## Step 13 - Graph Read Query Layer


### File


- [ ] `src/repo_context/graph/queries.py`


### Implement


- [ ] `get_symbol(conn, node_id)`
- [ ] `get_symbol_by_qualified_name(conn, repo_id, qualified_name, kind=None)`
- [ ] `get_parent_symbol(conn, node)`
- [ ] `get_child_symbols(conn, node_id)`
- [ ] `get_lexical_parent_symbol(conn, node)`
- [ ] `get_lexical_child_symbols(conn, node_id)`
- [ ] `get_outgoing_edges(conn, node_id, kind=None)`
- [ ] `get_incoming_edges(conn, node_id, kind=None)`
- [ ] `get_symbols_for_file(conn, file_id)`
- [ ] `get_repo_graph_stats(conn, repo_id)`


### Exact behavior


#### `get_symbol`
- [ ] delegate to node storage lookup by ID


#### `get_symbol_by_qualified_name`
- [ ] delegate to node storage lookup by qualified name


#### `get_parent_symbol`
- [ ] if node has no structural `parent_id`, return `None`
- [ ] otherwise fetch the structural parent node by ID


#### `get_child_symbols`
- [ ] return structural child nodes using `parent_id`


#### `get_lexical_parent_symbol`
- [ ] if node has no `lexical_parent_id`, return `None`
- [ ] otherwise fetch the lexical parent node by ID


#### `get_lexical_child_symbols`
- [ ] return lexical child nodes using `lexical_parent_id`


#### `get_outgoing_edges`
- [ ] delegate to edge storage outgoing edge listing


#### `get_incoming_edges`
- [ ] delegate to edge storage incoming edge listing


#### `get_symbols_for_file`
- [ ] delegate to node storage file listing


#### `get_repo_graph_stats`
- [ ] return counts for:
  - `repo_id`
  - total node count
  - total edge count
  - module count
  - class count
  - callable count
  - local callable count


### Callable count rule


- [ ] callable count must equal count of nodes with kind in `function`, `async_function`, `method`, `async_method`, `local_function`, `local_async_function`
- [ ] local callable count must equal count of nodes with kind in `local_function`, `local_async_function`


### Do not do


- [ ] do not add smart context assembly here
- [ ] do not add traversal engines here


### Done when


- [ ] later phases can reuse one small graph query API instead of writing raw SQL repeatedly


***


## Step 14 - Optional Filters Module


### File


- [ ] `src/repo_context/graph/filters.py`


### Implement


- [ ] add only tiny reusable helpers if needed by CLI or queries
- [ ] add callable-kind helper sets if useful
- [ ] leave this module minimal if not needed


### Do not do


- [ ] do not build a mini query language


### Done when


- [ ] no filtering logic is duplicated unnecessarily


***


## Step 15 - CLI Inspection Commands


### Files to modify


- [ ] existing CLI module from earlier phases


### Implement


Add these CLI commands.


### Command 1
- [ ] `repo-context graph-stats <repo-id>`


Required behavior:
- [ ] print counts of nodes and edges
- [ ] print module, class, callable, and local callable counts


### Command 2
- [ ] `repo-context list-nodes <repo-id>`


Required behavior:
- [ ] print stored nodes for the repo
- [ ] output enough fields to inspect identity, structure, scope, and hierarchy


### Command 3
- [ ] `repo-context list-edges <repo-id>`


Required behavior:
- [ ] print stored edges for the repo
- [ ] output enough fields to inspect edge direction and kind


### Command 4
- [ ] `repo-context show-node <node-id>`


Required behavior:
- [ ] print one node
- [ ] print immediate structural parent summary if parent exists
- [ ] print immediate structural child summary if children exist
- [ ] print immediate lexical parent summary if present
- [ ] print immediate lexical child summary if present


### Do not do


- [ ] do not add MCP-like behavior
- [ ] do not add complex formatting requirements
- [ ] do not hide important graph fields from CLI output


### Done when


- [ ] graph state can be inspected from the command line without direct SQL


***


## Step 16 - Placeholder Target Handling


### Files to verify


- [ ] storage and query modules


### Implement


Ensure graph queries behave correctly when edges point to placeholder target IDs such as:
- [ ] `external_or_unresolved:...`
- [ ] `unresolved_base:...`


### Exact behavior


- [ ] storing such edges must succeed
- [ ] listing such edges must succeed
- [ ] incoming and outgoing edge queries must not crash when endpoint target is not a real node row


### Do not do


- [ ] do not create fake nodes for placeholder targets in this phase


### Done when


- [ ] unresolved targets remain explicit and harmless to graph queries


***


## Step 17 - Tests


### Files to create or modify


- [ ] phase 4 tests under `tests/`


### Implement these tests


- [ ] `test_upsert_node`
- [ ] `test_upsert_edge`
- [ ] `test_get_node_by_id`
- [ ] `test_get_node_by_qualified_name`
- [ ] `test_get_node_by_qualified_name_ambiguous`
- [ ] `test_list_child_nodes`
- [ ] `test_list_lexical_children`
- [ ] `test_list_outgoing_and_incoming_edges`
- [ ] `test_replace_file_graph`
- [ ] `test_graph_stats`
- [ ] `test_graph_stats_include_local_callables`
- [ ] `test_placeholder_targets_do_not_break_queries`
- [ ] CLI inspection tests if CLI tests already exist in the project style


### Exact test assertions


#### `test_upsert_node`
- [ ] inserting a node creates one row
- [ ] upserting the same node ID updates the existing row
- [ ] row count does not increase on same ID reinsert


#### `test_upsert_edge`
- [ ] inserting an edge creates one row
- [ ] upserting the same edge ID updates the existing row
- [ ] row count does not increase on same ID reinsert


#### `test_get_node_by_id`
- [ ] correct node is returned by ID
- [ ] missing ID returns `None`


#### `test_get_node_by_qualified_name`
- [ ] correct node is returned for repo plus qualified name
- [ ] optional kind filter works
- [ ] missing name returns `None`


#### `test_get_node_by_qualified_name_ambiguous`
- [ ] duplicate visible qualified names do not cause silent guessing
- [ ] function returns `None` or deterministic ambiguity behavior according to project style


#### `test_list_child_nodes`
- [ ] structural children are returned correctly
- [ ] result ordering is deterministic


#### `test_list_lexical_children`
- [ ] lexical children are returned correctly
- [ ] nested functions under one lexical parent are returned correctly
- [ ] result ordering is deterministic


#### `test_list_outgoing_and_incoming_edges`
- [ ] outgoing edge query returns expected edges
- [ ] incoming edge query returns expected edges
- [ ] optional edge kind filter works


#### `test_replace_file_graph`
- [ ] old file-owned nodes are deleted
- [ ] old file-owned edges are deleted
- [ ] new file nodes are inserted
- [ ] new file edges are inserted
- [ ] unrelated file data remains untouched


#### `test_graph_stats`
- [ ] node and edge counts are correct
- [ ] module count is correct
- [ ] class count is correct
- [ ] callable count is correct


#### `test_graph_stats_include_local_callables`
- [ ] `local_function` and `local_async_function` contribute to callable count
- [ ] local callable count is correct


#### `test_placeholder_targets_do_not_break_queries`
- [ ] placeholder `to_id` values do not break edge listing
- [ ] graph queries still return valid results


### Do not do


- [ ] do not rely only on smoke tests
- [ ] do not leave file replacement untested


### Done when


- [ ] persistence, retrieval, cleanup, and graph stats are covered by tests


***


## Step 18 - End-to-End Fixture Validation


### Files to use


- [ ] reuse phase 3 and phase 03b fixture repos


### Implement


For at least one fixture repo:


- [ ] scan files using phase 2
- [ ] extract nodes and edges using phase 3 and phase 03b
- [ ] persist graph using phase 4
- [ ] run graph queries using phase 4 helpers
- [ ] assert exact expected results


### Do not do


- [ ] do not involve LSP
- [ ] do not involve MCP


### Done when


- [ ] phase 2, phase 3, phase 03b, and phase 4 work together on a real fixture flow


***


## Step 19 - Final Verification


Before marking phase 4 complete, verify all of the following:


- [ ] nodes can be inserted without duplication
- [ ] nodes can be updated without duplication
- [ ] edges can be inserted without duplication
- [ ] edges can be updated without duplication
- [ ] nodes can be queried by ID
- [ ] nodes can be queried by qualified name
- [ ] ambiguous qualified-name lookups do not silently guess
- [ ] structural child nodes can be listed by `parent_id`
- [ ] lexical child nodes can be listed by `lexical_parent_id`
- [ ] outgoing edges can be listed by source node
- [ ] incoming edges can be listed by target node
- [ ] file-owned graph state can be replaced cleanly
- [ ] graph stats can be computed
- [ ] required SQLite indexes exist
- [ ] CLI graph inspection commands work
- [ ] tests pass
- [ ] no LSP enrichment exists
- [ ] no plan risk engine exists
- [ ] no MCP server exists


Do not mark phase 4 done until every box above is true.


***


## Required Execution Order


Implement in this order and do not skip ahead:


- [ ] Step 1 add or verify indexes
- [ ] Step 2 node row mapping
- [ ] Step 3 edge row mapping
- [ ] Step 4 node upsert
- [ ] Step 5 bulk node upsert
- [ ] Step 6 node read helpers
- [ ] Step 7 delete nodes for file
- [ ] Step 8 edge upsert
- [ ] Step 9 bulk edge upsert
- [ ] Step 10 edge read helpers
- [ ] Step 11 delete edges for file
- [ ] Step 12 replace file graph
- [ ] Step 13 graph read query layer
- [ ] Step 14 optional filters module
- [ ] Step 15 CLI inspection commands
- [ ] Step 16 placeholder target handling
- [ ] Step 17 tests
- [ ] Step 18 end-to-end fixture validation
- [ ] Step 19 final verification


***


## Phase 4 Done Definition


Phase 4 is complete only when all of these are true:


- [ ] phase 1, phase 2, phase 3, and phase 03b contracts remain intact
- [ ] graph persistence is deterministic
- [ ] graph retrieval is deterministic
- [ ] structural and lexical parent relationships are both preserved correctly
- [ ] file-level graph replacement removes stale file-owned graph state
- [ ] placeholder edge targets remain explicit and do not break queries
- [ ] graph state can be inspected from CLI
- [ ] tests pass
- [ ] no out-of-scope features were added
```

## Blunt notes

A few important fixes were made here:

- added `scope` and `lexical_parent_id` to node schema
- added index on `lexical_parent_id`
- split structural vs lexical parent queries
- fixed callable stats to include `local_function` and `local_async_function`
- added ambiguity handling for `qualified_name` lookups
- added tests for lexical children and local callable stats

One subtle but important point: after 03b, `get_node_by_qualified_name` is no longer guaranteed to be unique unless your upstream symbol ID and duplicate-name policy make it so. So this checklist now forces deterministic ambiguity handling instead of silent guessing.

