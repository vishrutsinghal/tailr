# TailTrail Public Claims Policy

Purpose: keep TailTrail's public wording accurate, evidence-based, and enterprise-credible.

TailTrail should be described as a local-first AI coding governance helper. It helps agents plan, preserve safeguards, reduce noisy context, summarize provided evidence, and choose smaller reviewable workflows. It does not replace source inspection, tests, CI, scanners, reviewers, legal review, or security review.

## Allowed Claims

Use these when describing TailTrail publicly:

- TailTrail helps coding agents make smaller, reuse-first changes.
- TailTrail provides local, deterministic helper scripts.
- TailTrail is assistant-agnostic through instruction adapters.
- TailTrail is approval-first for scans, captures, and risky commands.
- TailTrail summarizes provided CI, Sonar, vulnerability, and scanner output.
- TailTrail estimates token reduction from local context choices.
- TailTrail reports measured token usage only when users provide real model/API telemetry.
- TailTrail includes a committed measured evidence portfolio with scenario-class coverage and evidence labels.
- TailTrail keeps learning and reporting local by default.
- TailTrail can flag some risky wording or workflow gaps through deterministic checks.

## Cautious Claims

Use these only with evidence and boundaries:

- Token savings: say estimated unless real usage telemetry is supplied.
- Productivity impact: say observed, local, or measured only when outcome telemetry supports it.
- Review quality: cite benchmark artifacts, local outcomes, or specific review findings.
- Measured efficacy: cite the committed portfolio only for represented scenario classes and include mixed/estimated labels when present.
- Security usefulness: say scanner-aware or evidence-preserving, not security-complete.
- Learning usefulness: say advisory and confidence-scored, not self-training.
- Graph usefulness: say metadata-guided or impact-oriented, not a full semantic code graph unless a future engine actually supports that.

## Disallowed Claims

Do not claim or imply:

- guaranteed token savings
- guaranteed code quality improvement
- exact savings without measured telemetry
- fully automatic compliance
- TailTrail replaces CI
- TailTrail replaces tests
- TailTrail replaces code review
- TailTrail replaces security review
- TailTrail replaces SAST, dependency, vulnerability, or secret scanners
- TailTrail proves vulnerabilities are fixed
- TailTrail automatically enforces organization policy everywhere
- TailTrail self-heals agent behavior without review
- TailTrail records or learns from user behavior without explicit approval

## Evidence Labels

Use explicit labels in public reports and demos:

- **Estimated**: derived from local character or context-size approximations.
- **Measured**: derived from user-provided model/API usage telemetry.
- **Mixed**: a portfolio contains both measured and estimated/local-evidence scenarios; measured claims apply only to measured records.
- **Benchmark-measured**: measured telemetry is paired with passing committed benchmark artifacts and applicable quality gates.
- **Observed**: derived from local approved outcome, quality-loop, or benchmark artifacts.
- **Advisory**: recommendation only; current source, policy, validation, and reviewer judgment still win.

## Release Check Behavior

`scripts/release-check.py` scans public-facing docs for risky phrases. It allows cautious or negative statements such as "TailTrail does not replace CI" but should fail on unsupported promotional claims.

When adding public docs, prefer this wording:

```text
TailTrail helps teams reduce avoidable AI coding mistakes through local, approval-first guidance and deterministic checks.
```

Avoid this wording:

```text
TailTrail guarantees token savings and replaces CI/security review.
```
