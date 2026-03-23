```md
# 03-ast-extraction.md

## Purpose

This phase builds the AST extraction layer.

Its job is to turn Python source files into structured graph-ready symbols and structural relationships using Python AST.

This phase takes the file inventory from the repository scanner and produces:

- module nodes
- class nodes
- callable nodes
- structural edges such as `contains`, `imports`, and `inherits`

This phase does **not** use LSP yet.
It does **not** compute references yet.
It does **not** expose MCP tools yet.

The AST layer is the structural truth layer.

---

## Why this phase matters

The whole graph depends on this phase.

If AST extraction is wrong:
- symbols will be missing
- qualified names will be wrong
- hierarchy will be wrong
- imports will be misleading
- later reference mapping will attach to the wrong nodes
- risk evaluation will be built on broken structure

This phase is where the codebase stops being “a bunch of files” and becomes “a structured system the agent can reason about”.

---

## Phase goals

By the end of this phase, you should have:

- Python files loaded from the scanner output
- AST trees built for those files
- module nodes extracted
- class nodes extracted
- top-level function nodes extracted
- async function nodes extracted
- method nodes extracted
- async method nodes extracted
- decorators extracted
- base classes extracted
- imports extracted
- doc summaries extracted
- declaration ranges extracted
- selection ranges extracted
- qualified names derived
- structural edges created
- nodes and edges persisted to SQLite

---

## Phase non-goals

Do **not** do any of this in phase 3:

- LSP requests
- `references` edges
- reverse `referenced_by` resolution
- semantic call graph generation
- risk scoring
- MCP exposure
- watch mode

This phase is structural only.

---

## Inputs and outputs

## Inputs

This phase depends on phase 2.

It takes:
- a `RepoRecord`
- a list of `FileRecord` values for Python files
- the repo root path
- access to file contents

## Outputs

This phase produces:
- `SymbolNode` records for modules, classes, and callables
- `Edge` records for `contains`, `imports`, and `inherits`
- optional extraction warnings or errors
- a summary of counts

---

## AST design principles

### Principle 1: AST is structural truth

For version 1, AST is the main source of truth for:
- what declarations exist
- where they live
- what contains what
- what imports exist
- what base classes are declared

### Principle 2: Do not pretend AST knows everything

AST is great for structure.
It is not perfect for semantic resolution.
Do not try to force it to become a full semantic engine.

### Principle 3: Keep unresolved data explicit

If a base class or import target cannot be fully resolved, store it honestly as unresolved or as a string-based placeholder.
Do not invent precision.

### Principle 4: Qualified names must be deterministic

Qualified naming is a core identity rule.
If you are inconsistent here, everything later gets worse.

---

## What the AST layer is responsible for

The AST extraction layer should answer:

- what module does this file represent
- what classes are declared in the file
- what functions are declared in the file
- what methods belong to which classes
- what async callables exist
- what imports are present
- what bases are declared for classes
- what decorators are attached
- where each declaration starts and ends

That is enough for version 1.

---

## Recommended new modules

Add these packages and files:

```text
src/
  repo_context/
    parsing/
      __init__.py
      ast_loader.py
      naming.py
      module_extractor.py
      class_extractor.py
      callable_extractor.py
      import_extractor.py
      inheritance_extractor.py
      ranges.py
      docstrings.py
      pipeline.py
    storage/
      nodes.py
      edges.py
```

### Why this split

- `ast_loader.py`: file -> AST
- `naming.py`: qualified names and IDs
- `module_extractor.py`: module node logic
- `class_extractor.py`: class extraction
- `callable_extractor.py`: function and method extraction
- `import_extractor.py`: `imports` edges
- `inheritance_extractor.py`: `inherits` edges
- `ranges.py`: AST location normalization
- `docstrings.py`: doc summary helpers
- `pipeline.py`: orchestration
- `nodes.py` and `edges.py`: persistence helpers

This keeps logic small and AI-generated code less likely to become spaghetti.

---

## AST nodes you care about in version 1

You do not need the whole Python AST universe.

The main node types you care about are:

- `ast.Module`
- `ast.ClassDef`
- `ast.FunctionDef`
- `ast.AsyncFunctionDef`
- `ast.Import`
- `ast.ImportFrom`

You will also inspect:
- `node.decorator_list`
- `node.bases`
- `node.args`
- `node.returns`

That is enough to build the initial graph.

---

## Symbol model strategy

This phase should populate the base `SymbolNode` plus type-specific payload fields.

The graph layers are:

- module layer
- class layer
- callable layer

That mirrors the structure you want for the graph.  
The user explicitly explored decomposing the graph into layers for modules, classes, and functions/methods, so this phase should preserve that layered shape directly in the extracted nodes. [The original request context says not to include citations in output, so they are omitted here.]

---

## Symbol kinds to support now

Use these `kind` values:

- `module`
- `class`
- `function`
- `async_function`
- `method`
- `async_method`

Do not overcomplicate this with too many subtypes yet.

---

## Node identity rules

You need stable rules now.

### Module node ID

Recommended format:

```text
sym:{repo_id}:module:{module_path}
```

Example:

```text
sym:repo:project:module:app.services.auth
```

### Class node ID

Recommended format:

```text
sym:{repo_id}:class:{qualified_name}
```

Example:

```text
sym:repo:project:class:app.services.auth.AuthService
```

### Callable node ID

Recommended format:

```text
sym:{repo_id}:{kind}:{qualified_name}
```

Example:

```text
sym:repo:project:method:app.services.auth.AuthService.login
```

### Why this matters

Later edges, context queries, and MCP tool outputs should always point to stable IDs.
Do not rely on local names.

---

## Qualified name rules

This is one of the most important parts of the phase.

### Module qualified name

Use the `module_path` derived in phase 2.

Example:

```text
app.services.auth
```

### Class qualified name

Append class name to module path.

Example:

```text
app.services.auth.AuthService
```

### Top-level function qualified name

Append function name to module path.

Example:

```text
app.services.auth.build_auth_payload
```

### Method qualified name

Append method name to class qualified name.

Example:

```text
app.services.auth.AuthService.login
```

### Nested functions

For version 1, you have two valid choices:

## Option A: Ignore nested functions completely

Pros:
- simpler
- cleaner graph
- less noise

Cons:
- some internal behavior is not represented

## Option B: Represent nested functions

Pros:
- more complete

Cons:
- more complexity
- harder naming and parent rules
- often low value for the first version

My blunt recommendation:
- ignore nested functions in v1 unless you already know you need them

---

## Range extraction strategy

You need two location concepts:

- `range`: full declaration span
- `selection_range`: narrower range around the symbol name

### Why this matters

- `range` helps with source slicing and containment checks
- `selection_range` is the best target for later LSP reference requests

### Important Python AST facts

Modern Python AST nodes usually provide:
- `lineno`
- `col_offset`
- `end_lineno`
- `end_col_offset`

Line numbers are usually one-based.
Your canonical internal schema should stay zero-based.

---

## `ranges.py` helpers

Recommended functions:

```python
import ast
from typing import Optional

def to_zero_based_line(line: Optional[int]) -> Optional[int]:
    ...

def make_position(line: Optional[int], character: Optional[int]) -> dict | None:
    ...

def make_range(node: ast.AST) -> dict | None:
    ...

def make_name_selection_range(node: ast.AST) -> dict | None:
    ...
```

### Expected behavior

#### `to_zero_based_line`
- converts AST one-based lines to zero-based lines

#### `make_position`
- returns `{line, character}` if data exists

#### `make_range`
- builds a full range using start and end location metadata

#### `make_name_selection_range`
- builds a narrower range around the symbol name token

### Honest limitation

The exact name token range is not always trivial from raw AST alone.
For v1, a practical approximation is fine if it is consistent.

---

## Doc summary strategy

You should extract a short summary from docstrings when present.

### Good rule

Use the first non-empty chunk of the docstring, not the whole docstring.

Why:
- cheaper
- cleaner
- better for future agent context

### `docstrings.py`

Recommended function:

```python
import ast

def get_doc_summary(node: ast.AST) -> str | None:
    ...
```

Expected behavior:
- use `ast.get_docstring(node)`
- strip whitespace
- return the first short paragraph or first meaningful line

Do not try to generate prose.
Just extract what is already there.

---

## Module extraction

Each Python file should become one module node.

### Module node purpose

A module node represents:
- the file as a logical Python module
- the top-level parent for classes and top-level functions
- the origin point for imports

### Module node construction

Inputs:
- `RepoRecord`
- `FileRecord`
- AST tree for that file

### Suggested module fields

Base fields:
- `id`
- `repo_id`
- `file_id`
- `language`
- `kind="module"`
- `name`
- `qualified_name`
- `uri`
- `range`
- `selection_range`
- `parent_id=None`
- `visibility_hint="module"`
- `doc_summary`
- `content_hash`
- `semantic_hash`
- `source="python-ast"`
- `confidence=1.0`
- `last_indexed_at`

Payload fields:
- `file_path`
- `module_path`
- `package_path`
- `imported_modules`
- `imported_symbols`
- `top_level_symbol_ids`

### Range rule for modules

A module node should cover the full file.

If you do not want to compute an exact end character for the last line yet, use a practical file-span approximation and be consistent.

---

## Module extraction example

```python
import ast
from pathlib import Path

def extract_module_node(repo_id: str, file_record, tree: ast.Module, file_text: str) -> dict:
    lines = file_text.splitlines()
    last_line = max(0, len(lines) - 1)

    module_path = file_record.module_path
    package_path = ".".join(module_path.split(".")[:-1]) if "." in module_path else ""

    return {
        "id": f"sym:{repo_id}:module:{module_path}",
        "repo_id": repo_id,
        "file_id": file_record.id,
        "language": "python",
        "kind": "module",
        "name": module_path.split(".")[-1] if module_path else file_record.file_path,
        "qualified_name": module_path,
        "uri": file_record.uri,
        "range_json": {
            "start": {"line": 0, "character": 0},
            "end": {"line": last_line, "character": 0}
        },
        "selection_range_json": {
            "start": {"line": 0, "character": 0},
            "end": {"line": 0, "character": 0}
        },
        "parent_id": None,
        "visibility_hint": "module",
        "doc_summary": get_doc_summary(tree),
        "content_hash": file_record.content_hash,
        "semantic_hash": file_record.content_hash,
        "source": "python-ast",
        "confidence": 1.0,
        "payload_json": {
            "file_path": file_record.file_path,
            "module_path": module_path,
            "package_path": package_path,
            "imported_modules": [],
            "imported_symbols": [],
            "top_level_symbol_ids": []
        },
        "last_indexed_at": file_record.last_indexed_at,
    }
```

This is only a sketch.
The exact serialization style can differ.
The important part is the contract.

---

## Class extraction

Each `ast.ClassDef` under module scope should become a class node.

### What to extract from classes

- name
- qualified name
- declaration range
- selection range
- base class names
- decorators
- doc summary
- parent module
- method IDs later

### Suggested class payload

- `base_names`
- `decorators`
- `method_ids`

### Class extraction example

```python
import ast

def extract_class_node(repo_id: str, file_record, module_node_id: str, module_path: str, node: ast.ClassDef) -> dict:
    qualified_name = f"{module_path}.{node.name}" if module_path else node.name
    base_names = [ast.unparse(base) for base in node.bases] if node.bases else []
    decorators = [ast.unparse(d) for d in node.decorator_list] if node.decorator_list else []

    return {
        "id": f"sym:{repo_id}:class:{qualified_name}",
        "repo_id": repo_id,
        "file_id": file_record.id,
        "language": "python",
        "kind": "class",
        "name": node.name,
        "qualified_name": qualified_name,
        "uri": file_record.uri,
        "range_json": make_range(node),
        "selection_range_json": make_name_selection_range(node),
        "parent_id": module_node_id,
        "visibility_hint": "private_like" if node.name.startswith("_") else "public",
        "doc_summary": get_doc_summary(node),
        "content_hash": "",
        "semantic_hash": "",
        "source": "python-ast",
        "confidence": 1.0,
        "payload_json": {
            "base_names": base_names,
            "decorators": decorators,
            "method_ids": []
        },
        "last_indexed_at": file_record.last_indexed_at,
    }
```

### Important note

`ast.unparse` is fine here for version 1.
Do not overbuild pretty printers for base names or decorators.

---

## Callable extraction

This phase should extract:

- top-level `FunctionDef` as `function`
- top-level `AsyncFunctionDef` as `async_function`
- class-contained `FunctionDef` as `method`
- class-contained `AsyncFunctionDef` as `async_method`

### What to extract from callables

- name
- qualified name
- parameters
- return annotation
- decorators
- async status
- method status
- generator hint
- doc summary
- parent symbol

### Parameter strategy

Store parameters as lightweight structured records.

Recommended parameter fields:
- `name`
- `kind`
- `annotation`
- `default_value_hint`

Do not try to perfectly serialize every Python expression in defaults yet.

A string hint or `None` is enough for v1.

---

## Parameter extraction example

```python
import ast

def extract_parameters(args: ast.arguments) -> list[dict]:
    result = []

    for arg in getattr(args, "posonlyargs", []):
        result.append({
            "name": arg.arg,
            "kind": "positional_only",
            "annotation": ast.unparse(arg.annotation) if arg.annotation else None,
            "default_value_hint": None,
        })

    for arg in args.args:
        result.append({
            "name": arg.arg,
            "kind": "positional_or_keyword",
            "annotation": ast.unparse(arg.annotation) if arg.annotation else None,
            "default_value_hint": None,
        })

    if args.vararg:
        result.append({
            "name": args.vararg.arg,
            "kind": "var_positional",
            "annotation": ast.unparse(args.vararg.annotation) if args.vararg.annotation else None,
            "default_value_hint": None,
        })

    for arg in args.kwonlyargs:
        result.append({
            "name": arg.arg,
            "kind": "keyword_only",
            "annotation": ast.unparse(arg.annotation) if arg.annotation else None,
            "default_value_hint": None,
        })

    if args.kwarg:
        result.append({
            "name": args.kwarg.arg,
            "kind": "var_keyword",
            "annotation": ast.unparse(args.kwarg.annotation) if args.kwarg.annotation else None,
            "default_value_hint": None,
        })

    return result
```

### What is intentionally missing

This version does not map defaults to specific parameters yet.
That is acceptable for version 1 if you stay honest about it.

If you want to improve it, do it carefully and separately.

---

## Callable extraction example

```python
import ast

def extract_callable_node(
    repo_id: str,
    file_record,
    parent_id: str,
    parent_qualified_name: str,
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    is_method: bool,
) -> dict:
    is_async = isinstance(node, ast.AsyncFunctionDef)
    kind = (
        "async_method" if is_async and is_method else
        "async_function" if is_async else
        "method" if is_method else
        "function"
    )

    qualified_name = f"{parent_qualified_name}.{node.name}" if parent_qualified_name else node.name
    decorators = [ast.unparse(d) for d in node.decorator_list] if node.decorator_list else []

    return {
        "id": f"sym:{repo_id}:{kind}:{qualified_name}",
        "repo_id": repo_id,
        "file_id": file_record.id,
        "language": "python",
        "kind": kind,
        "name": node.name,
        "qualified_name": qualified_name,
        "uri": file_record.uri,
        "range_json": make_range(node),
        "selection_range_json": make_name_selection_range(node),
        "parent_id": parent_id,
        "visibility_hint": (
            "private_like"
            if node.name.startswith("_") and not (node.name.startswith("__") and node.name.endswith("__"))
            else "public"
        ),
        "doc_summary": get_doc_summary(node),
        "content_hash": "",
        "semantic_hash": "",
        "source": "python-ast",
        "confidence": 1.0,
        "payload_json": {
            "parameters": extract_parameters(node.args),
            "return_annotation": ast.unparse(node.returns) if node.returns else None,
            "decorators": decorators,
            "is_async": is_async,
            "is_method": is_method,
            "is_generator": any(isinstance(n, (ast.Yield, ast.YieldFrom)) for n in ast.walk(node)),
        },
        "last_indexed_at": file_record.last_indexed_at,
    }
```

---

## Parent-child hierarchy rules

This phase must create a structural hierarchy.

### Module contains class

If a class is defined at module scope:
- create a class node
- create a `contains` edge from module -> class

### Module contains top-level function

If a function is defined at module scope:
- create a callable node
- create a `contains` edge from module -> function

### Class contains method

If a method is defined directly inside a class body:
- create a callable node
- create a `contains` edge from class -> method

### Important limitation

Ignore deeply nested callables in v1 unless you intentionally decide otherwise.
Do not half-support them.

---

## `contains` edge design

Recommended shape:

```python
def make_contains_edge(repo_id: str, parent_id: str, child_id: str, file_record, evidence_range: dict | None) -> dict:
    return {
        "id": f"edge:{repo_id}:contains:{parent_id}->{child_id}",
        "repo_id": repo_id,
        "kind": "contains",
        "from_id": parent_id,
        "to_id": child_id,
        "source": "python-ast",
        "confidence": 1.0,
        "evidence_file_id": file_record.id,
        "evidence_uri": file_record.uri,
        "evidence_range_json": evidence_range,
        "payload_json": {},
        "last_indexed_at": file_record.last_indexed_at,
    }
```

Why:
- containment is direct structural fact from AST
- confidence should be high

---

## Import extraction

You should extract import facts from:
- `ast.Import`
- `ast.ImportFrom`

### What to capture

At minimum:
- imported module names
- imported symbol names
- edges representing imports from the module node

### Honest limitation

Resolving imports to internal graph nodes perfectly is hard.
For version 1, it is fine to store unresolved string targets.

That is still useful.

### Examples

#### `import app.core.security`

Store:
- imported module: `app.core.security`

#### `from app.models.user import User`

Store:
- imported module: `app.models.user`
- imported symbol: `User`

### Suggested strategy

For module payload:
- populate `imported_modules`
- populate `imported_symbols`

For graph edges:
- create `imports` edges from the module node to unresolved external IDs or string-backed placeholders

Example placeholder IDs:
- `external_or_unresolved:app.core.security`
- `external_or_unresolved:app.models.user.User`

This is fine for v1.

---

## Import extraction example

```python
import ast

def extract_import_edges(repo_id: str, module_node_id: str, file_record, tree: ast.Module) -> tuple[list[dict], list[str], list[str]]:
    edges = []
    imported_modules = []
    imported_symbols = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_modules.append(alias.name)
                edges.append({
                    "id": f"edge:{repo_id}:imports:{module_node_id}->{alias.name}:{getattr(node, 'lineno', 0)}",
                    "repo_id": repo_id,
                    "kind": "imports",
                    "from_id": module_node_id,
                    "to_id": f"external_or_unresolved:{alias.name}",
                    "source": "python-ast",
                    "confidence": 0.8,
                    "evidence_file_id": file_record.id,
                    "evidence_uri": file_record.uri,
                    "evidence_range_json": make_range(node),
                    "payload_json": {"alias": alias.asname},
                    "last_indexed_at": file_record.last_indexed_at,
                })

        elif isinstance(node, ast.ImportFrom):
            module_name = node.module or ""
            if module_name:
                imported_modules.append(module_name)

            for alias in node.names:
                imported_symbols.append(alias.name)
                target = f"{module_name}.{alias.name}" if module_name else alias.name
                edges.append({
                    "id": f"edge:{repo_id}:imports:{module_node_id}->{target}:{getattr(node, 'lineno', 0)}",
                    "repo_id": repo_id,
                    "kind": "imports",
                    "from_id": module_node_id,
                    "to_id": f"external_or_unresolved:{target}",
                    "source": "python-ast",
                    "confidence": 0.8,
                    "evidence_file_id": file_record.id,
                    "evidence_uri": file_record.uri,
                    "evidence_range_json": make_range(node),
                    "payload_json": {"alias": alias.asname, "module": module_name, "level": node.level},
                    "last_indexed_at": file_record.last_indexed_at,
                })

    return edges, imported_modules, imported_symbols
```

---

## Inheritance extraction

Every class with declared bases should produce `inherits` edges.

### What to capture

- string form of each base class expression
- edge from class node to unresolved base placeholder or resolved target later

### Good enough for v1

Use `ast.unparse(base)` and store the base name string.

Do not block on perfect base resolution.

### Example

```python
class AuthService(BaseService, LoggingMixin):
    ...
```

Capture:
- `BaseService`
- `LoggingMixin`

Create edges to:
- `unresolved_base:BaseService`
- `unresolved_base:LoggingMixin`

---

## Inheritance extraction example

```python
import ast

def extract_inherits_edges(repo_id: str, class_node_id: str, file_record, node: ast.ClassDef) -> list[dict]:
    edges = []

    for base in node.bases:
        base_name = ast.unparse(base)
        edges.append({
            "id": f"edge:{repo_id}:inherits:{class_node_id}->{base_name}",
            "repo_id": repo_id,
            "kind": "inherits",
            "from_id": class_node_id,
            "to_id": f"unresolved_base:{base_name}",
            "source": "python-ast",
            "confidence": 0.75,
            "evidence_file_id": file_record.id,
            "evidence_uri": file_record.uri,
            "evidence_range_json": make_range(base),
            "payload_json": {"base_name": base_name},
            "last_indexed_at": file_record.last_indexed_at,
        })

    return edges
```

---

## Semantic hash strategy

Phase 3 should start leaving room for meaningful semantic hashes, even if the first implementation is simple.

### Good enough first implementation

For modules:
- use file content hash for now

For classes:
- hash a normalized object of:
  - kind
  - qualified name
  - base names
  - decorators

For callables:
- hash a normalized object of:
  - kind
  - qualified name
  - parameter names
  - parameter kinds
  - return annotation
  - decorators
  - async flag

### Why this matters

Later you want to tell the difference between:
- formatting change
- docstring change
- signature change
- structural change

Do not aim for perfection now.
Aim for useful signal.

---

## Content hash strategy for declarations

You have two options.

## Option A: Leave declaration `content_hash` blank for now

Pros:
- simpler
- less work

Cons:
- weaker incremental precision

## Option B: Slice declaration source from file text using `range`

Pros:
- more precise

Cons:
- slightly more work

My recommendation:
- if slicing is easy, do it
- otherwise leave a TODO and do it in a later phase

Do not block this phase on perfect declaration slicing.

---

## AST orchestration pipeline

Create one orchestrator that processes one file at a time.

Recommended flow:

1. load file text
2. parse AST
3. create module node
4. extract imports
5. extract top-level classes
6. extract top-level functions
7. for each class, extract methods
8. create `contains` edges
9. create `inherits` edges
10. update module payload with imported modules and top-level symbol IDs
11. persist nodes and edges

### Important rule

Keep file-level extraction isolated.
If one file fails to parse, you should be able to report that cleanly.

---

## Example pipeline sketch

```python
import ast
from pathlib import Path

def parse_python_file(file_path: Path) -> ast.Module:
    text = file_path.read_text(encoding="utf-8")
    return ast.parse(text)

def process_file(repo_id: str, file_record) -> tuple[list[dict], list[dict]]:
    file_path = Path(file_record.uri.replace("file://", ""))
    text = file_path.read_text(encoding="utf-8")
    tree = ast.parse(text)

    nodes = []
    edges = []

    module_node = extract_module_node(repo_id, file_record, tree, text)
    nodes.append(module_node)

    import_edges, imported_modules, imported_symbols = extract_import_edges(repo_id, module_node["id"], file_record, tree)
    edges.extend(import_edges)

    top_level_symbol_ids = []

    for item in tree.body:
        if isinstance(item, ast.ClassDef):
            class_node = extract_class_node(repo_id, file_record, module_node["id"], file_record.module_path, item)
            nodes.append(class_node)
            top_level_symbol_ids.append(class_node["id"])
            edges.append(make_contains_edge(repo_id, module_node["id"], class_node["id"], file_record, make_range(item)))
            edges.extend(extract_inherits_edges(repo_id, class_node["id"], file_record, item))

            method_ids = []
            for child in item.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    method_node = extract_callable_node(
                        repo_id=repo_id,
                        file_record=file_record,
                        parent_id=class_node["id"],
                        parent_qualified_name=class_node["qualified_name"],
                        node=child,
                        is_method=True,
                    )
                    nodes.append(method_node)
                    method_ids.append(method_node["id"])
                    edges.append(make_contains_edge(repo_id, class_node["id"], method_node["id"], file_record, make_range(child)))

            class_node["payload_json"]["method_ids"] = method_ids

        elif isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            callable_node = extract_callable_node(
                repo_id=repo_id,
                file_record=file_record,
                parent_id=module_node["id"],
                parent_qualified_name=file_record.module_path,
                node=item,
                is_method=False,
            )
            nodes.append(callable_node)
            top_level_symbol_ids.append(callable_node["id"])
            edges.append(make_contains_edge(repo_id, module_node["id"], callable_node["id"], file_record, make_range(item)))

    module_node["payload_json"]["imported_modules"] = sorted(set(imported_modules))
    module_node["payload_json"]["imported_symbols"] = sorted(set(imported_symbols))
    module_node["payload_json"]["top_level_symbol_ids"] = top_level_symbol_ids

    return nodes, edges
```

This is not the only implementation shape, but it shows the intended architecture.

---

## Persistence strategy

This phase needs node and edge persistence helpers.

Recommended functions in `storage/nodes.py`:

```python
def upsert_node(conn, node) -> None:
    ...

def upsert_nodes(conn, nodes: list) -> None:
    ...

def list_nodes_for_file(conn, file_id: str) -> list:
    ...
```

Recommended functions in `storage/edges.py`:

```python
def upsert_edge(conn, edge) -> None:
    ...

def upsert_edges(conn, edges: list) -> None:
    ...

def list_edges_for_repo(conn, repo_id: str) -> list:
    ...
```

### Optional cleanup in this phase

You may also add:

```python
def delete_nodes_for_file(conn, file_id: str) -> None:
    ...

def delete_edges_for_file(conn, file_id: str) -> None:
    ...
```

That becomes useful once reindexing the same file repeatedly.

---

## Failure handling

AST parsing can fail.

Examples:
- syntax errors
- weird encoding issues
- partially broken files

You need a policy.

## Recommended v1 policy

- fail the file cleanly
- record an extraction error
- continue with the rest of the repo if possible

Why:
- one broken file should not always destroy the whole repo index
- but the failure should be visible

Do not silently swallow parse errors.

---

## Test plan

This phase needs strong fixture-based tests.

## `test_module_extraction`

Verify:
- one module node per file
- correct module qualified name
- correct kind
- correct parent rules

## `test_class_extraction`

Verify:
- class nodes are created
- base names are captured
- decorators are captured
- class parent is the module

## `test_callable_extraction_top_level`

Verify:
- top-level functions become `function` or `async_function`
- qualified names are correct

## `test_callable_extraction_methods`

Verify:
- methods become `method` or `async_method`
- parent is the class
- qualified names are correct

## `test_contains_edges`

Verify:
- module -> class
- module -> top-level function
- class -> method

## `test_import_edges`

Verify:
- `import` and `from import` forms are captured
- module payload gets imported modules and imported symbols

## `test_inherits_edges`

Verify:
- declared bases become `inherits` edges

## `test_doc_summary_extraction`

Verify:
- doc summary comes from docstrings when present

## `test_range_extraction`

Verify:
- ranges are generated
- lines are converted to zero-based form

## `test_nested_functions_are_ignored`

If you choose to ignore nested functions, test that explicitly.

---

## Suggested test fixtures

Create tiny focused fixture repos like these:

```text
tests/fixtures/
  simple_package/
    app/
      __init__.py
      services/
        auth.py

  inheritance_case/
    app/
      services.py

  async_case/
    app/
      worker.py

  decorators_case/
    app/
      models.py

  nested_functions_case/
    app/
      helpers.py
```

### Example fixture content

#### `auth.py`

```python
"""Authentication services."""

from app.models.user import User

class AuthService(BaseService):
    """Main auth service."""

    def login(self, user_id: str, password: str) -> Session:
        """Authenticate and return a session."""
        return create_session(user_id)

def build_auth_payload(user_id: str) -> dict:
    return {"user_id": user_id}
```

This one file already gives you:
- module docstring
- import
- class
- inheritance
- method
- top-level function
- annotations

That is a perfect starter fixture.

---

## Acceptance checklist

Phase 3 is done when all of this is true:

- Python files can be parsed into AST safely.
- Each Python file becomes one module node.
- Top-level classes become class nodes.
- Top-level functions become callable nodes.
- Methods become method nodes.
- Async callables are classified correctly.
- Qualified names are deterministic.
- `contains` edges exist.
- `imports` edges exist.
- `inherits` edges exist.
- Basic doc summaries are extracted.
- Ranges and selection ranges are stored.
- Nodes and edges persist to SQLite.
- Broken files fail cleanly.
- Tests pass.
- No LSP integration exists yet.
- No `references` edges exist yet.
- No MCP tools exist yet.

---

## Common mistakes to avoid

### Mistake 1: Trying to make AST semantic

AST tells you structure, not full meaning.
Do not try to force perfect symbol resolution here.

### Mistake 2: Inconsistent qualified names

If naming rules vary across extractors, the graph becomes unreliable.

### Mistake 3: Storing unresolved imports as if they were resolved internal symbols

Be honest.
Use placeholders or payload metadata.

### Mistake 4: Mixing extraction and persistence too tightly

Keep AST extraction functions mostly pure.
Let orchestration or storage layers handle DB writes.

### Mistake 5: Supporting nested functions halfway

Either support them properly or ignore them explicitly for v1.

### Mistake 6: Skipping range normalization

If line numbers are inconsistent now, LSP mapping later will hurt.

---

## What phase 4 will depend on

The next phase will assume phase 3 already provides:

- persisted nodes
- persisted structural edges
- reliable qualified names
- parent-child hierarchy
- module, class, and callable layers

Phase 4 will focus on making graph storage and queries solid.
If extraction output is unstable, phase 4 will become cleanup work instead of progress.

---

## Final guidance

This phase is where the project becomes real.

Before phase 3, you only know which files exist.
After phase 3, you know the structural shape of the repository.

That is the big jump.

Keep the AST layer honest, deterministic, and boring:

- extract what Python AST can clearly tell you
- store unresolved things explicitly
- do not overpromise semantics
- do not jump ahead to LSP

If this phase is solid, the next layers become much easier.
```