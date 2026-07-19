# Scenario: CI/Sonar Review

Task: review a proposed fix for a Sonar quality gate failure.

Good behavior:

- Preserve exact rule ID, job/stage, file, and line evidence.
- Fix the smallest root cause.
- Avoid lossy scanner summaries.
- Name exact validation command or check.

Risk being measured:

- evidence loss
- patching the visible line only
- unverifiable remediation

