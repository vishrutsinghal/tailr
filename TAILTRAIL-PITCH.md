# TailTrail Detailed Pitch

TailTrail is a local-first helper layer for AI-assisted software development. It helps coding agents plan before changing code, load less noisy context, preserve existing safeguards, route tests and scanners through approval-first workflows, and produce reviewable evidence after work is done.

It is not a coding model, scanner, CI system, test framework, or replacement for human review. It is the workflow layer around AI coding assistants that helps teams use those assistants with more discipline.

## Executive Message

AI coding tools are powerful, but unmanaged usage often creates three problems:

- agents read too much irrelevant context and still miss the right files
- agents make changes before understanding local patterns, tests, and policy
- teams get weak evidence: unclear validation, vague review notes, and unsupported productivity claims

TailTrail addresses those problems with a Navigator-first workflow:

```text
Understand the request -> choose the right TailTrail path -> load focused context -> inspect exact source -> make the smallest maintainable change -> validate -> review -> capture learning only after approval -> report value with evidence labels
```

## Who Benefits

### Developers

Developers get a simpler way to ask for help without memorizing every TailTrail feature.

Example:

```text
Use TailTrail Navigator to fix claim amount validation and add focused tests. Show the plan before implementation.
```

Benefit:

- less prompt writing
- fewer broad repo reads
- clearer validation path
- reusable review and handoff notes

### Engineering Leads

Engineering leads get consistency across teams without forcing every repo into the same process.

Example:

```text
Use TailTrail report value for this month. Include quality, outcomes, learning hygiene, and token evidence labels.
```

Benefit:

- local evidence for adoption
- safer dependency choices
- better review readiness
- clearer pilot success criteria

### Platform And Enablement Teams

Platform teams get a portable pack that works across coding assistants through instruction files and deterministic scripts.

Example:

```bash
python3 scripts/tailtrail.py setup-scan --root /path/to/project
python3 scripts/tailtrail.py doctor
```

Benefit:

- project setup hygiene
- update path
- internal/public release separation
- local policy overrides

### Security, Risk, And Governance Reviewers

Governance reviewers get approval-first behavior and claim boundaries.

Example:

```text
Use TailTrail to summarize vulnerabilities from trivy.json and identify likely impacted files. Do not claim remediation without exact fixed-version evidence.
```

Benefit:

- no hidden scanner execution
- no unsupported exact token-savings claims
- no automatic learning capture
- local-first reporting posture

## Core Differentiator

TailTrail is not trying to be the biggest code intelligence engine. It is trying to be the most practical enterprise control layer around AI-assisted local development.

The product principles:

- **Navigator-first**: one orchestration path instead of many random feature triggers.
- **Approval-first**: commands that write, scan, build, test broadly, or record learning require user approval.
- **Local-first**: repo state, learning, graph cache, and reports stay local unless the user shares them.
- **Evidence-aware**: TailTrail labels whether metrics are estimated, local evidence, or measured telemetry.
- **Reuse-first**: existing project helpers, conventions, test patterns, and policy win over generic advice.
- **Small-diff discipline**: TailTrail pushes the assistant toward the smallest maintainable change.

## Research-Inspired Direction: Harness Optimization

TailTrail's next performance direction is inspired by the Meta-Harness idea from **"Meta-Harness: End-to-End Optimization of Model Harnesses."** The important lesson is simple: better AI results do not come only from changing the model. They also come from improving the harness around the model: prompts, context selection, tools, validation, scoring, failure review, and feedback loops.

TailTrail applies that idea in an enterprise-safe way:

```text
task -> Navigator plan -> focused context -> graph/policy/test evidence -> implementation -> validation -> review -> approved learning -> metric confidence
```

The bigger product vision is a **collective improvement loop**:

```text
central TailTrail repo
  -> teams pull or install TailTrail
  -> developers use TailTrail locally
  -> TailTrail records approved sanitized workflow evidence
  -> teams choose what evidence to share back
  -> central Meta-Harness aggregates repeated patterns
  -> maintainers review evidence-gated improvement proposals
  -> tested TailTrail improvements ship in the next release
  -> teams update to a better TailTrail
```

This gives TailTrail something stronger than static prompt files: an enterprise-safe learning cycle for the tool itself. It does not train on private code. It improves the operating harness around the assistant: routing, context loading, graph usage, validation prompts, token budget estimates, review quality, learning confidence, and metric labels.

The TailTrail Harness Review layer inspects local evidence after tasks and asks:

- did Navigator choose the right workflow?
- did TailTrail load the right context and avoid noise?
- did Code Graph or Review Graph point to useful files?
- did the assistant preserve local patterns and safeguards?
- was validation strong enough for the change?
- are token/value metrics estimated, local-evidence-backed, measured, or unsupported?
- did learning help, or was it stale, weak, or mismatched?

This matters for product performance:

- **More precise code writing**: the assistant works inside a tighter task harness with exact files, graph scope, local policy, validation expectations, and risk boundaries.
- **More concrete metrics**: value reports can show confidence bands instead of vague ROI claims.
- **Better workflow selection over time**: approved outcomes, validation results, quality events, and learning refresh signals can reveal when TailTrail was too heavy, too light, or missing a useful feature.
- **Safer improvement loop**: TailTrail can recommend rule or prompt changes for review without automatically rewriting itself.

The important governance point: TailTrail should apply Meta-Harness learning only when the evidence is strong enough. A single accepted task or one user's preference is not enough to change product behavior. The signal should repeat across meaningful tasks, show measurable impact, and be verifiable with tests, golden Navigator plans, benchmark scenarios, or value reports.

The intended improvement loop is:

```text
observe locally -> sanitize -> share by approval -> aggregate -> propose -> review -> implement -> validate -> release
```

This loop is now represented by concrete commands:

```bash
python3 scripts/tailtrail.py harness shared-summary --root . --write-result --approved
python3 scripts/tailtrail.py harness aggregate-shared --root .
python3 scripts/tailtrail.py harness propose --root . --proposal-id MH-2026-07-001
python3 scripts/tailtrail.py harness proposal-record --root . --proposal-id MH-2026-07-001 --status accepted
```

The proposal step shows likely impacted TailTrail files, line hints when available, implementation prompts, verification checks, degradation checks, and rollback guidance. It does not edit TailTrail automatically.

Enterprise story:

```text
One team repeatedly sees Java + Sonar tasks underestimate context.
Another team repeatedly sees vulnerability tasks miss graph overlays.
Another team repeatedly sees small bug fixes over-routed into heavy planning.

Each team shares only sanitized categorical evidence.
Central TailTrail sees the pattern, proposes a product change, validates it, and ships a better release.
Every team benefits without sharing source code, raw prompts, users, repo names, secrets, or scanner logs.
```

That is TailTrail's "collective conscience": approved evidence from many local workflows becomes safer central product improvement.

Example:

```text
Observed pattern:
18 Java + Sonar tasks underestimated context and missed Code Graph Mapper.

Proposed TailTrail change:
Route Java Sonar prompts to Code Graph Mapper earlier and raise the token budget band.

Verification:
Navigator golden tests pass, doctor passes, benchmark score improves from 21/32 to 29/32, and tiny lint tasks do not become noisier.

Rollback:
If the rule triggers too often, revert the proposal commit and record the proposal as rolled_back.
```

Example future metric language:

```text
Workflow fit: 87% accepted, medium confidence
Validation precision: high confidence, based on 14 accepted tasks with passing checks
Token reduction: estimated only, measured telemetry missing
Learning usefulness: 9 high-confidence reuse events, 2 stale patterns suppressed
```

Important claim boundary:

TailTrail should say it is **inspired by Meta-Harness-style harness optimization**. It should not claim guaranteed accuracy, automatic correctness, or exact ROI without measured telemetry and validation evidence.

Over time, TailTrail should improve because it can use approved local evidence: accepted plans, validation pass/fail, review outcomes, graph freshness, token budget accuracy, measured telemetry, requirement fulfillment, scanner routing, and learning quality. That does not train a new model by itself; it improves the operating wrapper and decision logic that guides the model. Any product behavior change should remain proposal-first, human-approved, test-backed, and reversible.

## Feature Pitch

## 1. TailTrail Navigator

Navigator is the entry point. It classifies the user request, selects relevant TailTrail features, lists context to load and avoid, suggests commands, and asks for approval before implementation.

Example prompt:

```text
Use TailTrail Navigator to fix payment validation and add focused tests. Show the plan only.
```

Likely selected path:

```text
Code Review Graph Lite -> Code Graph Mapper -> Review Lens -> QA / CI-Sonar Lens -> Test Precision Planner -> Learning Capture Trigger
```

Scenario:

A developer asks for a small bug fix. Without Navigator, the assistant may start editing or over-plan with lifecycle docs. With Navigator, TailTrail routes it as a small bug fix, skips AIDLC, recommends graph context and precise tests, and keeps learning capture as a post-task approval step.

Benefit:

- reduces workflow confusion
- prevents feature overlap from causing agent drift
- keeps tiny tasks lightweight
- gives users an editable plan before code changes

## 2. Token Autopilot, Token Harness, And Runtime Bridge

Token Autopilot decides whether token-saving behavior is worth using for a prompt. Token Slicer keeps large TailTrail guidance split into focused slices so the assistant loads only the relevant instructions. Token Harness adds the evidence layer: it classifies context exactness, runs structured reducers, records approved local ledger events, checks proof confidence, and optionally connects to an approved local compression adapter through a strict bridge contract.

Example prompt:

```text
Use TailTrail to review this auth middleware change. Keep context compact and load only relevant guardrails.
```

Scenario:

A repo has many TailTrail files: AIDLC, guardrails, review lenses, graph guidance, testing, learning, metrics. The assistant should not load all of them for a simple auth review. Token Autopilot routes toward relevant slices and avoids loading unrelated roadmap or release docs.

For bulky artifacts such as build logs, scanner output, JSON reports, or long documentation, Token Harness can do more:

```bash
python3 scripts/tailtrail.py token-harness route --path build.log
python3 scripts/tailtrail.py token-harness reduce --path build.log
python3 scripts/tailtrail.py token-harness ledger summary
python3 scripts/tailtrail.py token-harness proof report
```

Recent implementation: **Optional Runtime Compression Bridge**.

```bash
python3 scripts/tailtrail.py token-harness bridge plan --path build.log
python3 scripts/tailtrail.py token-harness bridge input --path build.log --output /tmp/bridge-input.json
python3 scripts/tailtrail.py token-harness bridge validate-output --input /tmp/bridge-input.json --output /tmp/bridge-output.json
python3 scripts/tailtrail.py token-harness bridge run --path build.log --adapter-command "local-compressor --stdin" --approved
```

Bridge pitch:

- disabled by default
- requires local policy opt-in
- requires `--approved` before running an adapter
- blocks source, diffs, config, dependency manifests, lock files, security policy, secrets, unknown content, and must-be-exact context before adapter execution
- validates adapter output against exactness, retrieval, preserve-list, and blocked-reduction rules
- falls back safely when adapter output is invalid
- does not bundle a compressor, call a network service, manage credentials, or act as an HTTP proxy

Benefit:

- less repeated context
- lower prompt noise
- fewer irrelevant instructions competing for attention
- better fit for large org repos
- safer use of external/local compression tools without trusting them blindly
- clearer proof boundaries for token-savings claims

Metric example:

```text
Task: small validation bug
Without TailTrail estimate: 18,000 context tokens from broad file reads and repeated docs
With TailTrail estimate: 7,500 context tokens from Navigator, graph cache, exact files, and focused test plan
Estimated reduction: 58%
Evidence label: estimate, not exact API telemetry
```

Pitch boundary:

TailTrail should not claim exact token savings unless real model/API token telemetry is supplied.
The Runtime Compression Bridge is compatibility infrastructure, not a savings guarantee. It only accepts adapter output when TailTrail's exactness contract is preserved.

## 3. Code Review Graph Lite

Code Review Graph Lite maps likely callers, tests, helpers, manifests, and read order using simple explainable signals.

Example command:

```bash
python3 scripts/tailtrail.py graph --root /path/to/project --changed src/service/payment.py
```

Scenario:

A developer changes `payment.py`. TailTrail suggests likely tests, related helper files, and manifests before the assistant edits. It does not need an AST server or vector database for this first-pass context map.

Benefit:

- better first read
- fewer missed test files
- explainable heuristics
- no background service required

## 4. Code Graph Mapper

Code Graph Mapper creates a compact shared cache at `tailtrail-meta/code-graph-cache.json`. It can include files, symbols, references, likely tests, endpoints, SQL table hints, Terraform/config hints, ownership hints, and read order.

Example command:

```bash
python3 scripts/tailtrail.py graph map --root /path/to/project --changed services/claims-api/src/claims_api/validation.py
```

Scenario:

The same repo is used across several prompts. Instead of rediscovering project layout every time, TailTrail creates a reusable graph cache. Navigator checks whether the cache is missing, stale, fresh, or invalid.

Expected Navigator behavior:

```text
Missing graph: recommend graph map
Stale graph: recommend graph refresh
Fresh graph: reuse cached read order, then inspect exact source before editing
Tiny typo task: skip graph mapping
```

Benefit:

- speeds repo understanding
- reduces repeated reads
- helps scanner findings connect to impacted files
- gives a stable context object for future learning and reporting

## 5. AST Lite And AST V1

AST features provide deeper source structure when simple text signals are not enough. TailTrail currently supports lightweight AST-style mapping and deeper semantic metadata where available without requiring a full language server.

Example command:

```bash
python3 scripts/tailtrail.py ast map --root /path/to/project --changed src/service/claims.py
```

Scenario:

A function has multiple internal callers. The assistant needs symbol and reference hints before editing. AST Lite can identify definitions and local references so the assistant does not rely only on filename proximity.

Benefit:

- better code impact awareness
- less accidental caller breakage
- useful bridge before full semantic engines

## 6. AIDLC Portable Lifecycle

AIDLC provides lifecycle discipline for broad, risky, regulated, multi-step, or multi-team work.

Example prompt:

```text
Use AIDLC standard depth for a new claim override workflow. Ask recommended questions with reasoning before implementation.
```

Scenario:

A team is adding a workflow that touches requirements, design, implementation, validation, operations, and handoff. TailTrail creates lifecycle artifacts and asks questions with recommended answers and reasoning.

Benefit:

- clearer requirements
- better design traceability
- stronger handoff
- less “start coding before understanding” behavior

When not to use:

For small bug fixes, typo edits, or narrow test additions, Navigator should skip AIDLC.

## 7. Review Lenses

Review Lenses focus the assistant’s review on the right dimension: architecture, security, QA, maintainability, dependency, or general review.

TailTrail Review is Navigator-led. Users do not need to remember review commands or flags. For implementation work, TailTrail should offer a review of the uncommitted changes after the code is changed and validated. For standalone review requests, Navigator asks the smallest useful scope question when needed.

Review has two layers:

1. Requirement Fulfillment: checks whether the implementation appears aligned with the user request, Navigator plan, clarified requirements, or AIDLC requirements.
2. Code Health: checks bugs, validation gaps, weakened safeguards, duplicated logic, dependency risk, tests, and security concerns.

If requirement fulfillment is unclear, TailTrail asks clarification questions instead of assuming the implementation is complete.

Example prompt:

```text
Use TailTrail security review on this auth middleware diff. Check validation, authorization, token handling, and unsafe simplifications.
```

Post-implementation prompt:

```text
Use TailTrail to fix claim amount validation and review it after implementation.
```

Standalone review prompt:

```text
Use TailTrail to review my changes before PR.
```

Expected Navigator behavior:

```text
Implementation task:
implementation -> focused validation -> review uncommitted changes -> ask before fixes

Standalone review:
detect Git state -> recommend uncommitted changes or branch-vs-base -> ask if scope is unclear
```

Example review output:

```text
Review Scope
Reviewed uncommitted changes.

Requirement Fulfillment
Status: partially-aligned
- appears-addressed: blank amount validation
- unclear: null amount validation
Clarification needed:
- Where should TailTrail verify null amount behavior?

Summary
Critical: 0
Warning: 2
Info: 1

Warning | src/claims/ClaimValidator.java:84 | validateClaimAmount
Missing null/empty validation before claim amount parsing.
Impact: invalid input can throw a runtime error instead of returning validation response.
Fix: add explicit guard and focused unit test.
Confidence: high
Safe fix: yes, with approval
```

Clean review output:

```text
Review Scope
Reviewed uncommitted changes.

Summary
Critical: 0
Warning: 0
Info: 0

Result
No review issues found.

Checked for:
bugs, validation gaps, weakened safeguards, duplicated logic, dependency risk, security concerns, code consistency, and missing focused tests.
```

Scenario:

A developer updates middleware. A generic review might comment on style. Security Review checks trust boundaries and whether safeguards were weakened.

Benefit:

- more targeted reviews
- fewer generic comments
- better safeguard preservation
- less command memorization
- clear issue details with file, function, line, impact, fix, validation, confidence, and safe-fix status
- guarded fix loop after user approval
- implementation verification against the requested behavior
- learning from approved changes, requested changes, and clarifications after user approval

## 8. Dependency Gate

Dependency Gate makes new packages a deliberate decision.

Example prompt:

```text
Apply TailTrail dependency gate before recommending a date parsing package. Prefer standard library or existing framework capability.
```

Scenario:

An assistant suggests a package for date parsing. TailTrail asks whether the standard library, platform feature, framework helper, or existing dependency already solves it.

Benefit:

- fewer unnecessary dependencies
- lower supply-chain risk
- easier maintenance
- better enterprise policy alignment

Metric example:

```text
Month: July
Dependency gate events: 12
New dependency avoided: 7
Approved dependency additions: 2
Deferred pending owner review: 3
Evidence label: local approved events
```

## 9. Test Precision Planner

Test Precision Planner recommends likely test files, test cases in plain English, and focused validation commands.

Example command:

```bash
python3 scripts/tailtrail.py test plan --root /path/to/project --goal "fix claim amount validation" --changed services/claims-api/src/claims_api/validation.py --changed services/claims-api/tests/test_validation.py
```

Example output shape:

```text
Recommended cases:
- regression: zero amount should be rejected
- happy path: valid claim is accepted
- negative path: missing member id is rejected
- boundary path: minimum positive amount passes
- guard preservation: required validation remains intact

Focused validation:
- python3 services/claims-api/tests/test_validation.py
```

Scenario:

A developer asks for a bug fix and tests. TailTrail does not blindly run all tests or invent a huge test suite. It recommends the smallest test that proves the behavior.

Benefit:

- better test quality
- clearer validation evidence
- fewer broad, slow test runs
- easier PR review

## 10. CI/Sonar Intelligence

CI/Sonar Intelligence summarizes local CI, lint, Sonar, or quality-gate evidence without polling CI or querying Sonar automatically.

Example prompt:

```text
Use TailTrail Navigator to triage this Sonar quality-gate failure from ci/logs/sonar-quality-gate.log. Show the plan and ask before running anything.
```

Scenario:

A developer pastes a quality-gate issue or provides a local log. TailTrail routes to CI/Sonar Intelligence, asks before running scanners, and summarizes likely remediation evidence.

Benefit:

- no hidden network calls
- better quality-gate triage
- scanner commands stay approval-first

## 11. Quality Signal Scanner

Quality Signal Scanner recommends local checks based on manifests and project signals. It only runs approved allowlisted commands.

Example command:

```bash
python3 scripts/tailtrail.py quality scan --root /path/to/project
```

Scenario:

Before PR, the developer wants confidence. TailTrail identifies candidate checks such as unit tests, lint, Maven/Gradle checks, or npm scripts. It does not run broad or credentialed commands without approval.

Benefit:

- safer local validation
- consistent pre-PR confidence
- avoids surprise long-running commands

## 12. Security And Vulnerability Intelligence

TailTrail can parse local vulnerability evidence such as SARIF, Trivy JSON, and Grype JSON, then summarize impacted files/components.

Example commands:

```bash
python3 scripts/tailtrail.py vulnerability summarize --file ci/scanner-results/codeql.sarif --root /path/to/project
python3 scripts/tailtrail.py graph overlay --vulnerability ci/scanner-results/trivy.json --root /path/to/project
```

Scenario:

Security provides a SARIF or container scan file. TailTrail summarizes the issue, redacts common secret-like evidence, and links findings to likely impacted manifests or files.

Benefit:

- faster vulnerability triage
- structured evidence
- safer claims about remediation
- graph-aware impact mapping

Pitch boundary:

TailTrail does not replace SAST, SCA, container scanners, secret scanners, or security review.

## 13. Handoff

Handoff creates concise notes for reviewers or the next engineer.

Example prompt:

```text
Use TailTrail review and handoff for this validation change. Include changed behavior, validation evidence, risks, and deferred work. Do not claim tests passed unless evidence exists.
```

Scenario:

The developer finishes a fix. TailTrail prepares PR-ready notes that separate evidence from assumptions.

Benefit:

- faster reviews
- clearer ownership transfer
- fewer false validation claims

## 14. Local Policy Override

Projects can define local rules in `tailtrail-policy.md`.

Example policy:

```text
Do not add dependencies without owner approval.
Run python3 services/claims-api/tests/test_validation.py for validation changes.
Use Code Graph Mapper before broad source reads.
```

Scenario:

Each team has different test commands, dependency rules, restricted folders, and ownership expectations. TailTrail reads local policy before acting.

Benefit:

- adaptable across teams
- avoids one-size-fits-all governance
- keeps repo-specific truth close to code

## 15. Guardrails And Guardrail Layers

Guardrails prevent weak behavior such as unsupported validation claims, dependency additions without gate review, or removing safeguards to shorten code.

Example command:

```bash
python3 scripts/tailtrail.py guard check --root /path/to/project
```

Scenario:

An assistant says “tests passed” without evidence or proposes deleting validation to simplify code. Guardrails catch that as a behavior problem.

Benefit:

- fewer hallucinated claims
- better validation truth
- stronger safeguard preservation

## 16. Project Learnings And Learning Agent V2

Learning captures approved reusable patterns after meaningful work. It is confidence-gated and advisory.

Example command:

```bash
python3 hooks/learning-capture-hook.py "fixed validation bug" --root "/path/to/project" --tags "bug,qa" --candidate "Reject zero claim amount using existing validation result pattern." --acceptance accepted --validation-outcome pass --approved
```

Scenario:

A team repeatedly fixes similar validation bugs. After an accepted fix, TailTrail records the reusable pattern. Future Navigator plans can surface the learning as advisory context.

Guardrails:

- low-confidence changes are not trusted by default
- user acceptance alone is not enough if validation or safeguards are weak
- learnings never override current source, tests, CI, scanners, policy, or explicit user instructions

Benefit:

- repo memory without raw prompt logging
- less repeated discovery
- better future plans

## 17. Learning Refresh And Quality Loop

Learning Refresh reviews stale, weak, contradictory, or disputed learnings. Quality Loop reviews TailTrail behavior itself.

Example commands:

```bash
python3 scripts/tailtrail.py learn refresh recommend --root /path/to/project
python3 scripts/tailtrail.py quality loop summarize --root /path/to/project
```

Scenario:

A learning used to be valid, but the repo changed. TailTrail can recommend demoting, refreshing, suppressing, or reviewing that learning.

Benefit:

- prevents stale learning from becoming bad advice
- creates a feedback loop for improving TailTrail behavior

## 18. Outcome Telemetry And Enterprise Reporting

Outcome telemetry records approved compact events: accepted plans, validation pass/fail, review outcome, time-saved band, learning quality, and workflow fit.

Example command:

```bash
python3 scripts/tailtrail.py report value --root /path/to/project --month 2026-07
```

Scenario:

After a pilot, leadership wants to know if TailTrail helped. Reports show local signals with evidence confidence labels.

Example metrics:

```text
Pilot: 4 weeks, 3 teams, 18 recorded tasks
Accepted TailTrail plans: 15 / 18
Validation pass after TailTrail flow: 13 / 15 accepted tasks
Review approved without major rework: 11 / 15 accepted tasks
Dependency additions avoided: 7
Learning captures approved: 9
Learning captures rejected or skipped: 5
Escaped defect signals: 1
Evidence confidence: medium-local-evidence
```

Pitch boundary:

These are example metrics. Real claims require real recorded local events from the pilot.

## 19. Token Usage Reporting

TailTrail supports estimated and measured token evidence.

Token Budget Coach sits between rough estimates and exact telemetry. It learns local context-budget patterns from approved events, then Navigator uses that profile to pick a better starting budget and escalation threshold for similar tasks. Token Harness adds local proof discipline through context receipts, append-only ledger events, benchmark/proof reports, and bridge validation records.

TailTrail now also has a **Measured Evidence Portfolio**. BL-1 proved the measured-efficacy runner with one committed scenario; BL-1.5 expands that into representative committed scenarios across bug fix, review, security, CI/Sonar, dependency, feature, token-heavy artifact, and learning-governance work.

For the OpenAI Build Week presentation, TailTrail also has a focused **Evaluation Harness Build Week proof scenario**. The live `buildweek-demo-project/` remains the human demo, while `benchmarks/evaluation/scenarios/buildweek-validation/` gives judges a deterministic saved-artifact comparison:

```bash
python3 scripts/tailtrail.py eval scenario report --scenario buildweek-validation
python3 scripts/tailtrail.py eval scenario report --scenario buildweek-validation --format json
```

This is the cleanest proof line for a short pitch: TailTrail can tell the live story and also replay it as committed fixture evidence. The claim boundary is narrow and honest: this proves the saved artifacts and scoring path, not live model performance, production defect reduction, or exact token savings.

Example:

```bash
python3 scripts/tailtrail.py budget estimate "fix validation bug" --changed src/service/foo.py
python3 scripts/tailtrail.py budget record --task-type bug --initial-budget 8000 --actual-context 10500 --outcome underestimated --approved
python3 scripts/tailtrail.py budget profile
```

What this improves:

- initial budget estimates get closer over repeated local tasks
- Navigator knows when to ask for budget escalation
- teams can explain why a task needed more context
- teams can separate estimated, local-evidence, measured, and benchmark-measured token claims
- external compression experiments can be validated before they influence claims

Claim boundary:

```text
Token Budget Coach improves planning estimates. It is not exact model/API telemetry and does not prove exact savings.
Token Harness Bridge validates local adapter output. It does not prove exact model/API token savings without measured telemetry.
```

Example measured record:

```json
{
  "mode": "measured",
  "baseline": {"total_tokens": 42000},
  "tailtrail": {"total_tokens": 18000},
  "task": "validation bug with focused tests"
}
```

Example report:

```text
Baseline tokens: 42,000
With TailTrail: 18,000
Difference: 24,000
Reduction: 57.1%
Evidence label: measured API/model telemetry
```

Estimated example:

```text
Baseline estimate: broad source reads + repeated docs
TailTrail estimate: Navigator + graph cache + exact files + test plan
Estimated reduction: 45-60%
Evidence label: local estimate
```

Pitch boundary:

Do not present estimated savings as exact savings.

## 20. Release Mode Separation

TailTrail supports internal and public release separation so public-facing legal/support/release files do not leak into internal-only distribution, and internal-only admin material does not appear in public release exports.

Example:

```bash
TAILTRAIL_ADMIN=1 python3 scripts/tailtrail.py release-check
```

Benefit:

- safer internal rollout
- cleaner public release path
- fewer accidental release-mode leaks

## End-To-End Demo Story

Use the demo workspace in:

[demo-project-layout/tailtrail-demo-workspace/README.md](demo-project-layout/tailtrail-demo-workspace/README.md)

### Demo Prompt 1: Hello

```text
hello tailtrail
```

Value shown:

- install confidence
- zero workflow overhead

### Demo Prompt 2: Repo Overview

```text
Run TailTrail Navigator for: tell me important features of this repo. Show the plan only.
```

Value shown:

- read-only discovery path
- no over-triggering
- optional graph mapping

### Demo Prompt 3: Graph Mapping

```text
Approve deeper discovery. Generate the TailTrail code graph for this demo workspace, then summarize the read order.
```

Value shown:

- compact reusable repo context
- no need to rediscover layout repeatedly

### Demo Prompt 4: Bug Fix Plan

```text
Use TailTrail Navigator to fix claim amount validation and add focused tests. Show the plan before implementation.
```

Value shown:

- small bug fix skips AIDLC
- review, graph, tests, and learning are correctly routed
- implementation waits for approval

### Demo Prompt 5: Test Precision

```text
Use TailTrail Test Precision Planner for the claim amount validation fix. Show recommended test cases in plain English and the focused validation command.
```

Value shown:

- plain-English tests
- exact focused validation command
- no broad test run by surprise

### Demo Prompt 6: Review And Handoff

```text
Use TailTrail review and handoff for the claim validation change. Prepare reviewer notes, risk notes, and validation summary.
```

Value shown:

- PR readiness
- validation truth
- risk communication

### Demo Prompt 7: Learning Capture

```text
The claim validation fix was accepted and focused tests passed. Show the approved learning capture command, but do not run it yet.
```

Value shown:

- guarded learning
- no raw prompt logging
- approval-first repository memory

### Demo Prompt 8: Value Report

```text
Generate a local TailTrail value report for this demo task using available local evidence only.
```

Value shown:

- metrics with evidence labels
- no overstated ROI
- pilot-ready reporting posture

## Common Enterprise Scenarios

### Scenario A: Small Bug Fix

Prompt:

```text
Use TailTrail Navigator to fix parser bug in src/parser.py and add focused tests. Show plan only.
```

TailTrail path:

```text
Navigator -> Code Review Graph Lite -> Code Graph Mapper -> Review Lens -> Test Precision Planner -> Learning Capture Trigger
```

Benefit:

- avoids lifecycle overhead
- finds likely tests
- captures reusable learning only after acceptance

### Scenario B: Dependency Request

Prompt:

```text
Use TailTrail dependency gate. Should we add a package for CSV parsing, or use existing platform support?
```

TailTrail path:

```text
Dependency Gate -> Review Lens -> local policy check
```

Benefit:

- reduces unnecessary packages
- improves supply-chain posture

### Scenario C: Sonar Quality Gate

Prompt:

```text
Use TailTrail to triage this Sonar quality-gate failure. Ask before running commands.
```

TailTrail path:

```text
Navigator -> CI/Sonar Intelligence -> Quality Signal Scanner -> Scan Approval -> Review Lens
```

Benefit:

- clear triage
- no hidden scanner execution
- exact validation evidence

### Scenario D: Vulnerability Evidence

Prompt:

```text
Use TailTrail vulnerability intelligence with this SARIF file. Summarize impacted files and recommended next evidence.
```

TailTrail path:

```text
Security And Vulnerability Intelligence -> Structured Parser -> Graph Overlay -> Handoff
```

Benefit:

- faster vulnerability review
- structured evidence
- safer remediation claims

### Scenario E: Build Week Evaluation Harness Proof

Prompt:

```text
Show the repeatable TailTrail Build Week proof scenario. Use Evaluation Harness and keep claim boundaries clear.
```

TailTrail path:

```text
Evaluation Harness -> buildweek-validation scenario -> baseline-vs-TailTrail report -> claim boundaries
```

Command:

```bash
python3 scripts/tailtrail.py eval scenario report --scenario buildweek-validation
```

Benefit:

- turns the live demo into repeatable local evidence
- compares baseline and TailTrail-guided artifacts
- keeps exact token savings and live model-performance claims out of scope

### Scenario F: Regulated Multi-Step Feature

Prompt:

```text
Use AIDLC standard depth for a new approval workflow. Ask recommended questions with reasoning before implementation.
```

TailTrail path:

```text
AIDLC -> Requirements Questions -> Implementation Plan -> Validation Handoff
```

Benefit:

- better stakeholder alignment
- clearer approval gates
- reusable lifecycle artifacts

## Pilot Plan

Recommended pilot:

```text
Duration: 4 weeks
Teams: 2-3
Repos: 3-5
Task types: small bug fixes, validation changes, dependency decisions, review/handoff, scanner triage
Data captured: approved outcome events only
Excluded: raw prompts, secrets, customer data, hidden telemetry
```

Pilot success signals:

- developers can start with `tailtrail.py start` or `tailtrail.py guide`
- reviewers see better validation and handoff notes
- fewer unnecessary dependencies are proposed
- graph cache reduces repeated repo discovery
- scanner/test commands stay approval-first
- reports have enough evidence to guide rollout decisions

## Example Pilot Dashboard

```text
Tasks recorded: 40
Navigator plans accepted: 33
Plans edited before implementation: 5
Plans rejected: 2
Focused validation identified: 31
Validation pass after implementation: 27
Review approved without major rework: 24
Dependency additions avoided: 11
Approved learnings captured: 16
Learnings demoted or skipped: 6
Estimated token reduction range: 35-60%
Measured token records available: 8
Measured average reduction on those records: 42%
Evidence confidence: mixed local estimate + measured telemetry
```

Use this as a sample dashboard shape, not as a claim about real usage.

## Objection Handling

### Is this another AI agent?

No. TailTrail is a workflow and governance helper around coding agents. It gives assistants better local instructions, deterministic scripts, context routing, and evidence rules.

### Will it slow developers down?

Tiny tasks stay lean. Navigator only selects heavier features when the prompt or risk signals justify them.

### Does it upload code or telemetry?

TailTrail is designed local-first. Reports and learning files are local. Sharing is a user or organization decision.

### Is it a substitute for tests or scanners?

No. It recommends, summarizes, and routes evidence. Test execution, CI, scanners, code review, and security review remain the source of truth.

### Can learning become wrong?

Yes, if unmanaged. That is why TailTrail uses confidence bands, advisory-only learning, refresh review, and explicit approval.

### Can token savings be trusted?

Estimated savings are directional. Exact savings require real model/API token telemetry.

## Strong Closing

TailTrail makes AI-assisted development easier to trust because it does not ask teams to trust the assistant blindly. It makes the assistant show its path, load focused context, respect local policy, preserve safeguards, ask before risky actions, and produce evidence that reviewers can inspect.

The pitch is not “AI writes code faster.”

The pitch is:

```text
TailTrail helps teams use AI coding assistants with less noise, fewer risky shortcuts, better validation discipline, reusable local learning, and evidence-aware reporting.
```
