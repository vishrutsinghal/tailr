# TailTrail Quality Loop

Quality Loop is the reviewable feedback loop for TailTrail behavior.

It is not self-healing automation. It observes compact approved events, summarizes patterns, and proposes improvements that a user or maintainer must review before changing TailTrail rules, prompts, Navigator behavior, or local policy.

## Use When

- TailTrail workflow choice may be drifting.
- Navigator chose too much process for a small task.
- Navigator skipped a needed gate for risky work.
- Review, QA, handoff, AIDLC, dependency gate, learning, or token routing overlapped.
- Users repeatedly reject or revise TailTrail plans.
- A team wants evidence before tuning TailTrail behavior.

## Do Not Use When

- The task is ordinary implementation and no TailTrail behavior review is needed.
- The user has not approved recording a quality event.
- The only available evidence is raw prompt text, raw logs, secrets, PII, PHI, or customer data.

## Files

- `.tailtrail/quality-events.jsonl`: compact approved local behavior events.
- `.tailtrail/quality-summary.md`: generated quality summary for review or Navigator tuning.
- `.tailtrail/quality-decisions.md`: approved or rejected decisions about TailTrail usage rules.

## Commands

```bash
python3 scripts/tailtrail.py quality-loop capture --workflow review,qa --fit correct --outcome accepted --approved
python3 scripts/tailtrail.py quality-loop summarize --month 2026-07 --write-result
python3 scripts/tailtrail.py quality-loop review --month 2026-07
python3 scripts/tailtrail.py quality-loop propose --month 2026-07
python3 scripts/tailtrail.py quality-loop decide --area navigator --decision "Skip AIDLC for tiny docs-only tasks." --approved
```

## Rules

- Capture writes require `--approved`.
- Without `--approved`, capture prints the event shape and records nothing.
- Do not store full raw prompts by default.
- Do not store secrets, credentials, PII, PHI, customer data, or raw logs.
- Do not infer user satisfaction from silence.
- Do not apply proposed changes automatically.
- Do not load `.tailtrail/quality-events.jsonl` into routine coding prompts.
- Use `.tailtrail/quality-summary.md` only for quality review, Navigator tuning, or local policy review.

## Signals

Record compact signals only:

- workflow selected and skipped
- recommendation source
- workflow fit: `too-heavy`, `too-light`, `correct`, or `unknown`
- user outcome: `accepted`, `rejected`, `revised`, `partially-accepted`, or `unknown`
- validation outcome: `pass`, `fail`, `not-run`, or `unknown`
- overlap flags
- missed gate flags
- improvement suggestion

## Proposal Boundaries

Quality Loop proposals should show:

- issue
- evidence
- proposed files that may be impacted
- prompt or rule change
- review note

Every proposal is advisory. Review before editing TailTrail files, prompts, Navigator rules, or local policy.
