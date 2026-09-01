# PM-L3 — Use Receipts And Closure Attribution Design

Status: implemented

## Architecture

```text
Learning V3 current record
        +
saved PM-L2 use proposal
        +
approved Planning Lock / requirement anchor
        |
        v
explicit decision -> run-local append-only use-receipts.jsonl
        |                         |
        |                         +-> read-only project utility projection
        v                                      |
canonical Completion Report                    v
requirements + drift + Harnesses +     next PM-L2 applicability score
failures + validation
        |
        v
append-only observed attribution (causal_claim=false)
```

The canonical stream is
`.tailtrail/runs/<run-id>/learning/use-receipts.jsonl`. Its fact owner remains
the Durable Workflow Runtime. `scripts/learning-use-receipt.py` is the single
contract writer; `scripts/completion-report.py` calls that writer during
canonical closure. Existing workflow candidate links remain source-by-reference
artifacts and are not converted into decisions.

## Event lifecycle

One deterministic receipt identity is derived from run ID, learning ID,
sorted requirement UIDs, and decision type. A `decision` event references the
exact saved proposal fingerprint and V3 record. An `attribution` event follows
the latest event for that receipt and references a fingerprinted Completion
Report evidence projection. Repeating the same decision or completion
fingerprint reuses the current event. A revised decision or changed evidence
appends; no event is edited.

The closed schema is `schemas/learning-use-receipt-event.schema.json`. Runtime
validation additionally enforces contiguous stream sequence, global digest
predecessor, per-receipt lifecycle predecessor, and the current repository
frame while holding the run-local stream lock.

## Attribution and utility

| Observed association | Base delta |
| --- | ---: |
| potentially-helped | +2 |
| neutral | 0 |
| insufficient | -3 |
| possible-harm | -6 |
| rejected-by-evidence | -4 |
| stale | -5 |
| inconclusive | 0 |

Drift and unresolved failures outrank passing evidence. A complete linked
requirement plus passing validation may be labeled `potentially-helped`; this
is still association, not causality. Applied/advisory/ignored/rejected/stale
remain explicit decisions rather than inferred behavior.

Security, dependency, release, and data-migration decision domains are capped
at ±5 per learning/domain. Other domains are capped at ±10. The project-wide
active-attribution projection is capped at ±20 per learning before it is added
to PM-L2 applicability. Only the latest attribution after the latest decision
counts, so revised closure does not double-count history.

## Interfaces

```bash
tailtrail learn receipt record --root . --run-id <run> --learning-id <id> \
  --decision applied --decision-type validation --requirement-uid <uid> \
  --rationale "Selected for the focused validation path" --approved
tailtrail learn receipt show --root . --run-id <run>
tailtrail learn receipt validate --root . [--run-id <run>]
tailtrail learn receipt attribute --root . --run-id <run> \
  --completion-report <report.json> --approved
```

Normal closure does not require the manual `attribute` command: the canonical
Completion Report appends/reuses attribution automatically and renders the
learning, linked requirements, decision type/state, evidence association, and
bounded utility delta. The manual command exists for deterministic recovery or
inspection of an already saved Completion Report.

## Failure and privacy boundaries

- A missing approved lock/anchor, unknown UID, missing proposal, changed V3
  record, blocked match, unsafe evidence path, malformed event, broken digest,
  or cross-project frame stops the write/read.
- Receipt data is sanitized metadata only. Raw source, prompts, logs, user/
  customer identity, credentials, and secrets are prohibited by contract and
  runtime validation.
- Current source, policy, tests, CI, scanner, guardrail, and explicit user
  evidence always override receipt utility.
- PM-L3 does not promote, amend, revoke, refresh, or create conflicts. Those
  lifecycle authorities remain with Learning Governance and PM-L4.
