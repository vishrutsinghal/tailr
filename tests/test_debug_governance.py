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
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec); sys.modules[name] = module; spec.loader.exec_module(module); return module


INTAKE = load("debug_governance_test_intake", "scripts/debug-intake.py")
GOVERNANCE = load("debug_governance_test_module", "scripts/debug-governance.py")
LEARNING = load("debug_governance_test_learning", "scripts/closure-learning.py")


class DebugGovernanceTests(unittest.TestCase):
    def test_exact_local_intake_and_portable_fingerprint_are_separate(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            secret = "Bearer abcdefghijklmnopqrstuvwxyz"
            email = "person@example.com"
            result = INTAKE.open_intake(root, "run", f"Payment failed for {email}", f"{secret}\nTraceback line 42", None, False)
            intake_text = INTAKE.intake_path(root, "run").read_text(encoding="utf-8")
            fingerprint_text = INTAKE.fingerprint_path(root, "run").read_text(encoding="utf-8")
            self.assertIn(secret, intake_text)
            self.assertIn(email, intake_text)
            self.assertNotIn(secret, fingerprint_text)
            self.assertNotIn(email, fingerprint_text)
            self.assertNotIn("Traceback line 42", fingerprint_text)
            self.assertTrue(result["fingerprint"]["portable"])
            self.assertEqual(result["fingerprint"]["privacy"]["raw_values"], False)
            self.assertEqual(result["governance"]["privacy"]["categories"], ["bearer-token", "email"])

    def test_token_posture_is_estimated_without_linked_telemetry_and_measured_with_it(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            INTAKE.open_intake(root, "run", "Intermittent duplicate charge", "stack line", None, False)
            initial = GOVERNANCE.show(root, "run")
            self.assertEqual(initial["token_posture"]["actual_status"], "unavailable")
            self.assertEqual(initial["token_posture"]["exactness"][0]["class"], "must-be-exact")
            telemetry = root / ".tailtrail" / "token-usage.jsonl"
            telemetry.write_text(json.dumps({"mode":"measured", "task_id":"run", "tailtrail":{"total_tokens":321}}) + "\n", encoding="utf-8")
            measured = GOVERNANCE.build(root, "run")
            self.assertEqual(measured["token_posture"]["actual_status"], "measured")
            self.assertEqual(measured["token_posture"]["actual_tokens"], 321)

    def test_sanitized_failure_identity_is_stable_across_runs(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first = INTAKE.open_intake(root, "run-a", "Duplicate charge", "Trace line", None, False)
            second = INTAKE.open_intake(root, "run-b", "Duplicate charge", "Trace line", None, False)
            self.assertEqual(first["fingerprint"]["fingerprint"], second["fingerprint"]["fingerprint"])

    def test_debug_learning_profile_contains_only_sanitized_categories(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            INTAKE.open_intake(root, "run", "Duplicate charge", "Bearer abcdefghijklmnopqrstuvwxyz", None, False)
            report = {"debug":{"debug_status":"pass", "domain":"code", "confidence_state":"behavior-restored", "domain_confidence_ceiling":"behavior-restored"}, "tests":{"passed_tiers":["integration"]}}
            profile = LEARNING.debug_profile(root, "run", report)
            self.assertEqual(profile["proven_cause_class"], "code")
            self.assertEqual(profile["raw_values"], False)
            serialized = json.dumps(profile)
            self.assertNotIn("Bearer", serialized)
            self.assertNotIn("Duplicate charge", serialized)


if __name__ == "__main__":
    unittest.main()
