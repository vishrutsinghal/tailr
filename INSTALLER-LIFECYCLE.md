# TailTrail Transactional Installer Lifecycle

This is the E3 contract for projecting TailTrail into a repository. Every
Codex, Copilot, and Claude lifecycle command uses `tailtrail.install`; host
qualification and real-host observations remain separate E4-E5 gates.

## Safety model

- `InstallPlan` v1 is deterministic for the same package, target state, host,
  profile, and operation. `--dry-run` creates no files or directories.
- Targets must exist, be writable directories, and must not be filesystem
  roots or symbolic links. Managed relative paths reject traversal and
  symbolic-link parents.
- Existing files without a matching ownership-manifest hash are conflicts.
  They are preserved unless `--force` is explicitly supplied; forced changes
  are backed up before replacement or removal.
- Files are copied into per-transaction staging, SHA-256 verified, and moved
  into place with atomic replacement. The completed ownership manifest records
  the package version, host, profile, paths, hashes, sizes, transaction,
  migrations, backups, and owner.
- Any application or verification exception restores the preceding bytes and
  manifest. A process kill or power loss leaves durable `prepared`, `applying`,
  or `verifying` state; the next mutation or `tailtrail recover` restores it.
- Verification and uninstall trust the installed manifest, never filename
  guesses. Modified managed files block update, rollback, and uninstall unless
  a reviewed forced operation preserves them in a backup.
- The latest five completed/recovered transactions per host are retained.
  Staging is removed after success. Unrelated target files are never included
  in cleanup.
- Extended payloads use one immutable versioned common runtime and one small
  launcher per host. A common path referenced by another current host manifest
  is preserved during update, uninstall, and rollback.

## State layout

```text
.tailtrail/install/
  lifecycle.lock
  journal-v1.jsonl
  manifests/<host>.json
  payload/common/<version>/...
  payload/<host>/scripts/tailtrail.py
  transactions/<transaction-id>/
    plan.json
    state.json
    before-manifest.json
    after-manifest.json
    backup/<managed paths>
```

The lock is process-owned and stale locks are recoverable. Ownership manifests
are independent per host, allowing host surfaces to coexist without conflating
their verification or uninstall status.

## Commands

```bash
tailtrail install --host codex --profile core --target . --dry-run
tailtrail setup --host codex --profile core --target .
tailtrail install --host codex --profile core --target .
tailtrail verify --host codex --target .
tailtrail doctor --host codex --target .
tailtrail status --host codex --target .
tailtrail update --host codex --target . --dry-run
tailtrail update --host codex --target .
tailtrail repair --host codex --target .
tailtrail rollback --to <transaction-id> --target .
tailtrail uninstall --host codex --target . --dry-run
tailtrail uninstall --host codex --target .
tailtrail recover --target .
```

Use `--format json` for the stable `tailtrail-install-result`,
`tailtrail-install-results`, or `tailtrail-install-error` envelope. Success is
exit `0`, CLI usage is exit `2`, and validation/conflict/unavailability is exit
`3`. Text is compact by default. Compatibility-controlled lifecycle JSON stays
full; `--compact` returns counts and `plan_summary`. Guided setup JSON is compact
by default and `--verbose` restores exact path lists and the full plan.
