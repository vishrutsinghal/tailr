# Code Graphing in TailTrail — Architecture and Implementation

## 1. Overview

This document describes the code graphing subsystem in TailTrail, including:

- What a "code graph" is and the different techniques used to build one
- TailTrail's existing `code-graph-mapper.py` implementation
- The code-graph cache (`.tailtrail/code-graph-cache.json`)
- Graph freshness, staleness, and passive capture during work
- How graph metrics feed into quantitative AIDLC mode selection
- Metrics confidence model
- Phased implementation plan

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

- **`scripts/code-graph-mapper.py`** — the main mapper that converts file bytes into structured graph nodes and edges
- **`tailtrail/scripts/code-graph-mapper.py`** — alternate copy (may be identical or slightly different)
- **`docs/arch/tailtrail-layer-coding-convention.md`** — the layer convention that defines what "layers" mean in this repo's graph model

The graph is consumed by:

- **`scripts/navigator_scope.py`** — Navigator's scope discovery, which uses graph edges to connect candidates
- **`scripts/navigator_core.py`** — core navigation utilities that may reference graph data
- **`scripts/task-start.py`** — Start plan assembly, which reads graph-derived signals for AIDLC mode selection

### 2.2 What the Code-Graph Mapper Produces

The mapper's primary output is a **`code-graph-cache.json`** file (or equivalent) that contains:

| Field | Description | Example |
|---|---|---|
| `node_id` | Unique identifier for each graph node | `"file:auth.py"` or `"func:validate_claim"` or `"class:Claim"` |
| `node_type` | What kind of node: file, module, function, class, symbol | `"function"` |
| `file_path` | Source file the node came from | `"src/claims_api/validate.py"` |
| `symbol_name` | Name of the symbol if the node is a function/class | `"validate_claim"` |
| `signature` | Function signature if available | `"validate_claim(claim: Claim) -> ValidationResult"` |
| `layer` | Which architectural layer this belongs to (from `tailtrail-layer-coding-convention.md`) | `"api"`, `"service"`, `"domain"` |
| `import_edges` | List of `{"from": node_id, "to": node_id, "import_path": "...", "kind": "direct|indirect"}` | See samples above |
| `call_edges` | List of function-to-function call relationships | `{"from": "submit_claim", "to": "validate_claim", "direct": true}` |
| `type_edges` | Relationships between types/classes (inherits, implements, uses) | `{"from": "Order", "to": "OrderItem", "kind": "has-many"}` |
| `metadata` | Build info: timestamp, file count, hash, version | `{"built_at": "2026-09-15T...", "files_scanned": 47, "version": "1.0"}` |

### 2.3 How the Mapper Reads Files

The mapper follows this general pattern:

1. **Enumerate target files** — walk the repository, find files matching supported extensions (.py, .js, .ts, etc.)
2. **Read each file's bytes** — read the file content
3. **Parse into AST** — use a language-appropriate parser (for Python: `ast` module or similar)
4. **Walk the AST** — extract nodes (functions, classes, imports, calls) and edges (who calls whom, who imports whom)
5. **Classify nodes into layers** — based on file path conventions from `tailtrail-layer-coding-convention.md`
6. **Emit graph nodes and edges** — write the structured output
7. **Cache the result** — write to `code-graph-cache.json` so subsequent runs can reuse it

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


