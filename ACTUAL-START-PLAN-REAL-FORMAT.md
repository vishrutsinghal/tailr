# ACTUAL Start Plan - Real Format (Not Idealized)

## What User Will Actually See

When they run:
```bash
tailtrail start "Update task-start.py, execution-evidence.py, closure-finalizer.py to fully leverage registry"
```

The output will be:

```
+--------------------------------------------+
| TAILTRAIL                                  |
| Requirement completion and drift control   |
| for AI-assisted delivery                   |
|                                            |
| PLAN     Navigator | AIDLC | Intent Bridge |
| MAP      Code Graph | Req Map | UI Guard   |
| VERIFY   Req | Arch | Behaviour | Maintain |
| DEBUG    Repro | Causes | Evidence | Fix   |
| CONTROL  Workflow | Recovery | Closure     |
| IMPROVE  Tokens | Learn | Eval | MCP       |
+--------------------------------------------+

# TailTrail Scope Confirmation Required

**Plan detail:** `Expert` (automatic for AIDLC Lite)

**Goal:** Update task-start.py, execution-evidence.py, closure-finalizer.py to fully leverage registry

## Scope-quality gate

- Status: **blocked**.
- Evidence state: `blocked-by-limits`.
- Request mode: `code-change`.
- Requirement-to-scope precedence: `eligible` (requirements-sufficient).
- Navigator graph management: `refresh`; cache `fresh`.
- Actionable reason: The bounded investigation exhausted an applicable read budget before proving an implementation owner.
- Navigator updated TailTrail graph metadata, but no Planning Lock, workflow, target receipt, learning receipt, or implementation authority was created.

## Why TailTrail stopped

- The bounded investigation exhausted an applicable read budget before proving an implementation owner.
- Graph evidence: `stale` persistent cache; bounded source relationships were checked independently.
- Active-host reasoning: `unavailable` (host-reasoning-has-no-supported-owner-alternatives).
- Candidate paths remain advisory evidence; none grants implementation authority.

## Requirements

**Interpretation evidence:** deterministic normalization; exact-goal-bound.

- **REQ-01:** Update task-start.py, execution-evidence.py, closure-finalizer.py to fully leverage registry

## One bounded scope question

**SCOPE-Q1:** What concrete module, symbol, caller, or reproduction entry point owns this behavior?

- Response format: Provide one known module, symbol, caller, or reproduction clue; do not choose from unsupported repository candidates.
- TailTrail found no query- or relationship-grounded, high-confidence owner option. This clarification grants no implementation authority or Planning Lock.

## To unblock

To unblock, build the missing evidence first, then re-run `tailtrail start` with the same goal.
- `tailtrail bootstrap --root .` builds the code graph this decision looked for.
- Or name one caller or test exercising the behavior, then re-run `tailtrail start`.
- Or answer with one listed owner path, ranked strongest evidence first:
  ```
  tailtrail start "<goal>" --scope-owner <path> --host <codex|copilot|claude>
  ```
  (--host selects whose requirement contract checks the answer).
  
  Suggested paths:
  - `tests/test_debug_harness.py`
  - `tests/test_workflow_freshness_recovery.py`
  - `tests/test_workflow_real_runs.py`

- Or answer `SCOPE-Q1` above with one known module, symbol, caller, or path.
- Answering changes nothing by itself: no Planning Lock, workflow, or approval is created until a re-run proves an owner.
```

---

## What This Means

**User sees this because:**
1. TailTrail's scope detection needs to know WHO owns the code being changed
2. It asked for one scope owner path (like `scripts/task-start.py`)
3. Without this, it won't create a Planning Lock

**User needs to do:**
```bash
tailtrail start "Update task-start.py, execution-evidence.py, closure-finalizer.py to fully leverage registry" \
  --scope-owner scripts/task-start.py \
  --host copilot
```

---

## After Providing Scope Owner

When you run with `--scope-owner`, TailTrail needs **host interpretation**:

```
# TailTrail Host Requirement Interpretation Required

**Plan detail:** `Expert` (automatic for AIDLC Lite)

**Goal:** Update task-start.py, execution-evidence.py, closure-finalizer.py to fully leverage registry

## State

- Active host: `copilot`.
- Status: `awaiting-host-interpretation`.
- Planning Lock: not created.

## Required host action

- Classify only the exact current goal into context, outcome, constraint, evidence, scope, or question clauses.
- Read every inspected requirement artifact listed below and bind each artifact-derived clause with its input ID and exact SHA-256.
- Create requirement rows only from outcome, constraint, or scope clauses.
- Return at most three material questions when implementation-affecting decisions remain.
- Keep quoted UI or error text out of semantic intent terms.
- Exclude private reasoning and invent no behavior, path, fact, approval, or authority beyond the supplied verified receipt.
- Validate against `schemas/requirement-interpretation.schema.json` and resubmit through MCP `requirement_interpretation` or CLI `--requirement-interpretation`.

- No deterministic fallback, graph lifecycle, scope decision, Planning Lock, workflow, or implementation authority was created for this agent-host Build request.
```

---

## The Real Lesson

**My idealized sample** showed what a fully-generated plan would look like AFTER all decisions are made.

**The ACTUAL output** shows TailTrail's **workflow** - it asks for clarification step-by-step:

1. **First:** "What is the scope owner?" (needs `--scope-owner`)
2. **Then:** "Interpret the requirement" (needs requirement classification)
3. **Finally:** Creates Planning Lock with focused validation, command registry, etc.

---

## To Get to the Pretty Plan

You'd need to:

```bash
# Step 1: Provide scope owner
tailtrail start "Update task-start.py, execution-evidence.py, closure-finalizer.py to fully leverage registry" \
  --scope-owner scripts/task-start.py \
  --host copilot

# Step 2: TailTrail asks for host interpretation (automatic if using MCP)

# Step 3: Planning Lock created with full plan visible for approval
```

Then you'd see the structured planning output (JSON in state directory, or formatted display).

---

## Key Difference

| Expected | Actual |
|----------|--------|
| "Here's your plan, approve it" | "Tell me who owns this, then I'll make the plan" |
| One command, one output | Multi-step workflow with questions |
| Long readable plan | Structured JSON + confirmation workflow |
| Static output | Interactive scope/requirement clarification |

