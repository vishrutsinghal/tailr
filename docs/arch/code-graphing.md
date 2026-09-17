# Code Graphing in TailTrail — Architecture and Implementation

## 1. Overview

This document describes the code graphing subsystem in TailTrail, including:

- What a "code graph" is and the different techniques used to build one
- TailTrail's existing `code-graph-mapper.py` implementation
- The code-graph cache (`.tailtrail/code-graph-cache.json`)
- Graph freshness, staleness, and passive capture during work
- How graph metrics feed into quantitative AIDLC mode selection
- The R1 calibration decision log for threshold tuning
- The Phase 6 post-discovery re-evaluation hook (implemented)
- Metrics confidence model
- Phased implementation plan (Phases 1–9 implemented except the Phase 5 tuning loop, which is ongoing by nature; host-agent fallback split by R0 — see §3.6/§3.10)

This document is intended for anyone implementing or reviewing the graphing subsystem, the AIDLC mode selection enhancement, or the code-graph acceleration model.

---

## 2. What a Code Graph Is

A code graph is a **graph data structure** where:

- **Nodes (vertices)** represent code entities: files, modules, classes, functions, symbols, endpoints
- **Edges (relationships)** represent connections: imports, calls, inheritance, data flow, type references, layer boundaries, test coverage

Different techniques build different kinds of graphs at different levels of granularity, from cheap file-level dependency maps to expensive full semantic call graphs with type inference.

---

## 3. Main Graph-Building Techniques

### 3.1 AST-Based Static Analysis

**How it works**: Parse source files into Abstract Syntax Trees (AST), then walk the AST to extract symbols (functions, classes, imports) and their relationships.

**Approaches by depth**:

| Depth | What it builds | Cost | Typical tools |
|---|---|---|---|
| **Shallow (token/line level)** | Files → imports → file-level dependencies | Fast — one pass, no tree walking | `ast.parse`, regex on `import`/`from` lines |
| **Medium (symbol level)** | Files → functions → function calls → call graph | Moderate — AST walk per file | `ast` module, clang AST, tree-sitter |
| **Deep (semantic level)** | Full call chains, type inference, data flow, control flow | Expensive — needs type resolution, interprocedural analysis | LSP, language servers, tree-sitter + semantic plugins, SCA tools |

#### Sample Output — Shallow File-Level Dependency Graph

```json
{
  "type": "file_dependency_graph",
  "nodes": [
    {"id": "auth.py", "type": "module", "layer": "src", "symbols": ["login", "logout", "validate_token"]},
    {"id": "orders.py", "type": "module", "layer": "src", "symbols": ["create_order", "get_order", "cancel_order"]},
    {"id": "claims_api.py", "type": "module", "layer": "src", "symbols": ["submit_claim", "validate_claim"]},
    {"id": "models.py", "type": "module", "layer": "src", "symbols": ["Claim", "Order", "User"]},
    {"id": "test_auth.py", "type": "module", "layer": "tests", "symbols": ["test_login", "test_logout"]}
  ],
  "edges": [
    {"from": "orders.py", "to": "models.py", "kind": "imports", "strength": 0.8},
    {"from": "auth.py", "to": "models.py", "kind": "imports", "strength": 1.0},
    {"from": "claims_api.py", "to": "auth.py", "kind": "imports", "strength": 0.9},
    {"from": "claims_api.py", "to": "orders.py", "kind": "imports", "strength": 0.7},
    {"from": "test_auth.py", "to": "auth.py", "kind": "tests", "strength": 1.0}
  ]
}
```

This is a **file-level dependency graph** — nodes are files, edges are import relationships. It answers: "what depends on what, at the file level?"

#### Sample Output — Medium Function Call Graph

```json
{
  "type": "function_call_graph",
  "nodes": [
    {"id": "submit_claim", "file": "claims_api.py", "kind": "function"},
    {"id": "validate_claim", "file": "claims_api.py", "kind": "function"},
    {"id": "create_order", "file": "orders.py", "kind": "function"},
    {"id": "login", "file": "auth.py", "kind": "function"},
    {"id": "validate_token", "file": "auth.py", "kind": "function"},
    {"id": "Claim", "file": "models.py", "kind": "class"}
  ],
  "edges": [
    {"from": "submit_claim", "to": "validate_claim", "kind": "calls", "direct": true},
    {"from": "submit_claim", "to": "create_order", "kind": "calls", "direct": true},
    {"from": "validate_claim", "to": "validate_token", "kind": "calls", "direct": true},
    {"from": "create_order", "to": "Claim", "kind": "instantiates", "direct": true},
    {"from": "login", "to": "validate_token", "kind": "calls", "direct": true}
  ]
}
```

This is a **function-level call graph** — nodes are individual functions/classes, edges are call relationships. It answers: "which function calls which, and where?"


This is a **function-level call graph** — nodes are individual functions/classes, edges are call relationships. It answers: "which function calls which, and where?"

#### Deep Semantic Level (Semantic Call Graph + Type Resolution)

Walks the AST more thoroughly, resolving types, following call chains through multiple hops, and building richer semantic edges:

```json
{
  "type": "semantic_call_graph",
  "nodes": [
    {"id": "submit_claim",
     "file": "claims_api.py",
     "kind": "function",
     "signature": "submit_claim(claim_data: dict) -> ClaimResult"},
    {"id": "validate_claim",
     "file": "claims_api.py",
     "kind": "function",
     "signature": "validate_claim(claim: Claim) -> ValidationResult"},
    {"id": "create_order",
     "file": "orders.py",
     "kind": "function",
     "signature": "create_order(items: List[OrderItem]) -> Order"}
  ],
  "edges": [
    {"from": "submit_claim", "to": "validate_claim", "kind": "calls", "direct": true, "hop": 1},
    {"from": "submit_claim", "to": "create_order", "kind": "calls", "direct": true, "hop": 1},
    {"from": "validate_claim", "to": "validate_token", "kind": "calls", "direct": true, "hop": 1}
  ],
  "cross_layer_edges": [
    {"from_layer": "src", "to_layer": "models", "count": 3}
  ]
}
```

This adds function signatures, multi-hop call chains, type relationships, and cross-layer edges. It answers: "What is the full call chain from this entry point? Which layers does this traverse?"

---

### Technique 2: Import-Level Dependency Graph

Simpler than a call graph — it traces which files/modules import which other files/modules. Faster and less precise but useful for architectural boundaries.

```json
{
  "type": "import_dependency_graph",
  "nodes": [
    {"id": "claims_api.py", "layer": "api", "imports": ["auth.py", "orders.py", "models.py"]},
    {"id": "auth.py", "layer": "service", "imports": ["models.py"]},
    {"id": "orders.py", "layer": "service", "imports": ["models.py"]},
    {"id": "models.py", "layer": "domain", "imports": []},
    {"id": "test_claims.py", "layer": "tests", "imports": ["claims_api.py", "models.py"]}
  ],
  "edges": [
    {"from": "claims_api.py", "kind": "imports", "to": "auth.py", "strength": 1.0},

### Technique 4: Data Flow Graph (DFG)

Tracks how data moves through a function: where values are defined, where they're used, and how they're transformed.

```json
{
  "type": "data_flow_graph",
  "function": "process_order(items: List[OrderItem]) -> Order",
  "file": "orders.py",
  "dataflow_nodes": [
    {"id": "D0", "var": "items", "def_line": 5, "use_lines": [8, 12, 15], "kind": "parameter"},
    {"id": "D1", "var": "total", "def_line": 9, "use_lines": [14, 16], "kind": "local", "init": 0.0},
    {"id": "D2", "var": "item_total", "def_line": 10, "use_lines": [11], "kind": "local", "init": null},
    {"id": "D3", "var": "order", "def_line": 14, "use_lines": [17], "kind": "local", "init": null}
  ],
  "def_use_edges": [
    {"def": "D0", "use": "D2", "at_line": 10, "kind": "passed-as-arg"},
    {"def": "D2", "use": "D1", "at_line": 11, "kind": "accumulate"},
    {"def": "D1", "use": "D3", "at_line": 14, "kind": "field-assignment"},
    {"def": "D0", "use": "D3", "at_line": 15, "kind": "field-assignment"}
  ],
  "slices": [
    {"variable": "total", "reachable_from": "items", "line_range": "9-16", "kind": "def-use chain"}
  ]
}
```

This answers: "Where does each variable come from? Where is it used? Can I trace a value back to its source?"

Useful for finding where sensitive data enters and flows through the system, understanding variable lifetimes, detecting unused variables, and tracking data provenance for security analysis.

---

### Technique 5: Incremental / Cached Graph Construction

Rather than building the full graph every time:
1. Hashes each file's content
2. Only re-parses files whose hash has changed
3. Reuses previously parsed ASTs, symbols, and edges for unchanged files
4. Merges incremental updates into the cached graph

```json
{
  "type": "incremental_graph_build",
  "strategy": "hash-based-incremental",
  "cache_version": "1.0",
  "files": [
    {
      "path": "auth.py",
      "hash": "sha256:abc123...",
      "status": "unchanged",
      "cached_at": "2026-09-15T10:00:00Z",
      "reused": true,
      "nodes_cached": 3,
      "edges_cached": 4
    },
    {
      "path": "claims_api.py",
      "hash": "sha256:def456...",
      "status": "changed",
      "cached_at": "2026-09-10T09:00:00Z",
      "reparsed": true,
      "reparse_time_ms": 12,
      "nodes_cached": 5,
      "edges_cached": 7
    }
  ],
  "graph_stats": {
    "total_nodes": 150,
    "total_edges": 340,
    "nodes_from_cache": 145,
    "nodes_reparsed": 5,
    "edges_from_cache": 330,
    "edges_reparsed": 10,
    "build_time_ms": 15,
    "full_build_time_ms_estimated": 450
  },
  "stale_files": [],
  "unresolved_symbols": []
}
```

This answers: "Which files changed since last build? How much work do we save by caching?"

Useful for making graph builds fast enough to run frequently — only paying for what changed, and detecting which parts of the graph may be stale.

---

That covers the main graph-building techniques with samples. The next sections document the actual code-graphing implementation in the TailTrail codebase.

---

    {"from": "claims_api.py", "kind": "imports", "to": "orders.py", "strength": 1.0},
    {"from": "auth.py", "kind": "imports", "to": "models.py", "strength": 1.0},
    {"from": "orders.py", "kind": "imports", "to": "models.py", "strength": 1.0}
  ],
  "layer_hierarchy": ["domain", "service", "api", "tests"],
  "layer_boundaries": [
    {"from": "tests", "to": "api", "direction": "allowed-down"},
    {"from": "api", "to": "service", "direction": "allowed-down"},
    {"from": "service", "to": "domain", "direction": "allowed-down"}
  ]
}
```

Answers: "What does each module depend on? Are there layer violations?"

Useful for architectural compliance, circular dependency detection, and computing fan-in/fan-out per module.

---

### Technique 3: Control Flow Graph (CFG)

Models execution flow *within a single function*: basic blocks and possible paths between them (branches, loops, exceptions).

```json
{
  "type": "control_flow_graph",
  "function": "validate_claim(claim: Claim) -> ValidationResult",
  "file": "claims_api.py",
  "basic_blocks": [
    {"id": "B0", "range": "lines 10-12", "instructions": ["entry", "claim = cast(Claim, claim)"]},
    {"id": "B1", "range": "lines 13-15", "instructions": ["if claim.amount <= 0:"]},
    {"id": "B2", "range": "lines 16-17", "instructions": ["raise ClaimValidationError('amount must be positive')"]},
    {"id": "B3", "range": "lines 18-20", "instructions": ["if claim.user_id is None:"]},
    {"id": "B4", "range": "lines 21-22", "instructions": ["raise ClaimValidationError('user_id required')"]},
    {"id": "B5", "range": "lines 23-25", "instructions": ["return ValidationResult(valid=True)"]}
  ],
  "edges": [
    {"from": "B0", "to": "B1", "kind": "fallthrough"},
    {"from": "B1", "to": "B2", "kind": "true-branch", "condition": "claim.amount <= 0"},
    {"from": "B1", "to": "B3", "kind": "false-branch", "condition": "claim.amount > 0"},
    {"from": "B2", "to": "exit", "kind": "throw", "exception": "ClaimValidationError"},
    {"from": "B3", "to": "B5", "kind": "false-branch", "condition": "claim.user_id is not None"}
  ],
  "cyclomatic_complexity": 3,
  "decision_points": [
    {"line": 13, "type": "if", "condition": "claim.amount <= 0"},
    {"line": 18, "type": "if", "condition": "claim.user_id is None"}
  ]
}
```

Answers: "What are all possible execution paths? How complex is this function (cyclomatic complexity)? Where are the decision points?"

Useful for computing cyclomatic complexity, identifying error paths, and finding unreachable code.

---

## 2. Code Graphing in the TailTrail Codebase

### 2.1 Where Graph Building Lives

The primary graph-building code lives in:

- **`scripts/code-graph-mapper.py`** — the existing mapper that converts `scope_evidence` candidate/edge data plus `code-graph-cache.json` into structured graph-derived metrics. Lives in `scripts/code_graph_mapper.py` / `scripts/code-graph-mapper.py` depending on checkout; the implementation currently extracts graph-derived fields from `scope_evidence` candidates and edges (cross-layer edges, candidate path/ratio data) and from a cached graph JSON (symbols, endpoints, external-dependency edges).
- **`docs/arch/navigation_aidlc_improvements.md§5`** and **`docs/arch/navigator_aidlc_improvements.md§5`** — the design framework that defines the tiered metric extraction model, the dual-gate wiring, and how graph-derived signals feed the quantitative dimension of AIDLC mode selection.

Note on terminology: the repository does not currently maintain a separate `code-graph-cache.json` as a first-class artifact produced by an active graph-builder. "Code graph" in this document refers to the graph conceptually encoded by `scope_evidence` candidates/edges plus any cached graph JSON consumed by `metrics_extractor.py` — not to a produced structural graph serialized at build time. Section 2.2 below lists the model structure that `metrics_extractor.py` consumes; it is not the schema of a currently-produced cache file.

The graph-derived metrics are consumed by:

- **`scripts/metrics_extractor.py`** — extracts quantitative complexity metrics: `cheap_scope_metrics()` (Tier 1 from `likely_impacted_files`), `graph_scope_metrics()` (Tier 2 from `scope_evidence` candidates/edges/behavior chains), `mapper_scope_metrics()` (Tier 3 from a cached graph JSON when present), `compute_complexity()` (tier selection + thresholds), and `scope_signal()` (returns whether scope supports Standard).
- **`scripts/task-start.py`** — Start plan assembly; `aidlc_mode_selection()` reads graph-derived `scope_signal` and `scope_floor_lite` as Dimension 2 of the dual-gate, and the Phase 6 re-evaluation hook reuses the same signals before lock finalization.
- **`scripts/navigator_scope.py`** — provides `scope_evidence` candidates/edges/behavior chains that `metrics_extractor.py` consumes as Tier 2 input.

The AIDLC mode selection side of this relationship is documented in detail in **`docs/arch/navigation_aidlc_improvements.md`** and **`docs/arch/navigator_aidlc_improvements.md`**; this file focuses on the graph-data side of the contract.

### 2.2 What the Code-Graph Mapper Produces

The "mapper" here is not a separate graph-builder binary. It is the extraction layer in `scripts/metrics_extractor.py` that reads **`scope_evidence`** candidates/edges/behavior chains (produced by `scripts/navigator_scope.py::assess_scope_quality`) and an optional cached graph JSON to produce the metrics that feed AIDLC mode selection.

The metrics layer consumes four data structures:

| Structure | Source | What it contributes |
|---|---|---|
| `likely_impacted_files` | Start-plan draft / scope candidates list | Tier 1: file count, changed-line estimate, path depth, layer breakdown, affected-paths set |
| `scope_evidence.candidates` | `assess_scope_quality()` in `scripts/navigator_scope.py` | Tier 2: implementation-owner file set, per-layer candidate ratios |
| `scope_evidence.edges` | `assess_scope_quality()` in `scripts/navigator_scope.py` | Tier 2: cross-layer edge count (edges whose endpoints live in different layers, only counted when both endpoint candidates are known) |
| `scope_evidence.behavior_chains` | `assess_scope_quality()` in `scripts/navigator_scope.py` | Tier 2: chain states (complete / partial / broken), depth list + stddev, incomplete-chain flag |
| `scope_evidence.module_resolution` (optional) | `assess_scope_quality()` in `scripts/navigator_scope.py` | Tier 2: ambiguous-module count |
| `code-graph-cache.json` (optional) | cached graph JSON on disk | Tier 3: symbol count in scope, endpoint count in scope, external-dependency edge count |

The metrics layer **does not** currently produce a serialized structured graph (nodes with `node_id`, `signature`, `call_edges`, `type_edges`, etc.) as a first-class artifact. The model it consumes — `scope_evidence` + optional cached JSON — is a lighter contract designed as input to quantitative mode selection, not a full structural graph serialization.

The **Tier 2 contract** (`scope_evidence`) is the authoritative graph-like structure currently in use. Its schema is defined in:

- **`schemas/navigator-scope-quality.schema.json`** — the JSON Schema for the `scope_evidence`-rooted assessment document
- **`scripts/navigator_scope.py::assess_scope_quality()`** — produces the `scope_evidence` document from candidate/edge/behavior-chain/source-finding data during scope discovery
- **`docs/arch/navigation_aidlc_improvements.md`** (and sibling) — the design framework that explains how Tier 2 fields map to quantitative mode-selection signals

If a fuller structural graph (AST nodes, call edges, type edges, import edges) is built later, it would be consumed as additional Tier 3 input by the same `metrics_extractor.py` interface — the tier model is designed to degrade gracefully from full graph → `scope_evidence` → `likely_impacted_files`.

### 2.3 How the Mapper Reads Files

The metrics layer reads files only in support of metric extraction, not to build a standalone graph. Currently:

1. **Tier 1** — Reads `likely_impacted_files` list (paths + line estimates) from the Start plan / scope draft. No file bytes read; this is a list-based extraction.
2. **Tier 2** — Reads `scope_evidence` document (JSON on disk or in the assessment result). No file bytes read; this is a document-based extraction of candidate/edge/chains data already computed by `assess_scope_quality()`.
3. **Tier 3** — Optionally reads a cached graph JSON (`code-graph-cache.json`) if present. File bytes are not re-parsed; the cache is a pre-built artifact whose format is up to the cache producer.

This is the current implementation. A future phase could add AST/import/call parsing as a Tier 3 producer of the cached JSON, but it is not implemented yet.

### 2.4 Graph Consumption Patterns in Navigator

Navigator uses the graph for:

- **Candidate identification** — given a target file/symbol, find related candidates via import edges, call edges, and same-file membership
- **Scope expansion** — from an initial candidate, walk edges to discover transitively related code
- **Layer analysis** — compute which layers a change touches by walking from the changed file's layer to reachable layers
- **Cross-layer edge counting** — count edges that cross layer boundaries (e.g., API → domain) for the quantitative metrics
- **Call chain depth** — walk call edges from an entry point to compute call chain depth and depth variance

### 2.5 Technique Comparison for the TailTrail Use Case

For the specific goal of feeding quantitative complexity metrics into AIDLC mode selection, here's how the techniques stack up:

| Technique | Good for AIDLC metrics? | Cost | Completeness |
|---|---|---|---|
| **Shallow file-level (imports only)** | Partially — can compute layer crossings and file fan-in/out | Low | Misses intra-file structure |
| **Function-level call graph** | Yes — call chain depth, cross-layer call edges, fan-in/fan-out | Medium | Captures function-to-function relationships |
| **Deep semantic (type resolution + multi-hop)** | Best — full call chains, type relationships, accurate layer analysis | High | Most complete but expensive |
| **Import dependency graph** | Partially — good for layer analysis, misses call structure | Low | Fast but coarse |
| **Control flow graph** | Partially — cyclomatic complexity per function | Medium | Intra-function only |
| **Data flow graph** | Partially — data provenance, variable flow analysis | High | Intra-function, specialized |
| **Incremental/cached** | Enables the above to be fast enough to run on demand | Low amortized | Depends on cache validity |

**Recommendation for the TailTrail use case**: A **function-level call graph with layer classification** is the sweet spot. It captures enough structure (call chains, cross-layer edges, fan-in/fan-out) to feed meaningful quantitative metrics into AIDLC mode selection without the cost of full semantic analysis. Layer classification comes from the file path convention, so no type resolution is needed.

---

---

## 3. Phased Implementation Plan

This section defines the phased implementation of the graphing subsystem. Each phase is independently testable; dependencies are explicit. Order rationale is summarized in §3.10.

> **Numbering note (revised):** this plan was revised to a 9-phase breakdown (cache → passive capture → explicit build → metrics → thresholds → mode-selection wiring → lifecycle/staleness → commit prompt → multi-language). The prior 6-phase numbering is superseded here. Mapping to prior references (e.g. `navigator_aidlc_improvements.md`): old Phase 3 (metrics extraction) = new Phase 4; old Phase 6 (post-discovery re-evaluation) = part of new Phase 6; old Phase 5 (host-agent fallback, split by R0) = see §3.6 note below, not on the critical path.

### 3.1 Phase 1 — Core Cache Infrastructure (foundation everything else builds on)

**Goal**: Establish the central cache artifact and its read/write contract. Without it, none of the metrics, prompts, or staleness detection work.

**Deliverables**:

| Item | What it is |
|---|---|
| Cache data model | Schema for a graph entry: file → symbols, endpoints, cross-file edges, last-read timestamp, file size, etc. Canonical paths: `.tailtrail/code-graph-cache.json` or `tailtrail-meta/code-graph-cache.json`. |
| `load()` / `save()` | Read/write the JSON with validation so a corrupt cache doesn't crash the agent. |
| `update(source_files)` | Incremental update: given files the agent actually read, merge new info rather than rebuilding from scratch. |
| `clear()` / selective invalidation | When to wipe: by file path, by session, by staleness age. |

**Why first:** storage layer. Every other phase reads from or writes to it. Get the contract right early; the rest is mostly wiring.

**Sensible default shape (start simple — file-level granularity is enough for v1):**

```json
{
  "version": 1,
  "last_updated": "<iso timestamp>",
  "files": {
    "src/auth.py": {
      "last_read": "<iso>",
      "symbols": ["login_user", "validate_token"],
      "endpoints": [],
      "imports": ["src/db.py", "src/config.py"],
      "size_bytes": 2048
    }
  }
}
```

Don't over-engineer v1. File-level granularity with symbols, imports, and read timestamp is enough to start. `last_read` must exist from day one because Phase 7 (staleness) needs it — adding it later forces a migration.

**Status**: ✅ Implemented — `scripts/code_graph_cache.py` (`empty_cache` / `normalize_cache` / `load` / `save` / `inspect_file` / `update` / `clear` / `invalidate` / `prune_missing` / `prune_older_than` / `stale_files`; checked by `tests/test_code_graph_cache.py`, 7 tests). Corrupt cache returns empty + reason instead of crashing; writes are atomic; `update()` merges incrementally with one batched save. Cheap extraction reuses dependency-free `code_relationships.extract` (plus a small Python decorator-route scan for `endpoints`). Default write path is local (`.tailtrail/code-graph-cache.json`); reads prefer existing shared (`tailtrail-meta/`) then local, matching `metrics_extractor.load_code_graph_cache()` order.

**Effort**: 1-2 days · **Dependencies**: none · **Risk**: low

### 3.2 Phase 2 — Passive Capture During Agent Work

**Goal**: Silently update the Phase 1 cache as a side effect of normal agent work (reading/exploring), via `update()`.

**Status**: ✅ Implemented — `scripts/capture_hooks.py` (`on_file_read` / `on_file_edit` / `on_import_encountered` / `on_symbol_observed` / `on_call_site_encountered` queue repo-relative paths in memory with zero disk I/O; `flush(root)` merges them into the Phase 1 cache in one batched `code_graph_cache.update()`; `pending()` / `discard()` support scope warm-up and selective clear; checked by `tests/test_capture_hooks.py`, 9 tests). The prior parallel-store draft (`scripts/capture_cache.py` → `.tailtrail/capture-cache.json`) is retired and removed; the Phase 1 cache shape is the single system of record. `graph_builder.commit_graph()` resolves scope from explicit targets → pending queue → Phase 1 cache files, and discards built paths from the queue (residual preserved).

**Key design decisions:**

- **Invisible to the main task.** Capture must not interrupt or slow down real work. All hooks are best-effort: failures are swallowed and never break the task.
- **Batched, not per-line.** Don't flush on every read. Flush on a natural boundary: end of a file-read session, end of a tool call touching multiple files, or on a timer.

**What gets captured (start minimal):**

- Which files were read
- Symbols/functions defined in those files (cheap extraction)
- Import references between files
- Rough line count or size

**What NOT to capture yet:**

- Full AST
- Dynamic call graphs
- Runtime behavior

That's Phase 3+ territory. Phase 2 is "agent read these files, here's what we can cheaply infer." Capture only what is already observed for task reasons — no new reads, no extra token cost. Symbol/import/size detail is derived at `flush()` time from file content already on disk; `on_traceback_observed` is kept as a signature-compatible no-op.

Flush boundaries: end of a file-read session, end of a multi-file tool call, or the 50-path auto-flush safety net. Every hook is best-effort and never raises.

**In-repo wiring (implemented):** `navigator_scope.investigate()` queues every file it actually reads (`facts` keys: broad + targeted discovery reads) and calls `flush(root)` once — passive capture as a side effect of scope discovery, via new opt-out flag `allow_passive_capture` (default `True`, mirroring `allow_git_inventory` / `allow_persistent_cache`). Threaded through `navigator.decide()`; the read-only `navigator scope inspect` CLI (`scripts/navigator-scope.py`) passes `allow_passive_capture=False` to honor its non-persisting contract. Checked by `tests/test_scope_capture_wiring.py` (capture populates the Phase 1 cache with correct symbols; opt-out writes nothing; results unchanged either way). Host-agent wiring beyond this (calling hooks from a specific external agent loop) remains per-host integration, not a TailTrail phase.

**Effort**: 1-2 days · **Dependencies**: Phase 1 · **Risk**: low

### 3.3 Phase 3 — Explicit Graph Build (on demand, not passive)

**Goal**: A deliberate, possibly expensive pass that builds a richer graph than passive capture can. Triggered by an explicit user command, a policy rule (e.g. before a large refactor), or session start for a known large project.

**Why separate from Phase 2:** passive capture is optimized for speed and non-intrusiveness; an explicit build can afford AST parsing, import-chain following, symlink resolution, etc. Don't make Phase 2 do Phase 3's job — different constraints, different triggers.

**Deliverables:**

| Item | Notes |
|---|---|
| AST-based symbol extraction | More accurate than regex inference. Per language; start with the primary language (Python, given TailTrail's stack). |
| Import/usage edge extraction | Which symbols are imported where — the cross-file edges. |
| Optional: call graph (limited) | Function A calls function B. Expensive; optional and language-specific. |
| Validation step | After building, validate the graph isn't empty or obviously broken before trusting it. |

**Flow (implemented):** parse each target file's AST → extract symbols/imports/call edges → cross-check passive queue (warmed files in scope when no explicit targets given; Phase 1 cache files as second fallback) → assemble nodes + edges → validate → write cache (shared `tailtrail-meta/` by default, `--local` for `.tailtrail/`) → discard built paths from the passive queue (residual preserved). Depth: `shallow` = imports only; `medium` = symbols + call edges (recommended for AIDLC metrics); `deep` = full mapper output. AST failures degrade gracefully (unparseable files yield no symbols, never break the build).

**Language strategy:** Python leads via AST (`extract_python`); other languages via the dependency-free `code_relationships` extractor + mapper heuristics. No universal-semantic pass — deliberately out of scope.

**Status**: ✅ Implemented — `scripts/graph_builder.py::commit_graph(root, target_files, depth, write_shared, clear_passive)` orchestrating the existing mapper (reuse-first: AST extraction, hashing, cache write stay in `code-graph-mapper.py`), plus `validate_payload()`, depth post-filtering, and a runnable CLI trigger (`python scripts/graph_builder.py --root . --changed <file> --depth medium [--local]`, exit 2 on empty scope). Checked by `tests/test_graph_builder.py` (11 tests: depth behavior, passive/Phase 1 scope fallback, residual preservation, validation round-trip, CLI build + CLI no-scope).

Layer classification stays a metrics-time concern (`metrics_extractor._infer_layer` from path conventions, no type resolution) — intentionally not duplicated into the build (see deferred item D1 below).

**Deferred / explicitly skipped (tracked):**

| ID | Item | Decision | Revisit trigger |
|---|---|---|---|
| D1 | Stamp `layer` into build output | **Skip** — layers are derived at metrics time from paths, always current; stamping creates a second source of truth that drifts when conventions change. Single consumer (`metrics_extractor`) needs no shared copy. | A second layer-consumer appears → extract `_infer_layer` into a shared helper instead of stamping. |
| D2 | Repoint Navigator's suggested `graph map`/`graph refresh` commands (`navigator.py`) at the builder CLI | **Done in Phase 8** — the commit prompt suggests `graph_builder --depth shallow\|medium` from live coverage/scope data; Navigator's default suggestions intentionally stay on the mapper path. | Closed. |

**Effort**: 2-3 days · **Dependencies**: Phase 1 (Phase 2 warms it but is not strictly required) · **Risk**: medium (AST failures need graceful degradation)

### 3.4 Phase 4 — Metrics Extraction (the AIDLC integration point)

**Status**: ✅ Implemented.

**Goal**: Read the graph (Phase 2 passive cache or Phase 3 explicit build) and produce quantitative signals that feed into `aidlc_mode_selection()`. This is where `metrics_extractor.py`-style logic lives.

**Implementation principle:** the metrics module must be **standalone and testable** — not deeply embedded in the agent loop. It takes a scope document or file list and returns a metrics dict (testable like the R1/R2 suites, reusable across the dual-gate and the re-evaluation hook).

**Tiered approach:**

| Tier | Source | Cost | When available |
|---|---|---|---|
| Tier 1 | `likely_impacted_files` + file list | Near-zero | Always |
| Tier 2 | `scope_evidence` document (from `investigate()`) | Low | After scope discovery |
| Tier 3 | Full `code-graph-cache.json` | Medium | After graph is built/populated |

**Deliverables (implemented):**
- `scripts/metrics_extractor.py`
- `extract_scope_complexity_metrics(document, root)` — dispatches on `plan["scope_evidence"]` vs `plan.get("likely_impacted_files", [])`
- `compute_complexity(likely_impacted_files, scope_evidence, root)` — Tier 1 always from `likely_impacted_files`; Tier 2 from `scope_evidence` if present; Tier 3 from `code-graph-cache.json` if present and covering included paths
- `load_thresholds(root)` — loads project overrides from `.tailtrail/aidlc-scope-thresholds.json` or falls back to `DEFAULT_THRESHOLDS`
- `assess_scope_quality(document, goal, tags, root, ..., compute_complexity=False)` — when `compute_complexity=True` returns `complexity_metrics` from the same code path

**Signals actually extracted:**

| Layer | Signal | Source | Used in dual-gate |
|---|---|---|---|
| Always | `affected_files` | `likely_impacted_files` | Yes — `affected_files_standard` / `affected_files_lite_floor` |
| Always | `changed_lines_estimate` | `likely_impacted_files` | Yes — `changed_lines_lite_floor` |
| Always | `layer_breakdown` | `likely_impacted_files` paths | Informational |
| Tier 2 | `affected_paths` (implementation-owner only) | `scope_evidence.candidates` roles | Informational |
| Tier 2 | `cross_layer_edges` | `scope_evidence.edges` + candidate layers | Yes — `cross_layer_edges_standard` |
| Tier 2 | `call_chain_depths`, `call_chain_depth_stddev` | `scope_evidence.behavior_chains` | Yes — `call_chain_depth_stddev_standard` |
| Tier 2 | `behavior_chain_incomplete` | `scope_evidence.behavior_chains.state` | Dual-gate (Standard/Full thresholds) |
| Tier 2 | `module_resolution_ambiguous` | `scope_evidence.module_resolution` | Yes — `module_resolution_ambiguous_standard` |
| Tier 2 | `investigation_files_read` | `scope_evidence.investigation` | Informational |
| Tier 3 | `symbols_in_scope`, `endpoints_in_scope` | `code-graph-cache.json` | Informational |
| Tier 3 | `external_dependency_edges` → `new_external_deps` (gate key) | `code-graph-cache.json` `service_edges` (`http-url`/`service-config`, in-scope) + legacy `edges[kind=external_dep]` | Yes — `new_external_deps_standard` |

Dual-gate signals to prioritize going forward: `affected_files`, `changed_lines_estimate`, `cross_layer_edges`, `call_chain_depth_stddev`, `module_resolution_ambiguous`, `new_external_deps`. Additive (extract but don't gate on yet, except where already thresholded): `symbols_in_scope`, `endpoints_in_scope`, `behavior_chain_incomplete`.

Every metric dict carries a `source` field (`"likely_impacted_files_only"`, `"scope_evidence"`, or `"scope_evidence+mapper"`) plus a `thresholds` snapshot so the decision is auditable.

**Fallback chain** (in `compute_complexity`):
- `scope_evidence` missing or not a dict → Tier 1 only; `source = "likely_impacted_files_only"`
- `scope_evidence` present, no graph cache → Tier 1 + Tier 2; `source = "scope_evidence"`
- `scope_evidence` + graph cache with mapper coverage → Tier 1 + Tier 2 + Tier 3; `source = "scope_evidence+mapper"`

Mode selection never blocks on graph availability.

**Phase 4 hardening (implemented):** audit found the `new_external_deps` gate was dead — `compute_complexity` set `external_dependency_edges` while `evaluate_scope_signal` read `new_external_deps`, and `mapper_scope_metrics` read `graph.edges`, a key the real mapper never emits (it emits `service_edges`). Fixed: mapper counts in-scope external `service_edges` (`http-url`/`service-config`; legacy `edges[kind=external_dep]` still accepted), `compute_complexity` maps the count onto the `new_external_deps` gate key, `evaluate_scope_signal` honors a project `behavior_chain_incomplete_standard: False` override, and the R1 log entry carries `new_external_deps` for calibration. Verified against the repo's own `tailtrail-meta` cache (real `service_edges` key present, no `edges` key). Checked by 4 new tests in `tests/test_metrics_extractor.py`; existing `test_aidlc_reevaluation.py` unaffected.

**Effort**: 1-2 days · **Dependencies**: Phase 1 minimum, Phase 2 to populate; Phase 3 enriches Tier 3 but Tier 1+2 work without it · **Risk**: low

### 3.5 Phase 5 — Thresholds and Calibration

**Status**: ✅ Implemented (defaults + validated overrides + R1 log + review CLI; the *tuning itself* stays an ongoing loop by nature).

**Goal**: Metrics are useless without thresholds to interpret them. Make thresholds (1) configurable per project, (2) observable, (3) calibratable.

**Deliverables:**

| Item | Notes | Status |
|---|---|---|
| Default thresholds | Reasonable documented values (see below). | ✅ in `DEFAULT_THRESHOLDS` |
| Project override file | `.tailtrail/aidlc-scope-thresholds.json` — tune without code changes. | ✅ via `load_thresholds(root)` + `validate_thresholds()` |
| Calibration log | R1 decision log — every dual-gate fire/non-fire logs metrics + path taken. | ✅ R1 log + `new_external_deps` field |
| Observability | Answer: how often did scope_signal fire? keyword_signal? how often did they disagree? | ✅ via review CLI (below) |

**Phase 5 hardening (implemented):** audit found overrides were merged unvalidated — a typo'd key was silently ignored, a mistyped value (e.g. `"many"`) could crash comparisons downstream. Fixed: `read_threshold_override()` + `validate_thresholds()` (unknown keys, wrong types, negative numerics dropped with warnings; strict bools; safe defaults always win; `load_thresholds()` signature unchanged). The loop also had no runnable surface — fixed with a read-only CLI: `python scripts/metrics_extractor.py --root . thresholds` (effective config + override warnings) and `... calibration` (fire rates, scope-floor holds, zero-metrics runs, threshold-drift warning). Checked by 5 new tests in `tests/test_metrics_extractor.py`.

**Current defaults** (project-tunable; loaded by `load_thresholds(root)`):

```python
DEFAULT_THRESHOLDS = {
    # Standard-escalation thresholds (any one fires scope_signal)
    "affected_files_standard": 20,
    "cross_layer_edges_standard": 2,
    "call_chain_depth_stddev_standard": 3.0,
    "module_resolution_ambiguous_standard": 3,
    "new_external_deps_standard": 1,
    "behavior_chain_incomplete_standard": True,
    # Standard floor (minimum scope to qualify for Standard)
    "affected_files_standard_floor": 10,
    "cross_layer_edges_standard_floor": 1,
    # Full escalation thresholds (any one fires Full candidate)
    "affected_files_full": 80,
    "cross_layer_edges_full": 6,
    "call_chain_depth_stddev_full": 5.0,
    "behavior_chain_incomplete_full": True,
    # Lite floor (keeps Lite even if keyword_signal fires)
    "affected_files_lite_floor": 5,
    "changed_lines_lite_floor": 50,
}
```

**Calibration is iterative, not one-shot.** Set defaults → run real tasks → `calibration` review → adjust the override file → repeat. The tooling for the loop is done; the tuning itself never closes.

**Known non-goal (tracked):** the `*_full` thresholds are defined but consumed by no gate — Full escalation policy lives in the Start path, not the extractor. If Full ever needs the same single-definition treatment as Standard got in Phase 6, that's a Phase 6 follow-up, not Phase 5 work.

**Effort**: ongoing · **Dependencies**: Phase 4 · **Risk**: low

### 3.6 Phase 6 — Wiring into Mode Selection (the actual integration)

**Status**: ✅ Implemented (dual-gate + R2 post-discovery re-evaluation).

**Goal**: `aidlc_mode_selection()` gains a dual-gate: Gate 1 (intent) + Gate 2 (scope metrics from Phase 4 crossing Phase 5 thresholds → scope_signal).

**Decision logic (simplified):**

```
if explicit_flag:
    use explicit mode
elif intent == "off":
    Off
elif intent == "full":
    Full
elif keyword_signal OR scope_signal:
    Standard  (with scope_floor check to prevent over-escalation on tiny scopes)
else:
    Lite
```

**The scope_floor is important:** even if scope_signal fires, a genuinely tiny scope (few files, low lines) stays Lite. Prevents a 1-file change with one cross-layer edge from escalating incorrectly.

**Implementation** (see `navigator_aidlc_improvements.md` dual-gate + Phase 6 design, R2 run):

- `scripts/task-start.py` — Start plan assembly; `aidlc_mode_selection()` reads `scope_signal` + `scope_floor_lite` as Dimension 2 of the dual-gate. Gate 1 is `_aidlc_intent()` (explicit full/standard/off captured directly; bare "use AIDLC" → Standard); keyword fallback applies only when host intent is unavailable.
- `compute_re_evaluation(lite_mode, hands_free, scope_evidence, likely_impacted_files, root)` in `scripts/metrics_extractor.py` — post-discovery re-check reusing the **exact same** `compute_complexity()` → `scope_signal` / `scope_floor_lite` pipeline. No separate trigger set.
- `planning_lock.create(..., re_evaluation_suggestion=None)` — consumes the suggestion; lock draft records `re_evaluation_suggested` + complexity snapshot before approval.
- `task-start.py` post-discovery path wires the call just before lock creation.

**Properties:**

- **Escalation-only**: Lite → Standard when `scope_signal=True` and not `scope_floor_lite` and not already escalated. Never modifies `off` or `full`.
- **Pre-lock only**: mode frozen after lock approval; draft requires explicit user approval, never silently advances.
- **Approval-bound**: draft carries `re_evaluation_suggested=True` + snapshot (`source`, `scope_signal`, `scope_floor_lite`, metrics).
- **Single threshold set**: initial decision and re-check share the same calibrated `scope_signal` / `scope_floor_lite` — literally the same function (`evaluate_scope_signal`), not a copy (see hardening note).

**Phase 6 hardening (implemented):** audit found `_aidlc_mode_selection_inner()` in `task-start.py` duplicated the signal/floor comparisons inline instead of calling `evaluate_scope_signal()` — the Phase 4 behavior-gate fix therefore applied to re-evaluation but not to initial selection, so the two points could disagree on identical complexity. Fixed: initial selection now calls `evaluate_scope_signal(complexity)` directly (net −12 lines); the duplicated hardcoded fallbacks are gone. Proven by `test_selection_and_reevaluation_agree_when_behavior_gate_disabled` (fails pre-fix, passes post-fix).

**Host-agent qualitative fallback note (old Phase 5, R0 split — not on the critical path):** 5A host-intent roundtrip ⏸ deferred (live `_aidlc_intent()` + dual-gate already covers the agreed outcome; revisit only if R1 logs show regex-missed explicit intents); 5B qualitative complexity fallback ❌ rejected unless R1 logs show real `zero_metrics` runs unfixable via better discovery. Retained as history only.

**Effort**: ~2 days (R2 portion) · **Dependencies**: Phase 4 + Phase 5 (placeholder thresholds suffice for wiring) · **Risk**: low-medium (approval-boundary care; escalation-only keeps it contained)

### 3.7 Phase 7 — Cache Lifecycle and Staleness Management

**Goal**: Handle cache aging — files change, projects evolve.

- **Staleness detection:** file mtime vs cache `last_read` — changed since last read → mark stale.
- **Selective invalidation:** clear stale entries without wiping the whole cache.
- **Full invalidation triggers:** new session, project reset, explicit user request.
- **Garbage collection:** drop entries for files that no longer exist.

**Why not first:** Phases 1–6 can ship with simple "clear on session start." Staleness management is a refinement that matters more as the cache persists across sessions. **But design it early:** the schema includes `last_read` timestamps from day one (see Phase 1) to avoid a later migration.

**Status**: ✅ Implemented — primitives existed since Phase 1; this phase added the Tier 3 trust gate and the explicit-request trigger surface.

**What was already there (Phase 1):** `stale_files()` (mtime vs `last_read`), `invalidate()` (selective), `clear()` (full), `prune_missing()` (GC), `prune_older_than()` (age-based).

**Phase 7 additions:**

- **Tier 3 trust gate (the tracked Phase 4 pickup — done):** `mapper_cache_freshness()` in `metrics_extractor.py` re-hashes in-scope files carrying cached sha256 metadata (`source_files`/`watch_files`/`scanner_evidence`); a missing or changed file makes the cache stale for that scope. `compute_complexity()` degrades to Tier 1+2 with a logged `tier3_skipped` reason instead of trusting drifted symbols. Cost is bounded by the affected set (no full-repo scan on the Start path). Caches with no metadata (legacy/test shapes) are trusted as before — verified when verifiable, backward compatible otherwise.
- **Lifecycle CLI (explicit-request trigger):** `python scripts/code_graph_cache.py --root . status|prune-missing|prune-older-than|invalidate|clear` (text/JSON). Session-start and project-reset clears remain host behaviors; this is how a user requests them.
- **Shape guard (found by testing):** the Phase 1 and mapper caches share canonical paths but not schemas — lifecycle writes *refuse* (exit 2) mapper-shaped files instead of normalizing them into oblivion, and `status` reports the kind honestly.

Checked by 2 freshness tests in `tests/test_metrics_extractor.py` (changed/missing file → skip + reason) and 5 CLI tests in `tests/test_code_graph_cache.py` (status/prune/invalidate/clear + mapper-shape refusal).

**Explicitly skipped (tracked):**

| ID | Item | Decision | Revisit trigger |
|---|---|---|---|
| D3 | Automatic session-start / project-reset clearing | **Skip** — clearing is a host lifecycle behavior and no host loop lives in-repo; the CLI is the trigger surface hosts call. Auto-clearing inside library functions would surprise long-lived hosts holding warmed state. | A host integration exists that needs it → wire `clear()`/`prune_missing()` into that host's session boundary, not into shared library code. |
| D4 | Freshness *weighting* (partial trust in stale graphs) | **Skip** — the gate is binary (trust/skip), the conservative posture: a stale symbol set misleads silently, while a skip only loses Tier 3 enrichment. | Real runs show Tier 3 skipping so often it starves metrics → consider per-file freshness (trust fresh entries, drop drifted ones) instead of whole-cache skip. |

**Effort**: 1-2 days · **Dependencies**: Phase 1 · **Risk**: low-medium

### 3.8 Phase 8 — Commit Prompt and Reporting (augmentation, not gating)

**Goal**: At plan completion / commit time, report graph coverage: what the graph knows about touched files, related-but-unread files, and coverage % of affected files with symbol-level detail. Guides better investigation; does not gate Phases 4–6.

**Trigger (Option C):** coverage = ready_files / task_relevant_files, where task_relevant = scope candidates ∪ likely_impacted files and a file is "ready" when the cache holds its imports + symbols.

| Coverage | Prompt? |
|---|---|
| 0-25% | No — wait for more accumulation |
| 25-40% | Consider — only for large tasks |
| 40%+ | Yes — build validates and gap-fills most task files |

**Prompt content:** files touched, import edges, symbols observed, call edges, coverage %. Bounded and cheap — a few curated observations, never a full graph dump. Accept → Phase 3 build + selective clear (untouched-file data preserved). Decline/silence → cache persists. Silence for 7 days after a recent commit reduces noise.

**Status**: ✅ Implemented — `scripts/commit_prompt.py::assess(root, task_files)` (read-only; CLI always exits 0, never gates) + `tests/test_commit_prompt.py` (8 tests). Coverage = ready/task per Option C, with the 0–25 / 25–40 / 40+ decision table (mid band prompts only for tasks ≥10 files). Related-unread comes from import overlap in both directions (task→dependency and dependent→task), capped at 10 with best-effort `dotted.module` → path mapping. Suppression reads the mapper cache commit timestamp (passive `last_updated` doesn't count as a commit). stdout is ASCII-only (Windows consoles).

**Picked up from Phase 3 (D2 — done):** the suggested build carries depth from live data — `shallow` for sprawling scopes (≥20 files), `medium` otherwise — with gap scope (task files outside mapper scope) and an exact runnable command. D2 is closed.

**Effort**: 1 day · **Dependencies**: Phase 1 (Phase 2 warms coverage) · **Risk**: low (non-blocking)

### 3.9 Phase 9 — Multi-Language and Richer Graph Techniques (extension, not foundation)

**Goal**: More languages, richer techniques (dynamic analysis, runtime tracing, dependency scanners), richer edge types. Explicitly extension work — the techniques catalog in §3 describes many options, but implementation starts narrow and grows.

**Capability matrix (declared in code as `code_relationships.LANGUAGE_SUPPORT`):**

| Language | Level | Parser | Techniques |
|---|---|---|---|
| Python | 2 | AST | definitions, imports, loaders, registrations |
| Terraform | 2 | structured-regex | definitions, imports, references |
| JavaScript / TypeScript | 1 | regex | definitions (incl. arrow consts, export-prefixed), imports, registrations, behavior |
| Java / C# / Go | 1 | regex | definitions, imports, registrations |

Level 2 = full local structure; level 1 = regex subset (documented heuristic). Unlisted suffixes (Vue, Svelte, SQL, configs) degrade to level 1 or reference-only — never crash, never block.

**Status**: ✅ Implemented as the extension pattern — step 1 (Python AST + import graph) predates this plan; step 2 landed here as JS/TS parity (arrow-function consts + `export`-prefixed declarations, deduped) plus the registry itself, with the mapper's `language_profiles()` deriving levels from it instead of a hardcoded Python carve-out (one behavior change: Terraform correctly reports level 2). Checked by `tests/test_code_relationships.py` (10 tests: registry levels, Python baseline, JS/TS syntax, no-crash on garbage, mapper derivation).

**Extension policy (how language N+1 lands):** add a `LANGUAGE_SUPPORT` entry → add the extractor branch → add tests → mapper levels follow automatically. Richer techniques (dynamic analysis, type resolution) stay separate opt-in passes outside this table — none adopted; static analysis remains the posture.

**Effort**: per language/technique · **Dependencies**: Phases 1–3 pattern proven on one language first · **Risk**: medium (scope creep — keep opt-in)

### 3.10 Phase Summary and Order Rationale

| Order | Phase | Reason it goes here | Status |
|---|---|---|---|
| **1** | Core cache infrastructure (§3.1) | Everything reads/writes this; get the contract right | ✅ Implemented — `scripts/code_graph_cache.py` + `tests/test_code_graph_cache.py` |
| **2** | Passive capture (§3.2) | Populates cache from real work; needed before metrics have anything to read | ✅ Implemented — `scripts/capture_hooks.py` + `tests/test_capture_hooks.py` |
| **3** | Explicit graph build (§3.3) | Richer source, separate from passive; can parallel Phase 4 once cache exists | ✅ Implemented — `scripts/graph_builder.py` + CLI + `tests/test_graph_builder.py` |
| **4** | Metrics extraction (§3.4) | Reads cache/scope evidence; needs Phases 1–2 minimum, Phase 3 optional but helpful | ✅ Implemented — `scripts/metrics_extractor.py` |
| **5** | Thresholds + calibration (§3.5) | Needs metrics to exist; R1 log starts once wiring exists | ✅ Implemented — validated overrides + review CLI + R1 log (tuning loop itself is ongoing by nature) |
| **6** | Wiring into mode selection (§3.6) | Needs metrics + thresholds; the integration point | ✅ Implemented (dual-gate + R2 re-evaluation) |
| **7** | Cache lifecycle / staleness (§3.7) | Refinement; simple invalidation suffices initially | ✅ Implemented — Tier 3 freshness gate + lifecycle CLI + shape guard |
| **8** | Commit prompt / reporting (§3.8) | Augmentation; gates nothing | ✅ Implemented — `scripts/commit_prompt.py` + `tests/test_commit_prompt.py` (closes D2) |
| **9** | Multi-language / richer techniques (§3.9) | Extension after foundation works | ✅ Implemented — registry + JS/TS parity + extension policy (richer techniques stay opt-in, none adopted) |

**Implemented portions**: Phases 1–9 (tooling complete), plus the R1 calibration decision log. Remaining: Phase 5 threshold *tuning* continues as real runs accumulate; new languages follow the §3.9 extension policy.

**Recommended order**: 1 → 2 → 3 → 4 (already delivered ahead via Tier 1+2, which need no populated cache); R2's Phase 6 work was implemented ahead of Phases 1–3 because it reuses Tier 1+2 metrics that exist today.

**Two implementation principles:**

1. **Passive and explicit are different modes, not one thing.** Passive capture is cheap, incremental, non-blocking; explicit build is deliberate, can be expensive, richer. Different constraints, different triggers.
2. **Metrics is a standalone layer, not embedded in the agent loop.** `metrics_extractor.py` is importable, testable, stateless — scope document/file list in, metrics dict out. Reusable across dual-gate and re-evaluation, independent of agent implementation.

### 3.11 Key Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Passive capture inconsistently triggered | Simple low-overhead hooks at worker/agent entry points |
| AST parse failures | Graceful degradation, skip problematic files, log gaps |
| Cache growth | Commit prompt + selective clear + staleness detection |
| Stale graph misleads metrics | Weight by freshness; files modified after `updated_at` flagged unmapped |
| Threshold calibration | Conservative defaults, `source` logging, tune from override rates |

### 3.12 Success Metrics

- scope_signal vs keyword_signal fire rate; scope_floor_lite volume; user override rate
- Start latency impact (<5%); graph build success rate; passive capture coverage per cycle



