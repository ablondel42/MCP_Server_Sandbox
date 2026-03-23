```md
# 08-mcp-server.md

## Purpose

This phase builds the MCP server layer.

The MCP server is the deterministic tool interface that exposes the repository graph, symbol context, reference data, and risk engine to an AI agent. It is not the place where natural-language reasoning should live. It is the place where structured tools live.

In plain language:

- the graph stores repository truth
- the context builder packages local symbol context
- the LSP layer enriches references
- the risk engine computes risk facts
- the MCP server exposes all of that through clear tool contracts

This phase is where the project becomes agent-usable.

---

## Why this phase matters

Without MCP, all your work still lives as internal modules and CLI commands.

That is fine for local debugging, but not enough for an AI-assisted workflow where an agent should be able to ask deterministic questions like:

- resolve this symbol
- show me context for this symbol
- refresh references for this symbol
- assess the risk of changing this target set

The MCP server is the bridge between your structured code intelligence system and the agent.

If this layer is sloppy:
- tool contracts become vague
- outputs become inconsistent
- the agent starts guessing
- server logic leaks into prompt logic
- debugging gets painful

So this phase is about making the system consumable and stable.

---

## Phase goals

By the end of this phase, you should have:

- an MCP server process
- clear tool registration
- machine-friendly tool input schemas
- machine-friendly tool output schemas
- tools for symbol lookup
- tools for symbol context retrieval
- tools for reference refresh and lookup
- tools for risk analysis
- deterministic error responses
- a CLI or launch entry point for the MCP server
- tests for MCP tool behavior

---

## Phase non-goals

Do **not** do any of this in phase 8:

- making the MCP server explain results in natural language
- embedding an LLM inside the server
- agent planning logic inside the server
- autonomous code edits
- workflow orchestration UI
- watch mode unless you already need it badly

This phase is tool exposure, not agent personality.

---

## What already exists from previous phases

This phase assumes you already have:

- repository scanning
- AST extraction
- graph storage
- context building
- LSP reference enrichment
- risk engine

The MCP server should expose these capabilities.
It should not reimplement them.

---

## Core design principle

The MCP server should compute facts, not prose.

That means the server should return:
- exact fields
- issue codes
- counts
- IDs
- decisions
- structured summaries

The AI agent can then:
- explain the result
- revise the user-facing plan
- ask follow-up questions
- present safe next steps

This separation keeps the server cheap, testable, and predictable.

---

## Recommended package structure additions

Add these files:

```text
src/
  repo_context/
    mcp/
      __init__.py
      server.py
      tools.py
      schemas.py
      errors.py
      adapters.py
```

### Why this split

- `server.py`: MCP server setup and registration
- `tools.py`: tool handlers
- `schemas.py`: input and output contracts
- `errors.py`: consistent server-side error shapes
- `adapters.py`: maps internal models to tool-facing payloads

This keeps tool exposure clean and prevents server code from becoming a junk drawer.

---

## Tool design principles

### Principle 1: Tool names should be obvious

A tool name should make its purpose clear without reading a paragraph.

### Principle 2: Inputs should be strict

Tool input should be explicit and validated.
Do not accept mushy input blobs.

### Principle 3: Outputs should be stable

The same request against the same graph state should return the same structure.

### Principle 4: Keep tools narrow

One tool should do one job well.
Do not make a giant “do everything” tool.

### Principle 5: Errors should be structured

Not found, stale context, missing references, and invalid input should all have explicit error responses.

---

## Suggested MCP tools

Version 1 only needs a small set.

Recommended tools:

- `resolve_symbol`
- `get_symbol_context`
- `refresh_symbol_references`
- `get_symbol_references`
- `analyze_symbol_risk`
- `analyze_target_set_risk`

That is enough for a strong first version.

You can add plan-specific wrappers later if needed.

---

## Tool 1: `resolve_symbol`

### Purpose

Resolve a symbol from a human-friendly identifier into a stable internal symbol.

### Why this tool matters

Agents often start with:
- a qualified name
- maybe a kind
- maybe partial user intent

This tool gives them a deterministic symbol handle to use in later tool calls.

### Recommended input

```json
{
  "repo_id": "repo:project",
  "qualified_name": "app.services.auth.AuthService.login",
  "kind": "method"
}
```

### Recommended output

```json
{
  "symbol": {
    "id": "sym:repo:project:method:app.services.auth.AuthService.login",
    "qualified_name": "app.services.auth.AuthService.login",
    "kind": "method",
    "file_id": "file:app/services/auth.py",
    "file_path": "app/services/auth.py",
    "module_path": "app.services.auth"
  }
}
```

### Error cases

- symbol not found
- ambiguous lookup if you allow kind-less lookup

If ambiguous, return a structured ambiguity response.
Do not silently guess.

---

## Tool 2: `get_symbol_context`

### Purpose

Return the assembled symbol context for one symbol.

### Why this tool matters

This is the main structured context tool for agent reasoning.

### Recommended input

```json
{
  "symbol_id": "sym:repo:project:class:app.services.auth.AuthService"
}
```

### Recommended output

```json
{
  "context": {
    "focus_symbol": { "...": "..." },
    "parent": { "...": "..." },
    "children": [],
    "incoming_edges": [],
    "outgoing_edges": [],
    "reference_summary": {
      "reference_count": 14,
      "referencing_file_count": 6,
      "referencing_module_count": 4,
      "available": true
    },
    "structural_summary": { "...": "..." },
    "freshness": { "...": "..." },
    "confidence": { "...": "..." }
  }
}
```

### Important rule

This tool should return structure, not generated explanation text.

---

## Tool 3: `refresh_symbol_references`

### Purpose

Refresh LSP-based references for one symbol.

### Why this tool matters

The agent may need fresh reference data before trusting risk analysis.

### Recommended input

```json
{
  "symbol_id": "sym:repo:project:method:app.services.auth.AuthService.login"
}
```

### Recommended output

```json
{
  "symbol_id": "sym:repo:project:method:app.services.auth.AuthService.login",
  "reference_summary": {
    "reference_count": 14,
    "referencing_file_count": 6,
    "referencing_module_count": 4,
    "available": true,
    "last_refreshed_at": "2026-03-23T22:40:00Z"
  }
}
```

### Error cases

- symbol not found
- symbol lacks usable declaration position
- LSP request failed
- file URI not tracked

These should return structured tool errors.

---

## Tool 4: `get_symbol_references`

### Purpose

Return the stored incoming `references` edges targeting one symbol.

### Why this tool matters

Sometimes the agent needs raw usage callers, not just counts.

### Recommended input

```json
{
  "symbol_id": "sym:repo:project:function:app.services.execute_job"
}
```

### Recommended output

```json
{
  "symbol_id": "sym:repo:project:function:app.services.execute_job",
  "references": [
    {
      "from_id": "sym:repo:project:function:app.api.handle_request",
      "to_id": "sym:repo:project:function:app.services.execute_job",
      "evidence_file_id": "file:app/api.py",
      "evidence_uri": "file:///workspace/project/app/api.py",
      "confidence": 0.9
    }
  ],
  "reference_summary": {
    "reference_count": 2,
    "referencing_file_count": 2,
    "referencing_module_count": 2,
    "available": true
  }
}
```

### Important rule

This tool should return stored graph data only.
Do not auto-refresh unless you explicitly design that behavior.

My recommendation:
- keep refresh as a separate tool

That makes freshness decisions explicit.

---

## Tool 5: `analyze_symbol_risk`

### Purpose

Run the risk engine for one symbol.

### Why this tool matters

This is the main deterministic safety check for one target.

### Recommended input

```json
{
  "symbol_id": "sym:repo:project:method:app.services.auth.AuthService.login"
}
```

### Recommended output

```json
{
  "risk": {
    "targets": [
      {
        "symbol_id": "sym:repo:project:method:app.services.auth.AuthService.login",
        "qualified_name": "app.services.auth.AuthService.login",
        "kind": "method",
        "file_id": "file:app/services/auth.py",
        "file_path": "app/services/auth.py",
        "module_path": "app.services.auth",
        "visibility_hint": "public"
      }
    ],
    "facts": { "...": "..." },
    "issues": [
      "high_reference_count",
      "cross_file_impact",
      "cross_module_impact",
      "public_surface_change"
    ],
    "risk_score": 60,
    "decision": "review_required"
  }
}
```

---

## Tool 6: `analyze_target_set_risk`

### Purpose

Run the risk engine for multiple resolved targets.

### Why this tool matters

Real changes often touch more than one symbol.

### Recommended input

```json
{
  "symbol_ids": [
    "sym:repo:project:method:app.services.auth.AuthService.login",
    "sym:repo:project:function:app.services.create_session"
  ]
}
```

### Recommended output

Same structure as `analyze_symbol_risk`, but with multiple targets.

---

## Should there be a plan tool in phase 8

You have two valid options.

## Option A: do not add a plan wrapper yet

Pros:
- cleaner architecture
- keeps phase 8 focused on exposing core tools
- lets the agent compose its own plan workflow

Cons:
- the agent has to do a bit more orchestration

## Option B: add a thin `evaluate_plan_risk` wrapper

Pros:
- convenient
- closer to the intended workflow

Cons:
- easy to blur the line between engine and workflow too early

My blunt recommendation:
- keep phase 8 focused on core tools
- add a plan wrapper only if you already know the workflow needs it immediately

---

## Tool schemas

Create `schemas.py`.

You need explicit input and output contracts.
You can use:
- dataclasses
- typed dicts
- Pydantic if you really want validation

For a budget-first solo-dev setup, dataclasses or simple validation helpers are enough.

### Example input schema

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class ResolveSymbolInput:
    repo_id: str
    qualified_name: str
    kind: Optional[str] = None
```

### Example output schema

```python
from dataclasses import dataclass
from typing import Any

@dataclass
class ToolResult:
    ok: bool
    data: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
```

### Why a shared result wrapper helps

It gives every tool the same top-level shape:
- success
- data
- error

That makes agent handling cleaner.

---

## Error design

Create `errors.py`.

Recommended error codes:

- `invalid_input`
- `symbol_not_found`
- `ambiguous_symbol`
- `references_unavailable`
- `lsp_failure`
- `stale_context`
- `internal_error`

### Suggested error shape

```json
{
  "ok": false,
  "error": {
    "code": "symbol_not_found",
    "message": "No symbol found for qualified name app.services.auth.AuthService.login",
    "details": {
      "qualified_name": "app.services.auth.AuthService.login"
    }
  }
}
```

### Why this matters

The agent should not have to parse random string errors.

---

## Adapters

Create `adapters.py`.

This file should convert internal objects into stable MCP payloads.

Examples:
- node row -> tool-facing symbol payload
- edge row -> tool-facing reference payload
- `RiskResult` -> tool-facing risk payload
- `SymbolContext` -> tool-facing context payload

### Why this matters

You do not want raw DB shapes leaking into the server contract.

---

## Server implementation strategy

Create `server.py`.

Responsibilities:

- initialize app config
- open DB access
- wire in LSP client if needed
- register MCP tools
- run the server

### Important rule

Do not put real business logic in `server.py`.
It should mainly wire handlers.

---

## Tool handler design

Create `tools.py`.

Each handler should:
1. validate input
2. call the correct internal service
3. map the result through an adapter
4. return a stable tool result
5. catch domain errors and convert them to structured MCP errors

That is all.

### Example shape

```python
def resolve_symbol_tool(conn, payload: dict) -> dict:
    ...
```

or if your MCP framework expects decorated handlers, that is fine too.

Just keep them thin.

---

## Example handler sketch

```python
def analyze_symbol_risk_tool(conn, payload: dict) -> dict:
    symbol_id = payload.get("symbol_id")
    if not symbol_id:
        return error_result("invalid_input", "symbol_id is required")

    try:
        result = analyze_symbol_risk(conn, symbol_id)
        return {
            "ok": True,
            "data": {
                "risk": result,
            },
        }
    except ValueError as exc:
        return error_result("symbol_not_found", str(exc))
    except Exception as exc:
        return error_result("internal_error", str(exc))
```

This is exactly how boring it should be.

---

## Reference freshness policy

Do not hide freshness policy in magic behavior.

You need to decide:

### Option A: read-only reference tool

- `get_symbol_references` only returns stored data
- `refresh_symbol_references` refreshes data explicitly

### Option B: auto-refresh if stale

- `get_symbol_references` may trigger LSP refresh

My recommendation:
- use Option A

Why:
- more predictable
- easier to test
- cheaper
- no surprise latency

---

## Suggested MCP workflow

A likely agent workflow with these tools is:

1. `resolve_symbol`
2. `get_symbol_context`
3. `refresh_symbol_references` if needed
4. `analyze_symbol_risk` or `analyze_target_set_risk`

That gives the agent:
- identity
- context
- freshness
- risk

This is already a strong workflow.

---

## CLI / launch entry point

Add a command like:

```text
repo-context serve-mcp
```

### What it should do

- start the MCP server
- load config
- connect to the database
- initialize dependencies
- begin serving registered tools

### Optional flags

- `--db-path`
- `--repo-root`
- `--debug`

Keep it simple.

---

## Testing plan

This phase needs contract tests.

### `test_resolve_symbol_tool_success`

Verify:
- valid input returns `ok=true`
- symbol payload is correct

### `test_resolve_symbol_tool_not_found`

Verify:
- missing symbol returns structured `symbol_not_found`

### `test_get_symbol_context_tool`

Verify:
- context payload exists
- expected top-level fields exist

### `test_refresh_symbol_references_tool`

Use a fake LSP client.
Verify:
- references are refreshed
- summary fields are returned

### `test_get_symbol_references_tool`

Verify:
- stored references come back correctly
- summary is included

### `test_analyze_symbol_risk_tool`

Verify:
- tool returns structured risk result

### `test_analyze_target_set_risk_tool`

Verify:
- multi-symbol input works

### `test_invalid_input_error_shape`

Verify:
- missing required fields return `invalid_input`

### `test_internal_error_shape`

Verify:
- unexpected failures return `internal_error`

---

## Suggested fake dependencies for tests

Use fake or stub components for:
- LSP client
- database fixtures
- graph queries

Do not make every MCP test depend on a real language server.
That is just asking for pain.

---

## Acceptance checklist

Phase 8 is done when all of this is true:

- The MCP server starts.
- Tools are registered cleanly.
- `resolve_symbol` works.
- `get_symbol_context` works.
- `refresh_symbol_references` works.
- `get_symbol_references` works.
- `analyze_symbol_risk` works.
- `analyze_target_set_risk` works.
- Tool inputs are validated.
- Tool outputs are structured and stable.
- Errors are structured and stable.
- The server does not generate natural-language explanations as tool truth.
- Tests pass.

---

## Common mistakes to avoid

### Mistake 1: Making the MCP server “smart”

It should be deterministic and boring, not conversational.

### Mistake 2: Returning raw DB rows directly

Always adapt internal objects to stable tool-facing payloads.

### Mistake 3: Mixing refresh and read behavior invisibly

Reference refresh should be explicit.

### Mistake 4: Weak error contracts

Random string exceptions are garbage for tool consumers.

### Mistake 5: Putting business logic in server wiring

Handlers should stay thin and call internal services.

### Mistake 6: One giant generic tool

That usually becomes hard to validate and hard for the agent to use correctly.

---

## What phase 9 will likely add

Once phase 8 exists, the next useful layer is usually one of these:

- a plan-oriented MCP wrapper tool
- incremental indexing and refresh orchestration
- approval-aware workflow integration
- a better agent contract around plan -> risk -> revise -> approve

That depends on how tightly you want to bind the graph engine to your coding workflow.

---

## Final guidance

This phase is the packaging layer.

Before phase 8:
- your system is useful to you as a developer

After phase 8:
- your system is usable by an AI agent in a deterministic way

That is the key transition.

Keep the MCP server:
- strict
- narrow
- structured
- boring

That is exactly what makes it reliable.
```