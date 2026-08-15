from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load():
    spec = importlib.util.spec_from_file_location("spec_kit_policy_test", ROOT / "scripts" / "spec-kit-policy.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


policy = load()


class SpecKitPolicyTests(unittest.TestCase):
    def test_committed_template_is_valid(self) -> None:
        payload = json.loads((ROOT / "templates" / "spec-kit-bridge-policy.example.json").read_text(encoding="utf-8"))
        self.assertEqual(policy.validate(payload), [])

    def test_check_uses_safe_template_without_project_write(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            result = policy.policy_status(root, None)
            self.assertEqual(result["state"], "valid")
            self.assertEqual(result["policy_source"], "built-in-template")
            self.assertFalse((root / ".tailtrail").exists())

    def test_init_creates_once_and_rejects_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            result = policy.init_policy(root, None)
            self.assertEqual(result["state"], "created")
            self.assertTrue((root / ".tailtrail" / "spec-kit-policy.json").is_file())
            with self.assertRaisesRegex(ValueError, "already exists"):
                policy.init_policy(root, None)

    def test_unsafe_privacy_and_approval_relaxation_is_rejected(self) -> None:
        payload = json.loads((ROOT / "templates" / "spec-kit-bridge-policy.example.json").read_text(encoding="utf-8"))
        payload["privacy"]["store_raw_prompts"] = True
        payload["approval"]["allow_automatic_spec_kit_execution"] = True
        issues = policy.validate(payload)
        self.assertTrue(any("store_raw_prompts" in item for item in issues))
        self.assertTrue(any("approval" in item for item in issues))

    def test_policy_path_cannot_escape_selected_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, "inside --root"):
                policy.policy_status(Path(temp), "../outside.json")


if __name__ == "__main__":
    unittest.main()
