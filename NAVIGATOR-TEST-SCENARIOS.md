# TailTrail Navigator Test Scenarios

This file is a practical scenario catalog for validating TailTrail Navigator behavior from simple tasks to complex enterprise flows.

Use it when changing Navigator, Test Precision Planner, Code Graph Mapper, QA routing, security routing, or command rendering. The examples below are written from the end-user perspective and include the expected plan shape plus discrepancies to watch.

## How To Run A Scenario

From the TailTrail repo:

```bash
python3 scripts/tailtrail.py guide "PROMPT_TEXT" --changed path/to/file
```

When TailTrail is installed outside the target repo:

```bash
python3 /Users/vsingha7/Documents/tailtrail/scripts/tailtrail.py guide "PROMPT_TEXT" --root /path/to/project --changed path/to/file
```

For JSON assertions:

```bash
python3 scripts/tailtrail.py guide "PROMPT_TEXT" --changed path/to/file --format json
```

Navigator is advisory. It should plan, show selected/skipped features, show suggested commands, and ask for approval. It should not edit files, run tests, run scanners, record learnings, or create graph cache files unless the user approves a follow-up command.

## Scenario 1: Tiny Documentation Fix

Prompt:

```text
fix typo in README
```

Command:

```bash
python3 scripts/tailtrail.py guide "fix typo in README" --changed README.md
```

Expected plan:

- Workflow: `lean`
- Selected:
  - Token Autopilot
  - TailTrail Lean
- Skipped:
  - Code Review Graph Lite
  - Code Graph Mapper
  - AIDLC
  - Review Lens
  - Test Precision Planner
  - Quality Signal Scanner
- Suggested commands:
  - none before implementation
- Implementation plan:
  - confirm the task is tiny
  - read exact target file only
  - make smallest edit
  - run or name the smallest relevant check only if behavior changed

Good behavior:

- Navigator should not recommend AIDLC, graph mapping, QA, scanners, or testing for a typo-only task.
- Navigator should not ask for scan approval.

## Scenario 2: Read-Only Repo Overview

Prompt:

```text
tell me important features of this repo
```

Command:

```bash
python3 scripts/tailtrail.py guide "tell me important features of this repo" --root .
```

Expected plan:

- Mode: Repo Overview / Discovery
- Selected:
  - Repo Overview
  - Token Autopilot
- Optional deeper discovery:
  - Code Graph Mapper
  - Default: not run
  - Creates `tailtrail-meta/code-graph-cache.json` only if the user later approves and runs `graph map`
- Avoid:
  - editing files
  - scanners
  - tests/builds
  - AIDLC/review/handoff unless the user asks for change work

Good behavior:

- Navigator should answer with a plan only.
- It should not generate code graph cache automatically.
- It should not run scanner/test/build commands.

Useful follow-up prompt:

```text
Approve the repo overview. Keep it compact. Do not run graph map yet.
```

Useful deeper-discovery prompt:

```text
Approve deeper discovery. Run the suggested Code Graph Mapper command, then summarize modules, tests, configs, endpoints, and read order.
```

## Scenario 3: Small Bug Fix With Unit Tests

Prompt:

```text
fix payment validation bug and add unit tests
```

Command:

```bash
python3 scripts/tailtrail.py guide "fix payment validation bug and add unit tests" --changed src/service/payment.py
```

Expected plan:

- Task types: `bug`, `qa`
- Workflow should include:
  - review
  - qa_review
  - test_precision
- Workflow should not include:
  - aidlc
- Selected:
  - Code Review Graph Lite
  - Code Graph Mapper
  - Learning Capture Trigger
  - Review Lens
  - QA / CI-Sonar Lens
  - Test Precision Planner
- Suggested command should include:

```bash
python3 scripts/tailtrail.py graph map --root "/path/to/repo" --changed src/service/payment.py
python3 scripts/tailtrail.py test plan --root "/path/to/repo" --goal "fix payment validation bug and add unit tests" --changed src/service/payment.py
```

Expected Test Precision Planner behavior:

- Shows likely test files.
- Shows test cases in normal English:
  - regression
  - happy path
  - negative path
  - boundary path
  - guard preservation when validation/security/data risks exist
- Shows focused validation commands.
- Does not create tests or run tests.

Good behavior:

- Navigator should show Test Precision Planner in Selected Features.
- Navigator should show Code Graph Mapper before broad source reads, but should not create or refresh `tailtrail-meta/code-graph-cache.json` until the user approves the graph command.
- Navigator should show a post-task Learning Capture Trigger, but should not write learning files until the user approves capture after acceptance, feedback, or validation evidence.
- The implementation plan should say to use Test Precision Planner before running commands.
- Review should remain selected because bug fixes need behavior/safeguard review.

Discrepancy to watch:

- Fixed behavior: `add unit tests` is treated as QA, not as a product feature by itself. A small bug fix plus test addition should skip AIDLC unless the prompt also mentions release, regulated, multi-team, schema, migration, production, broad scope, or an explicit feature/implementation request.

## Scenario 4: Test-Only Planning After Development

Prompt:

```text
after development, plan precise regression tests for the validator change before PR
```

Command:

```bash
python3 scripts/tailtrail.py guide "after development, plan precise regression tests for the validator change before PR" --changed src/main/java/com/acme/Validator.java
```

Expected plan:

- Selected:
  - Test Precision Planner
  - Review Lens
  - QA / CI-Sonar Lens
  - Handoff if `PR` is interpreted as reviewer/release prep
- Suggested commands should include:
  - `test plan --root ... --goal ... --changed src/main/java/com/acme/Validator.java`
- Implementation plan should focus on:
  - inspect current source and likely tests
  - use Test Precision Planner
  - run or name focused validation only after approval

End-user approval prompt:

```text
Approve Test Precision Planner only. Show likely test files, recommended test cases in plain English, and focused validation command. Do not run tests yet.
```

Good behavior:

- This is the cleanest way for users to trigger the testing phase for confidence after code is done.
- Navigator should not run the tests itself.

## Scenario 5: Sonar Quality Gate Plus Vulnerability Before PR

Prompt:

```text
fix Sonar quality gate failure and check vulnerability impact before PR
```

Command:

```bash
python3 scripts/tailtrail.py guide "fix Sonar quality gate failure and check vulnerability impact before PR" --changed src/main/java/PaymentValidator.java
```

Expected plan:

- Task types:
  - bug
  - review
  - ci-sonar
  - security
- Risk indicators:
  - ci/sonar
  - vulnerability scan
- Workflow should include:
  - review
  - security_review
  - ci_sonar_intelligence
  - qa_review
  - test_precision
  - vulnerability_review
  - quality_scan_approval
  - handoff
- Selected:
  - Code Review Graph Lite
  - Code Graph Mapper
  - Review Lens
  - Security Review
  - CI/Sonar Intelligence
  - QA / CI-Sonar Lens
  - Test Precision Planner
  - Security And Vulnerability Intelligence
  - Quality Signal Scanner
  - Handoff
- Scan Approval:
  - default should be `no`
  - user must approve one exact command

Good behavior:

- Navigator should separate general Sonar/quality work from vulnerability work.
- It should preserve exact scanner evidence requirements.
- It should not silently run `sonar-scanner`, vulnerability scans, tests, audits, or broad builds.

Discrepancy to watch:

- If the prompt says only `check vulnerability impact` without a specific scanner file, Navigator may recommend `vulnerability scan --root .`. That is okay as planning, but remediation still needs exact vulnerability evidence before claiming a fix.
- Scan Approval may show only commands detected from the current root. In a target repo with `pom.xml`, `package.json`, `pyproject.toml`, `.sln`, or `go.mod`, more candidate commands should appear.

## Scenario 6: Dependency Upgrade

Prompt:

```text
upgrade the HTTP client dependency safely and update tests
```

Command:

```bash
python3 scripts/tailtrail.py guide "upgrade the HTTP client dependency safely and update tests" --changed package.json
```

Expected plan:

- Selected:
  - Dependency Gate
  - Review Lens
  - Test Precision Planner
  - Code Review Graph Lite
- May select:
  - Quality Signal Scanner if prompt asks for audit/scan/check before PR
  - Security Review if CVE/security terms are present
- Suggested commands should include:
  - `intent "use dependency gate"`
  - `test plan --root ... --changed package.json`

Good behavior:

- Navigator should require dependency justification.
- It should prefer existing dependencies/platform capabilities unless the upgrade is explicitly required.
- Test Precision Planner should suggest validation around impacted behavior, not only manifest parsing.

## Scenario 7: Cross-Repo Reference

Prompt:

```text
Use TailTrail cross-repo reference. Target: /tmp/service-a Reference: /tmp/service-b Goal: match validation style without copying code
```

Command:

```bash
python3 scripts/tailtrail.py guide "Use TailTrail cross-repo reference. Target: /tmp/service-a Reference: /tmp/service-b Goal: match validation style without copying code"
```

Expected plan:

- Selected:
  - Cross-Repo Reference Mode
  - Token Autopilot
  - likely Review Lens if implementation/review terms appear
- Suggested command:
  - `reference --target "/tmp/service-a" --reference "/tmp/service-b" --goal "..."`
- Boundaries:
  - target repo is editable
  - reference repo is read-only
  - do not copy source code verbatim

Good behavior:

- Navigator should protect the edit boundary.
- It should recommend compact summaries or graph metadata for the reference repo.

## Scenario 8: Complex Regulated Feature

Prompt:

```text
implement a new claims approval endpoint for regulated workflow, update DB schema, add tests, prepare handoff, and check quality gate before release
```

Command:

```bash
python3 scripts/tailtrail.py guide "implement a new claims approval endpoint for regulated workflow, update DB schema, add tests, prepare handoff, and check quality gate before release" --changed src/main/java/com/acme/claims/ClaimApprovalController.java --changed db/migrations/V12__claim_approval.sql
```

Expected plan:

- Selected:
  - AIDLC
  - Code Review Graph Lite
  - Code Graph Mapper
  - Review Lens
  - QA / CI-Sonar Lens
  - Test Precision Planner
  - Quality Signal Scanner
  - Handoff
- May select:
  - Security Review if auth/permission/trust-boundary terms are included
  - CI/Sonar Intelligence if exact CI/Sonar output is provided
- Scan Approval:
  - should ask before quality gate, broad tests, Sonar, or build commands
- Implementation plan:
  - lifecycle planning first
  - inspect changed files and graph-suggested callers/tests
  - apply smallest maintainable change
  - use Test Precision Planner for exact test plan
  - run approved validation only after approval
  - prepare handoff

Good behavior:

- This is where AIDLC is appropriate.
- Graph/cache and Test Precision Planner both make sense because the task is broad and multi-step.

## Scenario 9: Learning Refresh Concern

Prompt:

```text
the last suggestion was wrong; refresh learnings before using old patterns for this parser bug
```

Command:

```bash
python3 scripts/tailtrail.py guide "the last suggestion was wrong; refresh learnings before using old patterns for this parser bug" --changed src/parser.py
```

Expected plan:

- Selected:
  - Review Lens
  - Learning Refresh Awareness
  - Code Review Graph Lite
- Graph-Aware Learning:
  - skipped if no index exists
- Suggested command:
  - `learn refresh recommend --root ...`
- Learning rule:
  - learnings are advisory only
  - current source/tests/scanners/policy/guardrails/user instructions win

Good behavior:

- Navigator should not use weak or stale learnings silently.
- It should suggest refresh review without editing learning files automatically.

## Scenario 10: End-To-End Testing Confidence

Prompt:

```text
use TailTrail Navigator for this fix, then after implementation run review and Test Precision Planner before final validation
```

Command:

```bash
python3 scripts/tailtrail.py guide "use TailTrail Navigator for this fix, then after implementation run review and Test Precision Planner before final validation" --changed src/service/order.py
```

Expected plan:

- Selected:
  - Review Lens
  - QA / CI-Sonar Lens
  - Test Precision Planner
  - Code Review Graph Lite
- Suggested commands:
  - `graph --changed src/service/order.py`
  - `intent "use review"`
  - `route ci-sonar`
  - `test plan --root ... --changed src/service/order.py`
- Approval:
  - user should approve the plan first
  - user should separately approve any actual test command execution

Good behavior:

- This is the recommended prompt when users want confidence after dev.
- It gives review plus plain-English test cases before final validation.

## Scenario 11: Ask For Actual Test Cases In Plain English

Prompt:

```text
show me the test cases in plain English for the changed validation logic
```

Command:

```bash
python3 scripts/tailtrail.py test plan --root . --changed src/service/validation.py --goal "show me the test cases in plain English for the changed validation logic"
```

Expected output:

- `Test Case Matrix` section with normal-language cases:
  - regression
  - happy path
  - negative path
  - boundary path
  - guard preservation when validation/security/data risks exist
- `Likely Test Files`
- `Existing Helpers To Reuse`
- `Focused Validation Commands`

Important boundary:

- This shows recommended test cases, not a guaranteed inventory of tests already implemented.
- It can say whether likely test files exist.
- It does not currently parse every existing test body and summarize implemented assertions.

Future enhancement:

- Implemented: use `tailtrail test summarize --changed ...` to inspect likely existing test files and summarize recognizable test functions or blocks in plain English. It remains heuristic and read-only; it does not execute tests or prove coverage.

## Implemented Tuning Results And Remaining Candidates

These items started as discrepancies or tuning candidates. The concrete items are now implemented; any remaining notes are future polish candidates.

### 1. Small Bug Plus "Add Tests" Should Not Select AIDLC

Fixed behavior:

- Prompt: `fix payment validation bug and add unit tests`
- Navigator classifies this as `bug`, `qa`.
- Navigator selects Review, QA, and Test Precision Planner.
- Navigator skips AIDLC unless broader lifecycle signals exist.

Why this matters:

- `add` is a broad word, but `add unit tests` is validation work, not product-feature work.
- Keeping this lean avoids making routine bug fixes feel too heavy.

Regression check:

- `tests/test_navigator_core.py` checks that `fix payment validation bug and add unit tests` does not include `feature`, does not select AIDLC, and does include Test Precision Planner.

### 2. Test Precision Planner Can Summarize Likely Existing Coverage

Implemented behavior:

- `test plan` shows recommended cases in English and likely test files.
- `test summarize` inspects likely existing test files and reports recognizable test functions or blocks with line numbers and assertion hints.
- It still does not execute tests or prove coverage.

Why it matters:

- Users may ask, "what test cases are implemented?" That is different from "what test cases should we add?"

Usage:

```bash
python3 scripts/tailtrail.py test summarize --root . --changed src/service/validation.py --goal "show implemented validation test cases"
```

### 3. Suggested Commands Use Explicit Root When Supported

Implemented behavior:

- Navigator now renders `test plan --root "/path/to/repo"` for Test Precision Planner.
- Navigator graph, graph map/refresh, AIDLC init, vulnerability scan, learning refresh/search, and test planner commands include explicit `--root "/target/repo"` when supported.

Why it matters:

- Users often run TailTrail from `/Users/vsingha7/Documents/tailtrail` against another repo using `--root /path/to/project`.

Why it matters:

- Users often run TailTrail from `/Users/vsingha7/Documents/tailtrail` against another repo using `--root /path/to/project`.
- Explicit roots make suggested commands easier to copy and safer across sibling repos.

### 4. Complex Prompts Can Use Compact Or Commands-Only Views

Observed behavior:

- A prompt with Sonar, vulnerability, PR, and tests can select Review, Security Review, CI/Sonar, QA, Test Precision, Vulnerability, Quality Scanner, Handoff, and graph features.

Why it matters:

- This is accurate for enterprise work, but it can feel overwhelming.

Implemented improvement:

- `--view compact`: shows workflow, selected features, commands, approval/evidence warnings, and next steps.
- `--view commands-only`: shows only suggested commands plus approval/evidence warnings.

Example:

```bash
python3 scripts/tailtrail.py guide "fix Sonar quality gate failure and check vulnerability impact before PR" --changed src/main/java/PaymentValidator.java --view compact
python3 scripts/tailtrail.py guide "fix Sonar quality gate failure and check vulnerability impact before PR" --changed src/main/java/PaymentValidator.java --view commands-only
```

Future candidate:

- Group selected features by phase: Discover, Plan, Implement, Validate, Handoff.

### 5. Vulnerability Planning Shows Exact Evidence Warning

Implemented behavior:

- Navigator can recommend vulnerability planning from vulnerability words alone.
- When vulnerability terms appear without scanner evidence, Navigator adds a warning that routing is planning-only until exact evidence is provided.

Evidence examples:

- CVE/GHSA ID
- SARIF, Trivy, Grype, or audit output file
- affected package plus installed and fixed versions

## Manual Acceptance Checklist

Use this checklist before changing Navigator behavior:

- Tiny docs prompt stays lean.
- Repo overview stays read-only and does not create graph cache.
- Unit-test prompt selects Test Precision Planner.
- Test Precision Planner suggested command includes `--root`, `--goal`, and `--changed`.
- Meaningful code-change prompts select Code Graph Mapper unless they are tiny typo/docs-only tasks.
- Meaningful code-change prompts show Learning Capture Trigger as a post-task approval step.
- Complex Sonar/vulnerability prompt asks scan approval with default `no`.
- Cross-repo prompt shows read-only reference boundary.
- Learning refresh prompt suggests refresh review without editing learning files.
- Navigator does not run tests, scanners, builds, graph map, or learning capture automatically.
- Navigator tells the user they can approve or edit the plan.
