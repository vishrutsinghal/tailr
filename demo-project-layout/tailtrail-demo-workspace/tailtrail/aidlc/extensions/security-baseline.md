# Security Baseline

Use this extension when the change touches authentication, authorization, secrets, user data, external input, network calls, file handling, dependency changes, or production configuration.

## Check

- Trust boundaries are identified.
- Authorization and authentication behavior is preserved or strengthened.
- Input validation and output escaping are preserved.
- Secrets are not logged, cached, committed, or placed in generated artifacts.
- Sensitive data handling follows project policy.
- Dependency changes pass `DEPENDENCY-GATE.md`.
- Errors fail safely without hiding actionable diagnostics.

## Handoff

Record security-sensitive decisions in `aidlc-docs/audit.md` and summarize remaining risk in the active handoff file.
