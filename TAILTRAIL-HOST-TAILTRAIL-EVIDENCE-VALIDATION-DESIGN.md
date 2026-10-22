# Host–TailTrail Evidence Validation Contract

## Purpose

Prevent TailTrail from producing a plan when either of these conditions is
true:

1. the requested behavior is already implemented at the relevant boundary; or
2. a material requirement, dependency, proof obligation, or preservation rule
   has been omitted from the canonical plan.

This document defines the shared contract between the host agent and
TailTrail. It is intentionally evidence-first: a host may investigate and
propose candidate answers, but TailTrail decides whether the evidence is
sufficient to accept them, calculate intake completeness, and allow a primary
Start Plan.

This is a design document. It does not itself authorize an implementation
change or replace the existing Host Question Flow plan.

## The Problem

Repeated work identified two connected failure classes.

### A. Existing implementation is missed

TailTrail has produced otherwise coherent plans for behavior that already
exists. The Phase 2 profile-field registry is the clearest recent example:
the registry, access function, and question planner were already present, but
a plan was approved and activated before read-only source inspection proved
that no behavioral delta remained.

This is recorded in `TAILTRAIL-ISSUES-LOG.md` Issue 21.7. It is a general
planning defect, not only a correction-work defect.

### B. Material requirements and dependencies are missed

TailTrail has accepted host findings or proof declarations but failed to carry
them into one or more of requirements, approved scope, typed schemas, proof
bindings, or the rendered plan. Candidate-answer durability exposed a concrete
example: changing an emitted `answer-recorded` payload requires both pipeline
logic and the schema that rejects undeclared properties, plus assertion-level
tests. A plan scoped only the pipeline and treated existing tests as sufficient
proof.

This is recorded in Issues 28, 31, and 35.

### Root cause

The current process gives the host enough freedom to provide a narrative,
while TailTrail checks primarily structural completeness: named paths, tiers,
and runnable commands. Neither side must establish a complete, fresh,
requirement-level chain from:

```text
user clause
  -> current observed behavior
  -> expected changed behavior
  -> implementation/dependency scope
  -> behavior-specific proof
  -> rendered plan
```

The solution is not an expanding keyword list. It is a typed, evidence-bound
intake stage that runs before the primary Start Plan.

## Principles

1. **The host gathers; TailTrail decides.** The host supplies observations and
   candidates. TailTrail owns mandatory fields, validation, acceptance, and
   completeness.
2. **A raw answer is not authority.** A host-provided path, root-cause theory,
   status, or proof command begins as a candidate. It cannot directly grant
   scope, acceptance, or plan approval.
3. **Every material requirement has a traceable chain.** There must be
   requirement-to-answer, answer-to-evidence, requirement-to-scope, and
   requirement-to-proof bindings.
4. **Existing behavior is a valid result.** `already-satisfied` is a safe
   terminal classification for that requested item, not a reason to invent a
   source edit.
5. **Unknown is safer than guessed.** A missing or contradictory detail stays
   open and triggers clarification. It must not be silently inferred into an
   approvable plan.
6. **Evidence must be fresh.** Source evidence is bound to repository-relative
   paths and content fingerprints. A changed file invalidates dependent
   acceptance until it is rechecked.
7. **Executable is not sufficient.** A runnable test command is proof only
   when it is bound to the requirement, asserted behavior, and source answer
   that justify it.
8. **The system must fail forward.** Every block identifies its classification,
   affected field or requirement, impact, and exact next host action.

## Roles and Authority

| Role | May do | May not do |
|---|---|---|
| Host agent | Inspect code, collect observations, propose candidates, supply exact commands and evidence | Mark an answer accepted, declare scope complete, mint a completion receipt, or approve its own plan |
| Navigator / intake service | Select the profile, issue questions, normalize candidates, validate and accept evidence | Treat unvalidated host prose as canonical truth |
| Reconciliation auditor | Independently compare accepted facts with requirements, scope, proof registry, and presentation | Rewrite requirements or approve unresolved gaps |
| User | Resolve decision escalations and approve an evidence-complete plan | Be asked to infer technical evidence that TailTrail can inspect |
| Optional read-only reviewer agent | Perform independent source/call-site inspection for complex work | Grant authority, alter scope, or override failed validation |

The optional reviewer is advisory. The authoritative cross-check is a
deterministic TailTrail audit over stored, fingerprinted artifacts.

## End-to-End Flow

```text
User request
  -> profile selection and field registry
  -> host investigation dossier / observations
  -> candidate extraction and normalization
  -> evidence, freshness, consistency, and semantic-delta validation
  -> bounded clarification loop or user-decision escalation
  -> accepted-answer and proof-binding registry
  -> TailTrail completion calculation
   -> intake-recorded receipt
   -> planning-readiness receipt
  -> canonical-plan reconciliation audit
  -> primary Start Plan
  -> explicit user approval
```

For implementation, correction, configuration/data, and QA/validation work,
the receipt and reconciliation audit are mandatory before a primary Start Plan
can become approvable. Documentation-only and review/read-only profiles use a
smaller profile and do not need artificial code-change evidence.

## 1. Profile-Owned Questionnaire

### How the host knows what to provide

The host must not guess which details TailTrail needs. Navigator selects one
of the existing task profiles and emits a profile-specific questionnaire. The
field registry, not the host, determines mandatory fields.

The questionnaire contains four sections:

```text
1. Task and outcome
2. Scope and ownership
3. Proof and preservation
4. Change Evidence
```

The first three sections retain existing Host Question Flow responsibilities.
The fourth section is the new conditional mandatory module that prevents the
repeated missed-code and missed-requirement failures.

### Change Evidence questions

For each material implementation requirement, TailTrail must issue or prefill
these questions:

| Field | Host must provide | TailTrail use |
|---|---|---|
| `current_state` | `missing`, `partial`, `satisfied`, `conflicting`, or `unknown` | Determines whether implementation is eligible |
| `current_behavior` | Observable current behavior, not a root-cause claim | Semantic-delta comparison |
| `behavior_evidence` | File, symbol/call site where possible, and source fingerprint | Grounding and freshness validation |
| `expected_behavior` | Precise observable post-change outcome | Canonical requirement and proof binding |
| `positive_criterion` | What must work after the change | Acceptance criterion |
| `preservation_criterion` | What must not regress | Preservation rule |
| `owner_candidate` | Proposed implementation path and role | Scope proposal input only |
| `dependency_candidates` | Schema, serializer, validator, caller, config, or test implications | Transitive scope audit |
| `proof_candidate` | Path, exact command, tier, asserted behavior | Proof-binding candidate |
| `open_risk` | Any missing information or uncertainty | Clarification or escalation route |

For a new feature, `current_behavior` describes adjacent behavior and the
public integration boundary. For QA-only work, the delta concerns test or
evidence behavior. Documentation-only and review/read-only profiles omit the
code-change fields unless they explicitly make a behavioral claim.

## 2. Candidate Answers Are Not Accepted Facts

### Observation and candidate model

The host submits one or more observations. TailTrail stores each unchanged,
assigns an observation ID, and extracts normalized candidates into the field
registry. A candidate retains its source observation, question ID, and source
evidence.

Conceptual record:

```json
{
  "answer_id": "ans-021",
  "question_id": "q-current-behavior-014",
  "field_id": "current_behavior",
  "value": "answer-recorded payload has no candidate-state field",
  "state": "candidate",
  "source_observation_id": "obs-008",
  "evidence": [
    {
      "path": "scripts/intake_pipeline.py",
      "symbol": "record_answer",
      "content_fingerprint": "sha256:..."
    }
  ],
  "authority_granted": false,
  "finalization_allowed": false
}
```

The host never supplies `state: accepted`, `authority_granted: true`, or
`finalization_allowed: true`. Those values are Navigator-owned state.

### Answer state machine

```text
candidate
  -> accepted                 evidence and consistency checks pass
  -> needs-clarification      evidence is incomplete or ambiguous
  -> conflicting              evidence contradicts another accepted candidate
  -> rejected                 evidence disproves the asserted answer
  -> stale                    an evidence fingerprint no longer matches

accepted -> stale             cited evidence changes
needs-clarification -> candidate -> accepted/rejected/conflicting
```

Only `accepted` answers can contribute to intake completeness, scope proposal,
canonical requirements, proof bindings, or a primary Start Plan.

### Privacy and retention boundary

"Store unchanged" preserves an answer's meaning and provenance; it does not
authorize durable storage of secrets, credentials, personal data, or private
chain-of-thought. Redact known secret shapes before persistence and reject or
quarantine material that cannot be safely redacted. Store the minimum
structured observation needed for review: normalized value, question/source
IDs, evidence references, and integrity fingerprints. Raw answer bytes are
not retained by default. Any exception must declare an owner, access boundary,
retention duration, deletion rule, and redaction status. Reports consume only
the sanitized record.

## 3. Verification of Host Answers

TailTrail verifies answers with different validators according to field type.
No single natural-language score is enough.

| Validator | Question it answers | Example |
|---|---|---|
| Structural validation | Is the submitted value well formed? | Path is repository-relative; tier is valid; command is nonempty |
| Repository validation | Does the cited evidence exist and remain fresh? | File and content fingerprint match |
| Semantic grounding | Does the cited symbol/call site support the claimed behavior? | `record_answer()` really emits the claimed payload |
| Dependency closure | What artifacts constrain this behavior? | Event schema with `additionalProperties: false` must be considered |
| Proof validation | Does the exact command prove this requirement? | Command, test path, tier, assertion, and answer ID are bound |
| Cross-field consistency | Do answers agree with each other? | `satisfied` cannot coexist with a required implementation owner without a partial/missing sub-item |
| Reconciliation | Did every accepted fact reach every canonical surface? | Proof command appears in registry and rendered plan with the same fingerprint |

### Semantic-delta gate

Before scope is approved, TailTrail produces a typed semantic-delta artifact:

```text
requested assertion
current observed assertion
evidence paths and fingerprints
expected post-change assertion
pre-change failing/new assertion scenario
```

Permitted outcomes are:

| Outcome | Meaning | Routing |
|---|---|---|
| `missing` | Requested behavior does not exist | Eligible for planning |
| `partial` | Some behavior exists but defined delta remains | Eligible for bounded planning |
| `satisfied` | Requested behavior already exists | `already-satisfied`; no implementation plan for that item |
| `conflicting` | Evidence or requirements disagree | Clarification or user decision required |
| `unknown` | Insufficient evidence | Clarification required |

An implementation plan cannot become approvable when every material item is
`satisfied`, or when a missing/partial assertion has no observable delta and
proof scenario.

Semantic validation must be bounded by evidence TailTrail can actually
inspect. Structural checks, path existence, content hashes, schema validation,
and static symbol/call relationships may be deterministic; they do not by
themselves prove runtime behavior. A behavioral claim is accepted only when a
behavior-specific test, trusted observation, or other declared evidence
supports it at the named boundary. If the analyzer cannot establish that
relation, retain `unknown` or `needs-clarification` rather than inferring
`satisfied` or `missing`. Reports label checks as mechanical, advisory, or
host/user judgment.

`already-satisfied` applies to one requirement at one named public or caller
boundary. Record the observed behavior, entry point, evidence, and compared
expected behavior; do not infer that adjacent requirements or preservation
rules are also satisfied.

## 4. Structured Proof Bindings

TailTrail stores proof as a first-class binding instead of scattered text.

```json
{
  "proof_binding_id": "proof-014",
  "requirement_uid": "req-...",
  "proof_path": "tests/test_intake_pipeline.py",
  "command": "python3 -m unittest tests.test_intake_pipeline",
  "tier": "unit",
  "asserted_behavior": "host observations remain candidates and cannot grant acceptance",
  "source_answer_id": "ans-021",
  "positive_criterion_id": "criterion-004",
  "preservation_criterion_ids": ["preserve-002"],
  "command_fingerprint": "sha256:..."
}
```

Where supported, a binding also names the test selector, test case, or
scenario ID that exercises the assertion. An `asserted_behavior` label alone
does not prove that a test contains that assertion. A trusted receipt records
the resolved command, requirement, tier, selected test/scenario identity when
available, exit status, duration, and bounded/redacted output references.

Rules:

- Every material requirement has at least one accepted proof binding or an
  explicit open proof question.
- An executable command alone is not a binding.
- A proof path is never an implementation owner solely because it is included
  in a binding.
- The binding must identify the behavior it asserts, so a passing unrelated
  suite cannot be credited.
- If a source answer, criterion, command, or evidence fingerprint changes, the
  binding becomes stale and must be revalidated.

## 5. Bounded Host–TailTrail Clarification Protocol

TailTrail must ask precise questions when validation fails; it must not silently
discard host material or request an unstructured re-explanation.

Each clarification includes:

```text
question ID
requirement / field ID
current candidate and cited evidence
validation failure classification
why it matters to scope, proof, or safety
accepted answer shape
exact next action
```

Example:

```text
Q-014 — schema dependency unresolved

Candidate: `record_answer()` needs a new durable field.
Evidence: `scripts/intake_pipeline.py::record_answer`.
Finding: the emitted event has a typed schema; its dependency is not bound.

Provide either:
1. the schema/validator path and evidence that constrains this event; or
2. evidence that the payload is intentionally untyped.

The Start Plan is blocked because accepting a pipeline-only owner could create
an anchor that cannot legally change the required serialized contract.
```

TailTrail permits a bounded number of clarification rounds per field (initial
proposal plus a configurable small number of follow-ups). If the same field
remains contradictory, the state becomes `user-decision-required`; TailTrail
states the available evidence and options without inventing an answer.

## 6. Intake Completion and Primary Start Gate

TailTrail, not the host, computes intake completion. Recording answers were
collected is distinct from declaring a plan ready for approval.

TailTrail may mint an `intake-recorded` receipt after validating and storing
submitted answers, even while material questions remain. This receipt records
the intake exchange only; it grants no planning or implementation authority.
A separate `planning-readiness` receipt may be minted only when:

1. the profile registry has been selected and all required fields are
   `accepted`, waived by profile, or explicitly routed to user decision;
2. each missing/partial requirement has a validated semantic delta;
3. each material requirement has an accepted proof binding; an unresolved
   proof question remains open and prevents planning readiness;
4. dependencies have been checked for typed contracts and behavior surfaces;
5. accepted evidence is fresh and non-conflicting; and
6. the receipt fingerprints its questions, accepted answers, evidence, proof
   bindings, profile version, and repository state.

`tailtrail start` for Host Question Flow work accepts a valid
`planning-readiness` receipt, not a raw host contract or an `intake-recorded`
receipt. A raw contract or intake-only receipt fails closed with the missing
readiness receipt and exact unfinished fields.

Receipts are versioned, append-only, and bound to the run, target identity,
profile/registry version, accepted-answer set, evidence fingerprints, and proof
bindings. Replay against another run, target, question revision, or repository
state is rejected. Identical inputs may be idempotent; changed accepted
evidence creates a new linked receipt version.

## 7. Canonical-Plan Reconciliation Before v1

Before rendering or persisting the primary Start Plan, a reconciliation audit
must compare the accepted receipt against every canonical plan surface.

| Accepted fact | Required destination |
|---|---|
| Requested/expected behavior | Requirement statement and acceptance criterion |
| Preservation rule | Requirement preservation contract |
| Owner candidate accepted by Navigator evidence | Scope role and approved anchor candidate |
| Schema/caller/test dependency | Scope or explicit justified non-edit dependency |
| Proof binding | Requirement validation contract, proof registry, and rendered proof table |
| `satisfied` classification | `already-satisfied` disposition, not implementation scope |
| Open risk | Question or user-decision route, not silent omission |

The audit fails closed if any accepted fact has no destination, any proof
fingerprint differs, a typed dependency is omitted, or presentation loses a
material field. It returns bounded proposed corrections before v1 rather than
allowing an incomplete plan to be approved and later stopped.

Revalidate at each authority boundary: planning-readiness calculation, primary
Start persistence, user approval, and activation. Each check verifies target
identity and every referenced content fingerprint. A changed file invalidates
only dependent answers and proof bindings, which become `stale`; a previous
receipt is never silently reused. Where locking is available, perform the last
freshness check and authority write under the same lock to reduce
time-of-check/time-of-use races.

## 8. Normal and Verbose Presentation

The normal Start presentation should be concise and operational. It must show:

- task profile and intake receipt status;
- material requirements and semantic-delta outcome;
- outstanding clarification or user-decision questions;
- approved owners/dependencies and proof bindings;
- reconciliation result; and
- a clear approval decision.

Verbose mode must preserve the full audit trail:

- all issued questions and candidate/accepted/rejected states;
- original host observations and answer lineage;
- evidence paths, symbols, and fingerprints;
- proof bindings and assertion details;
- stale/conflicting evidence history;
- reconciliation matrix; and
- review-cycle history and revisions.

Normal mode is a projection of persisted artifacts. Verbose mode is evidence,
not a second competing plan format.

### Lifecycle-authentic Start and Closure documents

The full verbose report is a persisted lifecycle artifact regardless of how
much detail is printed in chat. The visible Markdown file is a projection of
canonical records, not a separately reconstructed summary.

Before approval, Start generates the actual full Start Plan from the exact
saved proposal and current revision. It includes requirements and criteria,
interpretation provenance, question/answer history when present, AIDLC stage
and decisions when used, scope roles and evidence, controls, proof bindings,
risks, assumptions, open questions, audit/revision history, token estimates
with provenance, approval state, and its visible path. During pre-approval
AIDLC gathering, regenerate or version the Start artifact whenever questions,
answers, or the proposed boundary change. Unknown fields are marked pending
or unavailable, never presented as final.

The Closure Report is not created at Start or merely on approval. Generate it
only after the finalizer has persisted a closure result. Finalized does not
mean successful: an `evidence-incomplete` or failed outcome still gets a
Closure Report stating failures and blockers. Build it from the approved
anchor, source-edit records, execution events, trusted/attested receipts, test
output references, harness assessments, completion review, drift,
recovery/correction events, and linked token telemetry. Include changed paths
and available symbol/line locations, commands, exit codes, durations, failures
and retries, per-requirement verification, health checks, overall status,
residual risks, and unavailable data. Do not infer edits from a passing command
or claim token measurements from a planning estimate.

Keep canonical machine-readable artifacts under `.tailtrail/runs/<run-id>/`.
Write visible Markdown to `session-reports/<run-id>/start-plan.md` and
`session-reports/<run-id>/closure-report.md`. After Start generation and after
Closure finalization respectively, print both workspace-relative and absolute
paths. JSON metadata may accompany the internal artifacts but does not replace
the visible documents.

Token reporting distinguishes measured provider/API telemetry, planning
estimates, and unavailable values. Measured totals and phase breakdowns require
telemetry linked to this run ID. Estimates include source and confidence. If
phase attribution is unavailable, report it as unavailable rather than
inventing an allocation.

Generation is idempotent for an unchanged source fingerprint. Changed plans,
execution streams, receipts, or finalizer results create versioned artifacts
or atomically refresh the visible projection while preserving canonical
history. A failed render creates no success marker; the completion report
identifies the missing artifact and recovery action. Never create a
Closure-time placeholder at Start.

## Confidence: Useful for Triage, Never Authority

Do not use a numerical confidence score as an approval gate. A high score can
hide one critical missing schema, preservation rule, or proof binding.

The authoritative mechanism is state plus verification result:

```text
accepted | candidate | needs-clarification | conflicting | rejected | stale
```

An optional non-authoritative `evidence_strength` indicator may help the host
prioritize investigation, for example:

```text
strong  — exact symbol/call site and fresh direct test evidence
medium  — exact source evidence but no behavior-specific test yet
weak    — filename or lexical inference only
```

It must not grant acceptance, scope authority, receipt issuance, or approval.

## Cross-Check Architecture

Do not add a free-form “supervisor agent” that simply reviews prose and can
overrule evidence. That recreates the same authority ambiguity at another
layer.

Use these three defenses instead:

1. **Host investigation:** supplies candidate observations and evidence.
2. **Deterministic intake validation:** verifies structure, freshness,
   grounding, dependencies, proof bindings, and completeness.
3. **Independent reconciliation audit:** verifies accepted facts are present in
   requirements, scope, proof registry, and the presentation.

For complex or high-risk tasks, an optional independent read-only reviewer may
produce additional observations. Its findings enter the same candidate and
validation process; it cannot accept facts or edit code.

## Meta-Harness Feedback Loop

Meta-Harness is a useful **future cross-task product monitor** for this
contract. Its integration is proposed, not currently implemented by this
design. It must not become a second live planner or a per-task authority.

The division is deliberate:

```text
Per-task prevention
  host observations
    -> intake validation
    -> semantic-delta check
    -> reconciliation audit
    -> primary Start Plan / user approval

Cross-task improvement
  sanitized outcome events
    -> Meta-Harness analysis
    -> repeated finding
    -> reviewable product proposal
    -> maintainer approval, implementation, and regression proof
```

### Why Meta-Harness is not the primary Start gate

Meta-Harness is designed to evaluate TailTrail workflow fit, repeated failure
patterns, confidence, guardrails, context, metrics, and proposal readiness.
Its normal developer-task mode stays quiet, and its shareable inputs are
sanitized: they must not contain raw prompts, source bodies, logs, secrets,
repository identity, or user identity. It therefore cannot safely establish
fresh source-level truth for an individual requirement at the time a plan is
created.

The intake validator and reconciliation auditor have that per-task role. They
use the current, fingerprinted local evidence and fail closed before approval.
Meta-Harness learns only from their sanitized outcomes and improves future
TailTrail behavior when the same category recurs.

### Current integration boundary

The existing shared Meta-Harness input is the versioned `harness_summary`
event in `tailtrail-meta/harness-summary.jsonl`. `harness-review.py` validates
it against a fixed allowlist, and `meta-harness-analyze.py` reads that file and
aggregates its existing categorical fields. The conceptual
`host-question-flow-meta-feedback` event below is **not accepted by that
schema or consumed by the current analyzer**. Do not append it to the shared
summary or claim that it already contributes findings.

If this extension is approved for implementation, choose and document one
explicit integration before emitting events:

1. Map the new outcome categories losslessly into existing `harness_summary`
   fields when those fields genuinely represent the same fact; or
2. Introduce a versioned, closed event variant and update the shared schema,
   sanitizer, writer, analyzer, proposal path, packaging, and tests together.

Do not silently add unknown fields to the current allowlist, and do not map
distinct evidence states into a generic field merely to make the analyzer
accept them. Until one of these paths is implemented and validated, this
feedback loop is a design proposal only; the existing Meta-Harness remains
unchanged.

### Proposed sanitized feedback event

After a meaningful intake, reconciliation, correction, or closure outcome, a
future approved adapter may produce one sanitized categorical observation per
run and finding category. The following is conceptual and requires the schema
integration above before it can be emitted to any Meta-Harness input:

```json
{
  "type": "host-question-flow-meta-feedback",
  "schema_version": "1",
  "profile": "existing-code-change",
  "semantic_delta": "satisfied",
  "intake_outcome": "planning-readiness-blocked",
  "reconciliation_outcome": "dependency-omitted",
  "clarification_round_count": 2,
  "post_approval_contradiction": false,
  "stale_evidence_detected": false,
  "finding_codes": ["schema-dependency-omitted"]
}
```

The shareable event contains no raw answer text, source body, path, symbol,
command output, receipt identity, absolute location, repository identity, user
identity, private URL, secret, or token count. Run-to-event linkage, if needed
for idempotency, stays in local private state and is never exported. Redaction
happens before persistence of the shareable form; a sanitizer rejection emits
no event and creates no finding.

Deduplication is required to prevent one run from satisfying a cross-task
repeat threshold by itself. The local writer records at most one contribution
per `(run_id, finding_code)` and updates that contribution if the same run
reaches a later lifecycle stage. The shared event contains no run ID. The
analyzer counts accepted events from distinct local contributions; overlapping
input files are deduplicated by canonical source path. It must not collapse
identical event values across different contributions, because separate runs
can legitimately produce the same categorical outcome. The default repeat
threshold remains at least two distinct contributions, and a single event
must never create a product finding or proposal.

### Findings Meta-Harness should detect

Meta-Harness aggregates only repeated, meaningful evidence into findings such
as:

- `repeated-no-op-plan` — semantic validation later proves the named behavior
  already existed;
- `repeated-requirement-omission` — accepted intake facts are absent from the
  canonical requirement or plan projection;
- `repeated-schema-dependency-omission` — typed-contract dependencies are
  repeatedly omitted from scope;
- `repeated-proof-binding-mismatch` — runnable commands lack the bound
  assertion or are replaced during projection;
- `repeated-stale-receipt` — evidence becomes stale at an authority boundary;
- `repeated-clarification-dead-end` — a field/profile routinely exhausts the
  bounded clarification loop; and
- `repeated-presentation-loss` — canonical facts are absent from normal or
  verbose presentation.

A single event is a task-local observation, not product learning. Existing
Meta-Harness evidence thresholds, severity assessment, registry-aware impact
analysis, maintainer review, rollback, and proposal records govern any
TailTrail product change. This section does not change the current threshold
or analyzer behavior.

### Authority boundaries

Meta-Harness may:

- identify repeated categorical workflow failures;
- recommend a questionnaire field, validator, audit, routing rule, or
  regression scenario;
- create a reviewable, evidence-labeled proposal; and
- surface a compact hint only after the relevant proposal is accepted or
  implemented.

Meta-Harness must not:

- accept a host answer or classify a requirement as satisfied;
- alter the profile field registry during a live task;
- broaden or reduce scope, alter proof bindings, mint receipts, or unblock a
  Planning Lock;
- run heavy aggregation automatically during normal `start` or guide flows;
- auto-edit TailTrail; or
- override source evidence, policy, tests, scanners, explicit user decisions,
  or the per-task reconciliation audit.

This gives TailTrail two complementary protections: the live evidence gate
prevents an unsafe plan now, while Meta-Harness makes repeat host/TailTrail
failures visible and may turn proven patterns into reviewed product
improvements after the proposed schema and analyzer integration is implemented.

## Delivery Sequence

Implement in dependency order. Reuse current profile registries, Host Question
Flow, scope evidence, proof contracts, and Meta-Harness capabilities where they
already satisfy a requirement; do not create parallel owners.

### Phase 0 — Inventory And Ownership

- Trace current Start, AIDLC, scope, proof, receipt, audit, report, and Closure
   paths.
- Map each requirement to its current schema, writer, reader, CLI route, tests,
   and identified gap.

**Exit gate:** every requirement has an evidence-backed owner/dependency map
and an explicit reuse-or-gap decision.

### Phase 1 — Intake State And Privacy

- Add only missing candidate/accepted/stale/conflicting state and source
   lineage; keep host input non-authoritative.
- Define schema versioning, size bounds, ingestion redaction, retention,
   access, and deletion behavior before persisting observations.

**Exit gate:** malformed, stale, conflicting, oversized, or secret-bearing
input cannot become an accepted fact or grant authority.

### Phase 2 — Evidence And Semantic Delta

- Implement deterministic structural, path, fingerprint, schema, static
   relationship, dependency, and cross-field checks where evidence supports
   them.
- Require behavior-specific tests or trusted observations for behavioral
   claims. Unsupported semantic conclusions remain `unknown` or
   `needs-clarification`.
- Scope `already-satisfied` to one requirement and named boundary.

**Exit gate:** positive and negative tests prove validator claim boundaries;
unsupported source/runtime claims cannot be accepted by inference.

### Phase 3 — Proof Bindings And Readiness

- Bind each material requirement to the proof path, exact command, tier,
   asserted behavior, test/scenario selector when available, source answer, and
   evidence fingerprint.
- Keep `intake-recorded` separate from `planning-readiness`; only readiness
   can authorize an approvable Start Plan.
- Define replay, idempotency, target binding, and stale-evidence behavior.

**Exit gate:** unrelated passing suites cannot satisfy proof, stale bindings
are rejected, and intake-only receipts cannot authorize Start.

### Phase 4 — Reconciliation And Start Gate

- Reconcile every accepted fact with requirements, preservation, scope,
   dependencies, proof registry, and presentation.
- Recheck target identity and evidence fingerprints at readiness, Start
   persistence, approval, and activation; make the final check and authority
   write atomic where supported.

**Exit gate:** public CLI tests prove omitted or stale facts block before
approval with a bounded correction/clarification route.

### Phase 5 — Full Start Artifact

- Generate the actual full Start Plan from the exact saved pre-approval
   proposal, regardless of chat verbosity.
- Include AIDLC questions/answers when present, scope/evidence, requirements,
   controls, proof, risks, revisions/audits, token provenance, and
   pending/unavailable states.
- Refresh or version it when pre-approval questions, answers, scope, or proof
   changes; print and highlight both visible paths before approval.

**Exit gate:** public Start/AIDLC routes show that the artifact matches the
saved proposal and grants no authority before explicit approval/activation.

### Phase 6 — Execution And Closure Artifact

- Gather changed-path/source-edit records, execution events, trusted receipts,
   outputs, durations, failures/retries, corrections, harnesses, drift, health,
   and run-linked token telemetry from canonical sources.
- Generate Closure only after the real finalizer persists a result. Incomplete
   finalization still produces a factual failure report; Start never creates a
   Closure placeholder.
- Highlight the Closure path only after the artifact exists. Label token
   measurements as measured only with linked telemetry; otherwise show estimates
   with provenance or `unavailable`.

**Exit gate:** public finalization tests prove no early Closure, factual output
after both successful and incomplete finalization, and no missing-evidence
success claims.

### Phase 7 — Optional Meta-Harness Feedback

- Keep current `harness_summary` behavior unchanged until a versioned schema
   and analyzer integration is approved.
- If implemented, update schema, sanitizer, writer, analyzer, proposal path,
   packaging, and tests together. Deduplicate to one contribution per run and
   finding category; require at least two distinct contributions.
- Keep findings advisory and behind existing maintainer review/approval.

**Exit gate:** schema/privacy negatives, cross-run threshold, duplicate
ingestion, registry, and no-authority-escalation tests pass. This optional
phase does not block the per-task evidence gate.

The intake phases may be implemented as one shared slice only when their
schemas, public routes, and assertion-level tests land together. The Start and
Closure artifact phases remain separate lifecycle slices because they have
different source states and generation gates.

## Acceptance Criteria

The design is complete only when executable regressions prove all of the
following.

1. A feature already implemented at the named call site becomes
   `already-satisfied`; it cannot create an approvable implementation plan.
2. A host answer cannot directly mark itself accepted or grant scope authority.
3. A stale evidence fingerprint invalidates the dependent accepted answer and
   proof binding.
4. A payload change constrained by a typed schema cannot pass audit unless the
   schema is in approved scope or explicitly justified as unchanged.
5. A runnable command without a requirement-linked asserted behavior cannot
   satisfy a proof binding.
6. A raw host contract or intake-recorded receipt cannot start Host Question
   Flow planning without a valid planning-readiness receipt.
7. An accepted answer omitted from requirement, scope, proof, or presentation
   produces a pre-v1 reconciliation failure with precise correction guidance.
8. A conflicting answer follows the bounded clarification loop and then
   escalates to the user without being silently resolved.
9. Normal mode reports core outcomes; verbose mode renders the complete
   questionnaire, evidence lineage, proof bindings, reconciliation, and review
   history.
10. The visible full Start Plan is generated from the exact saved pre-approval
   plan regardless of chat verbosity, and includes available AIDLC
   questions/answers, scope, requirements, controls, proof, audit history, and
   token provenance.
11. No Closure Report exists before finalization. A successful or
   evidence-incomplete finalization produces a factual report with changed
   paths, execution events, commands, exit codes, durations, receipts,
   failures/corrections, harnesses, drift, health checks, token source/status,
   overall status, residual risks, and unavailable markers.
12. Public Start and Completion outputs highlight the workspace-relative and
   absolute paths to their Markdown reports. Missing artifacts are reported as
   missing, never represented by fabricated links.
13. Redaction and retention tests prove secrets/private reasoning are removed
   or rejected before persistence and do not reappear in reports.
14. Public-route tests prove freshness is rechecked at readiness, Start
   persistence, approval, and activation, including a file change between
   checks.
15. Public CLI tests prove an intake-recorded receipt cannot authorize Start,
   a planning-readiness receipt is bound to the matching run/target/repository
   snapshot, and replay against a different or stale context is rejected.
16. Semantic-validation tests distinguish mechanically verified facts from
   advisory claims; unsupported behavioral claims remain `unknown` rather than
   becoming accepted or `already-satisfied`.
17. A proof command that passes without the bound assertion/test selector does
   not satisfy its requirement; a matching trusted receipt does.
18. The proposed host-question event is rejected by the current shared schema
   until an explicitly versioned event contract and analyzer support are
   implemented; it is never silently accepted as `harness_summary`.
19. Sanitizer tests prove raw answer text, source, paths, identities, secrets,
   private URLs, and token counts cannot enter a shareable feedback event.
20. Repeated lifecycle events from one run contribute at most once per finding
   category; two distinct contributions are required to cross the repeat
   threshold, and identical categories from separate runs remain distinct.
21. Duplicate ingestion of the same canonical input file is idempotent, while
   a single task-local event cannot create a Meta-Harness finding or proposal.
22. Meta-Harness findings and proposals remain advisory: none can accept an
   answer, change a live plan, alter scope/proof, issue a receipt, or unblock
   approval without the existing explicit review and approval path.

## Non-Goals

- Replace user approval with automatic planning.
- Let a host, reviewer, or confidence score grant acceptance.
- Infer a root cause from a host claim without source evidence.
- Force documentation-only or read-only tasks through code-change questions.
- Treat test files as implementation owners merely because they appear in a
  proof binding.
- Create a second, divergent requirements system outside the canonical
  requirement/scope/proof artifacts.

## Relationship to Existing Records

This design consolidates the prevention direction from:

- Issue 21.1 — correction plans need a failing-premise gate;
- Issue 21.2 — proof must be symptom-specific;
- Issue 21.7 — semantic-delta verification applies to ordinary feature work;
- Issue 28 — missing proof paths cannot be corrected after activation;
- Issue 31 — exact host proof declarations must survive Start projection; and
- Issue 35 — planning audit must close typed-contract and assertion-level
  dependency scope.

The related seven-point delivery sequence is also recorded in
`TAILTRAIL-ISSUES-LOG.md` under **Host Question Flow: Outstanding Seven-Point
Delivery Sequence**.
