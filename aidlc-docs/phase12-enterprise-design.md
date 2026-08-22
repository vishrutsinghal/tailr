# Deferred Phase 12 Enterprise Adapter Design

## Ownership and truth

The local TailTrail ownership binding, approved anchor, append-only journal, projection, evidence, and completion receipt remain canonical. Enterprise state stores sanitized references, hashes, categorical events, leases, links, and projections only. An enterprise adapter cannot approve, execute, recover, close, publish, or replace local history.

## Components

- `enterprise.py`: entry policy, activation binding, parent/child links, status, and read-only observability.
- `enterprise_transport.py`: pluggable state-store protocol, local reference adapter, lease/fencing control, explicit event receipt ingestion, and deterministic replay.
- `enterprise_recovery.py`: backup manifest, restore validation, migration planning/activation, rollback, and conformance evaluation.

All reference implementations are local and dependency-free. Provider implementations must implement the same closed contracts and supply their own separately reviewed transport, authentication, encryption, availability, and operations design.

## Safety sequence

1. Record an approved, privacy-safe enterprise entry policy.
2. Re-evaluate it together with the live Phase 11 release gate.
3. Explicitly activate one canonical local workflow for one tenant and adapter.
4. Acquire a bounded lease; every event carries the exact current fencing token.
5. Ingest only ordered, idempotent, sanitized metadata receipts.
6. Derive read-only observability and replay projections.
7. Create and verify backup manifests before restore or migration.
8. Require exact-fingerprint approval for migration and rollback.

## Failure behavior

Expired leases, stale fencing tokens, duplicate IDs with different payloads, sequence gaps, unauthorized actors, tenant mismatch, cross-run identity, changed canonical ownership, invalid backups, missing controls, stale plans, and cost-limit breaches all block without modifying canonical workflow state.
