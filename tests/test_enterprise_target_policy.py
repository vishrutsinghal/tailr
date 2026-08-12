from __future__ import annotations

import importlib.util
import json
import subprocess
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


policy = load("enterprise_target_policy_test", "scripts/enterprise-target-policy.py")
lock = load("enterprise_target_policy_lock_test", "scripts/planning-lock.py")


def write_policy(path: Path, root: Path, *, restricted: list[str] | None = None, owners: list[str] | None = None) -> None:
    payload = {
        "schema_version": "1", "type": "tailtrail-enterprise-target-policy",
        "allowed_target_roots": [root.parent.as_posix()], "restricted_target_roots": restricted or [],
        "require_identity_verification": True, "require_declared_owner": bool(owners),
        "aliases": {"service": {"root": root.as_posix(), "access": "read-write", "owners": owners or []}},
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


class EnterpriseTargetPolicyTests(unittest.TestCase):
    def test_policy_allows_registered_owned_target_and_blocks_restricted_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "service"; root.mkdir()
            policy_path = Path(temp) / "enterprise.json"; write_policy(policy_path, root, owners=["platform-team"])
            loaded = policy.load(policy_path)
            passed = policy.evaluate(root, loaded, actor="platform-team", selected_alias="service")
            blocked_path = Path(temp) / "blocked.json"; write_policy(blocked_path, root, restricted=[root.as_posix()])
            blocked = policy.evaluate(root, policy.load(blocked_path), actor="platform-team", selected_alias="service")
        self.assertEqual(passed["status"], "passed")
        self.assertEqual(blocked["status"], "blocked")
        self.assertIn("restricted_target_roots", blocked["issues"][0])

    def test_changed_policy_blocks_approved_lock_write(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "service"; root.mkdir()
            policy_path = Path(temp) / "enterprise.json"; write_policy(policy_path, root)
            result = policy.evaluate(root, policy.load(policy_path), selected_alias="service")
            lock.create(root, "policy protected work", "policy-run", enterprise_policy=result)
            lock.approve(root, "policy-run", True)
            write_policy(policy_path, root, restricted=[root.as_posix()])
            with self.assertRaisesRegex(ValueError, "Enterprise target policy blocks managed source changes"):
                lock.assert_write_allowed(root, "policy-run")

    def test_start_alias_persists_policy_and_sanitized_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "service"; root.mkdir()
            policy_path = Path(temp) / "enterprise.json"; write_policy(policy_path, root)
            result = subprocess.run(
                [sys.executable, (ROOT / "scripts" / "task-start.py").as_posix(), "plan a service change", "--enterprise-policy", policy_path.as_posix(), "--target-alias", "service", "--planning-run-id", "policy-start"],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )
            lock_payload = json.loads((root / ".tailtrail" / "runs" / "policy-start" / "planning" / "lock-v1.json").read_text(encoding="utf-8"))
            receipt = json.loads((root / ".tailtrail" / "runs" / "policy-start" / "planning" / "target-resolution-receipt-v1.json").read_text(encoding="utf-8"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(lock_payload["enterprise_policy"]["status"], "passed")
        self.assertEqual(receipt["policy"]["selected_alias"], "service")
        self.assertNotIn("plan a service change", json.dumps(receipt))


if __name__ == "__main__":
    unittest.main()
