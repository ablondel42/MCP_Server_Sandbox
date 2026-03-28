# 10 Real Workflow Validation - Exact Implementation Checklist


## Objective


Implement phase 10 of the repository indexing pipeline.


Phase 10 must verify that phases 1 through 9 work together as one real deterministic workflow and that the stored graph, built symbol context, reference data, risk output, watch invalidation behavior, and MCP tool payloads are actually usable by an agent.


Phase 10 must provide:
- end-to-end workflow validation across earlier phases
- graph shape validation
- symbol context validation
- reference state validation
- MCP contract validation
- risk-result validation
- watch invalidation validation
- fixture-driven integration scenarios
- CLI inspection commands for all major parts and workflows
- tests for graph shape, context shape, MCP shape, and workflow behavior
- deterministic acceptance checks for real agent-consumable outputs


Phase 10 must not provide:
- new graph enrichment categories
- new LSP protocol features
- new risk heuristics unless needed to fix a verified workflow break
- agent planning logic
- freeform natural-language explanation generation as test truth
- UI dashboard work
- distributed orchestration complexity


***


## Consistency Rules


These rules are mandatory.


- [ ] Reuse the existing phase 1 through phase 9 services, storage, graph queries, context builder, reference logic, risk engine, MCP adapters, and watch-mode behavior.
- [ ] Keep phase 10 primarily about verification, inspection, and acceptance criteria.
- [ ] Do not move core graph or MCP business logic into phase 10 helpers.
- [ ] Keep validation deterministic and fixture-driven.
- [ ] Keep graph truth, context truth, reference truth, MCP truth, and risk truth distinct.
- [ ] Validate machine-friendly outputs, not narrative summaries.
- [ ] Treat output schemas and actual returned payloads as a contract that must match.
- [ ] Preserve the distinction between unavailable references and refreshed-zero references.
- [ ] Preserve the distinction between structural and lexical relationships.
- [ ] Preserve nested-scope compatibility introduced in phase 03b.
- [ ] Keep CLI inspection commands read-only unless a command explicitly says refresh or reindex.
- [ ] Keep debug output faithful to real stored or returned shapes.
- [ ] Do not invent alternate debug-only object models that differ from production payloads.


MCP tools are much easier to debug and validate when they can be inspected directly from the command line or an inspector, and structured contract validation is the reliable way to catch schema drift and payload mismatch early. [web:793][web:794][web:796][web:805]


***


## Required Inputs


Phase 10 must consume these existing inputs:


- [ ] repo scan and file metadata pipeline from phase 2
- [ ] AST and symbol extraction pipeline from phase 3 and phase 03b
- [ ] graph persistence and replacement helpers from phase 4
- [ ] symbol context builder from phase 5
- [ ] reference enrichment and reference queries from phase 6
- [ ] risk engine from phase 7
- [ ] MCP server tools, schemas, and adapters from phase 8
- [ ] watch mode and invalidation behavior from phase 9
- [ ] deterministic fixture repositories under `tests/fixtures/`


Do not build a parallel fake workflow that bypasses the real services.


***


## Required Outputs


Phase 10 must produce these capabilities:


- [ ] run a complete fixture workflow from scan through MCP inspection
- [ ] verify stored graph shape for representative repositories
- [ ] verify symbol context shape for representative symbols
- [ ] verify stored reference payload shape and availability semantics
- [ ] verify MCP tool output shape against expected contract
- [ ] verify risk outputs remain usable and structured
- [ ] verify watch invalidation flows through later layers honestly
- [ ] inspect agent-facing graph, context, references, risk, and MCP payloads from CLI
- [ ] report deterministic workflow summaries


Do not make phase 10 a vague “confidence” phase with no concrete assertions.


***


## Required File Layout


Create or extend these files:


- [ ] `docs/10-real-workflow.md`
- [ ] `src/repo_context/validation/__init__.py`
- [ ] `src/repo_context/validation/workflow.py`
- [ ] `src/repo_context/validation/contracts.py`
- [ ] `src/repo_context/validation/graph_checks.py`
- [ ] `src/repo_context/validation/context_checks.py`
- [ ] `src/repo_context/validation/mcp_checks.py`
- [ ] `src/repo_context/validation/reference_checks.py`
- [ ] `src/repo_context/validation/risk_checks.py`


Reuse existing files if they already exist.


Do not hide all workflow validation inside one giant test file.


***


## Validation Scope


Phase 10 must validate these layers explicitly:


- [ ] repository scan output is usable
- [ ] extracted symbols and edges are persisted correctly
- [ ] nested-scope symbols survive persistence and reload
- [ ] symbol context is structurally usable
- [ ] reference summaries distinguish unavailable from zero
- [ ] MCP tool payloads match actual usable agent-facing shapes
- [ ] risk results are machine-usable and preserve facts and issue codes
- [ ] watch invalidation keeps graph truth honest


Do not validate only storage counts while ignoring payload usability.


***


## Agent Usability Rules


Apply these rules exactly.


A graph or context output is agent-usable only if:


- [ ] key identifiers are present and stable
- [ ] relationship fields are explicit
- [ ] ambiguity is surfaced structurally rather than hidden
- [ ] unavailable data is marked explicitly
- [ ] payload shape is deterministic
- [ ] no important relationship is only implied in prose
- [ ] outputs are small enough and structured enough for tool consumers to reason over


Do not treat “human-readable enough” as the acceptance standard.


***


## CLI Inspection Scope


Phase 10 must add CLI functionality to inspect and debug all major parts.


### Required inspection areas


- [ ] repository files
- [ ] stored nodes
- [ ] stored edges
- [ ] one symbol payload
- [ ] one symbol context payload
- [ ] one symbol references payload
- [ ] one symbol risk payload
- [ ] one MCP tool payload
- [ ] one workflow validation report
- [ ] watch-mode incremental results when invoked manually


### Required CLI output rule


- [ ] every inspection command must support `--json`
- [ ] default human-readable output may exist
- [ ] JSON output must remain the source of truth for debugging payload shapes


Do not make CLI inspection rely only on pretty tables or prose.


***


## Step 1 - Workflow Validation Module


### File


- [ ] `src/repo_context/validation/workflow.py`


### Implement


Add a reusable fixture-driven workflow runner.


### Required entry points


- [ ] `run_full_workflow_validation(conn, repo_root, fixture_name)`
- [ ] `run_symbol_workflow_validation(conn, symbol_id)`
- [ ] `run_mcp_workflow_validation(conn, symbol_id)`
- [ ] `run_watch_workflow_validation(conn, repo_root, changed_paths)`


### Exact behavior


#### `run_full_workflow_validation`
- [ ] scan fixture repo using the real scan pipeline
- [ ] extract symbols using the real extraction pipeline
- [ ] persist graph using the real graph pipeline
- [ ] build symbol contexts for selected symbols
- [ ] enrich references where fixture outputs are available
- [ ] run risk analysis for selected symbols
- [ ] exercise MCP-facing adapters or tools
- [ ] return a structured workflow report


#### `run_symbol_workflow_validation`
- [ ] load one symbol
- [ ] build context
- [ ] inspect references and risk output
- [ ] return a structured report for that symbol


#### `run_mcp_workflow_validation`
- [ ] execute representative MCP tool paths for one symbol
- [ ] validate response wrapper shape
- [ ] validate data payload shape
- [ ] return a structured report


#### `run_watch_workflow_validation`
- [ ] simulate or trigger changed-file handling
- [ ] verify graph mutation or no-op behavior
- [ ] verify downstream invalidation state
- [ ] return a structured report


### Do not do


- [ ] do not replace real services with fake logic here
- [ ] do not return only pass/fail without structured details


### Done when


- [ ] one module can run real acceptance checks over the composed workflow


***


## Step 2 - Graph Shape Validators


### File


- [ ] `src/repo_context/validation/graph_checks.py`


### Implement


Add deterministic graph-shape assertions and reusable checks.


### Required checks


- [ ] `assert_file_nodes_exist`
- [ ] `assert_module_nodes_exist`
- [ ] `assert_expected_symbol_kinds`
- [ ] `assert_nested_scope_symbols_present`
- [ ] `assert_structural_edges_present`
- [ ] `assert_no_duplicate_stable_ids`
- [ ] `assert_reference_edge_shape`


### Exact behavior


- [ ] validate graph shape using stored nodes and edges
- [ ] validate representative symbol kinds from earlier phases
- [ ] validate phase 03b nested-scope symbols when fixture expects them
- [ ] validate phase 6 `references` edges where present
- [ ] return structured failure details or raise deterministic assertion failures


### Do not do


- [ ] do not rely only on raw row counts
- [ ] do not ignore shape-level failures because totals look correct


### Done when


- [ ] the project can verify that graph truth is structurally usable, not just non-empty


***


## Step 3 - Context Shape Validators


### File


- [ ] `src/repo_context/validation/context_checks.py`


### Implement


Add deterministic context-shape assertions and reusable checks.


### Required checks


- [ ] `assert_context_has_focus_symbol`
- [ ] `assert_context_has_structural_relationships`
- [ ] `assert_context_has_lexical_relationships`
- [ ] `assert_reference_summary_shape`
- [ ] `assert_freshness_shape`
- [ ] `assert_confidence_shape`
- [ ] `assert_context_is_agent_usable`


### Exact behavior


- [ ] validate that context payloads include stable IDs and expected top-level fields
- [ ] validate separate structural and lexical fields
- [ ] validate reference summary shape and availability semantics
- [ ] validate freshness and confidence sections exist and are typed correctly
- [ ] validate child and edge lists are deterministic


### Required availability rule


- [ ] unrefreshed symbols must not be validated as “zero references”
- [ ] refreshed-zero symbols must remain distinct from unavailable symbols


### Do not do


- [ ] do not treat a pretty printed context dump as sufficient validation
- [ ] do not accept merged parent semantics that hide structural vs lexical distinctions


### Done when


- [ ] the project can verify that symbol context payloads are structurally consumable by an agent


***


## Step 4 - Reference Shape Validators


### File


- [ ] `src/repo_context/validation/reference_checks.py`


### Implement


Add deterministic reference-shape assertions and reusable checks.


### Required checks


- [ ] `assert_references_payload_shape`
- [ ] `assert_reference_summary_availability_semantics`
- [ ] `assert_reference_edge_evidence_shape`
- [ ] `assert_referenced_by_derivation_shape`
- [ ] `assert_reference_state_is_agent_usable`


### Exact behavior


- [ ] validate stored reference lists and summaries
- [ ] validate evidence fields and confidence fields
- [ ] validate explicit `available` semantics
- [ ] validate reverse lookup payloads if exposed through existing helpers


### Do not do


- [ ] do not validate references using counts only
- [ ] do not hide unavailable state behind empty lists alone


### Done when


- [ ] reference outputs are verified as structured tool-usable truth


***


## Step 5 - Risk Shape Validators


### File


- [ ] `src/repo_context/validation/risk_checks.py`


### Implement


Add deterministic risk-shape assertions and reusable checks.


### Required checks


- [ ] `assert_risk_result_shape`
- [ ] `assert_risk_targets_shape`
- [ ] `assert_risk_facts_shape`
- [ ] `assert_risk_issue_codes_shape`
- [ ] `assert_risk_is_agent_usable`


### Exact behavior


- [ ] validate that risk outputs preserve targets, facts, issues, score, and decision
- [ ] validate issue ordering deterministically
- [ ] validate explicit availability facts are preserved
- [ ] validate no critical interpretation is hidden in prose


### Do not do


- [ ] do not treat a single risk score as sufficient
- [ ] do not accept stringified blobs instead of structured facts


### Done when


- [ ] risk outputs are validated as real machine-friendly contracts


***


## Step 6 - MCP Contract Validators


### File


- [ ] `src/repo_context/validation/mcp_checks.py`
- [ ] `src/repo_context/validation/contracts.py`


### Implement


Add schema and payload validation for MCP tool outputs.


### Required checks


- [ ] `assert_tool_result_shape`
- [ ] `assert_tool_error_shape`
- [ ] `assert_resolve_symbol_payload`
- [ ] `assert_symbol_context_payload`
- [ ] `assert_symbol_references_payload`
- [ ] `assert_risk_payload`
- [ ] `assert_mcp_payload_is_agent_usable`
- [ ] optional JSON Schema validation against published MCP schemas if already easy in the project


### Exact behavior


- [ ] validate real tool outputs or adapter outputs
- [ ] confirm required fields exist
- [ ] confirm field types are correct
- [ ] confirm deterministic wrapper shape is preserved
- [ ] confirm ambiguity and not-found results are structurally recoverable
- [ ] confirm output shape matches the published contract as closely as the project supports


### Required MCP rule


- [ ] if output schemas are published, actual structured results must conform to them
- [ ] contract drift must fail validation loudly


### Do not do


- [ ] do not test only happy-path tool calls
- [ ] do not trust schema declarations without validating real outputs


### Done when


- [ ] MCP payloads are validated as real machine contracts rather than hopeful documentation


***


## Step 7 - Fixture Workflow Scenarios


### Files to use


- [ ] existing fixtures from phases 3 through 9
- [ ] add focused workflow fixtures under `tests/fixtures/real_workflow/` if needed


### Minimum scenario coverage


- [ ] one simple module with one top-level function
- [ ] one nested-scope fixture with local function or local class
- [ ] one cross-file reference fixture
- [ ] one public heavily referenced symbol fixture
- [ ] one inheritance fixture
- [ ] one watch invalidation fixture
- [ ] one ambiguity fixture with duplicate qualified names under different files or scopes


### Implement


For each selected scenario:


- [ ] run real earlier-phase services
- [ ] validate graph shape
- [ ] validate context shape
- [ ] validate references shape
- [ ] validate MCP-facing payload shape
- [ ] validate risk payload shape
- [ ] capture deterministic expected assertions


### Do not do


- [ ] do not depend on human judgment during test execution
- [ ] do not leave acceptance criteria implicit


### Done when


- [ ] the project has representative end-to-end scenarios covering the real workflow surface


***


## Step 8 - Watch and Invalidation Workflow Checks


### Files to modify


- [ ] `src/repo_context/validation/workflow.py`
- [ ] tests under `tests/`


### Implement


Add composed checks for watch mode plus downstream honesty.


### Required behavior


- [ ] mutate a fixture file
- [ ] trigger incremental reindex path
- [ ] verify updated graph shape
- [ ] verify invalidated reference summaries become unavailable or stale
- [ ] verify context builder reflects that state honestly
- [ ] verify MCP `get_symbol_context` or `get_symbol_references` shows the same honest state
- [ ] verify risk results preserve explicit uncertainty where applicable


### Do not do


- [ ] do not stop validation at storage mutation only
- [ ] do not hide stale reference state from later layers


### Done when


- [ ] watch invalidation is verified all the way through agent-facing outputs


***


## Step 9 - CLI Inspection Commands


### Files to modify


- [ ] existing CLI module from earlier phases
- [ ] small CLI formatting helpers if needed


### Implement


Add these commands.


### Graph inspection commands

#### Command 1
- [ ] `repo-context inspect-file <repo-relative-path>`

### Required behavior
- [ ] show tracked file metadata
- [ ] show file ID and URI if available
- [ ] support `--json`

#### Command 2
- [ ] `repo-context inspect-node <node-id>`

### Required behavior
- [ ] show raw normalized stored node payload
- [ ] support `--json`

#### Command 3
- [ ] `repo-context inspect-edge <edge-id>`

### Required behavior
- [ ] show raw normalized stored edge payload
- [ ] support `--json`

#### Command 4
- [ ] `repo-context inspect-graph-for-file <repo-relative-path>`

### Required behavior
- [ ] list nodes and edges owned by one file
- [ ] support `--json`
- [ ] optionally support `--kinds` filtering


### Context inspection commands

#### Command 5
- [ ] `repo-context inspect-context <symbol-id>`

### Required behavior
- [ ] build symbol context using the real context builder
- [ ] print deterministic structured output
- [ ] include structural and lexical relationship sections
- [ ] include reference summary, freshness, and confidence
- [ ] support `--json`

#### Command 6
- [ ] `repo-context inspect-context-by-name <repo-id> <qualified-name>`

### Required behavior
- [ ] resolve a symbol deterministically or fail with ambiguity
- [ ] build context for the resolved symbol
- [ ] support `--kind`
- [ ] support `--file-id`
- [ ] support `--json`


### Reference inspection commands

#### Command 7
- [ ] `repo-context inspect-references <symbol-id>`

### Required behavior
- [ ] show stored incoming `references` edges for the target symbol
- [ ] show summary and availability state
- [ ] support `--json`

#### Command 8
- [ ] `repo-context inspect-referenced-by <symbol-id>`

### Required behavior
- [ ] show reverse-derived referencing symbols or stable reverse payload
- [ ] support `--json`

#### Command 9
- [ ] `repo-context inspect-references-from <symbol-id>`

### Required behavior
- [ ] show outgoing stored `references` edges where the symbol is the usage source
- [ ] support `--json`


### Risk inspection commands

#### Command 10
- [ ] `repo-context inspect-risk <symbol-id>`

### Required behavior
- [ ] run the real risk engine for one symbol
- [ ] print targets, facts, issues, score, and decision
- [ ] support `--json`

#### Command 11
- [ ] `repo-context inspect-risk-set <symbol-id-1> <symbol-id-2> ...`

### Required behavior
- [ ] run the real risk engine for multiple symbols
- [ ] print aggregate deterministic output
- [ ] support `--json`


### MCP inspection commands

#### Command 12
- [ ] `repo-context inspect-mcp-context <symbol-id>`

### Required behavior
- [ ] call the same path used by MCP-facing context output, either through the tool handler or adapter layer
- [ ] print the exact or near-exact payload shape an agent would see
- [ ] support `--json`

#### Command 13
- [ ] `repo-context inspect-mcp-references <symbol-id>`

### Required behavior
- [ ] return the same payload shape used by the MCP `get_symbol_references` tool
- [ ] support `--json`

#### Command 14
- [ ] `repo-context inspect-mcp-risk <symbol-id>`

### Required behavior
- [ ] return the same payload shape used by the MCP `analyze_symbol_risk` tool
- [ ] support `--json`

#### Command 15
- [ ] `repo-context inspect-mcp-tool <tool-name> <json-input>`

### Required behavior
- [ ] execute one MCP tool locally without running the full server when possible
- [ ] print structured tool output
- [ ] support exact contract debugging
- [ ] fail clearly if tool name is unknown or input JSON is invalid


### Workflow inspection commands

#### Command 16
- [ ] `repo-context validate-workflow <fixture-name>`

### Required behavior
- [ ] run the full workflow validation for one fixture
- [ ] print a structured validation report
- [ ] support `--json`

#### Command 17
- [ ] `repo-context validate-symbol-workflow <symbol-id>`

### Required behavior
- [ ] run symbol-focused workflow validation
- [ ] print graph, context, references, risk, and MCP validation summary
- [ ] support `--json`

#### Command 18
- [ ] `repo-context debug-reindex-file <absolute-or-relative-path>`

### Required behavior
- [ ] run the same incremental reindex path used by watch mode
- [ ] print structured per-file summary
- [ ] support `--json`

#### Command 19
- [ ] `repo-context debug-delete-file <repo-relative-path>`

### Required behavior
- [ ] run the same deleted-file cleanup path used by watch mode
- [ ] print structured summary
- [ ] support `--json`

#### Command 20
- [ ] `repo-context debug-normalize-event <path> --event-type <created|modified|deleted>`

### Required behavior
- [ ] run event normalization logic for one synthetic event
- [ ] print normalized event payload or explicit skip reason
- [ ] support `--json`


### Do not do


- [ ] do not print only pretty prose summaries
- [ ] do not make inspection commands silently auto-refresh references unless the command explicitly says refresh
- [ ] do not invent alternate payload names that differ from production outputs when avoidable


### Done when


- [ ] developers can inspect raw agent-facing and storage-facing state across all major system parts from CLI without guessing


***


## Step 10 - CLI Output Rules


### Files to verify


- [ ] CLI formatting helpers if any
- [ ] adapters if reused


### Implement


Use these output rules:


- [ ] default output may be readable structured text
- [ ] `--json` must print machine-friendly JSON
- [ ] field names must match internal or MCP-facing payloads exactly where possible
- [ ] missing optional sections must remain explicit rather than being silently omitted if omission causes ambiguity
- [ ] command exit codes must be deterministic
- [ ] invalid input must fail clearly


### Do not do


- [ ] do not invent alternate field names just for CLI aesthetics
- [ ] do not hide availability flags or ambiguity details in text only


### Done when


- [ ] CLI inspection is useful for both humans and contract-debugging


***


## Step 11 - Extensive Test Suite


### Files to create or modify


- [ ] phase 10 tests under `tests/`
- [ ] fixtures under `tests/fixtures/real_workflow/` as needed


### Test strategy


- [ ] combine contract tests, integration tests, and acceptance tests
- [ ] prefer real earlier-phase services over excessive mocking
- [ ] allow fake LSP outputs where deterministic references are required
- [ ] verify payload shape, not just business outcomes
- [ ] verify CLI JSON outputs for key inspection commands


### Implement these tests


- [ ] `test_full_workflow_simple_fixture`
- [ ] `test_full_workflow_nested_scope_fixture`
- [ ] `test_full_workflow_reference_fixture`
- [ ] `test_full_workflow_risk_fixture`
- [ ] `test_full_workflow_watch_invalidation_fixture`
- [ ] `test_context_payload_is_agent_usable`
- [ ] `test_references_payload_is_agent_usable`
- [ ] `test_risk_payload_is_agent_usable`
- [ ] `test_mcp_context_payload_matches_contract`
- [ ] `test_mcp_resolve_symbol_ambiguity_payload`
- [ ] `test_reference_unavailable_is_not_zero`
- [ ] `test_inspect_context_cli_output`
- [ ] `test_inspect_references_cli_output`
- [ ] `test_inspect_risk_cli_output`
- [ ] `test_inspect_mcp_context_cli_output`
- [ ] `test_inspect_mcp_tool_cli_output`
- [ ] `test_validate_workflow_cli_output`
- [ ] `test_debug_reindex_file_cli_output`


### Exact test assertions


#### `test_full_workflow_simple_fixture`
- [ ] scan, extract, persist, and context build all succeed
- [ ] expected graph nodes and edges exist
- [ ] context shape is valid


#### `test_full_workflow_nested_scope_fixture`
- [ ] nested symbols persist correctly
- [ ] lexical relationships are present
- [ ] MCP-facing context preserves those relationships


#### `test_full_workflow_reference_fixture`
- [ ] stored `references` edges have expected shape
- [ ] reference summary is correct
- [ ] MCP references payload is valid


#### `test_full_workflow_risk_fixture`
- [ ] risk result includes targets, facts, issues, score, and decision
- [ ] issue codes are deterministic
- [ ] availability facts are preserved


#### `test_full_workflow_watch_invalidation_fixture`
- [ ] watch-triggered update changes file graph state
- [ ] stale or unavailable references propagate honestly into context and MCP payloads


#### `test_context_payload_is_agent_usable`
- [ ] required stable IDs and relationships exist
- [ ] no critical field is only implied in prose
- [ ] payload shape is deterministic


#### `test_references_payload_is_agent_usable`
- [ ] evidence fields and summary fields exist
- [ ] availability semantics are correct


#### `test_risk_payload_is_agent_usable`
- [ ] facts and issues remain structured
- [ ] score and decision are present
- [ ] payload is deterministic


#### `test_mcp_context_payload_matches_contract`
- [ ] actual MCP context payload contains required fields
- [ ] structural and lexical relationships are separate
- [ ] reference summary shape is correct


#### `test_mcp_resolve_symbol_ambiguity_payload`
- [ ] ambiguous symbol lookup returns structured candidate details
- [ ] payload is recoverable by an agent without guessing


#### `test_reference_unavailable_is_not_zero`
- [ ] never-refreshed reference summary remains unavailable
- [ ] refreshed-zero remains a separate state


#### `test_inspect_context_cli_output`
- [ ] CLI returns expected top-level context shape
- [ ] `--json` output is valid JSON


#### `test_inspect_references_cli_output`
- [ ] CLI returns references and summary
- [ ] availability field is present


#### `test_inspect_risk_cli_output`
- [ ] CLI returns structured risk payload
- [ ] facts and issues are present


#### `test_inspect_mcp_context_cli_output`
- [ ] CLI returns expected MCP top-level payload shape
- [ ] `--json` output is valid machine-readable JSON


#### `test_inspect_mcp_tool_cli_output`
- [ ] tool invocation path returns stable wrapper shape
- [ ] invalid JSON input fails clearly


#### `test_validate_workflow_cli_output`
- [ ] validation report contains per-layer results
- [ ] overall pass or failure is explicit


#### `test_debug_reindex_file_cli_output`
- [ ] reindex debug command returns structured summary
- [ ] summary status is explicit


### Do not do


- [ ] do not rely only on smoke tests
- [ ] do not only test internal Python objects while ignoring tool-facing payloads


### Done when


- [ ] the real workflow is covered by deterministic acceptance tests that validate both truth and usability


***


## Step 12 - Acceptance Report


### File


- [ ] `docs/10-real-workflow.md`


### Implement


Document the final acceptance workflow and expected guarantees.


### Required sections


- [ ] scope
- [ ] required fixtures
- [ ] validation layers
- [ ] CLI inspection commands
- [ ] acceptance commands
- [ ] known limits
- [ ] failure interpretation rules
- [ ] debug workflow examples


### Required acceptance commands


Include commands such as:
- [ ] full fixture indexing command
- [ ] reference refresh command
- [ ] risk analysis command
- [ ] `inspect-context`
- [ ] `inspect-references`
- [ ] `inspect-risk`
- [ ] `inspect-mcp-context`
- [ ] `inspect-mcp-tool`
- [ ] `validate-workflow`
- [ ] watch-mode validation command if present


### Do not do


- [ ] do not leave the final acceptance workflow implicit in scattered test files
- [ ] do not describe guarantees that are not actually tested


### Done when


- [ ] one document explains how to prove the whole system works as intended


***


## Step 13 - Help Guide


### File


- [ ] `docs/10-real-workflow.md`


### Implement


Add a small practical help guide at the end of the document.


### Required help sections


- [ ] common debugging goals
- [ ] command reference
- [ ] concrete examples
- [ ] typical failure cases
- [ ] recommended debug sequence


### Required command reference entries


Include at minimum:
- [ ] `repo-context inspect-file`
- [ ] `repo-context inspect-node`
- [ ] `repo-context inspect-edge`
- [ ] `repo-context inspect-graph-for-file`
- [ ] `repo-context inspect-context`
- [ ] `repo-context inspect-context-by-name`
- [ ] `repo-context inspect-references`
- [ ] `repo-context inspect-referenced-by`
- [ ] `repo-context inspect-references-from`
- [ ] `repo-context inspect-risk`
- [ ] `repo-context inspect-risk-set`
- [ ] `repo-context inspect-mcp-context`
- [ ] `repo-context inspect-mcp-references`
- [ ] `repo-context inspect-mcp-risk`
- [ ] `repo-context inspect-mcp-tool`
- [ ] `repo-context validate-workflow`
- [ ] `repo-context validate-symbol-workflow`
- [ ] `repo-context debug-reindex-file`
- [ ] `repo-context debug-delete-file`
- [ ] `repo-context debug-normalize-event`


### Required example style


- [ ] each example must be concrete
- [ ] each example must use realistic placeholder values
- [ ] at least one example must show `--json`
- [ ] at least one example must show a pipe into `jq`
- [ ] examples must distinguish read-only inspection from mutating debug commands


### Example commands to include


- [ ] `repo-context inspect-context node:repo123:symbol:pkg.module.foo --json`
- [ ] `repo-context inspect-mcp-context node:repo123:symbol:pkg.module.foo --json | jq`
- [ ] `repo-context inspect-references node:repo123:symbol:pkg.module.foo --json`
- [ ] `repo-context inspect-risk node:repo123:symbol:pkg.module.foo --json`
- [ ] `repo-context inspect-context-by-name repo123 pkg.module.foo --kind function --json`
- [ ] `repo-context inspect-mcp-tool get_symbol_context '{"symbol_id":"node:repo123:symbol:pkg.module.foo"}'`
- [ ] `repo-context validate-workflow references_case --json`
- [ ] `repo-context debug-reindex-file src/pkg/module.py --json`
- [ ] `repo-context debug-normalize-event src/pkg/module.py --event-type modified --json`


### Do not do


- [ ] do not end the document without practical usage guidance
- [ ] do not rely on abstract examples only


### Done when


- [ ] a developer can use the document itself to inspect and debug the whole system without guesswork


***


## Step 14 - Final Verification


Before marking phase 10 complete, verify all of the following:


- [ ] phases 1 through 9 can be exercised together through real fixtures
- [ ] stored graph shape is validated, not just assumed
- [ ] nested-scope graph data is validated
- [ ] symbol context shape is validated
- [ ] structural vs lexical relationships stay separate
- [ ] reference availability vs zero is validated
- [ ] MCP payloads are validated against expected contracts
- [ ] risk results are validated as structured machine-friendly payloads
- [ ] CLI inspection commands work
- [ ] `inspect-mcp-context` shows the real agent-facing shape
- [ ] `inspect-mcp-tool` can debug tool contracts locally
- [ ] watch invalidation honesty is validated through later layers
- [ ] tests pass


Do not mark phase 10 done until every box above is true.


***


## Required Execution Order


Implement in this order and do not skip ahead:


- [ ] Step 1 workflow validation module
- [ ] Step 2 graph shape validators
- [ ] Step 3 context shape validators
- [ ] Step 4 reference shape validators
- [ ] Step 5 risk shape validators
- [ ] Step 6 MCP contract validators
- [ ] Step 7 fixture workflow scenarios
- [ ] Step 8 watch and invalidation workflow checks
- [ ] Step 9 CLI inspection commands
- [ ] Step 10 CLI output rules
- [ ] Step 11 extensive test suite
- [ ] Step 12 acceptance report
- [ ] Step 13 help guide
- [ ] Step 14 final verification


***


## Phase 10 Done Definition


Phase 10 is complete only when all of these are true:


- [ ] phases 1 through 9 are verified together through deterministic workflows
- [ ] stored graph shape is tested for real usability
- [ ] symbol context shape is tested for real agent usability
- [ ] reference payloads and availability semantics are tested for real agent usability
- [ ] MCP output contracts are tested against real outputs
- [ ] risk outputs remain structured and usable
- [ ] unavailable references remain distinct from refreshed-zero references
- [ ] CLI inspection exposes real graph, context, references, risk, and MCP-facing payloads
- [ ] practical debugging commands and examples exist in the doc
- [ ] tests pass


***


## Help Guide


Use this section to inspect the system quickly when something looks wrong.


### Common goals


Use these commands for the most common debugging tasks:

- Check whether a file is tracked and mapped correctly.
- Check what nodes and edges exist for one file.
- Check the exact symbol context the internal builder returns.
- Check the exact MCP payload the agent would receive.
- Check whether references are unavailable, zero, or nonzero.
- Check whether the risk engine is missing facts or flattening them badly.
- Check whether a watch-mode file change actually updated the graph.


### Command reference


#### Inspect tracked file metadata
```bash
repo-context inspect-file src/pkg/module.py
repo-context inspect-file src/pkg/module.py --json
```

#### Inspect one stored node
```bash
repo-context inspect-node node:repo123:symbol:pkg.module.foo
repo-context inspect-node node:repo123:symbol:pkg.module.foo --json | jq
```

#### Inspect one stored edge
```bash
repo-context inspect-edge edge:repo123:references:nodeA->nodeB:12:4
repo-context inspect-edge edge:repo123:references:nodeA->nodeB:12:4 --json
```

#### Inspect all graph state for one file
```bash
repo-context inspect-graph-for-file src/pkg/module.py
repo-context inspect-graph-for-file src/pkg/module.py --json | jq
```

#### Inspect internal symbol context
```bash
repo-context inspect-context node:repo123:symbol:pkg.module.foo
repo-context inspect-context node:repo123:symbol:pkg.module.foo --json | jq
```

#### Resolve by name, then inspect context
```bash
repo-context inspect-context-by-name repo123 pkg.module.foo
repo-context inspect-context-by-name repo123 pkg.module.foo --kind function --json
repo-context inspect-context-by-name repo123 pkg.module.foo --kind function --file-id file:repo123:src/pkg/module.py --json | jq
```

#### Inspect stored references
```bash
repo-context inspect-references node:repo123:symbol:pkg.module.foo
repo-context inspect-references node:repo123:symbol:pkg.module.foo --json | jq
```

#### Inspect reverse-derived callers
```bash
repo-context inspect-referenced-by node:repo123:symbol:pkg.module.foo
repo-context inspect-referenced-by node:repo123:symbol:pkg.module.foo --json
```

#### Inspect outgoing references from one symbol
```bash
repo-context inspect-references-from node:repo123:symbol:pkg.module.call_site
repo-context inspect-references-from node:repo123:symbol:pkg.module.call_site --json
```

#### Refresh references explicitly
```bash
repo-context refresh-references node:repo123:symbol:pkg.module.foo
```

#### Inspect risk for one symbol
```bash
repo-context inspect-risk node:repo123:symbol:pkg.module.foo
repo-context inspect-risk node:repo123:symbol:pkg.module.foo --json | jq
```

#### Inspect risk for multiple symbols
```bash
repo-context inspect-risk-set node:repo123:symbol:pkg.module.foo node:repo123:symbol:pkg.module.bar
repo-context inspect-risk-set node:repo123:symbol:pkg.module.foo node:repo123:symbol:pkg.module.bar --json
```

#### Inspect the MCP-facing context payload
```bash
repo-context inspect-mcp-context node:repo123:symbol:pkg.module.foo
repo-context inspect-mcp-context node:repo123:symbol:pkg.module.foo --json | jq
```

#### Inspect the MCP-facing references payload
```bash
repo-context inspect-mcp-references node:repo123:symbol:pkg.module.foo
repo-context inspect-mcp-references node:repo123:symbol:pkg.module.foo --json | jq
```

#### Inspect the MCP-facing risk payload
```bash
repo-context inspect-mcp-risk node:repo123:symbol:pkg.module.foo
repo-context inspect-mcp-risk node:repo123:symbol:pkg.module.foo --json | jq
```

#### Call one MCP tool locally for contract debugging
```bash
repo-context inspect-mcp-tool get_symbol_context '{"symbol_id":"node:repo123:symbol:pkg.module.foo"}'
repo-context inspect-mcp-tool get_symbol_references '{"symbol_id":"node:repo123:symbol:pkg.module.foo"}' --json | jq
repo-context inspect-mcp-tool analyze_symbol_risk '{"symbol_id":"node:repo123:symbol:pkg.module.foo"}'
```

#### Validate one fixture workflow
```bash
repo-context validate-workflow references_case
repo-context validate-workflow references_case --json | jq
```

#### Validate one symbol workflow
```bash
repo-context validate-symbol-workflow node:repo123:symbol:pkg.module.foo
repo-context validate-symbol-workflow node:repo123:symbol:pkg.module.foo --json
```

#### Debug the incremental reindex path directly
```bash
repo-context debug-reindex-file src/pkg/module.py
repo-context debug-reindex-file src/pkg/module.py --json | jq
```

#### Debug the deleted-file cleanup path directly
```bash
repo-context debug-delete-file src/pkg/old_module.py
repo-context debug-delete-file src/pkg/old_module.py --json
```

#### Debug event normalization directly
```bash
repo-context debug-normalize-event src/pkg/module.py --event-type modified
repo-context debug-normalize-event src/pkg/module.py --event-type modified --json
repo-context debug-normalize-event src/pkg/new_module.py --event-type created --json
```


### Recommended debug sequence


When a symbol “looks wrong,” use this order:

1. Inspect the file.
2. Inspect the file graph.
3. Inspect the node.
4. Inspect the internal context.
5. Inspect stored references.
6. Inspect MCP context.
7. Inspect MCP tool output directly.
8. Inspect risk output.
9. If the file changed recently, run debug reindex or validate watch behavior.

Example:
```bash
repo-context inspect-file src/pkg/module.py --json | jq
repo-context inspect-graph-for-file src/pkg/module.py --json | jq
repo-context inspect-context node:repo123:symbol:pkg.module.foo --json | jq
repo-context inspect-references node:repo123:symbol:pkg.module.foo --json | jq
repo-context inspect-mcp-context node:repo123:symbol:pkg.module.foo --json | jq
repo-context inspect-risk node:repo123:symbol:pkg.module.foo --json | jq
```


### Typical failure cases


#### Context looks empty
Possible causes:
- symbol ID is wrong
- symbol exists but graph replacement failed earlier
- lexical or structural relationships were not persisted as expected

Start with:
```bash
repo-context inspect-node <symbol-id> --json | jq
repo-context inspect-context <symbol-id> --json | jq
```

#### References show zero but should not
Possible causes:
- references were never refreshed
- references were invalidated by watch mode
- the symbol was changed and availability became stale

Check:
```bash
repo-context inspect-references <symbol-id> --json | jq
repo-context inspect-mcp-references <symbol-id> --json | jq
```

Look specifically for:
- `reference_summary.available`
- `reference_count`
- `last_refreshed_at`

#### MCP output differs from internal context
Possible causes:
- adapter drift
- tool handler shape drift
- schema drift

Check:
```bash
repo-context inspect-context <symbol-id> --json | jq
repo-context inspect-mcp-context <symbol-id> --json | jq
repo-context inspect-mcp-tool get_symbol_context '{"symbol_id":"<symbol-id>"}' --json | jq
```

#### Risk looks too low or too high
Possible causes:
- reference availability was flattened incorrectly
- local-scope or public-surface heuristics were applied wrongly
- issue ordering or scoring drifted

Check:
```bash
repo-context inspect-risk <symbol-id> --json | jq
repo-context inspect-mcp-risk <symbol-id> --json | jq
```

#### Watch mode did not update what you expected
Possible causes:
- event was ignored
- file extension unsupported
- parse failure preserved old graph state
- reference invalidation happened but re-refresh did not

Check:
```bash
repo-context debug-normalize-event src/pkg/module.py --event-type modified --json
repo-context debug-reindex-file src/pkg/module.py --json | jq
repo-context inspect-graph-for-file src/pkg/module.py --json | jq
repo-context inspect-references <symbol-id> --json | jq
```


### Read-only vs mutating commands


Treat these as read-only:
- `inspect-file`
- `inspect-node`
- `inspect-edge`
- `inspect-graph-for-file`
- `inspect-context`
- `inspect-context-by-name`
- `inspect-references`
- `inspect-referenced-by`
- `inspect-references-from`
- `inspect-risk`
- `inspect-risk-set`
- `inspect-mcp-context`
- `inspect-mcp-references`
- `inspect-mcp-risk`
- `inspect-mcp-tool`
- `validate-workflow`
- `validate-symbol-workflow`

Treat these as mutating or state-changing:
- `refresh-references`
- `debug-reindex-file`
- `debug-delete-file`

Do not confuse them during debugging.


### Minimal useful examples


#### See exactly what the agent would get for one symbol
```bash
repo-context inspect-mcp-context node:repo123:symbol:pkg.module.foo --json | jq
```

#### Check whether references are unavailable or truly zero
```bash
repo-context inspect-references node:repo123:symbol:pkg.module.foo --json | jq '.reference_summary'
```

#### Check why risk is high
```bash
repo-context inspect-risk node:repo123:symbol:pkg.module.foo --json | jq '{issues, risk_score, decision, facts}'
```

#### Validate one fixture end to end
```bash
repo-context validate-workflow references_case --json | jq
```
```

## Blunt advice

This version is better than a small patch. It gives you a real debugging surface.

The most important commands are probably:

- `inspect-context`
- `inspect-references`
- `inspect-risk`
- `inspect-mcp-context`
- `inspect-mcp-tool`
- `validate-workflow`
- `debug-reindex-file`

If you only implement two extra commands, make them:

- `inspect-mcp-context`
- `inspect-mcp-tool`

Because those two catch a stupid amount of integration drift fast. [modelcontextprotocol](https://modelcontextprotocol.io/docs/tools/inspector)