from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]


def load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


coordinated = load("coordinated_plan_test", "scripts/coordinated-plan.py")
planning_lock = load("coordinated_plan_planning_lock_test", "scripts/planning_lock.py")
write_guardian = load("coordinated_plan_write_guardian_test", "scripts/write_guardian.py")


class CoordinatedPlanTests(unittest.TestCase):
    def _proposal(self, root: Path) -> Path:
        path = root / "coordinated.json"
        path.write_text(json.dumps({
            "plan_id": "phase-4",
            "outcome": "Deliver the complete Phase 4 host projection outcome.",
            "children": [
                {
                    "run_id": "receipt-run",
                    "owner": "schemas/receipt.schema.json",
                    "requirements": ["REQ-RECEIPT"],
                    "depends_on": [],
                },
                {
                    "run_id": "engine-run",
                    "owner": "scripts/engine.py",
                    "requirements": ["REQ-ENGINE"],
                    "depends_on": ["receipt-run"],
                },
            ],
            "shared_proof": [{
                "command": "python3 -m unittest tests.test_host",
                "tiers": ["contract", "behaviour"],
                "asserted_behavior": "Both child outcomes compose into one host projection.",
            }],
            "success_criteria": ["Receipt contract precedes engine execution."],
        }), encoding="utf-8")
        return path

    def _snapshots(self) -> dict[str, dict[str, object]]:
        return {
            "receipt-run": {
                "run_id": "receipt-run",
                "plan_fingerprint": "sha256:receipt",
                "owner": "schemas/receipt.schema.json",
                "revision": 1,
                "pending_revision": None,
            },
            "engine-run": {
                "run_id": "engine-run",
                "plan_fingerprint": "sha256:engine",
                "owner": "scripts/engine.py",
                "revision": 1,
                "pending_revision": None,
            },
        }

    def _create(self, root: Path):
        snapshots = self._snapshots()
        with mock.patch.object(coordinated, "_child_snapshot", side_effect=lambda _root, run: snapshots[run]):
            return coordinated.create(root, self._proposal(root))

    def test_create_binds_exact_children_owners_and_dependency_order(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            result = self._create(root)

            proposal = result["proposal"]
            self.assertEqual(proposal["dependency_order"], ["receipt-run", "engine-run"])
            self.assertEqual(
                [child["plan_fingerprint"] for child in proposal["children"]],
                ["sha256:receipt", "sha256:engine"],
            )
            membership = json.loads((
                root / ".tailtrail" / "runs" / "engine-run" / "planning" / "coordinated-membership-v1.json"
            ).read_text(encoding="utf-8"))
            self.assertEqual(membership["depends_on"], ["receipt-run"])
            self.assertEqual(membership["coordination_fingerprint"], proposal["fingerprint"])

    def test_create_rejects_cycle_before_persisting_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = self._proposal(root)
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["children"][0]["depends_on"] = ["engine-run"]
            path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "contains a cycle"):
                coordinated.create(root, path)
            self.assertFalse((root / ".tailtrail" / "coordinated-plans" / "phase-4").exists())

    def test_create_rejects_declared_owner_that_differs_from_child_plan(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            snapshots = self._snapshots()
            snapshots["engine-run"] = {**snapshots["engine-run"], "owner": "scripts/other.py"}
            with mock.patch.object(coordinated, "_child_snapshot", side_effect=lambda _root, run: snapshots[run]):
                with self.assertRaisesRegex(ValueError, "does not match its canonical plan owner"):
                    coordinated.create(root, self._proposal(root))

    def test_failed_activation_mints_no_receipt_and_remains_write_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._create(root)
            snapshots = self._snapshots()

            def activate(_root, run_id, _approved, **_kwargs):
                if run_id == "engine-run":
                    raise ValueError("engine audit changed")
                return {"state": "execution-ready"}

            with mock.patch.object(coordinated, "_child_snapshot", side_effect=lambda _root, run: snapshots[run]), mock.patch.object(coordinated.PL, "activate", side_effect=activate):
                with self.assertRaisesRegex(ValueError, "every member remains write-blocked"):
                    coordinated.approve(root, "phase-4", True)

            state = json.loads((root / ".tailtrail" / "coordinated-plans" / "phase-4" / "state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["status"], "activation-failed")
            self.assertEqual(state["activated_pending_batch_commit"], ["receipt-run"])
            self.assertFalse((root / ".tailtrail" / "coordinated-plans" / "phase-4" / "batch-approval-v1.json").exists())

    def test_one_approval_commits_exact_batch_then_dependencies_unlock_in_order(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._create(root)
            snapshots = self._snapshots()
            with mock.patch.object(coordinated, "_child_snapshot", side_effect=lambda _root, run: snapshots[run]), mock.patch.object(coordinated.PL, "activate", return_value={"state": "execution-ready"}):
                result = coordinated.approve(root, "phase-4", True)
                self.assertEqual(result["state"]["status"], "activated")
                self.assertTrue(result["approval_receipt"]["approved"])
                self.assertEqual(
                    [child["state"] for child in result["state"]["children"]],
                    ["ready", "blocked"],
                )
                coordinated.checkpoint(root, "phase-4", "receipt-run", "active", None)
                evidence = root / "receipt-evidence.json"
                evidence.write_text(json.dumps({
                    "type": "tailtrail-closure-finalizer",
                    "run_id": "receipt-run",
                    "overall_status": "complete",
                }), encoding="utf-8")
                completed = coordinated.checkpoint(root, "phase-4", "receipt-run", "completed", evidence)

            states = {child["run_id"]: child["state"] for child in completed["state"]["children"]}
            self.assertEqual(states, {"receipt-run": "completed", "engine-run": "ready"})

    def test_one_batch_approval_accepts_an_audit_clean_pending_child_revision(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            snapshots = self._snapshots()
            snapshots["engine-run"] = {
                **snapshots["engine-run"],
                "revision": 2,
                "pending_revision": 2,
                "plan_fingerprint": "sha256:engine-v2",
            }
            with mock.patch.object(coordinated, "_child_snapshot", side_effect=lambda _root, run: snapshots[run]):
                coordinated.create(root, self._proposal(root))
            with mock.patch.object(coordinated, "_child_snapshot", side_effect=lambda _root, run: snapshots[run]), mock.patch.object(coordinated.PL, "activate", return_value={"state": "execution-ready"}) as activate, mock.patch.object(coordinated.REVISION, "approve", return_value={"state": "execution-ready"}) as revision_approve:
                result = coordinated.approve(root, "phase-4", True)

            activate.assert_called_once()
            revision_approve.assert_called_once_with(root.resolve(), "engine-run", 2, True)
            child = next(item for item in result["approval_receipt"]["children"] if item["run_id"] == "engine-run")
            self.assertEqual(child["revision"], 2)
            self.assertEqual(child["plan_fingerprint"], "sha256:engine-v2")

    def test_child_plan_drift_invalidates_batch_approval(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._create(root)
            snapshots = self._snapshots()
            with mock.patch.object(coordinated, "_child_snapshot", side_effect=lambda _root, run: snapshots[run]), mock.patch.object(coordinated.PL, "activate", return_value={"state": "execution-ready"}):
                coordinated.approve(root, "phase-4", True)
            changed = {**snapshots["engine-run"], "plan_fingerprint": "sha256:changed"}
            with mock.patch.object(coordinated, "_child_snapshot", side_effect=lambda _root, run: changed if run == "engine-run" else snapshots[run]):
                status = coordinated.show(root, "phase-4")

            self.assertFalse(status["approval_effective"])
            self.assertEqual(status["ready_children"], [])
            self.assertEqual(status["freshness"]["stale_children"][0]["run_id"], "engine-run")

    def test_completed_checkpoint_rejects_non_closure_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self._create(root)
            snapshots = self._snapshots()
            with mock.patch.object(coordinated, "_child_snapshot", side_effect=lambda _root, run: snapshots[run]), mock.patch.object(coordinated.PL, "activate", return_value={"state": "execution-ready"}):
                coordinated.approve(root, "phase-4", True)
                coordinated.checkpoint(root, "phase-4", "receipt-run", "active", None)
                evidence = root / "arbitrary.json"
                evidence.write_text("{}\n", encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "successful TailTrail closure-finalizer"):
                    coordinated.checkpoint(root, "phase-4", "receipt-run", "completed", evidence)

    def test_host_write_guard_uses_the_same_coordinated_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            membership = root / ".tailtrail" / "runs" / "engine-run" / "planning" / "coordinated-membership-v1.json"
            membership.parent.mkdir(parents=True)
            membership.write_text("{}\n", encoding="utf-8")
            blocked = types.SimpleNamespace(
                _assert_coordinated_execution_allowed=mock.Mock(side_effect=ValueError("dependency-blocked by receipt-run"))
            )
            with mock.patch.object(write_guardian, "_load", return_value=blocked):
                allowed, reason = write_guardian._coordinated_write_check(root, "engine-run")

            self.assertFalse(allowed)
            self.assertIn("dependency-blocked", reason or "")

    def test_planning_write_gate_requires_batch_commit_and_completed_dependencies(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run_id = "engine-run"
            plan_id = "phase-4"
            report = {"navigator": {"requirement_matrix": []}}
            material = {
                "run_id": run_id,
                "revision": 1,
                "report": report,
            }
            child_fingerprint = "sha256:" + hashlib.sha256(
                json.dumps(material, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest()
            coordination_fingerprint = "sha256:coordination"
            membership = root / ".tailtrail" / "runs" / run_id / "planning" / "coordinated-membership-v1.json"
            membership.parent.mkdir(parents=True)
            membership.write_text(json.dumps({
                "plan_id": plan_id,
                "coordination_fingerprint": coordination_fingerprint,
                "child_plan_fingerprint": child_fingerprint,
            }), encoding="utf-8")
            directory = root / ".tailtrail" / "coordinated-plans" / plan_id
            directory.mkdir(parents=True)
            (directory / "proposal.json").write_text(json.dumps({"fingerprint": coordination_fingerprint}), encoding="utf-8")
            state = {
                "status": "activation-failed",
                "coordination_fingerprint": coordination_fingerprint,
                "approval_receipt": None,
                "children": [],
            }
            (directory / "state.json").write_text(json.dumps(state), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "has not completed its atomic batch activation"):
                planning_lock._assert_coordinated_execution_allowed(root, run_id)

            receipt_path = directory / "batch-approval-v1.json"
            receipt_path.write_text(json.dumps({"coordination_fingerprint": coordination_fingerprint}), encoding="utf-8")
            state.update({
                "status": "activated",
                "approval_receipt": receipt_path.relative_to(root).as_posix(),
                "children": [
                    {"run_id": "receipt-run", "state": "active", "depends_on": []},
                    {"run_id": run_id, "state": "blocked", "depends_on": ["receipt-run"]},
                ],
            })
            (directory / "state.json").write_text(json.dumps(state), encoding="utf-8")
            with mock.patch.object(planning_lock, "revision_state", return_value={"active_revision": 1, "pending_revision": None}), mock.patch.object(planning_lock, "canonical_plan_report", return_value=(report, {"kind": "saved-start"})):
                with self.assertRaisesRegex(ValueError, "dependency-blocked"):
                    planning_lock._assert_coordinated_execution_allowed(root, run_id)
                state["children"][0]["state"] = "completed"
                state["children"][1]["state"] = "ready"
                (directory / "state.json").write_text(json.dumps(state), encoding="utf-8")
                allowed = planning_lock._assert_coordinated_execution_allowed(root, run_id)

            self.assertEqual(allowed["status"], "allowed")
            self.assertEqual(allowed["dependencies"], ["receipt-run"])


if __name__ == "__main__":
    unittest.main()
