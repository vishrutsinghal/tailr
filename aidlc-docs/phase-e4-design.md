# Enterprise Phase E4 Design

## Architecture

`adapters/host-compatibility-v1.json` is the versioned data authority.
`tailtrail.hosts.contracts` validates and exposes it. The E3 payload catalog
consumes its exact Core file list; `tailtrail.hosts.diagnostics` consumes the
same first action, markers, capabilities, detection method, qualification, and
receipt boundary. This removes independent installer and first-run mappings.

The E3 ownership manifest records `adapter_version`. A metadata-only adapter
migration creates a normal transaction even when file hashes are unchanged,
and records `adapter:<old>-><new>`. Rollback restores the prior manifest.

## Diagnostics

`tailtrail doctor --host` first validates owned-file hashes, then checks:

1. non-empty required host files;
2. exact Core manifest membership;
3. host-specific composition markers;
4. installed/current adapter version;
5. truthful host version detection;
6. qualification, support, capability, first-action, runtime, and receipt
   preparation boundaries.

Command detection is bounded to five seconds and does not access a network.
Copilot requires host-reported version metadata instead of guessing.

## Safety and privacy

Repository-only installation remains the default. The contract requires
separate approval for global settings, network activity, and account changes.
Runtime bundle preparation contains contract metadata only; receipt validation
continues to reject raw prompts, source, secrets, and unlinked evidence.

## Failure and recovery

Missing files, drift, stale metadata, unknown hosts, unsafe paths, conflicts,
and unsupported claims fail closed. All file and metadata changes reuse E3
staging, verification, automatic restoration, ownership, retention, and
rollback behavior. No dependency is added.
