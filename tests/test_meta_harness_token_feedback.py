from __future__ import annotations

import argparse
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


harness_review = load_script("harness_review_token_feedback_test", "scripts/harness-review.py")
meta_harness_analyze = load_script("meta_harness_analyze_token_feedback_test", "scripts/meta-harness-analyze.py")
meta_harness_propose = load_script("meta_harness_propose_token_feedback_test", "scripts/meta-harness-propose.py")


def shared_event(**overrides):
    event = {
        "schema_version": "1",
        "event_type": "harness_summary",
        "tailtrail_version": "local",
        "created_month": "2026-07",
        "task_type": "bug-fix",
        "language_family": "java",
        "workflow_selected": ["navigator", "token-harness"],
        "review_scope": "uncommitted",
        "requirement_fulfillment": "aligned",
        "clarification_needed": False,
        "validation_fit": "weak",
        "token_budget_fit": "ok",
        "metric_confidence": "medium",
        "learning_signal": "medium",
        "scanner_type": "sonar",
        "issue_type": "quality-risk",
        "token_strategy": "scanner-focused-summary",
        "token_exactness_class": "structure-exact",
        "token_evidence_label": "local-evidence",
        "token_reduction_band": "high",
        "token_proof_label": "local-evidence",
        "token_quality_outcome": "fail",
        "token_holdout": "false",
        "token_confidence_gate": "not-measured",
        "overall_fit": "medium",
        "overall_score_band": "60-79",
        "dimension_fits": {"validation_fit": "weak", "metric_confidence": "medium"},
        "artifact_presence": {"token_harness_events": "present"},
        "graph_cache_status": "available",
        "graph_cache_source": "shared",
        "recommendation_codes": ["token-feedback"],
        "privacy": "Commit-friendly categorical TailTrail harness metadata only. No prompts, responses, source, diffs, paths, repo names, users, emails, tickets, private URLs, package names, scanner raw output, secrets, or exact token usage.",
    }
    event.update(overrides)
    return event


class MetaHarnessTokenFeedbackTests(unittest.TestCase):
    def test_shared_summary_derives_sanitized_token_fields_from_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            trail = root / ".tailtrail"
            trail.mkdir()
            (trail / "token-harness-events.jsonl").write_text(
                json.dumps(
                    {
                        "schema_version": "1",
                        "type": "tailtrail-token-harness-event",
                        "sequence": 1,
                        "event_id": "th-20260718-000001",
                        "created_at": "2026-07-18T00:00:00+00:00",
                        "event_type": "context_receipt",
                        "task_type": "bug-fix",
                        "content_type": "scanner-output",
                        "strategy": "scanner-focused-summary",
                        "exactness_class": "structure-exact",
                        "tokens_before": 1000,
                        "tokens_after": 200,
                        "tokens_saved": 800,
                        "evidence_label": "local-evidence",
                        "validation_outcome": "pass",
                        "privacy": "No raw prompt, source, log, path, secret, repo name, or user identity.",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            review = harness_review.build_review(root, None)
            args = argparse.Namespace(
                task_type="bug-fix",
                language_family="java",
                workflow=["navigator,token-harness"],
                review_scope="uncommitted",
                requirement_fulfillment="aligned",
                clarification_needed=False,
                validation_fit=None,
                token_budget_fit=None,
                metric_confidence=None,
                learning_signal=None,
                scanner_type="sonar",
                issue_type="quality-risk",
            )
            event = harness_review.shared_event_from_review(review, args)
            harness_review.validate_shared_event(event)

        self.assertEqual(event["token_strategy"], "scanner-focused-summary")
        self.assertEqual(event["token_exactness_class"], "structure-exact")
        self.assertEqual(event["token_reduction_band"], "high")
        self.assertEqual(event["token_evidence_label"], "local-evidence")

    def test_shared_summary_rejects_unsafe_token_value(self) -> None:
        event = shared_event(token_strategy="https://private.example/scanner")

        with self.assertRaises(SystemExit):
            harness_review.validate_shared_event(event)

    def test_analysis_emits_token_strategy_quality_and_proof_gap_findings(self) -> None:
        analysis = meta_harness_analyze.build_analysis_from_events(
            [shared_event(), shared_event()],
            [],
            input_count=2,
            threshold=2,
        )
        categories = {finding["category"] for finding in analysis["findings"]}

        self.assertIn("token-strategy-quality-risk", categories)
        self.assertIn("token-proof-gap", categories)
        self.assertIn("token-holdout-gap", categories)
        self.assertEqual(analysis["distributions"]["token_strategy"]["scanner-focused-summary"], 2)

    def test_analysis_emits_low_reduction_and_exactness_mismatch_findings(self) -> None:
        events = [
            shared_event(token_reduction_band="low", token_exactness_class="must-be-exact", token_strategy="json-structure-summary"),
            shared_event(token_reduction_band="none", token_exactness_class="must-be-exact", token_strategy="json-structure-summary"),
        ]
        analysis = meta_harness_analyze.build_analysis_from_events(events, [], input_count=2, threshold=2)
        categories = {finding["category"] for finding in analysis["findings"]}

        self.assertIn("token-reduction-too-low", categories)
        self.assertIn("token-exactness-mismatch", categories)

    def test_proposal_maps_token_reducer_finding_to_token_files(self) -> None:
        analysis = meta_harness_analyze.build_analysis_from_events(
            [shared_event(), shared_event()],
            [],
            input_count=2,
            threshold=2,
        )
        finding = next(item for item in analysis["findings"] if item["category"] == "token-strategy-quality-risk")
        with tempfile.TemporaryDirectory() as temp:
            proposal = meta_harness_propose.build_proposal(Path(temp), analysis, "MH-2026-07-TH6", finding["finding_id"])

        self.assertEqual(proposal["status"], "proposed")
        files = {edit["file"] for edit in proposal["candidate_edits"]}
        self.assertIn("scripts/token-harness-reduce.py", files)
        self.assertIn("token-harness", proposal["affected_features"])


if __name__ == "__main__":
    unittest.main()
