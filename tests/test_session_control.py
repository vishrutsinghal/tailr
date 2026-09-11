from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / filename)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


SESSION = load("tailtrail_session_control_test", "session_control.py")
LOCK = load("tailtrail_session_lock_test", "planning-lock.py")
LEDGER = load("tailtrail_session_ledger_test", "run-ledger.py")
from workflow_runtime import capabilities, compiler, ownership, state as workflow_state, storage, task_scope


class SessionControlTests(unittest.TestCase):
    def _run(self, root: Path, run_id: str = "session-run") -> str:
        LOCK.create(root, "preserve one exact planning run", run_id)
        return run_id

    def test_attach_stop_and_exact_resume_preserve_canonical_lock(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); run_id = self._run(root)
            attached = SESSION.attach(root, run_id)
            stopped = SESSION.stop(root)
            lock_after_stop = LOCK.show(root, run_id)
            resumed = SESSION.resume(root, run_id)
            lock_after_resume = LOCK.show(root, run_id)
            events = LEDGER.read_events(LEDGER.state_dir(root, run_id) / "events.jsonl")

        self.assertEqual(attached["state"], "attached")
        self.assertEqual(stopped["state"], "detached")
        self.assertEqual(lock_after_stop["status"], "awaiting-approval")
        self.assertEqual(resumed["state"], "resumed-awaiting-approval")
        self.assertEqual(lock_after_resume["status"], "awaiting-approval")
        self.assertEqual(
            [row["event_type"] for row in events if row["event_type"].startswith("tailtrail_")],
            ["tailtrail_session_attached", "tailtrail_stop_requested", "tailtrail_session_detached", "tailtrail_session_resumed"],
        )

    def test_stop_is_idempotent_and_generation_does_not_advance_twice(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); run_id = self._run(root)
            SESSION.attach(root, run_id)
            first = SESSION.stop(root)
            second = SESSION.stop(root)
        self.assertFalse(first["idempotent"])
        self.assertTrue(second["idempotent"])
        self.assertEqual(first["attachment"]["fingerprint"], second["attachment"]["fingerprint"])

    def test_stop_without_any_run_is_successful_detached_noop(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            result = SESSION.stop(Path(temp))
        self.assertEqual(result["state"], "detached")
        self.assertIsNone(result["run_id"])
        self.assertTrue(result["idempotent"])

    def test_legacy_single_run_can_be_stopped_but_ambiguity_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self._run(root, "legacy-one")
            stopped = SESSION.stop(root)
            self.assertEqual(stopped["run_id"], "legacy-one")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self._run(root, "legacy-one"); self._run(root, "legacy-two")
            with self.assertRaisesRegex(ValueError, "multiple TailTrail runs"):
                SESSION.stop(root)

    def test_corrupt_attachment_and_cross_context_records_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); run_id = self._run(root)
            SESSION.attach(root, run_id, "context-a")
            self.assertEqual(SESSION.status(root, "context-b")["state"], "none")
            path = SESSION.attachment_path(root, "context-a")
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["run_id"] = "forged-run"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "fingerprint"):
                SESSION.status(root, "context-a")

    def test_resume_requires_safe_exact_identifier(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, "safe local identifier"):
                SESSION.resume(Path(temp), "../escape")

    def test_resume_blocks_target_drift_and_late_attachment_generation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root / "src").mkdir(); (root / "src" / "service.py").write_text("VALUE = 1\n", encoding="utf-8")
            run_id = self._run(root, "stale-run"); attached = SESSION.attach(root, run_id); SESSION.stop(root)
            (root / "src" / "new_owner.py").write_text("VALUE = 2\n", encoding="utf-8")
            resumed = SESSION.resume(root, run_id)
            with self.assertRaisesRegex(ValueError, "not attached"):
                SESSION.require_generation(root, attached["generation"])
        self.assertEqual(resumed["state"], "resume-stale")
        self.assertEqual(resumed["attachment"]["state"], "detached")

    def test_stop_pauses_ready_workflow_expires_authority_and_releases_reservation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root / "src").mkdir(); (root / "src" / "service.py").write_text("VALUE = 1\n", encoding="utf-8")
            run_id = "workflow-stop-run"; workflow_id = ownership.suggested_id(run_id)
            LOCK.create(root, "change the service safely", run_id)
            LOCK.save_start_report(root, run_id, {
                "goal": "change the service safely", "guided_delivery": {"mode": "guided-delivery"},
                "navigator": {"requirement_matrix": [{
                    "display_id": "REQ-01", "statement": "Change safely", "kind": "change",
                    "acceptance_criteria": [], "preserve_rules": [], "likely_paths": ["src/service.py"], "evidence_plan": [],
                }]},
            })
            LOCK.activate(root, run_id, True)
            ownership.bind(root, run_id, workflow_id)
            capabilities.propose(root, workflow_id, ["code-graph-mapper", "requirement-completion-harness", "evidence-aware-testing", "review"])
            task_scope.initialize(root, workflow_id); storage.initialize(root, workflow_id); compiler.compile(root, workflow_id)
            workflow_state.create(root, run_id, workflow_id); task_scope.acquire(root, workflow_id)
            SESSION.attach(root, run_id)
            stopped = SESSION.stop(root)
            workflow = workflow_state.show(root, workflow_id); reservation = task_scope.lock_show(root)

        self.assertEqual(workflow["workflow_status"], "paused")
        self.assertEqual(reservation["state"], "released")
        self.assertEqual(stopped["attachment"]["temporary_approvals"], "expired")
        self.assertEqual(stopped["attachment"]["reservation_release"], "released")


if __name__ == "__main__":
    unittest.main()
