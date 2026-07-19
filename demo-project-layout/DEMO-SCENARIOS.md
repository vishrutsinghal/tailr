# TailTrail Demo Scenarios

These scenarios describe what the future demo project should prove.

## Scenario 1: Hello And Install Check

Prompt:

```text
hello tailtrail
```

Expected:

- TailTrail confirms it is installed.
- No source files are read.
- No TailTrail state is written.

Feature shown:

- installation success check

## Scenario 2: Repo Overview

Prompt:

```text
Run TailTrail Navigator for: tell me important features of this repo. Show the plan only.
```

Expected:

- Navigator selects Repo Overview / Discovery.
- Code Graph Mapper appears only as optional deeper discovery.
- No `tailtrail-meta/code-graph-cache.json` is created until approved.

Feature shown:

- low-noise Navigator planning

## Scenario 3: Generate Code Graph Without Code Changes

Prompt:

```text
Use TailTrail deeper discovery. Generate the code graph for this repo, then summarize modules, endpoints, tests, configs, SQL tables, and suggested read order.
```

Expected:

- Code Graph Mapper creates or refreshes `tailtrail-meta/code-graph-cache.json`.
- The summary is compact and source-snippet-free.
- Navigator or the user can reuse it in later prompts.

Feature shown:

- token-saving graph cache
- read-order guidance

## Scenario 4: Small Bug Fix With Tests

Prompt:

```text
Use TailTrail Navigator to fix claim amount validation and add focused unit tests. Show the plan before implementation.
```

Expected:

- Navigator selects Review Lens, Code Graph Mapper, Test Precision Planner, and Learning Capture Trigger.
- AIDLC is skipped unless broader lifecycle language is present.
- Suggested commands include graph map or refresh and test plan.
- Learning capture is post-task and approval-first.

Feature shown:

- right-sized workflow
- unit-test precision
- approval-first learning

## Scenario 5: Dependency Decision

Prompt:

```text
Use TailTrail to decide whether we should add a new date parsing package for claim service validation.
```

Expected:

- Dependency Gate is selected.
- TailTrail recommends standard library or existing framework capabilities first if sufficient.
- New dependency requires explicit justification.

Feature shown:

- dependency minimization
- enterprise guardrails

## Scenario 6: CI/Sonar Issue

Prompt:

```text
Use TailTrail Navigator to triage this Sonar quality-gate failure from ci/logs/sonar-quality-gate.log. Show the plan and ask before running anything.
```

Expected:

- CI/Sonar Intelligence is selected.
- Quality Signal Scanner may be selected.
- Scan approval defaults to no.
- TailTrail summarizes evidence from local logs only.

Feature shown:

- scanner evidence handling
- no hidden CI polling

## Scenario 7: Vulnerability Evidence

Prompt:

```text
Use TailTrail to summarize vulnerabilities from ci/scanner-results/trivy.json and identify likely impacted service files.
```

Expected:

- Security And Vulnerability Intelligence is selected.
- Trivy/Grype structured parser is used when applicable.
- Code Graph Mapper links findings to impacted manifests or services.
- Remediation is not claimed without exact version/evidence.

Feature shown:

- vulnerability parsing
- graph overlay
- public claim guardrails

## Scenario 8: AIDLC Feature Delivery

Prompt:

```text
Use AIDLC standard depth for a new claim override workflow. Ask recommended questions with reasoning before implementation.
```

Expected:

- AIDLC artifacts are created under `docs/aidlc/` or `aidlc-docs/`.
- Questions include recommended answers and reasoning.
- Implementation waits until lifecycle state is clear.

Feature shown:

- lifecycle planning
- regulated-change discipline

## Scenario 9: Handoff And Review

Prompt:

```text
Use TailTrail review and handoff for the validation change. Prepare reviewer notes, risk notes, and validation summary.
```

Expected:

- Review lenses are selected.
- Handoff summarizes changed behavior, tests, risks, and skipped items.
- No claims are made about tests unless evidence exists.

Feature shown:

- PR readiness
- review quality

## Scenario 10: Learning And Value Report

Prompt:

```text
After this accepted fix, show the suggested learning capture command and generate a local value report.
```

Expected:

- Learning capture command is shown with placeholders for reusable pattern and validation outcome.
- No learning is recorded unless approved.
- Value report shows directional or measured token usage depending on available telemetry.

Feature shown:

- guarded learning
- value reporting
