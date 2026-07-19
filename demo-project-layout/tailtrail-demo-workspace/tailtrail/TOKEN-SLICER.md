# Token Slicer Plan

Token Slicer is the planned TailTrail feature for reducing repeated context, noisy tool output, unnecessary Markdown loading, and broad source-code scans. It should make TailTrail cheaper to use without making the workflow harder to understand.

## Problem

As TailTrail grows, the risk is not just more files. The real cost comes from loading the same guidance repeatedly, reading whole documents when only one section matters, scanning too much source code, pasting long terminal output into context, and asking the agent to rediscover stable project facts every run.

Token Slicer should turn repeated context into compact, reusable slices.

Use `GUARDRAILS.md` for exactness and validation truth. Token saving must not summarize away code, diffs, configs, commands, dependency versions, security rules, policy text, or logs that need exact diagnosis.

## Token Router

The decision layer for Token Slicer is called **Token Router**.

Token Router decides which token-saving technique to use for a specific task. It should stay tiny enough to load often. It does not perform every optimization; it chooses one or two useful lanes and leaves the rest unloaded.

Why this name:

- Clearer than "token traffic controller."
- Short enough for commands, docs, and future scripts.
- Describes the real job: route context to the cheapest safe handling path.

Primary entry file:

- `context/TailTrail.map.md`: short map for choosing what to read next.

Implemented file:

- `context/token-router.md`: tiny decision table for choosing the lane.

Implemented template:

- `templates/router-decision.md`: optional trace of why a lane was selected.

Implemented CLI:

- `scripts/route-context.py`: deterministic router that prints a decision and records local route state.

Implemented hook:

- `hooks/token-router-hook.py`: optional wrapper that prints a compact context injection for hook-capable hosts.

## Principles

- Load only the smallest useful slice.
- Keep default skills short.
- Put detailed guidance in opt-in reference files.
- Summarize noisy command output before using it.
- Identify relevant code paths before reading many files.
- Store stable project facts once, then refresh only when they change.
- Prefer plain Markdown and small local scripts before hooks or services.

## Strategy Lanes

Token Slicer has seven lanes. Use them in order.

### 1. Text Slice Lane

Purpose: reduce TailTrail's own guidance context.

Use for:

- active instructions
- skill guidance
- dependency policy
- AIDLC workflow
- one selected example
- local team policy

Rule: keep precise guidance as text, but load only the slice needed for the task.

### 2. Output Style Lane

Purpose: reduce assistant response verbosity.

Use for:

- implementation summaries
- review summaries
- handoffs
- routine command explanations

Rule: answer in the smallest useful format. Prefer changed/reused/skipped/validated/risk over long narrative. Expand only when the user asks for explanation or when risk needs detail.

### 3. Context Map Lane

Purpose: reduce source-code reading.

Use for:

- project entry points
- changed files
- likely callers
- likely tests
- shared helpers
- ownership boundaries

Rule: build or maintain a small project map before asking the agent to read many files. The map should point to likely relevant files; it should not replace reading the actual source before editing.

Future extension: Code Review Graph Lite can add a small impact map for reviews using simple file, path, import, and test-name signals. It should produce a compact `changed -> callers -> tests -> risks` summary and avoid full AST graphing until usage proves the need.

### 4. Output Slicer Lane

Purpose: reduce command, test, build, and log noise.

Use for:

- test output
- build output
- git status and diff summaries
- lint output
- long logs
- package manager output

Rule: summarize raw output into counts, first failures, changed files, and next actions. Keep full output only when the full log is the artifact under investigation.

### 5. Tool Sandbox Lane

Purpose: prevent MCP, browser, API, and search tools from dumping raw payloads into context.

Use for:

- browser page reads
- raw HTML
- GitHub or API JSON
- repeated MCP responses
- large tool payloads where only a few fields matter

Rule: store or summarize bulky tool responses outside the active conversation, then return a short summary plus a way to ask for exact fields. Keep exact data text when the task depends on byte-for-byte values.

### 6. Reuse Cache Lane

Purpose: avoid paying repeatedly for the same discovered facts or similar tool results.

Use for:

- repeated API/tool calls
- stable repo facts
- project setup details
- prior dependency checks
- known test commands

Rule: reuse a cached summary when inputs are unchanged or materially equivalent. Refresh when files, commands, versions, or policies change.

### 7. Compressed Reference Lane

Purpose: reduce repeated bulky reference context.

Use only for stable, read-mostly, non-exact content:

- long design docs
- old session summaries
- verbose process docs
- large examples or reports

Rule: keep this optional and off by default. Never compress source code, diffs, commands, file paths, identifiers, hashes, secrets, config values, or exact policy text.

Future extension: Visual PNG Reference Compression can convert bulky, stable, non-exact reference material into image snapshots when the agent only needs visual gist or layout. It must keep a manifest with source path, image path, refresh rule, and exact-text fallback.

## Leak Taxonomy

The token leaks TailTrail should address are:

| Leak | TailTrail response |
|---|---|
| Startup context already large | diagnose first, keep active skills short, use `context/TailTrail.map.md` |
| TailTrail docs loaded every run | Text Slice Lane |
| Assistant over-explains routine work | Output Style Lane |
| Whole files loaded for one function | Context Map Lane |
| Large terminal/test/build output | Output Slicer Lane |
| MCP/browser/API tools dump raw payloads | Tool Sandbox Lane |
| Repeated tool calls return same data | Reuse Cache Lane |
| Long sessions accumulate stale summaries | Project memory refresh and pruning |
| Bulky stable docs repeated often | Compressed Reference Lane |

## Later Phase 1 Extensions

These ideas are useful, but they should remain deferred until the current router and slice workflow has real usage data.

### Code Review Graph Lite

Purpose: reduce review context by showing the probable blast radius before reading many files.

Planned behavior:

- detect changed files from a diff or supplied path list
- find likely callers with targeted text search
- find likely tests by path/name conventions and imports
- identify shared helpers and dependency boundaries
- write a compact impact summary into `templates/impact-brief.md` shape

Boundaries:

- no full AST graph engine yet
- no semantic vector search yet
- no background indexing service
- no claim that the graph replaces reading exact source before editing

### Visual PNG Reference Compression

Purpose: reduce repeated bulky reference context when exact text is not needed.

Candidate inputs:

- old design background
- historical reports
- large visual diagrams
- stable process summaries
- non-normative reference material

Never compress:

- source code
- diffs
- configs
- commands
- test failures needed for diagnosis
- dependency names or versions
- paths, IDs, hashes, secrets
- security, validation, authorization, data integrity, privacy, or approval rules

Required manifest:

- source path
- generated image path
- refresh date
- invalidation rule
- exact-text fallback path

Router integration should add explicit routes only after manual usage proves value, for example `review-graph` and `visual-reference`.

## Phase 1 Files

### `context/TailTrail.map.md`

Purpose: a short index of what each TailTrail file is for and when to read it.

How it helps: the agent can read the map first, then load one relevant file instead of every Markdown file.

### `context/token-router.md`

Purpose: a tiny decision table for selecting the best token-saving lane.

Example decisions:

- docs or guidance: Text Slice Lane
- routine response: Output Style Lane
- source relevance: Context Map Lane
- logs or tests: Output Slicer Lane
- raw tool payload: Tool Sandbox Lane
- repeated facts: Reuse Cache Lane
- bulky stable reference: Compressed Reference Lane
- exact source/config/security content: exact text pass-through

How it helps: TailTrail can choose the right optimization without loading every optimization guide.

### `context/slices.md`

Purpose: define named context slices.

Example slices:

- `core`: `AGENTS.md`, `skills/tailtrail/SKILL.md`
- `review`: `skills/tailtrail-review/SKILL.md`, `DEPENDENCY-GATE.md`
- `aidlc`: `AIDLC.md`, `templates/change-brief.md`, `templates/diff-handoff.md`
- `examples`: one example file chosen by task type, not all examples

How it helps: future prompts can request a named slice instead of dumping the whole repo guidance.

### `context/cache-index.md`

Purpose: record reusable summaries and the input they came from.

Example entries:

- source: command, file, API call, or tool name
- key: stable identifier for the input
- summary: compact reusable facts
- refreshed: date or commit
- invalidates when: file, command, version, or policy changes

How it helps: repeated tool calls and repeated project discovery can reuse summaries instead of reloading raw payloads.

### `context/project-map.md`

Purpose: a compact map of a target repository's important code paths.

Example entries:

- entry points
- shared helpers
- key modules
- common tests
- dependency manifests
- known risky areas

How it helps: review and implementation tasks can start from likely relevant files instead of broad repo scans.

### `context/change-impact.md`

Purpose: a short per-change impact note.

Suggested fields:

```md
Changed files:
Likely callers:
Likely tests:
Risk area:
Need to read:
Do not need:
```

How it helps: the agent sees the probable blast radius before reading source files.

### `templates/context-brief.md`

Purpose: a compact handoff format for reusable project context.

Suggested fields:

```md
Project:
Task area:
Known files:
Existing patterns:
Commands:
Constraints:
Last verified:
```

How it helps: the agent can carry a small brief forward instead of reloading full docs.

### `templates/router-decision.md`

Purpose: a short optional trace for why Token Router selected a technique.

Suggested fields:

```md
Context type:
Exactness risk:
Selected lane:
Files loaded:
Skipped lanes:
Reason:
```

How it helps: teams can debug token-saving decisions without turning every prompt into a long explanation.

### `templates/tool-summary.md`

Purpose: a compact summary format for bulky tool responses.

Suggested fields:

```md
Tool:
Input:
Relevant fields:
Omitted:
Exact follow-up:
Cache key:
```

How it helps: browser/API/MCP output can be summarized without losing the path to exact details.

### `templates/impact-brief.md`

Purpose: a compact handoff format for code relevance.

Suggested fields:

```md
Change:
Touched files:
Relevant neighbors:
Tests to inspect:
Risk:
Confidence:
```

How it helps: source relevance can be summarized and reused without pasting broad code context.

### `context/compression-policy.md`

Purpose: define what may be compressed, what must stay text, and when to fall back.

How it helps: optional visual or bulk compression cannot accidentally hide exact data that must be read byte-for-byte.

### `context/prune-rules.md`

Purpose: define when saved context is stale or low-signal.

How it helps: long sessions and project memory do not accumulate outdated summaries that confuse later work.

### `scripts/route-context.py`

Purpose: return the selected route, lane, slice, load list, avoid list, exactness risk, reason, fallback, and optional JSON output.

Example use:

```bash
python3 scripts/route-context.py review
python3 scripts/route-context.py auto review this diff for unnecessary code
python3 scripts/route-context.py output --format json
```

How it helps: users and agents can get a repeatable context decision without loading the full Token Slicer design.

### `.tailtrail/token-router-state.json`

Purpose: generated local state for the most recent route decision.

How it helps: a long session can reuse the last selected lane without adding a persistent background service.

### `hooks/token-router-hook.py`

Purpose: optional hook entry point for hosts that can inject small prompt context.

How it helps: teams can automatically inject only the compact route decision while keeping full docs unloaded.

### `scripts/slice-context.py`

Purpose: optional local script that prints only the requested slice.

Example use:

```bash
python3 scripts/slice-context.py core
python3 scripts/slice-context.py review
```

How it helps: the user or agent can produce a small context packet without manually opening many files.

### `scripts/summarize-output.py`

Purpose: optional local script that turns noisy command output into a short structured summary.

Example use:

```bash
python3 scripts/summarize-output.py test < test-output.txt
python3 scripts/summarize-output.py log < build.log
```

How it helps: tests, logs, and command output can enter the conversation as a compact summary instead of raw noise.

### `scripts/cache-summary.py`

Purpose: optional local script that stores and retrieves compact summaries by key.

Example use:

```bash
python3 scripts/cache-summary.py put test-command npm-test-summary.md
python3 scripts/cache-summary.py get test-command
```

How it helps: repeated discoveries can be reused intentionally instead of pasted again.

### `scripts/prune-context.py`

Purpose: optional local script that reports stale cache entries, old project facts, and low-signal summaries.

How it helps: long sessions keep useful context while dropping stale or redundant memory.

## Token Slicer Workflow

1. Diagnose: check what context is being loaded before work starts.
2. Route: use `context/token-router.md` and `context/TailTrail.map.md` to choose the smallest safe lane.
3. Slice: load only TailTrail files needed for the task.
4. Style: keep routine responses compact unless detail is requested.
5. Map: use `context/project-map.md` or `context/change-impact.md` to identify relevant source files.
6. Read: inspect actual source files, diffs, and exact errors as text.
7. Summarize: compress terminal output, long logs, and repeated discoveries into a brief.
8. Sandbox: summarize bulky tool payloads and keep exact retrieval available.
9. Reuse: store stable facts in `context/project-memory.md` or `context/cache-index.md` when the user wants persistent local notes.
10. Refresh: update memory only when commands, structure, versions, or policies change.
11. Prune: remove stale, redundant, or low-signal saved summaries.

## Exact-Safe Rules

Always keep these as text:

- source code
- diffs
- stack traces needed for exact debugging
- commands
- file paths
- dependency names and versions
- hashes and IDs
- secrets or secret-like values
- config values
- security and approval rules

Do not visually compress or loosely summarize exact-work material. If exactness matters, read the source text.

## Noise Rules

- Do not paste full build logs unless the full log is the artifact under investigation.
- Prefer the first failing error, summary counts, and changed files over raw output dumps.
- Prefer file excerpts around relevant symbols over entire files.
- Prefer a context brief over re-reading stable docs.
- Prefer one selected example over the whole `examples/` folder.
- Prefer a project map over scanning a whole repository.
- Prefer command summaries over raw terminal transcripts.
- Prefer tool summaries over raw HTML or raw JSON.
- Prefer cached summaries over repeated equivalent tool calls.
- Prefer pruning stale memory over carrying old context forward.

## Implementation Plan

### Step 1: Documentation Foundation

Add this plan and link it from `README.md`, `DESIGN.md`, and `ROADMAP.md`.

Acceptance: users understand the future feature before any code exists.

### Step 2: Manual Context Slices

Add `context/TailTrail.map.md`, `context/slices.md`, and `templates/context-brief.md`.

Acceptance: a user can manually choose a slice and avoid loading unrelated docs.

### Step 3: Token Router

Add `context/token-router.md` and `templates/router-decision.md`.

Acceptance: a user or agent can choose the best lane for a task without loading every token-saving plan.

### Step 4: Output Style Contract

Tighten `@tailtrail` and `@tailtrail-review` response shape so routine work uses compact handoff fields.

Acceptance: normal TailTrail responses do not spend tokens on unrequested narrative.

### Step 5: Context Map Lite

Add `context/project-map.md`, `context/change-impact.md`, and `templates/impact-brief.md`.

Acceptance: a user can capture likely files, callers, tests, and risk areas without loading broad source context.

### Step 6: Output Slicer Plan

Add `scripts/summarize-output.py` only after the summary formats are stable.

Acceptance: noisy command output can be reduced to first failures, counts, changed files, and next actions.

### Step 7: Tool Sandbox Plan

Add `templates/tool-summary.md` and document how browser/API/MCP payloads should be summarized.

Acceptance: large raw HTML/JSON/tool payloads are represented by concise summaries unless exact fields are required.

### Step 8: Project Memory And Cache

Add `context/project-memory.example.md`, `context/cache-index.md`, and document copying project memory to a target repo.

Acceptance: repeated project facts and repeated tool outputs can be recorded without changing TailTrail code.

### Step 9: Slice Script

Add `scripts/slice-context.py` with no dependencies.

Acceptance: `python3 scripts/slice-context.py core` prints only the files in the `core` slice.

### Step 10: Reuse Cache Script

Add `scripts/cache-summary.py` only after manual cache entries prove useful.

Acceptance: stable summaries can be retrieved by key and refreshed deliberately.

### Step 11: Prune Rules

Add `context/prune-rules.md` and later `scripts/prune-context.py`.

Acceptance: stale project memory and low-signal summaries can be identified before they pollute future runs.

### Step 12: Compression Policy

Add `context/compression-policy.md`.

Acceptance: exact-safe content is clearly separated from optional bulky reference content.

### Step 13: Skill Integration

Update `@tailtrail` and `@tailtrail-review` with one short rule: for large or repeated work, use Token Slicer and load only the needed slice.

Acceptance: the active skill stays short and does not embed the full Token Slicer documentation.

### Step 14: Deferred For Review: Visual Bulk Adapter

Only after slicing, mapping, and output summarization work, consider a local optional adapter that compresses stable bulky references.

Acceptance: compression is opt-in, exact-safe, and never applied to source code, diffs, commands, configs, or approval rules.

### Step 15: Optional Hook

Only after manual slicing works, consider an optional lifecycle hook that reminds users which slice is active or injects a tiny map.

Acceptance: the hook reduces context without producing repeated startup noise.

## Deferred For Review

These ideas are not rejected. They are deferred so TailTrail stays simple while the routing, slicing, mapping, and summarizing foundation proves itself.

- Full AST graph engine.
- Full semantic vector search.
- Visual or image compression runtime.
- Auto hooks everywhere.
- Global installer.
- Persistent background service.
- Complex MCP proxy.

Review these again after the manual Token Router flow has real usage data.

## Non-Goals

- No claims of fixed percentage savings until measured locally.
- No background service.
- No external dependency.
- No automatic deletion or rewriting of user context.
- No vendored external token-reduction tools.
- No hidden global state in V1.

## Success Measure

Token Slicer is successful if a normal TailTrail run can start from a small map, load one focused guidance slice, identify relevant source files before reading broadly, summarize noisy output, and avoid repeatedly loading all docs, examples, plans, source files, and logs.

## Exact Token Usage Telemetry

TailTrail supports two evidence levels:

- Estimated: local character-count approximation from used and avoided files.
- Measured: real provider/model usage metadata supplied by the user.

Use measured telemetry when you need before/after token results:

```bash
python3 scripts/tailtrail.py savings report --telemetry .tailtrail/token-usage.jsonl
python3 scripts/tailtrail.py savings report --telemetry templates/token-usage-example.jsonl
python3 scripts/tailtrail.py report --token-telemetry .tailtrail/token-usage.jsonl
```

Required JSONL shape:

```json
{"mode":"measured","schema_version":"1","task_id":"sonar-fix-123","provider":"your-provider","model":"your-model","source":"usage_metadata","baseline":{"input_tokens":64000,"output_tokens":11000,"total_tokens":75000},"tailtrail":{"input_tokens":15000,"output_tokens":3500,"total_tokens":18500}}
```

Measured telemetry improves the result because it replaces local approximations with the actual usage numbers reported by the model/API surface. The report can then show before TailTrail, with TailTrail, token difference, and percentage reduction for the measured records.

Example-only stats from the sample file:

| Task | Before TailTrail | With TailTrail | Difference | Reduction |
|---|---:|---:|---:|---:|
| example-sonar-fix | 75,000 | 18,500 | 56,500 | 75.33% |
| example-review | 42,000 | 14,000 | 28,000 | 66.67% |

These are fake sample values. Real results vary, and TailTrail must not claim a fixed percentage reduction without local measured telemetry.
