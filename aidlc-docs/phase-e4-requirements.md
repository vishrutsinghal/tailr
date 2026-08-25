# Enterprise Phase E4 Requirements

Authority: `ENTERPRISE-READINESS-ASSESSMENT.md` Phase E4 and
`enterprise-closure-registry.json` requirements ENT-E4-001 through ENT-E4-003.

## Approved boundary

The user's explicit end-to-end E4 request approves requirements, workflow, and
implementation for Codex, GitHub Copilot, and Claude adapters. E5 operating
system qualification and E10 real-host observations remain separate gates.

## Requirements

- ENT-E4-001: Codex uses the E3 engine with an exact Core manifest, composition
  checks, diagnostics, native first action, update, rollback, uninstall,
  version limitation, and receipt preparation.
- ENT-E4-002: Copilot has equal lifecycle quality and states that CI—not model
  cooperation—is authoritative for enforceable policy.
- ENT-E4-003: Claude has non-empty required files, a native first action,
  installed-target diagnostics, complete lifecycle behavior, and receipt
  preparation; the empty first-run mapping defect is closed.
- All hosts use one precedence order and one adapter version. Core is default;
  Extended is additive.
- Global settings, network activity, and account changes remain out of scope
  and approval-required.
- Qualification states remain independent: contract-tested cannot imply
  runtime-observed or supported.

## Acceptance

All three hosts pass the same contract, lifecycle, composition, drift,
conflict, missing-file, migration, rollback, uninstall, negative-assurance,
installed-product, and portable receipt tests. Generated surfaces are current,
and release/package inventories contain every E4 product file.
