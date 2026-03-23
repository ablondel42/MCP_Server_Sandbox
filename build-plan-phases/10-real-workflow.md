```md
# 10-real-workflow.md

## Purpose

This phase defines the real workflow the system is meant to support.

Up to this point, you built the technical layers:

- scanning
- AST extraction
- graph storage
- context assembly
- LSP reference enrichment
- risk engine
- MCP server
- watch mode

Those layers are necessary, but they are still just infrastructure.

This phase is about the actual end-to-end user workflow:

1. the user asks the agent to plan a change
2. the agent drafts a plan
3. the agent uses MCP tools to inspect context and risk
4. the agent revises the plan based on deterministic findings
5. the agent presents the revised plan
6. the human approves or rejects
7. only then implementation can begin

That is the real product behavior.

---

## Why this phase matters

Without an explicit workflow phase, all the earlier work stays as disconnected capabilities.

That creates obvious problems:

- the agent may skip risk checks
- the approval gate may become optional in practice
- tool use may be inconsistent
- the system may drift back into “just code first and hope”
- the project loses its real value proposition

The real value is not “we have a graph”.
The real value is:

- safer AI-assisted planning
- deterministic pre-change checking
- human approval before code changes
- a cleaner loop between plan, context, risk, and execution

So this phase defines the operational contract.

---

## Phase goals

By the end of this phase, you should have:

- a documented end-to-end change workflow
- a clear separation between planning and implementation
- required MCP tool usage before implementation
- plan revision rules based on deterministic findings
- explicit human approval gating
- blocked execution when context is missing or risk is too high
- a repeatable workflow the agent can follow every time
- tests or scenario fixtures for workflow behavior
- prompts or agent instructions aligned with the real workflow

---

## Phase non-goals

Do **not** do any of this in phase 10:

- let the agent silently implement before approval
- let the server pretend to be the workflow brain
- blur planning and coding into one step
- make approval optional
- rely on vibes instead of deterministic tool use

This phase is about enforcing the intended workflow, not loosening it.

---

## What already exists from previous phases

This phase assumes you already have:

- repository graphing
- symbol context retrieval
- reference enrichment
- risk analysis
- MCP tool exposure
- optional watch mode for freshness

Now you define how they are used together in a real coding session.

---

## Core workflow principle

Planning and implementation must be separate phases.

That means:

### Planning phase

The agent may:
- inspect repository context
- resolve symbols
- gather references
- analyze risk
- draft or revise a plan

The agent may **not**:
- edit files
- apply patches
- generate final implementation changes as if approved

### Implementation phase

The agent may:
- implement only after human approval
- follow the approved plan
- use MCP again if needed for clarification or re-checks

This separation is one of the whole points of the system.

---

## Workflow actors

There are three actors in the real workflow.

### Actor 1: Human

Responsibilities:
- states the goal
- clarifies intent
- approves or rejects the plan
- decides whether to proceed

### Actor 2: Agent

Responsibilities:
- draft a plan
- inspect repository context through MCP tools
- revise the plan based on actual graph facts
- present the plan clearly
- wait for approval before implementation

### Actor 3: MCP server

Responsibilities:
- expose deterministic tools
- return graph facts
- return reference facts
- return risk facts
- return structured results
- never replace the agent’s explanation role

This division must stay clean.

---

## The real workflow

The real workflow should be defined as a strict sequence.

### Step 1: User states a requested change

Example:

- “Split AuthService.login into validation and token creation helpers”
- “Rename execute_job to run_job across the service layer”
- “Refactor BillingService to remove inheritance from BaseService”

At this point, no implementation should begin.

---

## Step 2: Agent drafts an initial plan

The agent should create an initial high-level plan based on the request.

Example shape:

- identify the target symbols
- describe intended edits
- describe expected files or modules involved
- note any obvious uncertainty

This plan is still provisional.

It is not approved.
It is not final.
It must be checked.

---

## Step 3: Agent resolves target symbols through MCP

Before trusting the plan, the agent should resolve the actual symbols involved.

Typical tool usage:

- `resolve_symbol`
- possibly more than once if the user named several targets

### Why this matters

Users often describe intent loosely.
The agent should not assume it picked the right symbol without checking.

If symbol resolution fails or is ambiguous:
- the plan must stay provisional
- implementation must not start

---

## Step 4: Agent gathers symbol context

For each resolved target, the agent should fetch context.

Typical tool usage:

- `get_symbol_context`

The goal is to understand:

- what the symbol is
- where it lives
- its parent and children
- structural relationships
- freshness and confidence signals
- whether reference data is already available

### Why this matters

You do not want the agent planning changes blind.

---

## Step 5: Agent refreshes references if needed

If reference data is unavailable or stale, the agent should refresh it.

Typical tool usage:

- `refresh_symbol_references`

Then, if useful:
- `get_symbol_references`

### Why this matters

Blast radius without references is weak.
For non-trivial changes, reference freshness should usually be checked before approval.

### Good practical rule

The agent should refresh references when:
- the target is public-like
- the symbol has stale context
- the change may affect callers
- the symbol is a callable or class likely used elsewhere

---

## Step 6: Agent runs risk analysis

The agent should then run deterministic risk analysis.

Typical tool usage:

- `analyze_symbol_risk`
- or `analyze_target_set_risk`

The result gives:
- facts
- issue codes
- score
- decision

### Important rule

The agent may explain the result, but the MCP tool output is the source of truth for risk facts.

---

## Step 7: Agent revises the plan

The plan should now be revised based on tool findings.

Examples:

### If references are broad

The agent should revise the plan to include:
- impacted files
- likely caller updates
- explicit caution about public usage

### If inheritance is involved

The agent should revise the plan to include:
- subclass impact checks
- override behavior review
- broader testing scope

### If context is stale or low-confidence

The agent should revise the plan to say:
- graph state is incomplete or uncertain
- approval should be cautious
- implementation should be blocked or limited until refreshed

This step matters a lot.
The agent should not just dump tool results.
It should turn them into a better plan.

---

## Step 8: Agent presents the revised plan for approval

At this point, the agent should present:

- the requested goal
- the resolved targets
- the revised implementation plan
- the key risk findings
- the recommendation
- a clear pause for human approval

### Important rule

The agent must not start coding in the same step.

It should stop and wait.

---

## Step 9: Human approves or rejects

Possible outcomes:

### Approved

The workflow can move to implementation.

### Rejected

The workflow returns to planning and revision.

### Needs clarification

The workflow stays in planning.
The agent may ask for clarification and re-run tools if needed.

---

## Step 10: Implementation begins only after approval

Only now can the agent:

- edit files
- generate patches
- apply changes
- continue with coding work

Even during implementation, the agent may still use MCP tools again if needed.
But approval is the gate that unlocks coding.

---

## Required tool usage policy

The workflow should define minimum tool usage rules.

### For any symbol-targeted change

Required:
- `resolve_symbol`
- `get_symbol_context`

### For non-trivial callable or class changes

Usually required:
- `refresh_symbol_references` if reference data is stale or unavailable
- `analyze_symbol_risk` or `analyze_target_set_risk`

### For multi-target changes

Required:
- `analyze_target_set_risk`

### For ambiguous user requests

Required:
- additional symbol resolution
- possibly user clarification before approval

Do not let the agent skip these steps casually.

---

## Blocking conditions

The workflow should explicitly define blocking conditions.

Implementation must not begin if any of these are true:

- target symbols are unresolved
- symbol resolution is ambiguous
- graph context is missing in a way that makes the plan unreliable
- risk output indicates missing context severe enough to block
- the human has not approved yet

### Optional stronger rule

You may also block implementation when:
- risk decision is high-risk
- until the user explicitly approves despite warnings

That is often a good default.

---

## Recommended workflow states

It helps to define simple states.

Suggested states:

- `request_received`
- `draft_plan_ready`
- `targets_resolved`
- `context_checked`
- `risk_checked`
- `awaiting_approval`
- `approved`
- `rejected`
- `implementation_in_progress`
- `implementation_blocked`

### Why this matters

Even if you do not build a UI yet, thinking in states helps keep the workflow honest.

---

## Suggested workflow data shape

You may want an internal workflow object later.

Example:

```python
{
  "request": "Split AuthService.login into validation and token creation helpers",
  "draft_plan": [...],
  "resolved_symbol_ids": [
    "sym:repo:project:method:app.services.auth.AuthService.login"
  ],
  "context_checked": true,
  "references_checked": true,
  "risk_checked": true,
  "risk_result": {
    "issues": [
      "high_reference_count",
      "cross_file_impact",
      "public_surface_change"
    ],
    "risk_score": 45,
    "decision": "review_required"
  },
  "approval_state": "awaiting_approval"
}
```

This is not required immediately, but it is a useful mental model.

---

## Agent behavior rules

This phase should document hard agent rules.

### Rule 1: Never implement before approval

No exceptions.

### Rule 2: Never skip symbol resolution when the change is symbol-targeted

If the request names a method, class, or function, resolve it first.

### Rule 3: Never present raw risk scores without interpretation

The agent should convert deterministic outputs into a clearer explanation, while keeping the score and issues visible.

### Rule 4: Never hide uncertainty

If context is stale, low-confidence, or unresolved, say that clearly.

### Rule 5: Revise the plan before approval, not after coding starts

The point is to catch problems before edits happen.

---

## Example real workflow scenario

### User request

“Rename execute_job to run_job across the service layer.”

### Agent draft plan

- rename the target function
- update imports and call sites
- verify service-layer references

### MCP usage

1. `resolve_symbol` for `app.services.execute_job`
2. `get_symbol_context`
3. `refresh_symbol_references`
4. `analyze_symbol_risk`

### Findings

- public-like function
- referenced in 6 files
- referenced across 4 modules
- risk decision = `review_required`

### Revised plan

- rename function declaration
- update all known call sites across 6 files
- update imports across 4 modules
- keep compatibility concerns in mind if external callers may exist
- recommend approval only if full call-site update is intended

### Approval gate

The agent stops and asks for approval.

Only after approval does implementation begin.

This is the exact behavior the system is supposed to enable.

---

## MCP role in the workflow

The MCP server should not own the workflow state machine.

It should only provide tools.

The workflow itself should live in:
- the agent instructions
- the client orchestration
- or a thin outer workflow wrapper if you later build one

### Why this matters

If you push the whole workflow into the MCP server, you make the server too opinionated and harder to reuse.

Keep the server narrow.
Keep workflow logic outside.

---

## Optional next layer: thin plan wrapper

Once this phase is defined, you may optionally add a higher-level tool later like:

- `evaluate_plan_workflow`

That tool could:
- resolve targets
- gather context
- refresh references if needed
- run risk analysis
- return a combined workflow packet

But that should be a thin orchestrator over existing tools and engine logic.
Do not collapse the whole architecture into one giant endpoint.

---

## Prompt and agent-instruction alignment

This phase should also update the agent instructions or prompting contract.

The agent should be explicitly told:

- plan first
- use MCP before implementation
- revise the plan using tool outputs
- stop for approval
- only implement after approval

If the prompt does not enforce this, the system will drift.

This part is not code-heavy, but it is critical.

---

## CLI or simulation support

You may optionally add a workflow simulation command like:

```text
repo-context simulate-workflow --request "Rename execute_job to run_job"
```

### What it could do

- resolve target symbols
- fetch context
- refresh references
- run risk analysis
- print a workflow summary
- stop at `awaiting_approval`

This is optional, but useful for testing the intended behavior outside a full agent environment.

---

## Testing plan

This phase needs scenario-based tests more than low-level unit tests.

### `test_symbol_targeted_change_requires_resolution`

Verify:
- workflow blocks if symbol resolution fails

### `test_nontrivial_change_requires_risk_check_before_approval`

Verify:
- approval state is not reached without risk analysis

### `test_workflow_stops_at_awaiting_approval`

Verify:
- after context and risk checks, the workflow does not auto-implement

### `test_unresolved_or_ambiguous_target_blocks_implementation`

Verify:
- implementation state is never entered

### `test_approved_workflow_can_transition_to_implementation`

Verify:
- approval changes state correctly

### `test_high_risk_result_does_not_auto-implement`

Verify:
- high-risk findings still require explicit human approval

### `test_plan_revision_uses_risk_findings`

Verify:
- revised plan changes when issues like `cross_module_impact` appear

---

## Acceptance checklist

Phase 10 is done when all of this is true:

- The planning phase is explicitly separate from implementation.
- MCP tool use is required before implementation for non-trivial changes.
- Symbol resolution is required for symbol-targeted requests.
- Context inspection is part of the standard flow.
- Reference refresh is used when needed.
- Risk analysis is part of the standard flow.
- Plans are revised based on deterministic findings.
- Human approval is a hard gate.
- Implementation never begins before approval.
- Workflow states are clear enough to enforce.
- Agent instructions reflect the workflow.
- Scenario tests or workflow simulations exist.

---

## Common mistakes to avoid

### Mistake 1: Treating approval as a soft suggestion

If approval is optional, the workflow is broken.

### Mistake 2: Letting the agent code while “still planning”

That destroys the whole guardrail model.

### Mistake 3: Using MCP only after a plan is already effectively decided

The whole point is to let MCP improve the plan before approval.

### Mistake 4: Hiding uncertainty from the human

The user should know when risk findings are based on stale or weak context.

### Mistake 5: Dumping raw tool output without revising the plan

The agent should synthesize findings into a better plan.

### Mistake 6: Moving workflow intelligence into the MCP server

Keep MCP deterministic and narrow.

---

## Final guidance

This phase is where the project stops being “a cool repository-analysis system” and becomes “a real guarded coding workflow”.

That distinction matters.

The real workflow is the product:

- request
- draft plan
- resolve
- inspect
- refresh
- analyze
- revise
- approve
- implement

If the system actually enforces that loop, it becomes valuable.
If it skips that loop, it is just another fancy dev tool.
```