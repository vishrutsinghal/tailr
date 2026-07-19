# TailTrail Local Policy Example

Copy this file to `tailtrail-policy.md` in a target project when the team needs local TailTrail rules. Keep the policy short, reviewable, and specific to the repository.

This file is guidance, not a hidden policy engine. It can extend TailTrail rules but should not silently weaken `GUARDRAILS.md`, `DEPENDENCY-GATE.md`, or explicit user requirements.

## Project Scope

Project name:

Primary owners:

Primary language and framework:

Generated or vendor folders to avoid:

Restricted files or folders:

## Local Commands

Use these commands when relevant and available:

- Format:
- Lint:
- Type check:
- Unit test:
- Focused test:
- Build:
- Security scan:

If a command is unknown, say it is unknown instead of inventing one.

## Dependency Policy

Before adding, upgrading, replacing, or removing dependencies:

- Apply `DEPENDENCY-GATE.md`.
- Prefer standard library, platform-native, framework, database, cloud, or installed dependency capabilities.
- Record owner, reason, version, validation, and rollback/removal note for approved dependency changes.

Project-specific dependency notes:

- Approved package sources:
- Restricted package types:
- Required approval owner:

## Testing And Validation

Minimum validation expectation:

- Small code-only change:
- Behavior change:
- API or contract change:
- Dependency change:
- Security-sensitive change:
- Data or migration change:

Validation gaps must be named in the handoff.

## Security And Data

Project-specific security requirements:

- Authentication:
- Authorization:
- Secrets:
- User/customer data:
- Logging:
- Error handling:

Do not include secrets, credentials, PII, PHI, customer data, or raw sensitive logs in generated artifacts.

## API And Code Conventions

Naming conventions:

Error handling conventions:

Validation conventions:

Testing conventions:

Accessibility requirements:

Observability or logging conventions:

## Review And Handoff

Use review when:

Use handoff when:

Required reviewers or owners:

Required handoff fields:

## CI, Sonar, And Release

CI expectations:

Sonar/static-analysis expectations:

Release or deployment notes:

Rollback expectations:

## Local TailTrail Overrides

Optional prompt overrides may live in:

- `.tailtrail/intent-overrides.json`
- `tailtrail/intent-overrides.json`

Use overrides only for narrow prompt wording, load lists, avoid lists, run order, validation notes, or local workflow preferences.

Optional structured policy overrides may live in:

- `.tailtrail/policy-overrides.json`

Use structured policy overrides only for simple local metadata such as required commands, reviewers, restricted paths, generated paths, dependency approval expectations, and release notes. Keep the Markdown policy as the human-readable source of truth.

## Token Harness Bridge

Runtime compression bridge is disabled by default. Enable it only when the team has approved a local adapter and understands that TailTrail validates adapter output but does not own or bundle the compressor.

runtime_compression_bridge: disabled
adapter_command: ""
allowed_content_types:
- log
- documentation
- scanner-output
- json
- tool-output
max_input_bytes: 250000
require_approval: true

Never route source, diffs, dependency manifests, lock files, security policy, secrets, or unknown content through a runtime compression adapter.

## Code Intelligence Policy

Provider-backed Semantic V3 ingestion is disabled by default. Enable it only when the team has approved local provider JSON exports and reviewed what metadata they contain.

provider_backed_semantic_ingestion: disabled
require_provider_ingestion_approval: true
allowed_provider_outputs:
- tailtrail-meta/providers/

Semantic V3 must not start JDT, Roslyn, language servers, SCIP, tree-sitter, SQL parsers, Terraform parsers, MCP providers, networked services, or repo-owned extractors. It may only ingest approved local JSON provider outputs.
