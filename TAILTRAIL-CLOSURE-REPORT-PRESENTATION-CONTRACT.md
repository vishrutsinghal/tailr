# TailTrail Closure Report Presentation Contract

## Purpose

The user-facing TailTrail Closure Report must explain the completed run in
plain Markdown. It is the readable conclusion of a run, not a dump of the
saved closure payload. Structured JSON remains available for forensic and
machine consumers in a separate technical audit artifact.

## Required report structure

Every successful closure report must render these sections, in this order:

1. **Run summary** — run ID, title or goal, final status, request mode,
   completion time when recorded, and whether source changes were expected.
2. **Outcome** — a short plain-language statement of what was delivered and
   which approved requirement outcomes were satisfied.
3. **Requirements and verification** — one readable row per requirement with
   its result, asserted behavior, and linked proof or an explicit reason it
   could not be verified.
4. **Testing performed** — every recorded proof command, its validation tier,
   execution result, and receipt/evidence quality. Do not imply a command ran
   when no corresponding result is saved.
5. **Code and artifact changes** — actual changed source paths and generated
   delivery artifacts. When a validation-only or read-only run made no source
   edit, say so plainly.
6. **Token and context usage** — show TailTrail’s planned token/context
   estimate and any measured host/provider consumption separately. If measured
   telemetry is unavailable, say it is unavailable; never label an estimate as
   consumed tokens.
7. **Scope and safeguards** — approved owner, inspection, proof-only, and
   excluded paths, plus applicable safety or policy outcomes.
8. **Out-of-scope findings requiring follow-up** — only confirmed,
   evidence-backed critical findings encountered in the host code that were
   outside the approved scope. Include impact and recommended next action. If
   none were recorded, say `No confirmed critical out-of-scope findings were
   recorded.` Do not manufacture findings from hypotheses or raw diagnostics.
9. **Final decision** — completion decision, any remaining limitation, and
   the next action when closure is incomplete or blocked.
10. **Technical evidence** — links or paths to the preserved JSON receipts and
    full technical audit artifact. This section must not inline a large JSON
    payload.

## Data and authority rules

- The report is a projection of saved canonical state, approved scope,
  requirement/proof bindings, managed evidence, and recorded closure facts.
  It must not invent a test result, token measurement, code change, finding,
  or requirement status.
- Human-readable prose is a presentation layer. It cannot override canonical
  completion state or turn declared evidence into trusted evidence.
- Each rendered requirement and proof entry must preserve its canonical
  identifier so the reader can trace it to the technical record.
- Render compact tables or lists for recurring items. Empty categories must
  use explicit, accurate prose rather than disappear silently.
- Keep full raw JSON out of the main `closure-report.md`. Save or retain it as
  a distinct technical audit artifact and link it from the report.

## Compatibility and safety requirements

- The report must work for implementation, validation-only, and read-only
  runs without assuming source changes exist.
- Existing closure validity, receipts, safeguards, and machine-readable
  artifacts remain unchanged; this work changes only the human projection and
  its regression coverage.
- Missing optional telemetry or findings must render honestly and must not
  block a valid closure solely because they are absent.
- A test must exercise the actual closure-report generation path and prove
  that the main report contains the readable sections while the raw technical
  payload remains separate.
