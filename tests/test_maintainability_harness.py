from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ledger = load("maintainability_test_ledger", "scripts/run-ledger.py")
anchor = load("maintainability_test_anchor", "scripts/change-intent-anchor.py")
harness = load("maintainability_test", "scripts/maintainability-harness.py")


class MaintainabilityHarnessTests(unittest.TestCase):
    def setup(self, root: Path) -> None:
        ledger.init_run(root, "run", "maintainability")
        (root / "src").mkdir()
        (root / "tests").mkdir()
        (root / "src" / "claims.py").write_text("def validate(value):\n return value > 0\n", encoding="utf-8")
        (root / "src" / "other.py").write_text("def validate(value):\n return value != 0\n", encoding="utf-8")
        (root / "tests" / "test_claims.py").write_text("def test_claim(): pass\n", encoding="utf-8")
        proposal = root / "proposal.json"
        proposal.write_text(json.dumps({"requirements": [{"statement": "reject zero", "likely_paths": ["src/claims.py", "tests/test_claims.py"], "acceptance_criteria": [], "preserve_rules": [], "evidence_plan": []}]}), encoding="utf-8")
        anchor.draft(root, "run", proposal)
        anchor.approve(root, "run")

    def test_reports_scope_and_duplicate_advisory(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.setup(root)
            result = harness.assess(root, "run", ["src/claims.py", "src/other.py"])
            activity = ledger.projection(root, "run")["activity"]
        self.assertFalse(result["complete"])
        self.assertEqual(result["findings"][0]["category"], "scope")
        self.assertEqual(result["advisories"][0]["category"], "duplicate-logic")
        self.assertEqual(activity["maintainability_assessed"], 1)

    def test_reports_test_only_change_as_test_chasing(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.setup(root)
            result = harness.assess(root, "run", ["tests/test_claims.py"])
        self.assertFalse(result["complete"])
        self.assertEqual(result["findings"][0]["category"], "test-chasing")


if __name__ == "__main__":
    unittest.main()
