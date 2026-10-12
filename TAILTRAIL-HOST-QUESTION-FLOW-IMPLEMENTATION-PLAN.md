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
- Preserve resumability, replay, CLI/MCP parity, and historical artifacts.

## Non-Goals

- Replacing Navigator with a new host conversation engine.
- Allowing internal components to contact the host directly.
- Rewriting historical TailTrail runs.
- Making every observation a new packet version.
- Automatically approving inferred implementation ownership.

## Core Invariants

1. The central intake pipeline generates authoritative IDs.
2. Navigator is the only host-facing component.
3. The host submits observations; Navigator accepts or rejects answers.
4. Internal components consume finalized Navigator projections only.
5. Missing or contradictory information creates clarification, not inference.
6. A finalized packet is immutable; changed accepted decisions create a new
   packet version.
7. Every editable path is bound to an accepted answer, packet version, and
   immutable anchor.
8. Every proof command is bound to a requirement and must exercise that
   requirement.
9. Components return typed evidence or clarification events to the pipeline.
10. CLI, orchestration, MCP, and internal entry points use the same state
    machine and validation rules.

## Canonical Objects

| Object | Purpose | Created by |
|---|---|---|
| `run_id` | Identifies one TailTrail interaction | Intake pipeline |
| `contract_id` | Identifies the host input contract | Intake pipeline |
| `question_id` | Correlates a Navigator question and host response | Intake pipeline |
| `observation_id` | Identifies an ingested host observation | Intake pipeline |
| `answer_id` | Identifies a validated answer | Navigator through pipeline |
| `requirement_id` | Identifies a finalized requirement | Navigator through pipeline |
| `path_binding_id` | Binds a path to a role and requirement | Intake pipeline |
| `proof_binding_id` | Binds a proof path/command to a requirement | Intake pipeline |
| `packet_id` | Identifies a finalized operational packet | Intake pipeline |
| `packet_version` | Identifies a changed accepted decision set | Intake pipeline |
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
- Role enum for existing, proposed, inspection, proof, generated, excluded,
  and external paths.
- State transition table.
- Packet version and dependency invalidation rules.
- Redaction and retention policy.

### Required decisions

- JSON contract plus append-only JSONL event stream.
- Central ID generation and collision handling.
- Maximum clarification rounds and question count per round.
- User escalation conditions.
- Compatibility behavior for runs without a contract.

### Tests

- Schema validation tests.
- Unknown role/state rejection tests.
- ID uniqueness and deterministic replay tests.
- Packet-version compatibility tests.

### Exit criteria

- Schemas are versioned.
- Every canonical object has an owner and lifecycle.
- Invalid state transitions fail closed.
- No implementation component is required to interpret raw host answers.

## Phase 1: Central Intake and Event Store

### Purpose

Create the source of IDs, immutable contracts, and append-only event history.

### Deliverables

- Intake pipeline module.
- Central ID generator.
- Contract persistence.
- Append-only event writer.
- Idempotency key support.
- Resume and replay APIs.
- Event-to-contract integrity checks.

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
packet-revised
projection-created
projection-invalidated
approval-recorded
```

### Tests

- Replayed events produce the same materialized contract.
- Duplicate event submission is idempotent.
- Events from a stale run or packet are rejected.
- Contract fingerprints change only through approved revision events.
- Redacted values never reappear in derived artifacts.

### Exit criteria

- All IDs are generated centrally.
- Contracts and events can be recovered after interruption.
- The event stream can rebuild the current contract and packet state.

## Phase 2: Navigator Host Protocol

### Purpose

Make Navigator the exclusive host-facing question and clarification boundary.

### Deliverables

- Task profiler.
- Profile-specific question planner.
- Question issuance through the intake pipeline.
- Host observation ingestion.
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
received -> normalized -> evidence-checked -> accepted
                                  |
                    contradicted / insufficient
                                  |
                         clarification-required
```

### Tests

- Host cannot mark an answer accepted.
- Observations without an active question or packet context are rejected or
  routed for classification.
- Navigator can ask a follow-up question using the same requirement lineage.
- Dead ends escalate to the user instead of silently choosing a path.
- Documentation tasks receive fewer questions than new feature tasks.
- Clarification rounds resume after process interruption.

### Exit criteria

- Host questions and answers are visible through Navigator only.
- No Planning Lock is created before required answers are accepted.
- No internal component has a host communication path.

## Phase 3: Requirement and Packet Finalization

### Purpose

Turn accepted answers into one immutable operational packet.

### Deliverables

- Requirement builder.
- Path-role binding builder.
- Proof binding builder.
- Positive and negative criteria binding.
- Packet finalization command.
- Packet revision and dependency invalidation.
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
- Changing a requirement creates a new packet version.
- Dependent scope and proof projections are invalidated after revision.

### Exit criteria

- Navigator can emit `requirements-finalized`.
- The packet contains all requirement, path, proof, and criteria bindings.
- Every binding has source answer IDs.
- No downstream component needs raw host conversation data.

## Phase 4: Scope Projection and Authority

### Purpose

Strengthen path-change authority for every file category.

### Deliverables

- Scope projection adapter for Navigator.
- Anchor binding containing packet and path-binding fingerprints.
- Write-time scope check.
- Closure-time changed-path check.
- Existing/proposed path verification.
- Role-preserving handling for tests, docs, config/data, generated files, and
  external references.
- Multi-file role conflict detection.

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

- Every editable path is traceable to an accepted answer and packet version.
- Write-time and closure-time checks agree.
- Scope cannot be broadened by a downstream component.

## Phase 5: Proof and Validation Projection

### Purpose

Ensure proof is requirement-specific and cannot be replaced by a nearby test.

### Deliverables

- Proof projection adapter.
- Existing and proposed proof path handling.
- Requirement-to-command binding.
- Positive and negative assertion coverage.
- Proof relevance check.
- Managed execution evidence correlation.
- Stale proof invalidation after packet revision.

### Tests

- A Delivery Record test cannot satisfy an unrelated P7 requirement.
- A proposed proof path becomes required completion scope.
- A command with no requirement binding is rejected.
- A passing command that does not cover the requirement remains incomplete.
- Amended proof remains requirement-bound and auditable.

### Exit criteria

- Every required requirement has an explicit proof binding.
- Proof commands are validated before execution.
- Completion reports retain proof-binding and artifact IDs.

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

### Adapter contract

```text
consume(finalized projection)
validate(input schema)
emit(evidence or clarification event)
```

A component may reject or request clarification through the pipeline, but it
may not contact the host or mutate the canonical contract.

### Tests

- Every adapter consumes the same packet version.
- Adapter rejection creates a typed clarification event.
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
- Event ordering and concurrency controls.

### Tests

- CLI, facade, and MCP parity tests.
- Direct internal bypass attempts fail.
- Interrupted host exchange resumes from the last valid event.
- Concurrent answers cannot overwrite a newer packet version.
- Sensitive observations are redacted in reports and logs.
- Historical runs remain readable through a compatibility adapter.

### Exit criteria

- There is one authoritative Start path regardless of entry point.
- Recovery does not lose accepted answers or create duplicate IDs.
- Sensitive host data is not copied into unrestricted artifacts.

## Phase 8: P7 End-to-End Validation

### Purpose

Use the original P7 failure as the proving scenario for the complete pipeline.

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

## Migration Strategy

Existing runs and components must remain usable during rollout.

1. Add readers that tolerate missing intake-contract fields in historical runs.
2. Generate compatibility projections for old requirement and scope artifacts.
3. Route new runs through the intake pipeline.
4. Migrate components one adapter at a time.
5. Keep old artifacts immutable and mark them as pre-pipeline.
6. Remove compatibility behavior only after retention and replay requirements
   are satisfied.

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

## Definition of Done

The implementation is complete when:

- Navigator is the only host-facing question boundary;
- central TailTrail services generate all authoritative IDs;
- host observations are accepted only through question/packet context;
- finalized packets are immutable and versioned when accepted decisions change;
- every editable path is bound to an answer, packet version, and anchor;
- every proof command is bound to a requirement;
- internal components consume projections and emit typed events only;
- CLI, orchestration, and MCP behavior is equivalent;
- incomplete P7 input produces clarification rather than inferred scope;
- complete P7 input produces end-to-end traceable evidence;
- historical runs remain readable.
