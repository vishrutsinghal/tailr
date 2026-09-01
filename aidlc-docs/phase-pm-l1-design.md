# PM-L1 Learning V3 Contract And Migration Design

## Canonical architecture

`.tailtrail/learning-v3/events.jsonl` is the canonical append-only store for
candidate and curated-learning facts. `scripts/learning-v3.py` is its only
physical mutation authority. Learning Agent, closure learning, promotion, and
the legacy curated command delegate to that authority.

Each record is a complete snapshot with these closed domains:

- learning class;
- sanitized provenance and relative evidence references;
- pseudonymous repository frame, tasks, tags, relative paths, requirements,
  and exclusions;
- freshness status, invalidators, revalidation point, and stale condition;
- confidence, observations, use count, curation, and an explicit no-causality
  flag;
- compact sanitized summary and advice;
- privacy declarations;
- lifecycle operation and exact predecessor;
- global sequence and SHA-256 append chain.

Create and amend remain current. Supersede names an existing, different current
replacement. Supersede and revoke are terminal. Validation recomputes every
digest, sequence, predecessor, status, project frame, and privacy boundary
before any append.

## Compatibility and migration

Existing `.tailtrail/learning-events.jsonl` and `.tailtrail/learnings.md` files
remain present as compatibility projections. They are not the canonical V3
owner and are not rewritten during migration. Compatibility reads project the
latest active V3 snapshot over its referenced legacy event, include legacy
events that have not been migrated, and omit terminal V3 facts.

Migration reads each legacy JSONL line deterministically. Only a non-empty,
normal-sensitivity candidate with no raw-prompt flag and no sensitive pattern
is eligible. V3 stores the sanitized candidate, safe relative applicability,
the source line, and a SHA-256 fingerprint; it does not copy the repository
name, prompt summary, solution, logs, source, or identities. Repeated migration
resolves to the same learning ID and does not append a duplicate record.

## Commands and failure behavior

`tailtrail learn v3 validate|state|migrate|amend|supersede|revoke` exposes the
contract without adding a top-level command. Migration writes, supersession,
and revocation require explicit approval. Dry-run migration is read-only.
Malformed JSON, broken chains, invalid transitions, unsafe paths, sensitive
text, cross-project records, and destructive compatibility behavior fail
closed with no new append.

PM-0/PM-L0 maturity validation now also verifies the V3 schema identity,
closed posture, required domains, implementation presence, and canonical
candidate/curated ownership.
