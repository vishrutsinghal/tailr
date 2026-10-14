# TailTrail Host Question Flow Implementation Plan

Status: draft for review

This plan implements the design in
`TAILTRAIL-HOST-QUESTION-FLOW-DESIGN.md`. It introduces a central intake
pipeline while keeping Navigator as the only host-facing boundary.

## Goals

- Let the host provide observations incrementally without deciding authority.
- Let Navigator own profiling, questions, clarification, and requirement
  finalization.
- Give every answer, path role, requirement, proof, and artifact a central ID.
- Feed validated projections into old and new TailTrail components through
  adapters.
- Prevent stale or unrelated scope and proof from reaching approval or closure.
- Prevent correction plans from reaching approval without a validated failing
  premise, owner participation, and symptom-specific proof.
- Preserve resumability, replay, CLI/MCP parity, and historical artifacts.

## Non-Goals

- Replacing Navigator with a new host conversation engine.
- Allowing internal components to contact the host directly.
- Rewriting historical TailTrail runs.
- Making every observation a new packet version.
- Automatically approving inferred implementation ownership.
- Treating host root-cause or owner hypotheses as authority.
- Requiring failing baselines for new capabilities, refactors, documentation,
  or other non-correction profiles.
- Executing reproduction commands automatically during command-free Debug
  Start.

## Core Invariants

1. The central intake pipeline generates authoritative IDs.
2. Navigator is the only host-facing component.
3. The host submits observations; Navigator accepts or rejects answers.
4. Internal components consume finalized Navigator projections only.
5. Missing or contradictory information creates clarification, not inference.
6. The anchor version is the only versioned authority; a packet is a view bound
  to one anchor version, not an independent version history.
7. Every editable path is bound to an accepted answer, packet view, and
  immutable anchor version.
8. Every proof command is bound to a requirement and must exercise that
   requirement.
9. Components return typed evidence or clarification events to the pipeline.
10. CLI, orchestration, MCP, and internal entry points use the same state
    machine and validation rules.
11. A correction cannot finalize while its premise is `unverified`,
    `contradicted`, or `already-satisfied`.
12. The host supplies observations and hypotheses; TailTrail derives the first
    failing transition and owner participation.
13. Reproduction and post-change proof are separate requirement-bound objects;
    executability alone is not semantic coverage.
14. A post-activation false premise terminates as an audited non-success state
    and never authorizes cosmetic implementation.

## Canonical Objects

| Object | Purpose | Created by |
|---|---|---|
| `run_id` | Identifies one TailTrail interaction | Intake pipeline |
| `contract_id` | Identifies the host input contract | Intake pipeline |
| `question_id` | Correlates a Navigator question and host response | Intake pipeline |
| `observation_id` | Identifies an ingested host observation | Intake pipeline |
| `answer_id` | Identifies a validated answer | Navigator through pipeline |
| `premise_binding_id` | Binds a correction premise to its public-route evidence and state | Intake pipeline |
| `requirement_id` | Identifies a finalized requirement | Navigator through pipeline |
| `path_binding_id` | Binds a path to a role and requirement | Intake pipeline |
| `proof_binding_id` | Binds a proof path/command to a requirement | Intake pipeline |
| `packet_id` | Identifies a finalized operational packet | Intake pipeline |
| `packet_view_id` | Identifies an operational projection for one anchor version | Intake pipeline |
| `anchor_version` | Identifies the only versioned authority for approved scope | Anchor store |
| `artifact_id` | Identifies stored evidence or output | Artifact store |
| `event_id` | Identifies one append-only event | Event store |

The host receives IDs created by TailTrail and echoes them when responding. The
host never creates authoritative TailTrail IDs.

## Phase 0: Contract and State Specification

### Purpose

Freeze the protocol before changing components.

### Deliverables

- Canonical host input contract schema.
- Question, observation, answer, packet, projection, and event schemas.
- Semantic host context schema for request mode, behavior surface, path roles,
  positive/negative criteria, exclusions, and proof surface.
- Correction-premise schema for change intent, premise state, public route,
  expected/actual behavior, provenance, evidence references, and owner
  hypothesis.
- Separate reproduction and post-change proof-binding schemas.
- Role enum for existing, proposed, inspection, proof, generated, excluded,
  and external paths.
- State transition table.
- Anchor-bound packet views and dependency invalidation rules.
- Redaction and retention policy.
- Timeout, pause, expiration, abandonment, and resume handling.

### Required decisions

- JSON contract plus append-only JSONL event stream.
- Central ID generation and collision handling.
- Profile-specific clarification defaults with a three-question round limit and
  a global five-round ceiling. The bounds defend against infinite loops,
  repeated non-resolving answers, unnecessary friction, and unbounded state
  growth.
- User escalation conditions.
- Compatibility behavior for runs without a contract.
- Content fingerprints identify immutable contracts, projections, and artifacts;
  generated IDs identify interaction objects such as runs, questions,
  observations, answers, and events.
- Exact redaction patterns, retention duration, and artifact storage boundaries;
  redaction and retention remain mandatory capabilities while policy details are
  finalized.

### Tests

- Schema validation tests.
- Unknown role/state rejection tests.
- ID uniqueness and deterministic replay tests.
- Packet-version compatibility tests.
- Correction-premise state and transition tests.
- Schema rejection when a correction treats a Planning Lock or scope rejection
  as defect evidence without an observed public-route failure.

### Exit criteria

- Schemas are versioned.
- Every canonical object has an owner and lifecycle.
- Invalid state transitions fail closed.
- No implementation component is required to interpret raw host answers.

### Status: complete

All Phase 0 deliverables are shipped as versioned JSON Schema (and one
companion data) artifacts under `schemas/`, with regression coverage under
`tests/`:

- `host-input-contract.schema.json` -- canonical host input contract: profile,
  change_intent, request_mode, behavior_surface, path role bindings
  (existing/proposed status), positive/negative criteria, proof binding,
  correction_premise with owner_hypothesis gating.
  (`tests/test_host_input_contract_schema.py`, 14 tests)
- `host-question-flow-event.schema.json` -- the append-only event envelope,
  verified against `scripts/intake_pipeline.py`'s real emitted shape, with
  typed payloads for `question-issued`, `host-observation-recorded`, and
  `answer-recorded`; remaining design-vocabulary event types are reserved for
  the phases that implement them.
  (`tests/test_host_question_flow_event_schema.py`, 7 tests)
- `host-question-flow-state.schema.json` + `host-question-flow-transitions.json`
  -- the full state enum and the authoritative transition adjacency list,
  transcribed edge-for-edge from the design doc's two resumable-state
  diagrams (main intake-to-activation sequence, plus the
  paused/expired/abandoned/resumed sub-lifecycle). No edges beyond what the
  design doc specifies are encoded.
- `host-question-flow-packet-view.schema.json` -- anchor-bound packet
  projections with no independent version counter of their own, enforcing
  the single-version-chain rule (Review Resolution #1).
- `proof-binding.schema.json` -- reproduction and post-change proof bindings
  as separate, non-interchangeable kinds; `post-change` requires
  `preservation_boundaries`, `reproduction` rejects it.
- `host-question-flow-redaction-policy.schema.json` -- redaction at ingestion
  (never report-rendering only) using the real, already-shipped
  `scripts/quality-loop.py` `SECRET_SHAPES` catalog as the enum, kept in sync
  by an explicit regression test, plus a retention/storage-boundary policy
  shape.

(`tests/test_host_question_flow_phase0_artifacts.py`, 24 tests, covers the
last four artifacts above.)

Not yet built, deferred to the phases that need them: the full "packet"/
"projection" schemas beyond the packet-view pointer shape (Phase 3), and the
versioned component/adapter registry that `consumer_component_id` resolves
against (Phase 6).

## Phase 1A: Minimal Intake and Event Correlation

### Purpose

Create the smallest source of IDs and event correlation needed to support
Navigator narration and question/answer exchange.

### Deliverables

- Intake pipeline module.
- Central ID generator.
- Contract persistence.
- Append-only event writer.
- Idempotency key support.
- Question, observation, and answer correlation.
- Minimal event-to-contract integrity checks.

### Event examples

```text
run-created
profile-selected
question-issued
host-observation-recorded
answer-accepted
answer-rejected
clarification-required
packet-finalized
anchor-revised
packet-view-materialized
packet-view-invalidated
projection-created
projection-invalidated
approval-recorded
```

### Tests

- Duplicate event submission is idempotent.
- Events from a stale run or packet are rejected.
- Contract fingerprints change only through approved revision events.
- Interaction IDs are unique and content fingerprints remain stable.

### Exit criteria

- Question, observation, and answer IDs are generated centrally.
- Navigator can correlate narration and direct responses without creating
  independent host state.

## Phase 2: Navigator Host Protocol

### Purpose

Make Navigator the exclusive host-facing question and clarification boundary.

### Deliverables

- Task profiler.
- Profile-specific question planner.
- Profile-field registry separate from issued question IDs.
- Question issuance through the intake pipeline.
- Host observation ingestion.
- Behavior-surface and proof-boundary context collection.
- Correction-specific expected/actual behavior, public-route, and evidence
  collection without accepting host root-cause authority.
- Initial narration ingestion as an observation batch.
- Candidate-answer extraction mapped to profile fields.
- Answer normalization and acceptance states.
- Bounded clarification loop.
- User-decision escalation.

### Profiles

- documentation-only;
- existing-code change;
- new feature;
- configuration/data;
- QA/validation-only;
- review/read-only.

### Acceptance states

```text
received
  -> normalized
  -> mapped-to-profile-field
  -> evidence-checked
       |
       +-> accepted
       +-> contradicted
       +-> insufficient
                 |
                 v
       clarification-required
                 |
                 v
       user-decision-required
```

The field-mapping step is shared by direct question responses and volunteered
narration. Direct responses receive their field from the issued question;
narration must produce an explicit candidate mapping before evidence checking.

### Tests

- Host cannot mark an answer accepted.
- A host-declared behavior surface selects evidence shape but does not grant
  proof or authority by assertion.
- Observations without an active question or packet context are rejected or
  routed for classification.
- Narration can fill candidate fields but cannot directly create an accepted
  answer or grant authority.
- A volunteered observation without a question ID retains a required field ID
  and observation ID.
- Only evidence-checked candidates can fill a profile field.
- Navigator can ask a follow-up question using the same requirement lineage.
- Dead ends escalate to the user instead of silently choosing a path.
- Documentation tasks receive fewer questions than new feature tasks.
- Clarification rounds resume after process interruption.
- Paused runs can expire or be explicitly abandoned without deleting evidence;
  resuming never approves or activates a run.
- An unverified correction enters `awaiting-reproduction-input` and creates no
  Planning Lock.
- An already-satisfied proposed layer routes to re-diagnosis instead of asking
  the host to invent a different failure.

### Exit criteria

- Host questions and answers are visible through Navigator only.
- No Planning Lock is created before required answers are accepted.
- No internal component has a host communication path.
- Runs have explicit paused, expired, abandoned, and resumed states.
- Narration reduces unnecessary questions without bypassing acceptance checks.

## Phase 1B: Full Event Durability and Replay

### Purpose

Complete the event-store capabilities after the user-facing Navigator slice is
working.

### Deliverables

- Full contract persistence and materialized projections.
- Resume and replay APIs.
- Event-to-contract integrity checks.
- Dependency-aware packet-view invalidation on anchor revision.
- Redaction at ingestion and protection against reappearance in derived
  artifacts.
- Expired and abandoned run handling that preserves evidence and blocks
  execution until explicit resume.

### Tests

- Replayed events produce the same materialized contract and packet view.
- Duplicate event submission is idempotent.
- Interrupted host exchanges resume without losing accepted answers.
- Redacted values never reappear in derived artifacts.
- Expired or abandoned runs cannot execute until explicitly resumed.

### Exit criteria

- The event stream can rebuild the current contract and anchor-bound packet
  view.
- Replay produces the same fingerprints as the original materialization.
- Recovery preserves lineage without creating duplicate IDs.

## Phase 3: Requirement and Packet Finalization

### Purpose

Turn accepted answers into one immutable operational packet.

### Deliverables

- Requirement builder.
- Path-role binding builder.
- Proof binding builder.
- Candidate-answer to profile-field binding builder.
- Positive and negative criteria binding.
- Correction-premise binding and owner-participation evidence binding.
- Packet finalization command.
- Anchor-bound packet-view materialization and dependency invalidation on anchor
  revision.
- Projection audit showing consumed, unused, contradicted, inferred, and
  projected-without-source answers.

### Existing versus proposed paths

Existing paths require existence and role evidence. Proposed paths require:

- explicit host declaration;
- a permitted proposed role;
- an ownership/convention reference or approved new-file decision;
- a post-implementation existence check;
- final diff membership;
- proof completion if the path is a test or proof path.

### Tests

- Old-file answers bind to the approved anchor.
- New-file answers remain proposed until verified after implementation.
- Unused answers block finalization or create clarification.
- Contradictory path roles cannot finalize.
- Narration-derived candidates use the same evidence gate as direct responses.
- Changing a requirement creates a new anchor revision and packet view.
- Dependent scope and proof projections are invalidated after anchor revision.
- A correction with `unverified`, `contradicted`, or `already-satisfied`
  premise cannot finalize.
- A scope or planning failure by itself cannot satisfy the correction premise.
- A new-capability profile finalizes without a failing baseline when its normal
  path, criteria, and proof contracts are complete.

### Exit criteria

- Navigator can emit `requirements-finalized`.
- The packet contains all requirement, path, proof, and criteria bindings.
- Every binding has source answer IDs.
- No downstream component needs raw host conversation data.
- Every correction packet has an accepted premise binding and derived
  owner-participation evidence.

## Phase 4A: Existing Scope Authority Baseline

### Purpose

Reuse and verify the already-shipped scope and anchor enforcement instead of
rebuilding it.

### Deliverables

- Confirm the existing scope projection adapter for Navigator.
- Confirm anchor binding with content fingerprints.
- Confirm write-time scope checks and closure-time changed-path checks.
- Confirm existing/proposed path verification.
- Confirm role-preserving handling for tests, docs, config/data, generated
  files, and external references.
- Confirm multi-file role conflict detection.

### Scenarios

#### Existing source file

Verify the declared owner exists, is in the approved anchor, and changed
symbols remain inside the packet boundary.

#### Proposed new source file

Verify the path was explicitly proposed, created under the approved root, and
is not substituted by an unrelated existing file.

#### Test or proof file

Keep it proof-only unless the profile is test-only. Require its command and
requirement binding before completion.

#### Documentation-only file

Use the docs-only profile and prevent source ownership from being inferred.

#### Configuration/data file

Require explicit role, consumer, write authority, and schema/format proof.

#### Generated/external file

Keep it out of editable scope unless an explicit approved role allows it.

### Tests

- Write outside the path binding is blocked.
- A path changed after packet revision is rejected as stale.
- Worktree and generated paths are excluded.
- Mixed-role multi-file changes preserve each role.
- Closure detects changed files not present in the anchor.

### Exit criteria

- Every existing editable path is traceable to the current anchor and scope
  projection.
- Write-time and closure-time checks agree.
- Scope cannot be broadened by a downstream component.

The existing enforcement is treated as a verified baseline. The remaining
answer-to-path authorization work is Phase 4B.

## Phase 4B: Answer-to-Path Authorization

### Purpose

Bind each editable path to the accepted answer, packet view, and anchor version
that authorized it.

### Deliverables

- Answer-to-path authorization record.
- Existing versus proposed-new path binding verification.
- Path-binding fingerprint included in the anchor projection.
- Write-time and closure-time lineage checks.
- Invalidation when a path role or accepted answer changes.

### Tests

- An editable path without an accepted source answer is rejected.
- A path from a stale packet view cannot be written.
- A proposed-new path is verified after creation before completion.
- Multi-file changes retain the correct answer and role for every path.

### Exit criteria

- Every editable path has answer, requirement, packet-view, and anchor-version
  lineage.
- Scope enforcement remains compatible with the existing shipped baseline.
- Downstream components cannot broaden editable scope.

## Phase 5: Proof and Validation Projection

### Purpose

Ensure proof is requirement-specific and cannot be replaced by a nearby test.

### Deliverables

- Proof projection adapter.
- Existing and proposed proof path handling.
- Requirement-to-command binding.
- Positive and negative assertion coverage.
- Separate reproduction and post-change proof bindings for corrections.
- Assertion/scenario identifiers linking both proof bindings to the reported
  symptom and preservation criteria.
- Proof relevance check.
- Managed execution evidence correlation.
- Stale proof invalidation after packet revision.

### Tests

- A Delivery Record test cannot satisfy an unrelated P7 requirement.
- A proposed proof path becomes required completion scope.
- A command with no requirement binding is rejected.
- A passing command that does not cover the requirement remains incomplete.
- Amended proof remains requirement-bound and auditable.
- An executable passing suite with no requirement-linked assertion remains
  unresolved.
- Reproduction covers the original expected/actual symptom at the public route;
  post-change proof covers the corrected behavior and preservation boundary.

### Exit criteria

- Every required requirement has an explicit proof binding.
- Proof bindings match the host-declared behavior surface and do not inherit a
  presentation harness from generic implementation wording.
- Proof commands are validated before execution.
- Completion reports retain proof-binding and artifact IDs.
- Correction completion reports retain premise, reproduction, post-change
  proof, and owner-participation binding IDs.

## Phase 6: Component Adapter Integration

### Purpose

Connect existing TailTrail components without allowing them to reinterpret
host intent.

### Adapters

- Navigator requirement/scope adapter.
- Planning Lock adapter.
- Workflow runtime adapter.
- Test precision adapter.
- Evidence execution adapter.
- Closure and completion adapter.
- Delivery Record adapter.
- MCP adapter.
- Versioned component/adapter registry defining component IDs, accepted
  projections, emitted event types, schema versions, authority levels, and
  clarification permission.

### Adapter contract

```text
consume(finalized projection)
validate(input schema)
emit(evidence or clarification event)
```

A component may reject or request clarification through the pipeline, but it
may not contact the host or mutate the canonical contract.

### Tests

- Every adapter consumes the same anchor-bound packet view.
- Adapter rejection creates a typed clarification event.
- Unknown component IDs and unauthorized event types are rejected.
- CLI and MCP produce equivalent projections.
- Components cannot write host-facing questions directly.
- Old components can consume compatibility projections.

### Exit criteria

- All required components operate through projections.
- No component reads raw host conversation state.
- Projection audit can identify every consumer of each answer.

## Phase 7: Entry-Point, Recovery, and Security Hardening

### Purpose

Make the pipeline unavoidable and safe across all supported entry points.

### Deliverables

- Top-level CLI integration.
- Orchestration facade integration.
- MCP Start integration.
- Direct internal entry-point guard.
- Resume/replay support.
- Redaction and retention enforcement.
- Authorization checks for user decisions and approval.
- Audited `invalidated-false-premise` non-success disposition after activation,
  with reason codes including `already-satisfied-no-op`.
- Event ordering and concurrency controls.

### Tests

- CLI, facade, and MCP parity tests.
- Direct internal bypass attempts fail.
- Interrupted host exchange resumes from the last valid event.
- Concurrent answers cannot overwrite a newer anchor revision or packet view.
- Sensitive observations are redacted in reports and logs.
- Historical runs remain readable through a compatibility adapter.
- Contradictory post-activation evidence preserves the anchor and audit trail,
  prohibits project writes, and requires a separate corrected Start.
- Invalidated false-premise runs cannot finalize as successful delivery.

### Exit criteria

- There is one authoritative Start path regardless of entry point.
- Recovery does not lose accepted answers or create duplicate IDs.
- Sensitive host data is not copied into unrestricted artifacts.

## Phase 8: P7 and Correction-Premise End-to-End Validation

### Purpose

Use the original P7 failure and Issue 21 false-premise correction as the proving
scenarios for the complete pipeline.

### Negative scenario

```text
P7 goal with no declared owner or proof
  -> Navigator asks profile-specific questions
  -> host observations are incomplete
  -> clarification state
  -> no resolved delivery-record owner
  -> no test_delivery_record.py proof
  -> no Planning Lock
```

### Positive scenario

```text
Host declares proposed implementation, inspection, and proof paths
  -> Navigator validates observations
  -> packet finalized
  -> scope and proof projections share packet IDs
  -> implementation proceeds after approval
  -> created paths and proof command are verified
  -> completion report traces every answer and artifact
```

### Required evidence

- question-to-answer trace;
- answer-to-requirement trace;
- requirement-to-path-role trace;
- path-to-anchor trace;
- requirement-to-proof trace;
- proof-to-execution artifact trace;
- packet revision and invalidation trace;
- CLI/MCP parity result.

### Exit criteria

- The negative P7 scenario fails safely with clarification.
- The positive P7 scenario completes with complete lineage.
- No generic graph match becomes an owner or proof without accepted evidence.
- The same packet and binding IDs appear in all downstream artifacts.

### Issue 21 correction-premise scenarios

Negative scenario:

```text
Host reports a downstream scope failure
  -> proposes an upstream classifier as root cause
  -> direct evidence shows that classifier already provides the requested role
  -> premise becomes already-satisfied/contradicted
  -> no correction Planning Lock
  -> Navigator routes re-diagnosis to the next downstream transition
```

Unverified Debug scenario:

```text
Host reports a plausible defect with no authoritative reproduction
  -> command-free Debug Start records orientation only
  -> awaiting-reproduction-input
  -> separately approved reproduction
  -> premise accepted or contradicted
```

Positive scenario:

```text
Observed public-route failure with fresh evidence
  -> TailTrail derives owner participation at the first failing transition
  -> reproduction and post-change proof bindings cover the same symptom
  -> packet finalizes
  -> approval and activation may proceed
```

Post-activation contradiction:

```text
New read-only evidence proves the approved layer already satisfied the behavior
  -> invalidated-false-premise
  -> no cosmetic edit and no successful closure
  -> separate Start required for corrected scope
```

### Issue 21 phase and fix map

| Issue section | Owning phases | Planned fix | Required proof |
|---|---|---|---|
| 21.1 failing-premise gate | 0, 2, 3, 8 | Schema and questions for premise state; finalization gate; owner-participation derivation | already-satisfied and unverified corrections create no lock |
| 21.2 symptom-specific proof | 0, 3, 5, 8 | Separate reproduction/post-change bindings with assertion coverage | unrelated passing suite remains unresolved |
| 21.3 path-layer conflation | 2, 3, 4A, 4B | Host diagnosis stays a hypothesis; TailTrail records first failing transition and path-binding lineage | downstream failure cannot authorize an upstream owner |
| 21.4 activated no-op recovery | 1B, 6, 7, 8 | Append-only invalidation event and non-success terminal disposition | invalidated run blocks writes and cannot report successful closure |
| 21.5 one-time observations | 3-7 owning adapters | Focused regressions only; no new canonical host fields until reproduced | typed inspect envelope, proposed-new routing, role preservation, metadata isolation as separately owned tests |
| 21.6 corrected workflow | 2, 3, 5, 7, 8 | End-to-end premise-to-proof flow with approved Debug reproduction boundary | negative, unverified, positive, and post-activation scenarios above |

## Migration Strategy

Existing runs and components must remain usable during rollout.

1. Add readers that tolerate missing intake-contract fields in historical runs.
2. Generate compatibility projections for old requirement and scope artifacts.
3. Route new runs through the intake pipeline.
4. Migrate components one adapter at a time.
5. Keep old artifacts immutable and mark them as pre-pipeline.
6. Remove compatibility behavior only after retention and replay requirements
   are satisfied.

## Incremental Value by Phase

Every phase should ship independently useful value; the system must not wait
for Phase 8 before becoming safer.

| Phase | Independent value |
|---|---|
| 0 | Stable protocol, state, role, redaction, and compatibility definitions |
| 1A | Minimal IDs and correlation for early narration and questioning |
| 2 | Navigator-controlled host questioning, narration, and clarification |
| 1B | Full durability, replay, expiry, and anchor-bound packet views |
| 3 | Finalized requirements, packet lineage, and projection audit |
| 4A | Verified reuse of shipped scope and anchor enforcement |
| 4B | Answer-to-path authorization and residual edit-boundary lineage |
| 5 | Requirement-specific proof and rejection of nearby unrelated tests |
| 6 | Safe plug-and-play component integration without direct host access |
| 7 | CLI/MCP parity, recovery, replay, redaction, and entry-point hardening |
| 8 | End-to-end P7 and correction-premise validation and acceptance evidence |

The first major user-facing value arrives in Phase 2. The first major safety
value arrives in Phase 4B, while Phase 4A verifies the existing baseline. Phase
8 is the end-to-end proof, not the first point at which the architecture is
useful.

## Operational Metrics

Track at least:

- clarification rounds per run;
- accepted versus rejected observations;
- unused or contradicted answers;
- packet revisions;
- invalidated projections;
- stale component submissions;
- scope violations prevented;
- proof relevance failures;
- correction-premise states, re-diagnosis routes, and no-op plans prevented;
- unverified corrections routed to approved reproduction;
- replay and recovery outcomes;
- CLI/MCP projection parity.

## Implementation Risks

- A central pipeline could become a monolith. Keep adapters narrow and schemas
  versioned.
- Strict validation could create friction. Use task profiles and proposed-new
  roles rather than weakening evidence requirements.
- Packet revisions could invalidate expensive work. Make invalidation explicit
  and retain reusable evidence where its source bindings remain valid.
- Old components may bypass the pipeline. Guard all entry points and add parity
  tests before migration.
- Host observations may contain secrets. Redact at ingestion, not only during
  report rendering.
- A premise gate could be over-applied to new work. Apply it only when
  `change_intent=correction`; other profiles keep their existing criteria.
- Reproduction evidence may become stale. Bind it to target identity, relevant
  content fingerprints, command/artifact provenance, and observation time.

## Definition of Done

The implementation is complete when:

- Navigator is the only host-facing question boundary;
- central TailTrail services generate all authoritative IDs;
- host observations are accepted only through question/packet context;
- finalized packets are immutable views bound to one anchor version;
- every editable path is bound to an answer, packet view, and anchor version;
- every proof command is bound to a requirement;
- every correction has an accepted premise binding, derived owner-participation
  evidence, and separate symptom-specific reproduction/post-change proof;
- internal components consume projections and emit typed events only;
- CLI, orchestration, and MCP behavior is equivalent;
- incomplete P7 input produces clarification rather than inferred scope;
- complete P7 input produces end-to-end traceable evidence;
- historical runs remain readable.
- false-premise corrections cannot reach approval, and contradictions found
  after activation terminate audibly without cosmetic edits or successful
  closure.

## Independent Review Findings (read-only review captured before resolution)

The following findings came from an independent read-through against live,
shipped TailTrail behavior. They are retained as review history; their
dispositions are recorded in the resolution section below.

1. **Packet-version lifecycle contradicts the single-chain rule.**
   The design doc now states a packet version is only a pointer to an
   anchor version (`packet for anchor-v3`), never an independent
   lifecycle -- because two version histories for one evolving truth is
   the exact split-brain shape behind the anchor-versioning fixes
   (Issues Log 13/13a). This plan still builds a full packet-version
   lifecycle (`packet-revised` events, revision/invalidation rules,
   "changing a requirement creates a new packet version" tests, and a
   Definition-of-Done line demanding "immutable and versioned" packets).
   Both cannot be true. Recommendation: scope packet machinery down to
   pointer-plus-invalidation-on-anchor-revision, or revisit the
   single-chain rule explicitly -- do not leave both standing.
2. **The central ID service is assumed, never justified.** The plan
   mandates generated IDs with collision/ordering handling while the
   system already identifies everything by content fingerprint (no HA,
   ordering, or collision story needed). Either add one paragraph on
   what fingerprints cannot do, or prefer content hashes for lineage
   and reserve generated IDs for interaction-scoped objects (questions,
   answers, events) that genuinely lack stable content.
3. **Redaction section should cite solved work.** Shaped-secret
   rejection at ingestion plus prompt removal from router state already
   exist and are tested -- adopt them as the starting sensitive-pattern
   catalog instead of leaving redaction open-ended.
4. **Phase 4 is largely shipped.** Write-time scope checks, closure-time
   changed-path checks, anchor binding with fingerprints, and
   role-preserving path handling all exist with red-to-green tests.
   Mark it done rather than rebuilding it; the residual is an explicit
   answer-to-path authorization record, which is smaller than this
   phase implies.
5. **Build narration (Phase 2) before the ID service (Phase 1).**
   Highest user-visible value with the lowest architectural risk --
   the reverse of the listed phase order. The phase table itself
   concedes the first safety value arrives in Phase 4; narration
   moves user-visible value earliest without new stateful machinery.

## Review Resolution

The independent findings are accepted with these dispositions:

1. The anchor version is the only versioned truth. Packet IDs identify
  anchor-bound operational views and never form a second version chain.
2. Content fingerprints identify immutable contracts, projections, and
  artifacts. Generated IDs are reserved for interaction-scoped objects such
  as runs, questions, observations, answers, and events.
3. Redaction starts from the shipped shaped-secret and prompt-retention
  protections. Remaining work defines policy boundaries and extends the
  catalog only where evidence requires it.
4. Existing Phase 4 enforcement is a verified Phase 4A baseline. Phase 4B
  contains only the residual answer-to-path authorization and lineage work.
5. Delivery uses a thin Phase 1A foundation, then Phase 2 narration, followed
  by Phase 1B durability and replay. This preserves early user value without
  making the host flow depend on a complete event-store implementation.
