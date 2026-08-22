# Durable Workflow Runtime Release And Migration

Existing TailTrail commands and `.tailtrail` artifacts remain authoritative.
Phase 11 does not automatically migrate, rewrite, delete, upload, or reinterpret
old workflow history. A newer runtime may read an older artifact only through an
explicit compatible adapter that preserves ownership, approval, evidence,
privacy, freshness, recovery, and completion boundaries.

`--no-workflow` remains the documented compatibility escape hatch. Passing the
Phase 11 release gate does not remove it: retirement requires a separate exact-
gate-fingerprint approval followed by an independently reviewed release change.
No compatibility aliases are currently registered. Any future alias must map to
one canonical stage and cannot bypass authority.

Retention remains configurable and count-based. Cleanup is explicit and manual,
has no background deletion or upload, removes only an exact terminal workflow
candidate, and preserves canonical run history.

## Rollback

If a workflow-default rollout fails, restore compatibility by retaining or
restoring `--no-workflow`, keeping existing commands and artifacts untouched,
disabling only the new default routing, and re-running host, scenario, template,
privacy, migration, and release-gate validation before another rollout. Never
roll back by deleting or rewriting historical `.tailtrail` evidence.
