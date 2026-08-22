# Optional Enterprise Adapter

The Phase 12 adapter is optional, provider-neutral, and disabled by default.
TailTrail's local ownership binding, approved anchor, journal, projection,
approval records, evidence, recovery state, and completion receipt remain the
only canonical workflow truth.

## Entry and activation

An administrator records a closed policy containing evidence of long-running
or cross-repository need, approved operational ownership, threat model,
tenancy, retention, backup, disaster recovery, audit, availability, and cost
controls, tenant/actor/repository allowlists, and bounded limits. Entry remains
blocked until the live Phase 11 release gate passes. Recording the policy does
not activate an adapter; activation is a second explicit per-workflow approval.

## Transport and isolation

The included local reference adapter implements the provider-neutral
`StateStore` protocol for deterministic conformance. A provider adapter may
implement the same metadata-only get, put, list, and append operations after a
separate security and operations review. TailTrail makes no provider call.

Every ingested event must bind the exact workflow, run, tenant, authorized
actor, current lease, fencing token, sequence, canonical local artifact
reference, and artifact hash. Failover acquires a higher lease epoch, making
older fencing tokens invalid. Duplicate event IDs are idempotent only when the
entire receipt is identical.

Cross-repository parent/child links are identity-only, read-only references.
They never grant approval or write authority in either repository.

## Recovery, migration, and rollback

Backups are bounded metadata manifests over canonical and enterprise artifacts.
Restore validation is read-only and never overwrites canonical history or
project files. Migration requires a verified backup and the exact current plan
fingerprint. Enterprise continuation remains a shadow of local truth. Rollback
requires the exact applied migration fingerprint and validates the preserved
backup before returning continuation to local mode.

There is no background retention cleanup, automatic migration, raw source/log
upload, autonomous agent channel, execution retry, provider requirement, or
automatic code/publish/deploy action.
