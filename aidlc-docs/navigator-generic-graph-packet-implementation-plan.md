# Generic Navigator Graph and Host-Packet Implementation Plan

## Status

Draft for review (revision 3). This document proposes behavior only; it does
not grant implementation authority or change TailTrail runtime behavior.

Revision 2 incorporates the read-only audit of `capture_hooks.py`,
`code_graph_cache.py`, `code-graph-mapper.py`, and `mcp-server.py`, and adopts
the incremental single-graph direction: one persistent usage-built graph,
extended per run, never rebuilt from scratch as a routine path.

Revision 3 locks the hard choice (approved docs-only): no full-graph build at
start. The host agent runs the code scan/search; Navigator captures metadata
from every file actually read and builds/extends the single graph. Next run
reuses that same graph only. There is exactly one graph; no fresh graph is
created as a routine path.

Revision 3.2 adds the shared-cache collision fix: one file, two sections
(`phase1_files` + `mapper_graph`), fail-closed on foreign shape, section-
preserving writes. Single-graph makes the collision worse until this lands,
so Stage 0 comes first.

## Problem

Navigator currently has the right broad building blocks, but they do not form a
single generic decision flow:

- `navigator_graph_lifecycle.py` can reuse, refresh, and build a persistent
  mapper graph.
- `navigator_scope.py` can investigate a bounded source slice and emit a
  sanitized host-reasoning packet.
- `capture_hooks.py` attempts to retain facts for every file processed.

The integration is incomplete. A cache may be source-fresh but unrelated to a
new request; broad lexical discovery can populate a graph with unrelated
owners; and `code_graph_cache.py` and `code-graph-mapper.py` write the same
cache filename with incompatible schemas (Phase 1 `{"version", "files"}`
versus mapper `{"graph_mode", "scope", "graph"}`). Worse, `normalize_cache()`
coerces a mapper-shaped file to an empty cache with no error, so a Phase 1
update over a mapper file silently discards mapper data (last-writer-wins);
existing guards (lifecycle mapper-shape refusal, `commit_prompt.py` `"graph"`
check) work around the collision instead of fixing it. Finally,
`capture_hooks.py` is wired only into `investigate()` reads
(`navigator_scope.py:1847-1848`); host-side reads served over MCP, plus debug
and CLI reads, bypass capture entirely, so the graph learns only from
machine-discovered files. Consequently, a host can receive several
plausible but unrelated existing files and be asked to choose one.

This is not a UI-only issue. The same failure is possible for API, worker,
command-line, infrastructure, data, and mixed-stack changes.

## Goals

1. Reuse a graph only when it is both **fresh** and **relevant** to the task.
2. Build a small, connected, evidence-backed graph packet when reuse is not
   possible, then progressively retain facts for files actually processed.
3. Give the host agent evidence and alternatives, not an ungrounded editable
   file choice.
4. Support a host-proposed new file path without falsely presenting it as an
   existing evidence-backed owner.
5. Preserve bounded reads, source hashing, privacy filtering, path safety, and
   existing Planning Lock and implementation-authority safeguards.
6. Maintain exactly one persistent usage-built graph on the existing cache
   path: extend per run, never rebuild from scratch as a routine path;
   freshness is per-file (hash-checked), never a whole-graph verdict. No
   full-graph build at start; no fresh graph as a routine path.
7. Capture metadata from host-side reads (MCP-served, debug, CLI) so the
   single graph converges on files actually used, not only files the machine
   discovered. The host agent runs the code scan/search on a miss; Navigator
   captures and extends.
8. Work with any repository language and project shape without framework or
   UI-specific rules.

## Non-goals

- Building a whole-repository graph for every request.
- Sending raw source bodies, secrets, or attachment bytes to the host packet.
- Automatically granting edit authority from keyword matches or graph edges.
- Changing parsers, adding dependencies, or making a language-specific
  classifier mandatory.
- Adding a third cache store alongside the two existing writers.

## Generic Model

### Roles rather than technology labels

Navigator represents discovered files through portable roles. A file can carry
more than one role.

| Role | Meaning | Examples |
| --- | --- | --- |
| `entrypoint` | How behavior begins | HTTP route, CLI command, event subscription, UI navigation |
| `orchestrator` | Coordinates the requested behavior | controller, page, service, workflow handler |
| `domain-owner` | Owns durable rules or state | model, validator, aggregate, schema, configuration |
| `integration-owner` | Crosses a system boundary | repository, client, adapter, resource declaration |
| `verification-owner` | Demonstrates behavior | unit, integration, end-to-end, contract test |
| `convention-owner` | Closest established implementation pattern | analogous feature, component, module, template |

The role model is evidence-based and generic. It does not assume React,
Python, REST, Terraform, or a particular directory structure.

These topology roles answer "where does this file sit in the behavior flow"
and are distinct from the existing edit-permission candidate roles
(`implementation-owner`, `inspection`, `proof`, `caller`, `configuration`,
`test`) and the behavior-evidence kinds. The implementation must include an
explicit old↔new mapping table plus a test asserting every packet topology
role projects onto exactly one candidate role; without it the two systems
will drift. Anchors and topology roles describe discovery only — they never
mint owners. The handoff is fixed: anchors → seeds → facts → behavior →
owners, and behavior-ownership qualification remains the sole owner-minting
path.

### Freshness and relevance

Freshness answers: “are the cached source facts unchanged?”

Relevance answers: “does the cached graph contain a connected path from task
anchors to at least one behavior owner or reusable convention?”

Both must be true for reuse. A graph containing only Action Configuration files
may be fresh but is not relevant to a File Configuration request. A graph with
a matching path but changed source hashes is relevant but not fresh and must be
refreshed.

## Target Runtime Flow

```text
request + attachments
  -> serve single-graph candidate slice (bounded, ranked, no bodies read)
  -> host uses served slice; if relevant files found, use them
  -> else host runs code scan/search for expected files (extras declared)
  -> capture metadata from every file actually read (machine or host reads)
  -> extend the single graph; per-file hash freshness, never whole rebuild
  -> anchor/path relevance check over collected edges before reuse
  -> emit sanitized host evidence packet (v2 with v1 projection)
  -> host selects existing boundary or proposes a new path with anchors
  -> Navigator validates proposal; Planning Lock remains separate
```

Division of labor (revision 3 hard choice):

- TailTrail never builds a full repository graph at start and never creates a
  fresh graph as a routine path. There is exactly one persistent usage-built
  graph on the existing cache path.
- TailTrail serves the current single-graph slice for the next run. If the
  host finds relevant files there, that ends discovery.
- Otherwise the host agent runs the code scan/search for expected files. Every
  host or machine read goes through `on_file_read` plus batched `flush()`,
  so Navigator captures metadata and extends the same single graph.
- On a miss the host may nominate files outside the served slice, but must
  state why; outside picks are recorded and visible in telemetry, and routine
  outside-picking is signal to improve ranking rather than silent token bleed.
  The machine narrows (ranking, never choosing) and the host selects within the
  bound (never reading outside it without declaring).

### 1. Derive bounded task anchors before graph lifecycle selection

Extend the existing seed machinery in `investigate()` (seeds, anchor paths /
directories, module stems) with role-labeled anchor hypotheses, and run it
before `GraphLifecycleManager.manage()` decides reuse/refresh/build. Do not
add a parallel resolver — there must be exactly one discovery-entry path. It
must derive only task-supported anchor hypotheses from the request and
repository facts, such as:

- a named command, event, route, or configuration concept;
- a known navigation/configuration section;
- a referenced existing symbol/path;
- an attachment-derived visible label or behavior contract;
- nearest exact or structural convention.

Anchors are hypotheses with confidence and evidence references, never owners
or implementation authority. The resolver must return `insufficient` rather
than broaden to generic keyword matches when it cannot form a bounded set.

Revision 3.1: goal word-matching is deprecated as discovery. Prompt
understanding belongs to the host agent. `goal_discovered_paths()` lexical
seeds (`lexical-path` / `lexical-body`) must not drive lifecycle target
selection or graph build scope. Lifecycle takes only host-supplied
`anchor_slice` paths, exact quoted literals (`exact_phrase_paths`), explicit
`--changed` paths, or fresh-graph reuse. Lexical-only seeds remain
`inspection-only` at best and never establish ownership.

### 2. Decide graph reuse using the anchor slice

Change lifecycle input from only goal-discovery paths to an `anchor_slice`:

```json
{
  "anchor_ids": ["entrypoint:file-configuration", "concept:ecg-consumer"],
  "paths": ["project-relative/path"],
  "relations": ["entrypoint->orchestrator"],
  "fingerprint": "sha256...",
  "coverage_required": ["entrypoint", "convention-owner"]
}
```

Reuse is allowed only if cache source hashes validate and the cache contains
the requested paths or a connected relation satisfying required coverage. Store
the outcome explicitly as `fresh-relevant`, `fresh-insufficient`,
`stale-relevant`, or `missing`.

`fresh-insufficient` must build or extend the bounded slice; it must not turn
unrelated cached owners into candidate choices.

### 3. Build only the missing evidence slice

When the cache is absent, stale, or insufficient:

1. Read direct anchors within existing Navigator limits.
2. Follow only evidence-bearing references/callers/imports/config links until
   minimum role coverage is met or the budget is exhausted.
3. Record excluded paths with a reason (for example, same lexical term but no
   path to an anchor).
4. Stop with an evidence-gap question if a bounded connected slice cannot be
   formed.

Existing language adapters in the mapper remain responsible for extraction.
Unknown-language files can still contribute portable file facts, imports,
configuration references, hashes, and explicit relationships without claiming
semantic precision they cannot prove.

### 4. Reconcile to one graph store on the existing path

Do not add new store files. Keep the existing
`tailtrail-meta/code-graph-cache.json` / `.tailtrail/code-graph-cache.json`
paths and reconcile the current writers into one container with two sections.
Verified collision: `code_graph_cache.py` (`{"version","files"}`),
`code-graph-mapper.py` (`{"schema_version","graph_mode","scope","graph"}`),
and `graph_builder.py` (mapper-shape writer, Phase-1 reader for warm scope)
share the filename. `normalize_cache()` coerces a mapper file to empty with
no error; mapper `status_for()` marks a Phase-1 file `invalid`; builder warm
scope then resolves to `[]` (`No scope to build`) or a later save clobbers
the only graph (last-writer-wins).

1. Container: `{"schema_version": 2, "sections": {"phase1_files": {...},
   "mapper_graph": {...}}}` on the existing path. `capture_hooks.py` /
   `code_graph_cache.py` own `phase1_files` only; `code-graph-mapper.py` /
   lifecycle / `graph_builder.py` own `mapper_graph` only. Every writer does
   read-modify-write and preserves the other section and unknown keys.
2. Fix the silent-loss path first: `normalize_cache()` stays strict Phase-1;
   `load()` detects a mapper shape (`graph_mode`/`schema_version`/`graph`
   without `files`) and returns `shape-mismatch`, never silent empty;
   `save()`/`write_cache()` read first and refuse to overwrite a foreign
   shape they cannot merge. Same mirror in mapper `load_cache()`.
3. Migrate in place with a unified reader (`phase1_files` + `mapper_graph` +
   warnings) that understands v1 Phase-1, v1 mapper, and v2 combined;
   builder reads per-file facts first and reparses only missing/stale files
   by hash.
4. Remove the mapper-schema refusal workarounds once both writers share the
   shape; keep legacy read support until normal retention/pruning, never
   delete user data during migration, and report migration state in
   diagnostics.

All writes remain atomic, path-safe, repository-local, versioned, and
best-effort only where current behavior is best-effort. A graph builder reads
valid per-file facts first, reparses only missing/stale files (per-file hash
freshness), and merges them into the requested slice. Rebuild-from-scratch
exists only as a tested corruption-repair path, never as a routine operation.

### 4b. Capture host-side reads into the single graph

Wire `on_file_read` plus batched `flush()` into every TailTrail-served read
path the host can trigger — MCP-served reads first, then debug and CLI read
paths — preserving the never-raises, no-disk-I/O-per-read capture contract.
The read-only `navigator scope inspect` CLI keeps its non-persisting opt-out.
Without this step the graph cannot converge on host-found files and the
serve-then-capture loop above stalls on the serve side.

### 5. Send the host an evidence packet, not a forced file choice

Extend `host_reasoning_packet()` with cache and topology information while
preserving source sanitization. Wire rules: packet v2 is a strict superset of
v1; v1 consumers receive a server-side projection (v1 fields byte-stable, new
sections dropped, never re-interpreted); the packet carries `packet_version`
and producers/consumers negotiate by version with fail-closed behavior on
unknown major versions; add a schema file for v2 alongside the existing v1
contract. The packet must contain:

```json
{
  "packet_version": 2,
  "cache": {
    "state": "fresh-relevant",
    "graph_fingerprint": "sha256...",
    "slice_fingerprint": "sha256...",
    "coverage": ["entrypoint", "convention-owner"]
  },
  "anchors": [{"id": "...", "role": "entrypoint", "path": "..."}],
  "relationships": [{"from": "...", "to": "...", "kind": "..."}],
  "existing_candidates": [{"path": "...", "roles": ["..."]}],
  "conventions": [{"path": "...", "reason": "..."}],
  "excluded_candidates": [{"path": "...", "reason": "unconnected"}],
  "suggested_read_order": ["..."],
  "limits": {"files_read": 0, "max_files": 0}
}
```

The packet contains project-relative paths, hashes, relation kinds, and
sanitized evidence summaries only. It must never contain raw file content,
unredacted attachment content, credentials, or untrusted host instructions.

### 6. Permit a controlled proposed-new-path boundary

Extend `validate_host_proposal()` to accept either:

- an existing candidate, validated against its candidate identifier, content
  fingerprint, and edge references; or
- a `proposed_new_path`, validated as a safe project-relative path and linked
  to at least one current `entrypoint`/`orchestrator` anchor and one convention
  or integration requirement.

The response must label this as `host-proposed-new-path`, not as a discovered
implementation owner. It remains a scope proposal, not Planning Lock or edit
authority.

## File-Level Change Plan (in stage order; each stage independently reviewable)

Stage 0. Shared-cache reconciliation (no discovery changes; recommended first
approval unit, in this order):
   - 0a. Fail-closed: `code_graph_cache.py:normalize_cache/load/save` surface
     `shape-mismatch` and refuse to clobber a foreign shape; mirror in
     `code-graph-mapper.py:load_cache/status_for`. Keep atomic writes.
     Tests: mapper file + Phase-1 save preserves `mapper_graph`; Phase-1 file
     + mapper status leaves bytes unchanged.
   - 0b. Unified container: `schema_version: 2` with `sections.phase1_files`
     + `sections.mapper_graph` on the existing path; section-preserving
     read-modify-write on both writers; unified reader for v1/v2 + warnings.
   - 0c. Builder/lifecycle switch: `graph_builder.py` warms from
     `phase1_files`, commits only `mapper_graph`; remove mapper-shape refusal
     workarounds after cross-reads prove clean. Legacy read retained, no
     delete-on-migrate, migration state in diagnostics.

Stage 1. `scripts/mcp-server.py`, debug/CLI read paths, `scripts/capture_hooks.py`
   - Queue plus batched-flush host-served reads into the single graph store.
   - Preserve never-raises capture semantics and the read-only opt-out.

Stage 2. `scripts/navigator_scope.py` (proposal validation only)
   - Add the `proposed_new_path` branch to `validate_host_proposal()`: safe
     project-relative path, linked to a current anchor and a convention or
     integration requirement, labeled `host-proposed-new-path`.
   - No discovery changes in this stage.

Stage 3. `scripts/navigator_scope.py` + `scripts/navigator_graph_lifecycle.py`
   - Anchor labeling on the existing `investigate()` seeds; anchor-aware
     reuse/extension in `manage()`; freshness and relevance recorded
     separately in lifecycle receipts (`fresh-relevant`,
     `fresh-insufficient`, `stale-relevant`, `missing`).
   - Add the bounded path query over collected relationship edges (anchor →
     file connectivity); `fresh-insufficient` builds/extends the slice and
     never promotes unconnected lexical matches.

Stage 4. `scripts/code-graph-mapper.py`
   - Read per-file facts before reparsing; write graph sections into the
     shared shape; slice coverage queryable by anchor and relation.

Stage 5. `scripts/navigator_scope.py` (packet), `scripts/navigator.py`, renderers
   - Packet v2 construction with v1 projection; anchor resolution before
     lifecycle management; evidence-gap question when anchors are
     insufficient (never an arbitrary file choice).

Stage 6. Tests and fixtures
   - Role-mapping table plus projection test (every topology role maps onto
     exactly one candidate role).
   - Focused fixtures across UI, API/service, worker/event, CLI, and
     infrastructure/config layouts with language-neutral expected roles.
   - Conformance cases: fresh-but-unrelated rejection, partial-slice
     extension, outside-slice nomination recording, legacy-shape read.

## Acceptance Criteria

- A fresh but unrelated cache cannot produce implementation-owner candidates.
- A task that maps to an existing connected cached slice avoids unnecessary
  source reprocessing.
- A missing graph builds only the bounded anchor slice and records processed
  files for later reuse.
- UI, API, worker, CLI, and infrastructure fixtures all use the same lifecycle
  and packet contract.
- Generic lexical matches with no anchor path are excluded and explained.
- A host can propose a new file path only with validated current anchors.
- A proposed new path never receives implementation authority before the
  existing Planning Lock flow approves it.
- Legacy mapper cache remains readable; migration does not delete user data.
- Exactly one graph store exists on the existing cache path; no writer
  silently discards a foreign shape.
- Host-served reads (MCP at minimum) extend the graph; the graph converges on
  files actually used across runs.
- Every packet topology role projects onto exactly one candidate role
  (mapping table plus test).
- Outside-slice host nominations are recorded with reasons and visible in
  telemetry.
- Cache corruption, stale hashes, unsafe paths, malformed packets, and missing
  anchors fail closed into bounded clarification rather than owner guessing.

## Validation Plan

1. Unit-test anchor extraction, freshness, relevance, shape reconciliation
   (including no-silent-loss), and safe proposed-path validation.
2. Add integration tests for cache reuse, fresh-but-unrelated rejection,
   partial-slice extension, and progressive per-file reuse.
3. Run existing Navigator, lifecycle, mapper, cache, task-start, MCP, and CLI
   regression suites.
4. Run a full targeted test matrix against fixtures representing each generic
   project topology named above.
5. Run `git diff --check` and Python compilation for changed scripts.

No dependency additions are planned. Exact commands and actual outcomes belong
in the validation handoff when implementation is approved and performed.

## Risks and Controls

| Risk | Control |
| --- | --- |
| Over-broad graph expansion | Anchor-first slice and existing read budgets |
| False owner confidence | Role/evidence packet; host selection; Planning Lock remains separate |
| Cache poisoning or stale facts | hashes, fingerprints, versioned schemas, atomic writes, fail-closed validation |
| Privacy leakage | sanitized packets and no raw source/attachment bodies |
| Migration data loss | legacy read-only compatibility and no delete-on-migrate behavior |
| Language-specific behavior leak | portable role contract with adapter-specific extraction only |

## Approval Needed

Approve this plan before modifying Navigator, cache schemas, host packet
contracts, or installation artifacts. Deliver in the staged order above
(0 → 6); each stage is independently reviewable and later stages must not
begin until the earlier stage's tests pass. Stages 0–1 carry no discovery or
packet-contract changes and are the recommended first approval unit.
