# Deferred Phase 12 Requirements

Status: approved by the user's explicit end-to-end implementation request on 2026-08-21.

## Functional requirements

1. Keep the local JSON runtime supported, canonical, and default.
2. Require affirmative evidence for long-running or cross-repository need and separately approved operational ownership, threat model, tenancy, retention, backup, disaster recovery, audit, availability, and cost controls before enterprise activation.
3. Provide a dependency-free pluggable state-store and explicit receipt-driven event-transport interface; do not contact or require a provider.
4. Preserve canonical workflow/run ownership and support explicit parent/child identities across repositories without granting cross-repository write authority.
5. Provide a centralized, sanitized, read-only observability projection.
6. Enforce tenant and actor authorization, monotonic concurrency leases, fencing tokens, event sequence, idempotency, and cross-workflow/run boundaries.
7. Provide explicit count-based retention metadata, backup verification, restore validation, and disaster-recovery readiness without background deletion or canonical-history replacement.
8. Provide approved migration and rollback between local and enterprise adapter modes. Migration must never make enterprise state canonical or auto-upload local artifacts.
9. Expose closed CLI and MCP inspection/control surfaces, schemas, registry, installed-pack, generated host, documentation, and drift checks.
10. Prove isolation, failover, replay, migration, rollback, cost controls, privacy, approval, and canonical closure convergence with deterministic tests.

## Explicit exclusions

- No autonomous free-form agent communication.
- No mandatory model API or provider call.
- No hidden/background execution or deletion.
- No raw workflow, source, prompt, command, or log upload.
- No automatic code, publish, or deployment retry.
- No mandatory Redis, database, queue, container, or Kubernetes dependency.

## Acceptance boundary

Implementation completion means the optional adapter surface exists and fails closed. It does not mean the enterprise adapter is activated in this repository. Activation requires a passing Phase 11 release gate plus the complete approved entry policy, and remains a separate per-workflow approval.
