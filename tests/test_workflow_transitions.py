from __future__ import annotations

import importlib.util
import json
import subprocess
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
    sys.modules[name] = module; spec.loader.exec_module(module)
    return module


lock = load("workflow_transitions_lock_test", "scripts/planning-lock.py")
from workflow_runtime import capabilities, compiler, contracts, reason_codes, state, storage, transitions


class WorkflowTransitionTests(unittest.TestCase):
    def _approved(self, root: Path, run_id: str) -> None:
        lock.create(root, "deliver one controlled change", run_id)
        lock.save_start_report(root, run_id, {"goal": "deliver one controlled change", "guided_delivery": {"mode": "guided-delivery"}, "navigator": {"requirement_matrix": [{"display_id": "REQ-01", "statement": "Deliver the approved behavior", "kind": "change", "acceptance_criteria": ["Behavior is proven"], "preserve_rules": ["Existing behavior remains"], "likely_paths": ["src/service.py"], "evidence_plan": ["focused test"]}]}})
        lock.activate(root, run_id, True)

    def _compiled(self, root: Path, run_id: str, workflow_id: str) -> None:
        self._approved(root, run_id)
        state.create(root, run_id, workflow_id)
        capabilities.propose(root, workflow_id, ["code-graph-mapper", "requirement-completion-harness", "evidence-aware-testing", "review"])
        compiler.compile(root, workflow_id); transitions.ensure_stages(root, workflow_id)

    def test_every_transition_table_edge_and_rejection_is_deterministic(self) -> None:
        for scope, table in (("workflow", reason_codes.WORKFLOW_TRANSITIONS), ("stage", reason_codes.STAGE_TRANSITIONS)):
            all_states = set(table)
            for previous, allowed in table.items():
                for next_state in all_states:
                    with self.subTest(scope=scope, previous=previous, next_state=next_state):
                        contract = transitions.transition_contract(scope, "subject", previous, next_state, "stage-ready")
                        self.assertEqual(contract["legal"], next_state in allowed)
                        self.assertEqual(contracts.validate_artifact(contract), [])

    def test_workflow_terminal_states_fail_closed_and_follow_up_is_linked(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self._approved(root, "parent-run")
            state.create(root, "parent-run", "ttw-parent-run")
            state.transition(root, "ttw-parent-run", "running", "workflow-started")
            completed = state.transition(root, "ttw-parent-run", "completed", "workflow-completed")
            with self.assertRaisesRegex(ValueError, "illegal-workflow-transition"):
                state.transition(root, "ttw-parent-run", "running", "workflow-started")
            self._approved(root, "child-run")
            child = state.follow_up(root, "ttw-parent-run", "child-run", "ttw-child-run")
            parent = state.show(root, "ttw-parent-run")

        self.assertEqual(completed["workflow_status"], "completed")
        self.assertEqual(child["parent_workflow_id"], "ttw-parent-run")
        self.assertEqual(parent["successor_workflow_id"], "ttw-child-run")

    def test_pause_resume_preserve_stage_and_artifact_projection(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self._compiled(root, "preserve-run", "ttw-preserve-run")
            before = state.show(root, "ttw-preserve-run")
            state.pause(root, "ttw-preserve-run"); after = state.resume(root, "ttw-preserve-run")

        for key in ("requirements", "current_requirement", "stage_states", "evidence_refs", "scope", "reservation"):
            self.assertEqual(before[key], after[key], key)

    def test_workflow_completion_rejects_an_incomplete_registered_graph(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self._compiled(root, "incomplete-run", "ttw-incomplete-run")
            state.transition(root, "ttw-incomplete-run", "running", "workflow-started")
            with self.assertRaisesRegex(ValueError, "stage-incomplete-for-completion"):
                state.transition(root, "ttw-incomplete-run", "completed", "workflow-completed")

    def test_supersession_preserves_both_records_and_links_them(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self._approved(root, "old-run"); state.create(root, "old-run", "ttw-old-run")
            self._approved(root, "new-run"); state.create(root, "new-run", "ttw-new-run")
            old = state.supersede(root, "ttw-old-run", "ttw-new-run")
            new = state.show(root, "ttw-new-run")

        self.assertEqual(old["workflow_status"], "superseded")
        self.assertEqual(old["successor_workflow_id"], "ttw-new-run")
        self.assertEqual(new["parent_workflow_id"], "ttw-old-run")

    def test_public_events_surface_and_structured_illegal_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self._approved(root, "events-run"); state.create(root, "events-run", "ttw-events-run")
            result = subprocess.run([sys.executable, (ROOT / "scripts" / "tailtrail.py").as_posix(), "workflow", "state", "events", "--root", root.as_posix(), "--workflow-id", "ttw-events-run"], cwd=ROOT, text=True, capture_output=True, check=False)
            illegal = subprocess.run([sys.executable, (ROOT / "scripts" / "tailtrail.py").as_posix(), "workflow", "state", "transition", "--root", root.as_posix(), "--workflow-id", "ttw-events-run", "--to", "completed", "--reason-code", "workflow-completed"], cwd=ROOT, text=True, capture_output=True, check=False)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(json.loads(result.stdout)["valid"])
        self.assertIn("workflow-ready", [row["event_type"] for row in json.loads(result.stdout)["events"]])
        self.assertEqual(illegal.returncode, 2)
        self.assertIn("reason_code=illegal-workflow-transition", illegal.stdout)

    def test_replay_rejects_a_rehashed_but_semantically_illegal_transition(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self._approved(root, "semantic-run"); state.create(root, "semantic-run", "ttw-semantic-run")
            path = storage.journal_path(root, "ttw-semantic-run")
            rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            ready = next(row for row in rows if row["event_type"] == "workflow-ready")
            ready["payload"]["from_state"] = "completed"
            previous = None
            for row in rows:
                row["previous_event_hash"] = previous; row["event_hash"] = storage._event_hash(row); previous = row["event_hash"]
            path.write_text("\n".join(json.dumps(row, sort_keys=True, separators=(",", ":")) for row in rows) + "\n", encoding="utf-8")
            replayed = storage.replay(root, "ttw-semantic-run")

        self.assertFalse(replayed["valid"])
        self.assertIn("illegal workflow transition", " ".join(replayed["issues"]))


if __name__ == "__main__":
    unittest.main()
