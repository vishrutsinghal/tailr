# Drift Analysis Implementation — Design Notes & Discussion Record

> **Status:** Design discussion record for the missing `drift_analysis.py` module.
> **Related docs:** `docs/arch/navigator-pipeline-orchestration.md` (§4.3 Drift-Corrected Handoff), `docs/arch/sequential-worker-pipeline.md` (§4.2 Drift Analysis).
> **Scope:** Captures the implementation plan, detection mechanism, and post-drift flow agreed during the design discussion for the Sequential Worker Pipeline drift gate.

---

## 1. Problem Statement

`scripts/pipeline_judge.py` implements the drift gate for the `TESTING → INFRA` stage transition:

```python
# scripts/pipeline_judge.py — _check_drift_gate (lines 51-71)
try:
    import drift_analysis
    result = drift_analysis.analyze(self.root, self.run_id)
    if result.get("drift_detected"):
        return False, "Stage transition blocked: Requirement drift detected..."
except ImportError:
    pass
```

**The `drift_analysis` module does not exist.** The `except ImportError: pass` silently falls back to the weaker `requirement_pointers` presence check (lines 65-69). This means:

- The primary drift gate is a **dead code path**.
- Docs §4.2/§4.3 "Drift Analysis" mandatory stage gate is only a proxy fallback, not the real requirement-drift comparison.
- A transition can pass without any real comparison of final code against original requirements.

## 2. Design Contract (from the architecture docs)

From `navigator-pipeline-orchestration.md` §4.3:

> Transitions between stages are not automatic; they are **evidence-gated**.
> 1. Agent submits a `HandoffManifest` (Changes → Test Results).
> 2. Navigator calls `PipelineJudge.verify_transition()`.
> 3. Judge runs **Drift Analysis** → Compares final code against original requirements.
> 4. If `drift_detected == true` → **Transition Blocked**.

From `sequential-worker-pipeline.md` §4.2:

> Before transitioning from `TESTING` → `INFRA`, the system triggers the **Drift Analysis** module.
> It compares the final state of the production code against the **Original Requirements**.
> If the fix introduces "Requirement Drift," the transition is blocked.

## 3. Reuse-First Design (no new dependencies)

The codebase already has the exact drift machinery. The new module reuses it rather than inventing new abstractions:

| Existing module | What it provides | How `drift_analysis` reuses it |
| :--- | :--- | :--- |
| `scripts/run-ledger.py` | `state_dir(root, run_id)` → `.tailtrail/runs/<run_id>` | Locate `anchors/approved-v1.json` (the approved requirement baseline) |
| `scripts/requirement-impact-map.py` | `map_impact(root, run_id, changed)` → per-requirement `classification: "mapped" \| "new-drift"` | Map each changed path to approved `likely_paths`; any `new-drift` = requirement drift |
| `scripts/harness-checkpoint.py` | `checkpoint()` scope logic: `approved_editable = likely_paths ∪ validation editable/proposed`; `unexpected = changed − approved_editable` → `new-drift` | Reuse the same approved-editable computation for scope drift |
| `scripts/planning_lock.py` | `pipeline.last_handoff.change_manifest` (the HandoffManifest the agent submitted) | Source of actual changed paths when no explicit list is passed |

## 4. The Two Sides of the Comparison

### "Original requirements" = the immutable approved anchor

`.tailtrail/runs/<run_id>/anchors/approved-v1.json` (written at plan approval, never mutated). Each requirement row contains:

- `requirement_uid`, `display_id`, `statement`
- `kind` — `"change"` or `"preserve"` (preserve requirements are exempt from the "unimplemented" check)
- `likely_paths` — the approved implementation-owner paths for that requirement
- `validation_contract` — `tiers`, `editable_paths`, `proposed_paths`
- `approved_fingerprint` — hash of the whole anchor

### "Final code" = actual change evidence

Sourced in priority order:

1. The `HandoffManifest.change_manifest` the agent submitted (e.g. `["src/auth.py:L20-L45"]`)
2. `pipeline.last_handoff.change_manifest` in the planning lock
3. Latest `checkpoints/checkpoint-*.json` → `changed_paths` (each with a content `fingerprint`)

## 5. The Three Deterministic Drift Checks

### Check A — Scope drift: did you touch files you were never approved to touch?

```
approved_editable = {likely_paths for all requirements}
                  ∪ {validation_contract.editable_paths}
                  ∪ {validation_contract.proposed_paths}
unexpected = set(actual_changed) − approved_editable
drift if unexpected ≠ ∅
```

This is the exact logic already in `harness-checkpoint.py:40-44` (`new-drift` classification). It catches "agent edited `infra/` during IMPLEMENTATION" or "agent edited `auth.py` during TESTING."

### Check B — Requirement coverage drift: did you change production code no requirement owns?

```
for each changed path p:
    if p is in NO requirement's likely_paths  →  new-drift
```

This is `requirement-impact-map.py:44` — a requirement row is `"mapped"` only if `relevant` (changed ∩ likely_paths) is non-empty; otherwise `"new-drift"`.

### Check C — Requirement-unimplemented drift: did a requirement get zero production changes?

```
for each requirement r (kind == "change"):
    if r.likely_paths ∩ actual_changed == ∅  →  requirement-unimplemented
```

This is the **"coding for the test"** case the docs target: only `tests/` changed, production untouched, yet the agent claims the requirement is done. `completion-review.py` already flags this as `new-drift` when an approved requirement is absent from the actual checkpoint.

> **Note:** `kind == "preserve"` requirements are exempt from Check C — they are preservation constraints, not new work. Their `likely_paths` define the approved boundary, and a change requirement touching those paths is fine.

## 6. Worked Examples

Approved anchor:

```
REQ-01  "JWT token rotation"   likely_paths: ["src/auth.py"]
REQ-02  "Rate limiting"        likely_paths: ["src/middleware/rate_limit.py"]
```

### Case 1 — clean handoff (TESTING → INFRA allowed)

```
change_manifest = ["src/auth.py", "tests/test_auth.py"]
A: both paths ∈ approved_editable          → no scope drift
B: src/auth.py ∈ REQ-01.likely_paths       → mapped
C: REQ-01 has a change; REQ-02 untouched   → REQ-02 flagged requirement-unimplemented
drift_detected = True  → transition BLOCKED (REQ-02 was never implemented)
```

This is the correct behavior — you cannot promote to INFRA while a requirement has no implementation.

### Case 2 — coding for the test

```
change_manifest = ["tests/test_auth.py"]   # only tests changed
A: tests path is editable (validation contract)  → no scope drift
B: no production path changed                     → no mapped requirement
C: REQ-01.likely_paths ∩ changed == ∅            → requirement-unimplemented
drift_detected = True  → transition BLOCKED
```

### Case 3 — scope creep

```
change_manifest = ["src/auth.py", "infra/terraform/main.tf"]
A: infra/terraform/main.tf ∉ approved_editable   → new-drift scope finding
drift_detected = True  → transition BLOCKED
```

## 7. Honest Boundary — What Path Comparison Cannot Detect

Path-based drift is deterministic but **shallow**: it proves *where* code changed, not that the code still *satisfies the requirement's intent*. Semantic drift ("passes tests but no longer implements REQ-01's business rule") is caught by the layers that already exist and that `drift_analysis` will call into:

| Layer | Module | What it verifies |
| :--- | :--- | :--- |
| Path/scope (new) | `drift_analysis.py` | approved paths vs actual changed paths (checks A/B/C above) |
| Evidence | `harness-checkpoint.py` | each requirement `state == "validated"` = authoritative evidence + required tiers passed + no non-passing evidence |
| Architecture contract | `architecture-fitness.py` | protected paths unchanged, no forbidden imports, no new dependencies |
| Behavior contract | `behavior-harness` | approved behavior scenarios still pass |

So `drift_analysis.analyze()` returns `drift_detected` from the path/scope layer, and the Judge's gate stays **fail-closed**: if the anchor is missing, if there is no change evidence, or if any of A/B/C finds drift, the `TESTING → INFRA` transition is blocked and the agent is sent back to IMPLEMENTATION with the specific finding (e.g. "REQ-02 has no implementation changes").

## 8. Post-Drift Flow: Who Is Notified, Who Resolves

Traced from `pipeline_orchestrator.py`, `pipeline_judge.py`, `harness-feedback.py`, `execution-failure.py`.

### What happens today when drift is detected

```
PipelineJudge._check_drift_gate()          → (False, "Stage transition blocked: ...")
        ↓
PipelineOrchestrator.request_handoff()     → returns string "Stage transition blocked: {error}"
        ↓
caller (Navigator/host agent)              → flow STOPS here
```

**Current state:** the drift gate blocks the transition and returns a message string, but:

- ❌ No drift artifact is persisted
- ❌ No explicit user notification is triggered
- ❌ No automatic regression loop is started
- ❌ The agent is not told to auto-fix

It relies on the host agent relaying the blocked message. The building blocks for a proper flow exist but are **not wired to the drift gate**.

### Building blocks that already exist

| Module | What it does | Who it faces |
| :--- | :--- | :--- |
| `harness-feedback.py` | Creates a `correction-needed` packet: `requirement_uid`, `drift_category`, `classification`, `evidence`, `allowed_scope`, `next_validation`; persists to `feedback/feedback-N.json`; rule: *"one highest-value correction only; do not retry indefinitely"* | Agent-facing |
| `execution-failure.py` `map_requirement()` | Records a `drift_link`: `drift_created: True`, `checkpoint_delta`, `suspected_paths`, `reason` | Persisted evidence |
| `execution-failure.py` `correction_route()` | Routes the correction: **blocked → `requires_approval: True`**; else → records one bounded next action with `correction_executed: False`. Boundary: *"it does not edit source or execute a retry"* | User-gated |
| `execution-failure.py` `authority_decision()` | `infrastructure/dependency/permission/data` → **blocked, user approval required**; read-only diagnosis → allowed; safe-retry (env/transient) → allowed | User-gated |
| `pipeline_orchestrator.handle_regression()` | Circuit breaker: after **3 loops** → *"CIRCUIT BREAKER TRIGGERED: Too many implementation-testing loops. Manual design review required."* | User-facing |

### Intended flow (what the implementation wires up)

**User IS notified. Agent does NOT auto-resolve.** The flow after drift:

```
1. Drift detected at TESTING → INFRA gate
        ↓
2. Transition BLOCKED (already works)
        ↓
3. Drift finding PERSISTED as evidence
   (execution-failure.map_requirement → drift_link artifact)
        ↓
4. USER NOTIFIED with the specific finding:
   "REQ-02 has no implementation changes" / "path X is outside approved scope"
        ↓
5. CORRECTION ROUTED (never auto-executed):
   ├─ Scope/requirement drift → return to IMPLEMENTATION stage
   │    (regression loop, max 3 iterations)
   ├─ After 3 loops → CIRCUIT BREAKER → "Manual design review required" (user decides)
   └─ Authority-blocked (infra/dependency/permission/data)
        → requires_approval: True → user must approve before any fix
        ↓
6. Agent proposes a bounded correction → user approves → agent fixes
   (correction_executed stays False until explicit approval)
```

### Key principle

- **Drift never auto-resolves.** `correction_route()` explicitly sets `correction_executed: False` and its boundary says *"it does not edit source or execute a retry."*
- **The user is the final gate.** Either through the regression loop's circuit breaker (3 strikes → manual design review) or through explicit approval for authority-blocked corrections.
- **The agent's job after drift** is to *propose* the correction (return to IMPLEMENTATION with the drift evidence), not to silently fix it.

## 9. Implementation Plan

### New file: `scripts/drift_analysis.py`

**`analyze(root: Path, run_id: str, evidence: dict | None = None) -> dict[str, Any]`** — the exact contract `pipeline_judge._check_drift_gate` already expects:

1. **Load approved baseline** — read `state_dir(root, run_id)/anchors/approved-v1.json`. If missing → **fail closed**: `drift_detected: True`, reason `anchor-missing` (a transition gate must never pass without the approved baseline).
2. **Determine actual changed paths** — primary: `evidence.get("change_manifest")` (from the HandoffManifest); fallback: `pipeline.last_handoff.change_manifest` in the planning lock; last resort: latest `checkpoints/checkpoint-*.json` `changed_paths`. If none → **fail closed**: `no-change-evidence`.
3. **Requirement mapping drift** — call `requirement_impact_map.map_impact(root, run_id, changed)`. Any requirement row with `classification == "new-drift"` (changed path outside its approved `likely_paths`) → drift finding.
4. **Scope drift** — recompute `approved_editable` exactly like `harness_checkpoint` (likely_paths ∪ validation editable/proposed). Any `unexpected` path → `new-drift` scope finding.
5. **Requirement coverage drift** — every approved requirement must have ≥1 changed path in its `likely_paths`. A requirement with zero changed paths → `requirement-unimplemented` (this is the "coding for the test" case: only tests changed, production untouched).
6. **Aggregate** — `drift_detected = bool(anchor_missing or no_change_evidence or scope_drift or requirement_unimplemented)`.
7. **Return** — `{"drift_detected": bool, "findings": [...], "scope_assessment": {...}, "evidence": {...}}` so the Judge's `result.get("drift_detected")` works unchanged and the findings are auditable.

Also add a `main()` CLI (`--root`, `--run-id`, `--changed`) matching the `harness-checkpoint.py` / `requirement-impact-map.py` pattern, so it can be run standalone and tested.

### Small change to `scripts/pipeline_judge.py`

- Pass the handoff evidence into the analyzer: `drift_analysis.analyze(self.root, self.run_id, evidence=evidence)` so `change_manifest` flows from the actual handoff.
- Keep the `requirement_pointers` check as a **secondary** guard (it is a legitimate extra constraint), but the primary real-drift comparison now runs.
- No other changes to the Judge.

### Focused test (per AGENTS.md: one runnable check that fails if behavior breaks)

New `tests/test_drift_analysis.py`:

- Temp root + fake `approved-v1.json` with two requirements and `likely_paths`.
- Case A: changed paths inside approved scope → `drift_detected == False`.
- Case B: changed path outside approved scope → `drift_detected == True` with `new-drift` finding.
- Case C: no changed path for a requirement → `drift_detected == True` with `requirement-unimplemented`.
- Case D: missing anchor → `drift_detected == True` (fail closed).

### Files touched (smallest maintainable diff)

1. `scripts/drift_analysis.py` — **new** (the missing module)
2. `scripts/pipeline_judge.py` — 1-line change (pass `evidence` into `analyze`)
3. `tests/test_drift_analysis.py` — **new** focused test

**Not touched:** `pipeline_manager.py`, `planning_lock.py`, `navigator_scope.py`, `write_guardian.py`, docs — they already work and need no changes.

### Verification

- Run `python3 -m pytest tests/test_drift_analysis.py` (or the project's test runner) — all 4 cases pass.
- Run existing pipeline tests (`pipeline_judge`, `pipeline_manager`, `pipeline_orchestrator`) to confirm no regression.
- Confirm `pipeline_judge._check_drift_gate` now takes the real path: `import drift_analysis` succeeds, `result.get("drift_detected")` is a real comparison, and the `except ImportError` fallback is no longer the active path.

## 10. Design Refinements from Review: Failure Classification, Fulfillment Drift, Requirement Concreteness

> **Status: implemented.** §10.1 lives in `scripts/pipeline_orchestrator.py` (`classify_test_failure` + classified `handle_regression` routing); §10.2 and §10.3 live in `scripts/drift_analysis.py` (`_requirement_validated` fulfillment check + `_validate_concreteness` gate). The classifier reuses `execution-failure.py`'s `classify()`, whose broken load path (`scripts/planning_lock.py` → `scripts/planning_lock.py`) was fixed as part of this work.

Review of the first implementation surfaced three gaps. Each is recorded here with the agreed direction.

### 10.1 Not every failed test is drift — classify the failure before routing

A failed test has at least three distinct causes, and they must route differently:

| Failure cause | Example | Is it drift? | Route |
| :--- | :--- | :--- | :--- |
| Mechanical/syntax | `SyntaxError`, import error, typo | No — rerunning the test is pointless until the code compiles | Direct handoff to the Implementation Worker as a mechanical fix; does not consume a regression-loop iteration; no design implication |
| Behavioral/assertion | Test ran and the assertion failed | Yes — the implementation contradicts the expected behavior | Regression loop with requirement-linked drift evidence; consumes a loop iteration |
| Environmental | Missing dependency, network, permissions | No (per `TAILTRAIL-POST-IMPLEMENTATION-FAILURE-DESIGN.md`) | Diagnose read-only; do not regress or edit source |

**Current gap:** `handle_regression(reason, evidence)` treats every failure identically — it resets the stage and increments `regression_count` without classifying the cause.

**Agreed direction:** classify the failure evidence before routing, reusing `execution-failure.classify()` (keyword classification of stable error codes) and `authority_decision()`. The Testing Worker's handoff to the Implementation Worker carries the classified failure; only behavioral failures create requirement-linked drift and consume the loop budget.

### 10.2 Passing tests do not prove fulfillment — fulfillment drift

Path-based drift (checks A/B/C) proves *where* code changed — it cannot prove the code *fulfills the requirement's intent*. A green test that is not linked to the requirement's acceptance criteria is not proof.

The anchor already carries the fulfillment contract per requirement:

- `acceptance_criteria` — observable, testable statements
- `behavior_contract.scenarios` — behavior evidence
- `validation_contract.tiers` — required evidence tiers

**Agreed direction:** extend the `TESTING → INFRA` drift gate with a **fulfillment check** that reuses `harness-checkpoint.py`'s `validated` computation: every approved `change` requirement must have authoritative, passing evidence at its required tiers, linked to that requirement. A requirement with production changes and passing-but-unlinked tests is `implemented-unverified` → drift. The gate becomes: **path drift (A/B/C) + fulfillment drift (evidence-linked validation)**, both against the same immutable anchor.

### 10.3 Concrete requirement analysis is the precondition

None of the above works if the requirements are vague. "Make it work" cannot be drift-checked. The approved anchor is the requirement-analysis artifact, and it must be concrete before the pipeline activates:

- Every `change` requirement needs observable `acceptance_criteria` and `likely_paths`.
- Every `preserve` requirement needs explicit `preserve_rules`.
- `constraint`/`safety` kinds carry their boundary; `decision` kinds pause rather than guess (matching `_REQUIREMENT_KIND_LABELS` in `planning_lock.py`).

**Agreed direction:** add a **planning-time concreteness gate** — the pipeline cannot activate (and the drift gate cannot run meaningfully) against an anchor whose change requirements lack acceptance criteria and likely paths. Vague requirements fail closed at planning, not silently at runtime.

## 11. Evidence Trail (source references)

| Claim | Evidence |
| :--- | :--- |
| `drift_analysis.py` is missing | `python3 -c "..."` → `drift_analysis.py MISSING`; only reference is the import inside `pipeline_judge.py` |
| Judge contract | `scripts/pipeline_judge.py:58-63` — `drift_analysis.analyze(self.root, self.run_id)` → `result.get("drift_detected")` |
| Anchor schema | `.tailtrail/runs/start-20260829065627-13f315/anchors/approved-v1.json` — `requirements[].{requirement_uid, display_id, kind, likely_paths, validation_contract, status}` |
| Scope drift logic | `scripts/harness-checkpoint.py:40-44` — `approved_editable` / `unexpected` / `new-drift` |
| Per-requirement mapping | `scripts/requirement-impact-map.py:44` — `classification: "mapped" \| "new-drift"` |
| Handoff manifest shape | `docs/arch/sequential-worker-pipeline.md` §3.2 + `scripts/pipeline_manager.py` `HandoffManifest` |
| Post-drift routing | `scripts/execution-failure.py` `correction_route()` / `authority_decision()`; `scripts/harness-feedback.py` |
| Circuit breaker | `scripts/pipeline_orchestrator.py` `handle_regression()` — 3-loop limit |
