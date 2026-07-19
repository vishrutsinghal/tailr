# TailTrail Pitch Plan

This plan lists the resources, files, evidence, and demo assets needed to pitch TailTrail clearly without overselling it.

TailTrail should be pitched as a local-first AI coding governance helper that helps teams keep agent-assisted development smaller, safer, more reviewable, and more evidence-aware. It should not be pitched as a replacement for tests, CI, scanners, code review, security review, compliance review, or release approval.

## Pitch Goals

Use the pitch to answer five questions quickly:

1. What problem does TailTrail solve?
2. How does it fit into a normal developer workflow?
3. What makes it safe enough for enterprise use?
4. What evidence do we have today?
5. What is intentionally not claimed yet?

## Core Story

Short version:

```text
TailTrail helps AI coding assistants plan before changing code, load less noisy context, reuse existing project patterns, preserve safeguards, ask before risky commands, and produce reviewable validation and handoff evidence.
```

Longer version:

```text
TailTrail is a local-first helper layer for AI-assisted software development. It gives coding assistants a Navigator-first workflow, deterministic project analyzers, approval-first scanner/test routing, local learning governance, and evidence-aware reporting. It is designed for teams that want AI coding help without hidden automation, broad context loading, unsupported claims, or accidental policy drift.
```

## Pitch Audience

### Engineering Leaders

Care about:

- developer productivity
- code quality and review load
- consistency across teams
- reduced risky agent behavior
- measurable local evidence

Most relevant assets:

- `README.md`
- `DEMO.md`
- `PUBLIC-CLAIMS.md`
- `PUBLIC-ROADMAP.md`
- `ARCHITECTURE.md`
- `TAILTRAIL-COMMANDS.md`
- benchmark and value-report examples

### Developers

Care about:

- how to start using it
- what commands to run
- how much it interrupts normal work
- whether it can help with tests, Sonar, vulnerability, and PR prep

Most relevant assets:

- `QUICKSTART.md`
- `CHEATSHEET.md`
- `USEFUL-PROMPTS.md`
- `USER-GUIDE.md`
- `NAVIGATOR-TEST-SCENARIOS.md`
- `TAILTRAIL-COMMANDS.md`

### Security, Risk, And Governance Reviewers

Care about:

- approval-first behavior
- no hidden telemetry
- no scanner replacement claims
- public claim guardrails
- release separation
- local-only learning and reporting posture

Most relevant assets:

- `PUBLIC-CLAIMS.md`
- `SECURITY.md`
- `NOTICE.md`
- `LICENSE`
- `GOVERNANCE.md`
- `GUARDRAILS.md`
- `LEARNING-GOVERNANCE.md`
- `RELEASE-CHECKLIST.md`
- `scripts/release-check.py`
- `scripts/public-doc-audit.py`

### Platform Or Enablement Teams

Care about:

- rollout model
- assistant compatibility
- update path
- project setup hygiene
- local policy override
- internal/public distribution separation

Most relevant assets:

- `USER-GUIDE.md`
- `adapters/README.md`
- `ADMIN-RELEASE-MODES.md`
- `PUBLIC-RELEASE-METADATA.md`
- `scripts/install-local.py`
- `scripts/install-launcher.py`
- `scripts/update-tailtrail.py`
- `scripts/setup-scan.py`
- `tailtrail-policy.example.md`

## Required Pitch Resources

### 1. One-Page Executive Summary

Needed file:

- `PITCH-ONE-PAGER.md`

Purpose:

- explain the product in one page
- show problem, solution, workflow, differentiators, proof, and boundaries
- useful for leadership or internal approval

Suggested sections:

- Problem
- TailTrail approach
- Key capabilities
- What is local-only
- What requires approval
- Evidence available today
- What TailTrail does not replace
- Recommended pilot path

Status:

- Not created yet.

### 2. Demo Script

Existing files:

- `DEMO.md`
- `buildweek-demo-project/DEMO-RUNBOOK.md`
- `buildweek-demo-project/DEMO-PROMPTS.md`

Purpose:

- show a ten-minute demo path
- demonstrate Navigator, graph, quality scan, vulnerability summary, value report, and repeatable Evaluation Harness proof

Recommended improvement:

- keep the Build Week live demo under three minutes
- use `eval scenario report --scenario buildweek-validation` as the repeatable proof fallback
- add a second demo flow focused on `Test Precision Planner`
- add compact Navigator view demo
- add commands-only view demo for enterprise prompts

Status:

- Existing and usable.
- Build Week demo docs now include the completed `buildweek-validation` proof scenario.
- Needs refresh for newest testing and Navigator view features outside the Build Week path.

### 3. Pitch Deck Outline

Needed file:

- `PITCH-DECK-OUTLINE.md`

Purpose:

- create a slide-by-slide structure before building a deck
- keep public/internal claims accurate
- avoid unsupported ROI or security claims

Suggested slide flow:

1. Title: TailTrail
2. Problem: AI coding creates drift, noise, and weak evidence when unmanaged
3. Product: Navigator-first local helper for safer AI coding
4. Workflow: plan, inspect, implement, test, review, report
5. Capabilities: Navigator, Token Autopilot, Token Harness, Runtime Compression Bridge, Code Graph, Test Precision, CI/Sonar, Vulnerability, Learning, Reporting
6. Enterprise posture: local-first, approval-first, deterministic scripts
7. Demo: simple bug fix with unit tests
8. Demo: Sonar/vulnerability before PR
9. Evidence: benchmark harness, outcome telemetry, Token Harness ledger/proof, token evidence labels
10. Boundaries: what TailTrail does not replace
11. Rollout: pilot, policy pack, setup hygiene, reporting
12. Roadmap: measured metrics, deeper engines, public/internal packaging

Status:

- Not created yet.

### 4. Demo Evidence Pack

Needed folder:

- `pitch/evidence/`

Purpose:

- store sanitized demo outputs and sample reports
- support claims with reproducible local artifacts

Recommended files:

- `pitch/evidence/navigator-simple.md`
- `pitch/evidence/navigator-complex.md`
- `pitch/evidence/buildweek-validation-scenario.md`
- `pitch/evidence/buildweek-validation-scenario.json`
- `pitch/evidence/test-precision-plan.md`
- `pitch/evidence/test-coverage-summary.md`
- `pitch/evidence/value-report.md`
- `pitch/evidence/token-savings-estimate.md`
- `pitch/evidence/token-harness-bridge-plan.md`
- `pitch/evidence/token-harness-proof-report.md`
- `pitch/evidence/measured-evidence-portfolio.md`
- `pitch/evidence/benchmark-summary.md`

Rules:

- no customer names
- no private repo names
- no secrets
- no raw logs with sensitive content
- no claims of exact token savings unless measured telemetry is included
- no claim that the Runtime Compression Bridge guarantees savings; it only validates approved local adapter output

Status:

- Not created yet.

### 5. Demo Repo Or Scenario Set

Existing files:

- `NAVIGATOR-TEST-SCENARIOS.md`
- `buildweek-demo-project/`
- `benchmarks/evaluation/scenarios/buildweek-validation/`

Purpose:

- show simple-to-complex Navigator behavior
- verify routing before demos
- explain known workflow choices
- give the Build Week demo a deterministic saved-artifact proof path

Recommended improvement:

- keep the live `buildweek-demo-project/` small and human-readable
- keep the committed `buildweek-validation` scenario as the repeatable proof artifact
- otherwise keep scenario commands self-contained and use TailTrail's own repo for broader demos

Status:

- Existing and useful.
- Build Week proof scenario is implemented.

### 6. Product Architecture Overview

Existing file:

- `ARCHITECTURE.md`

Purpose:

- explain components and boundaries
- show why TailTrail is local-first and deterministic

Pitch use:

- include one architecture diagram in deck or demo
- show command surface, Navigator, scripts, docs, local state, and reports

Status:

- Existing.

### 7. Claims And Safety Pack

Existing files:

- `PUBLIC-CLAIMS.md`
- `SECURITY.md`
- `NOTICE.md`
- `LICENSE`
- `RELEASE-CHECKLIST.md`
- `scripts/release-check.py`
- `scripts/public-doc-audit.py`

Purpose:

- prevent unsupported marketing language
- make public release credible
- show exact allowed/cautious/disallowed claims

Pitch use:

- include a short "what we do not claim" section
- show evidence labels: estimated, measured, observed, advisory

Status:

- Existing and important.

### 8. User Adoption Pack

Existing files:

- `QUICKSTART.md`
- `CHEATSHEET.md`
- `USEFUL-PROMPTS.md`
- `USER-GUIDE.md`
- `TAILTRAIL-COMMANDS.md`

Purpose:

- make the product usable after the pitch
- reduce "what do I type?" friction

Pitch use:

- show the one-command path:

```bash
python3 scripts/tailtrail.py start "fix validation bug and add unit tests" --changed src/service/foo.py
```

- show plan-only path:

```bash
python3 scripts/tailtrail.py guide "fix Sonar quality gate failure and check vulnerability impact before PR" --changed src/main/java/PaymentValidator.java --view compact
```

- show testing confidence path:

```bash
python3 scripts/tailtrail.py test plan --changed src/service/foo.py --goal "fix validation bug"
python3 scripts/tailtrail.py test summarize --changed src/service/foo.py --goal "show implemented test cases"
```

Status:

- Existing and recently updated.

### 9. Metrics And Reporting Pack

Existing files:

- `benchmarks/README.md`
- `benchmarks/scenarios/`
- `benchmarks/efficacy/`
- `templates/value-report.csv`
- `templates/token-savings-report.md`
- `templates/token-usage-example.jsonl`
- `schemas/token-harness-bridge-input.schema.json`
- `schemas/token-harness-bridge-output.schema.json`
- `scripts/tailtrail-report.py`
- `scripts/benchmark-tailtrail.py`
- `scripts/efficacy-benchmark.py`
- `scripts/analyze-benchmark.py`
- `scripts/token-harness.py`
- `scripts/token-harness-bridge.py`
- `scripts/token-harness-ledger.py`
- `scripts/token-harness-proof.py`
- `scripts/token-harness-reduce.py`

Purpose:

- show evidence without overstating ROI
- distinguish estimated versus measured token data
- support pilots with local outcome telemetry

Pitch use:

- show benchmark examples as local artifacts
- show Evaluation Harness Build Week proof with `python3 scripts/tailtrail.py eval scenario report --scenario buildweek-validation`
- show BL-1.5 portfolio coverage across task types
- show value report sections
- explain token labels:
  - estimated
  - local-evidence
  - measured
  - benchmark-measured
- show bridge safety posture:
  - disabled by default
  - policy opt-in
  - approval required for adapter run
  - exactness validation before accepting output
  - no bundled compressor, proxy, network call, or credential handling

Status:

- Existing.
- Needs curated demo outputs in `pitch/evidence/`.

### 10. Roadmap And Investment Case

Existing files:

- `ROADMAP.md`
- `PUBLIC-ROADMAP.md`
- `V2-IMPLEMENTATION-GUIDE.md`
- `HONEST-REVIEW.md`
- `HONEST-REVIEW-IMPLEMENTATION-PLAN.md`

Purpose:

- show maturity and next steps
- separate public-facing roadmap from internal planning
- acknowledge known limitations

Pitch use:

- public pitch should use `PUBLIC-ROADMAP.md`
- internal strategy discussion can use `ROADMAP.md`, `HONEST-REVIEW.md`, and implementation plans

Status:

- Existing.

## Recommended Pitch Package

### Internal Pitch Package

Include:

- `PITCH-ONE-PAGER.md`
- `PITCH-DECK-OUTLINE.md`
- `DEMO.md`
- `README.md`
- `USER-GUIDE.md`
- `USEFUL-PROMPTS.md`
- `NAVIGATOR-TEST-SCENARIOS.md`
- `ARCHITECTURE.md`
- `ROADMAP.md`
- `HONEST-REVIEW.md`
- `ENTERPRISE-REVIEW.md`
- `pitch/evidence/`

Keep internal-only:

- internal rollout risks
- internal adoption plan
- enterprise scoring
- private pilot notes
- internal feature backlog

### Public Pitch Package

Include:

- `PITCH-ONE-PAGER.md`
- `PITCH-DECK-OUTLINE.md` with public-safe wording
- `README.md`
- `DEMO.md`
- `ARCHITECTURE.md`
- `PUBLIC-CLAIMS.md`
- `PUBLIC-ROADMAP.md`
- `SECURITY.md`
- `SUPPORT.md`
- `CHANGELOG.md`
- `LICENSE`
- `NOTICE.md`
- sanitized `pitch/evidence/`

Exclude:

- internal strategy docs
- private organization names
- private repo names
- raw local telemetry
- unsupported impact claims
- internal-only release mode details

## Demo Flows To Prepare

### Demo 1: Small Bug Fix With Tests

Purpose:

- show that TailTrail keeps a small bug fix lean
- show Test Precision Planner
- show no AIDLC over-selection

Commands:

```bash
python3 scripts/tailtrail.py guide "fix payment validation bug and add unit tests" --changed src/service/payment.py --view compact
python3 scripts/tailtrail.py test plan --changed src/service/payment.py --goal "fix payment validation bug"
python3 scripts/tailtrail.py test summarize --changed src/service/payment.py --goal "show implemented validation test cases"
```

Talking points:

- Navigator selects Review, QA, and Test Precision.
- It skips AIDLC for small bug plus tests.
- Test Precision gives plain-English test cases.
- Summarize inspects likely existing tests without running them.

### Demo 2: Complex Sonar And Vulnerability Before PR

Purpose:

- show enterprise routing
- show compact/commands-only views
- show scan approval
- show vulnerability evidence warning

Commands:

```bash
python3 scripts/tailtrail.py guide "fix Sonar quality gate failure and check vulnerability impact before PR" --changed src/main/java/PaymentValidator.java --view compact
python3 scripts/tailtrail.py guide "fix Sonar quality gate failure and check vulnerability impact before PR" --changed src/main/java/PaymentValidator.java --view commands-only
```

Talking points:

- Navigator selects CI/Sonar, security, vulnerability, review, QA, test precision, and handoff when needed.
- Scans are not run automatically.
- Vulnerability work is planning-only until exact evidence is provided.

### Demo 3: Repo Overview With Optional Graph

Purpose:

- show low-noise discovery mode
- show graph is optional

Commands:

```bash
python3 scripts/tailtrail.py guide "tell me important features of this repo" --root . --view compact
python3 scripts/tailtrail.py graph map --root .
```

Talking points:

- Repo overview starts with docs, manifests, top-level structure, entry points, tests, and configs.
- Code graph cache is created only when approved.

### Demo 4: Value Report

Purpose:

- show evidence posture
- explain estimated versus measured token savings

Commands:

```bash
python3 scripts/tailtrail.py report value --month 2026-07
python3 scripts/tailtrail.py report pr --only quality --only tokens
```

Talking points:

- Reports are local.
- Exact token savings require measured telemetry.
- Outcome telemetry is approved and compact.

## Evidence To Prepare Before Pitch

Minimum evidence:

- one Navigator compact plan
- one commands-only plan
- one Build Week Evaluation Harness scenario report
- one Test Precision plan
- one Test Coverage summary
- one value report
- one benchmark summary
- one public release check result

Recommended command set:

```bash
python3 scripts/tailtrail.py guide "fix payment validation bug and add unit tests" --changed src/service/payment.py --view compact
python3 scripts/tailtrail.py test plan --changed src/service/payment.py --goal "fix payment validation bug"
python3 scripts/tailtrail.py test summarize --changed src/service/payment.py --goal "show implemented validation test cases"
python3 scripts/tailtrail.py guide "fix Sonar quality gate failure and check vulnerability impact before PR" --changed src/main/java/PaymentValidator.java --view commands-only
python3 scripts/tailtrail.py eval scenario report --scenario buildweek-validation
python3 scripts/tailtrail.py eval scenario report --scenario buildweek-validation --format json
python3 scripts/tailtrail.py report value --month 2026-07
TAILTRAIL_ADMIN=1 python3 scripts/tailtrail.py release-check
```

## Claim Boundaries For Pitch

Say:

- local-first
- approval-first
- deterministic helper scripts
- evidence-aware
- advisory learning
- estimated token savings unless measured telemetry exists
- helps reduce avoidable workflow mistakes

Do not say:

- guaranteed savings
- replaces CI
- replaces tests
- replaces security review
- proves vulnerabilities are fixed
- self-heals agent behavior automatically
- enforces all organization policy automatically

## Pitch Build Plan

### Phase 1: Prepare Pitch Docs

Create:

- `PITCH-ONE-PAGER.md`
- `PITCH-DECK-OUTLINE.md`

Update:

- `DEMO.md` for Test Precision, compact view, commands-only view, and evidence warning

### Phase 2: Prepare Evidence Pack

Create:

- `pitch/evidence/navigator-simple.md`
- `pitch/evidence/navigator-complex.md`
- `pitch/evidence/buildweek-validation-scenario.md`
- `pitch/evidence/test-precision-plan.md`
- `pitch/evidence/test-coverage-summary.md`
- `pitch/evidence/value-report.md`
- `pitch/evidence/release-check.md`

### Phase 3: Prepare Demo Script

Add:

- exact commands
- expected outputs
- speaking notes
- fallback screenshots or saved output files

### Phase 4: Public/Internal Split

Review:

- public package includes public-safe pitch docs only
- internal package may include enterprise review and honest review
- public docs pass `scripts/public-doc-audit.py`
- release package passes `TAILTRAIL_ADMIN=1 python3 scripts/tailtrail.py release-check`

### Phase 5: Dry Run

Run:

```bash
python3 scripts/check-tailtrail.py
python3 scripts/public-doc-audit.py --root .
python3 scripts/tailtrail.py doctor
python3 scripts/smoke-test.py
TAILTRAIL_ADMIN=1 python3 scripts/tailtrail.py release-check
```

Then do one full demo rehearsal with a timer.

## Pitch Readiness Checklist

- One-page summary exists.
- Deck outline exists.
- Demo script includes simple and complex flows.
- Demo script includes the `buildweek-validation` Evaluation Harness proof command.
- Evidence pack contains sanitized outputs.
- Public claims are checked against `PUBLIC-CLAIMS.md`.
- Public docs pass audit.
- Release check passes.
- No private repo names or internal identifiers in public pitch material.
- Token savings are labeled estimated unless measured telemetry exists.
- Value claims cite local benchmark, outcome, or measured artifacts.
- Boundaries are stated clearly.

## Current Gaps

- No dedicated one-page pitch file yet.
- No pitch deck outline file yet.
- No curated `pitch/evidence/` folder yet.
- `DEMO.md` should be refreshed with newest Test Precision and Navigator view features outside the Build Week path.
- No visual diagram or slide asset yet.

## Recommended Next Step

Create `PITCH-ONE-PAGER.md` and `PITCH-DECK-OUTLINE.md`, then generate sanitized evidence files under `pitch/evidence/`, starting with `buildweek-validation-scenario.md` from `python3 scripts/tailtrail.py eval scenario report --scenario buildweek-validation`.
