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


lock = load("workflow_storage_lock_test", "scripts/planning-lock.py")
ownership = load("workflow_storage_ownership_test", "scripts/workflow_runtime/ownership.py")
from workflow_runtime import storage


class WorkflowStorageTests(unittest.TestCase):
    def _bound_workflow(self, root: Path, run_id: str = "storage-run", workflow_id: str = "ttw-storage-run") -> str:
        lock.create(root, "add bounded validation", run_id)
        lock.save_start_report(root, run_id, {
            "goal": "add bounded validation",
            "guided_delivery": {"mode": "guided-delivery"},
            "navigator": {"requirement_matrix": [{"display_id": "REQ-01", "statement": "Reject invalid values", "kind": "change", "acceptance_criteria": ["Invalid values are rejected"], "preserve_rules": ["Valid values remain valid"], "likely_paths": ["src/validation.py"], "evidence_plan": ["focused test"]}]},
        })
        lock.activate(root, run_id, True)
        ownership.bind(root, run_id, workflow_id)
        return workflow_id

    def test_storage_schemas_are_well_formed_and_closed(self) -> None:
        event_schema = json.loads((ROOT / "schemas" / "workflow-storage-event.schema.json").read_text(encoding="utf-8"))
        projection_schema = json.loads((ROOT / "schemas" / "workflow-projection.schema.json").read_text(encoding="utf-8"))

        self.assertEqual(event_schema["properties"]["type"]["const"], "tailtrail-workflow-storage-event")
        self.assertFalse(event_schema["additionalProperties"])
        self.assertEqual(projection_schema["properties"]["type"]["const"], "tailtrail-workflow-projection")
        self.assertFalse(projection_schema["additionalProperties"])

    def test_storage_replays_append_only_journal_to_the_saved_projection(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); workflow_id = self._bound_workflow(root)
            initialized = storage.initialize(root, workflow_id)
            captured = storage.capture(root, workflow_id)
            replay = storage.replay(root, workflow_id)

        self.assertEqual(initialized["event"]["sequence"], 1)
        self.assertEqual(captured["event"]["sequence"], 2)
        self.assertTrue(replay["valid"])
        self.assertEqual(replay["replayed_projection"], replay["last_valid_projection"])
        self.assertIn("ownership", replay["replayed_projection"]["artifact_refs"])

    def test_interrupted_journal_is_blocked_without_losing_last_projection(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); workflow_id = self._bound_workflow(root)
            storage.initialize(root, workflow_id); storage.capture(root, workflow_id)
            before = storage.status(root, workflow_id)["last_valid_projection"]
            with storage.journal_path(root, workflow_id).open("a", encoding="utf-8") as handle:
                handle.write("{incomplete\n")
            replay = storage.replay(root, workflow_id)
            after = storage.status(root, workflow_id)["last_valid_projection"]

        self.assertFalse(replay["valid"])
        self.assertIn("invalid JSON", " ".join(replay["issues"]))
        self.assertEqual(before, after)

    def test_cross_run_and_sequence_tampering_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); workflow_id = self._bound_workflow(root)
            storage.initialize(root, workflow_id)
            path = storage.journal_path(root, workflow_id)
            event = json.loads(path.read_text(encoding="utf-8").strip())
            event["tailtrail_run_id"] = "wrong-run"
            event["sequence"] = 4
            event["event_hash"] = storage._event_hash(event)
            path.write_text(json.dumps(event) + "\n", encoding="utf-8")
            result = storage.validate(root, workflow_id)

        self.assertFalse(result["valid"])
        summary = " ".join(result["issues"])
        self.assertIn("another workflow or run", summary)
        self.assertIn("sequence gap", summary)

    def test_storage_journal_captures_references_and_hashes_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); workflow_id = self._bound_workflow(root)
            storage.initialize(root, workflow_id); storage.capture(root, workflow_id)
            journal = storage.journal_path(root, workflow_id).read_text(encoding="utf-8")

        self.assertIn("artifact_refs", journal)
        self.assertIn("artifact_hashes", journal)
        self.assertNotIn("add bounded validation", journal)
        self.assertNotIn("Reject invalid values", journal)

    def test_public_cli_initializes_and_validates_storage_without_execution(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); workflow_id = self._bound_workflow(root)
            init = subprocess.run(
                [sys.executable, (ROOT / "scripts" / "tailtrail.py").as_posix(), "workflow", "storage", "init", "--root", root.as_posix(), "--workflow-id", workflow_id],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )
            validate = subprocess.run(
                [sys.executable, (ROOT / "scripts" / "tailtrail.py").as_posix(), "workflow", "storage", "validate", "--root", root.as_posix(), "--workflow-id", workflow_id],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )

        self.assertEqual(init.returncode, 0, init.stdout + init.stderr)
        self.assertEqual(json.loads(init.stdout)["projection"]["last_sequence"], 1)
        self.assertEqual(validate.returncode, 0, validate.stdout + validate.stderr)
        self.assertTrue(json.loads(validate.stdout)["valid"])


if __name__ == "__main__":
    unittest.main()
