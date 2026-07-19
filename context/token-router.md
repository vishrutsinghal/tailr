# Token Router

Token Router is the decision layer for TailTrail's token-saving work. It chooses the smallest safe context technique for a task and keeps unrelated guidance, source, logs, and tool output out of the active conversation.

The router should be tiny enough to load often. It does not replace the TailTrail skills. It tells the agent what to load next.

Token Autopilot sits before Token Router. It decides whether routing is useful at all. Tiny low-risk prompts should skip routing to avoid spending more tokens than they save.

## Router Contract

Given a task, Token Router returns:

- selected lane
- files or context to load
- files or context to avoid
- exactness risk
- reason
- fallback if the first lane is not enough

The router should choose one primary lane and at most one supporting lane. If more lanes seem needed, prefer asking for a smaller task boundary or making a compact context brief.

## Decision Table

| Situation | Primary lane | Load | Avoid |
|---|---|---|---|
| Normal coding task | Text Slice | `core` slice, relevant source files | examples, roadmap, design docs |
| Diff or PR review | Text Slice + Context Map | `review` slice, changed files, likely callers/tests | unrelated examples, broad repo scans |
| Dependency/package decision | Text Slice | dependency policy, manifest snippets | broad docs, unrelated source |
| AIDLC/process request | Text Slice | `aidlc` slice | examples unless requested |
| QA or validation evidence | Output Slicer + Text Slice | QA / validation layer, validation handoff, exact command/result | raw full logs, unrelated test suites |
| CI/Sonar issue | Output Slicer + Text Slice | CI / Sonar layer, exact rule/job/file/line/failure | lossy scanner summaries |
| Release readiness | Text Slice + Output Slicer | release layer, handoff templates, exact validation/approval/version text | deployment claims without evidence |
| User asks for examples | Text Slice | one selected example | all examples |
| Large unknown repo area | Context Map | project map, change impact, likely files | whole directories |
| Test/build/lint output | Output Slicer | summarized failures, counts, affected files | raw full logs |
| Browser/API/MCP payload | Tool Sandbox | tool summary, exact follow-up path | raw HTML/JSON dumps |
| Repeated project facts | Reuse Cache | project memory, cache index | rediscovery |
| Stable bulky reference | Compressed Reference | compression candidate only if exactness is low | code, diffs, configs |
| Code, diff, config, security, IDs, paths | Exact Pass-through | exact text | summaries, compression |

## Exactness Risk

Use `high` exactness risk when the task involves:

- source code that may be edited
- diffs
- commands
- file paths
- stack traces
- dependency names or versions
- identifiers, hashes, IDs, or secrets
- config values
- authorization, validation, or approval rules

High exactness risk always means exact text. Do not compress or loosely summarize the material that must be read byte-for-byte.

Use `medium` exactness risk when the task needs technical meaning but not byte-for-byte recall. Examples: architecture overview, impact summary, selected examples, or test-output summary.

Use `low` exactness risk for stable background context where gist is enough. Examples: old process docs, roadmap notes, or large non-normative examples.

## Agent Implementation Details

When a TailTrail-aware agent starts a non-trivial task:

1. Classify the task using the decision table.
2. Mark exactness risk.
3. Load the selected slice or context only.
4. Load only the relevant layer from `context/guardrail-layers.md` when feature-specific checks are needed.
5. Keep source files, diffs, configs, commands, and security rules exact.
6. If the selected lane is insufficient, load one more lane and record why.
7. Do not load roadmap, design, examples, or future plans unless the user asks for those topics.

For routine tasks, the agent can apply the router mentally and skip emitting a router decision. For ambiguous, large, or repeated work, use `templates/router-decision.md` once that template exists.

## Org-Level Model

Token Router should support three policy layers:

| Layer | Purpose | Example files |
|---|---|---|
| Global | Company-wide defaults and safety rules | `AGENTS.md`, future dependency policy, compression policy |
| Team | Team-specific workflow and approvals | future `tailtrail-policy.md` |
| Project | Discovered project facts and relevance maps | future `context/project-map.md`, `context/project-memory.md` |

Precedence:

1. Explicit user instruction for the current task.
2. Global safety rules.
3. Team policy.
4. Project memory.
5. Router default.

Never let project memory override safety rules.

## Python Implementation

The implementation is deterministic and dependency-free:

```bash
python3 scripts/route-context.py review
python3 scripts/route-context.py dependency
python3 scripts/route-context.py output-log
python3 scripts/route-context.py auto review this diff for extra dependencies
```

Expected JSON shape:

```json
{
  "lane": "review",
  "supporting_lane": "context-map",
  "load": [
    "skills/tailtrail-review/SKILL.md",
    "context/change-impact.md"
  ],
  "avoid": [
    "examples/",
    "ROADMAP.md",
    "DESIGN.md"
  ],
  "exactness_risk": "high",
  "exact_text": true,
  "reason": "Diff review requires exact source plus likely impact context.",
  "fallback": "Load one relevant caller/test file if the change impact is unclear."
}
```

The Python router should not:

- call an LLM
- parse the whole repo
- mutate files
- run hooks
- compress content
- decide company policy

It should only route context.

By default the router writes `.tailtrail/token-router-state.json`. Pass `--no-state` for a dry run.

Hook-capable hosts can call:

```bash
python3 hooks/token-autopilot-hook.py review this diff
python3 hooks/token-router-hook.py auto review this diff
```

The autopilot hook should be preferred for automatic use because it can skip tiny prompts. Hooks print only compact context injection. They should not inject full docs, raw logs, source files, or cached state.

## Future Enhancements

Review these only after the router flow proves useful:

- Add team override support through `tailtrail-policy.md`.
- Add project memory awareness.
- Add measured token accounting for each route.
- Add optional hook integration that injects only the router map, not full docs.
- Add visual compression only for low-exactness stable references.
- Add graph or semantic search only if Context Map Lite is not enough.

## Success Criteria

Token Router succeeds when:

- a task loads one relevant slice instead of the full TailTrail docs
- exact source/diff/config/security material stays text
- large logs and tool payloads become summaries
- repeated project facts are reused
- teams can explain why a token-saving lane was selected
