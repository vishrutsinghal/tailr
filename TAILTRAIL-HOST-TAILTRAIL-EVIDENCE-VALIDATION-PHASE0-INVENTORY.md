# Host–TailTrail Evidence Validation — Phase 0 Inventory and Ownership Map

## Delivery Record

- **Design source:** `TAILTRAIL-HOST-TAILTRAIL-EVIDENCE-VALIDATION-DESIGN.md`
- **Validated run:** `start-20261027101501-5f1c2b`
- **Request mode:** `validation-only`
- **Inventory decision date:** 2026-10-28
- **Method:** Read-only tracing of the approved Start, AIDLC, scope, proof,
  receipt, audit, report, Closure, and Meta-Harness surfaces. File/symbol
  associations below are source-inspection evidence; they are not claims of
  runtime behavior beyond the linked focused tests.
- **No authority change:** This document does not grant an implementation
  owner, alter a Planning Lock, issue a receipt, or change Meta-Harness
  behavior.

## Exit-Gate Decision

**Met for Phase 0.** Each design capability has a current owner/dependency map
and an explicit reuse-or-gap decision. The inventory does **not** claim that
the complete Evidence Validation Contract is implemented. It identifies the
first integration slice still needed: a versioned planning-readiness receipt
and a pre-v1 reconciliation gate that consume the existing intake, semantic,
scope, and proof artifacts.

## Ownership Rules Used By This Map

| Role | Meaning in this inventory |
|---|---|
| Writer | The current component that persists or derives the artifact. |
| Reader | A component that validates, projects, or consumes that artifact. |
| CLI route | The public dispatcher route, when one is wired. A direct script is explicitly marked when no public route was established by this review. |
| Reuse | Current behavior can be consumed without a parallel owner. |
| Gap | The design requires a missing integration, schema, or proof boundary. It is not an authorization to edit the named file. |

## System Map

```text
Host observations / direct answers
  -> question-orchestrator.NavigatorHostProtocol
  -> intake_pipeline.IntakePipeline (append-only events, acceptance, replay)
  -> packet view / operational projection
  -> navigator_scope (path-role and freshness evidence)
  -> task-start + planning-audit (canonical Start and plan checks)
  -> execution-evidence + completion-policy + closure/report projections

Sanitized cross-task feedback remains separate:
  harness-review -> tailtrail-meta/harness-summary.jsonl -> meta-harness-analyze
```

## Evidence-Backed Owner and Dependency Matrix

| Design capability | Current schema / persistent record | Writer | Reader / public route | Focused proof | Reuse-or-gap decision |
|---|---|---|---|---|---|
| Hash-bound host contract, roles, criteria, proof command | `schemas/host-input-contract.schema.json`; validated contract projection | `scripts/host_contract.py`; `scripts/task-start.py` | `task-start.py --host-contract-*`; public `tailtrail start` delegates to `task-start.py` | `tests/test_host_contract.py`, `tests/test_host_input_contract_schema.py`, `tests/test_public_route_gate.py` | **Reuse.** Validation-only blocks implementation-owner roles. Gap: contract acceptance is not itself a planning-readiness receipt. |
| Requirement artifact grounding and typed interpretation | `schemas/requirement-interpretation.schema.json`; artifact SHA-256 bindings in Start inputs | `scripts/requirement_discovery.py`; `scripts/task-start.py` | `tailtrail start --requirement-artifact --requirement-interpretation-*` | `tests/test_requirement_routing_phase0.py`, `tests/test_requirement_discovery.py` | **Reuse.** Exact goal/artifact grounding exists. Gap: artifact-grounded facts are not yet reconciled against every Start projection. |
| Pre-lock requirement intake | `schemas/requirement-intake.schema.json`; `.tailtrail/requirement-intakes/<id>/current.json` | `scripts/requirement_intake.py` | `tailtrail requirements show|answer`; resumed by `tailtrail start --requirement-intake-id` | `tests/test_requirement_routing_phase0.py` | **Reuse for pre-lock questions.** Gap: this record is not the design's `intake-recorded`/`planning-readiness` receipt pair. |
| Six task profiles and mandatory field registry | `PROFILE_FIELDS` in `scripts/question-orchestrator.py` | `NavigatorHostProtocol.profile_task()` and `profile_fields()` | Navigator-facing API; `tailtrail planning question-context` exposes saved context | `tests/test_question_orchestrator.py` | **Reuse.** All six named profiles exist. Gap: Change Evidence fields from the design are not yet mandatory per material requirement. |
| Question issuance and host observation ingestion | Phase 1A event envelope: `schemas/host-question-flow-event.schema.json` | `IntakePipeline.issue_question()` and `record_observation()` | `NavigatorIntake`/`NavigatorHostProtocol`; question-context projection | `tests/test_intake_pipeline.py`, `tests/test_host_question_flow_event_schema.py` | **Reuse.** Questions and narration observations remain non-authoritative. |
| Candidate extraction, normalization, and no-self-acceptance | Event stream plus candidate records returned by `NavigatorHostProtocol` | `record_direct_candidate()`, `ingest_narration()`, `_candidate()` | `evidence_check()`; packet finalization reads only acceptance events | `tests/test_question_orchestrator.py`, `tests/test_intake_pipeline.py` | **Reuse.** Candidates retain `authority_granted: false`. Gap: candidate persistence is event-based rather than a dedicated versioned candidate registry with all design fields. |
| Acceptance, conflict handling, bounded clarification, user decision | `ACCEPTANCE_STATES`; intake event stream and packet receipt | `NavigatorHostProtocol.evidence_check()` / `clarification_route()`; `IntakePipeline.accept_answer()` | `finalize_packet_view()` rejects unaccepted, contradictory, or unconsumed answers | `tests/test_question_orchestrator.py`, `tests/test_intake_pipeline.py` | **Partial reuse.** Navigator-only acceptance and bounded clarification already exist. Gap: stale and rejected states are not yet a complete, persisted field-state machine tied to source fingerprints. |
| Source freshness, role separation, and scope evidence | `schemas/navigator-scope-evidence.schema.json`, host proposal schemas | `scripts/navigator_scope.py` | Navigator scope route and host-proposal validation | `tests/test_navigator_scope.py`, `tests/test_scope_capture_wiring.py`, `tests/test_scope_answer_mapping.py` | **Reuse.** Inspection and proof paths are distinct from implementation owners; stale/invented proposals reject. Gap: semantic-delta result is not yet the mandatory prerequisite for every material requirement. |
| Semantic delta / already-satisfied disposition | Existing source and scope evidence only; no dedicated Evidence Validation semantic-delta artifact | Existing static path/freshness and behavior-chain evidence in `navigator_scope.py` | Current planning/scoping projections | `tests/test_navigator_scope.py` | **Gap.** Add a typed requested/current/expected/pre-change-scenario artifact and route `satisfied` items away from implementation planning. |
| Requirement-linked proof bindings | `schemas/proof-binding.schema.json`; requirement validation contracts and command registry | `scripts/task-start.py`; `scripts/planning-revision.py` | `scripts/planning-audit.py`; `scripts/execution-evidence.py`; `scripts/closure-recorder.py` | `tests/test_host_question_flow_phase0_artifacts.py`, `tests/test_revision_proof_overlay.py`, `tests/test_execution_evidence.py` | **Partial reuse.** Command/tier/path bindings exist and audit rejects unbound proof. Gap: the canonical binding does not yet consistently include source answer ID, asserted behavior, selector, and evidence fingerprint. |
| Intake packet finalization and source-answer lineage | `schemas/host-question-flow-packet-view.schema.json`; private packet finalization receipt | `IntakePipeline.finalize_packet_view()` | Operational packet builder validates accepted IDs, path/proof/criteria bindings, and unused-answer rejection | `tests/test_intake_pipeline.py`, `tests/test_host_question_flow_phase0_artifacts.py` | **Reuse.** This is the strongest existing basis for a readiness receipt. Gap: no Start route currently requires this artifact before a Host Question Flow plan. |
| Completion policy for validation-only delivery | `.tailtrail/runs/<run>/validation-delivery/delivery-v1.json` | `scripts/completion-policy.py record-delivery` | `completion-report.py`, `closure-recorder.py`, `closure-finalizer.py` | `tests/test_completion_policy.py` | **Reuse.** Current hash-bound validation delivery prevents test-only closure for this run. It is a closure policy, not a pre-Start readiness receipt. |
| Plan audit and projection reconciliation | Planning audit JSON and Start/approved revision projections | `scripts/planning-audit.py`; `scripts/planning-revision.py` | `tailtrail planning audit`, `planning revision-show`, `task-start.py` renderer | `tests/test_start_plan_presentation.py`, `tests/test_public_route_gate.py`, `tests/test_planning_revision.py` | **Partial reuse.** Audit catches unbound proof/path/tier projection gaps. Gap: it does not compare every accepted intake fact against requirements, scope, dependency, proof, and presentation before v1. |
| Full Start artifact and verbose evidence projection | `.tailtrail/runs/<run>/...` plus `session-reports/<run>/start-plan.md` | `scripts/task-start.py` and report projection code | `tailtrail start`, `tailtrail planning show`, `tailtrail planning revision-show` | `tests/test_start_plan_presentation.py`, `tests/test_public_route_gate.py` | **Partial reuse.** Visible full Start report exists. Gap: complete questionnaire/candidate lineage, reconciliation matrix, and evidence history are not yet a single mandatory verbose projection. |
| Closure report after finalizer | `session-reports/<run>/closure-report.md`; finalizer and delivery records | `scripts/closure-finalizer.py` | `tailtrail completion-report`, closure routes | `tests/test_completion_report.py`, `tests/test_completion_policy.py` | **Reuse with current delivery policy.** The no-edit delivery record is now enforced. Gap: future Evidence Validation receipt lineage must flow into the report. |
| Sanitized Meta-Harness feedback | `tailtrail-meta/harness-summary.jsonl` and `tailtrail-meta/harness-summary.schema.json` | `scripts/harness-review.py` | `scripts/meta-harness-analyze.py` / public meta-harness routes | `tests/test_meta_harness.py`, `tests/test_meta_harness_token_feedback.py` | **Reuse current boundary only.** Current allowlist rejects unknown event fields. Gap: no versioned host-question-flow feedback event or analyzer support exists; do not emit one yet. |

## Delivery-Sequence Map

| Design phase | Existing foundations to reuse | First missing deliverable / owner decision |
|---|---|---|
| Phase 0 — Inventory and Ownership | This document, requirement artifact binding, current focused tests | **Complete.** No product behavior change is part of this phase. |
| Phase 1 — Intake State and Privacy | `IntakePipeline`, event redaction, host-question-flow event/state/redaction schemas | Add durable candidate/accepted/stale/conflicting records with source-fingerprint invalidation, retention, deletion, and size-bound enforcement. |
| Phase 2 — Evidence and Semantic Delta | `NavigatorHostProtocol`, `navigator_scope`, packet finalization | Add the typed semantic-delta artifact and deterministic dependency/cross-field validators; preserve `unknown` when evidence cannot prove behavior. |
| Phase 3 — Proof Bindings and Readiness | proof-binding schema, command registry, execution evidence, packet operational bindings | Define the canonical source-answer-linked proof-binding model and mint distinct `intake-recorded` and `planning-readiness` receipts. |
| Phase 4 — Reconciliation and Start Gate | planning audit, revision projection, public Start route | Require a valid readiness receipt; reconcile accepted facts to requirements, scope, dependencies, proof, and normal/verbose projections before v1. |
| Phase 5 — Full Start Artifact | persisted Start report and `session-reports` projection | Add the complete questionnaire, candidate/acceptance lineage, proof bindings, reconciliation matrix, and pending/stale history to verbose mode. |
| Phase 6 — Execution and Closure Artifact | completion policy, closure recorder/finalizer, delivery record | Consume readiness/reconciliation lineage in closure and report missing receipt/validation dependencies precisely. |
| Phase 7 — Optional Meta-Harness Feedback | shared allowlist/schema, sanitizer, analyzer/proposal paths | Version and test a distinct sanitized event contract; preserve the two-distinct-run threshold and advisory-only authority. |

## Acceptance-Criteria Coverage Index

| Design acceptance criteria | Current evidence | Decision |
|---|---|---|
| 1, 16 — already-satisfied and bounded semantic conclusions | Scope freshness/static evidence exists; no semantic-delta artifact | **Gap: Phase 2** |
| 2, 8 — host cannot self-accept; bounded escalation | Navigator-only acceptance and clarification loop | **Reuse, extend durability in Phase 1** |
| 3, 14, 15 — stale evidence and replay/target checks | Scope fingerprints and packet finalization freshness checks | **Partial reuse; unify in readiness gate** |
| 4 — typed dependency cannot disappear | Planning audit/proof checks exist | **Gap: dependency closure validator** |
| 5, 17 — command alone is insufficient proof | Proof-binding schema and planning audit | **Partial reuse; bind assertion/selector/source answer** |
| 6 — raw contract/intake cannot authorize Start | Host contract and intake are validated but Start can still use a raw validated contract | **Gap: Phase 3/4 readiness gate** |
| 7 — accepted fact cannot disappear in canonical plan | Planning audit checks selected projection gaps | **Gap: full receipt-to-plan reconciliation** |
| 9, 10, 12 — normal/verbose Start artifact accuracy | Persisted Start plans and public-route tests | **Partial reuse; add complete evidence projection** |
| 11 — no early Closure; factual incomplete closure | finalizer and completion policy | **Reuse; extend receipt lineage** |
| 13 — redaction/retention | intake redaction and redaction-policy schema | **Partial reuse; formal retention/deletion enforcement remains** |
| 18–22 — Meta-Harness privacy, threshold, no authority | current allowlist/sanitizer/analyzer architecture | **Reuse current safeguard; Phase 7 integration remains a gap** |

## Dependencies That Must Remain Separate

1. `scripts/question-orchestrator.py` may create candidates and ask follow-up
   questions, but it must not become a Planning Lock or scope authority.
2. `scripts/navigator_scope.py` owns path-role and freshness evidence; a
   candidate path cannot be promoted solely because host prose named it.
3. `scripts/planning-audit.py` can find projection omissions, but it must not
   mint accepted answers or a readiness receipt.
4. `scripts/completion-policy.py` proves a no-edit artifact reached closure;
   it must not be reused as a pre-Start authorization mechanism.
5. Meta-Harness consumes sanitized, aggregate data only. It cannot determine
   live per-requirement truth or unblock a Planning Lock.

## Phase 1 Entry Recommendation

Start Phase 1 with one bounded intake-state/privacy slice. Reuse the existing
append-only event pipeline and Navigator acceptance guard; do not create a
second intake store. Its plan should explicitly cover:

1. versioned candidate/accepted/stale/conflicting state records;
2. source-evidence fingerprints and targeted stale invalidation;
3. redaction before persistence, size bounds, retention, and deletion rules;
4. tests proving malformed, secret-bearing, stale, and contradictory input
   never becomes accepted or grants authority; and
5. no change to Start authorization until the later readiness-gate phase.

## Focused Proof for This Inventory

The activated plan binds the following commands; they validate the current
foundation and the no-edit delivery policy, not unimplemented later phases:

```text
python3 -m unittest discover -s tests -p test_host_question_flow_phase0_artifacts.py -v
python3 -m unittest tests.test_host_question_flow_phase0_artifacts tests.test_host_input_contract_schema tests.test_host_question_flow_event_schema tests.test_public_route_gate tests.test_start_plan_presentation tests.test_completion_policy
python3 -m unittest tests.test_completion_policy
```

The inventory must be recorded through `completion-policy.py record-delivery`
for run `start-20261027101501-5f1c2b`. A passing command without that
hash-bound receipt is intentionally insufficient for this validation-only run.
