# Deferred Phase 10 Requirements

The canonical 20-case matrix in `DURABLE-WORKFLOW-RUNTIME-REVISED.md` is
mandatory and may not be reduced. It covers forged/stale/cross-boundary
authority, storage corruption, terminal transitions, unsafe paths, private or
oversized content, untrusted command text, prohibited retries/providers,
over-broad session approval, unknown contracts, cross-workflow artifacts,
rollback claims, false evidence/completion, unmeasured token claims,
learning/evaluation privacy, and Start/host stop-rule preservation.

Governance requirements are strict registry ownership and duplicate-script
checks, adapter synchronization, installed-pack verification, schema/command
documentation drift checks, count-based local retention, explicit manual
cleanup only, no background deletion/upload, categorical denial audit records,
and no dependency change without the existing Dependency Gate.

Acceptance: all adversarial cases fail closed without project or external
mutation, privacy inspection reports only categorical local references, manual
cleanup is fingerprint-bound and terminal-only, and all strict governance
checks pass.
