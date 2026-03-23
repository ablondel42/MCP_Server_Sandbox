```md
# 07-risk-engine.md

## Purpose

This phase builds the risk engine.

The risk engine is the deterministic analysis layer that turns graph facts into structured risk signals. It is not tied only to one input shape like a specific plan request. Instead, it provides the reusable risk logic that later tools, workflows, and MCP endpoints will call.

In plain English:

- the graph tells you what exists
- LSP enrichment tells you where symbols are referenced
- the risk engine turns that data into risk facts, issue codes, scores, and decisions

The plan evaluator that comes later should use this engine.
The engine is the core logic.
The evaluator is just one consumer of that logic.

---

## Why this phase matters

Without a dedicated risk engine, risk logic gets scattered everywhere:

- some rules end up in CLI code
- some rules end up in MCP tools
- some rules end up in the agent prompt
- some rules end up duplicated in context builders

That is a bad design.

The risk engine should be the single reusable place that answers questions like:

- is this symbol risky to change
- why is it risky
- how broad is the blast radius
- is the graph too stale or uncertain to trust
- what deterministic issues should be raised

This phase is where the project stops being just a code graph and starts becoming a safety layer.

---

## Phase goals

By the end of this phase, you should have:

- a reusable risk engine module
- reusable fact extraction functions
- reusable issue detection functions
- reusable scoring functions
- reusable decision functions
- support for symbol-level risk analysis
- support for target-set risk analysis
- support for later plan-level composition
- structured machine-friendly risk outputs
- CLI commands for symbol and target risk inspection
- tests for risk facts, rules, scoring, and decisions

---

## Phase non-goals

Do **not** do any of this in phase 7:

- full MCP server implementation
- final plan-evaluation tool contract
- autonomous plan rewriting
- freeform natural-language narratives
- diff-aware code mutation analysis
- runtime validation
- test execution
- file watching

This phase is the reusable core risk layer, not the final workflow wrapper.

---

## What already exists from previous phases

This phase assumes you already have:

- repository and file inventory
- AST-based structural graph
- graph storage and graph queries
- symbol context assembly
- LSP-based `references` enrichment

The risk engine consumes those layers.
It does not replace them.

---

## Core idea

The risk engine should accept one or more target symbols and produce:

- deterministic facts
- issue codes
- a risk score
- a decision

That means the risk engine should be usable for:

- one symbol
- multiple symbols
- later plan assessment
- later pre-edit review
- later MCP calls

This is why the phase should be called `risk-engine`, not only `plan-risk evaluator`.

---

## Risk engine responsibilities

The risk engine should answer:

- how many references does this symbol have
- how many files reference it
- how many modules reference it
- does it look public
- does it participate in inheritance
- is the graph stale
- is the graph low-confidence
- does the target set span multiple files or modules
- what issues should be raised
- what score should be assigned
- what decision should be returned

That is enough for version 1.

---

## Recommended package structure additions

Add these files:

```text
src/
  repo_context/
    graph/
      risk_engine.py
      risk_facts.py
      risk_rules.py
      risk_scoring.py
      risk_targets.py
      risk_types.py
```

### Why this split

- `risk_engine.py`: orchestration entry points
- `risk_facts.py`: raw deterministic fact extraction
- `risk_rules.py`: issue detection
- `risk_scoring.py`: weights and decision thresholds
- `risk_targets.py`: target normalization and grouping
- `risk_types.py`: reusable result contracts

This keeps the logic reusable and prevents one giant file.

---

## Core data contracts

The risk engine should define its own reusable types.
Do not force everything into `PlanAssessment` yet.

Recommended types:

- `RiskTarget`
- `RiskFacts`
- `RiskResult`

The later plan evaluator can compose these into a `PlanAssessment`.

---

## Type: RiskTarget

Represents one analysis target.

### Suggested shape

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class RiskTarget:
    symbol_id: str
    qualified_name: str
    kind: str
    file_id: str
    file_path: str
    module_path: str
    visibility_hint: Optional[str] = None
```

### Why this exists

The engine should not depend on raw DB rows everywhere.
A small normalized target shape makes analysis cleaner.

---

## Type: RiskFacts

Represents deterministic analysis facts for one or more targets.

### Suggested shape

```python
from dataclasses import dataclass, field
from typing import Any

@dataclass
class RiskFacts:
    target_count: int = 0
    symbol_ids: list[str] = field(default_factory=list)
    symbol_kinds: dict[str, str] = field(default_factory=dict)

    reference_counts: dict[str, int] = field(default_factory=dict)
    referencing_file_counts: dict[str, int] = field(default_factory=dict)
    referencing_module_counts: dict[str, int] = field(default_factory=dict)

    touches_public_surface: bool = False
    target_spans_multiple_files: bool = False
    target_spans_multiple_modules: bool = False
    cross_file_impact: bool = False
    cross_module_impact: bool = False
    inheritance_involved: bool = False

    stale_symbols: list[str] = field(default_factory=list)
    low_confidence_symbols: list[str] = field(default_factory=list)
    low_confidence_edges: list[str] = field(default_factory=list)

    extra: dict[str, Any] = field(default_factory=dict)
```

### Why this shape works

It separates raw facts from:
- issue codes
- score
- decision

That keeps the engine explainable.

---

## Type: RiskResult

Represents the final output of the risk engine.

### Suggested shape

```python
from dataclasses import dataclass, field

@dataclass
class RiskResult:
    targets: list[RiskTarget] = field(default_factory=list)
    facts: RiskFacts = field(default_factory=RiskFacts)
    issues: list[str] = field(default_factory=list)
    risk_score: int = 0
    decision: str = "unknown"
```

### Why this exists

This is the reusable engine-level output.
The plan evaluator later can wrap this result without reimplementing the logic.

---

## Design principles

### Principle 1: Facts first, scoring second

Do not jump straight to a score.
Extract facts first, then derive issues, then derive score.

### Principle 2: The engine should be reusable

The engine should not care whether the caller is:
- a CLI command
- a plan evaluator
- a future MCP tool

### Principle 3: Deterministic only

The engine should use:
- graph facts
- thresholds
- small heuristics

It should not rely on freeform LLM interpretation.

### Principle 4: Missing or weak context should increase caution

The engine should never pretend stale or low-confidence data is fine.

---

## Analysis entry points

You should support at least these two entry points.

### Entry point 1: analyze one symbol

```python
def analyze_symbol_risk(conn, symbol_id: str) -> RiskResult:
    ...
```

### Entry point 2: analyze a target set

```python
def analyze_target_set_risk(conn, symbol_ids: list[str]) -> RiskResult:
    ...
```

### Why these are enough for now

- one symbol risk is useful for manual inspection
- target set risk is what later plan evaluation will build on

Do not build the plan wrapper into the engine itself yet.

---

## Target normalization

Create `risk_targets.py`.

Recommended helper:

```python
def load_risk_targets(conn, symbol_ids: list[str]) -> list[RiskTarget]:
    ...
```

### What it should do

For each symbol ID:
- load the node
- derive file path
- derive module path
- normalize it into `RiskTarget`

### Why it matters

The rest of the engine should work on normalized targets, not raw SQL rows.

---

## Fact extraction responsibilities

Create `risk_facts.py`.

Recommended helper:

```python
def build_risk_facts(conn, targets: list[RiskTarget]) -> RiskFacts:
    ...
```

This should compute:

- target count
- symbol kinds
- per-target reference counts
- per-target referencing file counts
- per-target referencing module counts
- whether any target is public-like
- whether target set spans multiple files
- whether target set spans multiple modules
- whether references imply cross-file impact
- whether references imply cross-module impact
- whether inheritance is involved
- whether stale symbols exist
- whether low-confidence symbols or edges exist

That is the engine’s raw material.

---

## Reference fact rules

The engine should use the stored `references` edges from phase 6.

For each target symbol:
- count reference edges where `to_id = target_symbol_id`
- count unique `evidence_file_id`
- count unique referencing modules

### Why this matters

These are your strongest first-order blast-radius signals.

### Suggested helper functions

```python
def get_reference_count(conn, target_id: str) -> int:
    ...

def get_referencing_file_count(conn, target_id: str) -> int:
    ...

def get_referencing_module_count(conn, target_id: str) -> int:
    ...
```

---

## Public-surface heuristic

A target should be considered public-like if:

- `visibility_hint == "public"`
- or its name does not start with `_`
- except magic methods like `__init__`, `__repr__`, `__call__` should not be treated as private-like

### Why this matters

Public-looking symbols are generally riskier to modify because they are more likely to be depended on.

### Suggested helper

```python
def is_public_like(target: RiskTarget) -> bool:
    ...
```

---

## Target spread facts

The engine should compute whether the target set itself spans multiple files or modules.

### `target_spans_multiple_files`

True if:
- the target set touches more than one file

### `target_spans_multiple_modules`

True if:
- the target set touches more than one module

### Why this matters

Even before references, a planned change that touches multiple files or modules is usually riskier than a local isolated one.

---

## Reference spread facts

These are different from target spread.

### `cross_file_impact`

True if:
- any target is referenced from more than one file
- or from a file other than its own

### `cross_module_impact`

True if:
- any target is referenced from more than one module
- or from a different module than its declaration module

### Why this distinction matters

A target may live in one file but still affect many other files.
That is exactly the kind of change-risk signal you care about.

---

## Inheritance facts

The engine should detect inheritance involvement.

### Suggested rules

For a class target:
- if it has outgoing `inherits` edges, set `inheritance_involved = True`

For a method target:
- find parent class
- if parent class has outgoing `inherits` edges, set `inheritance_involved = True`

### Why this matters

Inheritance makes behavior-sharing and override interactions more likely.

---

## Freshness facts

The engine should detect stale context.

Simple v1 rule:
- if target `last_indexed_at` is missing, mark stale
- if reference summary is unavailable for a target that should reasonably have references, mark caution
- if context builder says stale, carry that forward

### Suggested helper

```python
def collect_stale_symbols(conn, targets: list[RiskTarget]) -> list[str]:
    ...
```

Keep it simple.

---

## Confidence facts

The engine should detect low-confidence data.

Examples:
- target symbol confidence below `0.8`
- incoming or outgoing reference edge confidence below `0.8`

### Suggested helpers

```python
def collect_low_confidence_symbols(conn, targets: list[RiskTarget], threshold: float = 0.8) -> list[str]:
    ...

def collect_low_confidence_edges(conn, targets: list[RiskTarget], threshold: float = 0.8) -> list[str]:
    ...
```

### Why this matters

The engine should not act equally confident about exact AST structure and fuzzy LSP-mapped references.

---

## Issue code design

The engine should emit compact issue codes.

Recommended initial issue codes:

- `stale_context`
- `low_confidence_match`
- `high_reference_count`
- `cross_file_impact`
- `cross_module_impact`
- `public_surface_change`
- `inheritance_risk`
- `multi_file_change`
- `multi_module_change`

### Important note

Do **not** include `unresolved_target` here.
That belongs more naturally to the later plan evaluator or target-resolution wrapper.
The engine works on resolved targets.

This is another reason the phase should be `risk-engine`, not `plan-risk evaluator`.

---

## Rule detection

Create `risk_rules.py`.

Recommended helper:

```python
def detect_risk_issues(facts: RiskFacts) -> list[str]:
    ...
```

### Suggested rules

#### `stale_context`
Trigger if:
- `stale_symbols` is not empty

#### `low_confidence_match`
Trigger if:
- `low_confidence_symbols` is not empty
- or `low_confidence_edges` is not empty

#### `high_reference_count`
Trigger if:
- any target has reference count above threshold

Suggested threshold:
- `>= 10`

#### `cross_file_impact`
Trigger if:
- `cross_file_impact` is true

#### `cross_module_impact`
Trigger if:
- `cross_module_impact` is true

#### `public_surface_change`
Trigger if:
- `touches_public_surface` is true

#### `inheritance_risk`
Trigger if:
- `inheritance_involved` is true

#### `multi_file_change`
Trigger if:
- `target_spans_multiple_files` is true

#### `multi_module_change`
Trigger if:
- `target_spans_multiple_modules` is true

That is enough for v1.

---

## Scoring design

Create `risk_scoring.py`.

Recommended helpers:

```python
def score_risk(issues: list[str], facts: RiskFacts) -> int:
    ...

def decide_risk(issues: list[str], facts: RiskFacts, score: int) -> str:
    ...
```

### Suggested starting weights

- `stale_context`: +20
- `low_confidence_match`: +20
- `high_reference_count`: +20
- `cross_file_impact`: +10
- `cross_module_impact`: +15
- `public_surface_change`: +15
- `inheritance_risk`: +10
- `multi_file_change`: +10
- `multi_module_change`: +15

Clamp to `0..100`.

### Why simple weights are good enough

They are:
- predictable
- easy to explain
- easy to tune later

Do not waste time inventing a fake scientific risk model.

---

## Decision design

The engine should produce a coarse decision.

Recommended decisions:

- `safe_enough`
- `review_required`
- `high_risk`

### Suggested rules

- `0-29` -> `safe_enough`
- `30-69` -> `review_required`
- `70-100` -> `high_risk`

### Override rules

If:
- `stale_context` exists
- or `low_confidence_match` exists with other strong issues

Then bias upward toward at least `review_required`.

### Why this works

The engine should communicate severity, not final workflow policy.
Later the plan evaluator or MCP tool can add stricter gating.

---

## Example `risk_facts.py` sketch

```python
def build_risk_facts(conn, targets: list[RiskTarget]) -> RiskFacts:
    facts = RiskFacts()
    facts.target_count = len(targets)
    facts.symbol_ids = [t.symbol_id for t in targets]
    facts.symbol_kinds = {t.symbol_id: t.kind for t in targets}

    file_ids = set()
    module_paths = set()

    for target in targets:
        file_ids.add(target.file_id)
        module_paths.add(target.module_path)

        ref_count = get_reference_count(conn, target.symbol_id)
        ref_file_count = get_referencing_file_count(conn, target.symbol_id)
        ref_module_count = get_referencing_module_count(conn, target.symbol_id)

        facts.reference_counts[target.symbol_id] = ref_count
        facts.referencing_file_counts[target.symbol_id] = ref_file_count
        facts.referencing_module_counts[target.symbol_id] = ref_module_count

        if is_public_like(target):
            facts.touches_public_surface = True

        if ref_file_count >= 2:
            facts.cross_file_impact = True

        if ref_module_count >= 2:
            facts.cross_module_impact = True

        if target_has_inheritance_risk(conn, target):
            facts.inheritance_involved = True

    facts.target_spans_multiple_files = len(file_ids) >= 2
    facts.target_spans_multiple_modules = len(module_paths) >= 2
    facts.stale_symbols = collect_stale_symbols(conn, targets)
    facts.low_confidence_symbols = collect_low_confidence_symbols(conn, targets)
    facts.low_confidence_edges = collect_low_confidence_edges(conn, targets)

    return facts
```

This is clean, deterministic, and reusable.

---

## Example `risk_engine.py` sketch

```python
from repo_context.graph.risk_targets import load_risk_targets
from repo_context.graph.risk_facts import build_risk_facts
from repo_context.graph.risk_rules import detect_risk_issues
from repo_context.graph.risk_scoring import score_risk, decide_risk

def analyze_target_set_risk(conn, symbol_ids: list[str]) -> dict:
    targets = load_risk_targets(conn, symbol_ids)
    facts = build_risk_facts(conn, targets)
    issues = detect_risk_issues(facts)
    score = score_risk(issues, facts)
    decision = decide_risk(issues, facts, score)

    return {
        "targets": [target.__dict__ for target in targets],
        "facts": facts.__dict__,
        "issues": issues,
        "risk_score": score,
        "decision": decision,
    }

def analyze_symbol_risk(conn, symbol_id: str) -> dict:
    return analyze_target_set_risk(conn, [symbol_id])
```

This is exactly the kind of core engine you want.

---

## CLI additions for this phase

Add commands like:

### `analyze-symbol-risk`

```text
repo-context analyze-symbol-risk <symbol-id>
```

What it does:
- runs the risk engine on one symbol
- prints facts, issues, score, decision

### `analyze-target-set-risk`

```text
repo-context analyze-target-set-risk <symbol-id-1> <symbol-id-2> ...
```

What it does:
- runs the risk engine on multiple symbols
- prints aggregate result

### Why this matters

This lets you validate the engine before wrapping it in a plan evaluator or MCP tool.

---

## Example output

```json
{
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
  "facts": {
    "target_count": 1,
    "symbol_ids": [
      "sym:repo:project:method:app.services.auth.AuthService.login"
    ],
    "symbol_kinds": {
      "sym:repo:project:method:app.services.auth.AuthService.login": "method"
    },
    "reference_counts": {
      "sym:repo:project:method:app.services.auth.AuthService.login": 14
    },
    "referencing_file_counts": {
      "sym:repo:project:method:app.services.auth.AuthService.login": 6
    },
    "referencing_module_counts": {
      "sym:repo:project:method:app.services.auth.AuthService.login": 4
    },
    "touches_public_surface": true,
    "target_spans_multiple_files": false,
    "target_spans_multiple_modules": false,
    "cross_file_impact": true,
    "cross_module_impact": true,
    "inheritance_involved": false,
    "stale_symbols": [],
    "low_confidence_symbols": [],
    "low_confidence_edges": [],
    "extra": {}
  },
  "issues": [
    "high_reference_count",
    "cross_file_impact",
    "cross_module_impact",
    "public_surface_change"
  ],
  "risk_score": 60,
  "decision": "review_required"
}
```

That is a strong v1 engine output.

---

## Testing plan

This phase needs risk-centric tests.

### `test_analyze_low_risk_private_helper`

Fixture:
- `_helper()` used only locally

Expected:
- few or no issues
- low score
- `safe_enough`

### `test_analyze_public_heavily_referenced_method`

Fixture:
- public method referenced across multiple files

Expected:
- `high_reference_count`
- `cross_file_impact`
- `cross_module_impact`
- `public_surface_change`

### `test_analyze_inheritance_risk`

Fixture:
- inherited class or subclassed base method

Expected:
- `inheritance_risk`

### `test_analyze_multi_file_target_set`

Fixture:
- target set spans multiple files

Expected:
- `multi_file_change`

### `test_analyze_multi_module_target_set`

Fixture:
- target set spans multiple modules

Expected:
- `multi_module_change`

### `test_stale_symbol_triggers_issue`

Expected:
- `stale_context`

### `test_low_confidence_symbol_triggers_issue`

Expected:
- `low_confidence_match`

### `test_score_clamps_to_100`

Expected:
- score never exceeds 100

### `test_high_score_returns_high_risk`

Expected:
- decision becomes `high_risk`

---

## Suggested fixtures

Use small realistic cases.

### Fixture 1: local private helper

One `_normalize_value()` function used in one file.

### Fixture 2: public service method

One public method referenced from several files.

### Fixture 3: base class and subclass

A base service with subclasses.

### Fixture 4: two-target refactor

Two target symbols in different modules.

These are enough to validate the engine.

---

## Acceptance checklist

Phase 7 is done when all of this is true:

- The engine can analyze one symbol.
- The engine can analyze multiple symbols.
- `RiskTarget` normalization exists.
- `RiskFacts` extraction exists.
- Issue detection exists.
- Score computation exists.
- Decision computation exists.
- Public-surface heuristics work.
- Reference spread facts work.
- Inheritance risk works.
- Freshness and confidence issues work.
- CLI commands work.
- Tests pass.
- No MCP server exists yet.
- No plan wrapper exists yet unless only as a thin adapter.

---

## Common mistakes to avoid

### Mistake 1: Putting plan resolution inside the engine

The engine should work on resolved targets.
Plan resolution belongs in a thin wrapper later.

### Mistake 2: Making the engine return prose instead of structure

This is the exact place where structure wins.

### Mistake 3: Treating unavailable reference data as zero

Unavailable is not zero.
Be honest.

### Mistake 4: Scattering risk rules across the app

All core risk rules should live here.

### Mistake 5: Overfitting thresholds too early

Pick practical defaults and tune them later.
Do not obsess on the first pass.

### Mistake 6: Confusing engine output with workflow policy

The engine says:
- facts
- issues
- score
- decision

A later workflow can decide:
- ask for approval
- block edits
- revise plan
- proceed

That separation is important.

---

## What phase 8 will depend on

The next phase should use this engine to build a higher-level wrapper, likely through MCP.

That next layer can:
- resolve plan targets
- call the risk engine
- return a final plan-oriented assessment

That is why phase 7 should stay reusable and not collapse into one specific workflow shape.

---

## Final guidance

You were right to correct the naming.

`risk-engine` is the better phase name because this layer is broader than one plan-evaluation tool. It is the reusable deterministic core that later powers plan checks, pre-edit review, and possibly other guarded workflows.

Build it as a clean core service:

- facts first
- issues second
- score third
- decision last

That keeps the architecture sane.
```