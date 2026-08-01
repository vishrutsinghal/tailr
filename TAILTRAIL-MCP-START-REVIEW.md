# TailTrail MCP / Start Review and Implementation Plan

Status: reviewed and corrected. This document records the investigation, the
MCP declaration-order fix now present in source, documentation corrections, and
remaining recommended improvements. Proposed phases below remain unimplemented
unless explicitly stated otherwise.

Date: 2026-08-01

---

## 1. Original problem reported

> When using `tailtrail start`, the user expects a TailTrail Start plan
> (Navigator-first Start Report + Planning Lock), but gets a *general
> implementation plan*. Attempting to fix it through the MCP tool "did not
> work".

## 2. Investigation summary

| Check | Command | Result |
| --- | --- | --- |
| Start CLI | `python3 scripts/task-start.py "<goal>" --root <repo> --format markdown` | PASS — correct Start Report + `awaiting-approval` Planning Lock |
| MCP tool end-to-end | `initialize` + `tools/call` `tailtrail_start` over stdio `serve` | PASS — returned the full TailTrail Start Report |
| MCP self-check | `python3 scripts/mcp-server.py doctor` | Must pass after the declaration-order correction; not rerun in this workspace because no Python runtime is available. |
| MCP unit tests | `python3 -m unittest tests.test_mcp_server` | Focused coverage exists, including declaration-order diagnostics; not rerun in this workspace because no Python runtime is available. |

### Root-cause conclusions

1. **The planning engine is correct.** Both the CLI and the MCP `tailtrail_start`
   tool produce the proper TailTrail Start Report, not a generic plan.
2. **Real defect found and fixed:** the MCP server's `doctor` self-check was
   failing because one controlled tool (`harness_control_check`) was declared
   out of order inside `tool_definitions()`. A failing `doctor` makes the MCP
   integration look broken / unhealthy to a host validating the server.
3. **The "general plan instead of TailTrail plan" symptom is a host-invocation
   issue, not a code bug.** Natural-language `tailtrail start ...` is a
   convenience trigger only; it cannot guarantee the host model actually calls
   the tool. When the assistant answers conversationally instead of invoking
   `tailtrail_start` (or the `/tailtrail-start` prompt / CLI), you get a generic
   plan.

---

## 3. Changes already applied

### 3.1 Code fix — `scripts/mcp-server.py`

**Problem:** In `tool_definitions()`, the controlled tool `harness_control_check`
was placed between the read-only tools `workflow_dashboard_show` and
`planning_lock_show`. `ensure_safe_tools()` requires the dict key order to equal
`(*READ_ONLY_TOOLS, *CONTROLLED_TOOLS)`, so `doctor` failed.

**Fix:** `planning_lock_show` remains at the end of the read-only group;
`harness_control_check` follows it at the beginning of the controlled-tools
group. This makes declaration order match the allowlist.

Before (order excerpt):
```text
... workflow_dashboard_show, harness_control_check, planning_lock_show, source_patch_apply ...
```
After (order excerpt):
```text
... workflow_dashboard_show, planning_lock_show, harness_control_check, source_patch_apply ...
```

**Validation status:** static order inspection and regression coverage were
updated. Run the commands below in a Python-enabled environment before claiming
runtime success:

```bash
python3 scripts/mcp-server.py doctor
python3 -m unittest tests.test_mcp_server
```

### 3.2 Documentation fixes (earlier in session)

- `tailtrail-mcp.md`
  - Reconciled the "initial server remains R0-only" claim with the now-implemented
    approval-gated higher-tier tools.
  - Rewrote **Source mutation safety** so it no longer states "no source-write
    tool" while `source_patch_apply` is implemented; documented its exact gates.
  - Clarified the Non-goal bullet to "No automatic or unapproved source edits…".
  - Fixed a broken link: `roadmap.md` → `ROADMAP.md`.
- `META-HARNESS-IMPLEMENTATION.md`
  - Removed a duplicated `bootstrap refresh --root .` command line.
- `testing-confidence.md`
  - Added a Baseline note clarifying the 4.5/10 rating is the pre-V2 baseline,
    partly superseded by the V2–V5 / Phase 8.2–8.8 updates.

---

## 4. How to get a deterministic TailTrail Start plan (user guidance)

1. **Any shell (always works):**
   ```bash
   python3 scripts/tailtrail.py start "add payment retry handling"
   ```
2. **GitHub Copilot:** run the `/tailtrail-start` prompt
   (`.github/prompts/tailtrail-start.prompt.md`). Confirm this file exists in the
   project under test; installed packs must be reinstalled to pick it up.
3. **MCP host:** register the server with the `serve` argument and confirm health:
   ```json
   {
     "mcpServers": {
       "tailtrail": {
         "command": "python3",
         "args": ["/path/to/tailtrail/scripts/mcp-server.py", "serve"]
       }
     }
   }
   ```
   Then invoke the `tailtrail_start` tool with `{ "goal": "...", "approved": true }`.

---

## 5. Findings of improvement (prioritized)

### Priority P0 — reliability of the self-check contract

- **F1. `doctor` order-coupling is fragile.** `ensure_safe_tools()` fails on any
  ordering difference between `tool_definitions()` and
  `(*READ_ONLY_TOOLS, *CONTROLLED_TOOLS)`. This is easy to re-break on the next
  edit. Recommend comparing as sets for membership and separately asserting the
  wire order only where wire order matters, OR generate `tool_list()` order from
  the allowlist (already done) and make `doctor` explain the exact mismatched
  names.
- **F2. `doctor` is not enforced in CI.** The unit test `test_doctor_passes`
  exists, but the CLI `doctor` is not wired into CI, so config/registry drift can
  still ship. Recommend a CI step.

### Priority P1 — diagnosability

- **F3. `doctor` diagnostics — implemented.** It now reports the first
  differing index and the expected versus actual tool name. The focused test
  covers this failure mode.
- **F4. `registry_read_only_tools()` ignores the registry.** It loads nothing and
  just returns `DEFAULT_READ_ONLY_TOOLS`; `load_registry()` is defined but unused.
  Either wire the registry projection in (and validate it) or remove the dead
  `load_registry()` to avoid implying dynamic behavior that does not exist.

### Priority P2 — host-invocation clarity (the reported symptom)

- **F5. No host-side signal when a Start request was NOT tool-invoked.** Since
  natural language cannot guarantee invocation, add explicit, documented
  guidance (and a short troubleshooting section) telling users to use the
  `/tailtrail-start` prompt or `tailtrail_start` tool, and how to verify the
  server is registered and healthy.
- **F6. Install verification gap.** Provide a one-shot `tailtrail doctor`-style
  check that reports: prompt file present, skill present, MCP server registered
  and `doctor`-passing, and CLI reachable.

### Priority P3 — small correctness / hygiene

- **F7. `source_patch_apply` path validation is line-prefix based.** It validates
  only lines starting with `+++ b/` / `--- a/`. Rename/copy headers
  (`rename from`, `rename to`, `copy to`) are not path-validated. Recommend
  covering those git header forms to keep patches strictly in-repo.
- **F8. `DENIED_TOOL_TERMS` includes broad substrings** (e.g. `run`, `test`,
  `update`). `install_status` is already special-cased; document this allow-list
  exception clearly so future read-only tools with those substrings are handled
  intentionally, not by accident.

---

## 6. Proposed implementation plan (awaiting approval)

Smallest-safe-change ordering. Each phase is independently reviewable.

### Phase 1 — CI guard for the MCP self-check (P0)
- Add a CI job step running `python3 scripts/mcp-server.py doctor`.
- Acceptance: CI fails if tool order/registry/schema drifts again.
- Files: CI workflow (e.g. `.github/workflows/*.yml`).
- Risk: minimal (read-only check).

### Phase 2 — Better `doctor` diagnostics (P1) — implemented
- In `ensure_safe_tools()`, when order mismatches, append the first differing
  position with expected vs. actual name.
- Acceptance: `doctor` output names the offending tool.
- Files: `scripts/mcp-server.py`; extend `tests/test_mcp_server.py`.
- Risk: low.

### Phase 3 — Resolve registry projection dead code (P1)
- Either use `load_registry()` to project read-only tools and validate against
  `DEFAULT_READ_ONLY_TOOLS`, or remove `load_registry()` and the unused branch.
- Acceptance: no unused registry loader; behavior unchanged or explicitly wired.
- Files: `scripts/mcp-server.py`; test coverage for the chosen path.
- Risk: low–medium (choose the conservative removal unless dynamic projection is
  actually required).

### Phase 4 — Start troubleshooting + `tailtrail doctor` (P2)
- Add a short "Start plan did not appear?" troubleshooting section to
  `MCP-SERVER.md` and `USER-GUIDE.md`.
- Optionally add an install/health doctor that checks prompt file, skill, MCP
  registration, and CLI reachability.
- Acceptance: a user can self-diagnose the "generic plan" symptom in under a
  minute.
- Files: docs; optional `scripts/tailtrail.py` subcommand.
- Risk: low.

### Phase 5 — Patch header hardening (P3)
- Extend `source_patch_apply` to validate rename/copy git headers stay in-repo.
- Acceptance: a rename patch escaping the repo is rejected before `git apply`.
- Files: `scripts/mcp-server.py`; add a negative test.
- Risk: low, security-positive.

---

## 7. Validation status

- Static inspection confirms `tool_definitions()` now has the same read-only /
  controlled boundary as `READ_ONLY_TOOLS` and `CONTROLLED_TOOLS`.
- `tests/test_mcp_server.py` now checks both the correct order and the precise
  failure diagnostic.
- Runtime doctor and Python tests remain required in a Python-enabled
  environment. They were not run from this workspace because `py -3` reports
  `No installed Python found!`.

## 8. Remaining validation and implementation

- Run `python3 scripts/mcp-server.py doctor` and
  `python3 -m unittest tests.test_mcp_server`.
- Full repository test suite (`python3 -m unittest discover`) remains not run.
- CI wiring, registry decision, troubleshooting/health tooling, and patch-header
  hardening remain proposed.

## 9. Residual risk

- The reported "generic plan" symptom will recur whenever a host answers
  conversationally instead of invoking the Start tool/prompt. This is inherent to
  natural-language triggers; Phase 4 mitigates it with guidance and a health
  check but cannot force a host model to call a tool.

