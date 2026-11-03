# TailTrail Operator Guidance and Reporting Design

**Status:** Proposal for review. This document does not approve or implement a product change.

**Date:** 2026-11-03

## Purpose

Make TailTrail easier for a host and a user to operate without weakening its
approval, scope, proof, or audit rules. The design covers eight related needs:

1. A clear explanation of each blocker and its safe next action.
2. Complete questionnaire and requirement-bound proof before Start Plan v1.
3. Short, evidence-backed checklists for hosts and users.
4. A closure display that distinguishes the final run state from the last
   execution stage.
5. A useful summary of stale learnings, with the full audit detail retained.
6. A responsibility boundary that distinguishes host-operating mistakes from
   TailTrail projection or lifecycle defects.
7. One atomic approval surface for one cohesive outcome, without collapsing
   requirement-specific scope or proof.
8. Lossless, freshness-bound translation from accepted intake facts through
   canonical planning, execution evidence, and closure.

The common failure is a gap between TailTrail's saved state and the guidance
shown to the operator. A safety gate may work correctly while the command or
report gives a generic error, a long JSON object, or a misleading status.
The proposed changes make that state understandable and actionable.

## Eight behavior contracts

The eight needs above map one-to-one to the following contracts. These names
and identifiers are normative throughout this design; later sections provide
their detailed behavior and proof rather than defining additional contracts.

| ID | Contract | Governing decision | Primary owner boundary |
|---|---|---|---|
| C1 | Typed blocker and recovery guidance | Every refusal names its grounded cause, impact, authority requirement, and permitted recovery order. | Shared state resolver and the public command/report renderers. |
| C2 | Pre-v1 intake and proof readiness | Accepted intake facts and requirement-specific proof bindings must reconcile before v1 can become approval-ready. | Intake pipeline, planning-readiness, canonical plan projection, and planning audit. |
| C3 | Evidence-backed operator checklists | Checklist state is computed from canonical evidence; the host cannot mark an item complete. | Start and Completion Report projections over the shared resolver. |
| C4 | Terminal closure and pipeline history | Final run state and historical execution stages are distinct and both remain truthful. | Pipeline history, closure finalizer, and Completion Report. |
| C5 | Bounded learning-maintenance reporting | Normal output summarizes effect and next action while linking to the complete durable inventory. | Learning freshness projection and the Slice 0-confirmed detail artifact. |
| C6 | Host-versus-product responsibility classification | Responsibility follows the first failed boundary and its recorded inputs/outputs, not a convenient label. | Host preflight, public-route evidence, issue log, and Meta Harness review. |
| C7 | Atomic approval and proposal replacement | One cohesive outcome has one exact approval decision; child activation is all-or-none and replacement is append-only. | Planning lock/revision lifecycle and a versioned parent approval receipt. |
| C8 | Canonical state, freshness, and transport consistency | CLI and MCP render one freshness-bound state decision and never mix artifacts from different high-water marks. | Shared resolver over planning, execution, closure, pipeline, and learning artifacts. |

C8 is the foundation for C1, C3, C4, and C5. C2 supplies the validated
planning inputs consumed by C7. C6 is a cross-cutting governance contract and
does not create a second state or evidence store.

## Evidence and relationship to existing designs

This proposal extends, rather than replaces, the [Host–TailTrail Evidence
Validation Contract](TAILTRAIL-HOST-TAILTRAIL-EVIDENCE-VALIDATION-DESIGN.md).
That contract already defines candidate and accepted answers, structured proof
bindings, `planning-readiness`, pre-v1 reconciliation, and normal versus verbose
presentation. The [Host Question Flow
design](TAILTRAIL-HOST-QUESTION-FLOW-DESIGN.md) remains the owner of profile
questions and the host clarification boundary.

| Observed or existing behavior | Evidence | Consequence for this design |
|---|---|---|
| Issue 43 records a global proof command that did not bind to the intended individual requirements. | [Issue log, Section 43](TAILTRAIL-ISSUES-LOG.md) and `scripts/planning-audit.py` proof-binding findings | Reuse the existing proof-binding model; close its public Start-route gap before adding another model. |
| The Issue 45 public `closure finalize` route returned a generic missing-receipt error when all managed receipts were stale. | [Issue log, Section 45](TAILTRAIL-ISSUES-LOG.md) and run `start-20261103055428-bf2e84` | The recent approved run added a focused recovery message in `scripts/closure-finalizer.py`; the broader shared-guidance contract remains proposed. |
| The Issue 45 run needed three plan versions to bind one command to both `unit` and `behaviour`. The final managed command passed both tiers. | `session-reports/start-20261103055428-bf2e84/start-plan.md` and `session-reports/start-20261103055428-bf2e84/closure-report.md` | Pre-v1 projection and reconciliation should catch missing positional bindings before an approvable plan exists. |
| The completed Issue 45 report showed `Overall: complete` and `Active stage: TESTING`. | `scripts/completion-report.py::pipeline_summary` and the saved Issue 45 Completion Report | Display terminal run state separately from the historical execution badge. |
| The same report printed 68 stale-learning IDs inline. | `scripts/completion-report.py` attention rendering and the saved Issue 45 Completion Report | Keep exact IDs in the detailed record, but summarize them in the normal report. |
| An approval checklist and a testing-plan checklist already exist. | `scripts/verbose-reporting.py::approval_checklist` and `scripts/task-start.py::append_testing_plan` | Extend existing projections; do not build an independent checklist database. |

## Verified Phase 4 operating findings and coverage audit

Phase 4 run `start-20261103085553-36f9e7` exercised planning-readiness
reconciliation through the public Start route, approval/activation freshness,
managed proof, Architecture Fitness, and final closure. The run completed, but
its failed-then-passing evidence exposed several operator and product concerns.
This table records whether this design already covered each concern before the
run and adds only the missing contract.

| Verified-live challenge | Prior coverage in this document | Remaining gap and required design response |
|---|---|---|
| Phase 3 validated `semantic_delta` and `dependencies_checked`, but its normalized operational packet did not retain those values. Phase 4 initially rejected the otherwise valid receipt. | Partial. Section 2 required reconciliation of dependencies and accepted facts, but did not require lossless persistence between validation and projection. | Every field used to mint readiness must either be persisted in the immutable operational projection or be represented by an explicit, versioned validation result. A downstream consumer must never be forced to infer that a missing field was previously valid. Compatibility handling for older receipts must be explicit and covered by tests. |
| Questionnaire requirement identity and the independently generated canonical requirement identity did not always align. A single accepted requirement could encounter several heuristic canonical rows. | Partial. Section 2 required a requirement UID and rejected unrelated attribution, but did not define deterministic identity reconciliation. | Reconcile by saved identity first, then exact normalized statement and requirement-bound scope/proof evidence. A validated single requirement may replace heuristic clause expansion in the canonical projection. Multiple requirements that cannot be mapped uniquely remain blocked behind a bounded clarification; ordinal or lexical guessing must not grant authority. |
| An absent host-contract fingerprint was converted to the literal string `"None"`, producing a false mismatch during Start persistence. | Missing. The design required fingerprint freshness but did not define optional-value semantics. | Preserve absence as `null`/not-recorded. Compare a host-contract fingerprint only when a non-empty fingerprint is actually present and expected. Never stringify a missing identifier before validation. Add absent, present-and-matching, and present-and-mismatching public-route cases. |
| Managed proof first failed while the reconciliation defects were corrected, then passed on compatible retries. | Covered in principle by append-only history and verbose unsuccessful-attempt retention, but the Phase 4 run supplied concrete proof. | Keep every attempt, select the newest compatible result for the approved proof binding, and render earlier failures as superseded rather than erased. A later pass must not replace a failure from a different plan, command, tier, scenario, source state, or requirement. |
| Requirement tests passed, but closure correctly remained incomplete until the selected Architecture Fitness assessment was recorded. | Partial. The design separated proof from closure and required evidence-backed checklists, but did not make selected-harness readiness explicit enough. | Before finalization, show every selected harness, its required artifact, current status, and exact permitted next action. Passing requirement tests do not imply closure readiness when Architecture, Behaviour, Maintainability, or another selected control still lacks evidence. |
| The worktree already contained substantial earlier changes, so aggregate Git statistics were not a reliable measure of this slice. | Missing here, although the Playbook and Ground Rules already require an explicit shared baseline and reviewed scope. | Normal reports must use approved paths, source-edit receipts, and path fingerprints to describe the current run. They may show aggregate worktree status as context, but must not attribute unrelated dirty-worktree changes to this run. The host must establish or explicitly accept the baseline before persistence. |
| Recording the same source-edit metadata after a later edit reused the earlier receipt because the event identity did not include current file content. | Missing. Existing freshness rules focused on managed proof and closure projections, not source-edit receipt identity. | A source-edit receipt must bind the approved run/plan, requirement UID, changed path, and current content fingerprint (or an equivalent immutable source-state fingerprint). A later content change creates a new event and invalidates dependent proof/checklist/closure projections; metadata equality alone must not reuse the prior receipt. History remains append-only. |
| The Completion Report again printed 68 stale-learning IDs inline. | Fully covered by Section 5. | Do not add a second learning model. Implement Section 5: bounded count/effect/next action in normal mode, with all IDs retained in the existing verbose or canonical artifact. |

### Phase 4 operator rule

When a managed proof fails during implementation, classify the first failed
boundary before changing the plan. A dropped accepted field, false fingerprint
mismatch, or misprojected requirement identity is a TailTrail reconciliation
defect; a test assertion that exposes incorrect approved behavior is an
implementation/proof failure; a selected harness with no assessment is an
evidence-readiness gap. Preserve the failed attempt, correct only the owning
boundary, record any later source change as fresh source evidence, and rerun
the exact approved proof. Do not delete or relabel the earlier attempt.

The issue log still labels Issue 45 open. The approved Issue 45 run completed
with passing public-route proof, but this document does not infer that every
reporting surface now uses the new recovery guidance. Before implementing the
shared guidance, inventory each public route and update issue status from
current evidence. Similarly, verify Issue 44's current public behavior before
treating its older issue-log entry as an active defect.

## Responsibility findings from the Phase 3 combined-plan run

Run `start-20261103074542-c5f97c` exposed a useful distinction between
operator mistakes, TailTrail product defects, and mixed failures. Better host
knowledge can reduce retries, but it must not be used to relabel lost saved
input or misleading canonical output as an operator problem.

| Observed issue | Primary responsibility | Preventable through better host operation? | Required response |
|---|---|---|---|
| The work was initially presented as three independent plans even though the user requested one approval decision. | Mixed | Partly. The host should decide the approval topology before persistence and use one multi-requirement run for one cohesive outcome. TailTrail still lacks a first-class pre-approval parent/batch object with atomic child activation. | Add the host preflight rule now; design an atomic single-approval model that retains requirement-specific scope and proof internally. |
| Hand-built requirement interpretation used the wrong artifact-evidence key, included quoted hyphenated literals as semantic intent terms, and left an outcome/constraint clause unbound. | Host | Yes. The official builder or schema validator should have been used before Start. TailTrail correctly failed closed before creating a run. | Record the exact interpretation rules in operator guidance; keep the strict validator. Improve correction examples only where they remain unclear. |
| The accepted host contract carried a runnable combined proof command, but Start Plan v1 rendered no requirement-linked proof commands. | TailTrail | No. A knowledgeable host can repair this with `planning revise`, but that is a workaround for lost projection, not the intended flow. | Before v1, translate validated proof input into explicit per-requirement bindings or ask a bounded question. An incomplete projection must not become approval-ready. |
| CLI and MCP behavior implied `integration` proof after the host supplied only unit, contract, and behaviour tiers. | Mixed | Partly. The host should classify public-route crossings before Start; TailTrail should reconcile inferred and declared tiers before v1 rather than discover the mismatch only in the mandatory audit. | Add a tier-completeness preflight and retain the audit as a defense-in-depth check. |
| Every requirement displayed the full inferred inspection list and all proof paths even though each had one primary owner and proof command. | TailTrail | No. The data is safe but the normal projection is noisy and obscures the review decision. | Render primary requirement-bound owner/proof rows in normal mode; retain complete inferred paths in verbose and machine-readable artifacts. |
| Token estimation remained unavailable because scope was labelled `ambiguous` after all three requirement-to-owner and proof mappings were resolved. | TailTrail | No. The estimate is non-authoritative, but the reason is misleading. | Compute estimate readiness from the effective reviewed scope, or report the exact remaining ambiguity instead of a generic state. |
| `tailtrail stop` detached the three earlier plans but preserved their canonical `awaiting-approval` state. | TailTrail lifecycle/product design | The host can describe the state accurately but cannot mark those plans superseded through `stop`. | Add an append-only `superseded-by` relation or atomic replacement operation. Never make `stop` silently destructive. |
| The host reformatted the latest Start Plan instead of returning the exact canonical pending-revision rendering. | Host | Yes. This violated the canonical presentation boundary even though the rewritten plan was easier to read. | Require verbatim latest-plan output. Improve TailTrail's own normal renderer rather than repairing it in host prose. |

### Decision rule

Classify the first failed boundary, not the most convenient owner:

- **Host issue:** TailTrail received malformed, incomplete, contradictory, or
  incorrectly classified input and rejected or rendered that same input
  faithfully.
- **TailTrail issue:** validated input was lost, misprojected, repeated
  misleadingly, or could not be represented through the supported lifecycle.
- **Mixed issue:** the host omitted information that TailTrail could also have
  derived or requested before persistence. Fix the host preflight and the
  product reconciliation; do not choose only one.

The durable evidence for this classification should name the received host
contract, canonical requirement/proof projection, audit finding, and public
rendering. A retry that succeeds after manually repeating already-supplied
information is evidence of a projection gap, not proof that the original host
contract was incomplete.

## Host-side prevention contract

Before creating a Start Plan, the host must:

1. Decide whether the requested outcome requires one approval surface or
   several independently approvable outcomes. One cohesive outcome should be
   represented by one multi-requirement plan when TailTrail can preserve
   separate requirement owners and proofs honestly.
2. Validate hand-built interpretation input with the official builder. Artifact
   evidence uses `input_id`; artifact-grounded clauses use `source_input_id`.
   Do not repeat quoted literals as semantic intent terms, and ensure every
   outcome/constraint clause is referenced by a requirement.
3. Bind each requirement to its implementation owner, proof path, exact
   command, tiers, asserted behavior, and source answer. A global command in a
   host contract is not enough unless the canonical requirement rows retain the
   intended bindings.
4. Include integration proof when the asserted behavior crosses public CLI,
   MCP, API, process, or persistence boundaries.
5. Run the mandatory audit, revise the same run until clean, and inspect the
   pending-revision rendering. Show only that latest canonical rendering,
   verbatim; never replace it with a hand-normalized plan.
6. Describe lifecycle operations precisely. `stop` detaches routing and
   preserves the canonical run; it does not reject, delete, or supersede the
   plan.

These rules reduce host-caused retries. They do not excuse TailTrail from
retaining validated input or producing an accurate v1.

### Governing rule for one approval across several owners

Separate owner-focused runs remain the default when outcomes are independently
approvable or when combining them would weaken scope or proof. One approval is
permitted only for one cohesive user outcome whose requirements can retain
separate owner, inspection, proof, and preservation boundaries.

If the outcome fits in one multi-requirement plan, that plan is the approval
surface. If TailTrail's write-ownership policy requires several child runs,
the product must mint one versioned `batch-approval` receipt before any child
activates. The receipt binds the exact:

- parent outcome and request mode;
- ordered child run and requirement IDs;
- canonical plan and requirement-set fingerprints;
- scope-decision and approved-anchor fingerprints;
- proof-contract, command, tier, and scenario fingerprints; and
- positive, negative, and preservation criteria for every child.

Approval validates the complete set as one transaction. Activation is
all-or-none: a missing, stale, rejected, or mismatched child leaves every child
awaiting activation. A later child revision invalidates the parent receipt and
requires a new versioned approval; it never partially carries the old decision
forward. The user interface may collect one gesture, but the durable receipt is
the authority. Append-only child events link back to that receipt, and a
replacement records explicit `superseded-by` lineage without deleting the
older proposal. Host-side batching without this receipt is presentation
convenience only and must not be described as atomic approval.

## TailTrail product fixes from the same run

The contract map above owns the decisions; the delivery table below owns
sequencing and exit gates. This compact priority map retains the verified
Phase 3 findings without creating a second implementation plan:

| Priority | Product correction | Contract / delivery slice |
|---|---|---|
| P0 | Project validated proof and inferred tiers into explicit requirement bindings before v1; ask a bounded question when attribution is incomplete. | C2 and C8 / Slice 2 |
| P1 | Bind one approval to the complete fingerprinted child set with all-or-none activation. | C7 / Slice 2A |
| P1 | Preserve replaced pending proposals with explicit `superseded-by` lineage; keep `stop` non-destructive. | C7 / Slice 2A |
| P1 | Render each requirement's owner, inspection inputs, proof paths, command, and tiers once in normal mode. | C3 / Slice 3 |
| P2 | Estimate from effective reviewed scope and name the exact unresolved row when unavailable. | C3 / Slice 3 |

Regression coverage must include: one cohesive three-owner plan with one
approval decision; distinct commands per requirement; a global command that
cannot be attributed; inferred integration beyond the declared boundary;
verbatim pending-revision rendering; atomic replacement lineage; and a token
estimate whose availability follows effective scope rather than raw Navigator
ambiguity.

## Governance updates from verified-live learning

The run produced reusable guidance, not just design ideas:

- **Playbook:** add a condition-to-trick entry for one cohesive approval across
  several owners, exact interpretation field distinctions, pre-v1
  requirement-specific proof checks, public-boundary tier classification,
  verbatim latest-revision display, and truthful `stop` semantics.
- **Ground rules:** make approval topology explicit before persistence; require
  requirement-specific proof projection; prohibit host normalization of a
  canonical plan; require integration-tier review for public-route crossings;
  and prohibit describing a detached run as superseded or deleted.
- **Issue log:** record a product issue only after current public-route proof
  confirms validated input was lost or the lifecycle cannot represent the
  requested state. Host schema mistakes remain learning entries unless the
  error lacks actionable correction guidance.

The corresponding Playbook and Ground Rules changes are part of this
documentation update. Product implementation remains unapproved and belongs
to the delivery slices below.

## Product boundaries

- TailTrail's canonical requirements, approved anchor, intake records, proof
  bindings, evidence stream, and closure result remain the sources of truth.
- Presentation never creates approval, scope ownership, accepted answers, or
  trusted proof. A displayed command is advice until the relevant authority
  and preconditions are satisfied.
- The host supplies observations and candidates. TailTrail validates them and
  computes completeness. A host-provided empty question list is not a
  completion receipt.
- Raw narration cannot become a requirement or editable path by appearing in
  a checklist or error message.
- Missing, stale, conflicting, or unverified evidence remains visible and
  blocks the relevant transition.
- Normal views are concise. Verbose and machine-readable views preserve every
  material fact, including failed and superseded attempts.
- CLI and MCP routes must use the same decision and rendering inputs. Human
  wording may differ by transport, but blocker codes, authority, and next
  actions must agree.
- Historical runs remain readable. New schema fields are additive and have
  explicit `unknown`/`not-recorded` behavior for older artifacts.

## End-to-end operator experience

```text
Host observation and user request
    ↓
TailTrail profile questions and candidate answers
    ↓
Validated answers, scoped roles, and proof bindings
    ↓
Planning readiness and pre-v1 reconciliation
    ↓
Start Plan + checklist + any blocker guidance
    ↓ explicit approval and activation
Execution events, stage transitions, managed proof
    ↓
Closure record and finalizer
    ↓
Completion Report: terminal state, last execution stage,
proof history, maintenance summary, and full-detail links
```

At each transition, one state resolver identifies what is complete, what is
blocked, why, and which action is permitted next. The reports render that
resolver's result rather than each inventing recovery wording.

### Shared resolver state contract

The resolver is a deterministic read model, not a mutable authority store. It
reads the canonical artifacts for the requested run in dependency order:

1. accepted intake answers, structured proof bindings, and the current
   planning-readiness receipt;
2. the canonical plan selector: valid pending revision when explicitly under
   review, otherwise the active approved revision or original Start report;
3. the latest approved scope/anchor version and its requirement, path-role,
   and proof-contract fingerprints;
4. the append-only run ledger, source-edit events, managed execution evidence,
   and pipeline transition history;
5. the newest compatible closure record and finalizer projection; and
6. the learning-freshness projection and the Slice 0-confirmed durable detail
   artifact used by C5.

Every resolver result records the selected artifact IDs, schema versions,
content fingerprints, event-stream high-water marks, and the resulting
`state_fingerprint`. Compatibility is checked per approved proof binding and
source state; a newer event is not automatically compatible merely because it
has a later timestamp.

CLI and MCP call this same resolver and render the same typed result. A
renderer must not reread individual artifacts and reconstruct a different
decision. Immediately before display or persistence, the caller rechecks the
selected high-water marks and fingerprints. If any input changed, it either
recomputes from a fresh snapshot or fails with
`state-changed-during-projection`; it must never combine an old decision with
new evidence. Report regeneration after new evidence therefore produces a new
projection fingerprint while append-only history remains unchanged.

## 1. Blocker and recovery guidance

### Problem

TailTrail may return a low-level validation error even when it knows the
actionable cause. Issue 45 exposed this: the system correctly rejected a
receipt after a source edit, but `closure finalize` said only that no
requirement-linked receipt remained. That invited the wrong repair, such as
changing a valid proof contract.

### Proposed contract

Use a versioned, typed guidance result generated from current saved state.
It is a projection, not a separate authority store. A minimum item contains:

```text
code                 stable machine-readable blocker code
category             TailTrail defect | plan/scope gap |
                     implementation/proof failure | environment/dependency
severity             blocking | attention | informational
subject              run, requirement, field, proof binding, path, or receipt
cause                plain-language reason grounded in named evidence
impact               transition or claim that remains unavailable
source_references    artifact and event IDs supporting the conclusion
state_fingerprint    version/fingerprint of the inputs used for this advice
recovery_actions     ordered actions with required authority and preconditions
```

A recovery action can be an exact CLI/MCP operation, a question to answer, or
an instruction to revise the current plan. It must specify whether it needs
user approval, an activated run, or a fresh receipt. A copyable command is
rendered only when TailTrail has the exact run ID, approved command, target,
and required arguments. Otherwise the output names the missing input and
asks for it. Never fill placeholders with guessed paths or commands.

When several blockers exist, show the earliest dependency that the operator
can resolve and list the others in priority order. For example, an unapproved
proof amendment precedes a managed proof rerun. A command that is still
unauthorized must not appear as a ready-to-execute step.

Example for the Issue 45 state:

```text
Closure blocked: managed proof is stale
Requirement: REQ-01
Evidence: event 12 was rejected as source-changed-after-proof
Impact: closure cannot select event 12 as current proof

Next actions:
1. Confirm that the latest source edit has a recorded source-edit receipt.
2. Rerun the exact approved managed command for REQ-01.
3. Record closure for this run.
4. Finalize closure, then read the Completion Report.
```

The actual output includes concrete IDs and the approved command only when
they exist in the run's authority records. If the source-edit receipt already
exists, step 1 is marked complete rather than asking the operator to record
it again.

### Integration and proof

Reuse existing `next_actions`, planning-audit findings, closure guidance, and
current-evidence projections. Add the typed resolver at their shared state
boundary. Check planning failure, rejected revision, missing proof,
source-changed-after-proof, failed managed proof, missing closure record, and
environment failure through public CLI and MCP routes. Every message must
lead to one of: answer a specific question, revise the same plan, obtain
approval, rerun an approved command, record closure, or report a product
defect. Failure never becomes a pass through better wording.

## 2. Questionnaire and proof checks before v1

### Problem

Information supplied by the host can be recorded globally or in prose while
the generated requirement row still lacks a usable proof binding. The host
then sees revisions v2/v3 for a defect that existed before v1 was rendered.
The issue is a missing translation or reconciliation step, not a reason to
trust host assertions more broadly.

### Reuse the existing intake model

The [evidence validation contract](TAILTRAIL-HOST-TAILTRAIL-EVIDENCE-VALIDATION-DESIGN.md#4-structured-proof-bindings)
already specifies profile-owned mandatory fields, candidate-answer states,
source lineage, `intake-recorded`, `planning-readiness`, and pre-v1
reconciliation. This work should finish their public-route integration.

For Host Question Flow tasks, the route is:

```text
host observations → candidate answers → TailTrail validation
→ accepted answers + Navigator scope evidence + proof bindings
→ planning-readiness receipt → canonical projection comparison
→ Start Plan v1
```

Each accepted proof binding must identify the requirement UID, proof path,
exact approved or proposed command, tier, asserted behavior/scenario, source
answer ID, and evidence fingerprint. Where supported, include a test selector
or case identity. The binding must remain separate from path ownership: a
test file is proof scope, not an implementation owner merely because it
appears in a binding.

Before v1 is eligible for approval, compare accepted facts with the
requirement statement and criteria, preservation rules, path roles,
validation contract, command registry, normal Start Plan, and verbose Start
Plan. Fail with a typed question if any required fact is missing or appears
under an unrelated requirement. A passing global command must not be
attributed to every requirement by default.

### Structural readiness versus executed proof

Planning readiness says the proof *contract* is complete. It does not say the
code or tests have passed. The following states are distinct and must not be
collapsed:

| Proof state | Required facts | What may be approved | What remains blocked |
|---|---|---|---|
| `unresolved` | Path, command, tier, scenario/asserted behavior, requirement attribution, or source answer is missing or conflicting. | Nothing that relies on this proof. | Plan approval and activation. |
| `planned; collection pending` | The proposed path is role-classified as proof-only, new-file due diligence is complete, creation authority is explicit, and the exact command, selector if applicable, tiers, asserted behavior, requirement UID, source answer, and preservation boundary are bound. | The implementation plan may authorize creation of this exact proof file and later execution of its exact command. | Claims that the file exists, collects, executes, or passes; closure remains blocked. |
| `collected; execution pending` | The file exists in approved proof scope and the exact command imports and collects at least one intended test or scenario. | Managed execution of the approved binding. | Pass/fail claims and closure evidence. |
| `executed; current` | Compatible managed evidence exists for the approved plan, source state, command, tier, scenario, and requirement. | The proof may satisfy its requirement according to the recorded outcome. | Any unrelated requirement, command, tier, or changed source state. |

For an existing proof path, validate command viability before approval when
policy requires it. For a proposed test, approval authorizes a bounded future
creation and proof attempt; it is not evidence. After creation, validate
non-zero collection and run the exact approved command through managed
evidence before closure.

The unresolved state still blocks approval. The planned state is eligible only
because every structural proof decision is already explicit and reviewable. If
the workflow cannot preserve that distinction without treating a proposed path
as executable, keep the question open and repair the model before approval.

### Compatibility and proof

Apply the new Start gate to the Host Question Flow routes identified in the
existing contract. Inventory legacy Starts, documentation-only work, and
validation-only work before expanding it to all modes. Add public Start-route
cases for one bound requirement, multiple requirements with different
commands, an unbound global command, an unrelated requirement, a proposed
new test path, a stale answer, and an accepted answer omitted from the
rendered plan. No incomplete v1 may be labelled ready for approval.

## 3. Checklist-based host views

### Problem

Large command payloads contain the right facts but force a host to search
through JSON and prose for the next gate. Existing approval and testing
checklists cover only parts of the lifecycle and can show static empty boxes.
For a larger task, a flat list hides which requirement or phase is blocked.

### Proposed model

Extend the existing normal Start and Completion Report projections with a
checklist assembled from canonical state. Each item has a stable ID, parent
item for larger tasks, state, source references, and the fingerprint of the
facts that establish that state. Suggested states are `complete`, `pending`,
`blocked`, `stale`, and `not-applicable`. `not-applicable` is a recorded
decision with a reason; it cannot be used to hide missing mandatory fields.

```text
Phase 3A.2 — Planning
[✓] REQ-01 accepted — answer ans-21
[✓] Owner scope confirmed — scope decision sc-09
[✓] Unit proof bound — proof binding pb-03
[ ] Behaviour proof binding — question Q-14; approval blocked
[ ] User approval — available after Q-14 is resolved

Execution
[✓] Source-edit evidence recorded — event 7
[~] Managed proof stale — event 9; rerun approved command
[ ] Closure record — waits for current proof
```

The host cannot set a check to complete. It may supply a candidate answer or
perform an approved action; TailTrail recomputes the item from evidence.
When an answer, plan, scope, command, or source state changes, affected items
become stale or pending. The host sees one top-level summary for a small task
and nested requirement/phase checklists for a large one.

The normal view should show the current decision and next useful action. The
verbose Start/Closure artifacts retain the full questionnaire, candidates,
accepted answers, proof bindings, revision history, unsuccessful attempts,
and exact raw references. JSON remains available for machines. The normal
view never truncates a required reason into silence.

### Proof

Test a checklist before and after answering a question, revising a plan,
approving it, editing source, failing proof, passing a retry, and finalizing
closure. Verify that CLI and MCP render the same item states from the same
artifact. A deliberately stale receipt must untick the affected proof item.

## 4. Closure state and pipeline history

### Problem

The Issue 45 Completion Report correctly said the run was complete while its
pipeline section still said `Active stage: TESTING`. The stage is historical
execution information, but its label reads like unfinished work.

### Proposed projection

Represent two separate concepts in the report:

```text
Run lifecycle: CLOSED — COMPLETE
Last execution stage: TESTING (test-badge)
Stage history: IMPLEMENTATION → TESTING
Unvisited: INFRA (informational; no gate was claimed for it)
```

`CLOSED — COMPLETE` comes only from a successfully persisted finalizer and
current Completion Report decision. An incomplete, failed, stopped, or
awaiting-approval run must display its actual state. Closure is a terminal
run state in this view; it does not rewrite the stage history, count as a
pipeline handoff, or mark `INFRA` visited.

For every visited execution cycle, show the handoff time, stage, approved
paths that were used or affected, proof events, and result. Where exact file
attribution is unavailable, say `not recorded`; do not infer it from a later
Git diff. If implementation and testing alternate, preserve the full
sequence rather than collapsing repeated stages. A small text diagram is
sufficient for normal reports; the verbose record retains every transition
and event ID.

### Proof

Cover successful closure from TESTING, incomplete closure from TESTING,
stopped runs, unvisited INFRA, and an IMPLEMENTATION → TESTING →
IMPLEMENTATION → TESTING cycle. Confirm the terminal state changes only
after finalization and that stage-write controls continue to use the real
execution badge.

## 5. Stale-learning maintenance summary

### Problem

Issue 45's otherwise successful Completion Report listed 68 learning IDs
inside `What needs attention`. The full list is useful for an audit but
obscures the task's outcome and makes a maintenance observation look like a
closure failure.

### Proposed presentation

The normal report gives the count, effect on this run, and one safe next
action. It groups learnings by reason only when the saved learning checker
actually records reliable reason codes.

```text
Learning maintenance: 68 items may need review.
Effect on this run: none recorded.
Reason breakdown: unavailable in current evidence.
Next action: inspect the full learning inventory; refresh requires its own
reviewed maintenance action.
```

The full IDs, current and saved fingerprints, reason codes if known, and
source references remain in the existing verbose Closure Report or the
canonical JSON. Slice 0 must select exactly one of those existing artifacts as
the durable detail owner, verify that it retains every ID and known reason,
and record a stable link contract for normal reports. This owner decision is a
Slice 0 exit criterion, not an implementation-time choice. Add a separate
maintenance document only if neither existing artifact can serve that purpose
without losing detail. Until the owner is confirmed, the normal report may
show a grounded count and effect but must say that the complete-detail link is
unavailable. Never invent a reason distribution or silently refresh, discard,
or rewrite learnings as a side effect of a successful task closure.

If stale learnings actually affect the current run's proof, scope, or policy,
the report must say so and surface the real blocker. A large count alone is
not evidence that closure is invalid.

### Proof

Cover zero items, many items without reason codes, many items with recorded
reason codes, and a learning that truly blocks a current decision. The normal
report stays bounded; the detailed artifact contains every original ID.

## Delivery slices and ownership checks

These are proposed slices, not approved implementation runs. Before each
slice, inspect the current source, callers, public routes, schemas, tests,
and any existing owner. Split owners where TailTrail's scope policy requires
one implementation owner per run.

| Slice | Contracts | Outcome | Dependency | Owner confirmation | Exit gate |
|---|---|---|---|---|---|
| 0. Current-state inventory | C1–C8 | Record which public routes already satisfy each contract, including the current Issue 44 and Issue 45 behavior. | None. | Inspect `scripts/tailtrail.py`, `scripts/task-start.py`, `scripts/intake_pipeline.py`, `scripts/planning-audit.py`, `scripts/planning-revision.py`, `scripts/closure-finalizer.py`, and `scripts/completion-report.py`; identify the existing owner before planning each later slice. | Evidence-backed reuse/gap decision per contract; Issue 44/45 status recommendation; and one confirmed durable learning-detail owner with a tested normal-report link shape. |
| 1. Shared resolver and guidance rules | C1, C6, C8 | One freshness-bound resolver and typed blocker/recovery projection with stable codes, authority prerequisites, source references, high-water marks, and content-bound source-edit identity. | Slice 0. | Confirm the existing planning, evidence, pipeline, closure, and learning projection owners; do not create a parallel mutable state store. | CLI and MCP return the same decision fingerprint; public failures retain their refusal and give accurate next actions; a later edit invalidates dependent projections. |
| 2. Pre-v1 readiness integration | C2, C8 | Consume accepted answers and proof bindings at the public Start route; preserve validated semantic/dependency fields; reconcile identity, attribution, optional fingerprints, proposed-proof state, and inferred tiers before v1. | Slices 0 and 1. | Intake pipeline, Start builder, schemas, canonical plan selector, and planning audit. | Missing, wrongly attributed, tier-incomplete, falsely mismatched, lossy, or structurally unresolved facts cannot yield an approvable v1; proposed tests retain their explicit pending state. |
| 2A. Atomic approval topology and replacement | C7 | Bind one cohesive approval to the exact fingerprinted child set, preserve each scope/proof boundary, and record append-only replacement lineage. | Slices 1 and 2. | Planning lock/revision lifecycle, versioned parent approval receipt, approved anchors, and session control. | Activation is all-or-none; any child mismatch invalidates the parent receipt; replaced proposals remain auditable and visibly historical. |
| 3. Checklists and role-aware normal rendering | C3, C8 | Derive small and nested checklists from the shared resolver; show each requirement's primary owner/proof once and compute token-estimate availability from effective reviewed scope. | Slices 1 and 2; consume 2A status when present. | `scripts/verbose-reporting.py`, `scripts/task-start.py`, and `scripts/completion-report.py`. | Every item has an evidence-backed state, CLI/MCP agree, normal output is bounded, and unavailable estimates name the exact unresolved input. |
| 4. Terminal closure display | C4, C8 | Show final run state and full execution-cycle history separately, including selected-harness readiness before finalization. | Slice 1. | Pipeline lock/history, finalizer, completion renderer, and harness assessments. | A completed run is visually closed; historical badges remain truthful; a missing selected-harness artifact names the exact action. |
| 5. Learning summary | C5, C8 | Replace the normal inline ID dump with a grounded count, effect, next action, and link to the Slice 0-confirmed complete detail owner. | Slices 0 and 1. | Learning freshness projection, completion renderer, and the confirmed verbose/canonical detail artifact. | Normal output is bounded, the detail link resolves, and every original ID and known reason remains available. |

Slice 0 is essential: some apparent gaps already have partial fixes, and a
new implementation plan must target the first missing public transition.
The dependency column is authoritative for sequencing. Shared schema work may
be reused, but each slice keeps independent public-route proof. Slices 3–5
change presentation and must not change readiness or closure decisions.

## Acceptance criteria across the design

1. A blocked public command names its grounded cause, impact, affected IDs,
   and permitted recovery order; no advice grants missing authority.
2. An incomplete or stale Host Question Flow intake cannot create an
   approvable Start Plan v1. A structurally complete proof contract does not
   claim that the proof has executed or passed.
3. One command bound to REQ-01 is never credited to REQ-02 without an
   explicit validated binding. Proof paths are never promoted to editable
   ownership by presentation.
4. Normal checklists agree with canonical state and invalidate on relevant
   changes; verbose artifacts and JSON preserve every material item.
5. Successful finalization displays a closed run with its last real stage
   and complete transition history. An incomplete finalizer cannot do so.
6. The normal Completion Report does not dump dozens of learning IDs, while
   a durable detailed artifact still exposes every ID and known reason.
7. Public CLI and MCP tests cover both successful and negative paths,
   including legacy artifacts and report regeneration after new evidence.
8. No slice weakens explicit user approval, planning audit, scope roles,
   write-time guards, evidence freshness, or the append-only audit history.
9. One cohesive outcome can present one exact approval decision while retaining
   separate requirement owners and proof bindings; replacement records make
   older proposals visibly historical without deleting them.
10. Normal Start output does not repeat unrelated inferred paths under every
    requirement, and token-estimate unavailability identifies a concrete
    unresolved row rather than generic ambiguity.
11. Every readiness field relied on by reconciliation is present in the saved
    projection or represented by explicit versioned validation evidence;
    legacy fallback behavior is deterministic and tested.
12. Requirement reconciliation never grants authority from ambiguous identity.
    Saved UID, exact statement, and requirement-bound scope/proof evidence are
    used deterministically; unresolved multi-requirement mapping asks a bounded
    question before v1.
13. Missing optional fingerprints remain absent rather than becoming textual
    sentinel values, while real mismatches still fail before authority writes.
14. Editing an already-receipted path produces a new content-bound source-edit
    event and invalidates dependent proof, checklist, and closure projections;
    the prior receipt remains visible only as history.
15. A versioned parent approval binds every child ID and plan, scope, anchor,
    proof, command, tier, scenario, and criteria fingerprint. No child
    activates unless the complete set remains valid; any revision requires a
    new parent receipt.
16. A proposed test may be approved only in the explicit
    `planned; collection pending` state with a complete structural binding.
    The report never claims collection or execution until those events exist,
    and closure remains blocked until compatible managed proof is current.
17. Every CLI and MCP decision records one resolver state fingerprint and its
    selected artifact high-water marks. A change between resolution and display
    forces recomputation or a typed stale-projection refusal.
18. Slice 0 names one durable learning-detail owner and proves its normal-report
    link while retaining every original learning ID and known reason.

## Risks and decisions for review

- **Scope of the pre-v1 gate:** The existing evidence-validation design names
  Host Question Flow work. Expanding it to every TailTrail mode requires a
  separate compatibility decision and migration plan.
- **Proposed new proof files:** The proof contract must identify them before
  approval while execution and collection remain pending. The four-state table
  above is the required behavior; Slice 0 must confirm whether the existing
  new-file and proof-update rules can represent it without claiming evidence.
- **Guidance ownership:** Reuse existing next-action and closure projections;
  avoid a new mutable guidance store that could disagree with run state.
- **Learning detail owner:** Prefer the existing verbose Closure Report or
  canonical JSON. Slice 0 must choose one, verify completeness, and define the
  normal-report link before Slice 5 begins. Add a new document only if neither
  existing artifact can meet the audit and navigation requirement.
- **Historic pipeline attribution:** Older handoff records may not name files
  or achievements. Display `not recorded` rather than backfilling guesses.
- **Legacy readiness receipts:** Older operational packets may omit fields that
  their minting validator required but did not persist. Compatibility must be
  version-gated and based on the historical validator contract, never a broad
  default that lets malformed new receipts pass.
- **Source-edit event compatibility:** Adding content fingerprints changes
  receipt identity and current-evidence selection. Preserve old receipts as
  historical evidence, label fingerprint-less events as legacy, and require a
  fresh content-bound event after any new edit before closure.
- **Issue-log freshness:** Issue 44 and Issue 45 descriptions may lag current
  code. Focused current tests now show pending-revision carry-forward and stale
  managed-evidence recovery passing, but those tests alone do not prove every
  public route. Slice 0 updates issue status only after completing the route
  inventory.
- **Atomic approval semantics:** Resolved for this design: use one versioned
  parent `batch-approval` receipt bound to the exact child requirement IDs,
  plan/scope/anchor fingerprints, proof contracts, commands, tiers, scenarios,
  and criteria. Activation is all-or-none; UI collection of individual
  approvals is not a substitute authority model.
- **Resolver race handling:** A projection that changes during resolution and
  rendering must be recomputed or rejected with
  `state-changed-during-projection`; transport-specific caching must not return
  a decision from an older high-water mark.
- **Replacement semantics:** `stop` remains non-destructive routing control.
  Supersession needs its own explicit authority and append-only lineage so a
  replacement cannot silently revoke an unrelated approved or active run.

## Non-goals

- Automatically approving plans, accepting host answers, executing recovery
  commands, or refreshing learnings.
- Replacing the Host Question Flow, evidence-validation, or AIDLC contracts.
- Removing JSON, receipts, failed attempts, or verbose reports to shorten the
  normal view.
- Claiming a new test file has already collected or passed before it exists.

## Review request

Please review the eight named behavior contracts, especially pre-v1 proof/tier
reconciliation, the versioned parent approval receipt, proposed-test state
transitions, shared-resolver freshness, and the Slice 0 learning-detail owner.
Slice 0 must then confirm the current public behavior and owner boundaries
before any implementation plan is created.
