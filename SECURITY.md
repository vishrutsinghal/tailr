# Security Policy

TailTrail is a local, documentation-first development helper. It should not upload project code, logs, prompts, scanner output, secrets, or learning history by default.

## Supported Versions

Security fixes are handled on the latest public `main` branch until tagged releases are introduced.

## Reporting A Vulnerability

Please do not open a public issue for suspected vulnerabilities that include exploit details, secrets, private code, credentials, customer data, or sensitive logs.

Use GitHub private vulnerability reporting from this repository's **Security** tab. If private vulnerability reporting is unavailable for your fork or mirror, contact the repository maintainers through the non-public maintainer channel listed by that distribution owner.

Include:

- affected TailTrail version or commit
- affected file or command
- impact and reproduction steps
- whether any sensitive data may be involved
- suggested remediation, if known

## Security Boundaries

TailTrail is designed to:

- run locally
- avoid background services
- avoid hidden telemetry
- avoid automatic scanner execution
- avoid automatic learning capture
- ask before broad, networked, credentialed, or scanner-like commands
- label token savings as approximate unless measured model/API telemetry exists

TailTrail is not designed to:

- replace code review
- replace security review
- replace SAST, dependency, secret, container, or IaC scanners
- guarantee vulnerability remediation
- make deployment or release approval decisions
- store secrets, raw prompts, private logs, PII, PHI, or customer data

## Maintainer Response

Maintainers should:

1. Acknowledge reports privately.
2. Reproduce using local evidence only.
3. Avoid requesting sensitive user data.
4. Patch with the smallest safe change.
5. Add or update validation in `scripts/check-tailtrail.py` or `scripts/release-check.py`.
6. Publish a clear security note when a release is issued.
