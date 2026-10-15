# TailTrail Canonical Plan Projection Failure During AIDLC Enablement

## Correct framing

This work was **not** an attempt to adopt or redesign an AIDLC
question-and-answer workflow as a product feature.

The product work was to make Full AIDLC usable as an integrated TailTrail
capability:

- ship the pinned official pack with TailTrail;
- avoid a separate AIDLC installation;
- provision and detect it through normal TailTrail paths;
- support Codex, Copilot, and Claude; and
- prove the installed product works offline and fails closed on integrity
  problems.

TailTrail happened to route the rejected narrow plan through a component named
**AIDLC Requirements mode**. That mode was only the planning recovery path used
to clarify the incomplete plan.

The defect observed in both cycles was:

> TailTrail saved the expanded answers, but rendered the same original canonical requirements, scope, and unit-only proof plan.

Therefore, the primary corrective target is TailTrail's **canonical plan
revision and projection path**. It is not a new system for incorporating AIDLC
questions and answers.

## Run and evidence boundary

- Planning run: `start-20261015052506-d968a5`
- Cycle 1 events: requirements request 10, answer 11, rejection 12
- Cycle 2 events: requirements request 14, answer 15, rejection 16
- No AIDLC implementation, test, scanner, or Git operation ran under the
  rejected planning run.

Evidence comes from:

- `.tailtrail/runs/start-20261015052506-d968a5/planning/lock-v1.json`;
- `.tailtrail/runs/start-20261015052506-d968a5/planning/aidlc-requirements-v1.json`;
- `.tailtrail/runs/start-20261015052506-d968a5/planning/aidlc-revised-requirements-v1.json`;
- `.tailtrail/runs/start-20261015052506-d968a5/events.jsonl`; and
- the exact host submissions recorded in this conversation.

The source-code root cause has not been inspected. File ownership and internal
failure points below remain investigation candidates until proven at the real
public call site.

## Product requirement

The intended product outcome was:

1. Full AIDLC is bundled and integrated with TailTrail.
2. Users do not separately install the official AIDLC pack.
3. A normal TailTrail install contains the pinned rules, version, license,
   provenance, and SHA-256 integrity metadata.
4. Provisioning works without network access.
5. The public Full-mode route consumes the bundled pack and never silently
   downgrades a Full request to Lite.
6. Codex, Copilot, and Claude receive the supported integration.
7. Missing, altered, stale, incompatible, or unsafe destination state fails
   closed.
8. Built wheel and source distribution installations, public routes, host
   projections, and negative integrity cases provide executable proof.

## Original narrow TailTrail goal

The host initially persisted this narrower goal:

```text
Implement offline bundled-pack provisioning in scripts/aidlc-official-install.py. Only scripts/aidlc-official-install.py is editable; aidlc-rules and scripts/aidlc-official-detect.py are inspection-only; tests/test_aidlc_official_install.py is proof-only. A clean target must produce a detector-compatible SHA-256 manifest with official license and provenance and no network use; missing or altered bundled assets and an existing destination must fail closed. Proof command: python3 -m unittest tests.test_aidlc_official_install.
```

This was a host-input mistake. It reduced an installed-product outcome to one
editable helper and one unit-test path. The later planning cycles attempted to
correct that narrow plan before implementation.

---

## Cycle 1

### Requirement boundary shown by TailTrail

| ID | Requirement |
| --- | --- |
| REQ-01 | Implement offline bundled-pack provisioning in `scripts/aidlc-official-install.py`. |
| REQ-02 | Only `scripts/aidlc-official-install.py` is editable. |
| REQ-03 | `aidlc-rules` and `scripts/aidlc-official-detect.py` are inspection-only. |
| REQ-04 | `tests/test_aidlc_official_install.py` is proof-only. |
| REQ-05 | A clean target must produce a detector-compatible SHA-256 manifest with official license and provenance and no network use. |
| REQ-06 | Missing or altered bundled assets and an existing destination must fail closed. |
| REQ-07 | Proof command: `python3 -m unittest tests.test_aidlc_official_install`. |

### What the host understood

The plan needed to expand from one helper to the complete installed-product
boundary:

```text
TailTrail distribution
  -> bundled pinned AIDLC assets and legal/provenance metadata
  -> normal offline TailTrail installation
  -> detector, bridge, and public Full-mode route
  -> Codex, Copilot, and Claude projection
  -> wheel/sdist and negative integrity proof
```

This did not mean the host could grant itself new write authority. Newly named
paths could only be requested as owner candidates; Navigator evidence still
had to resolve every `implementation-owner`. Inspection and proof paths had to
remain non-editable.

### Prompt submitted to TailTrail

The host entered the required recovery route:

```text
python3 scripts/tailtrail.py planning aidlc-requirements --run-id start-20261015052506-d968a5
```

It then submitted these material answers:

| Question | Choice | Host answer |
| --- | --- | --- |
| Q1 | Other | The user-visible result is that TailTrail Full AIDLC works after a normal TailTrail install with no separate official-pack installation. The public host route must select Full mode and report the bundled pinned pack and provenance. |
| Q2 | B | The compatibility boundary includes source assets, Python wheel and sdist packaging, release manifests, the normal TailTrail installer/bootstrap path, detector and bridge contracts, and automatic Codex, Copilot, and Claude host projection. Existing Lite behavior may remain only when explicitly selected; Full mode must not silently downgrade. |
| Q3 | B | Require focused unit tests plus integration and distribution-contract proof: build wheel and sdist, install each into clean temporary environments without network access, verify bundled license/provenance/SHA-256 integrity, run the public detection and Full-mode route, exercise supported host projections, and prove tampered or missing assets fail closed. |
| Q4 | B | Expand the requirement boundary and proof plan to cover the complete product outcome. Split implementation ownership into focused TailTrail runs where needed for bundled assets and provenance, package/release manifests, installer/bootstrap integration, detector/bridge public behavior, host projections, and their real-call-site tests. Before presenting the revised plan for approval, the host must compare every user outcome, constraint, path role, positive and negative criterion, public call site, and executable proof against the saved plan; any gap must be corrected through TailTrail. |

### TailTrail result

TailTrail recorded the choices and details but rendered the same seven
requirements shown above.

The material scope still contained only:

| Path | Rendered role |
| --- | --- |
| `scripts/aidlc-official-install.py` | implementation owner/candidate |
| `tests/test_aidlc_official_install.py` | proof-only test evidence |

The only concrete validation command remained:

```text
python3 -m unittest discover -s tests -p test_aidlc_official_install.py -v
```

### Why Cycle 1 was rejected

The host review found that the saved expansion was absent from the canonical
requirements, scope, and proof projection:

- distribution assets and provenance had no owner candidate to resolve;
- wheel/sdist and release manifests were absent;
- normal installer/bootstrap integration was absent;
- detector, bridge, CLI/MCP, and no-silent-fallback behavior was absent;
- Codex, Copilot, and Claude projections were absent; and
- installed wheel/sdist, public-route, and negative-integrity proof was absent.

REQ-01, REQ-05, and REQ-06 remained useful narrow behaviors. REQ-02, REQ-03,
REQ-04, and REQ-07 were rejected because their scope and proof boundary could
not deliver the requested product outcome.

---

## Cycle 2

### What the host understood

Because the first expansion answer was saved but did not change the rendered
plan, the second cycle described the corrected product boundary more
explicitly:

1. bundled official rules, version, license, provenance, and hashes;
2. Python wheel, sdist, and release-manifest inclusion;
3. transactional normal-install provisioning without network access;
4. detector, bridge, CLI, and MCP Full-mode consumption without silent Lite
   fallback;
5. Codex, Copilot, and Claude projection; and
6. focused real-call-site and clean-install proof.

### Prompt submitted to TailTrail

The same recovery command was used on the same run:

```text
python3 scripts/tailtrail.py planning aidlc-requirements --run-id start-20261015052506-d968a5
```

The host then submitted:

| Question | Choice | Host answer |
| --- | --- | --- |
| Q1 | B | Required public outcome: a normal TailTrail installation immediately supports Full AIDLC for Codex, Copilot, and Claude without a separate AIDLC install, and reports the pinned bundled pack, version, integrity, license, and provenance. |
| Q2 | B | Preserve the compatibility contract across bundled `aidlc-rules` assets, Python wheel/sdist contents, release manifest, normal TailTrail installer/bootstrap, official detector and bridge, CLI/MCP public route, and Codex/Copilot/Claude host projections. Explicit Lite mode may remain; requested Full mode must never silently downgrade or fetch from the network. |
| Q3 | B | Exact proof boundary must contain owner-focused unit tests, public CLI/MCP integration tests, package build and content inspection, clean offline installs from both wheel and sdist, detector and Full-mode execution, all supported host projections, and negative missing/tampered/stale/existing-destination cases. |
| Q4 | Other | Replace the narrow boundary with a multi-run delivery batch: bundle the pinned official assets and metadata; include them in package and release manifests; provision them through normal installation; consume them through detector, bridge, CLI, and MCP Full mode; project them to Codex, Copilot, and Claude; and add real-call-site plus clean wheel/sdist proof. Each implementation file must be resolved through focused TailTrail scope, and the host must reject any omitted outcome, owner, public call site, negative criterion, or runnable proof. |

### TailTrail result

The saved `aidlc-revised-requirements-v1.json` contained the expanded answers.
Nevertheless, TailTrail again rendered:

- the same original seven canonical requirement rows;
- the same single implementation candidate;
- the same proof-only test path; and
- the same unit-only concrete command.

The evidence-capability section also continued to classify every requirement
as unit-tier only despite the recorded integration and distribution-proof
answer.

### Why Cycle 2 was rejected

The second result was internally contradictory:

| Persisted input | Rendered canonical result |
| --- | --- |
| Normal install supports Full AIDLC on all supported hosts | One provisioning helper owner |
| Packaging, release, installer, detector, bridge, CLI/MCP, and host boundaries | Those surfaces absent |
| Unit plus integration and distribution proof | Unit-only concrete proof |
| Six focused delivery slices | Original seven narrow rows repeated |

The complete proposal was rejected because approving it would freeze an
anchor that contradicted the persisted correction.

The event-16 rejection reason was:

```text
Mandatory host plan review failed. Two AIDLC Requirements cycles recorded the full six-slice product boundary, but TailTrail regenerated the unchanged one-file requirements and proof plan. The proposal still omits distributable bundled assets and provenance ownership, Python and release packaging manifests, normal installer/bootstrap integration, public detector/bridge Full-mode routing without silent Lite fallback, Codex/Copilot/Claude projections, and exact clean wheel/sdist offline proof. This plan must not be presented as approval-ready or implemented.
```

---

## Exact issue statement

The problem is not that TailTrail lacked a mechanism to ask AIDLC-branded
questions. The questions were asked and the answers were saved.

The failing transition was:

```text
expanded correction persisted
  -> canonical requirements remained original
  -> scope remained original
  -> proof contract remained original and unit-only
  -> renderer labeled the unchanged result as revised
```

This is a canonical revision/projection integrity failure.

### Confirmed behavior

- Both expanded answer sets were persisted.
- The rendered canonical requirements did not incorporate them.
- The rendered scope did not incorporate the additional product surfaces.
- The concrete validation contract did not incorporate the requested
  integration and distribution proof.
- TailTrail still produced approval wording for the unchanged plan.

### Not yet confirmed

- The exact function or source line that reused the original requirements.
- Whether the defect is caused by stale input, incorrect artifact selection,
  missing projection logic, or renderer selection.
- The final implementation owner.

Those points require a separate read-only call-chain investigation before a
code correction plan is approved.

## Corrected proposed fix

### Principle

Do not redesign the AIDLC question system. Repair the boundary between any
persisted material planning correction and the canonical plan that TailTrail
renders and asks the user to approve.

An answer or correction is still non-authoritative input. It must either:

1. produce a new canonical proposal whose requirements, Navigator-resolved
   scope, and proof contract reflect the correction; or
2. leave the run `revision-required` with an explicit unresolved question or
   scope/proof gap.

It must never persist the correction and render the old plan as revised.

### Fix 1: identify the first failing projection transition

Before implementation, trace the real public route used in this incident:

```text
planning aidlc-answer
  -> persisted revised-answer artifact
  -> materiality classification plus grounding and completeness validation
  -> validated correction-projection artifact
  -> canonical requirement selection/build
  -> Navigator scope projection
  -> validation-contract projection
  -> revised-report renderer
  -> approval gate
```

At every transition, record the input artifact path and fingerprint. The first
stage that receives the expanded answer artifact but emits the original
canonical fingerprint is the correction owner.

Do not assume the failure lives in the question generator merely because the
public command is called `aidlc-answer`.

### Fix 2: make canonical projection consume a validated correction projection

The canonical-plan builder must consume the active, versioned **validated
correction-projection artifact**, not raw free-form answers, a merely persisted
answer artifact, or the original Start requirement list, when producing a
revised proposal.

Raw narration and answers remain non-authoritative observations. Before a
correction-projection artifact can be created, TailTrail must classify whether
the input is material, validate its grounding against the bound source, and
validate that every required field is complete. The artifact must retain the
source-answer fingerprint and those validation results. If grounding or
completeness fails, no correction-projection artifact is created; the run
remains `revision-required` with the missing or invalid fields stated as open
questions.

For every materially affected requirement it must produce or request:

- revised outcome and preservation text;
- positive and negative criteria;
- requested owner candidates for Navigator evaluation;
- explicit inspection and proof-only roles;
- exact proof tiers and runnable commands; and
- public-route or host-projection coverage when named.

The host may submit only a requested path role or proposed owner candidate.
Only Navigator scope evidence may promote that candidate to
`implementation-owner`. An unresolved candidate remains a question. A
test/inspection path must never be passed through an editable owner field or
`--changed`.

If the correction introduces multiple independent owners, the original
single-owner run must remain blocked and TailTrail must route to focused plans.
That route is a consequence of canonical scope reconciliation; it does not
require redesigning the AIDLC question system.

### Fix 3: update requirements, scope, and proof atomically

A revised proposal is valid only when all three projections agree:

| Projection | Required result |
| --- | --- |
| Requirements | Every persisted material outcome and constraint maps to a canonical row or an explicit open question. |
| Scope | Every named path has Navigator-resolved authority or remains unresolved; inspection/proof paths remain non-editable. |
| Proof | Every positive and negative criterion has the required tier and exact runnable command, or remains an explicit blocker. |

TailTrail should build these projections in memory, validate them together,
then persist a new immutable revision. If any projection fails, it must write
no approval-ready report.

### Fix 4: add a correction-to-plan consistency gate

Before rendering approval wording, compare the persisted correction with the
new canonical proposal.

The gate must detect at least:

- a material correction with an unchanged canonical requirement fingerprint;
- named product surfaces missing from scope;
- integration or distribution proof reduced to unit-only proof;
- named public behavior without positive and negative criteria;
- supported hosts omitted without an explicit user decision; and
- an unresolved owner hidden behind approval wording.

For this incident the expected failure would be:

```text
canonical-revision-projection-mismatch

The persisted correction materially expands requirements, scope, and proof,
but the rendered canonical requirement, scope, and validation fingerprints are
unchanged. The run remains revision-required and cannot be presented or
approved.
```

### Fix 5: render from one canonical revised object

The machine-readable revised proposal, human-readable report, scope table,
validation table, and approval gate must consume the same canonical revised
object and fingerprints.

The renderer must not independently fall back to the original Start report.
If the revised object is missing or inconsistent, render a blocking diagnostic,
not the previous plan with a “revised” label.

### Fix 6: keep host review as a safety gate, not the primary repair

Mandatory host review remains valuable because it caught the defect. It is not
the mechanism that should translate answers into canonical requirements.

The review should verify that:

- every requested product outcome appears in the canonical requirements;
- Navigator-resolved scope matches those requirements;
- positive, negative, public-route, and installed-product proof is concrete;
- no unresolved question is hidden; and
- the rendered plan and machine-readable proposal share the same fingerprints.

A current passed review may make a proposal `approval-ready`. It cannot repair
missing projection data and cannot mint or activate an approved anchor.

### Authorization invariant

The following artifacts are proposals or checks only:

- persisted correction/answer;
- revised canonical proposal;
- Navigator scope proposal or decision before approval;
- validation contract; and
- host-review receipt.

None grants implementation authority. Only explicit user approval may mint
the approved anchor. Existing activation rules still apply after approval.

### Existing lifecycle mapping

This fix extends the current Planning Lock; it does not create a parallel
lifecycle:

| Condition | Existing lifecycle result |
| --- | --- |
| Material correction persisted | Lock remains non-approved; revision projection begins. |
| Projection incomplete or inconsistent | `revision-required`; writes forbidden. |
| Projection complete but not host-reviewed | `host-review-required` presentation status; lock still non-approved. |
| Current host review passes | `approval-ready` presentation status; no approved anchor yet. |
| User explicitly approves | Approved anchor may be minted through the existing approval/revision-approval route. |
| Existing activation command succeeds | Execution handoff becomes available. |

`planning revise` remains the pending-revision mechanism.
`revision-approve` may approve—and, where current behavior intentionally does
so, activate—only after explicit user approval of the current reviewed
fingerprints. `planning activate` consumes an already approved anchor and must
not repair missing projection or review data.

## Candidate implementation surfaces

These are investigation candidates, not confirmed owners:

| Candidate | Question to answer during root-cause tracing |
| --- | --- |
| `scripts/planning_lock.py` | Does the answer/revision transition persist expanded input but pass the original requirement list to the next stage or renderer? |
| `scripts/aidlc-requirements.py` | Does the requirements-stage result expose a revised canonical proposal, or only store answer metadata? |
| `scripts/planning-revision.py` | Can the existing revision model carry the corrected requirement, scope, and proof projection without a parallel mechanism? |
| `scripts/task-start.py` | Does revised-plan rendering read the active revision or fall back to the original Start report? |
| Navigator scope components | Can they accept requested owner candidates and return resolved roles or explicit questions for revised requirements? |
| CLI/MCP entry points | Do all public paths use the same active revised object and approval gate? |

Final implementation ownership must follow the proven first failing
transition, not this candidate list.

## Required regression proof

### Exact incident regression

1. Create the same narrow seven-row plan.
2. Persist an expansion naming packaging, installer, runtime, host, and
   wheel/sdist proof outcomes.
3. Assert the expanded input is present in the saved correction artifact.
4. Assert TailTrail does **not** render the original requirement/scope/proof
   fingerprints as revised.
5. Assert TailTrail either produces a reconciled canonical proposal or remains
   `revision-required` with exact missing fields.

### Projection tests

- material expanded input changes the canonical requirement fingerprint;
- every material correction has requirement-row lineage;
- requested owner candidates remain non-authoritative until Navigator resolves
  them;
- inspection and proof paths cannot become editable through revision input;
- scope expansion without evidence remains an explicit question;
- integration/distribution proof cannot collapse to unit-only validation;
- positive and negative criteria reach the validation contract; and
- partial projection writes no approval-ready artifact.

### Renderer and approval tests

- report, requirements, scope, validation, and approval gate use the same
  active revision fingerprints;
- missing revised canonical data produces a blocking diagnostic;
- the renderer never labels the original Start plan as revised;
- approval fails when the correction-to-plan consistency gate fails;
- host-review receipt becomes stale after any revised-plan change;
- passed host review creates no approved anchor; and
- only explicit user approval can mint the anchor.

### Public-route tests

- reproduce through the actual CLI command used by the host;
- exercise the equivalent MCP route;
- verify immutable events and revision artifacts;
- verify a second correction cycle retains both histories; and
- confirm CLI and MCP return the same blocking or revised result.

## Implementation phases

### Phase 0: read-only root-cause trace

- Reproduce the saved-answer/unchanged-plan mismatch at the public route.
- Record fingerprints at every transition.
- Identify the first stage that discards or ignores the active correction.
- Confirm the real implementation owner and public callers.

Exit: file-and-line evidence names the first failing transition.

### Phase 1: canonical revision projection

- Make the active correction feed the existing canonical revision model.
- Rebuild requirement rows, requested scope inputs, and validation contracts.
- Preserve Navigator as the only authority that promotes implementation
  owners.
- Persist a new immutable revision only when all projections validate.

Exit: expanded input cannot produce the unchanged original canonical proposal.

### Phase 2: consistency and rendering gate

- Compare correction and canonical fingerprints/coverage.
- Render only from the active revised canonical object.
- Block approval wording on mismatch or unresolved scope/proof.

Exit: the exact incident fails closed with a precise projection diagnostic.

### Phase 3: mandatory host-review enforcement

- Bind review to the exact revised report, requirement, scope, and proof
  fingerprints.
- Keep `host-review-required` and `approval-ready` as presentation states.
- Require explicit user approval before minting an anchor.

Exit: an incomplete, stale, or unreviewed plan cannot be presented as
approval-ready or approved.

### Phase 4: public-route qualification

- Run red-to-green CLI and MCP incident tests.
- Prove multi-cycle history remains immutable.
- Prove the corrected AIDLC-enablement requirement reaches a complete canonical
  proposal or an exact unresolved blocker.
- Generate managed evidence and the required completion/delivery records.

Exit: TailTrail no longer saves a material correction while rendering the
original plan as revised.

## Explicit non-goals

This correction does **not** propose:

- a new AIDLC question-and-answer product;
- a redesign of how AIDLC questions are generated;
- implementation of the bundled Full AIDLC feature itself;
- direct host assignment of `implementation-owner` authority;
- automatic implementation after answers are saved; or
- a new lifecycle parallel to the existing Planning Lock.

Multi-run or batch behavior is relevant only if Navigator proves that the
corrected product requirement has multiple independent implementation owners.
It is not the primary defect addressed by this report.

## Definition of done

The planning defect is fixed when:

- a persisted material correction is projected into the active canonical
  requirements, Navigator-resolved scope, and validation contract;
- an incomplete projection fails closed with exact missing fields;
- the original plan is never relabeled as revised after material expansion;
- renderer and approval paths use the same active revision fingerprints;
- host-requested paths remain candidates until Navigator resolves authority;
- test and inspection paths remain non-editable;
- host review is mandatory before presentation but cannot create authority;
- only explicit user approval can mint an approved anchor;
- the exact two-cycle incident is covered through CLI and MCP; and
- no AIDLC implementation begins under the rejected narrow run.
