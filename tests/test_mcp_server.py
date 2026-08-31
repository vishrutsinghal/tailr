import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MCP_PATH = ROOT / "scripts" / "mcp-server.py"


def load_module():
    spec = importlib.util.spec_from_file_location("tailtrail_mcp_server_test", MCP_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_script(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


mcp = load_module()
lock = load_script("mcp_execution_lock_test", "scripts/planning-lock.py")
anchor = load_script("mcp_execution_anchor_test", "scripts/change-intent-anchor.py")


class McpServerTests(unittest.TestCase):
    def test_debug_orientation_surface_is_read_only_or_explicitly_approval_gated(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaisesRegex(ValueError, "no debug orientation"):
                mcp.call_tool("debug_orientation_show", {"root": root.as_posix(), "run_id": "missing"})
            self.assertFalse((root / ".tailtrail").exists())
            with self.assertRaisesRegex(ValueError, "requires approved: true"):
                mcp.call_tool("debug_orientation_create", {"root": root.as_posix(), "run_id": "missing", "approved": False})

    def test_complete_debug_lifecycle_tools_are_classified_and_approval_gated(self) -> None:
        read_only = {"debug_intake_show", "debug_reproduction_show", "debug_orientation_show",
                     "debug_hypothesis_ledger_show", "debug_correction_show", "debug_governance_show",
                     "debug_harness_convergence_show", "debug_completion_report_show",
                     "workflow_current", "workflow_resume", "workflow_replay", "completion_report_show"}
        read_only.update({"debug_evaluation_report", "debug_release_gate"})
        controlled = {"debug_start", "debug_reproduction_draft", "debug_reproduction_revise",
                      "debug_reproduction_approve", "debug_orientation_create", "debug_hypothesis_add",
                      "debug_hypothesis_reprioritize", "debug_experiment_propose", "debug_experiment_record",
                      "debug_root_cause_prove", "debug_correction_propose", "debug_correction_approve",
                      "debug_harness_convergence_finalize", "debug_closure_finalize"}
        controlled.add("debug_evaluation_run")
        self.assertLessEqual(read_only, set(mcp.READ_ONLY_TOOLS))
        self.assertLessEqual(controlled, set(mcp.CONTROLLED_TOOLS))
        for name in controlled:
            required = mcp.tool_definitions()[name]["inputSchema"]["required"]
            self.assertIn("approved", required, name)
            with self.assertRaisesRegex(ValueError, "requires approved: true"):
                mcp.call_tool(name, {"root": ".", "run_id": "missing", "approved": False})

    def test_tool_list_has_read_only_and_one_approval_gated_allowlist(self):
        self.assertTrue({"navigator_plan", "ledger_state", "anchor_show", "git_readiness", "planning_lock_show", "planning_decision_show", "planning_investigation_show", "planning_revision_show", "planning_authority_show", "planning_question_context_show", "aidlc_official_status", "aidlc_official_bridge_show", "aidlc_official_state_show", "aidlc_official_sanitize_validate", "aidlc_official_session_status", "host_conformance_report", "execution_evidence_show"}.issubset(set(mcp.READ_ONLY_TOOLS)))
        self.assertTrue({"harness_control_check", "source_patch_apply", "planning_lock_start", "planning_lock_approve", "tailtrail_start", "execution_evidence_record", "planning_investigate", "planning_revision_propose", "planning_revision_approve", "planning_aidlc_standard_propose", "planning_aidlc_standard_approve", "spec_kit_import", "spec_kit_amendment_propose", "spec_kit_anchor_approve", "spec_kit_convergence_record", "spec_kit_ci_ingest"}.issubset(set(mcp.CONTROLLED_TOOLS)))
        self.assertEqual(set(mcp.HANDLERS), set((*mcp.READ_ONLY_TOOLS, *mcp.CONTROLLED_TOOLS)))
        self.assertEqual(mcp.ensure_safe_tools(), [])

    def test_tool_list_is_projected_from_registry(self):
        projection = mcp.load_registry().mcp_projection(mcp.load_registry().load_registry())

        projected = {item["tool"]: item for item in projection}
        self.assertTrue(set(mcp.READ_ONLY_TOOLS).issubset(projected))
        self.assertTrue(projected["anchor_show"]["read_only"])
        self.assertFalse(projected["harness_control_check"]["read_only"])
        self.assertTrue(projected["harness_control_check"]["requires_approval"])
        self.assertFalse(projected["source_patch_apply"]["read_only"])
        self.assertTrue(projected["source_patch_apply"]["requires_approval"])
        self.assertFalse(projected["planning_lock_start"]["read_only"])
        self.assertTrue(projected["planning_lock_approve"]["requires_approval"])
        self.assertFalse(projected["tailtrail_start"]["read_only"])
        self.assertTrue(projected["tailtrail_start"]["requires_approval"])
        self.assertTrue(projected["planning_investigation_show"]["read_only"])
        self.assertFalse(projected["planning_investigate"]["read_only"])
        self.assertTrue(projected["planning_investigate"]["requires_approval"])
        self.assertTrue(projected["planning_revision_show"]["read_only"])
        self.assertFalse(projected["planning_revision_propose"]["read_only"])
        self.assertTrue(projected["planning_revision_approve"]["requires_approval"])
        self.assertFalse(projected["planning_aidlc_standard_propose"]["read_only"])
        self.assertTrue(projected["planning_aidlc_standard_approve"]["requires_approval"])
        self.assertTrue(projected["planning_decision_show"]["read_only"])
        self.assertTrue(projected["planning_authority_show"]["read_only"])
        self.assertTrue(projected["execution_evidence_show"]["read_only"])
        self.assertFalse(projected["execution_evidence_record"]["read_only"])
        self.assertTrue(projected["execution_evidence_record"]["requires_approval"])

    def test_tool_schemas_are_json_objects(self):
        tools = mcp.tool_list()
        self.assertEqual([item["name"] for item in tools], list(mcp.TOOL_ORDER))
        for tool in tools:
            self.assertIsInstance(tool["description"], str)
            self.assertIsInstance(tool["inputSchema"], dict)
            self.assertEqual(tool["inputSchema"]["type"], "object")
            self.assertIn("additionalProperties", tool["inputSchema"])

    def test_host_conformance_report_is_read_only_and_does_not_infer_runtime_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = mcp.call_tool("host_conformance_report", {"root": tmp, "host": "codex"})
        self.assertTrue(result["execution"]["read_only"])
        self.assertEqual(result["result"]["runtime_conformance"][0]["runtime_status"], "not-validated")

    def test_question_context_show_is_read_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact = root / ".tailtrail" / "runs" / "question-run" / "planning" / "question-context-v1.json"
            artifact.parent.mkdir(parents=True)
            artifact.write_text(json.dumps({
                "schema_version": "1",
                "type": "tailtrail-question-context",
                "run_id": "question-run",
                "aidlc_mode": "standard",
                "question_authority": "official-ai-dlc-pack",
                "goal": "Add validation.",
                "requirements": [],
                "known_facts": [],
                "unknowns": [],
                "question_policy": {},
            }), encoding="utf-8")
            result = mcp.call_tool("planning_question_context_show", {"root": tmp, "run_id": "question-run"})
        self.assertTrue(result["execution"]["read_only"])
        self.assertEqual(result["result"]["question_authority"], "official-ai-dlc-pack")

    def test_enterprise_target_policy_inspection_is_read_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            policy = root / "enterprise-policy.json"
            policy.write_text(json.dumps({
                "schema_version": "1", "type": "tailtrail-enterprise-target-policy",
                "allowed_target_roots": [root.as_posix()], "restricted_target_roots": [],
                "require_identity_verification": True, "require_declared_owner": False, "aliases": {},
            }), encoding="utf-8")
            result = mcp.enterprise_target_policy_inspect({"root": root.as_posix(), "policy": "enterprise-policy.json"})
        self.assertTrue(result["execution"]["read_only"])
        self.assertEqual(result["result"]["status"], "passed")

    def test_doctor_names_the_first_tool_order_mismatch(self):
        original = mcp.tool_definitions

        def out_of_order_definitions():
            definitions = original()
            planning_lock = definitions.pop("planning_lock_show")
            definitions["planning_lock_show"] = planning_lock
            return definitions

        try:
            mcp.tool_definitions = out_of_order_definitions
            errors = mcp.ensure_safe_tools()
        finally:
            mcp.tool_definitions = original

        self.assertEqual(
            errors[0],
            "tool registry order mismatch at index 25: expected `planning_lock_show`, got `planning_decision_show`",
        )

    def test_unknown_tool_is_rejected(self):
        with self.assertRaises(ValueError):
            mcp.call_tool("write_file", {})
        request = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "apply_fix", "arguments": {}}}
        response = mcp.handle(request)
        self.assertIn("error", response)
        self.assertIn("Unknown or disallowed", response["error"]["message"])

    def test_execution_evidence_mcp_requires_explicit_approval(self):
        with self.assertRaisesRegex(ValueError, "approved: true"):
            mcp.execution_evidence_record({"run_id": "demo", "event": {}, "approved": False})

    def test_execution_evidence_show_is_read_only_when_no_events_exist(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = mcp.execution_evidence_show({"root": tmp, "run_id": "demo"})
        self.assertTrue(result["execution"]["read_only"])
        self.assertEqual(result["result"]["count"], 0)

    def test_execution_evidence_mcp_records_only_a_valid_approved_run_fact(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lock.create(root, "validate order", "evidence-run")
            proposal = root / "proposal.json"
            proposal.write_text(json.dumps({"requirements": [{
                "statement": "Reject an invalid order.", "acceptance_criteria": ["invalid orders reject"],
                "preserve_rules": ["valid orders remain accepted"], "likely_paths": ["src/orders.py"],
                "evidence_plan": [], "validation_contract": {"state": "required", "tiers": ["unit"]},
                "architecture_contract": {"required_paths": [], "protected_paths": [], "forbidden_imports": []},
                "behavior_contract": {"scenarios": []},
            }]}), encoding="utf-8")
            anchor.draft(root, "evidence-run", proposal)
            requirement_uid = anchor.approve(root, "evidence-run")["requirements"][0]["requirement_uid"]
            lock.approve(root, "evidence-run", True)
            recorded = mcp.execution_evidence_record({
                "root": root.as_posix(), "run_id": "evidence-run", "approved": True,
                "event": {"kind": "command-result", "requirement_uids": [requirement_uid],
                          "changed_paths": ["src/orders.py"], "tier": "unit", "command_label": "order validation",
                          "command": "python -m unittest tests.test_orders", "outcome": "pass",
                          "environment": "local", "asserted_behavior": "Invalid orders reject."},
            })
            shown = mcp.execution_evidence_show({"root": root.as_posix(), "run_id": "evidence-run"})

        self.assertFalse(recorded["execution"]["read_only"])
        self.assertEqual(recorded["result"]["kind"], "command-result")
        self.assertEqual(shown["result"]["count"], 1)

    def test_spec_kit_mcp_controls_are_approval_gated(self):
        with self.assertRaisesRegex(ValueError, "approved: true"):
            mcp.spec_kit_import({"root": ROOT.as_posix(), "feature": "001-orders", "approved": False})
        with self.assertRaisesRegex(ValueError, "approved: true"):
            mcp.spec_kit_convergence_record({"root": ROOT.as_posix(), "run_id": "run", "approved": False})

    def test_planning_investigation_mcp_requires_explicit_approval(self):
        with self.assertRaisesRegex(ValueError, "approved: true"):
            mcp.planning_investigate({
                "root": ROOT.as_posix(),
                "run_id": "planning-run",
                "paths": ["src/service.py"],
                "approved": False,
            })

    def test_planning_revision_mcp_requires_explicit_approval(self):
        with self.assertRaisesRegex(ValueError, "approved: true"):
            mcp.planning_revision_propose({
                "root": ROOT.as_posix(), "run_id": "planning-run", "changes": [{"kind": "scope-remove"}], "approved": False,
            })
        with self.assertRaisesRegex(ValueError, "approved: true"):
            mcp.planning_revision_approve({"root": ROOT.as_posix(), "run_id": "planning-run", "revision": 2, "approved": False})
        with self.assertRaisesRegex(ValueError, "approved: true"):
            mcp.planning_aidlc_standard_propose({"root": ROOT.as_posix(), "run_id": "planning-run", "approved": False})
        with self.assertRaisesRegex(ValueError, "approved: true"):
            mcp.planning_aidlc_standard_approve({"root": ROOT.as_posix(), "run_id": "planning-run", "revision": 2, "approved": False})

    def test_stdio_tools_list(self):
        request = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}) + "\n"
        result = subprocess.run(
            [sys.executable, MCP_PATH.as_posix(), "serve"],
            cwd=ROOT,
            input=request,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["id"], 1)
        self.assertEqual([item["name"] for item in payload["result"]["tools"]], list(mcp.TOOL_ORDER))

    def test_doctor_passes(self):
        result = subprocess.run(
            [sys.executable, MCP_PATH.as_posix(), "doctor"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn("Read-only", result.stdout)

    def test_maintainability_assessment_show_reads_latest_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact_dir = root / ".tailtrail" / "runs" / "demo" / "maintainability"
            artifact_dir.mkdir(parents=True)
            (artifact_dir / "assessment-1.json").write_text(json.dumps({"type": "tailtrail-maintainability-harness", "complete": True}), encoding="utf-8")
            result = mcp.maintainability_assessment_show({"root": root.as_posix(), "run_id": "demo"})
        self.assertTrue(result["execution"]["read_only"])
        self.assertTrue(result["result"]["complete"])

    def test_aidlc_official_status_is_read_only_when_no_pack_is_installed(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = mcp.aidlc_official_status({"root": Path(tmp).as_posix()})
        self.assertTrue(result["execution"]["read_only"])
        self.assertEqual(result["result"]["state"], "not-installed")

    def test_aidlc_official_state_show_is_read_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run = root / ".tailtrail" / "runs" / "demo"
            run.mkdir(parents=True)
            (run / "manifest.json").write_text(json.dumps({"schema_version": "1", "type": "tailtrail-run-manifest", "run_id": "demo", "goal": "inspect state"}), encoding="utf-8")
            result = mcp.aidlc_official_state_show({"root": root.as_posix(), "run_id": "demo"})
        self.assertTrue(result["execution"]["read_only"])
        self.assertTrue(result["result"]["valid"])
        self.assertEqual(result["result"]["status"], "incomplete")

    def test_aidlc_official_sanitize_validate_does_not_return_artifact_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "evaluation.json"
            path.write_text(json.dumps({
                "schema_version": "1", "type": "tailtrail-closure-calibrated-evaluation",
                "evaluation_id": "evaluation-1", "run_id": "run", "evidence_label": "saved-local-artifacts",
                "mode": "run-observation", "baseline": None, "tailtrail_outcome": {}, "comparison": None,
                "boundary": "Saved local evidence only.",
            }), encoding="utf-8")
            result = mcp.aidlc_official_sanitize_validate({"root": root.as_posix(), "input": "evaluation.json", "context": "evaluation"})
        self.assertTrue(result["execution"]["read_only"])
        self.assertEqual(result["result"]["status"], "passed")
        self.assertNotIn("Saved local evidence only", json.dumps(result))

    def test_control_check_requires_explicit_approval(self):
        with self.assertRaises(ValueError):
            mcp.harness_control_check({"run_id": "demo", "controls": "controls.json", "approved": False})

    def test_source_patch_requires_an_approved_planning_lock(self):
        original = mcp.command_result

        def denied_lock(command, cwd):
            return {"command": command, "exit_code": 2, "stdout": "", "stderr": "Planning Lock error"}

        try:
            mcp.command_result = denied_lock
            with self.assertRaisesRegex(ValueError, "Planning Lock"):
                mcp.source_patch_apply({"root": ROOT.as_posix(), "run_id": "plan-1", "approved": True, "patch": "diff --git a/a.txt b/a.txt\n"})
        finally:
            mcp.command_result = original

    def test_control_check_requires_an_approved_planning_lock(self):
        original = mcp.command_result

        def denied_lock(command, root):
            return {"exit_code": 2, "stdout": "", "stderr": "Planning Lock is awaiting approval"}

        try:
            mcp.command_result = denied_lock
            with self.assertRaisesRegex(ValueError, "Planning Lock"):
                mcp.harness_control_check({"root": ROOT.as_posix(), "run_id": "plan-1", "controls": "controls.json", "approved": True})
        finally:
            mcp.command_result = original

    def test_planning_lock_start_requires_an_explicit_user_start_signal(self):
        with self.assertRaisesRegex(ValueError, "approved: true"):
            mcp.planning_lock_start({"goal": "plan Terraform", "root": ROOT.as_posix()})

    def test_planning_lock_start_and_approve_construct_safe_commands(self):
        calls = []
        original = mcp.command_result

        def fake_command_result(command, cwd):
            calls.append(command)
            return {"command": command, "cwd": cwd.as_posix(), "exit_code": 0, "stdout": "{\"ok\": true}", "stderr": ""}

        try:
            mcp.command_result = fake_command_result
            started = mcp.planning_lock_start({"goal": "plan Terraform", "root": ROOT.as_posix(), "run_id": "tf-plan", "reference_roots": ["../reference"], "approved": True})
            approved = mcp.planning_lock_approve({"root": ROOT.as_posix(), "run_id": "tf-plan", "approved": True})
        finally:
            mcp.command_result = original

        self.assertTrue(started["execution"]["local_metadata_only"])
        self.assertTrue(approved["execution"]["local_metadata_only"])
        self.assertEqual(calls[0][2], "start")
        self.assertIn("--reference-root", calls[0])
        self.assertEqual(calls[1][2], "approve")
        self.assertIn("--approved", calls[1])

    def test_start_report_approval_activates_the_saved_plan(self):
        calls = []
        original = mcp.command_result
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = root / ".tailtrail" / "runs" / "saved-plan" / "planning" / "start-report-v1.json"
            report.parent.mkdir(parents=True)
            report.write_text("{}", encoding="utf-8")

            def fake_command_result(command, cwd):
                calls.append(command)
                return {"command": command, "cwd": cwd.as_posix(), "exit_code": 0, "stdout": "{\"ok\": true}", "stderr": ""}

            try:
                mcp.command_result = fake_command_result
                result = mcp.planning_lock_approve({"root": root.as_posix(), "run_id": "saved-plan", "approved": True})
            finally:
                mcp.command_result = original
        self.assertTrue(result["execution"]["local_metadata_only"])
        self.assertEqual(calls[0][2], "activate")
        self.assertEqual(calls[0][-2:], ["--format", "json"])

    def test_atomic_tailtrail_start_requires_explicit_request_and_returns_one_report(self):
        with self.assertRaisesRegex(ValueError, "approved: true"):
            mcp.tailtrail_start({"goal": "plan task 1"})

        calls = []
        original = mcp.command_result

        def fake_command_result(command, cwd):
            calls.append(command)
            return {"command": command, "cwd": cwd.as_posix(), "exit_code": 0, "stdout": "# TailTrail Start Plan\n\n## Planning Lock\n", "stderr": ""}

        try:
            mcp.command_result = fake_command_result
            result = mcp.tailtrail_start({"goal": "plan task 1 and task 2 hands-free", "root": ROOT.as_posix(), "run_id": "program-1", "changed": ["src/a.py"], "approved": True})
        finally:
            mcp.command_result = original

        self.assertTrue(result["result"].startswith("# TailTrail Start Plan"))
        self.assertTrue(result["execution"]["local_metadata_only"])
        self.assertTrue(result["execution"]["execution_blocked"])
        self.assertIn("task-start.py", calls[0][1])
        self.assertIn("--planning-run-id", calls[0])
        self.assertEqual(calls[0][calls[0].index("--format") + 1], "markdown")
        self.assertNotIn("--no-planning-lock", calls[0])

    def test_atomic_tailtrail_start_forwards_sanitized_debug_classification_inputs(self):
        calls = []
        original = mcp.command_result

        def fake_command_result(command, cwd):
            calls.append(command)
            return {"command": command, "cwd": cwd.as_posix(), "exit_code": 0, "stdout": "# TailTrail Debug Start Plan\n", "stderr": ""}

        try:
            mcp.command_result = fake_command_result
            result = mcp.tailtrail_start({
                "goal": "checkout is misbehaving",
                "root": ROOT.as_posix(),
                "workflow": "debug",
                "error_artifact_supplied": True,
                "reproduction_command_supplied": True,
                "approved": True,
            })
        finally:
            mcp.command_result = original

        self.assertTrue(result["result"].startswith("# TailTrail Debug Start Plan"))
        self.assertIn("--debug", calls[0])
        self.assertEqual(calls[0][calls[0].index("--error") + 1], "provided-via-mcp")
        self.assertEqual(calls[0][calls[0].index("--command") + 1], "provided-via-mcp")

    def test_navigator_plan_command_construction(self):
        calls = []
        original = mcp.command_result

        def fake_command_result(command, cwd):
            calls.append((command, cwd))
            return {"command": command, "cwd": cwd.as_posix(), "exit_code": 0, "stdout": "{\"ok\": true}", "stderr": ""}

        try:
            mcp.command_result = fake_command_result
            result = mcp.navigator_plan({"goal": "fix bug", "root": ROOT.as_posix(), "changed": ["src/a.py"], "format": "json"})
        finally:
            mcp.command_result = original

        self.assertEqual(result["result"], {"ok": True})
        command, cwd = calls[0]
        self.assertEqual(cwd, ROOT)
        self.assertIn("navigator.py", command[1])
        self.assertIn("--changed", command)
        self.assertIn("src/a.py", command)

    def test_start_report_stays_read_only_and_skips_planning_lock_write(self):
        calls = []
        original = mcp.command_result

        def fake_command_result(command, cwd):
            calls.append(command)
            return {"command": command, "cwd": cwd.as_posix(), "exit_code": 0, "stdout": "{\"ok\": true}", "stderr": ""}

        try:
            mcp.command_result = fake_command_result
            result = mcp.start_report({"goal": "plan Terraform", "root": ROOT.as_posix(), "format": "json"})
        finally:
            mcp.command_result = original

        self.assertEqual(result["result"], {"ok": True})
        self.assertIn("--no-planning-lock", calls[0])

    def test_guardrail_check_with_diff_uses_temp_diff_and_cleans_it(self):
        result = mcp.guardrail_check({"root": ROOT.as_posix(), "diff": "+\"left-pad\": \"1.0.0\"", "format": "json"})
        self.assertEqual(result["tool"], "guardrail_check")
        self.assertEqual(result["execution"]["exit_code"], 0)
        self.assertTrue(result["execution"]["read_only"])
        self.assertIn("tailtrail-guardrail-check", result["result"]["type"])

    def test_install_status_reads_manifest_without_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root / ".tailtrail-install.json"
            manifest.write_text(json.dumps({"surface": "core", "pack_dir": "."}), encoding="utf-8")
            before = manifest.read_text(encoding="utf-8")
            result = mcp.install_status({"root": root.as_posix()})
            after = manifest.read_text(encoding="utf-8")
        self.assertEqual(before, after)
        self.assertEqual(result["result"]["surface"], "core")

    def test_eval_scenario_list_is_read_only(self):
        result = mcp.eval_scenario_list({"format": "json"})

        self.assertEqual(result["tool"], "eval_scenario_list")
        self.assertEqual(result["execution"]["exit_code"], 0)
        self.assertTrue(result["execution"]["read_only"])
        self.assertEqual(result["result"]["type"], "evaluation-scenario-list")
        self.assertTrue(any(item["scenario_id"] == "validation-bug" for item in result["result"]["scenarios"]))

    def test_eval_scenario_report_is_read_only_and_does_not_write_result(self):
        result_path = ROOT / "benchmarks" / "evaluation" / "results" / "validation-bug-scenario-report.json"
        before_exists = result_path.exists()

        result = mcp.eval_scenario_report({"scenario": "validation-bug", "format": "json"})

        self.assertEqual(result["tool"], "eval_scenario_report")
        self.assertEqual(result["execution"]["exit_code"], 0)
        self.assertTrue(result["execution"]["read_only"])
        self.assertEqual(result["result"]["type"], "evaluation-scenario-result")
        self.assertEqual(result["result"]["scenario_id"], "validation-bug")
        self.assertEqual(result_path.exists(), before_exists)


if __name__ == "__main__":
    unittest.main()
