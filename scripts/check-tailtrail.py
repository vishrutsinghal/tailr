#!/usr/bin/env python3

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_FILES = {
    ".gitignore",
    ".codex-plugin/plugin.json",
    ".cursor/rules/tailtrail.mdc",
    ".github/actions/tailtrail-guard/action.yml",
    ".github/copilot-instructions.md",
    ".github/ISSUE_TEMPLATE/bug_report.md",
    ".github/ISSUE_TEMPLATE/docs_feedback.md",
    ".github/ISSUE_TEMPLATE/feature_request.md",
    ".github/ISSUE_TEMPLATE/security_note.md",
    ".github/pull_request_template.md",
    ".github/workflows/tailtrail-ci.yml",
    ".openai/chatgpt-instructions.md",
    ".pre-commit-hooks.yaml",
    "ADMIN-RELEASE-MODES.md",
    "AGENTS.md",
    "AIDLC.md",
    "ARCHITECTURE.md",
    "ASSISTANT-COMPATIBILITY.md",
    "CHANGELOG.md",
    "CLAUDE.md",
    "CHEATSHEET.md",
    "CODE_OF_CONDUCT.md",
    "CONTRIBUTING.md",
    "DEPENDENCY-GATE.md",
    "DEMO.md",
    "DESIGN.md",
    "ENTERPRISE-REVIEW.md",
    "EVALUATION-HARNESS.md",
    "GEMINI.md",
    "GUARDRAILS.md",
    "GOVERNANCE.md",
    "HONEST-REVIEW.md",
    "HONEST-REVIEW-IMPLEMENTATION-PLAN.md",
    "LICENSE",
    "LEARNING-GOVERNANCE.md",
    "META-HARNESS-IMPLEMENTATION.md",
    "MCP-SERVER.md",
    "NAVIGATOR-TEST-SCENARIOS.md",
    "NOTICE.md",
    "PITCH-PLAN.md",
    "PUBLIC-CLAIMS.md",
    "PUBLIC-RELEASE-METADATA.md",
    "PUBLIC-ROADMAP.md",
    "pyproject.toml",
    "QUICKSTART.md",
    "README.md",
    "RELEASE-CHECKLIST.md",
    "ROADMAP.md",
    "SECURITY.md",
    "SUPPORT.md",
    "TOKEN-AUTOPILOT.md",
    "TOKEN-HARNESS.md",
    "TOKEN-SLICER.md",
    "TAILTRAIL-COMMANDS.md",
    "TAILTRAIL-PITCH.md",
    "tailtrail-registry.json",
    "tailtrail-registry.schema.json",
    "tailtrail_cli.py",
    "tailtrail-policy.example.md",
    "tailtrail-meta/README.md",
    "tailtrail-meta/harness-summary.schema.json",
    "USEFUL-PROMPTS.md",
    "USER-GUIDE.md",
    "V2-IMPLEMENTATION-GUIDE.md",
    "VERSIONING.md",
    "adapters/README.md",
    "adapters/chatgpt-instructions.md",
    "adapters/claude.md",
    "adapters/copilot-instructions.md",
    "adapters/cursor.mdc",
    "adapters/gemini.md",
    "adapters/prompts/chatgpt.md",
    "adapters/prompts/claude.md",
    "adapters/prompts/codex.md",
    "adapters/prompts/copilot.md",
    "adapters/prompts/cursor.md",
    "adapters/prompts/gemini.md",
    "benchmarks/README.md",
    "benchmarks/evaluation/README.md",
    "benchmarks/evaluation/results/.gitkeep",
    "benchmarks/evaluation/scenarios/buildweek-validation/README.md",
    "benchmarks/evaluation/scenarios/buildweek-validation/baseline-artifact.md",
    "benchmarks/evaluation/scenarios/buildweek-validation/expected.json",
    "benchmarks/evaluation/scenarios/buildweek-validation/scenario.json",
    "benchmarks/evaluation/scenarios/buildweek-validation/tailtrail-artifact.md",
    "benchmarks/evaluation/scenarios/ci-failure/baseline-artifact.md",
    "benchmarks/evaluation/scenarios/ci-failure/expected.json",
    "benchmarks/evaluation/scenarios/ci-failure/scenario.json",
    "benchmarks/evaluation/scenarios/ci-failure/tailtrail-artifact.md",
    "benchmarks/evaluation/scenarios/dependency-decision/baseline-artifact.md",
    "benchmarks/evaluation/scenarios/dependency-decision/expected.json",
    "benchmarks/evaluation/scenarios/dependency-decision/scenario.json",
    "benchmarks/evaluation/scenarios/dependency-decision/tailtrail-artifact.md",
    "benchmarks/evaluation/scenarios/review-only/baseline-artifact.md",
    "benchmarks/evaluation/scenarios/review-only/expected.json",
    "benchmarks/evaluation/scenarios/review-only/scenario.json",
    "benchmarks/evaluation/scenarios/review-only/tailtrail-artifact.md",
    "benchmarks/evaluation/scenarios/security-triage/baseline-artifact.md",
    "benchmarks/evaluation/scenarios/security-triage/expected.json",
    "benchmarks/evaluation/scenarios/security-triage/scenario.json",
    "benchmarks/evaluation/scenarios/security-triage/tailtrail-artifact.md",
    "benchmarks/evaluation/scenarios/validation-bug/baseline-artifact.md",
    "benchmarks/evaluation/scenarios/validation-bug/expected.json",
    "benchmarks/evaluation/scenarios/validation-bug/scenario.json",
    "benchmarks/evaluation/scenarios/validation-bug/tailtrail-artifact.md",
    "benchmarks/results/.gitkeep",
    "benchmarks/efficacy/governance-remediation/baseline-artifact.md",
    "benchmarks/efficacy/governance-remediation/expected.json",
    "benchmarks/efficacy/governance-remediation/scenario.md",
    "benchmarks/efficacy/governance-remediation/tailtrail-artifact.md",
    "benchmarks/efficacy/governance-remediation/token-usage.jsonl",
    "benchmarks/efficacy/bug-fix-focused-tests/baseline-artifact.md",
    "benchmarks/efficacy/bug-fix-focused-tests/expected.json",
    "benchmarks/efficacy/bug-fix-focused-tests/scenario.md",
    "benchmarks/efficacy/bug-fix-focused-tests/tailtrail-artifact.md",
    "benchmarks/efficacy/bug-fix-focused-tests/token-usage.jsonl",
    "benchmarks/efficacy/ci-sonar-failure/baseline-artifact.md",
    "benchmarks/efficacy/ci-sonar-failure/expected.json",
    "benchmarks/efficacy/ci-sonar-failure/scenario.md",
    "benchmarks/efficacy/ci-sonar-failure/tailtrail-artifact.md",
    "benchmarks/efficacy/ci-sonar-failure/token-usage.jsonl",
    "benchmarks/efficacy/cross-file-feature/baseline-artifact.md",
    "benchmarks/efficacy/cross-file-feature/expected.json",
    "benchmarks/efficacy/cross-file-feature/scenario.md",
    "benchmarks/efficacy/cross-file-feature/tailtrail-artifact.md",
    "benchmarks/efficacy/dependency-decision/baseline-artifact.md",
    "benchmarks/efficacy/dependency-decision/expected.json",
    "benchmarks/efficacy/dependency-decision/scenario.md",
    "benchmarks/efficacy/dependency-decision/tailtrail-artifact.md",
    "benchmarks/efficacy/dependency-decision/token-usage.jsonl",
    "benchmarks/efficacy/learning-meta-harness-governance/baseline-artifact.md",
    "benchmarks/efficacy/learning-meta-harness-governance/expected.json",
    "benchmarks/efficacy/learning-meta-harness-governance/scenario.md",
    "benchmarks/efficacy/learning-meta-harness-governance/tailtrail-artifact.md",
    "benchmarks/efficacy/review-only/baseline-artifact.md",
    "benchmarks/efficacy/review-only/expected.json",
    "benchmarks/efficacy/review-only/scenario.md",
    "benchmarks/efficacy/review-only/tailtrail-artifact.md",
    "benchmarks/efficacy/review-only/token-usage.jsonl",
    "benchmarks/efficacy/security-vulnerability-triage/baseline-artifact.md",
    "benchmarks/efficacy/security-vulnerability-triage/expected.json",
    "benchmarks/efficacy/security-vulnerability-triage/scenario.md",
    "benchmarks/efficacy/security-vulnerability-triage/tailtrail-artifact.md",
    "benchmarks/efficacy/security-vulnerability-triage/token-usage.jsonl",
    "benchmarks/efficacy/token-heavy-artifact/baseline-artifact.md",
    "benchmarks/efficacy/token-heavy-artifact/expected.json",
    "benchmarks/efficacy/token-heavy-artifact/scenario.md",
    "benchmarks/efficacy/token-heavy-artifact/tailtrail-artifact.md",
    "benchmarks/efficacy/README.md",
    "benchmarks/scenarios/ci-sonar-review/baseline-output.md",
    "benchmarks/scenarios/ci-sonar-review/expected.json",
    "benchmarks/scenarios/ci-sonar-review/scenario.md",
    "benchmarks/scenarios/ci-sonar-review/tailtrail-output.md",
    "benchmarks/scenarios/native-date-field/baseline-output.md",
    "benchmarks/scenarios/native-date-field/expected.json",
    "benchmarks/scenarios/native-date-field/scenario.md",
    "benchmarks/scenarios/native-date-field/tailtrail-output.md",
    "benchmarks/scenarios/preserve-validation/baseline-output.md",
    "benchmarks/scenarios/preserve-validation/expected.json",
    "benchmarks/scenarios/preserve-validation/scenario.md",
    "benchmarks/scenarios/preserve-validation/tailtrail-output.md",
    "benchmarks/scenarios/shared-bug-fix/baseline-output.md",
    "benchmarks/scenarios/shared-bug-fix/expected.json",
    "benchmarks/scenarios/shared-bug-fix/scenario.md",
    "benchmarks/scenarios/shared-bug-fix/tailtrail-output.md",
    "benchmarks/scenarios/start-command-ux/baseline-output.md",
    "benchmarks/scenarios/start-command-ux/expected.json",
    "benchmarks/scenarios/start-command-ux/scenario.md",
    "benchmarks/scenarios/start-command-ux/tailtrail-output.md",
    "benchmarks/guardrail-precision/README.md",
    "benchmarks/guardrail-precision/thresholds.json",
    "buildweek-demo-project/.gitignore",
    "buildweek-demo-project/DEMO-RUNBOOK.md",
    "buildweek-demo-project/DEMO-PROMPTS.md",
    "buildweek-demo-project/FEATURE-COVERAGE.md",
    "buildweek-demo-project/README.md",
    "buildweek-demo-project/SUBMISSION-NOTES.md",
    "buildweek-demo-project/logs/ci-failure.log",
    "buildweek-demo-project/logs/sonar-sample.log",
    "buildweek-demo-project/logs/trivy-sample.json",
    "buildweek-demo-project/src/claims_api/__init__.py",
    "buildweek-demo-project/src/claims_api/models.py",
    "buildweek-demo-project/src/claims_api/service.py",
    "buildweek-demo-project/src/claims_api/validation.py",
    "buildweek-demo-project/tailtrail-meta/providers/sample-semantic.json",
    "buildweek-demo-project/tailtrail-policy.md",
    "buildweek-demo-project/tests/test_claim_validation.py",
    "aidlc/extensions/security-baseline.md",
    "aidlc/extensions/testing-baseline.md",
    "aidlc/stages/README.md",
    "aidlc/stages/build-test.md",
    "aidlc/stages/design.md",
    "aidlc/stages/handoff.md",
    "aidlc/stages/implementation.md",
    "aidlc/stages/operations.md",
    "aidlc/stages/requirements.md",
    "aidlc/stages/reverse-engineering.md",
    "aidlc/stages/workflow-planning.md",
    "aidlc/stages/workspace-detection.md",
    "assets/README.md",
    "assets/tailtrail-logo.svg",
    "assets/tailtrail-mark.svg",
    "context/TailTrail.map.md",
    "context/cache-index.md",
    "context/change-impact.md",
    "context/code-graph-mapper.md",
    "context/compression-policy.md",
    "context/cross-repo-reference.md",
    "context/flow-catalog.md",
    "context/guardrail-layers.md",
    "context/graph-aware-learning.md",
    "context/intent-aliases.md",
    "context/learning-agent.md",
    "context/learning-refresh.md",
    "context/navigator.md",
    "context/project-map.md",
    "context/quality-loop.md",
    "context/prune-rules.md",
    "context/review-lenses.md",
    "context/slices.md",
    "context/token-router.md",
    "examples/native-date-field.md",
    "examples/preserve-guard.md",
    "examples/shared-bug-fix.md",
    "examples/stdlib-csv.md",
    "hooks/README.md",
    "hooks/learning-capture-hook.py",
    "hooks/tailtrail-lifecycle-hook.py",
    "hooks/token-autopilot-hook.py",
    "hooks/token-router-hook.py",
    "scripts/aidlc-check.py",
    "scripts/aidlc-init.py",
    "scripts/analyze-benchmark.py",
    "scripts/ast-map.py",
    "scripts/benchmark-tailtrail.py",
    "scripts/bootstrap-snapshot.py",
    "scripts/check-tailtrail.py",
    "scripts/ci-summary.py",
    "scripts/cache-summary.py",
    "scripts/code-graph-mapper.py",
    "scripts/context-receipt.py",
    "scripts/context_receipt.py",
    "scripts/cross-repo-reference.py",
    "scripts/expand-intent.py",
    "scripts/export-release.py",
    "scripts/efficacy-benchmark.py",
    "scripts/efficacy-run.py",
    "scripts/evaluation-audit.py",
    "scripts/evaluation-harness.py",
    "scripts/graph-learning.py",
    "scripts/guardrail-check.py",
    "scripts/guardrail-precision.py",
    "scripts/harness-review.py",
    "scripts/meta-harness-analyze.py",
    "scripts/meta-harness-propose.py",
    "scripts/mcp-server.py",
    "scripts/install-copilot.py",
    "scripts/install-launcher.py",
    "scripts/install-local.py",
    "scripts/install_surfaces.py",
    "scripts/learning-agent.py",
    "scripts/learning-review.py",
    "scripts/learning-refresh.py",
    "scripts/learnings.py",
    "scripts/navigator.py",
    "scripts/navigator_core.py",
    "scripts/navigator_render.py",
    "scripts/outcome-telemetry.py",
    "scripts/policy-check.py",
    "scripts/prompt-profile.py",
    "scripts/prompt_profile.py",
    "scripts/public-doc-audit.py",
    "scripts/quality-run.py",
    "scripts/quality-loop.py",
    "scripts/quality-scan.py",
    "scripts/review-graph.py",
    "scripts/review-run.py",
    "scripts/scanner-graph-overlay.py",
    "scripts/release-check.py",
    "scripts/setup-scan.py",
    "scripts/smoke-test.py",
    "scripts/prune-context.py",
    "scripts/route-context.py",
    "scripts/slice-context.py",
    "scripts/sonar-summary.py",
    "scripts/summarize-output.py",
    "scripts/sync-adapters.py",
    "scripts/sync-governance.py",
    "scripts/task-start.py",
    "scripts/task-next.py",
    "scripts/tailtrail.py",
    "scripts/tailtrail-registry.py",
    "scripts/registry-drift.py",
    "scripts/tailtrail-report.py",
    "scripts/team-init.py",
    "scripts/test-precision.py",
    "scripts/token-auto.py",
    "scripts/token-budget-coach.py",
    "scripts/token_budget_coach.py",
    "scripts/token-harness.py",
    "scripts/token-harness-bridge.py",
    "scripts/token-harness-ledger.py",
    "scripts/token-harness-proof.py",
    "scripts/token-harness-reduce.py",
    "scripts/token-telemetry.py",
    "scripts/token_telemetry.py",
    "scripts/token-savings.py",
    "scripts/update-copilot.py",
    "scripts/update-tailtrail.py",
    "scripts/validation-summary.py",
    "scripts/vulnerability-run.py",
    "scripts/vulnerability-scan.py",
    "scripts/vulnerability-summary.py",
    "skills/tailtrail/SKILL.md",
    "skills/tailtrail-review/SKILL.md",
    "schemas/evaluation-harness-event.schema.json",
    "schemas/token-harness-bridge-input.schema.json",
    "schemas/token-harness-bridge-output.schema.json",
    "templates/context-brief.md",
    "templates/aidlc-audit.md",
    "templates/aidlc-state.md",
    "templates/behavior-analysis.md",
    "templates/benchmark-result.md",
    "templates/change-brief.md",
    "templates/ci-summary.md",
    "templates/code-graph-map.md",
    "templates/command-result.md",
    "templates/diff-handoff.md",
    "templates/evidence-note.md",
    "templates/enterprise-report.md",
    "templates/efficacy-result.md",
    "templates/evaluation-result.md",
    "templates/graph-learning.md",
    "templates/guardrail-finding.md",
    "templates/impact-brief.md",
    "templates/intent-overrides.json",
    "templates/implementation-plan.md",
    "templates/learnings.md",
    "templates/learning-signal.md",
    "templates/learning-refresh-report.md",
    "templates/meta-harness-proposal.md",
    "templates/operations-notes.md",
    "templates/outcome-event.md",
    "templates/policy-overrides.json",
    "templates/question-file.md",
    "templates/quality-run.md",
    "templates/quality-event.md",
    "templates/quality-review.md",
    "templates/quality-scan.md",
    "templates/risk-callout.md",
    "templates/requirements.md",
    "templates/review-graph.md",
    "templates/review-finding.md",
    "templates/review-result.md",
    "templates/router-decision.md",
    "templates/sonar-summary.md",
    "templates/stage-gate.md",
    "templates/tailtrail-gitignore.md",
    "templates/tool-summary.md",
    "templates/token-savings-report.md",
    "templates/token-usage-example.jsonl",
    "templates/validation-handoff.md",
    "templates/value-report.csv",
    "templates/vulnerability-remediation.md",
    "templates/vulnerability-summary.md",
    "templates/workflow-recommendation.md",
    "templates/workflow-plan.md",
    "tailtrail-meta/code-graph-cache.json",
    "reports/evaluation-harness/.gitkeep",
    "tests/test_context_receipt.py",
    "tests/test_deterministic_tools.py",
    "tests/test_cli_dispatch.py",
    "tests/test_efficacy_run.py",
    "tests/test_evaluation_audit.py",
    "tests/test_evaluation_harness_events.py",
    "tests/test_evaluation_harness_router.py",
    "tests/test_evaluation_harness_scenarios.py",
    "tests/test_meta_harness.py",
    "tests/test_meta_harness_token_feedback.py",
    "tests/test_mcp_server.py",
    "tests/golden/navigator_repo_overview.md",
    "tests/test_navigator_core.py",
    "tests/test_packaging_entry_point.py",
    "tests/test_guardrail_check.py",
    "tests/test_guardrail_precision.py",
    "tests/test_install_profiles.py",
    "tests/test_governance_sync.py",
    "tests/test_task_next.py",
    "tests/test_tailtrail_registry.py",
    "tests/test_registry_drift.py",
    "tests/test_token_harness.py",
    "tests/test_token_harness_bridge.py",
    "tests/test_token_harness_ledger.py",
    "tests/test_token_harness_proof.py",
    "tests/test_token_harness_reduce.py",
    "tests/test_review_output.py",
    "tests/test_review_scope.py",
    "tests/fixtures/guardrail/dependency-bad.diff",
    "tests/fixtures/guardrail/dependency-good.diff",
    "tests/fixtures/guardrail/formatting-good.diff",
    "tests/fixtures/guardrail/local-state-bad.diff",
    "tests/fixtures/guardrail/safeguard-bad.diff",
    "tests/fixtures/guardrail/todo-delete-good.diff",
    "tests/fixtures/guardrail/validation-bad.txt",
    "tests/fixtures/guardrail/validation-good.txt",
}
PUBLIC_EXPORT_EXCLUDED_FILES = {
    "ADMIN-RELEASE-MODES.md",
    "DESIGN.md",
    "scripts/export-release.py",
}
ALLOWED_EXTENSION_PREFIXES = (
    "benchmarks/guardrail-precision/fixtures/",
    "demo-project-layout/",
)

errors: list[str] = []


def fail(message: str) -> None:
    errors.append(f"TailTrail check failed: {message}")


def read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def list_files() -> list[str]:
    files: list[str] = []
    for path in ROOT.rglob("*"):
        if ".git" in path.parts:
            continue
        if "aidlc-rules" in path.parts:
            continue
        if ".tailtrail" in path.parts:
            continue
        if ".idea" in path.parts:
            continue
        if "__pycache__" in path.parts:
            continue
        if "benchmarks" in path.parts and "results" in path.parts and path.name != ".gitkeep":
            continue
        if path.name == ".DS_Store":
            continue
        if path.is_file():
            files.append(path.relative_to(ROOT).as_posix())
    return sorted(files)


def check_manifest() -> None:
    manifest = json.loads(read(".codex-plugin/plugin.json"))

    if manifest.get("name") != "tailtrail":
        fail("plugin name must be tailtrail")
    if manifest.get("skills") != "./skills/":
        fail("plugin skills path must be ./skills/")

    prompts = manifest.get("interface", {}).get("defaultPrompt", [])
    if not any("@tailtrail-review" in prompt for prompt in prompts):
        fail("plugin default prompts should mention @tailtrail-review")
    if not any("strict" in prompt for prompt in prompts):
        fail("plugin default prompts should mention strict mode")


def check_skill(relative_path: str, expected_name: str) -> None:
    body = read(relative_path)
    match = re.match(r"^---\n([\s\S]*?)\n---\n", body)

    if not match:
        fail(f"{relative_path} is missing YAML frontmatter")
        return

    frontmatter = match.group(1)
    if f"name: {expected_name}" not in frontmatter:
        fail(f"{relative_path} must declare name: {expected_name}")
    if "description: " not in frontmatter:
        fail(f"{relative_path} is missing a description")


def check_expected_files() -> None:
    files = set(list_files())
    expected_files = set(EXPECTED_FILES)
    if (ROOT / ".tailtrail-public-release").exists():
        expected_files -= PUBLIC_EXPORT_EXCLUDED_FILES
        expected_files.add(".tailtrail-public-release")

    for expected_file in sorted(expected_files):
        if expected_file not in files:
            fail(f"missing {expected_file}")

    for file in sorted(files):
        if file.startswith(ALLOWED_EXTENSION_PREFIXES):
            continue
        if file not in expected_files:
            fail(f"unexpected file {file}")


def check_content() -> None:
    unfinished_marker = "TO" + "DO"
    unfinished_pattern = re.compile(rf"\[{unfinished_marker}|{unfinished_marker}:", re.IGNORECASE)

    for file in list_files():
        body = read(file)
        if unfinished_pattern.search(body):
            fail(f"{file} contains an unfinished placeholder")
        if "\t" in body:
            fail(f"{file} contains tab indentation")


def check_python_scripts() -> None:
    for file in (
        "scripts/aidlc-check.py",
        "scripts/aidlc-init.py",
        "scripts/analyze-benchmark.py",
        "scripts/ast-map.py",
        "scripts/benchmark-tailtrail.py",
        "scripts/ci-summary.py",
        "scripts/cache-summary.py",
        "scripts/code-graph-mapper.py",
        "scripts/context-receipt.py",
        "scripts/context_receipt.py",
        "scripts/cross-repo-reference.py",
        "scripts/efficacy-benchmark.py",
        "scripts/efficacy-run.py",
        "scripts/evaluation-audit.py",
        "scripts/evaluation-harness.py",
        "scripts/expand-intent.py",
        "scripts/export-release.py",
        "scripts/graph-learning.py",
        "scripts/guardrail-check.py",
        "scripts/guardrail-precision.py",
        "scripts/harness-review.py",
        "scripts/meta-harness-analyze.py",
        "scripts/meta-harness-propose.py",
        "scripts/mcp-server.py",
        "scripts/install-copilot.py",
        "scripts/install-launcher.py",
        "scripts/install-local.py",
        "scripts/install_surfaces.py",
        "scripts/learning-agent.py",
        "scripts/learning-review.py",
        "scripts/learning-refresh.py",
        "scripts/learnings.py",
        "scripts/navigator.py",
        "scripts/navigator_core.py",
        "scripts/navigator_render.py",
        "scripts/outcome-telemetry.py",
        "scripts/policy-check.py",
        "scripts/prompt-profile.py",
        "scripts/prompt_profile.py",
        "scripts/public-doc-audit.py",
        "scripts/quality-run.py",
        "scripts/quality-loop.py",
        "scripts/quality-scan.py",
        "scripts/review-graph.py",
        "scripts/review-run.py",
        "scripts/scanner-graph-overlay.py",
        "scripts/release-check.py",
        "scripts/setup-scan.py",
        "scripts/smoke-test.py",
        "scripts/prune-context.py",
        "scripts/route-context.py",
        "scripts/slice-context.py",
        "scripts/sonar-summary.py",
        "scripts/summarize-output.py",
        "scripts/sync-adapters.py",
        "scripts/sync-governance.py",
        "scripts/task-start.py",
        "scripts/task-next.py",
        "scripts/tailtrail.py",
        "scripts/tailtrail-registry.py",
        "scripts/registry-drift.py",
        "scripts/tailtrail-report.py",
        "scripts/team-init.py",
        "scripts/test-precision.py",
        "scripts/token-auto.py",
        "scripts/token-budget-coach.py",
        "scripts/token_budget_coach.py",
        "scripts/token-harness.py",
        "scripts/token-harness-bridge.py",
        "scripts/token-harness-ledger.py",
        "scripts/token-harness-proof.py",
        "scripts/token-harness-reduce.py",
        "scripts/token-telemetry.py",
        "scripts/token_telemetry.py",
        "scripts/token-savings.py",
        "scripts/update-copilot.py",
        "scripts/update-tailtrail.py",
        "scripts/validation-summary.py",
        "scripts/vulnerability-run.py",
        "scripts/vulnerability-scan.py",
        "scripts/vulnerability-summary.py",
        "tailtrail_cli.py",
        "hooks/token-autopilot-hook.py",
        "hooks/learning-capture-hook.py",
        "hooks/tailtrail-lifecycle-hook.py",
        "hooks/token-router-hook.py",
    ):
        if not (ROOT / file).is_file():
            continue
        body = read(file)
        if "from __future__ import annotations" not in body:
            fail(f"{file} should use modern annotation behavior")
        if "subprocess.run" in body and "check=False" not in body:
            fail(f"{file} should handle subprocess errors explicitly")


def check_guardrails() -> None:
    required_links = [
        "AGENTS.md",
        "AIDLC.md",
        "DEPENDENCY-GATE.md",
        "TOKEN-SLICER.md",
        "context/slices.md",
        "skills/tailtrail/SKILL.md",
        "skills/tailtrail-review/SKILL.md",
        "scripts/expand-intent.py",
        "adapters/claude.md",
        "adapters/copilot-instructions.md",
        "adapters/cursor.mdc",
        "adapters/chatgpt-instructions.md",
        "adapters/gemini.md",
    ]
    for file in required_links:
        if "GUARDRAILS.md" not in read(file):
            fail(f"{file} should link to GUARDRAILS.md")

    guardrails = read("GUARDRAILS.md")
    for phrase in (
        "Do not act with more certainty than the evidence supports.",
        "Do not claim tests passed unless they were run and succeeded.",
        "Token saving must not hide material facts.",
    ):
        if phrase not in guardrails:
            fail(f"GUARDRAILS.md missing guardrail phrase: {phrase}")

    layers = read("context/guardrail-layers.md")
    for phrase in (
        "Guardrail Layers are compact task-specific reminders.",
        "## Code Consistency Layer",
        "Match existing naming conventions",
        "## QA / Validation Layer",
        "## CI / Sonar Layer",
        "## Release Layer",
        "Token saving must never hide material facts",
    ):
        if phrase not in layers:
            fail(f"context/guardrail-layers.md missing layer phrase: {phrase}")

    for file in (
        "context/slices.md",
        "context/TailTrail.map.md",
        "context/token-router.md",
        "scripts/route-context.py",
        "scripts/expand-intent.py",
        "README.md",
        "USER-GUIDE.md",
        "DESIGN.md",
    ):
        if not (ROOT / file).is_file():
            continue
        if "context/guardrail-layers.md" not in read(file):
            fail(f"{file} should mention context/guardrail-layers.md")


def check_policy_template() -> None:
    body = read("tailtrail-policy.example.md")
    for phrase in (
        "Copy this file to `tailtrail-policy.md`",
        "This file is guidance, not a hidden policy engine.",
        "If a command is unknown, say it is unknown instead of inventing one.",
    ):
        if phrase not in body:
            fail(f"tailtrail-policy.example.md missing policy phrase: {phrase}")

    overrides = json.loads(read("templates/policy-overrides.json"))
    for key in (
        "schema_version",
        "dependency_policy",
        "validation",
        "security",
        "ci_sonar",
        "ownership",
        "boundaries",
        "data_privacy",
        "release",
    ):
        if key not in overrides:
            fail(f"templates/policy-overrides.json missing key: {key}")

    for file in (
        "AGENTS.md",
        "AIDLC.md",
        "DEPENDENCY-GATE.md",
        "context/slices.md",
        "skills/tailtrail/SKILL.md",
        "skills/tailtrail-review/SKILL.md",
        "adapters/claude.md",
        "adapters/copilot-instructions.md",
        "adapters/cursor.mdc",
        "adapters/chatgpt-instructions.md",
        "adapters/gemini.md",
    ):
        if "tailtrail-policy.md" not in read(file):
            fail(f"{file} should mention tailtrail-policy.md")


def check_adapter_sync() -> None:
    adapters = {
        "adapters/claude.md": "CLAUDE.md",
        "adapters/cursor.mdc": ".cursor/rules/tailtrail.mdc",
        "adapters/copilot-instructions.md": ".github/copilot-instructions.md",
        "adapters/chatgpt-instructions.md": ".openai/chatgpt-instructions.md",
        "adapters/gemini.md": "GEMINI.md",
    }

    for source, target in adapters.items():
        if read(source) != read(target):
            fail(f"{target} must match {source}")


def check_governance_sync() -> None:
    import importlib.util

    script_path = ROOT / "scripts" / "sync-governance.py"
    spec = importlib.util.spec_from_file_location("tailtrail_sync_governance_check", script_path)
    if spec is None or spec.loader is None:
        fail("unable to load scripts/sync-governance.py")
        return

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for error in module.check():
        fail(error)


def check_registry_drift_advisory() -> None:
    import importlib.util

    script_path = ROOT / "scripts" / "registry-drift.py"
    spec = importlib.util.spec_from_file_location("tailtrail_registry_drift_check", script_path)
    if spec is None or spec.loader is None:
        fail("unable to load scripts/registry-drift.py")
        return

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    report = module.collect_drift(ROOT)
    blocking = [
        issue
        for issue in report.get("issues", [])
        if issue.get("category") in {"registry", "claims"}
    ]
    for issue in blocking:
        fail(f"registry drift {issue.get('category')}: {issue.get('message')}")


def main() -> int:
    check_expected_files()
    check_manifest()
    check_skill("skills/tailtrail/SKILL.md", "tailtrail")
    check_skill("skills/tailtrail-review/SKILL.md", "tailtrail-review")
    check_content()
    check_python_scripts()
    check_guardrails()
    check_policy_template()
    check_governance_sync()
    check_adapter_sync()
    check_registry_drift_advisory()

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    print("TailTrail check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
