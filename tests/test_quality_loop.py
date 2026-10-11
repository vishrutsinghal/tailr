import argparse
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module():
    spec = importlib.util.spec_from_file_location(
        "tailtrail_quality_loop_test", ROOT / "scripts" / "quality-loop.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


loop = load_module()

SHAPED_SECRETS = [
    "AKIAIOSFODNN7EXAMPLE",
    "ghp_1234567890abcdef1234567890abcdef1234",
    "xoxb-1234-5678-abcdefghij",
    "-----BEGIN RSA PRIVATE KEY-----",
    "Bearer abcdefghijklmnopqrstuvwx",
]


def base_args(**overrides):
    values = dict(
        fit="correct", outcome="accepted", validation_outcome="pass",
        sensitivity="normal", approval_status="approved", repo=None,
        root=Path(tempfile.gettempdir()), task_type="fix",
        goal_summary="fix login timeout", workflow="", skipped="",
        source="host", guardrails="", docs_loaded="", exact_materials="",
        checks="", validation_summary="unit pass", suggestion="none",
        overlap_flags="", missed_gate_flags="", notes="compact event",
    )
    values.update(overrides)
    return argparse.Namespace(**values)


class QualityLoopSecretTests(unittest.TestCase):
    def test_shaped_secrets_rejected_per_field(self) -> None:
        for field in ("goal_summary", "validation_summary", "suggestion", "notes"):
            for secret in SHAPED_SECRETS:
                with self.subTest(field=field, secret=secret[:15]):
                    with self.assertRaisesRegex(SystemExit, field):
                        loop.build_event(base_args(**{field: f"saw {secret} in output"}))

    def test_clean_prose_passes_untouched(self) -> None:
        event = loop.build_event(base_args(
            notes="the token budget and key rotation policy look sane, no secrets pasted"))
        self.assertIn("token budget", event["notes"])

    def test_approved_capture_with_secret_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            result = subprocess.run(
                [sys.executable, (ROOT / "scripts" / "quality-loop.py").as_posix(),
                 "capture", "--root", temp, "--fit", "correct", "--outcome", "accepted",
                 "--validation-outcome", "pass", "--notes", f"key AKIAIOSFODNN7EXAMPLE leaked",
                 "--approved"],
                text=True, capture_output=True, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((Path(temp) / ".tailtrail" / "quality-events.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
