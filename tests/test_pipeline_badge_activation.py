import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import importlib.util
import tempfile
import unittest

import planning_lock as pl
from scripts.pipeline_judge import PipelineJudge


def load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


completion_report = load("pipeline_badge_completion_report", "scripts/completion-report.py")


class PipelineBadgeActivationTests(unittest.TestCase):
    def test_create_defaults_to_pending_without_badge(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lock = pl.create(root, "fix a validation defect", "badge-default")
        self.assertEqual(lock["pipeline"]["active_stage"], "PENDING")

    def test_create_with_implementation_stage_activates_impl_badge(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "tests").mkdir(parents=True, exist_ok=True)
            (root / "tests" / "test_service.py").write_text("def test_ok(): pass")
            lock = pl.create(
                root,
                "standard mode order workflow",
                "badge-impl",
                pipeline_stage="IMPLEMENTATION",
            )
            self.assertEqual(lock["pipeline"]["active_stage"], "IMPLEMENTATION")
            judge = PipelineJudge(root, "badge-impl")
            allowed, error = judge.validate_write_access("tests/test_service.py")
            self.assertFalse(allowed, "impl-badge must block test paths")
            self.assertIn("prohibited", error.lower())

    def test_create_with_unknown_stage_stays_pending(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lock = pl.create(root, "fix a validation defect", "badge-unknown", pipeline_stage="REVIEW")
        self.assertEqual(lock["pipeline"]["active_stage"], "PENDING")

    def test_initial_stage_badges_every_mode(self) -> None:
        for mode in ("lite", "off", "standard", "full", None):
            with self.subTest(mode=mode):
                self.assertEqual(pl.initial_pipeline_stage(mode), "IMPLEMENTATION")
        for mode in ("lite", "off", "standard", "full", None):
            with self.subTest(mode=mode, debug=True):
                self.assertEqual(pl.initial_pipeline_stage(mode, debug_plan=True), "IMPLEMENTATION")

    def test_closure_summary_reports_missing_lock_as_not_recorded(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            summary = completion_report.pipeline_summary(Path(temp), "no-such-run")
        self.assertEqual(summary["status"], "not-recorded")
        self.assertIsNone(summary["active_badge"])

    def test_closure_summary_reports_badged_run_with_unvisited_stages(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            pl.create(root, "standard mode order workflow", "badge-closure", pipeline_stage="IMPLEMENTATION")
            summary = completion_report.pipeline_summary(root, "badge-closure")
        self.assertEqual(summary["status"], "badged")
        self.assertEqual(summary["active_stage"], "IMPLEMENTATION")
        self.assertEqual(summary["active_badge"], "impl-badge")
        self.assertEqual(summary["unvisited_stages"], ["TESTING", "INFRA"])

    def test_closure_summary_reports_unbadged_run(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            pl.create(root, "fix a validation defect", "badge-closure-lite")
            summary = completion_report.pipeline_summary(root, "badge-closure-lite")
        self.assertEqual(summary["status"], "unbadged")
        self.assertIsNone(summary["active_badge"])

    def test_closure_render_shows_pipeline_badges_section(self) -> None:
        rendered = completion_report.render({
            "run_id": "badge-closure", "overall_status": "evidence-incomplete",
            "boundary": "The report aggregates saved local artifacts.",
            "implementation": {"status": "implemented"},
            "requirement_status": {"complete": 0, "total": 1, "requirements": []},
            "tests": {"status": "not-evidenced", "passed_tiers": [], "tier_results": {}, "required_checks": [], "receipts": [], "receipt_refs": []},
            "drift": {"status": "not-assessed"}, "changed_scope": {"status": "not-assessed", "changed_paths": []},
            "behaviour": {"status": "not-assessed"}, "harnesses": [],
            "debug": {"debug_status": "not-triggered"},
            "learning_use": {"status": "not-recorded", "attributed": 0, "receipts": []},
            "token_usage": {"status": "unavailable"}, "source_artifacts": {},
            "execution_authority": {"status": "unavailable", "route": "not-recorded"},
            "canonical_state": {"status": "unknown"}, "recovery_checkpoint": {"status": "not-configured"},
            "official_aidlc": {"evidence_status": "not-triggered"},
            "pipeline": {"status": "badged", "active_stage": "IMPLEMENTATION", "active_badge": "impl-badge", "completed_stages": [], "unvisited_stages": ["TESTING", "INFRA"], "handoff_count": 0},
        })
        self.assertIn("## Pipeline badges", rendered)
        self.assertIn("impl-badge", rendered)
        self.assertIn("TESTING, INFRA", rendered)


if __name__ == "__main__":
    unittest.main()
