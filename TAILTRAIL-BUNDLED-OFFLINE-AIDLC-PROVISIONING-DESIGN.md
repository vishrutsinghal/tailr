# TailTrail Bundled Offline AIDLC Provisioning Design

## Status

- **Document status:** proposed design for review
- **Implementation status:** not implemented
- **Implementation valuation:** high-complexity, release-sensitive product work spanning supply-chain identity, packaging, source-checkout behavior, schema migration, runtime resolution, filesystem transactions, three host adapters, and public CLI/MCP routes. It is not a packaging-only change.
- **Decision:** Full AIDLC must be a normal TailTrail capability backed by a pinned, integrity-verified bundle shipped with TailTrail. Customers must not separately install the official rules before using Full mode.
- **Primary user outcome:** `tailtrail start ... --aidlc full` works without network access when the installed TailTrail package is intact, remains in Full mode, and fails closed with a precise recovery action when either the bundle or the destination is unsafe.

## Executive summary

TailTrail currently contains an `aidlc-rules/` directory, but the release and runtime paths do not treat it as a complete trusted product asset. The release manifest excludes it, the source-distribution manifest does not include it, the normal package manifest does not select it, and Full-mode detection accepts only a separately installed project-local manifest at `.tailtrail/official-aidlc/manifest.json`. The remaining installer downloads the official pack from the network. Consequently, an explicit Full-mode request can report that the official pack is not installed and route to Lite even though the product is intended to bundle AIDLC.

The permanent solution has one authenticated release trust anchor, two nested content-integrity layers, and one shared resolver:

1. TailTrail authenticates the released wheel or source distribution through the established release identity chain: GitHub/Sigstore attestation, the authenticated artifact digest, and the publication receipt. A detached checksum or a manifest stored inside the package is not publisher authentication by itself.
2. TailTrail ships a complete pinned official AIDLC bundle, its MIT-0 license, provenance, version metadata, and a release-authored SHA-256 manifest in source distributions and wheels.
3. TailTrail's normal `package-integrity.json` protects the exact packaged bundle inventory, while the bundle manifest protects the official pack inventory and provenance. Both must reject missing and unexpected files, not only hash mismatches for listed files.
4. Source checkouts use a separate repository-root provider and are labeled `development-local` unless their source identity is authenticated independently. They must never be reported as an authenticated release merely because local hashes match.
5. A single offline resolver verifies the applicable trust posture and integrity, then atomically projects the verified bundle into content-addressed project-managed state when Full mode first needs it.
6. Every Full-mode consumer uses the same resolver receipt. An explicit Full request never silently becomes Lite.
7. Missing, altered, stale, incompatible, incomplete, or unsafe state fails closed without overwriting or deleting evidence.

This design preserves support for explicitly supplied enterprise or external packs, but makes them advanced overrides rather than prerequisites for normal Full mode.

## Problem statement

The intended product contract is:

1. Full AIDLC is bundled and integrated with TailTrail.
2. A user does not separately install the official AIDLC pack.
3. A normal TailTrail installation contains the pinned rules, version, license, provenance, and SHA-256 integrity metadata.
4. Provisioning works without network access.
5. The public Full-mode route consumes the bundled pack and never silently downgrades an explicit Full request to Lite.
6. Codex, Copilot, and Claude use the same supported integration.
7. Missing, altered, stale, incompatible, incomplete, or unsafe state fails closed.
8. Source checkout, built wheel, installed source distribution, public routes, host projections, and negative integrity cases provide executable proof.

The current implementation does not satisfy that contract. It implements a separately installed external-pack model.

## Verified current state

The following findings were verified against the repository on 2026-11-03.

| Surface | Current behavior | Consequence |
| --- | --- | --- |
| `aidlc-rules/` | Contains 31 files and a `VERSION` file whose current value is `0.1.8`; it does not contain its own `manifest.json` or `LICENSE` at the bundle root. | The directory is not a complete independently verifiable official pack. Its local version cannot safely be treated as the upstream official revision. |
| `release-manifest.json` | Lists `aidlc-rules/` under candidate exclusions. | Release selection deliberately omits the rules. |
| `package-manifest.json` | Does not list `aidlc-rules` under required directories. | `setup.py` does not copy the rules into the wheel's package-owned resource inventory. |
| `MANIFEST.in` | Recursively includes `aidlc/`, but not `aidlc-rules/`. | A source distribution is not required to carry the official rule bundle. |
| `setup.py` | Copies only the files and directories selected by `package-manifest.json` into the wheel and generates `package-integrity.json`. | The packaging engine can protect the bundle, but only after the bundle joins the package manifest. |
| `scripts/aidlc-official-detect.py` | Looks for `.tailtrail/official-aidlc/manifest.json` by default and restricts pack paths to the target repository root. | It cannot discover a package-owned bundle installed in Python's site-packages directory. |
| `scripts/aidlc-official-install.py` | Downloads a pinned release archive and license from the official network source. | The existing installation route is not offline and makes customer provisioning a separate step. |
| `scripts/aidlc-official-bridge.py` | Full preflight calls the project-local detector. When the pack is unavailable, it returns an official-pack-unavailable Lite fallback. | An explicit Full request can cease being Full. |
| `scripts/official-aidlc-requirements.py` | Resolves the governing rules relative to the project-local compatibility manifest. | Direct use of a package-owned manifest outside the project would violate the current safe-path boundary. |
| Host adapters | Codex projection assumes the immutable pack already exists under `.tailtrail/official-aidlc`; other host installation surfaces carry scripts but not a normal bundled-pack provisioning contract. | Host support starts after a separately installed pack rather than from a normal TailTrail installation. |

The public compatibility command currently reports:

```text
state: not-installed
compatible: false
issue: official AIDLC manifest not found
manifest: .tailtrail/official-aidlc/manifest.json
```

No Phase 5 Planning Lock was created from that failed Full-mode preflight.

## Root cause

The failure is not a single missing lookup. TailTrail has three incompatible ownership assumptions:

1. **Release ownership:** `aidlc-rules/` is treated as a source-checkout convention directory and excluded from release packaging.
2. **Runtime ownership:** official AIDLC compatibility is treated as project-local state that must already exist below `.tailtrail/official-aidlc/`.
3. **Provisioning ownership:** the only complete provisioner treats the official pack as a remotely downloaded dependency.

Changing only the detector to look at `aidlc-rules/` would be unsafe because the current directory has no pack-local license or immutable official manifest. Changing only packaging would still leave the runtime bridge expecting a project-relative manifest. Changing only the installer would preserve the unwanted separate-install step. The release, resource, resolver, provisioning, routing, and host contracts must converge on one product model.

## Scope

This design covers:

- the trusted bundle layout;
- upstream provenance and license handling;
- wheel, source-distribution, source-checkout, and managed-host packaging;
- offline bundle discovery;
- atomic project projection;
- Full-mode routing behavior;
- Codex, Copilot, and Claude integration;
- external-pack compatibility;
- failure classification and recovery guidance;
- security boundaries;
- migration and release validation;
- executable positive and negative proof.

## Non-goals

This design does not:

- execute arbitrary scripts from the official pack;
- download or update rules during ordinary Full Start;
- automatically replace an altered project-local pack;
- silently accept an unpinned upstream branch;
- treat a runtime-generated hash list as trusted provenance;
- weaken the requirement, scope, Planning Lock, approval, or evidence gates;
- convert TailTrail's local Lite rules into official AIDLC authority;
- claim that the current checked-in rules already match a particular official release without provenance verification.

## Terminology and ownership

| Term | Meaning | Owner |
| --- | --- | --- |
| Bundled pack | Immutable official rule content shipped inside the TailTrail distribution. | TailTrail release engineering |
| Bundle manifest | Release-authored metadata binding upstream provenance, license, compatibility, and every bundled file hash. | TailTrail release engineering |
| Package integrity | TailTrail's outer `package-integrity.json`, which protects all package-owned resources including the bundled pack. | TailTrail packaging |
| Artifact identity receipt | Evidence that binds a wheel or sdist digest to an authenticated TailTrail release identity, such as the existing GitHub/Sigstore attestation and publication receipt. | TailTrail release engineering |
| Trust posture | Closed classification of the resolved bytes: `authenticated-release`, `development-local`, `corruption-detection-only`, or `external-explicit`. | Shared resolver |
| Project projection | Content-addressed verified copy under `.tailtrail/official-aidlc/packs/<pack-fingerprint>/`. | TailTrail managed state |
| Current selector | Atomic `.tailtrail/official-aidlc/current.json` pointer used only to choose a pack for future runs. It never rewrites an active run's frozen pack binding. | TailTrail managed state |
| Resolution receipt | Typed record identifying the effective pack, source, host, official revision, and fingerprints used for one Full-mode request. | Shared resolver |
| Host projection receipt | Host-specific reference/copy mapping, complete inventory hashes, instruction fingerprint, and origin pack fingerprint. | Host adapter |
| External pack | Explicit enterprise or operator-supplied pack selected by manifest. | User or enterprise administrator |

## Target architecture

```text
Authenticated TailTrail release artifact
  - GitHub/Sigstore identity attestation
  - publication receipt and artifact SHA-256
            |
            v
Pinned official upstream release
            |
            | release-time acquisition and verification
            v
TailTrail bundled pack
  - official rules
  - MIT-0 license
  - provenance metadata
  - immutable SHA-256 manifest
            |
            | included in wheel and source distribution
            v
TailTrail package resources
  - protected by package-integrity.json
            |
            | Full-mode resolver, no network
            v
Content-addressed project-managed projection
  .tailtrail/official-aidlc/packs/<pack-fingerprint>/
  .tailtrail/official-aidlc/current.json
            |
            | one verified resolution receipt
            +--------------------+--------------------+
            v                    v                    v
      Full Start bridge   Requirements stage   Host projection
                                                  |
                                  +---------------+---------------+
                                  v               v               v
                                Codex          Copilot          Claude
```

The official rules remain data. TailTrail reads Markdown and metadata required for stage governance; it does not execute pack code.

## Bundled pack layout

The release asset should use a stable layout:

```text
aidlc-rules/
├── manifest.json
├── LICENSE
├── BUNDLE_VERSION
├── aws-aidlc-rules/
│   └── core-workflow.md
└── aws-aidlc-rule-details/
    ├── common/
    ├── inception/
    ├── construction/
    ├── operations/
    └── extensions/
```

`BUNDLE_VERSION` is the TailTrail packaging contract version. It must not be used as the official upstream version. The official revision and commit belong in `manifest.json`.

Before this layout is declared valid, release engineering must establish the provenance of the existing 31 rule files. If those bytes cannot be proven to come from the pinned official source, the release process must reacquire a pinned official archive once, verify it, preserve its license, and check the exact verified files into the TailTrail release source. Customer runtime remains offline.

## Bundle manifest contract

The bundle manifest should be versioned independently of the existing project-pack schema. A representative shape is:

```json
{
  "schema_version": "2",
  "type": "tailtrail-bundled-official-aidlc-pack",
  "bundle": {
    "format_version": "1",
    "tailtrail_version": "1.1.0",
    "bundle_version": "1",
    "created_from": "verified-upstream-release"
  },
  "official": {
    "source": "https://github.com/awslabs/aidlc-workflows",
    "revision": "<pinned-tag>",
    "commit": "<full-commit-sha>",
    "source_archive_sha256": "<sha256>",
    "license": {
      "spdx": "MIT-0",
      "file": "LICENSE",
      "sha256": "<sha256>"
    }
  },
  "compatibility": {
    "minimum_tailtrail_version": "<version>",
    "maximum_tailtrail_version_exclusive": "<version>",
    "manifest_schema": "2",
    "supported_hosts": ["codex", "copilot", "claude"]
  },
  "required_capabilities": {
    "requirements": [
      "aws-aidlc-rules/core-workflow.md",
      "aws-aidlc-rule-details/inception/requirements-analysis.md",
      "aws-aidlc-rule-details/common/question-format-guide.md",
      "aws-aidlc-rule-details/common/content-validation.md",
      "aws-aidlc-rule-details/common/session-continuity.md"
    ]
  },
  "integrity": {
    "algorithm": "sha256",
    "files": [
      {"path": "LICENSE", "sha256": "<sha256>"},
      {"path": "aws-aidlc-rules/core-workflow.md", "sha256": "<sha256>"}
    ]
  }
}
```

The complete manifest contains one unique safe relative path for every distributed pack file except the manifest itself. It must reject:

- absolute paths;
- `..` traversal;
- backslash ambiguity where platform normalization could differ;
- duplicate paths;
- symlinks or non-regular files;
- missing files;
- unlisted unexpected regular files; a closed inventory is mandatory for every trusted bundle;
- malformed or uppercase SHA-256 values;
- a license that is not included in the integrity inventory;
- an unpinned revision or branch name;
- missing upstream archive provenance;
- unsupported TailTrail or host-adapter versions.

The manifest must be generated during the controlled release process from the verified upstream input. Runtime code may validate it but must not regenerate it from local bytes and then trust the result.

## Authenticated trust and integrity model

The two local hash manifests are nested integrity controls, not two independent trust anchors. Because `package-integrity.json` is read from the same installed package whose files it verifies, an attacker who can replace the entire package can replace the files and both manifests together. Those manifests detect accidental corruption and partial alteration; by themselves they do not prove who published the package.

### Trust anchor — authenticated TailTrail release artifact

The authenticated release chain is:

```text
GitHub/Sigstore identity attestation
  -> authenticated wheel or sdist digest
  -> publication/installation receipt for that exact artifact
  -> package-integrity.json
  -> aidlc-rules/manifest.json
  -> exact AIDLC rule and license inventory
```

The outer identity verification must use the existing release controls documented in `SUPPLY-CHAIN.md`, `release-channel-v1.json`, `platform-release-contract.json`, and `scripts/installation-qualification.py`. A runtime may report `authenticated-release` only when it can bind the installed artifact to a qualifying verified attestation or installation/publication receipt. If that binding is unavailable, matching local hashes may support `corruption-detection-only`, but the UI and receipt must not call the package release-authenticated or provenanced.

### Integrity layer 1 — TailTrail package inventory

`package-integrity.json` must cover:

- `aidlc-rules/manifest.json`;
- the official MIT-0 `LICENSE` stored inside the bundle;
- `BUNDLE_VERSION`;
- every official rule and rule-detail file.

Validation requires equality, not subset membership:

```text
expected package bundle inventory
  == package-integrity bundle entries
  == actual regular files below tailtrail/aidlc-rules/
```

A missing file, an unexpected regular file, a duplicate normalized path, a symlink, or a hash mismatch fails this layer.

### Integrity layer 2 — Official pack inventory and provenance

The bundle manifest binds:

- the official source identity;
- the pinned official tag and full commit;
- the upstream source archive hash;
- the official license identity and bytes;
- the exact rule-file inventory and hashes;
- compatibility with the running TailTrail release and host adapters.

Validation also requires equality:

```text
bundle manifest file inventory
  == actual regular files below the bundle root, excluding manifest.json
```

The package-integrity bundle entries and bundle-manifest inventory must agree on every shared path and digest. Any disagreement blocks Full mode. The bundle manifest supplies structured upstream provenance, but that provenance becomes release authority only when it is reached through the authenticated artifact chain above.

### Trust postures

| Posture | Minimum evidence | Permitted claim |
| --- | --- | --- |
| `authenticated-release` | Verified release identity/attestation binds the installed wheel or sdist digest; both integrity layers and closed inventories pass. | Normal production Full authority from the bundled pack. |
| `development-local` | Repository-root provider finds the checked-in bundle; bundle manifest and closed inventory pass; no authenticated release artifact is claimed. | Local development Full behavior with the posture disclosed. |
| `corruption-detection-only` | Local package and bundle hashes pass, but no qualifying artifact-identity receipt is available. | Integrity consistency only; never publisher identity or release provenance. Product policy must explicitly decide whether Full may proceed. |
| `external-explicit` | User-selected external pack passes the explicit external-pack policy and is frozen by fingerprint. | Authority only for the explicitly selected pack; never implicit substitution for the bundled release. |

## Package and release integration

### Resource-provider contract

One resolver API has two explicit providers. They share validation and receipt types but do not pretend that source and installed layouts have the same root or trust evidence.

#### Installed package provider

`InstalledPackageProvider` locates `tailtrail/aidlc-rules/` through `importlib.resources.files("tailtrail")` or the package module directory, never through the current working directory. It requires `package-integrity.json`, validates the complete package inventory, and validates the nested bundle manifest. It may return `authenticated-release` only when the installed artifact is bound to a qualifying release identity receipt; otherwise it returns `corruption-detection-only` or blocks according to the decided product policy.

#### Source checkout provider

`SourceCheckoutProvider` derives the repository root from the resolver module's `__file__` location and verified repository sentinels such as `pyproject.toml`, `package-manifest.json`, and `aidlc-rules/`. It must work when invoked from an unrelated current working directory. It validates the bundle manifest and exact checked-in bundle inventory directly; it does not require the wheel-generated `package-integrity.json`, because that file does not exist in a normal source checkout.

The source provider returns `development-local` unless the checkout's commit or tag is authenticated independently. It must never report `authenticated-release` merely because the local manifest matches the local bytes. The existing `tailtrail/install/catalog.py` source-root pattern is a reusable implementation precedent, but the new provider must validate its own sentinels and fail on ambiguous roots.

### Wheel

`package-manifest.json` adds `aidlc-rules` to `required_directories`. `setup.py` already copies every selected required directory into the `tailtrail/` package directory and adds its files to `package-integrity.json`. The built wheel therefore contains:

```text
tailtrail/aidlc-rules/...
```

### Source distribution

`MANIFEST.in` adds:

```text
recursive-include aidlc-rules *
```

An sdist-to-wheel build must produce the same normalized bundle inventory and hashes as a wheel built directly from the source checkout.

### Release manifest

`release-manifest.json` removes `aidlc-rules/` from candidate exclusions and adds the bundle's required release files. Release proof must fail if the bundle is absent, incomplete, or inconsistent with either integrity layer.

### Managed TailTrail host installation

The transactional installer includes the bundle through the extended common payload. The normal Full route must work whether TailTrail runs from:

- a source checkout;
- a Python wheel installed in an isolated environment;
- a wheel built from an sdist;
- a managed host payload installed into a target repository.

## Canonical resolver

One shared resolver should own pack selection. A suitable package-owned module is `tailtrail/aidlc_bundle.py`, exposed to legacy scripts through a thin compatibility adapter if needed.

### Resolver inputs

- target repository root;
- requested mode;
- selected host;
- optional explicit manifest path;
- running TailTrail version and host-adapter version;
- discovered resource provider and its trust evidence;
- optional authenticated artifact-identity or installation receipt;
- whether provisioning is permitted for this call.

### Resolution precedence

1. **Explicit manifest:** If the user supplies `--official-aidlc-manifest`, validate exactly that pack. Any defect blocks the request; never fall back to another source.
2. **Frozen run binding:** If the request belongs to an existing run, resolve only the exact pack fingerprint stored by that run. A newer `current.json` must not change the governing rules of an active run.
3. **Current project selection:** For a new run, validate `.tailtrail/official-aidlc/current.json` and the exact content-addressed pack it selects. Any altered, incomplete, incompatible, or unsafe selected state blocks the request; never hide it with the bundled copy.
4. **Bundled pack:** If no current project selection exists, validate the appropriate installed-package or source-checkout provider. When provisioning is permitted, project it atomically and validate the result.
5. **Unavailable:** If no valid source exists, return a typed blocker. Full mode remains requested and blocked; it does not become Lite.

This precedence prevents a damaged project-local state from being silently ignored while retaining advanced explicit-pack support.

### Resolver output

The resolver returns a closed receipt, for example:

```json
{
  "schema_version": "1",
  "type": "tailtrail-official-aidlc-resolution",
  "state": "ready",
  "requested_mode": "full",
  "effective_mode": "full",
  "source_kind": "tailtrail-bundled",
  "resource_provider": "installed-package",
  "trust_posture": "authenticated-release",
  "artifact_identity_receipt": "<receipt-reference>",
  "release_artifact_sha256": "<sha256>",
  "network_used": false,
  "host": "codex",
  "official_source": "https://github.com/awslabs/aidlc-workflows",
  "official_revision": "<pinned-tag>",
  "official_commit": "<full-commit-sha>",
  "bundle_manifest_fingerprint": "sha256:<digest>",
  "package_integrity_fingerprint": "sha256:<digest>",
  "project_manifest": ".tailtrail/official-aidlc/packs/<pack-fingerprint>/manifest.json",
  "project_selector": ".tailtrail/official-aidlc/current.json",
  "project_projection_fingerprint": "sha256:<digest>",
  "provisioning": "created",
  "boundary": "Verified rule data only; no pack script was executed."
}
```

The Full bridge, Requirements adapter, host projection, saved Start artifact, and later runtime attachment must reference the same receipt or its immutable fingerprint. They must not independently rediscover the pack. Every run stores the exact project pack path, pack fingerprint, bundle-manifest fingerprint, and trust posture; it never stores only the mutable `current.json` selector.

## Artifact and schema separation

The implementation must not overload one manifest with bundle, project, run, and host concerns. These are separate versioned contracts:

| Artifact | Purpose | Mutability |
| --- | --- | --- |
| Bundle manifest schema v2 | Host-neutral official source, license, compatibility, and complete file inventory for the immutable distributed pack. | Release-authored and immutable. |
| Project projection receipt | Binds the source bundle-manifest fingerprint, projected pack fingerprint, trust posture, copied inventory, and creation event. It does not add a selected host to the bundle manifest. | Append-only, one receipt per pack projection. |
| `current.json` selector | Chooses the default content-addressed pack for future runs. | Atomically replaceable through a controlled migration only. |
| Run resolution receipt | Freezes one run to an exact pack path and fingerprint, requested/effective mode, trust posture, and official identity. | Immutable for that run. |
| Host projection receipt | Binds one host's reference or copy mapping and instruction fingerprint to the same frozen project pack. | Append-only per projection operation. |

The project projection keeps the original host-neutral bundle manifest unchanged. Host identity belongs in the host projection receipt and resolution receipt, never in a rewritten copy of the official manifest.

## Read-only status versus provisioning

`tailtrail aidlc official status` should remain read-only. It may report:

```text
Project projection: absent
Bundled pack: compatible
Effective Full posture: ready-to-provision
Network required: no
```

An explicit `tailtrail aidlc official provision --root . --host codex` command may be provided for diagnostics and enterprise preparation, but users should not need it. `tailtrail start ... --aidlc full --host codex` invokes the same resolver with provisioning enabled as part of Full preflight.

Keeping the status command read-only prevents an inspection command from unexpectedly changing a repository.

## Atomic offline provisioning

Provisioning writes only TailTrail-managed state under `.tailtrail/`.

### Preconditions

1. The target root exists and is not a filesystem root.
2. The target `.tailtrail` path and each relevant ancestor are not unsafe symlinks.
3. The packaged TailTrail integrity check passes.
4. The bundled official-pack manifest and every listed file pass validation.
5. The selected host is supported by the bundle and current host-adapter contract.
6. No incompatible destination already exists.

### Algorithm

1. Acquire a bounded lifecycle lock below `.tailtrail/`.
2. Recheck the destination after acquiring the lock.
3. Compute the immutable pack fingerprint and target `.tailtrail/official-aidlc/packs/<pack-fingerprint>/`.
4. If that exact valid pack projection exists, return `reused` without rewriting pack files or appending duplicate projection events.
5. If the exact content-addressed destination exists but is invalid, return a typed failure. Do not overwrite or delete it.
6. Create a unique staging directory below the same filesystem, such as `.tailtrail/official-aidlc/packs/.staging-<uuid>`.
7. Copy exactly the closed manifest inventory from the verified bundled resource, preserving the host-neutral manifest unchanged.
8. Create a separate project projection receipt binding source manifest, trust posture, exact inventory, and destination fingerprint.
9. Flush written files where platform support permits.
10. Rehash the complete staging projection and validate it with the normal project-pack detector.
11. Atomically rename the staging directory to the content-addressed pack destination.
12. Revalidate the final destination.
13. Atomically create or update `.tailtrail/official-aidlc/current.json` for future runs only. Refuse the selector update if active-run policy or migration approval is unresolved.
14. Write the run resolution receipt atomically and append one successful provisioning event.
15. Release the lock.

On any failure, remove only the operation's staging directory. Never remove or modify a pre-existing destination. Never record a successful event before final validation.

### Concurrency

Two Full Starts may race. The lock and post-lock destination check must produce one `created` result and one `reused` result. Neither process may observe a partially copied pack.

### Idempotence

The immutable project-pack identity key should include:

```text
official source + official revision + official commit +
bundle manifest fingerprint + exact closed inventory + TailTrail compatibility version
```

Host identity is deliberately excluded from project-pack identity. Repeated resolution of the same pack performs no copy, changes no pack modification times, and creates no duplicate projection event. Host-specific idempotence is evaluated separately from the host projection receipt.

## Destination-state policy

| Destination state | Full-mode action | Automatic mutation |
| --- | --- | --- |
| Absent, bundle valid | Provision atomically and continue. | Create managed projection only. |
| Selected pack present and byte-identical | Reuse and continue. | None. |
| Present, compatible external pack explicitly selected | Use it and record `external-explicit`. | None. |
| Missing file | Fail closed as incomplete. | None. |
| Hash mismatch | Fail closed as altered. | None. |
| Unsupported version | Fail closed as incompatible. | None. |
| `current.json` selects an older valid compatible revision for a new run | Block until an explicit migration selects a newly provisioned content-addressed pack. | Add new pack only after approval; never overwrite old pack. |
| Active run refers to an older valid compatible revision | Continue using the exact frozen path and fingerprint. | None. The current selector cannot retarget the run. |
| Newer unrecognized revision | Fail closed as incompatible. | None. |
| Unsafe symlink, traversal, special file, or escaping path | Fail closed as unsafe. | None. |
| Partial staging directory from an interrupted prior attempt | Ignore as non-authoritative, report it, and remove only through a bounded recovery action. | No ordinary Start cleanup. |

An explicit approved repair command may move a defective managed destination to a timestamped backup and install the bundled projection. Repair must preserve the old bytes for audit and must not be implicit in Full Start.

## Full-mode routing contract

### Explicit Full request

For `--aidlc full` or explicit natural-language Full intent:

```text
requested_mode = full
effective_mode = full, when ready
effective_mode = unavailable, when blocked
```

The following result is forbidden:

```text
requested_mode = full
effective_mode = lite
```

If resolution fails, Start stops before requirement routing, scope discovery, graph work, Planning Lock creation, or implementation authority. The report retains `requested_mode: full` and states the exact repair action.

### Inferred Full request

Hands-free or program-scale routing may select Full automatically. Because a normal TailTrail distribution now includes the bundle, this route should normally succeed. If distribution integrity fails, the safe behavior is also to block rather than quietly claim that the requested end-to-end lifecycle ran under Lite.

If product policy intentionally retains a fallback for inferred, non-explicit Full selection, it must be separately named, prominent, and user-approved before a Lite Planning Lock is created. It must never reuse wording that implies Full ran. The recommended policy is to fail closed consistently for all selected Full routes.

### Standard mode

Standard official Requirements Analysis may consume the same bundled pack and resolver. Standard-mode compatibility behavior can be migrated separately, but it must not weaken the explicit Full rule.

## Host integration

### Shared behavior

Codex, Copilot, and Claude consume one immutable content-addressed project pack and one frozen run resolution receipt. The official bytes, project pack fingerprint, provenance, and trust posture are identical across hosts.

Each adapter declares one projection mode:

- **Reference:** the host can safely consume project-relative immutable pack paths. The adapter writes only instructions plus a receipt containing the referenced inventory and pack fingerprint.
- **Copy:** the host requires rules at a host-owned location. The adapter copies through a same-filesystem staging directory, validates every destination file, atomically installs the projection, and writes a complete receipt.

The mode is a host-adapter contract, not an operator guess. A host may not silently change from reference to copy or create an unrecorded second rule inventory.

### Host projection receipt

Every reference or copy operation records:

```text
host identity + adapter version + projection mode +
origin run-resolution fingerprint + origin project-pack fingerprint +
complete source-to-destination mapping + every destination SHA-256 +
host instruction-block fingerprint + reload posture + qualification result
```

Status recomputes the complete expected destination inventory and every digest. Checking only that the details directory exists is forbidden. Missing, additional, altered, symlinked, or non-regular destination entries fail conformance. Copy mode must reject unsafe destination ancestors and must not overwrite an unrecognized existing host projection.

### Codex

The existing Codex projection is migrated to the shared adapter contract. Its current core-file digest plus `details.is_dir()` status check is insufficient; it must validate the complete projected inventory and receipt.

### Copilot

Copilot receives an explicit adapter implementation, not documentation-only support. Its instructions and prompts reference the same verified project pack or use an audited copy only when the host contract requires it. The receipt records the exact mapping and fingerprint. It must not download a second pack.

### Claude

Claude receives an explicit adapter implementation under the same contract. Guidance and hooks reference the same verified project pack or an audited copy. Hook availability is a separate host enforcement capability; it does not change pack integrity or provenance.

### Host conformance invariant

For every host:

```text
same official source
same official revision and commit
same bundle manifest fingerprint
same project projection fingerprint
same trust posture
same Full-mode requirement authority
host-specific projection fingerprint and receipt only
```

## External and enterprise pack compatibility

The existing network installer can remain as an advanced external-pack mechanism, but it is no longer the normal prerequisite.

Rules:

1. A supplied `--official-aidlc-manifest` is an explicit override and is validated without fallback.
2. An external pack must satisfy the same provenance, license, integrity, compatibility, and path-safety requirements.
3. The saved resolution receipt records `source_kind: external-explicit`.
4. Ordinary Full Start never downloads a pack.
5. Existing project-local schema-v1 manifests remain readable only for the bounded legacy active-run behavior in the compatibility matrix; they cannot authorize a new bundled Full run.
6. A legacy pack that lacks the new provenance or compatibility fields cannot be silently upgraded by regenerating its manifest. It requires an explicit migration or replacement from authenticated source evidence.

## Security and safety model

### Threats and controls

| Threat | Required control |
| --- | --- |
| Entire package and its local manifests replaced together | Verify the wheel/sdist identity attestation and exact artifact digest before reporting `authenticated-release`; local hashes alone are only corruption detection. |
| Altered packaged rule | Authenticated artifact binding plus package-integrity hash plus inner bundle hash; fail before provisioning. |
| Missing or injected file not listed by a manifest | Require equality between expected, declared, and actual regular-file inventories at package, project, and copied-host layers. |
| Manifest regenerated after tampering | Manifest is release-authored and immutable; runtime never mints trust from current bytes or upgrades trust posture from matching local hashes. |
| Path traversal | Closed safe-relative-path validator for every manifest and destination path. |
| Symlink escape | Reject symlinks in bundle inventory, staging, destination, and managed ancestors. |
| Partial copy accepted as valid | Stage, fully verify, then atomically rename. |
| Race between Starts | Lifecycle lock and post-lock recheck. |
| Unsafe automatic repair | Existing invalid state blocks; repair requires a separate explicit approved operation. |
| Silent Full-to-Lite downgrade | Preserve requested mode and fail closed before Planning Lock. |
| Unpinned upstream movement | Require tag or commit plus full commit and source-archive digest. |
| License loss | Package the upstream MIT-0 license and include it in both integrity layers. |
| Host-specific rule divergence | One shared project pack; host adapters use explicit reference/copy modes and complete receipts. Every copied file is reverified. |
| Active run silently changes rules after upgrade | Freeze the exact pack path and fingerprint in the run receipt; `current.json` affects future runs only. |
| Pack code execution | Treat the pack as read-only data; never import or execute its scripts. |
| Network dependency | No network call in resolver, provisioning, status, Start, or host projection. |

### Privacy

The bundled pack contains public rule content and provenance metadata only. Resolution receipts must not contain user source, prompts beyond necessary run linkage, credentials, environment secrets, or private model reasoning.

### Auditability

Record append-only events for:

- bundle resolution attempted;
- bundle verification failed, with categorical reason and safe path reference;
- project projection created;
- identical project projection reused;
- future-run selector updated, with old and new fingerprints;
- active run resolved through its frozen pack binding;
- explicit external pack selected;
- Full Start blocked before Planning Lock;
- host projection created from a resolution receipt.

Do not log complete rule contents or secret-bearing environment values.

## Failure taxonomy and user guidance

Every failure must identify the classification, impact, and exact next action.

| Code | Meaning | Impact | Next action |
| --- | --- | --- | --- |
| `artifact-identity-unverified` | The installed artifact is not bound to a qualifying identity attestation or installation/publication receipt. | TailTrail may detect local corruption but cannot claim an authenticated release. | Verify or reinstall from the authenticated release channel; follow the explicit policy for `corruption-detection-only`. |
| `bundled-pack-missing` | Installed TailTrail distribution lacks required bundle assets. | Full cannot start; likely packaging defect. | Repair or replace the TailTrail installation from a verified artifact. |
| `bundled-pack-altered` | A packaged bundle hash differs. | Distribution integrity is compromised. | Reinstall the same verified TailTrail release; do not provision. |
| `bundled-pack-incompatible` | Bundle metadata does not support the running TailTrail or host adapter. | Full rules cannot safely govern this run. | Install a compatible TailTrail release. |
| `bundle-provenance-invalid` | Source, revision, commit, archive digest, or license is absent or invalid. | Official authority cannot be claimed. | Replace the release artifact; do not regenerate trust locally. |
| `destination-incomplete` | Project projection is missing a declared file. | Full cannot rely on the project state. | Run the explicit repair flow after reviewing the managed-state backup. |
| `destination-altered` | Project projection hash differs. | The local rule state is untrusted. | Preserve and repair explicitly; do not overwrite automatically. |
| `destination-stale` | Valid projection does not match the release-required pin. | The wrong official rules would govern the run. | Approve a controlled projection upgrade. |
| `destination-incompatible` | Projection schema or host compatibility is unsupported. | Full cannot continue. | Migrate or replace through the controlled repair path. |
| `destination-unsafe` | Symlink, traversal, special file, or unsafe managed root detected. | Copy or read could escape the repository boundary. | Correct the unsafe filesystem state manually, then retry. |
| `provisioning-interrupted` | Staging did not complete. | No successful projection exists. | Inspect the typed recovery report and retry; never use staging as authority. |
| `full-mode-unavailable` | No valid effective pack can be resolved. | No Planning Lock or Full authority is created. | Follow the underlying categorized recovery action. |

Example failure presentation:

```text
Full AIDLC could not start.

Classification: TailTrail distribution integrity defect
Reason: bundled-pack-altered
File: aidlc-rules/aws-aidlc-rules/core-workflow.md
Impact: no Planning Lock, scope, approval, or implementation authority was created.
Next action: reinstall TailTrail 1.1.0 from a verified wheel and retry the same Full request.
TailTrail did not downgrade this request to Lite and did not access the network.
```

## Public command behavior

### Status

```bash
tailtrail aidlc official status --root .
```

Read-only output distinguishes:

- package bundle state;
- resource provider and trust posture;
- artifact-identity receipt state;
- project projection state;
- selected future-run pack and any frozen active-run pack;
- effective Full readiness;
- selected official revision;
- whether provisioning would be required;
- whether network access is required, always `no` for the bundled route.

### Optional explicit provisioning

```bash
tailtrail aidlc official provision --root . --host codex
```

This is useful for diagnostics and pre-provisioned enterprise images. It uses the same resolver and creates no Planning Lock or implementation authority.

### Full Start

```bash
tailtrail start "<goal>" --aidlc full --host codex
```

The normal route automatically resolves and, when absent, provisions the bundled pack. The Start report records:

- `requested_mode: full`;
- `effective_mode: full`;
- official source, revision, and commit;
- resource provider, trust posture, and artifact-identity receipt reference;
- bundle and project fingerprints;
- provisioning result (`created`, `reused`, or `external-explicit`);
- `network_used: false`;
- host identity and official Requirements authority.

## Lifecycle boundaries

Bundled-pack readiness does not grant implementation authority.

```text
verify package and pack
  -> provision managed rule state
  -> establish official requirement authority
  -> complete requirements/questions
  -> resolve scope and proof
  -> create Planning Lock
  -> audit plan
  -> explicit user approval
  -> activation
  -> implementation and evidence
```

The resolver may establish only rule availability and provenance. It cannot:

- accept requirements;
- promote a path to implementation owner;
- approve a plan;
- activate a run;
- execute a command;
- write project source;
- claim proof or closure.

## Compatibility and migration

### Compatibility matrix

| Existing state | New Full run | Existing active run | Migration rule |
| --- | --- | --- | --- |
| Current valid schema-v2 content-addressed pack with accepted trust posture | Allowed. Freeze its exact path and fingerprint in the run receipt. | Continue on the frozen pack. | None. |
| Older but compatible valid schema-v2 pack | Block new selection until an explicit controlled migration chooses a new current pack. | Continue only on the exact previously frozen path and fingerprint. | Provision the new pack alongside the old pack, then atomically update `current.json` for future runs. |
| Valid schema-v1 project pack lacking the new provenance fields | Never silently promote it or use it as authority for a new bundled Full run. | A pre-existing run may continue or close only when its stored bytes and fingerprint remain exact and the receipt labels it `legacy-v1`; it grants no new authority. | Explicitly replace or migrate from authenticated source evidence. Never infer missing provenance. |
| Valid explicit enterprise pack | Allowed only through the explicit override route after full external-pack validation and fingerprint freeze. | Continue on the frozen explicit pack. | Enterprise policy owns replacement; no implicit bundled substitution. |
| Altered, incomplete, unsafe, or unrecognized v1/v2 pack | Blocked. | Blocked if the frozen bytes no longer validate. | Preserve evidence and use the explicit repair/replacement path. |

### Active-run upgrade rule

An upgrade never modifies or deletes a pack referenced by an active run. It adds a new content-addressed pack and changes `current.json` only for future runs after the migration is explicitly authorized. Active runs remain bound to their saved manifest path and fingerprint even after the selector changes. Retention policy may delete an old pack only after proving that no active, resumable, auditable, or closure-pending run references it.

### Existing network installer

The network installer may be retained for advanced external-pack acquisition, renamed or documented as an external override. User guidance must stop presenting it as required before normal Full mode.

### Existing manifest schema

The existing detector may continue parsing schema v1 strictly for the bounded compatibility cases in the matrix. The immutable bundled pack uses schema v2. A project projection stores the unchanged v2 bundle manifest plus a separate projection receipt; a host projection stores a separate host receipt. Compatibility code must never rewrite a v1 manifest as v2 or fill missing provenance fields with inferred values.

### Current rule directory

Before migration, verify whether the current 31 files actually match the intended pinned upstream release. The existing `VERSION` value alone is insufficient. Choose one of these release-time actions:

1. Prove the existing bytes against a trusted pinned upstream archive and generate the immutable manifest from that verified input; or
2. Replace the directory with a newly acquired, verified pinned release and preserve its license and provenance.

The second option is safer if provenance cannot be reconstructed conclusively.

## Implementation phases

### Phase 0 — Provenance decision and inventory

Deliverables:

- establish the pinned upstream tag and full commit;
- obtain and record the upstream archive SHA-256;
- verify or replace the current rule bytes;
- add the MIT-0 license inside the bundle;
- define bundle-versus-official version fields;
- inventory all required and optional rules;
- decide the supported TailTrail compatibility range;
- choose the authenticated release-artifact trust anchor and qualifying receipt;
- define the four trust postures and whether `corruption-detection-only` may proceed;
- approve the source-checkout provider's `development-local` contract;
- approve the v1/v2, active-run, external-pack, and host projection decisions listed in the decision table below.

Exit criteria:

- every bundled byte has verified provenance;
- no claim depends only on the existing `VERSION` file;
- license and source identity are unambiguous;
- no unresolved trust, migration, or active-run policy decision is deferred into runtime implementation.

### Phase 1 — Bundle manifest and package inclusion

Likely owners:

- `aidlc-rules/manifest.json` and bundle assets;
- `package-manifest.json`;
- `MANIFEST.in`;
- `release-manifest.json`;
- `setup.py` only if existing selection behavior needs extension;
- `scripts/package-release-proof.py`.

Deliverables:

- schema and validator for the bundled manifest;
- wheel and sdist inclusion;
- outer package-integrity coverage;
- authenticated artifact linkage and trust-posture classification;
- release proof that checks the artifact identity chain plus both integrity layers;
- mandatory exact inventory equality at package and bundle layers.

Exit criteria:

- wheel and sdist inventories contain the complete bundle;
- reproducible builds retain deterministic bundle hashes;
- missing or altered assets fail package proof.

### Phase 2 — Shared resolver and atomic projection

Likely owners:

- new package-owned resolver such as `tailtrail/aidlc_bundle.py`;
- `tailtrail/resources.py` for package-resource location and outer integrity;
- `scripts/aidlc-official-detect.py` as a compatibility adapter;
- transactional file helpers already used by the installer.

Deliverables:

- typed resolver receipt;
- explicit installed-package and source-checkout providers independent of the current working directory;
- resolution precedence;
- offline validation;
- content-addressed atomic project projection plus atomic future-run selector;
- frozen active-run binding and v1/v2 compatibility behavior;
- locking, idempotence, and recovery behavior;
- read-only status and optional explicit provision command.

Exit criteria:

- source checkout and installed package resolve the same identity;
- source checkout and installed package expose different truthful trust postures;
- no network access occurs;
- unsafe or conflicting destination state remains untouched and blocks.

### Phase 3 — Full route and official-stage integration

Likely owners:

- `scripts/aidlc-official-bridge.py`;
- `scripts/task-start.py`;
- `scripts/official-aidlc-requirements.py`;
- `scripts/planning_lock.py` where the resolution receipt joins saved planning state;
- MCP forwarding for the same public contract.

Deliverables:

- normal Full preflight consumes the resolver;
- explicit Full never becomes Lite;
- requirements and bridge artifacts reference one receipt fingerprint;
- failures stop before Planning Lock and show the exact recovery action;
- CLI and MCP routes remain consistent.

Exit criteria:

- a normal explicit Full Start reaches the official Requirements stage offline;
- all saved Full artifacts name the same pack identity;
- negative states create no plan or authority.

### Phase 4 — Host projections

Likely owners:

- `scripts/aidlc-official-host.py`;
- Codex, Copilot, and Claude adapter contracts and installation surfaces;
- host conformance tests.

Deliverables:

- all three hosts consume the same resolution receipt;
- each host declares and enforces reference or copy mode;
- host-specific projections are atomic, safe, and completely inventoried;
- each host reports the project-pack fingerprint, host-projection fingerprint, trust posture, and reload posture.

Exit criteria:

- Codex, Copilot, and Claude conformance results agree on official identity;
- status detects a missing, additional, altered, symlinked, or non-regular file anywhere in a copied host projection;
- no host silently downloads or substitutes rules.

### Phase 5 — Distribution and end-to-end proof

Likely proof owners:

- `tests/test_aidlc_official_detect.py`;
- `tests/test_aidlc_official_install.py` or a new bundle-resolver suite;
- `tests/test_aidlc_official_bridge.py`;
- `tests/test_auto_routing.py`;
- `tests/test_aidlc_official_host.py`;
- `tests/test_self_contained_package.py`;
- public CLI/MCP route tests.

Deliverables:

- source, wheel, and sdist offline Full runs;
- release-attestation and corruption-detection-only trust tests;
- source-provider tests from an unrelated current working directory;
- v1/v2 and active-run migration matrix;
- host matrix;
- negative integrity matrix;
- interrupted-write and concurrency proof;
- release documentation aligned with the implemented product model.

Exit criteria:

- every acceptance criterion in this design has executable proof;
- user documentation no longer requires separate pack installation;
- a built release artifact, not only the source checkout, proves Full readiness.

## File impact map

| File or area | Role in the fix | Expected change |
| --- | --- | --- |
| `aidlc-rules/` | Bundled official asset | Add verified license, manifest, distinct bundle version, and complete pinned contents. |
| `schemas/official-aidlc-pack.schema.json` or a new bundled schema | Manifest contract | Add provenance, compatibility, and bundle-source fields without weakening legacy validation. |
| `package-manifest.json` | Wheel resource selection | Include `aidlc-rules` as required packaged content. |
| `MANIFEST.in` | Source-distribution selection | Recursively include the bundle. |
| `release-manifest.json` | Release truth | Remove the exclusion and require bundle artifacts. |
| `setup.py` | Deterministic package build | Normally reuse existing copy/integrity behavior; adjust only if required for canonical resource placement. |
| `tailtrail/resources.py` | Installed-package resource trust | Expose the installed provider, complete package inventory validation, artifact-identity linkage, and truthful trust posture. |
| `tailtrail/install/catalog.py` or shared root helper | Source-checkout precedent | Reuse its package-versus-source root pattern without depending on the current working directory; add AIDLC-specific sentinel validation. |
| `SUPPLY-CHAIN.md`, `release-channel-v1.json`, `platform-release-contract.json`, `scripts/installation-qualification.py` | Authenticated release trust anchor | Bind the exact installed artifact digest to the existing attestation/publication contract. |
| New shared resolver | Selection and projection owner | Implement precedence, verification, receipt, lock, atomic copy, idempotence, and recovery. |
| Project projection/current-selector schemas | Project state contract | Separate immutable pack projection receipts from the future-run `current.json` selector. |
| Host projection receipt schema | Host state contract | Bind reference/copy mapping, complete hashes, instructions, host identity, and origin pack fingerprint. |
| `scripts/aidlc-official-detect.py` | Read-only compatibility view | Report project, bundled, and effective posture without mutation. |
| `scripts/aidlc-official-install.py` | Advanced external acquisition | Stop being the normal Full prerequisite; retain explicit external use if desired. |
| `scripts/aidlc-official-bridge.py` | Full preflight | Consume resolver receipt and remove explicit Full-to-Lite downgrade. |
| `scripts/task-start.py` | Public Start routing | Provision before official authority, preserve Full request, and stop safely on typed blockers. |
| `scripts/official-aidlc-requirements.py` | Requirements rule lookup | Resolve through the saved verified projection/receipt. |
| `scripts/aidlc-official-host.py` | Host rule projection | Bind host projection to the resolver receipt. |
| `scripts/mcp-server.py` | MCP parity | Forward the same host, mode, and resolver contract. |
| `tailtrail-registry.json` | Product ownership | Register any new command, module, schema, and tests. |
| User and command documentation | Product guidance | Describe bundled offline behavior and advanced override/repair routes accurately. |

This is inherently multi-owner work. TailTrail planning should represent it as requirement-scoped owners or focused dependent slices rather than assigning all files to one owner.

## Proof strategy

### Unit proof

- installed-package and source-checkout provider selection without current-working-directory dependence;
- trust-posture classification and prohibition on unauthenticated release claims;
- manifest schema validation;
- safe relative paths;
- duplicate, missing, and unexpected inventory rejection;
- pinned revision and full commit validation;
- license inclusion and hash validation;
- compatibility range evaluation;
- deterministic fingerprint generation;
- resolution precedence;
- idempotence identity;
- failure-code mapping.

### Contract proof

- outer package-integrity and inner pack-integrity agreement;
- authenticated artifact digest to package-integrity linkage;
- resolver receipt schema;
- bundle-manifest, project-projection-receipt, current-selector, run-receipt, and host-receipt separation;
- v1/v2 compatibility matrix and frozen active-run binding;
- bridge, Requirements adapter, and host adapter consume the same fingerprint;
- CLI and MCP results carry identical effective mode and pack identity.

### Behaviour proof

- explicit Full Start from an empty project automatically provisions and remains Full;
- status remains read-only;
- a repeated Full Start reuses the projection;
- altered project state blocks instead of being overwritten or hidden;
- missing package assets report a TailTrail distribution defect;
- a source checkout reports `development-local`, not `authenticated-release`;
- local hashes without a qualifying artifact receipt report `corruption-detection-only` and follow the decided policy;
- changing `current.json` never retargets an active run;
- no failure silently creates a Lite Planning Lock.

### Integration proof

- build a wheel, install it into an isolated virtual environment with `--no-index`, create a new Git repository, disable network access, and run the public Full route;
- build an sdist, build/install its wheel offline, and run the same route;
- run from the source checkout and compare the effective official identity;
- run from the source checkout while the process current directory is outside the repository;
- run Codex, Copilot, and Claude reference/copy paths against the same project pack;
- prove each copied host projection detects alteration anywhere in its complete inventory;
- migrate from an older compatible pack while an active run remains bound to the old content-addressed pack;
- exercise the MCP Start route in addition to the CLI.

### Failure and recovery proof

- remove one packaged file;
- alter one rule byte;
- add one unlisted file to the package bundle and to a project/host projection;
- alter rule bytes and rewrite both local hash manifests, then prove that the missing or mismatched outer artifact identity prevents an `authenticated-release` claim;
- alter the license;
- change official source or revision metadata;
- create an incomplete destination;
- create a stale destination;
- create a symlinked destination or escaping manifest entry;
- inject a failure before atomic rename;
- inject a failure after staging verification but before receipt creation;
- race two provisioning processes;
- verify that prior valid state remains readable after every injected failure.

### Red-to-green requirement

The public regression must fail against the current behavior with the exact symptom: an explicit Full request sees no project-local manifest and cannot use the package-owned rules. After implementation, the same isolated public invocation must remain Full, use no network, and record matching package, bundle, and project fingerprints.

## Acceptance criteria

### Packaging

- [ ] The checked-in bundle has verified upstream provenance and its own MIT-0 license.
- [ ] Wheel and source distribution contain the complete bundle.
- [ ] TailTrail package integrity covers every bundle file.
- [ ] The bundle manifest covers every distributed official file.
- [ ] Package, bundle-manifest, and actual regular-file inventories are exactly equal; unexpected files fail proof.
- [ ] A verified attestation/publication receipt binds the built artifact digest before the resolver reports `authenticated-release`.
- [ ] Local hashes without that outer binding are labeled `corruption-detection-only`, never release-authenticated.
- [ ] Direct wheel and sdist-to-wheel builds produce equivalent bundle inventory and hashes.

### Resolution and provisioning

- [ ] Full mode automatically discovers the package-owned bundle.
- [ ] Absent project state is provisioned without network access.
- [ ] Identical project state is reused without rewrite or duplicate events.
- [ ] Provisioning is atomic, locked, and restart-safe.
- [ ] Existing invalid or conflicting state is never overwritten automatically.
- [ ] Resolution returns a typed, fingerprinted receipt.
- [ ] The installed-package provider and source-checkout provider work without relying on the process current directory.
- [ ] Source checkout reports `development-local` unless its source identity is independently authenticated.
- [ ] Project packs are content-addressed, `current.json` selects only future runs, and active runs retain exact frozen bindings.
- [ ] The v1/v2 migration matrix is enforced without inferred provenance or in-place manifest promotion.

### Full routing

- [ ] Explicit Full remains Full or stops as unavailable; it never becomes Lite.
- [ ] Failure occurs before scope, Planning Lock, approval, or implementation authority.
- [ ] Full Requirements authority references the verified projected rules.
- [ ] CLI and MCP routes use the same resolver and report the same state.

### Hosts

- [ ] Codex consumes the bundled projection.
- [ ] Copilot consumes the bundled projection.
- [ ] Claude consumes the bundled projection.
- [ ] All hosts record the same official and projection fingerprints.
- [ ] Each host has an explicit reference/copy mode and a complete host projection receipt.
- [ ] Copied projections validate every expected file and reject missing, additional, altered, symlinked, or non-regular entries.
- [ ] No host downloads, rewrites, or substitutes rule content.

### Negative integrity

- [ ] Missing state fails closed.
- [ ] Altered state fails closed.
- [ ] Stale state fails closed.
- [ ] Incompatible state fails closed.
- [ ] Incomplete state fails closed.
- [ ] Unsafe destination state fails closed.
- [ ] Interrupted provisioning leaves no false success marker.

### Distribution proof

- [ ] Source checkout passes the offline Full public-route proof.
- [ ] Installed wheel passes the offline Full public-route proof.
- [ ] Installed source distribution passes the offline Full public-route proof.
- [ ] Built artifacts, not only repository fixtures, are inspected for bundle and integrity metadata.

## Required user-visible report

A successful Full preflight should expose a compact human-readable summary:

```text
Full AIDLC pack
- Source: TailTrail bundled official pack
- Official revision: <tag> (<commit>)
- Trust posture: authenticated-release | development-local | corruption-detection-only | external-explicit
- Artifact identity: verified receipt <reference> | unavailable
- License: MIT-0, verified
- Package integrity: verified
- Official pack integrity: 31/31 files verified
- Project projection: created | reused | external-explicit
- Project manifest: .tailtrail/official-aidlc/packs/<pack-fingerprint>/manifest.json
- Future-run selector: .tailtrail/official-aidlc/current.json
- Host projection: reference | copy (<host-projection-fingerprint>)
- Network used: no
- Host: codex | copilot | claude
- Effective mode: full
```

Verbose output and the Full Start artifact should additionally contain the resolution receipt path and all relevant fingerprints, without dumping full rule contents.

## Risks and trade-offs

### Distribution size

Bundling the complete official pack increases wheel and source-distribution size. This is the intentional cost of reliable offline Full mode. The pack is Markdown and metadata, so the security and operational benefit outweighs modest artifact growth.

### Upstream refresh responsibility

TailTrail becomes responsible for reviewing and releasing pinned upstream refreshes. This is preferable to unpinned runtime downloads, but it requires a documented release process, license review, compatibility testing, and explicit version changes.

### Duplicate project bytes

Atomic projection duplicates the packaged rule bytes under `.tailtrail/`. The duplication preserves existing project-relative bridge semantics, makes host access predictable, and isolates runs from Python environment movement. Direct package-path consumption would reduce duplication but require a wider change to bridge, stage, and host path contracts.

### Stale project projections

A TailTrail upgrade may encounter an older valid projection. Automatically replacing it could change the governing rules for an active run. The design therefore installs new content alongside old content, changes only the future-run selector through controlled migration, and keeps each active run frozen to its exact pack. This uses additional disk space but removes the unsafe choice between overwriting active authority and blocking every old active run.

### Backward compatibility

Supporting legacy project manifests while adding stronger bundled provenance increases validator complexity. Compatibility must be explicit and bounded; missing provenance must never be invented.

## Recommended decisions

1. Use an atomic project projection rather than teaching every consumer to read arbitrary site-packages paths.
2. Use content-addressed project packs plus an atomic future-run selector; never rewrite an active run's pack.
3. Keep `official status` read-only and let Full Start call the shared provisioner.
4. Preserve explicit external packs as advanced overrides.
5. Fail closed for all selected Full routes instead of silently falling back.
6. Use a new bundled-manifest schema with a separate project receipt, run receipt, selector, and host receipt; retain only bounded schema-v1 compatibility.
7. Treat the official pack as data only and never execute pack code.
8. Verify or replace the existing checked-in rules before asserting official provenance.
9. Require an authenticated artifact receipt for `authenticated-release`; label local-only validation truthfully.
10. Deliver the work in dependent phases with requirement-specific owners and proof rather than one broad owner claim.

## Decisions required before implementation

The pinned upstream release is essential, but it is not the only material decision. The following decisions are part of the safety contract and must be owned before their dependent implementation phase begins.

| Decision | Recommended direction | Accountable owner | Required before |
| --- | --- | --- | --- |
| Pinned official tag, full commit, archive digest, and license bytes | Choose one verified upstream release. Never retrospectively label the current files from `VERSION` alone. | Release engineering with Security/Legal review | Phase 1 bundle creation |
| Authenticated TailTrail artifact trust anchor | Reuse the existing GitHub/Sigstore attestation plus exact artifact digest and publication/installation receipt. | Supply-chain/release owner | Any `authenticated-release` claim |
| Behavior when artifact identity is unavailable | Report `corruption-detection-only`; recommended default is to block production Full until policy explicitly permits it. | Product security and lifecycle owner | Phase 2 resolver |
| Source-checkout provider and trust posture | Derive root from `__file__` plus repository sentinels; report `development-local` unless source identity is independently authenticated. | Packaging/resources owner | Phase 2 resolver |
| Bundle/project/run/host schema boundary | Keep immutable bundle manifest, projection receipt, selector, run receipt, and host receipt separate. | Resolver/schema owner | Phase 1 schema and Phase 2 projection |
| Legacy schema-v1 and explicit external-pack policy | No silent v1 promotion; allow only bounded legacy-run continuation or explicit validated external selection. | Runtime compatibility owner | Phase 2 migration support |
| Active-run behavior across upgrade | Add a new content-addressed pack, update only the future-run selector, and preserve frozen active-run bindings. | Lifecycle/runtime owner | Phase 2 migration support |
| Host reference-versus-copy strategy | Declare a mode per Codex, Copilot, and Claude adapter; require complete receipt and inventory verification for either mode. | Host adapter owners | Phase 4 |
| Inferred Full fallback policy | Recommended: every selected Full route fails closed; any Lite fallback requires a separately named, explicit user decision before a Planning Lock. | Product/lifecycle owner | Phase 3 public routing |

The source currently references `v1.0.1` and commit `e49341d` in the network installer, while checked-in `aidlc-rules/VERSION` says `0.1.8`. Neither value proves current-file provenance. Release engineering must choose and verify one official tag and full commit; implementation must not create a manifest that labels unverified bytes as that release.

## Definition of done

The feature is complete only when a user with a normal identity-verified TailTrail installation can enter a new repository, disconnect network access, run an explicit Full AIDLC Start through CLI or MCP on Codex, Copilot, or Claude, and reach the official Requirements stage using the bundled pinned rules. The report must show the artifact-identity receipt, truthful trust posture, verified license, provenance, hashes, frozen project projection, host projection, and `effective_mode: full`.

The same release must reject every missing, altered, stale, incompatible, incomplete, unsafe, or interrupted state before creating planning or implementation authority. Wheel, source distribution, source checkout, host projections, and public negative routes must all have executable proof.
