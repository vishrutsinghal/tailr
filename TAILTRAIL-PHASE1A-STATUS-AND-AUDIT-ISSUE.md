# Host Question Flow: Remaining Phases and Phase 1A Audit Blocker

## Purpose

Record the current delivery status of the TailTrail Host Question Flow, the
remaining Phase 1A work, and the historical planning-audit defect that was fixed
in the current branch.

This is a status and remediation record. It does not authorize source edits,
alter an approved anchor, or replace the implementation plan.

## Status snapshot (2026-10-16)

| Area | Status | Truth |
| --- | --- | --- |
| Phase 0 | complete | Contract, state, role, redaction, and compatibility baseline is present. |
| Phase 1A | **remaining integration gap** | Intake primitives exist, but `question-orchestrator.py` is not wired to them at the real call site. |
| Phase 1B | partial implementation | Replay, integrity, redacted projections, and lifecycle guards exist in `intake_pipeline.py`; end-to-end Phase 1A integration is still missing. |
| Phase 2 | partial / not complete | Host-boundary protocol, acceptance, clarification, and due-diligence work is not complete end to end. |
| Phase 2.5 | partial | Task profiles and focused tests exist; this does not complete Phase 2. |
| Phase 3 | not complete | Packet finalization and answer-to-binding projections remain outstanding. |
| Phases 4A-8 | not started or not fully validated | These remain roadmap work. |
| Pending-revision audit defect | **resolved** | Pending revisions are now audited from their `proposed_report`; regression coverage exists. |

## Current status

### Phase 0: Contract and state specification

Phase 0 is treated as the completed baseline. Its protocol, state, role,
redaction, and compatibility definitions are the basis for later work.

### Phase 1A: Minimal intake and event correlation

The following foundation is present:

- `scripts/intake_pipeline.py` provides central event, question, observation,
  and answer correlation primitives.
- Focused intake and event-schema tests exist and passed before the current
  planning attempt.

The remaining Phase 1A exit-criterion gap is at the real call site:

- `scripts/question-orchestrator.py` does not yet use the intake pipeline for
  Navigator-owned question issuance and direct or narration-derived answer
  recording.

The intended narrow change is therefore to wire the existing intake dependency
into `scripts/question-orchestrator.py`, preserving current question quality.
It must not introduce Phase 2 acceptance states, clarification loops, scope or
proof authority, packet finalization, or any new host-facing route.

## Phases that remain after Phase 1A

The delivery order is intentionally Phase 1A, then Phase 2, then Phase 1B.

| Phase | Remaining outcome |
| --- | --- |
| 2 — Navigator Host Protocol | Make Navigator the exclusive host question and clarification boundary; add profiling, profile fields, narration ingestion, candidate mapping, acceptance states, bounded clarification, escalation, and new-file due diligence. |
| 1B — Full Event Durability and Replay | Add the remaining integrated persistence, replay and resume behavior after Phase 1A wiring. Core primitives are present but not end-to-end complete. |
| 3 — Requirement and Packet Finalization | Convert accepted answers into one immutable, anchor-bound packet with requirement, path-role, proof, criteria, and correction-premise bindings. |
| 4A — Existing Scope Authority Baseline | Verify and adapt existing scope/anchor enforcement rather than duplicate it. |
| 4B — Answer-to-Path Authorization | Bind editable paths to accepted answers, packet views, and anchor versions. |
| 5 — Proof and Validation Projection | Require exact requirement-to-proof bindings and reject unrelated passing tests. |
| 6 — Component Adapter Integration | Route existing components through finalized projections without allowing direct host interpretation. |
| 7 — Entry-Point, Recovery, and Security Hardening | Enforce one CLI/facade/MCP path, safe recovery, redaction, authorization, and concurrency controls. |
| 8 — P7 and correction-premise end-to-end validation | Prove the full flow with safe negative and complete positive scenarios. |

## Phase 1A planning attempt

- **Run:** `start-20261016111910-f58865`
- **Initial state:** `awaiting-approval`
- **Revision:** v1 to v2
- **Approved editable owner proposed by v2:**
  `scripts/question-orchestrator.py`
- **Inspection-only dependency:** `scripts/intake_pipeline.py`
- **Proof path:** `tests/test_question_orchestrator.py`
- **Planned unit command:**
  `python3 -m unittest discover -s tests -p test_question_orchestrator.py -v`

The v2 revision deliberately made no scope or proof expansion. It clarified
that the intake module is an existing dependency to consume, not a second
implementation-owner path.

## Historical blocker: pending revisions were not audited

**Status: resolved in the current branch.** The original issue was valid when
observed, but the document previously described it as still active.

### What happened historically

1. The v1 planning audit found a named-path gap for
   `scripts/intake_pipeline.py` and requested behaviour and integration proof
   for the boundary constraint.
2. Those repairs were not safe. The host contract declared the intake module
   as inspection-only, and this internal wiring change has no user-facing
   behaviour or external integration requirement.
3. A v2 `requirement-update` revision preserved the exact owner and unit proof
   while removing the wording that caused the audit to infer unsupported
   authority and proof tiers.
4. The next `tailtrail planning audit` returned the old v1 requirement IDs,
   wording, path, and proof tiers instead of evaluating `revision-v2.json`.

### Validated symptom

The saved v2 revision has a new fingerprint and revised requirement text, but
the audit response reports v1 findings. In particular, it proposes:

- `scope-add` for `scripts/intake_pipeline.py`; and
- empty placeholder commands for `behaviour` and `integration` proof tiers.

That proved the audit result was stale relative to the pending revision.

## Why the suggested repairs must not be applied

| Suggested repair | Why it is unsafe |
| --- | --- |
| Add `scripts/intake_pipeline.py` as implementation scope | It changes an inspection-only dependency into editable write authority, violating the declared scope contract. |
| Add a behaviour proof command | It would claim a user-facing behaviour tier that this Phase 1A internal-wiring slice explicitly excludes. |
| Add an integration proof command | It would fabricate a proof obligation and potentially force Phase 2 work into the Phase 1A slice. |
| Approve v2 despite the audit | It would bypass the mandatory plan-completeness gate and make the approval record misleading. |

## Applied TailTrail fix

`tailtrail planning audit` now resolves the same planning artifact the user
would approve:

1. When a run is `awaiting-approval` and has a valid pending revision, load
   that revision's `proposed_report` and revised requirement matrix.
2. Audit named paths, validation tiers, focused proof commands, scope roles,
   and plan fingerprints from that candidate, not from the frozen v1 Start
   report.
3. When there is no pending revision, continue auditing the original current
   proposal.
4. Fail closed if the pending revision is malformed, stale, has mismatched
   fingerprints, or cannot be projected; do not silently fall back to v1.
5. Render the audit result with the artifact path, revision number, and
   fingerprint actually audited, so a host can verify that the report and
   approval candidate match.

### Regression coverage

- A v1 plan has a genuine audit finding; a v2 revision fixes it; auditing the
  run evaluates v2 and becomes clean.
- The audit output identifies v2's artifact path, revision, and fingerprint.
- A path declared inspection-only remains non-editable even when it appears in
  an earlier requirement statement.
- A removed tier is not reported from v1 after a v2 revision excludes it.
- A corrupt or stale pending revision fails closed rather than falling back to
   the base plan.
- An audit with no pending revision preserves existing base-plan behavior.

The implementation is in `scripts/planning-audit.py`, and the pending-revision
regression is covered by `tests/test_planning_audit.py`.

## Safe next steps

1. Start Phase 1A planning for the narrow `question-orchestrator.py` wiring.
2. Audit and approve that plan without expanding `intake_pipeline.py` into
   implementation scope.
3. Implement and prove the real call-site integration.
4. Reassess Phase 1B through the integrated Phase 1A flow.

Until then, the Host Question Flow is not complete, even though several later
phase primitives and tests now exist.
