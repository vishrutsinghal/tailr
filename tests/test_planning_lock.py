from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


lock = load("planning_lock_test", "scripts/planning-lock.py")
ledger = load("planning_lock_ledger_test", "scripts/run-ledger.py")


class PlanningLockTests(unittest.TestCase):
    def test_start_is_locked_until_a_separate_explicit_approval(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            created = lock.create(root, "replicate Terraform setup", "plan-1", ["../reference"])
            with self.assertRaisesRegex(ValueError, "explicit approval"):
                lock.assert_write_allowed(root, "plan-1")
            approved = lock.approve(root, "plan-1", True)
            allowed = lock.assert_write_allowed(root, "plan-1")
            activity = ledger.projection(root, "plan-1")["activity"]
        self.assertEqual(created["status"], "awaiting-approval")
        self.assertFalse(created["writes_allowed"])
        self.assertEqual(created["reference_roots"][0]["access"], "read-only")
        self.assertEqual(approved["status"], "approved")
        self.assertTrue(allowed["writes_allowed"])
        self.assertEqual(activity["planning_lock_created"], 1)
        self.assertEqual(activity["planning_lock_approved"], 1)

    def test_approval_flag_is_required(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lock.create(root, "plan", "plan-2")
            with self.assertRaisesRegex(ValueError, "--approved"):
                lock.approve(root, "plan-2", False)

    def test_activation_creates_anchor_from_the_saved_start_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lock.create(root, "fix claim validation", "plan-3")
            lock.save_start_report(root, "plan-3", {
                "goal": "fix claim validation",
                "guided_delivery": {"mode": "guided-delivery"},
                "navigator": {"likely_impacted_files": [{"path": "src/claims.py"}]},
            })
            activated = lock.activate(root, "plan-3", True)
            artifact = root / activated["anchor"]["artifact"]
            approved = json.loads(artifact.read_text(encoding="utf-8"))
        self.assertEqual(activated["planning_lock"]["status"], "approved")
        self.assertEqual(activated["anchor"]["status"], "created")
        self.assertEqual(approved["requirements"][0]["statement"], "fix claim validation")
        self.assertEqual(approved["requirements"][0]["likely_paths"], ["src/claims.py"])

    def test_lean_activation_does_not_create_an_anchor(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lock.create(root, "rename one local variable", "plan-4")
            lock.save_start_report(root, "plan-4", {
                "goal": "rename one local variable",
                "guided_delivery": {"mode": "lean"},
                "navigator": {},
            })
            activated = lock.activate(root, "plan-4", True)
        self.assertEqual(activated["anchor"]["status"], "not-required")


if __name__ == "__main__":
    unittest.main()
