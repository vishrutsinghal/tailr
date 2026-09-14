import sys
sys.path.insert(0, r"D:\PD\tailr-main\tailtrail\scripts")

import unittest
import os
import json
import shutil
from pathlib import Path
from datetime import datetime

import planning_lock as pl
from scripts.pipeline_manager import PipelineManager, HandoffManifest
from scripts.pipeline_judge import PipelineJudge
from scripts.navigator import process_handoff, start_hands_free_slice
from scripts.navigator_scope import WORKER_CONTRACTS, ROLES


class TestFullPipeline(unittest.TestCase):
    def setUp(self):
        self.root = Path("temp_pipeline_test").absolute()
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "src").mkdir(parents=True, exist_ok=True)
        (self.root / "src" / "app.py").write_text("print('hello')")
        (self.root / "tests").mkdir(parents=True, exist_ok=True)
        (self.root / "tests" / "test_app.py").write_text("def test_pass(): pass")
        self.run_id = "full-pipeline-test-1"
        state_dir = self.root / ".tailtrail" / "runs" / self.run_id
        state_dir.mkdir(parents=True, exist_ok=True)
        pl.L.init_run(self.root, self.run_id, "Test goal")
        lock_data = {
            "schema_version": "2",
            "type": "tailtrail-planning-lock",
            "run_id": self.run_id,
            "goal": "Test goal",
            "status": "approved",
            "pipeline": {
                "active_stage": "IMPLEMENTATION",
                "completed_stages": [],
                "stage_sequence": ["IMPLEMENTATION", "TESTING", "INFRA"],
                "handoff_manifest": None,
                "regression_count": 0
            }
        }
        lock_path = Path(pl.lock_path(self.root, self.run_id))
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock_path.write_text(json.dumps(lock_data))

    def tearDown(self):
        if self.root.exists():
            shutil.rmtree(self.root)

    def test_01_hands_free_slice_init(self):
        result = start_hands_free_slice(self.root, "hands-free task to test slicing", self.run_id)
        self.assertIn("IMPLEMENTATION", result)
        lock = json.loads(Path(pl.lock_path(self.root, self.run_id)).read_text())
        self.assertEqual(lock["pipeline"]["active_stage"], "IMPLEMENTATION")

    def test_02_write_guardian_blocks_prod_in_test_stage(self):
        lock = json.loads(Path(pl.lock_path(self.root, self.run_id)).read_text())
        lock["pipeline"]["active_stage"] = "TESTING"
        Path(pl.lock_path(self.root, self.run_id)).write_text(json.dumps(lock))
        judge = PipelineJudge(self.root, self.run_id)
        prod_file = "src/app.py"
        allowed, error = judge.validate_write_access(prod_file)
        self.assertFalse(allowed, "Write access should be denied for production file in TESTING stage")
        self.assertIn("prohibited", error.lower())

    def test_03_process_handoff_transition(self):
        manifest_data = {
            "change_manifest": ["src/app.py"],
            "requirement_pointers": ["REQ-01"],
            "context": "Implemented the app logic",
            "evidence": []
        }
        result = process_handoff(self.root, self.run_id, "IMPLEMENTATION", manifest_data)
        self.assertIn("Transitioned to", result)
        lock = json.loads(Path(pl.lock_path(self.root, self.run_id)).read_text())
        self.assertEqual(lock["pipeline"]["active_stage"], "TESTING")

    def test_04_drift_gate_blocks_uninformed_transition(self):
        lock = json.loads(Path(pl.lock_path(self.root, self.run_id)).read_text())
        lock["pipeline"]["active_stage"] = "TESTING"
        lock["pipeline"]["requirement_pointers"] = []
        Path(pl.lock_path(self.root, self.run_id)).write_text(json.dumps(lock))
        judge = PipelineJudge(self.root, self.run_id)
        evidence = {"requirement_pointers": [], "change_manifest": [], "context": "", "evidence": []}
        allowed, error = judge.verify_stage_transition("TESTING", "INFRA", evidence)
        self.assertFalse(allowed)
        self.assertIn("drift detected", error.lower())

    def test_05_write_guardian_allows_prod_in_impl_stage(self):
        judge = PipelineJudge(self.root, self.run_id)
        prod_file = "src/app.py"
        allowed, error = judge.validate_write_access(prod_file)
        self.assertTrue(allowed, f"Implementation worker should be allowed to edit production source: {error}")

    def test_06_full_pipeline_concept(self):
        from scripts.pipeline_manager import PipelineManager
        from scripts.pipeline_judge import PipelineJudge
        from scripts.navigator import process_handoff, start_hands_free_slice
        from scripts.write_guardian import WriteGuardian
        guardian = WriteGuardian(self.root, self.run_id)
        self.assertIsNotNone(guardian)
        result = process_handoff(self.root, self.run_id, "IMPLEMENTATION", {"change_manifest": [], "requirement_pointers": ["REQ-1"], "context": "test", "evidence": []})
        self.assertIsInstance(result, str)
        j = PipelineJudge(self.root, self.run_id)
        empty_evidence = {"requirement_pointers": [], "change_manifest": [], "context": "", "evidence": []}
        blocked, reason = j.verify_stage_transition("TESTING", "INFRA", empty_evidence)
        self.assertFalse(blocked)
        self.assertIn("drift", reason.lower())

if __name__ == "__main__":
    unittest.main()