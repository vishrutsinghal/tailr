# Generic Navigator Graph and Host-Packet Implementation Plan

## Status

Draft for review. This document proposes behavior only; it does not grant
implementation authority or change TailTrail runtime behavior.

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
owners; and `code_graph_cache.py` and `code-graph-mapper.py` use the same cache
filename with incompatible schemas. Consequently, a host can receive several
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
6. Work with any repository language and project shape without framework or
   UI-specific rules.

## Non-goals

- Building a whole-repository graph for every request.
- Sending raw source bodies, secrets, or attachment bytes to the host packet.
- Automatically granting edit authority from keyword matches or graph edges.
- Changing parsers, adding dependencies, or making a language-specific
  classifier mandatory.

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
  -> bounded intent/anchor resolver
  -> graph-cache freshness and relevance check
  -> reuse relevant graph OR construct bounded evidence slice
  -> persist per-file facts for files read
  -> derive/extend cross-file graph for that slice
  -> emit sanitized host evidence packet
  -> host selects existing boundary or proposes a new path with anchors
  -> Navigator validates proposal; Planning Lock remains separate
```

### 1. Derive bounded task anchors before graph lifecycle selection

Add an anchor-resolution phase before `GraphLifecycleManager.manage()` decides
reuse/refresh/build. It must derive only task-supported anchor hypotheses from
the request and repository facts, such as:

- a named command, event, route, or configuration concept;
- a known navigation/configuration section;
- a referenced existing symbol/path;
- an attachment-derived visible label or behavior contract;
- nearest exact or structural convention.

Anchors are hypotheses with confidence and evidence references, never owners
or implementation authority. The resolver must return `insufficient` rather
than broaden to generic keyword matches when it cannot form a bounded set.

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

### 4. Persist two compatible cache layers

Separate the incompatible current cache formats:

| Store | Proposed path | Contents | Writer |
| --- | --- | --- | --- |
| Processed-file facts | `tailtrail-meta/processed-file-cache-v1.json` | source hash, extraction version, symbols/refs/facts, timestamp | `capture_hooks.py` / `code_graph_cache.py` |
| Derived graph | `tailtrail-meta/code-graph-cache-v1.json` | graph nodes, edges, slices, source/watch hashes, inventory fingerprint | `code-graph-mapper.py` / lifecycle |

All writes must remain atomic, path-safe, repository-local, versioned, and
best-effort only where current behavior is best-effort. A graph builder reads
valid processed-file facts first, reparses only missing/stale files, and merges
them into the requested graph slice.

Provide a read-compatible migration for the existing
`tailtrail-meta/code-graph-cache.json` mapper cache:

1. Detect its schema without modifying it.
2. Read it as a legacy graph when valid.
3. Write new stores only after a successful new-format build.
4. Keep legacy data until normal retention/pruning; never delete it during
   migration.
5. Report migration state in diagnostics.

### 5. Send the host an evidence packet, not a forced file choice

Extend `host_reasoning_packet()` with cache and topology information while
preserving source sanitization. The packet must contain:

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

## File-Level Change Plan

1. `scripts/navigator_scope.py`
   - Add portable anchor discovery and relevance evaluation.
   - Add packet v2 construction and compatibility rendering for v1 consumers.
   - Add proposal validation branch for safe, anchored new paths.
   - Preserve current bounded-read and evidence-document controls.

2. `scripts/navigator_graph_lifecycle.py`
   - Accept the anchor slice as lifecycle input.
   - Replace lexical-only target selection with anchor-aware reuse/extension.
   - Record freshness and relevance separately in lifecycle receipts.

3. `scripts/code-graph-mapper.py`
   - Read processed-file facts before reparsing source.
   - Write the versioned derived graph format and retain legacy read support.
   - Make slice coverage queryable by anchor and relation, not only by path.

4. `scripts/code_graph_cache.py` and `scripts/capture_hooks.py`
   - Move per-file facts to the new processed-file cache path.
   - Preserve atomic writes, source hash validation, exclusion rules, and
     non-fatal capture semantics.
   - Remove the current mapper-schema refusal caused by shared filename.

5. `scripts/navigator.py` and start/report renderers
   - Resolve anchors before lifecycle management.
   - Pass packet v2 to the host-facing response.
   - Render a precise evidence-gap question when anchors are insufficient;
     do not ask the user to select an arbitrary unrelated file.

6. Tests
   - Add focused fixtures across UI, API/service, worker/event, CLI, and
     infrastructure/config layouts, using language-neutral expected roles.

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
- Cache corruption, stale hashes, unsafe paths, malformed packets, and missing
  anchors fail closed into bounded clarification rather than owner guessing.

## Validation Plan

1. Unit-test anchor extraction, freshness, relevance, cache migration, and
   safe proposed-path validation.
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
contracts, or installation artifacts. The implementation will be a cross-cutting
runtime and compatibility change and should be delivered in reviewable stages.
