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


lock = load("workflow_approval_lock_test", "scripts/planning-lock.py")
from workflow_runtime import approvals, compiler, start_integration, state, task_scope


class WorkflowApprovalTests(unittest.TestCase):
    def _activated(self, root: Path, run_id: str) -> tuple[str, dict[str, object]]:
        lock.create(root, "deliver one controlled change", run_id)
        report = {
            "goal": "deliver one controlled change",
            "guided_delivery": {"mode": "guided-delivery"},
            "navigator": {
                "registry_workflow": {"feature_ids": ["canonical-local-state", "code-graph-mapper", "requirement-completion-harness", "evidence-aware-testing", "review"]},
                "requirement_matrix": [{"display_id": "REQ-01", "statement": "Deliver the approved behavior", "kind": "change", "acceptance_criteria": ["Behavior is proven"], "preserve_rules": ["Existing behavior remains"], "likely_paths": ["src/service.py"], "evidence_plan": ["focused test"]}],
            },
        }
        report["workflow_runtime"] = start_integration.draft(report, run_id)
        lock.save_start_report(root, run_id, report)
        activated = lock.activate(root, run_id, True); runtime = activated["workflow_runtime"]
        return str(runtime["workflow_id"]), runtime

    def test_initial_approval_is_bound_but_cannot_start_a_guarded_stage(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); workflow_id, runtime = self._activated(root, "approval-bind")
            initial = runtime["initial_plan_approval"]
            state.transition_stage(root, workflow_id, "bootstrap", "ready", "stage-ready")
            with self.assertRaisesRegex(ValueError, "initial Planning Lock approval cannot substitute"):
                state.transition_stage(root, workflow_id, "bootstrap", "running", "approval-granted", initial["approval_id"])
            stage = approvals.decide(root, workflow_id, stage_ids=["bootstrap"], action_classes=["read_local"], operation_kind="other-guarded", operation_ref=runtime["compiler"]["artifact"], decision="approved", rationale="Approve only the typed bootstrap read stage.")
            running = state.transition_stage(root, workflow_id, "bootstrap", "running", "approval-granted", stage["record"]["approval_id"])

        self.assertEqual(running["stage_states"]["bootstrap"]["status"], "running")
        self.assertEqual(initial["tailtrail_run_id"], "approval-bind")
        self.assertTrue(initial["scope_ref"].endswith("/anchors/approved-v1.json"))
        self.assertTrue(initial["stage_graph_fingerprint"].startswith("sha256:"))

    def test_rejected_edited_expired_and_forged_approvals_never_authorize(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); workflow_id, runtime = self._activated(root, "approval-negative")
            state.transition_stage(root, workflow_id, "bootstrap", "ready", "stage-ready")
            values = dict(stage_ids=["bootstrap"], action_classes=["read_local"], operation_kind="other-guarded", operation_ref=runtime["compiler"]["artifact"], rationale="Bounded decision for a negative-path test.")
            rejected = approvals.decide(root, workflow_id, decision="rejected", **values)["record"]
            edited = approvals.decide(root, workflow_id, decision="edited", **values)["record"]
            for record in (rejected, edited):
                with self.assertRaisesRegex(ValueError, "approval decision"):
                    state.transition_stage(root, workflow_id, "bootstrap", "running", "approval-granted", record["approval_id"])
            session = approvals.grant_session(root, workflow_id, ["write_tailtrail_state"], True, "host-1")["record"]
            approvals.expire_session(root, workflow_id, "host-1", "host-session-ended")
            with self.assertRaisesRegex(ValueError, "expired"):
                state.transition_stage(root, workflow_id, "bootstrap", "running", "approval-granted", session["approval_id"])
            ledger_path = approvals.path(root, workflow_id); payload = json.loads(ledger_path.read_text(encoding="utf-8")); payload["approvals"][0]["approval_id"] = "wfauth-" + "0" * 24; ledger_path.write_text(json.dumps(payload), encoding="utf-8")
            validation = approvals.validate(root, workflow_id)

        self.assertFalse(validation["valid"])
        self.assertIn("forged", " ".join(validation["issues"]))

    def test_session_and_policy_sources_are_low_risk_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); workflow_id, _runtime = self._activated(root, "approval-low-risk")
            with self.assertRaisesRegex(ValueError, "only read_local/write_tailtrail_state"):
                approvals.grant_session(root, workflow_id, ["execute_project"], True)
            with self.assertRaisesRegex(ValueError, "requires action class"):
                approvals.decide(root, workflow_id, stage_ids=["focused-test"], action_classes=["write_tailtrail_state"], operation_kind="broad-test-build", operation_ref=compiler.show(root, workflow_id)["artifact"], decision="approved", rationale="Wrong class must fail.")
            session = approvals.grant_session(root, workflow_id, ["write_tailtrail_state"], True, "scope-session")["record"]
            task_scope.initialize(root, workflow_id)
            after_scope = approvals.show(root, workflow_id)

        self.assertTrue(next(row for row in after_scope["effective_status"] if row["approval_id"] == session["approval_id"])["effective"])

    def test_dependency_decision_remains_separate_and_cli_consumes_exact_stage_approval(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); workflow_id, runtime = self._activated(root, "approval-cli")
            dependency_ref = "tailtrail-meta/dependency-decisions/DD-001.json"; dependency_path = root / dependency_ref; dependency_path.parent.mkdir(parents=True)
            dependency_path.write_text(json.dumps({"schema_version": "1", "type": "tailtrail-dependency-decision", "decision_id": "DD-001", "status": "approved", "package": "example", "version": "1.0", "manifest_paths": ["requirements.txt"], "problem": "bounded gap", "alternatives": ["standard library"], "rationale": "approved separately", "owner": "team", "validation": ["focused check"], "rollback": "remove dependency"}), encoding="utf-8")
            dependency = approvals.decide(root, workflow_id, stage_ids=["implement"], action_classes=["write_tailtrail_state"], operation_kind="dependency", operation_ref=runtime["compiler"]["artifact"], decision="approved", rationale="Runtime stage may consume the separate Dependency Gate decision.", policy_ref=dependency_ref)
            ready = subprocess.run([sys.executable, (ROOT / "scripts" / "tailtrail.py").as_posix(), "workflow", "state", "stage", "--root", root.as_posix(), "--workflow-id", workflow_id, "--stage-id", "bootstrap", "--to", "ready", "--reason-code", "stage-ready"], cwd=ROOT, text=True, capture_output=True, check=False)
            decide = subprocess.run([sys.executable, (ROOT / "scripts" / "tailtrail.py").as_posix(), "workflow", "approvals", "decide", "--root", root.as_posix(), "--workflow-id", workflow_id, "--stage-id", "bootstrap", "--action-class", "read_local", "--operation-kind", "other-guarded", "--operation-ref", runtime["compiler"]["artifact"], "--decision", "approved", "--rationale", "Approve only the typed bootstrap read."], cwd=ROOT, text=True, capture_output=True, check=False)
            approval_id = json.loads(decide.stdout)["record"]["approval_id"] if decide.returncode == 0 else "missing"
            running = subprocess.run([sys.executable, (ROOT / "scripts" / "tailtrail.py").as_posix(), "workflow", "state", "stage", "--root", root.as_posix(), "--workflow-id", workflow_id, "--stage-id", "bootstrap", "--to", "running", "--reason-code", "approval-granted", "--approval-id", approval_id], cwd=ROOT, text=True, capture_output=True, check=False)

        self.assertEqual(dependency["record"]["policy_ref"], dependency_ref)
        self.assertEqual(ready.returncode, 0, ready.stdout + ready.stderr)
        self.assertEqual(decide.returncode, 0, decide.stdout + decide.stderr)
        self.assertEqual(running.returncode, 0, running.stdout + running.stderr)

    def test_explicit_skip_requires_category_and_exact_approval(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); workflow_id, runtime = self._activated(root, "approval-skip")
            with self.assertRaisesRegex(ValueError, "categorical"):
                approvals.decide(root, workflow_id, stage_ids=["bootstrap"], action_classes=["read_local", "write_tailtrail_state"], operation_kind="skip", operation_ref=runtime["compiler"]["artifact"], decision="approved", rationale="No reason is not enough.")
            skip = approvals.decide(root, workflow_id, stage_ids=["bootstrap"], action_classes=["read_local", "write_tailtrail_state"], operation_kind="skip", operation_ref=runtime["compiler"]["artifact"], decision="approved", rationale="Bootstrap proof is supplied by the approved canonical binding.", skip_reason_code="duplicate-proof")
            skipped = state.transition_stage(root, workflow_id, "bootstrap", "skipped", "stage-skipped-approved", skip["record"]["approval_id"])

        self.assertEqual(skipped["stage_states"]["bootstrap"]["status"], "skipped")

    def test_pause_and_material_revision_expire_session_authority_but_metadata_does_not(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); workflow_id, _runtime = self._activated(root, "approval-expiry")
            first = approvals.grant_session(root, workflow_id, ["write_tailtrail_state"], True, "host-pause")["record"]
            manifest = root / ".tailtrail" / "runs" / "approval-expiry" / "manifest.json"
            data = json.loads(manifest.read_text(encoding="utf-8")); data["goal"] = "cosmetic description edit"; manifest.write_text(json.dumps(data), encoding="utf-8")
            unchanged = compiler.compile(root, workflow_id)
            before_pause = approvals.show(root, workflow_id)
            state.pause(root, workflow_id); after_pause = approvals.show(root, workflow_id)
            state.resume(root, workflow_id)
            second = approvals.grant_session(root, workflow_id, ["write_tailtrail_state"], True, "host-revision")["record"]
            policy = {"schema_version": "1", "type": "tailtrail-workflow-compiler-policy", "required_capabilities": [], "forbidden_capabilities": [], "stage_prerequisites": {}, "pre_approved_stages": ["bootstrap"]}
            compiler.policy_path(root).write_text(json.dumps(policy), encoding="utf-8")
            revised = compiler.compile(root, workflow_id); after_revision = approvals.show(root, workflow_id)

        self.assertEqual(unchanged["status"], "unchanged")
        self.assertTrue(next(row for row in before_pause["effective_status"] if row["approval_id"] == first["approval_id"])["effective"])
        self.assertFalse(next(row for row in after_pause["effective_status"] if row["approval_id"] == first["approval_id"])["effective"])
        self.assertGreater(revised["revision"], unchanged["revision"])
        self.assertFalse(next(row for row in after_revision["effective_status"] if row["approval_id"] == second["approval_id"])["effective"])

    def test_cross_run_reuse_and_policy_guardrail_drift_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); first_id, first_runtime = self._activated(root, "approval-first")
            approved = approvals.decide(root, first_id, stage_ids=["bootstrap"], action_classes=["read_local"], operation_kind="other-guarded", operation_ref=first_runtime["compiler"]["artifact"], decision="approved", rationale="First run only.")["record"]
            second_id, _second_runtime = self._activated(root, "approval-second")
            second_path = approvals.path(root, second_id); second = json.loads(second_path.read_text(encoding="utf-8")); second["approvals"].append(approved); second_path.write_text(json.dumps(second), encoding="utf-8")
            cross = approvals.validate(root, second_id)
            root.joinpath("GUARDRAILS.md").write_text("# Guardrail\nRequire a new guarded review.\n", encoding="utf-8")
            drift = approvals.show(root, first_id)

        self.assertFalse(cross["valid"])
        self.assertIn("cross-run", " ".join(cross["issues"]))
        self.assertFalse(next(row for row in drift["effective_status"] if row["approval_id"] == approved["approval_id"])["effective"])


if __name__ == "__main__":
    unittest.main()
