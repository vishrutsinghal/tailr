# Dependency Gate

Use this gate before adding, upgrading, replacing, or introducing a runtime, build, test, infrastructure, or UI dependency.

Use `GUARDRAILS.md` with this gate for validation truth, exact package/version handling, approval boundaries, and safeguard preservation.

If `tailtrail-policy.md` exists, apply its local dependency approval owners, restricted package types, approved sources, validation expectations, and rollback requirements.

## Default Position

Do not add a dependency unless it clearly reduces risk, complexity, maintenance burden, or security exposure compared with using what the project already has.

## Gate Questions

Answer these before adding the dependency:

- What exact problem does it solve?
- Is the problem already solved by the standard library, platform, framework, database, cloud service, or installed dependency?
- Is a small direct implementation safer and easier to own?
- What code will this dependency replace or prevent?
- What new operational, security, license, upgrade, bundle-size, runtime, or supply-chain risk does it add?
- Who owns upgrades and vulnerability response?
- What focused validation proves the dependency is wired correctly?

## Decision

Use one of these outcomes:

- **Reject**: existing capability or direct code is smaller and safe.
- **Defer**: dependency might be useful, but current scope does not justify it.
- **Approve**: dependency materially reduces risk or complexity and has an owner.

## Required Handoff

When approved, record:

- package name and version or version range
- reason for approval
- alternatives considered
- ownership and upgrade expectation
- validation run
- rollback or removal note

Never remove validation, authorization, escaping, data integrity, accessibility, or error-handling guards just to avoid a dependency.
