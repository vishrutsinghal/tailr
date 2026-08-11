from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / path); module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader; sys.modules[name] = module; spec.loader.exec_module(module); return module


ledger = load("dashboard_ledger", "scripts/run-ledger.py")
anchor = load("dashboard_anchor", "scripts/change-intent-anchor.py")
dashboard = load("dashboard_script", "scripts/workflow-dashboard.py")


class WorkflowDashboardTests(unittest.TestCase):
    def test_dashboard_shows_active_requirement_drift_and_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); ledger.init_run(root, "run", "validation")
            proposal = root / "proposal.json"; proposal.write_text(json.dumps({"requirements": [{"statement": "reject zero", "acceptance_criteria": [], "preserve_rules": [], "likely_paths": ["src/a.py"], "evidence_plan": []}]}), encoding="utf-8")
            anchor.draft(root, "run", proposal); approved = anchor.approve(root, "run"); uid = approved["requirements"][0]["requirement_uid"]
            folder = ledger.state_dir(root, "run") / "checkpoints"; folder.mkdir(parents=True)
            (folder / "checkpoint-1.json").write_text(json.dumps({"checkpoint": 1, "requirements": [{"requirement_uid": uid, "state": "implemented-not-validated", "evidence": []}], "drift": [{"requirement_uid": uid, "classification": "unchanged"}]}), encoding="utf-8")
            result = dashboard.dashboard(root, "run")
        self.assertEqual(result["active_requirement"]["requirement_uid"], uid)
        self.assertEqual(result["drift"]["status"], "unresolved")
        self.assertTrue(result["canonical_state"]["valid"])
        harnesses = {item["name"]: item for item in result["harnesses"]}
        self.assertEqual(harnesses["Requirement Completion Harness"]["status"], "in-progress")
        self.assertEqual(harnesses["Maintainability Harness"]["status"], "not-selected")
        self.assertIn("## Harness usage", dashboard.markdown(result))
        self.assertIn("Workflow Dashboard", dashboard.markdown(result))
        self.assertIn("Canonical state:", dashboard.markdown(result))
        self.assertIn("Harness usage", dashboard.html_page(result))
