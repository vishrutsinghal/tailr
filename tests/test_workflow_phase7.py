from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module; spec.loader.exec_module(module); return module


LOCK = load("phase7_lock", "scripts/planning-lock.py")
from workflow_runtime import capabilities, compiler, context, evidence, outcomes, ownership, storage, task_scope


class WorkflowPhase7Tests(unittest.TestCase):
    def setup_workflow(self, root: Path) -> tuple[str, str]:
        run_id = "phase7-run"; workflow_id = ownership.suggested_id(run_id)
        LOCK.create(root, "deliver compact workflow context", run_id)
        report = {"goal":"deliver compact workflow context", "guided_delivery":{"mode":"guided-delivery"}, "navigator":{"requirement_matrix":[{"display_id":"REQ-01","statement":"Preserve workflow boundaries", "kind":"change", "acceptance_criteria":["Contracts validate"], "preserve_rules":["No raw data"], "likely_paths":["scripts/"], "evidence_plan":["unit test"]}]}}
        LOCK.save_start_report(root, run_id, report); LOCK.activate(root, run_id, True)
        ownership.bind(root, run_id, workflow_id)
        capabilities.propose(root, workflow_id, ["code-graph-mapper", "requirement-completion-harness", "evidence-aware-testing", "review"])
        task_scope.initialize(root, workflow_id); storage.initialize(root, workflow_id); compiler.compile(root, workflow_id); evidence.collect(root, workflow_id)
        return run_id, workflow_id

    def test_context_resume_and_linked_telemetry_are_compact_and_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); run_id, workflow_id = self.setup_workflow(root)
            receipt = context.record(root, workflow_id, "bootstrap", 400, [".tailtrail/context/bootstrap.json"], "structured-lossless", "reduced", [".tailtrail/context/retrieve.json"])
            telemetry = root / ".tailtrail" / "host-usage.json"; telemetry.write_text(json.dumps({"workflow_id":workflow_id,"tailtrail_run_id":run_id,"stage_id":"bootstrap","provider":"openai","usage":{"total_tokens":42}}), encoding="utf-8")
            measured = context.record_telemetry(root, workflow_id, "bootstrap", ".tailtrail/host-usage.json")
            summary = context.resume_summary(root, workflow_id)
            telemetry.write_text(json.dumps({"workflow_id":"ttw-other","tailtrail_run_id":run_id,"stage_id":"bootstrap","provider":"openai","usage":{"total_tokens":42}}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "linkage"):
                context.record_telemetry(root, workflow_id, "bootstrap", ".tailtrail/host-usage.json")
        self.assertEqual(receipt["token_posture"], "estimated")
        self.assertTrue(measured["measured"])
        self.assertEqual(summary["stages"][0]["token_posture"], "measured")
        self.assertNotIn("raw_prompt", json.dumps(summary).lower())
        self.assertNotIn("source_body", json.dumps(summary).lower())

    def test_incomplete_learning_is_not_positive_and_outputs_are_sanitized(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); _run_id, workflow_id = self.setup_workflow(root)
            evidence.sync_closure(root, "phase7-run", {"run_id":"phase7-run","overall_status":"evidence-incomplete","run_artifact":None})
            learning = outcomes.learning(root, workflow_id, "user")
            emitted = outcomes.emit(root, workflow_id)
            check = outcomes.validate(root, workflow_id)
        self.assertEqual(learning["status"], "not-eligible")
        self.assertEqual(learning["learning_kind"], "incomplete-delivery")
        self.assertEqual(emitted["event"]["closure_state"], "evidence-incomplete")
        self.assertEqual(emitted["meta"]["signals"]["missing_evidence"], "present")
        self.assertTrue(check["valid"])
        self.assertNotIn("raw_prompt", json.dumps(emitted).lower())
        self.assertNotIn("raw_log", json.dumps(emitted).lower())


if __name__ == "__main__": unittest.main()
