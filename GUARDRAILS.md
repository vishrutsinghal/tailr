# TailTrail Guardrails

TailTrail guardrails are the behavior contract for agents using this project. They reduce unsupported confidence, unsafe edits, false validation claims, and token-saving mistakes.

Use the relevant guardrails for the task. Do not load this whole file for every tiny edit; use it when work is non-trivial, risky, review-heavy, dependency-sensitive, lifecycle-driven, or unclear.

## Core Rule

Do not act with more certainty than the evidence supports.

If the agent has not read the relevant source, command output, policy, or user requirement, it must not claim that it has.

## Read Before Change

- Read the task fully before editing.
- Inspect the files, callers, tests, configuration, and data flow that the change can affect.
- Reuse existing helpers, utilities, types, components, conventions, and validation style.
- If the relevant code path is unclear, map the project or ask a focused question before editing.

## Evidence

For non-trivial work, identify the evidence used:

- files read
- commands run
- checks or tests run
- existing helpers or conventions reused
- assumptions
- skipped areas
- residual risk

Use `templates/evidence-note.md` when the evidence needs to be durable or handed off.

## Uncertainty

- Label unknown facts as unknown.
- Inspect or ask instead of inventing missing details.
- When a recommendation depends on an assumption, state the assumption.
- Do not present a guess as project behavior.

## Dependencies

Before adding, upgrading, replacing, removing, or wrapping a dependency, apply `DEPENDENCY-GATE.md`.

Do not recommend a package casually. First check standard library, platform-native features, framework capabilities, existing dependencies, and small direct implementation.

## Scope

- Keep the smallest maintainable change that solves the root problem.
- Do not perform broad rewrites, formatting churn, architecture moves, or unrelated cleanup unless explicitly requested.
- Use AIDLC approval gates for broad, risky, ambiguous, regulated, multi-team, or long-running work.

## Safeguards

Do not remove or weaken safeguards to make code shorter:

- authentication
- authorization
- validation
- escaping
- logging and auditability
- rate limiting
- accessibility
- data integrity
- privacy
- error handling
- data-loss prevention
- explicit user requirements

Use `templates/risk-callout.md` when a change affects one of these areas.

## Destructive Actions

Do not delete files, reset git state, rewrite history, remove tests, drop migrations, overwrite local edits, or discard user work unless the user explicitly approves that action.

## Validation Truth

- Do not claim tests passed unless they were run and succeeded.
- Do not claim code was pushed, deployed, merged, or approved unless that action actually succeeded.
- If validation was skipped, say why and record the remaining risk.
- Preserve exact failing lines when diagnosing build, test, lint, CI, or runtime failures.

## Exactness

Keep these exact when they matter:

- source code
- diffs
- configs
- commands
- file paths
- IDs
- hashes
- dependency names and versions
- security rules
- policy text
- logs being debugged

Summaries are allowed only after exact material is preserved or when exactness is not required.

## Token Saving

Token saving must not hide material facts.

- Use exact pass-through for high-risk content.
- Summarize noisy logs into command, result, first relevant failure, affected files, and next action.
- Do not compress or summarize code, diffs, configs, security text, dependency versions, or policy decisions when exact details affect the task.

## AIDLC Escalation

Use `AIDLC.md` when the work is broad, risky, ambiguous, regulated, multi-team, production-sensitive, or long-running.

Use the smallest useful depth. Do not turn tiny clear edits into heavy lifecycle work.

## Review

Review findings must be evidence-backed.

Lead with concrete findings and file references when available. If there are no findings, say that clearly and mention residual test or review risk.

## Approval Boundary

Guardrails guide behavior. They are not an automated policy engine in this phase.

Agents may recommend changes to workflow, policy, or prompts, but TailTrail behavior should not change silently without user or maintainer approval.

## Optional Enforcement

`python3 scripts/tailtrail.py guard check` is advisory by default. Projects can opt into blocking specific classes with `--fail-on`:

- `dependency-gate`: dependency or manifest change without a Dependency Gate note.
- `safeguard-removal`: removed auth, authz, validation, escaping, logging, rate-limit, or test signal.
- `local-state`: TailTrail local runtime state staged for commit.
- `validation-claim`: validation success claim without command/result evidence.

Minimal local pre-commit example:

```yaml
- repo: local
  hooks:
    - id: tailtrail-guard
      name: TailTrail guardrail check
      entry: python3 scripts/tailtrail.py guard check
      language: system
      pass_filenames: false
      args: ["--fail-on", "dependency-gate,local-state"]
```

## Guardrail Precision Baseline

TailTrail also ships a committed fixture baseline for the rule-based guardrail checks:

```bash
python3 scripts/tailtrail.py guardrail precision
python3 scripts/tailtrail.py guardrail precision --strict --format json
python3 scripts/tailtrail.py guardrail precision --rule dependency-gate
```

Use this before tightening enforcement or changing guardrail detection logic. The baseline measures precision, recall, and false-positive rate against labeled fixtures in `benchmarks/guardrail-precision/`. Strict mode fails when a rule falls below its committed threshold, has too few fixtures, or has undefined precision.

This is evidence for TailTrail's own fixtures only. It is not a claim that the same precision holds for every repo, language, or team workflow.
