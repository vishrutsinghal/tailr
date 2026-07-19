# TailTrail Public Release Checklist

Use this checklist before any open-market release.

## Required Before First Public Release

- [x] Confirm final public license choice is recorded in `PUBLIC-RELEASE-METADATA.md`.
- [x] Confirm `.codex-plugin/plugin.json` uses the same license identifier.
- [x] Confirm `NOTICE.md` contains accurate provenance and attribution.
- [x] Confirm `PUBLIC-CLAIMS.md` matches current product capability and evidence.
- [x] Replace the temporary security contact in `SECURITY.md` with the final public reporting path.
- [ ] Run `python3 scripts/tailtrail.py doctor`.
- [ ] Run `python3 scripts/release-check.py`.
- [ ] Run `git diff --check`.
- [ ] Confirm no `.DS_Store`, `__pycache__`, `.tailtrail/`, private logs, secrets, benchmark generated outputs, or local state are tracked.
- [ ] Confirm no proprietary company code, internal-only policy text, private repo names, credentials, tokens, PII, PHI, customer data, or sensitive logs are present.
- [ ] Confirm README quick start works from a fresh clone.
- [ ] Confirm `python3 scripts/tailtrail.py start "fix Sonar issue" --changed path/to/file` behaves safely when the file does not exist.
- [ ] Confirm public docs do not claim exact token savings unless measured model/API telemetry is provided.
- [ ] Confirm public docs do not imply TailTrail replaces tests, CI, scanners, code review, security review, legal review, or compliance approval.
- [ ] Tag the release only after the checklist is complete.

## Recommended Before Broad Promotion

- [x] Add GitHub issue templates.
- [x] Add a changelog.
- [ ] Add tagged release notes.
- [x] Add a public demo walkthrough.
- [x] Add a short architecture diagram.
- [x] Add a compressed public roadmap.
- [x] Add a public documentation audit.
- [x] Add a fresh-clone smoke test script.
- [x] Add CI that runs `scripts/check-tailtrail.py`, `scripts/tailtrail.py release-check`, adapter sync, and Python compile checks.
- [ ] Add package distribution only after the local Python entry point is stable.

## Release Positioning

Describe TailTrail as:

- local-first
- documentation-first
- assistant-agnostic
- approval-first
- token-aware, not token-magic
- learning-aware, not self-training
- scanner-aware, not a scanner replacement
