from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.test_aidlc_official_bridge import compatible_pack


ROOT = Path(__file__).resolve().parents[1]


def load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


lock = load("planning_revision_lock_test", "scripts/planning-lock.py")
revision = load("planning_revision_test", "scripts/planning-revision.py")
ledger = load("planning_revision_ledger_test", "scripts/run-ledger.py")
spec_import = load("planning_revision_spec_import_test", "scripts/spec-kit-import.py")
spec_bridge = load("planning_revision_spec_bridge_test", "scripts/spec-kit-bridge.py")


class PlanningRevisionTests(unittest.TestCase):
    def plan(self, root: Path, run_id: str = "revision") -> None:
        lock.create(root, "add cancellation", run_id)
        lock.save_start_report(root, run_id, {
            "goal": "add cancellation",
            "guided_delivery": {"mode": "guided-delivery", "selected": [{"name": "Requirement Completion Harness", "why": "map requirements"}]},
            "navigator": {
                "likely_impacted_files": [{"path": "src/service.py", "reason": "saved orchestration path"}, {"path": "src/api.py", "reason": "saved contract path"}],
                "requirement_matrix": [
                    {"display_id": "REQ-01", "kind": "change", "statement": "Cancel an eligible order.", "acceptance_criteria": ["eligible cancellation succeeds"], "preserve_rules": ["shipment behavior remains unchanged"], "likely_paths": ["src/service.py", "src/api.py"], "evidence_plan": ["service integration test"]},
                    {"display_id": "REQ-02", "kind": "preserve", "statement": "Preserve shipped-order rejection.", "acceptance_criteria": ["shipped order is rejected"], "preserve_rules": ["do not weaken the existing guard"], "likely_paths": ["src/service.py"], "evidence_plan": ["focused rejection test"]},
                ],
            },
        })

    def test_proposal_preserves_v1_and_requires_exact_revision_approval(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self.plan(root)
            original = lock.start_report_path(root, "revision").read_text(encoding="utf-8")
            proposed = revision.propose(root, "revision", json.dumps([{
                "kind": "scope-remove", "requirement_uid": "REQ-01", "path": "src/api.py", "reason": "User clarified this is internal-only service support.",
            }]), True)
            shown = revision.show(root, "revision", 2)
            with self.assertRaisesRegex(ValueError, "revision v2 is awaiting approval"):
                lock.activate(root, "revision", True)
            activated = revision.approve(root, "revision", 2, True)
            anchor = json.loads((root / activated["anchor"]["artifact"]).read_text(encoding="utf-8"))
            state = lock.revision_state(root, "revision")
            events = ledger.projection(root, "revision")["activity"]
            original_after = (root / ".tailtrail" / "runs" / "revision" / "planning" / "start-report-v1.json").read_text(encoding="utf-8")

        self.assertEqual(proposed["revision"], 2)
        self.assertEqual(shown["delta_summary"]["scope_removed"], ["src/api.py"])
        self.assertEqual(original, original_after)
        self.assertEqual(state["active_revision"], 2)
        self.assertIsNone(state["pending_revision"])
        self.assertNotIn("src/api.py", anchor["requirements"][0]["likely_paths"])
        self.assertEqual(events["planning_revision_proposed"], 1)
        self.assertEqual(events["planning_revision_approved"], 1)

    def test_proof_and_requirement_changes_keep_requirement_uid_continuity(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self.plan(root, "continuity")
            proposed = revision.propose(root, "continuity", json.dumps([
                {"kind": "requirement-update", "requirement_uid": "REQ-01", "statement": "Cancel an eligible order through service support only.", "reason": "Clarified delivery boundary."},
                {"kind": "proof-update", "requirement_uid": "REQ-01", "evidence_plan": ["service integration test", "idempotency proof"], "reason": "Add proof for the clarified path."},
            ]), True)

        row = next(item for item in proposed["requirement_continuity"] if item["display_id"] == "REQ-01")
        self.assertTrue(row["requirement_uid"].startswith("req-"))
        self.assertEqual(row["statement"], "Cancel an eligible order through service support only.")
        self.assertEqual(proposed["delta_summary"]["proof_changed"], [row["requirement_uid"]])

    def test_rejects_unapproved_revision_proposal(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self.plan(root)
            change = json.dumps([{"kind": "scope-remove", "requirement_uid": "REQ-01", "path": "src/api.py", "reason": "internal only"}])
            with self.assertRaisesRegex(ValueError, "approved-proposal"):
                revision.propose(root, "revision", change, False)

    def test_lite_run_can_switch_to_standard_then_gather_requirements_without_activation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); compatible_pack(root); self.plan(root, "standard-switch")
            original = lock.start_report_path(root, "standard-switch").read_text(encoding="utf-8")
            proposed = revision.propose_aidlc_standard(root, "standard-switch", True)
            with self.assertRaisesRegex(ValueError, "revision v2 is awaiting approval"):
                lock.activate(root, "standard-switch", True)
            switched = revision.approve_aidlc_standard(root, "standard-switch", 2, True)
            state = lock.revision_state(root, "standard-switch")
            lock_status = lock.show(root, "standard-switch")["status"]
            report = lock.active_start_report(root, "standard-switch")["report"]
            events = ledger.projection(root, "standard-switch")["activity"]
            original_after = lock.start_report_path(root, "standard-switch").read_text(encoding="utf-8")

        self.assertEqual(proposed["type"], "tailtrail-aidlc-mode-switch")
        self.assertEqual(switched["state"], "official-aidlc-host-generation-required")
        self.assertEqual(lock_status, "awaiting-approval")
        self.assertEqual(state["active_revision"], 2)
        self.assertEqual(report["aidlc_mode"]["mode"], "standard")
        self.assertEqual(report["aidlc_mode"]["state"], "official-host-requirements-pending")
        self.assertIn("aidlc_stage", report["aidlc_requirements"])
        self.assertEqual(original, original_after)
        self.assertEqual(events["planning_aidlc_mode_switch_proposed"], 1)
        self.assertEqual(events["planning_aidlc_mode_switch_approved"], 1)

    def test_standard_switch_rejects_non_lite_or_source_owned_run(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self.plan(root, "not-lite")
            payload = json.loads(lock.start_report_path(root, "not-lite").read_text(encoding="utf-8"))
            payload["report"]["aidlc_mode"] = {"mode": "standard"}
            lock.start_report_path(root, "not-lite").write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "awaiting Lite"):
                revision.propose_aidlc_standard(root, "not-lite", True)

            self.plan(root, "source-owned")
            payload = json.loads(lock.start_report_path(root, "source-owned").read_text(encoding="utf-8"))
            payload["report"]["spec_kit_source"] = {"feature_id": "001-orders"}
            lock.start_report_path(root, "source-owned").write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "source-owned"):
                revision.propose_aidlc_standard(root, "source-owned", True)

    def test_aidlc_bound_change_routes_to_aidlc_requirements_without_local_revision(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self.plan(root, "aidlc-route")
            payload = json.loads(lock.start_report_path(root, "aidlc-route").read_text(encoding="utf-8"))
            payload["report"]["aidlc_requirements"] = {"authority": "aidlc"}
            lock.start_report_path(root, "aidlc-route").write_text(json.dumps(payload), encoding="utf-8")
            result = revision.propose(root, "aidlc-route", json.dumps([{
                "kind": "proof-update", "requirement_uid": "REQ-01", "evidence_plan": ["integration proof"], "reason": "Require caller-path evidence before approval.",
            }]), True)
            route = revision.authority_show(root, "aidlc-route")
            aidlc_artifact = root / result["aidlc_refinement"]["artifact"]
            aidlc_exists = aidlc_artifact.is_file()

        self.assertEqual(result["route"], "aidlc-requirements")
        self.assertEqual(result["aidlc_refinement"]["state"], "aidlc-requirements-gathering")
        self.assertTrue(aidlc_exists)
        self.assertEqual(route["route_id"], "route-001")
        self.assertIn("revision_context", result["aidlc_refinement"])

    def test_intent_bridge_change_creates_source_amendment_route_without_rewrite(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            spec = root / "specs" / "001-orders" / "spec.md"; spec.parent.mkdir(parents=True)
            spec.write_text("FR-001: Amend an order before fulfilment.\n## Acceptance Criteria\n- Valid amendments succeed.\n", encoding="utf-8")
            spec_import.import_feature(root, "001-orders", "planning")
            source = spec_bridge.load(root, "001-orders")
            report = {"goal": "Use Intent Bridge", "guided_delivery": {"mode": "guided-delivery"}, "navigator": {"likely_impacted_files": [{"path": "src/orders.py"}], "requirement_matrix": spec_bridge.requirement_matrix(source, ["src/orders.py"])}, "spec_kit_source": source}
            lock.create(root, report["goal"], "intent-route")
            lock.save_start_report(root, "intent-route", report)
            original = lock.start_report_path(root, "intent-route").read_text(encoding="utf-8")
            result = revision.propose(root, "intent-route", json.dumps([{
                "kind": "requirement-update", "requirement_uid": "FR-001", "statement": "Changed wording", "reason": "Need a stronger source requirement.",
            }]), True)
            after = lock.start_report_path(root, "intent-route").read_text(encoding="utf-8")

        self.assertEqual(result["route"], "intent-bridge-amendment")
        self.assertEqual(result["state"], "source-amendment-required")
        self.assertEqual(original, after)
        self.assertIn("source amendment required", revision.render_authority_route(result))

    def test_hands_free_revision_becomes_the_anchor_requirement_matrix(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            lock.create(root, "hands-free: add cancellation", "hands-free-revision")
            lock.save_start_report(root, "hands-free-revision", {
                "goal": "hands-free: add cancellation",
                "guided_delivery": {"mode": "guided-delivery", "hands_free_program": {"feature_requirements": [{"display_id": "REQ-01", "statement": "Cancel an order."}]}},
                "navigator": {"likely_impacted_files": [{"path": "src/service.py"}], "requirement_matrix": [{"display_id": "REQ-01", "kind": "change", "statement": "Cancel an order.", "acceptance_criteria": ["cancellation works"], "preserve_rules": ["preserve shipment"], "likely_paths": ["src/service.py"], "evidence_plan": ["integration test"]}]},
            })
            revision.propose(root, "hands-free-revision", json.dumps([{
                "kind": "requirement-update", "requirement_uid": "REQ-01", "statement": "Cancel an eligible order only.", "reason": "Clarified eligibility boundary.",
            }]), True)
            activated = revision.approve(root, "hands-free-revision", 2, True)
            anchor = json.loads((root / activated["anchor"]["artifact"]).read_text(encoding="utf-8"))

        self.assertEqual(anchor["requirements"][0]["statement"], "Cancel an eligible order only.")

    def test_public_cli_proposes_and_approves_the_exact_revision(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self.plan(root, "cli-revision")
            changes = json.dumps([{"kind": "scope-remove", "requirement_uid": "REQ-01", "path": "src/api.py", "reason": "Internal service support only."}])
            proposed = subprocess.run([
                sys.executable, (ROOT / "scripts" / "tailtrail.py").as_posix(), "planning", "revise", "--root", root.as_posix(),
                "--run-id", "cli-revision", "--changes", changes, "--approved-proposal",
            ], cwd=ROOT, text=True, capture_output=True, check=False)
            approved = subprocess.run([
                sys.executable, (ROOT / "scripts" / "tailtrail.py").as_posix(), "planning", "revision-approve", "--root", root.as_posix(),
                "--run-id", "cli-revision", "--revision", "2", "--approved",
            ], cwd=ROOT, text=True, capture_output=True, check=False)

        self.assertEqual(proposed.returncode, 0, proposed.stderr + proposed.stdout)
        self.assertIn("# TailTrail Plan Revision", proposed.stdout)
        self.assertEqual(approved.returncode, 0, approved.stderr + approved.stdout)
        self.assertIn("# TailTrail Execution Handoff", approved.stdout)

    def test_public_cli_switches_lite_to_standard_without_activating_execution(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); compatible_pack(root); self.plan(root, "cli-standard")
            proposed = subprocess.run([
                sys.executable, (ROOT / "scripts" / "tailtrail.py").as_posix(), "planning", "aidlc-standard", "--root", root.as_posix(),
                "--run-id", "cli-standard", "--approved-proposal",
            ], cwd=ROOT, text=True, capture_output=True, check=False)
            approved = subprocess.run([
                sys.executable, (ROOT / "scripts" / "tailtrail.py").as_posix(), "planning", "aidlc-standard-approve", "--root", root.as_posix(),
                "--run-id", "cli-standard", "--revision", "2", "--approved",
            ], cwd=ROOT, text=True, capture_output=True, check=False)

        self.assertEqual(proposed.returncode, 0, proposed.stderr + proposed.stdout)
        self.assertIn("# TailTrail AIDLC Mode Switch", proposed.stdout)
        self.assertEqual(approved.returncode, 0, approved.stderr + approved.stdout)
        self.assertIn("# TailTrail Official AI-DLC Requirements", approved.stdout)


if __name__ == "__main__":
    unittest.main()
