# Support

This file explains the public support boundary for TailTrail.

## Supported

- Latest public `main` branch until tagged releases are introduced.
- Latest tagged public release after tags are introduced.
- Source checkout usage with `python3 scripts/tailtrail.py`.
- Documented local commands, public docs, and assistant adapter files.
- Reproducible issues with redacted command output.

## Not Supported By Default

- Private company CI systems.
- Proprietary scanner behavior.
- Assistant-specific behavior that ignores repository instructions.
- Unreviewed forks or modified distributions.
- Central telemetry, dashboards, hosted services, or package-manager installs that are not part of the release.

## Asking For Help

Use the public issue templates for non-sensitive bugs, feature requests, and docs feedback.

Do not post secrets, private code, customer data, PII, PHI, exploit details, private logs, or sensitive scanner output in public issues. Use `SECURITY.md` for vulnerability reports.

## Maintainer Expectations

Maintainers should ask for minimal redacted reproduction details, avoid collecting sensitive data, and separate public support from private enterprise support agreements.
