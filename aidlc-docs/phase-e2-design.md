# Phase E2 Design — Self-Contained Package

## Architecture

`tailtrail.kernel` owns interpreter compatibility and chooses exactly one
runtime root: installed package resources, or an explicit
`TAILTRAIL_SOURCE_COMPAT_ROOT` set by `tailtrail_cli.py`. There is no current-
working-directory or parent search. `tailtrail.resources` owns safe relative
resource resolution and complete SHA-256 verification. `tailtrail.cli` owns
stable package commands, JSON containment, categorical errors, and dispatch to
the packaged command implementation. The legacy top-level launcher is a thin
source adapter.

The stable Python API is intentionally limited to the names exported by
`tailtrail.__init__`. Existing script modules remain command implementation
details. This avoids promising hundreds of historical modules while retaining
all current CLI behavior inside the artifact.

## Artifact construction

`package-manifest.json` is the package source contract. `setup.py` extends the
standard setuptools build step to copy exact root resources and selected
resource directories below `tailtrail/`, rejects symbolic links, and emits
`package-integrity.json`. `MANIFEST.in` is explicit at the repository root and
prunes tests and local/user-owned files from the sdist. The release proof opens
archives as data; it does not import or execute them while checking names,
required members, digests, local-state fragments, and secret-like names.

## Runtime and failure behavior

The console verifies package integrity before dispatch. Missing/corrupt package
content and unsupported Python return exit 3. Validation returns 1, usage or
rejected input returns 2, and unexpected package failures are reserved as 70.
Native JSON is preserved. Legacy text produced for an explicit JSON request is
captured into one `tailtrail-command-result` object; subprocess output cannot
leak a second JSON document.

Packaged-state migration version 1 is the 0.6 baseline. The migration helper
rejects invalid versions, downgrades, and unknown future targets. No migration
is executed because no earlier packaged-state version exists.

## Proof topology

The maintained test builds wheel and sdist with a fixed source epoch, inspects
them, installs the wheel into a new virtual environment, creates a separate Git
project, and runs planning through closure. It captures and applies a real Mode
B recovery before reapplying the intended change and recording evidence. The
sdist is built and installed into an isolated target. CI repeats the suite on
3.12 and 3.13 and performs a named artifact inspection gate on 3.12.
