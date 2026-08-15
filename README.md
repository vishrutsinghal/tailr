<p align="center">
  <img src="assets/tailtrail-mark.png" width="150" alt="TailTrail logo" />
</p>

<h1 align="center">TailTrail</h1>

<p align="center">
  <strong>Plan first. Change with evidence. Finish without drift.</strong>
</p>

TailTrail is a local, approval-first workflow for AI-assisted software delivery. It helps coding agents understand the existing project, plan the smallest useful change, validate the real code path, and keep multi-file work aligned with the requirement.

It works with GitHub Copilot, Codex, Claude, Cursor, ChatGPT, and Gemini. Start small; TailTrail selects deeper checks only when the task needs them.

## Start here

1. Clone or download this repository.
2. Install TailTrail into the project where you want to work.
3. Verify the installation.
4. Ask for a plan before approving implementation.

```text
tailtrail start "fix the claim amount validation bug"
```

TailTrail returns a plan and a run ID. It does **not** implement the task until you approve that plan.

## Install TailTrail

Run the command from the root of this TailTrail repository. Replace the target path with the project you want TailTrail to guide.

### Windows (recommended)

GitHub Copilot:

```powershell
py -3 scripts\tailtrail.py install local --target "D:\path\to\your-project" --profile copilot
```

Codex plugin:

```powershell
py -3 scripts\tailtrail.py install codex-plugin --target "D:\path\to\your-project"
```

Claude:

```powershell
py -3 scripts\tailtrail.py install local --target "D:\path\to\your-project" --profile claude
```

### macOS / Linux

Use the same command with `python3` and forward-slash paths:

```bash
python3 scripts/tailtrail.py install local --target "/absolute/path/to/your-project" --profile copilot
```

Codex plugin on macOS:

```bash
python3 scripts/tailtrail.py install codex-plugin --target "/absolute/path/to/your-project"
```

This installs the project-local `AGENTS.md`, `.codex-plugin/plugin.json`, and
TailTrail skills. Open the target project in Codex, then start a new chat so
Codex loads the installed guidance.

### Update an existing installation

For an existing **GitHub Copilot** installation, use the updater. It reads the
installed manifest, refreshes the managed TailTrail pack and Copilot
instructions, and preserves locally edited managed files by default:

```powershell
# Preview first
py -3 scripts\update-tailtrail.py --root "D:\path\to\your-project" --dry-run

# Apply the safe, preserve-local-edits update
py -3 scripts\update-tailtrail.py --root "D:\path\to\your-project"
```

If you deliberately want the current TailTrail version to replace modified
managed files, keep recoverable backups with:

```powershell
py -3 scripts\update-tailtrail.py --root "D:\path\to\your-project" --strategy backup-overwrite
```

`install local` without `--force` is a **first-install** command: it leaves
existing managed files in place. `install local ... --force` can refresh a
profile, but it may overwrite its managed files. Use it for Codex or Claude
only after reviewing any local customizations; use the updater above for the
safe Copilot refresh path.

For an existing **Codex plugin** installation on macOS/Linux, preview the
refresh first, then apply it. The Codex plugin is refreshed through the
installer rather than the Copilot-only updater:

```bash
# Preview the Codex plugin refresh
python3 scripts/tailtrail.py install codex-plugin --target "/absolute/path/to/your-project" --dry-run

# Refresh TailTrail's Codex-managed files
python3 scripts/tailtrail.py install codex-plugin --target "/absolute/path/to/your-project" --force
```

`--force` replaces TailTrail-managed Codex files such as `AGENTS.md`, the
plugin manifest, and installed skills. Back up or commit local edits to those
files before applying it. It does not update your project source code.

After installing or updating, open a **new chat** in your AI host so it reads the refreshed instructions.

> GitHub Copilot reads the generated instructions from your project root, for example `.github/copilot-instructions.md`. The local `tailtrail/` folder is the installed runtime pack. Keep it local unless you intentionally want to share the pack with the repository.

### Optional: Full official AI-DLC workflow for Codex

TailTrail Lite and Standard modes are self-contained. Full mode is optional and
uses a **pinned, integrity-checked** AWS AI-DLC release. Install the pack, then
project it into the official Codex rule layout without replacing your existing
TailTrail guidance:

```powershell
py -3 scripts\tailtrail.py aidlc official install --root "D:\path\to\your-project" --host codex
py -3 scripts\tailtrail.py aidlc official host install --root "D:\path\to\your-project" --host codex
py -3 scripts\tailtrail.py aidlc official host status --root "D:\path\to\your-project" --host codex
```

The projection is conditional: Codex loads the exact official workflow only
for an explicit approved `--aidlc full` run. It does not make ordinary
TailTrail Start requests heavier. Runtime conformance remains
`not-validated` until real host receipts are recorded.

## Verify the installation

From the project that received the installed pack:

```powershell
py -3 tailtrail\scripts\tailtrail.py hello
py -3 tailtrail\scripts\tailtrail.py doctor
```

On macOS/Linux, use:

```bash
python3 tailtrail/scripts/tailtrail.py hello
python3 tailtrail/scripts/tailtrail.py doctor
```

You can also type `tailtrail hello` in a new Copilot, Codex, or Claude chat. A healthy installation returns the TailTrail ASCII banner and its installation result.

If Python is not found on Windows, install Python 3 from python.org and make sure the `py` launcher is available. Then repeat the Windows command above.

## Your normal workflow

### 1. Ask TailTrail to plan

In your assistant chat:

```text
tailtrail start "add payment retry handling"
```

For Copilot, `/tailtrail-start add payment retry handling` is also a convenient entry point when the installed prompt is available.

TailTrail inspects relevant context and returns a Planning Lock with the likely scope, requirements, selected checks, and next approval action.

### 2. Review and approve

Correct the plan if needed, then approve the specific run ID. For a larger project, ask for a `hands-free` or `end-to-end` plan; TailTrail will first break the work into ordered, reviewable slices.

### 3. Implement and validate

After approval, the agent follows the approved scope and collects focused evidence. Depending on the task, TailTrail can use requirement completion, architecture, behaviour, maintainability, test, continuity, and recovery checks.

### 4. Read the completion report

At the end, the report brings together requirement status, changed scope, evidence, unresolved drift, and recovery availability. Pasting a failure into the same chat is treated as follow-up evidence for the active run—not as a new task.

## What TailTrail adds

| Capability | Why it matters |
| --- | --- |
| Navigator | Turns an ambiguous request into a scoped, approval-first plan. |
| Requirement Completion Harness | Maps requirements to code, tests, evidence, and completion status. |
| Architecture and Behaviour Harnesses | Catches missed callers, wrong-layer changes, and flows that unit tests alone do not prove. |
| Evidence-aware testing | Chooses proportionate focused, integration, or release evidence without claiming checks that did not run. |
| Context Continuity | Keeps the active requirement, prior mistakes, and next correction focused across iterations. |
| Safe recovery | Uses bounded checkpoints and Git readiness to protect unrelated work. |
| MCP tools | Makes TailTrail decisions and receipts inspectable across supported hosts. |

## Intent Bridge for existing requirements

Use **Intent Bridge** when your team already has structured feature
requirements, design decisions, tasks, or contracts and you want TailTrail to
deliver against them without creating a competing set of documents. TailTrail
keeps the original source authoritative; it stores only normalized references,
fingerprints, mappings, evidence, and approval history locally.

```powershell
# Inspect compatible requirement artifacts without writing files
py -3 scripts\tailtrail.py intent-bridge detect --root "D:\path\to\your-project"

# Import one explicitly selected feature into local TailTrail state
py -3 scripts\tailtrail.py intent-bridge import --root "D:\path\to\your-project" --feature 014-order-amendment --mode planning

# Use that approved source in a normal Planning Lock
py -3 scripts\tailtrail.py start "Use Intent Bridge feature 014-order-amendment to plan order amendments" --intent-feature 014-order-amendment
```

After approval, TailTrail maps the imported requirements to code scope and
proof, works one approved slice at a time, and detects any later source change
as an amendment. It does not rewrite the original requirements, call external
systems, or claim CI/release success without a saved receipt.

## Useful commands

From this source checkout:

```powershell
# Plan only
py -3 scripts\tailtrail.py start "fix zero claim amounts" --changed src/claims_api/validation.py

# Inspect the code graph
py -3 scripts\tailtrail.py graph --root "D:\path\to\your-project" --changed src/claims_api/validation.py

# Check the installation and local setup
py -3 scripts\tailtrail.py doctor
```

Use `python3 scripts/tailtrail.py ...` on macOS/Linux. See the [command reference](TAILTRAIL-COMMANDS.md) for every command and option.

## Learn more when you need it

- [Quick start](QUICKSTART.md) and [User guide](USER-GUIDE.md)
- [Assistant compatibility](ASSISTANT-COMPATIBILITY.md)
- [TailTrail commands](TAILTRAIL-COMMANDS.md)
- [Harness Engineering](harness-engineering.md) and the [end-to-end workflow](harness-engineering-workflow.md)
- [Evidence-aware testing](testing-confidence.md)
- [TailTrail MCP](tailtrail-mcp.md) and [MCP implementation guide](tailtrail-mcp-learning-guide.md)
- [AIDLC](AIDLC.md) for broad, risky, or lifecycle-heavy work
- Intent Bridge: use `tailtrail intent-bridge detect` when a project already has a structured requirement source
- [Roadmap](ROADMAP.md) and [implementation backlog](tailtrail-implementation-backlog.md)

## Development and validation

TailTrail is designed to be local-first and explicit about evidence. Plans do not edit code; tests, scans, Git actions, and approvals are only reported when they actually ran.

To contribute or validate this repository, begin with [CONTRIBUTING.md](CONTRIBUTING.md), then run the checks described in the [release checklist](RELEASE-CHECKLIST.md).

---

Created by **Vishrut Singhal**.
