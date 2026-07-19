# TailTrail Build Week Video Outline

This is an optional visual outline for the required three-minute Build Week demo
video. It is not a required PowerPoint submission. Use title cards or a few
simple slides only when they make the live product demo easier to follow.

## 0:00-0:20 - The problem

**Title:** AI coding needs a local control layer

Show one sentence:

> Coding agents need focused context, explicit approval, and evidence that the
> change was actually validated.

Say that TailTrail is a local, approval-first workflow for Codex. Do not claim it
replaces CI, tests, security review, or human review.

## 0:20-0:45 - Show the real bug

Show the claims-service test failure: a zero-dollar claim is accepted despite the
positive-amount requirement.

Message: this is a small task, so TailTrail should keep the workflow small.

## 0:45-1:20 - Navigator and focused context

Show the Navigator output, then the Code Graph result for
`src/claims_api/validation.py`.

Message: TailTrail plans before editing, identifies the relevant validation
function and likely tests, and waits for approval before implementation.

## 1:20-2:05 - Codex implements the approved change

Show Codex receiving the approved plan, reading the focused files, and changing
`amount < 0` to `amount <= 0`. Then show the focused tests passing.

Message: Codex and GPT-5.6 are used for the coding step; TailTrail supplies the
local workflow and evidence boundaries around it.

## 2:05-2:30 - Review

Show the post-change review.

Message: the review checks code health and whether the original requirement was
fulfilled. It does not silently apply more fixes.

## 2:30-2:50 - Repeatable proof

Show `eval scenario report --scenario buildweek-validation`.

Message: this is deterministic saved-artifact evidence for the demo story. It
does not prove live model performance or exact token savings.

## 2:50-3:00 - Close

> TailTrail helps Codex make smaller, approval-first changes with focused
> validation and reviewable local evidence.

## Recording checklist

- Record a public YouTube video under three minutes with clear English audio.
- State what TailTrail does, show the working demo, and explain how Codex and
  GPT-5.6 are used.
- Use no unlicensed music or third-party trademarks.
- Prefer large terminal text and pre-recorded fallback clips for each command.
