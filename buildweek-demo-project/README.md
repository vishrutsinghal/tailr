# TailTrail Build Week Demo Project

This is a clean, standalone demo target for showing TailTrail in a competition or product pitch.

It is intentionally small. The goal is to demonstrate how TailTrail helps Codex work on a real repo without overwhelming judges with TailTrail's full source tree.

## Build Week Judge Guide

### Installation and supported platforms

TailTrail is a local Python tool with no third-party runtime dependencies. Run this
demo from a TailTrail source checkout with Python 3.9 or later.

```bash
python3 scripts/tailtrail.py doctor
```

The portable command path is intended for macOS and Linux. On Windows, use the
Python command available on the machine (commonly `py` or `python`) in place of
`python3`.

No package installation or external service is required for the demo path below.

### Install TailTrail guidance for Codex

1. From the TailTrail repo root, validate the source checkout:

```bash
python3 scripts/tailtrail.py doctor
```

2. Preview the Codex guidance install plan for the demo project:

```bash
python3 scripts/tailtrail.py install codex --target buildweek-demo-project --dry-run
```

3. Install TailTrail's portable Codex project guidance into the demo project:

```bash
python3 scripts/tailtrail.py install codex --target buildweek-demo-project
```

4. If you want native Codex plugin source and skills for `@tailtrail` and
`@tailtrail-review`, preview and install the plugin package instead:

```bash
python3 scripts/tailtrail.py install codex-plugin --target buildweek-demo-project --dry-run
python3 scripts/tailtrail.py install codex-plugin --target buildweek-demo-project
```

5. Open `buildweek-demo-project` in Codex and use the installed `AGENTS.md`
project guidance. If you installed the plugin package, Codex can also load
`.codex-plugin/plugin.json` and `skills/` for native plugin invocation.

### Use this demo with Codex

1. Open the TailTrail repository folder in Codex.
2. Use GPT-5.6 in Codex for the Build Week recording.
3. Ask Codex to read the repository's `AGENTS.md` and
   `buildweek-demo-project/tailtrail-policy.md` before changing code. They
   describe the approval-first workflow, the standard-library-only constraint,
   and the focused test command.
4. Run the failing test, then paste this prompt into Codex:

```text
Run TailTrail Navigator first for this task: fix the claim amount validation bug
and add focused validation. Use root buildweek-demo-project and changed file
src/claims_api/validation.py. Show the plan only. Do not implement until I approve.
```

5. Run the Code Graph command from the plan. After you approve the plan, ask
   Codex to make only the one-line validation fix, then run the focused tests and
   TailTrail review.

For the exact recording prompts, use `DEMO-PROMPTS.md`. For Build Week, obtain
the `/feedback` Session ID from the primary Codex build thread and enter it in
Devpost; do not commit it to the repository.

### Judge test path - no rebuild required

From the TailTrail repository root, judges can inspect the working workflow and
repeat the deterministic evidence check without modifying the demo project:

```bash
python3 scripts/tailtrail.py doctor
python3 scripts/tailtrail.py start "fix the claim amount validation bug and add focused validation" --root buildweek-demo-project --changed src/claims_api/validation.py
python3 scripts/tailtrail.py graph ast --root buildweek-demo-project --changed src/claims_api/validation.py --depth v2
python3 scripts/tailtrail.py eval scenario report --scenario buildweek-validation
```

`buildweek-validation` is a committed, local, saved-artifact scenario. It does
not require a model/API key, network access, package installation, or a project
rebuild. It demonstrates TailTrail's planning, focused-context, review,
safeguard, and evidence-label workflow. It is not a claim about live model
performance or exact token savings.

For the editable live bug-fix walkthrough, follow `DEMO-RUNBOOK.md`. The initial
unit test intentionally fails until the one-line validation fix is applied.

### Codex and GPT-5.6 contribution

TailTrail gives Codex an approval-first local development workflow: Navigator
plans the task, Code Graph narrows the code context, the developer approves the
implementation, and TailTrail records focused validation and review evidence.
In the live Build Week demonstration, Codex using GPT-5.6 reads the focused
context and implements the approved one-line claims-validation fix.

The repository documents the workflow and judge path. Submit the `/feedback`
Session ID from the primary Codex project-building thread directly in the Devpost
form; it is intentionally not committed to this repository.

## Demo Story

The repo contains a small Python claims intake service with one intentional validation bug:

- claim amounts must be positive
- the current implementation allows `0`
- the test suite has a focused failing regression test

TailTrail should help the assistant:

1. Start with Navigator instead of jumping into edits.
2. Inspect the relevant files first.
3. Use the code graph to avoid broad repo reads.
4. Make the smallest validation fix.
5. Run focused tests.
6. Review the implementation against the original requirement.
7. Produce evidence and token posture without claiming exact savings.
8. Show repeatable Evaluation Harness proof through the committed `buildweek-validation` scenario.

## Quick Commands

From the TailTrail repo root:

```bash
python3 scripts/tailtrail.py start "fix the claim amount validation bug and add focused validation" --root buildweek-demo-project --changed src/claims_api/validation.py
python3 scripts/tailtrail.py graph ast --root buildweek-demo-project --changed src/claims_api/validation.py --depth v2
python3 scripts/tailtrail.py test plan --root buildweek-demo-project --changed src/claims_api/validation.py --goal "fix zero amount validation"
python3 -m unittest discover -s buildweek-demo-project/tests
python3 scripts/tailtrail.py review --root buildweek-demo-project
python3 scripts/tailtrail.py report value --root buildweek-demo-project
python3 scripts/tailtrail.py eval scenario report --scenario buildweek-validation
```

For copy-paste prompts to use during the demo, see `DEMO-PROMPTS.md`.

For the full capability map, see `FEATURE-COVERAGE.md`.

## Repeatable Proof Scenario

The live demo workspace is backed by a deterministic Evaluation Harness scenario:

```bash
python3 scripts/tailtrail.py eval scenario report --scenario buildweek-validation
python3 scripts/tailtrail.py eval scenario report --scenario buildweek-validation --format json
```

Use this when judges or reviewers ask for repeatable evidence. It compares a baseline artifact with a TailTrail-guided artifact and keeps the claim boundary explicit: committed fixture evidence only, not live model performance or exact token savings.

## Optional Evidence Demos

```bash
python3 scripts/tailtrail.py ci summarize --file buildweek-demo-project/logs/ci-failure.log
python3 scripts/tailtrail.py sonar summarize --file buildweek-demo-project/logs/sonar-sample.log
python3 scripts/tailtrail.py vulnerability summarize --file buildweek-demo-project/logs/trivy-sample.json
python3 scripts/tailtrail.py graph ast --root buildweek-demo-project --changed src/claims_api/validation.py --depth v3 --provider-output buildweek-demo-project/tailtrail-meta/providers/sample-semantic.json --approved
```

## Expected Initial Test Result

One test should fail before the fix:

```text
test_rejects_zero_amount ... FAIL
```

After fixing `validate_claim_amount`, all tests should pass.

## Pitch Line

TailTrail turns Codex from a prompt-by-prompt coding assistant into a local development control layer: Navigator-first planning, code graph context, approval gates, focused tests, review, evidence labels, repeatable Evaluation Harness proof, and measured-or-estimated value reporting.
