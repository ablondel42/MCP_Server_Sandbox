# 03b-nested-scope-support.md


## Purpose


This phase adds the minimum useful nested-scope support between AST extraction and graph persistence.


The goal is not full compiler-grade scope analysis.
The goal is to preserve nested declarations as first-class symbols so later phases do not lose important structure.


In plain language:


- nested functions become real symbols
- nested async functions become real symbols
- local classes become real symbols
- lexical parents are tracked explicitly
- qualified names include nesting
- graph storage receives nested-aware extraction output


This phase is the bridge between basic AST extraction and correct graph modeling for local declarations.


---


## Why this phase matters


Without this phase, nested declarations either disappear or get flattened badly.


That creates obvious problems:


- local helper logic is missing from the graph
- outer-function context is incomplete
- later reference resolution becomes harder
- risk analysis underestimates some changes
- symbol identity becomes inconsistent if you retrofit nesting later


Python uses statically nested lexical scopes, and names are resolved through enclosing function scopes while skipping class scopes. [web:607][web:651]


This means nested functions are not optional noise if you want accurate code intelligence.


---


## Phase goals


By the end of this phase, you should have:


- extraction support for nested `def`
- extraction support for nested `async def`
- extraction support for local `class` inside a function
- explicit lexical parent tracking during AST traversal
- stable symbol IDs for nested declarations
- stable qualified names for nested declarations
- scope metadata on extracted symbols
- lexical parent metadata on extracted symbols
- `SCOPE_PARENT` structural edges in extracted output
- graph persistence support for the new symbol fields and edge type
- a deterministic duplicate-name policy for same-scope declarations
- a compatibility audit for old symbol-kind filters
- tests for nested declaration extraction and persistence


---


## Phase non-goals


Do **not** do any of this in phase 03b:


- perfect closure-capture analysis
- full variable binding graphs
- `nonlocal` semantics beyond future-proof model design
- `global` rebinding analysis
- LSP-based nested reference resolution
- risk-engine weighting changes
- MCP tool changes
- watch-mode changes


This phase is declaration extraction and graph-shape support, not full scope semantics.


---


## What already exists from previous phases


This phase assumes you already have:


- repository scanning
- file loading
- Python AST parsing
- base symbol extraction
- graph storage design or early graph persistence


This phase changes the contract between extraction and graph storage.
It should happen before graph persistence is treated as stable.


---


## Core design principle


Treat nested declarations as first-class symbols with local scope.


That means:


- they get real symbol records
- they get real symbol IDs
- they get real parent relationships
- they are queryable
- they are not treated as module-level public API by default


Python AST already exposes nested declaration structure through nodes such as `FunctionDef`, `AsyncFunctionDef`, and `ClassDef`, so extraction should preserve that lexical hierarchy directly. [web:634][web:643]


---


## Minimum supported declarations


For v1, support exactly these nested declarations:


- nested `def`
- nested `async def`
- local `class` inside a function


You may support nested classes inside class bodies too if it is already easy, but that is optional for this phase.


Do not broaden scope further yet.


---


## Core model changes


Yes, you need model changes.


Minimum required changes:


- add `local_function` to symbol kinds
- add `local_async_function` to symbol kinds
- add `scope` to symbol model
- add `lexical_parent_id` to symbol model
- add `SCOPE_PARENT` to structural edge types
- update qualified-name construction for nested declarations


That is the minimum useful set.
Anything less becomes hacky fast.


---


## Symbol field rules


You need explicit symbol-field semantics.


### Required fields


- `name`: raw declaration name, such as `inner`
- `qualified_name`: full lexical path, such as `app.jobs.run.inner`
- `scope`: one of `module`, `function`, `class`
- `lexical_parent_id`: immediate lexical parent symbol ID or `null`


### Required rules


- `name` is local and short
- `qualified_name` is stable and path-based
- `scope` describes where the declaration lives
- `lexical_parent_id` points to the immediate lexical declaration parent


Do not blur `name` and `qualified_name`.
You will regret that later in query code, adapters, and persistence.


---


## Symbol kind rules


Use these exact rules.


### Existing kinds retained


- `function`
- `async_function`
- `class`
- `method`
- `async_method`


### New kinds


- `local_function`
- `local_async_function`


### Classification rules


- module-level `def` -> `function`
- module-level `async def` -> `async_function`
- `def` inside function or method -> `local_function`
- `async def` inside function or method -> `local_async_function`
- `def` inside class body -> `method`
- `async def` inside class body -> `async_method`
- `class` inside function or method -> `class` with local function scope


### Important rule


A function inside a method is still a local function, not a method, because it is nested in a function scope at runtime, not declared directly on the class. Python nested-scope lookup is based on enclosing function scopes, and class scopes are skipped during free-name resolution. [web:607][web:651]


---


## Scope model


Add a `scope` field to symbols.


### Recommended values


- `module`
- `function`
- `class`


### Exact rules


- module-level functions and classes -> `scope = "module"`
- local functions and local classes inside functions -> `scope = "function"`
- methods and class-body symbols -> `scope = "class"`


Do not overcomplicate the scope enum in this phase.


---


## Lexical parent model


Add `lexical_parent_id` to symbols.


### Exact rules


- module-level declarations -> `lexical_parent_id = null`
- nested function -> parent is containing function or method symbol
- local class -> parent is containing function or method symbol
- method in local class -> parent is that class symbol


This field is required because later phases will need fast parent lookup without rebuilding scope from raw AST every time.


---


## Structural edge changes


Add one new edge type:


- `SCOPE_PARENT`


### Exact meaning


- `from_id` = nested declaration
- `to_id` = immediate lexical parent declaration


### Important rule


`SCOPE_PARENT` is lexical nesting only.
It is **not** a generic containment edge, **not** inheritance, and **not** call hierarchy.


### Examples


- local function -> outer function
- local async function -> outer function
- local class -> outer function
- method in local class -> local class


### Why this edge matters


A generic containment edge is too vague.
You need one edge that explicitly means lexical nesting so later context and reference logic can use it cleanly. Symbol-table designs for nested scopes typically rely on parent scope chains for lookup and recovery. [web:635][web:649]


---


## Qualified name rules


Nested declarations need stable qualified names.


### Required rule


Qualified names must include the lexical declaration path.


### Examples


- `app.jobs.run`
- `app.jobs.run.helper`
- `app.jobs.run.helper.inner`
- `app.jobs.run.LocalFormatter`
- `app.jobs.run.LocalFormatter.format`


### Construction rule


Build qualified names from:


1. module path
2. lexical declaration chain from outermost to innermost
3. current declaration name


### Important rule


Do not invent line-number-based names unless same-scope duplicate declarations force internal disambiguation.
Keep the visible qualified-name format clean and deterministic.


---


## Duplicate declaration policy


You need an explicit rule for duplicate names in the same lexical scope.


### Problem example


```python
def outer():
    def inner():
        ...
    def inner():
        ...
```


Python allows later declarations to shadow earlier ones in the same scope, so AST extraction may see multiple declarations with the same lexical path. [web:647][web:649]


### Required rule


Use this policy:


- keep `qualified_name` human-clean
- detect same-scope duplicate declarations during extraction
- if duplicates exist in the same lexical scope, preserve both symbols
- use a deterministic internal disambiguator for symbol identity only


### Recommended internal identity strategy


Any one of these is acceptable:


- append source-span suffix in symbol ID only
- append ordinal declaration index in symbol ID only
- include start line and column in symbol ID only


### Important rule


Do **not** pollute `qualified_name` first if you can avoid it.
Prefer a clean qualified name plus an internal ID disambiguator.


---


## Symbol ID rules


Nested declarations must have stable symbol IDs.


### Recommended base shape


```text
sym:{repo_id}:{kind}:{qualified_name}
```


### If same-scope duplicate exists


Use a deterministic suffix for ID only, for example:


```text
sym:{repo_id}:{kind}:{qualified_name}:line{lineno}:col{col}
```


### Examples


```text
sym:repo:project:local_function:app.jobs.run.helper
sym:repo:project:local_async_function:app.jobs.run.worker.fetch
sym:repo:project:local_function:app.jobs.run.inner:line12:col4
```


### Required rule


The ID must include the new local-function kind so nested callables are not conflated with module-level ones.


---


## AST traversal rules


This phase belongs mainly in the extractor.


Python AST represents nested declarations hierarchically through nodes like `FunctionDef`, `AsyncFunctionDef`, and `ClassDef`, so the extractor should maintain a declaration stack during traversal. [web:634][web:643]


### Required extractor state


Add:


- declaration stack
- current module path
- current file ID
- helper for current lexical parent
- helper for current scope kind


### Required traversal rule


When entering a declaration:


1. determine enclosing declaration state
2. classify symbol kind
3. assign scope
4. assign lexical parent
5. build qualified name
6. build symbol ID
7. emit symbol
8. emit `SCOPE_PARENT` edge if parent exists
9. push declaration onto stack
10. visit child body
11. pop declaration after exit


Do not try to reconstruct lexical parent relationships after traversal.


---


## Function extraction rules


For every `FunctionDef` and `AsyncFunctionDef`, apply these rules:


### Module scope


- `FunctionDef` -> `function`
- `AsyncFunctionDef` -> `async_function`
- `scope = "module"`
- `lexical_parent_id = null`


### Function scope


- `FunctionDef` -> `local_function`
- `AsyncFunctionDef` -> `local_async_function`
- `scope = "function"`
- `lexical_parent_id = immediate containing function or method`


### Class scope


- `FunctionDef` -> `method`
- `AsyncFunctionDef` -> `async_method`
- `scope = "class"`
- `lexical_parent_id = enclosing class`


### Important edge case


If a method contains a nested function, that nested function must be treated as `local_function` with the method as lexical parent.


---


## Class extraction rules


For every `ClassDef`, apply these rules:


### Module scope


- `kind = "class"`
- `scope = "module"`
- `lexical_parent_id = null`


### Function scope


- `kind = "class"`
- `scope = "function"`
- `lexical_parent_id = containing function or method`


### Class scope


Optional in this phase.
If already supported cleanly:
- `kind = "class"`
- `scope = "class"`
- `lexical_parent_id = enclosing class`


If not, document it and skip it for now.


---


## Extraction output contract


By the end of this phase, extracted file output must include:


- nested-aware symbols
- `scope` on every declaration symbol
- `lexical_parent_id` on every declaration symbol
- stable nested qualified names
- stable symbol IDs
- `SCOPE_PARENT` edges
- existing structural symbols and edges unchanged where possible


Do not leave phase 4 to infer any of this.


---


## Recommended package structure changes


Update or add these files as needed:


```text
src/
  repo_context/
    extraction/
      models.py
      visitor.py
      naming.py
      edges.py
```


And tests:


```text
tests/
  extraction/
    test_nested_symbols.py
  graph/
    test_nested_symbol_persistence.py
```


Keep the responsibility split clean.


---


## Step 1: Update extraction models


### Files


- [ ] `src/repo_context/extraction/models.py`
- [ ] any shared enums/constants module


### Implement


- [ ] add `local_function`
- [ ] add `local_async_function`
- [ ] add `scope` to symbol model
- [ ] add `lexical_parent_id` to symbol model
- [ ] add `SCOPE_PARENT` to edge-type enum/constants


### Validation rules


- [ ] module-level declarations must have `lexical_parent_id = null`
- [ ] local functions must not have `scope = "module"`
- [ ] methods must not have `scope = "function"`
- [ ] declaration symbols must always have a valid `scope`


### Done when


- [ ] the extraction model can represent nested declarations cleanly


---


## Step 2: Add lexical declaration stack


### Files


- [ ] `src/repo_context/extraction/visitor.py`


### Implement


Add extractor state for:


- [ ] declaration stack
- [ ] current lexical parent helper
- [ ] current scope helper
- [ ] nested qualified-name builder hook


### Rules


- [ ] push on declaration entry
- [ ] pop on declaration exit
- [ ] stack must reflect exact lexical nesting


### Done when


- [ ] the visitor always knows the immediate parent declaration and current scope kind


---


## Step 3: Update function extraction


### Files


- [ ] `src/repo_context/extraction/visitor.py`


### Implement


For `FunctionDef` and `AsyncFunctionDef`:


- [ ] inspect current enclosing scope
- [ ] classify kind correctly
- [ ] assign `scope`
- [ ] assign `lexical_parent_id`
- [ ] build nested qualified name
- [ ] build symbol ID
- [ ] emit symbol
- [ ] emit `SCOPE_PARENT` edge when parent exists


### Required rules


- [ ] nested inside function -> local function kind
- [ ] nested inside method -> local function kind
- [ ] nested inside class body -> method kind


### Done when


- [ ] nested callables are emitted correctly and deterministically


---


## Step 4: Update class extraction


### Files


- [ ] `src/repo_context/extraction/visitor.py`


### Implement


For `ClassDef`:


- [ ] if parent is module, emit module class
- [ ] if parent is function or method, emit local class with `scope = "function"`
- [ ] if parent is class, support nested class only if already easy and stable


### Required behavior


- [ ] methods inside local classes still attach to that class
- [ ] local classes get `lexical_parent_id` set to enclosing function or method
- [ ] local classes get nested qualified names
- [ ] local classes get stable symbol IDs


### Done when


- [ ] local classes are preserved as first-class extracted declarations


---


## Step 5: Build nested naming helpers


### Files


- [ ] `src/repo_context/extraction/naming.py`


### Implement


- [ ] helper to build lexical declaration path
- [ ] helper to build nested qualified names
- [ ] helper to build stable symbol IDs from nested qualified names
- [ ] helper to build deterministic duplicate-disambiguated IDs when needed


### Rules


- [ ] module path prefixes the qualified name
- [ ] outer declaration names appear before inner names
- [ ] naming must be deterministic across repeated parses
- [ ] same source file and AST should produce same names and IDs every time
- [ ] duplicate same-scope declarations must not collide in storage


### Done when


- [ ] nested symbols have stable names and IDs


---


## Step 6: Emit lexical parent edges


### Files


- [ ] `src/repo_context/extraction/edges.py`
- [ ] or edge emission inside `visitor.py` if already centralized there


### Implement


- [ ] emit one `SCOPE_PARENT` edge for every declaration with a lexical parent
- [ ] point the edge to the immediate parent only
- [ ] preserve existing containment or ownership edges unless intentionally replacing them


### Rules


- [ ] no module-level declaration gets `SCOPE_PARENT`
- [ ] no symbol may have more than one immediate `SCOPE_PARENT`
- [ ] do not skip parent generations
- [ ] do not use `SCOPE_PARENT` as a generic contains edge


### Done when


- [ ] the extracted graph shape preserves lexical nesting explicitly


---


## Step 7: Update phase 4 persistence contract


### Files


- [ ] phase 4 graph storage models
- [ ] DB schema/migrations
- [ ] graph insert/update code


### Implement


- [ ] persist `scope`
- [ ] persist `lexical_parent_id`
- [ ] persist new local-function kinds
- [ ] persist `SCOPE_PARENT` edges
- [ ] add index on `lexical_parent_id`


### Schema changes


At minimum:


- [ ] add nullable `scope` column to symbols table
- [ ] add nullable `lexical_parent_id` column to symbols table
- [ ] allow new kinds in validation
- [ ] allow `SCOPE_PARENT` in edge validation


### Migration rule


Do **not** blindly default all existing rows to `scope = "module"` during migration.


Use one of these two policies:


- add nullable columns and backfill on reindex
- or run an explicit backfill pass that recomputes real scope values


### Why this matters


A blind default makes existing methods and other stored declarations temporarily wrong until reindex, which is misleading and fragile.


### Done when


- [ ] phase 4 can store nested-aware extraction output without lossy adaptation
- [ ] migration truthfulness is preserved


---


## Step 8: Compatibility audit


### Files to check


- [ ] symbol serialization code
- [ ] graph insert code
- [ ] kind-filter queries
- [ ] unique-constraint logic
- [ ] existing extraction tests
- [ ] phase 4 persistence tests


### Verify


- [ ] files with no nested declarations still behave the same
- [ ] module-level function extraction is unchanged
- [ ] class and method extraction is unchanged
- [ ] old kind filters do not accidentally drop local functions
- [ ] old callable-kind helpers are updated to include local callable kinds when appropriate
- [ ] no uniqueness rules break on nested qualified names


### Required audit rule


Anywhere the code currently checks for callable kinds, explicitly decide whether that logic should include:
- [ ] `local_function`
- [ ] `local_async_function`


Do not leave this implicit.
Silent exclusion here is the most likely regression.


### Done when


- [ ] nested support does not regress plain codebases


---


## Step 9: Tests


### Files


- [ ] `tests/extraction/test_nested_symbols.py`
- [ ] `tests/graph/test_nested_symbol_persistence.py`


### Implement these tests


#### `test_extract_nested_function`


Verify:
- [ ] nested `inner` is emitted
- [ ] `inner.kind == "local_function"`
- [ ] `inner.scope == "function"`
- [ ] `inner.lexical_parent_id == outer.id`
- [ ] `SCOPE_PARENT(inner -> outer)` exists


#### `test_extract_nested_async_function`


Verify:
- [ ] nested async function is emitted
- [ ] kind is `local_async_function`
- [ ] parent linkage is correct


#### `test_extract_function_inside_method`


Verify:
- [ ] nested callable inside method is `local_function`
- [ ] parent is the method, not the class


#### `test_extract_local_class`


Verify:
- [ ] class inside function is emitted
- [ ] `scope == "function"`
- [ ] parent is containing function


#### `test_extract_method_inside_local_class`


Verify:
- [ ] method in local class is `method`
- [ ] parent is local class


#### `test_nested_qualified_name_is_stable`


Verify:
- [ ] nested path appears in qualified name
- [ ] repeated parse produces same qualified name and ID


#### `test_duplicate_same_scope_names_do_not_collide`


Verify:
- [ ] duplicate declarations in same lexical scope both persist
- [ ] their `qualified_name` can remain the same if that is the chosen policy
- [ ] their symbol IDs are different and deterministic


#### `test_phase4_persists_nested_symbol_fields`


Verify:
- [ ] `scope` is stored
- [ ] `lexical_parent_id` is stored
- [ ] `SCOPE_PARENT` edge is stored


#### `test_kind_filter_compatibility_for_callables`


Verify:
- [ ] existing callable helpers include local callable kinds where intended
- [ ] queries do not silently drop nested functions


### Done when


- [ ] nested extraction and persistence work end to end


---


## Explicit limitations


Document these clearly for v1:


- no closure-capture edges yet
- no full variable binding graph yet
- no `nonlocal` modeling yet
- no `global` rebinding modeling yet
- no scope-aware reference lookup yet
- no risk weighting changes yet


This phase preserves declaration structure first.
Full name-binding semantics come later.


---


## Acceptance checklist


Phase 03b is done when all of this is true:


- The extractor recognizes nested `def`.
- The extractor recognizes nested `async def`.
- The extractor recognizes local classes in functions.
- Nested declarations become real symbols.
- Nested declarations get stable qualified names.
- Nested declarations get stable symbol IDs.
- Duplicate same-scope declarations do not collide in storage.
- Nested declarations store `scope`.
- Nested declarations store `lexical_parent_id`.
- `SCOPE_PARENT` edges are emitted.
- Phase 4 persists the new fields and edge type.
- Existing non-nested extraction still works.
- Callable-kind filters have been audited for compatibility.
- Tests pass.


---


## Common mistakes to avoid


### Mistake 1: Flattening nested functions into module scope


That destroys real lexical structure.


### Mistake 2: Treating functions inside methods as methods


They are local functions, not class members in the same sense.


### Mistake 3: Delaying lexical-parent inference until graph persistence


The extractor already knows the truth.
Capture it there.


### Mistake 4: Using vague containment edges only


You need a specific lexical-parent edge.


### Mistake 5: Overengineering full scope semantics immediately


Start with declaration structure first.


### Mistake 6: Forgetting downstream kind filters


Anything that assumes only old function kinds will break silently.


### Mistake 7: Forcing fake `module` scope during migration


That creates temporarily wrong stored truth.


### Mistake 8: Assuming qualified name alone is always unique


Same-scope duplicate declarations can exist and need deterministic ID handling.


---


## What the next phases will use


Once this phase exists:


- phase 4 can persist nested-aware graph state
- phase 5 can include nested callables in symbol context
- phase 6 can add scope-aware reference logic later
- phase 7 can weight local functions differently in risk
- phase 8 can resolve nested symbols deterministically


This phase makes those later upgrades possible without ugly retrofits.


---


## Final guidance


This phase should stay narrow and strict.


Keep it focused on:


- extracting nested declarations
- assigning correct kinds
- storing scope metadata
- storing lexical parent links
- generating stable names and IDs
- handling duplicate same-scope declarations deterministically
- persisting the new shape cleanly
- auditing compatibility filters
