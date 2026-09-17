from __future__ import annotations

import importlib.util
import json
import shlex
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


ledger = load("closure_finalizer_ledger_test", "scripts/run-ledger.py")
anchor = load("closure_finalizer_anchor_test", "scripts/change-intent-anchor.py")
lock = load("closure_finalizer_lock_test", "scripts/planning_lock.py")
recorder = load("closure_finalizer_recorder_test", "scripts/closure-recorder.py")
evidence = load("closure_finalizer_evidence_test", "scripts/execution-evidence.py")
finalizer = load("closure_finalizer_test", "scripts/closure-finalizer.py")


class ClosureFinalizerTests(unittest.TestCase):
    def setup_run(self, root: Path, *, behavior_scenario: bool = True, extra_unapproved_file: bool = False) -> tuple[str, Path]:
        (root / "src").mkdir()
        (root / "tests").mkdir()
        (root / "src" / "service.py").write_text("def cancel():\n    return True\n", encoding="utf-8")
        (root / "tests" / "test_service.py").write_text("import unittest\n\nclass ServiceTest(unittest.TestCase):\n    def test_cancel(self):\n        self.assertTrue(True)\n", encoding="utf-8")
        if extra_unapproved_file:
            (root / "src" / "unapproved_helper.py").write_text("def helper():\n    return True\n", encoding="utf-8")
        lock.create(root, "cancel an order", "run")
        proposal = root / "proposal.json"
        command = f"{shlex.quote(sys.executable)} -m unittest discover -s tests -p test_service.py -v"
        proposal.write_text(json.dumps({"requirements": [{
            "statement": "Cancel an eligible order exactly once.", "acceptance_criteria": ["cancelled once"],
            "preserve_rules": ["shipped orders remain rejected"],
            "likely_paths": ["src/service.py", "tests/test_service.py"], "evidence_plan": [],
            "validation_contract": {"state": "required", "tiers": ["unit"], "commands": [command]},
            "architecture_contract": {"required_paths": [], "protected_paths": [], "forbidden_imports": []},
            "behavior_contract": {"scenarios": ([{
                "scenario_id": "eligible-cancellation", "preconditions": ["eligible order"],
                "action": "cancel order", "expected_outcome": "one cancellation", "preservation": ["shipped orders reject"],
                "evidence": [{"tier": "unit", "asserted_behavior": "Eligible order cancellation is idempotent."}],
            }] if behavior_scenario else [])},
        }]}), encoding="utf-8")
        anchor.draft(root, "run", proposal)
        uid = anchor.approve(root, "run")["requirements"][0]["requirement_uid"]
        lock.approve(root, "run", True)
        run = ledger.state_dir(root, "run")
        (run / "planning").mkdir(exist_ok=True)
        (run / "planning" / "execution-handoff-v1.json").write_text(json.dumps({"closure": {"selected_harnesses": [
            "Architecture Fitness Harness", "Behaviour Harness", "Maintainability Harness",
        ]}}), encoding="utf-8")
        input_path = root / "closure-input.json"
        input_path.write_text(json.dumps({
            "schema_version": "1", "type": "tailtrail-execution-closure-input", "run_id": "run",
            "changed_paths": ["src/service.py", "tests/test_service.py"],
            "receipts": [{"requirement_uids": [uid], "tier": "unit", "command_label": "cancellation unit proof",
                "command": command, "outcome": "pass", "environment": "local",
                "asserted_behavior": "Eligible order cancellation is idempotent."}],
        }), encoding="utf-8")
        evidence.run_command(root, "run", [uid], ["unit"], command, "cancellation unit proof", ["src/service.py", "tests/test_service.py"], True, 30)
        recorder.record(root, run_id="run")
        return uid, input_path

    def test_finalizes_selected_local_harnesses_and_completion_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.setup_run(root)
            result = finalizer.finalize(root, "run")
            activity = ledger.projection(root, "run")["activity"]
        self.assertFalse(result["reused"])
        self.assertEqual(result["overall_status"], "complete")
        self.assertEqual(set(result["assessments"]), {"Architecture Fitness Harness", "Behaviour Harness", "Maintainability Harness"})
        self.assertTrue(all(item["complete"] for item in result["assessments"].values()))
        self.assertEqual(result["higher_tier_evidence"]["status"], "pass")
        self.assertEqual(result["recovery"]["status"], "not-needed")
        self.assertEqual(result["context_continuity"]["status"], "none")
        self.assertEqual(activity["closure_finalized"], 1)

    def test_replay_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.setup_run(root)
            first = finalizer.finalize(root, "run")
            second = finalizer.finalize(root, "run")
            activity = ledger.projection(root, "run")["activity"]
        self.assertFalse(first["reused"])
        self.assertTrue(second["reused"])
        self.assertEqual(first["finalizer_id"], second["finalizer_id"])
        self.assertEqual(activity["closure_finalized"], 1)

    def test_new_execution_evidence_refreshes_a_previous_finalization(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            uid, _ = self.setup_run(root)
            first = finalizer.finalize(root, "run")
            approved = json.loads(
                (ledger.state_dir(root, "run") / "anchors" / "approved-v1.json").read_text(encoding="utf-8")
            )
            command = approved["requirements"][0]["validation_contract"]["commands"][0]
            evidence.append(root, "run", {
                "kind": "command-result", "requirement_uids": [uid],
                "changed_paths": ["src/service.py", "tests/test_service.py"], "tier": "unit",
                "command_label": "cancellation unit proof", "command": command,
                "outcome": "fail", "environment": "local",
                "asserted_behavior": "latest attempt failed",
            }, True)
            refreshed = finalizer.finalize(root, "run")
            replay = finalizer.finalize(root, "run")

        self.assertNotEqual(first["finalizer_id"], refreshed["finalizer_id"])
        self.assertFalse(refreshed["reused"])
        self.assertEqual("evidence-incomplete", refreshed["overall_status"])
        self.assertTrue(replay["reused"])
        self.assertEqual(refreshed["finalizer_id"], replay["finalizer_id"])

    def test_closure_refreshes_graph_and_records_hash_bound_run_mapping(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.setup_run(root)
            start_report = ledger.state_dir(root, "run") / "planning" / "start-report-v1.json"
            start_report.write_text(json.dumps({
                "schema_version": "1",
                "type": "tailtrail-start-report",
                "run_id": "run",
                "goal": "cancel an order",
                "report": {
                    "navigator": {
                        "scope_evidence": {
                            "decision_fingerprint": "sha256:" + "a" * 64,
                            "requirements": [{
                                "implementation_owners": ["src/service.py"],
                                "inspection_paths": [],
                                "proof_paths": ["tests/test_service.py"],
                            }],
                        }
                    }
                },
            }), encoding="utf-8")

            result = finalizer.finalize(root, "run")
            graph_cache = root / "tailtrail-meta" / "code-graph-cache.json"
            graph_cache_exists = graph_cache.is_file()
            mapping_index = json.loads(
                (root / "tailtrail-meta" / "navigator-run-mappings-v1.json").read_text(encoding="utf-8")
            )
            activity = ledger.projection(root, "run")["activity"]

        self.assertEqual(result["graph_lifecycle"]["action"], "create")
        self.assertTrue(graph_cache_exists)
        self.assertEqual(result["run_mapping"]["run_id"], "run")
        self.assertEqual(result["run_mapping"]["closure_status"], "complete")
        self.assertEqual(mapping_index["mappings"], [result["run_mapping"]])
        self.assertEqual(activity["navigator_graph_lifecycle_recorded"], 1)

    def test_finalizer_bridges_saved_evidence_when_no_manual_record_exists(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            uid, input_path = self.setup_run(root)
            records = ledger.state_dir(root, "run") / "closure-records"
            for path in records.glob("*"):
                path.unlink()
            result = finalizer.finalize(root, "run")
            recreated = [
                json.loads(path.read_text(encoding="utf-8"))
                for path in records.glob("closure-*.json")
                if json.loads(path.read_text(encoding="utf-8")).get("type") == "tailtrail-closure-record"
            ]

        self.assertEqual(result["overall_status"], "complete")
        self.assertEqual(len(recreated), 1)

    def test_selected_behavior_without_a_declared_scenario_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.setup_run(root, behavior_scenario=False)
            result = finalizer.finalize(root, "run")
        self.assertEqual(result["overall_status"], "evidence-incomplete")
        self.assertFalse(result["assessments"]["Behaviour Harness"]["complete"])
        self.assertIn("No receipt command", result["boundary"])

    def test_rejects_mismatched_input_before_recording_anything(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _, input_path = self.setup_run(root)
            payload = json.loads(input_path.read_text(encoding="utf-8"))
            payload["run_id"] = "other-run"
            input_path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "must match"):
                finalizer.finalize(root, "run", input_path)
            other_run = ledger.state_dir(root, "other-run")
        self.assertFalse(other_run.exists())

    def test_unapproved_changed_path_is_reported_as_unresolved_scope_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            uid, _ = self.setup_run(root, extra_unapproved_file=True)
            drift_input = root / "drift-input.json"
            drift_input.write_text(json.dumps({
                "schema_version": "1",
                "type": "tailtrail-execution-closure-input",
                "run_id": "run",
                "changed_paths": ["src/service.py", "tests/test_service.py", "src/unapproved_helper.py"],
                "receipts": [{
                    "requirement_uids": [uid],
                    "tier": "unit",
                    "command_label": "cancellation unit proof",
                    "command": "tailtrail-never-execute-finalizer-sentinel",
                    "outcome": "pass",
                    "environment": "local",
                    "asserted_behavior": "Eligible order cancellation is idempotent.",
                }],
            }), encoding="utf-8")

            result = finalizer.finalize(root, "run", drift_input)
            checkpoints = sorted((ledger.state_dir(root, "run") / "checkpoints").glob("checkpoint-*.json"))
            checkpoint = json.loads(checkpoints[-1].read_text(encoding="utf-8"))
            report = json.loads(Path(result["completion_report"]).read_text(encoding="utf-8"))

        self.assertEqual(result["overall_status"], "evidence-incomplete")
        self.assertEqual(checkpoint["scope_assessment"]["status"], "unresolved")
        self.assertEqual(checkpoint["scope_assessment"]["unexpected_paths"], ["src/unapproved_helper.py"])
        self.assertEqual(report["drift"]["status"], "unresolved")
        self.assertTrue(any(item.get("path") == "src/unapproved_helper.py" for item in report["drift"]["findings"]))


if __name__ == "__main__":
    unittest.main()
