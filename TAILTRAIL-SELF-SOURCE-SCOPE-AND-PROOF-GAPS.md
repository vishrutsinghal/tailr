# TailTrail Self-Source Scope and Plan-Proof Consistency Gaps

Status: proposed corrective design based on live TailTrail runs; no product code is changed by this document.

## Executive summary

The Full AIDLC bundling work exposed two separate TailTrail defects that combine into a misleading planning experience.

1. TailTrail's repository path policy correctly protects `tailtrail/` and `aidlc-rules/` inside a customer's repository, but applies the same exclusion inside TailTrail's own product source checkout. As a result, TailTrail cannot reliably plan changes to its own Python package or its bundled AIDLC assets.
2. A planning revision can add commands and evidence tiers to a requirement's canonical `validation_contract` without rebuilding the other plan projections that users and later gates rely on. The approved anchor can therefore look complete while `focused_validation` remains unresolved, `checks[]` remains narrower, or Behaviour Harness scenarios remain generic or irrelevant.

The first defect is a workspace-context problem. The second is a canonical-projection and convergence-gate problem. They should be corrected in separate focused runs, even though both were observed while trying to plan the same Full AIDLC integration.

The intended outcome is not to weaken TailTrail's exclusions or approval rules. It is to make the exclusions context-aware and make every plan surface derive from one validated effective plan.

## Observed incident

The relevant planning run was `start-20261015100356-fb0066`.

The intended correction was a prerequisite for bundled Full AIDLC integration: permit TailTrail product source and bundled AIDLC assets to participate in evidence-backed Navigator scope only in the actual TailTrail source checkout, while preserving all protections in customer repositories and installed packs.

The run resolved `scripts/repository_path_policy.py` as the only implementation owner and `tests/test_repository_path_policy.py` as proof-only. That was not enough for the real correction:

- `scripts/repository_path_policy.py` owns workspace eligibility.
- `scripts/navigator_scope.py` calls that policy and owns repository file-kind classification and candidate routing.
- Both layers must understand the same verified workspace context.
- The planned proof also needed positive source-checkout cases and negative installed, nested, state, agent, generated, vendor, and VCS cases.

Revision v3 then exposed the second defect. The revision added broader proof wording and tiers, but the effective plan remained internally inconsistent:

- top-level `validation_contract.tiers` could contain `unit`, `behaviour`, and `integration`;
- `validation_contract.checks[]` could still describe only the original unit command;
- saved `focused_validation` rows could still say behaviour or integration was unresolved;
- the Behaviour Harness could remain selected with generic, non-requirement-specific scenarios;
- the planning audit could inspect the top-level contract and miss the disagreement among those projections.

The plan was therefore not safe to approve. The run was stopped without implementation.

## Gap 1 — TailTrail excludes its own product source

### Symptom

In the TailTrail repository itself, these paths are product source or shipped product assets:

- `tailtrail/install/catalog.py`
- other Python modules under top-level `tailtrail/`
- the pinned official rules under top-level `aidlc-rules/`

The current workspace policy excludes them before Navigator can classify their repository role:

- `scripts/repository_path_policy.py` includes `tailtrail` in `TAILTRIAL_ROOTS`.
- It includes `aidlc-rules` in `CONVENTION_ROOTS`.
- `classify_path()` returns `tailtrail-managed` for those roots.
- `scripts/navigator_scope.py::classify_repository_role()` requires an `application` policy verdict before ordinary source, configuration, documentation, manifest, or test roles can participate in scope.

This means the same safety rule that is correct for an installed TailTrail copy inside a customer's project blocks TailTrail from maintaining its own package and bundled rules in its source repository.

### Why the existing rule is still necessary

Removing `tailtrail` or `aidlc-rules` from the exclusion sets globally would be unsafe.

In an ordinary customer repository:

- `tailtrail/` can be an installed tool payload, not application code;
- `aidlc-rules/` can be a copied or managed rule pack, not customer-owned implementation;
- nested copies can appear under fixtures, vendor directories, generated output, worktrees, or installed payload roots;
- granting those paths ordinary application eligibility could let Navigator assign implementation authority to managed tooling.

The defect is therefore not that the exclusion exists. The defect is that the policy has no explicit knowledge of which workspace it is classifying.

### Root cause

`repository_path_policy.classify_path()` deliberately performs pure, zero-I/O, per-path classification. Its current inputs are the repository root, relative path, worktree roots, and optional agent roots. None of those inputs says whether the root is:

1. the TailTrail product source checkout;
2. an installed TailTrail pack;
3. an ordinary customer repository; or
4. an unknown or incomplete workspace.

Because the classifier lacks that context, it can only apply one global meaning to `tailtrail/` and `aidlc-rules/`.

`navigator_scope.py` already contains partial source-checkout awareness in `_tailtrail_source_checkout()`, but that knowledge is used only for `scripts/` file-kind classification. It is not supplied to the earlier workspace-policy gate. The gate therefore excludes the path before the later source-checkout rule can help.

### Required fix

Introduce one explicit, immutable workspace-context value, computed once per Navigator investigation and passed into every path-policy call.

Suggested states:

| Context | Meaning | Default treatment of `tailtrail/` and `aidlc-rules/` |
| --- | --- | --- |
| `tailtrail-source-checkout` | Verified TailTrail product repository | Top-level product paths may be application-eligible |
| `installed-tailtrail-pack` | TailTrail payload installed into another project | Managed tooling; excluded from application ownership |
| `ordinary-repository` | No verified TailTrail product identity | Managed tooling/convention roots remain excluded |
| `unknown` | Markers are absent, incomplete, contradictory, or unsafe | Fail closed; preserve the existing exclusions |

The detector should use multiple independent repository markers rather than a directory name alone. A robust source-checkout decision should require an agreed set such as:

- TailTrail project identity in `pyproject.toml`;
- `package-manifest.json` with the expected TailTrail package identity;
- `scripts/tailtrail.py`;
- the top-level `tailtrail/` Python package marker;
- the repository registry or another committed product marker.

Exact marker policy should be centralized and tested. A partial match must not grant source authority. An installed marker such as `.tailtrail-install.json`, or a path under `.tailtrail/install/payload`, must take precedence and classify as installed/managed even if copied source-like files are present.

The per-path classifier must remain zero-I/O. Workspace detection may perform bounded I/O once. The resulting context is then passed to `classify_path()` as data, just as `worktree_roots` is computed once and passed in today.

Conceptual call shape:

```python
context = detect_workspace_context(root)
worktree_roots = git_worktree_roots(root)

classify_path(
    root,
    relative,
    workspace_context=context,
    worktree_roots=worktree_roots,
)
```

### Eligibility rules in a verified source checkout

Only the following exception should be introduced:

- top-level `tailtrail/**` may return `application` because it is TailTrail product source;
- top-level `aidlc-rules/**` may return `application` because it is a shipped product asset.

That exception must not apply to:

- `.tailtrail/**`;
- `tailtrail-meta/**`;
- nested `**/tailtrail/**` copies;
- nested `**/aidlc-rules/**` copies;
- installed payload roots;
- linked or generic worktree copies;
- `.claude/**`, `.codex/**`, `.copilot/**`, or configured agent roots;
- `.git/**`, `.hg/**`, or `.svn/**`;
- generated, build, cache, dependency, or vendor directories.

Workspace eligibility must not itself promote a path to `implementation-owner`. After an `application` verdict, `navigator_scope._file_kind_role()` must still assign the normal repository role from the file type and repository conventions. In particular, making `aidlc-rules/VERSION` eligible does not automatically make every rule file editable implementation scope. Requirement ownership, inspection status, proof status, and explicit new-file evidence remain separate decisions.

### Reason-code compatibility

Existing exclusions and their reason codes should remain stable for ordinary repositories and installed packs. New positive reason codes may explain the verified exception, for example:

- `tailtrail-product-source`
- `bundled-aidlc-product-asset`

The context decision itself should have an auditable receipt containing:

- context state;
- markers checked;
- marker hashes or bounded identity facts where appropriate;
- reason codes;
- detector version;
- a fingerprint consumed by Navigator scope evidence.

No per-path call should reread those markers.

### Caller changes

Changing only `repository_path_policy.py` is incomplete. Every caller that needs workspace eligibility must receive the same context, especially:

- `navigator_scope.classify_repository_role()`;
- candidate creation and repository scans;
- scope inspection and Start routes;
- new-file due-diligence checks;
- any audit/debug projection that calls the classifier with Git inventory disabled.

Debug or command-free routes may receive a precomputed context. If no trustworthy context is available, they must use `unknown` and fail closed rather than perform hidden I/O or assume source-checkout authority.

## Gap 2 — Plan revisions do not rebuild all proof projections

### Symptom

A `proof-update` revision can update the canonical requirement row while leaving other saved plan surfaces stale.

The current behavior is visible in the code:

- `scripts/planning-revision.py::_apply_change()` unions `commands`, `tiers`, `editable_paths`, and `proposed_paths` into the requirement's `validation_contract`.
- It does not rebuild `validation_contract.checks[]` for the changed command/tier relationship.
- It does not regenerate the report's `focused_validation` rows.
- It does not recalculate selected feature controls.
- It does not regenerate or validate Behaviour Harness scenarios against the revised requirement and command.
- `scripts/planning-audit.py` checks named paths, inferred tiers, and whether some proof registration exists, but does not compare all of those projections for semantic and structural agreement.

This creates two conflicting truths:

1. the effective requirement contract used as authorization; and
2. the user-visible and harness-specific projections that still describe the old plan.

### Why this is dangerous

The inconsistency is not cosmetic.

- A user can see unresolved proof while an anchor authorizes execution.
- A command can be accepted for tiers not represented in its structured `checks[]` entry.
- A generic Behaviour Harness scenario can be linked by ID even though the command does not prove the asserted behavior.
- An audit can report `clean` after checking only top-level tier and command presence.
- Approval freezes a plan whose visible explanation and executable authority disagree.
- Closure can become structurally complete without proving the specific requested behavior.

The issue log already records a related confirmed case under Issue 23.4: approval and closure tolerated unresolved or generic proof projections.

### Root cause

TailTrail currently stores multiple derived forms of the same plan facts:

- requirement `validation_contract`;
- per-command `checks[]`;
- `focused_validation` rows;
- selected feature controls;
- Behaviour Harness scenarios;
- rendered Start Report sections;
- approved anchor and later execution authorization.

Start-time code constructs several of these projections together, but revision-time code updates only part of the structure. There is no single effective-plan builder that every Start, revision, audit, approval, execution, and closure path consumes.

### Required fix

Create one canonical effective-plan projection function. It should take the base Start plan plus all validated pending revision deltas and produce a complete, internally consistent plan object.

Conceptually:

```text
base Start evidence
  + validated revision deltas
  -> canonical effective requirement rows
  -> scope projection
  -> command/check projection
  -> focused-validation projection
  -> feature-control selection
  -> requirement-specific harness scenarios
  -> rendered plan and approval candidate
```

No derived projection should be mutated independently after this builder exists.

### Proof-update semantics

A validated `proof-update` must update or regenerate all dependent fields atomically:

- `validation_contract.commands`;
- `validation_contract.tiers`;
- `validation_contract.checks[]`, with exact command-to-tier and candidate-path bindings;
- `validation_contract` proof-path authority fields;
- report-level `focused_validation` rows;
- affected selected controls;
- Behaviour Harness scenarios when behaviour proof is genuinely required;
- the rendered Focused validation and selected-feature sections;
- the plan fingerprint used for approval.

The update must be rejected if it cannot produce a complete projection. Adding a tier name without a legal path, runnable command, or requirement-specific assertion must not turn an unresolved plan green.

Raw host text is not sufficient authority. Any host-supplied correction must first be classified, grounded, and validated. The effective-plan builder should consume a validated, structured correction-projection artifact rather than free-form answers or a raw discussion record.

### Focused-validation rules

For every required tier, the effective plan must contain either:

- an existing eligible proof path, exact runnable command, and requirement-specific assertion/scenario; or
- an explicitly approved proposed proof path with its legal pipeline stage and exact future command.

Otherwise the tier remains unresolved and blocks approval.

The focused-validation display must be generated from the same structured checks used by execution authorization. It must never preserve an old unresolved row after the canonical contract is revised, and it must never claim a command/tier relationship absent from `checks[]`.

### Behaviour Harness selection

Behaviour Harness selection must be based on the effective requirement semantics and actual proof boundary, not merely on broad words introduced by corrective planning prose.

When selected:

- every scenario must identify the exact requirement UID;
- expected and preserved behavior must be specific to that requirement;
- the selected command must contain a named assertion or scenario capable of proving it;
- a generic journey or refactor scenario must not satisfy the gate by ID alone.

When the work is an internal deterministic classifier with no user-visible journey, Behaviour Harness should not be selected solely because surrounding prose says “behavior,” “workflow,” or “integration.” Unit and integration tiers may still be appropriate, but feature-control selection must reflect the actual proof boundary.

### Mandatory convergence gate

Before a plan can be presented as approvable, the audit must compare:

1. requirement statements and acceptance criteria;
2. scope evidence roles and fingerprints;
3. `validation_contract.tiers` and `commands`;
4. every `validation_contract.checks[]` entry;
5. focused-validation rows;
6. selected feature controls;
7. Behaviour Harness scenarios and requirement bindings;
8. rendered plan sections;
9. the approval fingerprint.

Any mismatch, stale projection, unresolved row, generic scenario, illegal proof path, or command/tier disagreement must produce `gaps-found` and make approval unavailable.

The same effective-plan fingerprint should be checked again at execution and closure. Approval should authorize exactly one converged plan, not a collection of independently updated projections.

## Relationship between the two gaps

These defects were encountered in sequence but should not be combined into one implementation owner.

The self-source scope defect prevented TailTrail from identifying all legitimate owners for the AIDLC bundle work. The proof-projection defect then made an attempted prerequisite plan appear closer to approval than it really was. Fixing only the path policy would still leave unsafe plan revisions. Fixing only plan convergence would still leave TailTrail unable to scope its own package and bundled rules.

The correct sequence is:

1. establish context-aware self-source eligibility;
2. propagate that context through Navigator and prove exclusions remain intact;
3. establish one canonical effective-plan projection;
4. make revision, audit, approval, execution, and closure consume it;
5. retry the Full AIDLC bundle plan only after both foundations are proven.

## Proposed implementation phases

Each phase should use focused, single-owner TailTrail runs where possible. Tests remain proof-only until a legal TESTING-stage handoff or a pre-activation proof-path revision grants test edit authority.

### Phase A — Freeze current behavior with fixtures

Owner candidates: focused test files only, handled through QA/test-authorized runs.

- Add a matrix for source checkout, installed pack, ordinary repository, nested copy, managed state, agent root, generated path, vendor path, VCS metadata, and linked worktree.
- Add a regression fixture reproducing a proof update whose top-level contract, `checks[]`, focused validation, and Behaviour Harness projection disagree.
- Demonstrate the intended new assertions fail on the current code before implementation.

### Phase B — Workspace-context detection

Primary owner candidate: the module chosen to own the detector after Navigator evidence review.

- Define the context states and receipt schema.
- Detect context once with bounded repository identity checks.
- Give installed-pack evidence precedence.
- Fail closed on incomplete or contradictory markers.
- Fingerprint the result for scope evidence.

### Phase C — Context-aware path policy

Primary owner: `scripts/repository_path_policy.py`.

- Accept the precomputed context without adding per-path I/O.
- Permit only top-level TailTrail package and bundled AIDLC paths in a verified source checkout.
- Preserve every existing exclusion elsewhere.
- Add stable positive reason codes without changing existing negative reason codes unnecessarily.

### Phase D — Navigator propagation

Primary owner: `scripts/navigator_scope.py`.

- Compute or receive the context once per investigation.
- Pass it to all workspace-policy calls.
- Keep workspace eligibility separate from file-kind, requirement ownership, proof role, anchor authority, and write-time enforcement.
- Include the context receipt and fingerprint in scope evidence.

### Phase E — Canonical effective-plan builder

Primary owner: a single existing planning module selected by code ownership evidence; do not introduce a new module unless new-file due diligence proves it necessary.

- Apply validated revision deltas to canonical requirements.
- Regenerate all proof, focused-validation, feature-control, and scenario projections.
- Produce one fingerprinted approval candidate.
- Ensure rendering reads the effective projection rather than stale saved fragments.

### Phase F — Revision and audit convergence

Likely focused owners: `scripts/planning-revision.py` and `scripts/planning-audit.py` in separate runs.

- Make `proof-update` invoke the effective-plan builder.
- Add cross-projection consistency findings.
- Reject unresolved or generic proof.
- Block approval unless the audit is clean against the exact pending revision fingerprint.

### Phase G — Execution and closure enforcement

- Bind managed execution to exact command/check/tier records from the approved effective plan.
- Require requirement-specific Behaviour Harness evidence where selected.
- Reject stale or generic scenario IDs.
- Recheck the effective-plan fingerprint at closure.

### Phase H — Retry bundled Full AIDLC integration

Only after Phases B through G are green should TailTrail re-plan the larger AIDLC bundle requirement. At that point Navigator should be able to scope package code, bundle assets, manifests, public routes, host adapters, and negative integrity proof without either excluding its own product or presenting a half-updated proof plan.

## Acceptance test matrix

### Workspace-context and path-policy tests

| Case | Expected workspace verdict | Expected downstream behavior |
| --- | --- | --- |
| Verified TailTrail source root + `tailtrail/install/catalog.py` | `application` | Normal file-kind classification may yield `implementation-owner` |
| Verified TailTrail source root + `aidlc-rules/VERSION` | `application` | Eligible product asset; ownership still requires requirement evidence |
| Ordinary customer repository + `tailtrail/install/catalog.py` | excluded | Managed TailTrail tooling, never customer application ownership |
| Ordinary customer repository + `aidlc-rules/VERSION` | excluded | Managed convention/rule asset |
| Installed pack root with source-like markers | excluded | Installed-pack evidence wins |
| Incomplete or contradictory source markers | excluded | Context is `unknown`; fail closed |
| Verified source root + `.tailtrail/runs/x.json` | excluded | TailTrail state remains protected |
| Verified source root + `tailtrail-meta/cache.json` | excluded | Generated TailTrail metadata remains protected |
| Verified source root + `fixture/tailtrail/module.py` | excluded | Nested copy remains protected |
| Verified source root + `fixture/aidlc-rules/VERSION` | excluded | Nested bundle copy remains protected |
| Verified source root + `.codex/worktrees/x/tailtrail/a.py` | excluded | Worktree/agent precedence remains intact |
| Verified source root + `vendor/tailtrail/a.py` | excluded | Vendor/generated precedence remains intact |

Additional invariants:

- context detection performs bounded I/O once per investigation;
- `classify_path()` performs zero I/O per path;
- repeated calls return identical roles and reason ordering;
- Windows case folding and separator normalization remain deterministic;
- existing ordinary-repository exclusion tests remain byte-for-byte compatible where practical.

### Plan-projection tests

| Case | Expected result |
| --- | --- |
| Proof revision adds one command and three tiers | `commands`, `tiers`, `checks[]`, focused validation, rendering, and fingerprint all agree |
| Tier is added without a command or legal proof path | Plan remains unresolved and non-approvable |
| Command exists only in top-level contract | Audit reports cross-projection mismatch |
| `checks[]` omits a revised tier | Audit reports command/tier mismatch |
| Focused-validation row remains unresolved after revision | Approval is blocked |
| Generic Behaviour Harness scenario shares only a requirement ID | Approval or closure is blocked |
| Requirement-specific scenario and assertion match the approved command | Behaviour proof may proceed |
| Internal classifier requirement has no genuine behaviour boundary | Behaviour Harness is not selected merely from incidental wording |
| Revision changes requirement wording | feature controls and scenarios are recalculated from the revised requirement |
| Saved projection fingerprint differs from approval candidate | Approval fails closed |
| Execution receipt references stale plan fingerprint | Execution evidence is rejected |

### Public-route tests

At least one integration test must exercise the real route used by a host, not only helper functions:

- run scope inspection from the TailTrail source checkout and confirm product paths can become candidates;
- run the same request against a simulated installed/customer repository and confirm those paths remain excluded;
- create an awaiting-approval plan, apply a proof revision, and confirm the rendered revised report is fully converged;
- attempt approval with an intentionally stale focused-validation or scenario projection and confirm fail-closed behavior.

## Risks and safeguards

### Risk: global protection is accidentally weakened

Safeguard: source exceptions require a verified root context and apply only to exact top-level product roots. Installed, nested, state, agent, generated, vendor, VCS, and worktree precedence stays stronger.

### Risk: source detection trusts forgeable filenames

Safeguard: require several independent markers, validate expected content or identity, fingerprint the receipt, and fail closed on partial or conflicting evidence. A directory named `tailtrail` is never sufficient.

### Risk: context detection violates zero-I/O classification

Safeguard: separate one-time detection from pure per-path classification. Pass an immutable context object into the hot path.

### Risk: projection rebuilding changes approved meaning silently

Safeguard: every material revision creates a new proposal fingerprint and requires explicit user approval. Rebuilding projections is deterministic derivation, not new authority.

### Risk: audit becomes green from labels rather than executable proof

Safeguard: require an exact command, eligible existing or proposed path, non-zero executable proof semantics, and a requirement-specific assertion/scenario. Tier labels alone never satisfy the gate.

### Risk: one large correction recreates the original planning ambiguity

Safeguard: implement the detector, path policy, Navigator propagation, effective-plan builder, revision behavior, audit gate, and closure enforcement as focused owner-specific runs with front-loaded scope and proof contracts.

## Interim host guidance

Until both defects are fixed:

1. Treat top-level `tailtrail/**` and `aidlc-rules/**` exclusions in TailTrail's own source checkout as a known planning limitation, not proof that those files are irrelevant.
2. Do not bypass the limitation by globally removing protected roots or manually promoting installed/nested copies.
3. Trace workspace eligibility, repository file-kind, requirement ownership, approved-anchor authority, and write-time enforcement as separate decisions.
4. After every proof revision, inspect all of these together: top-level contract, `checks[]`, focused validation, selected controls, Behaviour Harness scenarios, and rendered plan.
5. Reject the plan if any projection remains unresolved or disagrees, even if planning audit reports `clean`.
6. Do not approve a plan that selects generic UI or behaviour proof for an internal classifier without a real user-visible boundary.
7. Keep the stopped run `start-20261015100356-fb0066` as historical evidence. Do not resume and approve v3 as an implementation plan.
8. Start new focused correction runs only after each proposed owner's participation and symptom-specific proof have been established read-only.

## Recommended ownership split

This document is not itself implementation authority. Navigator must confirm exact owners before each run. The expected split is:

| Concern | Likely implementation owner | Proof area |
| --- | --- | --- |
| Workspace-context detection | Existing repository/workspace policy owner selected by evidence | Context matrix and marker precedence tests |
| Pure context-aware eligibility | `scripts/repository_path_policy.py` | `tests/test_repository_path_policy.py` |
| Navigator propagation and evidence receipt | `scripts/navigator_scope.py` | Navigator scope and public inspection tests |
| Effective-plan projection | Existing canonical planning builder selected by caller analysis | Focused-validation contract tests |
| Proof revision convergence | `scripts/planning-revision.py` | Revision overlay and pending-report tests |
| Mandatory plan consistency audit | `scripts/planning-audit.py` | Cross-projection audit tests |
| Harness scenario specificity | Existing Behaviour Harness planning/assessment owner | Requirement-specific scenario regressions |
| Approval/execution/closure fingerprint enforcement | Existing lifecycle gate owners, in separate runs | Public approval, managed execution, and closure tests |

If evidence shows that one existing owner already controls multiple concerns, reuse it. Do not add a new abstraction merely to match this table.

## Completion definition

The corrective work is complete only when all of the following are true:

- TailTrail can plan legitimate changes to its own top-level package and bundled AIDLC assets from a verified source checkout.
- The same paths remain excluded in ordinary repositories, installed packs, nested copies, managed state, agent roots, worktrees, generated output, vendor trees, and VCS metadata.
- Workspace context is computed once, fingerprinted, and consumed consistently without per-path I/O.
- A planning revision produces one converged effective plan across contracts, checks, focused validation, controls, scenarios, rendering, and fingerprints.
- Audit and approval reject every unresolved or inconsistent projection.
- Execution and closure reject stale plan fingerprints and generic scenario-only evidence.
- Public-route regression tests prove both the positive source-checkout behavior and every material negative boundary.
- The Full AIDLC bundling requirement can then be planned without silent scope loss, irrelevant proof, or a downgrade in safety.
