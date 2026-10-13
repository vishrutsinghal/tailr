# TailTrail Managed Workspace Exclusion

Status: draft for review

## Purpose

TailTrail supports parallel work through Git worktrees and agent-managed
workspace copies. Those workspaces are useful for isolation, but their files
must not be treated as application ownership or proof evidence for the parent
repository.

The failure mode is duplicate repository content entering discovery:

```text
real file:
  scripts/task-start.py

managed copy:
  .claude/worktrees/old-run/scripts/task-start.py
```

If both paths enter Navigator or graph discovery, stale copies can compete with
real files for ownership, proof, relationship edges, and cache ranking.

## Design Rule

```text
agent workspace isolation is allowed
agent workspace contents are not application scope
```

A managed workspace path may be read for host or workflow operations, but it
must not become:

- an implementation owner;
- an inspection path for the parent repository;
- a proof path;
- a relationship edge source or target;
- a graph-cache candidate;
- an anchor path for the parent checkout.

## Generic Path Roles

The path policy should classify repository paths before candidate creation:

| Role | Meaning | May become application scope? |
|---|---|---|
| `application` | Real file in the target repository | Yes, subject to normal evidence |
| `managed-worktree` | Nested agent or Git worktree copy | No |
| `agent-managed` | Host-specific workspace/control files | No |
| `tailtrail-managed` | `.tailtrail` state and runtime artifacts | No |
| `generated` | Generated metadata or cache output | No by default |
| `external` | Path outside the target repository | No |
| `unknown` | Unclassified path | No until resolved |

## Detection Signals

Detection must use more than one hard-coded agent directory.

### Git worktree evidence

Use Git metadata where available to identify linked worktrees and their roots.
A linked worktree is operational workspace state, not parent-repository
application scope. Note the distinction the detector must keep: `.git/worktrees/`
itself is Git admin metadata, not a nested copy -- only the linked worktree
roots it points at are `managed-worktree`. Substring matching alone cannot
tell these apart; the Git signal must resolve roots, not just match names.

### Path signals

Recognize managed structures such as:

```text
.claude/worktrees/**
.codex/worktrees/**
.copilot/worktrees/**
.git/worktrees/**
*/worktrees/**
```

The generic `worktrees` path component is important because agent names differ.

### Managed-directory registry

Maintain one versioned registry for known agent-managed roots and TailTrail
state directories. Examples may include:

```text
.claude
.codex
.copilot
.tailtrail
.tailtrail-meta
```

The registry is an additional signal, not the only protection. It must be
configurable (a hardcoded name list just recreates today's per-agent bug
for the next agent); matching against it is case-insensitive.

### Repository-root boundary

A path outside the selected target root is `external`. A nested repository or
nested worktree must not be promoted merely because it contains a familiar
filename.

## Central Classifier

Create one shared path-policy helper, for example:

```text
scripts/repository_path_policy.py
```

The helper should expose a single classification API:

```text
classify_repository_path(root, path) -> {
    role,
    status,
    reason_codes,
    repository_root,
    worktree_root,
    content_fingerprint,
}
```

Every scanner and planner must use this helper:

- code graph mapper;
- review graph;
- AST map;
- Navigator fallback inventory;
- repository discovery;
- scope resolution;
- proof candidate selection;
- cache persistence.

No component should maintain an independent `SKIP_DIRS` list.

## Classifier Performance Contract

The classifier runs on every discovered path, so it must be pure
string/path logic with zero I/O per path. Anything needing Git (such as
`git worktree list`) is computed once per run and passed in, never
queried per file -- otherwise discovery gets slow everywhere. This is a
hard requirement on the helper's signature, not an optimization note.

## Signal Precedence

Overlapping signals need a deterministic winner, or identical checkouts
produce different fingerprints. Evaluate in this fixed order, first
match wins:

```text
1. outside target root              -> external
2. TailTrail state roots            -> tailtrail-managed
3. Git worktree copy (cached list)  -> managed-worktree
4. generic `worktrees` component    -> managed-worktree
5. agent-managed roots (registry)   -> agent-managed
6. generated/vendor rules           -> generated
7. otherwise in-root                -> application
```

Case-insensitivity is mandatory at every step (Windows checkouts):
`.CLAUDE`, `Worktrees`, and `TAILTRIAL-META` must match exactly like
their lowercase forms.

## Relationship to the Existing Role Classifier

This policy does not create a parallel role system. It is the
discovery-phase precursor: it answers "is this path even considerable?"
before candidate creation. The existing `classify_repository_role()`
keeps answering "what role does it play?" afterwards. The mapping is one
line: any non-`application` verdict excludes the path with the policy
reason attached; only `application` paths reach file-kind
classification. No second owner/proof vocabulary is minted here.

## Filtering Boundary

Filtering must happen before a path becomes a candidate. The correct order is:

```text
filesystem/Git discovery
  -> repository path classification
  -> exclude managed/external/generated paths
  -> candidate creation
  -> lexical and relationship analysis
  -> owner/proof selection
  -> cache persistence
```

Filtering only during report rendering is too late. A polluted candidate may
already have influenced ranking, relationship edges, or focused proof.

## Exclusion Provenance

Excluded paths should remain explainable without entering application scope:

```json
{
  "path": ".claude/worktrees/run-1/scripts/task-start.py",
  "role": "managed-worktree",
  "status": "excluded",
  "reason_codes": ["nested-managed-worktree", "outside-application-scope"],
  "content_fingerprint": "sha256:..."
}
```

This supports debugging and audit without allowing excluded files to become
owners or proof.

## Cache Behavior

Existing graph caches may already contain polluted paths. After the classifier
is deployed:

1. invalidate affected graph-cache sections;
2. rebuild the cache using the central classifier;
3. verify that no managed-worktree paths remain;
4. persist exclusion provenance separately if diagnostics require it;
5. reject stale cache entries whose path role is no longer `application`.

Refreshing the cache before fixing the walkers is ineffective because it simply
recreates the pollution.

## Cross-Agent Regression Matrix

The same fixture must be tested against every managed layout:

```text
.claude/worktrees/run-a/scripts/ghost.py
.codex/worktrees/run-b/scripts/ghost.py
.copilot/worktrees/run-c/scripts/ghost.py
.git/worktrees/run-d/scripts/ghost.py
custom-agent/worktrees/run-e/scripts/ghost.py
```

Expected result:

```text
real repository file: included
managed worktree file: excluded
```

The fixture should also verify:

- real files with the same basename remain selectable;
- nested worktree files do not create relationship edges;
- excluded paths do not enter proof candidates;
- cache refresh removes historical polluted entries;
- missing Git metadata still uses the same path policy;
- CLI, MCP, and direct scanner entry points agree.

## Host Independence

The policy is host-independent. Claude, Copilot, Codex, MCP, and local CLI
execution may use different workspace layouts, but application ownership rules
must remain identical.

The host adapter may identify its own workspace for operational routing, but it
must not change repository path classification or promote its workspace files
into application scope.

## Rollout Phases

### Phase 1: Shared policy

- Define path roles and reason codes.
- Add the central classifier.
- Add cross-agent fixture tests.

### Phase 2: Scanner integration

- Replace local exclusion lists in code graph, review graph, AST map, and
  Navigator fallback discovery.
- Add candidate-level exclusion provenance.
- No flag day: keep each walker's old list until the shared policy is
  proven for that walker, then delete the old list. A walker is proven
  when its cross-agent fixture passes with the policy on and the old
  list removed.

### Phase 3: Cache migration

- Invalidate polluted cache sections.
- Refresh caches after the walkers use the shared policy.
- Add stale-role rejection during cache reads.

### Phase 4: Scope and proof integration

- Prevent excluded paths from becoming owners, inspection paths, or proof.
- Add Start Report diagnostics when a requested path is excluded.
- Preserve explicit user explanations without granting authority.

### Phase 5: Entry-point parity

- Verify CLI, MCP, orchestration, and direct scanner behavior.
- Add replay and recovery tests.
- Confirm host adapters do not alter path policy.

## Failure Handling

If a path cannot be classified confidently:

```text
unknown -> excluded from application scope -> clarification or user decision
```

TailTrail must not silently guess that an unknown nested path is application
owned. A host may explain the path, but the central classifier and scope
pipeline must still validate the explanation.

## Metrics

Track:

- excluded managed-worktree paths;
- cache entries removed during migration;
- owner/proof candidates rejected by path policy;
- duplicate basename candidates before and after filtering;
- CLI/MCP path-classification parity;
- stale cache entries rejected;
- unknown paths requiring clarification.

## Definition of Done

This design is implemented when:

- all scanners use one repository path classifier;
- agent and worktree layouts are excluded generically;
- real repository files remain discoverable;
- polluted caches are migrated and verified clean;
- excluded paths cannot become owners or proof;
- exclusion reasons remain auditable;
- CLI, MCP, and host adapters agree;
- cross-agent fixtures pass;
- a missing-Git fallback cannot reintroduce pollution.
