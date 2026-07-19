# TailTrail Useful Prompts

This page is an end-user prompt cookbook. Use it when you want TailTrail to choose the workflow, generate a plan, run a focused helper, or report metrics without remembering every command.

Default rule:

```text
Use TailTrail start. Plan first, ask approval, implement after approval, then run report value.
Task: <your task>
```

Use command-backed prompts when your assistant can run local shell commands. Use plain prompts when the assistant is reading TailTrail docs or adapter instructions but you do not want it to run commands yet.

## Prompt Style

### Short Daily Prompt

```text
Use TailTrail start. Plan first, ask approval, implement after approval, then run report value.
Task: fix the failing payment validation test.
```

Use when: you want the full default flow.

What it should do:

- Run Navigator through `start`.
- Show selected and skipped TailTrail features.
- Ask before implementation.
- After the work is done, show value metrics with `report value`.

### Compact Plan Only

```text
Use TailTrail guide for this task:
fix the failing payment validation test.

Show the Navigator plan only. Do not implement until I approve.
```

Use when: you want routing and planning only.

### Command-Backed Prompt

```text
Run TailTrail start for this repo:
python3 /Users/vsingha7/Documents/tailtrail/scripts/tailtrail.py start "fix the failing payment validation test" --root .

Show the plan first. Do not implement until I approve.
```

Use when: the target repo does not have `scripts/tailtrail.py`, or you want to reference your TailTrail checkout directly.

## Start

### Basic Implementation Task

```text
Use TailTrail start. Plan first, ask approval, implement after approval, then run report value.
Task: add retry handling for payment capture.
```

Use when: normal feature or bug work.

Likely output:

```text
Start Here
- Review the Navigator plan.
- Approve, edit, or ask for a smaller plan.

Navigator Summary
- Workflow: graph -> review
- Selected: Token Autopilot, Code Review Graph Lite, Review Lens
- Skipped: AIDLC because no broad/risky lifecycle signal was detected
- Likely impacted files: unknown until source inspection

Approval
- Reply approve to inspect exact files and proceed.
```

### Known File

```text
Use TailTrail start. Plan first, ask approval, implement after approval, then run report value.
Task: fix null pointer in claim mapper.
Changed file: src/main/java/com/acme/claims/ClaimMapper.java
```

Use when: you know the likely file.

Command-backed version:

```text
Run:
python3 /Users/vsingha7/Documents/tailtrail/scripts/tailtrail.py start "fix null pointer in claim mapper" --root . --changed src/main/java/com/acme/claims/ClaimMapper.java

Show the plan only. Do not implement until I approve.
```

## Guide

### Plan Only

```text
Use TailTrail guide:
review the auth middleware change for security and validation risk.

Show only the Navigator plan. Do not edit files.
```

Use when: you want to see the workflow before committing to work.

### Repo Overview

```text
Use TailTrail guide:
tell me important features of this repo.

Show the plan first. Ask before deeper discovery or code graph generation.
```

Likely output:

```text
Goal
tell me important features of this repo

Mode
Repo Overview / Discovery

Plan
- Inspect README and top-level project structure.
- Identify language, framework, entry points, tests, and major modules.
- Summarize important repo features and how they fit together.
- Ask before running scans, tests, builds, or writing files.

Optional deeper discovery
- Run Code Graph Mapper only if approved.
```

## AIDLC

### Start AIDLC

```text
Use TailTrail AIDLC standard depth for this task.
Create or update lifecycle docs only after showing the plan.
Task: migrate payment retry behavior across services.
```

Use when: work is broad, risky, regulated, multi-step, or multi-team.

### AIDLC With Questions

```text
Use TailTrail AIDLC standard depth.
Before implementation, ask any required questions with your recommended answer and reasoning after each question.
Task: add a new settlement workflow.
```

Likely output:

```text
Questions
1. Which settlement states are in scope?
Recommended: limit V1 to pending, completed, failed.
Reasoning: keeps the first implementation testable and avoids release ambiguity.

2. Should this change require operations handoff?
Recommended: yes.
Reasoning: settlement workflows usually need monitoring and rollback notes.
```

### AIDLC Plus Review

```text
Use TailTrail AIDLC and Review.
Plan lifecycle docs first, then review the proposed change for dependency, validation, security, and scope risks.
Task: update claims ingestion workflow.
```

Use when: the task needs lifecycle discipline and review discipline.

## Review

### Review A Diff

```text
Use TailTrail Review on this diff.
Check for unnecessary dependencies, duplicate logic, broad rewrites, weakened safeguards, missing validation, and unclear handoff.
```

Use when: reviewing a patch before commit or PR.

### Review With Lenses

```text
Use TailTrail Review with architecture, security, QA, maintainability, and dependency lenses.
Focus on findings first. Keep the summary brief.
```

Likely output:

```text
Findings
- P1 Security: input validation is bypassed in the new endpoint.
- P2 QA: changed branch has no focused test.
- P2 Dependency: new package is introduced without Dependency Gate evidence.

Open Questions
- Was the new endpoint intended to be public?

Summary
- The diff is close, but validation and dependency evidence need tightening.
```

### Post-Implementation Review

```text
Use TailTrail Review after implementation.
Check the changed files, likely callers, likely tests, dependency changes, validation evidence, and handoff notes.
Do not claim tests passed unless they actually ran.
```

## Dependency Gate

### Before Adding A Package

```text
Use TailTrail Dependency Gate before recommending any new package.
Prefer standard library, platform-native features, framework capabilities, and already-installed dependencies.
Task: parse a CSV import file.
```

Likely output:

```text
Dependency Gate
- First choice: use existing standard library CSV parser.
- New dependency: not justified yet.
- Validation: add focused CSV parsing tests for quoting, empty values, and invalid rows.
```

### Dependency Gate Plus Review

```text
Use TailTrail Dependency Gate and Review.
The proposed change adds a new dependency. Decide if it is justified, then review the diff for ownership, security, and validation risk.
```

## Code Graph Mapper

### Generate Graph Without Code Changes

```text
Use TailTrail Code Graph Mapper for this repo.
Generate the graph cache only. Do not edit code.
After mapping, summarize entry points, major modules, tests, configs, endpoints, DB tables, and suggested read order.
```

Command-backed version:

```text
Run:
python3 /Users/vsingha7/Documents/tailtrail/scripts/tailtrail.py graph map --root .

Then summarize the generated `tailtrail-meta/code-graph-cache.json` at a high level. Do not edit code.
```

Likely output:

```text
Code Graph Mapper
- Cache: tailtrail-meta/code-graph-cache.json
- Languages detected: Java, SQL, Terraform
- Entry points: src/main/...
- Likely tests: src/test/...
- Suggested read order: manifests -> config -> entry points -> services -> tests

Note
- The graph is metadata only. Exact source files still need to be read before edits.
```

### Graph Plus Sonar

```text
Use TailTrail Code Graph Mapper and CI/Sonar Intelligence.
Map the repo, connect the Sonar finding to likely files/callers/tests, and ask before running any scan.
Finding: cognitive complexity in PaymentValidator.
```

## CI/Sonar

### Summarize Logs

```text
Use TailTrail CI/Sonar Intelligence.
Summarize this pasted CI or Sonar output. Keep exact failing rule IDs, file paths, line numbers, commands, and error messages.
Do not run scans unless I approve.
```

### Fix Sonar With Review

```text
Use TailTrail start. Plan first, ask approval, implement after approval, then run review and report value.
Task: fix the Sonar cognitive complexity issue in PaymentValidator.
Changed file: src/main/java/com/acme/payment/PaymentValidator.java
```

Likely output:

```text
Selected Features
- Code Review Graph Lite
- CI/Sonar Intelligence
- Review Lens
- Quality Signal Scanner, approval required before running checks

Plan
- Read the exact file and nearby tests.
- Identify the smallest extraction that preserves validation order.
- Run focused validation only after approval.
- Review for behavior preservation and validation truth.
```

## Security And Vulnerability

### Triage Vulnerability

```text
Use TailTrail Security And Vulnerability Intelligence.
Triage this vulnerability output. Return finding list, severity, affected component, current version, fixed version if present, evidence lines, and remediation options.
Do not implement a fix unless I ask.
```

### Vulnerability Fix With Dependency Gate

```text
Use TailTrail start with Security And Vulnerability Intelligence and Dependency Gate.
Plan first and ask approval.
Task: remediate GHSA finding in package.json without broad dependency churn.
Changed file: package.json
```

Likely output:

```text
Selected Features
- Security And Vulnerability Intelligence
- Dependency Gate
- Review Lens
- Quality Signal Scanner with scan approval

Plan
- Read package manifest and lockfile.
- Identify direct vs transitive dependency.
- Prefer minimal safe version bump.
- Ask before running npm audit or tests.
```

## Quality Scanner

### Recommend Checks

```text
Use TailTrail Quality Signal Scanner.
Inspect this repo's manifests and recommend local quality commands. Do not run them.
```

### Run One Approved Check

```text
Use TailTrail Quality Signal Scanner.
Recommend focused checks for this task. Ask me which one to run, then run only the exact approved command.
Task: update auth middleware validation.
```

## Test Precision Planner

### Plan Precise Tests After Development

```text
Use TailTrail Test Precision Planner after this implementation.
Show likely test files, recommended test cases in plain English, reusable fixtures/helpers, and focused validation commands.
Do not create tests or run commands until I approve.
Changed file: src/service/payment.py
Goal: fix payment validation bug.
```

Use when: code is done or nearly done and you want confidence before final validation or PR.

Command-backed version:

```text
Run:
python3 /Users/vsingha7/Documents/tailtrail/scripts/tailtrail.py test plan --root . --changed src/service/payment.py --goal "fix payment validation bug"

Show the Test Case Matrix first. Do not run tests yet.
```

Likely output:

```text
Test Case Matrix
- regression: capture the exact bug that should fail before the fix
- happy path: valid payment passes validation
- negative path: invalid payment is rejected safely
- boundary path: missing, null, empty, or max/min values are handled
- guard preservation: validation/security/data safeguards still block unsafe paths

Likely Test Files
- tests/service/test_payment.py

Focused Validation Commands
- pytest tests/service/test_payment.py
```

### Navigator Plus Test Precision

```text
Use TailTrail Navigator for this fix.
Plan first, ask approval, implement after approval, then run Review and Test Precision Planner before final validation.
Task: fix order validation edge case and add regression coverage.
Changed file: src/service/order.py
```

Use when: you want the default workflow plus a deliberate testing phase.

Likely output:

```text
Selected Features
- Code Review Graph Lite
- Review Lens
- QA / CI-Sonar Lens
- Test Precision Planner

Suggested Commands
- tailtrail graph --changed src/service/order.py
- tailtrail intent "use review"
- tailtrail test plan --root "/path/to/repo" --goal "..." --changed src/service/order.py
```

### Ask For Implemented Test Coverage Summary

```text
Use TailTrail Test Precision Planner.
First show recommended test cases in plain English.
Then inspect the likely existing test files and tell me which cases appear already covered and which are missing.
Do not edit files or run tests yet.
Changed file: src/service/validation.py
```

Command-backed version:

```text
Run:
python3 /Users/vsingha7/Documents/tailtrail/scripts/tailtrail.py test summarize --root . --changed src/service/validation.py --goal "show implemented validation test cases"

Show discovered test names, line numbers, assertion hints, recommended cases to confirm, and missing or uncertain coverage.
```

Boundary: `test summarize` is heuristic and read-only. It inspects likely existing test files, but it does not execute tests or prove coverage.

## Navigator E2E Scenario Testing

### Validate Navigator Routes

```text
Use TailTrail Navigator test scenarios.
Open NAVIGATOR-TEST-SCENARIOS.md and run the scenarios that match this change.
Report which selected features, skipped features, suggested commands, and approval prompts match expectations.
Do not implement fixes unless I ask.
```

Use when: changing Navigator, Test Precision Planner, graph routing, QA routing, security routing, or command rendering.

Command-backed version:

```text
Run these representative Navigator scenarios and compare with NAVIGATOR-TEST-SCENARIOS.md:
python3 /Users/vsingha7/Documents/tailtrail/scripts/tailtrail.py guide "fix typo in README" --root . --changed README.md
python3 /Users/vsingha7/Documents/tailtrail/scripts/tailtrail.py guide "fix payment validation bug and add unit tests" --root . --changed src/service/payment.py --view compact
python3 /Users/vsingha7/Documents/tailtrail/scripts/tailtrail.py guide "fix Sonar quality gate failure and check vulnerability impact before PR" --root . --changed src/main/java/PaymentValidator.java --view commands-only
python3 /Users/vsingha7/Documents/tailtrail/scripts/tailtrail.py guide "tell me important features of this repo" --root .
```

Likely output:

```text
Navigator Scenario Results
- Tiny docs: passed, workflow lean
- Unit tests: passed, Test Precision Planner selected
- Sonar/vulnerability: passed, scan approval default no
- Repo overview: passed, read-only mode with optional graph map

Discrepancies
- Small bug plus "add tests" may over-select AIDLC
- Some commands may still assume the target repo as current working directory
```

## Cross-Repo Reference

### Read-Only Reference Repo

```text
Use TailTrail Cross-Repo Reference Mode.
Target repo: /path/to/service-a
Reference repo: /path/to/service-b
Goal: match validation style.
Only edit the target repo. Do not copy source code from the reference repo.
```

Likely output:

```text
Reference Boundary
- Editable target: /path/to/service-a
- Read-only reference: /path/to/service-b

Plan
- Read target policy and target implementation first.
- Read reference only for naming, validation shape, test style, and config conventions.
- Do not copy source code.
```

### Cross-Repo Plus Graph

```text
Use TailTrail Cross-Repo Reference Mode and Code Graph Mapper.
Create or reuse a compact graph for the reference repo if useful.
Target repo: /path/to/service-a
Reference repo: /path/to/service-b
Goal: understand retry pattern before implementing in target.
Ask before generating any graph cache.
```

## Learning

### Search Learnings

```text
Use TailTrail Learning Agent.
Search for advisory learnings related to Sonar, Java, and validation in this repo.
Show confidence score and do not apply any learning automatically.
```

### Capture Learning After Accepted Work

```text
Use TailTrail Learning Agent after this accepted task.
Ask me before recording. If approved, capture a compact reusable learning with confidence score, tags, validation outcome, and files affected.
Do not record raw prompts, raw logs, secrets, PII, PHI, or source snippets.
```

### Learning Plus Graph

```text
Use TailTrail Graph-Aware Learning.
Find learnings connected to this file and related symbols, but treat them as advisory only.
Changed file: src/main/java/com/acme/payment/PaymentValidator.java
```

## Metrics And Reports

### Value Metrics After Work

```text
Use TailTrail report value after this task.
Show local evidence only. Do not claim exact ROI or exact token savings unless measured telemetry exists.
```

Command-backed version:

```text
Run:
python3 /Users/vsingha7/Documents/tailtrail/scripts/tailtrail.py report value --root . --month 2026-07

Summarize evidence confidence, governance outcomes, adoption outcomes, learning hygiene, and token evidence.
```

### Token Savings Estimate

```text
Use TailTrail token savings estimate.
Used context: README.md, context/code-graph-mapper.md, tailtrail-meta/code-graph-cache.json
Avoided context: ROADMAP.md, USER-GUIDE.md, HONEST-REVIEW.md
Label this as estimated, not exact.
```

### Measured Token Report

```text
Use TailTrail measured token report from `.tailtrail/token-usage.jsonl`.
Show baseline tokens, TailTrail tokens, saved tokens, and reduction percentage.
If telemetry is missing, say exact token savings are unavailable.
```

### Monthly CSV Export

```text
Use TailTrail to generate this month's value report as CSV.
Run:
python3 /Users/vsingha7/Documents/tailtrail/scripts/tailtrail.py report value --root . --month 2026-07 --format csv --write-result
```

### Compare Two Months

```text
Use TailTrail value comparison.
Compare last month's value report JSON with this month's value report JSON.
Show only local evidence deltas and do not make ROI claims.
```

Command-backed version:

```text
Run:
python3 /Users/vsingha7/Documents/tailtrail/scripts/tailtrail.py report compare --previous-report .tailtrail/value-report-2026-06.json --current-report .tailtrail/value-report-2026-07.json
```

## Handoff

### Prepare Handoff

```text
Use TailTrail Handoff.
Prepare a compact handoff for this change with files changed, behavior changed, validation run, validation not run, risks, rollback notes, and reviewer focus.
Do not claim checks passed unless they actually ran.
```

### AIDLC Plus Handoff

```text
Use TailTrail AIDLC and Handoff.
Update lifecycle state and prepare handoff notes for reviewer and future continuation.
Task: payment retry rollout.
```

## Guardrails

### Check Before Commit

```text
Use TailTrail Guardrails.
Check staged changes for dependency gate misses, validation claims without evidence, weakened safeguards, local state files, and unsupported public claims.
Do not modify files.
```

Command-backed version:

```text
Run:
python3 /Users/vsingha7/Documents/tailtrail/scripts/tailtrail.py guard check --root .
```

### Strict Review

```text
Use TailTrail strict mode and Review.
Challenge scope, dependencies, validation claims, and removed safeguards.
Prefer smaller changes and exact evidence.
```

## Governance And Policy

### Local Policy

```text
Use TailTrail local policy.
Read `tailtrail-policy.md` if present. If only `tailtrail-policy.example.md` exists, treat it as a template, not active policy.
Apply repo-specific validation commands, dependency rules, ownership, and restricted folders.
```

### Governance Sync

```text
Use TailTrail governance check.
Verify repeated governance text is in sync before committing TailTrail docs or adapter changes.
```

Command-backed version:

```text
Run:
python3 /Users/vsingha7/Documents/tailtrail/scripts/tailtrail.py governance check
```

## Feature Combinations

### Normal Bug Fix

```text
Use TailTrail start. Plan first, ask approval, implement after approval, run review, then run report value.
Task: fix the null pointer in claim mapper.
Changed file: src/main/java/com/acme/claims/ClaimMapper.java
```

### Sonar Fix With Metrics

```text
Use TailTrail start with CI/Sonar Intelligence, Code Graph Mapper, Review, and report value.
Plan first. Ask before graph generation, scans, tests, or implementation.
Task: fix Sonar cognitive complexity in PaymentValidator.
Changed file: src/main/java/com/acme/payment/PaymentValidator.java
```

Likely output:

```text
Start Here
- Approve Navigator plan before implementation.
- Optional: approve Code Graph Mapper if repeated source discovery is likely.
- Optional: approve focused quality command after code change.

Selected Features
- CI/Sonar Intelligence
- Code Review Graph Lite
- Review Lens
- Quality Signal Scanner
- Value Report after work

Approval Questions
- Generate graph cache? recommended if this file has many callers.
- Run focused validation? recommended after implementation.
- Capture learning? only after user accepts the solution.
```

### Vulnerability Fix With Handoff

```text
Use TailTrail start with Security And Vulnerability Intelligence, Dependency Gate, Review, Handoff, and report value.
Plan first and ask approval before scans or dependency updates.
Task: remediate GHSA finding in package.json and prepare PR handoff.
```

### Cross-Repo Pattern Implementation

```text
Use TailTrail Cross-Repo Reference Mode, Code Graph Mapper, Dependency Gate, and Review.
Target repo: /path/to/current-service
Reference repo: /path/to/reference-service
Goal: implement the same error response style without copying code.
Plan first, ask approval, then only edit the target repo.
```

### Large Regulated Change

```text
Use TailTrail AIDLC comprehensive depth with Security Review, QA Review, Dependency Gate, Handoff, and report value.
Ask required questions with recommended answers and reasoning.
Task: add a new regulated settlement workflow.
```

Likely output:

```text
Selected Features
- AIDLC comprehensive
- Security Review
- QA Review
- Dependency Gate
- Handoff
- Value Report after work

Required Docs
- aidlc-docs/aidlc-state.md
- aidlc-docs/requirements.md
- aidlc-docs/workflow-plan.md
- aidlc-docs/validation-handoff.md

Approval
- Approve requirements before implementation.
- Approve scanner/test commands before running them.
```

### Repo Discovery With Optional Graph

```text
Use TailTrail start.
Task: tell me important features of this repo.
Show the plan first. If deeper discovery is useful, recommend Code Graph Mapper and ask before generating it.
After overview is complete, run report value.
```

Likely output:

```text
Mode
Repo Overview / Discovery

Plan
- Inspect README and manifests.
- Identify entry points, tests, configs, and major modules.
- Avoid implementation features.
- Recommend graph map only if overview needs deeper module/symbol discovery.

After Completion
- Run report value for local evidence.
```

## What To Avoid

Avoid vague prompts:

```text
Use TailTrail.
```

Better:

```text
Use TailTrail start. Plan first, ask approval, implement after approval, then run report value.
Task: fix the Sonar issue in PaymentValidator.
Changed file: src/main/java/com/acme/payment/PaymentValidator.java
```

Avoid asking for exact savings without telemetry:

```text
Tell me exactly how many tokens TailTrail saved.
```

Better:

```text
Show TailTrail token evidence. Use measured token telemetry only if available; otherwise label the result as estimated or unavailable.
```
