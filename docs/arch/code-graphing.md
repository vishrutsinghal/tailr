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
- Phased implementation plan (Phases 3 and 6 implemented; Phase 5 split by R0)

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

This section defines the phased implementation of the graphing subsystem. Each phase is independently testable; dependencies are explicit.

### 3.1 Phase 1: Passive Capture Infrastructure

**Goal**: Capture file reads, edits, import edges, symbols, call sites, and traceback fragments as byproducts of worker/agent activity — never as separate analysis work.

**Deliverables**:
- `scripts/capture_cache.py` — `PassiveCaptureCache` managing `.tailtrail/capture-cache.json` (local, not git-shared)
- `scripts/capture_hooks.py` — thin `on_file_read/on_file_edit/on_import_encountered/on_symbol_observed/on_call_site_encountered/on_traceback_observed` functions wired into worker/agent read and write paths
- All hooks are best-effort: failures are swallowed and never break the task

**Cache shape**: `updated_at`, `files_touched[]` (path, first_seen, last_seen, times_seen, edit_count), `import_edges_captured[]`, `symbols_observed[]`, `call_edges_captured[]`, `traceback_chains_captured[]`

**Principle**: capture only what is already observed for task reasons. No new reads, no extra token cost.

**Effort**: 1-2 days · **Dependencies**: none · **Risk**: low

### 3.2 Phase 2: Explicit Graph Build Pipeline

**Goal**: When the user accepts the commit prompt, build the explicit AST graph: validate, gap-fill, assemble, write cache, clear passive capture.

**Deliverables**:
- `scripts/graph_builder.py` — `build_graph(root, target_files, depth)` with depth `shallow | medium | deep`
- Schema validation of node/edge fields (Section 3.2 table of this document)
- Gap-fill from `likely_impacted_files` / scope candidates not present in the passive cache
- Selective clear: residual cache data for untouched files is preserved

**Flow**: parse each target file's AST → extract symbols/imports/call edges → cross-check passive cache (warmed files validate fast, only gaps are filled) → classify layers from path conventions → assemble nodes + edges with `metadata.built_at` → write `.tailtrail/code-graph-cache.json` (git-shareable) → clear the passive capture cache.

**Depth**: shallow = imports only; medium = symbols + call edges (recommended for AIDLC metrics); deep = semantic, optional.

**Effort**: 2-3 days · **Dependencies**: Phase 1 · **Risk**: medium (AST failures need graceful degradation)

### 3.3 Phase 3: Metrics Extraction from Graph

**Status**: ✅ Implemented.

**Goal**: Extract quantitative complexity metrics and feed them into AIDLC mode selection as Dimension 2.

**Deliverables**:
- `scripts/metrics_extractor.py`
- `extract_scope_complexity_metrics(document, root)` — dispatches on `plan["scope_evidence"]` vs `plan.get("likely_impacted_files", [])`
- `compute_complexity(likely_impacted_files, scope_evidence, root)` — the tier plumbing: Tier 1 always from `likely_impacted_files`; Tier 2 from `scope_evidence` if present; Tier 3 from `code-graph-cache.json` if present and covering included paths
- `load_thresholds(root)` — loads project overrides from `.tailtrail/aidlc-scope-thresholds.json` or falls back to `DEFAULT_THRESHOLDS`
- `assess_scope_quality(document, goal, tags, root, ..., compute_complexity=False)` — Phase 4 integration point; when `compute_complexity=True` returns `complexity_metrics` from the same code path

**Signals actually extracted**:

| Layer | Signal | Source | Used in dual-gate |
|---|---|---|---|
| Always | `affected_files` | `likely_impacted_files` | Yes — `affected_files_standard` / `affected_files_lite_floor` |
| Always | `changed_lines_estimate` | `likely_impacted_files` | Yes — `changed_lines_lite_floor` |
| Always | `layer_breakdown` | `likely_impacted_files` paths | Informational |
| Tier 2 | `affected_paths` (implementation-owner only) | `scope_evidence.candidates` roles | Informational |
| Tier 2 | `cross_layer_edges` | `scope_evidence.edges` + candidate layers | Yes — `cross_layer_edges_standard` |
| Tier 2 | `call_chain_depths`, `call_chain_depth_stddev` | `scope_evidence.behavior_chains` | Yes — `call_chain_depth_stddev_standard` |
| Tier 2 | `behavior_chain_incomplete` | `scope_evidence.behavior_chains.state` | Informational |
| Tier 2 | `module_resolution_ambiguous` | `scope_evidence.module_resolution` | Yes — `module_resolution_ambiguous_standard` |
| Tier 2 | `investigation_files_read` | `scope_evidence.investigation` | Informational |
| Tier 3 | `symbols_in_scope`, `endpoints_in_scope` | `code-graph-cache.json` | Informational |
| Tier 3 | `external_dependency_edges` | `code-graph-cache.json` | Yes — `new_external_deps_standard` |

Every metric dict carries a `source` field (`"likely_impacted_files_only"`, `"scope_evidence"`, or `"scope_evidence+mapper"`) plus a `thresholds` snapshot so the decision is auditable.

**Default thresholds** (project-tunable via `.tailtrail/aidlc-scope-thresholds.json`; loaded by `load_thresholds(root)`):

```python
DEFAULT_THRESHOLDS = {
    # Standard-escalation thresholds (any one fires scope_signal)
    "affected_files_standard": 20,
    "cross_layer_edges_standard": 2,
    "call_chain_depth_stddev_standard": 3.0,
    "module_resolution_ambiguous_standard": 3,
    "new_external_deps_standard": 1,
    # Lite floor (keeps Lite even if keyword_signal fires)
    "affected_files_lite_floor": 5,
    "changed_lines_lite_floor": 50,
}
```

**Fallback chain** (also in `compute_complexity`):
- `scope_evidence` missing or not a dict → Tier 1 only; `source = "likely_impacted_files_only"`
- `scope_evidence` present, no graph cache → Tier 1 + Tier 2; `source = "scope_evidence"`
- `scope_evidence` + graph cache with mapper coverage → Tier 1 + Tier 2 + Tier 3; `source = "scope_evidence+mapper"`

Mode selection never blocks on graph availability.

**Effort**: 1-2 days · **Dependencies**: Phase 2 (Tier 3 only; Tier 1+2 work without it) · **Risk**: low

### 3.4 Phase 4: Commit Prompt with Task-Relevant Coverage

**Goal**: At plan completion, prompt the user to commit an AST graph when passive-cache coverage of task-relevant files is high enough (Option C trigger).

**Trigger**: coverage = ready_files / task_relevant_files, where task_relevant = scope candidates ∪ likely_impacted files and a file is "ready" when the cache holds its imports + symbols.

| Coverage | Prompt? |
|---|---|
| 0-25% | No — wait for more accumulation |
| 25-40% | Consider — only for large tasks |
| 40%+ | Yes — build validates and gap-fills most task files |

**Prompt content**: files touched, import edges, symbols observed, call edges, coverage %. Accept → Phase 2 build + cache clear. Decline/silence → cache persists. Silence for 7 days after a recent commit reduces noise.

**Effort**: 1 day · **Dependencies**: Phase 1 · **Risk**: low (non-blocking)

### 3.5 Phase 5: Host-Agent Qualitative Fallback

**Status**: Split (R0 decision); not implemented.

**R0 decision (see `navigator_aidlc_improvements.md`)**:

- **5A — Host-Agent Intent Roundtrip**: ⏸ **Deferred**. The agreed user-facing outcome (bare "use AIDLC" → Standard, explicit full/standard/off captured directly) is already live via `task-start.py`'s `_aidlc_intent()` + dual-gate without a host roundtrip. A host roundtrip would add a model call per Start and reintroduce host-LLM non-determinism at a control point. Revisit trigger: R1 calibration log shows regex-missed explicit intents in real runs.
- **5B — Qualitative Complexity Fallback**: ❌ **Rejected unless evidence reopens it**. `cheap_scope_metrics()` always extracts file counts and line estimates from `likely_impacted_files`, so true zero-metrics requires both empty discovery input **and** an unparseable language. The honest fix for zero-metrics runs is better discovery, not host guessing. Single reopen criterion: R1 logs show real `zero_metrics` runs that cannot be resolved by improving discovery input.

**Legacy note**: The original layout (1-day effort, host-agent bounded question returning `complexity_tier: low | medium | high`) was replaced by the R0 split. This section is retained as history only.
### 3.6 Phase 6: Post-Discovery Re-Evaluation Hook

**Status**: ✅ Implemented (R2).

**Goal**: After scope discovery, re-check whether a Lite-selected mode should escalate when scope data is richer than Start-time signals.

**Implementation** (see `navigator_aidlc_improvements.md` Phase 6 design + R2 run):

- `compute_re_evaluation(lite_mode, hands_free, scope_evidence, likely_impacted_files, root)` in `scripts/metrics_extractor.py` — the single re-evaluation trigger, reusing the **exact same** `compute_complexity()` → `scope_signal` / `scope_floor_lite` pipeline from the dual-gate. No separate trigger set to maintain.
- `planning_lock.create(..., re_evaluation_suggestion=None)` — consumes the suggestion; lock draft records `re_evaluation_suggested` + the complexity snapshot at the time of discovery.
- `task-start.py` post-discovery path wires the call just before lock creation, so escalation is visible in the lock draft before approval.

**Properties** (per R0 design):

- **Escalation-only**: Lite → Standard when `scope_signal=True` and not `scope_floor_lite` and not already escalated. Never modifies `off` or `full`.
- **Pre-lock only**: mode is frozen after lock approval. The guard lives in the finalization path itself — the draft records the suggestion and requires explicit user approval; it does not silently advance.
- **Approval-bound**: lock draft carries `re_evaluation_suggested=True` for any proposed Lite→Standard escalation, plus the complexity snapshot (`source`, `scope_signal`, `scope_floor_lite`, metrics) so the approval decision is evidence-grounded.
- **Reuses dual-gate thresholds** — the same calibrated `scope_signal` / `scope_floor_lite` that governs the initial decision also governs the re-check, so there is only one threshold set to maintain.

**History note**: the earlier draft (Lite + scope reveals ≥10 candidates or ≥2 cross-layer edges → propose Standard) was replaced by the R2 reuse-of-dual-gate design. This section summarizes the implemented behavior.

**Effort**: ~2 days (R2) · **Dependencies**: Phase 3 (`compute_complexity`); Phase 1/2 not strictly required because Tier 1+2 metrics already produce a `scope_signal` · **Risk**: low-medium (approval-boundary care required; escalation-only constraint keeps it contained)

### 3.7 Phase Summary

| Phase | Goal | Effort | Dependencies | Status |
|---|---|---|---|---|
| 1 | Passive capture infrastructure | 1-2 days | none | Not implemented |
| 2 | Explicit graph build pipeline | 2-3 days | 1 | Not implemented |
| 3 | Metrics extraction from graph | 1-2 days | 2 | ✅ Implemented — `scripts/metrics_extractor.py` |
| 4 | Commit prompt (task-relevant coverage) | 1 day | 1 | Not implemented |
| 5 | Host-agent qualitative fallback | 1 day | none | Split (R0): 5A deferred, 5B rejected |
| 6 | Post-discovery re-evaluation | 2-3 days | 1+2+3 | ✅ Implemented (R2) — `compute_re_evaluation()` + `planning_lock.create(re_evaluation_suggestion)` |

**Implemented portions**: Phases 3 + 6, plus the R1 calibration decision log (see Section 3.8.1). Remaining roadmap: Phases 1, 2, 4, and the deferred/rejected portions of Phase 5.

**Recommended order**: 1 → 2 → 3 → 4 (already partially delivered by Phase 3 + R1); R2's Phase 6 was implemented ahead of Phases 1/2 because it reuses Tier 1+2 metrics that exist today.

### 3.8 Key Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Passive capture inconsistently triggered | Simple low-overhead hooks at worker/agent entry points |
| AST parse failures | Graceful degradation, skip problematic files, log gaps |
| Cache growth | Commit prompt + selective clear + staleness detection |
| Stale graph misleads metrics | Weight by freshness; files modified after `updated_at` flagged unmapped |
| Threshold calibration | Conservative defaults, `source` logging, tune from override rates |

### 3.9 Success Metrics

- scope_signal vs keyword_signal fire rate; scope_floor_lite volume; user override rate
- Start latency impact (<5%); graph build success rate; passive capture coverage per cycle



