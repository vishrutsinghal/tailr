from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "dependency-decision.py"


def load_module():
    spec = importlib.util.spec_from_file_location("tailtrail_dependency_decision_test", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


dependency = load_module()


def decision(package: str = "requests", status: str = "approved") -> dict[str, object]:
    return {
        "schema_version": "1",
        "type": "tailtrail-dependency-decision",
        "decision_id": "DD-001",
        "status": status,
        "package": package,
        "version": "2.32.3",
        "manifest_paths": ["requirements.txt"],
        "problem": "HTTP client support is required for the approved integration.",
        "alternatives": ["Existing standard-library client", "Direct protocol implementation"],
        "rationale": "The package provides the required maintained client behavior.",
        "owner": "platform-team",
        "validation": ["python -m unittest discover -s tests -p test_*.py -v"],
        "rollback": "Remove the package and restore the prior request path.",
    }


DIFF = """diff --git a/requirements.txt b/requirements.txt
index 1234567..7654321 100644
--- a/requirements.txt
+++ b/requirements.txt
@@ -1 +1,2 @@
 existing==1.0.0
+requests==2.32.3
"""


class DependencyDecisionTests(unittest.TestCase):
    def test_added_dependency_requires_matching_approved_decision(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            missing = dependency.check(root, "tailtrail-meta/dependency-decisions", DIFF)
            self.assertEqual(missing["status"], "failed")
            self.assertEqual(missing["missing_decisions"][0]["package"], "requests")

            directory = root / "tailtrail-meta" / "dependency-decisions"
            directory.mkdir(parents=True)
            (directory / "DD-001.json").write_text(json.dumps(decision()), encoding="utf-8")
            matched = dependency.check(root, "tailtrail-meta/dependency-decisions", DIFF)
            self.assertEqual(matched["status"], "passed")
            self.assertEqual(matched["missing_decisions"], [])

    def test_deferred_or_rejected_record_cannot_authorize_dependency(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            directory = root / "tailtrail-meta" / "dependency-decisions"
            directory.mkdir(parents=True)
            (directory / "DD-001.json").write_text(json.dumps(decision(status="deferred")), encoding="utf-8")
            result = dependency.check(root, "tailtrail-meta/dependency-decisions", DIFF)
            self.assertEqual(result["status"], "failed")
            self.assertEqual(len(result["missing_decisions"]), 1)

    def test_invalid_record_fails_structure_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            directory = root / "tailtrail-meta" / "dependency-decisions"
            directory.mkdir(parents=True)
            item = decision()
            del item["rollback"]
            (directory / "DD-001.json").write_text(json.dumps(item), encoding="utf-8")
            _decisions, errors = dependency.read_decisions(root, "tailtrail-meta/dependency-decisions")
            self.assertTrue(any("missing `rollback`" in error for error in errors))

    def test_advisory_hook_reports_but_never_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            diff = root / "changes.patch"
            diff.write_text(DIFF, encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(ROOT / "hooks" / "guard-advisory-hook.py"), "--root", str(root), "--diff", str(diff), "--format", "json"],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertTrue(report["advisory"])
            self.assertEqual(report["dependency_decisions"]["status"], "failed")
            self.assertFalse((root / ".tailtrail").exists())

    def test_ci_uses_base_to_head_diff_and_structured_gate(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "trust.yml").read_text(encoding="utf-8")
        self.assertIn("fetch-depth: 0", workflow)
        self.assertIn("tailtrail-guard.diff", workflow)
        self.assertIn("tailtrail.py guard check", workflow)
        self.assertIn("tailtrail.py dependency check", workflow)

    def test_release_two_files_are_shipped_by_the_extended_surface(self) -> None:
        install_surfaces = ROOT / "scripts" / "install_surfaces.py"
        body = install_surfaces.read_text(encoding="utf-8")
        self.assertIn('"scripts/dependency-decision.py",', body)
        installer = (ROOT / "scripts" / "install-copilot.py").read_text(encoding="utf-8")
        self.assertIn('"hooks",', installer)
