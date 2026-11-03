# TailTrail Start Plan - Full Review Record

**Presentation version:** `5`

## Planning Lock

- **Run ID:** `start-20261103072510-b9704f`
- **Status:** `awaiting-approval`
- **Goal:** Complete Phase 3 MCP Start receipt routing in scripts/mcp-server.py for the Host Question Flow design. Expose a planning-readiness receipt input on tailtrail_start and forward it unchanged to the public CLI Start validator; do not let MCP accept a raw host contract, an intake-recorded receipt, stale evidence, or a mismatched target as planning authority. Preserve ordinary MCP Start calls that are outside Host Question Flow. Prove with tests/test_mcp_server.py using python3 -m unittest tests.test_mcp_server -v.
- **Request mode:** `implementation`
- **Managed writes allowed:** `false`
- **Execution status:** planning only; no source change, proof command, scanner, or Git operation has run.
- **Plan revision:** active `1`; pending `none`.

## Bound Planning Inputs

| ID | Role | Path or reference | Access | Status | Integrity |
|---|---|---|---|---|---|
| `IN-02` | requirement-artifact | `/Users/vsingha7/Desktop/tailr/TAILTRAIL-HOST-TAILTRAIL-EVIDENCE-VALIDATION-DESIGN.md` | read-only | inspected | `2cdec26124ac3acbf3ad4c8646e8f9608e7bf9d963fb9225623b12e5aec027c6` |
- These inputs remain read-only context and never grant editable implementation scope.

## Command Reference Registry

| ID | Kind | Command |
|---|---|---|
| `cmd-5886f1` | proof | `python3 -m unittest tests.test_mcp_server -v` |

## Validation Requirements And Focused Validation Matrix

### REQ-01

**Description:** Expose a planning-readiness receipt input on tailtrail_start and forward it unchanged to the public CLI Start validator; do not let MCP accept a raw host contract, an intake-recorded receipt, stale evidence, or a mismatched target as planning authority. Preserve ordinary MCP Start calls outside Host Question Flow.

- **Requirement type:** `change`
- **Validation state:** `required`
- **Editable owner(s):** `scripts/mcp-server.py`
- **Read-only input(s):** `scripts/navigator-scope-release.py`, `scripts/task-start.py`, `scripts/intake_pipeline.py`, `TAILTRAIL-HOST-TAILTRAIL-EVIDENCE-VALIDATION-DESIGN.md`
- **Proof path(s):** `tests/test_context_continuity.py`, `tests/test_mcp_server.py`
- **Success criteria:** MCP forwards a matching receipt to the canonical public CLI validator and preserves ordinary non-Host-Question-Flow Start calls.
- **Preservation criteria:** MCP does not treat raw host contracts, intake-recorded receipts, stale evidence, or wrong targets as authority.

| Tier | Command ID | Command | Candidate | State |
|---|---|---|---|---|
| contract | `cmd-5886f1` | `python3 -m unittest tests.test_mcp_server -v` | `tests/test_mcp_server.py` | resolved |
| unit | `cmd-5886f1` | `python3 -m unittest tests.test_mcp_server -v` | `tests/test_mcp_server.py` | resolved |

## Plan

1. **REQ-01:** Implement Expose a planning-readiness receipt input on tailtrail_start and forward it unchanged to the public CLI Start validator; do not let MCP accept a raw host contract, an intake-recorded receipt, stale evidence, or a mismatched target as planning authority. Preserve ordinary MCP Start calls outside Host Question Flow. in `scripts/mcp-server.py`; verify with `cmd-5886f1`, `cmd-5886f1`; inspect `scripts/navigator-scope-release.py`, `scripts/task-start.py`, `scripts/intake_pipeline.py`, `TAILTRAIL-HOST-TAILTRAIL-EVIDENCE-VALIDATION-DESIGN.md`; prove against `tests/test_context_continuity.py`, `tests/test_mcp_server.py`.
## Selected TailTrail Features

| Feature | When used | Why it is selected |
|---|---|---|
| Navigator | planning | established the evidence-bound scope and approval boundary |
| Token Autopilot | as required by the plan | selected for this task |
| Bootstrap Snapshot | as required by the plan | selected for this task |
| Code Review Graph Lite | as required by the plan | selected for this task |
| Code Graph Mapper | as required by the plan | selected for this task |
| Learning Capture Trigger | as required by the plan | selected for this task |
| Review Lens | as required by the plan | selected for this task |
| Focused QA Lens | as required by the plan | selected for this task |
| Test Precision Planner | as required by the plan | selected for this task |
| Project Learnings | as required by the plan | selected for this task |
| Learning Refresh Awareness | as required by the plan | selected for this task |

### Required before closure

- **Focused testing and validation:** prove the changed behavior, required preservation cases, and regression boundary with factual computational evidence
- **Canonical completion and closure:** prevent completion while required evidence is missing, unavailable, or failing

## Architecture Analysis

- **Status:** `not selected`. This control is not part of the approved proof boundary for this plan.

## Behaviour Analysis

- **Status:** `not selected`. This control is not part of the approved proof boundary for this plan.

## Focused Validation Coverage Summary

- **Requirements covered:** 1/1.
- **Proof command reuse:**
  - `cmd-5886f1` covers 1 requirement(s): REQ-01.

## Token Estimate

- Unavailable: scope is `ambiguous`, so a token estimate would not be reliable.
- This is an estimate from saved scope, not measured model/provider usage.

## Implementation Boundary

- **Editable scope:** `scripts/mcp-server.py`.
- **Read-only / proof-only scope:** `TAILTRAIL-HOST-TAILTRAIL-EVIDENCE-VALIDATION-DESIGN.md`, `scripts/intake_pipeline.py`, `scripts/navigator-scope-release.py`, `scripts/task-start.py`, `tests/test_context_continuity.py`, `tests/test_mcp_server.py`.
- **Excluded:** every path, command, external system, deployment, and data change not explicitly recorded above remains outside this approval.
- **Data impact:** no data impact is authorized unless a requirement above names it explicitly.

## Approval Checklist

- [x] Requirements are present and reviewable.
- [x] Every requirement has an editable implementation owner.
- [x] Runnable proof commands are registered and mapped to requirements.
- [x] Material questions are resolved.
- [x] Mandatory planning audit is clean for this exact plan revision.
- [ ] The host has reviewed the scope, preservation criteria, proof commands, analyses, and excluded boundary.

## Review Cycles Summary

| Cycle | Revision | Status | Action |
|---|---|---|---|
| 1 | v1 | initial review | Start Plan generated and mandatory audit required |

- **Total review cycles:** 1
- **Revision cycles:** 0
- **Latest audit:** `clean`; 0 finding(s).

## Approval Decision

**READY FOR APPROVAL** — review this plan, then explicitly approve this exact run. Approval is separate from activation and permits no unlisted work.

## Canonical Machine Record

- Machine-readable state remains available at [`.tailtrail/runs/start-20261103072510-b9704f/planning/start-report-v1.json`](.tailtrail/runs/start-20261103072510-b9704f/planning/start-report-v1.json); it is not the approval view.

---

*End of Start Plan.*