from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from tests import test_workflow_template_execution as template_tests
from workflow_runtime import adapters, compiler, correction, evidence, executor, freshness, ownership, resume, retry, storage, task_scope, transitions


class WorkflowFreshnessRecoveryTests(unittest.TestCase):
    def _fixture(self) -> dict:
        return json.loads((template_tests.FIXTURES / "small-change.json").read_text(encoding="utf-8"))

    def _activate(self, root: Path, suffix: str) -> tuple[str, str, unittest.TestCase]:
        helper = template_tests.WorkflowTemplateExecutionTests(methodName="test_status_is_read_only_and_missing_authority_stops_before_dispatch")
        workflow_id, uid = helper._activate(root, self._fixture(), suffix)
        task_scope.initialize(root, workflow_id)
        return workflow_id, uid, helper

    def _fail_bootstrap(self, root: Path, workflow_id: str, uid: str, helper: unittest.TestCase) -> None:
        stage = compiler.show(root, workflow_id)["stages"][0]
        executor.start(root, workflow_id, "bootstrap", None)
        approval_id = helper._approval(root, workflow_id, stage)
        executor.start(root, workflow_id, "bootstrap", approval_id)
        result = helper._result("bootstrap", uid, "bootstrap", root, workflow_id); result["outcome"] = "fail"
        result_ref = ".tailtrail/results/bootstrap-fail.json"; destination = root / result_ref
        destination.parent.mkdir(parents=True, exist_ok=True); destination.write_text(json.dumps(result), encoding="utf-8")
        adapters.record(root, workflow_id, "bootstrap", "bootstrap", result_ref)
        executor.finish(root, workflow_id, "bootstrap")

    def test_all_eight_freshness_types_are_automatic_and_dependency_scoped(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); workflow_id, _, _ = self._activate(root, "-freshness")
            before = freshness.snapshot(root, workflow_id)
            key_by_type = {"source-edit":"scoped_sources", "manifest-change":"manifests", "policy-change":"policies", "graph-stale":"graph_fingerprint", "doc-only-edit":"scoped_docs", "branch-change":"repository_identity", "dependency-add":"dependencies", "security-finding":"security_fingerprint"}
            results = {}
            for change_type, key in key_by_type.items():
                after = json.loads(json.dumps(before))
                after[key] = "sha256:changed" if isinstance(after[key], str) else {**after[key], f"{change_type}.fixture":"sha256:changed"}
                baseline = {"revision":1, "snapshot":before, "snapshot_fingerprint":"sha256:baseline"}
                with patch("workflow_runtime.freshness.ensure", return_value=baseline), patch("workflow_runtime.freshness.snapshot", return_value=after):
                    results[change_type] = freshness.assess(root, workflow_id)
        self.assertEqual(set(results), freshness.CHANGE_TYPES)
        self.assertEqual(results["doc-only-edit"]["status"], "documentation-only")
        self.assertEqual(results["doc-only-edit"]["affected_stage_ids"], [])
        self.assertIn("implement", results["source-edit"]["affected_stage_ids"])
        self.assertIn("bootstrap", results["branch-change"]["affected_stage_ids"])
        self.assertIn("review", results["security-finding"]["affected_stage_ids"])

    def test_low_risk_retry_is_bounded_idempotent_and_records_attempt_receipts(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); workflow_id, uid, helper = self._activate(root, "-retry")
            self._fail_bootstrap(root, workflow_id, uid, helper)
            decision = retry.decide(root, workflow_id, "bootstrap")
            self.assertTrue(decision["eligible"]); operation_id = decision["operation_id"]
            handoff = retry.prepare(root, workflow_id, "bootstrap")
            self.assertEqual(handoff["operation_id"], operation_id)
            result = helper._result("bootstrap", uid, "bootstrap", root, workflow_id)
            result_ref = ".tailtrail/results/bootstrap-retry.json"; (root / result_ref).write_text(json.dumps(result), encoding="utf-8")
            recorded = retry.record(root, workflow_id, "bootstrap", result_ref)
            self.assertEqual(recorded["attempt"]["outcome"], "pass")
            self.assertFalse(retry.decide(root, workflow_id, "bootstrap")["eligible"])
            self.assertEqual(len(retry.show(root, workflow_id)["attempts"]), 2)

    def test_project_writes_never_retry_and_repeated_failure_preserves_recovery_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); workflow_id, uid, helper = self._activate(root, "-recovery")
            self._fail_bootstrap(root, workflow_id, uid, helper)
            duplicate = correction.route(root, workflow_id, "bootstrap")
            second = correction.route(root, workflow_id, "bootstrap", "unchanged")
            third = correction.route(root, workflow_id, "bootstrap", "regressed")
            self.assertEqual(duplicate["route_status"], "duplicate-suppressed")
            self.assertEqual(second["status"], "recovery-replan")
            self.assertEqual(third["status"], "needs-decision")
            continuation = resume.plan(root, workflow_id)
            self.assertEqual(continuation["next_action"], "retry")
            self.assertEqual(continuation["preserved_requirement_uids"], [uid])

            # A project-write stage is denied even when its state is failed.
            plan = compiler.show(root, workflow_id); implement = next(row for row in plan["stages"] if row["adapter_action_class"] == "write_project")
            projection = storage.status(root, workflow_id)["last_valid_projection"]
            projected = json.loads(json.dumps(projection)); projected["stages"][implement["stage_id"]]["status"] = "failed"
            with patch("workflow_runtime.retry.storage.status", return_value={"last_valid_projection":projected}):
                denied = retry.decide(root, workflow_id, implement["stage_id"])
            self.assertFalse(denied["eligible"])
            self.assertIn("never retry", denied["reason"])

    def test_checkpoints_are_versioned_and_show_is_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); workflow_id, _, _ = self._activate(root, "-checkpoints")
            first = freshness.checkpoint(root, workflow_id, "approved-baseline")
            second = freshness.checkpoint(root, workflow_id, "stage-passed:bootstrap")
            before = list((ownership.binding_path(root, workflow_id).parent / "freshness").glob("assessment-*.json"))
            shown = freshness.show(root, workflow_id)
            after = list((ownership.binding_path(root, workflow_id).parent / "freshness").glob("assessment-*.json"))
        self.assertEqual(first["revision"], 1); self.assertEqual(second["revision"], 2)
        self.assertEqual(second["previous_checkpoint_ref"], first["artifact_ref"])
        self.assertEqual(shown["checkpoint"]["revision"], 2)
        self.assertEqual(before, after)

    def test_new_untracked_source_file_stales_graph_inventory_without_user_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); workflow_id, _, _ = self._activate(root, "-new-file")
            freshness.checkpoint(root, workflow_id, "approved-baseline")
            source = root / "src" / "new_handler.py"; source.parent.mkdir(parents=True, exist_ok=True)
            source.write_text("def handle():\n    return True\n", encoding="utf-8")
            result = freshness.assess(root, workflow_id)
        self.assertIn("graph-stale", result["change_types"])
        self.assertIn("discover", result["affected_stage_ids"])

    def test_accepted_evidence_incomplete_never_retries_or_becomes_success(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); workflow_id, uid, helper = self._activate(root, "-incomplete")
            self._fail_bootstrap(root, workflow_id, uid, helper)
            receipt = evidence.receipt_path(root, workflow_id); receipt.parent.mkdir(parents=True, exist_ok=True)
            receipt.write_text(json.dumps({"state":"evidence-incomplete-accepted"}), encoding="utf-8")
            decision = retry.decide(root, workflow_id, "bootstrap")
            continuation = resume.plan(root, workflow_id)
        self.assertFalse(decision["eligible"])
        self.assertIn("never authorizes retry", decision["reason"])
        self.assertEqual(continuation["status"], "needs-decision")


if __name__ == "__main__":
    unittest.main()
