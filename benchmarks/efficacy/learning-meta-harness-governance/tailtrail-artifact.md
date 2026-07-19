# TailTrail Output

Learning review:

- Matching learning found: `sonar-java-complexity-extract-guards`
- Confidence: `62`
- Status: suggest with caution
- Advisory only: current source, tests, CI, scanner output, policy, guardrails, and explicit user instructions win.

Learning decision: do not apply automatically. Ask the user to approve `use learnings`, `ignore learnings`, or `edit plan`.

Meta-Harness readiness:

- Decision: `advise_repo_maintainer`
- Registry status: healthy
- Proposal status: no central TailTrail change yet
- Reason: evidence is useful locally but not enough repeated sanitized evidence for a central product change.

Rollback: if a future proposal is accepted and degrades Navigator behavior, revert the proposal commit and record the proposal as rolled_back.
