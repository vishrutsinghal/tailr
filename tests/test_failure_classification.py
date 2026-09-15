import unittest
from pathlib import Path
import shutil
import json

from scripts.pipeline_orchestrator import PipelineOrchestrator, classify_test_failure


class TestClassifyTestFailure(unittest.TestCase):
    """Design §10.1: classify a test failure before routing it."""

    def test_mechanical_markers_route_without_budget(self):
        """Syntax/compile failures are mechanical fixes, not regressions."""
        for code in ("SYNTAX_ERROR", "PARSE_FAILURE", "COMPILE_ERROR", "INDENTATION_ERROR"):
            decision = classify_test_failure(code)
            self.assertEqual(decision["route"], "mechanical", code)
            self.assertFalse(decision["burns_regression_budget"], code)

    def test_behavioral_failure_burns_budget(self):
        """An assertion failure contradicts expected behavior: regression."""
        decision = classify_test_failure("TEST_FAILURE")
        self.assertEqual(decision["route"], "regression")
        self.assertEqual(decision["classification"], "code")
        self.assertTrue(decision["burns_regression_budget"])

    def test_environmental_failure_routes_to_diagnose(self):
        """Timeouts are transient: diagnose read-only, no stage change."""
        decision = classify_test_failure("TIMEOUT")
        self.assertEqual(decision["route"], "diagnose")
        self.assertFalse(decision["burns_regression_budget"])

    def test_permission_failure_routes_to_diagnose(self):
        """Permission failures are authority blockers, not regressions."""
        decision = classify_test_failure("ACCESS_DENIED")
        self.assertEqual(decision["route"], "diagnose")
        self.assertFalse(decision["burns_regression_budget"])


class TestHandleRegressionRouting(unittest.TestCase):
    """The orchestrator routes classified failures without burning budget
    for mechanical or environmental causes."""

    def setUp(self):
        self.root = Path("temp_regression_test_root").absolute()
        self.root.mkdir(parents=True, exist_ok=True)
        self.run_id = "regression-test-run"
        planning_dir = self.root / ".tailtrail" / "runs" / self.run_id / "planning"
        planning_dir.mkdir(parents=True, exist_ok=True)
        self.lock_path = planning_dir / "lock-v1.json"
        self._write_lock("TESTING")

    def _write_lock(self, stage: str) -> None:
        lock = {
            "schema_version": "2",
            "type": "tailtrail-planning-lock",
            "run_id": self.run_id,
            "status": "approved",
            "pipeline": {
                "active_stage": stage,
                "completed_stages": ["IMPLEMENTATION"],
                "stage_sequence": ["IMPLEMENTATION", "TESTING", "INFRA"],
                "handoff_manifest": None,
                "regression_count": 0,
            },
        }
        self.lock_path.write_text(json.dumps(lock), encoding="utf-8")

    def tearDown(self):
        if self.root.exists():
            shutil.rmtree(self.root)

    def _lock(self) -> dict:
        return json.loads(self.lock_path.read_text(encoding="utf-8"))

    def test_mechanical_failure_handsoff_without_budget(self):
        """Syntax error: back to IMPLEMENTATION, regression budget untouched."""
        orchestrator = PipelineOrchestrator(self.root, self.run_id)
        result = orchestrator.handle_regression(
            "SyntaxError in src/app.py", [], error_code="SYNTAX_ERROR"
        )
        self.assertIn("Mechanical fix handoff", result)
        lock = self._lock()
        self.assertEqual(lock["pipeline"]["regression_count"], 0)
        self.assertEqual(lock["pipeline"]["active_stage"], "IMPLEMENTATION")
        self.assertEqual(lock["pipeline"]["last_regression"]["route"], "mechanical")

    def test_environmental_failure_stays_in_testing(self):
        """Timeout: no stage change, no budget, diagnose read-only."""
        orchestrator = PipelineOrchestrator(self.root, self.run_id)
        result = orchestrator.handle_regression(
            "test runner timed out", [], error_code="TIMEOUT"
        )
        self.assertIn("Diagnosis required", result)
        lock = self._lock()
        self.assertEqual(lock["pipeline"]["regression_count"], 0)
        self.assertEqual(lock["pipeline"]["active_stage"], "TESTING")
        self.assertEqual(lock["pipeline"]["last_regression"]["route"], "diagnose")

    def test_behavioral_failure_burns_budget_and_regresses(self):
        """Assertion failure: regression loop, budget consumed."""
        orchestrator = PipelineOrchestrator(self.root, self.run_id)
        result = orchestrator.handle_regression(
            "assertion failed", [], error_code="TEST_FAILURE"
        )
        self.assertIn("Regression triggered", result)
        lock = self._lock()
        self.assertEqual(lock["pipeline"]["regression_count"], 1)
        self.assertEqual(lock["pipeline"]["active_stage"], "IMPLEMENTATION")
        self.assertEqual(lock["pipeline"]["last_regression"]["route"], "regression")

    def test_no_error_code_defaults_to_regression(self):
        """Backward compatible: unclassified failures stay conservative."""
        orchestrator = PipelineOrchestrator(self.root, self.run_id)
        result = orchestrator.handle_regression("test failed", [])
        self.assertIn("Regression triggered", result)
        self.assertEqual(self._lock()["pipeline"]["regression_count"], 1)

    def test_circuit_breaker_still_applies_to_behavioral_loops(self):
        """Three behavioral loops freeze the pipeline for design review."""
        orchestrator = PipelineOrchestrator(self.root, self.run_id)
        for i in range(3):
            orchestrator.handle_regression(f"bug {i}", [], error_code="TEST_FAILURE")
        result = orchestrator.handle_regression("bug 3", [], error_code="TEST_FAILURE")
        self.assertIn("CIRCUIT BREAKER TRIGGERED", result)
        self.assertEqual(self._lock()["pipeline"]["regression_count"], 3)

    def test_mechanical_loops_do_not_trigger_circuit_breaker(self):
        """Mechanical fixes never consume budget, so they never trip the breaker."""
        orchestrator = PipelineOrchestrator(self.root, self.run_id)
        for i in range(5):
            result = orchestrator.handle_regression(
                f"syntax error {i}", [], error_code="SYNTAX_ERROR"
            )
            self.assertIn("Mechanical fix handoff", result)
        self.assertEqual(self._lock()["pipeline"]["regression_count"], 0)


if __name__ == "__main__":
    unittest.main()