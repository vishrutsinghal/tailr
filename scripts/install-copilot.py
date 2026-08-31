#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from install_surfaces import DEFAULT_SURFACE, SURFACES, resolve


ROOT = Path(__file__).resolve().parents[1]
IMPORT_ROOT = ROOT.parent if (ROOT / "__init__.py").is_file() else ROOT
try:
    sys.path.remove(IMPORT_ROOT.as_posix())
except ValueError:
    pass
sys.path.insert(0, IMPORT_ROOT.as_posix())

COPILOT_SOURCE = ROOT / "adapters" / "copilot-instructions.md"
START_PROMPT_SOURCE = ROOT / ".github" / "prompts" / "tailtrail-start.prompt.md"

PACK_FILES = [
    ".cursor/rules/tailtrail.mdc",
    ".github/copilot-instructions.md",
    ".github/prompts/tailtrail-start.prompt.md",
    ".openai/chatgpt-instructions.md",
    "AGENTS.md",
    "AIDLC.md",
    "ADMIN-RELEASE-MODES.md",
    "ASSISTANT-COMPATIBILITY.md",
    "ARCHITECTURE.md",
    "CHANGELOG.md",
    "CLAUDE.md",
    "CONTRIBUTING.md",
    "DEBUG-HARNESS.md",
    "DEPENDENCY-GATE.md",
    "DURABLE-WORKFLOW-RUNTIME-REVISED.md",
    "EVALUATION-HARNESS.md",
    "ENTERPRISE-REVIEW.md",
    "ENTERPRISE-READINESS-ASSESSMENT.md",
    "GEMINI.md",
    "GUARDRAILS.md",
    "HOST-ADAPTERS.md",
    "GOVERNANCE.md",
    "INSTALL.md",
    "INSTALLER-LIFECYCLE.md",
    "IMPROVEMENT-PLAN.md",
    "LEARNING-GOVERNANCE.md",
    "MCP-SERVER.md",
    "MANIFEST.in",
    "META-HARNESS-IMPLEMENTATION.md",
    "NAVIGATOR-TEST-SCENARIOS.md",
    "PACKAGE-CONTRACT.md",
    "REPOSITORY-ENFORCEMENT.md",
    "platform-release-contract.json",
    "PUBLIC-CLAIMS.md",
    "PUBLIC-RELEASE-METADATA.md",
    "QUICKSTART.md",
    "CHEATSHEET.md",
    "README.md",
    "RELEASE-CHECKLIST.md",
    "release-build-lock.json",
    "ROADMAP.md",
    "SECURITY.md",
    "SUPPORT.md",
    "SUPPLY-CHAIN.md",
    "TOKEN-AUTOPILOT.md",
    "TOKEN-HARNESS.md",
    "TOKEN-SLICER.md",
    "TAILTRAIL-COMMANDS.md",
    "TAILTRAIL-PITCH.md",
    "context-continuity-harness.md",
    "harness-engineering.md",
    "harness-engineering-workflow.md",
    "program-delivery-harness.md",
    "enterprise-closure-registry.json",
    "enterprise-closure-registry.schema.json",
    "release-manifest.json",
    "release-manifest.schema.json",
    "tailtrail-registry.json",
    "tailtrail-registry.schema.json",
    "tailtrail-spec-kit-integration.md",
    "tailtrail-automation-guide.md",
    "tailtrail-aidlc-integration.md",
    "tailtrail-closure-learning-automation-plan.md",
    "tailtrail-enterprise-target-workspace.md",
    "tailtrail-implementation-backlog.md",
    "tailtrail-interactive-plan-mode.md",
    "tailtrail-mcp.md",
    "testing-confidence.md",
    "context/TailTrail.map.md",
    "context/guardrail-layers.md",
    "context/intent-aliases.md",
    "context/slices.md",
    "context/token-router.md",
    "pyproject.toml",
    "package-manifest.json",
    "package-manifest.schema.json",
    "setup.py",
    "tailtrail-policy.example.md",
    "tailtrail-enforcement-baseline.json",
    "tailtrail-enforcement-policy.json",
    "tailtrail-enforcement-suppressions.json",
    "tailtrail_cli.py",
    "templates/intent-overrides.json",
    "templates/enterprise-target-policy.example.json",
    "templates/dependency-decision.example.json",
    "USEFUL-PROMPTS.md",
    "USER-GUIDE.md",
    "VERSIONING.md",
    "aidlc-docs/phase-e0-design.md",
    "aidlc-docs/phase-e0-requirements.md",
    "aidlc-docs/phase-e3-design.md",
    "aidlc-docs/phase-e3-requirements.md",
]

PACK_DIRS = [
    "adapters",
    "aidlc",
    "assets",
    "benchmarks",
    "context",
    "docs",
    "hooks",
    "templates",
    "tailtrail",
    "schemas",
]

PACK_SCRIPTS = [
    "scripts/__init__.py",
    "scripts/aidlc-check.py",
    "scripts/aidlc-official-bridge.py",
    "scripts/aidlc-official-detect.py",
    "scripts/aidlc-official-host.py",
    "scripts/aidlc-official-install.py",
    "scripts/official-aidlc-requirements.py",
    "scripts/official-aidlc-checkpoint.py",
    "scripts/official-aidlc-state.py",
    "scripts/official-aidlc-sanitize.py",
    "scripts/official-aidlc-runtime.py",
    "scripts/planning-discussion.py",
    "scripts/planning-aidlc-question.py",
    "scripts/question-orchestrator.py",
    "scripts/planning-feature-controls.py",
    "scripts/planning-investigation.py",
    "scripts/planning-revision.py",
    "scripts/aidlc-init.py",
    "scripts/aidlc-requirements.py",
    "scripts/advanced-runtime.py",
    "scripts/analyze-benchmark.py",
    "scripts/architecture-fitness.py",
    "scripts/architecture_planning.py",
    "scripts/behaviour_planning.py",
    "scripts/ui_planning.py",
    "scripts/ast-map.py",
    "scripts/behavior-harness.py",
    "scripts/benchmark-tailtrail.py",
    "scripts/bootstrap-snapshot.py",
    "scripts/change-intent-anchor.py",
    "scripts/cache-summary.py",
    "scripts/check-tailtrail.py",
    "scripts/ci-evidence-ingest.py",
    "scripts/completion-review.py",
    "scripts/closure-contract.py",
    "scripts/evidence-tiers.py",
    "scripts/closure-close.py",
    "scripts/closure-correction.py",
    "scripts/closure-evaluation.py",
    "scripts/closure-finalizer.py",
    "scripts/closure-learning.py",
    "scripts/closure-recorder.py",
    "scripts/completion-report.py",
    "scripts/delivery-orchestrator.py",
    "scripts/ci-summary.py",
    "scripts/code-graph-mapper.py",
    "scripts/code_graph_inventory.py",
    "scripts/context-receipt.py",
    "scripts/context-continuity.py",
    "scripts/context_receipt.py",
    "scripts/cross-repo-reference.py",
    "scripts/efficacy-benchmark.py",
    "scripts/efficacy-run.py",
    "scripts/evaluation-audit.py",
    "scripts/evaluation-dataset.py",
    "scripts/evaluation-harness.py",
    "scripts/execution-evidence.py",
    "scripts/execution-failure.py",
    "scripts/dependency-decision.py",
    "scripts/export-release.py",
    "scripts/expand-intent.py",
    "scripts/evidence-metrics.py",
    "scripts/enterprise-target-policy.py",
    "scripts/enterprise-readiness.py",
    "scripts/flaky-test-tracker.py",
    "scripts/first-run.py",
    "scripts/graph-learning.py",
    "scripts/host-adapter-conformance.py",
    "scripts/host-runtime-conformance.py",
    "scripts/host-workspace-adapter.py",
    "scripts/git-readiness.py",
    "scripts/guardrail-precision.py",
    "scripts/harness-checkpoint.py",
    "scripts/harness-convergence.py",
    "scripts/harness-controls.py",
    "scripts/harness-feedback.py",
    "scripts/harness-review.py",
    "scripts/harness-template.py",
    "scripts/higher-tier-testing.py",
    "scripts/guardrail-check.py",
    "scripts/install-copilot.py",
    "scripts/install-launcher.py",
    "scripts/install-local.py",
    "scripts/installer.py",
    "scripts/install_surfaces.py",
    "scripts/maintainability-harness.py",
    "scripts/maintainability_planning.py",
    "scripts/learning-agent.py",
    "scripts/learning-refresh.py",
    "scripts/learning-review.py",
    "scripts/learnings.py",
    "scripts/meta-harness-analyze.py",
    "scripts/meta-harness-propose.py",
    "scripts/mcp-server.py",
    "scripts/navigator.py",
    "scripts/navigator_core.py",
    "scripts/navigator_discovery.py",
    "scripts/navigator_render.py",
    "scripts/outcome-telemetry.py",
    "scripts/policy-check.py",
    "scripts/phase8-advanced.py",
    "scripts/package-release-proof.py",
    "scripts/platform-qualification.py",
    "scripts/planning-lock.py",
    "scripts/prompt-profile.py",
    "scripts/prompt_profile.py",
    "scripts/public-benchmark.py",
    "scripts/prune-context.py",
    "scripts/public-doc-audit.py",
    "scripts/program-checkpoint.py",
    "scripts/program-plan.py",
    "scripts/quality-loop.py",
    "scripts/quality-run.py",
    "scripts/quality-scan.py",
    "scripts/review-graph.py",
    "scripts/review-run.py",
    "scripts/scanner-graph-overlay.py",
    "scripts/setup-scan.py",
    "scripts/spec-kit-amendment.py",
    "scripts/spec-kit-bridge.py",
    "scripts/spec-kit-ci-gate.py",
    "scripts/spec-kit-converge.py",
    "scripts/spec-kit-detect.py",
    "scripts/spec-kit-evidence.py",
    "scripts/spec-kit-import.py",
    "scripts/spec-kit-integration.py",
    "scripts/spec-kit-observability.py",
    "scripts/spec-kit-policy.py",
    "scripts/spec-kit-slices.py",
    "scripts/supply-chain.py",
    "scripts/slice-context.py",
    "scripts/smoke-test.py",
    "scripts/summarize-output.py",
    "scripts/recovery-reconcile.py",
    "scripts/repository-enforcement.py",
    "scripts/recovery-diagnostician.py",
    "scripts/release-confidence.py",
    "scripts/release-check.py",
    "scripts/release_manifest.py",
    "scripts/route-context.py",
    "scripts/requirement_discovery.py",
    "scripts/requirement-completion.py",
    "scripts/requirement-impact-map.py",
    "scripts/requirement-recovery-manifest.py",
    "scripts/run-ledger.py",
    "scripts/task-recovery-boundary.py",
    "scripts/task-recovery.py",
    "scripts/sonar-summary.py",
    "scripts/sync-adapters.py",
    "scripts/testing-profile.py",
    "scripts/tailtrail.py",
    "scripts/tailtrail-registry.py",
    "scripts/registry-drift.py",
    "scripts/tailtrail-report.py",
    "scripts/sync-governance.py",
    "scripts/task-start.py",
    "scripts/start_posture.py",
    "scripts/target_workspace.py",
    "scripts/test-tier-selector.py",
    "scripts/test-precision.py",
    "scripts/task-next.py",
    "scripts/workflow-runtime.py",
    "scripts/workflow_runtime/__init__.py",
    "scripts/workflow_runtime/approvals.py",
    "scripts/workflow_runtime/adapter_catalog.py",
    "scripts/workflow_runtime/adapters.py",
    "scripts/workflow_runtime/assurance.py",
    "scripts/workflow_runtime/capabilities.py",
    "scripts/workflow_runtime/ci.py",
    "scripts/workflow_runtime/compiler.py",
    "scripts/workflow_runtime/contracts.py",
    "scripts/workflow_runtime/correction.py",
    "scripts/workflow_runtime/context.py",
    "scripts/workflow_runtime/denials.py",
    "scripts/workflow_runtime/enterprise.py",
    "scripts/workflow_runtime/enterprise_recovery.py",
    "scripts/workflow_runtime/enterprise_transport.py",
    "scripts/workflow_runtime/evidence.py",
    "scripts/workflow_runtime/evidence_completion.py",
    "scripts/workflow_runtime/executor.py",
    "scripts/workflow_runtime/freshness.py",
    "scripts/workflow_runtime/ownership.py",
    "scripts/workflow_runtime/outcomes.py",
    "scripts/workflow_runtime/mcp_bridge.py",
    "scripts/workflow_runtime/projection.py",
    "scripts/workflow_runtime/reason_codes.py",
    "scripts/workflow_runtime/resume.py",
    "scripts/workflow_runtime/release.py",
    "scripts/workflow_runtime/retention.py",
    "scripts/workflow_runtime/retry.py",
    "scripts/workflow_runtime/start_integration.py",
    "scripts/workflow_runtime/state.py",
    "scripts/workflow_runtime/storage.py",
    "scripts/workflow_runtime/task_scope.py",
    "scripts/workflow_runtime/templates.py",
    "scripts/workflow_runtime/transitions.py",
    "scripts/workflow_runtime/vertical.py",
    "scripts/token-auto.py",
    "scripts/token-budget-coach.py",
    "scripts/token_budget_coach.py",
    "scripts/ui-consistency.py",
    "scripts/token-harness.py",
    "scripts/token-harness-ledger.py",
    "scripts/token-harness-proof.py",
    "scripts/token-harness-bridge.py",
    "scripts/token-harness-reduce.py",
    "scripts/token-telemetry.py",
    "scripts/token_telemetry.py",
    "scripts/token-savings.py",
    "scripts/update-copilot.py",
    "scripts/team-init.py",
    "scripts/update-tailtrail.py",
    "scripts/validation-summary.py",
    "scripts/validation-receipt.py",
    "scripts/vulnerability-run.py",
    "scripts/vulnerability-scan.py",
    "scripts/vulnerability-summary.py",
    "scripts/workflow-dashboard.py",
    "scripts/debug-intake.py",
    "scripts/debug-reproduction.py",
    "scripts/debug-orientation.py",
    "scripts/debug-hypothesis.py",
    "scripts/debug-correction.py",
    "scripts/debug-harness-convergence.py",
    "scripts/debug-completion.py",
    "scripts/debug-privacy.py",
    "scripts/debug-governance.py",
    "scripts/debug-evaluation.py",
]

MANIFEST_NAME = ".tailtrail-install.json"

LOCAL_INSTALL_GITIGNORE = [
    ".tailtrail/",
    "tailtrail/",
    ".github/copilot-instructions.md",
    ".github/prompts/tailtrail-start.prompt.md",
    ".cursor/rules/tailtrail.mdc",
    ".openai/chatgpt-instructions.md",
    "CLAUDE.md",
    "GEMINI.md",
    "AGENTS.md",
    "AIDLC.md",
    "DEPENDENCY-GATE.md",
    "GUARDRAILS.md",
    "GOVERNANCE.md",
    "INSTALL.md",
    "CHEATSHEET.md",
    "TOKEN-AUTOPILOT.md",
    "TOKEN-SLICER.md",
    "TAILTRAIL-COMMANDS.md",
    "USEFUL-PROMPTS.md",
    "USER-GUIDE.md",
    "tailtrail-policy.md",
    "tailtrail-policy.example.md",
    "aidlc-docs/",
    "!tailtrail-meta/",
    "!tailtrail-meta/README.md",
    "!tailtrail-meta/code-graph-cache.json",
    "!tailtrail-meta/harness-summary.schema.json",
    "!tailtrail-meta/harness-summary.jsonl",
]


def copy_file(source: Path, destination: Path, force: bool, written: list[str], skipped: list[str]) -> None:
    if destination.exists() and not force:
        skipped.append(destination.as_posix())
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    written.append(destination.as_posix())


def pack_ignore(directory: str, names: list[str]) -> set[str]:
    ignored = {"__pycache__", ".DS_Store"}.intersection(names)
    if Path(directory).name == "results" and "benchmarks" in Path(directory).parts:
        ignored.update(name for name in names if name.endswith(".md"))
    return ignored


def copy_dir(source: Path, destination: Path, force: bool, written: list[str], skipped: list[str]) -> None:
    if destination.exists() and not force:
        skipped.append(destination.as_posix())
        return
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination, ignore=pack_ignore)
    written.append(destination.as_posix())


def pack_entries_for(pack_files: list[str] | tuple[str, ...], pack_dirs: list[str] | tuple[str, ...], pack_scripts: list[str] | tuple[str, ...]) -> list[str]:
    entries: list[str] = []
    entries.extend(pack_files)
    for relative_dir in pack_dirs:
        source_dir = ROOT / relative_dir
        for path in sorted(source_dir.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts and path.name != ".DS_Store":
                if relative_dir == "benchmarks" and "results" in path.parts and path.suffix == ".md":
                    continue
                entries.append(path.relative_to(ROOT).as_posix())
    entries.extend(pack_scripts)
    return sorted(entries)


def pack_entries() -> list[str]:
    return pack_entries_for(PACK_FILES, PACK_DIRS, PACK_SCRIPTS)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def install_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT00:00:00+00:00")


def write_manifest(
    pack_root: Path,
    pack_dir: Path,
    written: list[str],
    surface: str,
    pack_files: list[str] | tuple[str, ...],
    pack_dirs: list[str] | tuple[str, ...],
    pack_scripts: list[str] | tuple[str, ...],
    upgraded: bool = False,
) -> None:
    if pack_dir.as_posix() == ".":
        location = "repository root"
    else:
        location = pack_dir.as_posix()
    files = {
        relative_path: {
            "sha256": sha256(ROOT / relative_path),
        }
        for relative_path in pack_entries_for(pack_files, pack_dirs, pack_scripts)
    }
    # Hash the written files rather than the in-memory rendered text. On Windows
    # text output can use a different newline representation, and the manifest
    # must describe the exact bytes later used for safe upgrade checks.
    for relative_path, rendered in (
        (".github/copilot-instructions.md", copilot_body(pack_dir)),
        (".github/prompts/tailtrail-start.prompt.md", start_prompt_body(pack_dir)),
    ):
        destination = pack_root / relative_path
        digest = sha256(destination) if destination.is_file() else hashlib.sha256(rendered.encode("utf-8")).hexdigest()
        files[relative_path] = {"sha256": digest}
    manifest = {
        "version": 1,
        "tool": "tailtrail",
        "surface": surface,
        "pack_dir": pack_dir.as_posix(),
        "pack_location": location,
        "updated_at": install_timestamp(),
        "files": files,
        "customization": {
            "preferred_override_files": [
                ".tailtrail/intent-overrides.json",
                f"{pack_dir.as_posix()}/intent-overrides.json" if pack_dir.as_posix() != "." else "intent-overrides.json",
            ],
            "note": "Customize TailTrail through override files instead of editing managed core files.",
        },
    }
    if upgraded:
        manifest["upgraded_at"] = datetime.now(timezone.utc).isoformat()
    destination = pack_root / MANIFEST_NAME
    destination.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    written.append(destination.as_posix())


def validate_pack_dir(pack_dir: str) -> Path:
    path = Path(pack_dir)
    if path.is_absolute():
        raise SystemExit("--pack-dir must be relative to the target project root")
    if any(part == ".." for part in path.parts):
        raise SystemExit("--pack-dir must not contain '..'")
    return path


def copilot_body(pack_dir: Path | None) -> str:
    body = COPILOT_SOURCE.read_text(encoding="utf-8")
    if pack_dir is None:
        return body

    pack_label = pack_dir.as_posix()
    if pack_label == ".":
        pack_label = "repository root"
        prefix = ""
        script_prefix = "scripts"
    else:
        prefix = f"{pack_dir.as_posix()}/"
        script_prefix = f"{pack_dir.as_posix()}/scripts"

    return (
        body
        + "\n\n"
        + "## Installed TailTrail Pack Location\n\n"
        + f"TailTrail support files are installed under `{pack_label}`.\n\n"
        + "When using TailTrail support files, resolve them from this location:\n\n"
        + f"- `{prefix}AGENTS.md`\n"
        + f"- `{prefix}AIDLC.md`\n"
        + f"- `{prefix}DEPENDENCY-GATE.md`\n"
        + f"- `{prefix}GUARDRAILS.md`\n"
        + f"- `{prefix}GOVERNANCE.md`\n"
        + f"- `{prefix}tailtrail-policy.example.md`\n"
        + f"- `{prefix}context/flow-catalog.md`\n"
        + f"- `{prefix}context/guardrail-layers.md`\n"
        + f"- `{prefix}context/intent-aliases.md`\n"
        + f"- `{prefix}context/navigator.md`\n"
        + f"- `{prefix}context/code-graph-mapper.md`\n"
        + f"- `{prefix}context/review-lenses.md`\n"
        + f"- `{prefix}context/TailTrail.map.md`\n"
        + f"- `{prefix}context/slices.md`\n"
        + f"- `{prefix}TAILTRAIL-COMMANDS.md`\n"
        + f"- `{prefix}USEFUL-PROMPTS.md`\n"
        + f"- `{prefix}hooks/`\n"
        + f"- `{prefix}benchmarks/`\n"
        + f"- `{prefix}aidlc/stages/`\n"
        + f"- `{prefix}templates/`\n\n"
        + "When scripts are needed, use:\n\n"
        + f"- `python3 {script_prefix}/tailtrail.py help`\n"
        + f"- `python3 {script_prefix}/tailtrail.py do \"fix Sonar issue and prepare PR\"`\n"
        + f"- `python3 {script_prefix}/tailtrail.py \"fix Sonar issue and prepare PR\"`\n"
        + f"- `python3 {script_prefix}/tailtrail.py guide \"fix Sonar issue and prepare PR\"`\n"
        + f"- `python3 {script_prefix}/navigator.py \"fix Sonar issue and prepare PR\"`\n"
        + f"- `python3 {script_prefix}/tailtrail.py graph --changed path/to/file`\n"
        + f"- `python3 {script_prefix}/tailtrail.py graph map --changed path/to/file`\n"
        + f"- `python3 {script_prefix}/tailtrail.py graph status --changed path/to/file`\n"
        + f"- `python3 {script_prefix}/tailtrail.py ci summarize --file ci.log`\n"
        + f"- `python3 {script_prefix}/tailtrail.py sonar summarize --file sonar.log`\n"
        + f"- `python3 {script_prefix}/tailtrail.py validation summarize --ci ci.log --sonar sonar.log`\n"
        + f"- `python3 {script_prefix}/tailtrail.py quality scan --changed path/to/file`\n"
        + f"- `python3 {script_prefix}/tailtrail.py quality run --approved --command \"npm run lint\"`\n"
        + f"- `python3 {script_prefix}/tailtrail.py quality-loop review --month 2026-07`\n"
        + f"- `python3 {script_prefix}/tailtrail.py report --month 2026-07`\n"
        + f"- `python3 {script_prefix}/tailtrail.py report value --month 2026-07`\n"
        + f"- `python3 {script_prefix}/tailtrail.py policy check --root .`\n"
        + f"- `python3 {script_prefix}/tailtrail.py governance check`\n"
        + f"- `python3 {script_prefix}/tailtrail.py vulnerability scan --changed package.json`\n"
        + f"- `python3 {script_prefix}/tailtrail.py vulnerability summarize --file audit.log`\n"
        + f"- `python3 {script_prefix}/tailtrail.py vulnerability run --approved --command \"npm audit\"`\n"
        + f"- `python3 {script_prefix}/expand-intent.py \"use AIDLC and review\"`\n"
        + f"- `python3 {script_prefix}/install-local.py --inspect`\n"
        + f"- `python3 {script_prefix}/benchmark-tailtrail.py`\n"
        + f"- `python3 {script_prefix}/analyze-benchmark.py {prefix}benchmarks/results/latest.json`\n"
        + f"- `python3 {script_prefix}/team-init.py --root . --mode optional`\n"
        + f"- `python3 {script_prefix}/learnings.py init --root .`\n"
        + f"- `python3 {script_prefix}/learning-agent.py search --tags sonar,java --limit 3`\n"
        + f"- `python3 {script_prefix}/learning-refresh.py recommend --root .`\n"
        + f"- `python3 {script_prefix}/graph-learning.py search --changed path/to/file --tags sonar,java`\n"
        + f"- `python3 {prefix}hooks/learning-capture-hook.py \"Fixed validator complexity\" --candidate \"Extract named guard methods while preserving validation order.\"`\n"
        + f"- `python3 {script_prefix}/review-graph.py --changed path/to/file`\n"
        + f"- `python3 {script_prefix}/code-graph-mapper.py map --changed path/to/file`\n"
        + f"- `python3 {script_prefix}/token-auto.py \"review this diff\"`\n"
        + f"- `python3 {script_prefix}/token-savings.py estimate --used {prefix}context/slices.md --avoided {prefix}ROADMAP.md {prefix}USER-GUIDE.md`\n"
        + f"- `python3 {script_prefix}/tailtrail.py token-harness bridge plan --path build.log`\n"
        + f"- `python3 {script_prefix}/tailtrail.py token-harness bridge validate-output --input /tmp/bridge-input.json --output /tmp/bridge-output.json`\n"
        + f"- `python3 {script_prefix}/route-context.py review`\n"
        + f"- `python3 {script_prefix}/aidlc-init.py --root . --depth standard`\n"
        + f"- `python3 {script_prefix}/aidlc-check.py --root .`\n"
        + f"- `python3 {prefix}hooks/tailtrail-lifecycle-hook.py \"use AIDLC and review\"`\n"
    )


def write_copilot(destination: Path, pack_dir: Path | None, force: bool, written: list[str], skipped: list[str]) -> None:
    if destination.exists() and not force:
        skipped.append(destination.as_posix())
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(copilot_body(pack_dir), encoding="utf-8")
    written.append(destination.as_posix())


def start_prompt_body(pack_dir: Path | None) -> str:
    body = START_PROMPT_SOURCE.read_text(encoding="utf-8")
    if pack_dir is None or pack_dir.as_posix() == ".":
        script_path = "scripts/tailtrail.py"
    else:
        script_path = f"{pack_dir.as_posix()}/scripts/tailtrail.py"
    return body.replace("{{TAILTRAIL_START_COMMAND}}", f'python3 {script_path} start "<goal>"')


def write_start_prompt(destination: Path, pack_dir: Path | None, force: bool, written: list[str], skipped: list[str]) -> None:
    if destination.exists() and not force:
        skipped.append(destination.as_posix())
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(start_prompt_body(pack_dir), encoding="utf-8")
    written.append(destination.as_posix())


def gitignore_covers(pattern: str, lines: list[str]) -> bool:
    if pattern in lines:
        return True
    if pattern == ".tailtrail/" and any(line in {".tailtrail/", ".tailtrail"} for line in lines):
        return True
    if pattern == "tailtrail/" and any(line in {"tailtrail/", "tailtrail"} for line in lines):
        return True
    return False


def write_gitignore(target_root: Path, pack_dir: Path | None, written: list[str], skipped: list[str]) -> None:
    gitignore = target_root / ".gitignore"
    existing = gitignore.read_text(encoding="utf-8").splitlines() if gitignore.exists() else []
    existing_stripped = [line.strip() for line in existing if line.strip() and not line.lstrip().startswith("#")]
    entries = list(LOCAL_INSTALL_GITIGNORE)
    if pack_dir is not None and pack_dir.as_posix() not in {"tailtrail", "."}:
        entries.append(f"{pack_dir.as_posix().rstrip('/')}/")
    missing = [entry for entry in entries if not gitignore_covers(entry, existing_stripped)]
    if not missing:
        skipped.append(gitignore.as_posix())
        return
    section = [
        "",
        "# TailTrail local install/runtime files",
        "# Keep TailTrail setup files local. Commit only reviewed tailtrail-meta/ metadata.",
        *missing,
    ]
    gitignore.parent.mkdir(parents=True, exist_ok=True)
    gitignore.write_text("\n".join([*existing, *section]).rstrip() + "\n", encoding="utf-8")
    written.append(gitignore.as_posix())


def read_manifest(pack_root: Path) -> dict[str, object] | None:
    path = pack_root / MANIFEST_NAME
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SystemExit(f"Unable to read install manifest {path}: {error}") from error
    if not isinstance(value, dict):
        raise SystemExit(f"Install manifest {path} must contain a JSON object")
    return value


def manifest_files(manifest: dict[str, object] | None) -> dict[str, dict[str, str]]:
    raw = manifest.get("files") if isinstance(manifest, dict) else {}
    if not isinstance(raw, dict):
        return {}
    result: dict[str, dict[str, str]] = {}
    for key, value in raw.items():
        if isinstance(key, str) and isinstance(value, dict):
            sha_value = value.get("sha256")
            if isinstance(sha_value, str):
                result[key] = {"sha256": sha_value}
    return result


def installed_surface(manifest: dict[str, object] | None) -> str:
    value = manifest.get("surface") if isinstance(manifest, dict) else None
    return value if isinstance(value, str) else "unknown"


def source_hash(relative_path: str, pack_dir: Path) -> str:
    if relative_path == ".github/copilot-instructions.md":
        return hashlib.sha256(copilot_body(pack_dir).encode("utf-8")).hexdigest()
    if relative_path == ".github/prompts/tailtrail-start.prompt.md":
        return hashlib.sha256(start_prompt_body(pack_dir).encode("utf-8")).hexdigest()
    return sha256(ROOT / relative_path)


def write_entry(relative_path: str, destination: Path, pack_dir: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if relative_path == ".github/copilot-instructions.md":
        destination.write_text(copilot_body(pack_dir), encoding="utf-8")
    elif relative_path == ".github/prompts/tailtrail-start.prompt.md":
        destination.write_text(start_prompt_body(pack_dir), encoding="utf-8")
    else:
        shutil.copy2(ROOT / relative_path, destination)


def can_upgrade_entry(destination: Path, relative_path: str, previous_files: dict[str, dict[str, str]]) -> tuple[bool, str | None]:
    if not destination.exists():
        return True, None
    previous = previous_files.get(relative_path, {})
    previous_hash = previous.get("sha256")
    if previous_hash and destination.is_file() and sha256(destination) == previous_hash:
        return True, None
    return False, f"{destination.as_posix()} exists and differs from the previous TailTrail-managed hash"


def plan_upgrade(pack_root: Path, pack_dir: Path) -> tuple[dict[str, object], list[str], list[str]]:
    manifest = read_manifest(pack_root)
    if manifest is None:
        raise SystemExit(f"No TailTrail install manifest found at {pack_root / MANIFEST_NAME}")
    current_surface = installed_surface(manifest)
    if current_surface == "extended":
        return manifest, [], []
    if current_surface != "core":
        raise SystemExit(f"Cannot upgrade unknown installed surface: {current_surface}")
    core_files, core_dirs, core_scripts = resolve("core", PACK_FILES, PACK_DIRS, PACK_SCRIPTS)
    extended_files, extended_dirs, extended_scripts = resolve("extended", PACK_FILES, PACK_DIRS, PACK_SCRIPTS)
    core_entries = set(pack_entries_for(core_files, core_dirs, core_scripts))
    extended_entries = set(pack_entries_for(extended_files, extended_dirs, extended_scripts))
    to_add = sorted(extended_entries - core_entries)
    previous_files = manifest_files(manifest)
    blocked: list[str] = []
    for relative_path in to_add:
        ok, reason = can_upgrade_entry(pack_root / relative_path, relative_path, previous_files)
        if not ok and reason:
            blocked.append(reason)
    return manifest, to_add, blocked


def status(pack_root: Path, pack_dir: Path) -> int:
    manifest = read_manifest(pack_root)
    if manifest is None:
        print(f"manifest: missing ({pack_root / MANIFEST_NAME})")
        print("surface: unknown")
        return 1
    surface = installed_surface(manifest)
    print(f"manifest: {pack_root / MANIFEST_NAME}")
    print(f"surface: {surface}")
    if surface == "core":
        _, to_add, blocked = plan_upgrade(pack_root, pack_dir)
        print(f"upgrade_adds: {len(to_add)} files")
        if to_add:
            print("upgrade_examples:")
            for item in to_add[:10]:
                print(f"- {item}")
        if blocked:
            print("upgrade_blockers:")
            for item in blocked:
                print(f"- {item}")
    elif surface == "extended":
        print("upgrade_adds: 0 files")
        print("already extended")
    else:
        print("upgrade_adds: unknown")
    return 0


def upgrade_to_extended(pack_root: Path, pack_dir: Path, force: bool, written: list[str], skipped: list[str]) -> int:
    manifest, to_add, blocked = plan_upgrade(pack_root, pack_dir)
    if installed_surface(manifest) == "extended":
        print("TailTrail install is already extended.")
        return 0
    if blocked and not force:
        print("TailTrail upgrade blocked to avoid overwriting user changes.")
        for item in blocked:
            print(f"- {item}")
        print("Use --force only after reviewing the listed files.")
        return 1
    for relative_path in to_add:
        write_entry(relative_path, pack_root / relative_path, pack_dir)
        written.append((pack_root / relative_path).as_posix())
    extended_files, extended_dirs, extended_scripts = resolve("extended", PACK_FILES, PACK_DIRS, PACK_SCRIPTS)
    write_manifest(pack_root, pack_dir, written, "extended", extended_files, extended_dirs, extended_scripts, upgraded=True)
    if not to_add:
        skipped.append("No files needed to be added.")
    return 0


def print_first_run(target: Path, pack_dir: Path) -> int:
    return subprocess.run([sys.executable, str(ROOT / "scripts" / "first-run.py"), "--target", target.as_posix(), "--profile", "copilot", "--pack-dir", pack_dir.as_posix()], cwd=ROOT, check=False).returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Install TailTrail GitHub Copilot support into a target project.")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Target project root.")
    parser.add_argument("--target", type=Path, help="Alias for --root that installs a managed pack at the target root.")
    parser.add_argument("--with-tailtrail-pack", action="store_true", help="Copy TailTrail support docs, templates, context, AIDLC, and scripts.")
    parser.add_argument("--pack-only", action="store_true", help="Install the managed TailTrail pack without writing Copilot instructions.")
    parser.add_argument("--pack-dir", default="tailtrail", help="Folder for TailTrail support files when --with-tailtrail-pack is used. Use '.' for root layout.")
    parser.add_argument("--surface", choices=SURFACES, default=DEFAULT_SURFACE, help="Surface-area profile: core is first-run minimal, extended is the full pack.")
    parser.add_argument("--upgrade", action="store_true", help="Upgrade an existing Core install to Extended without deleting files.")
    parser.add_argument("--status", action="store_true", help="Report installed surface and what an upgrade would add.")
    parser.add_argument("--no-gitignore", action="store_true", help="Do not add TailTrail local-install ignore entries to .gitignore.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing target files.")
    args = parser.parse_args()

    # E3 compatibility boundary: retain the historical flags, but make the
    # package-owned transactional engine the only executable write path.
    from tailtrail.install.cli import main as installer_main

    target_root = (args.target or args.root).resolve()
    operation = "status" if args.status else "update" if args.upgrade else "install"
    forwarded = [operation, "--host", "copilot", "--target", target_root.as_posix(), "--profile", "extended" if args.upgrade else args.surface]
    if args.force:
        forwarded.append("--force")
    return installer_main(forwarded)


if __name__ == "__main__":
    raise SystemExit(main())
