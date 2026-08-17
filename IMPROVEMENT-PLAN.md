# TailTrail — Detailed Improvement Plan

> Created: August 16, 2026  
> Scope: All aspects rated below 8/10 in the honest review.  
> Format: Each section has the current score, root causes, specific changes, and done criteria.

---

## Delivered releases

### Release 1 — Trust foundation — implemented

- GitHub Actions validates Python 3.11–3.13, contracts, registry, adapters, and a fresh-clone installer smoke path.
- Installation now includes profile-aware verification and a local `hello` smoke check.
- Generated Python/platform cache files are ignored and removed from tracked source.

### Release 2 — Product enforcement — implemented

- CI builds an explicit base-to-head diff and runs the Guard CLI against that actual change set.
- New dependency additions are gated by a structured, reviewable decision record in `tailtrail-meta/dependency-decisions/`.
- `tailtrail dependency validate|check` validates record structure and matches approved decisions to dependency-manifest additions.
- `hooks/guard-advisory-hook.py` provides non-blocking local feedback; it never edits, stages, installs, commits, or pushes.
- Focused tests cover missing, approved, rejected/deferred, malformed decisions, CI wiring, and hook non-blocking behavior.

### Release 3 — Simplify the experience — implemented

- README now presents one outcome-first path: install, start, review, approve, and read the Completion Report.
- `INSTALL.md` is the canonical source for supported platforms, host profiles, updates, verification, install surfaces, and optional Full AI-DLC setup.
- Added concise Codex, Copilot, and Claude quickstarts under `docs/hosts/`.
- Reworked `QUICKSTART.md` and `CHEATSHEET.md` around daily user choices; the detailed User Guide now routes setup questions to `INSTALL.md`.
- Core install surfaces ship the quickstart docs and host guides, while Extended retains the broader documentation and tools.
- Documentation and installer-surface contracts are covered by focused regression tests.

### Release 4 — Maintainability — implemented

- Added characterization tests for local discovery selection, Start posture data, and compact/verbose report contracts before refactoring.
- Extracted deterministic filesystem/Git/graph discovery into `scripts/navigator_discovery.py`; Navigator retains compatibility wrappers for existing callers.
- Extracted side-effect-free token, setup, review, harness, bootstrap, and evaluation posture builders into `scripts/start_posture.py`.
- The existing Navigator decision boundary and Start renderer remain public and unchanged; installed packs now ship both extracted modules.
- Registry ownership and installer-surface checks cover the new modules.

---

## Summary Table

| Aspect | Score | Priority |
|---|:---:|:---:|
| Test coverage | 2/10 | P0 |
| Enforcement / teeth | 3/10 | P0 |
| Real-world efficacy evidence | 3/10 | P1 |
| Onboarding / simplicity | 3/10 | P0 |
| Install experience | 4/10 | P0 |
| Reliability / bug density | 4/10 | P0 |
| Maintainability | 4/10 | P1 |
| Code quality | 5/10 | P1 |
| Documentation | 5/10 | P2 |

---

## 1. Test Coverage — 2/10 → Target 8/10

### Current state

- There are ~50 test files in `/tests/` but most are smoke tests or load-and-check-one-property tests.
- The most critical routing logic — `_aidlc_intent`, `aidlc_mode_selection`, AIDLC question generation, Navigator impacted-file filtering, `compact_start_report` rendering — has zero dedicated tests.
- We discovered and fixed bugs in `_aidlc_intent`, `is_actionable_changed_path`, SKILL.md launcher path, and a SyntaxError in `task-start.py` all through **manual running**, not tests.
- No CI pipeline is visible. No test runner configuration (`pytest.ini`, `pyproject.toml [tool.pytest]`).

### Root causes

1. Tests were added reactively per feature, not per risk surface.
2. The most complex functions (`aidlc_mode_selection`, `compact_start_report`) are not unit-tested at all.
3. No contract tests — the shape of what `build_report()` returns is not validated.

### Specific changes needed

#### 1.1 — `tests/test_aidlc_mode_selection.py` (NEW)
Cover every routing branch of `_aidlc_intent` and `aidlc_mode_selection`:

```python
# Every combination that must work from a user perspective
phrases_standard = [
    "use standard aidlc implement pipeline audit events",
    "aidlc standard",
    "standard aidlc",
    "apply the standard aidlc mode",
    "implement with aidlc standard mode",
    "aidlc normal mode please",
    "using standard aidlc",
]
phrases_requested = [
    "using aidlc",
    "use aidlc",
    "with aidlc please",
    "implement pipeline feature, use aidlc",
]
phrases_full = [
    "full aidlc",
    "official aidlc mode",
    "use complete aidlc",
    "enterprise aidlc workflow",
]
phrases_optout = [
    "without aidlc",
    "no aidlc please",
    "skip aidlc for this",
    "do not use aidlc",
]
phrases_none = [
    "implement pipeline audit events generator",
    "just implement this feature",
    "fix the bug in service.py",
]
```

Each phrase must assert the correct `mode` in the returned dict.

#### 1.2 — `tests/test_navigator_impacted_files.py` (NEW)
Test that TailTrail-managed paths are always filtered out:
```python
managed_paths = [
    "skills/tailtrail-start/SKILL.md",
    ".codex-plugin/plugin.json",
    ".github/copilot-instructions.md",
    "AGENTS.md",
    "AIDLC.md",
    "GUARDRAILS.md",
    "TOKEN-AUTOPILOT.md",
]
# All of the above must return False from is_actionable_changed_path
# Real project files must return True
real_paths = [
    "src/components/Button.tsx",
    "src/pages/dashboard/hooks/usePipelineDetails.ts",
    "tests/integration/pipeline.test.ts",
]
```

#### 1.3 — `tests/test_compact_start_report.py` (NEW)
Test the output structure of `compact_start_report`:
- Every section header (`## Planning Lock`, `## Scope`, `## Requirements`, etc.) must be present in the correct order.
- Tables must have a `| --- |` row.
- AIDLC questions section must appear when `aidlc_requirements` is set and mode is standard/full.
- Approval section must prompt for AIDLC answers when questions are present.
- No SyntaxErrors (f-string escaping).

#### 1.4 — `tests/test_install_paths.py` (NEW)
Validate that installed launcher paths are correct:
- After `install codex-plugin`, `skills/tailtrail-start/SKILL.md` must contain `tailtrail/scripts/tailtrail.py` not `scripts/tailtrail.py`.
- `AGENTS.md` must reference `tailtrail/scripts/tailtrail.py`.

#### 1.5 — Add `pytest.ini` and `CI` config
```ini
# pytest.ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = *Tests
python_functions = test_*
addopts = -v --tb=short
```

Add a GitHub Actions workflow `.github/workflows/tests.yml`:
```yaml
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: python -m pytest tests/ -v
```

### Done criteria
- `python -m pytest tests/` passes with 0 failures on every push.
- `_aidlc_intent`, `aidlc_mode_selection`, `is_actionable_changed_path`, and `compact_start_report` each have ≥10 test cases covering real user phrases and edge cases.
- A new regression cannot be merged without a failing test catching it.

---

## 2. Enforcement / Teeth — 3/10 → Target 7/10

### Current state

TailTrail now has a CI enforcement foundation: the Guard CLI evaluates the real
change diff for selected guardrail classes, and dependency-manifest additions
require an approved structured decision record. A local advisory hook provides
the same feedback without blocking a developer. Broader source-semantic,
policy-as-code, and local blocking controls remain future work.

### Root causes

1. The framework was designed as guidance for models, not enforcement for humans/CI.
2. The hooks directory exists (`hooks/`) but the only hook is `learning-capture-hook.py` — a post-task learning recorder, not a guardrail enforcer.
3. No machine-checkable assertions for the highest-value rules.

### Specific changes needed

#### 2.1 — Pre-commit hook: dependency gate check
Create `hooks/pre-commit-dependency-gate.py`:
- Scans staged `package.json`, `requirements.txt`, `pyproject.toml`, `pom.xml`, `go.mod` diffs.
- If a new dependency appears without a `DEPENDENCY-GATE.md` decision entry, print a warning and exit 1.
- Configurable: `--warn-only` for teams not ready to block.

```bash
# .pre-commit-config.yaml entry
- repo: local
  hooks:
    - id: tailtrail-dependency-gate
      name: TailTrail Dependency Gate
      entry: python3 hooks/pre-commit-dependency-gate.py
      language: python
      stages: [commit]
      types: [file]
```

#### 2.2 — Pre-commit hook: false validation claim scanner
Create `hooks/pre-commit-validation-truth.py`:
- Scans staged `.md` files (PR descriptions, changelogs, commit messages) for patterns like:
  - `tests passed` / `all tests pass` / `CI passed` not preceded by a CI receipt link or `tailtrail completion-report` output.
  - `deployed to` / `pushed to production` in a commit message without a receipt.
- Prints a warning with the offending line and exits 1 (or warn-only mode).

#### 2.3 — Pre-commit hook: safeguard preservation check
Create `hooks/pre-commit-safeguard-check.py`:
- Diffs staged source files.
- Flags removal of lines containing: `authorize`, `authenticate`, `validate(`, `sanitize(`, `escape(`, `@Secured`, `hasPermission`, `requiresRole`.
- Does not block — prints a structured warning asking the developer to confirm intentional removal.

#### 2.4 — `tailtrail guard` command (integrate into CLI)
Already has `scripts/guardrail-check.py` and `scripts/guardrail-precision.py` — wire these to run as:
```bash
tailtrail guard --staged     # check staged changes
tailtrail guard --diff HEAD  # check last commit
```
Return exit code 1 on violations so CI can use it.

#### 2.5 — Document the enforcement path clearly
Add `ENFORCEMENT.md`:
- Step 1: Advisory (current — Markdown rules).
- Step 2: Soft enforcement (pre-commit hooks, warn-only).
- Step 3: Hard enforcement (CI gate, blocks merge).
- Show one concrete install command per step.

### Done criteria
- `hooks/pre-commit-dependency-gate.py` exists, blocks a commit that adds a package without a DEPENDENCY-GATE entry.
- `tailtrail guard --staged` returns exit code 1 on a staged diff that removes an auth check.
- `ENFORCEMENT.md` exists and is linked from README.

---

## 3. Real-World Efficacy Evidence — 3/10 → Target 7/10

### Current state

- Benchmarks are in `scripts/benchmark-tailtrail.py` and `scripts/efficacy-benchmark.py`.
- All scenarios are **synthetic and self-scored** — the honest disclaimers in `PUBLIC-CLAIMS.md` confirm this.
- No published before/after data from a real project with real model runs.

### Root causes

1. Getting real efficacy data requires either running live models (cost, privacy) or finding a contributor who will share anonymized before/after diffs.
2. The tool itself warns against fake claims, so it cannot claim efficacy it hasn't measured.

### Specific changes needed

#### 3.1 — Create a public, reproducible benchmark project
- Add `benchmarks/reference-project/` — a small, real-ish open-source frontend or API (e.g. a simple Todo API in Express or FastAPI).
- Add `benchmarks/scenarios/` — 5 realistic tasks:
  1. Add a dependency without a gate check.
  2. Fix a validation bug.
  3. Add a new API endpoint.
  4. Refactor a 200-line file.
  5. Fix a Sonar cognitive complexity issue.
- For each scenario: `baseline-prompt.md` (raw prompt, no TailTrail), `tailtrail-prompt.md` (with TailTrail start + AIDLC).
- Commit the **actual output** from a real model run (GPT-4o or Claude 3.5) for both.

#### 3.2 — Publish scored results with honest labels
- Run `tailtrail eval` against the committed outputs.
- Publish scores to `benchmarks/results/public-benchmark-2026-08.json`.
- Label every score: `fixture-scored` (deterministic, no model) vs `model-run` (actual model, with date and model version).
- Add a `benchmarks/README.md` that explains methodology, what was measured, and what was not.

#### 3.3 — Add a `tailtrail benchmark run-public` command
- Runs the 5 scenarios against locally provided outputs.
- Prints a comparison table: diff size, new dependencies, removed safeguards, false validation claims, scope creep.
- Does not call any model — compares committed artifacts only.

#### 3.4 — Create `PUBLIC-CLAIMS.md` scorecard section
Add a section to the existing `PUBLIC-CLAIMS.md`:
```markdown
## Measured evidence (as of 2026-08)
| Claim | Evidence type | Value | Source |
|---|---|---|---|
| Reduces diff size | fixture-scored | -34% median | benchmarks/results/public-benchmark-2026-08.json |
| Dependencies added without gate | fixture-scored | 0 of 5 scenarios | same |
| False "tests passed" claims | fixture-scored | 0 of 5 scenarios | same |
```
Only include claims backed by the committed benchmark results.

### Done criteria
- `benchmarks/reference-project/` exists with ≥5 scenarios.
- `benchmarks/results/public-benchmark-2026-08.json` is committed with honest labels.
- `PUBLIC-CLAIMS.md` references only fixture-scored or measured results.

---

## 4. Onboarding / Simplicity — 3/10 → Target 8/10

### Current state

- 150+ scripts, 10+ phases, 20+ documentation files, multiple install profiles, two surfaces (core/extended), multiple update commands.
- A new user reading the README faces: `install local`, `install codex-plugin`, `install copilot`, `--surface core`, `--surface extended`, `--profile copilot`, `tailtrail do`, `tailtrail start`, `tailtrail guide`, `tailtrail next` — all before writing a single line of code.
- The phase-by-phase history in `DESIGN.md` is internal engineering context presented as user documentation.

### Root causes

1. Every feature added over time got a new command, new doc, new script — nothing was ever removed or consolidated.
2. The README leads with install options instead of the value proposition and a single first action.
3. The "Core" surface exists but is not prominently offered — most install instructions default to Extended.

### Specific changes needed

#### 4.1 — Rewrite README.md structure

New structure:
```
1. What problem does TailTrail solve? (3 sentences, no phases)
2. Install in 1 command (single recommended path — codex-plugin or copilot)
3. Your first task (copy-paste one command)
4. What you get (3 concrete outcomes with examples)
5. For teams / enterprises (link to ENTERPRISE-REVIEW.md)
6. Advanced / full command surface (collapsed or linked to CHEATSHEET.md)
```

Remove from README:
- Phase history references.
- All platform-specific install variants in the main body (move to INSTALL.md).
- The "Choose a surface" section (default to core; offer extended on request).

#### 4.2 — Create `INSTALL.md` (move all install variants here)
Move the Windows/macOS/Linux/profile/surface/update install matrix out of README into `INSTALL.md`. README links to it for "full install options."

#### 4.3 — One recommended first command
Pick one and make it the default everywhere:
```bash
python3 scripts/tailtrail.py install codex-plugin --target /path/to/your-project
```
Remove or de-emphasize the 8 other install variants from the main path. They still exist; they just aren't the first thing a new user sees.

#### 4.4 — `tailtrail onboard` interactive wizard
Create `scripts/onboard.py`:
```
$ tailtrail onboard
? What assistant do you use? (Codex / Copilot / Claude / Cursor / Other)
? What is your project root? [/current/dir]
? What kind of project is it? (Frontend / Backend / Full-stack / Other)

→ Installing TailTrail Core for Codex...
→ Done. Run this in your project:
  python3 tailtrail/scripts/tailtrail.py start "describe your first task"
```
3 questions, one output command. No phases, no surfaces, no profiles.

#### 4.5 — `CHEATSHEET.md` — one-page problem → command map
```markdown
| I want to... | Command |
|---|---|
| Plan a task before implementing | tailtrail start "describe task" |
| Review a diff before merging | tailtrail review |
| Stop AI from hallucinating tests | Read GUARDRAILS.md — "Validation Truth" section |
| Add a dependency safely | tailtrail guard → read DEPENDENCY-GATE.md |
| Resume a previous plan | tailtrail start "task" --run-id <id> |
| Use full AIDLC lifecycle | tailtrail start "task" --aidlc standard |
```
This already partially exists as `CHEATSHEET.md` — but it needs to lead with problems, not commands.

#### 4.6 — Archive or hide `DESIGN.md` phase history
Move the Phase 1–10 history section of `DESIGN.md` to `context/design-history.md`. Keep `DESIGN.md` as current architecture only.

### Done criteria
- A new user can go from zero to `tailtrail start "fix my bug"` in under 5 minutes following only the README.
- README has ≤3 install commands visible at top level.
- `tailtrail onboard` exists and produces one copy-paste command.
- `CHEATSHEET.md` leads with user problems, not command names.

---

## 5. Install Experience — 4/10 → Target 8/10

### Current state (bugs seen directly)

1. `install codex-plugin --force` copies only `AGENTS.md`, `.codex-plugin/`, `skills/` — silently does NOT update the `tailtrail/` pack. Users think they've updated but haven't.
2. `SKILL.md` shipped with `python3 scripts/tailtrail.py` but launcher is at `tailtrail/scripts/tailtrail.py` — every `tailtrail start` from Codex silently fails.
3. Two separate update paths: `update-tailtrail.py` (for Copilot) and `install --force` (for others) with different behavior and no guidance on which to use.
4. No verification step after install — no "did this work?" confirmation.

### Root causes

1. `install_surfaces.py` defines what gets copied per profile but doesn't include the `tailtrail/` pack for the codex-plugin profile.
2. The SKILL.md launcher path was hardcoded from a source-checkout context, not an installed-pack context.
3. No post-install smoke test is run automatically.

### Specific changes needed

#### 5.1 — Fix `install_surfaces.py`: codex-plugin must include pack or document it doesn't
Two options — pick one:

**Option A (recommended):** Add a clear message after `install codex-plugin` that the TailTrail pack is separate:
```
Done. The Codex plugin files are installed.
NOTE: The TailTrail scripts pack (tailtrail/) is managed separately.
To update it: python3 scripts/update-tailtrail.py --root <target> --strategy backup-overwrite
```

**Option B:** Make `install codex-plugin --force` also update the pack when it exists.

#### 5.2 — Validate launcher path at install time
In `install-local.py` / `install_surfaces.py`, after copying SKILL.md:
```python
# Verify the launcher path that was written is actually reachable
target_launcher = target / "tailtrail" / "scripts" / "tailtrail.py"
fallback_launcher = target / "scripts" / "tailtrail.py"
if not target_launcher.exists() and not fallback_launcher.exists():
    print("WARNING: No TailTrail launcher found at tailtrail/scripts/tailtrail.py")
    print("         SKILL.md references this path. Run the pack install first.")
```

#### 5.3 — Post-install smoke test
After every install, automatically run:
```python
result = subprocess.run(
    [sys.executable, launcher_path, "hello"],
    cwd=target, capture_output=True, text=True
)
if result.returncode != 0 or "Installation check: passed" not in result.stdout:
    print("WARNING: TailTrail smoke test failed. Check the launcher path.")
    print(result.stderr)
else:
    print("Smoke test: passed ✓")
```

#### 5.4 — Single `tailtrail update` command
Replace the two separate update paths with one:
```bash
tailtrail update --root /path/to/project          # updates everything: pack + adapter files
tailtrail update --root /path/to/project --dry-run # preview
tailtrail update --root /path/to/project --pack-only    # only the scripts pack
tailtrail update --root /path/to/project --adapter-only # only AGENTS.md / SKILL.md / instructions
```
Internally delegate to `update-tailtrail.py` or `install_surfaces.py` as appropriate — but the user only needs to know one command.

#### 5.5 — Install verification command
```bash
tailtrail install verify --root /path/to/project
```
Checks:
- Launcher path matches what is in SKILL.md / AGENTS.md.
- Pack version matches source version.
- Smoke test passes.
- `.tailtrail-install.json` manifest is current.
- Prints a clear pass/fail per check.

### Done criteria
- `install codex-plugin --force` either updates the pack OR prints a clear instruction to update it separately.
- SKILL.md launcher path is verified at install time and never points to a nonexistent path.
- `tailtrail install verify` exists and catches the class of bugs we fixed manually.
- Post-install smoke test runs automatically for every install profile.

---

## 6. Reliability / Bug Density — 4/10 → Target 8/10

### Bugs found and fixed in one session (direct evidence)

| Bug | Impact | How found |
|---|---|---|
| `"use standard aidlc"` routed to lite mode | Core AIDLC feature silently broken | Manual run |
| SKILL.md had `scripts/tailtrail.py` (wrong path) | Every `tailtrail start` from Codex failed | Manual run |
| TailTrail's own files in impacted files list | Noise in every start report | Manual run |
| SyntaxError: backslash in f-string | Entire tool crashed | Error message |
| Impacted files truncated to 6 with hidden remainder | Users couldn't see all files | Code review |
| Planning Lock section had no blank line before Scope | Formatting broken | Visual inspection |

### Root causes

1. Changes are made and pushed without running the tool end-to-end.
2. The SKILL.md and AGENTS.md are not part of the install test — the install test only checks that files were copied, not that the content is correct.
3. f-string syntax was introduced in an environment (macOS Python 3.12) that allows it, but it fails on 3.11. No multi-version CI.

### Specific changes needed

#### 6.1 — End-to-end integration test
Add `tests/test_start_integration.py`:
```python
def test_start_with_standard_aidlc_routes_correctly(self):
    result = subprocess.run(
        [sys.executable, "scripts/tailtrail.py", "start",
         "use standard aidlc implement pipeline audit events", "--root", ROOT.as_posix()],
        cwd=ROOT, capture_output=True, text=True
    )
    self.assertEqual(result.returncode, 0)
    self.assertIn("standard", result.stdout.lower())
    self.assertNotIn("lite", result.stdout.lower().split("selected mode")[1][:50])

def test_start_output_has_all_required_sections(self):
    result = subprocess.run([...])
    for section in ["## Planning Lock", "## Scope", "## Requirements",
                    "## Selected TailTrail features", "## Plan", "## Approval"]:
        self.assertIn(section, result.stdout)

def test_no_tailtrail_files_in_impacted_files(self):
    # When run in the TailTrail repo itself, its own files should not appear
    result = subprocess.run([...])
    self.assertNotIn("skills/tailtrail-start", result.stdout)
    self.assertNotIn("AGENTS.md", result.stdout)
```

#### 6.2 — Python version matrix in CI
```yaml
# .github/workflows/tests.yml
strategy:
  matrix:
    python-version: ["3.11", "3.12", "3.13"]
```
This catches f-string syntax differences, `match` statement incompatibilities, and other version-specific issues.

#### 6.3 — Syntax check as part of every test run
```python
# tests/test_syntax.py — runs ast.parse on every script
import ast
from pathlib import Path

SCRIPTS = Path(__file__).parents[1] / "scripts"

class SyntaxTests(unittest.TestCase):
    def test_all_scripts_parse_cleanly(self):
        for path in sorted(SCRIPTS.glob("*.py")):
            with self.subTest(script=path.name):
                ast.parse(path.read_text(encoding="utf-8"))
```

#### 6.4 — SKILL.md / AGENTS.md content test
```python
# tests/test_install_content.py
def test_skill_md_references_correct_launcher_path(self):
    skill = (ROOT / "skills" / "tailtrail-start" / "SKILL.md").read_text()
    self.assertIn("tailtrail/scripts/tailtrail.py", skill)
    self.assertNotIn("python3 scripts/tailtrail.py start", skill)  # old wrong path
```

#### 6.5 — Lint gate
Add `ruff` or `flake8` to CI:
```yaml
- run: pip install ruff && ruff check scripts/ --select E,F,W --ignore E501
```
Catches undefined variables, unused imports, basic SyntaxErrors before they reach users.

### Done criteria
- CI runs on Python 3.11, 3.12, 3.13.
- All 150 scripts parse without SyntaxError (caught by `test_syntax.py`).
- `test_start_integration.py` covers the 6 bug classes listed above.
- `ruff` passes on `scripts/` with zero errors.
- No new bug of the type "core feature silently broken" reaches a user.

---

## 7. Maintainability — 4/10 → Target 7/10

### Current state

- Merge conflicts in 4 files from a single `git pull` — `navigator.py`, `task-start.py`, `skills/tailtrail-start/SKILL.md`, `skills/tailtrail-review/SKILL.md`.
- The same governance text appears word-for-word in `AGENTS.md`, `GUARDRAILS.md`, `copilot-instructions.md`, `adapters/copilot-instructions.md`, `skills/tailtrail-start/SKILL.md`, and `.github/copilot-instructions.md`.
- The `sync-governance.py` script exists but doesn't cover all the duplicate locations.
- `navigator.py` is 1973 lines. `task-start.py` is 1655 lines. Both are growing with every feature.

### Root causes

1. Copy-paste governance text — no single canonical source driving all adapter files.
2. No architecture rule preventing monolith growth — new features just get appended.
3. No process for detecting when a script exceeds a size threshold.

### Specific changes needed

#### 7.1 — Canonical governance block with enforced sync
The `<!-- tailtrail-governance:start / end -->` block already exists. Extend `sync-governance.py` to cover **all** files that contain governance text:
```python
GOVERNANCE_TARGETS = [
    "AGENTS.md",
    "GUARDRAILS.md",
    "adapters/copilot-instructions.md",
    "adapters/claude.md",
    "adapters/cursor.mdc",
    "adapters/gemini.md",
    "adapters/chatgpt-instructions.md",
    ".github/copilot-instructions.md",  # in target projects — generate on install
]
```
Add `tailtrail governance sync --check` that exits 1 if any target is out of sync.
Add this to CI:
```yaml
- run: python3 scripts/tailtrail.py governance sync --check
```

#### 7.2 — Split `navigator.py` into modules (no behavior change)
Current monolith responsibilities → proposed split:

| New file | Lines (est.) | Responsibility |
|---|:---:|---|
| `scripts/navigator_classify.py` | ~200 | `task_types()`, `risk_indicators()`, `is_tiny()`, keyword dicts |
| `scripts/navigator_discover.py` | ~300 | `goal_discovered_paths()`, `repository_discovered_paths()`, `git_changed()` |
| `scripts/navigator_features.py` | ~400 | All feature selection logic (AIDLC, review, CI, security, etc.) |
| `scripts/navigator_impacted.py` | ~150 | `is_actionable_changed_path()`, managed path filtering, dedup |
| `scripts/navigator_render.py` | existing | Already split out — keep as-is |
| `scripts/navigator_core.py` | existing | Already split out — keep as-is |
| `scripts/navigator.py` | ~200 | `decide()` + `main()` — thin orchestrator only |

Each module has its own test file. `navigator.py` imports and delegates — no logic in it.

#### 7.3 — Split `task-start.py` into modules

| New file | Lines (est.) | Responsibility |
|---|:---:|---|
| `scripts/start_aidlc.py` | ~150 | `_aidlc_intent()`, `aidlc_mode_selection()`, `_gather_aidlc_if_requested()` |
| `scripts/start_delivery.py` | ~200 | `guided_delivery()`, `hands_free_requirements()` |
| `scripts/start_posture.py` | ~150 | `token_posture()`, `learning_quality()`, `setup_posture()`, `review_posture()` |
| `scripts/start_report.py` | ~300 | `compact_start_report()`, `verbose_start_report()`, `render_markdown()` |
| `scripts/task-start.py` | ~100 | `build_report()` + `main()` — thin orchestrator only |

#### 7.4 — Script size guard in CI
```python
# tests/test_script_sizes.py
MAX_LINES = 800  # warn at 500, hard fail at 800

class ScriptSizeTests(unittest.TestCase):
    def test_no_script_exceeds_size_limit(self):
        for path in sorted((ROOT / "scripts").glob("*.py")):
            with self.subTest(script=path.name):
                lines = len(path.read_text().splitlines())
                self.assertLess(lines, MAX_LINES,
                    f"{path.name} is {lines} lines — split it into focused modules")
```

#### 7.5 — `CHANGELOG.md` discipline
Currently `CHANGELOG.md` exists but entries are sparse. Add a rule:
- Every PR that changes a `scripts/*.py` file must include a `CHANGELOG.md` entry.
- Format: `## [version] — date / - What changed and why`.
- `tailtrail install verify` checks that the installed pack version matches the CHANGELOG version.

### Done criteria
- `tailtrail governance sync --check` passes in CI with zero drift.
- `navigator.py` is under 300 lines (thin orchestrator only).
- `task-start.py` is under 200 lines (thin orchestrator only).
- No script in `scripts/` exceeds 800 lines (enforced by test).
- `CHANGELOG.md` has an entry for every version.

---

## 8. Code Quality — 5/10 → Target 8/10

### Current state

- The core scripts (`navigator.py`, `task-start.py`) are large monoliths that mix classification, feature selection, rendering, and I/O in one file.
- Large keyword dictionaries (risk keywords, UI path parts, stop words) are embedded inline with logic — makes them hard to update and impossible to test independently.
- Some functions are 50-100 lines with no sub-function decomposition.
- No type checking (no `mypy` or `pyright` configuration).
- f-string nesting bugs (fixed manually) suggest no linting.

### Root causes

1. Scripts grew incrementally — no architectural review when they crossed size thresholds.
2. No linting or type checking in the development workflow.

### Specific changes needed

#### 8.1 — Extract keyword dictionaries to data files
The large keyword dicts in `navigator_core.py` (risk keywords, UI parts, stop words) should move to `data/` as JSON:
```
data/risk-keywords.json
data/ui-path-parts.json
data/goal-discovery-stop-words.json
```
`navigator_core.py` loads them once at module import. Benefits: editable without touching Python, testable by loading and validating the JSON, mergeable without Python conflicts.

#### 8.2 — Add `mypy` type checking
```bash
pip install mypy
mypy scripts/navigator_core.py scripts/navigator.py scripts/task-start.py --ignore-missing-imports
```
Add to CI. The type annotations already exist — enforcing them catches bugs like passing `None` where a `str` is expected (the root of several silent failures we saw).

#### 8.3 — Add `ruff` linting
```bash
ruff check scripts/ --select E,F,W,N --ignore E501
```
This catches: undefined names, unused imports, inconsistent naming, obvious bugs.

#### 8.4 — Reduce function length
Any function over 50 lines should be decomposed. Specifically:
- `guided_delivery()` in `task-start.py` (~100 lines) → split into `_select_harnesses()` and `_defer_harnesses()`.
- `decide()` in `navigator.py` (~300 lines) → each feature selection block becomes a helper (`_select_aidlc()`, `_select_review()`, `_select_ci_sonar()`, etc.).
- `compact_start_report()` (~200 lines) → each section becomes `_render_planning_lock()`, `_render_scope()`, `_render_aidlc_questions()`, etc.

#### 8.5 — Remove dead/duplicate scripts
A manual audit is needed, but likely candidates:
- `context_receipt.py` and `context-receipt.py` (both exist — one is likely a rename artifact).
- `prompt_profile.py` and `prompt-profile.py` (same pattern).
- `token_budget_coach.py` and `token-budget-coach.py`.
- `token_telemetry.py` and `token-telemetry.py`.

Run:
```bash
ls scripts/*.py | sed 's/-/_/g' | sort | uniq -d
```
For each duplicate pair, consolidate to the hyphen-name version and update all imports.

### Done criteria
- `mypy` passes on `navigator_core.py`, `navigator.py`, `task-start.py` with zero errors.
- `ruff` passes on all `scripts/*.py` with zero errors.
- No function in the 5 core scripts exceeds 60 lines.
- Duplicate script pairs are resolved (zero duplicates found by the dedup check).

---

## 9. Documentation — 5/10 → Target 8/10

### Current state

- `DESIGN.md` is 709 lines of phase history written as user documentation.
- README leads with install options, not value proposition.
- The "start here" path is buried.
- `USER-GUIDE.md`, `QUICKSTART.md`, `CHEATSHEET.md`, `TAILTRAIL-COMMANDS.md`, `USEFUL-PROMPTS.md` all exist and overlap significantly.
- No separation between "user docs" and "contributor/internal docs".

### Root causes

1. Each phase added its own documentation section rather than updating the existing docs.
2. No doc ownership — everything lives at the root level with equal prominence.

### Specific changes needed

#### 9.1 — Two-folder doc structure
```
docs/
  user/
    README.md          ← the new README (replaces current)
    QUICKSTART.md      ← 5-minute path to first result
    CHEATSHEET.md      ← problem → command, one page
    INSTALL.md         ← all platform/profile variants
    ENFORCEMENT.md     ← new (from improvement #2)
  contributor/
    DESIGN.md          ← architecture + history (moved from root)
    CONTRIBUTING.md
    CHANGELOG.md
    VERSIONING.md
    HONEST-REVIEW.md   ← this review + improvement plan
    IMPROVEMENT-PLAN.md ← this file
```
Keep `AGENTS.md`, `GUARDRAILS.md`, `DEPENDENCY-GATE.md`, `AIDLC.md` at root — they are loaded by agents and must stay at root level.

#### 9.2 — README rewrite (outcomes-first)
```markdown
# TailTrail

Stop your AI coding agent from hallucinating tests, removing safeguards, and
adding packages it doesn't need.

[one sentence: how it works]
[one sentence: what you get]

## Get started in 2 minutes
[single install command]
[single first task command]
[screenshot or ASCII output of a real start report]

## What TailTrail prevents
- AI claiming "tests passed" without running them
- Silent removal of auth/validation code
- Casual new dependencies without review
- Multi-file changes drifting from the original requirement

[links to deeper docs]
```

#### 9.3 — Archive phase history
Move the Phase 1–10 narrative from `DESIGN.md` into `docs/contributor/design-history.md`. Replace `DESIGN.md` with current architecture only (modules, data flow, extension points).

#### 9.4 — Consolidate overlapping docs
| Keep | Archive/merge |
|---|---|
| `CHEATSHEET.md` (rewritten) | `USEFUL-PROMPTS.md` → merge into CHEATSHEET |
| `QUICKSTART.md` | `USER-GUIDE.md` → merge long-form content here |
| `TAILTRAIL-COMMANDS.md` | Keep as-is (comprehensive reference) |

#### 9.5 — Version the docs
Add a `docs/` frontmatter to each user-facing doc:
```markdown
---
updated: 2026-08-16
tailtrail-version: "≥ 0.6.0"
---
```
So users know if docs match their installed version.

### Done criteria
- New user follows README to first `tailtrail start` output in under 5 minutes.
- Phase history is no longer in user-facing docs.
- Zero content duplication between `QUICKSTART.md` and `USER-GUIDE.md`.
- `docs/` folder structure exists and is linked from README.

---

## Implementation Order (Recommended)

### Sprint 1 — Fix the foundation (P0)
1. `tests/test_syntax.py` — catch SyntaxErrors before users do
2. `tests/test_aidlc_mode_selection.py` — prevent AIDLC routing regressions
3. `tests/test_navigator_impacted_files.py` — prevent TailTrail files appearing in plans
4. `pytest.ini` + GitHub Actions CI on Python 3.11/3.12/3.13
5. Install verification: fix SKILL.md path check, add post-install smoke test
6. `tests/test_install_content.py` — catch wrong launcher paths at test time

### Sprint 2 — Enforcement and reliability (P0/P1)
1. `hooks/pre-commit-dependency-gate.py`
2. `hooks/pre-commit-validation-truth.py`
3. `tailtrail guard --staged` wired to exit code
4. `ruff` + `mypy` in CI
5. End-to-end integration tests for `tailtrail start`

### Sprint 3 — Refactoring (P1)
1. Split `navigator.py` into 5 modules
2. Split `task-start.py` into 5 modules
3. Extract keyword dicts to `data/` JSON
4. Script size guard in CI
5. Deduplicate `context_receipt.py` / `prompt_profile.py` etc.

### Sprint 4 — Documentation and onboarding (P2)
1. README rewrite (outcomes-first)
2. `tailtrail onboard` wizard
3. `CHEATSHEET.md` rewrite (problem-first)
4. Archive phase history to `docs/contributor/`
5. `docs/` folder structure

### Sprint 5 — Efficacy evidence (P1, ongoing)
1. `benchmarks/reference-project/` with 5 scenarios
2. `benchmarks/results/` with committed, scored outputs
3. `PUBLIC-CLAIMS.md` scorecard update
4. `tailtrail benchmark run-public` command

---

## Release 5 — Evidence implementation

Release 5 now has an honest two-layer evidence boundary:

- `benchmarks/public/` contains five committed, sanitized `fixture-scored`
  scenarios for dependency decisions, validation/caller proof, API contracts,
  bounded refactoring, and static-analysis remediation.
- `tailtrail benchmark run-public` evaluates only saved artifacts. It makes no
  model or network call and is not live-model performance evidence.
- `tailtrail benchmark capture-model-run ... --approved` records an opt-in,
  provenance-only real-run record. It requires consent and rejects raw prompt,
  response, source, repository/path, and secret fields. The saved record keeps
  SHA-256 artifact identities, provider/model metadata, and supplied telemetry
  only.
- Complete supplied before/after token totals are labelled
  `benchmark-measured`; otherwise the result is `model-run-unmeasured`. No
  real model-run result or numeric efficacy claim is committed by default.

## Success Metrics

After all sprints, the following must be true:

| Metric | Target |
|---|---|
| `pytest tests/` on Python 3.11 | 0 failures |
| `ruff check scripts/` | 0 errors |
| `mypy` on 3 core scripts | 0 errors |
| `tailtrail governance sync --check` | passes |
| Lines in `navigator.py` | < 300 |
| Lines in `task-start.py` | < 200 |
| Time from zero to first `tailtrail start` output | < 5 minutes |
| Bugs found by users before tests | 0 (regression target) |
| Public benchmark scenarios | ≥ 5, scored, committed |

