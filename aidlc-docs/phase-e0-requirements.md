# Enterprise Phase E0 Requirements

Status: approved by the user's explicit request to implement Enterprise Phase
E0 end to end on 2026-08-22.

Lifecycle depth: comprehensive.

## Goal

Establish one auditable enterprise stabilization baseline with complete
ownership, maturity, inventory, defect, phase, validation, and release-candidate
disposition before later enterprise implementation changes the product boundary.

## Requirements

1. `ENT-E0-001` declares the authority document, exact Git baseline, branch,
   worktree state, release-candidate state, and disposition of every untracked
   path without deleting or silently adopting user work.
2. `ENT-E0-002` provides a versioned machine-readable closure registry, JSON
   Schema, deterministic validator, readable status, and JSON inventory.
3. `ENT-E0-003` inventories public commands, schemas, adapters, persisted state
   literals, CI controls, install profiles/surfaces, release files, support
   claims, and registered features by reusing existing authoritative sources.
4. `ENT-E0-004` gives every registered feature an enterprise maturity through
   an explicit normalization policy while preserving the existing Core or
   Extended classification.
5. `ENT-E0-005` activates a feature freeze through E12. Only correctness,
   security, packaging, compatibility, release, support, and evidence changes
   are allowed inside the program.
6. `ENT-E0-006` assigns every E0-E12 closure requirement and every known test,
   package, release, smoke, install, platform, and host-proof defect to an owner,
   priority, phase, implementation path, validation obligation, acceptance
   condition, maturity, and status.

## Safeguards

- The registry must not claim GA, production provider readiness, real-host
  conformance, clean release state, or resolved defects without evidence.
- Local and user-owned untracked files must be preserved and classified, never
  deleted, staged, or silently included.
- E0 must reuse the existing feature registry rather than create a competing
  command/script ownership source.
- Inventory is read-only and must not create workflow state, contact providers,
  execute scanners, or mutate a target repository.
- Completed E0 requirements require evidence references; future requirements
  remain planned until their actual gates pass.
- No dependency may be added for registry or schema validation.

## Acceptance

- Registry validation fails for duplicate requirement IDs, missing owners,
  invalid/missing phases, unknown or later-phase dependencies, empty validation
  and acceptance lists, completed items without evidence, invalid maturity,
  missing inventory categories, and unclassified untracked files.
- All phases E0-E12 have owned requirements.
- Every existing feature maps to a known enterprise maturity.
- Codex, Copilot, Claude, Core, and Extended are present in the inventory.
- Release-file inventory reports missing files truthfully instead of converting
  absence into success.
- The top-level TailTrail CLI exposes validate, status, and JSON inventory.
- Focused tests and existing strict feature-registry validation pass.

## Non-goals

- Fixing E1 defects.
- Building the E2 package or E3 installer.
- Activating or deploying an enterprise provider.
- Recording fabricated host receipts or changing current release eligibility.
- Staging, committing, pushing, deleting, or adopting unrelated user files.

