# Support

This file explains the public support boundary for TailTrail.

## Supported

- Latest public `master` branch until tagged releases are introduced.
- Latest tagged public release after tags are introduced.
- Source checkout usage with `python3 scripts/tailtrail.py`.
- Self-contained wheel and sdist installs on CPython 3.12 and 3.13.
- The `tailtrail` console command, resource-integrity check, and stable Python
  API named in `PACKAGE-CONTRACT.md`.
- Transactional Codex, Copilot, and Claude repository projection through the
  plan, ownership, backup, recovery, rollback, and uninstall contract in
  `INSTALLER-LIFECYCLE.md`.
- Contract-tested v3 Codex, Copilot, and Claude Core adapters as defined in
  `HOST-ADAPTERS.md`; this is local contract support, not a claim that a named
  host version or operating-system matrix is runtime-observed.
- Documented local commands, public docs, and assistant adapter files.
- Release candidates that pass the shared `release-manifest.json` gates in `.github/workflows/trust.yml`.
- Linux, macOS, and Windows are release-supported for a specific commit only
  when its exact CPython 3.12/3.13 hosted receipt aggregate passes. Until those
  receipts exist, the workflow is configured but platform support is not
  claimed.
- Canonical wheels and sdists whose hashes, CycloneDX SBOM, provenance
  candidate, locked build inputs, and tag identity attestations satisfy
  `SUPPLY-CHAIN.md`.
- Reproducible issues with redacted command output.

## Not Supported By Default

- Private company CI systems.
- Proprietary scanner behavior.
- Assistant-specific behavior that ignores repository instructions.
- Runtime-observed or release-supported Codex, Copilot, or Claude versions
  until the E5 and E10 matrices pass.
- Unreviewed forks or modified distributions.
- Central telemetry, dashboards, hosted services, or package-manager installs
  other than the released wheel and sdist.
- Local or simulated platform runs presented as hosted support evidence.
- Unsigned rebuilds, artifacts whose checksum or attestation does not verify,
  and publication-time artifact rebuilds.

## Asking For Help

Use the public issue templates for non-sensitive bugs, feature requests, and docs feedback.

Do not post secrets, private code, customer data, PII, PHI, exploit details, private logs, or sensitive scanner output in public issues. Use `SECURITY.md` for vulnerability reports.

Before opening an issue, try self-service by role (see "Role-Based Quick Start"
below): run `doctor`, follow the diagnostic it prints, and only escalate if the
documented remediation does not resolve it.

## Role-Based Quick Start

Every role below reuses the same underlying commands; this is a routing index,
not a separate product surface.

- **Developer**: `tailtrail start "<goal>"` for planning, `tailtrail doctor`
  when something looks wrong, `TAILTRAIL-COMMANDS.md` for the full command
  catalog, and `CHEATSHEET.md` for short-form syntax.
- **Repository administrator**: `INSTALL.md` for install/update/rollback,
  `tailtrail-enforcement-policy.json` plus `repository-enforcement.py explain`
  for the effective policy, and `DEPENDENCY-GATE.md` before approving new
  dependencies.
- **Security reviewer**: `SECURITY.md` for reporting and severity/response
  timelines, `GUARDRAILS.md` and `aidlc-docs/phase10-threat-model.md` for the
  threat model and mitigations, and `enforce` CLI output for enforced vs.
  advisory controls.
- **Platform/enterprise administrator**: the "Enterprise Adapter
  Administrator Runbook" below, `INSTALLER-LIFECYCLE.md` for the transactional
  install/update/rollback contract, and `HOST-ADAPTERS.md` for per-host rollout
  behavior.
- **Auditor**: `enterprise support-bundle` for a sanitized, integrity-checked
  evidence bundle, `enterprise access-review` for the approved allowlist, and
  `PUBLIC-CLAIMS.md` for what evidence labels (`measured`, `estimated`,
  `advisory`, and so on) mean.
- **Support operator**: run `doctor` first; if it reports a specific failing
  check, follow that check's own remediation text rather than guessing. Ask
  for the redacted host, profile, transaction ID, `status`, and `doctor`
  result before escalating (see "Maintainer Expectations" below).

## Maintainer Expectations

Maintainers should ask for minimal redacted reproduction details, avoid collecting sensitive data, and separate public support from private enterprise support agreements.
Installer incidents should include the redacted host, profile, transaction ID,
`status`, and `doctor` result. Retained transactions should not be deleted until
the affected update, recovery, rollback, or uninstall is resolved.

## Enterprise Adapter Administrator Runbook

This is the minimum operational runbook for the optional local, provider-neutral
enterprise adapter (`scripts/workflow_runtime/enterprise*.py`). It is scoped to
what the local adapter can actually do; it is not a claim of a deployed remote
service, on-call rotation, or SLA.

1. **Diagnose.** Run `workflow-runtime.py enterprise conformance --root <path>
   --workflow-id <id>` (or the `workflow_enterprise_conformance` MCP tool).
   A `blocked` status lists the exact failing categorical checks
   (for example `replay`, `backup-and-restore`).
2. **Review access.** Run `enterprise access-review --root <path> --workflow-id
   <id>` to see the exact tenant/actor/repository allowlist the workflow is
   bound to, before assuming an authorization problem.
3. **Export evidence for handoff.** Run `enterprise support-bundle --root
   <path> --workflow-id <id> --approved` to produce one sanitized,
   integrity-fingerprinted bundle combining conformance, observability, and
   access-review. Verify it later with `enterprise support-bundle-verify
   --bundle-ref <path>` before relying on it — this also detects tampering.
4. **Explain policy.** Run `repository-enforcement.py explain --root <path>`
   to see the exact merged rule catalog (classification, severity, protected
   paths) currently in effect, including any repository overrides.
5. **Break-glass boundary.** There is no privileged bypass command. Every
   mutating enterprise operation (`activate`, `ingest`, `backup`, `migrate`,
   `rollback`, `support-bundle`) already requires `--approved`; an operator
   cannot skip approval, and TailTrail records the resulting event in the
   local run ledger rather than a separate audit system.
6. **Segregation of duties.** The person diagnosing (`conformance`,
   `access-review`, `explain`) never needs write access; only the person
   applying a change needs the `--approved` flag. Keep these separated in
   practice even though the local adapter does not enforce it technically.

This runbook does not cover a real deployed provider's on-call rotation,
paging, SLA, or incident-response process; those remain explicit gaps until an
actual enterprise provider is selected and qualified (Phase E8).
