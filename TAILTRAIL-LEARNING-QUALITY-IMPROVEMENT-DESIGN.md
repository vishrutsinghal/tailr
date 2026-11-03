# TailTrail Learning Quality Improvement Design

## Status

This document defines how TailTrail should turn verified delivery experience
into compact, evidence-backed, reusable guidance. The first delivery slice in
this worktree consolidates equivalent Learning V3 candidates while preserving
the append-only record. The broader capture and quality improvements below are
design proposals and must be delivered through separately approved slices.

## Purpose

TailTrail has accumulated extensive operational experience, but its canonical
learning store does not represent most of it usefully. The repository already
contains detailed defect investigations, verified host techniques, proof
recipes, recovery paths, user corrections, and completed-run evidence. Most of
that knowledge currently lives only in:

- `TAILTRAIL-ISSUES-LOG.md`;
- `TAILTRAIL-PLAYBOOK.md`;
- `TAILTRIAL-GROUND-RULES.md`;
- Completion Reports and Delivery Records;
- approved plans and revisions;
- managed proof and closure receipts; and
- `TAILTRAIL-OPERATOR-GUIDANCE-AND-REPORTING-DESIGN.md`.

The learning system should not copy those documents into another large memory
file. It should extract small reusable decisions, bind them to exact evidence,
validate their current applicability, and retrieve no more than the few items
that materially help the active task.

## Evidence baseline

The learning inventory inspected on 2026-11-03 contained:

| Measure | Observed value |
|---|---:|
| Learning V3 candidates | 69 |
| Unique source runs | 61 |
| Unique advice statements | 1 |
| `partial` validation outcomes | 68 |
| `fail` validation outcomes | 1 |
| Candidates with a file association | 46 |
| Candidates with a runnable validation command | 0 |
| Confidence range | 0-31 |
| Retrieval band | all `do-not-use` |
| Promotion state | all `candidate-only` |

Every candidate carried the same advice:

> Do not declare completion while requirement drift, failed evidence, or
> unresolved execution failures remain.

The candidates did preserve some useful context: source run, requirement IDs,
affected paths, and categorical tags such as `requirement-incomplete`,
`evidence-gap`, and `requirement-drift`. They did not preserve the specific
failure, correction, proof command, successful recovery, or boundary that
would help a later host avoid the same problem.

By contrast, `TAILTRAIL-ISSUES-LOG.md` contains at least 50 numbered issue
sections plus sub-findings. Many have a symptom, root cause, correction,
focused proof, status, and run evidence. The playbook contains verified-live
operator techniques. These are much stronger learning sources than a generic
incomplete-closure sentence, but the current capture path does not project
them into Learning V3.

## Problem statement

The present learning flow has five quality failures.

### 1. Repeated observations become repeated records

Equivalent advice was captured once per closure observation. Contextual tag or
path differences prevented one useful aggregate view. This inflated review and
refresh output without increasing knowledge.

### 2. The specific lesson is discarded

A run may prove that a pending-plan renderer used stale v1, that proof was
bound globally instead of per requirement, or that a validation-only closure
incorrectly demanded a source-edit receipt. The captured candidate reduces all
of these to the same generic statement about incomplete closure.

### 3. Evidence needed for reuse is absent

The records contain no runnable validation commands. They do not identify the
public route, expected and actual behavior, proven cause boundary, fixed
version, preservation criteria, or exact recovery action.

### 4. Confidence cannot improve responsibly

Observation count alone is not proof. Sixty-nine weak copies must not become a
trusted learning merely because they are numerous. Confidence should improve
only when independent evidence confirms the advice and later use receipts show
compatible outcomes.

### 5. Freshness is too coarse for append-only references

Migrated records point to one exact line in
`.tailtrail/learning-events.jsonl`, but the current source invalidator hashes
the entire append-only file. Appending a new event therefore makes every prior
line appear changed. Exact provenance verification already checks the cited
line separately. Freshness must respect that fragment boundary.

## Product objective

TailTrail learning should answer this question:

> For this exact task type, path, requirement, and evidence boundary, what
> previously verified guidance can reduce mistakes without overriding current
> source, policy, proof, or approval?

A useful learning is a bounded advisory record, not a transcript, plan,
permission, root-cause assertion, or replacement for investigation.

## Non-negotiable invariants

1. Learning history remains append-only. Consolidation appends an aggregate
   amendment and supersession transitions; it never deletes or rewrites prior
   records.
2. Raw prompts, raw logs, source bodies, stack traces, credentials, identity
   data, PII, PHI, and customer data are forbidden.
3. Host statements begin as candidates. They cannot mark themselves accepted,
   validated, current, or trusted.
4. Current source, tests, CI, scanners, policy, guardrails, approved scope,
   managed evidence, and explicit user decisions always win.
5. Learning never grants implementation scope, proof authority, plan approval,
   or closure authority.
6. Open or speculative issue-log findings are not positive guidance. They may
   become investigation notes or `avoid-history` only after evidence and an
   explicit governance decision.
7. Observation count affects visibility and review priority, not confidence by
   itself.
8. Retrieval remains default-deny and bounded to the most relevant few items.

## Canonical consolidation contract

Equivalent-advice consolidation uses the following rules:

- normalize whitespace and case for comparison;
- require the same learning class;
- allow tags, paths, requirements, and source runs to differ;
- select the earliest current record as the stable canonical learning ID;
- append a canonical amendment containing unioned applicability;
- sum `observation_count` and `use_count` without increasing confidence;
- preserve the most conservative confidence and sensitivity;
- attach exact source-event references that retain source-run lineage;
- append `supersede` transitions from every merged record to the canonical ID;
- reject missing, terminal, cross-class, or different-advice records; and
- require explicit `--approved` execution.

For the current data this should leave one current canonical record with:

- `observation_count: 69`;
- 61 unique source-run IDs discoverable through its source-event evidence;
- unioned task types, tags, paths, requirements, exclusions, and invalidators;
- the original advice;
- conservative `do-not-use` confidence until separately revalidated; and
- 68 terminal records whose replacement points to the canonical learning.

## What a useful learning should contain

The existing Learning V3 record remains the advisory owner. Supporting
projections may expose richer evidence, but should not duplicate raw source.

| Field | Purpose |
|---|---|
| Learning class | Positive pattern, avoid-history, validation command, project convention, dependency decision, debug cause, or general guidance. |
| Summary | One specific reusable outcome, not a generic completion warning. |
| Advice | The action a later host may consider. |
| Problem signature | Stable symptom or condition that determines applicability. |
| Behavior surface | CLI, MCP, planning, scope, proof, workflow, closure, learning, installation, or presentation. |
| Applicability | Task types, tags, paths, requirement categories, public routes, and explicit exclusions. |
| Evidence | Issue section, run ID, approved requirement, proof receipt, test path, and exact command where available. |
| Outcome | Fixed, rejected, superseded, partially validated, or confirmed reusable. |
| Preservation boundary | What the fix must not weaken or change. |
| Recovery action | The exact next command or decision when the pattern is encountered. |
| Freshness | Content-scoped invalidators and revalidation deadline. |
| Utility | Observation count, use count, later outcomes, and non-causal usefulness score. |
| Governance | Candidate, challenged, revalidated, curated, superseded, or revoked. |

The schema should remain closed. If these concepts cannot be represented by
existing fields and evidence references, add a separately versioned supporting
artifact rather than placing unstructured prose or raw history into the V3
record.

## Learning sources and eligibility

### Issue log

An issue is eligible only when the reusable part is evidence-backed. A fixed
issue can produce a positive pattern and a validation recipe. An open issue can
produce an `avoid-history` candidate only when the failed behavior was
reproduced and the warning is useful without asserting an unproven cause.

Required extraction:

- issue identifier and status;
- public symptom;
- first proven failing boundary;
- generic root pattern, when proven;
- accepted fix or recovery action;
- exact proof path and command;
- preservation criteria;
- affected versions or freshness triggers; and
- source run or artifact references.

### Playbook

Only entries explicitly marked verified-live are eligible. A playbook entry is
a strong host-operation candidate because it already has a condition and a
tested technique. It still needs current-source and command validation before
promotion.

### Completion and Delivery Records

Completion should capture specific categorical observations, not generate the
same sentence for every incomplete run. Examples include:

- approved command missing from a requirement binding;
- newer managed evidence not selected;
- selected harness missing its required artifact;
- source changed after proof;
- closure requested an inapplicable source-edit receipt; and
- final report rendered a stale projection.

### User correction and plan rejection

Repeated user corrections are valuable negative signals. They should record
the rejected pattern and corrected decision, not the user's raw wording. A
single rejection remains low-confidence. Repeated compatible rejections can
open a governance challenge but cannot silently create policy.

### Managed proof and Meta Harness

Managed proof supplies the strongest local validation evidence. The Meta
Harness should check that candidate claims match actual source participation,
public-route behavior, proof results, and declared preservation boundaries. It
monitors both TailTrail and host behavior; it does not become a second planning
or learning authority.

## Candidate-to-learning pipeline

1. **Detect:** identify a specific reusable decision or failure pattern from a
   closure, issue, review, or verified playbook entry.
2. **Classify:** assign the learning class and behavior surface.
3. **Sanitize:** remove raw prompt, log, source, identity, and sensitive data.
4. **Normalize:** create a stable problem signature and advice key.
5. **Deduplicate:** attach a new observation to an equivalent current learning
   or create one candidate when no safe match exists.
6. **Bind evidence:** attach issue, run, requirement, path, command, tier,
   asserted behavior, and proof receipt references.
7. **Validate:** inspect current source and execute or verify the exact proof
   through the public route that owns the behavior.
8. **Challenge:** compare against current policy, contradictory learnings, open
   issues, and negative outcome receipts.
9. **Govern:** require explicit acceptance, revalidation, supersession,
   revocation, or promotion.
10. **Retrieve:** match only current, relevant, sufficiently useful records and
    present them as default-deny advice.
11. **Attribute:** record whether the user applied, ignored, rejected, or used
    the advice only as context.
12. **Refresh:** invalidate only the evidence domain that actually changed.

## Examples of real useful learnings available in this repository

These are candidate formulations. They still require current evidence review
before capture or promotion.

| Source | Useful candidate | Why it helps |
|---|---|---|
| Issue 4 | Check the latest approved anchor before falling back to repository role classification at write time. | Prevents an approved configuration owner from being rejected as `unknown`. |
| Issues 13/13a | Resolve the latest approved anchor version; never read a frozen `approved-v1.json` as current truth. | Prevents corrected scope from remaining stale across closure and harness paths. |
| Issues 21/21.7 | A correction plan needs a reproduced failing premise and symptom-specific proof at the real call site. | Stops no-op implementation plans for behavior already present. |
| Issues 23/45 | Select current evidence per approved proof binding and show older attempts as history. | Prevents an old failure from hiding a newer compatible pass. |
| Issues 25/28 | Register a new proof-only test before activation through a proof update; do not pass a missing test through `--changed`. | Avoids scope and closure drift for new tests. |
| Issue 29 | Material accepted answers must project through a validated correction artifact into canonical requirements and proof. | Prevents saved answers from leaving the original plan unchanged. |
| Issues 31/43 | Bind proof per requirement with path, exact command, tier, asserted behavior, and source answer ID. | Prevents a valid global command from becoming unresolved or attaching to unrelated requirements. |
| Issues 32/44/48/49 | A rejected or revised plan must render the latest pending canonical proposal and preserve prior revision history. | Prevents users approving stale v1 or losing material correction content. |
| Issue 37 | Validation-only closure must prove the declared validation artifact and must not fabricate or demand a source-edit receipt. | Keeps closure policy aligned with request authority. |
| Issues 39/50 | Declared request mode and validated host contract must participate before classifier and scope routing. | Prevents validation wording from becoming implementation scope. |
| Ground Rule 16 | A proof candidate must import and collect at least one test; a test-like filename is insufficient. | Prevents zero-test helpers from appearing as executable proof. |
| Playbook evidence tiers | Register exact proof before activation and run it through managed evidence for trusted closure. | Prevents correct code closing as evidence-incomplete. |

These candidates are more useful than the current generic closure warning
because each has a recognizable trigger, a bounded action, and a proof or
policy boundary.

## Confidence and usefulness

Confidence and usefulness answer different questions.

- **Confidence:** how strongly current evidence supports the advice.
- **Usefulness:** how often compatible use was associated with a successful
  outcome.
- **Observation count:** how many compatible observations exist.

Recommended confidence inputs:

| Evidence | Effect |
|---|---|
| User narration without repository evidence | Candidate only; no confidence increase. |
| Reproduced symptom | Supports problem signature, not the fix. |
| Focused red-to-green proof | Strong support for the bounded fix. |
| Public-route behavior proof | Stronger than a direct helper-only test. |
| Independent compatible successful uses | Small bounded usefulness increase. |
| User acceptance without proof | Context only. |
| Rejection, stale evidence, or policy conflict | Challenge, demote, suppress, or revoke. |

No record should become trusted merely because it has many observations.

## Freshness improvements

Freshness must be evidence-fragment aware.

1. A `path#line=N` source reference fingerprints and rechecks the referenced
   event, not the entire append-only file.
2. Appending a later event must not stale unchanged earlier events.
3. Mutable source, test, policy, ownership, manifest, graph, and schema files
   retain content-based invalidators.
4. A learning tied to a public command becomes stale when that command or its
   proof binding changes.
5. A learning tied only to a general policy rule should not inherit dozens of
   unrelated source paths from observation context.
6. Retrieval and refresh sweep must use the same comparison implementation and
   produce the same reason codes.

## Retrieval improvements

Normal retrieval should show at most three records and explain:

- why each record matched;
- current confidence and usefulness;
- exact evidence and freshness state;
- the proposed advice;
- what the advice cannot authorize; and
- the decision choices: apply, advisory, ignore, reject, or request refresh.

When no record is current and sufficiently relevant, TailTrail should remain
quiet. A large stale inventory is a maintenance concern, not task guidance.

## Meta Harness coverage

Meta Harness should audit the learning pipeline with these checks:

1. Every promoted learning has current evidence and a reproducible proof or an
   explicitly documented non-executable policy basis.
2. Every fixed high-impact issue has a disposition: reusable learning,
   playbook-only technique, policy rule, or documented reason not to capture.
3. Open issues are not emitted as positive guidance.
4. Candidate advice does not assert a root cause beyond its evidence.
5. Duplicate rate, missing-command rate, and generic-advice rate remain below
   agreed thresholds.
6. Retrieval never includes stale, terminal, sensitive, conflicting, or
   out-of-frame records.
7. Use receipts cannot raise confidence without compatible closure outcomes.
8. Host and TailTrail actions remain separately attributable.

## Reporting improvements

The normal Completion Report should summarize learning maintenance:

```text
Learning maintenance
- Current reusable matches: 0
- Stale candidates: 69
- Duplicate groups: 1
- Effect on this closure: none
- Next action: review the detailed learning inventory
```

The verbose report should retain IDs, reason distribution, canonical and
replacement relationships, source-run count, and exact governance commands.
Successful closure must not be visually dominated by a long list of stale IDs.

## Delivery phases

### Phase 1: Canonical duplicate consolidation

- Aggregate equivalent advice across contextual tags and paths.
- Preserve observation and source-run lineage.
- Append canonical amendment and supersession transitions.
- Keep confidence conservative.
- Prove rejection of cross-class and different-advice merges.

### Phase 2: Fragment-aware freshness

- Fingerprint exact append-only source fragments.
- Preserve whole-file invalidation for mutable source.
- Add append-without-stale and edited-line-stales regressions.

### Phase 3: Structured issue-to-learning candidates

- Add a sanitized extractor for fixed issue records and verified playbook
  entries.
- Require symptom, action, evidence, preservation, and freshness fields.
- Produce candidates only; no automatic promotion.

### Phase 4: Specific closure learning

- Replace the generic incomplete-closure sentence with stable categorical
  patterns linked to exact requirement and proof state.
- Deduplicate before capture.
- Record successful recovery as separate evidence.

### Phase 5: Meta Harness governance

- Audit capture coverage, evidence quality, duplicate rate, false advice,
  privacy, freshness, and retrieval behavior.
- Require explicit resolution for failed governance checks.

### Phase 6: Operator and report experience

- Show bounded normal summaries and complete verbose evidence.
- Provide one exact action for consolidate, revalidate, suppress, challenge,
  supersede, or revoke.

## Acceptance criteria

1. Equivalent observations produce one current canonical learning.
2. Raw history remains byte-preserved and append-only transitions retain every
   prior learning ID.
3. Canonical observation count and unique source-run lineage are correct.
4. Confidence does not rise merely due to consolidation.
5. Every reusable learning contains a specific trigger, action, evidence, and
   freshness boundary.
6. Fixed issue knowledge can be accounted for without copying the issue log.
7. Open or unverified findings never become positive guidance.
8. Retrieval remains advisory, default-deny, and subordinate to current
   authority and evidence.
9. Normal reporting is concise; verbose reporting retains full audit detail.
10. Meta Harness can detect missing capture, weak evidence, unsafe content,
    duplicates, stale advice, and behavior that diverges from this contract.

## Non-goals

- Training a model from repository history.
- Copying issue logs, chats, prompts, source, or test output into learning
  content.
- Automatically promoting candidates because they are frequent.
- Letting learning decide scope, approval, implementation, proof, or closure.
- Replacing issue tracking, playbook guidance, managed evidence, or policy.
- Treating every issue as reusable knowledge.
