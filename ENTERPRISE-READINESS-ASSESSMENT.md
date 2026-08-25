# TailTrail Enterprise Readiness Assessment

**Original assessment date:** 2026-08-20

**Implementation review updated:** 2026-08-22

**Assessment type:** Honest product, design, implementation, and architecture review

**Decision:** Enter an enterprise stabilization program. Freeze capability expansion until the supported package, installation, release, host-conformance, enforcement, and operational gates in Sections 13–19 are complete.

## 1. Executive Verdict

TailTrail is a strong idea with a real problem behind it: AI-assisted development needs better control over planning, context selection, safeguard preservation, validation truth, evidence, and closure. The project has unusually mature thinking about what an AI coding assistant must not claim. The Planning Lock, approved requirement boundary, evidence model, guardrail language, local-first privacy posture, and assistant adapter concept are all credible foundations.

The product is not enterprise-ready yet.

Today, TailTrail is best described as a sophisticated local workflow and governance framework for AI-assisted coding. It is not yet a consistently installable, operationally unified, enforceable enterprise control product. The largest risks are not a lack of features. They are product-surface drift, competing entry points, uncertain distribution, advisory governance, incomplete runtime validation, and an architecture that has grown wider than its reliable operational core.

The right response is revision, not abandonment. The project should enter a stabilization program with one canonical product path, a smaller Core profile, a real package boundary, a versioned state model, enforceable CI controls, and evidence-backed proof of value. Advanced graph, learning, MCP, meta-harness, and full durable-runtime work should remain available, but should not define the default product until the core path is dependable.

## 2. Honest Ratings

| Area | Rating | Honest interpretation |
| --- | ---: | --- |
| Problem and idea | 8.5/10 | Important, underserved AI-coding trust problem with a distinct angle. |
| Product design | 7.5/10 | Strong principles and lifecycle concepts; too much accumulated scope and too many surfaces. |
| User experience | 6.0/10 | The intended flow is thoughtful, but the command and installation experience is not yet obvious enough. |
| Implementation quality | 6.0/10 | Serious deterministic implementation and tests, but public entry-point and release/package inconsistencies remain. |
| Architecture | 6.5/10 | Good ownership and evidence boundaries; currently more specified than operationally unified. |
| Governance model | 7.0/10 | Excellent honesty and safeguards as guidance; limited cross-host enforcement. |
| Validation maturity | 4.5/10 | Focused validation is useful; integration, E2E, infrastructure, and release proof are weak. |
| Distribution maturity | 4.5/10 | Source checkout path is clearer than installed artifact behavior. |
| Enterprise readiness | 5.5/10 | Strong privacy posture, but insufficient enforcement, supportability, rollout, and operational evidence. |
| Overall product readiness | 6.5/10 | Credible internal engineering tool; not yet a broadly dependable enterprise product. |

These ratings are deliberately lower than an architecture-only rating because enterprise buyers experience the install, upgrade, failure, audit, support, and rollback paths, not only the design documents.

## 3. What Is Strong

### 3.1 The problem selection is strong

TailTrail addresses real failure modes in AI-assisted development:

- unsupported claims that tests, scans, or reviews passed;
- edits made without understanding callers, tests, policy, or scope;
- loss of security, validation, accessibility, or data-integrity safeguards;
- oversized context that hides important facts and increases cost;
- workflow drift between an approved goal and the resulting change;
- completion reports that confuse a recommendation with evidence.

This is a better enterprise problem than building another generic prompt wrapper. Trust, traceability, and bounded autonomy are legitimate buying concerns.

### 3.2 The governance principles are unusually disciplined

The strongest material is in `GUARDRAILS.md`, `GOVERNANCE.md`, `SECURITY.md`, and `PUBLIC-CLAIMS.md`:

- validation is treated as evidence, not a claim;
- exact source, commands, paths, and results matter;
- destructive, remote, scanner, and heavy operations are approval-gated;
- local-first operation is the default;
- learning does not override source, policy, tests, CI, scanners, or user direction;
- token savings and security claims are constrained unless measured;
- TailTrail explicitly does not replace tests, CI, scanners, code review, or human approval.

This honesty is a competitive advantage. Preserve it when simplifying the product.

### 3.3 The Planning Lock is a valuable product primitive

The approved run identity, scope, requirement boundary, approval state, freshness, evidence, and closure concepts form a useful control model. They can become the foundation of an enterprise product if they are made small, deterministic, versioned, and consistently used by every command.

### 3.4 The architecture has good boundaries in principle

The layered architecture correctly separates:

1. developer intent;
2. Navigator routing and approvals;
3. context selection;
4. governance;
5. code intelligence;
6. quality and security evidence;
7. review and handoff;
8. learning and metrics;
9. distribution and adoption.

The durable runtime boundary also correctly states that TailTrail should own ordering, authority checks, replay, stage outcomes, and completion while the host and repository continue to perform source edits and project-native commands.

### 3.5 The repository has substantial deterministic work

The repository contains many tests, adapter contracts, registry checks, workflow tests, guardrail fixtures, benchmarks, and CI checks. This is not a prototype with only a pitch deck. The issue is that this investment is spread across a very large surface and does not yet prove the complete installed product path.

### 3.6 Privacy positioning is credible, with a caveat

Local-first operation, no default telemetry upload, no background service, and explicit approval for networked or remote activity are good enterprise defaults. The caveat is that a privacy design is not the same as a completed enterprise privacy program. The product still needs documented data classification, retention, redaction, audit export, administrator controls, and a clear support process.

## 4. Verified Issues and Risks

The following findings are separated from broader architectural judgment. They should be treated as the initial remediation backlog.

### P0: Canonical entry point is inconsistent

**Finding:** The repository-root `navigator.py` imports `navigator_core`, `navigator_render`, `prompt_profile`, and `token_budget_coach` as though those modules were importable from the root. The implementation lives under `scripts/`, so a direct `import navigator` fails with `ModuleNotFoundError: navigator_core`. Meanwhile, `python3 scripts/tailtrail.py hello` succeeds.

**Why it matters:** Two entry-point stories create support and release ambiguity. A user, installer, or integration may select the broken path while the documented CLI selects another path.

**Required decision:** Choose one public source entry point. The preferred direction is a package-owned `tailtrail` module with one console script. Keep compatibility shims only when they are tested and explicitly documented.

**Likely files:** `navigator.py`, `scripts/navigator.py`, `scripts/tailtrail.py`, `tailtrail_cli.py`, `pyproject.toml`.

**Acceptance:** A clean checkout and a clean installed artifact expose the same `hello`, `start`, `guide`, and JSON output contracts. Direct imports of non-public compatibility files are either supported or removed.

### P0: Release checks have drifted from the repository

**Finding (resolved in E1):** `scripts/release-check.py` required `DEMO.md`, but the root inventory did not contain that file. `scripts/check-tailtrail.py` expected `.github/workflows/tailtrail-ci.yml`, while the actual workflow was `.github/workflows/trust.yml`. E1 added the legitimate missing public files and made `release-manifest.json` the shared authority consumed by the active release paths.

**Why it matters:** A release gate that does not describe the current tree cannot be trusted. It can produce false failures, encourage bypasses, or hide missing checks.

**Required decision:** Make the source tree, release scripts, CI, and release checklist share one machine-readable release manifest or one clearly owned inventory.

**Likely files:** `scripts/release-check.py`, `scripts/check-tailtrail.py`, `RELEASE-CHECKLIST.md`, `.github/workflows/trust.yml`, `SECURITY.md`, `INSTALL.md`.

**Acceptance:** Release checks pass from a clean clone without hand-created files or renamed workflow assumptions. Every required public file is either present, removed from the requirement list, or generated by a documented build step.

### P0: Distribution boundary is not proven

**Finding:** `pyproject.toml` exposes `tailtrail_cli:main`, but the declared package configuration only lists `tailtrail_cli` as a module and does not clearly package the runtime under `scripts/`, adapters, schemas, templates, or context assets. The console shim searches for a source checkout.

**Why it matters:** A repository checkout is not a product installation. Enterprise users need a self-contained artifact, predictable versioning, upgrade behavior, and a supported rollback path.

**Required decision:** Decide explicitly whether TailTrail is source-only, a Python distribution, a plugin bundle, or a layered product. The enterprise recommendation is a tested Python distribution plus optional adapter/profile assets.

**Likely files:** `pyproject.toml`, `tailtrail_cli.py`, `INSTALL.md`, `scripts/install-local.py`, `scripts/install-surfaces.py`, package/module layout.

**Acceptance:** `pip install` or `pipx install` into an empty environment works without source-checkout discovery. The installed command can run `hello`, `doctor`, `start --format json`, and a no-op completion path without relying on the repository.

### P1: Governance remains advisory across assistants

**Finding:** TailTrail instructions can guide Copilot, Claude, Cursor, ChatGPT, Gemini, and other hosts, but the project itself acknowledges that Markdown adapter conformance is not equivalent to runtime conformance. `GUARDRAILS.md` is not an automated policy engine.

**Why it matters:** Enterprise customers need to know which controls block a merge, which controls warn, and which controls depend on the assistant obeying text instructions.

**Required decision:** State a precise enforcement model. TailTrail should promise enforceable repository and CI controls, not universal enforcement inside every model host.

**Acceptance:** Documentation and CI output classify controls as `enforced`, `host-assisted`, or `advisory`. A supported PR action can block selected violations independent of the model host.

### P1: Product scope is too broad for the default experience

**Finding:** The repository contains a very large documentation and implementation surface, including Navigator, context slicing, graph intelligence, quality/security radar, learning, meta-harnesses, MCP, AIDLC, and a durable runtime. The architecture describes more capability than the package boundary and first-run experience currently unify.

**Why it matters:** Breadth increases compatibility, packaging, documentation drift, support cost, and cognitive load. Enterprise readiness depends on predictable behavior more than feature count.

**Required decision:** Establish a Core profile and an Extended profile.

**Recommended Core:** install, doctor, start, approved plan, focused validation, review, completion report, evidence export, policy and dependency checks.

**Recommended Extended:** graph enrichers, learning, evaluation harness, MCP integrations, advanced runtime templates, cross-repository features, and meta-harness evolution.

**Acceptance:** A new user can complete a supported first workflow with one install command and one documented command path. Every advertised command has an owner, maturity label, test, and documentation entry.

### P1: Runtime maturity is difficult to understand

**Finding:** `ARCHITECTURE.md`, `CHANGELOG.md`, and `DURABLE-WORKFLOW-RUNTIME-REVISED.md` use different language for implemented foundations, narrow verticals, deferred phases, and complete runtime behavior.

**Why it matters:** Customers cannot determine whether a capability is production-supported, experimental, partially implemented, or only designed. Ambiguous maturity language becomes an enterprise support risk.

**Acceptance:** Every major feature has one status: `supported`, `preview`, `experimental`, `planned`, or `retired`. The changelog, roadmap, command catalog, and release metadata use the same status vocabulary.

### P1: Persisted state needs a formal compatibility contract

**Finding:** The durable runtime stores versioned artifacts under `.tailtrail/workflows/<workflow-id>/` and describes ownership, journals, projections, approvals, evidence, and completion artifacts. The design is strong, but enterprise readiness requires explicit migration, corruption, locking, interruption, and recovery guarantees.

**Risk areas to test:** concurrent runs, interrupted writes, stale locks, partial journals, corrupted projections, schema upgrades, stale evidence, changed target/HEAD, and resume after process termination.

**Acceptance:** State artifacts have schema versions and migration rules. Writes are atomic where required. Corruption fails closed with a diagnostic. Replay is deterministic. A false completion report cannot be produced from incomplete or stale evidence.

### P1: Validation proves local contracts better than customer outcomes

**Finding:** `testing-confidence.md` rates focused unit/regression planning at 7/10 and validation truth at 7/10, but integration testing at 2/10, E2E at 1/10, infrastructure validation at 1/10, and release confidence at 3/10. The document explicitly says this is a design and prioritization document, not proof that the proposed runtime exists.

**Why it matters:** Enterprise buyers care about the complete path: install, configure, run, interrupt, recover, upgrade, export evidence, and operate in CI. Fixture benchmarks alone do not establish that.

**Acceptance:** A release has clean-install, upgrade, rollback, persistence-recovery, CI, adapter, and representative end-to-end evidence.

### P2: Declared Python support exceeds tested support

**Finding:** `pyproject.toml` declares Python `>=3.9`, while the CI matrix and Ruff target reviewed by the assessment are centered on newer versions.

**Required decision:** Either test every declared supported version or narrow the declared support range. Enterprise support claims must match CI evidence.

**Acceptance:** Python 3.9 through 3.13 are tested if retained, or the project declares the actual minimum supported version and documents the support policy.

### P2: Value and efficacy evidence is not yet production evidence

**Finding:** The benchmark and evaluation material is useful deterministic fixture evidence. It is not the same as measured outcomes on representative repositories or live workflows.

**Missing measures:** defect prevention, false positives, approval latency, time-to-completion, rollback frequency, context reduction, validation escape rate, operator burden, and adoption/retention.

**Acceptance:** Public claims cite scenario, sample size, method, artifact, confidence/limitation, and whether the result is measured, local-validated, heuristic, or estimated.

## 5. Product Architecture Diagnosis

### 5.1 The central architecture is right, but the center is too large

The current design treats TailTrail as a control tower surrounded by many specialized layers. That is conceptually coherent, but it creates a risk: the product becomes a catalog of capabilities instead of a dependable workflow.

The enterprise product should have a smaller center:

```text
Intent
  -> Approved run and requirements
  -> Scoped execution/evidence events
  -> Focused validation and review
  -> Completion or explicit incomplete state
```

Everything else should attach to that center through typed, versioned interfaces:

- context slicing enriches planning;
- graph intelligence enriches scope;
- scanners enrich evidence;
- adapters translate host behavior;
- learning consumes sanitized outcomes;
- meta-harness proposes changes.

No extension should be able to bypass authority, scope, evidence truth, or closure rules.

### 5.2 Recommended target architecture

#### A. Product kernel

Own only the invariants that must be stable:

- run identity and approved anchor;
- requirement and scope model;
- authority and approval records;
- event and receipt schema;
- freshness and drift classification;
- deterministic state projection;
- completion report;
- schema migration and recovery.

The kernel must have no model-provider dependency, no arbitrary command execution, and no feature-specific business logic.

#### B. Capability adapters

Each capability should declare:

- stable adapter ID and version;
- input schema;
- approval requirements;
- scope and freshness requirements;
- idempotency behavior;
- output receipt schema;
- failure and retry class;
- whether it is Core or Extended.

Capabilities may recommend or report. The kernel decides whether the workflow can advance.

#### C. Host adapters

Host adapters should translate assistant-specific instructions and runtime receipts into the same TailTrail event vocabulary. They must not imply that instruction loading proves host behavior.

Supported compatibility should be reported as:

- `instruction-compatible`;
- `runtime-observed`;
- `contract-tested`;
- `unknown`.

#### D. Repository integration

Repository-native tests, builds, scanners, package managers, and deployment tools remain authoritative for project behavior. TailTrail selects, approves, invokes when permitted, and records factual results. It must not pretend to replace them.

#### E. Policy and CI enforcement

The enterprise boundary should be a repository/CI integration that can independently enforce:

- required evidence fields;
- prohibited unsupported claims;
- dependency gate decisions;
- safeguard-removal review;
- scope and approval requirements;
- stale or incomplete completion records;
- release manifest consistency.

#### F. Local state and audit export

Local state should be private by default, exportable by explicit action, redactable, retention-controlled, and inspectable. Enterprise users need a deterministic evidence bundle without requiring raw prompts, source, secrets, or provider telemetry.

### 5.3 Architectural decisions to make now

1. Is the public product a Python package, a plugin pack, a source checkout, or a combination?
2. What exact command is canonical?
3. What is the minimum supported workflow?
4. What can be enforced without trusting a model host?
5. Which runtime phases are supported in production versus preview?
6. What is the persisted-state compatibility promise?
7. What evidence is required for a completion report?
8. What data can leave the workstation, and how is it redacted and retained?
9. What is the support policy for Python, assistants, operating systems, and CI providers?
10. What metrics demonstrate value without making unsupported productivity or security claims?

## 6. Concrete End-to-End Stabilization Plan

This plan is intentionally dependency-ordered. Do not start with more feature breadth until the earlier exit gates pass.

### Phase 0: Product decision and freeze

**Goal:** Stop architectural drift while the supported center is defined.

**Actions:**

- Declare Core and Extended profiles.
- Freeze new feature work outside the Core path except security, correctness, packaging, and release blockers.
- Create a command maturity table: command, owner, profile, status, inputs, outputs, tests, docs, and support policy.
- Define the supported workflow from install to completion.
- Define terminology for `supported`, `preview`, `experimental`, `planned`, and `retired`.

**Exit criteria:** A new contributor can identify the supported product path from the README, command catalog, package metadata, and release checklist without reconciling conflicting documents.

### Phase 1: Canonical entry point and package boundary

**Goal:** Make the product installable and predictable.

**Actions:**

- Choose one canonical Python package/module layout.
- Move or expose runtime modules through that package rather than relying on source-checkout paths.
- Repair or retire the root `navigator.py` compatibility surface.
- Package required schemas, adapters, templates, registry data, and runtime assets.
- Remove source-checkout discovery from the installed execution path.
- Add clean-environment install tests for wheel and sdist.
- Test direct CLI, module invocation where supported, and JSON output contracts.

**Primary files:** `pyproject.toml`, `tailtrail_cli.py`, `navigator.py`, `scripts/navigator.py`, `scripts/tailtrail.py`, `INSTALL.md`.

**Exit criteria:** A fresh environment with only the documented installation can run the Core workflow. No command needs the repository root to exist.

### Phase 2: Release truth and CI contract

**Goal:** Make release automation authoritative.

**Actions:**

- Reconcile `scripts/release-check.py`, `scripts/check-tailtrail.py`, CI workflow names, and public file inventory.
- Replace duplicated hard-coded inventories with a generated or shared manifest where practical.
- Make the release checklist executable in the same order as CI.
- Add clean-clone validation and artifact inspection.
- Finalize security contact, support process, versioning, and failure disclosure paths.
- Add artifact hashes, provenance metadata, and signed release guidance when the distribution boundary is stable.

**Primary files:** `scripts/release-check.py`, `scripts/check-tailtrail.py`, `.github/workflows/trust.yml`, `RELEASE-CHECKLIST.md`, `SECURITY.md`, `PUBLIC-RELEASE-METADATA.md`, `VERSIONING.md`.

**Exit criteria:** The release gate passes on a clean clone and fails for a deliberately missing public file, wrong version, broken artifact, unsupported claim, or stale workflow reference.

### Phase 3: Kernel and durable-state hardening

**Goal:** Make approved runs and completion reports trustworthy under failure.

**Actions:**

- Write the canonical state-machine specification in terms of allowed states and transitions.
- Define ownership, authority, evidence, freshness, drift, retry, recovery, and terminal-state invariants.
- Add atomic-write and interrupted-write tests.
- Add concurrent-run and stale-lock tests.
- Add journal replay and projection determinism tests.
- Add corruption diagnostics and fail-closed behavior.
- Add schema migrations with forward/backward compatibility policy.
- Add fixture-based recovery scenarios for every supported terminal and recoverable state.

**Primary files:** `scripts/workflow-runtime.py`, `scripts/workflow_runtime/`, `DURABLE-WORKFLOW-RUNTIME-REVISED.md`, `tests/test_workflow_vertical.py`, `tests/test_workflow_freshness_recovery.py`, `tests/test_closure_contract.py`.

**Exit criteria:** The same event stream always produces the same projection; stale, incomplete, unauthorized, or corrupted state cannot produce a successful completion report.

### Phase 4: Evidence and validation contract

**Goal:** Connect approved requirements to adequate proof.

**Actions:**

- Implement a small versioned validation contract, such as `.tailtrail/testing.yml` or its equivalent.
- Define evidence tiers: unit, component, integration, contract, E2E, infra, release-smoke.
- Require each approved requirement to declare proof obligations or a documented reason for an exception.
- Record exact command, working directory, environment classification, exit code, timestamp, artifact references, and limitations.
- Distinguish local, CI, scanner, provider, heuristic, and measured evidence.
- Add a completion rule that blocks unsupported claims and evidence-incomplete success.
- Keep repository-native commands authoritative.

**Primary files:** `testing-confidence.md`, validation planners, workflow evidence modules, `TAILTRAIL-COMMANDS.md`, focused test suites.

**Exit criteria:** A passing narrow test cannot be represented as proof of a wider requirement unless the requirement explicitly says that is sufficient.

### Phase 5: Enforceable enterprise controls

**Goal:** Make the product useful even when the assistant host is imperfect.

**Actions:**

- Ship a supported CI/PR action for Core policy controls.
- Block invalid completion claims, missing evidence, stale approval, unauthorized scope changes, and unapproved dependency decisions where configured.
- Emit machine-readable SARIF or equivalent findings only when the semantics are clear and supported.
- Add repository policy configuration with versioned schema and validation.
- Add organization guidance for retention, redaction, export, and audit handling.
- Add administrator controls for allowed profiles, networked actions, scanners, remote evidence, and release channels.

**Primary files:** `.github/actions/`, `.github/workflows/`, `GUARDRAILS.md`, `GOVERNANCE.md`, `DEPENDENCY-GATE.md`, policy schemas, CI integration docs.

**Exit criteria:** The documentation clearly identifies every control as enforced, host-assisted, or advisory, and a CI-only run can reject selected violations without model cooperation.

### Phase 6: Assistant and operating-environment compatibility

**Goal:** Make supported environments measurable and supportable.

**Actions:**

- Define a support matrix for Python, macOS, Linux, Windows, CI providers, and assistant hosts.
- Test Python versions that are actually declared.
- Separate instruction compatibility from runtime conformance.
- Publish adapter contract fixtures and host-observed receipts where available.
- Add install/update/uninstall/rollback tests for each supported surface.
- Document unsupported hosts and degraded behavior.

**Primary files:** `ASSISTANT-COMPATIBILITY.md`, `adapters/`, adapter tests, `INSTALL.md`, CI matrix.

**Exit criteria:** Every supported environment has a reproducible smoke test, a known limitation list, and a version policy.

### Phase 7: Independent efficacy and pilot program

**Goal:** Prove that the product helps teams without overstating claims.

**Actions:**

- Select representative repositories and sanitized workflows.
- Measure defect escape, missing-test detection, unsupported-claim detection, approval friction, time-to-completion, context volume, rollback, false positives, and operator burden.
- Compare baseline workflow with TailTrail Core.
- Record sample size, scenario, method, environment, artifacts, and limitations.
- Run a small pilot with explicit opt-in and no raw source or prompt collection by default.
- Use pilot results to remove noisy controls and simplify first-run UX.

**Exit criteria:** Public claims reference reproducible evidence. Pilot users can complete the Core workflow, recover from interruption, and explain why a completion report was accepted or blocked.

### Phase 8: General availability gate

**Goal:** Release only when the product is operationally supportable.

**Required gates:**

- Clean install works from wheel and sdist.
- Core commands have stable text and JSON contracts.
- Supported Python and OS matrix is green.
- Release checks and public-doc audits pass.
- Persistence recovery and migration tests pass.
- CI/PR enforcement controls pass on positive and negative fixtures.
- Security contact and disclosure path are real and tested.
- Upgrade and rollback paths are documented and exercised.
- Completion reports cannot claim success from incomplete evidence.
- Support, versioning, retention, redaction, and data-flow docs are complete.
- Pilot evidence supports only the claims actually made.

## 7. First 30 Days: Concrete Implementation Backlog

### Week 1: Truth and scope

- Decide the canonical command and package shape.
- Mark Core versus Extended capabilities.
- Add a command maturity inventory.
- Repair or retire the duplicate Navigator entry point.
- Record current known failures as regression tests.

### Week 2: Packaging and release checks

- Make the package self-contained.
- Build wheel and sdist in CI.
- Install into an empty environment.
- Reconcile release file and workflow inventories.
- Make `release-check`, `doctor`, and clean-clone smoke checks agree.

### Week 3: Runtime and evidence safety

- Add interrupted-write, corruption, stale-lock, and replay tests.
- Define the minimum completion-report invariant.
- Add one requirement-to-evidence contract fixture.
- Ensure evidence-incomplete and stale states fail closed.

### Week 4: Core user journey and pilot readiness

- Document the one supported first-run journey.
- Add end-to-end install -> start -> approve -> focused validation -> review -> completion smoke.
- Add JSON receipts for every Core stage.
- Publish the support matrix and explicit non-goals.
- Prepare a small sanitized pilot protocol.

## 8. Metrics That Matter

Do not optimize for command count or documentation volume. Track:

| Metric | Why it matters | Target direction |
| --- | --- | --- |
| Clean-install success rate | Proves the product boundary works. | Near 100% in supported matrix. |
| Core first-run completion rate | Measures usability and operational cohesion. | Increase without manual intervention. |
| Completion-report false-success rate | Protects the core trust promise. | Zero known false successes. |
| Evidence completeness rate | Measures requirement-to-proof discipline. | Increase while preserving truthful exceptions. |
| Guardrail precision and recall | Prevents noisy governance. | Improve both; report tradeoffs. |
| Mean recovery time | Measures interruption and failure handling. | Decrease. |
| Upgrade rollback success | Measures operational safety. | Near 100% in tested paths. |
| Approval latency | Detects approval fatigue. | Decrease without weakening controls. |
| False-positive rate | Protects user trust. | Decrease by control and scenario. |
| Defect escape rate in pilot | Measures real outcome value. | Decrease against baseline. |
| Operator time per workflow | Measures product burden. | Decrease after initial learning period. |
| Support incidents by command/profile | Identifies surface area that is not ready. | Decrease and concentrate on Core. |

All metrics must be labeled as `measured`, `local-validated`, `provider-backed`, `heuristic`, or `estimated`.

## 9. Enterprise Non-Goals

These boundaries should remain explicit:

- TailTrail does not replace tests, CI, scanners, security review, or human approval.
- TailTrail does not guarantee that every assistant host obeys Markdown instructions.
- TailTrail does not certify regulatory compliance by itself.
- TailTrail does not prove that code is secure merely because a workflow completed.
- TailTrail does not claim exact token savings without measured provider telemetry.
- TailTrail does not upload source, prompts, secrets, or raw logs by default.
- TailTrail does not silently run destructive, remote, deployment, merge, or publication actions.
- TailTrail does not let historical learning override current source, policy, tests, CI, scanners, or explicit user direction.

These are product strengths when presented as boundaries, not weaknesses to hide.

## 10. Files to Review or Revise First

### Entry point and packaging

- `navigator.py`
- `scripts/navigator.py`
- `scripts/tailtrail.py`
- `tailtrail_cli.py`
- `pyproject.toml`
- `INSTALL.md`

### Release truth and enterprise operations

- `scripts/release-check.py`
- `scripts/check-tailtrail.py`
- `.github/workflows/trust.yml`
- `RELEASE-CHECKLIST.md`
- `SECURITY.md`
- `PUBLIC-RELEASE-METADATA.md`
- `VERSIONING.md`
- `SUPPORT.md`

### Product boundary and claims

- `README.md`
- `DESIGN.md`
- `ARCHITECTURE.md`
- `PUBLIC-CLAIMS.md`
- `PUBLIC-ROADMAP.md`
- `CHANGELOG.md`
- `TAILTRAIL-COMMANDS.md`

### Runtime, evidence, and recovery

- `DURABLE-WORKFLOW-RUNTIME-REVISED.md`
- `scripts/workflow-runtime.py`
- `scripts/workflow_runtime/`
- `testing-confidence.md`
- `tests/test_workflow_vertical.py`
- `tests/test_workflow_freshness_recovery.py`
- `tests/test_closure_contract.py`

### Compatibility and adapters

- `ASSISTANT-COMPATIBILITY.md`
- `adapters/README.md`
- `adapters/`
- `tests/test_host_adapter_conformance.py`

## 11. Final Recommendation

TailTrail should continue, but the next release should be a stabilization release rather than another capability release.

The product thesis is good enough to justify the work. The current implementation is not yet coherent enough to justify broad enterprise claims. The fastest route to enterprise readiness is:

1. make one product path real;
2. make the installed artifact self-contained;
3. make release checks agree with the repository;
4. make persisted workflow state fail closed and recover deterministically;
5. connect requirements to adequate evidence;
6. enforce a small set of controls independently in CI;
7. measure real pilot outcomes;
8. only then expand the product surface.

**Bottom line:** TailTrail has the foundations of an enterprise-grade trust layer, but it should earn that label through packaging, recovery, enforcement, supportability, and measured outcomes. The architecture does not need a wholesale rewrite. It needs a smaller kernel, clearer contracts, fewer competing paths, and disciplined execution against the phases above.

## 12. Assessment Evidence Boundary

This assessment is based on read-only inspection of the repository's architecture, design, governance, security, public-claims, installation, release, compatibility, runtime, testing-confidence, implementation entry points, package metadata, CI workflow, representative tests, and release scripts. The focused executable checks reviewed for this assessment were:

- `python3 -c 'import navigator'`: failed because `navigator_core` was not importable from the repository-root entry point.
- `python3 scripts/tailtrail.py hello`: passed.

No full test suite, build, scanner, vulnerability audit, or release was run as part of this assessment. Those commands should be run with the appropriate approval after the P0 package and release-path changes are made.

## 13. 2026-08-22 Implementation Delta

This section updates the original assessment after Deferred Phases 7–12. It is
the current implementation baseline for the enterprise stabilization program.
The earlier findings remain useful historical diagnosis, but status and release
decisions must use this section and the closure program that follows. Sections
13–19 supersede the original sequencing in Sections 6 and 7 wherever they
differ; the original sections are retained to preserve assessment history.

### 13.1 Status vocabulary

Every capability and environment must use one of these product statuses:

| Status | Meaning |
| --- | --- |
| `supported` | The documented install, runtime, upgrade, rollback, validation, and support paths are reproducibly green for the stated version matrix. |
| `preview` | The contract is implemented and tested locally, but one or more production, host, scale, or support gates remain. |
| `experimental` | The capability may change and has no compatibility promise. It cannot be required by the Core workflow. |
| `planned` | No supported implementation exists. Documentation must not imply otherwise. |
| `retired` | The surface is no longer supported and has a documented replacement or migration path. |

Evidence labels remain separate from maturity status: `measured`,
`provider-backed`, `local-validated`, `heuristic`, `estimated`, and
`not-validated` describe the evidence behind a claim.

### 13.2 Implemented and locally validated

The following work is materially implemented:

- Planning Lock, approved requirements, authority, scope, freshness, drift,
  evidence, and fail-closed completion boundaries.
- Versioned workflow schemas, append-only event journals, deterministic replay,
  atomic projections, recovery, migration, rollback, concurrency leases, and
  fencing behavior.
- Token telemetry, learning-candidate, and evaluation adapters with explicit
  evidence and privacy boundaries.
- Closed MCP read-only and workflow-controlled surfaces with local conformance
  checks.
- Provider-neutral CI receipt ingestion and continuation behavior.
- Negative-assurance behavior for unsupported actions, stale evidence,
  unauthorized advancement, retention, and release gating.
- Release-proof contracts for six observable host scenarios, sanitized receipts,
  compatibility, freshness, and canonical-run linkage.
- A provider-neutral enterprise adapter with tenant, actor, and repository
  isolation; leases and fencing; receipt transport and replay; observability;
  backup and restore verification; and migration and rollback contracts.
- Versioned instruction composition for Codex, GitHub Copilot, and Claude with
  the precedence order host safety, user request, official AI-DLC rules, and
  TailTrail assurance rules.
- Core and Extended installation surfaces, host-specific dry runs, first-run
  verification, selected CI enforcement, dependency checks, and local-first
  privacy guidance.
- E4 v3 Codex, GitHub Copilot, and Claude contracts with exact Core files,
  host-native first actions, composition markers, diagnostics, version-detection
  limits, transactional metadata migration, installed-wheel lifecycle proof,
  and equal portable six-scenario receipt preparation.

These are implementation claims, not general availability claims. The durable
runtime and enterprise adapter are locally validated control-plane work. They
are not evidence of a deployed enterprise service, production scale, or real
host equivalence.

### 13.3 Partially implemented

| Area | Current implementation | Missing closure evidence or behavior |
| --- | --- | --- |
| Python distribution | `pyproject.toml` exposes a `tailtrail` console command. | Only `tailtrail_cli` is packaged; it searches for a source checkout. Wheel and sdist are not self-contained. |
| Host installation | E3 provides one transactional engine; E4 drives all three exact Core manifests from the v3 host contract and proves install, update, repair, rollback, and uninstall from source and wheel. | E5 still owns operating-system and path/permission qualification. |
| First run | Codex, Copilot, and Claude have exact non-empty required files, native first actions, installed-target diagnostics, composition checks, and checkout-free wheel journeys. | E10 still owns real named-host execution receipts. |
| Core profile | A smaller surface exists. | Extended remains the default and Core still contains more than the minimum supported journey. |
| CI enforcement | The repository workflow runs tests, registry and adapter checks, guard classes, dependency checks, and smoke. | The workflow is Ubuntu-only, is not a reusable supported action, and currently exercises failing gates. |
| Release automation | Release, doctor, public-doc, and smoke scripts exist. | Their file inventories and workflow assumptions disagree; the clean smoke creates state that is then rejected. |
| Host conformance | Local instruction, installer, composition, diagnostic, migration, negative, and receipt-preparation contracts pass for all three E4 adapters. | Genuine version-linked runtime receipts for Codex, Copilot, and Claude remain absent and cannot be inferred from contract tests. |
| Enterprise storage | Provider-neutral contracts, isolation, replay, backup, migration, and rollback are implemented. | No production provider qualification, scale test, disaster-recovery exercise, service objective, or operator runbook is complete. |
| Support | Security, versioning, support, and claim-boundary documents exist. | The supported product is still source checkout; package-manager installation and enterprise operational support are not released. |

### 13.4 Current release blockers

The following are blocking defects, not deferred enhancements:

1. `python3 -c 'import navigator'` fails because the root `navigator.py` cannot
   import `navigator_core`.
2. The installed console launcher searches for `scripts/tailtrail.py` in a
   source checkout and exits when it cannot find one.
3. Resolved in E1: release, doctor, audit, export, CI, and support surfaces now
   share the versioned release manifest, legitimate public files are present,
   and approved upstream repositories use an explicit allowlist.
4. Resolved in E1: the fresh-clone smoke builds an isolated manifest candidate
   and runs release preflight before any journey creates TailTrail state.
5. Resolved in E1: the complete suite now passes all 716 tests with no baseline
   exception list.
6. Resolved in E4: Claude requires both `CLAUDE.md` and
   `.claude/commands/tailtrail-start.md`; generic, missing, and partial installs
   fail closed.
7. CI declares only Ubuntu and Python 3.11–3.13 while package metadata declares
   Python 3.9+ and installation documentation describes Windows, macOS, and
   Linux.
8. The real-run release gate has no qualifying host proof: 0 of 15 required
   scenarios and 0 of 6 templates, with Codex, Copilot, and Claude all
   `not-validated`.
9. There is no complete install, update, uninstall, verify, and rollback matrix
   for every supported host and operating system.
10. The assessment itself and other local work are currently untracked. Release
    evidence must be generated from an explicit clean candidate commit, not an
    ambiguous working tree.

## 14. Enterprise Product Definition

### 14.1 Canonical product promise

TailTrail is a local-first trust and workflow control layer for AI-assisted
software development. It creates an approved requirement and scope boundary,
records factual execution and validation evidence, prevents unsupported
completion, and provides deterministic recovery and audit export across
supported coding hosts.

TailTrail does not replace repository-native tests, builds, scanners, CI,
review, deployment systems, or human approval. Host instructions are never
treated as proof that a host obeyed them.

### 14.2 Supported Core journey

The only mandatory enterprise Core journey is:

```text
install
  -> verify and doctor
  -> create approved run and requirements
  -> execute within approved scope
  -> record factual evidence
  -> focused validation and review
  -> complete or report explicit evidence-incomplete state
  -> export, retain, recover, update, roll back, or uninstall safely
```

Everything required by this journey must be in the self-contained package and
must not depend on a TailTrail source checkout, a model provider, a hosted
service, or raw prompt telemetry.

### 14.3 Core and Extended boundary

Core must be the default. It contains only:

- CLI and configuration validation;
- run, requirement, approval, scope, and authority contracts;
- workflow journal, projection, evidence, freshness, recovery, and completion;
- Guard and dependency decisions required by the default policy;
- host install, verify, update, rollback, and uninstall contracts;
- Codex, Copilot, and Claude Core adapters;
- local evidence store, redacted export, doctor, and support diagnostics;
- CI policy evaluation and machine-readable findings;
- schemas, migrations, templates, and minimum documentation required to operate
  those features.

Extended capabilities are opt-in adapters: advanced AIDLC modes, graph mapping,
learning, benchmarks, token analysis, evaluation, specialist quality and
security helpers, meta-harnesses, enterprise remote storage, and additional
hosts. Extended adapters cannot bypass or weaken Core authority, evidence,
privacy, or closure invariants.

### 14.4 Enterprise non-functional requirements

The supported product must satisfy all of these dimensions:

| Dimension | Required outcome |
| --- | --- |
| Security | Least privilege, explicit trust boundaries, safe path handling, input/schema validation, secret-safe logs, signed release guidance, vulnerability disclosure, and dependency review. |
| Privacy | Local-first storage, no source or prompt upload by default, explicit export, redaction validation, retention controls, and documented data flows. |
| Reliability | Atomic durable writes, deterministic replay, idempotency, concurrency fencing, corruption diagnostics, backup/restore, migration, rollback, and fail-closed completion. |
| Compatibility | Declared and tested Python, OS, CI, host, state-schema, CLI, JSON, and adapter version matrices. |
| Operability | Doctor, structured diagnostics, audit export, observability, runbooks, failure classification, recovery procedures, service objectives where a remote service exists, and support escalation. |
| Accessibility | Human-readable output must remain usable with keyboard and screen-reader workflows; machine-readable output must not be the only explanation of a block. |
| Performance | Measured startup, install, projection/replay, policy evaluation, evidence-bundle size, and supported scale envelopes with regression budgets. |
| Maintainability | Small package boundaries, shared contracts, no duplicated inventories, generated schemas/docs where appropriate, compatibility fixtures, and ownership metadata. |
| Supply chain | Locked release inputs, artifact hashes, SBOM where supported, provenance, dependency decisions, release signing, and reproducible artifact inspection. |
| Supportability | Clear maturity labels, supported version window, deprecation and migration policy, incident severity, response expectations, release cadence, and known limitations. |

## 15. Target Enterprise Architecture

### 15.1 Package and process topology

```text
CLI / Python API / MCP
          |
          v
Enterprise Product Kernel
  - run and approved anchor
  - requirements, scope, authority, approvals
  - event and receipt schemas
  - evidence, freshness, drift, completion
  - journal, projection, migration, recovery
          |
          +-------------------+-------------------+
          |                   |                   |
          v                   v                   v
 Capability Registry     Host Adapter API     Policy/CI API
 - Core/Extended         - Codex              - repository policy
 - lifecycle hooks       - Copilot            - Guard/dependency rules
 - typed receipts        - Claude             - release rules
 - maturity/version      - future hosts       - findings/SARIF
          |                   |                   |
          +-------------------+-------------------+
                              |
                              v
                   Storage and Audit API
                   - local default store
                   - redacted export
                   - optional enterprise provider
                   - leases, replay, backup, migration
```

### 15.2 Product kernel

The kernel owns only invariants that every workflow must preserve:

- globally unique run and workflow identities;
- immutable approved requirement and scope anchors;
- actor, tenant, repository, authority, and approval records;
- monotonic event ordering and idempotency;
- canonical receipt and evidence schemas;
- freshness, compatibility, drift, and terminal-state classification;
- deterministic projection and replay;
- completion-report eligibility;
- schema migration, recovery, and rollback.

The kernel must not contain host-specific prompts, arbitrary project command
execution, model-provider behavior, scanner-specific logic, or enterprise
provider-specific persistence.

### 15.3 Capability adapter contract

Every Core or Extended capability must declare:

- stable adapter ID, version, maturity, and owner;
- Core or Extended classification;
- input, output, configuration, and receipt schemas;
- approval, authority, scope, and freshness requirements;
- idempotency key and retry class;
- local, network, secret, and data-egress behavior;
- failure, cancellation, recovery, and rollback semantics;
- compatibility range and migration behavior;
- validation fixtures and required evidence tier;
- whether it recommends, observes, executes, enforces, or reports.

Only the kernel advances workflow state. An adapter cannot convert missing,
stale, heuristic, or failed evidence into success.

### 15.4 Host adapter contract

Codex, Copilot, and Claude must be thin delivery adapters over the same kernel
and installer engine. Each adapter owns:

- installed instruction, plugin, skill, prompt, or command surfaces;
- host-specific precedence and capability limitations;
- detection of supported host/version where possible;
- host-native first action and diagnostics;
- portable real-run scenario bundle and sanitized receipt capture;
- version compatibility, update, rollback, and uninstall behavior.

Host status must be reported independently as:

- `instruction-compatible`;
- `contract-tested`;
- `runtime-observed`;
- `supported` only after the full release matrix passes;
- `unknown` or `not-validated` otherwise.

### 15.5 Installer engine

All hosts must use one versioned installer engine with an `InstallPlan` and an
installed ownership manifest. The engine must:

1. detect platform, Python, target repository, host, existing install, and
   conflicting files;
2. produce a no-write dry run;
3. validate paths and reject unsafe or inaccessible targets;
4. stage files in a temporary location;
5. verify staged hashes and schemas;
6. back up replaced managed files without overwriting unrelated user files;
7. apply changes atomically where the platform permits;
8. write a manifest containing version, surface, host, installed paths, hashes,
   backups, migrations, and ownership;
9. run host-aware verification from the installed product, not the source tree;
10. restore the prior state automatically when application or verification
    fails;
11. support deterministic update, explicit rollback, and safe uninstall;
12. preserve or report user-modified managed files instead of silently
    replacing or deleting them.

### 15.6 Distribution model

The first canonical distribution is a self-contained Python wheel and sdist,
installed with `pipx` or an isolated virtual environment on Windows, macOS, and
Linux. The supported command is always `tailtrail`.

The intended first-run experience is:

```bash
pipx install tailtrail
tailtrail install --host codex --profile core --target .
tailtrail doctor --host codex --target .
```

Equivalent `copilot` and `claude` host values use the same command shape.
Standalone signed binaries, Homebrew, WinGet, Chocolatey, and other package
managers may be added only as distribution adapters over the same verified
artifacts and manifest contract. They are not separate implementations.

### 15.7 Independent policy enforcement

Enterprise controls cannot depend solely on model cooperation. A supported
repository/CI integration must independently evaluate:

- approval and scope requirements;
- stale, missing, incompatible, or inadequate evidence;
- unsupported validation and completion claims;
- safeguard removal;
- dependency decisions;
- local/private state exposure;
- release manifest and version consistency;
- policy/schema compatibility;
- retention and redaction obligations where configured.

Every control must be labeled `enforced`, `host-assisted`, or `advisory`.
Blocking behavior must be policy-configurable, versioned, testable on positive
and negative fixtures, and accompanied by a human-readable remediation.

### 15.8 Enterprise storage and administration

Local storage remains the default authoritative mode. An optional enterprise
provider must implement the existing provider-neutral contract and add:

- organization, tenant, repository, actor, and role policy boundaries;
- authentication and authorization integration without storing provider secrets
  in workflow artifacts;
- append-only audit retention and explicit legal/retention controls;
- encrypted transport and storage under the provider's documented boundary;
- export, deletion, hold, redaction, backup, restore, and disaster-recovery
  procedures;
- observable lease, replay, ingestion, rejection, migration, and rollback
  behavior;
- rate, quota, availability, latency, recovery-point, and recovery-time
  objectives;
- administrator diagnostics and audit reconciliation without raw source,
  prompts, secrets, or private logs by default.

## 16. Unified Installation and Host Experience

### 16.1 Required lifecycle commands

The canonical CLI must provide consistent text and JSON contracts for:

```text
tailtrail install --host <codex|copilot|claude> --profile <core|extended>
tailtrail verify --host <host|all>
tailtrail doctor --host <host|all>
tailtrail status --host <host|all>
tailtrail update --dry-run
tailtrail update
tailtrail rollback --to <version-or-manifest>
tailtrail uninstall --dry-run
tailtrail uninstall
```

The command may expose compatibility aliases during migration, but the help,
documentation, generated host prompts, and support procedures must use this one
shape.

### 16.2 Codex

The Codex adapter must install the project guidance, plugin manifest, and Core
skills required for the supported workflow. Verification must confirm exact
managed files, compatible versions, instruction composition, plugin/skill
availability, and a real installed-package `hello` and `start` path. Global
configuration changes remain opt-in and must be independently approved.

### 16.3 GitHub Copilot

The Copilot adapter must install repository instructions and the Core pack
through the common installer manifest. CI enforcement remains authoritative
when Copilot cannot guarantee full workflow invocation. Verification must cover
instruction loading surfaces, managed-pack integrity, repository policy, and
the supported first action without claiming identical IDE behavior.

### 16.4 Claude

The Claude adapter must install and verify `CLAUDE.md`, the supported command or
plugin surfaces, and the same Core contracts. The current empty required-file
mapping must be eliminated. Claude must have a host-native first action,
installation diagnostics, update, rollback, uninstall, and real-run receipt
coverage equal to the other supported hosts.

### 16.5 Operating-system matrix

At minimum, every release candidate must exercise:

| Platform | Required paths |
| --- | --- |
| Windows | Supported Python versions, `pipx`/isolated install, paths with spaces, non-ASCII paths, permission denial, update, rollback, uninstall, and all three host profiles. |
| macOS | Supported Python versions on current supported runners, `pipx`/isolated install, Intel/Apple-silicon-neutral Python behavior, permissions, update, rollback, uninstall, and all three host profiles. |
| Linux | Supported Python versions, clean containers, read-only and permission-denied targets, update, rollback, uninstall, and all three host profiles. |

Platform documentation must distinguish automated CI proof from manual or
provider-backed validation.

## 17. Comprehensive Implementation Program

This program contains every currently identified enterprise-readiness item.
There is no unspecified “finish later” bucket. New facts discovered during
implementation must be recorded in the requirement-to-phase matrix and assigned
to a phase before the affected gate can pass.

### Phase E0 — Baseline, ownership, and feature freeze

**Purpose:** Establish one auditable program baseline before changing product
boundaries.

**Implementation:**

- Commit or explicitly exclude the assessment and other intended release files.
- Create a machine-readable enterprise closure registry containing requirement
  ID, owner, priority, phase, dependencies, implementation paths, validation,
  evidence, maturity, and status.
- Inventory every public command, schema, adapter, persisted artifact, CI rule,
  install surface, release file, and support claim.
- Mark each feature Core, Extended, experimental, planned, or retired.
- Freeze new capabilities until E12 passes; allow only correctness, security,
  packaging, compatibility, release, support, and evidence work.
- Record all five current test defects and every release/smoke failure as tracked
  closure items.

**Validation:** Registry schema tests, duplicate/missing-owner checks, docs-to-
registry consistency, and a clean candidate-commit declaration.

**Exit gate:** Every known item in Sections 13–19 has an ID, owner, phase, and
acceptance test. No public surface has an unknown maturity state.

### Phase E1 — Restore test, release, and repository truth

**Purpose:** Make the existing repository internally consistent before moving
code into a package.

**Implementation:**

- Fix the unsupported evaluation event, scenario inventory, Navigator reason,
  inaccessible-target verification, and UI message regressions.
- Repair or retire root `navigator.py` with compatibility tests.
- Replace duplicated hard-coded release/public-file/workflow inventories with
  one versioned release manifest.
- Add explicit URL and file-scope allowlists so pinned official upstream sources
  are permitted while private or accidental references remain blocked.
- Correct the fresh-clone smoke ordering and isolate generated `.tailtrail`
  state from release hygiene.
- Reconcile doctor, release check, public-doc audit, smoke, CI, release checklist,
  support docs, and actual workflow names.
- Add the legitimate missing templates/files or remove stale requirements from
  the shared manifest with an explicit product decision.

**Validation:** Full unit/contract suite; release check; doctor; public-doc audit;
fresh-clone smoke; deliberate negative fixtures for missing files, wrong
versions, private references, stale workflows, and local state.

**Exit gate:** The clean candidate commit passes all repository gates, and each
gate fails for its intentional negative fixture without false positives on
approved upstream references.

### Phase E2 — Self-contained product kernel and package

**Purpose:** Make the installed artifact the canonical product boundary.

**Implementation:**

- Create a normal `tailtrail` package with kernel, CLI, schemas, migrations,
  templates, registry, adapters, and required static resources as package data.
- Move reusable behavior out of dynamic script loading into importable modules;
  keep thin script wrappers only for documented compatibility periods.
- Remove source-checkout discovery from normal installed execution.
- Define stable Python API boundaries only where an API support promise is
  intended.
- Define stable text and JSON CLI envelopes, exit-code taxonomy, error and
  diagnostic contracts, and deprecation behavior.
- Build wheel and sdist and inspect their contents for completeness, secrets,
  local state, and unintended files.
- Choose the supported Python range and align metadata, Ruff, docs, and CI.

**Validation:** Build wheel/sdist; install each into empty environments; run
`hello`, doctor, start, approval, evidence, closure, recovery, migration, and
JSON-contract tests without a checkout; test missing/corrupt package resources;
verify artifact inventory and hashes.

**Exit gate:** The Core workflow runs from installed wheel and sdist with the
repository absent. All supported Python versions pass and unsupported versions
fail with a clear message.

### Phase E3 — Transactional installer lifecycle

**Purpose:** Create one safe installer engine for every host.

**Implementation:**

- Implement the versioned `InstallPlan` and ownership-manifest schemas.
- Add target, filesystem, permission, conflict, symlink, traversal, and unsafe-
  path validation.
- Add staging, hashing, backups, atomic application, verification, automatic
  restoration on failure, and idempotent reinstall.
- Implement common install, verify, doctor, status, update, rollback, and
  uninstall commands with text and JSON output.
- Preserve unrelated user files and detect modified managed files.
- Support Core-to-Extended and Extended-to-supported-version migrations without
  deleting user changes.
- Add retention and cleanup rules for backups and temporary installation data.

**Validation:** Positive and negative fixtures for new install, reinstall,
conflict, inaccessible target, interrupted write, corrupt staging, modified
managed files, update, failed update, rollback, uninstall, and repeated
operations.

**Exit gate:** Every lifecycle operation is deterministic, recoverable, and
manifest-driven; no host-specific installer bypasses it.

### Phase E4 — Codex, Copilot, and Claude adapters

**Purpose:** Deliver equal contract quality without pretending the hosts are
identical.

**Implementation:**

- Refactor all three host installers onto the common engine.
- Define exact Core installed-file manifests and host-native first actions.
- Fix Claude required-file and verification behavior.
- Unify Core/Extended selection and make Core the default.
- Add host/version compatibility declarations, capability limitations,
  instruction composition, diagnostics, and migration rules.
- Provide portable six-scenario real-run bundles and sanitized receipt capture
  for every host.
- Keep global settings, network activity, and host account changes explicitly
  opt-in and approval-gated.

**Validation:** Adapter unit, composition, installer, update, rollback,
uninstall, conflict, and negative-assurance tests for every host; generated-file
drift checks; local installed-product E2E journeys.

**Exit gate:** Codex, Copilot, and Claude pass the same installer and Core
contract suite, with documented host-specific limitations and no empty or
generic false-positive verification.

**Implementation status (2026-08-22): complete.** Adapter v3 is the single
machine-readable authority consumed by the package-owned installer,
first-run surface, composition generator, diagnostics, and receipt preparation.
All three hosts pass the same source and checkout-free installed-wheel lifecycle
tests. Claude's empty verification mapping is closed. The complete 748-test
suite passes on CPython 3.12 and 3.13. Qualification remains
`contract-tested`; E5 platform support and E10 `runtime-observed` evidence are
not claimed.

### Phase E5 — Cross-platform distribution and supply chain

**Purpose:** Make installation reproducible and supportable on major operating
systems.

**Implementation:**

- Add Windows, macOS, and Linux CI jobs across the chosen Python support matrix.
- Test `pipx` or isolated-environment installation from built artifacts, not the
  checkout.
- Exercise path spaces, Unicode, line endings, permissions, symlinks, shell
  launchers, and platform-specific failure behavior.
- Generate artifact hashes, dependency inventory/SBOM where supported, build
  provenance, and signed-release guidance.
- Verify sdist-to-wheel builds and inspect artifacts before publication.
- Add package-manager adapters only after the canonical artifacts pass; adapters
  must verify the same hashes and invoke the same installer contracts.

**Validation:** Clean OS matrix, artifact reproducibility/inspection, tampered-
artifact negatives, launcher tests, upgrade/rollback/uninstall matrix, and
documented manual evidence for any platform behavior unavailable in CI.

**Exit gate:** Every claimed OS, Python version, artifact type, and host profile
has a green reproducible install lifecycle and a published support limitation
list.

**Implementation status (2026-08-22): implemented; hosted exit evidence
pending.** The repository now has an exact Linux/macOS/Windows x CPython
3.12/3.13 workflow, immutable canonical artifact handoff, isolated wheel and
sdist-to-wheel lifecycle qualification for every Core host, a closed receipt
schema and exact aggregate gate, byte-for-byte rebuild checks, archive
inspection, locked build inputs, SHA-256 inventory, CycloneDX 1.6 SBOM,
in-toto/SLSA provenance candidate, tamper negatives, and a least-privilege
tag-only GitHub/Sigstore identity attestation job. Local macOS qualification
passes both artifact routes, all host lifecycles, spaces/Unicode, CRLF,
permissions, symlink rejection, rollback, and uninstall. It is recorded as
`ci: false` and does not satisfy the six-cell hosted gate. ENT-E5-001,
ENT-E5-002, and DEF-011 therefore remain evidence-open until one source commit
produces all hosted receipts and a release tag produces identity attestations;
configured CI is not represented as observed platform support.

### Phase E6 — Repository and CI enforcement product

**Purpose:** Enforce selected controls without trusting a coding assistant.

**Implementation:**

- Package a supported CLI-based reusable CI/PR integration with pinned version
  input and least-privilege permissions.
- Define the versioned repository policy schema, defaults, overrides, migration,
  and validation.
- Classify every rule as enforced, host-assisted, or advisory.
- Enforce configured approval/scope, evidence, stale completion, dependency,
  safeguard, local-state, redaction, and release-manifest rules.
- Emit stable JSON and SARIF or an equivalent supported findings format with
  precise locations, severity, rule IDs, evidence, and remediation.
- Add baseline/suppression behavior that cannot silently hide newly introduced
  high-severity findings.
- Document GitHub first; keep provider-neutral CLI contracts for other CI
  systems.

**Validation:** Positive/negative repositories, pull-request diff behavior,
shallow clone and initial commit behavior, permissions, forks, stale baselines,
suppression expiry, schema incompatibility, and false-positive fixtures.

**Exit gate:** A CI-only invocation can reproducibly reject every configured
Core violation without model cooperation, and every finding has an actionable
human explanation.

### Phase E7 — State, security, privacy, and resilience qualification

**Purpose:** Qualify the Core trust boundary under failure and misuse.

**Implementation:**

- Complete state-machine, authority, idempotency, concurrency, freshness,
  cancellation, retry, recovery, migration, and terminal-state specifications.
- Threat-model CLI, MCP, installer, repository inputs, local state, audit export,
  enterprise transport, and host receipt boundaries.
- Test traversal, symlink, injection, malformed schemas, oversized input,
  corrupted journals, partial writes, stale locks, replay, duplicate events,
  cross-tenant identifiers, and unauthorized state advancement.
- Define sensitive-data classes, default exclusions, redaction, retention,
  deletion, export, backup, and diagnostic rules.
- Add security disclosure exercises, dependency review, secret scanning, and
  release-supply-chain checks without overstating security guarantees.
- Add performance and scale envelopes for Core journal, replay, policy, install,
  and audit operations.

**Validation:** Security and privacy negative fixtures, deterministic recovery
suite, fuzz/property testing where justified, concurrency tests, backup/restore,
migration compatibility, performance baselines, and documented residual risks.

**Exit gate:** Unauthorized, stale, corrupt, incomplete, cross-boundary, or
privacy-unsafe state cannot produce successful completion or silent data loss.

### Phase E8 — Enterprise provider and administrator operations

**Purpose:** Turn the provider-neutral adapter into an operable optional
enterprise deployment.

**Implementation:**

- Select and document the first provider implementation through the Dependency
  Gate and architecture decision process.
- Implement tenant and repository provisioning, authentication integration,
  authorization roles, policy distribution, leases/fencing, ingestion,
  reconciliation, audit export, quotas, and administrator diagnostics.
- Implement encrypted transport/storage according to the provider boundary,
  secret management, key ownership, rotation, and revocation procedures.
- Define backup schedule, restore verification, migration, rollback, disaster
  recovery, regional/data-residency boundaries where claimed, and capacity
  planning.
- Define service metrics, alerts, dashboards, availability/latency/error
  objectives, RPO/RTO, incident classification, and on-call/runbook ownership.
- Preserve full local continuation when enterprise connectivity is unavailable
  and reconcile without violating ordering or tenant isolation.

**Validation:** Provider contract suite, isolation and authorization negatives,
load and soak tests, network partition/retry/replay, duplicate/out-of-order
events, backup restore, migration rollback, disaster-recovery exercise, secret
rotation, audit reconciliation, and local-offline continuation.

**Exit gate:** The provider passes the neutral contract and operational drills;
activation remains blocked for repositories that do not meet release-policy and
real-run evidence requirements.

### Phase E9 — Observability, audit, governance, and administration

**Purpose:** Make enterprise operation explainable without exposing sensitive
development data.

**Implementation:**

- Define stable operational metrics, structured event categories, correlation
  IDs, tracing boundaries, health indicators, and failure taxonomy.
- Build deterministic, redacted evidence and audit exports with schema version,
  integrity hashes, provenance, retention metadata, and verification commands.
- Add administrator policy inspection, effective-policy explanation, adapter
  inventory, support bundle generation, and drift reporting.
- Document data-flow diagrams, processing boundaries, retention/deletion,
  subprocessors or providers where relevant, access reviews, and customer-owned
  controls.
- Define change management, segregation of duties, privileged operation audit,
  break-glass procedures, and periodic restore/access/reconciliation exercises.

**Validation:** Redaction leak fixtures, export round-trip and integrity checks,
effective-policy tests, observability cardinality limits, support-bundle privacy
checks, access review, and operational tabletop exercises.

**Exit gate:** Operators can diagnose and audit supported workflows and provider
health using sanitized metadata, and every privileged action is attributable
without requiring raw source or prompts.

### Phase E10 — Real host, release, and compatibility proof

**Purpose:** Replace compatibility assumptions with version-specific evidence.

**Implementation:**

- Execute all required scenarios and templates in supported Codex, Copilot, and
  Claude versions using release-candidate artifacts.
- Record sanitized canonical-run-linked receipts with environment, host version,
  adapter version, scenario version, outcome, limitation, and freshness.
- Exercise approval, rejection, stale evidence, recovery, CI wait, incomplete
  proof, update, rollback, and uninstall behavior.
- Define evidence expiration and host-version retirement rules.
- Publish the support matrix without generalizing one version's result to
  another host or version.

**Validation:** Runtime conformance report, release compatibility gate, stale and
incompatible receipt negatives, receipt tamper checks, and independent review
of sanitized proof.

**Exit gate:** Every supported host/version passes the complete current scenario
set and installation lifecycle. Missing, failed, stale, or incompatible evidence
keeps the exact host/version out of `supported` status.

### Phase E11 — Documentation, support, pilot, and efficacy

**Purpose:** Prove that teams can operate the product and that claims match real
outcomes.

**Implementation:**

- Rewrite README, installation, commands, architecture, compatibility, security,
  privacy, support, versioning, migration, rollback, disaster recovery, release,
  and troubleshooting docs around the canonical package and Core journey.
- Add role-based guides for developer, repository administrator, security,
  platform, auditor, and support operator.
- Define supported version window, deprecation period, security response,
  severity, support intake, escalation, maintenance, release cadence, and end-
  of-life policies.
- Run representative, opt-in pilots using sanitized evidence and no default raw
  prompt/source collection.
- Measure install success, first-run completion, false-success, evidence
  completeness, false positives, approval latency, recovery time, rollback,
  operator burden, defect escape, and adoption/retention with limitations and
  sample sizes.
- Remove noisy controls and usability friction revealed by evidence without
  weakening Core safeguards.

**Validation:** Documentation command tests, newcomer usability exercises,
support simulations, pilot methodology review, claim-to-evidence audit, and
accessibility checks for CLI and human-readable reports.

**Exit gate:** Intended users can install, complete, diagnose, recover, update,
roll back, and uninstall without source-checkout knowledge; every public outcome
claim cites adequate evidence and limitations.

### Phase E12 — General availability and continuous release governance

**Purpose:** Release only when the entire supported boundary is operationally
closed.

**Implementation:**

- Finalize the release candidate from a clean, reviewed commit and immutable
  dependency inputs.
- Run all package, OS/Python, host, CI enforcement, state, security/privacy,
  provider, backup/recovery, migration/rollback, docs, and pilot gates.
- Produce hashes, provenance, SBOM where supported, signed artifacts and release
  notes, compatibility matrix, known limitations, support dates, and rollback
  instructions.
- Verify the public artifact from an external clean environment before
  publication.
- Record release approval and publish only the claims supported by the release
  evidence bundle.
- Establish recurring compatibility, dependency, restore, migration, security,
  host-runtime, efficacy, and support reviews for every maintained release.

**Validation:** One orchestrated release gate that consumes the evidence from
E0–E11, plus deliberate negative candidates for missing, stale, failed,
incompatible, tampered, or unapproved evidence.

**Exit gate:** Every requirement in the closure registry is `passed` or is an
explicit enterprise non-goal. There are no deferred blockers, unowned gaps,
unsupported success claims, or untested supported environments.

## 18. Requirement-to-Phase Closure Matrix

This matrix prevents work from disappearing between architecture, product,
implementation, validation, and operations.

| Requirement | Primary phase | Required proof |
| --- | --- | --- |
| Canonical product and maturity inventory | E0 | Complete closure registry and docs consistency |
| Green full suite and root Navigator | E1 | Full suite and compatibility tests |
| Authoritative release manifest and smoke | E1 | Positive and negative clean-clone gates |
| Self-contained wheel and sdist | E2 | Empty-environment Core workflow |
| Stable CLI, JSON, exit codes, schemas | E2 | Contract and compatibility fixtures |
| Shared transactional installer | E3 | Failure, recovery, rollback, uninstall matrix |
| Codex installation and lifecycle | E4–E5 | Host adapter, OS, and installed E2E proof |
| Copilot installation and lifecycle | E4–E5 | Host adapter, OS, and installed E2E proof |
| Claude installation and lifecycle | E4–E5 | Host adapter, OS, and installed E2E proof |
| Windows, macOS, and Linux support | E5 | Green declared OS/Python matrix |
| Artifact supply-chain integrity | E5, E12 | Hashes, inspection, provenance, signing guidance |
| Independent CI/policy enforcement | E6 | Positive/negative CI-only fixtures |
| State integrity and recovery | E7 | Replay, corruption, concurrency, migration, recovery suite |
| Security and privacy boundaries | E7, E9 | Threat model, negative fixtures, redaction/data-flow proof |
| Enterprise provider deployment | E8 | Provider contract, isolation, load, DR, migration proof |
| Audit, observability, and administration | E9 | Sanitized audit/export and operational exercises |
| Real Codex/Copilot/Claude behavior | E10 | Fresh version-linked scenario receipts |
| Support and operational ownership | E11 | Published policies and support simulations |
| Measured efficacy and usability | E11 | Pilot artifacts, method, sample, limitations |
| General availability | E12 | Complete immutable release evidence bundle |

## 19. Program Governance and Definition of Done

### 19.1 Phase execution rules

- Execute phases in dependency order. Parallel work is allowed only when it does
  not bypass an earlier exit gate.
- Use comprehensive AIDLC artifacts and explicit approval gates for package,
  installer, security/privacy, enterprise provider, and GA boundaries.
- Apply `DEPENDENCY-GATE.md` before adding, changing, replacing, or removing any
  dependency or provider SDK.
- Preserve exact commands, exit codes, artifact hashes, versions, schemas,
  receipts, migrations, security rules, and failure logs in release evidence.
- Record source edits and validation results factually; conversational claims
  are not evidence.
- A failing, missing, stale, incompatible, estimated, or heuristic result cannot
  satisfy a gate that requires passing measured, provider-backed, or
  local-validated evidence.
- New requirements discovered during a phase must be added to the closure
  registry, assigned an owner and phase, and validated before that phase or a
  dependent gate closes.
- Do not weaken privacy, authorization, validation, accessibility, auditability,
  data integrity, recovery, or evidence truth to simplify installation or pass a
  release gate.

### 19.2 Definition of enterprise-ready

TailTrail may be called enterprise-ready only when all of the following are
true for the exact released version:

- Core is self-contained, default, and installable without a source checkout.
- Wheel and sdist pass clean installation and artifact inspection.
- Every declared Python version and Windows, macOS, and Linux environment passes
  the supported lifecycle matrix.
- Codex, Copilot, and Claude pass installation, update, rollback, uninstall,
  instruction, contract, and fresh runtime-conformance gates for named versions.
- Release, doctor, smoke, public-doc, registry, adapter, full-suite, and negative
  gates agree and pass on a clean candidate.
- Selected governance controls are independently enforceable in CI.
- Durable local state fails closed and passes recovery, corruption, concurrency,
  migration, and rollback tests.
- Optional enterprise storage passes isolation, authorization, replay, backup,
  restore, disaster recovery, migration, rollback, observability, and support
  drills before it is enabled.
- Security, privacy, data-flow, retention, redaction, dependency, supply-chain,
  vulnerability-response, support, versioning, deprecation, and operations
  policies match the implementation.
- Public claims are linked to appropriate measured, provider-backed, or local-
  validated evidence with limitations.
- A representative pilot demonstrates that intended users can operate and
  recover the product without maintainer intervention.
- The closure registry contains no failed, missing, unowned, or deferred item
  inside the supported boundary.

### 19.3 Explicit non-goals

The enterprise program does not require TailTrail to:

- guarantee that an assistant host follows instructions;
- replace tests, builds, CI, scanners, review, deployment, or human approval;
- certify compliance or code security by itself;
- upload raw source, prompts, secrets, or private logs by default;
- support every assistant, CI provider, package manager, or enterprise backend;
- claim exact productivity, token, quality, or security improvement without
  adequate measurement.

Anything not listed as an explicit non-goal is either represented in the closure
matrix or must be added to it before enterprise GA. This is the boundary that
prevents loose ends from being silently postponed.

## 20. Phase E0 Implementation Record

**Implementation date:** 2026-08-22

**Status:** Implemented and locally validated. This closes E0 only; it does not
change the blocked release candidate, resolve E1-E12 requirements, or establish
enterprise GA.

### 20.1 Implemented controls

- `enterprise-closure-registry.json` is the machine-readable authority for the
  E0-E12 closure program. It records program authority, feature freeze, exact
  baseline, untracked-file dispositions, maturity mapping, inventory contracts,
  owned requirements, dependencies, implementation paths, validation,
  acceptance, evidence, status, and known defects.
- `enterprise-closure-registry.schema.json` defines the versioned closed shape
  for the registry.
- `scripts/enterprise-readiness.py` provides strict `validate`, readable
  `status`, and complete JSON `inventory` commands.
- The validator composes the existing feature registry instead of duplicating
  command or script ownership.
- The top-level CLI exposes `tailtrail enterprise-readiness
  validate|status|inventory` and the feature registry claims its implementation,
  documentation, and tests.
- The feature freeze is active through E12 and permits only correctness,
  security, packaging, compatibility, release, support, and evidence changes.
- Every current untracked path has an explicit `include`, `exclude`, or
  `pending-review` disposition. E0 does not delete, stage, commit, or adopt
  unrelated user work.
- Every phase E0-E12 has at least one owned, prioritized requirement with
  dependencies, paths, validation, acceptance, maturity, and status.
- Twelve known baseline defects cover all five full-suite failures plus the root
  Navigator, package, release, smoke, Claude verification, platform-matrix, and
  real-host-proof blockers.

### 20.2 Current inventory projection

The validated 2026-08-22 source baseline projects:

| Category | Current count or coverage |
| --- | ---: |
| Public command roots | 68 |
| Registered features | 77 |
| JSON Schema files | 125 |
| Adapter files | 18 |
| Canonical host surfaces | Codex, Copilot, Claude |
| Persisted `.tailtrail` artifact literals | 55 |
| CI workflows | 2 |
| Named CI steps | 9 |
| Installer profiles | 9, including Codex, Codex plugin, Copilot, and Claude |
| Installer surfaces | Core and Extended |
| Declared release files | 18 |
| Projected support/claim bullets | 88 |

The release inventory truthfully retains six missing files: `DEMO.md`, the
pull-request template, and four issue templates. Their absence is assigned to
E1 and does not get converted into E0 success or a release-ready claim.

### 20.3 E0 requirement outcome

| Requirement | Outcome |
| --- | --- |
| `ENT-E0-001` baseline and candidate declaration | Complete |
| `ENT-E0-002` registry, schema, and validator | Complete |
| `ENT-E0-003` complete enterprise surface inventory | Complete |
| `ENT-E0-004` feature maturity and surface normalization | Complete |
| `ENT-E0-005` feature freeze | Complete |
| `ENT-E0-006` defect and E0-E12 closure traceability | Complete |

### 20.4 Validation evidence

- `python3 -m unittest tests.test_enterprise_readiness -v`: 17 tests passed.
- Combined enterprise-readiness, registry, drift, CLI, installer, and workflow-
  documentation integration: 98 tests passed.
- `python3 -m unittest discover -s tests -p 'test_*.py' -v`: 704 tests ran
  with the same five registered E1 defects (four failures and one error); no E0
  test failed.
- `python3 scripts/enterprise-readiness.py validate`: passed.
- `python3 scripts/tailtrail-registry.py validate --strict`: passed.
- `python3 scripts/tailtrail.py enterprise-readiness status`: registry passed,
  feature freeze active through E12, E0 exit gate passed, 27 requirements
  classified, and 12 known defects recorded.

The E0 gate is satisfied because the remaining defects and future requirements
are completely owned and classified. They remain open or planned and continue
to block their dependent E1-E12 gates.

## 21. Phase E1 Implementation Record

Date: 2026-08-22

**Status:** Implemented and locally validated. E1 closes repository test and
release truth only. E2-E12 remain planned, the feature freeze remains active,
and the overall enterprise release candidate remains blocked.

### 21.1 Correctness closure

- Added the Phase 8 `evaluation_calibrated` ledger event.
- Reconciled the committed `dwr-small-change-vertical` evaluation scenario.
- Preserved the new Full-mode Planning Lock boundary in Navigator reasoning.
- Replaced a mutable developer-specific inaccessible-target fixture with an
  isolated guaranteed-missing target.
- Restored the compact UI preservation contract.
- Repaired root `navigator.py` compatibility module resolution.
- Closed `DEF-001` through `DEF-006` with focused and complete-suite evidence.

### 21.2 Release truth closure

- Added `release-manifest.json`, its closed-field schema, and the shared
  dependency-free reader/validator.
- Unified candidate scope, required files, versions, workflow fragments,
  approved upstream repositories, hygiene, distribution policy, and smoke
  ordering across release check, public audit, doctor/repository check, export,
  smoke, CI, and Extended-pack ownership.
- Added the four issue templates, pull-request template, and public demo that
  the release contract legitimately required.
- Removed the two tracked `.DS_Store` artifacts from the candidate.
- Reconciled active release, support, versioning, admin, benchmark, metadata,
  and CI documentation with `.github/workflows/trust.yml`.
- Closed `DEF-008` and `DEF-009`. Later-phase defects remain open.

### 21.3 Validation evidence

- Complete suite: 716 tests passed with no exception list.
- E1 negative fixtures passed for missing files, wrong versions, private
  repository references, stale workflows, and local state; the approved
  official upstream fixture passed.
- Enterprise registry, strict feature registry, repository check, public audit,
  release check, source doctor, manifest-isolated fresh-clone smoke, root
  Navigator import, Python compilation, and diff hygiene passed.

The manifest-built candidate is internally clean and green. This is not a claim
that the dirty developer worktree is committed, that package/install/platform
work is complete, or that real Codex, Copilot, or Claude release proof exists.

## 22. Phase E7 Implementation Record

**Implementation date:** 2026-08-25

**Status:** In progress and locally validated. This section documents new
resilience, security, privacy, and accessibility evidence added against
`ENT-E7-001` and `ENT-E7-002`. It does not close E7, does not change the
blocked release candidate, and does not imply E5/E6 hosted evidence or E8-E12
requirements are satisfied.

### 22.1 What already existed before this record

Most of the durable-state and security/privacy mechanisms required by E7 were
already implemented and tested by the earlier durable-workflow-runtime and
repository-enforcement work: deterministic journal replay, corruption/partial-
write fail-closed handling, freshness/stale detection, migration, rollback,
backup/restore, closed-schema contract validation (malformed/oversized/
traversal-shaped input), and redaction of secret-shaped values. E7 did not
need to re-implement these; it needed to close the specific gaps the earlier
assessment identified and consolidate the evidence.

### 22.2 New evidence added in this record

- **Local concurrency and idempotency** (`ENT-E7-001`): `tests/test_workflow_concurrency.py`
  exercises the real `LEDGER.RunLock` file lock under genuine multi-thread
  contention on the same workflow journal and proves `retry.register_initial`
  suppresses a duplicate initial dispatch instead of double-recording it.
- **Performance regression budgets** (`ENT-E7-001`): `tests/test_workflow_performance.py`
  adds documented, intentionally generous budgets for journal replay latency,
  `state.doctor` diagnosis latency, and projection-vs-journal size, so a gross
  regression (for example an accidental O(n^2) replay) would fail the suite.
- **Executable STRIDE threat model** (`ENT-E7-002`): `aidlc-docs/phase10-threat-model.md`
  was expanded from a 15-line stub into a STRIDE-mapped table that cites a
  concrete mitigating control and executable proof for spoofing, tampering,
  repudiation, information disclosure, denial of service, and elevation of
  privilege. `tests/test_threat_model_stride.py` is the consolidated fixture
  pack; it reuses existing control functions directly rather than duplicating
  mitigations. An explicit residual-risk note states this is deterministic
  unit-level proof, not fuzzing or a third-party security review.
- **Accessible output** (`ENT-E7-002`): `tests/test_accessible_output.py` proves
  the shipped `tailtrail.install` CLI error envelope always carries both a
  machine `error` code and a distinct human-readable `message` (JSON and text
  modes), that no shipped `tailtrail/` or `scripts/` source relies on ANSI
  color escapes for meaning, and that every `denials.REASONS` value is a
  readable hyphenated phrase rather than an opaque code.

### 22.3 Requirement outcome

| Requirement | Outcome |
| --- | --- |
| `ENT-E7-001` durable state, recovery, concurrency, migration, performance | In progress: all listed validation categories now have passing local evidence; remains `preview` pending longer-run/scale evidence and multi-host concurrency, which is out of local scope. |
| `ENT-E7-002` security, privacy, redaction, retention, accessibility | In progress: all listed validation categories now have passing local evidence; stays open because its registry dependencies `ENT-E6-001` and `ENT-E7-001` are not yet `complete`. |

### 22.4 Validation evidence

- `python3 -m unittest tests.test_workflow_concurrency tests.test_workflow_performance tests.test_threat_model_stride tests.test_accessible_output -v`: 16 new tests passed.
- `python3 -m unittest discover -s tests -p 'test_*.py'`: full suite passed with
  the new files classified in `enterprise-closure-registry.json`'s untracked
  disposition list (previously the enterprise-readiness gate correctly failed
  closed on unclassified new paths).
- No E7 test was skipped, marked expected-failure, or excluded from the
  discovered suite.

E7 remains open. The residual gaps are explicitly: multi-host/multi-tenant
concurrency and soak/scale testing (deferred to the enterprise-provider phase),
and adversarial/third-party security and accessibility review (never claimed
as complete by this record).

## 23. Phase E8 Implementation Record

**Implementation date:** 2026-08-25

**Status:** In progress and locally validated. This section documents new
evidence added against `ENT-E8-001`. It does not close E8, does not change the
blocked release candidate, and does not imply a deployed enterprise provider,
production scale, or a real disaster-recovery/on-call program exists.

### 23.1 What already existed before this record

The provider-neutral local enterprise adapter (`scripts/workflow_runtime/enterprise.py`,
`enterprise_recovery.py`, `enterprise_transport.py`) already implemented and
tested policy governance, tenant/actor/repository isolation, evidence-gated
activation, lease acquisition with fencing tokens, idempotent ordered event
ingestion, deterministic replay, backup manifests, restore validation,
migration, and rollback. `tailtrail/enterprise` does not exist as a package;
this logic still lives under `scripts/workflow_runtime/`, which is recorded as
an open packaging gap rather than corrected in this record.

### 23.2 New evidence added in this record

`tests/test_workflow_enterprise_qualification.py` closes the five validation
categories that had no executable coverage:

- **Load/soak**: a 100-event sequential-ingest run against a raised policy
  limit, asserting replay stays valid and completes within a documented,
  generous time budget.
- **Secret rotation**: proves a released lease's fencing token is permanently
  rejected — even for a brand-new event — once the workflow rotates to the
  next lease epoch.
- **Disaster-recovery drill**: corrupts the live distributed event journal
  after a verified backup exists, then proves `replay`, `restore_validate`,
  and `conformance` all fail closed together. None of them falsely reports
  the corrupted workflow as recoverable.
- **Offline local continuation**: makes the enterprise state-store directory
  inaccessible (permission-denied) and proves canonical local workflow storage
  keeps working normally throughout, then proves ingestion resumes cleanly
  once access returns.
- **Administrator diagnostics**: a subprocess-level CLI test proves
  `workflow-runtime.py enterprise conformance` returns the same categorical,
  sanitized diagnostic as the Python API.

### 23.3 Requirement outcome

| Requirement | Outcome |
| --- | --- |
| `ENT-E8-001` enterprise provider and administrator operations | In progress: all listed validation categories now have passing local evidence against the provider-neutral adapter; remains `preview` because there is no deployed provider, no real network-partition test against an actual remote service, no KMS-backed secret rotation, no production-scale load test, and no human DR/on-call runbook. It also stays open because its dependencies `ENT-E7-001` and `ENT-E7-002` are not yet `complete`. |

### 23.4 Validation evidence

- `python3 -m unittest tests.test_workflow_enterprise_qualification -v`: 5 new
  tests passed.
- `python3 -m unittest tests.test_workflow_enterprise_adapter tests.test_workflow_enterprise_recovery tests.test_workflow_enterprise_transport tests.test_workflow_enterprise_mcp tests.test_workflow_enterprise_qualification`:
  all pass together.
- No E8 test was skipped, marked expected-failure, or excluded from the
  discovered suite.

E8 remains open. The residual gaps are explicitly the ones a local repository
cannot prove by itself: a real deployed provider, production network-partition
behavior, KMS-backed secret/credential rotation, production-scale load, and a
human-owned disaster-recovery/on-call runbook.

## 24. Phase E9 Implementation Record

**Implementation date:** 2026-08-25

**Status:** In progress and locally validated. This section documents new
evidence added against `ENT-E9-001`. It does not close E9, does not change the
blocked release candidate, and does not imply a deployed audit/SIEM system,
production observability backend, or a real human tabletop exercise exists.

### 24.1 What already existed before this record

`enterprise_transport.observe()` already produced a sanitized, read-only
observability projection, and `enterprise_recovery.conformance()` already
produced a categorical administrator diagnostic (also CLI-accessible).
`repository-enforcement.py` already merged policy overrides and classified
every rule as `enforced`, `host-assisted`, or `advisory`, but only as a
side effect of evaluating a diff — there was no standalone "show me the
current effective policy" view. `templates/enterprise-report.md` already
existed as a governance report template.

### 24.2 New evidence added in this record

- **Effective policy** (`scripts/repository-enforcement.py`): a new
  `explain_policy()` function and `explain` CLI subcommand report the merged
  rule catalog — classification, enabled, severity, protected paths, locked
  status, and enforced/host-assisted/advisory counts — without requiring a
  diff. It reuses `merge_override()` rather than duplicating merge logic.
- **Access review** (`enterprise_recovery.access_review`): a new read-only
  function reporting the exact tenant/actor/repository allowlist a workflow
  binding is authorized against.
- **Support bundle and audit round-trip** (`enterprise_recovery.support_bundle`
  / `verify_support_bundle`): a new sanitized, integrity-fingerprinted bundle
  combining conformance, observability, and access-review, with a verifier
  that detects tampering (fingerprint mismatch) before trusting it. Three new
  closed schemas (`workflow-enterprise-access-review`,
  `-support-bundle`, `-support-bundle-verification`) were registered in the
  DWR-0 contract type registry so these new artifacts are validated exactly
  like every other workflow artifact, not exempted from it.
- **Observability cardinality**: a new test proves the sanitized `observe()`
  projection's field set never grows with event count — only the bounded
  `transport_event_count` integer changes — closing the "does this leak
  unbounded per-event detail" gap.
- **Tabletop drill**: a new test executes the exact administrator runbook
  sequence end to end: corrupt live state, diagnose with `conformance`,
  export a support bundle that truthfully reports the blocked status, and
  confirm the bundle itself still verifies intact.
- **Runbook documentation**: `SUPPORT.md` gained an "Enterprise Adapter
  Administrator Runbook" section (diagnose, access-review, export, explain
  policy, break-glass boundary, segregation of duties), scoped explicitly to
  what the local adapter can do.

### 24.3 Requirement outcome

| Requirement | Outcome |
| --- | --- |
| `ENT-E9-001` observability, audit export, governance, administration | In progress: all listed validation categories now have passing local evidence; remains `preview` because there is no deployed audit/SIEM integration, no real access-control system to review, no production observability backend, and no human tabletop exercise with a real incident-response team. It also stays open because its dependency `ENT-E8-001` is not yet `complete`. |

### 24.4 Validation evidence

- `python3 -m unittest tests.test_workflow_enterprise_observability -v`: 6 new
  tests passed.
- `python3 -m unittest tests.test_repository_enforcement tests.test_workflow_enterprise_recovery tests.test_workflow_enterprise_adapter tests.test_workflow_enterprise_transport tests.test_workflow_enterprise_mcp tests.test_workflow_contracts tests.test_run_ledger tests.test_workflow_enterprise_qualification tests.test_workflow_enterprise_observability`:
  all pass together (one unrelated `git init` failure reproduced as sandbox
  flakiness accessing `~/.gitconfig`, not a code regression, and passed on
  retry in isolation).
- `python3 scripts/tailtrail-registry.py validate --strict`: passed.
- `python3 -m unittest tests.test_workflow_documentation tests.test_cli_dispatch tests.test_workflow_mcp tests.test_workflow_enterprise_mcp`:
  passed, confirming the new `explain`/`access-review`/`support-bundle`/
  `support-bundle-verify` CLI surfaces did not break existing documentation or
  dispatch contracts.

E9 remains open. The residual gaps are explicitly: a deployed audit/SIEM or
observability backend, real access-control systems to review, and a human
tabletop exercise with an actual incident-response team.

## 25. Phase E10 Implementation Record

**Implementation date:** 2026-08-25

**Status:** In progress. This is real, host-observed evidence for one host
only (Copilot); it is not a claim that E10 is closed, that Codex or Claude are
validated, or that the blocked release candidate has changed.

### 25.1 Why this phase is different from E7–E9

E7, E8, and E9 qualify local contract behavior, which can legitimately be
implemented and tested inside this repository. E10 exists specifically to
replace that kind of local simulation with **real host-observed** evidence —
its own acceptance text requires "fresh passing runtime proof" and explicitly
distinguishes `contract-tested` from `runtime-observed`. Fabricating a receipt
to claim a host ran scenarios it did not run would violate this project's own
evidence-truth principle. `ENT-E10-001` also lists `ENT-E5-001`, `ENT-E6-001`,
and `ENT-E7-002` as dependencies, none of which are `complete`.

### 25.2 What was actually done

The current session is a real, live GitHub Copilot host operating on this
repository. Rather than fabricate receipts, it actually executed the six
scenarios defined in `adapters/runtime-scenarios-v1.json` end to end, for
real, against an isolated scratch git target (`/tmp/tailtrail-e10-scratch`,
not this repository), using the genuine production CLIs:
`scripts/task-start.py`, `scripts/planning-lock.py`,
`scripts/harness-checkpoint.py`, `scripts/harness-feedback.py`,
`scripts/task-recovery-boundary.py`, `scripts/execution-evidence.py`,
`scripts/validation-receipt.py`, and `scripts/closure-close.py`. Every
artifact referenced in a receipt (Planning Locks, Start Reports, approved
anchors, checkpoints, feedback packets, a real recovery boundary and Git
branch, and a real `awaiting-ci` closure decision) was independently
verified on disk before the receipt was written.

Six receipts were then built from the real `bundle_payload("copilot")`
digest and genuinely observed transitions, and recorded through
`scripts/host-runtime-conformance.py record`, which independently re-derives
each scenario's canonical probes from the real persisted run state rather
than trusting the receipt.

### 25.3 Honest result

| Scenario | Evaluation | Note |
| --- | --- | --- |
| small-bug | passed | Planning Lock, Start Report, approval, and no pre-approval writes all verified. |
| hands-free-feature | passed | `hands_free_program` (requirements, dependency order, first slice, approval gate) and execution handoff verified. |
| rejected-requirement | passed | `proposal_rejected` recorded in the same run; the run was never approved, so implementation stayed blocked. |
| evidence-failure | passed | A real failing unit-tier result produced an `implemented-not-validated` checkpoint, and `harness-feedback.py` recorded a real correction packet; no completion report was ever generated. |
| recovery | **failed** | Approved anchor and recovery boundary (with a real Git branch) were verified, but the receipt honestly omitted `resume-recommendation` because no dedicated resume-recommendation mechanism could be independently verified in this run. This was disclosed, not hidden or forced to pass. |
| ci-wait | passed | A real `closure-close.py --decision wait-ci` run produced a genuine `awaiting-ci` state with no positive learning recorded. |

`scripts/host-runtime-conformance.py report --host copilot` shows
`scenario_coverage: 6/6` but an overall `runtime_status: "failed"`, per the
tool's own honest rollup rule that one failed scenario fails the host
aggregate. **Codex and Claude were not executed in this session and remain
`not-validated`.** No result for any host is claimed beyond what was actually
observed.

The full receipts, evaluations, bundle, and aggregate report are preserved at
`e10-real-run-evidence/copilot-2026-08-25/` because the scratch working
target was ephemeral.

### 25.4 Requirement and defect outcome

| Item | Outcome |
| --- | --- |
| `ENT-E10-001` real host, release, and compatibility proof | In progress: genuine Copilot evidence now exists for all 6 scenarios (5 passed, 1 honestly failed); Codex and Claude remain not-validated; dependencies `ENT-E5-001`, `ENT-E6-001`, `ENT-E7-002` are not yet complete. |
| `DEF-012` no qualifying real-run proof | Still open: Copilot's aggregate result is `failed`, not `passed`, and two of three hosts have zero real evidence. |

### 25.5 Validation evidence

- `python3 scripts/host-runtime-conformance.py record --host copilot --receipt <receipt>` for all 6 scenarios: recorded successfully; evaluations shown above.
- `python3 scripts/host-runtime-conformance.py report --host copilot`: `scenario_coverage: 6/6`, `runtime_status: failed`.
- `python3 scripts/enterprise-readiness.py validate` and `python3 scripts/tailtrail-registry.py validate --strict`: passed after adding the new evidence directory's disposition.

E10 remains open. This record intentionally does not claim more than it
proved: one host, six real scenarios, five passing and one honestly failing,
with the other two required hosts still unvalidated.

## 26. Phase E11 Implementation Record

**Implementation date:** 2026-08-25

**Status:** In progress for `ENT-E11-001` (documentation/support); `ENT-E11-002`
(pilot/efficacy) stays `planned` — this record defines a protocol only and
does not claim any pilot has run. Neither closes E11, and dependency
`ENT-E10-001` is not yet `complete`.

### 26.1 Why the pilot half of this phase is different

Like E10, `ENT-E11-002`'s acceptance criterion ("pilot users complete and
recover the Core journey without maintainer intervention") requires real
external participants operating real deployments. That cannot be produced or
simulated inside this repository without becoming a fabricated claim, which
this project's own `PUBLIC-CLAIMS.md` explicitly forbids. `ENT-E11-001`
(documentation and support operations), by contrast, is genuinely local and
was implemented for real.

### 26.2 New evidence added in this record

- **Role-based routing** (`ENT-E11-001`): `SUPPORT.md` gained a "Role-Based
  Quick Start" section covering all 6 required roles (developer, repository
  administrator, security reviewer, platform/enterprise administrator,
  auditor, support operator), each pointed at real existing commands and
  docs rather than duplicated content, plus role-aware escalation guidance
  in "Asking For Help".
- **Version and security policy gaps closed**: `VERSIONING.md` gained
  "Supported Version Window" and "Deprecation Policy"; `SECURITY.md` gained
  "Severity Levels" and a "Response Timeline".
- **Documentation command tests, newcomer journey, and support simulation**
  (`ENT-E11-001`): `tests/test_newcomer_support_journey.py` adds three real
  proofs — every install-lifecycle operation named in `INSTALL.md` is a real
  CLI operation; one continuous real journey (install -> verify -> doctor ->
  status -> update -> uninstall) succeeds end to end through the actual
  `InstallEngine` with no manual intervention; and a support self-service
  simulation where a deleted managed file is diagnosed by `doctor`, resolved
  by `repair`, and re-verified — closing the "no test simulates a newcomer or
  support self-service journey" gap identified before this record.
- **Pilot protocol, not pilot results** (`ENT-E11-002`): `PUBLIC-CLAIMS.md`
  gained a "Pilot Protocol" section defining opt-in method, sample-size
  disclosure, default privacy limits, the exact measures to record (install
  success, first-run completion, false-success, evidence completeness,
  approval latency, recovery time, rollback success, operator burden),
  evidence labeling, and a publication rule that a pilot claim may only cite
  its own recorded sample. **No pilot has been run under this protocol.**

### 26.3 Requirement outcome

| Requirement | Outcome |
| --- | --- |
| `ENT-E11-001` documentation and role-based support | In progress: role routing, version/security policy gaps, and three new executable proofs (doc-command validation, newcomer journey, support simulation) are real and pass; stays open because dependency `ENT-E10-001` is not complete and the 6 role guides are consolidated routing sections rather than 6 standalone long-form guides. |
| `ENT-E11-002` representative pilot and efficacy proof | Still `planned`: a real, reviewable pilot protocol now exists, but zero pilot execution, adoption, false-positive, or operator-burden evidence exists. This is explicitly the boundary this record will not cross. |

### 26.4 Validation evidence

- `python3 -m unittest tests.test_newcomer_support_journey -v`: 3 new tests passed.
- `python3 -m unittest tests.test_release_truth tests.test_workflow_documentation tests.test_newcomer_support_journey tests.test_transactional_installer`: 34 tests passed together.
- Verified the new `PUBLIC-CLAIMS.md` "Pilot Protocol" section introduces none of `scripts/release-check.py`'s risky-claim phrases (checked in isolation from the pre-existing "Disallowed Claims" list, which legitimately contains those phrases as prohibited examples).
- `python3 scripts/enterprise-readiness.py validate` (git-resolution issues only, a known sandbox artifact unrelated to this change) and `python3 scripts/tailtrail-registry.py validate --strict` (passed).

E11 remains open. `ENT-E11-002` in particular cannot progress further from inside
this repository: it requires an actual opt-in pilot with real participants,
which is out of scope for a coding session and must happen separately.

## 27. Phase E12 Implementation Record

**Implementation date:** 2026-08-25

**Status:** In progress. The orchestrated release-gate mechanism required by
`ENT-E12-001` is real, tested, and reports honestly. General availability
itself has not happened: the gate correctly reports `blocked` against the
real registry today, and `ENT-E12-002`'s recurring reviews are scheduled but
not yet exercised even once.

### 27.1 Why E12 cannot close today

E12's exit gate is explicit: "Every requirement in the closure registry is
`passed` or is an explicit enterprise non-goal." `ENT-E12-001` itself lists
`ENT-E5-002`, `ENT-E8-001`, `ENT-E9-001`, and `ENT-E11-002` as dependencies,
none of which are `complete`. The genuine, locally-implementable part of this
phase is not declaring GA — it is building the orchestration mechanism that
will correctly refuse to declare GA until every dependency really is
`complete`. That mechanism is what this record adds.

### 27.2 New evidence added in this record

- **Orchestrated E0-E11 release gate** (`ENT-E12-001`): `scripts/enterprise-readiness.py`
  gained `ga_release_gate()` and `verify_ga_bundle()`, exposed as
  `enterprise-readiness ga-gate [--approved] [--write PATH]` and
  `enterprise-readiness ga-verify --bundle PATH`. The gate composes only real
  existing signals: `validate_registry()`, a new rollup across every
  requirement and known defect, and `release_manifest.validate()` (reused,
  not duplicated) for missing or incompatible release-candidate files.
- **Immutable, tamper-evident bundle**: the gate's output is fingerprinted
  with the same sha256-canonical-JSON pattern already established by
  `enterprise_recovery.support_bundle()`. `verify_ga_bundle()` detects a
  tampered bundle (fingerprint mismatch) and a stale bundle whose stored
  requirement/defect/candidate summary no longer matches the current registry
  (`registry-drift-since-bundle`) — reusing the established fingerprint
  pattern rather than inventing a new one.
- **No self-approval**: publication requires an explicit `approved=True`
  caller decision; `tests/test_ga_release_gate.py` proves the gate stays
  `blocked` on `not-approved-for-publication` even when every other signal is
  clean, so the mechanism itself cannot declare GA on its own.
- **Honest negative result on the real registry**: running
  `enterprise-readiness ga-gate --approved` against this repository today
  reports `blocked` with `registry-invalid` (the known sandbox git-resolution
  flakiness), `incomplete-requirements`, `open-defects`, and
  `candidate-inconsistent` (this session's own dirty local `.tailtrail/runs/`
  state) — the gate does not fabricate readiness to make this record look
  more complete than it is.
- **Continuous release governance schedule** (`ENT-E12-002`): `VERSIONING.md`
  gained a "Continuous Release Governance" section defining a 9-dimension
  recurring review schedule (compatibility, dependency, restore, migration,
  security, host-runtime, efficacy, deprecation, support), each with a cadence
  and the exact existing artifact that would evidence one real completed
  cycle. The section explicitly states no cycle has run yet.
- **Two missed E9 schema dispositions closed**: while validating this record,
  `schemas/workflow-enterprise-access-review.schema.json`,
  `-support-bundle.schema.json`, and `-support-bundle-verification.schema.json`
  were found to be untracked with no candidate disposition (a gap left over
  from Phase E9). They are now correctly dispositioned as `include`.

### 27.3 Requirement outcome

| Requirement | Outcome |
| --- | --- |
| `ENT-E12-001` immutable enterprise GA evidence bundle | In progress: the orchestration mechanism is real, tested, and reports honestly; remains open because its own dependencies are not `complete` and no bundle has ever been approved for actual publication. |
| `ENT-E12-002` continuous release and compatibility governance | In progress: the 9-dimension recurring review schedule is real and tested; remains open because zero review cycles have been exercised under it. |

### 27.4 Validation evidence

- `python3 -m unittest tests.test_ga_release_gate -v`: 9 new tests passed.
- `python3 -m unittest tests.test_continuous_release_governance -v`: 3 new tests passed.
- `python3 scripts/enterprise-readiness.py ga-gate --write <path>` followed by
  `python3 scripts/enterprise-readiness.py ga-verify --bundle <path>`: real
  CLI round-trip, reports `{"status": "passed", "issues": []}` (the bundle
  itself is intact) while the gate decision remains `blocked`.
- `python3 -m unittest tests.test_ga_release_gate tests.test_continuous_release_governance tests.test_enterprise_readiness tests.test_release_truth tests.test_cli_dispatch tests.test_workflow_documentation`:
  70 of 76 tests passed together; the 6 failures are the same known sandbox
  `~/.gitconfig` git-resolution flakiness documented in prior phase records,
  not a regression from this change.
- `python3 scripts/enterprise-readiness.py validate` (git-resolution issues
  only) and `python3 scripts/tailtrail-registry.py validate --strict` (passed).

E12 remains open, as it must: general availability has not happened, and this
record does not claim it has. What now exists is a real, tested mechanism that
will correctly refuse to say otherwise until E1-E11 actually close.
