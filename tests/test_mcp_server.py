import importlib.util
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from tests.proc_quote import quote


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
lock = load_script("mcp_execution_lock_test", "scripts/planning_lock.py")
anchor = load_script("mcp_execution_anchor_test", "scripts/change-intent-anchor.py")
reproduction = load_script("mcp_reproduction_guidance_test", "scripts/debug-reproduction.py")
requirement_discovery = load_script("mcp_requirement_discovery_test", "scripts/requirement_discovery.py")


def requirement_interpretation(goal: str, host: str = "codex") -> dict:
    return {
        "schema_version": "1",
        "type": "tailtrail-host-requirement-interpretation",
        "host": host,
        "goal": goal,
        "private_reasoning_excluded": True,
        "clauses": [{"clause_id": "C-01", "role": "outcome", "text": goal}],
        "requirements": [{
            "display_id": "REQ-01",
            "statement": goal,
            "kind": "change",
            "source_clause_ids": ["C-01"],
            "intent_terms": requirement_discovery.query_terms(goal),
            "quoted_literals": [],
            "intent_class": "general",
            "confidence": "medium",
        }],
        "material_questions": [],
    }


def scope_proposal(packet: dict, host: str) -> dict:
    candidates = {row["path"]: row for row in packet["candidates"]}
    requirement = packet["requirements"][0]
    chosen, alternative = [row["path"] for row in packet["route"]["eligible_candidates"][:2]]
    inspection = next(row["path"] for row in packet["candidates"] if row["role"] == "literal-emitter")
    material = [(chosen, "implementation-owner"), (inspection, "inspection")]
    claims = [{
        "path": path,
        "candidate_id": candidates[path]["candidate_id"],
        "content_fingerprint": candidates[path]["content_fingerprint"],
        "claim_role": role,
        "evidence_edge_ids": candidates[path]["evidence_edge_ids"],
    } for path, role in material]
    return {
        "schema_version": "2",
        "type": "tailtrail-navigator-host-scope-proposal",
        "host": host,
        "evidence_packet_fingerprint": packet["packet_fingerprint"],
        "scope_evidence_fingerprint": packet["scope_evidence_fingerprint"],
        "target_identity_fingerprint": packet["target_identity_fingerprint"],
        "goal_fingerprint": packet["goal_fingerprint"],
        "scope_state": "proposed-resolved",
        "authority": "evidence-refinement-only",
        "requirements": [{
            "requirement_id": requirement["requirement_id"],
            "statement_fingerprint": requirement["statement_fingerprint"],
            "implementation_owners": [chosen],
            "callers": [],
            "inspection_paths": [inspection],
            "proof_paths": [],
            "excluded_candidates": [row["path"] for row in requirement["excluded_candidates"]],
            "path_claims": claims,
            "preservation_boundaries": ["Preserve the unselected renderer."],
            "evidence_edge_ids": sorted({edge for claim in claims for edge in claim["evidence_edge_ids"]}),
            "confidence": "high",
            "decision_reasons": ["The request context selects one strongly evidenced renderer."],
            "alternatives": [alternative],
            "uncertainties": [],
        }],
        "private_reasoning_excluded": True,
    }


class McpServerTests(unittest.TestCase):
    def test_requirement_intake_tools_expose_read_and_approved_answer_boundaries(self) -> None:
        tools_by_name = {item["name"]: item for item in mcp.tool_list()}

        self.assertIn("requirement_intake_show", mcp.READ_ONLY_TOOLS)
        self.assertIn("requirement_intake_answer", mcp.CONTROLLED_TOOLS)
        self.assertIn("requirement_intake_show", tools_by_name)
        self.assertIn("requirement_intake_answer", tools_by_name)
        with self.assertRaisesRegex(ValueError, "approved: true"):
            mcp.requirement_intake_answer(
                {"intake_id": "intake-0123456789abcdef", "answers": {"DEC-01": "value"}}
            )

    def test_debug_preflight_is_read_only_and_bounded(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "src" / "report.py"
            proof = root / "tests" / "test_report.py"
            source.parent.mkdir(parents=True)
            proof.parent.mkdir(parents=True)
            source.write_text("def render_steps(steps):\n    return steps + steps\n", encoding="utf-8")
            proof.write_text("def test_render_steps_once():\n    assert True\n", encoding="utf-8")
            result = mcp.call_tool("debug_preflight", {
                "root": root.as_posix(),
                "goal": "debug repeated report steps",
                "host": "codex",
            })

        self.assertEqual(result["tool"], "debug_preflight")
        self.assertTrue(result["execution"]["read_only"])
        self.assertEqual(result["result"]["host_contract"]["max_reasoning_passes"], 1)
        self.assertLessEqual(result["result"]["metrics"]["evidence_files"], 6)

    def test_fsr5_mcp_validates_host_reasoning_then_creates_only_the_resolved_run(self) -> None:
        fixture = json.loads((ROOT / "tests" / "fixtures" / "navigator-scope" / "typescript-genuine-renderer-ambiguity.json").read_text(encoding="utf-8"))
        interpretation = requirement_interpretation(fixture["goal"])
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for relative, body in fixture["repository_files"].items():
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(body, encoding="utf-8")
            first = mcp.tailtrail_start({
                "goal": fixture["goal"], "root": root.as_posix(), "host": "codex",
                "requirement_interpretation": interpretation,
                "run_id": "fsr5-mcp", "format": "json", "approved": True,
            })
            packet = first["host_reasoning_packet"]
            self.assertFalse(first["run_created"])
            self.assertEqual(first["requirement_route"]["state"], "eligible")
            self.assertTrue(first["requirement_route"]["scope_question_allowed"])
            self.assertEqual(first["scope_contract"]["state"], "ambiguous")
            self.assertEqual(packet["route"]["state"], "requested")
            proposal = scope_proposal(packet, "codex")
            invented = copy.deepcopy(proposal)
            invented["requirements"][0]["implementation_owners"] = ["src/pages/InventedPage.tsx"]
            invented["requirements"][0]["path_claims"][0]["path"] = "src/pages/InventedPage.tsx"
            denied = mcp.navigator_scope_proposal_record({
                "root": root.as_posix(), "packet": packet, "proposal": invented,
                "approved": True,
            })
            self.assertEqual(denied["result"]["status"], "rejected")
            denied_start = mcp.tailtrail_start({
                "goal": fixture["goal"], "root": root.as_posix(), "host": "codex",
                "requirement_interpretation": interpretation,
                "host_scope_proposal": invented, "run_id": "fsr5-mcp",
                "format": "json", "approved": True,
            })
            self.assertFalse(denied_start["run_created"])
            self.assertEqual(denied_start["scope_contract"]["state"], "ambiguous")
            validation = mcp.navigator_scope_proposal_record({
                "root": root.as_posix(), "packet": packet, "proposal": proposal,
                "approved": True,
            })
            self.assertEqual(validation["result"]["status"], "accepted")
            self.assertFalse(validation["run_created"])
            self.assertFalse((root / ".tailtrail" / "runs" / "fsr5-mcp").exists())
            second = mcp.tailtrail_start({
                "goal": fixture["goal"], "root": root.as_posix(), "host": "codex",
                "requirement_interpretation": interpretation,
                "host_scope_proposal": proposal, "run_id": "fsr5-mcp",
                "format": "json", "approved": True,
            })

        self.assertTrue(second["run_created"])
        self.assertEqual(second["scope_contract"]["state"], "resolved")
        self.assertEqual(second["scope_contract"]["decision_reason"], "host-evidence-supported-owner-resolved")
        self.assertIsNone(second["host_reasoning_packet"])

    def test_phase8_mcp_defers_scope_for_open_requirement_intake(self) -> None:
        goal = (
            "Create the dapdes-act/dev/auditlogging/apigee-client-credentials "
            "resource because it does not exist in AWS and is needed to store OEM credentials."
        )
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            response = mcp.tailtrail_start({
                "goal": goal,
                "root": root.as_posix(),
                "aidlc": "lite",
                "format": "json",
                "approved": True,
            })

        self.assertFalse(response["run_created"])
        self.assertIsNone(response["scope_contract"])
        self.assertIsNone(response["host_reasoning_packet"])
        self.assertEqual(response["requirement_route"]["state"], "deferred")
        self.assertFalse(response["requirement_route"]["scope_question_allowed"])
        self.assertEqual(response["requirement_route"]["route"], "lite-questions")

    def test_phase9_mcp_exposes_host_interpretation_before_scope(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            response = mcp.tailtrail_start({
                "goal": "Update the service behavior",
                "root": root.as_posix(),
                "host": "codex",
                "format": "json",
                "approved": True,
            })

        self.assertFalse(response["run_created"])
        self.assertIsNone(response["scope_contract"])
        self.assertIsNone(response["host_reasoning_packet"])
        self.assertEqual(response["requirement_route"]["state"], "deferred")
        self.assertEqual(response["requirement_route"]["route"], "host-interpretation")
        self.assertFalse(response["requirement_route"]["scope_question_allowed"])

    def test_phase9_mcp_rejects_deferred_route_authority_contradictions(self) -> None:
        deferred = {
            "scope_question_precondition": {
                "state": "deferred",
                "requirements_state": "clarification-required",
                "open_material_decision_ids": ["MAT-01"],
                "scope_question_allowed": False,
                "reason_code": "requirements-must-be-resolved-before-scope-question",
            },
            "recommended_route": "lite-questions",
        }
        contradictions = (
            {"planning_lock": {"run_id": "must-not-exist"}},
            {"scope_host_packet": {"route": {"state": "requested"}}},
        )
        for contradiction in contradictions:
            with self.subTest(contradiction=contradiction):
                with self.assertRaisesRegex(
                    ValueError, "requirement-before-scope conformance violation"
                ):
                    mcp.requirement_scope_transport({**deferred, **contradiction})

    def test_phase9_mcp_rejects_scope_state_without_requirement_route(self) -> None:
        with self.assertRaisesRegex(ValueError, "typed requirement route"):
            mcp.requirement_scope_transport(
                {"planning_lock": {"run_id": "must-not-exist"}}
            )

    def test_debug_reproduction_mcp_returns_canonical_next_actions(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            reproduction.L.init_run(root, "mcp-debug-guidance", "debug guidance")
            response = mcp.call_tool("debug_reproduction_draft", {
                "root": root.as_posix(),
                "run_id": "mcp-debug-guidance",
                "approved": True,
                "contract": {
                    "domain": "code",
                    "trigger": "wrapped prose becomes two requirements",
                    "expected": "one requirement",
                    "actual": "two requirements",
                    "reproduction_method": "run the focused parser fixture",
                    "safety_boundary": "local fixture only",
                },
            })

            guidance = response["next_actions"]
            self.assertEqual(guidance["state"], "reproduction-approval-required")
            self.assertEqual(guidance["run_id"], "mcp-debug-guidance")
            self.assertEqual(guidance["revision"], 1)
            action_ids = {item["id"] for item in guidance["actions"]}
            self.assertTrue({"approve-reproduction", "revise-reproduction", "explain-reproduction", "show-status", "stop-tailtrail", "resume-tailtrail"}.issubset(action_ids))
            shown = mcp.call_tool("debug_reproduction_show", {
                "root": root.as_posix(), "run_id": "mcp-debug-guidance"
            })
            self.assertEqual(shown["next_actions"], guidance)
            attempt = mcp.call_tool("debug_reproduction_attempt_show", {
                "root": root.as_posix(), "run_id": "mcp-debug-guidance"
            })
            self.assertEqual(attempt["result"]["state"], "not-run")
            self.assertEqual(attempt["next_actions"]["state"], "not-run")

    def test_debug_orientation_surface_is_read_only_or_explicitly_approval_gated(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaisesRegex(ValueError, "no debug orientation"):
                mcp.call_tool("debug_orientation_show", {"root": root.as_posix(), "run_id": "missing"})
            self.assertFalse((root / ".tailtrail").exists())
            with self.assertRaisesRegex(ValueError, "requires approved: true"):
                mcp.call_tool("debug_orientation_create", {"root": root.as_posix(), "run_id": "missing", "approved": False})

    def test_complete_debug_lifecycle_tools_are_classified_and_approval_gated(self) -> None:
        read_only = {"debug_intake_show", "debug_reproduction_show", "debug_reproduction_attempt_show", "debug_orientation_show",
                     "debug_hypothesis_ledger_show", "debug_correction_show", "debug_governance_show",
                     "debug_harness_convergence_show", "debug_completion_report_show",
                     "workflow_current", "workflow_resume", "workflow_replay", "completion_report_show"}
        read_only.update({"debug_evaluation_report", "debug_release_gate"})
        controlled = {"debug_start", "debug_reproduction_draft", "debug_reproduction_revise", "debug_reproduction_reopen",
                      "debug_reproduction_approve", "debug_reproduction_attempt_record", "debug_orientation_create", "debug_hypothesis_add",
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

    def test_missing_debug_lifecycle_artifacts_return_structured_read_only_states(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for tool in ("debug_correction_show", "debug_governance_show", "debug_completion_report_show"):
                result = mcp.call_tool(tool, {"root": root.as_posix(), "run_id": "missing"})["result"]
                self.assertEqual(result["status"], "not-created", tool)
                self.assertEqual(result["lifecycle_classification"], "not-yet-expected", tool)
            convergence = mcp.call_tool("debug_harness_convergence_show", {"root": root.as_posix(), "run_id": "missing"})["result"]
            self.assertEqual(convergence["status"], "not-created")
            self.assertEqual(convergence["selected"][0]["control"], "Requirement Completion Harness")
            self.assertFalse((root / ".tailtrail").exists())

    def test_tool_list_has_read_only_and_one_approval_gated_allowlist(self):
        self.assertTrue({"navigator_plan", "intent_resolve", "ledger_state", "anchor_show", "git_readiness", "planning_lock_show", "planning_decision_show", "planning_investigation_show", "planning_revision_show", "planning_authority_show", "planning_question_context_show", "aidlc_official_status", "aidlc_official_bridge_show", "aidlc_official_state_show", "aidlc_official_sanitize_validate", "aidlc_official_session_status", "host_conformance_report", "execution_evidence_show"}.issubset(set(mcp.READ_ONLY_TOOLS)))

    def test_intent_resolve_is_read_only_and_never_grants_authority(self):
        result = mcp.call_tool(
            "intent_resolve",
            {"text": "Use TailTrail to reject zero quantities but preserve positive quantities."},
        )
        self.assertTrue(result["execution"]["read_only"])
        self.assertEqual(result["result"]["action"], "start")
        self.assertEqual(result["result"]["authority"]["classification"], "planning-only")
        self.assertFalse(result["result"]["authority"]["approval_inferred"])
        self.assertFalse(result["result"]["authority"]["execution_granted"])

    def test_intent_resolve_fails_closed_for_vague_or_ambiguous_approval(self):
        vague = mcp.call_tool(
            "intent_resolve",
            {"text": "looks good", "active_state": "awaiting-approval"},
        )["result"]
        self.assertEqual(vague["action"], "clarify")
        ambiguous = mcp.call_tool(
            "intent_resolve",
            {"text": "approve", "active_state": "ambiguous"},
        )["result"]
        self.assertEqual(ambiguous["reason_codes"], ["exact-run-id-required"])

    def test_real_evaluation_portfolio_report_is_read_only_and_honest(self):
        with tempfile.TemporaryDirectory() as temp:
            report = mcp.call_tool("real_evaluation_portfolio_report", {"root": temp})
        self.assertEqual("protocol-ready", report["status"])
        self.assertEqual("no-performance-claim", report["claim_status"])
        self.assertEqual(18, report["task_count"])

    def test_adoption_validation_report_is_read_only_and_honest(self):
        with tempfile.TemporaryDirectory() as temp:
            report = mcp.call_tool("adoption_validation_report", {"root": temp})
        self.assertEqual("protocol-ready", report["status"])
        self.assertEqual("no-adoption-claim", report["claim_status"])
        self.assertFalse(Path(temp, ".tailtrail").exists())

    def test_enterprise_conformance_report_is_static_and_read_only(self):
        report = mcp.call_tool("enterprise_conformance_report", {"root": str(ROOT)})
        self.assertEqual("passed", report["status"])
        self.assertEqual([], report["probes"])
        self.assertFalse(report["release_qualification"]["qualified"])
        self.assertTrue({"harness_control_check", "source_patch_apply", "planning_lock_start", "planning_lock_approve", "tailtrail_start", "navigator_scope_proposal_record", "execution_evidence_record", "planning_investigate", "planning_revision_propose", "planning_revision_approve", "planning_aidlc_standard_propose", "planning_aidlc_standard_approve", "spec_kit_import", "spec_kit_amendment_propose", "spec_kit_anchor_approve", "spec_kit_convergence_record", "spec_kit_ci_ingest"}.issubset(set(mcp.CONTROLLED_TOOLS)))
        self.assertEqual(set(mcp.HANDLERS), set((*mcp.READ_ONLY_TOOLS, *mcp.CONTROLLED_TOOLS)))
        self.assertEqual(mcp.ensure_safe_tools(), [])

    def test_tool_list_is_projected_from_registry(self):
        projection = mcp.load_registry().mcp_projection(mcp.load_registry().load_registry())
        definitions = mcp.tool_definitions()

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
        for name in ("navigator_plan", "start_report", "tailtrail_start"):
            self.assertIn("outputSchema", definitions[name])
            self.assertIn("scope_contract", definitions[name]["outputSchema"]["properties"])
            route_schema = definitions[name]["outputSchema"]["properties"]["requirement_route"]
            self.assertIn("requirement_route", definitions[name]["outputSchema"]["required"])
            self.assertFalse(route_schema["additionalProperties"])
            self.assertEqual(
                route_schema["properties"]["scope_question_allowed"]["type"],
                "boolean",
            )
            self.assertFalse(definitions[name]["annotations"]["destructiveHint"])
        self.assertFalse(projected["navigator_scope_proposal_record"]["read_only"])
        self.assertTrue(projected["navigator_scope_proposal_record"]["requires_approval"])
        self.assertTrue(projected["planning_investigation_show"]["read_only"])
        self.assertFalse(projected["planning_investigate"]["read_only"])
        self.assertTrue(projected["planning_investigate"]["requires_approval"])
        self.assertTrue(projected["planning_revision_show"]["read_only"])
        self.assertFalse(projected["planning_revision_propose"]["read_only"])
        self.assertIn("supersede_pending", definitions["planning_revision_propose"]["inputSchema"]["properties"])
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
            "tool registry order mismatch at index 26: expected `planning_lock_show`, got `planning_decision_show`",
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
        with self.assertRaisesRegex(ValueError, "approved: true"):
            mcp.execution_evidence_run({"run_id": "demo", "approved": False})

    def test_navigator_scope_proposal_record_requires_explicit_approval(self):
        with self.assertRaisesRegex(ValueError, "approved: true"):
            mcp.navigator_scope_proposal_record({
                "root": ROOT.as_posix(),
                "evidence": {},
                "proposal": {},
                "approved": False,
            })

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

    def test_execution_evidence_mcp_runs_only_approved_proof_and_returns_exit_code(self):
        command = f"{quote(sys.executable)} -c {quote('print(\"mcp proof\")')}"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "src" / "orders.py").write_text("value = 1\n", encoding="utf-8")
            lock.create(root, "validate order", "managed-run")
            proposal = root / "proposal.json"
            proposal.write_text(json.dumps({"requirements": [{
                "statement": "Reject an invalid order.", "acceptance_criteria": ["invalid orders reject"],
                "preserve_rules": [], "likely_paths": ["src/orders.py"], "evidence_plan": ["unit"],
                "validation_contract": {"state": "required", "tiers": ["unit"], "commands": [command]},
            }]}), encoding="utf-8")
            anchor.draft(root, "managed-run", proposal)
            uid = anchor.approve(root, "managed-run")["requirements"][0]["requirement_uid"]
            lock.approve(root, "managed-run", True)
            response = mcp.execution_evidence_run({
                "root": root.as_posix(), "run_id": "managed-run", "requirement_uids": [uid],
                "tiers": ["unit"], "changed": ["src/orders.py"], "command": command,
                "command_label": "order proof", "timeout_seconds": 30, "approved": True,
            })

        self.assertEqual(response["result"]["outcome"], "pass")
        self.assertEqual(response["execution"]["exit_code"], 0)
        self.assertTrue(response["execution"]["command_executed"])

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

    def _patch_gate_repo(self, stage):
        import os

        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.email", "t@t.t"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.name", "t"], cwd=root, check=True)
        (root / "src").mkdir()
        (root / "src" / "app.py").write_text("print('hello')", encoding="utf-8")
        (root / "tests").mkdir()
        lock_dir = root / ".tailtrail" / "runs" / "patch-gate-1" / "planning"
        lock_dir.mkdir(parents=True)
        (lock_dir / "lock-v1.json").write_text(json.dumps({
            "schema_version": "2", "run_id": "patch-gate-1", "status": "approved",
            "pipeline": {"active_stage": stage, "completed_stages": [],
                         "stage_sequence": ["IMPLEMENTATION", "TESTING", "INFRA"]},
        }), encoding="utf-8")
        os.environ.pop("TAILTRAIL_ACTIVE_RUN_ID", None)
        self.addCleanup(os.environ.pop, "TAILTRAIL_ACTIVE_RUN_ID", None)
        original = mcp.require_approved_planning_lock
        mcp.require_approved_planning_lock = lambda *a, **k: None
        self.addCleanup(setattr, mcp, "require_approved_planning_lock", original)
        return root

    @staticmethod
    def _new_file_patch(rel):
        body = "def test_x(): pass\n"
        return (
            f"diff --git a/{rel} b/{rel}\nnew file mode 100644\n"
            f"--- /dev/null\n+++ b/{rel}\n@@ -0,0 +1 @@\n+{body}"
        )

    def test_source_patch_blocked_by_active_badge(self):
        root = self._patch_gate_repo("TESTING")
        with self.assertRaisesRegex(ValueError, "blocked by active TESTING badge"):
            mcp.source_patch_apply({
                "root": root.as_posix(), "run_id": "patch-gate-1",
                "approved": True, "patch": self._new_file_patch("src/app2.py"),
            })
        self.assertFalse((root / "src" / "app2.py").exists())

    def test_source_patch_allowed_in_badge(self):
        root = self._patch_gate_repo("TESTING")
        result = mcp.source_patch_apply({
            "root": root.as_posix(), "run_id": "patch-gate-1",
            "approved": True, "patch": self._new_file_patch("tests/test_x.py"),
        })
        self.assertTrue(result["result"]["applied"])
        self.assertTrue((root / "tests" / "test_x.py").exists())

    def test_source_patch_skips_gate_without_active_stage(self):
        root = self._patch_gate_repo("PENDING")
        result = mcp.source_patch_apply({
            "root": root.as_posix(), "run_id": "patch-gate-1",
            "approved": True, "patch": self._new_file_patch("src/app2.py"),
        })
        self.assertTrue(result["result"]["applied"])

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
            result = mcp.tailtrail_start({"goal": "plan task 1 and task 2 hands-free", "root": ROOT.as_posix(), "run_id": "program-1", "changed": ["src/a.py"], "graph": "refresh", "approved": True})
        finally:
            mcp.command_result = original

        self.assertTrue(result["result"].startswith("# TailTrail Start Plan"))
        self.assertTrue(result["execution"]["local_metadata_only"])
        self.assertTrue(result["execution"]["execution_blocked"])
        self.assertIn("task-start.py", calls[0][1])
        self.assertIn("--planning-run-id", calls[0])
        self.assertEqual(calls[0][calls[0].index("--graph") + 1], "refresh")
        self.assertEqual(calls[0][calls[0].index("--format") + 1], "json")
        self.assertNotIn("--no-planning-lock", calls[0])
        self.assertIsNone(result["scope_contract"])

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

    def test_atomic_tailtrail_start_passes_debug_diagnosis_via_stdin(self):
        calls = []
        original = mcp.command_result
        diagnosis = {"schema_version": "1", "type": "tailtrail-host-debug-diagnosis"}

        def fake_command_result(command, cwd, *, stdin_data=None):
            calls.append((command, stdin_data))
            return {"command": command, "cwd": cwd.as_posix(), "exit_code": 0, "stdout": "{}", "stderr": ""}

        try:
            mcp.command_result = fake_command_result
            mcp.tailtrail_start({
                "goal": "debug repeated report steps",
                "root": ROOT.as_posix(),
                "host": "codex",
                "workflow": "debug",
                "debug_diagnosis": diagnosis,
                "format": "json",
                "approved": True,
            })
        finally:
            mcp.command_result = original

        self.assertIn("--debug-diagnosis-stdin", calls[0][0])
        self.assertNotIn("--debug-diagnosis", calls[0][0])
        self.assertEqual(json.loads(calls[0][1]), diagnosis)

    def test_atomic_tailtrail_start_forwards_typed_host_requirement_interpretation(self):
        calls = []
        original = mcp.command_result
        goal = "A warning is visible. Remove it."
        proposal = {
            "schema_version": "1",
            "type": "tailtrail-host-requirement-interpretation",
            "host": "codex",
            "goal": goal,
            "private_reasoning_excluded": True,
            "clauses": [{"clause_id": "C-01", "role": "outcome", "text": "Remove it."}],
            "requirements": [{
                "display_id": "REQ-01", "statement": "Remove the visible warning.",
                "source_clause_ids": ["C-01"], "intent_terms": ["remove", "warning"],
            }],
            "material_questions": [],
        }

        def fake_command_result(command, cwd):
            calls.append(command)
            return {"command": command, "cwd": cwd.as_posix(), "exit_code": 0, "stdout": "{}", "stderr": ""}

        try:
            mcp.command_result = fake_command_result
            mcp.tailtrail_start({
                "goal": goal,
                "root": ROOT.as_posix(),
                "requirement_artifacts": ["/tmp/requirements.md"],
                "requirement_interpretation": proposal,
                "format": "json",
                "approved": True,
            })
        finally:
            mcp.command_result = original

        self.assertIn("--requirement-interpretation", calls[0])
        self.assertEqual(
            calls[0][calls[0].index("--requirement-artifact") + 1],
            "/tmp/requirements.md",
        )
        forwarded = json.loads(calls[0][calls[0].index("--requirement-interpretation") + 1])
        self.assertEqual(forwarded, proposal)

    def test_atomic_tailtrail_start_forwards_required_planning_artifacts(self):
        calls = []
        original = mcp.command_result

        def fake_command_result(command, cwd):
            calls.append(command)
            return {"command": command, "cwd": cwd.as_posix(), "exit_code": 2, "stdout": "{}", "stderr": ""}

        try:
            mcp.command_result = fake_command_result
            mcp.tailtrail_start({
                "goal": "Add tests from the referenced specification.",
                "root": ROOT.as_posix(),
                "host": "codex",
                "requirement_artifacts": ["/tmp/requirements.md", "/tmp/contracts.txt"],
                "format": "json",
                "approved": True,
            })
        finally:
            mcp.command_result = original

        artifact_positions = [
            index for index, value in enumerate(calls[0])
            if value == "--requirement-artifact"
        ]
        self.assertEqual(
            [calls[0][index + 1] for index in artifact_positions],
            ["/tmp/requirements.md", "/tmp/contracts.txt"],
        )

    def test_atomic_tailtrail_start_forwards_visual_artifacts_and_observations(self):
        calls = []
        original = mcp.command_result
        observations = {
            "locator": "/tmp/mockup.png",
            "summary": "ECG section with dropdown and table.",
            "open_questions": ["What are the exact headers?"],
            "complete": False,
        }

        def fake_command_result(command, cwd):
            calls.append(command)
            return {"command": command, "cwd": cwd.as_posix(), "exit_code": 2, "stdout": "{}", "stderr": ""}

        try:
            mcp.command_result = fake_command_result
            mcp.tailtrail_start({
                "goal": "Add a table shown in the attached image.",
                "root": ROOT.as_posix(),
                "host": "codex",
                "visual_artifacts": ["/tmp/mockup.png"],
                "visual_observations": observations,
                "format": "json",
                "approved": True,
            })
        finally:
            mcp.command_result = original

        self.assertIn("--visual-artifact", calls[0])
        self.assertEqual(
            calls[0][calls[0].index("--visual-artifact") + 1],
            "/tmp/mockup.png",
        )
        forwarded = json.loads(calls[0][calls[0].index("--visual-observations") + 1])
        self.assertEqual(forwarded, observations)

    def test_tailtrail_start_renders_requirement_clarification_without_navigator(self):
        original = mcp.command_result
        clarification = {
            "type": "tailtrail-requirement-clarification",
            "boundary": "No graph lifecycle or Planning Lock was created.",
            "intake_id": "intake-0123456789abcdef",
            "recommended_route": "lite-questions",
            "material_questions": ["Which source supplies the account list?"],
            "requirement_evidence": {},
            "continuation": {"prompt": "Answer the material question."},
            "scope_question_precondition": {"state": "deferred"},
        }

        def fake_command_result(command, cwd):
            return {"command": command, "cwd": cwd.as_posix(), "exit_code": 0,
                    "stdout": json.dumps(clarification), "stderr": ""}

        try:
            mcp.command_result = fake_command_result
            result = mcp.tailtrail_start({
                "goal": "Add the ECG configuration view.",
                "root": ROOT.as_posix(),
                "format": "markdown",
                "approved": True,
            })
        finally:
            mcp.command_result = original

        self.assertIn("# TailTrail Requirement Clarification", result["result"])
        self.assertIn("Which source supplies the account list?", result["result"])

    def test_atomic_tailtrail_start_normalizes_host_visual_attachment(self):
        calls = []
        original = mcp.command_result

        def fake_command_result(command, cwd):
            calls.append(command)
            return {"command": command, "cwd": cwd.as_posix(), "exit_code": 2, "stdout": "{}", "stderr": ""}

        with tempfile.TemporaryDirectory() as temp:
            image = Path(temp) / "mockup.png"
            image.write_bytes(bytes.fromhex("89504e470d0a1a0a") + b"\x00" * 64)
            try:
                mcp.command_result = fake_command_result
                mcp.tailtrail_start({
                    "goal": "Add the section shown in the attached image.",
                    "root": ROOT.as_posix(),
                    "host": "codex",
                    "visual_attachments": [{
                        "attachment_id": "chat-image-1",
                        "local_path": image.as_posix(),
                        "media_type": "image/png",
                    }],
                    "visual_observations": {
                        "locator": "chat-image-1",
                        "summary": "ECG section with a dropdown and table.",
                        "open_questions": ["What are the exact table headers?"],
                        "complete": False,
                    },
                    "format": "json",
                    "approved": True,
                })
            finally:
                mcp.command_result = original

        staged_path = calls[0][calls[0].index("--visual-artifact") + 1]
        self.assertNotEqual(staged_path, image.as_posix())
        self.assertFalse(Path(staged_path).exists())
        forwarded = json.loads(calls[0][calls[0].index("--visual-observations") + 1])
        self.assertEqual(forwarded["locator"], staged_path)

    def test_atomic_tailtrail_start_forwards_answered_requirement_intake(self):
        calls = []
        original = mcp.command_result

        def fake_command_result(command, cwd):
            calls.append(command)
            return {"command": command, "cwd": cwd.as_posix(), "exit_code": 0, "stdout": "{}", "stderr": ""}

        try:
            mcp.command_result = fake_command_result
            mcp.tailtrail_start({
                "goal": "Create the credential resource.",
                "root": ROOT.as_posix(),
                "host": "codex",
                "requirement_intake_id": "intake-0123456789abcdef",
                "aidlc": "standard",
                "format": "json",
                "approved": True,
            })
        finally:
            mcp.command_result = original

        self.assertIn("--requirement-intake-id", calls[0])
        self.assertEqual(
            calls[0][calls[0].index("--requirement-intake-id") + 1],
            "intake-0123456789abcdef",
        )

    def test_atomic_tailtrail_start_uses_the_shared_multiline_requirement_frame(self):
        goal = "Add delivery-address validation without breaking valid\r\naddresses."
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root / "src" / "address_validation.py"
            target.parent.mkdir(parents=True)
            target.write_text("def validate_address(value):\n    return bool(value)\n", encoding="utf-8")

            result = mcp.tailtrail_start({
                "goal": goal,
                "root": root.as_posix(),
                "changed": ["src/address_validation.py"],
                "run_id": "mcp-ns1-frame",
                "aidlc": "off",
                "format": "markdown",
                "approved": True,
            })
            saved = lock.active_start_report(root, "mcp-ns1-frame")

        self.assertEqual(result["execution"]["exit_code"], 0)
        self.assertIn("Add delivery-address validation without breaking valid addresses.", result["result"])
        self.assertNotIn("**REQ-02:** Addresses.", result["result"])
        self.assertEqual(saved["goal"], goal)
        decision = saved["report"]["navigator"]["scope_evidence"]["decision_fingerprint"]
        self.assertEqual(result["scope_contract"]["decision_fingerprint"], decision)
        self.assertEqual(result["scope_contract"]["normalized_decision_fingerprint"], decision)
        self.assertEqual(result["execution"]["transport_format"], "json")
        self.assertEqual(result["execution"]["response_format"], "markdown")
        self.assertEqual(
            [row["statement"] for row in saved["report"]["navigator"]["requirement_matrix"]],
            ["Add delivery-address validation without breaking valid addresses."],
        )

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
