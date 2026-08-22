# Deferred Phase 9 Implementation Plan

- Reuse canonical ownership, compiler, task-scope freshness, append-only storage, projection, event ledger, MCP bridge, installer inventory, and host conformance helpers.
- Store supplied CI results as sanitized local artifacts plus a fingerprinted per-workflow index.
- Treat the CI policy as exact continuation authority, never execution authority.
- Keep terminal stages monotonic and frozen prerequisites authoritative.
- Leave canonical recovery and closure untouched; failure/cancellation stops at failed/blocked metadata state.
- Add no dependency and perform no external provider operation.

# Deferred Phase 12 Implementation Plan

- Reuse canonical ownership, compiler, storage replay, evidence, release gate, privacy validation, atomic JSON, run locks, event ledger, MCP bridge, installer, registry, and host generation.
- Implement a provider-neutral metadata state-store protocol and dependency-free local reference adapter.
- Require approved entry controls plus a passing Phase 11 gate, then separate per-workflow activation.
- Enforce tenant/actor/repository authorization, monotonic lease epochs, fencing tokens, sequence, idempotency, linked hashes, and bounded event/backup costs.
- Keep parent/child links and centralized observability read-only and sanitized.
- Require verified backup manifests and exact fingerprints for migration and rollback; never overwrite canonical local history.
- Add closed CLI/MCP/schema/package/docs/host surfaces and deterministic isolation, replay, failover, recovery, privacy, cost, migration, and rollback proof.
- Add no dependency and perform no provider, model, queue, database, container, upload, background worker, code retry, publish, or deployment operation.
