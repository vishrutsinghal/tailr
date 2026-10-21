from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]


def load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


verbose = load("start_plan_presentation_verbose", "scripts/verbose-reporting.py")
lock = load("start_plan_presentation_lock", "scripts/planning_lock.py")
ledger = load("start_plan_presentation_ledger", "scripts/run-ledger.py")
audit = load("start_plan_presentation_audit", "scripts/planning-audit.py")


def sample_report() -> dict[str, object]:
    return {
        "goal": "Render a reviewable Start Plan.",
        "navigator": {
            "scope_evidence": {"implementation_owners": ["scripts/presenter.py"]},
            "requirement_matrix": [{
                "display_id": "REQ-01",
                "requirement_uid": "req-presentation",
                "kind": "change",
                "statement": "Render a reviewable Start Plan.",
                "acceptance_criteria": ["The normal plan is readable."],
                "preserve_rules": ["Keep machine records available."],
                "likely_paths": ["scripts/presenter.py"],
                "scope_evidence": {
                    "implementation_owners": ["scripts/presenter.py"],
                    "inspection_paths": ["scripts/source.py"],
                    "proof_paths": ["tests/test_presenter.py"],
                },
                "validation_contract": {
                    "state": "required",
                    "tiers": ["unit"],
                    "commands": ["python3 -m unittest tests.test_presenter"],
                    "candidate_paths": ["tests/test_presenter.py"],
                },
            }],
        },
        "guided_delivery": {"stages": ["render", "validate"], "selected": [{"name": "Navigator"}]},
        "risks": ["projection drift"],
    }


class StartPlanPresentationTests(unittest.TestCase):
    def test_verbose_without_aidlc_is_structured_markdown_not_json(self) -> None:
        report = sample_report()
        requirements = report["navigator"]["requirement_matrix"]  # type: ignore[index]
        rendered = verbose.generate_start_plan_verbose(
            "run-presentation", requirements, {}, "Render a reviewable Start Plan.",
            plan_data={"report": report, "planning_lock": {"status": "awaiting-approval"}},
        )

        self.assertIn("## Planning Lock", rendered)
        self.assertIn("## Command Reference Registry", rendered)
        self.assertIn("## Validation Requirements And Focused Validation Matrix", rendered)
        self.assertIn("## Architecture Analysis", rendered)
        self.assertIn("## Behaviour Analysis", rendered)
        self.assertIn("## Token Estimate", rendered)
        self.assertNotIn("## AIDLC Decisions", rendered)
        self.assertNotIn("```json", rendered)
        self.assertNotIn("## Complete Saved Planning Payload", rendered)

    def test_verbose_includes_aidlc_only_when_saved_artifacts_exist(self) -> None:
        report = sample_report()
        requirements = report["navigator"]["requirement_matrix"]  # type: ignore[index]
        rendered = verbose.generate_start_plan_verbose(
            "run-aidlc", requirements, {}, "Render a reviewable Start Plan.",
            plan_data={
                "report": report,
                "planning_lock": {"status": "awaiting-approval"},
                "aidlc": {"aidlc-requirements-v1.json": {"questions": [{"id": "Q1", "question": "Which proof?"}]}},
            },
        )

        self.assertIn("## AIDLC Decisions", rendered)
        self.assertIn("Which proof?", rendered)
        self.assertNotIn("```json", rendered)

    def test_planning_show_defaults_to_the_normal_saved_plan(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run_id = "run-public-plan"
            report = sample_report()
            lock.create(root, str(report["goal"]), run_id)
            ledger.atomic_json(lock.start_report_path(root, run_id), {"report": report})
            lock.generate_start_plan_verbose_report(root, run_id)
            visible = root / "session-reports" / run_id / "start-plan.md"
            visible.write_text("# Legacy plan\n\n```json\n{}\n```\n", encoding="utf-8")

            output = io.StringIO()
            with mock.patch.object(sys, "argv", ["planning-lock.py", "show", "--root", str(root), "--run-id", run_id]):
                with contextlib.redirect_stdout(output):
                    self.assertEqual(lock.main(), 0)
            refreshed_verbose = visible.read_text(encoding="utf-8")

        rendered = output.getvalue()
        self.assertIn("# TailTrail Start Plan", rendered)
        self.assertIn("## Command Reference Registry", rendered)
        self.assertIn("## Validation Requirements And Focused Validation Matrix", rendered)
        self.assertIn("## Implementation Boundary", rendered)
        self.assertIn("## Approval Checklist", rendered)
        self.assertIn("## Review Cycles Summary", rendered)
        self.assertIn("session-reports/run-public-plan/start-plan.md", rendered)
        self.assertNotIn('"writes_allowed"', rendered)
        self.assertNotIn("```json", refreshed_verbose)

    def test_initial_review_is_cycle_one_not_zero_revisions(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run = root / ".tailtrail" / "runs" / "run-cycle-one"
            run.mkdir(parents=True)
            (run / "events.jsonl").write_text("", encoding="utf-8")
            summary = audit._build_review_cycles_summary(root, "run-cycle-one")

        self.assertEqual(summary["total_review_cycles"], 1)
        self.assertEqual(summary["revision_cycles"], 0)
        self.assertEqual(summary["cycles"][0]["status"], "initial-review")

    def test_normal_plan_requires_a_clean_audit_before_ready_for_approval(self) -> None:
        report = sample_report()
        requirements = report["navigator"]["requirement_matrix"]  # type: ignore[index]
        rendered = verbose.generate_start_plan_normal(
            "run-audit-gate", requirements, {}, str(report["goal"]),
            plan_data={"report": report, "planning_lock": {"status": "awaiting-approval"}},
        )

        self.assertIn("Mandatory planning audit is clean", rendered)
        self.assertIn("NOT READY FOR APPROVAL", rendered)
        self.assertIn("clean mandatory planning audit", rendered)


if __name__ == "__main__":
    unittest.main()
