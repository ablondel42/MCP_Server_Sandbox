# 02-repo-scanner.qwen.md

You are implementing phase `02-repo-scanner`.

Follow this file exactly.
Do not rename required files, required functions, required fields, or required commands.
Do not skip fields because they seem optional unless this file explicitly allows it.

## Objective

Implement a deterministic repository scanner for Python files.

The scanner must:
- validate a repository root
- walk the repository tree
- skip ignored directories
- keep only supported source files
- derive deterministic repo-relative paths
- derive deterministic file URIs
- derive deterministic Python module paths
- compute deterministic file hashes
- collect file size and last-modified metadata
- create `RepoRecord`
- create `FileRecord`
- persist repo and file records to SQLite
- expose CLI support for `repo-context scan-repo`

This phase is complete only when all required files exist, all required functions exist, all required tests pass, and no out-of-scope functionality was added.

## Out of scope

Do not implement any item in this list:
- AST parsing
- symbol extraction
- import extraction
- class extraction
- function extraction
- LSP requests
- node creation
- edge creation
- graph context building
- risk scoring
- MCP tools
- watch mode

Do not add placeholder implementations for out-of-scope items.
Do not add “future-ready” abstractions for out-of-scope items unless they are required by an existing import contract.

## Required outputs

Create these files:
- `src/repo_context/parsing/__init__.py`
- `src/repo_context/parsing/scanner.py`
- `src/repo_context/parsing/pathing.py`
- `src/repo_context/parsing/hashing.py`
- `src/repo_context/storage/repos.py`
- `src/repo_context/storage/files.py`

Add CLI support for:
- `repo-context scan-repo /path/to/repo`

Add tests for:
- scanning
- filtering
- module-path derivation
- hashing
- URI generation
- persistence

## Phase rules

Implement all items in this list:
- repository root validation
- directory walking
- ignored-directory filtering
- supported-extension filtering
- repo-relative path derivation
- file URI derivation
- Python module-path derivation
- file content hashing
- file size collection
- file modified-time collection
- `RepoRecord` creation or update
- `FileRecord` creation
- persistence of repo and file records
- deterministic scan ordering
- CLI command to scan and persist

Do not implement any item outside this list unless it is strictly required to support the listed items.

## Config rules

Use:
- `AppConfig.ignored_dirs`
- `AppConfig.supported_extensions`

Do not duplicate ignore logic in unrelated files.
Do not hardcode ignore rules in the CLI file.
Do not hardcode supported file extensions in unrelated files.

## FileRecord contract

Use this dataclass contract exactly:

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

Use these field rules exactly:
- `id` must use format `file:{repo_relative_path}`
- `repo_id` must come from the repo record
- `file_path` must be repo-relative and POSIX-style
- `uri` must be a valid `file://` URI
- `module_path` must be derived from filesystem layout
- `language` must be exactly `python`
- `content_hash` must use SHA-256 with prefix `sha256:`
- `size_bytes` must come from the filesystem
- `last_modified_at` must be an ISO 8601 UTC string
- `last_indexed_at` must be set during the scan and used consistently

Do not omit any `FileRecord` field.
Do not rename any `FileRecord` field.
Do not store absolute file paths as the main file identity.

## RepoRecord rules

Use the existing phase 1 `RepoRecord` contract exactly.

Generate values with these rules:
- `id` must use format `repo:{folder_name}` for v1
- `name` must be the repo folder name
- `root_path` must be the resolved absolute path
- `default_language` must be exactly `python`
- `created_at` and `last_indexed_at` must be set consistently

If an existing repo row already exists, update it without breaking the phase 1 contract.

## Required pathing file

Create `src/repo_context/parsing/pathing.py`.

It must contain exactly these functions:

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

Implement these rules exactly:
- `normalize_repo_root` must resolve the path
- `normalize_repo_root` must verify that the path exists
- `normalize_repo_root` must verify that the path is a directory
- `to_relative_path` must return a repo-relative POSIX-style path string
- `to_file_uri` must return a valid `file://` URI
- `derive_module_path` must remove `.py`
- `derive_module_path` must remove a trailing `__init__`
- `derive_module_path` must join remaining path parts with `.`

Do not make module derivation fuzzy.
Do not special-case undocumented patterns.

## Required hashing file

Create `src/repo_context/parsing/hashing.py`.

It must contain exactly these functions:

```python
from pathlib import Path

def sha256_text(text: str) -> str:
    ...

def sha256_file(file_path: Path) -> str:
    ...
```

Implement these rules exactly:
- use SHA-256
- return values with `sha256:` prefix
- hash file bytes in `sha256_file`
- do not assume a text encoding for file hashing

If a file cannot be read for hashing, fail clearly.
Do not silently skip files.
Do not invent partial hashes.

## Required scanner file

Create `src/repo_context/parsing/scanner.py`.

It must contain exactly these functions:

```python
from pathlib import Path
from repo_context.models.repo import RepoRecord
from repo_context.models.file import FileRecord

def should_ignore_dir(name: str, ignored_dirs: tuple[str, ...]) -> bool:
    ...

def is_supported_source_file(path: Path, supported_extensions: tuple[str, ...]) -> bool:
    ...

def build_repo_record(repo_root: Path) -> RepoRecord:
    ...

def build_file_record(repo_id: str, repo_root: Path, file_path: Path) -> FileRecord:
    ...

def scan_repository(repo_root: str | Path, config) -> tuple[RepoRecord, list[FileRecord]]:
    ...
```

Implement these rules exactly:
- `should_ignore_dir` must match exact directory names only
- `is_supported_source_file` must keep only configured supported extensions
- `build_repo_record` must produce a valid repo record from the normalized root
- `build_file_record` must fully populate `FileRecord`
- `scan_repository` must return one repo record and one list of file records sorted by `file_path`

Use `os.walk`.
Prune ignored directories by mutating `dirnames` in place.
Keep returned ordering deterministic.
Keep repo-relative paths POSIX-style.

Do not put SQLite persistence inside `scanner.py` as its main responsibility.
A small wrapper is allowed only if scanning logic remains clearly separate from persistence.

## Required persistence files

Create `src/repo_context/storage/repos.py`.

It must contain exactly these functions:

```python
from repo_context.models.repo import RepoRecord

def upsert_repo(conn, repo: RepoRecord) -> None:
    ...

def get_repo_by_id(conn, repo_id: str) -> RepoRecord | None:
    ...
```

Create `src/repo_context/storage/files.py`.

It must contain exactly these functions:

```python
from repo_context.models.file import FileRecord

def upsert_file(conn, file_record: FileRecord) -> None:
    ...

def upsert_files(conn, file_records: list[FileRecord]) -> None:
    ...

def list_files_for_repo(conn, repo_id: str) -> list[FileRecord]:
    ...
```

Optional in this phase:

```python
def delete_files_not_in_set(conn, repo_id: str, keep_paths: set[str]) -> None:
    ...
```

If you implement deletion sync:
- document it clearly
- test it explicitly

If you do not implement deletion sync:
- do not imply that database state is fully synchronized after a rescan

## CLI rules

Add support for this command:

```text
repo-context scan-repo /path/to/repo
```

Optional flags:
- `--db-path`
- `--json`

CLI must do all of the following:
- validate the repo path
- run the scanner
- persist repo and file records
- print a short summary

Do not put scanning logic inside the CLI file.
Do not put persistence implementation details directly inside argument parsing code.
The CLI should orchestrate existing functions.

## File-by-file requirements

### `src/repo_context/parsing/__init__.py`
This file must exist.

### `src/repo_context/parsing/pathing.py`
This file must contain:
- `normalize_repo_root`
- `to_relative_path`
- `to_file_uri`
- `derive_module_path`

### `src/repo_context/parsing/hashing.py`
This file must contain:
- `sha256_text`
- `sha256_file`

### `src/repo_context/parsing/scanner.py`
This file must contain:
- `should_ignore_dir`
- `is_supported_source_file`
- `build_repo_record`
- `build_file_record`
- `scan_repository`

This file must not contain:
- AST parsing
- symbol extraction
- SQLite persistence as its main responsibility

### `src/repo_context/storage/repos.py`
This file must contain:
- `upsert_repo`
- `get_repo_by_id`

### `src/repo_context/storage/files.py`
This file must contain:
- `upsert_file`
- `upsert_files`
- `list_files_for_repo`

Optional:
- `delete_files_not_in_set`

### CLI integration
Add support for:
- `repo-context scan-repo /path/to/repo`

## Implementation rules

Follow all rules in this list:
- do not parse AST in this phase
- do not create nodes in this phase
- do not create edges in this phase
- do not call LSP in this phase
- do not add MCP code in this phase
- do not omit any listed function
- do not rename any listed function
- do not omit any listed `FileRecord` field
- do not rename any listed `FileRecord` field
- do not infer that metadata fields can be skipped
- do not store absolute file paths as the main file identity
- do not use fuzzy directory ignore matching
- do not put scanning logic inside the CLI file
- do not put SQLite persistence logic inside `scanner.py` unless it is a clearly separate convenience wrapper
- use deterministic ordering for returned file records
- use `os.walk` and prune ignored directories by mutating `dirnames` in place
- keep repo-relative paths POSIX-style
- keep module-path derivation deterministic
- if file deletion sync is not implemented, keep behavior explicit and limited
- if a file cannot be read for hashing, fail clearly

## Required tests

Add these tests.

### `test_scanner_basic`
Verify all items in this list:
- only `.py` files are found
- file count is correct
- `file_path` values are repo-relative
- results are sorted deterministically
- `module_path` values are correct

### `test_scanner_ignores_dirs`
Verify ignored directories are skipped:
- `.git`
- `node_modules`
- `__pycache__`

### `test_module_path_derivation`
Verify these exact mappings:
- `app/services/auth.py -> app.services.auth`
- `app/__init__.py -> app`
- `pkg/subpkg/__init__.py -> pkg.subpkg`
- `main.py -> main`
- `tools/_internal.py -> tools._internal`

### `test_file_uri_generation`
Verify all items in this list:
- URIs begin with `file://`
- URIs are valid file URIs for local files

### `test_hashing_is_stable`
Verify all items in this list:
- hashing the same file twice returns the same value
- the hash uses the `sha256:` prefix

### `test_scan_persists_records`
Verify all items in this list:
- one repo row exists after scanning
- expected file rows exist after scanning

### `test_empty_repo`
Verify all items in this list:
- scanning a repo with no `.py` files does not crash
- the repo row exists
- the file count is zero

### `test_invalid_repo_path`
Verify all items in this list:
- invalid repo path fails clearly
- non-directory repo path fails clearly

### Optional deletion-sync test
Add this test only if deletion sync is implemented.

Verify all items in this list:
- removed files are deleted from database state during a rescan

## Verification checklist

Before finishing, verify every item in this list:
- [ ] Scanner accepts a repo path
- [ ] Invalid repo paths fail clearly
- [ ] Ignored directories are skipped by exact directory-name matching
- [ ] Only `.py` files are included
- [ ] `FileRecord` values include `file_path`, `uri`, `module_path`, `content_hash`, `size_bytes`, `last_modified_at`, and `last_indexed_at`
- [ ] `RepoRecord` is created or updated
- [ ] Repo and file records are persisted to SQLite
- [ ] Returned file order is deterministic
- [ ] Module-path derivation matches the documented examples exactly
- [ ] Hashing uses SHA-256 with `sha256:` prefix
- [ ] `repo-context scan-repo /path/to/repo` works
- [ ] Tests pass
- [ ] No AST parsing exists in this phase
- [ ] No LSP integration exists in this phase
- [ ] No node creation exists in this phase
- [ ] No edge creation exists in this phase

Do not mark the phase complete until every required non-optional item is true.

## Completion rule

The phase is complete only when:
- all required files exist
- all required functions exist with the listed names
- the scanner produces deterministic `RepoRecord` and `FileRecord` outputs
- persistence works
- all required tests pass
- no out-of-scope functionality was added

## Recommended execution order

Implement work in this order:
1. create `parsing/__init__.py`
2. implement `pathing.py`
3. implement `hashing.py`
4. implement `scanner.py`
5. implement `storage/repos.py`
6. implement `storage/files.py`
7. add CLI wiring for `scan-repo`
8. add tests
9. run tests
10. verify the checklist
11. stop without adding out-of-scope functionality
