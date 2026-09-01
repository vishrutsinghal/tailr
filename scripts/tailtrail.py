#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if SCRIPTS.as_posix() not in sys.path:
    sys.path.insert(0, SCRIPTS.as_posix())

from install_surfaces import CORE_CONTEXT, CORE_FILES, CORE_SCRIPTS, CORE_TEMPLATES
import navigator_core

PYTHON = sys.executable

COMMANDS = {
    "help": "Show the main TailTrail command surface.",
    "commands": "Print the detailed command catalog.",
    "hello": "Confirm TailTrail is installed and reachable.",
    "version": "Show source/pack location.",
    "package-info": "Show installed package mode and verified resource status.",
    "start": "Start a task with Navigator-first plan, metrics, setup posture, and learning quality.",
    "planning": "Create, inspect, discuss, revise, approve, or enforce a Planning Lock for one run.",
    "do": "Alias for start; run Navigator-first planning for a free-form task.",
    "run": "Alias for start; run Navigator-first planning for a free-form task.",
    "next": "Recommend one deterministic next action after a Start report.",
    "guide": "Preview the future Navigator entry point for a user goal.",
    "navigator": "Use the short TailTrail Navigator context, plan, or implementation-proposal modes.",
    "ledger": "Create, append, validate, or project local Phase 1 run state.",
    "failure": "Record or inspect sanitized post-implementation failure artifacts.",
    "debug": "Debug Harness: turn a symptom into a proven root cause (Code/Architecture/Database/API-integration domains only).",
    "anchor": "Draft, approve, invalidate, or review a local change-intent anchor.",
    "intent": "Expand a short TailTrail prompt through expand-intent.py.",
    "expand": "Alias for intent.",
    "route": "Choose a token-saving context route through route-context.py.",
    "token": "Decide whether token routing is useful through token-auto.py.",
    "token-harness": "Classify, reduce, prove, and optionally bridge safe Token Harness context.",
    "budget": "Estimate, record, and learn local token budgets through Token Budget Coach.",
    "profile": "Show prompt compression profiles for focused TailTrail context loading.",
    "receipt": "Capture or summarize context receipts for local token evidence.",
    "telemetry": "Create normalized measured token telemetry without API calls.",
    "savings": "Estimate or report token savings with explicit evidence labels.",
    "report": "Generate a local TailTrail enterprise report.",
    "release-check": "Run public release readiness checks.",
    "setup-scan": "Classify TailTrail files in a cloned or existing repo.",
    "target": "Resolve one editable target workspace before planning.",
    "reference": "Plan safe read-only cross-repo reference usage.",
    "intent-bridge": "Inspect, import, and prove delivery against an existing structured requirement source.",
    "graph": "Generate Code Review Graph Lite, scanner overlays, AST maps, or manage Code Graph Mapper cache.",
    "ci": "Summarize CI/build/test output.",
    "sonar": "Summarize Sonar/static-analysis output.",
    "validation": "Combine CI and Sonar evidence into a validation handoff.",
    "quality": "Recommend or run approved local quality checks.",
    "review": "Review uncommitted, branch, path, or full-repo scope with guarded fix guidance.",
    "test": "Plan precise tests and focused validation for a repo change.",
    "quality-loop": "Capture and review TailTrail workflow quality signals.",
    "outcome": "Capture and summarize local TailTrail adoption outcomes.",
    "harness": "Review local TailTrail workflow fit and metric confidence.",
    "completion-report": "Create the required end-of-task TailTrail Completion Report for one approved run.",
    "closure": "Validate, record, finalize, or route bounded correction for closure evidence.",
    "bootstrap": "Create or inspect a safe pre-task repo/runtime snapshot.",
    "ui": "Discover existing local UI conventions for a consistent UI change.",
    "mcp": "Run the opt-in read-only TailTrail MCP server tools.",
    "vulnerability": "Summarize, plan, or run approved vulnerability scans.",
    "engine": "Run V2.7 evidence-based engine helpers.",
    "aidlc": "Run AIDLC init/check helpers.",
    "benchmark": "Run local benchmarks, public fixture evidence, or sanitized model-run capture.",
    "efficacy": "Run BL-1 measured-efficacy runner with strict measured/estimate labels.",
    "analyze": "Run analyze-benchmark.py.",
    "eval": "Audit and later run the Evaluation Harness umbrella.",
    "doctor": "Run source or installed-pack validation checks.",
    "guard": "Run local guardrail checks against a diff or staged changes.",
    "guardrail": "Run guardrail checks and precision baselines.",
    "dependency": "Validate structured Dependency Gate decisions against a diff.",
    "enforce": "Run versioned repository and CI policy enforcement with JSON/SARIF output.",
    "governance": "Check or sync repeated governance text.",
    "registry": "Inspect and validate the TailTrail feature registry.",
    "maturity": "Inspect or validate product-maturity baselines, ownership, and controls.",
    "presentation": "Validate or render canonical reports and run PM-3 host presentation conformance.",
    "flow": "Use the PM-2 start, discuss, approve, continue, status, and close façade.",
    "discuss": "Discuss one awaiting TailTrail plan from saved evidence.",
    "approve": "Approve the active plan or exact next durable stage.",
    "continue": "Advance one dependency-ready durable workflow stage.",
    "close": "Finalize closure and show evidence-backed acceptance choices.",
    "enterprise-readiness": "Inspect and validate the enterprise stabilization baseline and closure registry.",
    "policy": "Initialize or validate local TailTrail policy files.",
    "install": "Install a host profile through the transactional lifecycle.",
    "setup": "Detect or select a host, install/update it, verify it, and show reload guidance.",
    "verify": "Verify manifest-owned host files.",
    "status": "Show installed host lifecycle status.",
    "rollback": "Restore a prior installer transaction.",
    "uninstall": "Safely remove manifest-owned host files.",
    "repair": "Repair missing or corrupt managed host files transactionally.",
    "recover": "Recover an interrupted installer transaction.",
    "first-run": "Verify a local TailTrail install and show one simple first action.",
    "update": "Update installed project payloads from the current TailTrail package.",
    "upgrade": "Verify a local release wheel, upgrade the package, and update installed project payloads.",
    "release": "Show trusted release discovery and verification metadata.",
    "qualify": "Aggregate instruction, real-host, platform, and publication evidence.",
    "team-init": "Run team-init.py.",
    "adapters": "Check or sync assistant adapter files and required adapter behavior.",
    "learn": "Use Learning V3 capture, retrieval, use receipts, closure attribution, governance, migration, and compatibility commands.",
    "learnings": "Alias for learn.",
    "admin": "Run admin-only release packaging commands.",
}


def admin_mode_enabled() -> bool:
    return os.environ.get("TAILTRAIL_ADMIN", "").lower() in {"1", "true", "yes", "on"}


def public_release_enabled() -> bool:
    return (ROOT / ".tailtrail-public-release").exists()


def release_check_allowed() -> bool:
    return admin_mode_enabled() or public_release_enabled()


def internal_release_enabled() -> bool:
    return (ROOT / ".tailtrail-internal-release").exists()


def packaged_runtime_enabled() -> bool:
    return (ROOT / "package-integrity.json").is_file()


def invocation() -> str:
    command_name = os.environ.get("TAILTRAIL_COMMAND_NAME")
    if command_name:
        return command_name
    return f"python3 {Path(sys.argv[0]).as_posix()}"


def warn_if_stale_checkout() -> None:
    """Best-effort notice when an installed launcher runs a different, stale
    TailTrail checkout than the one under the current directory. Only fires
    when invoked through a generated launcher/wrapper (TAILTRAIL_COMMAND_NAME
    is set); silent for direct `python3 scripts/tailtrail.py` runs and tests."""
    if not os.environ.get("TAILTRAIL_COMMAND_NAME"):
        return
    try:
        here = Path(__file__).resolve()
        cwd = Path.cwd()
        for candidate in (cwd, *cwd.parents):
            local_entry = candidate / "scripts" / "tailtrail.py"
            if local_entry.is_file() and local_entry.resolve() != here:
                print(
                    f"TailTrail note: `{invocation()}` runs {here}, but {local_entry.resolve()} "
                    "is a different TailTrail checkout under the current directory. If output looks "
                    "out of date, run that checkout directly (python3 scripts/tailtrail.py ...) or "
                    "refresh this launcher: python3 scripts/install-launcher.py --force",
                    file=sys.stderr,
                )
                return
    except OSError:
        return


def quiet_enabled(args: list[str] | None = None) -> bool:
    if os.environ.get("TAILTRAIL_QUIET", "").lower() in {"1", "true", "yes", "on"}:
        return True
    return bool(args and "--quiet" in args)


def strip_wrapper_flags(args: list[str]) -> list[str]:
    return [item for item in args if item not in {"--quiet", "--debug", "--build"}]


def json_output_requested(args: list[str]) -> bool:
    for index, value in enumerate(args):
        if value == "--format" and index + 1 < len(args) and args[index + 1] == "json":
            return True
        if value == "--format=json":
            return True
    return False


def startup_banner_lines(columns: int | None = None) -> list[str]:
    """Render a terminal-safe banner without assuming the host panel width."""
    feature_rows = (
        "PLAN     Navigator | AIDLC | Intent Bridge",
        "MAP      Code Graph | Req Map | UI Guard",
        "VERIFY   Req | Arch | Behaviour | Maintain",
        "DEBUG    Repro | Causes | Evidence | Fix",
        "CONTROL  Workflow | Recovery | Closure",
        "IMPROVE  Tokens | Learn | Eval | MCP",
    )
    if columns is None:
        configured = os.environ.get("TAILTRAIL_BANNER_WIDTH", "").strip()
        if configured.isdigit():
            columns = int(configured)
        elif sys.stdout.isatty():
            columns = shutil.get_terminal_size(fallback=(48, 24)).columns
        else:
            # Captured output is commonly pasted into a narrower chat panel.
            columns = 46
    # Category rows remain single-line. Markdown-fenced Start output scrolls on
    # panels narrower than this minimum instead of reflowing the ASCII design.
    outer_width = max(46, min(int(columns), 72))
    content_width = outer_width - 4
    rendered_rows = ["TAILTRAIL"]
    description_words = "Requirement completion and drift control for AI-assisted delivery".split()
    description_line = ""
    for word in description_words:
        candidate = f"{description_line} {word}".strip()
        if description_line and len(candidate) > content_width:
            rendered_rows.append(description_line)
            description_line = word
        else:
            description_line = candidate
    rendered_rows.extend([description_line, "", *feature_rows])
    border = "+" + ("-" * (outer_width - 2)) + "+"
    return [border, *(f"| {row.ljust(content_width)} |" for row in rendered_rows), border]


def print_startup_banner(markdown_fence: bool = False) -> None:
    if markdown_fence:
        print("```text")
    for line in startup_banner_lines():
        print(line)
    if markdown_fence:
        print("```")
    print("")


def script(name: str) -> Path:
    return SCRIPTS / name


def run_script(name: str, args: list[str]) -> int:
    command = [PYTHON, script(name).as_posix(), *args]
    capture = os.environ.get("TAILTRAIL_JSON_ENVELOPE_CAPTURE") == "1"
    result = subprocess.run(command, cwd=Path.cwd(), check=False, text=capture, stdout=subprocess.PIPE if capture else None, stderr=subprocess.PIPE if capture else None)
    if capture:
        if result.stdout:
            print(result.stdout, end="")
        if result.stderr:
            print(result.stderr, end="", file=sys.stderr)
    return result.returncode


def print_help() -> None:
    command = invocation()
    print("TailTrail command surface")
    print("")
    print("Usage:")
    print(f"  {command} <command> [args]")
    print("")
    print("Common commands:")
    command_names = [
        "hello",
        "start",
        "do",
        "next",
        "guide",
        "graph",
        "ci",
        "sonar",
        "validation",
        "quality",
        "review",
        "test",
        "quality-loop",
        "outcome",
        "harness",
        "bootstrap",
        "mcp",
        "vulnerability",
        "engine",
        "intent",
        "route",
        "token",
        "budget",
        "profile",
        "receipt",
        "telemetry",
        "savings",
        "report",
        "setup-scan",
        "target",
        "reference",
        "aidlc",
        "benchmark",
        "efficacy",
        "analyze",
        "eval",
        "doctor",
        "guard",
        "guardrail",
        "dependency",
        "governance",
        "registry",
        "policy",
        "install",
        "update",
        "team-init",
        "learn",
    ]
    if release_check_allowed():
        command_names.insert(command_names.index("setup-scan"), "release-check")
    if admin_mode_enabled():
        command_names.append("admin")
    for name in command_names:
        print(f"  {name:<10} {COMMANDS[name]}")
    print("")
    print("Examples:")
    print(f"  {command} hello")
    print(f'  {command} start "fix Sonar issue and prepare PR"')
    print(f'  {command} do "fix Sonar issue and prepare PR"')
    print(f'  {command} "fix Sonar issue and prepare PR"')
    print(f"  {command} next")
    print(f'  {command} start "fix Sonar issue and prepare PR" --verbose')
    print(f'  {command} guide "fix Sonar issue and prepare PR"')
    print(f"  {command} graph --changed src/service/foo.py")
    print(f"  {command} graph ast --changed src/service/foo.py --depth v1")
    print(f"  {command} graph ast --changed src/service/foo.py --depth v2")
    print(f"  {command} graph ast --changed src/service/foo.py --depth v3 --provider-output tailtrail-meta/providers/semantic.json --approved")
    print(f"  {command} graph overlay --sonar sonar.log --changed src/service/foo.py")
    print(f"  {command} graph overlay --vulnerability audit.log --changed package.json")
    print(f"  {command} graph map --changed src/service/foo.py")
    print(f"  {command} graph status --changed src/service/foo.py")
    print(f"  {command} ci summarize --file ci.log")
    print(f"  {command} sonar summarize --file sonar.log")
    print(f"  {command} validation summarize --ci ci.log --sonar sonar.log")
    print(f"  {command} quality scan --changed src/service/foo.py")
    print(f'  {command} quality run --approved --command "npm run lint"')
    print(f"  {command} review")
    print(f"  {command} review --scope branch --base main")
    print(f"  {command} review --scope path --dir services/payment")
    print(f"  {command} test plan --changed src/service/foo.py")
    print(f'  {command} test plan --changed src/service/foo.py --goal "fix validation bug"')
    print(f"  {command} test summarize --changed src/service/foo.py")
    print(f'  {command} quality-loop capture --workflow review,qa --fit correct --outcome accepted --approved')
    print(f"  {command} quality-loop review --month 2026-07")
    print(f'  {command} outcome capture --task-type bug-fix --workflow start,review --acceptance accepted --validation-outcome pass --approved')
    print(f"  {command} outcome summarize --month 2026-07")
    print(f"  {command} harness quick --root .")
    print(f"  {command} harness review --root . --write-result")
    print(f"  {command} harness confidence --root .")
    print(f"  {command} harness recommendations --root .")
    print(f"  {command} harness export-summary --root . --write-result")
    print(f"  {command} harness shared-summary --root . --dry-run")
    print(f"  {command} harness shared-summary --root . --write-result --approved")
    print(f"  {command} harness shared-status --root .")
    print(f"  {command} harness shared-sanitize --root .")
    print(f"  {command} bootstrap snapshot --root .")
    print(f"  {command} bootstrap snapshot --root . --write-result")
    print(f"  {command} bootstrap status --root .")
    print(f"  {command} ui discover --root . --changed src/components/Example.tsx")
    print(f"  {command} bootstrap refresh --root .")
    print(f"  {command} harness aggregate-shared --root . --format markdown")
    print(f"  {command} harness aggregate-shared --roots ../repo-a --roots ../repo-b")
    print(f"  {command} harness analyze --summary tailtrail-meta/harness-summary.jsonl")
    print(f"  {command} harness readiness --root .")
    print(f"  {command} harness readiness --roots ../repo-a --roots ../repo-b")
    print(f"  {command} harness propose --root . --proposal-id MH-2026-07-001")
    print(f"  {command} harness proposal-status --root .")
    print(f"  {command} harness proposal-record --root . --proposal-id MH-2026-07-001 --status accepted")
    print(f"  {command} mcp tools")
    print(f"  {command} mcp doctor")
    print(f"  {command} mcp serve")
    print(f"  {command} vulnerability scan --changed package.json")
    print(f"  {command} vulnerability summarize --file audit.log")
    print(f"  {command} engine summarize-output --file build.log")
    print(f"  {command} engine slice-context --file src/service/foo.py --query validate")
    print(f"  {command} engine cache-summary")
    print(f"  {command} engine prune-context --file noisy-context.md")
    print(f"  {command} learn review --root .")
    print(f"  {command} learn govern --root .")
    print(f'  {command} intent "use AIDLC and review"')
    print(f"  {command} route review")
    print(f"  {command} token-harness route --path src/app.py")
    print(f"  {command} token-harness reduce --path report.sarif")
    print(f"  {command} token-harness reduce --path src/app.py --mode structure")
    print(f"  {command} token-harness reduce --path report.sarif --write-receipt --approved")
    print(f"  {command} token route --path report.sarif --format json")
    print(f"  {command} token-harness ledger append --event-type route_decision --task-type bug-fix --content-type source --strategy exact-pass-through --exactness-class must-be-exact --tokens-before 1200 --tokens-after 1200 --evidence-label local-evidence --approved")
    print(f"  {command} token-harness ledger summary")
    print(f"  {command} token-harness ledger validate")
    print(f"  {command} token-harness proof report")
    print(f"  {command} token-harness proof holdout --task-id TASK-123 --task-class bug-fix")
    print(f"  {command} token-harness bridge plan --path build.log")
    print(f"  {command} token-harness bridge input --path build.log --output /tmp/bridge-input.json")
    print(f"  {command} token-harness bridge validate-output --input /tmp/bridge-input.json --output /tmp/bridge-output.json")
    print(f'  {command} token-harness bridge run --path build.log --adapter-command "local-compressor --stdin" --approved')
    print(f'  {command} budget estimate "fix validation bug" --changed src/service/foo.py')
    print(f'  {command} budget record --task-type bug --initial-budget 8000 --actual-context 10500 --outcome underestimated --approved')
    print(f"  {command} budget profile")
    print(f"  {command} profile review")
    print(f'  {command} receipt capture --task "fix validation bug" --profile review --loaded src/service/foo.py --avoided ROADMAP.md --approved')
    print(f'  {command} receipt capture --task "fix Sonar issue" --loaded src/App.java --loaded-exactness must-be-exact --loaded-strategy exact-pass-through --preserve "line numbers" --approved')
    print(f"  {command} receipt summary")
    print(f"  {command} receipt retrieve --path src/App.java")
    print(f'  {command} telemetry manual --task-id demo-001 --provider openai --model gpt-5 --baseline-input 42000 --baseline-output 3000 --tailtrail-input 18000 --tailtrail-output 2500')
    print(f"  {command} telemetry import-openai --source openai-usage.jsonl --output .tailtrail/token-usage.jsonl")
    print(f"  {command} telemetry import-claude --source claude-usage.jsonl --output .tailtrail/token-usage.jsonl")
    print(f"  {command} telemetry import-gemini --source gemini-usage.jsonl --output .tailtrail/token-usage.jsonl")
    print(f"  {command} savings estimate --used context/slices.md --avoided ROADMAP.md USER-GUIDE.md")
    print(f"  {command} savings import --source usage.jsonl --output .tailtrail/token-usage.jsonl")
    print(f"  {command} report --month 2026-07")
    print(f"  {command} report value --month 2026-07")
    print(f"  {command} report trend")
    print(f"  {command} report pr --only quality --only tokens")
    print(f"  {command} guardrail precision")
    print(f"  {command} guardrail precision --strict --format json")
    print(f"  {command} guardrail precision --rule dependency-gate")
    print(f"  {command} dependency check --diff changes.patch")
    if release_check_allowed():
        print(f"  {command} release-check")
    if admin_mode_enabled():
        print(f"  {command} admin export --mode internal --target /tmp/tailtrail-internal --force")
        print(f"  {command} admin export --mode public --target /tmp/tailtrail-public --force")
    print(f"  {command} setup-scan --root .")
    print(f"  {command} reference --target /path/to/service-a --reference /path/to/service-b --goal \"match validation style\"")
    print(f"  {command} guard check")
    print(f"  {command} guard check --enforce")
    print(f"  {command} guard check --fail-on dependency-gate,local-state")
    print(f"  {command} governance check")
    print(f"  {command} governance check --strict")
    print(f"  {command} governance inventory")
    print(f"  {command} registry list")
    print(f"  {command} registry show meta-harness")
    print(f"  {command} registry surfaces")
    print(f"  {command} registry workflow review")
    print(f"  {command} registry mcp --format json")
    print(f"  {command} registry validate --strict")
    print(f"  {command} registry drift")
    print(f"  {command} enterprise-readiness validate")
    print(f"  {command} enterprise-readiness status")
    print(f"  {command} enterprise-readiness inventory --format json")
    print(f"  {command} adapters check")
    print(f"  {command} adapters sync")
    print(f"  {command} policy check --root .")
    print(f"  {command} install launcher --dry-run")
    print(f"  {command} install codex --target /path/to/project --dry-run")
    print(f"  {command} install codex --target /path/to/project")
    print(f"  {command} install codex-plugin --target /path/to/project --dry-run")
    print(f"  {command} install codex-plugin --target /path/to/project")
    print(f"  {command} install copilot --surface core")
    print(f"  {command} install local --surface core --profile copilot")
    print(f"  {command} install upgrade-to-extended")
    print(f"  {command} install status")
    print(f"  {command} aidlc init --root . --depth standard")
    print(f"  {command} benchmark efficacy")
    print(f"  {command} efficacy run")
    print(f"  {command} efficacy run --scenario governance-remediation")
    print(f"  {command} efficacy run --portfolio")
    print(f"  {command} efficacy run --strict --format json")
    print(f"  {command} eval audit")
    print(f"  {command} eval audit --strict")
    print(f"  {command} eval audit --write-report --approved")
    print(f"  {command} doctor")
    print("")
    print(f"Run `{command} commands` for the detailed catalog.")


def print_commands() -> int:
    catalog = ROOT / "TAILTRAIL-COMMANDS.md"
    if catalog.is_file():
        print(catalog.read_text(encoding="utf-8"), end="")
        return 0
    print_help()
    return 0


def print_version() -> int:
    manifest = ROOT / ".tailtrail-install.json"
    print("TailTrail")
    print(f"Location: {ROOT}")
    if manifest.is_file():
        print(f"Install manifest: {manifest}")
    else:
        print("Install manifest: not present")
    return 0


def package_info(args: list[str]) -> int:
    packaged = packaged_runtime_enabled()
    manifest = ROOT / "package-manifest.json"
    valid = manifest.is_file()
    payload = {
        "type": "tailtrail-package-status",
        "mode": "installed-package" if packaged else "source-compatibility",
        "root": ROOT.as_posix(),
        "valid": valid,
        "issues": [] if valid else ["missing package-manifest.json"],
    }
    if json_output_requested(args):
        print(json.dumps(payload, sort_keys=True))
    else:
        print(f"TailTrail package {'passed' if valid else 'failed'}.")
        print(f"Mode: {payload['mode']}")
        print(f"Package root: {ROOT}")
    return 0 if valid else 1


def hello() -> int:
    manifest = ROOT / ".tailtrail-install.json"
    mode = "installed package" if packaged_runtime_enabled() else "installed pack" if manifest.is_file() else "source checkout"
    if not quiet_enabled(sys.argv[2:]):
        # Chat hosts capture stdout and render it as Markdown. Preserve the
        # banner's fixed-width layout there while keeping an interactive
        # terminal free of literal Markdown fence markers.
        print_startup_banner(markdown_fence=not sys.stdout.isatty())
    print("Hello from TailTrail.")
    print("Installation check: passed")
    print(f"Mode: {mode}")
    print(f"Location: {ROOT}")
    print(f"Command: {invocation()}")
    print("Next check: run `tailtrail doctor` for full validation.")
    return 0


def guide(args: list[str]) -> int:
    if not args:
        print('Usage: tailtrail guide "your goal" [--changed path/to/file]')
        return 2
    return run_script("navigator.py", [*args, "--command-prefix", invocation()])


def navigator(args: list[str]) -> int:
    if not args:
        print('Usage: tailtrail navigator [context|plan|implement] "your scope" [--changed path/to/file]')
        return 2
    mode = "context"
    if args[0] in {"context", "plan", "implement"}:
        mode, args = args[0], args[1:]
    if not args:
        print(f'Usage: tailtrail navigator {mode} "your scope" [--changed path/to/file]')
        return 2
    flag_index = next((index for index, value in enumerate(args) if value.startswith("--")), len(args))
    goal = f"TailTrail Navigator {mode} " + " ".join(args[:flag_index])
    return run_script("navigator.py", [goal, *args[flag_index:], "--command-prefix", invocation()])


def print_start_overview() -> None:
    print("# TailTrail Start")
    print()
    print("TailTrail turns a coding request into a focused, approval-first workflow.")
    print()
    print("## Main Feature Groups")
    print()
    print("- Navigator: plans the next safe step before implementation.")
    print("- Code Graph: maps relevant symbols, callers, and focused tests.")
    print("- Guardrails and policy: preserve validation, dependency, and safety rules.")
    print("- AIDLC, Intent Bridge, and Interactive Plan: clarify and approve requirements.")
    print("- Completion, Architecture, Behaviour, and Maintainability Harnesses: verify intent and drift.")
    print("- Debug Harness: controls reproduction, hypotheses, experiments, and bounded correction.")
    print("- Durable Workflow, recovery, and closure: preserve resumable state and evidence.")
    print("- Test Precision, CI/Sonar, security, and UI Consistency: guide focused validation when approved.")
    print("- Token tools: keep context lean and label estimates honestly.")
    print("- Learning, MCP, handoff, value reports, Meta-Harness, and Evaluation Harness: preserve and expose useful evidence.")
    print()
    print("## Start A Task")
    print()
    print('tailtrail start "your goal" --changed path/to/file')
    print()
    print("Example:")
    print('tailtrail start "fix the claim amount validation bug" --changed src/claims_api/validation.py --verbose')
    print()
    print("Start is plan-only. It does not edit code until you approve the plan.")
    print()
    print("A goal that reports a symptom rather than a requirement (\"orders")
    print("double-charge on timeout\") is routed to the Debug Harness instead of")
    print("the normal build workflow. Force one or the other with --debug / --build.")


def classify_start_intent(goal: str, args: list[str]) -> str:
    """Compatibility projection of Navigator's canonical typed decision."""
    override = "debug" if "--debug" in args else "build" if "--build" in args else None
    decision = navigator_core.classify_workflow_intent(
        goal,
        override=override,
        has_error_artifact="--error" in args,
        has_reproduction_command="--command" in args,
    )
    return "debug" if decision.workflow_type == "debug-investigation" else "build"


def filter_debug_forward_args(args: list[str]) -> list[str]:
    """Keep only the goal text and the flags debug-intake.py understands;
    silently drop build-only flags (--changed, --verbose, --debug, --build)
    rather than letting them fail argparse in the Debug Harness scripts."""
    allowed_value_flags = {"--error", "--command", "--run-id", "--root"}
    allowed_flags = {"--attach"}
    kept: list[str] = []
    skip_next = False
    for index, value in enumerate(args):
        if skip_next:
            skip_next = False
            continue
        if value in allowed_value_flags:
            kept.append(value)
            if index + 1 < len(args):
                kept.append(args[index + 1])
                skip_next = True
            continue
        if value in allowed_flags:
            kept.append(value)
            continue
        if value.startswith("--"):
            # Unrecognized (build-only) flag: drop it, and drop its value too
            # unless the next token is itself a flag (e.g. --verbose).
            if index + 1 < len(args) and not args[index + 1].startswith("--"):
                skip_next = True
            continue
        kept.append(value)
    return kept


def start(args: list[str]) -> int:
    if not args:
        print_startup_banner(markdown_fence=True)
        print_start_overview()
        return 0
    goal = next((value for value in args if not value.startswith("--")), "")
    if not quiet_enabled(args) and not json_output_requested(args):
        print_startup_banner(markdown_fence=True)
        # The delegated Start process writes directly to the same stream.
        # Flush first so redirected/Copilot/Codex output cannot place the
        # parent banner after the child report.
        sys.stdout.flush()
    # Start always delegates to the canonical Planning Lock renderer. Navigator
    # inside task-start owns build/debug classification; Debug Intake is a later
    # approved transition, never a Start side effect.
    forwarded = [item for item in args if item != "--quiet"]
    return run_script("orchestration_facade.py", ["start", *forwarded, "--command-prefix", invocation()])


def doctor(args: list[str] | None = None) -> int:
    if args:
        return run_script("installer.py", ["doctor", *args])
    if packaged_runtime_enabled():
        package_manifest_path = ROOT / "package-manifest.json"
        try:
            package_manifest = json.loads(package_manifest_path.read_text(encoding="utf-8"))
            required = package_manifest["runtime_required"]
            if not isinstance(required, list) or not all(isinstance(item, str) for item in required):
                raise ValueError("runtime_required must be a list of paths")
        except (OSError, json.JSONDecodeError, KeyError, ValueError) as error:
            print("TailTrail installed-package doctor failed.")
            print(f"Package manifest error: {error}")
            return 1
        missing = [item for item in required if not (ROOT / item).exists()]
        if missing:
            print("TailTrail installed-package doctor failed.")
            print("Missing:")
            for item in missing:
                print(f"- {item}")
            return 1
        print("TailTrail installed-package doctor passed.")
        print(f"Package location: {ROOT}")
        return 0

    if internal_release_enabled() or not (ROOT / ".codex-plugin").exists():
        manifest_path = ROOT / ".tailtrail-install.json"
        surface = "extended"
        if manifest_path.exists():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                manifest = {}
            if isinstance(manifest, dict) and manifest.get("surface") == "core":
                surface = "core"
        extended_required = [
            "AGENTS.md",
            "AIDLC.md",
            "DEPENDENCY-GATE.md",
            "EVALUATION-HARNESS.md",
            "GUARDRAILS.md",
            "GOVERNANCE.md",
            "MCP-SERVER.md",
            "TAILTRAIL-COMMANDS.md",
            "tailtrail-registry.json",
            "tailtrail-registry.schema.json",
            "USEFUL-PROMPTS.md",
            "USER-GUIDE.md",
            "scripts/tailtrail.py",
            "scripts/planning-lock.py",
            "scripts/tailtrail-registry.py",
            "scripts/task-next.py",
            "scripts/ast-map.py",
            "scripts/setup-scan.py",
            "scripts/cross-repo-reference.py",
            "scripts/code-graph-mapper.py",
            "scripts/efficacy-benchmark.py",
            "scripts/efficacy-run.py",
            "scripts/evaluation-audit.py",
            "scripts/evaluation-harness.py",
            "scripts/adoption-validation.py",
            "scripts/review-graph.py",
            "scripts/ci-summary.py",
            "scripts/sonar-summary.py",
            "scripts/validation-summary.py",
            "scripts/quality-scan.py",
            "scripts/review-run.py",
            "scripts/test-precision.py",
            "scripts/quality-run.py",
            "scripts/quality-loop.py",
            "scripts/outcome-telemetry.py",
            "scripts/harness-review.py",
            "scripts/bootstrap-snapshot.py",
            "scripts/vulnerability-summary.py",
            "scripts/vulnerability-scan.py",
            "scripts/vulnerability-run.py",
            "scripts/summarize-output.py",
            "scripts/slice-context.py",
            "scripts/cache-summary.py",
            "scripts/prune-context.py",
            "scripts/graph-learning.py",
            "scripts/guardrail-check.py",
            "scripts/guardrail-precision.py",
            "scripts/learning-agent.py",
            "scripts/learning-v3.py",
            "scripts/learning-retrieval.py",
            "scripts/learning-use-receipt.py",
            "scripts/learning-governance.py",
            "scripts/learning-calibration.py",
            "scripts/learning-review.py",
            "scripts/learning-refresh.py",
            "scripts/learnings.py",
            "scripts/mcp-server.py",
            "scripts/expand-intent.py",
            "scripts/route-context.py",
            "scripts/navigator_core.py",
            "scripts/navigator_render.py",
            "scripts/policy-check.py",
            "scripts/sync-governance.py",
            "scripts/install-launcher.py",
            "scripts/install_surfaces.py",
            "scripts/tailtrail-report.py",
            "scripts/token-telemetry.py",
            "scripts/token_telemetry.py",
            "hooks/learning-capture-hook.py",
        ]
        core_required = sorted(
            {
                *CORE_FILES,
                *CORE_CONTEXT,
                *CORE_TEMPLATES,
                *CORE_SCRIPTS,
                ".tailtrail-install.json",
                "adapters/chatgpt-instructions.md",
                "adapters/claude.md",
                "adapters/copilot-instructions.md",
                "adapters/cursor.mdc",
                "adapters/gemini.md",
            }
        )
        required = core_required if surface == "core" else extended_required
        missing = [item for item in required if not (ROOT / item).exists()]
        if missing:
            print("TailTrail installed-pack doctor failed.")
            print("Missing:")
            for item in missing:
                print(f"- {item}")
            return 1
        print("TailTrail installed-pack doctor passed.")
        print(f"Surface: {surface}")
        print(f"Pack location: {ROOT}")
        return 0

    checks = [
        ("sync-governance.py", ["check"]),
        ("check-tailtrail.py", []),
        ("sync-adapters.py", ["--check"]),
    ]
    for name, args in checks:
        print(f"Running {name} {' '.join(args)}".rstrip(), flush=True)
        code = run_script(name, args)
        if code != 0:
            return code
    print("TailTrail doctor passed.")
    return 0


def aidlc(args: list[str]) -> int:
    if not args:
        print("Usage: tailtrail aidlc init|check|official [args]")
        return 2
    action, rest = args[0], args[1:]
    if action == "init":
        return run_script("aidlc-init.py", rest)
    if action == "check":
        return run_script("aidlc-check.py", rest)
    if action == "official":
        if rest[:1] == ["install"]:
            return run_script("aidlc-official-install.py", rest[1:])
        if rest[:1] == ["host"]:
            return run_script("aidlc-official-host.py", rest[1:])
        if rest[:1] == ["sanitize"]:
            return run_script("official-aidlc-sanitize.py", rest[1:])
        if rest[:1] == ["state"]:
            return run_script("official-aidlc-state.py", rest[1:])
        if rest[:1] == ["runtime"]:
            return run_script("official-aidlc-runtime.py", rest[1:])
        if rest[:1] == ["bridge"]:
            return run_script("aidlc-official-bridge.py", rest[1:])
        if rest[:1] == ["checkpoint"]:
            return run_script("official-aidlc-checkpoint.py", rest[1:])
        return run_script("aidlc-official-detect.py", rest)
    print("Unknown aidlc action. Use: init, check, or official")
    return 2


def debug(args: list[str]) -> int:
    if not args:
        print("Usage: tailtrail debug \"<symptom>\" [--error <file>] [--command \"<cmd>\"] [--run-id <id>] [--attach]")
        print("       tailtrail debug reproduction draft|revise|approve|reject|show ...")
        print("       tailtrail debug orientation create|show ...")
        print("       tailtrail debug hypothesis add|reprioritize|propose|experiment|replan|prove|domain-status|show ...")
        print("       tailtrail debug correction propose|approve|show ...")
        print("       tailtrail debug convergence select|finalize|show ...")
        print("       tailtrail debug governance build|show ...")
        print("       tailtrail debug evaluation catalog|run|report|release-gate ...")
        print("       tailtrail debug completion-report generate|show ...  # debug section; canonical closure remains authoritative")
        return 2
    action, rest = args[0], strip_wrapper_flags(args[1:])
    if action == "reproduction":
        return run_script("debug-reproduction.py", rest)
    if action == "orientation":
        return run_script("debug-orientation.py", rest)
    if action == "hypothesis":
        return run_script("debug-hypothesis.py", rest)
    if action == "correction":
        return run_script("debug-correction.py", rest)
    if action == "convergence":
        return run_script("debug-harness-convergence.py", rest)
    if action == "governance":
        return run_script("debug-governance.py", rest)
    if action == "evaluation":
        return run_script("debug-evaluation.py", rest)
    if action == "completion-report":
        return run_script("debug-completion.py", rest)
    if action in {"open", "show"}:
        return run_script("debug-intake.py", strip_wrapper_flags(args))
    return run_script("debug-intake.py", ["open", "--symptom", action, *rest])


def install(args: list[str]) -> int:
    if not args:
        print("Usage: tailtrail install --host codex|copilot|claude --profile core|extended --target <path> [--dry-run]")
        return 2
    action, rest = args[0], args[1:]
    if action in {"codex", "codex-plugin", "copilot", "claude"}:
        host = "codex" if action == "codex-plugin" else action
        return run_script("installer.py", ["install", "--host", host, *rest])
    if action == "local":
        return run_script("install-local.py", rest)
    if action == "launcher":
        return run_script("install-launcher.py", rest)
    if action == "verify":
        # Read-only compatibility for pre-E3 projected packs. Canonical E3
        # verification is the top-level `tailtrail verify --host ...` command.
        return run_script("first-run.py", rest)
    if action == "upgrade-to-extended":
        return run_script("installer.py", ["update", "--host", "all", "--profile", "extended", *rest])
    if action.startswith("--"):
        return run_script("installer.py", ["install", *args])
    print("Unknown install action. Use --host codex|copilot|claude, or a compatibility host alias.")
    return 2


def summarize_command(command_name: str, script_name: str, args: list[str]) -> int:
    if not args or args[0] != "summarize":
        print(f"Usage: tailtrail {command_name} summarize [args]")
        return 2
    return run_script(script_name, args[1:])


def quality(args: list[str]) -> int:
    if not args:
        print("Usage: tailtrail quality scan|run [args]")
        return 2
    action, rest = args[0], args[1:]
    if action == "scan":
        return run_script("quality-scan.py", rest)
    if action == "run":
        return run_script("quality-run.py", rest)
    print("Unknown quality action. Use: scan or run")
    return 2


def test(args: list[str]) -> int:
    if not args:
        print("Usage: tailtrail test plan|summarize [args]")
        return 2
    action, rest = args[0], args[1:]
    if action in {"plan", "summarize"}:
        return run_script("test-precision.py", [action, *rest])
    print("Unknown test action. Use: plan or summarize")
    return 2


def review(args: list[str]) -> int:
    return run_script("review-run.py", args)


def vulnerability(args: list[str]) -> int:
    if not args:
        print("Usage: tailtrail vulnerability summarize|scan|run [args]")
        return 2
    action, rest = args[0], args[1:]
    if action == "summarize":
        return run_script("vulnerability-summary.py", rest)
    if action == "scan":
        return run_script("vulnerability-scan.py", rest)
    if action == "run":
        return run_script("vulnerability-run.py", rest)
    print("Unknown vulnerability action. Use: summarize, scan, or run")
    return 2


def graph(args: list[str]) -> int:
    if args and args[0] == "ast":
        return run_script("ast-map.py", args[1:])
    if args and args[0] == "overlay":
        return run_script("scanner-graph-overlay.py", args[1:])
    if args and args[0] in {"map", "status", "refresh"}:
        return run_script("code-graph-mapper.py", args)
    return run_script("review-graph.py", args)


def engine(args: list[str]) -> int:
    if not args:
        print("Usage: tailtrail engine summarize-output|slice-context|cache-summary|prune-context [args]")
        return 2
    action, rest = args[0], args[1:]
    if action == "summarize-output":
        return run_script("summarize-output.py", rest)
    if action == "slice-context":
        return run_script("slice-context.py", rest)
    if action == "cache-summary":
        return run_script("cache-summary.py", rest)
    if action == "prune-context":
        return run_script("prune-context.py", rest)
    print("Unknown engine action. Use: summarize-output, slice-context, cache-summary, or prune-context")
    return 2


def learn(args: list[str]) -> int:
    if args and args[0] == "v3":
        return run_script("learning-v3.py", args[1:])
    if args and args[0] == "retrieve":
        return run_script("learning-retrieval.py", args[1:])
    if args and args[0] == "receipt":
        return run_script("learning-use-receipt.py", args[1:])
    if args and args[0] == "governance":
        return run_script("learning-governance.py", args[1:])
    if args and args[0] in {"calibrate", "calibration"}:
        return run_script("learning-calibration.py", args[1:])
    if args and args[0] == "graph":
        return run_script("graph-learning.py", args[1:])
    if args and args[0] == "refresh":
        return run_script("learning-refresh.py", args[1:])
    if args and args[0] in {"review", "govern"}:
        return run_script("learning-review.py", args[1:])
    if args and args[0] in {"capture", "score", "search", "promote", "summarize", "prune", "rebuild-index"}:
        return run_script("learning-agent.py", args)
    if args and args[0] == "agent":
        return run_script("learning-agent.py", args[1:])
    return run_script("learnings.py", args)


def guard(args: list[str]) -> int:
    if not args:
        print("Usage: tailtrail guard check|precision [args]")
        return 2
    action, rest = args[0], args[1:]
    if action == "check":
        has_explicit_diff = any(item == "--diff" or item.startswith("--diff=") for item in rest)
        if not has_explicit_diff and not (Path.cwd() / ".git").exists():
            return run_script("guardrail-check.py", ["--diff", "/dev/null", *rest])
        return run_script("guardrail-check.py", rest)
    if action == "precision":
        return run_script("guardrail-precision.py", rest)
    print("Unknown guard action. Use: check or precision")
    return 2


def guardrail(args: list[str]) -> int:
    if not args:
        print("Usage: tailtrail guardrail precision|check [args]")
        return 2
    action, rest = args[0], args[1:]
    if action == "precision":
        return run_script("guardrail-precision.py", rest)
    if action == "check":
        return run_script("guardrail-check.py", rest)
    print("Unknown guardrail action. Use: precision or check")
    return 2


def dependency(args: list[str]) -> int:
    if not args:
        print("Usage: tailtrail dependency validate|check [args]")
        return 2
    return run_script("dependency-decision.py", args)


def enforce(args: list[str]) -> int:
    if not args or args[0] not in {"validate", "check", "migrate"}:
        print("Usage: tailtrail enforce validate|check|migrate [args]")
        return 2
    return run_script("repository-enforcement.py", args)


def admin(args: list[str]) -> int:
    if not admin_mode_enabled():
        print("admin commands are not available in this TailTrail distribution.")
        return 2
    if not args:
        print("Usage: tailtrail admin export --mode internal|public --target /path [--force|--list]")
        return 2
    action, rest = args[0], args[1:]
    if action == "export":
        return run_script("export-release.py", rest)
    print("Unknown admin action. Use: export")
    return 2


def benchmark(args: list[str]) -> int:
    if args and args[0] == "run-public":
        return run_script("public-benchmark.py", ["run", *args[1:]])
    if args and args[0] == "capture-model-run":
        return run_script("public-benchmark.py", ["capture", *args[1:]])
    if args and args[0] == "report-public":
        return run_script("public-benchmark.py", ["report", *args[1:]])
    if args and args[0] == "model-runs":
        return run_script("public-benchmark.py", ["model-runs", *args[1:]])
    if args and args[0] == "public":
        return run_script("public-benchmark.py", args[1:])
    if args and args[0] == "efficacy":
        return run_script("efficacy-benchmark.py", args[1:])
    return run_script("benchmark-tailtrail.py", args)


def efficacy(args: list[str]) -> int:
    if not args:
        print("Usage: tailtrail efficacy run|report [args]")
        return 2
    action, rest = args[0], args[1:]
    if action in {"run", "report"}:
        return run_script("efficacy-run.py", rest)
    print("Unknown efficacy action. Use: run or report")
    return 2


def harness(args: list[str]) -> int:
    if args and args[0] == "git-readiness":
        return run_script("git-readiness.py", args[1:])
    if args and args[0] == "boundary":
        return run_script("task-recovery-boundary.py", args[1:])
    if args and args[0] == "recovery":
        return run_script("task-recovery.py", args[1:])
    if args and args[0] == "reconcile":
        return run_script("recovery-reconcile.py", args[1:])
    if args and args[0] == "mode-b":
        return run_script("requirement-recovery-manifest.py", args[1:])
    if args and args[0] == "diagnose":
        return run_script("recovery-diagnostician.py", args)
    if args and args[0] == "program":
        return run_script("program-plan.py", args[1:])
    if args and args[0] == "program-checkpoint":
        return run_script("program-checkpoint.py", args[1:])
    if args and args[0] == "orchestrate":
        return run_script("delivery-orchestrator.py", args[1:])
    if args and args[0] == "architecture":
        return run_script("architecture-fitness.py", args[1:])
    if args and args[0] == "behavior":
        return run_script("behavior-harness.py", args[1:])
    if args and args[0] == "maintainability":
        return run_script("maintainability-harness.py", args[1:])
    if args and args[0] == "higher-tier":
        return run_script("higher-tier-testing.py", args[1:])
    if args and args[0] == "release-confidence":
        return run_script("release-confidence.py", args[1:])
    if args and args[0] in {"plan", "check"}:
        return run_script("harness-controls.py", args)
    if args and args[0] == "checkpoint":
        return run_script("harness-checkpoint.py", args[1:])
    if args and args[0] == "completion-review":
        return run_script("completion-review.py", args[1:])
    if args and args[0] == "completion-report":
        return run_script("completion-report.py", args[1:])
    if args and args[0] == "dashboard":
        return run_script("workflow-dashboard.py", args[1:])
    if args and args[0] == "feedback":
        return run_script("harness-feedback.py", args[1:])
    if args and args[0] == "impact-map":
        return run_script("requirement-impact-map.py", args[1:])
    if args and args[0] == "converge":
        return run_script("harness-convergence.py", args[1:])
    if args and args[0] == "template":
        return run_script("harness-template.py", args[1:])
    if args and args[0] == "tier-select":
        return run_script("test-tier-selector.py", args[1:])
    if args and args[0] == "ci-ingest":
        return run_script("ci-evidence-ingest.py", args[1:])
    if args and args[0] == "flaky":
        return run_script("flaky-test-tracker.py", args[1:])
    if args and args[0] == "evidence-metrics":
        return run_script("evidence-metrics.py", args[1:])
    if args and args[0] == "phase8":
        return run_script("phase8-advanced.py", args[1:])
    if args and args[0] == "advanced":
        return run_script("advanced-runtime.py", args[1:])
    if args and args[0] == "continuity":
        return run_script("context-continuity.py", args[1:])
    if args and args[0] in {"testing-profile", "validation-receipt", "requirement-completion"}:
        scripts = {"testing-profile": "testing-profile.py", "validation-receipt": "validation-receipt.py", "requirement-completion": "requirement-completion.py"}
        return run_script(scripts[args[0]], args[1:])
    if args and args[0] in {"aggregate-shared", "analyze", "readiness"}:
        return run_script("meta-harness-analyze.py", args)
    if args and args[0] == "propose":
        return run_script("meta-harness-propose.py", args)
    if args and args[0] == "proposal-status":
        return run_script("meta-harness-propose.py", ["status", *args[1:]])
    if args and args[0] == "proposal-record":
        return run_script("meta-harness-propose.py", ["record", *args[1:]])
    return run_script("harness-review.py", args)


def closure(args: list[str]) -> int:
    if not args or args[0] not in {"validate", "record", "finalize", "correct", "learn", "evaluate", "close"}:
        print("Usage: tailtrail closure validate|record|finalize|correct|learn|evaluate|close --root . [--run-id <run-id>] [--input closure-input.json]")
        return 2
    scripts = {"validate": "closure-contract.py", "record": "closure-recorder.py", "finalize": "closure-finalizer.py", "correct": "closure-correction.py", "learn": "closure-learning.py", "evaluate": "closure-evaluation.py", "close": "closure-close.py"}
    return run_script(scripts[args[0]], args[1:])


def bootstrap(args: list[str]) -> int:
    if not args:
        print("Usage: tailtrail bootstrap snapshot|status|refresh [args]")
        return 2
    return run_script("bootstrap-snapshot.py", args)


def mcp(args: list[str]) -> int:
    if not args:
        print("Usage: tailtrail mcp serve|tools|doctor [args]")
        return 2
    action, rest = args[0], args[1:]
    if action in {"serve", "tools", "doctor"}:
        return run_script("mcp-server.py", [action, *rest])
    print("Unknown mcp action. Use: serve, tools, or doctor")
    return 2


def workflow(args: list[str]) -> int:
    if not args or args[0] not in {"bind", "show", "validate", "capabilities", "task", "storage", "state", "compile", "approvals", "evidence", "vertical", "adapters", "stage-results", "execute", "freshness", "retry", "resume", "correction", "context", "outcomes", "ci", "assurance", "retention", "release", "enterprise"}:
        print("Usage: tailtrail workflow bind|show|validate|capabilities|task|storage|state|compile|approvals|evidence|vertical|adapters|stage-results|execute|freshness|retry|resume|correction|context|outcomes|ci|assurance|retention|release|enterprise --root . [--run-id <run-id>] [--workflow-id <workflow-id>]")
        return 2
    return run_script("workflow-runtime.py", args)


def registry(args: list[str]) -> int:
    if not args:
        print("Usage: tailtrail registry list|show|surfaces|validate [args]")
        return 2
    return run_script("tailtrail-registry.py", args)


def spec_kit(args: list[str]) -> int:
    if not args or args[0] in {"--help", "-h"}:
        print("Usage: tailtrail intent-bridge detect|status|inspect|import|bridge|slices|evidence|amendment|converge|ci-ingest|ci-gate|observe|release|governance|evaluate|policy [args]")
        return 0 if args else 2
    if args[0] == "policy":
        return run_script("spec-kit-policy.py", args[1:])
    if args[0] in {"detect", "status", "inspect"}:
        return run_script("spec-kit-detect.py", args)
    if args[0] == "import":
        return run_script("spec-kit-import.py", args[1:])
    if args[0] == "bridge":
        return run_script("spec-kit-bridge.py", args[1:])
    if args[0] == "slices":
        return run_script("spec-kit-slices.py", args[1:])
    if args[0] == "evidence":
        return run_script("spec-kit-evidence.py", args[1:])
    if args[0] == "amendment":
        return run_script("spec-kit-amendment.py", args[1:])
    if args[0] == "converge":
        return run_script("spec-kit-converge.py", args[1:])
    if args[0] == "ci-ingest":
        return run_script("spec-kit-integration.py", args[1:])
    if args[0] == "ci-gate":
        return run_script("spec-kit-ci-gate.py", args[1:])
    if args[0] in {"observe", "release", "governance", "evaluate"}:
        return run_script("spec-kit-observability.py", ["report" if args[0] == "observe" else args[0], *args[1:]])
    print("Use: tailtrail intent-bridge detect|status|inspect|import|bridge|slices|evidence|amendment|converge|ci-ingest|ci-gate|observe|release|governance|evaluate|policy")
    return 2


def token(args: list[str]) -> int:
    if args and args[0] == "route":
        return run_script("token-harness.py", args)
    return run_script("token-auto.py", args)


def evaluation(args: list[str]) -> int:
    if args and args[0] in {"learning", "learning-calibration"}:
        return run_script("learning-calibration.py", args[1:])
    return run_script("evaluation-harness.py", args)


def adapters(args: list[str]) -> int:
    action = args[0] if args else "check"
    rest = args[1:] if args else []
    if action == "check":
        return run_script("sync-adapters.py", ["--check", *rest])
    if action == "sync":
        return run_script("sync-adapters.py", ["--write", *rest])
    if action == "conformance":
        return run_script("host-adapter-conformance.py", rest)
    if action == "runtime":
        return run_script("host-runtime-conformance.py", rest)
    print("Usage: tailtrail adapters check|sync|conformance|runtime")
    return 2


def main() -> int:
    warn_if_stale_checkout()
    if len(sys.argv) < 2 or sys.argv[1] in {"help", "-h", "--help"}:
        print_help()
        return 0

    command = sys.argv[1]
    args = sys.argv[2:]

    if command == "commands":
        return print_commands()
    if command in {"hello", "hi", "ping"}:
        return hello()
    if command == "version":
        return print_version()
    if command == "package-info":
        return package_info(args)
    if command in {"start", "do", "run"}:
        return start(args)
    if command == "flow":
        if args[:1] == ["start"]:
            return start(args[1:])
        return run_script("orchestration_facade.py", args)
    if command == "presentation":
        return run_script("presentation.py", args)
    if command in {"discuss", "approve", "continue", "close"}:
        return run_script("orchestration_facade.py", [command, *args])
    if command == "planning":
        if args and args[0] == "question-context":
            return run_script("question-orchestrator.py", ["show", *args[1:]])
        if args and args[0] == "aidlc-question":
            return run_script("planning-aidlc-question.py", args[1:])
        if args and args[0] in {"discuss", "explain", "discussion-show", "decision-show"}:
            return run_script("planning-discussion.py", args)
        if args and args[0] in {"investigate", "investigation-show"}:
            investigation_args = ["investigate", *args[1:]] if args[0] == "investigate" else ["show", *args[1:]]
            return run_script("planning-investigation.py", investigation_args)
        if args and args[0] in {"revise", "revision-show", "revision-approve", "authority-show", "aidlc-standard", "aidlc-standard-approve", "feature-controls-show", "feature-controls-propose", "feature-controls-approve"}:
            revision_args = (
                ["propose", *args[1:]] if args[0] == "revise"
                else ["show", *args[1:]] if args[0] == "revision-show"
                else ["authority-show", *args[1:]] if args[0] == "authority-show"
                else ["aidlc-standard", *args[1:]] if args[0] == "aidlc-standard"
                else ["aidlc-standard-approve", *args[1:]] if args[0] == "aidlc-standard-approve"
                else ["approve", *args[1:]]
            )
            if args[0].startswith("feature-controls-"):
                control_args = ["show", *args[1:]] if args[0] == "feature-controls-show" else ["propose", *args[1:]] if args[0] == "feature-controls-propose" else ["approve", *args[1:]]
                return run_script("planning-feature-controls.py", control_args)
            return run_script("planning-revision.py", revision_args)
        return run_script("planning-lock.py", args)
    if command == "next":
        return run_script("task-next.py", [*strip_wrapper_flags(args), "--command-prefix", invocation()])
    if command == "guide":
        return guide(args)
    if command == "navigator":
        return navigator(args)
    if command == "ledger":
        return run_script("run-ledger.py", args)
    if command == "failure":
        return run_script("execution-failure.py", args)
    if command == "debug":
        return debug(args)
    if command == "execution-evidence":
        return run_script("execution-evidence.py", strip_wrapper_flags(args))
    if command == "anchor":
        return run_script("change-intent-anchor.py", args)
    if command in {"intent", "expand"}:
        return run_script("expand-intent.py", args)
    if command == "route":
        return run_script("route-context.py", args)
    if command == "token":
        return token(args)
    if command == "token-harness":
        return run_script("token-harness.py", args)
    if command == "budget":
        return run_script("token-budget-coach.py", args)
    if command == "profile":
        return run_script("prompt-profile.py", args)
    if command == "receipt":
        return run_script("context-receipt.py", args)
    if command == "telemetry":
        return run_script("token-telemetry.py", args)
    if command == "savings":
        return run_script("token-savings.py", args)
    if command == "report":
        return run_script("tailtrail-report.py", args)
    if command == "release-check":
        if not release_check_allowed():
            print("release-check is not available in this TailTrail distribution.")
            print("This command is reserved for admin/public-release packaging.")
            return 2
        return run_script("release-check.py", args)
    if command == "admin":
        return admin(args)
    if command == "setup-scan":
        return run_script("setup-scan.py", args)
    if command == "target":
        return run_script("target_workspace.py", args)
    if command == "reference":
        return run_script("cross-repo-reference.py", args)
    if command in {"intent-bridge", "spec-kit"}:
        return spec_kit(args)
    if command == "graph":
        return graph(args)
    if command == "ci":
        return summarize_command("ci", "ci-summary.py", args)
    if command == "sonar":
        return summarize_command("sonar", "sonar-summary.py", args)
    if command == "validation":
        return summarize_command("validation", "validation-summary.py", args)
    if command == "quality":
        return quality(args)
    if command == "review":
        return review(args)
    if command == "test":
        return test(args)
    if command == "quality-loop":
        return run_script("quality-loop.py", args)
    if command == "outcome":
        return run_script("outcome-telemetry.py", args)
    if command == "harness":
        return harness(args)
    if command == "completion-report":
        return run_script("completion-report.py", args)
    if command == "closure":
        return closure(args)
    if command == "bootstrap":
        return bootstrap(args)
    if command == "ui":
        return run_script("ui-consistency.py", args)
    if command == "mcp":
        return mcp(args)
    if command == "workflow":
        return workflow(args)
    if command == "vulnerability":
        return vulnerability(args)
    if command == "engine":
        return engine(args)
    if command == "aidlc":
        return aidlc(args)
    if command == "benchmark":
        return benchmark(args)
    if command == "efficacy":
        return efficacy(args)
    if command == "analyze":
        return run_script("analyze-benchmark.py", args)
    if command == "eval":
        return evaluation(args)
    if command == "doctor":
        return doctor(args)
    if command == "guard":
        return guard(args)
    if command == "guardrail":
        return guardrail(args)
    if command == "dependency":
        return dependency(args)
    if command == "enforce":
        return enforce(args)
    if command == "governance":
        if not args:
            print("Usage: tailtrail governance check|sync")
            return 2
        return run_script("sync-governance.py", args)
    if command == "registry":
        return registry(args)
    if command == "maturity":
        if args[:1] == ["maintainability"]:
            return run_script("product-maintainability.py", args[1:])
        return run_script("product-maturity.py", args)
    if command == "enterprise-readiness":
        return run_script("enterprise-readiness.py", args)
    if command == "policy":
        return run_script("policy-check.py", args)
    if command == "install":
        return install(args)
    if command == "setup":
        return run_script("installer.py", ["setup", *args])
    if command == "status" and any(item == "--run-id" or item.startswith("--run-id=") for item in args):
        return run_script("orchestration_facade.py", ["status", *args])
    if command in {"verify", "status", "rollback", "uninstall", "repair", "recover"}:
        return run_script("installer.py", [command, *args])
    if command == "first-run":
        return run_script("first-run.py", args)
    if command == "update":
        return run_script("installer.py", ["update", *args])
    if command == "upgrade":
        return run_script("upgrade-tailtrail.py", args)
    if command == "release":
        return run_script("release-info.py", args)
    if command == "qualify":
        return run_script("installation-qualification.py", args)
    if command == "team-init":
        return run_script("team-init.py", args)
    if command == "adapters":
        return adapters(args)
    if command in {"learn", "learnings"}:
        return learn(args)

    return start(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
