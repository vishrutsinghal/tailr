from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load():
    spec = importlib.util.spec_from_file_location("host_adapter_conformance_test", ROOT / "scripts" / "host-adapter-conformance.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


conformance = load()


def load_mcp():
    spec = importlib.util.spec_from_file_location("host_scope_mcp_test", ROOT / "scripts" / "mcp-server.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


mcp = load_mcp()


def host_proposal(packet: dict, host: str) -> dict:
    candidates = {row["path"]: row for row in packet["candidates"]}
    requirement = packet["requirements"][0]
    chosen, alternative = [row["path"] for row in packet["route"]["eligible_candidates"][:2]]
    inspection = next(row["path"] for row in packet["candidates"] if row["role"] == "literal-emitter")
    claims = [{
        "path": path,
        "candidate_id": candidates[path]["candidate_id"],
        "content_fingerprint": candidates[path]["content_fingerprint"],
        "claim_role": role,
        "evidence_edge_ids": candidates[path]["evidence_edge_ids"],
    } for path, role in ((chosen, "implementation-owner"), (inspection, "inspection"))]
    return {
        "schema_version": "2", "type": "tailtrail-navigator-host-scope-proposal", "host": host,
        "evidence_packet_fingerprint": packet["packet_fingerprint"],
        "scope_evidence_fingerprint": packet["scope_evidence_fingerprint"],
        "target_identity_fingerprint": packet["target_identity_fingerprint"],
        "goal_fingerprint": packet["goal_fingerprint"], "scope_state": "proposed-resolved",
        "authority": "evidence-refinement-only", "private_reasoning_excluded": True,
        "requirements": [{
            "requirement_id": requirement["requirement_id"],
            "statement_fingerprint": requirement["statement_fingerprint"],
            "implementation_owners": [chosen], "callers": [], "inspection_paths": [inspection],
            "proof_paths": [], "excluded_candidates": [row["path"] for row in requirement["excluded_candidates"]],
            "path_claims": claims,
            "preservation_boundaries": ["Preserve the unselected renderer."],
            "evidence_edge_ids": sorted({edge for claim in claims for edge in claim["evidence_edge_ids"]}),
            "confidence": "high", "decision_reasons": ["Request context selects one supported renderer."],
            "alternatives": [alternative], "uncertainties": [],
        }],
    }


class HostAdapterConformanceTests(unittest.TestCase):
    def test_scope_inspect_keeps_non_persisting_opt_out(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "src").mkdir()
            (root / "src" / "calculator.py").write_text(
                "def calculate_total(items):\n    return sum(items)\n", encoding="utf-8"
            )
            inspected = subprocess.run([
                sys.executable, (ROOT / "scripts" / "tailtrail.py").as_posix(),
                "navigator", "scope", "inspect", "--root", root.as_posix(),
                "--goal", "fix the calculate_total bug",
            ], cwd=ROOT, text=True, capture_output=True, check=False)
            self.assertEqual(inspected.returncode, 0, inspected.stderr)
            self.assertIn("host_packet", json.loads(inspected.stdout))
            self.assertFalse((root / ".tailtrail" / "code-graph-cache.json").exists())
            self.assertFalse((root / "tailtrail-meta" / "code-graph-cache.json").exists())

    def test_fsr5_cli_mcp_and_hosts_share_proposal_validation_truth(self) -> None:
        fixture = json.loads((ROOT / "tests" / "fixtures" / "navigator-scope" / "typescript-genuine-renderer-ambiguity.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for relative, body in fixture["repository_files"].items():
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(body, encoding="utf-8")
            inspected = subprocess.run([
                sys.executable, (ROOT / "scripts" / "tailtrail.py").as_posix(),
                "navigator", "scope", "inspect", "--root", root.as_posix(),
                "--goal", fixture["goal"],
            ], cwd=ROOT, text=True, capture_output=True, check=False)
            self.assertEqual(inspected.returncode, 0, inspected.stderr)
            packet = json.loads(inspected.stdout)["host_packet"]
            packet_path = root / "packet.json"
            proposal_path = root / "proposal.json"
            packet_path.write_text(json.dumps(packet), encoding="utf-8")
            normalized_fingerprints = set()
            for host in ("codex", "copilot", "claude"):
                proposal = host_proposal(packet, host)
                proposal_path.write_text(json.dumps(proposal), encoding="utf-8")
                cli = subprocess.run([
                    sys.executable, (ROOT / "scripts" / "tailtrail.py").as_posix(),
                    "navigator", "scope", "proposal-record", "--root", root.as_posix(),
                    "--packet", packet_path.as_posix(), "--proposal", proposal_path.as_posix(),
                    "--approved",
                ], cwd=ROOT, text=True, capture_output=True, check=False)
                self.assertEqual(cli.returncode, 0, cli.stderr + cli.stdout)
                cli_result = json.loads(cli.stdout)
                mcp_result = mcp.navigator_scope_proposal_record({
                    "root": root.as_posix(), "packet": packet, "proposal": proposal,
                    "approved": True,
                })["result"]
                self.assertEqual(cli_result, mcp_result)
                self.assertFalse(cli_result["run_created"])
                normalized_fingerprints.add(cli_result["normalized_scope_fingerprint"])
            self.assertFalse((root / ".tailtrail" / "runs").exists())
        self.assertEqual(len(normalized_fingerprints), 1)

    def test_generated_codex_copilot_and_claude_surfaces_match_matrix(self) -> None:
        matrix = conformance.load(ROOT)
        self.assertEqual(conformance.check(ROOT, matrix), [])
        self.assertEqual(matrix["precedence"], conformance.PRECEDENCE)
        self.assertEqual({item["id"] for item in matrix["conformance_scenarios"]}, conformance.REQUIRED_SCENARIOS)
        scope = conformance.load_scope_contract(ROOT)
        self.assertEqual({item["id"] for item in scope["scenarios"]}, conformance.REQUIRED_SCOPE_SCENARIOS)
        self.assertEqual(scope["contract_version"], "v2")
        reasoning = conformance.load_reasoning_contract(ROOT)
        self.assertEqual({item["id"] for item in reasoning["scenarios"]}, conformance.REQUIRED_REASONING_SCENARIOS)
        self.assertEqual(reasoning["contract_version"], "v1")
        requirement_routing = conformance.load_requirement_routing_contract(ROOT)
        self.assertEqual(
            {item["id"] for item in requirement_routing["scenarios"]},
            conformance.REQUIRED_REQUIREMENT_ROUTING_SCENARIOS,
        )
        self.assertEqual(requirement_routing["contract_version"], "v1")

    def test_composed_surface_preserves_precedence_and_closure_boundaries(self) -> None:
        matrix = conformance.load(ROOT)
        body = conformance.render(next(item for item in matrix["hosts"] if item["id"] == "copilot"), matrix)
        self.assertIn("1. Host safety", body)
        self.assertIn("2. User request", body)
        self.assertIn("3. Official AI-DLC stage rules", body)
        self.assertIn("4. TailTrail assurance rules", body)
        self.assertIn("`wait-ci` does not create learning", body)

    def test_all_three_hosts_render_the_same_workflow_mcp_boundary(self) -> None:
        matrix = conformance.load(ROOT)
        rendered = {host["id"]: conformance.render(host, matrix) for host in matrix["hosts"]}
        for body in rendered.values():
            self.assertIn("## Durable Workflow MCP boundary", body)
            self.assertIn("same canonical workflow ID", body)
            self.assertIn("cannot invent Planning Lock, AIDLC", body)
            self.assertIn("canonical workflow status or completion boundary", body)
            self.assertIn("CI continuation requires the exact approved CI policy", body)
            self.assertIn("never fixes source, changes", body)
            self.assertIn("Negative assurance returns categorical", body)
            self.assertIn("There is no background deletion", body)
            self.assertIn("Phase 11 release proof accepts only linked sanitized", body)
            self.assertIn("never retires `--no-workflow`", body)
            self.assertIn("Phase 12 enterprise continuation is optional", body)
            self.assertIn("current fencing token", body)
            self.assertIn("canonical local ownership, approvals", body)

    def test_all_three_hosts_share_natural_intent_and_authority_boundaries(self) -> None:
        matrix = conformance.load(ROOT)
        rendered = {host["id"]: conformance.render(host, matrix) for host in matrix["hosts"]}
        for host, body in rendered.items():
            self.assertIn("explicit TailTrail task in ordinary language", body)
            self.assertIn("let Navigator discover scope and controls", body)
            self.assertIn("request asking only for an approach routes to `guide`", body)
            self.assertIn("similar wording never approve", body)
            self.assertIn("MCP `intent_resolve` are read-only typed", body)
            source = next(item["source"] for item in matrix["hosts"] if item["id"] == host)
            adapter = (ROOT / source).read_text(encoding="utf-8")
            self.assertIn("Natural TailTrail requests", adapter)
            self.assertIn("intent_resolve", adapter)
            self.assertIn("similar wording never approve", adapter)

    def test_all_three_hosts_share_fsr5_reasoning_and_mcp_boundaries(self) -> None:
        matrix = conformance.load(ROOT)
        for host in matrix["hosts"]:
            body = conformance.render(host, matrix)
            self.assertIn("## Active-host scope reasoning boundary", body)
            self.assertIn("exact packet, scope decision, target, goal", body)
            self.assertIn("Unsupported, stale, or authority-expanding proposals create no run", body)
            self.assertIn("**supported-selection:** `accepted` / scope `resolved` / run created `false`", body)
            source = (ROOT / host["source"]).read_text(encoding="utf-8")
            self.assertIn("schema-v2 proposal", source)
            self.assertIn("stale hash", source)

    def test_all_three_hosts_share_requirement_before_scope_boundary(self) -> None:
        matrix = conformance.load(ROOT)
        for host in matrix["hosts"]:
            body = conformance.render(host, matrix)
            self.assertIn("## Requirement-before-scope host boundary", body)
            self.assertIn("MCP `requirement_route`", body)
            self.assertIn("target identity, then requirement sufficiency", body)
            source = (ROOT / host["source"]).read_text(encoding="utf-8")
            self.assertIn("Requirement-before-scope host boundary", source)
            self.assertIn(
                "scope availability cannot preempt requirement intake",
                " ".join(source.split()),
            )

    def test_phase9_requirement_routing_contract_fails_closed_on_mutation(self) -> None:
        original = json.loads(
            (ROOT / "adapters" / "requirement-routing-scenarios-v1.json").read_text(
                encoding="utf-8"
            )
        )
        mutations = []
        authority = json.loads(json.dumps(original))
        authority["scenarios"][0]["run_created"] = True
        mutations.append(authority)
        premature = json.loads(json.dumps(original))
        premature["scenarios"][1]["scope_question_allowed"] = True
        mutations.append(premature)
        expanded = json.loads(json.dumps(original))
        expanded["scenarios"][0]["approval"] = True
        mutations.append(expanded)

        for index, mutation in enumerate(mutations):
            with self.subTest(index=index), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                adapters = root / "adapters"
                schemas = root / "schemas"
                adapters.mkdir()
                schemas.mkdir()
                (adapters / "requirement-routing-scenarios-v1.json").write_text(
                    json.dumps(mutation), encoding="utf-8"
                )
                (schemas / "host-requirement-routing-conformance.schema.json").write_text(
                    "{}\n", encoding="utf-8"
                )
                with self.assertRaises(ValueError):
                    conformance.load_requirement_routing_contract(root)

    def test_cli_mcp_markdown_json_and_all_hosts_share_one_scope_fingerprint(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "src" / "service.py"
            source.parent.mkdir(parents=True)
            source.write_text("def deliver(value):\n    return value\n", encoding="utf-8")
            command = [
                sys.executable,
                (ROOT / "scripts" / "task-start.py").as_posix(),
                "update delivery service behavior",
                "--root", root.as_posix(),
                "--changed", "src/service.py",
                "--aidlc", "off",
                "--no-planning-lock",
                "--format", "json",
            ]
            cli = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
            self.assertEqual(cli.returncode, 0, cli.stderr + cli.stdout)
            cli_report = json.loads(cli.stdout)
            mcp_json = mcp.start_report({"goal": "update delivery service behavior", "root": root.as_posix(), "changed": ["src/service.py"], "format": "json"})
            mcp_markdown = mcp.start_report({"goal": "update delivery service behavior", "root": root.as_posix(), "changed": ["src/service.py"], "format": "markdown"})

        cli_contract = conformance.scope_projection("codex", cli_report)["contract"]
        host_contracts = [conformance.scope_projection(host, cli_report)["contract"] for host in ("codex", "copilot", "claude")]
        fingerprints = {
            cli_contract["normalized_decision_fingerprint"],
            mcp_json["scope_contract"]["normalized_decision_fingerprint"],
            mcp_markdown["scope_contract"]["normalized_decision_fingerprint"],
            *(row["normalized_decision_fingerprint"] for row in host_contracts),
        }
        self.assertEqual(len(fingerprints), 1)
        self.assertEqual(cli_contract["scope_gate"], "pass")
        self.assertTrue(cli_contract["execution_blocked"])
        self.assertTrue(mcp_markdown["result"].startswith("# TailTrail Start Report"))
        self.assertIn(cli_contract["decision_fingerprint"], mcp_markdown["result"])
        self.assertTrue(all(row["roles"] == cli_contract["roles"] for row in host_contracts))

    def test_adapters_contain_no_stale_post_lock_discovery_guidance(self) -> None:
        matrix = conformance.load(ROOT)
        for host in matrix["hosts"]:
            with self.subTest(host=host["id"]):
                source = (ROOT / host["source"]).read_text(encoding="utf-8")
                generated = (ROOT / host["generated"]).read_text(encoding="utf-8")
                self.assertIn("Scope evidence v2 host boundary", source)
                self.assertNotIn(conformance.STALE_SCOPE_TEXT, source.lower())
                self.assertNotIn(conformance.STALE_SCOPE_TEXT, generated.lower())


if __name__ == "__main__":
    unittest.main()
