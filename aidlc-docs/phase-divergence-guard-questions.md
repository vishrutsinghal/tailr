# Phase: divergence-guard Integration — Clarification Questions

Context grounding these questions (already verified directly against the
code, not assumed):

- `divergence-guard` (supplied as a combined single-file dump at
  `/Users/vsingha7/Desktop/divergence-guard-combined.py`) is a complete,
  independent, standalone Python package — its own `pyproject.toml`, CLI
  (`divergence-guard install/uninstall/status/check`), MCP server exposing
  `audit_diff`/`audit_working_tree`/`suggest_concise_version`, and one
  adapter per host (`claude`, `codex`, `generic`). It is not a patch to
  TailTrail's own code.
- Its capability (score a diff for conciseness/scope-creep via file-count,
  additive-only-diff, and TODO-marker heuristics) does **not** duplicate
  anything already in TailTrail — `guardrail-check.py` does diff analysis
  for a different concern set (dependency gates, safeguard removal,
  local-state writes, validation-claim honesty), and
  `maintainability_planning.py`'s "scope creep" reference is only a
  keyword tag in requirement classification, not a diff analyzer. This is
  genuinely new capability, not redundant.
- **Zero file-level collision risk** was confirmed: TailTrail's own host
  wiring never writes to `.mcp.json` or `~/.codex/config.toml` — it only
  writes project-local `.codex-plugin/`-style convention files into
  governed target repos. divergence-guard's adapters write to the AI
  tool's own global MCP config, a disjoint file set. Installing both
  side by side cannot corrupt either system's existing entries.
- **Gap found**: divergence-guard has no Copilot adapter today, only
  `claude`/`codex`/`generic`. TailTrail's own host contract is
  `HOSTS = ("codex", "copilot", "claude")` — exact parity would require a
  new `CopilotAdapter`.
- **Dependency-philosophy conflict found**: divergence-guard's
  `pyproject.toml` declares `dependencies = ["mcp>=2.0"]`. TailTrail's own
  `pyproject.toml` has `dependencies = []` and a verified, repository-wide,
  zero-third-party-import convention across all ~280 scripts. These only
  collide if divergence-guard's code is vendored directly into TailTrail
  rather than kept as a separate installable package.

Please answer each question by filling in the letter choice after the
`[Answer]:` tag. If none of the options match, choose the last option
(Other) and describe your preference. Let me know when you're done.

## Question 1
What's the right integration depth between TailTrail and divergence-guard?

A) **Standalone companion** — keep divergence-guard a fully separate pip
   package with its own install step (`pip install divergence-guard &&
   divergence-guard install`), documented in TailTrail's docs as a
   complementary tool. Zero code changes to TailTrail, zero risk, but the
   user must remember a second install step.
B) **TailTrail-orchestrated install** — TailTrail's own per-host install
   loop (`scripts/install-local.py` / `scripts/first-run.py`, which already
   iterates `HOSTS` from `tailtrail/hosts/contracts.py`) also invokes
   divergence-guard's adapter for that same host, as one new optional step.
   Single unified install experience; divergence-guard stays a separate,
   independently-testable package but becomes a soft dependency of
   TailTrail's installer (guarded so TailTrail still works if it's absent).
C) **Full code-level vendoring** — drop divergence-guard's own CLI/MCP
   server/adapters entirely; port just the `core.py` engine
   (`analyze_diff`/`suggest_tighter_version`) into TailTrail's own
   `scripts/`, exposed through TailTrail's existing CLI dispatcher and
   existing stdlib-only MCP server (`scripts/mcp-server.py`). No second
   install step ever, but divergence-guard can no longer be installed or
   used independently of TailTrail, and new code must be written into
   TailTrail's dispatcher/MCP server.
D) Other (please describe after [Answer]: tag below)

[Answer]: 

## Question 2
divergence-guard has no Copilot adapter yet (only claude/codex/generic),
but TailTrail's own contract requires exact codex/copilot/claude parity.
Should that gap be closed as part of this phase?

A) Yes — write a `CopilotAdapter` now, before anything ships, so
   divergence-guard matches TailTrail's existing three-host guarantee from
   day one.
B) No — ship with claude/codex/generic now; Copilot support is an explicit
   fast-follow, called out as a known gap rather than silently missing.
C) Not needed — the `generic` fallback (instructions file + git pre-commit
   hook) is an acceptable permanent answer for Copilot; no dedicated
   adapter is required.
D) Other (please describe after [Answer]: tag below)

[Answer]: 

## Question 3
This question only applies if your Question 1 answer was B (TailTrail-
orchestrated install). Should divergence-guard's install be on by default
for every `tailtrail setup`, or opt-in?

A) Opt-in only — gated the same way we gate other non-core/unproven
   surface (an explicit flag or the `extended` install profile), consistent
   with treating new capabilities as `incubating` until proven.
B) On by default for every install once this phase's implementation and
   tests are complete — no extra flag needed.
C) Not applicable — my Question 1 answer was A or C, not B.
D) Other (please describe after [Answer]: tag below)

[Answer]: 

## Question 4
This question only applies if your Question 1 answer was C (full code-level
vendoring). How should the `mcp>=2.0` dependency conflict with TailTrail's
zero-third-party-dependency convention be resolved?

A) Avoid it entirely — reimplement just the 3 tool functions TailTrail
   needs (`audit_diff`, `audit_working_tree`, `suggest_concise_version`)
   using TailTrail's own existing stdlib-only, hand-rolled MCP
   server/JSON-RPC pattern already in `scripts/mcp-server.py`, so no new
   dependency is introduced anywhere in the repository.
B) Accept `mcp` as TailTrail's first-ever third-party dependency, scoped
   narrowly to this one feature, with that exception documented explicitly
   as a deliberate, one-time departure from the existing convention.
C) Not applicable — my Question 1 answer was A or B, not C.
D) Other (please describe after [Answer]: tag below)

[Answer]: 
