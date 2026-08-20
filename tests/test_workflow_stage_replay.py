from __future__ import annotations

import importlib.util
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


lock = load("workflow_stage_replay_lock_test", "scripts/planning-lock.py")
from workflow_runtime import approvals, capabilities, compiler, ownership, state, storage, transitions


class WorkflowStageReplayTests(unittest.TestCase):
    def _workflow(self, root: Path) -> str:
        run_id = "stage-replay-run"; workflow_id = "ttw-stage-replay"
        lock.create(root, "validate a replayable stage", run_id)
        lock.save_start_report(root, run_id, {"goal": "validate a replayable stage", "guided_delivery": {"mode": "guided-delivery"}, "navigator": {"requirement_matrix": [{"display_id": "REQ-01", "statement": "Replay stage state", "kind": "change", "acceptance_criteria": ["Replay matches"], "preserve_rules": ["Journal remains append-only"], "likely_paths": ["src/service.py"], "evidence_plan": ["focused test"]}]}})
        lock.activate(root, run_id, True); state.create(root, run_id, workflow_id)
        capabilities.propose(root, workflow_id, ["code-graph-mapper", "review"]); compiler.compile(root, workflow_id)
        transitions.ensure_stages(root, workflow_id)
        return workflow_id

    def _approval(self, root: Path, workflow_id: str, stage_id: str) -> str:
        plan = compiler.show(root, workflow_id)
        stage = next(row for row in plan["stages"] if row["stage_id"] == stage_id)
        record = approvals.decide(root, workflow_id, stage_ids=[stage_id], action_classes=[stage["adapter_action_class"]], operation_kind="other-guarded", operation_ref=plan["artifact"], decision="approved", rationale=f"Approve only the {stage_id} typed transition for this replay test.")
        return str(record["record"]["approval_id"])

    def test_stage_prerequisites_and_replay_projection_are_authoritative(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); workflow_id = self._workflow(root)
            with self.assertRaisesRegex(ValueError, "illegal-stage-transition"):
                state.transition_stage(root, workflow_id, "graph-impact", "running", "stage-started")
            state.transition_stage(root, workflow_id, "scope-diff", "ready", "stage-ready")
            state.transition_stage(root, workflow_id, "scope-diff", "running", "stage-started", self._approval(root, workflow_id, "scope-diff"))
            state.transition_stage(root, workflow_id, "scope-diff", "passed", "stage-passed")
            state.transition_stage(root, workflow_id, "graph-impact", "ready", "stage-ready")
            state.transition_stage(root, workflow_id, "graph-impact", "running", "stage-started", self._approval(root, workflow_id, "graph-impact"))
            state.transition_stage(root, workflow_id, "graph-impact", "passed", "stage-passed")
            saved = storage.status(root, workflow_id)["last_valid_projection"]
            replayed = storage.replay(root, workflow_id)

        self.assertTrue(replayed["valid"])
        self.assertEqual(replayed["replayed_projection"], saved)
        self.assertEqual(saved["stages"]["scope-diff"]["status"], "passed")
        self.assertEqual(saved["stages"]["graph-impact"]["status"], "passed")

    def test_stage_stale_and_retry_path_is_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); workflow_id = self._workflow(root)
            approval_id = self._approval(root, workflow_id, "scope-diff")
            for next_state, reason in (("ready", "stage-ready"), ("running", "stage-started"), ("passed", "stage-passed"), ("stale", "input-stale"), ("ready", "retry-eligible")):
                result = state.transition_stage(root, workflow_id, "scope-diff", next_state, reason, approval_id if next_state == "running" else None)

        self.assertEqual(result["stage_states"]["scope-diff"]["status"], "ready")

    def test_doctor_classifies_terminal_and_external_dependency_without_repair(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); workflow_id = self._workflow(root)
            state.transition(root, workflow_id, "blocked", "external-dependency")
            blocked = state.doctor(root, workflow_id)
            state.cancel(root, workflow_id, True)
            terminal = state.doctor(root, workflow_id)

        self.assertIn("external-dependency", blocked["classifications"])
        self.assertIn("terminal-state", terminal["classifications"])

    def test_doctor_classifies_missing_authority_stale_evidence_and_corruption(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lock.create(root, "await authority", "authority-run")
            lock.save_start_report(root, "authority-run", {"goal": "await authority", "guided_delivery": {"mode": "guided-delivery"}, "navigator": {"requirement_matrix": [{"display_id": "REQ-01", "statement": "Await authority", "kind": "change", "acceptance_criteria": ["Approval is explicit"], "preserve_rules": ["No execution"], "likely_paths": ["src/service.py"], "evidence_plan": ["approval"]}]}})
            lock.activate(root, "authority-run", True); ownership.bind(root, "authority-run", "ttw-authority-run")
            storage.initialize(root, "ttw-authority-run"); storage.lifecycle(root, "ttw-authority-run", "workflow-created")
            transitions.workflow(root, "ttw-authority-run", "awaiting_approval", "workflow-created")
            authority = state.doctor(root, "ttw-authority-run")
            workflow_id = self._workflow(root)
            state.transition_stage(root, workflow_id, "scope-diff", "ready", "stage-ready")
            state.transition_stage(root, workflow_id, "scope-diff", "running", "stage-started", self._approval(root, workflow_id, "scope-diff"))
            state.transition_stage(root, workflow_id, "scope-diff", "passed", "stage-passed")
            state.transition_stage(root, workflow_id, "scope-diff", "stale", "input-stale")
            stale = state.doctor(root, workflow_id)
            journal = storage.journal_path(root, workflow_id)
            journal.write_text(journal.read_text(encoding="utf-8") + "not-json\n", encoding="utf-8")
            corrupt = state.doctor(root, workflow_id)

        self.assertIn("missing-authority", authority["classifications"])
        self.assertIn("stale-evidence", stale["classifications"])
        self.assertIn("corruption", corrupt["classifications"])


if __name__ == "__main__":
    unittest.main()
