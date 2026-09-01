# PM-L2 — Navigator Retrieval And Conflict Gate Design

Status: implemented
Requirements: `aidlc-docs/phase-pm-l2-requirements.md`

## Flow

1. Navigator classifies the task and resolves changed/target paths.
2. `scripts/learning-retrieval.py` verifies the Learning V3 repository frame and builds a closed task frame.
3. The gate reads terminal-aware current V3 records, never raw prompt/source/log history.
4. Applicability scoring uses task type, tags, paths, requirement IDs, confidence, and curated status. At least one explicit applicability signal is mandatory.
5. Freshness checks apply lifecycle, revalidation deadline, refresh actions, append-only provenance, explicit source existence, privacy, and applicability exclusions.
6. Reserved `learning:<id>` exclusions create a deterministic symmetric contradiction edge; both candidates are blocked.
7. Eligible results sort by applicability, confidence, and learning ID and stop at three.
8. Navigator renders only `proposed` or `blocked`; `quiet` produces no learning section. Proposed advice is visibly marked as not instruction and defaults to `do-not-use`.
9. Start posture and `tailtrail next` propagate the proposal's pending decision;
   legacy graph matches cannot bypass the V3 proposal gate.

## Contracts And Ownership

- Canonical facts: `.tailtrail/learning-v3/events.jsonl`, owned by Learning Governance.
- Retrieval implementation: `scripts/learning-retrieval.py`, owned by Navigator as a read-only consumer.
- Output contract: `schemas/learning-use-proposal.schema.json`, closed and capped at three.
- Compatibility graph search remains metadata for refresh awareness; it is not implementation authority and its candidate text is no longer rendered by Navigator.
- No proposal is persisted, so PM-L2 cannot be confused with the PM-L3 use-receipt stream.

## Failure Posture

Corrupt V3 state, invalid refresh metadata, changed reference fingerprints,
expired revalidation, missing explicitly scoped files, non-normal sensitivity,
exclusions, and contradictions fail closed. Blocked rows contain identifiers,
reasons, and invalidator results but intentionally omit summary/advice content.

## Validation

`tests/test_learning_retrieval.py` is the focused runnable contract. It covers
mandatory framing, deterministic ranking/cap, quiet Lite behavior, stale and
suppressed records, explicit contradictions, exclusions, privacy, source
invalidators, CLI routing, Navigator rendering, and schema/package presence.
