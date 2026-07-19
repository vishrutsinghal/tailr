# TailTrail Demo Script

This script is written for a short live demo. Each step includes the prompt, expected TailTrail path, and presenter note.

## Step 1: Installation Check

Prompt:

```text
hello tailtrail
```

Command:

```bash
python3 scripts/tailtrail.py hello
```

Expected:

- TailTrail confirms it is reachable.
- No repo files are changed.

Presenter note:

Use this to show that TailTrail has a low-friction health check before any workflow starts.

## Step 2: Repo Overview Plan

Prompt:

```text
Run TailTrail Navigator for: tell me important features of this repo. Show the plan only.
```

Command:

```bash
python3 scripts/tailtrail.py guide "tell me important features of this repo" --root demo-project-layout/tailtrail-demo-workspace
```

Expected:

- Navigator selects Repo Overview / Discovery.
- Code Graph Mapper appears as optional deeper discovery.
- No files are edited.
- No graph cache is created unless the presenter approves the graph command.

Presenter note:

This shows that TailTrail does not make every prompt heavy. A read-only question gets a read-only plan.

## Step 3: Generate Graph Context

Prompt:

```text
Approve deeper discovery. Generate the TailTrail code graph for this demo workspace, then summarize the read order.
```

Command:

```bash
python3 scripts/tailtrail.py graph map --root demo-project-layout/tailtrail-demo-workspace --changed services/claims-api/src/claims_api/validation.py --changed services/claims-api/tests/test_validation.py
```

Expected:

- `tailtrail-meta/code-graph-cache.json` is created inside the demo workspace.
- The graph gives compact metadata and suggested read order.
- The agent still reads exact source before editing.

Presenter note:

This is the token-saving story: graph metadata helps avoid rediscovering the same project shape in later prompts.

## Step 4: Bug-Fix Plan

Prompt:

```text
Use TailTrail Navigator to fix claim amount validation and add focused tests. Show the plan before implementation.
```

Command:

```bash
python3 scripts/tailtrail.py guide "fix claim amount validation and add focused tests" --root demo-project-layout/tailtrail-demo-workspace --changed services/claims-api/src/claims_api/validation.py --changed services/claims-api/tests/test_validation.py --view compact
```

Expected:

- Navigator selects Code Review Graph Lite.
- Navigator selects Code Graph Mapper.
- Navigator selects Review Lens.
- Navigator selects Test Precision Planner.
- Navigator includes Learning Capture Trigger as a post-task step.
- AIDLC is skipped because this is a small bug fix.

Presenter note:

The important point is not that TailTrail fixes the bug automatically. It picks the right route and asks for approval.

## Step 5: Test Precision Planner

Prompt:

```text
Use TailTrail Test Precision Planner for the claim amount validation fix. Show recommended test cases in plain English and the focused validation command.
```

Command:

```bash
python3 scripts/tailtrail.py test plan --root demo-project-layout/tailtrail-demo-workspace --goal "fix claim amount validation" --changed services/claims-api/src/claims_api/validation.py --changed services/claims-api/tests/test_validation.py
```

Expected:

- likely test file: `services/claims-api/tests/test_validation.py`
- regression case: zero amount should be rejected
- boundary case: minimum positive amount should pass
- negative case: missing member id or unsupported claim type should fail
- validation command: `python3 services/claims-api/tests/test_validation.py`

Presenter note:

This demonstrates that TailTrail can express tests in normal language before code changes.

## Step 6: Review And Handoff

Prompt:

```text
Use TailTrail review and handoff for the claim validation change. Prepare reviewer notes, risk notes, and validation summary. Do not claim tests passed unless evidence exists.
```

Expected:

- review lens checks safeguards and scope
- handoff summarizes changed behavior, tests, and risks
- validation evidence is explicit

Presenter note:

This is the enterprise delivery story: review quality and handoff clarity without bloated process.

## Step 7: Learning Capture After Acceptance

Prompt:

```text
The claim validation fix was accepted and focused tests passed. Show the approved learning capture command, but do not run it yet.
```

Expected:

- TailTrail shows a learning capture command.
- The command includes a reusable pattern and validation outcome.
- Nothing is recorded unless the user approves and runs it.

Presenter note:

This shows guarded learning. TailTrail does not blindly learn from every interaction.

## Step 8: Value Report

Prompt:

```text
Generate a local TailTrail value report for this demo task using available local evidence only.
```

Expected:

- report is local and advisory
- token savings are directional unless measured telemetry exists
- no raw prompts or private data are uploaded

Presenter note:

This closes the loop with measurable value without overstating exact ROI.
