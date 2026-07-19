# TailTrail Context Map

Read this file first when a TailTrail task feels broad, repeated, or likely to load many Markdown files. Pick one slice or lane, then load only the files needed for that task.

## Default Routes

| Task | Load first | Usually avoid |
|---|---|---|
| Normal implementation | `core` slice from `context/slices.md` | examples, roadmap, design |
| Review or simplification | `review` slice and `context/change-impact.md` | unrelated examples, full docs |
| QA, CI, Sonar, or release evidence | relevant layer in `context/guardrail-layers.md` plus `output` or `aidlc` slice | raw full logs, unrelated lifecycle files |
| Heavy Sonar, vulnerability, QA, dependency, review, or handoff source mapping | `code-graph` slice and `context/code-graph-mapper.md` | stale graph caches, broad source folders |
| Token-saving decision | `context/token-router.md` | all future-scope docs |
| AIDLC workflow | `aidlc` slice | every lifecycle artifact |
| Example calibration | one matching file in `examples/` | all examples |
| TailTrail design change | `DESIGN.md`, `ROADMAP.md`, affected file | unrelated target-project files |

## Always Keep Exact

Do not compress or loosely summarize source code, diffs, commands, config values, dependency names or versions, file paths, stack traces, identifiers, hashes, secrets, validation rules, authorization rules, approval rules, or explicit user requirements.

## Smallest Useful Flow

1. Choose a route from this map.
2. Load the matching slice from `context/slices.md`.
3. Load only the relevant layer from `context/guardrail-layers.md` when the task needs feature-specific guardrails.
4. Read exact source or diff material only after the slice identifies what matters.
5. Summarize noisy output with `templates/tool-summary.md`.
6. Record stable project facts in `context/project-map.md` or `context/cache-index.md` only when they will be reused.
