from __future__ import annotations

import ast
import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

WRAPPER_PAIRS = {
    "scripts/context-receipt.py": "context_receipt",
    "scripts/prompt-profile.py": "prompt_profile",
    "scripts/token-budget-coach.py": "token_budget_coach",
    "scripts/token-telemetry.py": "token_telemetry",
}

USER_FACING_DOCS = (
    "INSTALL.md",
    "README.md",
    "QUICKSTART.md",
    "CHEATSHEET.md",
    "TAILTRAIL-COMMANDS.md",
    "USER-GUIDE.md",
    "USEFUL-PROMPTS.md",
    "demo-project-layout/tailtrail-demo-workspace/tailtrail/USER-GUIDE.md",
)

TAILTRAIL_DISPATCH = {
    "budget": "token-budget-coach.py",
    "profile": "prompt-profile.py",
    "receipt": "context-receipt.py",
    "telemetry": "token-telemetry.py",
    "token-harness": "token-harness.py",
    "failure": "execution-failure.py",
}


class CliDispatchTests(unittest.TestCase):
    def test_start_without_a_goal_shows_feature_overview(self) -> None:
        result = subprocess.run(
            [sys.executable, (ROOT / "scripts" / "tailtrail.py").as_posix(), "start"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("# TailTrail Start", result.stdout)
        self.assertIn("## Main Feature Groups", result.stdout)
        self.assertIn("Navigator", result.stdout)
        self.assertIn("Evaluation Harness", result.stdout)

    def test_hyphen_wrappers_delegate_to_importable_modules(self) -> None:
        for wrapper, module in WRAPPER_PAIRS.items():
            with self.subTest(wrapper=wrapper):
                tree = ast.parse((ROOT / wrapper).read_text(encoding="utf-8"))
                imports = [node for node in tree.body if isinstance(node, ast.ImportFrom) and node.module == module]
                self.assertEqual(len(imports), 1)
                self.assertEqual([alias.name for alias in imports[0].names], ["main"])
                comments = (ROOT / wrapper).read_text(encoding="utf-8")
                self.assertIn("Thin CLI wrapper", comments)
                function_defs = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
                self.assertEqual(function_defs, [], f"{wrapper} should stay a thin CLI wrapper")

    def test_tailtrail_dispatch_uses_public_hyphenated_wrappers(self) -> None:
        body = (ROOT / "scripts" / "tailtrail.py").read_text(encoding="utf-8")
        for command, wrapper in TAILTRAIL_DISPATCH.items():
            with self.subTest(command=command):
                self.assertIn(f'if command == "{command}":', body)
                self.assertIn(f'return run_script("{wrapper}", args)', body)

    def test_install_codex_routes_to_the_codex_profile(self) -> None:
        body = (ROOT / "scripts" / "tailtrail.py").read_text(encoding="utf-8")
        self.assertIn('if action == "codex":', body)
        self.assertIn('return run_script("install-local.py", ["--profile", "codex", *rest])', body)

    def test_install_codex_plugin_routes_to_the_codex_plugin_profile(self) -> None:
        body = (ROOT / "scripts" / "tailtrail.py").read_text(encoding="utf-8")
        self.assertIn('if action == "codex-plugin":', body)
        self.assertIn('return run_script("install-local.py", ["--profile", "codex-plugin", *rest])', body)

    def test_install_claude_routes_to_the_claude_profile(self) -> None:
        body = (ROOT / "scripts" / "tailtrail.py").read_text(encoding="utf-8")
        self.assertIn('if action == "claude":', body)
        self.assertIn('return run_script("install-local.py", ["--profile", "claude", *rest])', body)

    def test_completion_report_has_a_public_harness_dispatch(self) -> None:
        body = (ROOT / "scripts" / "tailtrail.py").read_text(encoding="utf-8")
        self.assertIn('if args and args[0] == "completion-report":', body)
        self.assertIn('return run_script("completion-report.py", args[1:])', body)
        self.assertIn('if command == "completion-report":', body)
        self.assertIn('return run_script("completion-report.py", args)', body)

    def test_public_benchmark_has_explicit_cli_dispatches(self) -> None:
        body = (ROOT / "scripts" / "tailtrail.py").read_text(encoding="utf-8")
        self.assertIn('if args and args[0] == "run-public":', body)
        self.assertIn('return run_script("public-benchmark.py", ["run", *args[1:]])', body)
        self.assertIn('if args and args[0] == "capture-model-run":', body)
        self.assertIn('return run_script("public-benchmark.py", ["capture", *args[1:]])', body)

    def test_interactive_plan_mode_has_a_public_planning_dispatch(self) -> None:
        body = (ROOT / "scripts" / "tailtrail.py").read_text(encoding="utf-8")
        self.assertIn('if args and args[0] in {"discuss", "explain", "discussion-show", "decision-show"}:', body)
        self.assertIn('return run_script("planning-discussion.py", args)', body)
        self.assertIn('if args and args[0] in {"investigate", "investigation-show"}:', body)
        self.assertIn('return run_script("planning-investigation.py", investigation_args)', body)
        self.assertIn('"feature-controls-show", "feature-controls-propose", "feature-controls-approve"', body)
        self.assertIn('return run_script("planning-revision.py", revision_args)', body)

    def test_official_aidlc_status_has_a_public_dispatch(self) -> None:
        body = (ROOT / "scripts" / "tailtrail.py").read_text(encoding="utf-8")
        self.assertIn('if action == "official":', body)
        self.assertIn('return run_script("aidlc-official-install.py", rest[1:])', body)
        self.assertIn('return run_script("aidlc-official-host.py", rest[1:])', body)
        self.assertIn('return run_script("aidlc-official-detect.py", rest)', body)
        self.assertIn('return run_script("aidlc-official-bridge.py", rest[1:])', body)
        self.assertIn('return run_script("official-aidlc-state.py", rest[1:])', body)
        self.assertIn('return run_script("official-aidlc-sanitize.py", rest[1:])', body)
        self.assertIn('return run_script("official-aidlc-runtime.py", rest[1:])', body)

    def test_host_runtime_conformance_has_a_public_dispatch(self) -> None:
        body = (ROOT / "scripts" / "tailtrail.py").read_text(encoding="utf-8")
        self.assertIn('if action == "runtime":', body)
        self.assertIn('return run_script("host-runtime-conformance.py", rest)', body)

    def test_closure_commands_have_contract_and_recorder_dispatches(self) -> None:
        body = (ROOT / "scripts" / "tailtrail.py").read_text(encoding="utf-8")
        self.assertIn('if command == "closure":', body)
        self.assertIn('"finalize": "closure-finalizer.py"', body)
        self.assertIn('"correct": "closure-correction.py"', body)

    def test_first_run_has_a_public_dispatch(self) -> None:
        body = (ROOT / "scripts" / "tailtrail.py").read_text(encoding="utf-8")
        self.assertIn('if command == "first-run":', body)
        self.assertIn('return run_script("first-run.py", args)', body)

    def test_ui_discovery_has_a_public_dispatch(self) -> None:
        body = (ROOT / "scripts" / "tailtrail.py").read_text(encoding="utf-8")
        self.assertIn('if command == "ui":', body)
        self.assertIn('return run_script("ui-consistency.py", args)', body)

    def test_target_workspace_has_a_public_dispatch(self) -> None:
        body = (ROOT / "scripts" / "tailtrail.py").read_text(encoding="utf-8")
        self.assertIn('if command == "target":', body)
        self.assertIn('return run_script("target_workspace.py", args)', body)

    def test_durable_workflow_runtime_has_a_public_dispatch(self) -> None:
        body = (ROOT / "scripts" / "tailtrail.py").read_text(encoding="utf-8")
        self.assertIn('if command == "workflow":', body)
        self.assertIn('return workflow(args)', body)
        self.assertIn('{"bind", "show", "validate", "capabilities", "task", "storage", "state", "compile", "approvals", "evidence", "vertical", "adapters", "execute", "freshness", "retry", "resume", "correction"}', body)

    def test_spec_kit_policy_has_a_public_dispatch(self) -> None:
        body = (ROOT / "scripts" / "tailtrail.py").read_text(encoding="utf-8")
        self.assertIn('if command in {"intent-bridge", "spec-kit"}:', body)
        self.assertIn('return run_script("spec-kit-policy.py", args[1:])', body)

    def test_spec_kit_detection_has_a_public_dispatch(self) -> None:
        body = (ROOT / "scripts" / "tailtrail.py").read_text(encoding="utf-8")
        self.assertIn('run_script("spec-kit-detect.py", args)', body)

    def test_spec_kit_import_has_a_public_dispatch(self) -> None:
        body = (ROOT / "scripts" / "tailtrail.py").read_text(encoding="utf-8")
        self.assertIn('run_script("spec-kit-import.py", args[1:])', body)

    def test_spec_kit_navigator_bridge_has_a_public_dispatch(self) -> None:
        body = (ROOT / "scripts" / "tailtrail.py").read_text(encoding="utf-8")
        self.assertIn('run_script("spec-kit-bridge.py", args[1:])', body)

    def test_spec_kit_slice_bridge_has_a_public_dispatch(self) -> None:
        body = (ROOT / "scripts" / "tailtrail.py").read_text(encoding="utf-8")
        self.assertIn('run_script("spec-kit-slices.py", args[1:])', body)

    def test_spec_kit_evidence_bridge_has_a_public_dispatch(self) -> None:
        body = (ROOT / "scripts" / "tailtrail.py").read_text(encoding="utf-8")
        self.assertIn('run_script("spec-kit-evidence.py", args[1:])', body)

    def test_spec_kit_amendment_bridge_has_a_public_dispatch(self) -> None:
        body = (ROOT / "scripts" / "tailtrail.py").read_text(encoding="utf-8")
        self.assertIn('run_script("spec-kit-amendment.py", args[1:])', body)

    def test_spec_kit_convergence_has_a_public_dispatch(self) -> None:
        body = (ROOT / "scripts" / "tailtrail.py").read_text(encoding="utf-8")
        self.assertIn('run_script("spec-kit-converge.py", args[1:])', body)

    def test_spec_kit_ci_receipt_has_a_public_dispatch(self) -> None:
        body = (ROOT / "scripts" / "tailtrail.py").read_text(encoding="utf-8")
        self.assertIn('run_script("spec-kit-integration.py", args[1:])', body)

    def test_spec_kit_ci_gate_has_a_public_dispatch(self) -> None:
        body = (ROOT / "scripts" / "tailtrail.py").read_text(encoding="utf-8")
        self.assertIn('run_script("spec-kit-ci-gate.py", args[1:])', body)

    def test_intent_bridge_alias_has_a_public_dispatch(self) -> None:
        body = (ROOT / "scripts" / "tailtrail.py").read_text(encoding="utf-8")
        self.assertIn('if command in {"intent-bridge", "spec-kit"}:', body)

    def test_spec_kit_observability_has_a_public_dispatch(self) -> None:
        body = (ROOT / "scripts" / "tailtrail.py").read_text(encoding="utf-8")
        self.assertIn('run_script("spec-kit-observability.py"', body)

    def test_user_facing_docs_do_not_advertise_importable_module_paths(self) -> None:
        for doc in USER_FACING_DOCS:
            with self.subTest(doc=doc):
                body = (ROOT / doc).read_text(encoding="utf-8")
                self.assertNotIn("scripts/context_receipt.py", body)
                self.assertNotIn("scripts/prompt_profile.py", body)
                self.assertNotIn("scripts/token_budget_coach.py", body)
                self.assertNotIn("scripts/token_telemetry.py", body)

    def test_do_alias_routes_to_start(self) -> None:
        result = subprocess.run(
            [sys.executable, (ROOT / "scripts" / "tailtrail.py").as_posix(), "do", "fix validation bug", "--format", "json"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["goal"], "fix validation bug")
        self.assertIn("navigator", report)
        self.assertEqual(report["planning_lock"]["status"], "awaiting-approval")
        self.assertFalse(report["planning_lock"]["writes_allowed"])
        self.assertIn("planning_report", report)
        self.assertEqual(report["next_step"], "Review the guided delivery plan, then approve or edit before implementation.")

    def test_free_form_task_routes_to_start(self) -> None:
        result = subprocess.run(
            [sys.executable, (ROOT / "scripts" / "tailtrail.py").as_posix(), "fix", "validation", "bug", "--format", "json"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["goal"], "fix validation bug")
        self.assertIn("navigator", report)
        self.assertEqual(report["planning_lock"]["status"], "awaiting-approval")
        self.assertFalse(report["planning_lock"]["writes_allowed"])
        self.assertEqual(report["next_step"], "Review the guided delivery plan, then approve or edit before implementation.")

    def test_known_review_command_still_dispatches_directly(self) -> None:
        result = subprocess.run(
            [sys.executable, (ROOT / "scripts" / "tailtrail.py").as_posix(), "review", "--help"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--scope", result.stdout)

    def test_adapters_check_dispatches_to_contract_check(self) -> None:
        result = subprocess.run(
            [sys.executable, (ROOT / "scripts" / "tailtrail.py").as_posix(), "adapters", "check"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Adapter sync passed.", result.stdout)


if __name__ == "__main__":
    unittest.main()
