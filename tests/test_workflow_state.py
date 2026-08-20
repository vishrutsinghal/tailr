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
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


lock = load("workflow_state_lock_test", "scripts/planning-lock.py")
from workflow_runtime import capabilities, state, task_scope


class WorkflowStateTests(unittest.TestCase):
    def _approved_run(self, root: Path, run_id: str, paths: list[str] | None = None) -> None:
        lock.create(root, "add a bounded validation rule", run_id)
        lock.save_start_report(root, run_id, {
            "goal": "add a bounded validation rule",
            "guided_delivery": {"mode": "guided-delivery"},
            "navigator": {"requirement_matrix": [{"display_id": "REQ-01", "statement": "Reject invalid values", "kind": "change", "acceptance_criteria": ["Invalid values are rejected"], "preserve_rules": ["Valid values remain valid"], "likely_paths": paths or ["src/validation.py"], "evidence_plan": ["focused test"]}]},
        })
        lock.activate(root, run_id, True)

    def test_create_and_show_uses_canonical_run_without_execution(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self._approved_run(root, "state-run")
            created = state.create(root, "state-run", "ttw-state-run")
            shown = state.show(root, "ttw-state-run")

        self.assertEqual(created["lifecycle_state"], "active")
        self.assertEqual(shown["tailtrail_run_id"], "state-run")
        self.assertTrue(shown["current_requirement"]["requirement_uid"].startswith("req-"))
        self.assertEqual(shown["current_stage"], "not-executing")
        body = (ROOT / "scripts" / "workflow_runtime" / "state.py").read_text(encoding="utf-8")
        self.assertNotIn("subprocess", body)
        self.assertNotIn("run_script(", body)

    def test_pause_resume_and_illegal_transition_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self._approved_run(root, "state-pause")
            state.create(root, "state-pause", "ttw-state-pause")
            paused = state.pause(root, "ttw-state-pause")
            resumed = state.resume(root, "ttw-state-pause")
            with self.assertRaisesRegex(ValueError, "paused workflow"):
                state.resume(root, "ttw-state-pause")

        self.assertEqual(paused["lifecycle_state"], "paused")
        self.assertEqual(resumed["lifecycle_state"], "active")

    def test_cancel_requires_confirmation_and_releases_only_owned_reservation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root / "src").mkdir(); (root / "src" / "validation.py").write_text("X = 1\n", encoding="utf-8")
            self._approved_run(root, "state-cancel", ["src/validation.py"])
            state.create(root, "state-cancel", "ttw-state-cancel")
            capabilities.propose(root, "ttw-state-cancel", ["code-graph-mapper"])
            task_scope.initialize(root, "ttw-state-cancel"); task_scope.acquire(root, "ttw-state-cancel")
            with self.assertRaisesRegex(ValueError, "--confirmed"):
                state.cancel(root, "ttw-state-cancel", False)
            cancelled = state.cancel(root, "ttw-state-cancel", True)
            lock_after = task_scope.lock_show(root)

        self.assertEqual(cancelled["status"], "cancelled")
        self.assertEqual(cancelled["reservation_release"]["state"], "released")
        self.assertEqual(lock_after["state"], "released")

    def test_doctor_reports_stale_scope_without_repairing_it(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root / "src").mkdir(); owned = root / "src" / "validation.py"; owned.write_text("X = 1\n", encoding="utf-8")
            self._approved_run(root, "state-doctor", ["src/validation.py"])
            state.create(root, "state-doctor", "ttw-state-doctor")
            capabilities.propose(root, "ttw-state-doctor", ["code-graph-mapper"])
            task_scope.initialize(root, "ttw-state-doctor")
            owned.write_text("X = 2\n", encoding="utf-8")
            result = state.doctor(root, "ttw-state-doctor")

        self.assertEqual(result["status"], "blocked")
        self.assertIn("approved scoped path fingerprint changed", " ".join(result["state"]["blocked_or_stale_reasons"]))

    def test_public_cli_state_create_and_replay(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self._approved_run(root, "state-cli")
            create = subprocess.run([sys.executable, (ROOT / "scripts" / "tailtrail.py").as_posix(), "workflow", "state", "create", "--root", root.as_posix(), "--run-id", "state-cli", "--workflow-id", "ttw-state-cli"], cwd=ROOT, text=True, capture_output=True, check=False)
            replay = subprocess.run([sys.executable, (ROOT / "scripts" / "tailtrail.py").as_posix(), "workflow", "state", "replay", "--root", root.as_posix(), "--workflow-id", "ttw-state-cli"], cwd=ROOT, text=True, capture_output=True, check=False)

        self.assertEqual(create.returncode, 0, create.stdout + create.stderr)
        self.assertEqual(json.loads(create.stdout)["lifecycle_state"], "active")
        self.assertEqual(replay.returncode, 0, replay.stdout + replay.stderr)
        self.assertTrue(json.loads(replay.stdout)["valid"])


if __name__ == "__main__":
    unittest.main()
