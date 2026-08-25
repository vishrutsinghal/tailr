# Enterprise Phase E0 Design

## Decision

Use a dedicated `enterprise-closure-registry.json` for program closure while
retaining `tailtrail-registry.json` as the authoritative feature, command, and
script registry. The enterprise validator composes both sources and fails when
ownership, maturity, phase, inventory, evidence, or candidate disposition is
unknown.

## Components

### Closure registry

The closure registry owns:

- program authority and feature-freeze state;
- exact candidate baseline and local-file dispositions;
- feature-status to enterprise-maturity normalization;
- inventory contracts and their owners;
- E0-E12 requirements and dependencies;
- known defects and their owning closure requirements.

It does not duplicate every feature-registry command or script entry. Instead,
the inventory projection reads the existing authoritative registry and source
surfaces so drift remains detectable.

### Schema

The Draft 2020-12 schema documents the closed record shape, allowed phases,
priorities, maturity states, requirement states, inventory categories, feature
freeze, candidate dispositions, and defect linkage. The standard-library
validator provides semantic checks that JSON Schema alone cannot express,
including dependency direction, current repository coverage, documentation
phase coverage, and untracked path classification.

### Validator and inventory

`scripts/enterprise-readiness.py` provides:

- `validate`: strict semantic validation with non-zero failure status;
- `status`: concise E0 gate and requirement/defect state;
- `inventory`: full JSON projection of the current enterprise surface.

Discovery is deterministic and read-only:

- Python AST for public command roots;
- repository enumeration and JSON parsing for schemas;
- adapter-directory and canonical-host surface enumeration;
- source literal projection for `.tailtrail` persisted artifacts;
- workflow named-step projection for CI controls;
- installer tuple parsing for profiles and Core/Extended surfaces;
- exact present/missing projection for declared release files;
- section-aware bullet projection for support and public claims;
- feature registry projection with normalized enterprise maturity.

### CLI and feature registry

The public source-checkout command is:

```text
tailtrail enterprise-readiness validate|status|inventory
```

The feature is Extended because it governs TailTrail's own enterprise release
program rather than the target-repository Core workflow. Its implementation,
documentation, and focused tests are claimed in the existing feature registry.

## Failure behavior

Validation fails closed for malformed structure, missing authority, incomplete
phase coverage, duplicate IDs, missing owners or validation, invalid maturity,
unknown/later dependencies, unclassified local files, missing canonical host
surfaces, empty state/CI/claim inventories, invalid schema JSON, missing install
profiles/surfaces, or incomplete completion evidence.

Known missing release files and future enterprise work remain explicit planned
or open records. Their presence does not make E0 invalid because E0's purpose is
complete truthful classification; E1-E12 own their remediation and proof.

## Dependencies and privacy

The implementation uses only the Python standard library and existing TailTrail
sources. It does not add a dependency, network call, provider integration,
telemetry upload, scanner, or background service. Inventory output contains
repository metadata and public policy text, not raw prompts, source bodies,
secrets, or runtime logs.

## Recovery

E0 adds versioned additive files and narrow CLI/registry documentation entries.
Recovery is a normal source revert of the E0-owned paths. Unrelated untracked
files are outside TailTrail ownership and must remain untouched.

