import unittest
from pathlib import Path
import shutil
import json
import os

from scripts.pipeline_manager import PipelineManager, HandoffManifest
from scripts.pipeline_judge import PipelineJudge
from scripts.pipeline_orchestrator import PipelineOrchestrator
from scripts.navigator_scope import WORKER_CONTRACTS, ROLES

class TestSequentialPipeline(unittest.TestCase):
    def setUp(self):
        self.root = Path("temp_test_root").absolute()
        self.root.mkdir(parents=True, exist_ok=True)
        self.run_id = "test-run-123"
        
        # Mocking the Planning Lock structure
        self.state_dir = self.root / ".tailtrail" / "runs" / self.run_id
        self.planning_dir = self.state_dir / "planning"
        self.planning_dir.mkdir(parents=True, exist_ok=True)
        
        self.lock_path = self.planning_dir / "lock-v1.json"
        self.initial_lock = {
            "schema_version": "2",
            "type": "tailtrail-planning-lock",
            "run_id": self.run_id,
            "status": "approved",
            "pipeline": {
                "active_stage": "IMPLEMENTATION",
                "completed_stages": [],
                "stage_sequence": ["IMPLEMENTATION", "TESTING", "INFRA"],
                "handoff_manifest": None,
                "regression_count": 0
            }
        }
        with open(self.lock_path, "w") as f:
            json.dump(self.initial_lock, f)

    def tearDown(self):
        if self.root.exists():
            shutil.rmtree(self.root)

    def test_write_access_enforcement(self):
        """Test that the Judge blocks writes to prohibited roles based on the active badge."""
        judge = PipelineJudge(self.root, self.run_id)
        
        # Mock the Lock to be in IMPLEMENTATION stage
        # (The Judge uses PipelineManager which reads the lock)
        
        # 1. Test valid write: Production source in IMPLEMENTATION stage
        # We need to ensure the file exists or just mock classify_repository_role
        # For a real test, we create the file
        prod_file = "src/app.py"
        (self.root / "src").mkdir(parents=True, exist_ok=True)
        (self.root / "src/app.py").write_text("print('hello')")
        
        # Use the judge to check access
        # Note: judge internally calls classify_repository_role
        allowed, error = judge.validate_write_access(prod_file)
        self.assertTrue(allowed, f"Implementation worker should be allowed to edit production source: {error}")

        # 2. Test prohibited write: Test file in IMPLEMENTATION stage
        test_file = "tests/test_app.py"
        (self.root / "tests").mkdir(parents=True, exist_ok=True)
        (self.root / "tests/test_app.py").write_text("def test_pass(): pass")
        
        allowed, error = judge.validate_write_access(test_file)
        self.assertFalse(allowed, "Implementation worker should NOT be allowed to edit test files.")
        self.assertIn("prohibited", error.lower())

    def test_stage_transition_and_handoff(self):
        """Test that the pipeline correctly transitions stages and records handoffs."""
        manager = PipelineManager(self.root, self.run_id)
        orchestrator = PipelineOrchestrator(self.root, self.run_id)
        
        # Transition from IMPLEMENTATION -> TESTING
        manifest = {
            "change_manifest": ["src/app.py"],
            "requirement_pointers": ["REQ-01"],
            "context": "Fixed the bug",
            "evidence": []
        }
        result = orchestrator.request_handoff("IMPLEMENTATION", manifest)
        
        self.assertIn("Transitioned to TESTING", result)
        self.assertEqual(manager.get_current_stage(), "TESTING")
        
        # Verify lock updated
        lock = json.loads((self.lock_path).read_text())
        self.assertIn("IMPLEMENTATION", lock["pipeline"]["completed_stages"])
        self.assertEqual(lock["pipeline"]["active_stage"], "TESTING")

    def test_regression_circuit_breaker(self):
        """Test that the circuit breaker blocks too many regressions."""
        orchestrator = PipelineOrchestrator(self.root, self.run_id)
        
        # Trigger regressions 3 times
        for i in range(3):
            orchestrator.handle_regression(f"Bug {i}", [])
            
        # The 4th attempt should trigger the circuit breaker
        result = orchestrator.handle_regression("Bug 3", [])
        self.assertIn("CIRCUIT BREAKER TRIGGERED", result)

    def test_test_worker_cannot_edit_prod(self):
        """Test that the Testing worker is strictly blocked from editing production code."""
        # Update lock to TESTING stage
        lock = self.initial_lock.copy()
        lock["pipeline"]["active_stage"] = "TESTING"
        with open(self.lock_path, "w") as f:
            json.dump(lock, f)
            
        judge = PipelineJudge(self.root, self.run_id)
        
        prod_file = "src/app.py"
        (self.root / "src").mkdir(parents=True, exist_ok=True)
        (self.root / "src/app.py").write_text("print('hello')")
        
        allowed, error = judge.validate_write_access(prod_file)
        self.assertFalse(allowed, "Testing worker must NOT be allowed to edit production source.")
        self.assertIn("prohibited", error.lower())

if __name__ == "__main__":
    unittest.main()
