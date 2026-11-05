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


lock = load("planning_revision_lock_test", "scripts/planning_lock.py")
revision = load("planning_revision_test", "scripts/planning-revision.py")
ledger = load("planning_revision_ledger_test", "scripts/run-ledger.py")
spec_import = load("planning_revision_spec_import_test", "scripts/spec-kit-import.py")
spec_bridge = load("planning_revision_spec_bridge_test", "scripts/spec-kit-bridge.py")


class PlanningRevisionTests(unittest.TestCase):
    def test_output_revision_is_separate_from_implementation_ownership(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.plan(root, "output-revision")
            proposed = revision.propose(root, "output-revision", json.dumps([{
                "kind": "output-add", "requirement_uid": "REQ-01",
                "path": "generated/provenance.json", "role": "generated-output",
                "existing": False, "new_file_verdict": "new-confirmed",
                "source_answer_ids": ["answer-output"],
                "evidence_fingerprint": "sha256:" + "1" * 64,
                "reason": "Record the approved generated artifact without owner promotion.",
            }]), True)
            row = proposed["proposed_report"]["navigator"]["requirement_matrix"][0]

        self.assertNotIn("generated/provenance.json", row["likely_paths"])
        self.assertEqual(row["writable_outputs"][0]["role"], "generated-output")

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

    def v2_plan(self, root: Path, run_id: str) -> dict[str, object]:
        owner = root / "src" / "owner.py"; owner.parent.mkdir(parents=True, exist_ok=True); owner.write_text("def owner():\n    return True\n", encoding="utf-8")
        helper = root / "src" / "helper.py"; helper.write_text("def helper():\n    return True\n", encoding="utf-8")
        proof = root / "tests" / "test_owner.py"; proof.parent.mkdir(parents=True, exist_ok=True); proof.write_text(
            "import unittest\nfrom src.owner import owner\n\n"
            "class OwnerTests(unittest.TestCase):\n"
            "    def test_owner(self):\n"
            "        self.assertTrue(owner())\n",
            encoding="utf-8",
        )
        started = subprocess.run([
            sys.executable, (ROOT / "scripts" / "task-start.py").as_posix(),
            "fix owner behavior", "--root", root.as_posix(), "--changed", "src/owner.py",
            "--planning-run-id", run_id, "--format", "json",
        ], cwd=ROOT, text=True, capture_output=True, check=False)
        self.assertEqual(started.returncode, 0, started.stdout + started.stderr)
        return json.loads(started.stdout)

    def test_v2_revision_cannot_promote_proof_only_test_silently(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self.v2_plan(root, "v2-proof-role")
            change = json.dumps([{
                "kind": "scope-add", "requirement_uid": "REQ-01", "path": "tests/test_owner.py",
                "reason": "Treat the proof as implementation scope.",
            }])
            with self.assertRaisesRegex(ValueError, "proof-only test evidence"):
                revision.propose(root, "v2-proof-role", change, True)

        self.assertFalse((root / ".tailtrail" / "runs" / "v2-proof-role" / "planning" / "revisions" / "revision-v2.json").exists())

    def test_proof_path_add_joins_validation_contract_editable_paths(self) -> None:
        """Issue 25 regression: a proof-only test file has a revision path
        into the exact fields harness-checkpoint.py's drift check reads
        (`validation_contract.editable_paths`/`proposed_paths`), distinct
        from `scope_evidence.proof_paths`."""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self.v2_plan(root, "v2-proof-path-add")
            change = json.dumps([{
                "kind": "proof-update", "requirement_uid": "REQ-01",
                "reason": "Bind the new proof-only test file as editable proof scope.",
                "evidence_plan": ["Run the new test module"],
                "commands": ["python3 -m unittest discover -s tests -p test_owner.py -v"],
                "tiers": ["unit"],
                "editable_paths": ["tests/test_owner.py"],
            }])
            proposed = revision.propose(root, "v2-proof-path-add", change, True)
            activated = revision.approve(root, "v2-proof-path-add", 2, True)
            anchor = json.loads((root / activated["anchor"]["artifact"]).read_text(encoding="utf-8"))

        self.assertEqual(proposed["revision"], 2)
        contract = anchor["requirements"][0]["validation_contract"]
        self.assertEqual(contract["editable_paths"], ["tests/test_owner.py"])

    def test_proof_boundary_expand_does_not_fall_through_to_requirement_add(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.plan(root, "boundary-expand-branch")
            report_path = lock.start_report_path(root, "boundary-expand-branch")
            saved = json.loads(report_path.read_text(encoding="utf-8"))
            saved["report"]["navigator"]["host_proof_boundary"] = {
                "behavior_surface": "workflow",
                "allowed_tiers": ["unit"],
            }
            saved["report"]["navigator"]["host_proof_boundary_conflict"] = {
                "state": "inferred-tier-conflicts-host-proof-boundary",
                "allowed_tiers": ["unit"],
                "conflicts": [{"requirement_id": "REQ-01", "inferred_tiers": ["integration"]}],
            }
            report_path.write_text(json.dumps(saved), encoding="utf-8")
            proposed = revision.propose(root, "boundary-expand-branch", json.dumps([{
                "kind": "proof-boundary-expand",
                "reason": "Authorize the required integration proof.",
                "allowed_tiers": ["unit", "integration"],
                "rationale": "The public revision-to-audit route is integration proof.",
            }]), True)

        expansion = proposed["proposed_report"]["proof_boundary_expansion"]
        self.assertEqual(expansion["new_allowed_tiers"], ["unit", "integration"])
        self.assertTrue(expansion["audit_required"])
        navigator = proposed["proposed_report"]["navigator"]
        self.assertEqual(navigator["host_proof_boundary"]["allowed_tiers"], ["unit", "integration"])
        self.assertNotIn("host_proof_boundary_conflict", navigator)

    def test_proof_rebuild_preserves_registry_backed_command_and_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.plan(root, "registry-proof-rebuild")
            proposed = revision.propose(root, "registry-proof-rebuild", json.dumps([{
                "kind": "proof-update",
                "requirement_uid": "REQ-01",
                "reason": "Bind the focused revision regression.",
                "evidence_plan": ["Run the planning revision regression."],
                "commands": ["python3 -m unittest tests.test_planning_revision -v"],
                "tiers": ["unit"],
                "editable_paths": ["tests/test_planning_revision.py"],
            }]), True)

        report = proposed["proposed_report"]
        contract = report["navigator"]["requirement_matrix"][0]["validation_contract"]
        check = contract["checks"][0]
        command_id = check["command_id"]
        self.assertEqual(contract["command_registry"][command_id]["command"], "python3 -m unittest tests.test_planning_revision -v")
        self.assertEqual(check["candidate_paths"], ["tests/test_planning_revision.py"])
        self.assertEqual(report["focused_validation"][0]["command_id"], command_id)

    def test_superseding_revision_deduplicates_command_id_and_literal_proof(self) -> None:
        """Repeating an existing proof must not render it twice in v3."""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.plan(root, "dedupe-proof-binding")
            proof = root / "tests" / "test_planning_revision.py"
            proof.parent.mkdir(parents=True, exist_ok=True)
            proof.write_text("# proof fixture\n", encoding="utf-8")
            command = "python3 -m unittest tests.test_planning_revision -q"
            first = revision.propose(root, "dedupe-proof-binding", json.dumps([{
                "kind": "proof-update",
                "requirement_uid": "REQ-01",
                "reason": "Register the approved proof binding.",
                "evidence_plan": ["Run the focused proof."],
                "checks": [{"command": command, "tiers": ["unit", "contract", "behaviour"]}],
                "editable_paths": ["tests/test_planning_revision.py"],
            }]), True)
            second = revision.propose(root, "dedupe-proof-binding", json.dumps([
                {
                    "kind": "proof-update",
                    "requirement_uid": "REQ-01",
                    "reason": "Retain the same proof while revising the scenario.",
                    "evidence_plan": ["Run the focused proof."],
                    "checks": [{"command": command, "tiers": ["behaviour", "contract", "unit"]}],
                    "editable_paths": ["tests/test_planning_revision.py"],
                },
                {
                    "kind": "behaviour-scenario-add",
                    "requirement_uid": "REQ-01",
                    "reason": "Make the observable cancellation outcome explicit.",
                    "scenario": {
                        "scenario_id": "BHV-REQ-01",
                        "action": "Cancel an eligible order",
                        "expected_outcome": "The cancellation is observable through the public route",
                    },
                },
            ]), True, supersede_pending=True)

        self.assertEqual(first["revision"], 2)
        self.assertEqual(second["revision"], 3)
        row = second["proposed_report"]["navigator"]["requirement_matrix"][0]
        self.assertEqual(len(row["validation_contract"]["checks"]), 1)
        self.assertEqual(
            row["validation_contract"]["checks"][0]["tiers"],
            ["behaviour", "contract", "unit"],
        )
        focused = [
            item for item in second["proposed_report"]["focused_validation"]
            if item["requirement_id"] == "REQ-01"
        ]
        self.assertEqual(len(focused), 1)
        self.assertEqual(focused[0]["tiers"], ["behaviour", "contract", "unit"])

    def test_superseding_lossy_revision_recovers_exact_proof_bindings_from_active_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.plan(root, "recover-exact-proof")
            report_path = lock.start_report_path(root, "recover-exact-proof")
            saved = json.loads(report_path.read_text(encoding="utf-8"))
            row = saved["report"]["navigator"]["requirement_matrix"][0]
            command = "python3 -m unittest tests.test_planning_revision"
            evidence = "sha256:" + "a" * 64
            adequacy = {
                "schema_version": "1",
                "path": "tests/test_planning_revision.py",
                "role": "editable-proof",
                "test_cases": ["planning revision proof projection"],
                "fixtures": ["saved active Start report"],
                "assertions": ["every exact tier binding preserves proof adequacy"],
                "baseline": {
                    "command": command,
                    "outcome": "not-run",
                    "observed": "Planning-only intake identified missing revision coverage.",
                },
            }
            row["validation_contract"] = {
                "state": "required",
                "commands": [command],
                "tiers": ["unit", "contract"],
                "candidate_paths": ["tests/test_planning_revision.py"],
                "editable_paths": ["tests/test_planning_revision.py"],
                "proof_adequacy_required": True,
                "checks": [
                    {
                        "command": command,
                        "candidate_paths": ["tests/test_planning_revision.py"],
                        "tiers": ["unit"],
                        "asserted_behavior": "Unit behavior remains exact.",
                        "source_answer_id": "answer-proof",
                        "evidence_fingerprint": evidence,
                        "proof_adequacy": adequacy,
                    },
                    {
                        "command": command,
                        "candidate_paths": ["tests/test_planning_revision.py"],
                        "tiers": ["contract"],
                        "asserted_behavior": "Contract behavior remains exact.",
                        "source_answer_id": "answer-proof",
                        "evidence_fingerprint": evidence,
                        "proof_adequacy": adequacy,
                    },
                ],
            }
            report_path.write_text(json.dumps(saved), encoding="utf-8")
            first = revision.propose(root, "recover-exact-proof", json.dumps([{
                "kind": "proof-update",
                "requirement_uid": "REQ-01",
                "reason": "Build the canonical proof projection.",
                "evidence_plan": ["Run the focused proof."],
            }]), True)
            first_check = first["proposed_report"]["navigator"]["requirement_matrix"][0]["validation_contract"]["checks"][0]
            self.assertEqual(len(first_check["exact_bindings"]), 2)
            self.assertTrue(all(
                binding.get("proof_adequacy") == adequacy
                for binding in first_check["exact_bindings"]
            ))
            pending_path = root / first["artifact"]
            pending = json.loads(pending_path.read_text(encoding="utf-8"))
            pending_check = pending["proposed_report"]["navigator"]["requirement_matrix"][0]["validation_contract"]["checks"][0]
            pending_check.pop("exact_bindings", None)
            pending_path.write_text(json.dumps(pending), encoding="utf-8")

            second = revision.propose(root, "recover-exact-proof", json.dumps([{
                "kind": "proof-update",
                "requirement_uid": "REQ-01",
                "reason": "Recover exact proof identity while rebuilding.",
                "evidence_plan": ["Run the focused proof."],
            }]), True, supersede_pending=True)

        check = second["proposed_report"]["navigator"]["requirement_matrix"][0]["validation_contract"]["checks"][0]
        self.assertEqual(len(check["exact_bindings"]), 2)
        self.assertEqual(
            {binding["asserted_behavior"] for binding in check["exact_bindings"]},
            {"Unit behavior remains exact.", "Contract behavior remains exact."},
        )
        self.assertTrue(all(
            binding.get("proof_adequacy") == adequacy
            for binding in check["exact_bindings"]
        ))
        self.assertNotIn(
            "planning_revision_proof_binding_recovery",
            second["proposed_report"],
        )

    def test_supersede_replaces_pending_from_active_plan_without_leaking_unapproved_delta(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.plan(root, "replace-pending-from-active")
            first = revision.propose(root, "replace-pending-from-active", json.dumps([
                {
                    "kind": "proof-boundary-expand",
                    "reason": "Propose behavior proof for the first draft.",
                    "allowed_tiers": ["unit", "behaviour"],
                    "rationale": "The first draft proposed an observable scenario.",
                },
                {
                    "kind": "behaviour-scenario-add",
                    "requirement_uid": "REQ-01",
                    "reason": "Add the first draft behavior scenario.",
                    "scenario": {
                        "scenario_id": "BHV-UNAPPROVED-DRAFT",
                        "action": "Exercise the first draft",
                        "expected_outcome": "The first draft is observable",
                    },
                },
            ]), True)
            second = revision.propose(root, "replace-pending-from-active", json.dumps([{
                "kind": "requirement-update",
                "requirement_uid": "REQ-01",
                "statement": "Cancel an eligible order through the bounded service path.",
                "reason": "Replace the unapproved draft with a bounded requirement.",
            }]), True, supersede_pending=True)
            superseded = revision.show(root, "replace-pending-from-active", int(first["revision"]))

        report = second["proposed_report"]
        row = report["navigator"]["requirement_matrix"][0]
        self.assertNotIn("proof_boundary_expansion", report)
        self.assertNotIn("behaviour", row.get("validation_contract", {}).get("tiers", []))
        self.assertFalse(any(
            scenario.get("scenario_id") == "BHV-UNAPPROVED-DRAFT"
            for scenario in report.get("behaviour_plan", {}).get("scenarios", [])
            if isinstance(scenario, dict)
        ))
        self.assertEqual(second["supersedes_revision"], first["revision"])
        self.assertEqual(superseded["state"], "superseded")

    def test_behaviour_scenario_revision_adds_concrete_source_bound_scenario(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.plan(root, "scenario-revision")
            change = json.dumps([{
                "kind": "behaviour-scenario-add",
                "requirement_uid": "REQ-01",
                "reason": "Add the user-observable packet finalization scenario.",
                "scenario": {
                    "scenario_id": "BHV-REQ-01",
                    "action": "Finalize accepted answers into an operational packet",
                    "expected_outcome": "Every packet binding contains a source answer ID",
                },
            }])
            proposed = revision.propose(root, "scenario-revision", change, True)
            report = proposed["proposed_report"]
            row = next(item for item in report["navigator"]["requirement_matrix"] if item["display_id"] == "REQ-01")

        scenario = report["behaviour_plan"]["scenarios"][-1]
        self.assertEqual(scenario["scenario_id"], "BHV-REQ-01")
        self.assertEqual(scenario["requirement_ids"], ["REQ-01"])
        self.assertTrue(row["behavior_contract"]["scenarios"])
        self.assertIn("behaviour", row["validation_contract"]["tiers"])

    def test_requirement_update_rebuilds_explicit_narrowed_proof_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.plan(root, "narrow-proof-revision")
            change = json.dumps([{
                "kind": "requirement-update",
                "requirement_uid": "REQ-01",
                "statement": "Wire the orchestrator through the intake dependency.",
                "reason": "Narrow the change to internal wiring and focused unit proof.",
                "validation_contract": {
                    "state": "required",
                    "tiers": ["unit"],
                    "commands": ["python3 -m unittest discover -s tests -p test_question_orchestrator.py -v"],
                    "candidate_paths": ["tests/test_question_orchestrator.py"],
                },
                "behavior_contract": {"scenarios": []},
            }])
            proposed = revision.propose(root, "narrow-proof-revision", change, True)
            report = proposed["proposed_report"]
            row = next(item for item in report["navigator"]["requirement_matrix"] if item["display_id"] == "REQ-01")

        self.assertEqual(row["validation_contract"]["tiers"], ["unit"])
        self.assertEqual(row["validation_contract"]["commands"], ["python3 -m unittest discover -s tests -p test_question_orchestrator.py -v"])
        self.assertEqual(report["focused_validation"][0]["tier"], "unit")

    def test_requirement_update_can_correct_kind_before_approval(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run_id = "kind-correction"
            statement = "Extend the resolver while preserving idempotence."
            lock.create(root, statement, run_id)
            lock.save_start_report(root, run_id, {
                "goal": statement,
                "guided_delivery": {"mode": "guided-delivery"},
                "navigator": {"requirement_matrix": [{
                    "display_id": "REQ-01", "kind": "preserve", "statement": statement,
                    "acceptance_criteria": ["projection works"],
                    "preserve_rules": ["idempotence remains"],
                    "likely_paths": ["src/resolver.py"], "evidence_plan": ["focused proof"],
                }]},
            })
            base_change = {
                "kind": "requirement-update", "requirement_uid": "REQ-01",
                "statement": statement, "reason": "Correct the requirement authority before approval.",
            }
            with self.assertRaisesRegex(ValueError, "supply explicit `requirement_kind`"):
                revision.propose(root, run_id, json.dumps([base_change]), True)
            proposed = revision.propose(root, run_id, json.dumps([{
                **base_change, "requirement_kind": "change",
            }]), True)

        row = proposed["proposed_report"]["navigator"]["requirement_matrix"][0]
        self.assertEqual(row["kind"], "change")
        normalized = proposed["changes"][0]
        self.assertEqual(normalized["requirement_kind_before"], "preserve")
        self.assertEqual(normalized["requirement_kind"], "change")

    def test_proof_path_add_rejects_implementation_owner_role_paths(self) -> None:
        """Symmetric guard: validation_contract.editable_paths/proposed_paths
        grant proof-assertion editability only, never implementation scope —
        the same way scope-add already rejects test-role paths."""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self.v2_plan(root, "v2-proof-path-reject")
            change = json.dumps([{
                "kind": "proof-update", "requirement_uid": "REQ-01",
                "reason": "Attempt to smuggle implementation scope through a proof field.",
                "evidence_plan": ["Attempted proof-path smuggling"],
                "proposed_paths": ["src/helper.py"],
            }])
            with self.assertRaisesRegex(ValueError, "implementation-owner path"):
                revision.propose(root, "v2-proof-path-reject", change, True)

    def test_v2_explicit_scope_revision_converges_with_activation_anchor_and_handoff(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); started = self.v2_plan(root, "v2-converge")
            base_decision = started["navigator"]["scope_evidence"]["decision_fingerprint"]
            change = json.dumps([
                {
                    "kind": "scope-add", "requirement_uid": "REQ-01", "path": "src/helper.py",
                    "reason": "The user confirmed the existing helper is part of the implementation boundary.",
                    "scope_authority": "explicit-user-scope", "confirmed": True,
                },
                {
                    "kind": "proof-update", "requirement_uid": "REQ-01",
                    "reason": "Bind executable proof before approving the revised scope.",
                    "evidence_plan": ["Run the owner test module."],
                    "commands": ["python3 -m unittest discover -s tests -p test_owner.py -v"],
                    "tiers": ["unit"],
                    "editable_paths": ["tests/test_owner.py"],
                },
            ])
            proposed = revision.propose(root, "v2-converge", change, True)
            rendered = revision.render(proposed)
            activated = revision.approve(root, "v2-converge", 2, True)
            active = lock.active_start_report(root, "v2-converge")["report"]
            anchor = json.loads((root / activated["anchor"]["artifact"]).read_text(encoding="utf-8"))
            verbose_dir = root / ".tailtrail" / "runs" / "v2-converge" / "verbose-reports"
            start_markdown_exists = (verbose_dir / "start-plan-verbose-v1.md").is_file()
            start_metadata_exists = (verbose_dir / "start-plan-verbose-v1.json").is_file()
            visible_start = root / "session-reports" / "v2-converge" / "start-plan.md"
            visible_start_exists = visible_start.is_file()
            visible_start_body = visible_start.read_text(encoding="utf-8")

        revised_decision = active["navigator"]["scope_evidence"]["decision_fingerprint"]
        self.assertNotEqual(base_decision, revised_decision)
        self.assertEqual(active["scope_decision_revision"]["scope_decision"]["decision_fingerprint"], revised_decision)
        self.assertEqual(anchor["scope_decision"]["decision_fingerprint"], revised_decision)
        self.assertEqual(set(anchor["requirements"][0]["likely_paths"]), {"src/owner.py", "src/helper.py"})
        self.assertEqual(set(activated["execution_handoff"]["likely_paths"]), {"src/owner.py", "src/helper.py"})
        self.assertTrue(start_markdown_exists)
        self.assertTrue(start_metadata_exists)
        self.assertTrue(visible_start_exists)
        self.assertIn("## Canonical Machine Record", visible_start_body)
        self.assertNotIn("## Complete Saved Planning Payload", visible_start_body)
        self.assertNotIn("Unit tests passed (62/62)", visible_start_body)
        self.assertIn("### Implementation owners", rendered)
        self.assertIn("### Existing proof paths", rendered)

    def test_v2_revision_preserves_host_inspection_and_proof_context(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.v2_plan(root, "v2-preserve-host-context")
            report_path = lock.start_report_path(root, "v2-preserve-host-context")
            saved = json.loads(report_path.read_text(encoding="utf-8"))
            row = saved["report"]["navigator"]["requirement_matrix"][0]
            row["scope_evidence"]["inspection_paths"].append("scripts/read_only_context.py")
            row["scope_evidence"]["proof_paths"].append("tests/test_host_context.py")
            report_path.write_text(json.dumps(saved), encoding="utf-8")

            proposed = revision.propose(root, "v2-preserve-host-context", json.dumps([{
                "kind": "proof-update",
                "requirement_uid": "REQ-01",
                "reason": "Register the focused owner proof without dropping host context.",
                "evidence_plan": ["Run the owner test module."],
                "commands": ["python3 -m unittest discover -s tests -p test_owner.py -v"],
                "tiers": ["unit"],
                "editable_paths": ["tests/test_owner.py"],
            }]), True)

        revised = proposed["proposed_report"]["navigator"]["requirement_matrix"][0]
        self.assertIn("scripts/read_only_context.py", revised["scope_evidence"]["inspection_paths"])
        self.assertIn("tests/test_host_context.py", revised["scope_evidence"]["proof_paths"])

    def test_v2_revision_restores_nonimplementation_context_before_rebuilding_scope(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.v2_plan(root, "v2-restore-nonimplementation")
            report_path = lock.start_report_path(root, "v2-restore-nonimplementation")
            saved = json.loads(report_path.read_text(encoding="utf-8"))
            navigator = saved["report"]["navigator"]
            navigator.pop("host_scope_routing", None)
            navigator["host_input_contract_validated"] = {
                "contract_id": "validation-contract",
                "fingerprint": "sha256:validation-contract",
                "request_mode": "validation-only",
                "paths": [
                    {"path": "tests/test_owner.py", "role": "existing-proof-path"},
                ],
            }
            saved["report"]["host_input_contract"] = {"request_mode": "validation-only"}
            report_path.write_text(json.dumps(saved), encoding="utf-8")

            proposed = revision.propose(root, "v2-restore-nonimplementation", json.dumps([{
                "kind": "proof-update",
                "requirement_uid": "REQ-01",
                "reason": "Keep the non-editing proof route while revising its command binding.",
                "evidence_plan": ["Run the owner proof."],
                "commands": ["python3 -m unittest tests.test_owner -q"],
                "tiers": ["unit"],
                "editable_paths": ["tests/test_owner.py"],
            }]), True)

        navigator = proposed["proposed_report"]["navigator"]
        row = navigator["requirement_matrix"][0]
        self.assertEqual(navigator["host_scope_routing"]["request_mode"], "validation-only")
        self.assertEqual(row["scope_evidence"]["implementation_owners"], [])
        self.assertEqual(row["likely_paths"], [])
        self.assertFalse(navigator["scope_quality"]["blocking"])

    def test_validated_aidlc_correction_is_used_as_the_next_revision_base(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.plan(root, "aidlc-canonical-base")
            active = lock.active_start_report(root, "aidlc-canonical-base")["report"]
            requirements = json.loads(json.dumps(active["navigator"]["requirement_matrix"]))
            requirements[0]["statement"] = "Cancel an eligible order and record the validated AIDLC correction."
            planning = root / ".tailtrail" / "runs" / "aidlc-canonical-base" / "planning"
            correction = planning / "aidlc-revised-requirements-v1.json"
            correction.write_text(json.dumps({"requirements": requirements, "aidlc_answers": {"Q-01": "accepted"}}), encoding="utf-8")
            (planning / "aidlc-correction-state.json").write_text(json.dumps({
                "state": "revision-ready",
                "active_revision": correction.relative_to(root).as_posix(),
            }), encoding="utf-8")

            proposed = revision.propose(root, "aidlc-canonical-base", json.dumps([{
                "kind": "proof-update",
                "requirement_uid": "REQ-01",
                "reason": "Bind proof after the validated correction.",
                "evidence_plan": ["Run the focused cancellation proof."],
                "commands": ["python3 -m unittest tests.test_planning_revision -v"],
                "tiers": ["unit"],
                "editable_paths": ["tests/test_planning_revision.py"],
            }]), True)

        self.assertEqual(proposed["base_projection"]["kind"], "validated-aidlc-correction")
        self.assertEqual(
            proposed["proposed_report"]["navigator"]["requirement_matrix"][0]["statement"],
            "Cancel an eligible order and record the validated AIDLC correction.",
        )

    def test_canonical_projection_is_versioned_and_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.plan(root, "canonical-idempotence")
            first_report, first_source = lock.canonical_plan_report(root, "canonical-idempotence")
            second_report, second_source = lock.canonical_plan_report(root, "canonical-idempotence")
            planning = root / ".tailtrail" / "runs" / "canonical-idempotence" / "planning"
            artifacts = list(planning.glob("canonical-plan-projection-v*.json"))

        self.assertEqual(first_report, second_report)
        self.assertEqual(first_source["canonical_artifact"], second_source["canonical_artifact"])
        self.assertEqual(len(artifacts), 1)
        self.assertEqual(first_source["kind"], "active-approved-report")

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
        removal = proposed["changes"][0]["removal"]
        self.assertEqual(removal["field"], "likely_paths")
        self.assertEqual(removal["before"], ["src/service.py", "src/api.py"])
        self.assertEqual(removal["after"], ["src/service.py"])
        self.assertEqual(removal["reason"], "User clarified this is internal-only service support.")
        self.assertEqual(original, original_after)
        self.assertEqual(state["active_revision"], 2)
        self.assertIsNone(state["pending_revision"])
        self.assertNotIn("src/api.py", anchor["requirements"][0]["likely_paths"])
        self.assertEqual(events["planning_revision_proposed"], 1)
        self.assertEqual(events["planning_revision_approved"], 1)

    def test_pending_revision_can_be_superseded_without_activation_and_projections_converge(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self.plan(root, "supersede")
            report_path = lock.start_report_path(root, "supersede")
            saved = json.loads(report_path.read_text(encoding="utf-8"))
            saved["report"]["navigator"]["requirement_query_frame"] = {
                "schema_version": "1",
                "type": "tailtrail-requirement-query-frame",
                "exact_goal_preserved": True,
                "query_terms": ["cancel", "preserve"],
                "requirements": [
                    {"display_id": "REQ-01", "requirement_id": "old-1", "statement": "Cancel an eligible order.", "query_terms": ["cancel"]},
                    {"display_id": "REQ-02", "requirement_id": "old-2", "statement": "Preserve shipped-order rejection.", "query_terms": ["preserve"]},
                ],
            }
            saved["report"]["guided_delivery"]["slice_strategy"] = {"requirement_ids": ["REQ-01", "REQ-02"]}
            report_path.write_text(json.dumps(saved), encoding="utf-8")
            revision.propose(root, "supersede", json.dumps([{
                "kind": "requirement-update", "requirement_uid": "REQ-01",
                "statement": "Cancel eligible orders.", "reason": "First wording was incomplete.",
            }]), True)
            corrected = revision.propose(root, "supersede", json.dumps([
                {
                    "kind": "requirement-update", "requirement_uid": "REQ-01",
                    "statement": "Cancel eligible orders while preserving shipped-order rejection.",
                    "reason": "Consolidate the complete behavior into one requirement.",
                },
                {
                    "kind": "requirement-remove", "requirement_uid": "REQ-02",
                    "reason": "The second row is redundant after consolidation.",
                },
            ]), True, supersede_pending=True)
            old = revision.show(root, "supersede", 2)
            state = lock.revision_state(root, "supersede")
            decisions = revision.show(root, "supersede", 3)["proposed_report"]
            events = ledger.projection(root, "supersede")["activity"]

        self.assertEqual(corrected["revision"], 3)
        self.assertEqual(corrected["supersedes_revision"], 2)
        self.assertEqual(old["state"], "superseded")
        self.assertEqual(old["superseded_by_revision"], 3)
        self.assertEqual(state["active_revision"], 1)
        self.assertEqual(state["pending_revision"], 3)
        self.assertEqual([row["display_id"] for row in corrected["requirement_continuity"]], ["REQ-01"])
        frame = decisions["navigator"]["requirement_query_frame"]
        self.assertEqual([row["display_id"] for row in frame["requirements"]], ["REQ-01"])
        self.assertEqual(frame["requirements"][0]["statement"], "Cancel eligible orders while preserving shipped-order rejection.")
        self.assertEqual(decisions["guided_delivery"]["slice_strategy"]["requirement_ids"], ["REQ-01"])
        self.assertEqual(events["planning_revision_proposed"], 2)
        self.assertEqual(events["planning_revision_superseded"], 1)

    def test_revision_repairs_phantom_ids_in_derived_requirement_projections(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.plan(root, "phantom-derived-references")
            report_path = lock.start_report_path(root, "phantom-derived-references")
            saved = json.loads(report_path.read_text(encoding="utf-8"))
            saved["report"]["navigator"]["requirement_matrix"] = [
                saved["report"]["navigator"]["requirement_matrix"][0]
            ]
            saved["report"]["architecture_plan"] = {
                "invariants": [
                    {"invariant": "phantom only", "requirement_ids": ["REQ-03"]},
                    {"invariant": "mixed", "requirement_ids": ["REQ-01", "REQ-03"]},
                ],
                "scope_roles": [
                    {"path": "src/service.py", "requirement_ids": ["REQ-01", "REQ-02"]},
                    {"path": "tests/test_phantom.py", "requirement_ids": ["REQ-02"]},
                ],
            }
            saved["report"]["guided_delivery"]["slice_strategy"] = {
                "mode": "requirement-sequenced",
                "requirement_ids": ["REQ-01", "REQ-02", "REQ-03"],
            }
            report_path.write_text(json.dumps(saved), encoding="utf-8")

            proposed = revision.propose(root, "phantom-derived-references", json.dumps([{
                "kind": "proof-update",
                "requirement_uid": "REQ-01",
                "reason": "Rebuild the canonical proof projection.",
                "evidence_plan": ["Run the focused proof."],
            }]), True)

        report = proposed["proposed_report"]
        architecture = report["architecture_plan"]
        self.assertEqual(architecture["invariants"], [{"invariant": "mixed", "requirement_ids": ["REQ-01"]}])
        self.assertEqual(architecture["scope_roles"], [{"path": "src/service.py", "requirement_ids": ["REQ-01"]}])
        self.assertEqual(report["guided_delivery"]["slice_strategy"]["requirement_ids"], ["REQ-01"])
        repairs = report["planning_revision_projection_repair"]["repairs"]
        self.assertTrue(any(row.get("removed_requirement_ids") == ["REQ-02", "REQ-03"] for row in repairs))
        self.assertTrue(any(row.get("action") == "removed-empty-derived-row" for row in repairs))

    def test_supersede_requires_an_existing_pending_revision(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self.plan(root, "nothing-pending")
            with self.assertRaisesRegex(ValueError, "no pending plan revision"):
                revision.propose(root, "nothing-pending", json.dumps([{
                    "kind": "requirement-remove", "requirement_uid": "REQ-02", "reason": "Redundant.",
                }]), True, supersede_pending=True)

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

    def test_required_aidlc_switch_supersedes_rejected_pending_revision(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.plan(root, "standard-rejection-recovery")
            revision.propose(root, "standard-rejection-recovery", json.dumps([{
                "kind": "requirement-update",
                "requirement_uid": "REQ-01",
                "statement": "Cancel an eligible order through the recovered requirement flow.",
                "reason": "First material proposal.",
            }]), True)
            ledger.append_event(root, "standard-rejection-recovery", "proposal_rejected", {"reason": "first rejection"})
            ledger.append_event(root, "standard-rejection-recovery", "proposal_rejected", {"reason": "second rejection"})

            switched = revision.propose_aidlc_standard(root, "standard-rejection-recovery", True)
            state = lock.revision_state(root, "standard-rejection-recovery")
            superseded = revision.show(root, "standard-rejection-recovery", 2)

        self.assertEqual(switched["revision"], 3)
        self.assertEqual(switched["supersedes_revision"], 2)
        self.assertEqual(state["pending_revision"], 3)
        self.assertEqual(superseded["state"], "superseded")
        self.assertEqual(superseded["superseded_by_revision"], 3)

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

    def test_revision_show_renders_pending_start_plans(self) -> None:
        """The public route is human-readable by default for every revision.

        The first pending version exercises registry-backed ``command_id``
        rendering.  A superseding version proves the route is not hard-coded
        to v2.  JSON remains an opt-in machine route.
        """
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.v2_plan(root, "revision-show")
            report_path = lock.start_report_path(root, "revision-show")
            saved = json.loads(report_path.read_text(encoding="utf-8"))
            saved["report"]["input_roles"] = {
                "inputs": [
                    {"input_id": "IN-01", "role": "target", "locator": root.as_posix(), "access": "read-write", "status": "verified"},
                    {
                        "input_id": "IN-02", "role": "requirement-artifact",
                        "locator": "/tmp/requirements.md", "access": "read-only",
                        "status": "inspected", "sha256": "bound-hash",
                    },
                ],
            }
            report_path.write_text(json.dumps(saved), encoding="utf-8")
            command = "python3 -m unittest discover -s tests -p test_owner.py -v"
            v2 = revision.propose(root, "revision-show", json.dumps([{
                "kind": "proof-update",
                "requirement_uid": "REQ-01",
                "reason": "Bind the registry-backed public-route proof.",
                "evidence_plan": ["Run the owner proof."],
                "commands": [command],
                "tiers": ["unit"],
                "editable_paths": ["tests/test_owner.py"],
            }]), True)
            v3 = revision.propose(root, "revision-show", json.dumps([{
                "kind": "requirement-update",
                "requirement_uid": "REQ-01",
                "statement": "Fix owner behavior while preserving the public revision view.",
                "reason": "Create a later pending revision for public rendering coverage.",
                "retain_scope_confirmed": True,
            }]), True, supersede_pending=True)

            def revision_show(number: int, *extra: str) -> subprocess.CompletedProcess[str]:
                return subprocess.run([
                    sys.executable, (ROOT / "scripts" / "tailtrail.py").as_posix(),
                    "planning", "revision-show", "--root", root.as_posix(),
                    "--run-id", "revision-show", "--revision", str(number), *extra,
                ], cwd=ROOT, text=True, capture_output=True, check=False)

            shown_v2 = revision_show(int(v2["revision"]))
            shown_v3 = revision_show(int(v3["revision"]))
            raw_v3 = revision_show(int(v3["revision"]), "--format", "json")
            visible_v3 = (root / "session-reports" / "revision-show" / "start-plan.md").read_text(encoding="utf-8")

        for shown in (shown_v2, shown_v3):
            self.assertEqual(shown.returncode, 0, shown.stderr + shown.stdout)
            self.assertIn("# TailTrail Start Plan", shown.stdout)
            self.assertIn("## Command Reference Registry", shown.stdout)
            self.assertIn("## Bound Planning Inputs", shown.stdout)
            self.assertIn("`/tmp/requirements.md`", shown.stdout)
            self.assertIn("`bound-hash`", shown.stdout)
            self.assertIn("never grant editable implementation scope", shown.stdout)
            self.assertNotIn('"proposed_report"', shown.stdout)
        self.assertIn(command, shown_v2.stdout)
        self.assertIn("Fix owner behavior while preserving the public revision view.", visible_v3)
        self.assertIn("Plan revision:** active `1`; pending `3`.", visible_v3)
        self.assertEqual(raw_v3.returncode, 0, raw_v3.stderr + raw_v3.stdout)
        self.assertIn('"proposed_report"', raw_v3.stdout)

    def test_revision_show_fails_closed_for_a_malformed_pending_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.v2_plan(root, "revision-show-malformed")
            proposed = revision.propose(root, "revision-show-malformed", json.dumps([{
                "kind": "proof-update",
                "requirement_uid": "REQ-01",
                "reason": "Bind the public-route proof.",
                "evidence_plan": ["Run the owner proof."],
                "commands": ["python3 -m unittest discover -s tests -p test_owner.py -v"],
                "tiers": ["unit"],
                "editable_paths": ["tests/test_owner.py"],
            }]), True)
            artifact = revision.revision_path(root, "revision-show-malformed", int(proposed["revision"]))
            saved = json.loads(artifact.read_text(encoding="utf-8"))
            saved["proposed_report"] = None
            artifact.write_text(json.dumps(saved), encoding="utf-8")
            shown = subprocess.run([
                sys.executable, (ROOT / "scripts" / "tailtrail.py").as_posix(),
                "planning", "revision-show", "--root", root.as_posix(),
                "--run-id", "revision-show-malformed",
            ], cwd=ROOT, text=True, capture_output=True, check=False)

        self.assertEqual(shown.returncode, 2)
        self.assertIn("has no renderable proposed Start Plan", shown.stdout)
        self.assertNotIn('"proposed_report"', shown.stdout)

    def test_requirement_update_remaps_scope_packet_references(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); self.v2_plan(root, "v2-reword")
            before = lock.active_start_report(root, "v2-reword")["report"]
            old_ids = {
                str(item.get("requirement_id", ""))
                for item in before["navigator"]["requirement_query_frame"]["requirements"]
                if isinstance(item, dict)
            }
            change = json.dumps([{
                "kind": "requirement-update", "requirement_uid": "REQ-01",
                "statement": "Fix owner behavior and reject empty names.",
                "retain_scope_confirmed": True,
                "reason": "Clarify acceptance without changing ownership.",
            }])
            proposed = revision.propose(root, "v2-reword", change, True)
            shown = revision.show(root, "v2-reword", 2)
            revised = shown["proposed_report"]

            def requirement_id_lists(value, path="report"):
                found = []
                if isinstance(value, dict):
                    for key, item in value.items():
                        if key == "requirement_ids" and isinstance(item, list):
                            found.extend((path, str(identifier)) for identifier in item)
                        else:
                            found.extend(requirement_id_lists(item, f"{path}.{key}"))
                elif isinstance(value, list):
                    for index, item in enumerate(value):
                        found.extend(requirement_id_lists(item, f"{path}[{index}]"))
                return found

        self.assertEqual(proposed["revision"], 2)
        self.assertIn("Fix owner behavior and reject empty names.", revised["navigator"]["requirement_matrix"][0]["statement"])
        leftovers = [(path, identifier) for path, identifier in requirement_id_lists(revised) if identifier in old_ids]
        print("LEFTOVER:", leftovers)
        self.assertFalse(leftovers, "superseded frame IDs must not survive the revision")

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

    def test_public_cli_renders_lite_fallback_when_official_pack_is_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.plan(root, "cli-standard-fallback")
            proposed = subprocess.run([
                sys.executable, (ROOT / "scripts" / "tailtrail.py").as_posix(), "planning", "aidlc-standard", "--root", root.as_posix(),
                "--run-id", "cli-standard-fallback", "--approved-proposal",
            ], cwd=ROOT, text=True, capture_output=True, check=False)
            approved = subprocess.run([
                sys.executable, (ROOT / "scripts" / "tailtrail.py").as_posix(), "planning", "aidlc-standard-approve", "--root", root.as_posix(),
                "--run-id", "cli-standard-fallback", "--revision", "2", "--approved",
            ], cwd=ROOT, text=True, capture_output=True, check=False)

        self.assertEqual(proposed.returncode, 0, proposed.stderr + proposed.stdout)
        self.assertEqual(approved.returncode, 0, approved.stderr + approved.stdout)
        self.assertIn("# TailTrail AIDLC Mode Switch Result", approved.stdout)
        self.assertIn("No official AIDLC questions or answers were generated", approved.stdout)
        self.assertIn("No implementation authority was granted", approved.stdout)


if __name__ == "__main__":
    unittest.main()
