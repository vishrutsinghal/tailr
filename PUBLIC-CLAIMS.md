# TailTrail Public Claims Policy

Purpose: keep TailTrail's public wording accurate, evidence-based, and enterprise-credible.

PM-7 adoption qualification is evidence-gated. A coded usability protocol,
fixture receipt, local test, configured workflow, or read-only report is not a
new-user or experienced-user outcome. Adoption and developer-experience claims
require genuine observer-attested receipts that meet every cohort, friction,
comprehension, and zero-safety-weakening gate in the sealed PM-7 catalog.

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

## Public evidence portfolio

The committed public portfolio currently contains five **fixture-scored**,
sanitized comparisons under `benchmarks/public/`. They cover dependency
decisions, validation/caller proof, API contracts, bounded refactoring, and
complexity remediation. They are reproducible deterministic evidence only and
must not be presented as live-model performance.

Their committed result is `benchmarks/results/public-benchmark-2026-08.json`.

No real model-run result is committed by default. When a contributor supplies
an explicitly approved, sanitized model-run receipt with complete provider
telemetry, TailTrail records it as `benchmark-measured`; otherwise it records
`model-run-unmeasured`. Any public numeric claim must cite the exact committed
result and its label.

## Pilot Protocol

This section defines how a representative efficacy pilot must be run and
reported (Phase E11, `ENT-E11-002`). **No pilot has been executed under this
protocol yet; nothing in this section is a claim of measured pilot outcomes.**
It exists so that if and when a pilot runs, its evidence is comparable and
its claims stay bounded.

- **Method**: opt-in only. Participants explicitly consent per repository;
  there is no default or silent enrollment.
- **Sample**: record the number of participating repositories/teams, task
  types attempted, and duration. A single-repository or single-user trial must
  be labeled as such, not generalized to "teams" or "enterprises."
- **Privacy**: no raw source, prompts, or private logs are collected by
  default. Only sanitized `enterprise support-bundle` output, redacted
  `doctor`/`completion-report` results, and explicit participant-provided
  telemetry may be collected, and only with the participant's approval.
- **Measures**: install success rate, first-run completion rate, false-success
  rate (completion reports later found wrong), evidence completeness rate,
  approval latency, recovery time after an interrupted run, rollback success,
  and operator time per workflow (self-reported, since TailTrail does not
  observe wall-clock human time).
- **Evidence labeling**: pilot results follow the same `Evidence Labels`
  above. Self-reported operator burden is `estimated` unless corroborated by
  timestamped logs; everything else follows the measured/observed/advisory
  rules already defined.
- **Limitations that must be disclosed with any pilot claim**: sample size,
  which task types were and were not attempted, whether participants had
  prior TailTrail experience, and whether any maintainer intervened during
  the pilot (if so, the affected run is not "without maintainer
  intervention").
- **Publication rule**: a pilot claim may only cite this protocol's actual
  recorded artifacts (sample size, method, dated report). It may never be
  phrased as if it applies beyond the recorded sample.

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
