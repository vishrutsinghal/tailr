# TailTrail Intent Aliases

TailTrail intent aliases let users ask for a full workflow with a short phrase.

The resolver is `scripts/expand-intent.py`. It converts phrases such as `use AIDLC`, `use review`, or `use AIDLC and review` into a concrete TailTrail flow with:

- internal prompt text
- files to load
- files to avoid
- run order
- optional validation commands
- override source, when customized

## Supported Flows

| Flow | Common User Phrases | Purpose |
|---|---|---|
| `hello` | `hello tailtrail`, `hello TailTrail`, `hello taitrail`, `tailtrail hello`, `hi tailtrail`, `ping tailtrail` | Run the TailTrail install smoke check and show the banner/status output. |
| `implementation` | `use tailtrail`, `implement`, `small change`, `fix this` | Normal TailTrail coding discipline. |
| `delivery` | `use delivery flow`, `feature flow`, `end-to-end flow` | Plan, implement, validate, review, and hand off meaningful feature work. |
| `risk` | `use risk flow`, `risk review`, `production risk` | Review dependency, security, validation, data integrity, rollout, and ownership risk. |
| `review` | `use review`, `tailtrail review`, `review this diff` | Review changed code for risk, duplication, dependency drift, broad rewrites, and missing checks. |
| `architecture_review` | `use architecture review`, `data flow review` | Review boundaries, data flow, coupling, and blast radius. |
| `security_review` | `use security review`, `auth review` | Review trust boundaries, auth, secrets, input handling, escaping, and privacy. |
| `qa_review` | `use QA review`, `validation review` | Review regression paths, manual checks, automated checks, and validation evidence. |
| `maintainability_review` | `use maintainability review`, `simplicity review` | Review duplication, unnecessary abstractions, readability, and ownership burden. |
| `dependency_review` | `use dependency review`, `package review` | Review dependency additions, upgrades, replacements, and package risk. |
| `dependency` | `use dependency gate`, `check dependency`, `can we add this package` | Apply the dependency gate before adding or recommending a package. |
| `aidlc` | `use aidlc`, `run aidlc`, `aidlc standard` | Use lifecycle structure for broad, risky, ambiguous, or long-running work. |
| `aidlc_review` | `use aidlc and review`, `run aidlc then review`, `full flow` | Plan/manage the work with AIDLC, implement, then review the final diff. |
| `review_aidlc` | `review then aidlc`, `stabilize then document` | Review existing changes first, then update lifecycle docs to match the intended path. |
| `aidlc_handoff` | `use aidlc and handoff`, `run aidlc then handoff` | Manage work with AIDLC, then create a transfer package. |
| `review_handoff` | `use review and handoff`, `review then handoff` | Review the final diff, then create a transfer package. |
| `aidlc_review_handoff` | `use aidlc review and handoff`, `full flow with handoff` | Manage with AIDLC, review the final diff, then create a handoff. |
| `handoff` | `use handoff`, `create handoff`, `handoff this work` | Create a compact transfer package for review, validation, operations, or another assistant. |
| `release` | `use release flow`, `release handoff` | Prepare final validation, risk, rollback, and approval handoff. |
| `learnings` | `project learnings`, `save learning`, `remember this pattern` | Capture durable project facts in `.tailtrail/learnings.md`. |
| `token` | `save tokens`, `route context`, `use token router` | Use Token Autopilot and Token Router to load the smallest safe context slice. |

## Resolution Rule

When a user gives a short TailTrail phrase, resolve it before loading TailTrail support files.

Recommended command:

```bash
python3 scripts/expand-intent.py "use AIDLC and review"
```

For JSON output:

```bash
python3 scripts/expand-intent.py "use AIDLC and review" --format json
```

## Override Rule

Project or organization overrides may replace internal prompt text and metadata without editing TailTrail source files.

Supported override locations, in priority order:

1. `--overrides /path/to/intent-overrides.json`
2. `TAILTRAIL_INTENT_OVERRIDES=/path/to/intent-overrides.json`
3. `.tailtrail/intent-overrides.json`
4. `tailtrail/intent-overrides.json`

Use `templates/intent-overrides.json` as the starting shape.

Overrides are intentionally explicit. A flow override replaces only the fields it declares. Undeclared fields keep the TailTrail defaults.

## Safety Rule

Intent expansion is not permission to skip reading code. The expanded prompt still requires the assistant to inspect relevant files, preserve safeguards, avoid unnecessary dependencies, and validate non-trivial behavior.
