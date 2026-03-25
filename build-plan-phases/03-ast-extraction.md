Absolutely. Here is the rigid checkbox version, written to leave as little room for interpretation as possible and to stay consistent with an already-built phase 1 and phase 2.

# 03 AST Extraction - Exact Implementation Checklist

## Objective

Implement phase 3 of the repository indexing pipeline.

Phase 3 must read Python files already discovered by phase 2, parse them with Python AST, extract structural symbols and structural relationships, and persist the result to SQLite.

Phase 3 must produce:
- module nodes
- class nodes
- callable nodes
- `contains` edges
- `imports` edges
- `inherits` edges

Phase 3 must not produce:
- LSP-based data
- `references` edges
- reverse reference mappings
- semantic call graphs
- risk scoring
- MCP tools
- watch mode

***

## Consistency Rules

These rules are mandatory.

- [ ] Reuse the existing phase 1 and phase 2 models, database schema style, naming style, and storage patterns.
- [ ] Do not invent a parallel model shape for nodes or edges.
- [ ] Do not rename existing model fields just for phase 3 convenience.
- [ ] Do not change phase 1 or phase 2 contracts unless absolutely required.
- [ ] If a helper already exists from earlier phases and fits the need, reuse it.
- [ ] If a helper does not exist, add it in the phase 3 parsing or storage modules only.
- [ ] Keep the same serialization style already used in the project for JSON fields.
- [ ] Keep the same SQLite access style already used in the project.
- [ ] Keep the same CLI or pipeline orchestration style already used in earlier phases.
- [ ] Keep behavior deterministic.

***

## Required Inputs

Phase 3 must consume these existing inputs:

- [ ] one `RepoRecord`
- [ ] Python `FileRecord` values already produced by phase 2
- [ ] repository root path
- [ ] file contents from disk
- [ ] SQLite database connection or the existing storage access layer

Do not add new required inputs for this phase.

***

## Required Outputs

Phase 3 must produce these outputs:

- [ ] `SymbolNode` record for each Python module
- [ ] `SymbolNode` record for each top-level class
- [ ] `SymbolNode` record for each top-level function
- [ ] `SymbolNode` record for each top-level async function
- [ ] `SymbolNode` record for each direct class method
- [ ] `SymbolNode` record for each direct async class method
- [ ] `Edge` record for each `contains` relationship
- [ ] `Edge` record for each `imports` relationship
- [ ] `Edge` record for each `inherits` relationship
- [ ] extraction errors or warnings for broken files
- [ ] summary counts of extracted nodes and edges

Do not output any new graph relationship kinds in this phase.

***

## Required File Layout

Create exactly these phase 3 modules if they do not already exist:

- [ ] `src/repo_context/parsing/__init__.py`
- [ ] `src/repo_context/parsing/ast_loader.py`
- [ ] `src/repo_context/parsing/naming.py`
- [ ] `src/repo_context/parsing/module_extractor.py`
- [ ] `src/repo_context/parsing/class_extractor.py`
- [ ] `src/repo_context/parsing/callable_extractor.py`
- [ ] `src/repo_context/parsing/import_extractor.py`
- [ ] `src/repo_context/parsing/inheritance_extractor.py`
- [ ] `src/repo_context/parsing/ranges.py`
- [ ] `src/repo_context/parsing/docstrings.py`
- [ ] `src/repo_context/parsing/pipeline.py`
- [ ] `src/repo_context/storage/nodes.py`
- [ ] `src/repo_context/storage/edges.py`

Do not create extra phase-3-specific packages unless strictly necessary.

***

## Symbol Kinds

Use exactly these `kind` values and no others:

- [ ] `module`
- [ ] `class`
- [ ] `function`
- [ ] `async_function`
- [ ] `method`
- [ ] `async_method`

Do not add:
- nested function kinds
- property kinds
- static method kinds
- classmethod kinds
- decorator kinds

Those can be added in later phases if needed.

***

## Identity Rules

Apply these ID rules exactly.

### Module node ID

- [ ] format is `sym:{repo_id}:module:{module_path}`

Example:
```text
sym:repo:project:module:app.services.auth
```

### Class node ID

- [ ] format is `sym:{repo_id}:class:{qualified_name}`

Example:
```text
sym:repo:project:class:app.services.auth.AuthService
```

### Callable node ID

- [ ] format is `sym:{repo_id}:{kind}:{qualified_name}`

Example:
```text
sym:repo:project:method:app.services.auth.AuthService.login
```

### Edge IDs

- [ ] `contains` edges must use a deterministic ID derived from repo id, edge kind, parent id, and child id
- [ ] `imports` edges must use a deterministic ID derived from repo id, edge kind, module node id, unresolved target, and line number when needed for uniqueness
- [ ] `inherits` edges must use a deterministic ID derived from repo id, edge kind, class node id, and base name

Do not use random IDs.

***

## Qualified Name Rules

Apply these naming rules exactly.

- [ ] module qualified name = `file_record.module_path`
- [ ] class qualified name = `{module_path}.{class_name}`
- [ ] top-level function qualified name = `{module_path}.{function_name}`
- [ ] method qualified name = `{class_qualified_name}.{method_name}`

Do not vary this between extractors.

***

## Nested Function Policy

Apply this rule exactly:

- [ ] ignore nested functions in version 1
- [ ] do not create nodes for nested functions
- [ ] do not create edges for nested functions
- [ ] do not partially support nested functions

This must be tested explicitly.

***

## AST Coverage

Only use these AST node types as first-class extraction targets:

- [ ] `ast.Module`
- [ ] `ast.ClassDef`
- [ ] `ast.FunctionDef`
- [ ] `ast.AsyncFunctionDef`
- [ ] `ast.Import`
- [ ] `ast.ImportFrom`

Inspect these attributes where relevant:

- [ ] `decorator_list`
- [ ] `bases`
- [ ] `args`
- [ ] `returns`

Do not expand scope to broader semantic analysis.

***

## Step 1 - AST Loader

### File

- [ ] `src/repo_context/parsing/ast_loader.py`

### Implement

- [ ] read file content from disk using UTF-8
- [ ] return file text as a string
- [ ] parse file text with `ast.parse`
- [ ] return parsed `ast.Module`
- [ ] surface read failures explicitly
- [ ] surface syntax failures explicitly

### Do not do

- [ ] do not silently ignore parse errors
- [ ] do not persist anything in this module
- [ ] do not mutate database state here

### Done when

- [ ] valid Python file returns text and AST
- [ ] invalid Python file returns a clear failure the pipeline can record

***

## Step 2 - Naming Helpers

### File

- [ ] `src/repo_context/parsing/naming.py`

### Implement

- [ ] helper to build module qualified name
- [ ] helper to build class qualified name
- [ ] helper to build top-level callable qualified name
- [ ] helper to build method qualified name
- [ ] helper to build module node ID
- [ ] helper to build class node ID
- [ ] helper to build callable node ID

### Do not do

- [ ] do not duplicate naming logic in extractor modules
- [ ] do not invent alternative naming schemes

### Done when

- [ ] all phase 3 extractors can use one shared naming source
- [ ] same input always yields same output

***

## Step 3 - Range Helpers

### File

- [ ] `src/repo_context/parsing/ranges.py`

### Implement

- [ ] `to_zero_based_line(line)`
- [ ] `make_position(line, character)`
- [ ] `make_range(node)`
- [ ] `make_name_selection_range(node)`

### Exact behavior

- [ ] convert AST one-based line numbers to zero-based line numbers
- [ ] preserve character offsets as provided by AST
- [ ] `make_range(node)` must use `lineno`, `col_offset`, `end_lineno`, and `end_col_offset` when present
- [ ] `make_name_selection_range(node)` must return a narrower name-focused range for `ClassDef`, `FunctionDef`, and `AsyncFunctionDef`
- [ ] if exact name token bounds are difficult, return a consistent approximation based on declaration start
- [ ] if required location metadata is missing, return `None`

### Do not do

- [ ] do not mix one-based and zero-based lines anywhere in persisted output

### Done when

- [ ] all extracted declarations can store normalized location data consistently

***

## Step 4 - Docstring Helper

### File

- [ ] `src/repo_context/parsing/docstrings.py`

### Implement

- [ ] `get_doc_summary(node)`

### Exact behavior

- [ ] call `ast.get_docstring(node)`
- [ ] strip leading and trailing whitespace
- [ ] split into meaningful chunks
- [ ] return the first non-empty short paragraph or first meaningful line
- [ ] return `None` if docstring is missing or empty

### Do not do

- [ ] do not generate summaries
- [ ] do not return the full docstring unless it is already only one short meaningful chunk

### Done when

- [ ] module, class, and callable extractors can use one shared doc summary helper

***

## Step 5 - Module Extraction

### File

- [ ] `src/repo_context/parsing/module_extractor.py`

### Implement

For each parsed Python file:

- [ ] create exactly one module node
- [ ] set `kind` to `module`
- [ ] set `parent_id` to `None`
- [ ] derive `qualified_name` from `file_record.module_path`
- [ ] derive `name` from the last component of `module_path`, or fallback to file path if needed
- [ ] set `language` to `python`
- [ ] set `uri` from `file_record.uri`
- [ ] set `doc_summary` from the module AST node
- [ ] set `content_hash` from `file_record.content_hash`
- [ ] set initial `semantic_hash` equal to `file_record.content_hash`
- [ ] set `source` to `python-ast`
- [ ] set `confidence` to `1.0`
- [ ] set `last_indexed_at` from `file_record.last_indexed_at`

### Required module range behavior

- [ ] module `range_json` must cover the full file
- [ ] module `selection_range_json` may point to line 0 character 0 as a consistent placeholder in v1

### Required module payload

- [ ] `file_path`
- [ ] `module_path`
- [ ] `package_path`
- [ ] `imported_modules`
- [ ] `imported_symbols`
- [ ] `top_level_symbol_ids`

### Do not do

- [ ] do not create more than one module node per file
- [ ] do not leave module payload keys missing

### Done when

- [ ] every parsed Python file produces exactly one persisted-ready module node

***

## Step 6 - Class Extraction

### File

- [ ] `src/repo_context/parsing/class_extractor.py`

### Implement

For each top-level `ast.ClassDef` in `tree.body`:

- [ ] create one class node
- [ ] derive class qualified name from module path plus class name
- [ ] derive class node ID from class qualified name
- [ ] set `parent_id` to module node ID
- [ ] set `kind` to `class`
- [ ] set `name` to class name
- [ ] set `language` to `python`
- [ ] set `uri` from `file_record.uri`
- [ ] set `range_json` from `make_range(node)`
- [ ] set `selection_range_json` from `make_name_selection_range(node)`
- [ ] set `doc_summary` from `get_doc_summary(node)`
- [ ] set `source` to `python-ast`
- [ ] set `confidence` to `1.0`
- [ ] set `last_indexed_at` from `file_record.last_indexed_at`

### Required class payload

- [ ] `base_names` as a list of strings produced with `ast.unparse`
- [ ] `decorators` as a list of strings produced with `ast.unparse`
- [ ] `method_ids` initialized as an empty list

### Visibility rule

- [ ] set `visibility_hint` to `private_like` if class name starts with `_`
- [ ] otherwise set `visibility_hint` to `public`

### Do not do

- [ ] do not inspect nested classes in v1
- [ ] do not build fancy base or decorator formatting logic

### Done when

- [ ] every top-level class produces one persisted-ready class node

***

## Step 7 - Callable Extraction

### File

- [ ] `src/repo_context/parsing/callable_extractor.py`

### Implement

Support these mappings:

- [ ] top-level `FunctionDef` -> `function`
- [ ] top-level `AsyncFunctionDef` -> `async_function`
- [ ] direct class `FunctionDef` -> `method`
- [ ] direct class `AsyncFunctionDef` -> `async_method`

For each callable node:

- [ ] derive `kind` exactly from async status and method status
- [ ] derive `qualified_name` using shared naming helpers
- [ ] derive node ID using shared naming helpers
- [ ] set `parent_id` to module node ID for top-level callables
- [ ] set `parent_id` to class node ID for methods
- [ ] set `name` to callable name
- [ ] set `language` to `python`
- [ ] set `uri` from `file_record.uri`
- [ ] set `range_json` from `make_range(node)`
- [ ] set `selection_range_json` from `make_name_selection_range(node)`
- [ ] set `doc_summary` from `get_doc_summary(node)`
- [ ] set `source` to `python-ast`
- [ ] set `confidence` to `1.0`
- [ ] set `last_indexed_at` from `file_record.last_indexed_at`

### Required callable payload

- [ ] `parameters`
- [ ] `return_annotation`
- [ ] `decorators`
- [ ] `is_async`
- [ ] `is_method`
- [ ] `is_generator`

### Generator rule

- [ ] set `is_generator` to `True` if `ast.walk(node)` contains `ast.Yield` or `ast.YieldFrom`
- [ ] otherwise set `is_generator` to `False`

### Visibility rule

- [ ] if callable name starts with `_` and is not a dunder, set `visibility_hint` to `private_like`
- [ ] otherwise set `visibility_hint` to `public`

### Do not do

- [ ] do not create nodes for nested functions
- [ ] do not create extra callable kinds in v1

### Done when

- [ ] top-level functions and direct methods both produce correct persisted-ready callable nodes

***

## Step 8 - Parameter Extraction

### File

- [ ] `src/repo_context/parsing/callable_extractor.py`

### Implement

Extract parameters from `ast.arguments`.

Each parameter record must include:

- [ ] `name`
- [ ] `kind`
- [ ] `annotation`
- [ ] `default_value_hint`

### Exact supported kinds

- [ ] positional-only args -> `positional_only`
- [ ] regular args -> `positional_or_keyword`
- [ ] `*args` -> `var_positional`
- [ ] keyword-only args -> `keyword_only`
- [ ] `**kwargs` -> `var_keyword`

### Exact annotation behavior

- [ ] if annotation exists, convert using `ast.unparse`
- [ ] if annotation does not exist, store `None`

### Exact default behavior

- [ ] in v1, `default_value_hint` may always be `None`
- [ ] do not pretend defaults are mapped if they are not

### Return annotation behavior

- [ ] if callable return annotation exists, convert using `ast.unparse`
- [ ] otherwise store `None`

### Do not do

- [ ] do not overbuild parameter-default alignment in this phase

### Done when

- [ ] every callable payload contains consistent structured parameter data

***

## Step 9 - Contains Edge Creation

### File

- [ ] `src/repo_context/parsing/pipeline.py` or shared helper used by pipeline

### Implement

Create `contains` edges for these exact relationships:

- [ ] module -> class
- [ ] module -> top-level callable
- [ ] class -> direct method

### Required edge fields

- [ ] deterministic edge ID
- [ ] `repo_id`
- [ ] `kind="contains"`
- [ ] `from_id`
- [ ] `to_id`
- [ ] `source="python-ast"`
- [ ] `confidence=1.0`
- [ ] `evidence_file_id`
- [ ] `evidence_uri`
- [ ] `evidence_range_json`
- [ ] `payload_json`
- [ ] `last_indexed_at`

### Do not do

- [ ] do not infer containment beyond direct AST structure

### Done when

- [ ] every structural parent-child relation in scope is represented as a `contains` edge

***

## Step 10 - Import Extraction

### File

- [ ] `src/repo_context/parsing/import_extractor.py`

### Implement

Walk the AST and process all:

- [ ] `ast.Import`
- [ ] `ast.ImportFrom`

### Exact import collection behavior

For `ast.Import`:
- [ ] append each `alias.name` to module payload `imported_modules`
- [ ] create one `imports` edge per imported module

For `ast.ImportFrom`:
- [ ] if `node.module` exists, append it to module payload `imported_modules`
- [ ] append each imported symbol name to module payload `imported_symbols`
- [ ] create one `imports` edge per imported symbol

### Exact unresolved target rules

For plain imports:
- [ ] use `external_or_unresolved:{module_name}`

For from imports:
- [ ] if module exists, use `external_or_unresolved:{module_name}.{symbol_name}`
- [ ] if module does not exist, use `external_or_unresolved:{symbol_name}`

### Required imports edge fields

- [ ] deterministic edge ID
- [ ] `kind="imports"`
- [ ] `from_id` = module node ID
- [ ] unresolved `to_id`
- [ ] `source="python-ast"`
- [ ] `confidence=0.8`
- [ ] evidence metadata
- [ ] payload containing alias and import metadata

### Relative import behavior

- [ ] store `level` from `ImportFrom.level` in payload
- [ ] store `module` from `ImportFrom.module` in payload

### Do not do

- [ ] do not resolve imports to internal graph nodes in this phase
- [ ] do not pretend unresolved imports are resolved

### Done when

- [ ] imports are captured in module payload and as `imports` edges

***

## Step 11 - Inheritance Extraction

### File

- [ ] `src/repo_context/parsing/inheritance_extractor.py`

### Implement

For each top-level class node:

- [ ] iterate over `node.bases`
- [ ] convert each base to string using `ast.unparse`
- [ ] create one `inherits` edge per base

### Exact unresolved target rule

- [ ] `to_id` must be `unresolved_base:{base_name}`

### Required inherits edge fields

- [ ] deterministic edge ID
- [ ] `kind="inherits"`
- [ ] `from_id` = class node ID
- [ ] unresolved `to_id`
- [ ] `source="python-ast"`
- [ ] `confidence=0.75`
- [ ] evidence metadata
- [ ] payload with `base_name`
- [ ] `last_indexed_at`

### Do not do

- [ ] do not attempt full inheritance resolution in this phase

### Done when

- [ ] every declared base class produces one `inherits` edge

***

## Step 12 - Semantic Hashes

### Files

- [ ] extractor modules or one shared helper module

### Implement

### Module semantic hash
- [ ] set equal to `file_record.content_hash` in v1

### Class semantic hash
Hash a normalized object containing:
- [ ] `kind`
- [ ] `qualified_name`
- [ ] `base_names`
- [ ] `decorators`

### Callable semantic hash
Hash a normalized object containing:
- [ ] `kind`
- [ ] `qualified_name`
- [ ] parameter names
- [ ] parameter kinds
- [ ] return annotation
- [ ] decorators
- [ ] async flag

### Do not do

- [ ] do not leave semantic hash undefined
- [ ] do not block phase 3 trying to perfect this

### Done when

- [ ] semantic hashes are deterministic and structurally meaningful

***

## Step 13 - Declaration Content Hash Policy

### Files

- [ ] extractor modules or one shared helper module

### Implement

Choose one consistent policy:

Policy A:
- [ ] set declaration `content_hash` to empty string for class and callable nodes

Policy B:
- [ ] slice source text for the declaration using extracted range
- [ ] hash the sliced declaration text
- [ ] store the result as declaration `content_hash`

### Required rule

- [ ] choose one policy and apply it consistently to all declaration nodes in this phase

### Do not do

- [ ] do not mix policies unpredictably
- [ ] do not fabricate content hashes

### Done when

- [ ] declaration content hash behavior is explicit and consistent

***

## Step 14 - Per-File Pipeline

### File

- [ ] `src/repo_context/parsing/pipeline.py`

### Implement

For each Python file record, execute these exact steps in order:

- [ ] load file text
- [ ] parse AST
- [ ] create module node
- [ ] extract import edges and import payload data
- [ ] extract top-level class nodes
- [ ] for each class node, create module -> class `contains` edge
- [ ] for each class node, extract `inherits` edges
- [ ] for each class body direct callable, extract method node
- [ ] for each method node, create class -> method `contains` edge
- [ ] extract top-level callable nodes
- [ ] for each top-level callable node, create module -> callable `contains` edge
- [ ] update class payload `method_ids`
- [ ] update module payload `imported_modules`
- [ ] update module payload `imported_symbols`
- [ ] update module payload `top_level_symbol_ids`
- [ ] persist all nodes
- [ ] persist all edges

### Exact isolation rule

- [ ] one file must be processable independently of every other file
- [ ] one file failure must not prevent other files from being processed

### Do not do

- [ ] do not process nested functions
- [ ] do not mix repo-wide semantic resolution into this pipeline

### Done when

- [ ] one file run yields complete structural output for that file only

***

## Step 15 - Node Persistence

### File

- [ ] `src/repo_context/storage/nodes.py`

### Implement

- [ ] `upsert_node(conn, node)`
- [ ] `upsert_nodes(conn, nodes)`
- [ ] `list_nodes_for_file(conn, file_id)`

Optional:
- [ ] `delete_nodes_for_file(conn, file_id)`

### Exact persistence behavior

- [ ] use the existing database schema style from earlier phases
- [ ] insert new nodes
- [ ] update existing nodes by stable ID
- [ ] preserve JSON serialization consistency with existing project code

### Do not do

- [ ] do not change the schema style established by earlier phases
- [ ] do not make storage functions depend on AST internals

### Done when

- [ ] nodes can be inserted, updated, and listed for one file consistently

***

## Step 16 - Edge Persistence

### File

- [ ] `src/repo_context/storage/edges.py`

### Implement

- [ ] `upsert_edge(conn, edge)`
- [ ] `upsert_edges(conn, edges)`
- [ ] `list_edges_for_repo(conn, repo_id)`

Optional:
- [ ] `delete_edges_for_file(conn, file_id)`

### Exact persistence behavior

- [ ] use the existing database schema style from earlier phases
- [ ] insert new edges
- [ ] update existing edges by stable ID
- [ ] preserve JSON serialization consistency with existing project code

### Do not do

- [ ] do not change the schema style established by earlier phases
- [ ] do not make storage functions depend on AST internals

### Done when

- [ ] edges can be inserted, updated, and listed consistently

***

## Step 17 - Failure Handling

### File

- [ ] `src/repo_context/parsing/pipeline.py`
- [ ] any existing result-reporting or run-reporting code already used by the project

### Implement

When a file cannot be read or parsed:

- [ ] mark that file as failed
- [ ] record why it failed
- [ ] continue processing the remaining files if possible

### Required behavior

- [ ] failure must be visible
- [ ] failure must not be silently swallowed
- [ ] one broken file must not destroy the whole repo run by default

### Do not do

- [ ] do not silently skip broken files

### Done when

- [ ] the indexing run can finish with partial success and visible failures

***

## Step 18 - Test Fixtures

### Files to create

Create fixture repos under `tests/fixtures/`.

Minimum fixture set:

- [ ] `tests/fixtures/simple_package/`
- [ ] `tests/fixtures/inheritance_case/`
- [ ] `tests/fixtures/async_case/`
- [ ] `tests/fixtures/decorators_case/`
- [ ] `tests/fixtures/nested_functions_case/`

### Fixture requirements

At least one fixture must include:

- [ ] module docstring
- [ ] import statement
- [ ] top-level class
- [ ] declared base class
- [ ] direct method
- [ ] top-level function
- [ ] annotations

### Do not do

- [ ] do not use large real repos as the main test input
- [ ] do not hide many cases in one giant fixture

### Done when

- [ ] fixtures are small, focused, and deterministic

***

## Step 19 - Tests

### Files to create or modify

- [ ] phase 3 tests under `tests/`

### Implement these tests

- [ ] `test_module_extraction`
- [ ] `test_class_extraction`
- [ ] `test_callable_extraction_top_level`
- [ ] `test_callable_extraction_methods`
- [ ] `test_contains_edges`
- [ ] `test_import_edges`
- [ ] `test_inherits_edges`
- [ ] `test_doc_summary_extraction`
- [ ] `test_range_extraction`
- [ ] `test_nested_functions_are_ignored`

### Exact test assertions

#### Module extraction
- [ ] one module node is created per Python file
- [ ] module kind is `module`
- [ ] module qualified name matches `module_path`
- [ ] module parent is `None`

#### Class extraction
- [ ] class nodes are created for top-level classes only
- [ ] class base names are captured
- [ ] class decorators are captured
- [ ] class parent is module node ID

#### Callable extraction
- [ ] top-level sync functions become `function`
- [ ] top-level async functions become `async_function`
- [ ] direct class sync methods become `method`
- [ ] direct class async methods become `async_method`
- [ ] qualified names are correct

#### Contains edges
- [ ] module -> class exists
- [ ] module -> top-level callable exists
- [ ] class -> method exists

#### Import edges
- [ ] plain imports are captured
- [ ] from imports are captured
- [ ] imported modules appear in module payload
- [ ] imported symbols appear in module payload

#### Inherits edges
- [ ] each declared base creates one `inherits` edge

#### Doc summary
- [ ] first meaningful doc chunk is extracted
- [ ] missing docstring yields `None`

#### Range extraction
- [ ] line numbers are zero-based
- [ ] range and selection range exist where expected

#### Nested functions
- [ ] nested functions do not produce nodes
- [ ] nested functions do not produce edges

### Done when

- [ ] all required phase 3 extraction behavior is covered by tests

***

## Step 20 - Final Verification

Before marking phase 3 complete, verify all of the following:

- [ ] Python files parse safely into AST
- [ ] each Python file becomes one module node
- [ ] top-level classes become class nodes
- [ ] top-level functions become callable nodes
- [ ] direct class methods become method nodes
- [ ] async callables are classified correctly
- [ ] qualified names are deterministic
- [ ] `contains` edges exist
- [ ] `imports` edges exist
- [ ] `inherits` edges exist
- [ ] doc summaries are extracted
- [ ] ranges are stored
- [ ] selection ranges are stored
- [ ] nodes persist to SQLite
- [ ] edges persist to SQLite
- [ ] broken files fail cleanly
- [ ] tests pass
- [ ] no LSP integration exists
- [ ] no `references` edges exist
- [ ] no MCP tools exist

Do not mark this phase done until every box above is true.

***

## Required Execution Order

Implement in this order and do not skip ahead:

- [ ] Step 1 AST loader
- [ ] Step 2 naming helpers
- [ ] Step 3 range helpers
- [ ] Step 4 docstring helper
- [ ] Step 5 module extraction
- [ ] Step 6 class extraction
- [ ] Step 7 callable extraction
- [ ] Step 8 parameter extraction
- [ ] Step 9 contains edge creation
- [ ] Step 10 import extraction
- [ ] Step 11 inheritance extraction
- [ ] Step 12 semantic hashes
- [ ] Step 13 declaration content hash policy
- [ ] Step 14 per-file pipeline
- [ ] Step 15 node persistence
- [ ] Step 16 edge persistence
- [ ] Step 17 failure handling
- [ ] Step 18 test fixtures
- [ ] Step 19 tests
- [ ] Step 20 final verification

***

## Phase 3 Done Definition

Phase 3 is complete only when all of these are true:

- [ ] phase 1 and phase 2 contracts remain intact
- [ ] Python files discovered in phase 2 can be parsed in phase 3
- [ ] structural symbols are extracted deterministically
- [ ] structural edges are extracted deterministically
- [ ] unresolved imports and bases remain explicit
- [ ] nodes and edges are persisted consistently with the existing project style
- [ ] broken files fail visibly without collapsing the full run
- [ ] tests pass
- [ ] no out-of-scope features were added

If you want, next I can do the same rigid no-interpretation rewrite for phase 4 too, so the whole plan stays in one consistent format.