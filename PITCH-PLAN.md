# TailTrail Build Week Pitch Package

This document is the final source of truth for the Build Week submission
materials. The required submission is a working project, a public YouTube demo
video under three minutes with audio, a repository judges can access, a project
description, and the primary Codex `/feedback` Session ID entered in Devpost.

## Submission assets

| Asset | File or destination | Purpose |
|---|---|---|
| Judge README | `buildweek-demo-project/README.md` | Setup, supported platforms, exact commands, and no-rebuild test path. |
| Submission description | `buildweek-demo-project/SUBMISSION-NOTES.md` | Copy into the Devpost project description. |
| Submission checklist | `buildweek-demo-project/BUILDWEEK-SUBMISSION.md` | Final Devpost and repository checklist. |
| Recording runbook | `buildweek-demo-project/DEMO-RUNBOOK.md` | 2:45 live workflow. |
| Recording prompts | `buildweek-demo-project/DEMO-PROMPTS.md` | Copy-paste prompts for the Codex portion of the recording. |
| Video script | `PITCH-SCRIPT.md` | Spoken narration for the public YouTube video. |
| Optional visual outline | `PITCH-DECK-OUTLINE.md` | Title cards or supporting slides; no PowerPoint is required. |
| One-page overview | `PITCH-ONE-PAGER.md` | Shareable product summary. |

## Required recording story

1. Show the intentionally failing zero-dollar-claim test.
2. Show TailTrail Navigator producing the plan before an edit.
3. Show Code Graph narrowing the context to the validation function and focused
   test.
4. Show Codex using GPT-5.6 make the approved one-line fix.
5. Show the focused tests and the post-change review.
6. Show `buildweek-validation` as repeatable local saved-artifact evidence.
7. State the claim boundary: it does not prove live model performance or exact
   token savings.

## Claim boundaries

Use this public description:

> TailTrail helps teams use Codex with a local, approval-first workflow for
> focused code context, validation, review, and evidence.

Do not claim that TailTrail replaces tests, CI, scanners, security review, or
human review. Do not claim exact token savings without measured provider
telemetry. The Evaluation Harness scenario compares committed artifacts; it is
not a live-model or production-outcome benchmark.

## Submission-day order

1. Run the recording once from a clean demo state.
2. Upload the finished video to YouTube as a public video.
3. Verify the repository is public, or share the private repository with
   `testing@devpost.com` and `build-week-event@openai.com`.
4. Copy `SUBMISSION-NOTES.md` into Devpost.
5. Paste the public YouTube URL and the primary Codex `/feedback` Session ID
   into Devpost.
6. Use `BUILDWEEK-SUBMISSION.md` for the final check.
