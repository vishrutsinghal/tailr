from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_script(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {relative}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


proof = load_script("token_harness_proof_test", "scripts/token-harness-proof.py")


def telemetry_record(task_id: str, baseline: int, tailtrail: int) -> str:
    return json.dumps(
        {
            "mode": "measured",
            "task_id": task_id,
            "provider": "openai",
            "model": "gpt-test",
            "source": "test",
            "baseline": {"total_tokens": baseline},
            "tailtrail": {"total_tokens": tailtrail},
        }
    )


def ledger_event(sequence: int, before: int, after: int, event_type: str = "context_receipt", validation: str = "not-run") -> str:
    return json.dumps(
        {
            "schema_version": "1",
            "type": "tailtrail-token-harness-event",
            "sequence": sequence,
            "event_id": f"th-20260718-{sequence:06d}",
            "created_at": "2026-07-18T00:00:00+00:00",
            "event_type": event_type,
            "task_type": "bug-fix",
            "content_type": "json",
            "strategy": "json-structure-summary",
            "exactness_class": "structure-exact",
            "tokens_before": before,
            "tokens_after": after,
            "tokens_saved": before - after,
            "evidence_label": "local-evidence",
            "validation_outcome": validation,
            "privacy": "No raw prompt, source, log, path, secret, repo name, or user identity.",
        }
    )


class TokenHarnessProofTests(unittest.TestCase):
    def report(self, root: Path, *extra: str) -> dict:
        result = subprocess.run(
            [sys.executable, (ROOT / "scripts" / "tailtrail.py").as_posix(), "token-harness", "proof", "report", "--root", root.as_posix(), "--format", "json", *extra],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        return json.loads(result.stdout)

    def test_empty_inputs_return_estimated(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            payload = self.report(Path(temp))

        self.assertEqual(payload["evidence_label"], "estimated")
        self.assertFalse(payload["measured_claim_allowed"])

    def test_ledger_only_returns_local_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            ledger = root / ".tailtrail" / "token-harness-events.jsonl"
            ledger.parent.mkdir()
            ledger.write_text(ledger_event(1, 1000, 600) + "\n", encoding="utf-8")
            payload = self.report(root)

        self.assertEqual(payload["evidence_label"], "local-evidence")
        self.assertEqual(payload["ledger"]["tokens_saved"], 400)
        self.assertFalse(payload["measured_claim_allowed"])

    def test_complete_telemetry_returns_measured_when_gate_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            trail = root / ".tailtrail"
            trail.mkdir()
            (trail / "token-usage.jsonl").write_text("\n".join([telemetry_record("a", 1000, 500), telemetry_record("b", 1200, 800), telemetry_record("c", 800, 500)]) + "\n", encoding="utf-8")
            payload = self.report(root)

        self.assertEqual(payload["evidence_label"], "measured")
        self.assertTrue(payload["measured_claim_allowed"])
        self.assertTrue(payload["confidence"]["passed"])

    def test_benchmark_flag_returns_benchmark_measured_when_gate_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            trail = root / ".tailtrail"
            trail.mkdir()
            (trail / "token-usage.jsonl").write_text("\n".join([telemetry_record("a", 1000, 500), telemetry_record("b", 1200, 800), telemetry_record("c", 800, 500)]) + "\n", encoding="utf-8")
            payload = self.report(root, "--benchmark-passed")

        self.assertEqual(payload["evidence_label"], "benchmark-measured")
        self.assertTrue(payload["measured_claim_allowed"])

    def test_gate_blocks_measured_when_sample_count_is_low(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            trail = root / ".tailtrail"
            trail.mkdir()
            (trail / "token-usage.jsonl").write_text(telemetry_record("a", 1000, 500) + "\n", encoding="utf-8")
            payload = self.report(root)

        self.assertEqual(payload["evidence_label"], "estimated")
        self.assertFalse(payload["confidence"]["passed"])
        self.assertIn("below minimum", payload["confidence"]["reasons"][0])

    def test_quality_failure_blocks_measured(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            trail = root / ".tailtrail"
            trail.mkdir()
            (trail / "token-usage.jsonl").write_text("\n".join([telemetry_record("a", 1000, 500), telemetry_record("b", 1200, 800), telemetry_record("c", 800, 500)]) + "\n", encoding="utf-8")
            (trail / "token-harness-events.jsonl").write_text(ledger_event(1, 1, 1, "quality_result", "fail") + "\n", encoding="utf-8")
            payload = self.report(root)

        self.assertEqual(payload["evidence_label"], "local-evidence")
        self.assertFalse(payload["confidence"]["passed"])
        self.assertTrue(any("quality" in reason for reason in payload["confidence"]["reasons"]))

    def test_strict_rejects_half_populated_measured_telemetry(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            trail = root / ".tailtrail"
            trail.mkdir()
            (trail / "token-usage.jsonl").write_text(json.dumps({"mode": "measured", "task_id": "bad", "baseline": {"total_tokens": 100}}) + "\n", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, (ROOT / "scripts" / "tailtrail.py").as_posix(), "token-harness", "proof", "report", "--root", root.as_posix(), "--strict"],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("half-populated", result.stderr + result.stdout)

    def test_holdout_is_deterministic_and_sensitive_classes_are_excluded(self) -> None:
        first = proof.holdout_payload(type("Args", (), {"task_id": "TASK-1", "task_class": "bug-fix", "repo_id": "repo", "holdout_rate": 10, "holdout_salt": "salt"})())
        second = proof.holdout_payload(type("Args", (), {"task_id": "TASK-1", "task_class": "bug-fix", "repo_id": "repo", "holdout_rate": 10, "holdout_salt": "salt"})())
        sensitive = proof.holdout_payload(type("Args", (), {"task_id": "TASK-2", "task_class": "security", "repo_id": "repo", "holdout_rate": 100, "holdout_salt": "salt"})())

        self.assertEqual(first["holdout"], second["holdout"])
        self.assertFalse(sensitive["holdout"])
        self.assertIn("sensitive", sensitive["reason"])

    def test_pricing_fields_block_measured_claims(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            trail = root / ".tailtrail"
            trail.mkdir()
            records = [json.loads(telemetry_record("a", 1000, 500)), json.loads(telemetry_record("b", 1200, 800)), json.loads(telemetry_record("c", 800, 500))]
            records[0]["cost_usd"] = 1.23
            (trail / "token-usage.jsonl").write_text("\n".join(json.dumps(row) for row in records) + "\n", encoding="utf-8")
            payload = self.report(root)

        self.assertEqual(payload["evidence_label"], "estimated")
        self.assertFalse(payload["confidence"]["passed"])
        self.assertTrue(any("pricing" in reason for reason in payload["confidence"]["reasons"]))


if __name__ == "__main__":
    unittest.main()
