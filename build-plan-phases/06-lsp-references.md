Implement phase 6 in the **smallest correct way**.

## Goal

Add exactly one semantic enrichment to the graph:

- `references`

Use a Python LSP server to get references for one target symbol, map returned locations back to stored internal symbols, and persist `references` edges.

## Mandatory choices

- Use `pyright-langserver --stdio`
- Use `lsprotocol`
- Build a tiny in-project stdio JSON-RPC client
- Do not use a heavy LSP client framework
- Do not build a generic editor abstraction
- Do not support multiple LSP servers in v1

## Version pins

- `pyright@1.1.408`
- `lsprotocol==2023.0.1`

## Install

```bash
pip3 install pyright
python -m pip install lsprotocol==2023.0.1
```

## Allowed LSP surface

Implement only:

- `initialize`
- `initialized`
- `textDocument/didOpen`
- `textDocument/references`
- `shutdown`
- `exit`

Do not implement:

- hover
- rename
- diagnostics
- completion
- code actions
- semantic tokens
- workspace symbols
- any other LSP feature

## Truth rules

- Store only `references` edges as truth
- Derive `referenced_by` by reverse lookup
- Do not persist `referenced_by`
- Keep unavailable references distinct from refreshed-zero references
- Reuse existing phases 1 through 5 storage, models, helpers, and context builder
- Support nested local functions and local classes from phase 03b

## Required files

Create or extend:

- `src/repo_context/lsp/__init__.py`
- `src/repo_context/lsp/client.py`
- `src/repo_context/lsp/protocol.py`
- `src/repo_context/lsp/references.py`
- `src/repo_context/lsp/mapper.py`
- `src/repo_context/lsp/resolver.py`
- `src/repo_context/graph/references.py`

## Required implementation order

1. minimal stdio LSP client
2. protocol helpers
3. query position resolver
4. file resolution by URI
5. range containment helper
6. smallest containing symbol picker
7. module fallback helper
8. reference edge builder
9. transactional replace for one target
10. enrichment orchestrator
11. graph queries and stats
12. `SymbolContext.reference_summary`
13. CLI commands
14. failure handling
15. tests

## Hard behavior rules

Before requesting references for a target symbol:

1. start the LSP server
2. send `initialize`
3. send `initialized`
4. send `didOpen` for the target file using current file contents
5. then send `textDocument/references`
6. use `includeDeclaration = false`

If tests prove Pyright still misses cross-file references, add one explicit fallback mode that opens all tracked `.py` files before the references request.

Do not assume `rootUri` alone is enough.

## Required code skeleton

### `src/repo_context/lsp/client.py`

Implement this shape:

```python
import json
import subprocess
from pathlib import Path


class PyrightLspClient:
    def __init__(self, server_cmd=None):
        self.server_cmd = server_cmd or ["pyright-langserver", "--stdio"]
        self.proc = None
        self._next_id = 1
        self._started = False

    def start(self, repo_root: str):
        if self._started:
            return
        self.proc = subprocess.Popen(
            self.server_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.request(
            "initialize",
            {
                "processId": None,
                "rootUri": Path(repo_root).resolve().as_uri(),
                "capabilities": {},
                "workspaceFolders": [
                    {
                        "name": Path(repo_root).name,
                        "uri": Path(repo_root).resolve().as_uri(),
                    }
                ],
            },
        )
        self.notify("initialized", {})
        self._started = True

    def _write_message(self, payload: dict):
        body = json.dumps(payload).encode("utf-8")
        header = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
        assert self.proc and self.proc.stdin
        self.proc.stdin.write(header + body)
        self.proc.stdin.flush()

    def _read_message(self) -> dict:
        assert self.proc and self.proc.stdout
        headers = b""
        while b"\r\n\r\n" not in headers:
            chunk = self.proc.stdout.read(1)
            if not chunk:
                raise RuntimeError("LSP server closed stdout unexpectedly")
            headers += chunk

        header_blob, _ = headers.split(b"\r\n\r\n", 1)
        content_length = None
        for line in header_blob.split(b"\r\n"):
            if line.lower().startswith(b"content-length:"):
                content_length = int(line.split(b":", 1)[1].strip())
                break
        if content_length is None:
            raise RuntimeError("Missing Content-Length header")

        body = self.proc.stdout.read(content_length)
        return json.loads(body.decode("utf-8"))

    def request(self, method: str, params: dict):
        msg_id = self._next_id
        self._next_id += 1
        self._write_message(
            {"jsonrpc": "2.0", "id": msg_id, "method": method, "params": params}
        )

        while True:
            message = self._read_message()
            if message.get("id") == msg_id:
                if "error" in message:
                    raise RuntimeError(f"LSP error for {method}: {message['error']}")
                return message.get("result")

    def notify(self, method: str, params: dict):
        self._write_message({"jsonrpc": "2.0", "method": method, "params": params})

    def did_open(self, uri: str, text: str):
        self.notify(
            "textDocument/didOpen",
            {
                "textDocument": {
                    "uri": uri,
                    "languageId": "python",
                    "version": 1,
                    "text": text,
                }
            },
        )

    def find_references(self, uri: str, line: int, character: int, include_declaration: bool = False):
        return self.request(
            "textDocument/references",
            {
                "textDocument": {"uri": uri},
                "position": {"line": line, "character": character},
                "context": {"includeDeclaration": include_declaration},
            },
        )

    def close(self):
        if not self.proc:
            return
        try:
            self.request("shutdown", {})
        finally:
            try:
                self.notify("exit", {})
            finally:
                self.proc.terminate()
                self.proc = None
                self._started = False
```

## Protocol helpers

### `src/repo_context/lsp/protocol.py`

Implement this shape:

```python
from lsprotocol import types as lsp


def build_references_params(uri: str, line: int, character: int, include_declaration: bool = False):
    return lsp.ReferenceParams(
        text_document=lsp.TextDocumentIdentifier(uri=uri),
        position=lsp.Position(line=line, character=character),
        context=lsp.ReferenceContext(include_declaration=include_declaration),
    )


def normalize_location(location) -> dict:
    if isinstance(location, dict):
        return {
            "uri": location["uri"],
            "range": location["range"],
        }
    return {
        "uri": location.uri,
        "range": {
            "start": {
                "line": location.range.start.line,
                "character": location.range.start.character,
            },
            "end": {
                "line": location.range.end.line,
                "character": location.range.end.character,
            },
        },
    }
```

## Query position resolver

### `src/repo_context/lsp/resolver.py`

Implement:

```python
def get_reference_query_position(symbol) -> dict:
    if symbol.selection_range_json:
        return symbol.selection_range_json["start"]
    if symbol.range_json:
        return symbol.range_json["start"]
    raise ValueError(f"Symbol {symbol.id} has no stored range for references query")
```

Also implement exact URI lookup:

```python
def resolve_file_by_uri(conn, uri: str):
    row = conn.execute(
        "SELECT * FROM files WHERE uri = ? LIMIT 1",
        (uri,),
    ).fetchone()
    return row
```

## Range containment and mapping

### `src/repo_context/lsp/mapper.py`

Implement:

```python
def _pos_le(a: dict, b: dict) -> bool:
    return (a["line"], a["character"]) <= (b["line"], b["character"])


def _pos_ge(a: dict, b: dict) -> bool:
    return (a["line"], a["character"]) >= (b["line"], b["character"])


def range_contains(outer: dict, inner: dict) -> bool:
    return _pos_le(outer["start"], inner["start"]) and _pos_ge(outer["end"], inner["end"])


def _range_span_key(r: dict):
    return (
        r["end"]["line"] - r["start"]["line"],
        r["end"]["character"] - r["start"]["character"],
    )


def pick_smallest_containing_symbol(symbols_in_file, usage_range: dict):
    candidates = [
        s for s in symbols_in_file
        if s.get("range_json") and range_contains(s["range_json"], usage_range)
    ]
    if not candidates:
        return None

    candidates.sort(
        key=lambda s: (
            _range_span_key(s["range_json"]),
            -(s.get("lexical_depth", 0)),
            s["id"],
        )
    )
    return candidates[0]


def find_module_node_for_file(symbols_in_file):
    for symbol in symbols_in_file:
        if symbol.get("kind") == "module":
            return symbol
    return None
```

## Edge builder

### `src/repo_context/lsp/references.py`

Implement:

```python
from datetime import datetime, timezone


def build_reference_edge(
    repo_id: str,
    from_id: str,
    to_id: str,
    confidence: float,
    evidence_file_id: str,
    evidence_uri: str,
    evidence_range_json: dict,
    payload_json: dict,
) -> dict:
    start = evidence_range_json["start"]
    edge_id = f"edge:{repo_id}:references:{from_id}->{to_id}:{start['line']}:{start['character']}"
    return {
        "id": edge_id,
        "repo_id": repo_id,
        "kind": "references",
        "from_id": from_id,
        "to_id": to_id,
        "source": "lsp",
        "confidence": confidence,
        "evidence_file_id": evidence_file_id,
        "evidence_uri": evidence_uri,
        "evidence_range_json": evidence_range_json,
        "payload_json": payload_json,
        "last_indexed_at": datetime.now(timezone.utc).isoformat(),
    }
```

## Replace edges for one target only

Implement:

```python
import json


def replace_reference_edges_for_target(conn, target_symbol_id: str, edges: list[dict], refresh_metadata: dict):
    try:
        conn.execute("BEGIN")
        conn.execute(
            "DELETE FROM edges WHERE kind = 'references' AND to_id = ?",
            (target_symbol_id,),
        )

        for edge in edges:
            conn.execute(
                """
                INSERT INTO edges (
                    id, repo_id, kind, from_id, to_id, source, confidence,
                    evidence_file_id, evidence_uri, evidence_range_json, payload_json, last_indexed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    edge["id"],
                    edge["repo_id"],
                    edge["kind"],
                    edge["from_id"],
                    edge["to_id"],
                    edge["source"],
                    edge["confidence"],
                    edge["evidence_file_id"],
                    edge["evidence_uri"],
                    json.dumps(edge["evidence_range_json"]),
                    json.dumps(edge["payload_json"]),
                    edge["last_indexed_at"],
                ),
            )

        conn.execute(
            """
            INSERT INTO reference_refresh (
                target_symbol_id, available, last_refreshed_at, refresh_status, error_code
            ) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(target_symbol_id) DO UPDATE SET
                available = excluded.available,
                last_refreshed_at = excluded.last_refreshed_at,
                refresh_status = excluded.refresh_status,
                error_code = excluded.error_code
            """,
            (
                refresh_metadata["target_symbol_id"],
                refresh_metadata["available"],
                refresh_metadata["last_refreshed_at"],
                refresh_metadata.get("refresh_status"),
                refresh_metadata.get("error_code"),
            ),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
```

## Enrichment orchestrator

Implement `enrich_references_for_symbol(conn, lsp_client, target_symbol, open_all_files=False)` with this exact flow:

1. resolve query position from `selection_range_json.start`, else `range_json.start`
2. ensure client started for repo root
3. open target file via `didOpen`
4. optionally open all tracked `.py` files if fallback mode enabled
5. request `textDocument/references` with `includeDeclaration=False`
6. normalize each location
7. resolve file by exact URI
8. load symbols for that file
9. pick smallest containing symbol by range containment
10. if none, fall back to module node
11. if still none, skip
12. confidence:
   - `0.9` for exact symbol match
   - `0.7` for module fallback
13. build one `references` edge
14. deduplicate by:
   - target symbol ID
   - source symbol ID
   - evidence URI
   - evidence start line
   - evidence start character
15. replace old target references transactionally
16. mark refresh metadata available
17. return reference stats

Use this code shape:

```python
from datetime import datetime, timezone
from pathlib import Path

from .protocol import normalize_location
from .resolver import get_reference_query_position, resolve_file_by_uri
from .mapper import pick_smallest_containing_symbol, find_module_node_for_file


def enrich_references_for_symbol(conn, lsp_client, target_symbol, open_all_files: bool = False):
    position = get_reference_query_position(target_symbol)

    lsp_client.start(target_symbol.repo_root)

    target_path = Path(target_symbol.file_path)
    target_text = target_path.read_text(encoding="utf-8")
    lsp_client.did_open(target_symbol.uri, target_text)

    if open_all_files:
        rows = conn.execute("SELECT path, uri FROM files WHERE path LIKE '%.py'").fetchall()
        for row in rows:
            path = Path(row["path"])
            if not path.exists() or str(path) == str(target_path):
                continue
            lsp_client.did_open(row["uri"], path.read_text(encoding="utf-8"))

    locations = lsp_client.find_references(
        target_symbol.uri,
        position["line"],
        position["character"],
        include_declaration=False,
    ) or []

    edges = []
    seen = set()

    for loc in locations:
        normalized = normalize_location(loc)
        file_row = resolve_file_by_uri(conn, normalized["uri"])
        if not file_row:
            continue

        symbols = load_symbols_for_file(conn, file_row["id"])
        source_symbol = pick_smallest_containing_symbol(symbols, normalized["range"])
        mapping_mode = "exact_symbol"
        confidence = 0.9

        if source_symbol is None:
            source_symbol = find_module_node_for_file(symbols)
            mapping_mode = "module_fallback"
            confidence = 0.7

        if source_symbol is None:
            continue

        dedupe_key = (
            target_symbol.id,
            source_symbol["id"],
            normalized["uri"],
            normalized["range"]["start"]["line"],
            normalized["range"]["start"]["character"],
        )
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        edge = build_reference_edge(
            repo_id=target_symbol.repo_id,
            from_id=source_symbol["id"],
            to_id=target_symbol.id,
            confidence=confidence,
            evidence_file_id=file_row["id"],
            evidence_uri=normalized["uri"],
            evidence_range_json=normalized["range"],
            payload_json={
                "mapping_mode": mapping_mode,
                "target_symbol_kind": target_symbol.kind,
                "source_symbol_kind": source_symbol["kind"],
                "source_symbol_scope": source_symbol.get("scope"),
            },
        )
        edges.append(edge)

    refresh_metadata = {
        "target_symbol_id": target_symbol.id,
        "available": True,
        "last_refreshed_at": datetime.now(timezone.utc).isoformat(),
        "refresh_status": "ok",
        "error_code": None,
    }

    replace_reference_edges_for_target(conn, target_symbol.id, edges, refresh_metadata)
    return build_reference_stats(conn, target_symbol.id)
```

## Mapping rules

- Resolve file by exact URI match only
- Pick the smallest containing symbol only
- Nested local function wins over outer function if it is narrower
- If no containing symbol exists, fall back to module node
- If no module node exists, skip the location
- Do not fabricate symbols
- Do not collapse nested usages to module scope when a narrower symbol exists

## Confidence rules

Use only:

- `0.9` exact containing symbol
- `0.7` module fallback

Do not use `1.0`.

## Edge rules

Every stored usage edge must have:

- `kind = "references"`
- `from_id = containing symbol`
- `to_id = target symbol`
- `source = "lsp"`

Edge ID must be:

```text
edge:{repo_id}:references:{from_id}->{to_id}:{line}:{character}
```

Use evidence start line and character.

Keep self-references.

## Refresh state rules

Track refresh state explicitly per target symbol.

Create a `reference_refresh` table or equivalent metadata with at least:

- `target_symbol_id`
- `available`
- `last_refreshed_at`
- optional `refresh_status`
- optional `error_code`

Rules:

- never refreshed != zero references
- successful refresh with zero references => `available = true`
- missing refresh state => `available = false`
- do not infer zero references from missing edges

## Graph queries

### `src/repo_context/graph/references.py`

Implement:

- `list_reference_edges_for_target(conn, target_id)`
- `list_referenced_by(conn, target_id)`
- `list_references_from_symbol(conn, source_id)`
- `build_reference_stats(conn, target_id)`
- `get_reference_refresh_state(conn, target_id)`

Rules:

- `list_reference_edges_for_target` returns stored `references` edges where `to_id = target_id`
- `list_referenced_by` derives reverse usage from stored `references` edges
- `list_references_from_symbol` returns stored `references` edges where `from_id = source_id`
- `build_reference_stats` includes:
  - `reference_count`
  - `referencing_file_count`
  - `referencing_module_count`
  - `available`
  - `last_refreshed_at`
- `available = true` only if refresh metadata says so
- never-refreshed must return `available = false`

Implement this exact shape for refresh state:

```python
def get_reference_refresh_state(conn, target_id: str) -> dict:
    row = conn.execute(
        """
        SELECT target_symbol_id, available, last_refreshed_at, refresh_status, error_code
        FROM reference_refresh
        WHERE target_symbol_id = ?
        """,
        (target_id,),
    ).fetchone()

    if not row:
        return {
            "target_symbol_id": target_id,
            "available": False,
            "last_refreshed_at": None,
            "refresh_status": None,
            "error_code": None,
        }
    return dict(row)
```

## SymbolContext update

Update phase 5 context building so `reference_summary` includes:

- `reference_count`
- `referencing_file_count`
- `referencing_module_count`
- `available`
- `last_refreshed_at`

Rules:

- if never refreshed, `available = false`
- if refreshed and zero edges found, `available = true`
- do not call LSP during normal context building

## CLI commands

Add:

- `repo-context refresh-references <node-id>`
- `repo-context show-references <node-id>`
- `repo-context show-referenced-by <node-id>`

Required behavior:

- `refresh-references` loads target symbol, refreshes references, prints stats, prints availability
- `show-references` prints stored incoming `references` edges for target symbol
- `show-referenced-by` prints reverse lookup derived from stored `references` edges
- commands must show whether reference data is available or unavailable

## Failure rules

- if LSP server is unavailable, raise a clear error
- do not silently convert failure into zero references
- if refresh fails before commit, old references for that target must remain intact
- one target refresh failure must not corrupt other targets

## Tests

Implement at least these tests:

- `test_get_reference_query_position_prefers_selection_range`
- `test_map_location_to_smallest_containing_symbol`
- `test_map_location_inside_local_function_prefers_local_function`
- `test_module_fallback_when_no_symbol_contains_usage`
- `test_build_reference_edge`
- `test_replace_reference_edges_for_target`
- `test_reference_stats`
- `test_reference_stats_distinguish_unavailable_from_zero`
- `test_context_includes_reference_summary_when_available`
- `test_context_marks_reference_summary_unavailable_when_not_refreshed`
- `test_protocol_builds_references_request_with_include_declaration_false`
- `test_client_opens_target_document_before_request`

Use a fake or mocked LSP client for most tests.
Do not require a real language server for the core suite.

## Required assertions

- `selection_range_json.start` is preferred over `range_json.start`
- missing both ranges raises clearly
- usage inside a method maps to the method, not class/module
- usage inside a nested local function maps to that local function, not outer function
- module fallback returns module node and uses lower confidence
- built edge has correct kind, IDs, source, evidence, deterministic ID
- replacing one target removes only old edges for that target
- unrelated targets remain untouched
- reference stats correctly compute counts and availability
- never-refreshed and refreshed-zero are distinct
- protocol request uses `includeDeclaration = false`
- client sends `didOpen` before `textDocument/references`

## Final constraints

- Do not overengineer this
- Do not add abstractions for future phases
- Do not add async unless already required by the project
- Do not add unrelated LSP features
- Do not create a second semantic graph
- Do not store raw LSP locations as final truth
- Do not persist `referenced_by`
- Do not replace references globally
- Do not replace by `from_id`

## Final done definition

Phase 6 is done only if all are true:

- one narrow feature exists: `references`
- Pyright runs through a minimal stdio client
- returned locations are mapped to stable internal symbol IDs
- nested local declarations remain valid mapping targets
- `references` edges are the only stored usage truth
- reverse usage is derived, not duplicated
- refresh metadata exists
- unavailable is distinct from zero
- CLI inspection works
- tests pass
- no out-of-scope LSP features were added