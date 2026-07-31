---
name: tailtrail-review
description: Use to review code, a git diff, a pull request, or a proposed implementation for requirement fulfillment, unnecessary complexity, avoidable dependencies, duplicate logic, over-broad rewrites, risky simplification, missing focused checks, weakened safeguards, unsupported claims, or changes that should reuse existing project patterns. TailTrail Review returns concrete findings that help keep code small, correct, maintainable, safe, and aligned with the user request.
---

# TailTrail Review

Use TailTrail Review to inspect a change before it lands. The goal is not to make code tiny at any cost; the goal is to remove work the codebase should not have to own.

For broad or repeated reviews, use `context/TailTrail.map.md` and the `review` slice from `context/slices.md`. Keep the exact diff and touched source text exact.

For risky or non-trivial reviews, apply `GUARDRAILS.md`, especially evidence, safeguard preservation, validation truth, exactness, and review guardrails.

If `tailtrail-policy.md` exists in the target project, use it for local validation expectations, ownership, restricted folders, dependency rules, and review requirements. Treat `tailtrail-policy.example.md` as a template only.

When a diff adds, upgrades, removes, or wraps a dependency, apply `DEPENDENCY-GATE.md`. For AIDLC-driven work, use `templates/diff-handoff.md` to check changed, reused, skipped, validated, and risk notes.

When the review follows a TailTrail Navigator or AIDLC plan, include a requirement-fulfillment pass:

- compare the diff against the original user request
- compare against approved Navigator plan, AIDLC requirements, or clarified acceptance criteria when available
- identify missing requested behavior, partial implementation, over-implementation, and assumptions that need clarification
- ask concise clarification questions when fulfillment cannot be judged from the diff and available requirements
- do not treat code health as sufficient if the requested behavior was not actually delivered

Use the command surface when available:

```bash
python3 scripts/tailtrail.py review
python3 scripts/tailtrail.py review --scope branch --base main
python3 scripts/tailtrail.py review --scope path --dir services/payment
python3 scripts/tailtrail.py test plan --changed path/to/file
```

## Review Pass

Inspect the current diff or supplied code for:

1. Missing, partial, or incorrect fulfillment of the user request, approved plan, AIDLC requirement, or acceptance criteria.
2. Reimplementation of an existing helper, component, type, utility, or pattern.
3. New dependencies that standard library, platform, framework, or installed packages already cover.
4. Single-use abstractions, broad configuration, wrapper layers, or scaffolding added for imagined future needs.
5. Symptom patches that should be root-cause fixes in a shared function or common path.
6. Large rewrites where a smaller targeted change would solve the same behavior.
7. Removed or weakened validation, authorization, escaping, accessibility, privacy, logging, auditability, error handling, or data-loss protection.
8. Non-trivial behavior with no focused runnable check.
9. Unsupported claims that tests, scans, builds, pushes, approvals, deployments, or token savings succeeded without evidence.

## Finding Format

Lead with actionable findings. For each finding, include:

- Severity: `high`, `medium`, or `low`.
- Location: file and line when available.
- Issue: what is unnecessary, risky, or over-broad.
- Change: the smaller or safer alternative.
- Evidence: exact diff, file, caller, test, or policy signal behind the finding when useful.
- Requirement link: user request, approved plan item, AIDLC requirement, or acceptance criterion when the finding is about fulfillment.

If there are no useful findings, say that clearly and mention any remaining test or review risk.

For command-style review summaries, include enough detail for each finding to be actionable:

- severity
- one-line issue description
- file name
- function or symbol when known
- line number when available
- recommended fix direction

If the user asks for a guarded fix loop, ask for approval before applying changes. Record learning or outcome details only when the user explicitly approves capture.

## Review Standards

- Do not request churn for personal style preference.
- Do not remove code that documents required business behavior.
- Do not suggest shorter code if it weakens important safeguards.
- Prefer deleting unused structure over renaming or reshaping it.
- Prefer one focused follow-up check over a large test suite unless the repository already uses that style for the touched area.
- Keep exact diffs, source snippets, line numbers, commands, dependency names, security rules, scanner IDs, and validation evidence exact when they affect the finding.
- Learning is advisory only; current source, tests, CI, scanners, policy, guardrails, and explicit user instructions always win.
