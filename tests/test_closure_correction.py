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


ledger = load("closure_correction_ledger_test", "scripts/run-ledger.py")
anchor = load("closure_correction_anchor_test", "scripts/change-intent-anchor.py")
lock = load("closure_correction_lock_test", "scripts/planning-lock.py")
recorder = load("closure_correction_recorder_test", "scripts/closure-recorder.py")
finalizer = load("closure_correction_finalizer_test", "scripts/closure-finalizer.py")
correction = load("closure_correction_test", "scripts/closure-correction.py")


class ClosureCorrectionTests(unittest.TestCase):
    def incomplete_run(self, root: Path, *, failed_receipt: bool = False) -> None:
        (root / "src").mkdir(); (root / "tests").mkdir()
        (root / "src" / "service.py").write_text("def cancel():\n    return True\n", encoding="utf-8")
        (root / "tests" / "test_service.py").write_text("# test\n", encoding="utf-8")
        lock.create(root, "cancel an order", "run")
        proposal = root / "proposal.json"
        proposal.write_text(json.dumps({"requirements": [{
            "statement": "Cancel an eligible order.", "acceptance_criteria": ["cancelled"],
            "preserve_rules": ["shipped remains rejected"], "likely_paths": ["src/service.py", "tests/test_service.py"],
            "evidence_plan": [], "validation_contract": {"state": "required", "tiers": ["unit"]},
            "behavior_contract": {"scenarios": []},
        }]}), encoding="utf-8")
        anchor.draft(root, "run", proposal)
        uid = anchor.approve(root, "run")["requirements"][0]["requirement_uid"]
        lock.approve(root, "run", True)
        run = ledger.state_dir(root, "run")
        (run / "planning").mkdir(exist_ok=True)
        selected = [] if failed_receipt else ["Behaviour Harness"]
        (run / "planning" / "execution-handoff-v1.json").write_text(json.dumps({"closure": {"selected_harnesses": selected}}), encoding="utf-8")
        source = root / "closure-input.json"
        source.write_text(json.dumps({"schema_version": "1", "type": "tailtrail-execution-closure-input", "run_id": "run", "changed_paths": ["src/service.py", "tests/test_service.py"], "receipts": [{"requirement_uids": [uid], "tier": "unit", "command_label": "unit proof", "command": "tailtrail-never-execute-correction-sentinel", "outcome": "fail" if failed_receipt else "pass", "environment": "local", "asserted_behavior": "eligible cancellation"}]}), encoding="utf-8")
        recorder.record(root, source)

    def test_finalizer_creates_one_bounded_same_run_correction_packet(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.incomplete_run(root, failed_receipt=True)
            finalized = finalizer.finalize(root, "run")
            packet = finalized["correction"]
            activity = ledger.projection(root, "run")["activity"]
        self.assertEqual(packet["status"], "correction-ready")
        self.assertEqual(packet["convergence"]["action"], "bounded-correction")
        self.assertEqual(packet["convergence"]["cycle"], 1)
        self.assertIn("continuity/packet-1.md", packet["continuity"]["packet"])
        self.assertEqual(activity["closure_correction_routed"], 1)
        self.assertEqual(activity["context_continuity_rendered"], 1)

    def test_same_failure_fingerprint_reuses_packet_without_another_cycle(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.incomplete_run(root, failed_receipt=True)
            finalizer.finalize(root, "run")
            again = correction.handoff(root, "run")
            activity = ledger.projection(root, "run")["activity"]
        self.assertTrue(again["reused"])
        self.assertEqual(activity["closure_correction_routed"], 1)
        self.assertEqual(activity["harness_convergence_assessed"], 1)

    def test_public_cli_returns_the_saved_correction_handoff(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.incomplete_run(root, failed_receipt=True)
            finalizer.finalize(root, "run")
            result = subprocess.run(
                [sys.executable, (ROOT / "scripts" / "tailtrail.py").as_posix(), "closure", "correct", "--root", root.as_posix(), "--run-id", "run"],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)["reused"])


if __name__ == "__main__":
    unittest.main()
