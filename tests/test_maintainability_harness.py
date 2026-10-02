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

    def mnt_setup(self, root: Path) -> None:
        ledger.init_run(root, "mntrun", "maintainability")
        (root / "src").mkdir()
        body = "def calc(value):\n return value * 2\n"
        (root / "src" / "a.py").write_text(body, encoding="utf-8")
        (root / "src" / "b.py").write_text(body, encoding="utf-8")
        (root / "src" / "m.py").write_text("class ThingManager:\n def run(self):\n  return 1\n", encoding="utf-8")
        proposal = root / "proposal.json"
        proposal.write_text(json.dumps({"requirements": [{"requirement_uid": "REQ-MNT-1", "statement": "reduce duplication", "likely_paths": ["src/a.py", "src/b.py", "src/m.py"], "acceptance_criteria": [], "preserve_rules": [], "evidence_plan": [], "maintainability_contract": {"candidate_paths": ["src/a.py", "src/b.py"], "rules": [{"rule_id": "MNT-01", "requirement_uid": "REQ-MNT-1"}]}}]}), encoding="utf-8")
        anchor.draft(root, "mntrun", proposal)
        anchor.approve(root, "mntrun")
        harness.capture_baseline(root, "mntrun")

    def test_mnt01_regressed_when_duplicates_persist(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.mnt_setup(root)
            result = harness.assess(root, "mntrun", ["src/a.py", "src/b.py"])
        self.assertFalse(result["complete"])
        self.assertEqual(result["rule_results"][0]["state"], "regressed")
        self.assertEqual(result["findings"][0]["category"], "duplication-not-reduced")

    def test_mnt01_improved_when_duplicates_shrink(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.mnt_setup(root)
            (root / "src" / "b.py").write_text("def calc(value):\n return value * 3\n", encoding="utf-8")
            result = harness.assess(root, "mntrun", ["src/a.py", "src/b.py"])
        self.assertTrue(result["complete"])
        self.assertEqual(result["rule_results"][0]["state"], "improved")

    def test_abstraction_advisory_does_not_block(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.mnt_setup(root)
            result = harness.assess(root, "mntrun", ["src/m.py"])
        self.assertTrue(any(item["category"] == "unnecessary-abstraction" and item["symbol"] == "ThingManager" for item in result["advisories"]))

    def test_rule_with_unknown_requirement_uid_is_flagged(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            ledger.init_run(root, "badrun", "maintainability")
            (root / "src").mkdir()
            (root / "src" / "a.py").write_text("x = 1\n", encoding="utf-8")
            proposal = root / "proposal.json"
            proposal.write_text(json.dumps({"requirements": [{"requirement_uid": "REQ-REAL", "statement": "x", "likely_paths": ["src/a.py"], "acceptance_criteria": [], "preserve_rules": [], "evidence_plan": [], "maintainability_contract": {"candidate_paths": ["src/a.py"], "rules": [{"rule_id": "MNT-01", "requirement_uid": "REQ-GHOST"}]}}]}), encoding="utf-8")
            anchor.draft(root, "badrun", proposal)
            anchor.approve(root, "badrun")
            harness.capture_baseline(root, "badrun")
            result = harness.assess(root, "badrun", ["src/a.py"])
        self.assertFalse(result["complete"])
        self.assertEqual(result["findings"][0]["category"], "rule-identity")
        self.assertEqual(result["rule_results"][0]["state"], "unknown-requirement")


if __name__ == "__main__":
    unittest.main()
