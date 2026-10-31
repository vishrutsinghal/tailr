# TailTrail Start Plan - Full Review Record

**Presentation version:** `4`

## Planning Lock

- **Run ID:** `start-20261030164241-6c2ecb`
- **Status:** `awaiting-approval`
- **Goal:** Record every orchestrator-driven return to IMPLEMENTATION with its reason, classification, evidence, and outcome in canonical pipeline history.
- **Request mode:** `implementation`
- **Managed writes allowed:** `false`
- **Execution status:** planning only; no source change, proof command, scanner, or Git operation has run.
- **Plan revision:** active `1`; pending `3`.

## Bound Planning Inputs

- No read-only planning inputs were bound to this plan.

## Command Reference Registry

| ID | Kind | Command |
|---|---|---|
| `cmd-20b152` | proof | `python3 -m unittest discover -s tests -p test_failure_classification.py -v` |
| `cmd-add31c` | proof | `python3 -m unittest tests.test_sequential_pipeline -v` |

## Validation Requirements And Focused Validation Matrix

### REQ-01

**Description:** Record every orchestrator-driven return to IMPLEMENTATION with its reason, classification, evidence, and outcome in canonical pipeline history.

- **Requirement type:** `change`
- **Validation state:** `required`
- **Editable owner(s):** `scripts/pipeline_orchestrator.py`
- **Proof path(s):** `tests/test_sequential_pipeline.py`, `tests/test_failure_classification.py`
- **Success criteria:** The stated requirement is observably satisfied on its approved path.; Every orchestrator-driven return to IMPLEMENTATION records its reason, classification, evidence, and outcome through the canonical pipeline history API.; Mechanical returns are visibly distinct from budget-consuming regressions.
- **Preservation criteria:** Do not change behavior outside this approved requirement boundary.; Do not change the existing regression budget or environmental diagnose-no-transition behavior.; Do not invent stage-bound files when the handoff or evidence did not supply them.
- **Requirement behaviour scenarios:**
  - `BHV-PIPELINE-RETURN-01`: Route both a mechanical failure and a budget-consuming regression from testing back to implementation. → Each return records the reason, classification, supplied evidence, outcome, and no inferred stage-bound files; the mechanical return remains distinct from the regression.

| Tier | Command ID | Candidate | State |
|---|---|---|---|
| unit | `cmd-20b152` | `tests/test_failure_classification.py` | resolved |
| unit | `cmd-add31c` | `tests/test_sequential_pipeline.py` | resolved |
| behaviour | `cmd-add31c` | `tests/test_sequential_pipeline.py` | resolved |

## Selected TailTrail Features

| Feature | When used | Why it is selected |
|---|---|---|
| Navigator | planning | established the evidence-bound scope and approval boundary |
| Token Autopilot | as required by the plan | selected for this task |
| Bootstrap Snapshot | as required by the plan | selected for this task |
| Code Review Graph Lite | as required by the plan | selected for this task |
| Code Graph Mapper | as required by the plan | selected for this task |
| Learning Capture Trigger | as required by the plan | selected for this task |
| CI/Sonar Intelligence | as required by the plan | selected for this task |
| QA / CI-Sonar Lens | as required by the plan | selected for this task |
| Project Learnings | as required by the plan | selected for this task |
| Learning Refresh Awareness | as required by the plan | selected for this task |

### Required before closure

- **Focused testing and validation:** prove the changed behavior, required preservation cases, and regression boundary with factual computational evidence
- **Canonical completion and closure:** prevent completion while required evidence is missing, unavailable, or failing

## Architecture Analysis

- **Status:** `planning-hypothesis`.
- **Evidence boundary:** Derived from explicit user wording and repository path inventory only. Source, caller relationships, and edit necessity are not confirmed until after approval.

| Requirement | Invariant | Planned proof |
|---|---|---|
| REQ-01 | The implementation must follow the existing repository boundaries discovered after approval. | Changed-scope comparison plus the repository's focused tests. |

### Scoped evidence

| Path | Role | Planned use | Confidence |
|---|---|---|---|
| `scripts/pipeline_orchestrator.py` | orchestration boundary | Primary implementation candidate, subject to post-approval source and caller confirmation. | repository-inventory hypothesis |
| `tests/test_failure_classification.py` | test evidence | Run only when its tier proves an approved requirement. | repository-inventory hypothesis |

### Post-change checks

1. Confirm the authoritative boundary and material callers before the first edit.
2. Compare actual changed files and symbols with the approved impact map; justify or correct every unexpected path.
3. Detect missed callers, caller-specific business logic, wrong-layer placement, and public-contract drift.
4. Check dependency manifests and imports when the approved contract forbids a new dependency.
5. Run every requirement-linked validation tier and preserve unresolved evidence as a gap, not a pass.

## Behaviour Analysis

- **Status:** `not selected`. This control is not part of the approved proof boundary for this plan.

## Focused Validation Coverage Summary

- **Requirements covered:** 1/1.
- **Proof command reuse:**
  - `cmd-20b152` covers 1 requirement(s): REQ-01.
  - `cmd-add31c` covers 1 requirement(s): REQ-01.

## Token Estimate

- **Planned working set:** approximately `698` tokens (confidence: `medium`).
- **Scoped-file ceiling:** approximately `4528` tokens; estimated reduction `84.58%`.
- **Confidence basis:** at least one bounded slice lacks an exact combined behavior-and-symbol anchor.
- This is an estimate from saved scope, not measured model/provider usage.

## Implementation Boundary

- **Editable scope:** `scripts/pipeline_orchestrator.py`.
- **Read-only / proof-only scope:** `tests/test_failure_classification.py`, `tests/test_sequential_pipeline.py`.
- **Excluded:** every path, command, external system, deployment, and data change not explicitly recorded above remains outside this approval.
- **Data impact:** no data impact is authorized unless a requirement above names it explicitly.

## Approval Checklist

- [x] Requirements are present and reviewable.
- [x] Every requirement has an editable implementation owner.
- [x] Runnable proof commands are registered and mapped to requirements.
- [x] Material questions are resolved.
- [x] Mandatory planning audit is clean for this exact plan revision.
- [ ] The host has reviewed the scope, preservation criteria, proof commands, analyses, and excluded boundary.
- **Risks to review:** ci/sonar

## Review Cycles Summary

| Cycle | Revision | Status | Action |
|---|---|---|---|
| 1 | v1 | initial review | Start Plan generated and mandatory audit required |
| 2 | v2 | revision recorded | Plan changed and must be audited again |
| 3 | v3 | revision recorded | Plan changed and must be audited again |

- **Total review cycles:** 3
- **Revision cycles:** 2
- **Latest audit:** `clean`; 0 finding(s).

## Approval Decision

**READY FOR APPROVAL** — review this plan, then explicitly approve this exact run. Approval is separate from activation and permits no unlisted work.

## Canonical Machine Record

- Machine-readable state remains available at [`.tailtrail/runs/start-20261030164241-6c2ecb/planning/start-report-v1.json`](.tailtrail/runs/start-20261030164241-6c2ecb/planning/start-report-v1.json); it is not the approval view.

---

*End of Start Plan.*