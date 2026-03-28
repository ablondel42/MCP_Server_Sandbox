# 07 Risk Engine - Exact Implementation Checklist


## Objective


Implement phase 7 of the repository indexing pipeline.


Phase 7 must turn stored graph facts and LSP-enriched reference facts into a reusable deterministic risk engine that can analyze one symbol or a set of symbols and return:


- normalized targets
- deterministic facts
- issue codes
- risk score
- decision


Phase 7 must provide:
- one reusable risk engine module
- target normalization
- risk fact extraction
- issue detection
- score computation
- decision computation
- symbol-level risk analysis
- target-set risk analysis
- CLI inspection commands
- tests for facts, rules, scores, and decisions
- compatibility with nested-scope symbols introduced in phase 03b
- compatibility with explicit reference availability state introduced in phase 6


Phase 7 must not provide:
- MCP server implementation
- final plan-evaluation wrapper contract
- autonomous plan rewriting
- freeform narrative analysis
- diff-aware mutation analysis
- runtime validation
- test execution
- watch mode


***


## Consistency Rules


These rules are mandatory.


- [ ] Reuse the existing phase 1 through phase 6 models, graph queries, context builder, nested-scope behavior, and reference enrichment outputs.
- [ ] Keep the engine reusable and independent of any one workflow wrapper.
- [ ] Keep the engine deterministic.
- [ ] Separate facts, issues, score, and decision into distinct steps.
- [ ] Do not put risk logic in CLI handlers.
- [ ] Do not put risk logic in MCP adapters.
- [ ] Do not put risk logic in context-builder modules.
- [ ] Do not treat unavailable reference data as known zero.
- [ ] Keep outputs machine-friendly and JSON-friendly.
- [ ] Keep thresholds explicit and easy to tune later.
- [ ] Preserve the distinction between structural hierarchy and lexical nesting.
- [ ] Treat local functions, local async functions, and local classes as valid first-class risk targets.
- [ ] Keep issue ordering deterministic and stable.


***


## Required Inputs


Phase 7 must consume these existing inputs:


- [ ] stored nodes
- [ ] stored edges
- [ ] graph query helpers
- [ ] symbol context helpers from phase 5
- [ ] reference stats, refresh state, and `references` edges from phase 6
- [ ] resolved symbol IDs


Do not make the risk engine responsible for unresolved-target plan parsing.


***


## Required Outputs


Phase 7 must produce these capabilities:


- [ ] analyze one symbol by symbol ID
- [ ] analyze multiple symbols by symbol ID list
- [ ] normalize raw symbols into `RiskTarget`
- [ ] compute deterministic `RiskFacts`
- [ ] detect issue codes
- [ ] compute risk score
- [ ] compute decision
- [ ] return a reusable `RiskResult`
- [ ] inspect results from CLI


Do not add plan-level text generation in this phase.


***


## Required File Layout


Create or extend these files:


- [ ] `src/repo_context/graph/risk_engine.py`
- [ ] `src/repo_context/graph/risk_facts.py`
- [ ] `src/repo_context/graph/risk_rules.py`
- [ ] `src/repo_context/graph/risk_scoring.py`
- [ ] `src/repo_context/graph/risk_targets.py`
- [ ] `src/repo_context/graph/risk_types.py`


Reuse existing files if they already exist.


Do not collapse all risk logic into one giant file.


***


## Core Data Contracts


Phase 7 must define and use these reusable engine-level types:


- [ ] `RiskTarget`
- [ ] `RiskFacts`
- [ ] `RiskResult`


Do not force everything into a later `PlanAssessment` type in this phase.


***


## Risk Model Rules


Apply these rules exactly.


- [ ] facts must represent stored or directly-derived graph truth only
- [ ] issues must be derived only from facts
- [ ] score must be derived only from issue codes and explicit weights
- [ ] decision must be derived only from score and explicit override rules
- [ ] no step may depend on LLM output
- [ ] no step may silently assume missing enrichment means zero impact


Do not blend the layers together.


***


## Step 1 - Define Risk Types


### File


- [ ] `src/repo_context/graph/risk_types.py`


### Implement


Define these contracts:


- [ ] `RiskTarget`
- [ ] `RiskFacts`
- [ ] `RiskResult`


### Required `RiskTarget` fields


- [ ] `symbol_id`
- [ ] `qualified_name`
- [ ] `kind`
- [ ] `scope`
- [ ] `file_id`
- [ ] `file_path`
- [ ] `module_path`
- [ ] `visibility_hint`
- [ ] `lexical_parent_id`


### Required `RiskFacts` fields


- [ ] `target_count`
- [ ] `symbol_ids`
- [ ] `symbol_kinds`
- [ ] `reference_counts`
- [ ] `reference_availability`
- [ ] `referencing_file_counts`
- [ ] `referencing_module_counts`
- [ ] `touches_public_surface`
- [ ] `touches_local_scope_only`
- [ ] `target_spans_multiple_files`
- [ ] `target_spans_multiple_modules`
- [ ] `cross_file_impact`
- [ ] `cross_module_impact`
- [ ] `inheritance_involved`
- [ ] `stale_symbols`
- [ ] `low_confidence_symbols`
- [ ] `low_confidence_edges`
- [ ] `extra`


### Required `RiskResult` fields


- [ ] `targets`
- [ ] `facts`
- [ ] `issues`
- [ ] `risk_score`
- [ ] `decision`


### Required behavior


- [ ] types must be JSON-friendly
- [ ] default values must be safe and deterministic
- [ ] no field may require LLM-generated text


### Do not do


- [ ] do not add prose explanation fields
- [ ] do not add plan-wrapper-only fields


### Done when


- [ ] one stable reusable engine contract exists


***


## Step 2 - Risk Engine Entry Points


### File


- [ ] `src/repo_context/graph/risk_engine.py`


### Implement


- [ ] `analyze_symbol_risk(conn, symbol_id)`
- [ ] `analyze_target_set_risk(conn, symbol_ids)`


### Exact behavior


#### `analyze_symbol_risk`
- [ ] delegate to `analyze_target_set_risk` with one symbol ID


#### `analyze_target_set_risk`
- [ ] normalize targets
- [ ] build facts
- [ ] detect issues
- [ ] compute score
- [ ] compute decision
- [ ] return `RiskResult`


### Required build order


- [ ] load targets
- [ ] build facts
- [ ] detect issues
- [ ] score issues
- [ ] decide final decision
- [ ] assemble final result


### Do not do


- [ ] do not mix target resolution from user prose into this module
- [ ] do not return only a score without facts and issues


### Done when


- [ ] the engine can analyze one symbol or multiple symbols with the same core pipeline


***


## Step 3 - Target Normalization


### File


- [ ] `src/repo_context/graph/risk_targets.py`


### Implement


- [ ] `load_risk_targets(conn, symbol_ids)`


### Exact behavior


For each input symbol ID:


- [ ] load the symbol node
- [ ] fail clearly if the symbol does not exist
- [ ] extract `qualified_name`
- [ ] extract `kind`
- [ ] extract `scope`
- [ ] extract `file_id`
- [ ] derive `file_path`
- [ ] derive `module_path`
- [ ] extract `visibility_hint`
- [ ] extract `lexical_parent_id`
- [ ] normalize into `RiskTarget`


### Required dedup rule


- [ ] remove duplicate input symbol IDs while preserving deterministic order


### Required nested-scope rule


- [ ] local functions and local async functions must normalize exactly like other symbols
- [ ] local classes must normalize exactly like other symbols
- [ ] do not reject a target only because it is nested


### Do not do


- [ ] do not silently skip unknown symbol IDs
- [ ] do not keep raw DB rows as engine targets


### Done when


- [ ] the rest of the engine can operate only on normalized `RiskTarget` values


***


## Step 4 - Public Surface Heuristic


### File


- [ ] `src/repo_context/graph/risk_targets.py` or `src/repo_context/graph/risk_facts.py`


### Implement


- [ ] `is_public_like(target)`


### Exact behavior


A target is public-like if:


- [ ] `visibility_hint == "public"`
- [ ] or its name does not start with `_`


### Exact exception behavior


- [ ] magic methods like `__init__`, `__repr__`, and `__call__` must not be treated as private-like just because they start with `_`
- [ ] dunder names must still count as public-like for this heuristic


### Nested-scope rule


- [ ] local functions and local classes inside function scope should not become public-like purely because their short names lack a leading underscore
- [ ] if `scope == "function"`, default to not public-like unless `visibility_hint == "public"` explicitly says otherwise


### Do not do


- [ ] do not invent framework-specific visibility rules
- [ ] do not depend only on one heuristic if both `visibility_hint` and name are available


### Done when


- [ ] the engine has one deterministic public-surface heuristic for all targets


***


## Step 5 - Reference Fact Helpers


### File


- [ ] `src/repo_context/graph/risk_facts.py`


### Implement


- [ ] `get_reference_count(conn, target_id)`
- [ ] `get_reference_availability(conn, target_id)`
- [ ] `get_referencing_file_count(conn, target_id)`
- [ ] `get_referencing_module_count(conn, target_id)`


### Exact behavior


#### `get_reference_count`
- [ ] return the number of stored `references` edges where `to_id = target_id`
- [ ] if references were never refreshed for the target, return a value consistent with explicit availability handling and do not pretend fresh zero truth


#### `get_reference_availability`
- [ ] return explicit refresh availability state from phase 6
- [ ] return `False` if the target has never been refreshed successfully


#### `get_referencing_file_count`
- [ ] count unique `evidence_file_id` values from `references` edges where `to_id = target_id`


#### `get_referencing_module_count`
- [ ] derive module identity from source symbols of `references` edges where `to_id = target_id`
- [ ] count unique source modules deterministically


### Nested-scope rule


- [ ] references from local functions and methods must count toward their containing module correctly
- [ ] do not derive module identity from naive string splitting when stored graph relations already exist


### Do not do


- [ ] do not derive these facts from imports
- [ ] do not treat unavailable reference enrichment as definitely zero without checking availability state


### Done when


- [ ] the engine can compute blast-radius facts from stored `references` data only


***


## Step 6 - Inheritance Risk Helper


### File


- [ ] `src/repo_context/graph/risk_facts.py`


### Implement


- [ ] `target_has_inheritance_risk(conn, target)`


### Exact behavior for class targets


- [ ] if the class has outgoing `inherits` edges, return `True`


### Exact behavior for method targets


- [ ] resolve the structural parent class
- [ ] if the parent class has outgoing `inherits` edges, return `True`
- [ ] otherwise return `False`


### Exact behavior for local functions and local classes


- [ ] local functions must return `False`
- [ ] local classes inside function scope must return `False` in v1 unless the project already persists meaningful inheritance for them


### Exact behavior for other target kinds


- [ ] return `False`


### Do not do


- [ ] do not invent override detection in this phase
- [ ] do not perform deep inheritance traversal


### Done when


- [ ] the engine can flag inheritance involvement using stored structural graph facts only


***


## Step 7 - Freshness Fact Helpers


### File


- [ ] `src/repo_context/graph/risk_facts.py`


### Implement


- [ ] `collect_stale_symbols(conn, targets)`


### Exact behavior


A target must be considered stale if any of these are true:


- [ ] the target node `last_indexed_at` is missing
- [ ] the phase 5 context builder reports stale freshness for the target
- [ ] reference data is unavailable for a target in a way that the project treats as caution-worthy


### Required nested-scope rule


- [ ] apply the same freshness rules to local and nested symbols
- [ ] do not skip nested targets just because they are local


### Required output


- [ ] return a list of stale target symbol IDs
- [ ] preserve deterministic order


### Do not do


- [ ] do not add time-age thresholds yet
- [ ] do not invent smart freshness scoring in this phase


### Done when


- [ ] the engine can carry freshness risk forward from existing graph state honestly


***


## Step 8 - Confidence Fact Helpers


### File


- [ ] `src/repo_context/graph/risk_facts.py`


### Implement


- [ ] `collect_low_confidence_symbols(conn, targets, threshold=0.8)`
- [ ] `collect_low_confidence_edges(conn, targets, threshold=0.8)`


### Exact behavior for symbols


- [ ] collect target symbol IDs whose stored symbol confidence is below threshold


### Exact behavior for edges


- [ ] inspect relevant edges touching the targets, especially `references` edges
- [ ] collect edge IDs whose confidence is below threshold


### Required output


- [ ] preserve deterministic order
- [ ] do not include duplicates


### Do not do


- [ ] do not inspect unrelated repo edges
- [ ] do not hide low-confidence reference mappings


### Done when


- [ ] the engine can detect weak graph evidence explicitly


***


## Step 9 - Build Risk Facts


### File


- [ ] `src/repo_context/graph/risk_facts.py`


### Implement


- [ ] `build_risk_facts(conn, targets)`


### Exact behavior


This function must compute:


- [ ] `target_count`
- [ ] `symbol_ids`
- [ ] `symbol_kinds`
- [ ] `reference_counts`
- [ ] `reference_availability`
- [ ] `referencing_file_counts`
- [ ] `referencing_module_counts`
- [ ] `touches_public_surface`
- [ ] `touches_local_scope_only`
- [ ] `target_spans_multiple_files`
- [ ] `target_spans_multiple_modules`
- [ ] `cross_file_impact`
- [ ] `cross_module_impact`
- [ ] `inheritance_involved`
- [ ] `stale_symbols`
- [ ] `low_confidence_symbols`
- [ ] `low_confidence_edges`
- [ ] `extra`


### Exact target spread rules


#### `target_spans_multiple_files`
- [ ] `True` if target set includes more than one distinct file ID
- [ ] `False` otherwise


#### `target_spans_multiple_modules`
- [ ] `True` if target set includes more than one distinct module path
- [ ] `False` otherwise


### Exact local-scope rule


#### `touches_local_scope_only`
- [ ] `True` if all targets are nested or local declarations with `scope == "function"`
- [ ] `False` otherwise


### Exact reference spread rules


#### `cross_file_impact`
- [ ] `True` if any target has references from more than one file
- [ ] or if any target is referenced from a file other than its own file
- [ ] `False` otherwise
- [ ] if reference availability is `False` for all targets, do not force this fact to `True` or `False` based on missing data alone


#### `cross_module_impact`
- [ ] `True` if any target has references from more than one module
- [ ] or if any target is referenced from a module other than its own module
- [ ] `False` otherwise
- [ ] if reference availability is `False` for all targets, do not force this fact to `True` or `False` based on missing data alone


### Exact public surface rule


- [ ] `touches_public_surface = True` if any target is public-like
- [ ] otherwise `False`


### Exact inheritance rule


- [ ] `inheritance_involved = True` if any target has inheritance risk
- [ ] otherwise `False`


### Required `extra` field rule


- [ ] initialize `extra` as an empty dict unless a deterministic extra fact is actually stored


### Recommended availability extra fields


Store these in `extra` if useful:
- [ ] `all_references_available`
- [ ] `any_references_unavailable`


### Do not do


- [ ] do not jump directly to issues or score here
- [ ] do not blend scoring weights into fact extraction


### Done when


- [ ] the engine has one clean deterministic fact layer that is reusable everywhere


***


## Step 10 - Issue Code Detection


### File


- [ ] `src/repo_context/graph/risk_rules.py`


### Implement


- [ ] `detect_risk_issues(facts)`


### Allowed issue codes


- [ ] `stale_context`
- [ ] `low_confidence_match`
- [ ] `high_reference_count`
- [ ] `cross_file_impact`
- [ ] `cross_module_impact`
- [ ] `public_surface_change`
- [ ] `inheritance_risk`
- [ ] `multi_file_change`
- [ ] `multi_module_change`
- [ ] `reference_data_unavailable`


Do not add `unresolved_target` in this phase.


### Exact trigger rules


#### `stale_context`
- [ ] trigger if `facts.stale_symbols` is not empty


#### `low_confidence_match`
- [ ] trigger if `facts.low_confidence_symbols` is not empty
- [ ] or if `facts.low_confidence_edges` is not empty


#### `high_reference_count`
- [ ] trigger if any target reference count is `>= 10`
- [ ] trigger only for targets whose reference availability is `True`


#### `cross_file_impact`
- [ ] trigger if `facts.cross_file_impact` is `True`


#### `cross_module_impact`
- [ ] trigger if `facts.cross_module_impact` is `True`


#### `public_surface_change`
- [ ] trigger if `facts.touches_public_surface` is `True`


#### `inheritance_risk`
- [ ] trigger if `facts.inheritance_involved` is `True`


#### `multi_file_change`
- [ ] trigger if `facts.target_spans_multiple_files` is `True`


#### `multi_module_change`
- [ ] trigger if `facts.target_spans_multiple_modules` is `True`


#### `reference_data_unavailable`
- [ ] trigger if any target has `reference_availability = False`


### Required behavior


- [ ] return issue codes in deterministic order
- [ ] do not return duplicates


### Do not do


- [ ] do not embed score values in issue strings
- [ ] do not emit prose explanations instead of issue codes


### Done when


- [ ] facts cleanly translate into reusable issue codes


***


## Step 11 - Risk Scoring


### File


- [ ] `src/repo_context/graph/risk_scoring.py`


### Implement


- [ ] `score_risk(issues, facts)`


### Exact weights


- [ ] `stale_context` = `+20`
- [ ] `low_confidence_match` = `+20`
- [ ] `high_reference_count` = `+20`
- [ ] `cross_file_impact` = `+10`
- [ ] `cross_module_impact` = `+15`
- [ ] `public_surface_change` = `+15`
- [ ] `inheritance_risk` = `+10`
- [ ] `multi_file_change` = `+10`
- [ ] `multi_module_change` = `+15`
- [ ] `reference_data_unavailable` = `+15`


### Exact behavior


- [ ] sum weights of triggered issues
- [ ] clamp final score to the integer range `0..100`


### Local-scope mitigation rule


- [ ] if `touches_local_scope_only` is `True` and `public_surface_change` is not triggered, you may subtract a small fixed local-only mitigation such as `-10`
- [ ] if this mitigation is used, clamp after subtraction
- [ ] if this mitigation is not used in v1, leave it out explicitly and do not imply it exists


### Do not do


- [ ] do not use floating score output in v1
- [ ] do not invent nonlinear formulas in this phase


### Done when


- [ ] score computation is simple, explicit, deterministic, and easy to tune


***


## Step 12 - Risk Decision


### File


- [ ] `src/repo_context/graph/risk_scoring.py`


### Implement


- [ ] `decide_risk(issues, facts, score)`


### Allowed decisions


- [ ] `safe_enough`
- [ ] `review_required`
- [ ] `high_risk`


### Base threshold rules


- [ ] `0..29` -> `safe_enough`
- [ ] `30..69` -> `review_required`
- [ ] `70..100` -> `high_risk`


### Override rules


- [ ] if `stale_context` exists, final decision must be at least `review_required`
- [ ] if `low_confidence_match` exists and at least one other non-trivial issue exists, final decision must be at least `review_required`
- [ ] if `reference_data_unavailable` exists and any of `public_surface_change`, `cross_module_impact`, or `inheritance_risk` also exists, final decision must be at least `review_required`


### Do not do


- [ ] do not add workflow-policy decisions like `blocked`
- [ ] do not let the decision contradict the clamped score and override rules


### Done when


- [ ] the engine returns one coarse deterministic severity decision


***


## Step 13 - Assemble Final Result


### File


- [ ] `src/repo_context/graph/risk_engine.py`


### Implement


Ensure the final result contains:


- [ ] normalized `targets`
- [ ] built `facts`
- [ ] detected `issues`
- [ ] computed `risk_score`
- [ ] computed `decision`


### Required behavior


- [ ] result ordering must be deterministic
- [ ] target order must match normalized deterministic input order
- [ ] issues order must match the engine’s deterministic rule order


### Do not do


- [ ] do not drop facts from the final result
- [ ] do not return only summarized text


### Done when


- [ ] one engine call returns a complete reusable machine-friendly `RiskResult`


***


## Step 14 - CLI Commands


### Files to modify


- [ ] existing CLI module from earlier phases


### Implement


Add these commands.


### Command 1
- [ ] `repo-context analyze-symbol-risk <symbol-id>`


### Required behavior
- [ ] analyze one symbol
- [ ] print targets, facts, issues, risk score, and decision


### Command 2
- [ ] `repo-context analyze-target-set-risk <symbol-id-1> <symbol-id-2> ...`


### Required behavior
- [ ] analyze multiple symbols
- [ ] print aggregate result


### Output rules


- [ ] JSON output is acceptable
- [ ] deterministic readable structured text is acceptable
- [ ] output must include all core engine fields
- [ ] output must show explicit reference availability state


### Do not do


- [ ] do not mix user-prose plan parsing into these commands
- [ ] do not hide unavailable reference state from the printed facts


### Done when


- [ ] the risk engine can be inspected from CLI without any later plan wrapper


***


## Step 15 - Tests


### Files to create or modify


- [ ] phase 7 tests under `tests/`


### Implement these tests


- [ ] `test_analyze_low_risk_private_helper`
- [ ] `test_analyze_local_function_stays_local_scope`
- [ ] `test_analyze_public_heavily_referenced_method`
- [ ] `test_analyze_inheritance_risk`
- [ ] `test_analyze_multi_file_target_set`
- [ ] `test_analyze_multi_module_target_set`
- [ ] `test_stale_symbol_triggers_issue`
- [ ] `test_low_confidence_symbol_triggers_issue`
- [ ] `test_reference_data_unavailable_triggers_issue`
- [ ] `test_score_clamps_to_100`
- [ ] `test_high_score_returns_high_risk`


### Exact test assertions


#### `test_analyze_low_risk_private_helper`
- [ ] private-like helper with local use yields few or no issues
- [ ] score is low
- [ ] decision is `safe_enough`


#### `test_analyze_local_function_stays_local_scope`
- [ ] local function is accepted as a valid target
- [ ] it does not trigger `public_surface_change` only because its name lacks leading underscore
- [ ] local-scope facts are correct


#### `test_analyze_public_heavily_referenced_method`
- [ ] issues include `high_reference_count`
- [ ] issues include `cross_file_impact`
- [ ] issues include `cross_module_impact`
- [ ] issues include `public_surface_change`


#### `test_analyze_inheritance_risk`
- [ ] inherited class or method context triggers `inheritance_risk`


#### `test_analyze_multi_file_target_set`
- [ ] target set spanning multiple files triggers `multi_file_change`


#### `test_analyze_multi_module_target_set`
- [ ] target set spanning multiple modules triggers `multi_module_change`


#### `test_stale_symbol_triggers_issue`
- [ ] stale targets produce `stale_context`


#### `test_low_confidence_symbol_triggers_issue`
- [ ] low-confidence symbols or edges produce `low_confidence_match`


#### `test_reference_data_unavailable_triggers_issue`
- [ ] unavailable reference refresh state produces `reference_data_unavailable`
- [ ] the engine does not treat this as fresh zero references


#### `test_score_clamps_to_100`
- [ ] score never exceeds `100`


#### `test_high_score_returns_high_risk`
- [ ] high enough score returns `high_risk`


### Do not do


- [ ] do not rely only on smoke tests
- [ ] do not leave issue ordering nondeterministic


### Done when


- [ ] fact extraction, issue detection, scoring, and decisions are covered by deterministic tests


***


## Step 16 - Fixture Validation


### Files to use


- [ ] reuse existing phase 3 through phase 6 fixtures
- [ ] add small focused risk fixtures only if necessary


### Minimum useful fixture cases


- [ ] one local private helper
- [ ] one local function nested inside another function
- [ ] one public heavily referenced symbol
- [ ] one inheritance case
- [ ] one multi-file target set
- [ ] one multi-module target set


### Implement


For at least one fixture path:


- [ ] build the graph through earlier phases
- [ ] enrich references where needed
- [ ] run the risk engine
- [ ] assert exact facts, issues, score, and decision


### Do not do


- [ ] do not require MCP or plan wrappers
- [ ] do not depend on LLM output for assertions


### Done when


- [ ] phases 2 through 7 work together on deterministic risk analysis


***


## Step 17 - Final Verification


Before marking phase 7 complete, verify all of the following:


- [ ] the engine can analyze one symbol
- [ ] the engine can analyze multiple symbols
- [ ] `RiskTarget` normalization exists
- [ ] `RiskFacts` extraction exists
- [ ] issue detection exists
- [ ] score computation exists
- [ ] decision computation exists
- [ ] public-surface heuristics work
- [ ] local-scope heuristics work
- [ ] reference spread facts work
- [ ] inheritance risk works
- [ ] freshness issues work
- [ ] confidence issues work
- [ ] unavailable reference data remains distinct from fresh zero
- [ ] CLI commands work
- [ ] tests pass
- [ ] no MCP server exists yet
- [ ] no plan wrapper exists yet unless it is only a thin adapter


Do not mark phase 7 done until every box above is true.


***


## Required Execution Order


Implement in this order and do not skip ahead:


- [ ] Step 1 define risk types
- [ ] Step 2 risk engine entry points
- [ ] Step 3 target normalization
- [ ] Step 4 public surface heuristic
- [ ] Step 5 reference fact helpers
- [ ] Step 6 inheritance risk helper
- [ ] Step 7 freshness fact helpers
- [ ] Step 8 confidence fact helpers
- [ ] Step 9 build risk facts
- [ ] Step 10 issue code detection
- [ ] Step 11 risk scoring
- [ ] Step 12 risk decision
- [ ] Step 13 assemble final result
- [ ] Step 14 CLI commands
- [ ] Step 15 tests
- [ ] Step 16 fixture validation
- [ ] Step 17 final verification


***


## Phase 7 Done Definition


Phase 7 is complete only when all of these are true:


- [ ] phase 1 through phase 6 contracts remain intact
- [ ] the risk engine is reusable outside any single workflow
- [ ] facts are separated from issues
- [ ] issues are separated from score
- [ ] score is separated from decision
- [ ] local and nested symbols are valid first-class risk targets
- [ ] unavailable reference data is not misrepresented as fresh zero
- [ ] CLI inspection works
- [ ] tests pass
- [ ] no out-of-scope workflow wrapper was baked into the engine
