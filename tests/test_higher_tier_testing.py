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
    module = importlib.util.module_from_spec(spec); assert spec and spec.loader; sys.modules[name] = module; spec.loader.exec_module(module); return module


ledger = load("higher_tier_ledger", "scripts/run-ledger.py")
anchor = load("higher_tier_anchor", "scripts/change-intent-anchor.py")
runner = load("higher_tier_runner", "scripts/higher-tier-testing.py")
confidence = load("higher_tier_confidence", "scripts/release-confidence.py")


class HigherTierTestingTests(unittest.TestCase):
    def setup(self, root: Path) -> str:
        ledger.init_run(root, "run", "release confidence")
        proposal = root / "proposal.json"
        proposal.write_text(json.dumps({"requirements": [{"statement": "submit claim through service", "likely_paths": ["src/service.py"], "acceptance_criteria": [], "preserve_rules": [], "evidence_plan": [], "validation_contract": {"state": "required", "tiers": ["integration", "release-smoke"]}}]}), encoding="utf-8")
        drafted = anchor.draft(root, "run", proposal); anchor.approve(root, "run")
        return drafted["requirements"][0]["requirement_uid"]

    def profile(self, root: Path, remote: bool = False) -> Path:
        path = root / "profile.json"
        path.write_text(json.dumps({"tiers": [{"name": "integration", "adapter": "integration", "command": [sys.executable, "-c", "pass"], "environment": "local-service", "requires_approval": True, "prerequisites": [], "cleanup": []}, {"name": "release-smoke", "adapter": "release-smoke", "command": [sys.executable, "-c", "pass"], "environment": "staging", "requires_approval": True, "remote": remote, "safe_test_account": remote, "prerequisites": [], "cleanup": []}]}), encoding="utf-8")
        return path

    def test_declared_integration_runs_only_with_approval_and_records_receipt(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); uid = self.setup(root); profile = self.profile(root)
            with self.assertRaises(ValueError): runner.execute(root, "run", profile, "integration", uid, "claim submits", False, False)
            result = runner.execute(root, "run", profile, "integration", uid, "claim submits", True, False)
            activity = ledger.projection(root, "run")["activity"]
        self.assertEqual(result["outcome"], "pass")
        self.assertEqual(activity["higher_tier_executed"], 1)
        self.assertNotIn("stdout", result)

    def test_remote_release_smoke_is_blocked_without_separate_remote_approval(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); uid = self.setup(root); profile = self.profile(root, remote=True)
            result = runner.execute(root, "run", profile, "release-smoke", uid, "staging smoke", True, False)
        self.assertEqual(result["outcome"], "blocked")

    def test_release_confidence_keeps_missing_release_evidence_incomplete(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); uid = self.setup(root); receipts = root / "receipts.json"
            receipts.write_text(json.dumps({"receipts": [{"requirement_uid": uid, "tier": "integration", "outcome": "pass"}, {"requirement_uid": uid, "tier": "release-smoke", "outcome": "unavailable"}]}), encoding="utf-8")
            result = confidence.assess(root, "run", receipts)
        self.assertFalse(result["confidence_complete"])
        self.assertEqual(result["findings"][0]["tier"], "release-smoke")


if __name__ == "__main__": unittest.main()
