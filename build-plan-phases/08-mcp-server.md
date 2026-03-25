Yes — this phase should be strict as hell, because MCP is where sloppy contracts start poisoning the agent loop. MCP’s own tool spec emphasizes structured inputs, structured outputs, and distinct handling for protocol errors versus tool execution errors, which is exactly why your server should stay narrow and deterministic. [modelcontextprotocol](https://modelcontextprotocol.io/specification/draft/server/tools)

# 08 MCP Server - Exact Implementation Checklist

## Objective

Implement phase 8 of the repository indexing pipeline.

Phase 8 must expose the repository graph, symbol context, reference data, and risk engine through a deterministic MCP server with strict tool contracts.

Phase 8 must provide:
- an MCP server process
- tool registration
- strict input schemas
- strict output schemas
- structured error responses
- tools for symbol resolution
- tools for context retrieval
- tools for reference refresh and retrieval
- tools for risk analysis
- a CLI launch entry point
- tests for tool behavior

Phase 8 must not provide:
- natural-language explanation generation
- embedded LLM reasoning inside the server
- agent planning logic
- autonomous code edits
- UI workflow orchestration
- hidden auto-refresh behavior
- watch mode unless already needed elsewhere

***

## Consistency Rules

These rules are mandatory.

- [ ] Reuse the existing phase 1 through phase 7 services, models, and query helpers.
- [ ] Do not reimplement graph logic inside MCP handlers.
- [ ] Do not reimplement context assembly inside MCP handlers.
- [ ] Do not reimplement reference enrichment inside MCP handlers.
- [ ] Do not reimplement risk logic inside MCP handlers.
- [ ] Keep tools narrow.
- [ ] Keep inputs explicit and validated.
- [ ] Keep outputs stable and machine-friendly.
- [ ] Keep errors structured and machine-readable.
- [ ] Keep the MCP server deterministic and boring.

Structured schemas and explicit tool contracts improve MCP consistency because the client can reason about expected inputs and outputs safely instead of guessing. [zilliz](https://zilliz.com/ai-faq/how-does-mcp-maintain-consistency-across-modeltool-interactions)

***

## Required Inputs

Phase 8 must consume these existing inputs:

- [ ] graph storage and query helpers from phase 4
- [ ] symbol context builder from phase 5
- [ ] reference enrichment and reference queries from phase 6
- [ ] risk engine from phase 7
- [ ] app config and DB access from earlier phases
- [ ] optional LSP client dependency for refresh tools

Do not make the MCP layer the source of truth for any repository facts.

***

## Required Outputs

Phase 8 must produce these capabilities:

- [ ] start an MCP server process
- [ ] register tools cleanly
- [ ] validate tool input
- [ ] return stable success payloads
- [ ] return stable structured errors
- [ ] resolve one symbol
- [ ] return one symbol context
- [ ] refresh one symbol’s references
- [ ] return stored references for one symbol
- [ ] analyze one symbol risk
- [ ] analyze multiple symbol risk
- [ ] expose a CLI launch command

Do not add plan wrappers unless you intentionally decide to break scope.

***

## Required File Layout

Create or extend these files:

- [ ] `src/repo_context/mcp/__init__.py`
- [ ] `src/repo_context/mcp/server.py`
- [ ] `src/repo_context/mcp/tools.py`
- [ ] `src/repo_context/mcp/schemas.py`
- [ ] `src/repo_context/mcp/errors.py`
- [ ] `src/repo_context/mcp/adapters.py`

Reuse existing files if they already exist.

Do not create a second server package with overlapping responsibility.

***

## Tool Set

Implement exactly these version 1 tools:

- [ ] `resolve_symbol`
- [ ] `get_symbol_context`
- [ ] `refresh_symbol_references`
- [ ] `get_symbol_references`
- [ ] `analyze_symbol_risk`
- [ ] `analyze_target_set_risk`

Do not add one giant catch-all tool.

***

## Shared Result Contract

All tool handlers must use one stable top-level result shape.

### Success shape

- [ ] top-level `ok = true`
- [ ] top-level `data` object exists
- [ ] top-level `error = null` or omitted consistently according to project style

### Error shape

- [ ] top-level `ok = false`
- [ ] top-level `error` object exists
- [ ] top-level `data = null` or omitted consistently according to project style

### Required error object fields

- [ ] `code`
- [ ] `message`
- [ ] `details`

This matches MCP guidance that tool execution problems should be returned as structured tool-facing errors rather than random strings. [modelcontextprotocol](https://modelcontextprotocol.io/specification/2025-06-18/server/tools)

***

## Error Codes

Use exactly these server-side tool error codes in phase 8:

- [ ] `invalid_input`
- [ ] `symbol_not_found`
- [ ] `ambiguous_symbol`
- [ ] `references_unavailable`
- [ ] `lsp_failure`
- [ ] `stale_context`
- [ ] `internal_error`

Do not invent many extra codes unless strictly necessary.

***

## Step 1 - MCP Schemas

### File

- [ ] `src/repo_context/mcp/schemas.py`

### Implement

Define explicit input and output contracts for all tools.

### Required input contracts

- [ ] `ResolveSymbolInput`
- [ ] `GetSymbolContextInput`
- [ ] `RefreshSymbolReferencesInput`
- [ ] `GetSymbolReferencesInput`
- [ ] `AnalyzeSymbolRiskInput`
- [ ] `AnalyzeTargetSetRiskInput`

### Required shared output contract

- [ ] one shared tool result wrapper, such as `ToolResult`

### Exact input fields

#### `ResolveSymbolInput`
- [ ] `repo_id`
- [ ] `qualified_name`
- [ ] optional `kind`

#### `GetSymbolContextInput`
- [ ] `symbol_id`

#### `RefreshSymbolReferencesInput`
- [ ] `symbol_id`

#### `GetSymbolReferencesInput`
- [ ] `symbol_id`

#### `AnalyzeSymbolRiskInput`
- [ ] `symbol_id`

#### `AnalyzeTargetSetRiskInput`
- [ ] `symbol_ids`

### Required validation behavior

- [ ] required fields must be enforced
- [ ] empty required strings must be rejected
- [ ] `symbol_ids` must be a non-empty list of non-empty strings
- [ ] validation failures must return `invalid_input`

### Do not do

- [ ] do not accept freeform blob payloads
- [ ] do not rely only on agent-side correctness

### Done when

- [ ] every tool has explicit machine-friendly validated input and output shapes

***

## Step 2 - MCP Error Helpers

### File

- [ ] `src/repo_context/mcp/errors.py`

### Implement

Add shared helpers to build structured error results.

### Required helpers

- [ ] `error_result(code, message, details=None)`
- [ ] optional small exception-to-error mapper if useful

### Exact behavior

- [ ] every error result must follow the shared result contract
- [ ] details must be a dict or `None`
- [ ] unknown failures must map to `internal_error`

### Do not do

- [ ] do not return raw Python exception strings without wrapping
- [ ] do not scatter ad-hoc error JSON creation across handlers

### Done when

- [ ] all tools can return consistent structured errors

***

## Step 3 - MCP Adapters

### File

- [ ] `src/repo_context/mcp/adapters.py`

### Implement

Add adapter helpers that map internal objects to tool-facing payloads.

### Required adapters

- [ ] node -> symbol payload
- [ ] edge -> reference payload
- [ ] `SymbolContext` -> context payload
- [ ] `RiskResult` -> risk payload

### Required symbol payload fields

- [ ] `id`
- [ ] `qualified_name`
- [ ] `kind`
- [ ] `file_id`
- [ ] `file_path` when derivable
- [ ] `module_path` when derivable

### Required reference payload fields

- [ ] `from_id`
- [ ] `to_id`
- [ ] `evidence_file_id`
- [ ] `evidence_uri`
- [ ] `confidence`
- [ ] evidence range if your tool contract includes it

### Required context payload fields

- [ ] `focus_symbol`
- [ ] `parent`
- [ ] `children`
- [ ] `incoming_edges`
- [ ] `outgoing_edges`
- [ ] `reference_summary`
- [ ] `structural_summary`
- [ ] `freshness`
- [ ] `confidence`

### Required risk payload fields

- [ ] `targets`
- [ ] `facts`
- [ ] `issues`
- [ ] `risk_score`
- [ ] `decision`

### Do not do

- [ ] do not leak raw DB rows directly into tool contracts
- [ ] do not mutate internal service objects in adapters

### Done when

- [ ] internal models are cleanly separated from tool-facing payloads

***

## Step 4 - `resolve_symbol` Tool

### File

- [ ] `src/repo_context/mcp/tools.py`

### Implement

- [ ] handler for `resolve_symbol`

### Exact input

- [ ] `repo_id`
- [ ] `qualified_name`
- [ ] optional `kind`

### Exact behavior

- [ ] validate input
- [ ] resolve symbol by repo ID and qualified name
- [ ] if `kind` is provided, apply it
- [ ] if exactly one symbol matches, return it
- [ ] if no symbol matches, return `symbol_not_found`
- [ ] if lookup is ambiguous under the chosen lookup mode, return `ambiguous_symbol`
- [ ] do not silently guess among multiple matches

### Exact success output

- [ ] `ok = true`
- [ ] `data.symbol` contains adapted symbol payload

### Do not do

- [ ] do not return context here
- [ ] do not return prose explanation

### Done when

- [ ] an agent can deterministically turn a human-friendly symbol reference into one stable internal symbol

***

## Step 5 - `get_symbol_context` Tool

### File

- [ ] `src/repo_context/mcp/tools.py`

### Implement

- [ ] handler for `get_symbol_context`

### Exact input

- [ ] `symbol_id`

### Exact behavior

- [ ] validate input
- [ ] build symbol context using phase 5 and phase 6 services
- [ ] return the structured context
- [ ] if symbol does not exist, return `symbol_not_found`

### Exact success output

- [ ] `ok = true`
- [ ] `data.context` contains adapted context payload

### Do not do

- [ ] do not generate English explanation text
- [ ] do not auto-refresh references here

### Done when

- [ ] an agent can request one stable local symbol context object

***

## Step 6 - `refresh_symbol_references` Tool

### File

- [ ] `src/repo_context/mcp/tools.py`

### Implement

- [ ] handler for `refresh_symbol_references`

### Exact input

- [ ] `symbol_id`

### Exact behavior

- [ ] validate input
- [ ] load target symbol
- [ ] call phase 6 reference enrichment for that symbol
- [ ] return updated reference summary
- [ ] if symbol does not exist, return `symbol_not_found`
- [ ] if declaration position cannot be resolved, return `references_unavailable`
- [ ] if LSP request fails, return `lsp_failure`

### Exact success output

- [ ] `ok = true`
- [ ] `data.symbol_id`
- [ ] `data.reference_summary`

### Do not do

- [ ] do not hide failed LSP refresh behind fake zero counts
- [ ] do not make this tool return raw LSP locations only

### Done when

- [ ] an agent can explicitly refresh one symbol’s references and get a stable summary back

***

## Step 7 - `get_symbol_references` Tool

### File

- [ ] `src/repo_context/mcp/tools.py`

### Implement

- [ ] handler for `get_symbol_references`

### Exact input

- [ ] `symbol_id`

### Exact behavior

- [ ] validate input
- [ ] load stored `references` edges targeting the symbol
- [ ] load stored reference stats for the symbol
- [ ] return both raw references and summary
- [ ] if symbol does not exist, return `symbol_not_found`

### Exact success output

- [ ] `ok = true`
- [ ] `data.symbol_id`
- [ ] `data.references`
- [ ] `data.reference_summary`

### Freshness rule

- [ ] this tool must be read-only
- [ ] this tool must not auto-refresh references implicitly

### Do not do

- [ ] do not mix refresh and read behavior invisibly

### Done when

- [ ] an agent can inspect stored callers and usage summary without triggering LSP work

***

## Step 8 - `analyze_symbol_risk` Tool

### File

- [ ] `src/repo_context/mcp/tools.py`

### Implement

- [ ] handler for `analyze_symbol_risk`

### Exact input

- [ ] `symbol_id`

### Exact behavior

- [ ] validate input
- [ ] call the phase 7 risk engine for one symbol
- [ ] return structured risk result
- [ ] if symbol does not exist, return `symbol_not_found`

### Exact success output

- [ ] `ok = true`
- [ ] `data.risk` contains adapted risk payload

### Do not do

- [ ] do not add explanation prose
- [ ] do not collapse facts and issues into one text field

### Done when

- [ ] an agent can run a deterministic safety check for one symbol

***

## Step 9 - `analyze_target_set_risk` Tool

### File

- [ ] `src/repo_context/mcp/tools.py`

### Implement

- [ ] handler for `analyze_target_set_risk`

### Exact input

- [ ] `symbol_ids`

### Exact behavior

- [ ] validate input
- [ ] call the phase 7 risk engine for the given symbol set
- [ ] return structured aggregate risk result
- [ ] if any symbol does not exist, return `symbol_not_found` or a stricter deterministic validation error according to project conventions
- [ ] do not silently skip bad symbol IDs

### Exact success output

- [ ] `ok = true`
- [ ] `data.risk` contains adapted risk payload

### Do not do

- [ ] do not parse user prose here
- [ ] do not accept empty symbol lists

### Done when

- [ ] an agent can assess a resolved multi-target change set deterministically

***

## Step 10 - Tool Handler Rules

### File

- [ ] `src/repo_context/mcp/tools.py`

### Implement

All handlers must follow this exact handler pattern:

- [ ] validate input
- [ ] call one internal service
- [ ] adapt result to tool payload
- [ ] return shared success wrapper
- [ ] catch domain errors
- [ ] map domain errors to structured MCP tool errors
- [ ] catch unexpected failures and return `internal_error`

### Do not do

- [ ] do not put core business logic in handlers
- [ ] do not open-code different result shapes per tool

### Done when

- [ ] all tools behave consistently at the handler layer

***

## Step 11 - Server Wiring

### File

- [ ] `src/repo_context/mcp/server.py`

### Implement

This module must:

- [ ] initialize config
- [ ] initialize DB access
- [ ] initialize LSP dependency only if needed by refresh tools
- [ ] register all MCP tools
- [ ] start serving

### Required behavior

- [ ] server wiring must stay thin
- [ ] tool handlers must be injected or wired cleanly
- [ ] no risk logic may live here
- [ ] no context assembly logic may live here
- [ ] no graph query SQL may live here

### Do not do

- [ ] do not turn `server.py` into a junk drawer
- [ ] do not hide business logic inside registration closures unless unavoidable

### Done when

- [ ] the MCP server process can start and expose the required tools cleanly

***

## Step 12 - CLI Launch Entry Point

### Files to modify

- [ ] existing CLI module from earlier phases

### Implement

Add:

- [ ] `repo-context serve-mcp`

### Optional flags

- [ ] `--db-path`
- [ ] `--repo-root`
- [ ] `--debug`

### Required behavior

- [ ] load config
- [ ] initialize dependencies
- [ ] start MCP server
- [ ] fail clearly on startup errors

### Do not do

- [ ] do not bury server startup inside unrelated CLI commands

### Done when

- [ ] the MCP server can be launched deterministically from the project CLI

***

## Step 13 - Reference Freshness Policy

### Files to verify

- [ ] `src/repo_context/mcp/tools.py`
- [ ] `src/repo_context/mcp/server.py`

### Implement

Use this explicit policy:

- [ ] `get_symbol_references` is read-only
- [ ] `refresh_symbol_references` performs refresh
- [ ] no tool may auto-refresh references silently unless the tool name explicitly says refresh

### Do not do

- [ ] do not hide network or LSP latency inside read-only tools
- [ ] do not mutate state from supposedly read-only tools

### Done when

- [ ] reference freshness behavior is explicit and predictable

***

## Step 14 - Deterministic Ambiguity Handling

### Files to verify

- [ ] `resolve_symbol` tool
- [ ] adapters and error helpers if needed

### Implement

If symbol resolution is ambiguous:

- [ ] return `ok = false`
- [ ] return `error.code = "ambiguous_symbol"`
- [ ] include enough structured details for the agent to recover, such as:
  - [ ] candidate symbol IDs
  - [ ] candidate qualified names
  - [ ] candidate kinds

### Do not do

- [ ] do not silently pick the first match
- [ ] do not hide ambiguity behind `symbol_not_found`

### Done when

- [ ] the agent can recover from ambiguous symbol resolution without guessing

***

## Step 15 - Tests

### Files to create or modify

- [ ] phase 8 tests under `tests/`

### Test strategy

- [ ] use fake or stub LSP client for refresh tool tests
- [ ] use deterministic DB fixtures
- [ ] test tool contracts, not just internal services

### Implement these tests

- [ ] `test_resolve_symbol_tool_success`
- [ ] `test_resolve_symbol_tool_not_found`
- [ ] `test_get_symbol_context_tool`
- [ ] `test_refresh_symbol_references_tool`
- [ ] `test_get_symbol_references_tool`
- [ ] `test_analyze_symbol_risk_tool`
- [ ] `test_analyze_target_set_risk_tool`
- [ ] `test_invalid_input_error_shape`
- [ ] `test_internal_error_shape`

### Exact test assertions

#### `test_resolve_symbol_tool_success`
- [ ] valid input returns `ok = true`
- [ ] symbol payload fields are correct

#### `test_resolve_symbol_tool_not_found`
- [ ] missing symbol returns `ok = false`
- [ ] error code is `symbol_not_found`

#### `test_get_symbol_context_tool`
- [ ] context payload exists
- [ ] expected top-level fields exist

#### `test_refresh_symbol_references_tool`
- [ ] fake LSP client is used
- [ ] references are refreshed
- [ ] updated summary is returned

#### `test_get_symbol_references_tool`
- [ ] stored references are returned
- [ ] summary is included
- [ ] tool does not auto-refresh

#### `test_analyze_symbol_risk_tool`
- [ ] structured risk result is returned
- [ ] facts, issues, score, and decision exist

#### `test_analyze_target_set_risk_tool`
- [ ] multi-symbol input works
- [ ] aggregate risk result is returned

#### `test_invalid_input_error_shape`
- [ ] missing required fields return `invalid_input`
- [ ] error payload shape is stable

#### `test_internal_error_shape`
- [ ] unexpected handler failures return `internal_error`
- [ ] error payload shape is stable

### Do not do

- [ ] do not rely only on end-to-end smoke tests
- [ ] do not require a real language server for the whole MCP tool suite

### Done when

- [ ] tool contracts and error contracts are covered by deterministic tests

***

## Step 16 - Final Verification

Before marking phase 8 complete, verify all of the following:

- [ ] the MCP server starts
- [ ] tools are registered cleanly
- [ ] `resolve_symbol` works
- [ ] `get_symbol_context` works
- [ ] `refresh_symbol_references` works
- [ ] `get_symbol_references` works
- [ ] `analyze_symbol_risk` works
- [ ] `analyze_target_set_risk` works
- [ ] tool inputs are validated
- [ ] tool outputs are structured and stable
- [ ] errors are structured and stable
- [ ] the server does not generate natural-language explanations as tool truth
- [ ] tests pass

Do not mark phase 8 done until every box above is true.

***

## Required Execution Order

Implement in this order and do not skip ahead:

- [ ] Step 1 MCP schemas
- [ ] Step 2 MCP error helpers
- [ ] Step 3 MCP adapters
- [ ] Step 4 `resolve_symbol` tool
- [ ] Step 5 `get_symbol_context` tool
- [ ] Step 6 `refresh_symbol_references` tool
- [ ] Step 7 `get_symbol_references` tool
- [ ] Step 8 `analyze_symbol_risk` tool
- [ ] Step 9 `analyze_target_set_risk` tool
- [ ] Step 10 tool handler rules
- [ ] Step 11 server wiring
- [ ] Step 12 CLI launch entry point
- [ ] Step 13 reference freshness policy
- [ ] Step 14 deterministic ambiguity handling
- [ ] Step 15 tests
- [ ] Step 16 final verification

***

## Phase 8 Done Definition

Phase 8 is complete only when all of these are true:

- [ ] phase 1 through phase 7 contracts remain intact
- [ ] the MCP server is a thin deterministic tool layer
- [ ] core graph, context, references, and risk logic remain in internal services
- [ ] tool contracts are strict
- [ ] error contracts are strict
- [ ] refresh behavior is explicit
- [ ] no natural-language reasoning is embedded as tool truth
- [ ] tests pass

If you want, I can keep going and convert phase 9 too, same format.