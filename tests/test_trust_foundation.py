from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if SCRIPTS.as_posix() not in sys.path:
    sys.path.insert(0, SCRIPTS.as_posix())


def load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


first_run = load("trust_first_run", "scripts/first-run.py")
navigator = load("trust_navigator", "scripts/navigator.py")
task_start = load("trust_task_start", "scripts/task-start.py")


class TrustFoundationContractTests(unittest.TestCase):
    def test_auto_verify_detects_a_copilot_pack_and_runs_a_local_smoke_check(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)
            (target / ".github").mkdir()
            (target / ".github" / "copilot-instructions.md").write_text("guidance\n", encoding="utf-8")
            pack = target / "tailtrail"
            pack.mkdir()
            (pack / ".tailtrail-install.json").write_text(json.dumps({"surface": "core"}), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, (SCRIPTS / "tailtrail.py").as_posix(), "install", "verify", "--target", target.as_posix(), "--format", "json"],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["profile"], "copilot")
        self.assertEqual(payload["profile_selection"], "auto-detected")
        self.assertEqual(payload["installation"], "passed")
        self.assertEqual(payload["smoke"]["status"], "passed")

    def test_verify_reports_an_incomplete_install_without_mutating_the_target(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)
            result = first_run.check(target, "auto", "tailtrail")
        self.assertEqual(result["profile"], "generic")
        self.assertEqual(result["installation"], "incomplete")
        self.assertEqual(result["required"], ["AGENTS.md"])

    def test_aidlc_mode_contract_distinguishes_default_standard_and_full(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            plan = {"risk_indicators": []}
            self.assertEqual(task_start.aidlc_mode_selection("fix a typo", None, root, plan, None)["mode"], "lite")
            self.assertEqual(task_start.aidlc_mode_selection("use AIDLC to plan a payment change", None, root, plan, None)["mode"], "standard")
            self.assertEqual(task_start._aidlc_intent("use full AIDLC for this task".lower()), "full")

    def test_changed_scope_contract_excludes_tailtrail_state_but_keeps_project_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.assertFalse(navigator.is_actionable_changed_path(root, ".tailtrail/runs/run-1/approved.md"))
            self.assertFalse(navigator.is_actionable_changed_path(root, "scripts/__pycache__/navigator.cpython-313.pyc"))
            self.assertTrue(navigator.is_actionable_changed_path(root, "src/orders/service.py"))

    def test_planning_lock_contract_keeps_required_sections_and_never_runs_execution(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = task_start.build_report("fix zero quantity validation", root, ["src/order_service/validation.py"], "tailtrail")
            report["planning_lock"] = task_start.planning_lock.create(root, report["goal"], "trust-contract")
            rendered = task_start.compact_start_report(report)
        for heading in ("## Planning Lock", "## Scope", "## Requirements", "## Selected TailTrail features", "## Plan", "## Focused validation", "## Token posture", "## Approval"):
            self.assertIn(heading, rendered)
        self.assertIn("no source files, tests, scanners, or Git changes were run", rendered)

    def test_ci_workflow_covers_compile_contracts_registry_adapters_and_smoke(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "trust.yml").read_text(encoding="utf-8")
        for command in ("compileall", "unittest discover", "tailtrail-registry.py validate --strict", "tailtrail.py adapters check", "smoke-test.py"):
            self.assertIn(command, workflow)

    def test_cache_hygiene_ignores_python_and_platform_generated_files(self) -> None:
        ignored = (ROOT / ".gitignore").read_text(encoding="utf-8")
        for pattern in (".tailtrail/", "__pycache__/", "*.py[cod]", "__MACOSX/"):
            self.assertIn(pattern, ignored)

    def test_fresh_clone_smoke_excludes_local_runtime_state(self) -> None:
        smoke = (SCRIPTS / "smoke-test.py").read_text(encoding="utf-8")
        self.assertIn("git archive", smoke)
        for excluded in (".tailtrail", ".video-tools", "__MACOSX", "__pycache__"):
            self.assertIn(excluded, smoke)


if __name__ == "__main__":
    unittest.main()
