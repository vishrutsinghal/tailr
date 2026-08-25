# Enterprise Phase E3 Requirements

Authority: `ENTERPRISE-READINESS-ASSESSMENT.md` Sections 15.5, 16.1, and E3.
Approval: the user's explicit end-to-end E3 implementation request on
2026-08-22 approves requirements, workflow, and implementation. Closeout is
evidence-gated.

## E3-R1 — One installer authority

All Codex, Copilot, and Claude install and update entry points use one
package-owned engine and versioned plan/ownership/journal schemas. Compatibility
wrappers may translate arguments but may not maintain an independent write
path.

## E3-R2 — Safe deterministic planning

Detect host, profile, target, Python/package version, existing manifest,
conflicts, modified managed files, and desired additions/removals. Reject
missing, inaccessible, root, traversal, and symlink targets/paths. A dry run
must be deterministic and create no state.

## E3-R3 — Transactional application and recovery

Stage and hash every payload; durably journal before mutation; back up replaced
bytes; use atomic file replacement; verify from installed bytes; automatically
restore on apply/verification failure; and recover incomplete durable
transactions after unclean termination.

## E3-R4 — Complete lifecycle

Provide install, verify, doctor, status, update, repair, recover, rollback, and
uninstall with stable text/JSON/exit behavior. Reinstall and repeated lifecycle
operations are idempotent. Core-to-Extended and supported-version updates are
manifest deltas, not deletion/re-copy guesses.

## E3-R5 — User work and retention

Never silently replace or delete unrelated/user-modified files. Default to a
conflict; explicit force must first preserve bytes. Retain five recent
transactions per host, remove completed staging, and prune only installer-owned
transaction data.

## Acceptance matrix

Positive and negative proof must cover dry run, new install, all three host
catalogs, reinstall, Core-to-Extended, managed update, conflict, force backup,
failed verification, corrupt staging, unclean interruption/recovery, repair,
rollback, uninstall, repeated uninstall, unsafe/symlink/inaccessible target,
live/stale lock, JSON/text/exit contracts, retention, installed-wheel execution,
and the complete supported Python matrix.
