# TailTrail

## A local, approval-first control layer for Codex

TailTrail helps teams use Codex with a smaller, safer, and more reviewable local
development workflow. It does not replace Codex, tests, CI, security tools, or
human review. It gives those tools a clearer sequence: plan, inspect, approve,
change, validate, review, and preserve evidence.

## The problem

Coding agents are powerful, but a vague request can lead to broad repository
reads, premature edits, missed local policy, and weak validation evidence.
Developers and reviewers need a way to keep AI-assisted changes focused and
auditable without adding a cloud service or a heavy process to every small task.

## The TailTrail workflow

```text
Task -> Navigator plan -> focused code context -> approval -> small change -> focused test and review -> evidence
```

- **Navigator-first:** recommends the leanest workflow before implementation.
- **Code Graph:** maps local symbols, likely callers, and likely tests so the
  coding agent can read targeted context instead of the entire repository.
- **Policy and approval gates:** preserve local validation and dependency rules;
  risky commands and provider-backed metadata remain explicit choices.
- **Focused validation and review:** guide the smallest relevant test run and
  check requirement fulfillment after the change.
- **Evidence-aware reporting:** distinguish local estimates, measured telemetry,
  and deterministic saved-artifact evidence.

## Build Week demo

The demo uses a small Python claims service with an intentional bug: it accepts a
zero-dollar claim even though claim amounts must be positive. TailTrail guides
Codex to inspect the right validation file and test, wait for approval, make the
one-line fix, run the focused tests, and review the result.

The demo also includes `buildweek-validation`, a deterministic local scenario
that compares committed baseline and TailTrail-guided artifacts. It makes the
demo repeatable without claiming live model performance, production outcomes, or
exact token savings.

## Why Codex and GPT-5.6

Codex is the coding agent in the demonstrated workflow. GPT-5.6 is used through
Codex to reason over the Navigator plan, inspect the focused code context, and
implement the approved minimal fix. The submission's primary Codex `/feedback`
session ID is supplied in the Devpost form as required by Build Week.

## Local-first boundaries

- No external service, model/API key, package installation, or network access is
  required for the judge test path.
- TailTrail does not automatically edit code, run scanners, upload telemetry, or
  replace CI, tests, scanners, or review.
- Token savings are estimates unless measured provider telemetry is supplied.

## Judge path

From the repository root:

```bash
python3 scripts/tailtrail.py doctor
python3 scripts/tailtrail.py start "fix the claim amount validation bug and add focused validation" --root buildweek-demo-project --changed src/claims_api/validation.py
python3 scripts/tailtrail.py graph ast --root buildweek-demo-project --changed src/claims_api/validation.py --depth v2
python3 scripts/tailtrail.py eval scenario report --scenario buildweek-validation
```

See `buildweek-demo-project/README.md` for supported platforms, the live demo,
and exact verification commands.
