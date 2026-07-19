#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if SCRIPTS.as_posix() not in sys.path:
    sys.path.insert(0, SCRIPTS.as_posix())

from install_surfaces import CORE_CONTEXT, CORE_FILES, CORE_SCRIPTS, CORE_TEMPLATES

PYTHON = sys.executable

COMMANDS = {
    "help": "Show the main TailTrail command surface.",
    "commands": "Print the detailed command catalog.",
    "hello": "Confirm TailTrail is installed and reachable.",
    "version": "Show source/pack location.",
    "start": "Start a task with Navigator-first plan, metrics, setup posture, and learning quality.",
    "do": "Alias for start; run Navigator-first planning for a free-form task.",
    "run": "Alias for start; run Navigator-first planning for a free-form task.",
    "next": "Recommend one deterministic next action after a Start report.",
    "guide": "Preview the future Navigator entry point for a user goal.",
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
    "reference": "Plan safe read-only cross-repo reference usage.",
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
    "bootstrap": "Create or inspect a safe pre-task repo/runtime snapshot.",
    "mcp": "Run the opt-in read-only TailTrail MCP server tools.",
    "vulnerability": "Summarize, plan, or run approved vulnerability scans.",
    "engine": "Run V2.7 evidence-based engine helpers.",
    "aidlc": "Run AIDLC init/check helpers.",
    "benchmark": "Run benchmark-tailtrail.py or efficacy benchmarks.",
    "efficacy": "Run BL-1 measured-efficacy runner with strict measured/estimate labels.",
    "analyze": "Run analyze-benchmark.py.",
    "eval": "Audit and later run the Evaluation Harness umbrella.",
    "doctor": "Run source or installed-pack validation checks.",
    "guard": "Run local guardrail checks against a diff or staged changes.",
    "guardrail": "Run guardrail checks and precision baselines.",
    "governance": "Check or sync repeated governance text.",
    "registry": "Inspect and validate the TailTrail feature registry.",
    "policy": "Initialize or validate local TailTrail policy files.",
    "install": "Run install helpers.",
    "update": "Run update-tailtrail.py.",
    "team-init": "Run team-init.py.",
    "adapters": "Check or sync assistant adapter files and required adapter behavior.",
    "learn": "Run simple learnings or Learning Agent V2.",
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


def invocation() -> str:
    command_name = os.environ.get("TAILTRAIL_COMMAND_NAME")
    if command_name:
        return command_name
    return f"python3 {Path(sys.argv[0]).as_posix()}"


def quiet_enabled(args: list[str] | None = None) -> bool:
    if os.environ.get("TAILTRAIL_QUIET", "").lower() in {"1", "true", "yes", "on"}:
        return True
    return bool(args and "--quiet" in args)


def strip_wrapper_flags(args: list[str]) -> list[str]:
    return [item for item in args if item != "--quiet"]


def json_output_requested(args: list[str]) -> bool:
    for index, value in enumerate(args):
        if value == "--format" and index + 1 < len(args) and args[index + 1] == "json":
            return True
        if value == "--format=json":
            return True
    return False


def print_startup_banner() -> None:
    try:
        print("╭────────────────────────────────────────────╮")
        print("│ TailTrail                                  │")
        print("│ Navigator online. Context stays lean.      │")
        print("│                                            │")
        print("│ Navigator • Code Graph • Guardrails        │")
        print("│ AIDLC • Review Lenses • Test Precision     │")
        print("│ Token Budget • CI/Sonar • Security         │")
        print("│ Learning • Handoff • Value Reports         │")
        print("│ Meta-Harness • Shared Metadata             │")
        print("╰────────────────────────────────────────────╯")
        print("")
    except UnicodeEncodeError:
        print("+--------------------------------------------+")
        print("| TailTrail                                  |")
        print("| Navigator online. Context stays lean.      |")
        print("|                                            |")
        print("| Navigator * Code Graph * Guardrails        |")
        print("| AIDLC * Review Lenses * Test Precision     |")
        print("| Token Budget * CI/Sonar * Security         |")
        print("| Learning * Handoff * Value Reports         |")
        print("| Meta-Harness * Shared Metadata             |")
        print("+--------------------------------------------+")
        print("")


def script(name: str) -> Path:
    return SCRIPTS / name


def run_script(name: str, args: list[str]) -> int:
    command = [PYTHON, script(name).as_posix(), *args]
    result = subprocess.run(command, cwd=Path.cwd(), check=False)
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
        "reference",
        "aidlc",
        "benchmark",
        "efficacy",
        "analyze",
        "eval",
        "doctor",
        "guard",
        "guardrail",
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


def hello() -> int:
    manifest = ROOT / ".tailtrail-install.json"
    mode = "installed pack" if manifest.is_file() else "source checkout"
    if not quiet_enabled(sys.argv[2:]):
        print_startup_banner()
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


def start(args: list[str]) -> int:
    if not args:
        print('Usage: tailtrail start "your goal" [--changed path/to/file]')
        return 2
    if not quiet_enabled(args) and not json_output_requested(args):
        print_startup_banner()
    return run_script("task-start.py", [*strip_wrapper_flags(args), "--command-prefix", invocation()])


def doctor() -> int:
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
        print("Usage: tailtrail aidlc init|check [args]")
        return 2
    action, rest = args[0], args[1:]
    if action == "init":
        return run_script("aidlc-init.py", rest)
    if action == "check":
        return run_script("aidlc-check.py", rest)
    print("Unknown aidlc action. Use: init or check")
    return 2


def install(args: list[str]) -> int:
    if not args:
        print("Usage: tailtrail install codex|codex-plugin|copilot|local|launcher|upgrade-to-extended|status [args]")
        return 2
    action, rest = args[0], args[1:]
    if action == "copilot":
        return run_script("install-copilot.py", rest)
    if action == "codex":
        return run_script("install-local.py", ["--profile", "codex", *rest])
    if action == "codex-plugin":
        return run_script("install-local.py", ["--profile", "codex-plugin", *rest])
    if action == "local":
        return run_script("install-local.py", rest)
    if action == "launcher":
        return run_script("install-launcher.py", rest)
    if action == "upgrade-to-extended":
        return run_script("install-copilot.py", ["--surface", "extended", "--upgrade", *rest])
    if action == "status":
        return run_script("install-copilot.py", ["--status", *rest])
    print("Unknown install action. Use: codex, codex-plugin, copilot, local, launcher, upgrade-to-extended, or status")
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
    if args and args[0] in {"aggregate-shared", "analyze", "readiness"}:
        return run_script("meta-harness-analyze.py", args)
    if args and args[0] == "propose":
        return run_script("meta-harness-propose.py", args)
    if args and args[0] == "proposal-status":
        return run_script("meta-harness-propose.py", ["status", *args[1:]])
    if args and args[0] == "proposal-record":
        return run_script("meta-harness-propose.py", ["record", *args[1:]])
    return run_script("harness-review.py", args)


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


def registry(args: list[str]) -> int:
    if not args:
        print("Usage: tailtrail registry list|show|surfaces|validate [args]")
        return 2
    return run_script("tailtrail-registry.py", args)


def token(args: list[str]) -> int:
    if args and args[0] == "route":
        return run_script("token-harness.py", args)
    return run_script("token-auto.py", args)


def evaluation(args: list[str]) -> int:
    return run_script("evaluation-harness.py", args)


def adapters(args: list[str]) -> int:
    action = args[0] if args else "check"
    rest = args[1:] if args else []
    if action == "check":
        return run_script("sync-adapters.py", ["--check", *rest])
    if action == "sync":
        return run_script("sync-adapters.py", ["--write", *rest])
    print("Usage: tailtrail adapters check|sync")
    return 2


def main() -> int:
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
    if command in {"start", "do", "run"}:
        return start(args)
    if command == "next":
        return run_script("task-next.py", [*strip_wrapper_flags(args), "--command-prefix", invocation()])
    if command == "guide":
        return guide(args)
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
    if command == "reference":
        return run_script("cross-repo-reference.py", args)
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
    if command == "bootstrap":
        return bootstrap(args)
    if command == "mcp":
        return mcp(args)
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
        return doctor()
    if command == "guard":
        return guard(args)
    if command == "guardrail":
        return guardrail(args)
    if command == "governance":
        if not args:
            print("Usage: tailtrail governance check|sync")
            return 2
        return run_script("sync-governance.py", args)
    if command == "registry":
        return registry(args)
    if command == "policy":
        return run_script("policy-check.py", args)
    if command == "install":
        return install(args)
    if command == "update":
        return run_script("update-tailtrail.py", args)
    if command == "team-init":
        return run_script("team-init.py", args)
    if command == "adapters":
        return adapters(args)
    if command in {"learn", "learnings"}:
        return learn(args)

    return start(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
