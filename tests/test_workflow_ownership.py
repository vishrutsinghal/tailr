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


lock = load("workflow_ownership_lock_test", "scripts/planning_lock.py")
ownership = load("workflow_ownership_test", "scripts/workflow_runtime/ownership.py")
from workflow_runtime import capabilities
from workflow_runtime import task_scope


class WorkflowOwnershipTests(unittest.TestCase):
    def _approved_run(self, root: Path, run_id: str, likely_paths: list[str] | None = None) -> None:
        lock.create(root, "add a bounded validation rule", run_id)
        lock.save_start_report(root, run_id, {
            "goal": "add a bounded validation rule",
            "guided_delivery": {"mode": "guided-delivery"},
            "navigator": {"requirement_matrix": [{"display_id": "REQ-01", "statement": "Reject invalid values", "kind": "change", "acceptance_criteria": ["Invalid values are rejected"], "preserve_rules": ["Valid values remain valid"], "likely_paths": likely_paths or ["src/validation.py"], "evidence_plan": ["focused test"]}]},
        })
        lock.activate(root, run_id, True)

    def test_dwr_b_schemas_are_well_formed_and_closed(self) -> None:
        plan_schema = json.loads((ROOT / "schemas" / "workflow-capability-plan.schema.json").read_text(encoding="utf-8"))
        grant_schema = json.loads((ROOT / "schemas" / "workflow-preapproval.schema.json").read_text(encoding="utf-8"))

        self.assertEqual(plan_schema["properties"]["type"]["const"], "tailtrail-workflow-capability-plan")
        self.assertFalse(plan_schema["additionalProperties"])
        self.assertEqual(grant_schema["properties"]["type"]["const"], "tailtrail-workflow-preapproval")
        self.assertFalse(grant_schema["additionalProperties"])

    def test_dwr_c_schemas_are_well_formed_and_closed(self) -> None:
        scope_schema = json.loads((ROOT / "schemas" / "workflow-task-scope.schema.json").read_text(encoding="utf-8"))
        reservation_schema = json.loads((ROOT / "schemas" / "workflow-code-change-reservation.schema.json").read_text(encoding="utf-8"))

        self.assertEqual(scope_schema["properties"]["type"]["const"], "tailtrail-workflow-task-scope")
        self.assertFalse(scope_schema["additionalProperties"])
        self.assertEqual(reservation_schema["properties"]["type"]["const"], "tailtrail-workflow-code-change-reservation")
        self.assertFalse(reservation_schema["additionalProperties"])

    def test_bind_references_existing_canonical_run_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self._approved_run(root, "workflow-bind")
            binding = ownership.bind(root, "workflow-bind", "ttw-workflow-bind")
            result = ownership.validate(root, "ttw-workflow-bind")

        self.assertEqual(binding["tailtrail_run_id"], "workflow-bind")
        self.assertTrue(binding["requirement_matrix_ref"].endswith("#/requirements"))
        self.assertTrue(result["valid"])

    def test_bind_rejects_unapproved_or_anchorless_run(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); lock.create(root, "do not bind early", "workflow-unapproved")
            with self.assertRaisesRegex(ValueError, "approved Planning Lock"):
                ownership.bind(root, "workflow-unapproved", "ttw-unapproved")

    def test_validate_blocks_when_anchor_fingerprint_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self._approved_run(root, "workflow-tamper")
            ownership.bind(root, "workflow-tamper", "ttw-tamper")
            anchor = root / ".tailtrail" / "runs" / "workflow-tamper" / "anchors" / "approved-v1.json"
            payload = lock.read(anchor); payload["approved_fingerprint"] = "sha256:changed"; anchor.write_text(json.dumps(payload), encoding="utf-8")
            result = ownership.validate(root, "ttw-tamper")

        self.assertFalse(result["valid"])
        self.assertIn("fingerprint", " ".join(result["issues"]))

    def test_validate_reports_bound_workspace_inventory_drift_without_blocking(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self._approved_run(root, "workflow-drift")
            ownership.bind(root, "workflow-drift", "ttw-drift-workspace")
            (root / "new-module.py").write_text("VALUE = 1\n", encoding="utf-8")
            result = ownership.validate(root, "ttw-drift-workspace")

        self.assertTrue(result["valid"], result["issues"])
        self.assertTrue(any("rebind" in notice for notice in result["notices"]))
        self.assertEqual(result["inventory_drift"]["added"], ["new-module.py"])

    def test_validate_names_removed_and_modified_files_in_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "src").mkdir()
            (root / "src" / "validation.py").write_text("def valid(value):\n    return True\n", encoding="utf-8")
            (root / "keep.py").write_text("KEEP = 1\n", encoding="utf-8")
            self._approved_run(root, "workflow-drift-names")
            ownership.bind(root, "workflow-drift-names", "ttw-drift-names")
            (root / "src" / "validation.py").unlink()
            (root / "keep.py").write_text("KEEP = 2\n", encoding="utf-8")
            (root / "other.py").write_text("OTHER = 3\n", encoding="utf-8")
            result = ownership.validate(root, "ttw-drift-names")

        self.assertTrue(result["valid"], result["issues"])
        self.assertEqual(result["inventory_drift"]["added"], ["other.py"])
        self.assertEqual(result["inventory_drift"]["removed"], ["src/validation.py"])
        self.assertEqual([row["path"] for row in result["inventory_drift"]["changed"]], ["keep.py"])

    def test_rebind_reports_then_records_acceptance_on_confirmation(self) -> None:
        from unittest import mock
        from workflow_runtime import approvals as workflow_approvals
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self._approved_run(root, "workflow-rebind")
            ownership.bind(root, "workflow-rebind", "ttw-rebind")
            self.assertEqual(ownership.rebind(root, "ttw-rebind")["state"], "in-sync")
            (root / "new-module.py").write_text("VALUE = 1\n", encoding="utf-8")
            pending = ownership.rebind(root, "ttw-rebind")
            self.assertEqual(pending["state"], "rebind-required")
            self.assertEqual([(row["path"], row["change"]) for row in pending["changed"]], [("<project-languages>", "changed"), ("new-module.py", "added")])
            self.assertFalse(ownership.rebind_covers(root, "ttw-rebind"))
            with mock.patch.object(workflow_approvals, "expire_session", return_value={"expired": 0}) as expired:
                rebased = ownership.rebind(root, "ttw-rebind", confirmed=True)
            self.assertEqual(rebased["state"], "rebased")
            self.assertEqual(rebased["rebase_count"], 1)
            expired.assert_called_once_with(root.resolve(), "ttw-rebind", None, "target-identity-changed")
            self.assertTrue(ownership.rebind_covers(root, "ttw-rebind"))
            self.assertEqual(len(ownership.show(root, "ttw-rebind")["rebases"]), 1)
            self.assertTrue(ownership.validate(root, "ttw-rebind")["valid"])
            (root / "another.py").write_text("ANOTHER = 1\n", encoding="utf-8")
            self.assertFalse(ownership.rebind_covers(root, "ttw-rebind"))

    def test_rebind_refuses_a_different_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self._approved_run(root, "workflow-rebind-root")
            ownership.bind(root, "workflow-rebind-root", "ttw-rebind-root")
            saved_lock = root / ".tailtrail" / "runs" / "workflow-rebind-root" / "planning" / "lock-v1.json"
            payload = json.loads(saved_lock.read_text(encoding="utf-8"))
            payload["target_identity"]["root"] = (root / "elsewhere").as_posix()
            saved_lock.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "different workspace"):
                ownership.rebind(root, "ttw-rebind-root")

    def test_rebind_cli_reports_without_recording(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self._approved_run(root, "workflow-rebind-cli")
            ownership.bind(root, "workflow-rebind-cli", "ttw-rebind-cli")
            result = subprocess.run(
                [sys.executable, (ROOT / "scripts" / "workflow-runtime.py").as_posix(),
                 "rebind", "--root", root.as_posix(), "--workflow-id", "ttw-rebind-cli"],
                cwd=ROOT, text=True, capture_output=True, check=False)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)["state"], "in-sync")

    def test_public_cli_binds_and_validates_the_same_workflow_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self._approved_run(root, "workflow-cli")
            bind = subprocess.run(
                [sys.executable, (ROOT / "scripts" / "tailtrail.py").as_posix(), "workflow", "bind", "--root", root.as_posix(), "--run-id", "workflow-cli", "--workflow-id", "ttw-cli-workflow"],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )
            validate = subprocess.run(
                [sys.executable, (ROOT / "scripts" / "tailtrail.py").as_posix(), "workflow", "validate", "--root", root.as_posix(), "--workflow-id", "ttw-cli-workflow"],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )

        self.assertEqual(bind.returncode, 0, bind.stdout + bind.stderr)
        self.assertEqual(json.loads(bind.stdout)["workflow_id"], "ttw-cli-workflow")
        self.assertEqual(validate.returncode, 0, validate.stdout + validate.stderr)
        self.assertTrue(json.loads(validate.stdout)["valid"])

    def test_dwr_b_declares_registered_capabilities_and_scope_bound_preapproval(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self._approved_run(root, "workflow-capabilities")
            ownership.bind(root, "workflow-capabilities", "ttw-capabilities")
            plan = capabilities.propose(root, "ttw-capabilities", ["code-graph-mapper", "requirement-completion-harness"])
            validation = capabilities.validate(root, "ttw-capabilities")
            grant = capabilities.grant_preapproval(root, "ttw-capabilities", [plan["stages"][0]["stage_id"]], "2099-01-01T00:00:00+00:00")
            grant_validation = capabilities.validate_preapproval(root, "ttw-capabilities")

        self.assertTrue(validation["valid"])
        self.assertEqual(plan["canonical_approval"]["type"], "planning-lock")
        self.assertEqual(plan["stages"][0]["execution_authority"], "not-implemented")
        self.assertEqual(grant["action_classes"], ["tailtrail-state"])
        self.assertTrue(grant_validation["valid"])

    def test_dwr_b_rejects_unregistered_capabilities_and_tampered_command_text(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self._approved_run(root, "workflow-capability-tamper")
            ownership.bind(root, "workflow-capability-tamper", "ttw-capability-tamper")
            with self.assertRaisesRegex(ValueError, "unregistered"):
                capabilities.propose(root, "ttw-capability-tamper", ["shell-exec"])
            plan = capabilities.propose(root, "ttw-capability-tamper", ["code-graph-mapper"])
            path = root / plan["artifact"]
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["stages"][0]["command"] = "git reset --hard"
            payload["plan_fingerprint"] = capabilities._json_digest({key: value for key, value in payload.items() if key != "plan_fingerprint"})
            path.write_text(json.dumps(payload), encoding="utf-8")
            result = capabilities.validate(root, "ttw-capability-tamper")

        self.assertFalse(result["valid"])
        self.assertIn("prohibited command text", " ".join(result["issues"]))

    def test_dwr_b_public_cli_never_dispatches_declared_capabilities(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self._approved_run(root, "workflow-capability-cli")
            ownership.bind(root, "workflow-capability-cli", "ttw-capability-cli")
            result = subprocess.run(
                [sys.executable, (ROOT / "scripts" / "tailtrail.py").as_posix(), "workflow", "capabilities", "propose", "--root", root.as_posix(), "--workflow-id", "ttw-capability-cli", "--capability", "code-graph-mapper"],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        output = json.loads(result.stdout)
        self.assertEqual(output["stages"][0]["execution_authority"], "not-implemented")

    def test_dwr_b_bridge_has_no_shell_or_project_execution_path(self) -> None:
        body = (ROOT / "scripts" / "workflow_runtime" / "capabilities.py").read_text(encoding="utf-8")

        self.assertNotIn("subprocess", body)
        self.assertNotIn("run_script(", body)
        self.assertIn("not-implemented", body)

    def test_dwr_c_uses_scoped_freshness_and_preserves_unrelated_work(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root / "src").mkdir()
            owned = root / "src" / "owned.py"; unrelated = root / "src" / "unrelated.py"
            owned.write_text("OWNED = 1\n", encoding="utf-8"); unrelated.write_text("OTHER = 1\n", encoding="utf-8")
            self._approved_run(root, "workflow-scope", ["src/owned.py"])
            ownership.bind(root, "workflow-scope", "ttw-scoped-workflow")
            capabilities.propose(root, "ttw-scoped-workflow", ["code-graph-mapper"])
            scope = task_scope.initialize(root, "ttw-scoped-workflow")
            reservation = task_scope.acquire(root, "ttw-scoped-workflow")
            unrelated.write_text("OTHER = 2\n", encoding="utf-8")
            unaffected = task_scope.freshness(root, "ttw-scoped-workflow")
            owned.write_text("OWNED = 2\n", encoding="utf-8")
            stale = task_scope.freshness(root, "ttw-scoped-workflow")
            diagnosis = task_scope.diagnose(root, "ttw-scoped-workflow")

        self.assertEqual(scope["requirements"][0]["paths"][0]["path"], "src/owned.py")
        self.assertEqual(reservation["state"], "active")
        self.assertTrue(unaffected["fresh"])
        self.assertFalse(stale["fresh"])
        self.assertEqual(diagnosis["status"], "stale")
        self.assertEqual(diagnosis["reservation"]["workflow_id"], "ttw-scoped-workflow")

    def test_dwr_c_allows_only_one_code_changing_reservation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root / "src").mkdir(); (root / "src" / "owned.py").write_text("X = 1\n", encoding="utf-8")
            for run_id, workflow_id in (("workflow-one", "ttw-workflow-one"), ("workflow-two", "ttw-workflow-two")):
                self._approved_run(root, run_id, ["src/owned.py"])
                ownership.bind(root, run_id, workflow_id)
                capabilities.propose(root, workflow_id, ["code-graph-mapper"])
                task_scope.initialize(root, workflow_id)
            task_scope.acquire(root, "ttw-workflow-one")
            with self.assertRaisesRegex(ValueError, "already held"):
                task_scope.acquire(root, "ttw-workflow-two")
            read_only = task_scope.diagnose(root, "ttw-workflow-two")

        self.assertEqual(read_only["status"], "blocked")
        self.assertIn("another workflow", read_only["reason"])

    def test_dwr_c_public_cli_captures_scope_without_executing_work(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root / "src").mkdir(); (root / "src" / "owned.py").write_text("X = 1\n", encoding="utf-8")
            self._approved_run(root, "workflow-scope-cli", ["src/owned.py"])
            ownership.bind(root, "workflow-scope-cli", "ttw-scope-cli")
            capabilities.propose(root, "ttw-scope-cli", ["code-graph-mapper"])
            result = subprocess.run(
                [sys.executable, (ROOT / "scripts" / "tailtrail.py").as_posix(), "workflow", "task", "scope-init", "--root", root.as_posix(), "--workflow-id", "ttw-scope-cli"],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)["state"], "captured")


if __name__ == "__main__":
    unittest.main()
