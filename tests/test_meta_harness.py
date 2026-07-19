from __future__ import annotations

import importlib.util
import json
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


meta_harness_analyze = load_script("meta_harness_analyze_test", "scripts/meta-harness-analyze.py")
meta_harness_propose = load_script("meta_harness_propose_test", "scripts/meta-harness-propose.py")


def shared_event(**overrides):
    event = {
        "schema_version": "1",
        "event_type": "harness_summary",
        "tailtrail_version": "local",
        "created_month": "2026-07",
        "task_type": "bug-fix",
        "language_family": "java",
        "workflow_selected": ["aidlc", "review"],
        "review_scope": "uncommitted",
        "requirement_fulfillment": "partially-aligned",
        "clarification_needed": False,
        "validation_fit": "weak",
        "token_budget_fit": "underestimated",
        "metric_confidence": "weak",
        "learning_signal": "weak",
        "scanner_type": "sonar",
        "issue_type": "validation-gap",
        "token_strategy": "scanner-focused-summary",
        "token_exactness_class": "structure-exact",
        "token_evidence_label": "local-evidence",
        "token_reduction_band": "high",
        "token_proof_label": "local-evidence",
        "token_quality_outcome": "not-run",
        "token_holdout": "unknown",
        "token_confidence_gate": "not-measured",
        "overall_fit": "medium",
        "overall_score_band": "60-79",
        "dimension_fits": {"validation_fit": "weak", "metric_confidence": "weak"},
        "artifact_presence": {"quality_events": "present"},
        "graph_cache_status": "missing",
        "graph_cache_source": "none",
        "recommendation_codes": ["strengthen-validation-evidence"],
        "privacy": "Commit-friendly categorical TailTrail harness metadata only. No prompts, responses, source, diffs, paths, repo names, users, emails, tickets, private URLs, package names, scanner raw output, secrets, or exact token usage.",
    }
    event.update(overrides)
    return event


class MetaHarnessTests(unittest.TestCase):
    def test_analyze_groups_repeated_sanitized_events(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "harness-summary.jsonl"
            events = [shared_event(), shared_event(), shared_event(task_type="feature", workflow_selected=["review"])]
            path.write_text("".join(json.dumps(event, sort_keys=True) + "\n" for event in events), encoding="utf-8")

            analysis = meta_harness_analyze.build_analysis([path], threshold=2)

        self.assertEqual(analysis["valid_event_count"], 3)
        self.assertEqual(analysis["invalid_event_count"], 0)
        self.assertEqual(analysis["registry_maturity"]["status"], "healthy")
        self.assertGreaterEqual(analysis["registry_maturity"]["feature_count"], 1)
        categories = {item["category"] for item in analysis["findings"]}
        self.assertIn("validation-fit-gap", categories)
        self.assertIn("graph-cache-gap", categories)
        self.assertIn("scanner-graph-gap", categories)
        markdown = meta_harness_analyze.render_markdown(analysis)
        self.assertIn("TailTrail Meta-Harness Analysis", markdown)
        self.assertIn("Registry Maturity", markdown)
        self.assertIn("Do not use this output to score individual developers", markdown)

    def test_analyze_rejects_private_looking_shared_event(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "harness-summary.jsonl"
            path.write_text(json.dumps(shared_event(task_type="/private/repo")) + "\n", encoding="utf-8")

            analysis = meta_harness_analyze.build_analysis([path], threshold=2)

        self.assertEqual(analysis["valid_event_count"], 0)
        self.assertEqual(analysis["invalid_event_count"], 1)
        self.assertEqual(analysis["input_issue_count"], 0)
        self.assertIn("sanitizer", analysis["invalid_issues"][0].lower())

    def test_missing_input_is_not_invalid_event(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "missing.jsonl"
            analysis = meta_harness_analyze.build_analysis([path], threshold=2)

        self.assertEqual(analysis["valid_event_count"], 0)
        self.assertEqual(analysis["invalid_event_count"], 0)
        self.assertEqual(analysis["input_issue_count"], 1)
        self.assertIn("input missing", analysis["input_issues"][0])

    def test_readiness_tiers_stay_quiet_without_valid_evidence(self) -> None:
        analysis = meta_harness_analyze.build_analysis_from_events([], [], input_count=0, threshold=2, input_issues=[])

        readiness = meta_harness_analyze.build_readiness(analysis)
        tiers = {item["tier"]: item for item in readiness["tiers"]}

        self.assertEqual(tiers["developer-task"]["decision"], "stay_quiet")
        self.assertEqual(tiers["repo-maintainer"]["decision"], "stay_quiet")
        self.assertEqual(tiers["central-tailtrail-maintainer"]["decision"], "stay_quiet")

    def test_readiness_tiers_advise_repo_maintainer_for_sanitizer_issues(self) -> None:
        analysis = meta_harness_analyze.build_analysis_from_events(
            [shared_event(), shared_event()],
            ["line 1: unsafe text marker"],
            input_count=3,
            threshold=2,
            input_issues=[],
        )

        readiness = meta_harness_analyze.build_readiness(analysis)
        tiers = {item["tier"]: item for item in readiness["tiers"]}

        self.assertEqual(tiers["repo-maintainer"]["decision"], "advise_repo_maintainer")
        self.assertEqual(tiers["central-tailtrail-maintainer"]["decision"], "advise_repo_maintainer")

    def test_readiness_tiers_recommend_central_improvement_for_clean_repeated_findings(self) -> None:
        analysis = meta_harness_analyze.build_analysis_from_events(
            [shared_event(), shared_event()],
            [],
            input_count=2,
            threshold=2,
            input_issues=[],
        )

        readiness = meta_harness_analyze.build_readiness(analysis)
        tiers = {item["tier"]: item for item in readiness["tiers"]}
        markdown = meta_harness_analyze.render_readiness_markdown(readiness)

        self.assertEqual(tiers["developer-task"]["decision"], "stay_quiet")
        self.assertEqual(tiers["repo-maintainer"]["decision"], "advise_repo_maintainer")
        self.assertEqual(tiers["central-tailtrail-maintainer"]["decision"], "recommend_central_tailtrail_improvement")
        self.assertIn("Central product improvement requires clean sanitized evidence", markdown)

    def test_propose_creates_reviewable_candidate_without_editing_files(self) -> None:
        analysis = meta_harness_analyze.build_analysis_from_events(
            [shared_event(), shared_event()],
            [],
            input_count=2,
            threshold=2,
        )
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "scripts").mkdir()
            (root / "scripts" / "navigator_core.py").write_text("def classify_goal():\n    pass\n", encoding="utf-8")

            proposal = meta_harness_propose.build_proposal(root, analysis, "MH-2026-07-001")

        self.assertEqual(proposal["status"], "proposed")
        self.assertEqual(proposal["proposal_id"], "MH-2026-07-001")
        self.assertEqual(proposal["central_readiness_decision"], "recommend_central_tailtrail_improvement")
        self.assertTrue(proposal["registry_validation"]["valid"])
        self.assertGreaterEqual(len(proposal["affected_features"]), 1)
        self.assertEqual(proposal["proposal_evidence_label"], "local-evidence")
        self.assertTrue(proposal["registry_validation"]["feature_impacts"])
        self.assertTrue(proposal["candidate_edits"])
        self.assertIn("Recommended changes only", proposal["user_note"])
        rendered = meta_harness_propose.render_markdown(proposal)
        self.assertIn("Review these recommendations before adding them", rendered)
        self.assertIn("Registry Impact", rendered)

    def test_proposal_evidence_label_is_capped_by_weakest_registry_feature(self) -> None:
        analysis = meta_harness_analyze.build_analysis_from_events(
            [shared_event(), shared_event()],
            [],
            input_count=2,
            threshold=2,
        )
        token_finding = next(item for item in analysis["findings"] if item["category"] == "token-budget-underestimate")

        with tempfile.TemporaryDirectory() as temp:
            proposal = meta_harness_propose.build_proposal(Path(temp), analysis, "MH-2026-07-002", token_finding["finding_id"])

        self.assertEqual(proposal["status"], "proposed")
        self.assertIn("token-harness", proposal["affected_features"])
        self.assertEqual(proposal["proposal_evidence_label"], "estimated")

    def test_proposal_rejects_unknown_registry_feature(self) -> None:
        analysis = meta_harness_analyze.build_analysis_from_events(
            [shared_event(), shared_event()],
            [],
            input_count=2,
            threshold=2,
        )
        analysis["findings"][0]["affected_features"] = ["unknown-feature"]

        with tempfile.TemporaryDirectory() as temp:
            proposal = meta_harness_propose.build_proposal(Path(temp), analysis, "MH-2026-07-003", analysis["findings"][0]["finding_id"])

        self.assertEqual(proposal["status"], "no_proposal")
        self.assertIn("Registry-aware proposal validation failed", proposal["reason"])
        self.assertFalse(proposal["registry_validation"]["valid"])
        self.assertIn("unknown-feature", proposal["registry_validation"]["issues"][0])

    def test_proposal_record_and_status_are_local(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            record = meta_harness_propose.record_status(
                root,
                "MH-2026-07-001",
                "accepted",
                "accepted after tests",
                "validation improved",
            )
            status = meta_harness_propose.status_summary(root)

        self.assertEqual(record["status"], "accepted")
        self.assertEqual(status["proposal_count"], 1)
        self.assertEqual(status["status_counts"]["accepted"], 1)
        self.assertEqual(status["path"], ".tailtrail/meta-harness-proposals.jsonl")


if __name__ == "__main__":
    unittest.main()
