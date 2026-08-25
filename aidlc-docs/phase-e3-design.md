# Enterprise Phase E3 Design

## Boundary

`tailtrail.install` is the single lifecycle authority. `catalog.py` selects
host/profile payloads, immutable dataclasses describe plans/results, `engine.py`
owns validation and state transitions, and `cli.py` owns stable rendering and
exit behavior. `scripts/installer.py` is a thin package compatibility launcher.
Historical host scripts retain source/inventory helpers needed by packaging,
but their executable `main` paths delegate to this engine.

## Transaction protocol

1. Validate target and state paths.
2. Acquire an exclusive process lock; remove only a demonstrably stale lock.
3. Recover any durable incomplete transaction.
4. Build a hash-based plan and stop on conflicts.
5. Create transaction state, plan, backups, and a journal `prepared` event.
6. Stage each file, verify SHA-256, atomically replace, and durably update the
   created/touched set.
7. Apply safe manifest removals while preserving modified files.
8. Atomically write the ownership manifest, verify installed hashes, then mark
   the transaction complete.
9. On failure, restore backups/created paths and the preceding manifest. On an
   unclean stop, the next locked operation performs the same restoration.

## Trust boundaries

Manifest paths are revalidated before every filesystem access. Symlink parents,
filesystem-root targets, malformed manifests, concurrent writers, missing or
modified files, and conflicting rollback state fail closed. Forced operations
do not waive backup. No runtime/build/test dependency is added.

## Phase boundary

E3 proves the shared lifecycle and current host catalogs. E4 still owns exact
host composition, precedence, native first actions, diagnostics, and portable
receipt qualification. E5 still owns Windows/macOS/Linux runner evidence.
