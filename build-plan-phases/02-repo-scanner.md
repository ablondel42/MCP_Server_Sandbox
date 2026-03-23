```md
# 02-repo-scanner.md

## Purpose

This phase builds the repository scanner.

Its job is simple:

- walk a repository from a known root
- find supported source files
- ignore junk and irrelevant directories
- derive stable file metadata
- persist file records to SQLite

This phase does **not** parse Python AST yet.
It does **not** extract symbols yet.
It does **not** call LSP yet.

The scanner is the inventory layer.
If the inventory is wrong, the graph will be wrong later.

---

## Why this phase matters

The scanner decides what the system even sees.

If it misses files:
- symbols go missing
- references later become incomplete
- risk evaluation becomes misleading

If it includes garbage:
- indexing gets slower
- the graph gets noisy
- later phases waste effort on junk

So this phase is about producing a clean, deterministic, repeatable file inventory.

---

## Phase goals

By the end of this phase, you should have:

- a repository scanner that walks from a repo root
- directory filtering and ignore handling
- support for Python files only
- stable repo-relative file paths
- LSP-friendly file URIs
- Python module path derivation
- file hashing
- file size collection
- last modified time collection
- persistence of `RepoRecord` and `FileRecord`
- a CLI command to scan and register files
- tests for scanner behavior

---

## Phase non-goals

Do **not** do any of this in phase 2:

- AST parsing
- symbol extraction
- import extraction
- class extraction
- function extraction
- LSP requests
- graph edge creation
- risk scoring
- MCP server work

This phase is only about files and repository metadata.

---

## What already exists from phase 1

This phase assumes phase 1 already gives you:

- project structure
- config
- core models
- SQLite bootstrap
- CLI shell
- serialization helpers
- base tests

If phase 1 is weak, fix it first.

---

## Scanner responsibilities

The repository scanner should do exactly these things:

1. Accept a repository root path.
2. Validate that the path exists and is a directory.
3. Walk the directory tree.
4. Ignore unwanted directories.
5. Keep only supported source files.
6. Compute file metadata.
7. Derive a stable module path.
8. Build `FileRecord` values.
9. Persist them.
10. Optionally register or update the `RepoRecord`.

That is enough.
Do not make the scanner smart in other ways.

---

## Design principles

### Principle 1: Deterministic output

Scanning the same repository twice without file changes should produce the same file inventory.

### Principle 2: Repo-relative identity

Internally, files should be identified by repo-relative paths, not arbitrary absolute paths.

### Principle 3: Cheap metadata now, deeper parsing later

The scanner should not try to understand code.
It should only collect file facts.

### Principle 4: Honest filtering

If a file is ignored, it should be ignored by a clear rule, not fuzzy logic.

---

## Inputs and outputs

## Input

The scanner takes:

- repository root path
- application config

Optional later:
- a custom ignore list
- a mode such as full scan vs changed-only scan

For this phase, keep it simple and do full scans.

## Output

The scanner should produce:

- one `RepoRecord`
- zero or more `FileRecord` entries
- a scan summary for the CLI

Example summary:

```json
{
  "repo_id": "repo:demo",
  "file_count": 23,
  "ignored_dir_count": 7,
  "supported_extensions": [".py"]
}
```

---

## Recommended package structure for this phase

Add these files:

```text
src/
  repo_context/
    parsing/
      __init__.py
      scanner.py
      pathing.py
      hashing.py
    storage/
      repos.py
      files.py
```

### Why these modules

- `scanner.py`: walking logic and orchestration
- `pathing.py`: path normalization and module-path derivation
- `hashing.py`: content hashing helpers
- `repos.py`: repo persistence helpers
- `files.py`: file persistence helpers

Keep the scanner orchestration separate from persistence logic.

---

## Core behaviors to implement

## Behavior 1: Validate repo root

Before scanning:
- check the path exists
- check it is a directory
- normalize it to a canonical absolute path

If the path is invalid, fail early with a clear error.

### Good rule

Resolve the path once at the start and use the resolved path everywhere.

---

## Behavior 2: Ignore known junk directories

The scanner should skip directories that should never be indexed.

Recommended default ignored directories:

- `.git`
- `.venv`
- `venv`
- `__pycache__`
- `.mypy_cache`
- `.pytest_cache`
- `.ruff_cache`
- `build`
- `dist`
- `node_modules`

You can already keep this list in `config.py`.

### Important rule

Ignore by directory name, not by fuzzy contains-matching.

Bad:
- skip any path containing `build`

Good:
- skip a directory entry whose name is exactly `build`

That avoids weird accidental exclusions.

---

## Behavior 3: Only keep supported source files

For version 1, only keep `.py` files.

That includes:
- regular Python modules
- `__init__.py`

That excludes:
- `.pyc`
- notebooks
- text files
- configs
- generated junk

### Why

The project starts with Python only.
Do not pretend to support more. Keep the inventory aligned with the real scope.

---

## Behavior 4: Derive repo-relative file paths

Every file should be stored using a path relative to the repository root.

Example:

```text
repo root: /workspace/project
absolute:  /workspace/project/app/services/auth.py
stored:    app/services/auth.py
```

### Why this matters

Repo-relative paths are:
- stable inside the repo
- portable between machines
- better for IDs
- easier to display
- easier to map to module paths

Absolute paths should still be available when building file URIs, but they should not be the main stored identity.

---

## Behavior 5: Build file URIs

Each file should have an LSP-compatible URI.

Example:

```text
file:///workspace/project/app/services/auth.py
```

### Why do this now

Even though LSP comes later, storing the URI now avoids future conversion mess.

The scanner is already the right place to establish file identity in all relevant forms:
- repo-relative path
- absolute resolved path
- file URI

---

## Behavior 6: Derive Python module paths

The scanner should derive a module-like path for every Python file.

Examples:

```text
app/services/auth.py        -> app.services.auth
app/models/user.py          -> app.models.user
app/__init__.py             -> app
pkg/subpkg/__init__.py      -> pkg.subpkg
main.py                     -> main
```

### Rule for `__init__.py`

When the file name is `__init__.py`, drop the last `__init__` segment from the module path.

### Why this matters

Module paths will later be used for:
- module nodes
- qualified names
- imports
- graph relationships

So derive them consistently now.

---

## Behavior 7: Compute content hash

The scanner should hash the full file content.

Recommended:
- SHA-256

Example output:

```text
sha256:8d3f...
```

### Why this matters

Later this supports:
- change detection
- incremental indexing
- stale-data checks

Even though phase 2 does not do incremental indexing yet, this field belongs here.

---

## Behavior 8: Record file size and mtime

For each file, collect:

- size in bytes
- last modified time

### Why this matters

This is useful for:
- debugging
- sanity checks
- later update detection

Do not overthink it.
These are cheap metadata fields.

---

## FileRecord contract

This phase should fully populate `FileRecord`.

Recommended dataclass shape:

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class FileRecord:
    id: str
    repo_id: str
    file_path: str
    uri: str
    module_path: str
    language: str
    content_hash: str
    size_bytes: int
    last_modified_at: str
    last_indexed_at: Optional[str] = None
```

### Field generation rules

#### `id`

Recommended format:

```text
file:{repo_relative_path}
```

Example:

```text
file:app/services/auth.py
```

Why:
- simple
- readable
- stable enough inside a repo

If you want stricter uniqueness later, you can namespace by repo ID too.

#### `repo_id`

Should come from the `RepoRecord`.

Example:

```text
repo:demo
```

#### `file_path`

Repository-relative path.

Example:

```text
app/services/auth.py
```

#### `uri`

Resolved file URI.

Example:

```text
file:///workspace/project/app/services/auth.py
```

#### `module_path`

Derived Python module path.

Example:

```text
app.services.auth
```

#### `language`

For now:
```text
python
```

#### `content_hash`

Full-file SHA-256 hash.

#### `size_bytes`

File size from the filesystem.

#### `last_modified_at`

Store as ISO 8601 UTC string if possible.

#### `last_indexed_at`

For now, set to the current scan time or leave null until a full indexing phase uses it more formally.

My recommendation:
- set it during the scan
- be consistent

---

## RepoRecord handling

The scanner should also create or update the repository record.

Recommended shape:

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class RepoRecord:
    id: str
    root_path: str
    name: str
    default_language: str
    created_at: str
    last_indexed_at: Optional[str] = None
```

### Repo ID rule

Keep it simple at first.

Good options:
- `repo:{folder_name}`
- a hash-derived ID from the canonical root path

My blunt recommendation for v1:
- start with `repo:{folder_name}`
- only make it more complex if real collisions appear

Example:

```text
repo:project
```

### Repo name rule

Use the folder name by default.

Example:

```text
project
```

### Root path rule

Store the resolved absolute path.

Example:

```text
/workspace/project
```

---

## Recommended modules and functions

## `parsing/pathing.py`

This file should handle path normalization and module-path derivation.

Recommended functions:

```python
from pathlib import Path

def normalize_repo_root(path: str | Path) -> Path:
    ...

def to_relative_path(repo_root: Path, file_path: Path) -> str:
    ...

def to_file_uri(file_path: Path) -> str:
    ...

def derive_module_path(repo_root: Path, file_path: Path) -> str:
    ...
```

### Expected behavior

#### `normalize_repo_root`
- resolve the path
- validate existence
- validate directory

#### `to_relative_path`
- return a POSIX-style repo-relative path string

#### `to_file_uri`
- return a proper `file://` URI

#### `derive_module_path`
- remove `.py`
- split path into parts
- drop trailing `__init__`
- join with dots

---

## `parsing/hashing.py`

This file should contain content hashing helpers.

Recommended functions:

```python
from pathlib import Path

def sha256_text(text: str) -> str:
    ...

def sha256_file(file_path: Path) -> str:
    ...
```

### Expected behavior

- read file content safely
- hash the bytes
- return a prefixed string like `sha256:...`

Keep it tiny.

---

## `parsing/scanner.py`

This is the main scanner orchestration file.

Recommended responsibilities:

- walk the repo root
- filter ignored dirs
- filter file extensions
- build file metadata
- return `FileRecord` values

Recommended functions:

```python
from pathlib import Path

def should_ignore_dir(name: str, ignored_dirs: tuple[str, ...]) -> bool:
    ...

def is_supported_source_file(path: Path, supported_extensions: tuple[str, ...]) -> bool:
    ...

def scan_repository(repo_root: Path, config) -> tuple[RepoRecord, list[FileRecord]]:
    ...
```

### Important rule

Do not make this file talk directly to SQLite if you can avoid it.
Let it return records, and let a higher layer persist them.

If you want a convenience function that scans and saves, keep it separate.

---

## `storage/repos.py`

This file should own repo persistence.

Recommended functions:

```python
def upsert_repo(conn, repo: RepoRecord) -> None:
    ...

def get_repo_by_id(conn, repo_id: str) -> RepoRecord | None:
    ...
```

---

## `storage/files.py`

This file should own file persistence.

Recommended functions:

```python
def upsert_file(conn, file_record: FileRecord) -> None:
    ...

def upsert_files(conn, file_records: list[FileRecord]) -> None:
    ...

def list_files_for_repo(conn, repo_id: str) -> list[FileRecord]:
    ...
```

### Optional in this phase

You can also add:

```python
def delete_files_not_in_set(conn, repo_id: str, keep_paths: set[str]) -> None:
    ...
```

This is useful if you want the scanner to keep DB state in sync during rescans.
If that feels like too much for phase 2, you can postpone deletion sync until indexing phases.
But it is a reasonable addition here.

---

## Scanner algorithm

Use a simple deterministic algorithm.

### Step 1

Normalize and validate the repo root.

### Step 2

Create or update a `RepoRecord`.

### Step 3

Walk the directory tree using `os.walk` or `Path.rglob`.

My recommendation:
- use `os.walk`
- mutate `dirnames` in place to prune ignored directories early

That is efficient and explicit.

### Step 4

For each candidate file:
- confirm it has `.py`
- resolve absolute path
- derive repo-relative path
- derive URI
- derive module path
- compute hash
- collect size
- collect mtime
- build `FileRecord`

### Step 5

Return all file records sorted by `file_path`.

Sorting matters because deterministic output makes tests cleaner and behavior easier to debug.

---

## Example implementation sketch

```python
import os
from pathlib import Path
from datetime import datetime, timezone

from repo_context.models.repo import RepoRecord
from repo_context.models.file import FileRecord
from repo_context.parsing.pathing import (
    normalize_repo_root,
    to_relative_path,
    to_file_uri,
    derive_module_path,
)
from repo_context.parsing.hashing import sha256_file

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def should_ignore_dir(name: str, ignored_dirs: tuple[str, ...]) -> bool:
    return name in ignored_dirs

def is_supported_source_file(path: Path, supported_extensions: tuple[str, ...]) -> bool:
    return path.suffix in supported_extensions

def build_repo_record(repo_root: Path) -> RepoRecord:
    now = utc_now_iso()
    return RepoRecord(
        id=f"repo:{repo_root.name}",
        root_path=str(repo_root),
        name=repo_root.name,
        default_language="python",
        created_at=now,
        last_indexed_at=now,
    )

def build_file_record(repo_id: str, repo_root: Path, file_path: Path) -> FileRecord:
    stat = file_path.stat()
    rel = to_relative_path(repo_root, file_path)
    now = utc_now_iso()
    return FileRecord(
        id=f"file:{rel}",
        repo_id=repo_id,
        file_path=rel,
        uri=to_file_uri(file_path),
        module_path=derive_module_path(repo_root, file_path),
        language="python",
        content_hash=sha256_file(file_path),
        size_bytes=stat.st_size,
        last_modified_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
        last_indexed_at=now,
    )

def scan_repository(repo_root: str | Path, config) -> tuple[RepoRecord, list[FileRecord]]:
    root = normalize_repo_root(repo_root)
    repo = build_repo_record(root)
    results: list[FileRecord] = []

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not should_ignore_dir(d, config.ignored_dirs)]

        for filename in filenames:
            path = Path(dirpath) / filename
            if not is_supported_source_file(path, config.supported_extensions):
                continue
            results.append(build_file_record(repo.id, root, path))

    results.sort(key=lambda x: x.file_path)
    return repo, results
```

This is enough for phase 2.
Do not make it fancier yet.

---

## CLI design for this phase

Add a command like:

```text
repo-context scan-repo /path/to/repo
```

### Expected behavior

- validate the path
- run the scanner
- persist repo and file records
- print a short summary

Example output:

```text
Repository scanned successfully
Repo ID: repo:project
Files found: 23
Language: python
```

### Optional flags

You may add:
- `--db-path`
- `--json`

But do not go overboard.

---

## Persistence flow

Recommended persistence sequence:

1. open DB connection
2. upsert repo record
3. upsert all file records
4. commit transaction
5. print summary

### Good practice

Do the whole scan persistence inside one transaction if possible.

Why:
- cleaner state
- fewer half-written updates

---

## How to derive module paths correctly

Use these examples as contract tests.

### Example 1

```text
repo root: /repo
file: /repo/app/services/auth.py
module_path: app.services.auth
```

### Example 2

```text
repo root: /repo
file: /repo/app/__init__.py
module_path: app
```

### Example 3

```text
repo root: /repo
file: /repo/pkg/subpkg/__init__.py
module_path: pkg.subpkg
```

### Example 4

```text
repo root: /repo
file: /repo/main.py
module_path: main
```

### Example 5

```text
repo root: /repo
file: /repo/tools/_internal.py
module_path: tools._internal
```

### Important rule

Do not try to validate whether the module path is importable.
This phase only derives the logical path from filesystem layout.

---

## Edge cases to handle

## Edge case 1: Empty repository

If the repo contains no `.py` files:
- still create or update the repo record
- return zero file records
- do not crash

## Edge case 2: Files with unreadable content

If a file cannot be read:
- either skip it and record an error in the scan summary
- or fail the whole scan

My recommendation for v1:
- fail fast unless you have a strong reason to continue
- debugging is easier when the scanner is strict

## Edge case 3: Symlinks

Keep it simple.
Do not follow exotic symlink behavior in v1 unless needed.

A good default:
- accept normal filesystem walking behavior
- do not optimize around symlink complexity yet

## Edge case 4: Non-UTF-8 files

If hashing reads raw bytes, this is less of a problem.
Do not overcomplicate text decoding in the scanner.
You are hashing files, not parsing them yet.

## Edge case 5: Duplicate weird paths

Always normalize through `Path.resolve()` at the repo root level.

---

## Database sync strategy

There are two valid options.

## Option A: Scan inserts and updates only

The scanner:
- adds new files
- updates changed files
- does not remove deleted files from the DB

Pros:
- simpler
- less dangerous

Cons:
- DB can get stale

## Option B: Scan fully syncs file inventory

The scanner:
- adds new files
- updates existing files
- removes missing files from the DB

Pros:
- cleaner inventory state

Cons:
- slightly more logic

My blunt recommendation:
- use Option B if you can implement it cleanly
- otherwise use Option A now and add cleanup in phase 4

Just do not leave the behavior ambiguous.

---

## Testing plan

This phase needs real tests.

## `test_scanner_basic`

Create a tiny fixture repo and verify:
- only `.py` files are found
- count is correct
- file paths are relative
- module paths are correct

## `test_scanner_ignores_dirs`

Verify ignored folders are skipped:
- `.git`
- `node_modules`
- `__pycache__`

## `test_module_path_derivation`

Use multiple fixture paths and check exact expected module paths.

## `test_file_uri_generation`

Ensure URIs are valid and begin with `file://`.

## `test_hashing_is_stable`

Hash the same file twice and confirm the hash is identical.

## `test_scan_persists_records`

Run the scan and verify the DB contains:
- one repo row
- expected file rows

## `test_empty_repo`

Scan a repo with no `.py` files and verify:
- no crash
- repo row exists
- file count is zero

---

## Suggested fixtures

Create fixture repositories like these:

```text
tests/fixtures/
  simple_repo/
    app/
      __init__.py
      services/
        __init__.py
        auth.py
      models/
        user.py
    main.py
    README.md

  repo_with_ignored_dirs/
    .git/
    node_modules/
    app/
      keep.py

  empty_repo/
    README.md
```

Keep fixtures tiny and explicit.

---

## Acceptance checklist

Phase 2 is done when all of this is true:

- Scanner accepts a repo path.
- Invalid repo paths fail cleanly.
- Ignored directories are skipped.
- Only `.py` files are kept.
- File records include repo-relative path, URI, module path, hash, size, and mtime.
- Repo record is created or updated.
- File records are persisted to SQLite.
- Output order is deterministic.
- Tests pass.
- No AST parsing exists yet.
- No LSP integration exists yet.
- No node or edge creation exists yet.

---

## Common mistakes to avoid

### Mistake 1: Parsing code in the scanner

Do not sneak AST logic into this phase.

### Mistake 2: Storing absolute paths as primary identity

Absolute paths are useful, but repo-relative paths are the right core file identity.

### Mistake 3: Deriving module paths inconsistently

If this is wrong now, qualified names and later graph nodes will be wrong too.

### Mistake 4: Hardcoding ignore logic in random places

Keep ignore rules centralized in config and scanner helpers.

### Mistake 5: Making the CLI do scanner logic itself

CLI should call scanner functions, not contain scanner logic.

### Mistake 6: Returning unsorted file lists

Deterministic ordering matters more than people think.

---

## What phase 3 will depend on

The next phase will assume phase 2 already provides:

- trusted file inventory
- stable repo-relative file identities
- module-path derivation
- persisted file metadata
- a clean repo record

Phase 3 will use those files as the input set for AST parsing.
If the scanner lies, the parser will lie too.

---

## Final guidance

This phase should produce a boring, clean list of Python files and metadata.

That is exactly what you want.

Do not try to be clever.
The scanner is not a parser.
It is not a graph engine.
It is not a risk engine.

It is just the layer that answers:

- what files exist
- where they are
- how they should be identified
- whether they changed

If it does that reliably, phase 2 is successful.
```