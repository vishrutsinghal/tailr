# TailTrail - OpenAI Build Week Submission Notes

## Track

Developer Tools.

## Project description

TailTrail is a local, approval-first control layer for Codex. It helps developers
turn a coding request into a focused workflow: Navigator plans before editing,
Code Graph narrows local code context, the developer approves implementation,
focused tests validate the change, and review/evidence outputs make the result
easy to inspect.

The Build Week demo fixes an intentional validation bug in a small Python claims
service. TailTrail guides Codex to inspect the relevant function and regression
test, wait for approval, make the smallest fix, validate it, and review whether
the original requirement was fulfilled.

## What is meaningful

- Navigator-first planning for small and larger coding tasks.
- Local AST-based code context with evidence labels.
- Explicit approval boundaries for implementation and provider-backed metadata.
- Focused validation and post-change requirement review.
- A deterministic `buildweek-validation` Evaluation Harness scenario that lets
  judges replay the demo story from committed artifacts.

## Codex and GPT-5.6

Codex is the coding agent shown in the demo. GPT-5.6 is used through Codex for
the approved implementation step after TailTrail has produced the local plan and
focused context. TailTrail supplies the workflow, guardrails, and evidence layer;
it does not replace the model.

Submit the `/feedback` Session ID from the primary project-building Codex thread
in the Devpost form. Keep that identifier in the form rather than committing it
to the repository.

## Judge testing path

From the repository root, with Python 3.9 or later:

```bash
python3 scripts/tailtrail.py doctor
python3 scripts/tailtrail.py start "fix the claim amount validation bug and add focused validation" --root buildweek-demo-project --changed src/claims_api/validation.py
python3 scripts/tailtrail.py graph ast --root buildweek-demo-project --changed src/claims_api/validation.py --depth v2
python3 scripts/tailtrail.py eval scenario report --scenario buildweek-validation
```

The judge path is local and requires no model/API key, package install, network
access, database, or external scanner. The repeatable scenario does not modify
the demo project or require a rebuild. For the editable live walkthrough, see
`DEMO-RUNBOOK.md`.

## Claim boundaries

TailTrail does not claim that the saved-artifact scenario proves live model
performance, production defect reduction, scanner replacement, or exact token
savings. Token savings are estimates unless measured provider telemetry is
supplied.
