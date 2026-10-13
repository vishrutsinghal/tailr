# TailTrail Managed Workspace Exclusion Problem

Status: observed problem statement

## Executive Summary

TailTrail uses repository discovery to select implementation owners, proof paths,
callers, graph relationships, and focused validation. Agent-managed workspaces
and Git worktrees contain copies of the same repository files, but they are not
application scope for the parent checkout.

Some TailTrail discovery paths currently walk into those managed copies. This
allows stale or duplicate files to enter the candidate pool and compete with
real repository files.

The problem is not that worktrees exist. Worktrees are useful for parallel
agent execution. The problem is that repository discovery does not consistently
classify their contents as managed workspace data before ownership and proof
selection.

## Concrete Example

The target repository contains:

```text
scripts/task-start.py
```

An agent-managed worktree contains a copy:

```text
.claude/worktrees/old-run/scripts/task-start.py
```

Both paths may have the same filename, symbols, imports, tests, and relationship
edges. If both enter the Navigator candidate pool, the copied path can be
selected as an implementation owner or proof path.

The correct classification is:

```text
scripts/task-start.py
  role: application
  status: eligible

.claude/worktrees/old-run/scripts/task-start.py
  role: managed-worktree
  status: excluded
```

## Discovery Pipeline

The affected pipeline is:

```text
filesystem/Git discovery
  -> candidate creation
  -> lexical matching
  -> relationship extraction
  -> owner ranking
  -> proof selection
  -> graph-cache persistence
  -> Start Report and Planning Lock
```

The managed-workspace classification must occur before candidate creation. If it
happens only while rendering the final report, the polluted path may already
have influenced ownership, proof, and graph fingerprints.

## Affected Discovery Paths

The problem can enter through several independent walkers:

- `scripts/code-graph-mapper.py` recursively discovers text and source files;
- `scripts/review-graph.py` builds review candidates and relationship context;
- `scripts/ast-map.py` discovers AST-readable files;
- `scripts/navigator_scope.py` has a filesystem fallback when Git discovery is
  unavailable;
- `scripts/navigator_discovery.py` has its own discovery exclusions.

Each independent exclusion list can disagree with the others. Fixing one walker
is therefore not a complete solution.

## Why the Problem Persists

Graph discovery writes data to persistent cache artifacts such as:

```text
tailtrail-meta/code-graph-cache.json
```

Once a worktree path enters the cache, later Start requests may reuse it even
when the original worktree no longer exists or the current source is unchanged.

Refreshing the cache before fixing the walkers is ineffective:

```text
unfixed walker
  -> refresh
  -> worktree copies discovered again
  -> polluted cache recreated
```

The correct order is:

```text
fix path classification
  -> invalidate stale cache data
  -> refresh graph cache
  -> verify no managed-worktree paths remain
```

## Failure Effects

A polluted candidate pool can cause:

- a stale worktree copy to become the implementation owner;
- a copied test to become the approved proof path;
- duplicate relationship edges to change candidate ranking;
- focused validation commands to target the wrong checkout;
- different Start Reports across runs with no application source change;
- stale worktree content to influence planning fingerprints;
- closure drift when the selected worktree path is not in the real edit scope;
- cache size and scan time to grow unnecessarily.

The result can look like a nondeterministic Navigator decision. The apparent
flakiness is caused by the changing set of nested worktrees, not by random
business behavior.

## Why Host Identity Is Not the Rule

The observed path used Claude's layout:

```text
.claude/worktrees/
```

That does not make this a Claude-only problem. Other agents or host adapters may
use layouts such as:

```text
.codex/worktrees/
.copilot/worktrees/
.git/worktrees/
custom-agent/worktrees/
```

The policy must be host-independent. The host adapter may identify its own
workspace for operational routing, but it must not change application ownership
rules.

## Required Generic Classification

A central policy should classify every discovered path before it becomes a
candidate:

| Role | Meaning | Application scope |
|---|---|---|
| `application` | Real file in the target repository | Eligible after normal evidence |
| `managed-worktree` | Nested agent or Git worktree copy | Never eligible |
| `agent-managed` | Host workspace/control file | Never eligible |
| `tailtrail-managed` | `.tailtrail` state and runtime artifacts | Never eligible |
| `generated` | Cache or generated output | Excluded by default |
| `external` | Outside the selected target root | Never eligible |
| `unknown` | Not safely classified | Clarification or exclusion |

Detection should combine:

- Git worktree metadata;
- generic `worktrees` path components;
- known agent-managed roots;
- TailTrail-managed roots;
- target-root boundaries;
- nested repository/worktree checks.

No scanner should maintain its own unrelated `SKIP_DIRS` policy.

## Current Remediation Status

Already implemented and tested:

- `scripts/code-graph-mapper.py` excludes `.claude` and `worktrees`;
- `scripts/review-graph.py` excludes `.claude` and `worktrees`;
- `scripts/ast-map.py` excludes `.claude` and `worktrees`;
- regression tests preserve real files and exclude nested worktree files;
- the refreshed graph cache contained zero `.claude/worktrees` entries.

Remaining work:

- update `scripts/navigator_scope.py` fallback inventory;
- update `scripts/navigator_discovery.py` exclusions;
- centralize the policy instead of keeping duplicated exclusion lists;
- add Git-aware fallback coverage;
- add cross-agent layout fixtures;
- reject stale managed-worktree cache entries by role.

## Required Regression

The regression must exercise a public discovery path, not only a private helper.
It should create a temporary Git-aware repository fixture containing:

```text
src/real.py
.claude/worktrees/stale-run/src/ghost.py
```

The test should simulate Git being unavailable at the Git boundary, run the
Navigator fallback inventory, and assert:

```text
src/real.py
  -> included

.claude/worktrees/stale-run/src/ghost.py
  -> excluded as managed-worktree
```

The test must also preserve an auditable exclusion reason and confirm that the
excluded file cannot become an owner, proof path, relationship edge, or cache
entry.

## Required Outcome

The implementation is complete when:

- one central path-policy classifier serves all discovery paths;
- worktree and agent-managed copies are excluded before candidate creation;
- real repository files remain discoverable;
- stale caches are invalidated and rebuilt;
- CLI, MCP, and host adapters agree on path roles;
- fallback discovery cannot reintroduce managed-worktree pollution;
- cross-agent fixtures pass;
- exclusion reasons remain available for diagnosis without granting scope.

The detailed architecture and rollout plan are in
[TAILTRAIL-MANAGED-WORKSPACE-EXCLUSION-DESIGN.md](TAILTRAIL-MANAGED-WORKSPACE-EXCLUSION-DESIGN.md).
