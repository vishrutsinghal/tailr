# TailTrail Learning Governance

TailTrail learning is local, advisory, and evidence-weighted. It helps future work start with better repo context, but it must not become a silent source of bad patterns.

## Learning V3 Contract

New candidate and curated-learning facts use the append-only
`.tailtrail/learning-v3/events.jsonl` contract. Each record carries its class,
sanitized provenance, repository applicability frame, freshness invalidators,
utility evidence, privacy posture, lifecycle transition, and digest-chain
position. Amendments, revalidation, supersession, and revocation append a new record; they do
not edit history.

The legacy `.tailtrail/learning-events.jsonl` and `.tailtrail/learnings.md`
files remain readable compatibility projections for at least two releases.
Migration preserves their bytes and imports only sanitized candidate fields by
relative source reference and fingerprint.

```bash
python3 scripts/tailtrail.py learn v3 validate --root .
python3 scripts/tailtrail.py learn v3 state --root .
python3 scripts/tailtrail.py learn v3 migrate --root . --dry-run
python3 scripts/tailtrail.py learn v3 migrate --root . --approved
python3 scripts/tailtrail.py learn v3 amend --root . --learning-id <id> --reason "clarify applicability" --advice "..." --approved
python3 scripts/tailtrail.py learn v3 revalidate --root . --learning-id <id> --reason "current evidence confirms it" --evidence-ref <relative-path> --approved
python3 scripts/tailtrail.py learn v3 supersede --root . --learning-id <id> --replacement-id <id> --reason "newer evidence" --approved
python3 scripts/tailtrail.py learn v3 revoke --root . --learning-id <id> --reason "policy conflict" --approved
```

V3 rejects raw prompts, source, logs, identity fields, sensitive candidate
text, unsafe paths, and records from another project frame. Utility remains an
observed association and never a causal claim.

## Navigator Retrieval And Conflict Gate

Navigator retrieves only after it has both the repository project frame and a
classified task frame. `tailtrail learn retrieve` applies deterministic task,
tag, path, requirement, confidence, and curation scoring; returns at most three
records; and explains each match and invalidator check. Lite remains quiet when
no candidate reaches its high-value threshold.

The gate blocks terminal records, elapsed revalidation, approved stale or
suppression actions, changed provenance, missing explicitly scoped source,
task/path/tag/requirement exclusions, non-normal sensitivity, and explicit
`learning:<id>` contradictions. Blocked output contains IDs and reasons, never
the blocked advice. Eligible advice is rendered only as a default-deny use
proposal and is not injected into requirements, plans, implementation
instructions, source, or task state.

```bash
python3 scripts/tailtrail.py learn retrieve --root . --task-types qa --tags validation --path tests/test_service.py
```

## Use Receipts And Closure Attribution

After the user or host chooses what to do with a saved Learning Use Proposal,
record the decision against the approved requirement UID. The run-local
`.tailtrail/runs/<run-id>/learning/use-receipts.jsonl` stream is append-only,
repository-framed, digest-chained, and sanitized.

```bash
python3 scripts/tailtrail.py learn receipt record --root . --run-id <run-id> --learning-id <learning-id> --decision applied --decision-type implementation --requirement-uid <requirement-uid> --rationale "Used for the approved implementation choice" --approved
python3 scripts/tailtrail.py learn receipt show --root . --run-id <run-id>
python3 scripts/tailtrail.py learn receipt validate --root .
```

Decisions are `applied`, `advisory`, `ignored`, `rejected`, or `stale`.
Applied/advisory decisions require the exact current eligible V3 record from
the saved proposal; terminal, changed, missing, or blocked advice cannot be
recorded as used. Every decision is linked to approved requirement UIDs and a
decision domain such as implementation, validation, architecture, dependency,
security, release, debugging, or review.

Canonical closure joins the latest decision to requirement status, drift,
Harness status, unresolved failures, validation, and a fingerprinted Completion
Report. It appends one categorical association and renders it in the report.
Changed closure evidence supersedes the prior attribution; identical evidence
is reused. Only the latest attribution after the latest decision affects
utility.

Association deltas are deliberately small and bounded. Security, dependency,
release, and data-migration domains cap at ±5; other domains cap at ±10; the
project retrieval adjustment caps at ±20. `causal_claim` is always false.
Receipts never override current source, tests, CI, scanner, policy, guardrails,
or explicit user evidence and never promote a learning automatically.

## Refresh, Conflict, And Negative Learning

The append-only `.tailtrail/learning-conflicts.jsonl` stream is the canonical
owner of challenges, pairwise conflicts, revalidation decisions, and
negative-learning candidates. Every transition is repository-framed,
digest-chained, sanitized, and explicit-approval gated.

```bash
python3 scripts/tailtrail.py learn governance state --root .
python3 scripts/tailtrail.py learn governance challenge --root . --learning-id <id> --reason "contradicted by current evidence" --evidence-ref <relative-path> --approved
python3 scripts/tailtrail.py learn governance challenge-resolve --root . --challenge-id <id> --resolution confirm --reason "focused validation confirms it" --evidence-ref <relative-path> --approved
python3 scripts/tailtrail.py learn governance conflict --root . --learning-id <id-a> --learning-id <id-b> --reason "contradictory advice" --evidence-ref <relative-path> --approved
python3 scripts/tailtrail.py learn governance negative-scan --root .
python3 scripts/tailtrail.py learn governance negative-scan --root . --approved
```

New and revalidated V3 records fingerprint policy, graph, symbol, manifest,
ownership, source, and validation domains. Any declared change blocks the
record until evidence-backed revalidation. Open challenges and conflicts also
block affected records. Corrupt governance evidence blocks retrieval globally.

Two distinct adverse PM-L3 receipts after the latest revalidation form a
negative-learning candidate. The candidate retains only learning IDs,
categorical signals, counts, and evidence references. It never copies raw
failure content. Explicit promotion creates sanitized `avoid-history` and
revokes the contradicted source learning; explicit dismissal keeps the audit
trail and removes the open-candidate block.

## Purpose

Use learning governance to decide whether a prior event is safe to reuse, needs more evidence, should stay as weak history, or should be suppressed from future retrieval.

Learning governance protects against:

- user-biased acceptance of weak fixes
- stale code, policy, scanner, or validation assumptions
- repeated rejected patterns
- missing validation evidence
- dependency or security shortcuts
- noisy learning files that increase token cost

## Core Rule

User acceptance is useful evidence, not proof.

Current source, tests, CI, scanner output, local policy, guardrails, and explicit user instructions always override old learnings.

## Confidence Bands

| Score | Meaning | Retrieval behavior |
|---:|---|---|
| 0-39 | do not use | Do not retrieve during normal work. |
| 40-59 | weak historical note | Show only for debugging, refresh, or explicit history review. |
| 60-79 | candidate learning | Suggest with caution and require current-source inspection. |
| 80-100 | trusted reusable repo pattern | Eligible for curated reuse if it is normal sensitivity and not stale. |

Low-confidence accepted work can be recorded as an event when the user explicitly wants history, but it must not be promoted into `.tailtrail/learnings.md` unless stronger evidence raises the score.

## When To Capture

Capture a learning only when the result is likely reusable:

- a repeated bug pattern was fixed
- a CI, Sonar, lint, or vulnerability issue had a reusable resolution
- a validation command was confirmed
- a dependency decision was approved through the dependency gate
- a reviewer or owner gave useful feedback
- a project convention was discovered and confirmed

Prefer compact summaries over raw history.

## When Not To Capture

Do not capture:

- secrets, credentials, tokens, PII, PHI, customer data, or raw logs
- full user prompts, full assistant responses, or source snippets by default
- one-off tiny edits with no future value
- speculative ideas that were not validated
- fixes that removed validation, authorization, escaping, accessibility, data-loss prevention, or policy safeguards
- dependency changes that skipped required approval
- rejected solutions unless the rejection reason is useful avoid-history

## Review Command

Run learning review before broad reuse, monthly hygiene checks, or after TailTrail gives weak suggestions:

```bash
python3 scripts/tailtrail.py learn review --root .
python3 scripts/tailtrail.py learn review --root . --write-result
python3 scripts/tailtrail.py learn review --root . --format json
```

The review command reads compact local learning metadata and reports:

- weak or do-not-use event counts
- rejected event counts
- missing validation evidence
- guardrail weakening signals
- low-confidence user overrides
- duplicate learning candidates
- conflicting learning candidates
- stale or blocking refresh actions

It does not edit learning files.

## Refresh Actions

Use refresh actions only after review:

```bash
python3 scripts/tailtrail.py learn refresh recommend --root .
python3 scripts/tailtrail.py learn refresh stale --root . --days 90
python3 scripts/tailtrail.py learn refresh apply --root . --learning-id 20260712-abc12345 --action suppress --reason "Rejected by reviewer" --approved
```

Approved blocking actions such as `mark-stale`, `suppress`, `archive`, and `delete` prevent automatic retrieval.

## Promotion Rules

### Debug Harness candidates

A Debug run can create positive learning only after the canonical Completion
Report is complete and the delivery is explicitly accepted by a user or linked
trusted CI. The candidate may contain only a sanitized failure fingerprint,
proven cause domain, domain-capped confidence state, validation tiers, and the
acceptance source. Raw symptoms, prompts, source, logs, stack frames,
repository/user/customer identity, credentials, and secrets are forbidden.

Debug learning remains `candidate-only` and follows the same review,
confidence, staleness, suppression, and explicit promotion rules below. A
Debug closure or high confidence state never promotes guidance by itself.

Promote to curated learnings only when:

- the event is reusable
- confidence is at least 80 or meets the risk-specific threshold
- validation passed or objective evidence is strong
- sensitivity is normal
- the learning has a stale condition
- no refresh action suppresses it
- current source and policy do not contradict it

Promotion should be explicit:

```bash
python3 scripts/tailtrail.py learn promote --root . --event-id 20260712-abc12345
```

## Token Discipline

Normal work should read `.tailtrail/learning-index.md` first and retrieve at most three matching learnings. Do not load `.tailtrail/learning-events.jsonl` into normal implementation context unless the user explicitly asks for learning history or debugging.

If learning files grow noisy, run review and refresh instead of loading more context.

## Calibration And Proof

PM-L5 uses the committed paired scenario catalog to measure learning-on versus
control behavior for every Learning V3 class. Run:

```bash
python3 scripts/tailtrail.py eval learning evaluate --format json
```

Fixture evidence is useful for regressions but cannot establish general product
efficacy. A project adjustment is available only after later, validated PM-L3
use receipts provide at least four mixed positive/adverse outcomes for a class.
The approved projection is repository-framed, integrity-linked to its report,
bounded to plus or minus ten points, and revalidated on every retrieval.
Invalid calibration blocks advice instead of silently falling back.

`meta-feed` emits only repeated categorical observations that pass the existing
shared Harness sanitizer. Exact scores, times, token counts, receipt identities,
prompts, source, logs, and project identity never enter Meta-Harness evidence.

## Enterprise Use

Use Enterprise Reporting for trend review:

```bash
python3 scripts/tailtrail.py report --month 2026-07
```

The report includes learning hygiene signals. Use them to improve TailTrail rules, Navigator behavior, local policy, or team guidance. Do not use them for hidden user scoring or surveillance.
