## 2. Identified Improvement Areas

### 2.1 Gap #1 — No Quantitative Code Complexity Metric

#### 2.1.1 Current Behavior

Navigator's `navigator_standard_evidence()` selects Standard mode based **only** on keyword presence:

```python
# scripts/task-start.py ~line 945
selected = (
    len(signals) >= 2          # >=2 programme-scale keyword matches
    or len(critical_risks) >= 2  # >=2 critical risk matches
    or (len(decisions) >= 2 and bool(signals or critical_risks))
)
```

The function `navigator_standard_evidence()` (line 923) checks the goal text and risk indicators for these 12 `NAVIGATOR_STANDARD_SIGNALS`:

```python
("regulated", "compliance", "multi-team", "production", "release",
 "rollout", "migration", "infrastructure", "terraform", "security",
 "operations", "programme", "program")
```

Critical risks subset:
```python
{"regulated", "compliance", "production", "security", "migration"}
```

No actual code is inspected — no file count, call graph depth, cyclomatic complexity, test coverage, or integration boundary analysis.

#### 2.1.2 Problem

A task that touches 50 files with deep call chains, touches 3 service layers, has no test coverage in the changed area, and involves database schema changes — but does not mention any of the 12 programme-scale keywords — will stay on **Lite** mode.

**Example**: `"Refactor the order processing pipeline to use async handlers"`:
- No programme-scale keywords → `signals = []`
- No explicit risk keywords → `critical_risks = []`
- Result: `selected = False` → Lite mode
- Reality: touches order_service.py, payment_service.py, notification_service.py, 3 new handler classes, async queue integration, 6 test files. This is arguably a Standard-level task.

The system's "complexity" is measured as **text keyword count**, not **structural code impact**.

#### 2.1.3 Suggested Direction

Add a **quantitative complexity signal** to `navigator_standard_evidence()` or a new function that feeds into `aidlc_mode_selection()`:

```python
def code_complexity_signal(root, changed_files, graph_stats):
    score = 0
    if len(changed_files) >= 5:
        score += 1
    elif len(changed_files) >= 3:
        score += 0.5
    if graph_stats and graph_stats.get("max_depth", 0) >= 4:
        score += 1
    coverage_gap = graph_stats.get("coverage_gap", 0) if graph_stats else 0
    if coverage_gap and coverage_gap > 0.3:
        score += 1
    boundaries = graph_stats.get("boundaries_touched", []) if graph_stats else []
    if len(boundaries) >= 2:
        score += 1
    return score
```

Then in `aidlc_mode_selection()`:
```python
complexity_score = code_complexity_signal(root, changed_files, graph_stats)
if complexity_score >= 2:
    routing["selected"] = True
    routing["evidence"].append({
        "type": "code-complexity",
        "score": complexity_score,
        "source": "changed-file-analysis"
    })
```

This would make a 50-file refactor with no programme keywords correctly route to Standard mode based on objective evidence.

#### 2.1.4 Trade-offs

| Consideration | Impact |
|---|---|
| Graph must be available before mode selection | May require early graph build or reuse; adds latency if graph is not cached |
| Complexity threshold needs calibration | Too sensitive → Standard on every medium task; too lenient → same as today |
| Graph stats may be incomplete for first-time runs | Fallback to keyword-only signals if graph unavailable |
# Navigator AIDLC Mode Selection — Improvement Analysis

## 1. Overview

This document captures improvement opportunities in how Navigator selects an AI-DLC (AIDLC) mode (Lite / Standard / Full / Off) during TailTrail Start. The current selection is deterministic and keyword-driven, with no quantitative complexity assessment, no dynamic re-evaluation after scope discovery, and some structural redundancy. This document is intended for review and possible future evolution of the `scripts/task-start.py → aidlc_mode_selection()` routing path.

### 1.1 Scope

This document covers the decision tree inside `scripts/task-start.py` lines ~896–1204:
- `_aidlc_intent()` — natural-language intent detection
- `navigator_standard_evidence()` — programme-scale signal detection
- `aidlc_mode_selection()` — final mode routing

It does **not** cover downstream Official AIDLC lifecycle stages (that is the authority of the official pack boundary) or the Planning Lock approval flow (covered elsewhere).

### 1.2 Baseline Behavior (Current State)

The current mode selection proceeds in five stages:

```
┌─────────────────────────────────────────────────────────────────┐
│                  CURRENT AIDLC MODE SELECTION                     │
├─────────────────────────────────────────────────────────────────┤
│ 1. Explicit --aidlc flag  → wins immediately (explicit-flag)     │
│                                                                   │
│ 2. Natural-language intent → opt-out → Off                       │
│                               full  → Full                         │
│                               standard → Standard                  │
│                               requested → go to stage 3            │
│                               none → go to stage 3                 │
│                                                                   │
│ 3. Auto-routing (intent=none or requested):                      │
│    hands_free = goal has "hands-free"/"end-to-end"               │
│    routing = navigator_standard_evidence(goal, plan)             │
│                                                                   │
│    IF intent=="none" AND NOT hands_free AND NOT routing.selected:│
│        → LITE (selection: default)                                │
│        → full_escalation: not-eligible                            │
│    ELIF hands_free AND routing.selected:                         │
│        → FULL (or eligible-awaiting-compatible-pack)              │
│    ELIF intent in {"requested","standard"} OR routing.selected     │
│         OR hands_free:                                            │
│        → STANDARD                                                 │
│    ELSE:                                                          │
│        → LITE (fallback)                                         │
└─────────────────────────────────────────────────────────────────┘
```

### 1.3 AIDLC Mode Definitions (Reference)

| Mode | When Selected | What It Enables | What It Excludes |
|---|---|---|---|
| **Off** | User opts out (`"without AIDLC"`, `"AIDLC off"`) | AIDLC lifecycle disabled; Navigator requirement boundary governs | Local AIDLC Requirements stage, official pack verification |
| **Lite** (default) | No signals, no hands-free, no explicit intent | Navigator planning + Planning Lock + task-selected controls + Local AIDLC Lifecycle Lite | Mandatory AIDLC workshop, official pack identity |
| **Standard** | ≥2 programme signals, OR hands-free + signals, OR explicit standard/fuller intent | Everything in Lite + verified official AI-DLC Requirements Analysis rules + host-generated official questions with options/recommendations/reasoning | Full lifecycle stages after requirements |
| **Full** | Hands-free + ≥2 signals + official pack available | Everything in Standard + Phase A compatibility verification + full official lifecycle rules + receipt-driven attachment with ordered resume/redo/jump/recovery history | TailTrail-generated substitute questions, silent fallback |
### 2.2 Gap #2 — Brittle Natural-Language Intent Detection

#### 2.2.1 Current Behavior

`_aidlc_intent()` (line 896) uses exact regex patterns to detect AIDLC mode intent:

```python
def _aidlc_intent(lowered):
    if "aidlc" not in normalized:
        return "none"
    if re.search(r"(without|skip|disable|no)\s+aidlc|aidlc\s+(off|disabled)"):
        return "opt-out"
    if re.search(r"(full|official|enterprise)\s+aidlc|aidlc\s+(full|official|enterprise)"):
        return "full"
    if re.search(r"(standard|medium|normal|regular)\s+aidlc|aidlc\s+(standard|medium|normal|regular)"):
        return "standard"
    return "requested"
```

#### 2.2.2 Problem

The detection is case-insensitive but **word-order-sensitive** and does not normalize mode synonyms before matching.

| User Input | Intent Returned | Expected | Issue |
|---|---|---|---|
| `"use AIDLC medium"` | `"requested"` | `"standard"` | Medium should normalize to standard before matching |
| `"use AIDLC lifecycle"` | `"requested"` | ambiguous | Falls through to risk routing; unclear what mode |
| `"full lifecycle AIDLC"` | `"requested"` | `"full"` | Word order reversed — regex `aidlc\s+(full...)` doesn't match |
| `"AIDLC standard mode"` | `"standard"` | `"standard"` | Works because sentence starts with qualifier |
| `"AIDLC required"` | `"requested"` | ambiguous | No mode qualifier detected |
| `"skip the AIDLC lifecycle"` | `"requested"` | `"opt-out"` | Has "skip" but "lifecycle" breaks the regex |

The core issue: the regex patterns are **brittle** to word order, adjective-noun inversion, and mode synonym normalization.

#### 2.2.3 Suggested Direction

Two improvements:

**A) Normalize mode synonyms before regex matching**

```python
MODE_SYNONYMS = {
    "simple": "lite", "basic": "lite", "minimal": "lite", "lightweight": "lite",
    "medium": "standard", "normal": "standard", "regular": "standard",
    "full": "full", "complete": "full", "comprehensive": "full",
    "enterprise": "full", "official": "full",
    "standard": "standard", "lite": "lite",
    "off": "off", "disabled": "off", "none": "off",
}

def _normalize_aidlc_intent(lowered):
    normalized = lowered
    for synonym, canonical in MODE_SYNONYMS.items():
        normalized = re.sub(
            rf"\b{synonym}\b(?=.*\b(?:mode|a?idlc|lifecycle|workflow)\b)",
            canonical, normalized, flags=re.IGNORECASE
        )
    return normalized
```

**B) Two-pass intent detection: anchor + qualifier**

Detect an **anchor** ("AIDLC") and a **qualifier** (the mode word anywhere near it):

```python
def _aidlc_intent_v2(lowered):
    anchor_match = re.search(r"\baidlc\b", lowered)
    if not anchor_match:
        return "none"
    anchor_pos = anchor_match.start()
    words = lowered.split()
    anchor_word_idx = lowered[:anchor_pos].split().index("aidlc") if "aidlc" in lowered.split() else 0
    for i, word in enumerate(words):
        w = word.lower().strip(",.:;!?")
        canonical = MODE_SYNONYMS.get(w)
        if canonical:
            if abs(i - anchor_word_idx) <= 3:
                if canonical == "off":
                    if re.search(r"(without|skip|disable|turn\s*off|switch\s*off)", lowered, re.IGNORECASE):
                        return "opt-out"
                    return "off"
                return canonical
    return "requested"
```

This handles:
- `"AIDLC medium"` → anchor="AIDLC", qualifier="medium" → canonical="standard" → `"standard"`
- `"full lifecycle AIDLC"` → anchor at end, qualifier="full" within 3 words → `"full"`
- `"skip the AIDLC lifecycle"` → anchor present, qualifier absent, but "skip" nearby → `"opt-out"`
- `"use AIDLC lifecycle"` → anchor present, qualifier absent → `"requested"` (correctly ambiguous)

#### 2.2.4 Trade-offs

| Consideration | Impact |
|---|---|
| Synonym table must be maintained | New synonyms added over time as users phrase things differently |
| Distance threshold (+/-3 words) is a heuristic | May miss `"AIDLC"` separated by 4+ words from the mode word in long sentences |
| Ambiguous cases ("AIDLC lifecycle") remain `"requested"` | This is intentional — ambiguous cases correctly fall through to risk routing rather than guessing |
### 2.3 Gap #3 — No Post-Planning Re-Evaluation of AIDLC Mode

#### 2.3.1 Current Behavior

The AIDLC mode is computed **once** at Start time and written into the Planning Lock (`lock-v1.json`). The saved start report shows:

```json
{ "mode": "lite", "selection": "default", "state": "local-lite",
  "full_escalation": { "state": "not-eligible" } }
```

After scope discovery, if the actual scope is larger than the initial goal implied, the mode is **not revisited**. The system trusts the planning evidence (file reads, read-only inspection of models.py/service.py) but does not re-run the mode selection with updated evidence.

#### 2.3.2 Problem

Scenario: A user says `"Fix validation bug in claims API"`. Start selects Lite. During scope discovery, Navigator finds:
- 3 files changed (validation.py, models.py, service.py)
- A new integration point (external claims adjudicator API)
- Existing test gaps in the claims flow

The scope evidence now supports Standard mode, but the mode is locked to Lite. There is no path to say: "Discovery revealed this is more complex than the initial goal suggested — should we upgrade to Standard?"

#### 2.3.3 Evidence from Saved Reports

Examining saved start reports (e.g., `start-20260808123420-180837`):
- Mode is computed once and recorded in `lock-v1.json`
- No field like `mode_re_evaluated` or `discovery_triggered_mode_change` exists
- Even when `scope_evidence` later shows more files than the initial goal implied, the AIDLC mode is unchanged

#### 2.3.4 Suggested Direction

Add a **discovery-triggered re-evaluation trigger point** between scope discovery and Planning Lock finalization:

```python
def re_eval_aidlc_mode(initial_mode, discovery_evidence, hands_free):
    if initial_mode == "off":
        return "off"
    if initial_mode == "full":
        return "full"
    current_signals = discovery_evidence.get("signals", [])
    current_risks = discovery_evidence.get("critical_risks", [])
    changed_count = len(discovery_evidence.get("changed_files", []))
    graph_depth = discovery_evidence.get("graph_depth", 0)
    selected = (
        len(current_signals) >= 2 or len(current_risks) >= 2
        or changed_count >= 5 or graph_depth >= 4
    )
    if selected and initial_mode == "lite":
        return "standard"
    return initial_mode
```

And a user-facing prompt when escalation is detected:

```
!! AIDLC Escalation Detected
Scope discovery found:
  - 5 changed files (threshold: >=5)
  - Graph depth 4 (threshold: >=4)
  - 2 critical risk signals
Start selected: Lite
Suggested: Standard
Do you want to upgrade to Standard AIDLC mode?
[Yes, upgrade] [Keep Lite] [Explain why]
```

#### 2.3.5 Trade-offs

| Consideration | Impact |
|---|---|
| Adds a user decision point mid-pipeline | Slower than current single-decision flow, but more accurate |
| Escalation from Lite to Standard is safe | Downgrade (Standard to Lite) should not happen automatically |
| Re-evaluation only applies before lock finalization | After lock approval, mode is final (new Start needed to change) |
### 2.4 Gap #4 — Duplicated `hands_free` Detection

#### 2.4.1 Current Behavior

`hands_free` detection (checking for `"hands-free"`, `"hands free"`, `"end-to-end"`, `"end to end"` in the goal text) is implemented independently in two functions:

| Function | File | Line | Purpose |
|---|---|---|---|
| `aidlc_mode_selection()` | `scripts/task-start.py` | ~1139 | Determines if Full mode escalation applies |
| `guided_delivery()` | `scripts/task-start.py` | ~1229 | Determines if Guided Delivery harness applies |

```python
# In aidlc_mode_selection() — line ~1139
hands_free = bool(
    re.search(r"\b(hands[- ]?free|end[- ]?to[- ]?end)\b", lowered)
)

# In guided_delivery() — line ~1229
hands_free = bool(
    re.search(r"\b(hands[- ]?free|end[- ]?to[- ]?end)\b", lowered)
)
```

Both use the same regex pattern but are separate code paths.

#### 2.4.2 Problem

If the regex pattern ever changes in one function (e.g., to add `"handsfree"` or `"autonomous"`), the other function may not be updated, leading to inconsistent behavior: the AIDLC mode might select Full while Guided Delivery does not activate, or vice versa.

There is also no shared helper, no unit test that verifies both functions return the same `hands_free` value for the same goal text.

#### 2.4.3 Suggested Direction

Extract the detection into a shared helper:

```python
# scripts/helpers.py or scripts/task-start.py (shared section)

HAND_FREE_PATTERNS = re.compile(
    r"\b(hands[- ]?free|handsfree|end[- ]?to[- ]?end|autonomous|fully\s*automated)\b",
    re.IGNORECASE
)

def is_hands_free(goal_text: str) -> bool:
    """Detect hands-free / end-to-end intent in goal text.
    Shared by aidlc_mode_selection() and guided_delivery().
    """
    lowered = goal_text.lower() if goal_text else ""
    return bool(HAND_FREE_PATTERNS.search(lowered))
```

Then both functions call `is_hands_free(goal)`:

```python
# In aidlc_mode_selection()
hands_free = is_hands_free(goal)

# In guided_delivery()
hands_free = is_hands_free(goal)
```

#### 2.4.4 Trade-offs

| Consideration | Impact |
|---|---|
| Simple refactor, low risk | Extract helper, replace two inline regex checks |
| Adding new patterns affects both consumers | Intentional — both should agree on what "hands-free" means |
| May need a test to verify consistency | Lightweight: parametrize test with goal text, assert `is_hands_free()` result |
| May need a test to verify consistency | Lightweight: parametrize test with goal text, assert `is_hands_free()` result |

### 2.5 Gap #5 — Single-Feature Threshold Is Too Conservative

#### 2.5.1 Current Behavior

The selection threshold in `navigator_standard_evidence()` requires **>=2 programme-scale signals** OR **>=2 critical risks** OR **>=2 material decisions with at least one signal** to mark `routing["selected"] = True`:

```python
selected = (
    len(signals) >= 2          # exactly 2
    or len(critical_risks) >= 2  # exactly 2
    or (len(decisions) >= 2 and bool(signals or critical_risks))
)
```

A single critical risk signal (e.g., just `"production"` or just `"regulated"`) is **not sufficient** to trigger Standard mode.

#### 2.5.2 Problem

A task that is entirely about a production database migration — but the goal text only mentions `"migration"` once — stays on Lite:

**Example goal**: `"Migrate the user session store from Redis to DynamoDB"`
- Contains `"migration"` → 1 critical risk signal
- `len(critical_risks) = 1` → does not meet threshold of 2
- `selected = False` → Lite mode
- In reality: this is a high-risk production change that arguably needs Standard's official requirements analysis

The threshold treats all signals as equal weight. A task with one critical risk signal is treated the same as a task with one benign signal (e.g., just `"infrastructure"`).

#### 2.5.3 Suggested Direction

Weight critical risks more heavily — a single critical risk should be sufficient to trigger Standard:

```python
# Current
selected = (
    len(signals) >= 2
    or len(critical_risks) >= 2
    or (len(decisions) >= 2 and bool(signals or critical_risks))
)

# Proposed
selected = (
    len(signals) >= 2                          # >=2 programme signals
    or len(critical_risks) >= 1                # >=1 critical risk
    or (len(decisions) >= 2 and len(signals) >= 1)  # >=2 decisions + >=1 signal
)
```

Or, with a signal weighting system:

```python
SIGNAL_WEIGHTS = {
    "regulated": 2, "compliance": 2, "production": 2,
    "security": 2, "migration": 2,
    "multi-team": 1, "release": 1, "rollout": 1,
    "infrastructure": 1, "terraform": 1,
    "operations": 1, "programme": 1, "program": 1,
}

def signal_weighted_score(signals, critical_risks):
    score = sum(SIGNAL_WEIGHTS.get(s, 0) for s in signals)
    score += sum(SIGNAL_WEIGHTS.get(r, 0) for r in critical_risks)
    return score

# Threshold: score >= 3 triggers Standard
selected = signal_weighted_score(signals, critical_risks) >= 3
```

With this:
- `"migration"` alone: score = 2 (one critical risk at weight 2) → 2 < 3 → still Lite
- `"production migration"`: score = 2 + 2 = 4 → >= 3 → **Standard**
- `"infrastructure release"`: score = 1 + 1 = 2 → still Lite
- `"regulated production migration"`: score = 2 + 2 + 2 = 6 → **Standard**

This preserves the intent (don't escalate on a single benign signal) while being less conservative about genuinely risky single-signal tasks.

#### 2.5.4 Trade-offs

| Consideration | Impact |
|---|---|
| Single critical risk to Standard adds more Standard-mode tasks | More official AIDLC requirements analysis runs; higher cost per task |
| Weighting system must be calibrated | Threshold of 3 may need adjustment based on observed outcomes |
| Decisions-based escalation needs review | The current `len(decisions) >= 2 AND bool(signals or critical_risks)` already captures material decisions; keep that path |
### 2.6 Gap #6 — No Integration with Code Intelligence Depth

#### 2.6.1 Current Behavior

Navigator has a `code_intelligence` configuration section with depth levels (`lite`, `v1`, `v2`, `v3`) that controls how much code analysis is performed. The `is_tiny()` check (line 690) uses `len(changed) <= 1` to short-circuit analysis for trivial tasks. But `aidlc_mode_selection()` does not consult:

- The `code_intelligence.default` setting
- The number of changed files from the plan (`len(changed)`)
- The code graph depth or breadth

#### 2.6.2 Problem

The system has the data (changed file count, graph depth, code intelligence level) but does not use it for AIDLC mode selection. A task with 1 changed file and no signals goes to Lite. A task with 20 changed files, 4 layers deep in the graph, and no signals — also goes to Lite. They receive the same mode despite very different complexity.

#### 2.6.3 Suggested Direction

Pass code intelligence evidence into the mode selection:

```python
def aidlc_mode_selection(goal, plan, code_intel, changed_files):
    # ... existing intent and signal detection ...
    code_complexity = _assess_code_complexity(
        code_intel=code_intel,
        changed_files=changed_files,
        graph=plan.get("graph_stats", {})
    )
    if code_complexity >= COMPLEXITY_THRESHOLD:
        routing["selected"] = True
        routing["evidence"].append({
            "type": "code-intelligence",
            "complexity_score": code_complexity,
            "level": code_intel.get("default", "lite")
        })
```

Where `_assess_code_complexity` uses:
- `code_intel.default` — if the user set a higher default (e.g., `v2` or `v3`), that's a signal they expect more analysis
- `len(changed_files)` — file count as a complexity proxy
- `graph_stats.max_depth` — call chain depth
- `graph_stats.boundaries_touched` — number of architectural boundaries affected

#### 2.6.4 Trade-offs

| Consideration | Impact |
|---|---|
| Requires graph or directory scan before mode selection | Adds latency; may need a lightweight pre-scan (file count only) for mode selection, with full analysis after |
| `code_intel.default` is a user setting, not a task signal | A user who sets `v3` by default may get Standard mode on simple tasks; make it a soft signal (adds 0.5 to score, not a full signal) |
| File count alone is a weak proxy | A task changing 20 config files is different from a task changing 20 source files; weight by file type |
## 3. Summary of Improvement Areas

| # | Gap | Severity | Current Behavior | Proposed Direction | Key File(s) |
|---|---|---|---|---|---|
| 1 | No quantitative complexity metric | **High** | Keyword-only; 50-file refactor with no keywords to Lite | Add code-complexity signal (file count, graph depth, coverage gap, boundaries) to `navigator_standard_evidence()` or new function | `scripts/task-start.py:923` |
| 2 | Brittle intent detection | **Medium** | Exact regex, word-order-sensitive, no synonym normalization | Add synonym normalization + two-pass anchor/qualifier detection in `_aidlc_intent()` | `scripts/task-start.py:896` |
| 3 | No post-discovery re-evaluation | **Medium** | Mode locked at Start; no revision path after scope discovery | Add re-evaluation trigger before lock finalization with user prompt for Lite-to-Standard escalation | `scripts/task-start.py` + lock finalization path |
| 4 | Duplicated `hands_free` check | **Low** | Same regex in `aidlc_mode_selection()` and `guided_delivery()` | Extract `is_hands_free()` shared helper | `scripts/task-start.py:1139`, `:1229` |
| 5 | Threshold >=2 signals too conservative | **Low** | Single critical risk not enough for Standard | Weight critical risks (weight 2) vs. programme signals (weight 1); threshold >=3 | `scripts/task-start.py:945` |
| 6 | No code intelligence integration | **Low** | `code_intel`, `len(changed)`, graph depth not used | Pass code intelligence evidence into mode selection as a soft signal | `scripts/task-start.py:1132` |

### 3.1 Prioritization Rationale

- **Gap 1 (High)**: Most impactful. Directly addresses the core limitation — the system has no objective measure of how complex a task is, only whether certain words appear in the goal text.
- **Gap 2 (Medium)**: Improves user experience for people who phrase AIDLC intent in non-standard ways. Prevents ambiguous intent from silently defaulting.
- **Gap 3 (Medium)**: Addresses a correctness gap — if scope discovery reveals the task is bigger than expected, the mode should be re-checkable.
- **Gaps 4-6 (Low)**: Structural improvements, weighting refinements, and unused data integration. Lower risk, lower impact individually, but collectively make the system more robust.

## 4. Open Questions for Review

The following are intentionally left open for review and do not represent decisions:

1. **Complexity threshold calibration**: What score/threshold gives the right balance between over-escalating (Standard on simple tasks) and under-escalating (Lite on genuinely complex tasks)?

2. **When to re-evaluate**: Should re-evaluation happen automatically and prompt the user, or should it be a flag the user can opt into (e.g., `--aidlc auto-escalate`)?

3. **Downgrade protection**: Should the system ever downgrade from Standard to Lite based on discovery? Currently there is no path; is that correct?

4. **Graph availability latency**: If Gap 1 requires graph stats before mode selection, does the system build a minimal graph first (slow start) or accept graph-unavailable as a fallback to keyword-only signals?

5. **User override**: Should users be able to override the auto-selected mode after seeing both the goal-based selection and the code-complexity evidence? (e.g., "I know this is complex but I want Lite" or "This looks simple but I want Standard for the documentation")

6. **Code intelligence as a mode signal vs. a separate harness decision**: Gap 6 could be interpreted as "code intelligence depth should affect the delivery harness, not the AIDLC mode." Is that the right separation?
## 5. Design Framework for Quantitative Code-Complexity Metrics

### 5.1 Core Principle: Deterministic Over Host-Agent Reasoning

**Short answer**: Do **not** make the agent host the primary gatherer. Use the existing deterministic static-analysis + code-graph path. Reserve host reasoning only as a last-resort fallback for languages the mapper doesn't cover.

**Why agent-host reasoning is a poor primary path here:**

| Concern | Host-agent reasoning | Deterministic static analysis |
|---|---|---|
| **Determinism** | Non-deterministic — different reasoning paths on rerun | Reproducible from AST / graph / file count |
| **Token cost** | Reads files, reasons about complexity → expensive per run | Capped budgets (`InvestigationLimits`, `max_total_read_bytes`) |
| **Testability** | Hard to assert "complexity score is X" in a test | Easy: feed a fixed `scope_evidence` doc, assert metric values |
| **TailTrail philosophy** | Violates "bounded discovery" and evidence-first norms | Aligns with `navigator_scope.py`'s capped investigation design |
| **Timing** | Would need to happen *before* mode selection — slows start | Metrics already derivable from `scope_evidence` computed at line 2408 |

The existing `navigator_scope.investigate()` (line 1621) already builds a `scope_evidence` document with candidates, edges, behavior chains, and investigation stats. The data is there; it just isn't extracted into metrics and fed to `aidlc_mode_selection()`.



### 5.2 What Already Exists That Can Be Leveraged

#### 5.2.1 Data available in `scope_evidence` document (from `investigate()`)

The Navigator scope investigation at `scripts/navigator_scope.py:1621` produces a `scope_evidence` document with:

| Field | Contains | Quantitative value derivable |
|---|---|---|
| `candidates[]` | File/module candidates with roles, statuses, edges | `len(candidates)` = affected file count; role distribution (implementation-owner, test, excluded, supporting) |
| `edges[]` | Relationship edges with `kind`, `strength`, `from_candidate_id`, `to_candidate_id` | Cross-layer edges from specific `kind` values; edge count per candidate |
| `behavior_chains` | Complete/partial execution chains | Chain depth; chain completeness ratio; gap points |
| `investigation` | Investigation metadata (`files_read`, `bytes_read`, limits, phases) | Coverage ratio; investigation effort; files found vs. attempted |
| `ownership_selection` | Qualified candidates, selected candidates, reasons | Qualification ratio; selection confidence |
| `module_resolution` | Resolution stats (`ambiguous`, `unresolved`, `resolved`) | Resolution ambiguity count — indicator of codebase complexity |
| `evidence_state` | `"resolved"` or `"partial"` | Completeness signal |

These fields exist but are not computed as standalone metrics for AIDLC routing today.

#### 5.2.2 Capabilities available in `code-graph-mapper.py`

`scripts/code-graph-mapper.py` can extract from a repository:

| Capability | Metric it can produce |
|---|---|
| File/module inventory | `affected_files` count, file list |
| Call chains (`call_chains[]`) | `call_chain_depth_mean`, `call_chain_depth_stddev`, `max_chain_depth`, chain count |
| Symbols per file (`symbols[]`) | Function/class density per file |
| Endpoints (`endpoints[]`) | API surface size |
| Type hierarchy (`type_hierarchy[]`) | Inheritance depth, type coupling |
| Import relationships | Import graph edges, cross-module dependencies |

These are available when the mapper has been run and a `code-graph-cache.json` exists (see `.tailtrail/meta/code-graph-cache.json`).

#### 5.2.3 Capabilities available as cheap fallback

When no graph cache or full scope investigation is available:

| Capability | Cost | Metric it can produce |
|---|---|---|
| `plan["likely_impacted_files"]` | O(n) — already computed at line 2405 | `affected_files` from path list |
| File path analysis | O(n) — path string inspection | Layer detection (src/ vs. tests/ vs. infra/); path depth stddev |
| File size inspection | O(n) — stat() call per file | `changed_lines_estimate` from file size or git diff |
| Git diff inspection | O(diff) — subprocess call | Actual changed-line count |

These are cheap enough to run before mode selection without noticeable latency.


## 5. Design Framework for Quantitative Code-Complexity Metrics

### 5.1 Core Principle: Deterministic Over Host-Agent Reasoning

**Short answer**: Do **not** make the agent host the primary gatherer. Use the existing deterministic static-analysis + code-graph path. Reserve host reasoning only as a last-resort fallback for languages the mapper doesn't cover.

**Why agent-host reasoning is a poor primary path here:**

| Concern | Host-agent reasoning | Deterministic static analysis |
|---|---|---|
| **Determinism** | Non-deterministic — different reasoning paths on rerun | Reproducible from AST / graph / file count |
| **Token cost** | Reads files, reasons about complexity → expensive per run | Capped budgets (`InvestigationLimits`, `max_total_read_bytes`) |
| **Testability** | Hard to assert "complexity score is X" in a test | Easy: feed a fixed `scope_evidence` doc, assert metric values |
| **TailTrail philosophy** | Violates "bounded discovery" and evidence-first norms | Aligns with `navigator_scope.py`'s capped investigation design |
| **Timing** | Would need to happen *before* mode selection — slows start | Metrics already derivable from `scope_evidence` computed at line 2408 |

The existing `navigator_scope.investigate()` (line 1621) already builds a `scope_evidence` document with candidates, edges, behavior chains, and investigation stats. The data is there; it just isn't extracted into metrics and fed to `aidlc_mode_selection()`.

---

### 5.2 What Already Exists That Can Be Leveraged

#### 5.2.1 Data available in `scope_evidence` document (from `investigate()`)

| Data in the document | Quantitative value derivable | Current use |
|---|---|---|
| `candidates[]` list | `len(candidates)` = affected candidate count | Not extracted for AIDLC |
| `candidates[].role`, `candidates[].status` | Count by role/status (implementation-owner, test, excluded, etc.) | Not extracted for AIDLC |
| `edges[]` with `kind` field | `cross_layer_edges` = edges crossing repository layers | Not extracted for AIDLC |
| `behavior_chains` with chain states | Call-chain depth / completeness | Not extracted for AIDLC |
| `investigation.files_read`, `bytes_read` | Scope investigation effort | Not extracted for AIDLC |
| `ownership_selection.qualified_candidates`, `selected_candidates` | Candidate qualification counts | Not extracted for AIDLC |
| `module_resolution` stats | Resolution ambiguity counts | Not extracted for AIDLC |

#### 5.2.2 Capabilities available in `code-graph-mapper.py`

| Capability | Relevance to complexity |
|---|---|
| AST-based `call_chains[]` extraction (line 271-299) | Call-chain depth, breadth |
| `symbols[]`, `endpoints[]`, `type_hierarchy[]` | File/entity density |
| `code_graph_cache.json` persistent cache | Reuse across runs without re-parsing |

#### 5.2.3 Capabilities available as cheap fallback

| Capability | Relevance |
|---|---|
| `navigator_core.is_tiny()` (line 690) | Pattern for cheap pre-screen using `len(changed) <= 1` |
| `plan["likely_impacted_files"]` (line 2405-2407) | List of likely paths available before mode selection |
| Git change inspection | Could give diff file count + changed-line estimate |




### 5.3 Proposed Tiered Metric Extraction

#### Tier 1 — Cheap deterministic metrics (always available)

Compute from `plan["likely_impacted_files"]` or `scope_evidence["candidates"]` — no graph parse needed:

```python
def cheap_scope_metrics(
    likely_impacted_files: list[dict[str, Any]],
    candidates: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Tier-1 metrics available even without a full graph investigation."""
    paths = [str(item.get("path", "")) for item in likely_impacted_files if item.get("path")]
    candidate_paths = [str(row.get("path", "")) for row in candidates if row.get("path")] if candidates else []
    all_paths = paths or candidate_paths

    return {
        "affected_files": len(set(all_paths)),
        "unique_paths": len(set(all_paths)),
        "has_multiple_layers": _count_layers(all_paths) >= 2,
        "path_depth_stddev": _path_depth_variance(all_paths),
        "changed_lines_estimate": _estimate_changed_lines(all_paths),
    }
```

This runs in O(n) on path count — no AST, no graph parse.

#### Tier 2 — Graph-derived metrics (when `scope_evidence` is available and complete)

Extract from `scope_evidence["edges"]`, `behavior_chains`, and `candidates`:

```python
def graph_scope_metrics(
    scope_evidence: dict[str, Any],
    root: Path,
) -> dict[str, Any]:
    """Tier-2 metrics from the full Navigator scope investigation."""
    candidates = scope_evidence.get("candidates", [])
    edges = scope_evidence.get("edges", [])
    behavior_chains = scope_evidence.get("behavior_chains", {})

    cross_layer_kinds = {"imports-module", "loads-module", "renders-for", "configures-owner"}
    cross_layer_edges = [
        edge for edge in edges
        if edge.get("kind") in cross_layer_kinds
    ]

    chain_state = str(behavior_chains.get("state", "not-exercised"))
    complete_chains = behavior_chains.get("chains", [])

    return {
        "affected_files": len({str(row.get("path", "")) for row in candidates if row.get("path")}),
        "cross_layer_edge_count": len(cross_layer_edges),
        "cross_layer_kind_counts": _count_by_kind(cross_layer_edges),
        "behavior_chain_state": chain_state,
        "complete_behavior_chains": len(complete_chains),
        "incomplete_behavior_chains": sum(
            1 for row in complete_chains if row.get("state") in {"partial", "incomplete"}
        ),
        "candidate_qualification_ratio": (
            scope_evidence.get("ownership_selection", {}).get("selected_candidates", 0)
            / max(1, scope_evidence.get("ownership_selection", {}).get("qualified_candidates", 1))
        ),
        "module_resolution_ambiguous": scope_evidence.get("module_resolution", {}).get("ambiguous", 0),
        "module_resolution_unresolved": scope_evidence.get("module_resolution", {}).get("unresolved", 0),
    }
```

#### Tier 3 — AST/mapper metrics (deepest, most expensive)

Only when the code-graph mapper has already run and cached data is available:

```python
def mapper_scope_metrics(
    graph_cache: dict[str, Any] | None,
    target_paths: list[str],
) -> dict[str, Any]:
    """Tier-3 metrics from cached code-graph-mapper output."""
    if not graph_cache:
        return {"available": False}

    call_chains = graph_cache.get("call_chains", [])
    symbols = graph_cache.get("symbols", [])
    endpoints = graph_cache.get("endpoints", [])

    target_set = set(target_paths)
    relevant_chains = [c for c in call_chains if c.get("file", "") in target_set]
    relevant_symbols = [s for s in symbols if s.get("file", "") in target_set]

    chain_depths = [len(chain.get("chain", [])) for chain in relevant_chains] if relevant_chains else []

    return {
        "available": True,
        "call_chain_count": len(relevant_chains),
        "call_chain_depth_mean": float(mean(chain_depths)) if chain_depths else 0.0,
        "call_chain_depth_stddev": float(pstdev(chain_depths)) if len(chain_depths) > 1 else 0.0,
        "symbol_count": len(relevant_symbols),
        "endpoint_count": len([e for e in endpoints if e.get("file", "") in target_set]),
        "max_chain_depth": max(chain_depths) if chain_depths else 0,
    }
```



### 5.4 Wiring Point in the Existing Pipeline

```
compose_start_report()  (task-start.py)

  │
  ├─ line 2402 ─ scope_evidence fingerprint verified
  │
  ├─ line 2405-2407 ─ likely_impacted_files = navigator_scope.project_likely_impacted(...)
  │
  ├─ line 2408-2410 ─ scope_quality = navigator_scope.assess_scope_quality(...)
  │
  ├─ ★ NEW: line ~2410.5 ─ scope_complexity = extract_scope_complexity_metrics(
  │                          root, plan.get("scope_evidence"), plan.get("likely_impacted_files"))
  │                          plan["scope_complexity"] = scope_complexity
  │
  ├─ ... requirement matrix, etc. ...
  │
  └─ line 2593 ─ mode = aidlc_mode_selection(goal, aidlc_mode, root, plan, official_manifest)
                    │
                    ├─ ★ MODIFIED: navigator_standard_evidence() now also receives
                    │   plan.get("scope_complexity") and folds its signals into routing
                    │
                    └─ ★ OR: aidlc_mode_selection() reads plan["scope_complexity"] directly
```

The cleanest insertion point is a **new function** `extract_scope_complexity_metrics()` that produces a dict, stored in `plan["scope_complexity"]`, then read by either `navigator_standard_evidence()` or `aidlc_mode_selection()`.

---

### 5.5 Modified Routing Logic (Dual-Gate)

```python
def aidlc_mode_selection_with_scope(
    goal: str,
    requested: str | None,
    root: Path,
    plan: dict[str, Any],
    manifest: str | None,
    thresholds: dict[str, Any] | None = None,
) -> dict[str, Any]:
    thresholds = thresholds or DEFAULT_AIDLC_SCOPE_THRESHOLDS

    # --- existing path unchanged through intent + flag handling ---
    lowered = goal.lower()
    hands_free = is_hands_free(goal)
    if requested:
        ...
    intent = _aidlc_intent(lowered)
    if intent in {"opt-out", "full", "standard"}:
        ...

    # --- existing keyword/risk signal ---
    routing = navigator_standard_evidence(goal, plan)
    keyword_signal = routing["selected"]

    # --- NEW: scope-complexity signal ---
    complexity = plan.get("scope_complexity", {})
    scope_signal = (
        complexity.get("affected_files", 0) >= thresholds["affected_files_standard"] or
        complexity.get("cross_layer_edge_count", 0) >= thresholds["cross_layer_edges_standard"] or
        complexity.get("call_chain_depth_stddev", 0.0) >= thresholds["call_chain_depth_stddev_standard"] or
        complexity.get("module_resolution_ambiguous", 0) >= thresholds["module_resolution_ambiguous_standard"] or
        complexity.get("new_external_deps", 0) >= thresholds["new_external_deps_standard"]
    )

    # --- NEW: scope floor (prevents over-escalation from lone keywords) ---
    scope_floor_lite = (
        complexity.get("affected_files", 9999) <= thresholds["affected_files_lite_floor"] and
        complexity.get("changed_lines_estimate", 9999) <= thresholds["changed_lines_lite_floor"]
    )

    # --- mode decision ---
    if intent == "none" and not hands_free and not keyword_signal and not scope_signal:
        mode = "lite"
    elif hands_free and (keyword_signal or scope_signal):
        mode = "full"
    elif keyword_signal and not scope_floor_lite:
        mode = "standard"
    elif scope_signal:
        mode = "standard"
    elif keyword_signal and scope_floor_lite:
        mode = "lite"
    else:
        mode = "lite"
```

---

### 5.6 Threshold Defaults (Starting Point — Tunable Per Project)

```python
DEFAULT_AIDLC_SCOPE_THRESHOLDS = {
    # Standard escalation thresholds (any one fires)
    "affected_files_standard": 20,
    "cross_layer_edges_standard": 2,
    "call_chain_depth_stddev_standard": 3.0,
    "module_resolution_ambiguous_standard": 3,
    "new_external_deps_standard": 1,
    # Lite floor (keeps Lite even if keyword fires)
    "affected_files_lite_floor": 5,
    "changed_lines_lite_floor": 50,
}
```

These are **defaults only**. A project could override via `.tailtrail/aidlc-scope-thresholds.json` or `tailtrail-policy.md`.

---

### 5.7 Fallback When No Scope Evidence Is Available

If `scope_evidence` is missing (e.g., tiny task, or investigation not run), fall back to `likely_impacted_files` only:

```python
if not isinstance(plan.get("scope_evidence"), dict):
    complexity = cheap_scope_metrics(
        plan.get("likely_impacted_files", []),
    )
    complexity["source"] = "likely_impacted_files_only"
else:
    complexity = graph_scope_metrics(plan["scope_evidence"], root)
    complexity["source"] = "scope_evidence"
    cache = load_code_graph_cache(root)
    mapper = mapper_scope_metrics(cache, complexity["affected_paths"])
    if mapper["available"]:
        complexity.update(mapper)
        complexity["source"] += "+mapper"
```

This means even without a full investigation, the routing gets at least Tier-1 metrics from `likely_impacted_files`.

---

### 5.8 Should the Agent Host Ever Be Involved?

**Primary path**: No. The deterministic tiers above cover the vast majority of cases and align with TailTrail's evidence-first, bounded-discovery philosophy.

**Acceptable fallback**: When a project uses a language or framework that the code-graph mapper doesn't support (e.g., a new language, custom DSL, or heavily metaprogramming codebase), and no `scope_evidence` document exists, the host agent **could** provide a qualitative complexity assessment as a last resort — but only if:

- It's marked as `source: "host-agent-qualitative"` in the metrics dict
- It's treated as a **weak signal** (lower weight than deterministic metrics)
- It's bounded (e.g., host returns a simple `complexity_tier: "low" | "medium" | "high"` rather than open-ended reasoning)
- It's clearly labeled in the routing evidence so the user knows it's host-judgment, not computed evidence

This keeps the system deterministic by default and only degrades to host judgment when absolutely necessary.



### 5.9 Architecture Summary

```
User runs: tailtrail start "Fix validation bug..."

┌─────────────────────────────────────────────────────────┐
│ 1. Navigator discovery / investigation                  │
│    → investigate() produces scope_evidence document     │
│    → candidates[], edges[], behavior_chains, stats      │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│ 2. extract_scope_complexity_metrics()  [NEW]            │
│    Tier 1: cheap_scope_metrics() from likely_impacted   │
│    Tier 2: graph_scope_metrics() from scope_evidence    │
│    Tier 3: mapper_scope_metrics() from graph cache      │
│    → plan["scope_complexity"] = {...}                    │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│ 3. aidlc_mode_selection()  [MODIFIED]                   │
│    Reads: goal keywords + risk_indicators               │
│    Reads: plan["scope_complexity"]                      │
│    Applies: keyword_signal OR scope_signal → Standard   │
│             scope_floor_lite prevents over-escalation    │
└────────────────────────┬────────────────────────────────┘
                         │
                    mode = "lite" | "standard" | "full" | "off"
```

---


### 5.10.5 How Different Project Types Might Tune These

| Project Profile | Adjustments | Reasoning |
|---|---|---|
| **Small team, single service** | Lower `affected_files_standard` to 8-10; lower `standard_escalation_score` to 35 | Fewer people to coordinate — breadth matters more |
| **Large team, multi-service** | Raise `affected_files_standard` to 30-50; raise `standard_escalation_score` to 50-60 | Large repos naturally have many files touched; need stronger signal |
| **Safety-critical (regulated/security)** | Lower `new_external_deps_standard` to 0 (any new dep triggers); lower `standard_escalation_score` to 30 | Even small structural novelty is high-risk |
| **Rapid-iteration startup** | Raise `standard_escalation_score` to 55-65; raise `affected_files_lite_floor` to 10 | Default to Lite more aggressively; only escalate when clearly warranted |
| **Mature legacy codebase** | Lower `call_chain_depth_stddev_standard` to 1.0; raise `ambiguity` weight to 0.20 | Legacy code tends to have deeper, more tangled call chains |

### 5.10.6 Validation Methodology

Before these thresholds are used in production, they should be validated against known-good historical decisions:

1. **Collect historical data**: If TailTrail has past runs with known mode selections, extract the metrics for those runs.
2. **Label the outcomes**: For each historical run, determine whether the mode selection was "appropriate" (this requires human judgment or post-hoc review).
3. **Plot the distribution**: Show the complexity score distribution for Lite vs. Standard runs. Look for separation.
4. **Find the decision boundary**: Identify the score threshold that best separates Lite-appropriate from Standard-appropriate runs.
5. **Test sensitivity**: Vary each threshold ±20% and measure how many historical classifications change. Thresholds with high sensitivity need more careful calibration.
6. **Check false positives**: For runs classified as Standard by the new logic but Lite in practice, understand why the metrics suggested Standard and whether that was actually warranted.
7. **Check false negatives**: For runs classified as Lite by the new logic but Standard in practice, understand what the metrics missed.

If no historical data is available, use synthetic test cases (like the worked examples above) to validate that the thresholds produce intuitive results for known scenarios.

### 5.10.7 Relationship to Code Graphing (Cross-Reference)

The quality of threshold calibration depends on the quality of the metric extraction. The code graphing implementation in `docs/arch/code-graphing.md` defines how metrics are computed. Key dependencies:

| Calibration Concern | Graph Dependency |
|---|---|
| `affected_files` accuracy | Graph must correctly identify all files in the change scope |
| `call_chain_depth_*` accuracy | Graph must have function-level call edges, not just imports |
| `cross_layer_edge_count` accuracy | Graph must correctly classify files into layers |
| `new_external_deps` accuracy | Graph must distinguish existing vs. new edges (requires comparison to baseline graph) |
| `module_resolution_ambiguous` accuracy | Graph must report resolution failures explicitly |

If the graph is shallow (imports only), the metrics will be: `affected_files` ✓, `cross_layer_edge_count` partial, `call_chain_depth_*` missing, `new_external_deps` missing. This means the calibration is less reliable for early-phase implementations that only have shallow graph coverage.

### 5.10.8 Continuous Calibration Loop

Thresholds should not be set once and forgotten. A continuous calibration loop:

```
┌─────────────────────────────────────────────────────────┐
│ 1. Run with current thresholds                            │
│    → For each run, record: goal, metrics, selected mode  │
│    → Store in run metadata or calibration log             │
└──────────────────────────┬────────────────────────────────┘
                           │
┌──────────────────────────▼────────────────────────────────┐
│ 2. Periodic review (weekly/monthly or on-demand)          │
│    → Sample recent runs, compare auto-selected mode        │
│      to what a human would have chosen                    │
│    → Identify runs where auto-selection seems wrong        │
└──────────────────────────┬────────────────────────────────┘
                           │
┌──────────────────────────▼────────────────────────────────┐
│ 3. Adjust thresholds                                       │
│    → If too many Standard escalations: raise thresholds    │
│    → If too many Lite (missing real complexity): lower    │
│    → Adjust weights if specific dimensions are off         │
└──────────────────────────┬────────────────────────────────┘
                           │
┌──────────────────────────▼────────────────────────────────┐
│ 4. Validate against holdout set or new runs               │
│    → Don't tune on the same data used to set thresholds    │
│    → Track calibration drift over time                     │
└─────────────────────────────────────────────────────────┘
```

This loop can be manual (human reviews a sample and adjusts) or partially automated (statistical analysis of mode distribution vs. metric values).



## 5.10 Decision Framework: When to Escalate

This section defines the concrete decision logic for when quantitative metrics should trigger a higher AIDLC mode. It answers: **"At what `affected_files` count do we escalate to Standard? And what makes a task 'complex enough' for Full?"**

### 5.10.1 The Core Heuristic

Escalation is **not** a single threshold on `affected_files`. It's a multi-signal assessment where any one strong signal can trigger Standard, and multiple signals together can trigger Full. This prevents both over-escalation (a 30-file well-contained refactor shouldn't force Full) and under-escalation (a 3-file auth patch that introduces a new external dependency should escalate).

The decision uses a **scoring model** with three tiers of signals:

```
TIER 1 — STRONG INDIVIDUAL SIGNALS (any ONE triggers Standard)
  · cross_layer_edges >= 3
  · new_external_dependencies >= 1
  · call_chain_depth_stddev >= 3.5
  · module_resolution_ambiguous >= 5
  · behavior_chain_state == "incomplete"

TIER 2 — MODERATE SIGNALS (need 2+ to trigger Standard)
  · affected_files >= 20
  · affected_files >= 10 AND cross_layer_edges >= 2
  · critical_risk_keyword detected AND affected_files >= 3

TIER 3 — WEAK SIGNALS (need 3+ to trigger Standard)
  · affected_files >= 10
  · call_chain_depth_mean >= 2.5
  · files_in_multiple_layers >= 2
```


### 5.10.2 Standard vs. Full: Different Thresholds

Full mode is **not** just "more of the same signals." It requires evidence of **programme-scale coordination complexity** that goes beyond technical scope. The distinction:

```
STANDARD triggers when:
  · Technical scope is material (many files, deep call chains, cross-layer)
  · OR a high-stakes content keyword is present with non-trivial scope
  · OR multiple moderate signals combine

FULL triggers when (requires BOTH a technical signal AND a programme signal):
  · Technical: affected_files >= 30 OR cross_layer_edges >= 5
  · PLUS Programme: any of:
      - hands_free or end_to_end phrase in goal
      - goal contains "release", "rollout", "migration", "multi-team"
      - scope_evidence.state == "programme_coordination"
      - explicit --aidlc full flag
```

**The key insight**: Full is reserved for work that is both technically large **and** involves coordination/release/migration concerns. A large refactor that's purely internal (no release, no multi-team handoff) stays Standard. A small security patch in production stays Standard (keyword + small scope, not Full).


## 5.10 Decision Framework: When to Escalate

### 5.10.1 The Core Question

At what point does a task become "complex enough" to warrant Standard or Full AIDLC mode?

This is fundamentally a **risk-based decision**, not a pure file-count decision. The quantitative metrics are signals, not answers. A task that touches 30 files in a single module with no cross-layer edges may be less risky than a task that touches 3 files across API + service + database layers.

The system should look for **patterns across multiple signals**, not any single threshold.

### 5.10.2 Decision Tree

```
START: Goal received → keyword analysis + scope metrics extracted

├── Keywords fire (≥2 programme signals OR ≥2 critical risks)?
│   ├── YES → Check scope floor:
│   │   ├── Tiny scope (≤5 files, ≤50 estimated lines)?
│   │   │   └── → Lite + risk noted in report
│   │   └── Not tiny?
│   │       └── → Standard (keyword-driven escalation)
│   └── NO → Continue to scope analysis

├── Scope metrics fire (≥1 quantitative threshold)?
│   ├── YES → Standard (scope-driven escalation)
│   └── NO → Continue to combined assessment

└── Combined assessment:
    ├── Multiple weak signals (1 keyword + 1 metric near threshold,
    │   or 2 metrics each just below threshold)?
    │   └── → Standard (weak-signal aggregation)
    └── No signals, no metrics near threshold?
        └── → Lite
```

### 5.10.3 Escalation Thresholds by Mode

| Mode change | Trigger condition | Rationale |
|---|---|---|
| Lite → Standard | ≥2 programme keywords OR ≥2 critical risks (non-tiny scope) OR ≥1 scope metric above threshold OR 1 keyword + 1 metric near threshold | Material scope or risk detected; coordination/review benefit outweighs overhead |
| Standard → Full | `hands_free` phrase AND scope metrics indicate program-scale (≥10 files across ≥3 layers OR ≥5 cross-layer edges) OR explicit `--aidlc full` flag | Hands-free program delivery with material scope warrants full lifecycle rigor |
| Any → Off | Explicit `"without AIDLC"` / `"AIDLC off"` keyword OR user opt-out in project policy | User explicitly rejects AIDLC |
| Any → Lite (override) | User explicitly selects Lite despite signals firing | User authority overrides auto-selection |


## 6. Implementation Phases

This section defines a phased roadmap for implementing the quantitative code-complexity metric feature. Each phase is independently testable and delivers incremental value. Phases are ordered by risk and dependency — later phases build on earlier ones.

### Phase 1 — Metric Extraction Infrastructure

**Goal**: Add the ability to extract quantitative metrics from existing scope evidence data.

**Scope**:
- [ ] Add `extract_scope_complexity_metrics(root, scope_evidence, likely_impacted_files)` to `scripts/navigator_scope.py`
- [ ] Implement Tier 1 (cheap_scope_metrics) and Tier 2 (graph_scope_metrics) extractors
- [ ] Return structured dict with `source` field indicating which tiers contributed
- [ ] Add unit tests for metric extraction with synthetic scope_evidence documents

**Files changed**:
- `scripts/navigator_scope.py` — new extraction functions
- `tests/test_navigator_scope_metrics.py` — new test file

**Dependencies**: None. Uses data already available in `scope_evidence` document.

**Exit criteria**:
- Metric extraction returns correct values for known synthetic inputs
- `source` field correctly identifies which tier produced each metric
- Unit tests pass

**Estimated effort**: 1-2 days

---

### Phase 2 — Wiring Metrics into Mode Selection

**Goal**: Connect extracted metrics to `aidlc_mode_selection()` with dual-gate logic.

**Scope**:
- [ ] Add `DEFAULT_AIDLC_SCOPE_THRESHOLDS` constant to `scripts/task-start.py`
- [ ] Insert `extract_scope_complexity_metrics()` call in `compose_start_report()` at line ~2410.5
- [ ] Store result in `plan["scope_complexity"]`
- [ ] Modify `aidlc_mode_selection()` or `navigator_standard_evidence()` to read `plan["scope_complexity"]`
- [ ] Implement dual-gate logic: keyword_signal OR scope_signal → escalate; scope_floor_lite prevents over-escalation
- [ ] Add unit tests for routing decisions with various metric combinations

**Files changed**:
- `scripts/task-start.py` — wiring and modified routing
- `tests/test_aidlc_scope_complexity.py` — new test file

**Dependencies**: Phase 1 complete.

**Exit criteria**:
- Known goal+scope combinations produce expected mode decisions
- Scope floor correctly keeps Lite for tiny scope even when keyword fires
- Scope signal correctly escalates to Standard for large scope without keyword

**Estimated effort**: 2-3 days

---

### Phase 3 — Threshold Calibration and Project Overrides

**Goal**: Make thresholds tunable per project and establish calibration methodology.

**Scope**:
- [ ] Add optional project-level threshold override file (e.g., `.tailtrail/aidlc-scope-thresholds.json`)
- [ ] Load overrides in `compose_start_report()` if file exists
- [ ] Document threshold semantics and tuning guidance
- [ ] Run calibration experiments on historical TailTrail runs (if available) or synthetic scenarios
- [ ] Record calibration results in `docs/arch/aidlc-calibration.md` or similar

**Files changed**:
- `scripts/task-start.py` — threshold loading
- `.tailtrail/aidlc-scope-thresholds.json` — example override file (optional)
- `docs/arch/aidlc-calibration.md` — calibration documentation (new)

**Dependencies**: Phase 2 complete.

**Exit criteria**:
- Project override file is loaded and applied correctly
- Defaults are documented with rationale
- Calibration notes exist for future tuning

**Estimated effort**: 1 day

---



### Phase 4 — Extending `assess_scope_quality()` (Optional Consolidation)

**Goal**: Optionally move metric extraction into `assess_scope_quality()` so it's a single extraction point.

**Scope**:
- [ ] Evaluate whether `assess_scope_quality()` should return complexity metrics alongside its current pass/block verdict
- [ ] If yes: add `complexity_metrics` field to its return dict
- [ ] Update `compose_start_report()` to read metrics from `scope_quality` instead of separate `scope_complexity`
- [ ] Remove or deprecate standalone `extract_scope_complexity_metrics()` if consolidated

**Files changed**:
- `scripts/navigator_scope.py` — extended return
- `scripts/task-start.py` — updated read path

**Dependencies**: Phase 2 or 3 complete.

**Exit criteria**:
- Single extraction point serves both quality validation and complexity metrics
- No duplicate extraction logic

**Estimated effort**: 0.5-1 day

**Note**: This phase is **optional** — it's a consolidation, not a feature addition. Phase 2 can work with a standalone function indefinitely.

---

### Phase 5 — Host-Agent Qualitative Fallback (Contingency)

**Goal**: Add a bounded host-agent fallback for projects where deterministic metrics are unavailable.

**Scope**:
- [ ] Define fallback interface: host returns `complexity_tier: "low" | "medium" | "high"` with `source: "host-agent-qualitative"`
- [ ] Treat fallback as weak signal (lower weight, does not override deterministic metrics)
- [ ] Document when fallback is acceptable (unsupported language, no scope_evidence, no graph cache)
- [ ] Add guardrails: fallback cannot escalate to Full mode on its own

**Files changed**:
- `scripts/task-start.py` — fallback handling
- `docs/arch/aidlc-host-fallback.md` — fallback policy (new)

**Dependencies**: Phase 2 complete.

**Exit criteria**:
- Fallback is clearly labeled as qualitative/weak
- Fallback cannot drive Full escalation alone
- Policy documents acceptable use cases

**Estimated effort**: 1 day

**Note**: This phase should only be implemented if there's a demonstrated need — it's a contingency, not a default path.

---

### Phase 6 — Post-Discovery Re-Evaluation Hook (Separate Enhancement)

**Goal**: Allow AIDLC mode to be re-checked after scope discovery reveals larger-than-expected scope.

**Scope**:
- [ ] Identify where in the lock-finalization or Planning Lock flow a re-evaluation hook could be added
- [ ] Define trigger conditions (e.g., `scope_quality.changed_files` exceeds threshold after investigation)
- [ ] Define user interaction model (auto-prompt vs. opt-in flag)
- [ ] Implement hook and tests

**Files changed**:
- `scripts/task-start.py` and/or lock finalization path
- `tests/test_aidlc_reevaluation.py` — new test file

**Dependencies**: Phase 2 complete (needs metrics to re-evaluate against).

**Exit criteria**:
- Re-evaluation triggers when scope exceeds threshold
- User is prompted or can opt-in via flag
- Tests cover both auto and opt-in paths

**Estimated effort**: 2-3 days

**Note**: This is a separate enhancement from the quantitative metric feature. It uses the metrics but adds a different capability (dynamic re-checking).

---

### Phase Summary Table

| Phase | Goal | Effort | Dependencies | Risk |
|---|---|---|---|---|
| 1 | Metric extraction infrastructure | 1-2 days | None | Low |
| 2 | Wire metrics into mode selection | 2-3 days | Phase 1 | Medium |
| 3 | Threshold calibration + overrides | 1 day | Phase 2 | Low |
| 4 | Consolidate into assess_scope_quality | 0.5-1 day | Phase 2 or 3 | Low |
| 5 | Host-agent qualitative fallback | 1 day | Phase 2 | Medium (contingency) |
| 6 | Post-discovery re-evaluation hook | 2-3 days | Phase 2 | Medium |

**Total if all phases implemented**: ~8-11 days

**Minimum viable (Phases 1+2)**: ~3-5 days — this delivers the core feature: quantitative metrics influencing AIDLC mode selection.

---

### 6.1 Recommended Implementation Order

For a first implementation, the recommended order is:

1. **Phase 1** — Get metrics extracting correctly (no mode routing change yet, easy to test in isolation)
2. **Phase 2** — Wire into mode selection with conservative thresholds (start strict to avoid over-escalation)
3. **Phase 3** — Add project overrides so teams can tune without code changes

Phases 4-6 are enhancements that can be prioritized based on observed need after Phases 1-3 are in production.

---

### 6.2 Risks and Mitigations

| Risk | Phase | Mitigation |
|---|---|---|
| Graph not available at mode selection time | 1-2 | Tier 1 metrics from `likely_impacted_files` work without graph; Tier 2/3 degrade gracefully |
| Thresholds cause over-escalation | 2-3 | Start conservative; phase 3 adds project tuning; add logging of which signal fired |
| Performance impact on start latency | 1-2 | Tier 1 is O(n) on path count; Tier 2/3 only run when scope_evidence exists; cache reuse |
| Testability of routing decisions | 2 | Synthetic scope_evidence documents with known metric values; assert mode outputs |
| Project override file misconfiguration | 3 | Validate JSON schema; fall back to defaults on error; log override loading |
| Host-agent fallback abused as primary path | 5 | Guardrails: weak signal only, cannot drive Full, clearly labeled |

---

### 6.3 Success Metrics (Post-Implementation)

After Phases 1-3 are implemented, the following can be tracked:

| Metric | Target |
|---|---|
| Tasks with `scope_signal=True` that would have been Lite under old system | Track volume and sample for quality review |
| Tasks kept on Lite due to `scope_floor_lite` despite keyword firing | Track volume — confirms dual-gate prevents over-escalation |
| User override rate (user manually changing auto-selected mode) | Lower is better — indicates thresholds are well-calibrated |
| Start latency impact | Should be minimal — Tier 1 is cheap; Tier 2/3 reuse existing data |

These metrics inform whether Phase 3 calibration adjustments are needed.
