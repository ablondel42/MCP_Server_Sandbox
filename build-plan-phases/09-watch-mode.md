```md
# 09-watch-mode.md

## Purpose

This phase adds watch mode.

Watch mode keeps the repository graph fresh while the codebase changes, without requiring a full manual rescan and reindex every time. It listens for filesystem changes, determines what changed, and refreshes only the affected graph state.

In plain English:

- files change
- watch mode notices
- the system rescans only what matters
- AST structure is refreshed
- reference data is refreshed when needed
- the graph stays usable without full rebuilds every time

This phase is about freshness and developer workflow speed.

---

## Why this phase matters

Without watch mode, the system becomes stale fast during active development.

That causes obvious problems:

- symbol context becomes outdated
- reference counts drift
- risk analysis becomes less trustworthy
- the agent may reason over old graph state
- the user has to keep triggering manual refreshes

A manual reindex command is still useful, but it is a bad primary workflow once the system is actually used during coding.

Watch mode is the layer that makes the system feel alive.

---

## Phase goals

By the end of this phase, you should have:

- a filesystem watcher for repository changes
- change event normalization
- file create, modify, delete handling
- selective rescanning of changed files
- selective AST re-extraction
- graph replacement for affected files
- cleanup for deleted files
- optional targeted reference invalidation or refresh
- freshness tracking updates
- a CLI command to run watch mode
- tests for file-event handling and incremental refresh behavior

---

## Phase non-goals

Do **not** do any of this in phase 9:

- building a distributed indexing service
- watching multiple repos with a huge orchestration layer
- adding a UI dashboard
- implementing perfect semantic dependency invalidation
- fully automatic global LSP refresh on every keystroke

This phase is local incremental freshness, not infrastructure theater.

---

## What already exists from previous phases

This phase assumes you already have:

- repo scanning
- AST extraction
- graph storage with file replacement
- context assembly
- LSP reference enrichment
- risk engine
- MCP tool exposure

Watch mode sits on top of those layers.
It orchestrates them.
It should not duplicate them.

---

## Core idea

Watch mode should observe filesystem changes and trigger the smallest reasonable graph update.

For each relevant event:

- identify which file changed
- determine if the file is supported
- rescan metadata
- re-extract AST structure
- replace graph state for that file
- invalidate or refresh affected reference data
- update freshness metadata

That is the whole job.

---

## Recommended package structure additions

Add these files:

```text
src/
  repo_context/
    indexing/
      __init__.py
      watch.py
      events.py
      incremental.py
      invalidation.py
      scheduler.py
```

### Why this split

- `watch.py`: filesystem watcher setup
- `events.py`: normalize raw file events
- `incremental.py`: changed-file reindex flow
- `invalidation.py`: reference invalidation rules
- `scheduler.py`: debounce and batch behavior

This keeps the watch layer from turning into one giant unstable loop.

---

## Watch mode design principles

### Principle 1: Incremental by default

Do not full-reindex the whole repo for one file save unless you truly have no better option.

### Principle 2: Debounce noisy events

Editors often generate multiple save-related events.
You need batching and debounce, or watch mode will thrash.

### Principle 3: File-level replacement is the main primitive

The graph already supports replacing one file’s nodes and edges.
Use that.
Do not invent a new mutation model.

### Principle 4: Reference freshness should be explicit

You do not need to fully recompute all references after every save.
You do need to know what became stale.

### Principle 5: Deletion must be handled cleanly

Deleted files should not leave dead nodes and edges behind.

---

## Change types to handle

At minimum, watch mode should support:

- file created
- file modified
- file deleted
- optionally file moved or renamed

### Practical truth

Rename events are often messy across operating systems and tools.
For v1, it is totally acceptable to model a rename as:
- delete old path
- create new path

That is simpler and good enough.

---

## Supported file policy

Only react to supported source files.

For v1:
- `.py` files

Ignore:
- temp files
- editor swap files
- unsupported extensions
- ignored directories like `.git`, `.venv`, `node_modules`

The same filtering rules from repo scanning should apply here.
Do not create a second ignore system.

---

## Event normalization

Raw watcher libraries often emit noisy, inconsistent event objects.

Create a normalized event shape in `events.py`.

Recommended shape:

```python
from dataclasses import dataclass
from typing import Literal, Optional

@dataclass
class FileChangeEvent:
    event_type: Literal["created", "modified", "deleted"]
    absolute_path: str
    repo_relative_path: str
    is_supported: bool
    old_absolute_path: Optional[str] = None
```

### Why this matters

The rest of your pipeline should not care about watcher-library weirdness.

---

## Recommended watcher library approach

Use a cheap and common local library for filesystem watching.

Good practical options include:
- `watchdog`
- polling fallback if needed

My blunt recommendation:
- start with `watchdog`
- only add fallback complexity if it is actually needed

This is a solo-dev project.
Do not overengineer platform support on day 1.

---

## Debounce and batching

This phase absolutely needs debounce.

Editors often trigger multiple events for one save.
Without debounce:
- you reindex the same file repeatedly
- the LSP layer gets hammered
- CPU waste increases
- the graph may churn unnecessarily

### Recommended debounce behavior

- collect changed file paths for a short window, such as `250ms` to `1000ms`
- batch them
- process each file once per batch

### Why batching matters

If a save triggers:
- file write
- temp file swap
- metadata update

You still want one reindex action, not three.

---

## Incremental reindex responsibilities

Create `incremental.py`.

Recommended function:

```python
def reindex_changed_file(conn, repo_root, absolute_path, config) -> dict:
    ...
```

### What it should do for created or modified files

1. confirm the file still exists
2. confirm it is supported
3. rebuild or upsert the `FileRecord`
4. parse AST
5. extract nodes and structural edges
6. replace stored file graph
7. mark reference freshness as stale for impacted targets
8. return a summary

### Example summary

```json
{
  "file_path": "app/services/auth.py",
  "status": "reindexed",
  "node_count": 4,
  "edge_count": 6
}
```

---

## Deleted file handling

Deleted files need a separate path.

Create a helper like:

```python
def handle_deleted_file(conn, repo_id: str, repo_relative_path: str) -> dict:
    ...
```

### What it should do

1. find the stored file record
2. delete edges owned by that file
3. delete nodes owned by that file
4. delete the file record
5. invalidate references pointing to symbols that no longer exist if needed
6. return a summary

### Why this matters

If you skip deletion handling, the graph becomes trash quickly.

---

## Reference invalidation strategy

This is the tricky part.

When a file changes, some reference edges may become stale even if they were not directly stored under that changed file. For example:
- a changed caller file may alter outgoing references
- a changed declaration file may affect incoming references to its symbols

You do not need perfect invalidation in v1.
You do need an honest policy.

---

## Two valid reference policies

## Option A: mark references stale, refresh on demand

When a file changes:
- invalidate reference freshness for symbols in that file
- optionally invalidate symbols that previously referenced them
- do not immediately call LSP

Pros:
- cheap
- simpler
- avoids hammering the language server

Cons:
- first later request may need refresh

## Option B: immediately refresh references for affected symbols

When a file changes:
- refresh references right away for touched symbols

Pros:
- graph stays fresher automatically

Cons:
- can be expensive and noisy during active editing

My blunt recommendation:
- use Option A for v1
- mark stale and refresh on demand through explicit tools or later idle-time refresh

That is the safer cheap solution.

---

## Freshness invalidation rules

Create `invalidation.py`.

Recommended helpers:

```python
def mark_symbols_in_file_stale(conn, file_id: str) -> None:
    ...

def invalidate_reference_summaries_for_file(conn, file_id: str) -> None:
    ...

def collect_impacted_symbol_ids(conn, file_id: str) -> list[str]:
    ...
```

### Good enough v1 rule

When a file changes:
- symbols in that file become freshly reindexed structurally
- any stored reference summaries involving those symbols should be considered stale until refreshed
- any `references` edges with evidence in that file should be removed and recomputed later

That is honest and practical.

---

## `references` cleanup policy

For changed files, at minimum you should remove:
- `references` edges whose `evidence_file_id` equals the changed file

### Why

If the changed file contains callers, those reference edges are probably stale.

### Optional additional invalidation

If the changed file contains declarations for target symbols:
- you may also remove `references` edges where `to_id` is one of those symbol IDs

This is more aggressive and often safer.

### Practical recommendation

For v1:
- remove `references` edges with `evidence_file_id = changed_file_id`
- mark reference data for symbols declared in the changed file as stale
- refresh later on demand

That is a good balance.

---

## File create flow

When a new supported file appears:

1. create or upsert `FileRecord`
2. AST-parse and extract graph data
3. replace file graph
4. mark relevant reference state stale
5. optionally log summary

### Important note

A new file may introduce:
- new declarations
- new callers
- new imports
- new inheritance edges

So creation is not just metadata insertion.

---

## File modify flow

When an existing supported file changes:

1. update `FileRecord` metadata and hash
2. remove stale `references` edges with evidence in that file
3. re-extract AST nodes and structural edges
4. replace file graph
5. mark related reference state stale
6. optionally schedule later reference refresh

This is the main path watch mode will hit.

---

## File delete flow

When a tracked supported file is deleted:

1. remove stale `references` edges with evidence in that file
2. collect symbol IDs declared in that file
3. remove edges targeting or sourced from now-deleted nodes if needed
4. delete file-owned nodes
5. delete file record
6. mark any affected summaries stale

### Important truth

Deletion is the place where lazy cleanup causes the most damage.
Be explicit and strict here.

---

## Suggested `scheduler.py` behavior

You want a tiny queue and debounce layer.

Recommended responsibilities:

- accept normalized file events
- deduplicate by path
- collapse multiple modify events into one work item
- process sequentially or in small batches
- avoid concurrent writes to the same repo DB

### Why this matters

SQLite plus multiple overlapping writes plus noisy watcher events is how you create stupid bugs.

For v1:
- one worker
- one repo
- sequential processing

That is totally fine.

---

## Example watch loop shape

```python
def run_watch_mode(repo_root, conn, config):
    scheduler = EventScheduler(debounce_ms=500)

    for raw_event in watch_filesystem(repo_root):
        event = normalize_event(raw_event, repo_root, config)
        if event is None or not event.is_supported:
            continue

        scheduler.submit(event)

        for batch in scheduler.ready_batches():
            process_event_batch(conn, repo_root, batch, config)
```

This is enough conceptually.
Do not make the loop fancy.

---

## Batch processing strategy

Create one batch processor.

Recommended helper:

```python
def process_event_batch(conn, repo_root, events: list[FileChangeEvent], config) -> list[dict]:
    ...
```

### Good behavior

- merge events by repo-relative path
- if both create and modify appear, treat as modify/create final state
- if delete is the latest event, handle as delete
- process each final path once

### Why this matters

You want final-state behavior, not event-history worship.

---

## Suggested event collapse rules

For one file path inside a batch:

- latest `deleted` wins over previous modify/create
- `created` followed by `modified` becomes one create/modify handling path
- repeated `modified` becomes one modified event

Keep the rules tiny and deterministic.

---

## Database transaction strategy

For each changed file:
- use one transaction per file update

Why:
- file-level replacement is already a clean unit of work
- easier rollback on parse failures
- easier debugging

For a batch:
- do not put the whole batch in one giant transaction unless you truly need that

That just makes rollback painful.

---

## Parse failure policy in watch mode

Files may be temporarily invalid during active editing.

You need a policy.

## Recommended v1 policy

If AST parsing fails for a modified file:

- keep the previous valid graph state for that file
- mark the file as having a parse error or stale state
- do not replace valid graph data with broken partial data
- surface the failure in logs or status

### Why this is the right call

During live editing, temporary syntax errors are normal.
Destroying previously valid graph state every time the user types a broken line would be dumb.

This is one of the few places where “do not replace on failure” is better than strict replacement.

---

## Parse error tracking

You may want a small table for indexing or watch errors.

Optional table:

```sql
CREATE TABLE IF NOT EXISTS file_errors (
  file_id TEXT NOT NULL,
  error_type TEXT NOT NULL,
  message TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (file_id, error_type)
);
```

### Why this is useful

It lets you record:
- syntax errors
- unreadable files
- temporary extraction failures

This is optional but smart.

---

## CLI additions for this phase

Add a command like:

```text
repo-context watch <repo-root>
```

### What it should do

- start the watcher
- print small incremental summaries
- keep running until stopped

### Optional flags

- `--debounce-ms`
- `--verbose`
- `--no-reference-invalidation`
- `--db-path`

Keep defaults sane.
Do not require too much configuration.

---

## MCP interaction with watch mode

The MCP server and watch mode can coexist in two ways.

## Option A: separate processes

- one watch-mode process updates the graph
- one MCP process serves queries

Pros:
- simple mental model
- less coupling

Cons:
- two processes to run

## Option B: integrated watch option in the MCP server

- MCP server starts watch mode too

Pros:
- fewer moving parts for the user

Cons:
- more coupling
- more complexity in the server process

My recommendation:
- start with Option A
- only integrate later if you really want a single process

That is cleaner for v1.

---

## Testing plan

This phase needs event-driven tests.

### `test_modify_event_reindexes_file`

Verify:
- a changed `.py` file updates file metadata
- nodes and structural edges are replaced

### `test_create_event_adds_file`

Verify:
- a new file becomes a `FileRecord`
- AST nodes appear
- graph state is stored

### `test_delete_event_removes_file_graph`

Verify:
- file record is removed
- nodes for the file are removed
- edges owned by the file are removed

### `test_ignored_file_event_is_skipped`

Verify:
- ignored directories and unsupported files do not trigger indexing

### `test_event_batch_deduplicates_paths`

Verify:
- multiple modify events collapse into one effective operation

### `test_reference_edges_for_changed_file_are_invalidated`

Verify:
- `references` edges with `evidence_file_id` matching changed file are removed

### `test_parse_failure_keeps_previous_graph_state`

Verify:
- broken temporary code does not erase previous valid graph state

### `test_rename_behaves_as_delete_plus_create`

If you support rename normalization, verify final behavior.

---

## Suggested fixture strategy

Use temporary directories in tests.

A good test flow is:

1. create a small repo fixture
2. run initial scan and index
3. mutate a file
4. emit normalized event
5. run batch processor
6. assert graph changes

This is much easier to trust than mocking everything.

---

## Acceptance checklist

Phase 9 is done when all of this is true:

- The watcher can observe supported file changes.
- Events are normalized into a stable internal shape.
- Debounce and path deduplication exist.
- File create events add file and graph state.
- File modify events update file and graph state.
- File delete events cleanly remove file and graph state.
- `references` edges for changed files are invalidated.
- Staleness is tracked honestly after changes.
- Temporary parse failures do not destroy last valid graph state.
- CLI watch mode runs.
- Tests pass.

---

## Common mistakes to avoid

### Mistake 1: Reindexing the whole repo for every save

That defeats the point of watch mode.

### Mistake 2: Trusting raw watcher events directly

Normalize and debounce them first.

### Mistake 3: Deleting valid graph state on temporary syntax errors

That makes watch mode miserable during real editing.

### Mistake 4: Forgetting reference invalidation

Structural graph refresh alone is not enough once references exist.

### Mistake 5: Running many overlapping DB writes

Keep processing sequential for v1.
SQLite likes boring.

### Mistake 6: Building a huge distributed architecture for local watching

That is pure overkill here.

---

## What phase 10 will likely add

Once watch mode exists, the next useful phase is usually one of these:

- a plan-oriented MCP workflow tool
- approval-aware agent integration
- stale-context coordination between watch mode and MCP tools
- richer incremental reference refresh behavior

That depends on how far you want the workflow automation to go.

---

## Final guidance

This phase is mostly orchestration discipline.

The individual building blocks already exist.
Watch mode just connects them into a live update loop.

Keep it simple:

- watch files
- debounce noise
- reindex changed files
- delete removed files
- invalidate stale references
- preserve last valid state when parsing fails

That is enough to make the system feel alive without making it fragile.
```