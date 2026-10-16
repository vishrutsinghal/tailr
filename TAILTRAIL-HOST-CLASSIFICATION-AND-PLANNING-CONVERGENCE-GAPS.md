# TailTrail Host Classification and Planning Convergence Gaps

## Status and provenance

This document records observed TailTrail planning failures and proposes generic product corrections. None of the fixes described here are implemented merely because this document exists.

The document was created outside a TailTrail Planning Lock under an explicit user override. TailTrail could not create a valid plan for this new documentation file because the `REQ-ID=new:path` scope-answer route rejected an exact, goal-bound path even after deterministic new-file due diligence returned `new-confirmed`. That failure is recorded as Gap 5.

Implementation status (branch `tailtrail_v3`, user waived TailTrail ceremony for the fixes): Gaps 1–9 are implemented; the approval-audit gate below is implemented in the working tree and awaiting commit. See `## Implementation log` and the per-gap `Fix status` lines.

Primary incident evidence:

- Stopped run: `start-20261015145324-7ca58a`.
- Request mode supplied by the host: `implementation`.
- Intended implementation owner: `scripts/navigator_host_protocol.py`.
- Intended proof path: `tests/test_navigator_host_protocol.py`.
- Intended proof command: `python3 -m unittest tests.test_navigator_host_protocol tests.test_intake_pipeline tests.test_new_file_due_diligence -v`.
- Saved result: an `evaluation_harness` plan with no canonical scope decision, no implementation owner, and no registered proof command.

## Executive summary

TailTrail currently lets lexical routing run ahead of the host's typed understanding of the request. In the observed run, the words `proof` and `evidence` caused an implementation request to be classified as an Evaluation Harness request. That early return produced no `scope_evidence`. Later task-type and scope-quality safeguards were conditional on `scope_evidence` already existing, so they were skipped and a Planning Lock was persisted with `scope_decision: null`.

The mandatory host audit found the missing owner and proof. Correction then failed for two independent reasons: audit-generated commands omitted the required `--approved-proposal` marker, and planning revision applied a 500-character generic text limit to an already-valid 840-character canonical requirement whose intake contract allowed 1,000 characters.

The deeper product gap is that TailTrail already defines a structured host-input contract containing request mode, path roles, criteria, and proof, but the public Start flow does not consume it. The host therefore supplied complete information, but it remained prose rather than a validated projection used by routing and planning.

The generic correction is:

> The host proposes a typed, exact-request-bound interpretation. TailTrail validates its shape, grounding, repository evidence, path roles, and contradictions. Keywords remain fallback hints only. No accepted host contract, verified scope, and registered proof means no implementation Planning Lock.

## Problem statement

TailTrail needs to support semantically different requests that share the same vocabulary. For example:

- `Create a security proof report` can be read-only or validation-only.
- `Create the Phase 2 protocol and prove it` is implementation work.

A keyword list cannot reliably distinguish these requests. Expanding the list with more verbs only moves the false-positive boundary. Adding `create` as an implementation keyword would fix the observed sentence but break legitimate report-generation requests.

When a capable host is present, TailTrail should not attempt to replace the host's semantic interpretation with lexical guessing. The host should propose a typed classification, while TailTrail retains the essential enforcement responsibilities:

- validate the contract and bind it to the exact request;
- detect contradictions with explicit user authority;
- verify path roles through repository evidence and policy;
- reject or question incomplete scope and proof;
- prevent host narration from directly granting authority;
- fail closed before persisting a Planning Lock.

## Observed failure chain

```text
Host supplies an implementation request, proposed owner, proof path, and command
    |
    v
Goal contains the words "proof" and "evidence"
    |
    v
Navigator selects the Evaluation Harness early-return route
    |
    v
No canonical scope_evidence or scope_quality object is produced
    |
    v
The explicit --task-type implementation gate is skipped
because it only runs when scope_evidence already exists
    |
    v
The scope-quality gate is also skipped for the same reason
    |
    v
Planning Lock is created with scope_decision = null
    |
    v
Planning audit detects the missing owner, proof path, and command
    |
    +--> Suggested revision command fails because --approved-proposal is absent
    |
    +--> Corrected revision still fails before applying changes because
         the saved 840-character requirement is revalidated with a 500-character limit
```

This is not one isolated parsing error. It is a convergence failure across host interpretation, routing, scope, persistence, audit, and revision.

## Detailed gaps and root causes

### Gap 1: lexical routing can override the host's semantic classification

**Fix status: implemented** (`89085d9` Gap 1 routing precedence). `evaluation_only_requested()` takes the declared task type and a declared `implementation` always vetoes the eval-only route; no keyword list was extended. The declaration threads `task-start build_report()` → `navigator.decide()` before early-return selection, with `routing_evidence.authority_source` recording `declared-task-type` vs `keyword-fallback`.

`evaluation_harness_plan()` selects the Evaluation Harness when trigger words such as `proof`, `evidence`, or `report` appear and no `--changed` path is present. `evaluation_only_requested()` tries to veto that selection with another keyword list of code-action terms.

The approach is structurally fragile:

- synonyms and grammatical forms will always be incomplete;
- the same verb can describe a code change or a document-generation request;
- explicit request mode is stronger evidence than lexical matching;
- adding more terms increases false positives in a different direction.

In the observed run, `Create the Phase 2A Navigator Host Protocol...` did not match the hard-coded implementation verbs even though the host declared `--task-type implementation`.

### Gap 2: explicit task type is checked after the route that needs it

**Fix status: implemented** (`89085d9` plus `4c678fc` Gap 2 fail-closed lock). The declaration now enters routing before special-route selection, and a declared implementation with no resulting scope evidence returns a typed `missing-canonical-scope-evidence` boundary (exit 2, no run) instead of skipping the gate.

The public Start flow calls Navigator before passing the declared task type into routing. The later task-type gate runs only if `scope_evidence` is already a dictionary.

This creates a circular dependency:

1. The declaration is needed to prevent the wrong no-scope route.
2. The declaration is evaluated only after the selected route has produced scope.
3. The wrong route produces no scope.
4. The declaration is therefore never evaluated.

The host supplied the correct request type, but the product architecture prevented it from influencing the decision at the necessary point.

### Gap 3: missing scope evidence disables the safety gate instead of activating it

**Fix status: implemented** (`f5b1a95` Gap 3 pre-lock invariant). Immediately before `planning_lock.create`, a mode-aware invariant blocks declared implementation requests with missing/blocking scope quality, no canonical requirements, an invalid decision fingerprint, or any unresolved requirement row — typed `missing-canonical-scope-evidence` (and siblings), exit 2, no run. Read-only, validation-only, undeclared, and debug routes never trigger it.

The scope-quality gate currently applies only when `scope_evidence` exists. That is appropriate for genuinely read-only advisory routes, but unsafe for a declared implementation request.

For implementation, absence of canonical scope evidence is itself a blocking condition. It must never mean that the gate is not applicable.

The observed Planning Lock contained:

- no `scope_evidence`;
- no `scope_quality`;
- no `scope_decision`;
- no likely implementation paths;
- an unresolved proof row.

Despite that state, it was persisted as `awaiting-approval`.

### Gap 4: the host-input contract exists as a schema but is not a public runtime boundary

**Fix status: implemented** (`6d50035` Gap 4 intake; `21466bd` Gap 8 projection). `scripts/host_contract.py` parses one transport (inline/file/base64), validates shape, enums, path safety, and mode/authority consistency (`read-only`+owners and owner+proof same-path are `contradicted`; missing fields are `insufficient`), binds goal/target fingerprints, and returns `accepted` only. Accepted `implementation` maps into routing; the validated proof projection joins focused validation for single-requirement plans (multi-requirement stays recorded-only, no over-claim). MCP/adapter parity remains open.

`schemas/host-input-contract.schema.json` already models the correct concepts:

- task profile;
- change intent;
- request mode;
- behavior surface;
- positive and negative criteria;
- path bindings and path roles;
- new-file evidence;
- proof command and tiers;
- correction premise.

No runtime component currently consumes `tailtrail-host-input-contract` in the public Start path. The schema is therefore descriptive rather than authoritative.

Consequences:

- the host's request mode does not reliably control routing;
- path roles are repeated through separate flags and prose;
- the exact proof command is present in narration but absent from `validation_contract`;
- later components must rediscover or revise information the host already supplied;
- raw goal text is overloaded as both user intent and a machine-readable transport.

### Gap 5: verified new files cannot reliably enter canonical scope

**Fix status: implemented** (`b05b9ed` Gap 5 lane). `proposal_from_scope_answers()` strips `new:` before normalization/grounding, grounds the stripped path against the goal, runs full due diligence, asks the necessity question when same-directory owners share requirement vocabulary (`extend-or-justify`, fail closed), and emits validated `proposed_new_path` + `anchor_paths` + `convention_refs` rows. The confirmed root cause matched the hypothesis: the prefixed token was normalized and looked up instead of the stripped path.

While creating this document, deterministic new-file due diligence for `TAILTRAIL-HOST-CLASSIFICATION-AND-PLANNING-CONVERGENCE-GAPS.md` returned:

- verdict: `new-confirmed`;
- exact path does not exist;
- eligible application/documentation path;
- no name or symbol collision;
- no existing owner evidence;
- strong one-file-per-concern repository precedent.

The documented scope flow still failed:

1. Passing the path through `--changed` returned `changed-path-missing`. This is expected because `--changed` represents an existing or already-created editable target.
2. Starting without `--changed` correctly returned a canonical `SCOPE-Q1` packet and created no run.
3. Answering both requirements with `REQ-ID=new:TAILTRAIL-HOST-CLASSIFICATION-AND-PLANNING-CONVERGENCE-GAPS.md` returned:

   ```text
   answer-not-evidence-backed:new:TAILTRAIL-HOST-CLASSIFICATION-AND-PLANNING-CONVERGENCE-GAPS.md:ground-it-in-the-goal-or---changed
   ```

4. The exact path was already present in the goal.
5. Rebinding it as an explicit quoted literal did not change the rejection.
6. The unqualified `new:path` form was rejected with `answer-needs-requirement`, confirming that `REQ-ID=path` was required but not accepted.

No Planning Lock was created, which is the correct fail-closed outcome. The bug is that the valid new-file route cannot reach an accepted proposal.

Probable boundary failure: the `new:` answer is being checked against candidate evidence or goal grounding using the prefixed token rather than the normalized repository-relative path, or the quoted-literal/path grounding evidence is not propagated into the scope-answer validator. This must be proven in implementation rather than assumed from the external symptom.

### Gap 6: planning revision uses a stricter limit than canonical intake

**Fix status: implemented** (`e37e830` Gap 6 contract). One shared `MAX_CANONICAL_REQUIREMENT_STATEMENT_CHARS = 1500` in `requirement_discovery.py`, consumed by intake, both schemas, and revision; `_safe_statement(saved=True/False)` gives field-specific errors naming saved data vs new input; reasons/paths/IDs keep their own smaller limits.

Canonical requirement intake and its JSON schema allowed the observed 840-character requirement because their maximum was 1,000 characters. Planning revision later passed that saved statement through a generic helper capped at 500 characters.

As a result:

- a valid persisted plan became impossible to revise;
- the error incorrectly blamed `revision change statement`;
- adding short `statement` fields to the revision payload could not help because the failure occurred while loading the existing plan;
- proof projection fixes were never reached.

The requested interim product limit is now 1,500 characters. The important correction is not merely increasing one number; every producer, schema, loader, revision route, replay path, and error message must share the same contract.

### Gap 7: audit suggestions are not executable as emitted

**Fix status: implemented** (`0608bc5` Gap 7 renderer). Central `correction_command()` renders every executable suggestion with the complete payload, `--approved-proposal`, `--supersede-pending` only when pending, plus a shell-safe `--changes-base64` form; templates name `open_fields`; missing scope evidence yields `restart-required` with re-route guidance instead of a doomed `scope-add`. Tests parse every executable under a mirror of the real parser and apply one through real `propose()`.

Planning audit suggested `planning revise` commands without `--approved-proposal`, while the revision command requires that marker before it records a host-reviewed proposal.

The tests only verified that suggestion text contained terms such as `scope-add` or `proof-update`. They did not execute the rendered suggestion through the public CLI.

Audit guidance is part of the product contract. A suggested correction must either be executable or be explicitly labeled as a non-executable template with every unresolved field identified.

### Gap 8: proof information is transported as prose instead of a validated projection

**Fix status: implemented** (`21466bd` Gap 8 projection). `apply_host_contract_proof()` consumes the validated envelope (never regexes): single-requirement plans get the command in focused validation (compiled into `checks[]`), proof-role paths in candidate linkage with verified `existing`/`proposed` states, criteria unioned, owner paths recorded-but-never-promoted. No prose extraction exists anywhere.

The exact proof command appeared in the host's requirement text, but the requirement matrix derives only proof tiers from prose. This is safer than executing or authorizing arbitrary extracted shell text, but it leaves no supported structured Start input that carries the already-known command into `validation_contract`.

The correct fix is not command extraction with a regular expression. A command becomes authoritative only after it is supplied through a validated, exact-request-bound proof artifact and checked against path roles, requirement identity, tiers, and repository conventions.

### Gap 9: focused tests did not cover the complete public workflow

**Fix status: implemented** (`1f5874b` Gap 9 gate). `tests/test_public_route_gate.py` runs real subprocess CLIs in temp repos asserting artifacts and non-creation: declared-implementation skips eval, contradicted contracts create no run directory, accepted contracts route and record, and an audit→revise(`--approved-proposal`)→re-audit loop clears its finding. Each earlier gap added its own public-route tests (`decide()`, `evidence_document()`, propose→validate→record, intake→routing, 500/1000/1500/1501, real `propose()`).

The pulled fix correctly passed focused tests for:

- TailTrail self-source workspace eligibility;
- proof-projection rebuilding after a valid `proof-update`;
- stale proof projection detection.

Those tests began after routing, scope creation, and revision loading had already succeeded. They therefore did not cover:

- implementation requests containing Evaluation Harness trigger words;
- declared task type reaching Navigator before special-route selection;
- absence of scope evidence on an implementation Start;
- valid canonical requirements longer than 500 characters entering revision;
- executability of audit-rendered correction commands;
- new-file `REQ-ID=new:path` convergence;
- public host-input-contract ingestion.

The fix was valid within its tested boundary, but the boundary was too narrow to prove the customer-facing workflow.

## Generic target architecture

### Authority precedence

TailTrail should use this precedence order:

1. Explicit user request and explicit user approval.
2. Validated, exact-request-bound host-input contract.
3. Deterministic repository, policy, and scope evidence.
4. Heuristic keyword and classifier signals.

Lower-precedence evidence may detect a contradiction, but it must not silently override a higher-precedence decision. A material conflict becomes a question or a blocking state.

### Host responsibility

The host agent should understand the user request and propose a closed typed contract containing:

- `request_mode`: `implementation`, `read-only`, or `validation-only`;
- `change_intent`: correction, new capability, refactor, validation, or prose-only;
- task profile;
- behavior surface;
- exact change authority;
- path-role proposals;
- positive and negative success criteria;
- proof path, tiers, and runnable command;
- new-file evidence when applicable;
- confidence and evidence references;
- `private_reasoning_excluded: true`.

The host proposes meaning. It does not grant repository authority.

### TailTrail responsibility

TailTrail should validate and enforce:

- contract schema and supported version;
- exact goal and artifact hashes;
- allowed enum values;
- path normalization and workspace eligibility;
- path-role consistency;
- repository evidence supporting implementation owners;
- proof-only paths never becoming implementation owners;
- implementation paths never entering proof-only editable fields;
- request-mode and authority consistency;
- required positive and negative criteria;
- proof-to-requirement and command-to-tier bindings;
- new-file due diligence and post-implementation reachability;
- contradictions between host claims, explicit user wording, and deterministic evidence.

TailTrail returns one of three semantic validation states:

- `accepted`: complete, grounded, and non-contradictory;
- `insufficient`: one or more mandatory fields remain open;
- `contradicted`: supplied claims conflict with stronger authority or evidence.

Only `accepted` input may progress toward an implementation Planning Lock.

### Role of keyword routing

Keyword routing remains useful when no host is attached, but only as a fallback proposal:

- With an accepted host contract, keyword signals cannot override request mode or change intent.
- Without a host contract, heuristics may propose a profile and route.
- Material ambiguity triggers a bounded question.
- An unresolved fallback decision creates no implementation Planning Lock.

This preserves quick CLI usability without treating a vocabulary list as semantic authority.

## Proposed fixes

### Fix 1: make the validated host contract a first-class Start input

Add one public contract path shared by CLI, MCP, Codex, Copilot, and Claude. The transport may be an inline JSON value, base64 JSON, or an intake artifact ID, but every adapter must converge on the same validated artifact.

Required behavior:

1. Validate the host contract before Navigator routing.
2. Bind it to the exact goal, target identity, and referenced artifact hashes.
3. Store only normalized fields and evidence references; exclude private reasoning.
4. Pass accepted request mode and change intent into Navigator.
5. Pass proposed paths through Navigator scope verification instead of promoting them directly.
6. Project accepted criteria and proof into the canonical requirement matrix.
7. Preserve the contract ID and fingerprint through Planning Lock, approved anchor, execution handoff, and closure.

Raw narration may produce candidate answers, but it never directly creates the accepted contract.

### Fix 2: move declared request mode ahead of special routing

`task-start` should pass the validated request mode or declared task type into `build_report()` and `navigator.decide()` before Evaluation Harness, repository overview, or other early-return routes are selected.

Evaluation Harness-only routing is permitted when:

- the accepted mode is `read-only` or `validation-only`; or
- no host contract exists and fallback classification is unambiguous.

It is not permitted when accepted mode is `implementation`, even if the goal contains `proof`, `evidence`, `report`, `review`, `validation`, or similar words.

Do not fix this by adding `create` or more synonyms to the current keyword list. That would be a case-specific patch.

### Fix 3: add an independent fail-closed Planning Lock invariant

**Fix status: implemented, then extended to approval time.** `f5b1a95` enforces the pre-creation invariant (`implementation_lock_blockers()`); the follow-up approval-audit gate (working tree, uncommitted) enforces the same convergence at approval: `planning_lock.approve()` and `planning-revision approve()` run a fresh audit on the exact bytes being approved and refuse `gaps-found`, recording the receipt. Exemptions (debug, lean, legacy-thin, missing report) are explicit and recorded. Proof-disposition and per-slice owner cardinality remain open by design (see log).

Immediately before `planning_lock.create`, enforce a mode-aware invariant.

For `implementation`, require:

- accepted request-mode decision;
- sufficient canonical requirements;
- canonical scope evidence for every requirement;
- non-blocking scope quality;
- a non-null, fingerprint-bound scope decision;
- exactly the approved implementation-owner cardinality for each active slice;
- registered proof path and command, or an explicit unresolved proof question;
- no unresolved path-role conflict;
- no unresolved material host question.

If any item is missing, return a typed blocking report and create no run.

Read-only and validation-only routes may legitimately have no implementation owner, but that exception must be selected from accepted request mode, not inferred from a missing object.

### Fix 4: consume a validated proof projection

The canonical plan builder should consume a validated host-input-contract proof projection, not raw goal text or free-form narration.

Example shape:

```json
{
  "requirement_id": "REQ-01",
  "proof": {
    "path": "tests/test_navigator_host_protocol.py",
    "path_role": "proposed-proof-path",
    "tiers": ["unit"],
    "command": "python3 -m unittest tests.test_navigator_host_protocol tests.test_intake_pipeline tests.test_new_file_due_diligence -v"
  }
}
```

Before projection, TailTrail verifies:

- the requirement binding;
- normalized path role;
- existing or proposed state;
- new-file due diligence for proposed proof files;
- command-to-tier positional mapping;
- command consistency with the named proof path and repository runner;
- absence of implementation authority in proof-only fields.

The accepted projection atomically rebuilds `validation_contract.checks[]`, focused-validation rows, and the plan fingerprint.

### Fix 5: repair new-file scope-answer normalization and grounding

The `new:` prefix is a transport marker, not part of the repository path. Normalize the answer before grounding and evidence checks:

```text
REQ-01=new:path/to/file.md
        |   |
        |   +--> normalized relative path: path/to/file.md
        +------> proposed-state marker: new
```

The validator must:

1. Parse the requirement ID separately.
2. Strip and record the `new:` marker.
3. Normalize the repository-relative path.
4. Ground the normalized path against quoted literals, typed path bindings, or exact goal path tokens.
5. Consume deterministic new-file due-diligence evidence.
6. Create a proposed-owner candidate, never an already-approved owner.
7. Bind the candidate to the canonical scope packet and target fingerprint.
8. Require user approval before the proposed path becomes editable.

Positive grounding must not depend on `--changed`, because `--changed` asserts an existing editable target and cannot represent a file that has not been created.

### Fix 6: establish one 1,500-character canonical statement contract

Introduce one named contract constant, for example:

```text
MAX_CANONICAL_REQUIREMENT_STATEMENT_CHARS = 1500
```

Use the same limit in:

- host requirement interpretation;
- canonical requirement-set schema;
- requirement sufficiency and normalization;
- requirement add/update revision;
- saved-report loading;
- approved-anchor construction;
- replay and recovery;
- imported requirement adapters where TailTrail owns normalization.

Rules:

- accept 1 to 1,500 characters;
- never silently truncate;
- reject 1,501 characters with a precise error;
- prefer multiple atomic requirement rows when the request has separable outcomes;
- keep unrelated fields such as revision reasons on their own smaller limits;
- identify whether an error concerns saved canonical data or new revision input.

The limit is a safety ceiling, not a recommended requirement size.

### Fix 7: make audit corrections executable and authority-aware

Centralize correction rendering instead of assembling partial shell snippets inside each finding.

Every executable suggestion should include:

- exact run ID and requirement ID;
- complete validated change payload;
- `--approved-proposal` where required;
- portable `--changes-base64` encoding;
- `--supersede-pending` only when a pending revision actually exists;
- the required authority marker or a clearly identified open question.

If canonical scope evidence is absent, audit must not suggest that a plain `scope-add` can repair the plan. It should emit a blocking `missing-canonical-scope-evidence` finding and require re-routing or an evidence-bound host scope proposal.

Audit output should distinguish:

- executable correction;
- non-executable template awaiting host information;
- restart-required conformance failure.

### Fix 8: make revision validation field-specific

Replace the generic use of `_safe_text()` for canonical requirement statements with field-specific validators:

- canonical requirement statement: 1-1,500 characters;
- revision reason: bounded separately, for example 1-500 characters;
- path: repository-relative and traversal-safe;
- proof command: non-empty, bounded, and preserved exactly;
- display ID: short identifier contract;
- evidence-plan item: its own bounded text contract.

When loading a saved report, errors must say `saved canonical requirement` rather than `revision change`. A valid saved plan must never become unrevisionable under a stricter downstream limit.

### Fix 9: add public-route convergence tests

Unit tests remain necessary, but the release gate must also cover complete public workflows from host input through Planning Lock and revision.

The test harness should assert both artifact contents and negative non-creation of runs.

## Delivery phases

### Phase A: immediate fail-closed safety

Purpose: prevent invalid implementation locks before adding new functionality.

Deliverables:

- Pass declared request mode into pre-route evaluation.
- Block implementation Planning Locks when scope evidence or scope decision is absent.
- Add regression coverage for implementation goals containing Evaluation Harness vocabulary.
- Preserve genuine read-only Evaluation Harness routing.

Exit criterion: the original Phase 2A request creates no no-scope Planning Lock.

### Phase B: requirement and revision contract convergence

Purpose: make every valid canonical requirement revisable.

Deliverables:

- Shared 1,500-character contract.
- Field-specific validation errors.
- Audit commands containing required proposal markers.
- Public CLI tests that execute rendered corrections.

Exit criterion: a valid 1,500-character requirement can enter Start, receive a proof revision, rebuild projections, and remain approval-ready.

### Phase C: new-file scope convergence

Purpose: make the documented `new:` route usable without misusing `--changed`.

Deliverables:

- Normalize `REQ-ID=new:path` before grounding.
- Bind due-diligence evidence to the scope packet.
- Persist proposed-owner state without granting approval.
- Support one proposed file shared by multiple requirements without duplicating authority.
- Add negative collision, ineligible-path, stale-packet, and ungrounded-path cases.

Exit criterion: the documentation request that produced this file reaches an awaiting-approval Planning Lock whose only implementation owner is the proposed Markdown file.

### Phase D: host-input-contract runtime integration

Purpose: replace keyword authority and prose transport with a validated public contract.

Deliverables:

- CLI and MCP ingestion.
- Codex, Copilot, and Claude adapter parity.
- Exact-goal and artifact hash binding.
- Accepted/insufficient/contradicted state machine.
- Projection into routing, scope, requirements, criteria, and proof.
- Bounded clarification and user-decision escalation.

Exit criterion: all supported hosts produce the same canonical plan from the same validated contract.

### Phase E: end-to-end qualification and migration

Purpose: prove the behavior across installations and preserve compatible routes.

Deliverables:

- Wheel and source-distribution tests.
- CLI/MCP/host-adapter parity tests.
- Replay and recovery tests.
- Legacy raw CLI fallback behavior.
- Observability explaining which authority selected each route.
- Documentation and migration notes.

Exit criterion: release qualification proves positive behavior and all fail-closed negative cases.

## Acceptance criteria

### Positive cases

1. A host-declared implementation request containing `proof`, `evidence`, `report`, `review`, and `validation` remains an implementation route.
2. A host-declared read-only request containing `create`, `generate`, or `produce` remains read-only.
3. An accepted host contract projects request mode, criteria, path roles, proof tiers, and exact commands into the canonical plan.
4. A proposed new file grounded in the exact goal and verified by due diligence becomes a proposed owner candidate.
5. One proposed file may serve multiple requirements while retaining one path identity and requirement-specific mappings.
6. Requirement statements of 500, 1,000, and 1,500 characters survive Start, revision, approval, anchor construction, handoff, and replay.
7. Audit-generated executable corrections run successfully through the public CLI.
8. A valid proof update atomically rebuilds checks, focused validation, and fingerprints.
9. Codex, Copilot, Claude, CLI, and MCP converge on the same normalized contract.

### Negative cases

1. Missing host contract fields produce `insufficient` and no implementation Planning Lock.
2. A read-only contract carrying edit authority is `contradicted`.
3. An implementation contract with no scope evidence creates no run.
4. A proof-only path cannot become an implementation owner.
5. An implementation-owner path cannot be smuggled through proof-only fields.
6. Raw narration cannot grant request mode, path authority, or proof authority.
7. A stale goal, target, artifact, scope-packet, or contract fingerprint fails closed.
8. A new path with collision, ineligible workspace role, or contrary owner evidence is rejected or questioned.
9. A requirement statement of 1,501 characters fails with no truncation and no partial persistence.
10. A tier without a positional proof command remains unresolved.
11. An audit suggestion missing required authority is never labeled executable.
12. An Evaluation Harness heuristic cannot override an accepted implementation contract.

## Required regression scenarios

| Scenario | Expected result |
| --- | --- |
| `Create a security proof report` with `request_mode=read-only` | Evaluation/report route; no implementation owner required |
| `Create the Phase 2 protocol and prove it` with `request_mode=implementation` | Navigator implementation scope; Evaluation Harness may be supporting evidence only |
| Implementation mode with no `scope_evidence` | Typed blocking response; no run directory and no Planning Lock |
| Exact `REQ-01=new:docs/new-design.md` with confirmed due diligence | Proposed-owner candidate bound to the packet; still awaiting user approval |
| Same new path absent from goal and path bindings | Rejected as ungrounded |
| Same new path collides with an existing concern | Collision-blocked; no scope promotion |
| Valid 1,500-character saved requirement plus `proof-update` | Revision proposal succeeds and projections converge |
| 1,501-character requirement | Precise validation error; no persistence |
| Audit finding with executable repair | Rendered command includes complete payload and required proposal marker |
| Raw narration containing a shell command | Observation only; command is not authoritative until validated into proof binding |

## Observability requirements

Every Start and revision report should expose:

- request-mode authority source;
- host-contract ID and fingerprint when present;
- whether keywords were used as fallback;
- any contradiction and the evidence that caused it;
- scope-evidence state and decision fingerprint;
- proposed versus approved path roles;
- proof-binding source and requirement IDs;
- Planning Lock invariant evaluation;
- exact reason no run was created when blocked.

This information should be compact in normal output and available in full JSON for audit. It must exclude private reasoning.

## Compatibility and migration

- Existing raw CLI users may continue without a host contract, but heuristic routing must fail closed on material ambiguity.
- Existing accepted plans remain immutable.
- Existing requirements between 501 and 1,000 characters become revisable rather than requiring migration.
- Raising the canonical maximum to 1,500 requires schema-version-compatible validation updates across every producer and consumer in one release.
- Legacy plans missing scope evidence must not be silently treated as v2-valid. They require restart or an explicit migration route that preserves approval boundaries.
- Host adapters must share one conformance suite so behavior cannot drift by provider.

## Non-goals

- TailTrail should not expose or persist host private chain-of-thought.
- TailTrail should not trust host path ownership without repository evidence.
- TailTrail should not infer executable proof commands from free-form prose.
- TailTrail should not remove all keyword routing; it remains a useful no-host fallback.
- TailTrail should not make `--changed` represent a file that does not yet exist.
- TailTrail should not weaken user approval or Planning Lock immutability.
- TailTrail should not treat a larger statement limit as permission to collapse unrelated outcomes into one requirement.

## Recommended implementation boundaries

These are investigation targets, not pre-approved implementation owners:

- Navigator routing and Evaluation Harness selection.
- Start request-mode propagation and pre-lock invariants.
- Host-input-contract validation and projection.
- Navigator scope-answer parsing and new-file evidence binding.
- Canonical requirement validation and schemas.
- Planning audit correction rendering.
- Planning revision loading and proof projection.
- CLI, MCP, and host-adapter conformance tests.

Each implementation run must establish its own evidence-backed owner and proof roles before editing.

## Implementation log

Branch `tailtrail_v3` (TailTrail ceremony waived by the user for these fixes; every change red-proven and measured):

| Commit | Gap | What landed |
| --- | --- | --- |
| `89085d9` | 1, 2 | Declared `implementation` vetoes the eval-only route before early-return selection; `routing_evidence.authority_source` |
| `4c678fc` | 2 | `missing-canonical-scope-evidence` boundary: no scope on implementation means no run |
| `f5b1a95` | 3 | `implementation_lock_blockers()`: quality, requirements, decision fingerprint, per-requirement scope |
| `6d50035` | 4 | `scripts/host_contract.py`: parse/validate/bind (`accepted`/`insufficient`/`contradicted`), `--host-contract` transports, routing + recorded authority |
| `21466bd` | 8 | `apply_host_contract_proof()`: validated command into focused validation/`checks[]`, single-requirement scope |
| `b05b9ed` | 5 | `new:` stripped before grounding, due diligence, necessity question, `declared-new` proposed lane |
| `e37e830` | 6 | Shared 1500-char ceiling, `_safe_statement(saved=True/False)`, schema bumps |
| `0608bc5` | 7 | Central correction renderer with `--approved-proposal`, portable base64 form, kind labels |
| `1f5874b` | 9 | `tests/test_public_route_gate.py`: subprocess Start/audit/revise loops with non-creation asserts |
| uncommitted | 3 ext | Approval-audit gate: `require_clean_audit()` in `planning_lock.approve()` and `planning-revision approve()`; recorded `debug`/`lean`/`legacy-thin`/`missing-report` exemptions |

Open by design: proof-disposition and per-slice owner cardinality at lock time; MCP/Codex/Copilot/Claude parity; replay/recovery and packaging qualification; multi-requirement contract proof projection (recorded-only, no over-claim).

## Definition of done

The issue is complete only when all of the following are true:

1. [x] Host semantic classification is a validated proposal and keyword routing is fallback-only.
2. [~] Implementation cannot persist without accepted request mode, canonical scope, and proof disposition. (Mode/scope/fingerprint gated at creation and approval; per-tier proof disposition and owner cardinality still advisory.)
3. [~] The existing host-input-contract schema is exercised by the public runtime. (CLI done; MCP/adapters open.)
4. [x] New-file scope answers work through the documented evidence-first route.
5. [x] The 1,500-character canonical statement contract is consistent across schemas and code.
6. [x] Audit corrections are executable or explicitly non-executable.
7. [x] Revision accepts every statement that canonical intake accepts.
8. [~] Positive and negative public-route regressions pass for CLI, MCP, and all supported hosts. (CLI done; MCP/hosts open.)
9. [x] Completion evidence names exact commands, results, remaining risks, and any skipped qualification. (This log plus per-commit red/green reports.)

