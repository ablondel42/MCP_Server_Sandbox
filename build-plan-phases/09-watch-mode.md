# 09 Watch Mode - Exact Implementation Checklist


## Objective


Implement phase 9 of the repository indexing pipeline.


Phase 9 must keep the repository graph fresh during active development by watching filesystem changes and performing the smallest reasonable incremental update.


Phase 9 must provide:
- filesystem watching for repository changes
- normalized change events
- debounce and path deduplication
- file create handling
- file modify handling
- file delete handling
- incremental file reindexing
- graph replacement for changed files
- cleanup for deleted files
- reference invalidation
- CLI watch mode
- tests for event handling and incremental refresh
- compatibility with nested-scope graph state from phase 03b
- compatibility with explicit reference availability state from phase 6


Phase 9 must not provide:
- distributed indexing infrastructure
- multi-repo orchestration complexity
- UI dashboard work
- perfect semantic dependency invalidation
- full global LSP refresh on every save


***


## Consistency Rules


These rules are mandatory.


- [ ] Reuse the existing phase 1 through phase 8 models, repo scanning rules, AST extraction pipeline, graph replacement helpers, reference logic, and CLI style.
- [ ] Reuse the same supported-file and ignored-path rules already used by repo scanning.
- [ ] Reuse file-level graph replacement as the main persistence primitive.
- [ ] Keep watch mode orchestration separate from AST extraction logic.
- [ ] Keep watch mode orchestration separate from MCP server logic.
- [ ] Keep writes sequential for v1.
- [ ] Keep reference invalidation explicit.
- [ ] Keep parse-failure behavior conservative.
- [ ] Keep event normalization deterministic.
- [ ] Keep batch collapse rules tiny and explicit.
- [ ] Preserve structural graph truth and nested-scope graph truth together when a file is reindexed.
- [ ] Preserve the explicit distinction between unavailable references and zero references after invalidation.


Filesystem watcher libraries commonly emit duplicate or bursty modify/create events for a single user save, so debounce and batch collapse are not optional polish here. [web:752][web:753][web:754][web:759]


***


## Required Inputs


Phase 9 must consume these existing inputs:


- [ ] repo root path
- [ ] app config and ignore rules
- [ ] file scanning helpers or file metadata builders
- [ ] phase 3 and phase 03b AST extraction pipeline
- [ ] phase 4 graph replacement helpers
- [ ] phase 6 reference edge storage and invalidation helpers
- [ ] existing DB access layer


Do not create a second indexing pipeline for watch mode.


***


## Required Outputs


Phase 9 must produce these capabilities:


- [ ] watch one repository for file changes
- [ ] normalize raw watcher events into one internal event shape
- [ ] ignore unsupported and ignored-path events
- [ ] debounce noisy events
- [ ] deduplicate changed paths per batch
- [ ] incrementally reindex created files
- [ ] incrementally reindex modified files
- [ ] cleanly remove deleted files
- [ ] invalidate stale reference state for changed files
- [ ] preserve previous valid graph state on temporary parse failure
- [ ] expose a CLI watch command


Do not make watch mode responsible for plan evaluation or MCP orchestration.


***


## Required File Layout


Create or extend these files:


- [ ] `src/repo_context/indexing/__init__.py`
- [ ] `src/repo_context/indexing/watch.py`
- [ ] `src/repo_context/indexing/events.py`
- [ ] `src/repo_context/indexing/incremental.py`
- [ ] `src/repo_context/indexing/invalidation.py`
- [ ] `src/repo_context/indexing/scheduler.py`


Reuse existing files if they already exist.


Do not collapse the whole watch loop into one file.


***


## Supported File Policy


Apply these rules exactly.


- [ ] only react to supported source files
- [ ] for v1, supported source files are `.py` files
- [ ] ignore unsupported extensions
- [ ] ignore temp files
- [ ] ignore swap files
- [ ] ignore ignored directories such as `.git`, `.venv`, and `node_modules`
- [ ] use the same ignore rules as repo scanning
- [ ] do not create a second inconsistent ignore system


No event for an ignored or unsupported file may trigger indexing.


***


## Event Model


Use one normalized internal event shape.


### Required normalized event fields


- [ ] `event_type`
- [ ] `absolute_path`
- [ ] `repo_relative_path`
- [ ] `is_supported`
- [ ] optional `old_absolute_path`
- [ ] optional `old_repo_relative_path`


### Allowed `event_type` values


- [ ] `created`
- [ ] `modified`
- [ ] `deleted`


### Rename rule


- [ ] rename support is optional in v1
- [ ] if rename is handled, model it as delete old path plus create new path
- [ ] do not attempt cross-platform perfect rename semantics


### Important rule


Do not leak watcher-library-specific event classes outside normalization.


***


## Step 1 - Watcher Setup


### File


- [ ] `src/repo_context/indexing/watch.py`


### Implement


Add watcher setup for one local repository.


### Required behavior


- [ ] watch the repo root recursively
- [ ] receive raw file events
- [ ] pass raw events into event normalization
- [ ] skip unsupported or ignored paths
- [ ] feed normalized events into the scheduler
- [ ] process scheduler batches


### Library recommendation rule


- [ ] use `watchdog` for v1 unless the project already chose another local watcher library
- [ ] do not add polling fallback complexity unless actually needed


### Do not do


- [ ] do not implement multi-repo watching in v1
- [ ] do not process raw watcher events directly without normalization


### Done when


- [ ] the project can observe local repository file changes and route them into the incremental pipeline


***


## Step 2 - Event Normalization


### File


- [ ] `src/repo_context/indexing/events.py`


### Implement


- [ ] `FileChangeEvent`
- [ ] `normalize_event(raw_event, repo_root, config)`


### Exact behavior


- [ ] convert watcher-specific event objects into the internal event shape
- [ ] compute `repo_relative_path`
- [ ] compute `is_supported`
- [ ] return `None` for ignored or unusable events
- [ ] normalize create events to `created`
- [ ] normalize modify events to `modified`
- [ ] normalize delete events to `deleted`


### Rename handling rule


- [ ] if the watcher library exposes moves and you choose to support them, normalize them as:
  - [ ] one delete event for old path
  - [ ] one create event for new path
- [ ] otherwise ignore move-specific richness in v1


### Do not do


- [ ] do not leak watcher-library event types outside this module
- [ ] do not trust editor temp-file noise as meaningful source changes


### Done when


- [ ] the rest of the system sees one stable event shape only


***


## Step 3 - Scheduler and Debounce


### File


- [ ] `src/repo_context/indexing/scheduler.py`


### Implement


Add a tiny sequential debounce and batching scheduler.


### Required responsibilities


- [ ] accept normalized events
- [ ] deduplicate by repo-relative path
- [ ] batch events within a debounce window
- [ ] emit ready batches for processing
- [ ] avoid overlapping writes for the same repo


### Required debounce rule


- [ ] default debounce window must be configurable
- [ ] recommended default range is `250ms` to `1000ms`
- [ ] process each path at most once per batch


### Required processing rule


- [ ] one worker only in v1
- [ ] sequential batch handling only in v1


### Do not do


- [ ] do not allow concurrent DB writes for the same repo in v1
- [ ] do not process one raw modify burst as many separate file reindexes


### Done when


- [ ] noisy save events collapse into one stable work unit per file path


***


## Step 4 - Event Collapse Rules


### File


- [ ] `src/repo_context/indexing/scheduler.py` or a helper in `events.py`


### Implement


Add deterministic final-state event collapse for one path inside a batch.


### Exact collapse rules


- [ ] repeated `modified` events collapse to one `modified`
- [ ] `created` followed by `modified` collapses to one effective create-or-modify processing path
- [ ] latest `deleted` wins over earlier create or modify events in the same batch
- [ ] one final path must be processed once per batch


### Do not do


- [ ] do not preserve noisy event history if final file state is enough
- [ ] do not make collapse rules implicit


### Done when


- [ ] each batch produces one deterministic final action per affected path


***


## Step 5 - Incremental Reindex for Changed File


### File


- [ ] `src/repo_context/indexing/incremental.py`


### Implement


- [ ] `reindex_changed_file(conn, repo_root, absolute_path, config)`


### Exact behavior for created or modified files


- [ ] confirm the file currently exists
- [ ] confirm the file is supported
- [ ] rebuild or upsert the `FileRecord`
- [ ] parse AST using the existing phase 3 and phase 03b pipeline
- [ ] extract nodes and structural edges
- [ ] preserve nested-scope fields and edges from phase 03b
- [ ] replace stored file graph using existing phase 4 helpers
- [ ] invalidate reference state for impacted symbols and file evidence
- [ ] return a structured summary


### Required summary fields


- [ ] `file_path`
- [ ] `status`
- [ ] `node_count`
- [ ] `edge_count`
- [ ] `invalidated_reference_edge_count` when available


### Allowed `status` values


- [ ] `reindexed`
- [ ] `skipped`
- [ ] `parse_failed`
- [ ] `error`


### Do not do


- [ ] do not full-reindex the entire repo for one file save
- [ ] do not bypass existing extraction and graph replacement helpers


### Done when


- [ ] one changed file can be incrementally reindexed and replace its graph state cleanly


***


## Step 6 - Deleted File Handling


### File


- [ ] `src/repo_context/indexing/incremental.py`


### Implement


- [ ] `handle_deleted_file(conn, repo_id, repo_relative_path)`


### Exact behavior


- [ ] find the stored file record by repo and relative path
- [ ] if no file record exists, return a deterministic no-op summary
- [ ] remove `references` edges whose `evidence_file_id` is that file ID
- [ ] collect symbol IDs declared in that file
- [ ] remove edges targeting or sourcing deleted symbols if your graph cleanup layer requires it
- [ ] delete file-owned nodes
- [ ] delete the file record
- [ ] mark affected reference state stale or unavailable explicitly
- [ ] return a structured summary


### Required summary fields


- [ ] `file_path`
- [ ] `status`
- [ ] `deleted_node_count` when available
- [ ] `deleted_edge_count` when available
- [ ] `invalidated_target_symbol_count` when available


### Allowed delete status values


- [ ] `deleted`
- [ ] `not_tracked`
- [ ] `error`


### Do not do


- [ ] do not leave dead file records behind
- [ ] do not leave obvious file-owned graph junk behind


### Done when


- [ ] deleting a tracked file removes its graph state cleanly


***


## Step 7 - Reference Invalidation Helpers


### File


- [ ] `src/repo_context/indexing/invalidation.py`


### Implement


- [ ] `mark_symbols_in_file_stale(conn, file_id)`
- [ ] `invalidate_reference_summaries_for_file(conn, file_id)`
- [ ] `collect_impacted_symbol_ids(conn, file_id)`


### Minimum v1 behavior


When a file changes:


- [ ] symbols declared in that file must be treated as structurally refreshed
- [ ] stored `references` edges whose `evidence_file_id = file_id` must be removed
- [ ] reference summary availability for symbols declared in that file must be marked stale or unavailable until refreshed again
- [ ] impacted symbol IDs must be collectable deterministically


### Required phase 6 compatibility rule


- [ ] invalidation must update explicit refresh-state metadata, not just delete edges
- [ ] after invalidation, “unavailable” must remain distinguishable from “known zero references”


### Do not do


- [ ] do not attempt perfect semantic invalidation in v1
- [ ] do not pretend references are still fresh after caller-file edits


### Done when


- [ ] the system has one honest explicit invalidation policy for changed files


***


## Step 8 - Reference Cleanup Policy


### File


- [ ] `src/repo_context/indexing/invalidation.py` or `src/repo_context/indexing/incremental.py`


### Implement


Apply this exact v1 cleanup policy for changed files:


- [ ] remove stored `references` edges where `evidence_file_id = changed_file_id`
- [ ] mark reference data for symbols declared in that file as unavailable or stale
- [ ] do not automatically recompute references during the file reindex path


### Optional stricter behavior


- [ ] optionally also remove `references` edges where `to_id` is a symbol declared in the changed file if you intentionally choose the stricter invalidation path


### Default recommendation


- [ ] use the minimum required policy above unless stricter invalidation is already easy and consistent


### Required clarification


- [ ] if you keep target-directed `references` edges whose evidence lives elsewhere, explicit refresh metadata for those targets must still stay honest
- [ ] do not let old edge presence falsely imply fresh target-level reference truth after declaration-side changes


### Do not do


- [ ] do not silently keep caller-side reference edges that are now probably stale
- [ ] do not auto-trigger expensive LSP refresh on every save in v1


### Done when


- [ ] references are invalidated honestly and cheaply during watch mode


***


## Step 9 - Parse Failure Policy


### File


- [ ] `src/repo_context/indexing/incremental.py`


### Implement


Apply this exact policy for temporary parse failures on changed files.


### Exact behavior


If AST parsing fails for a modified or created file:


- [ ] keep the previous valid graph state for that file unchanged
- [ ] do not replace valid nodes and edges with partial or empty state
- [ ] record the parse failure in logs or status output
- [ ] optionally persist file error state if the project already supports it
- [ ] return a summary with `status = "parse_failed"`


### Required reference policy on parse failure


- [ ] do not invalidate previously valid graph state just because the current edit is temporarily broken
- [ ] do not claim the file was successfully refreshed
- [ ] if you track file parse error state, keep it separate from graph truth


### Do not do


- [ ] do not delete valid graph state because the current file contents are temporarily broken
- [ ] do not persist partial broken AST output


### Done when


- [ ] temporary syntax errors during editing do not destroy the last known valid graph state


***


## Step 10 - Optional File Error Tracking


### Files to modify


- [ ] migrations or DB init, only if you intentionally support persistent file error tracking
- [ ] related storage helpers if added


### Optional implement


- [ ] `file_errors` table
- [ ] helpers to upsert and clear file parse errors


### Required rule


- [ ] this is optional in phase 9
- [ ] if added, it must stay small and deterministic


### Do not do


- [ ] do not block watch mode on this optional table
- [ ] do not create a large diagnostics subsystem here


### Done when


- [ ] parse failures can optionally be persisted without expanding scope too much


***


## Step 11 - Batch Processor


### File


- [ ] `src/repo_context/indexing/watch.py` or `src/repo_context/indexing/incremental.py`


### Implement


- [ ] `process_event_batch(conn, repo_root, events, config)`


### Exact behavior


- [ ] merge events by repo-relative path
- [ ] collapse each path to one final effective action
- [ ] for each final action:
  - [ ] if final state is delete, run deleted-file flow
  - [ ] otherwise run changed-file reindex flow
- [ ] process one file at a time
- [ ] return a list of structured per-file summaries


### Do not do


- [ ] do not wrap the whole batch in one giant transaction
- [ ] do not process the same path multiple times in one batch


### Done when


- [ ] one batch produces one deterministic incremental indexing result per affected file


***


## Step 12 - Transaction Rules


### Files to verify


- [ ] `src/repo_context/indexing/incremental.py`
- [ ] graph replacement helpers from earlier phases


### Implement


Apply these exact transaction rules:


- [ ] use one transaction per changed file update
- [ ] use one transaction per deleted file cleanup
- [ ] rollback a file update cleanly on failure
- [ ] do not let one file failure destroy the whole batch


### Do not do


- [ ] do not use one giant transaction for a noisy batch
- [ ] do not leave half-updated file graph state


### Done when


- [ ] file-level work is isolated, debuggable, and rollback-safe


***


## Step 13 - CLI Watch Command


### Files to modify


- [ ] existing CLI module from earlier phases


### Implement


Add:


- [ ] `repo-context watch <repo-root>`


### Optional flags


- [ ] `--debounce-ms`
- [ ] `--verbose`
- [ ] `--no-reference-invalidation`
- [ ] `--db-path`


### Required behavior


- [ ] start watcher
- [ ] print small incremental summaries
- [ ] keep running until stopped
- [ ] fail clearly on startup errors


### Do not do


- [ ] do not hide watch mode under unrelated commands
- [ ] do not require excessive configuration for normal use


### Done when


- [ ] watch mode can be launched from CLI and stay running as a local dev workflow tool


***


## Step 14 - MCP Coexistence Policy


### Files to verify


- [ ] watch mode docs or CLI help text
- [ ] server startup conventions if relevant


### Implement


Use this v1 coexistence policy:


- [ ] watch mode runs as a separate process from the MCP server by default
- [ ] do not tightly integrate watch mode into MCP server startup in v1
- [ ] if both operate on the same SQLite DB, document the single-writer expectation clearly


### Do not do


- [ ] do not couple file watching directly into the MCP server lifecycle yet
- [ ] do not require MCP to be running for watch mode to work
- [ ] do not imply safe concurrent writers if the current storage layer is not designed for it


### Done when


- [ ] watch mode remains a clean local updater instead of inflating server complexity


***


## Step 15 - Tests


### Files to create or modify


- [ ] phase 9 tests under `tests/`


### Test strategy


- [ ] prefer temp directories and real small file mutations over excessive mocking
- [ ] test normalized events, batch collapse, incremental indexing, deletion, invalidation, and parse failure behavior


### Implement these tests


- [ ] `test_modify_event_reindexes_file`
- [ ] `test_create_event_adds_file`
- [ ] `test_delete_event_removes_file_graph`
- [ ] `test_ignored_file_event_is_skipped`
- [ ] `test_event_batch_deduplicates_paths`
- [ ] `test_reference_edges_for_changed_file_are_invalidated`
- [ ] `test_reference_availability_becomes_unavailable_after_invalidation`
- [ ] `test_parse_failure_keeps_previous_graph_state`
- [ ] `test_rename_behaves_as_delete_plus_create` if rename normalization is supported


### Exact test assertions


#### `test_modify_event_reindexes_file`
- [ ] changed `.py` file updates file metadata
- [ ] stored nodes for the file are replaced
- [ ] stored structural edges for the file are replaced
- [ ] nested-scope symbol fields remain persisted after reindex


#### `test_create_event_adds_file`
- [ ] new supported file creates or upserts file record
- [ ] AST nodes appear
- [ ] graph state is stored


#### `test_delete_event_removes_file_graph`
- [ ] file record is removed
- [ ] file-owned nodes are removed
- [ ] file-owned edges are removed


#### `test_ignored_file_event_is_skipped`
- [ ] ignored directories do not trigger indexing
- [ ] unsupported files do not trigger indexing


#### `test_event_batch_deduplicates_paths`
- [ ] repeated events for same path collapse to one effective operation


#### `test_reference_edges_for_changed_file_are_invalidated`
- [ ] `references` edges with matching `evidence_file_id` are removed


#### `test_reference_availability_becomes_unavailable_after_invalidation`
- [ ] invalidated symbols do not report fresh zero references
- [ ] explicit availability state changes correctly


#### `test_parse_failure_keeps_previous_graph_state`
- [ ] temporary broken code does not erase previous valid nodes
- [ ] status reports parse failure honestly


#### `test_rename_behaves_as_delete_plus_create`
- [ ] old path graph state is removed
- [ ] new path graph state is added


### Do not do


- [ ] do not rely only on smoke tests
- [ ] do not require a real language server for the whole watch suite


### Done when


- [ ] watch mode behavior is covered by deterministic incremental tests


***


## Step 16 - Final Verification


Before marking phase 9 complete, verify all of the following:


- [ ] the watcher can observe supported file changes
- [ ] events are normalized into a stable internal shape
- [ ] debounce and path deduplication exist
- [ ] file create events add file and graph state
- [ ] file modify events update file and graph state
- [ ] file delete events cleanly remove file and graph state
- [ ] nested-scope graph data survives incremental reindex
- [ ] `references` edges for changed files are invalidated
- [ ] reference availability state becomes honest after invalidation
- [ ] staleness is tracked honestly after changes
- [ ] temporary parse failures do not destroy last valid graph state
- [ ] CLI watch mode runs
- [ ] tests pass


Do not mark phase 9 done until every box above is true.


***


## Required Execution Order


Implement in this order and do not skip ahead:


- [ ] Step 1 watcher setup
- [ ] Step 2 event normalization
- [ ] Step 3 scheduler and debounce
- [ ] Step 4 event collapse rules
- [ ] Step 5 incremental reindex for changed file
- [ ] Step 6 deleted file handling
- [ ] Step 7 reference invalidation helpers
- [ ] Step 8 reference cleanup policy
- [ ] Step 9 parse failure policy
- [ ] Step 10 optional file error tracking
- [ ] Step 11 batch processor
- [ ] Step 12 transaction rules
- [ ] Step 13 CLI watch command
- [ ] Step 14 MCP coexistence policy
- [ ] Step 15 tests
- [ ] Step 16 final verification


***


## Phase 9 Done Definition


Phase 9 is complete only when all of these are true:


- [ ] phase 1 through phase 8 contracts remain intact
- [ ] watch mode is incremental by default
- [ ] event handling is normalized and debounced
- [ ] file graph replacement is reused as the core write primitive
- [ ] nested-scope graph truth remains intact after reindex
- [ ] reference invalidation is honest
- [ ] unavailable references remain distinct from zero references
- [ ] parse failures preserve last valid graph state
- [ ] watch mode remains separate from MCP server lifecycle by default
- [ ] tests pass
