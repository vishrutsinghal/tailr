from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
if (ROOT / "scripts").as_posix() not in sys.path:
    sys.path.insert(0, (ROOT / "scripts").as_posix())


def load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


task_start = load("debug_start_planning_task_start", "scripts/task-start.py")
reproduction = load("debug_start_planning_reproduction", "scripts/debug-reproduction.py")
debug_diagnosis = load("debug_start_planning_host_diagnosis", "scripts/debug-host-diagnosis.py")
from workflow_runtime import approvals as workflow_approvals
from workflow_runtime import freshness as workflow_freshness
from workflow_runtime import resume as workflow_resume
from workflow_runtime import state as workflow_state


class DebugStartPlanningTests(unittest.TestCase):
    def build(self, root: Path, **kwargs):
        return task_start.build_report(
            "payments are sometimes charged twice after timeout",
            root,
            kwargs.pop("changed", []),
            "python3 scripts/tailtrail.py",
            workflow_override=kwargs.pop("workflow_override", None),
            has_error_artifact=kwargs.pop("has_error_artifact", False),
            has_reproduction_command=kwargs.pop("has_reproduction_command", False),
            debug_diagnosis=kwargs.pop("debug_diagnosis", None),
        )

    def diagnosis(self, root: Path) -> dict:
        goal = "payments are sometimes charged twice after timeout"
        source = root / "src" / "payments.py"
        proof = root / "tests" / "test_payments.py"
        source.parent.mkdir(parents=True, exist_ok=True)
        proof.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("def charge(order):\n    return submit(order)\n", encoding="utf-8")
        proof.write_text("def test_timeout_charge_once():\n    assert True\n", encoding="utf-8")
        source_hash = "sha256:" + __import__("hashlib").sha256(source.read_bytes()).hexdigest()
        proof_hash = "sha256:" + __import__("hashlib").sha256(proof.read_bytes()).hexdigest()
        raw = {
            "schema_version": "1",
            "type": "tailtrail-host-debug-diagnosis",
            "host": "codex",
            "root": root.resolve().as_posix(),
            "goal_fingerprint": debug_diagnosis.goal_fingerprint(goal),
            "authority": "advisory-only",
            "checks_performed": ["source-read", "test-read"],
            "evidence": [
                {"id": "E-OWNER", "path": "src/payments.py", "sha256": source_hash, "role": "implementation-owner", "behavior_roles": ["data-producer"], "kind": "source-read", "symbols": ["charge"], "start_line": 1, "end_line": 2, "finding": "Defines the charge submission boundary named by the symptom."},
                {"id": "E-PROOF", "path": "tests/test_payments.py", "sha256": proof_hash, "role": "proof", "behavior_roles": ["proof"], "kind": "test-read", "symbols": ["test_timeout_charge_once"], "start_line": 1, "end_line": 2, "finding": "Contains the focused timeout behavior test."},
            ],
            "behavior_trace": {
                "direction": "observed-output-to-producer",
                "state": "partial",
                "nodes": [
                    {"id": "TRACE-OWNER", "role": "data-producer", "path": "src/payments.py", "symbols": ["charge"], "evidence_id": "E-OWNER"},
                    {"id": "TRACE-PROOF", "role": "proof", "path": "tests/test_payments.py", "symbols": ["test_timeout_charge_once"], "evidence_id": "E-PROOF"},
                ],
                "edges": [{"id": "TRACE-EDGE", "from": "TRACE-PROOF", "to": "TRACE-OWNER", "relationship": "exercises"}],
                "divergence_candidates": ["TRACE-OWNER"],
                "boundary": "The producer is a hypothesis boundary until reproduction and an experiment prove the cause.",
            },
            "findings": [
                {"id": "D-OBS", "statement": "The charge boundary and a focused timeout proof both exist.", "state": "observation", "confidence": "high", "evidence_ids": ["E-OWNER", "E-PROOF"]},
                {"id": "D-HYP", "statement": "The timeout retry may submit the same order twice.", "state": "hypothesis", "confidence": "medium", "evidence_ids": ["E-OWNER"]},
            ],
            "test_cases": [
                {"id": "TEST-01", "tier": "reproduction", "state": "existing", "statement": "The timeout path demonstrates two submissions before correction.", "path": "tests/test_payments.py", "command": "python3 -m unittest tests.test_payments"},
                {"id": "TEST-02", "tier": "regression", "state": "existing", "statement": "The same order is submitted exactly once after correction.", "path": "tests/test_payments.py", "command": "python3 -m unittest tests.test_payments"},
            ],
            "reproduction": {"status": "candidate-identified", "observation": "The reported timeout path charges twice.", "expected": "The order is charged once.", "artifact_refs": [], "proposed_steps": ["Run the focused timeout test after exact reproduction approval."], "candidate_command": "python3 -m unittest tests.test_payments"},
            "unknowns": ["Whether the retry or submission boundary creates the duplicate effect."],
            "preflight": {
                "packet_fingerprint": "sha256:" + "1" * 64,
                "elapsed_ms": 120,
                "files_considered": 20,
                "files_read": 4,
                "bytes_read": 1200,
                "estimated_tokens": 220,
                "termination_reason": "inventory-exhausted",
                "host_reasoning_passes": 1,
                "reuse_key": "sha256:" + "2" * 64,
            },
            "requirement_refinement": {
                "statement": "Prevent duplicate payment submission after a timeout.",
                "acceptance_criteria": ["The timeout path submits one payment."],
                "preserve_rules": ["Successful first-attempt payments remain unchanged."],
                "evidence_ids": ["D-OBS"],
            },
            "proposal": {
                "route": "prepare-reproduction",
                "requirement_id": "REQ-DEBUG-01",
                "owner_evidence_ids": ["E-OWNER"],
                "proof_evidence_ids": ["E-PROOF"],
                "trace_node_ids": ["TRACE-OWNER", "TRACE-PROOF"],
                "finding_ids": ["D-OBS", "D-HYP"],
                "test_case_ids": ["TEST-01", "TEST-02"],
                "boundary": "advisory-only; no approval or execution authority",
            },
        }
        return debug_diagnosis.validate(root, goal, raw, "codex")

    def test_debug_start_builds_planning_payload_without_debug_intake(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = self.build(root)

            self.assertEqual(report["debug_plan"]["workflow_type"], "debug-investigation")
            self.assertEqual(report["navigator"]["task_types"], ["debug"])
            self.assertEqual(report["navigator"]["requirement_matrix"][0]["kind"], "debug-investigation")
            self.assertFalse((root / ".tailtrail").exists())

    def test_debug_start_excludes_all_tailtrail_state_from_scope_orientation(self):
        goal = "debug the issue in the report: first 6 steps are repeating in the report"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            managed = root / ".tailtrail" / "install" / "transactions" / "tx" / "backup" / ".tailtrail" / "install" / "payload" / "common" / "0.6.0" / "scripts" / "task-start.py"
            managed.parent.mkdir(parents=True)
            managed.write_text("first 6 steps repeating report generator\n", encoding="utf-8")
            source = root / "src" / "report_generator.py"
            source.parent.mkdir()
            source.write_text("def generate_report(steps):\n    return steps\n", encoding="utf-8")

            report = task_start.build_report(goal, root, [], "python3 scripts/tailtrail.py", workflow_override="debug")

        paths = {
            row["path"]
            for group in ("implementation_owners", "inspection_paths", "proof_paths", "excluded_candidates")
            for row in report["debug_plan"]["static_orientation"].get(group, [])
        }
        self.assertFalse(any(path.startswith(".tailtrail/") for path in paths))
        self.assertNotIn(".tailtrail/install/transactions", task_start.render_markdown(report, verbose=True))

    def test_hash_bound_host_diagnosis_enriches_debug_plan_without_claiming_root_cause(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            diagnosis = self.diagnosis(root)
            report = self.build(root, debug_diagnosis=diagnosis)
            rendered = task_start.render_markdown(report, verbose=True)
            compact = task_start.render_markdown(report, verbose=False)

        self.assertEqual(report["debug_plan"]["host_diagnosis"]["status"], "preliminary")
        self.assertEqual(
            report["debug_plan"]["host_diagnosis"]["evidence_completeness"]["status"],
            "complete",
        )
        self.assertIn("Evidence completeness: `complete`", rendered)
        self.assertIn("Evidence completeness:** `complete`", compact)
        self.assertIn("Typed host proposal: `prepare-reproduction`", rendered)
        self.assertIn("Typed host proposal:** `prepare-reproduction`", compact)
        self.assertIn("Safe fallback: `continue-approved-debug-investigation`", rendered)
        self.assertIn("Safe fallback:** `continue-approved-debug-investigation`", compact)
        self.assertEqual(report["debug_plan"]["safe_fallback"]["correction_scope"], "blocked")
        self.assertEqual(report["debug_plan"]["safe_fallback"]["user_input"], "not-required")
        self.assertIn("host-diagnosis", report["debug_plan"]["scope_seed_sources"])
        self.assertIn("## Preliminary debug analysis", rendered)
        self.assertIn("Host-assisted Debug Diagnosis", rendered)
        self.assertIn("## Required test cases", rendered)
        self.assertIn("TEST-01", rendered)
        self.assertIn("python3 -m unittest tests.test_payments", rendered)
        self.assertIn("Full diagnosed-file ceiling", rendered)
        self.assertNotIn("Focused context estimate: **not claimed yet**", rendered)
        self.assertIn("not root-cause proof", rendered)
        self.assertIn("Prevent duplicate payment submission after a timeout.", rendered)
        self.assertIn("tests/test_payments.py", {row["path"] for row in report["debug_plan"]["static_orientation"]["proof_paths"]})
        self.assertIn("one host reasoning pass", rendered)
        self.assertIn("Focused proof: `tests/test_payments.py`", compact)
        shared_command = "python3 -m unittest tests.test_payments"
        self.assertEqual(
            sum(row.get("command") == shared_command for row in report["debug_plan"]["validation_rows"]),
            1,
        )
        reproduction_rows = [
            row for row in report["debug_plan"]["validation_rows"] if row.get("tier") == "Reproduction"
        ]
        self.assertEqual(len(reproduction_rows), 1)
        self.assertIsNone(reproduction_rows[0].get("command"))
        self.assertEqual(compact.count("python3 -m unittest tests.test_payments"), 1)
        self.assertLessEqual(len(compact.splitlines()), 60)

    def test_compact_debug_plan_groups_owner_symbols_and_shows_actionable_proof_guidance(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            diagnosis = self.diagnosis(root)
            diagnosis["evidence"].append({
                "id": "E-TRANSFER",
                "path": "src/payments.py",
                "sha256": diagnosis["evidence"][0]["sha256"],
                "role": "implementation-owner",
                "behavior_roles": ["data-transfer"],
                "kind": "source-read",
                "symbols": ["submit"],
                "start_line": 1,
                "end_line": 2,
                "finding": "Receives the payment request from the charge boundary.",
            })
            diagnosis["reproduction"]["candidate_command"] = None
            diagnosis["reproduction"]["proposed_steps"] = [
                "Run the smallest timeout scenario.",
                "Count payment submissions.",
                "Record the failing result.",
            ]
            diagnosis["test_cases"][0]["command"] = None
            diagnosis["test_cases"].append({
                "id": "TEST-03",
                "tier": "behaviour",
                "state": "proposed",
                "statement": "Successful first-attempt payments remain unchanged.",
                "path": "tests/test_payments.py",
                "command": "python3 -m unittest tests.test_payments",
            })
            diagnosis["proposal"]["owner_evidence_ids"].append("E-TRANSFER")
            diagnosis["proposal"]["test_case_ids"].append("TEST-03")
            report = self.build(root, debug_diagnosis=diagnosis)
            compact = task_start.render_markdown(report, verbose=False)

        self.assertIn(
            "Likely owner: `src/payments.py` — `charge` (data producer); `submit` (data transfer).",
            compact,
        )
        self.assertNotIn("`src/payments.py`, `src/payments.py`", compact)
        self.assertIn("continues through the approved Debug investigation without guessing correction scope", compact)
        self.assertIn("TEST-02 — Regression assertion", compact)
        self.assertIn("TEST-03 — Behaviour assertion", compact)
        self.assertIn("creates the reproduction draft only", compact)
        self.assertIn("grants no source-edit authority", compact)

    def test_host_diagnosis_rejects_stale_and_private_reasoning(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            diagnosis = self.diagnosis(root)
            raw = {key: value for key, value in diagnosis.items() if key not in {"status", "token_estimate", "boundary"}}
            raw["evidence"][0]["sha256"] = "sha256:" + "0" * 64
            with self.assertRaisesRegex(ValueError, "stale"):
                debug_diagnosis.validate(root, "payments are sometimes charged twice after timeout", raw, "codex")
            raw["evidence"][0]["sha256"] = "sha256:" + __import__("hashlib").sha256((root / "src" / "payments.py").read_bytes()).hexdigest()
            raw["private_reasoning"] = "hidden"
            with self.assertRaisesRegex(ValueError, "not accepted"):
                debug_diagnosis.validate(root, "payments are sometimes charged twice after timeout", raw, "codex")

    def test_host_diagnosis_rejects_candidate_only_owner_promotion(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            diagnosis = self.diagnosis(root)
            raw = {key: value for key, value in diagnosis.items() if key not in {"status", "token_estimate", "boundary"}}
            raw["evidence"][0]["behavior_roles"] = ["candidate-only"]
            with self.assertRaisesRegex(ValueError, "candidate-only|lacks behavior-specific evidence"):
                debug_diagnosis.validate(root, "payments are sometimes charged twice after timeout", raw, "codex")

    def test_resolved_trace_requires_an_implementation_owner_producer(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            diagnosis = self.diagnosis(root)
            raw = {key: value for key, value in diagnosis.items() if key not in {"status", "token_estimate", "boundary"}}
            raw["behavior_trace"]["state"] = "resolved-to-producer"
            raw["evidence"][0]["role"] = "inspection"
            raw["behavior_trace"]["divergence_candidates"] = []
            with self.assertRaisesRegex(ValueError, "implementation-owner data producer"):
                debug_diagnosis.validate(root, "payments are sometimes charged twice after timeout", raw, "codex")

    def test_trace_nodes_must_match_their_evidence_roles_and_symbols(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            diagnosis = self.diagnosis(root)
            raw = {key: value for key, value in diagnosis.items() if key not in {"status", "token_estimate", "boundary"}}
            raw["behavior_trace"]["nodes"][0]["role"] = "output-renderer"
            with self.assertRaisesRegex(ValueError, "role does not match its evidence"):
                debug_diagnosis.validate(root, "payments are sometimes charged twice after timeout", raw, "codex")

    def test_resolved_trace_requires_a_connected_observed_output_to_producer_path(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            diagnosis = self.diagnosis(root)
            raw = {key: value for key, value in diagnosis.items() if key not in {"status", "token_estimate", "boundary"}}
            raw["behavior_trace"] = {
                "direction": "observed-output-to-producer",
                "state": "resolved-to-producer",
                "nodes": [
                    {"id": "TRACE-OUTPUT", "role": "observed-output", "path": "report.html", "symbols": [], "evidence_id": None},
                    {"id": "TRACE-OWNER", "role": "data-producer", "path": "src/payments.py", "symbols": ["charge"], "evidence_id": "E-OWNER"},
                    {"id": "TRACE-PROOF", "role": "proof", "path": "tests/test_payments.py", "symbols": ["test_timeout_charge_once"], "evidence_id": "E-PROOF"},
                ],
                "edges": [{"id": "TRACE-EDGE", "from": "TRACE-PROOF", "to": "TRACE-OWNER", "relationship": "exercises"}],
                "divergence_candidates": ["TRACE-OWNER"],
                "boundary": "The producer remains preliminary until reproduction proves the cause.",
            }
            with self.assertRaisesRegex(ValueError, "no complete observed-output-to-producer"):
                debug_diagnosis.validate(root, "payments are sometimes charged twice after timeout", raw, "codex")

    def test_incomplete_contract_is_reported_without_claiming_semantic_falsity(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            diagnosis = self.diagnosis(root)
            raw = {key: value for key, value in diagnosis.items() if key not in {"status", "token_estimate", "boundary", "evidence_completeness"}}
            raw["test_cases"] = [row for row in raw["test_cases"] if row["tier"] == "reproduction"]
            raw["proposal"]["test_case_ids"] = ["TEST-01"]
            validated = debug_diagnosis.validate(
                root,
                "payments are sometimes charged twice after timeout",
                raw,
                "codex",
            )

        completeness = validated["evidence_completeness"]
        self.assertEqual(completeness["status"], "incomplete")
        self.assertIn("test-contract", {
            row["id"] for row in completeness["checks"] if row["status"] == "incomplete"
        })
        self.assertIn("not proof", completeness["boundary"])

    def test_host_proposal_rejects_unrestricted_reasoning_and_incomplete_ids(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            diagnosis = self.diagnosis(root)
            raw = {key: value for key, value in diagnosis.items() if key not in {"status", "token_estimate", "boundary", "evidence_completeness"}}
            raw["proposal"]["analysis"] = "unrestricted reasoning"
            with self.assertRaisesRegex(ValueError, "proposal contains unsupported field"):
                debug_diagnosis.validate(root, "payments are sometimes charged twice after timeout", raw, "codex")
            raw["proposal"].pop("analysis")
            raw["proposal"]["test_case_ids"] = ["TEST-01"]
            with self.assertRaisesRegex(ValueError, "test references are incomplete"):
                debug_diagnosis.validate(root, "payments are sometimes charged twice after timeout", raw, "codex")

    def test_host_proposal_rejects_authority_and_unbounded_routes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            diagnosis = self.diagnosis(root)
            raw = {key: value for key, value in diagnosis.items() if key not in {"status", "token_estimate", "boundary", "evidence_completeness"}}
            raw["proposal"]["route"] = "apply-fix"
            with self.assertRaisesRegex(ValueError, "proposal route is invalid"):
                debug_diagnosis.validate(root, "payments are sometimes charged twice after timeout", raw, "codex")
            raw["proposal"]["route"] = "prepare-reproduction"
            raw["proposal"]["boundary"] = "approved"
            with self.assertRaisesRegex(ValueError, "advisory-only"):
                debug_diagnosis.validate(root, "payments are sometimes charged twice after timeout", raw, "codex")

    def test_host_must_not_request_user_evidence_when_reproduction_route_exists(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            diagnosis = self.diagnosis(root)
            raw = {key: value for key, value in diagnosis.items() if key not in {"status", "token_estimate", "boundary", "evidence_completeness", "safe_fallback"}}
            raw["proposal"]["route"] = "request-more-evidence"
            with self.assertRaisesRegex(ValueError, "must prepare reproduction"):
                debug_diagnosis.validate(root, "payments are sometimes charged twice after timeout", raw, "codex")

    def test_host_requests_input_only_when_no_reproduction_or_external_context_exists(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            diagnosis = self.diagnosis(root)
            raw = {key: value for key, value in diagnosis.items() if key not in {"status", "token_estimate", "boundary", "evidence_completeness", "safe_fallback"}}
            raw["reproduction"]["artifact_refs"] = []
            raw["reproduction"]["proposed_steps"] = []
            raw["reproduction"]["candidate_command"] = None
            reproduction_case = next(row for row in raw["test_cases"] if row["tier"] == "reproduction")
            reproduction_case["path"] = ""
            reproduction_case["command"] = None
            reproduction_case["state"] = "proposed"
            raw["proposal"]["route"] = "request-more-evidence"
            validated = debug_diagnosis.validate(
                root,
                "payments are sometimes charged twice after timeout",
                raw,
                "codex",
            )

        self.assertEqual(validated["safe_fallback"]["state"], "awaiting-reproduction-input")
        self.assertEqual(validated["safe_fallback"]["user_input"], "required")
        self.assertEqual(validated["safe_fallback"]["correction_scope"], "blocked")

    def test_compact_trace_follows_edges_instead_of_repeating_multi_role_nodes(self):
        trace = {
            "nodes": [
                {"id": "N1", "role": "observed-output", "path": "report.html"},
                {"id": "N2", "role": "output-renderer", "path": "report.py", "symbols": ["render"]},
                {"id": "N3", "role": "data-transfer", "path": "report.py", "symbols": ["render"]},
                {"id": "N4", "role": "data-transfer", "path": "hooks.py", "symbols": ["attach"]},
                {"id": "N5", "role": "data-producer", "path": "steps.py", "symbols": ["collect"]},
            ],
            "edges": [
                {"from": "N1", "to": "N2", "relationship": "rendered-by"},
                {"from": "N2", "to": "N4", "relationship": "reads-from"},
                {"from": "N4", "to": "N5", "relationship": "receives-from"},
            ],
        }

        self.assertEqual(
            task_start.compact_behavior_trace_steps(trace),
            ["report.html", "report.py::render", "hooks.py::attach", "steps.py::collect"],
        )

    def test_branching_behavior_graph_preserves_every_producer_path(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            diagnosis = self.diagnosis(root)
            source = root / "src" / "payments.py"
            source.write_text(
                "def charge(order):\n    return submit(order)\n\n"
                "def retry_charge(order):\n    return submit(order)\n",
                encoding="utf-8",
            )
            source_hash = "sha256:" + __import__("hashlib").sha256(source.read_bytes()).hexdigest()
            raw = {key: value for key, value in diagnosis.items() if key not in {"status", "token_estimate", "boundary", "evidence_completeness"}}
            raw["evidence"][0]["sha256"] = source_hash
            raw["evidence"].extend([
                {"id": "E-RENDER", "path": "src/payments.py", "sha256": source_hash, "role": "implementation-owner", "behavior_roles": ["output-renderer"], "kind": "source-read", "symbols": ["charge"], "start_line": 1, "end_line": 2, "finding": "Presents the payment outcome."},
                {"id": "E-RETRY", "path": "src/payments.py", "sha256": source_hash, "role": "implementation-owner", "behavior_roles": ["data-producer"], "kind": "source-read", "symbols": ["retry_charge"], "start_line": 4, "end_line": 5, "finding": "Produces the retry outcome."},
            ])
            raw["behavior_trace"] = {
                "direction": "observed-output-to-producer",
                "state": "resolved-to-producer",
                "nodes": [
                    {"id": "GRAPH-OUTPUT", "role": "observed-output", "path": "payment-result", "symbols": [], "evidence_id": None},
                    {"id": "GRAPH-RENDER", "role": "output-renderer", "path": "src/payments.py", "symbols": ["charge"], "evidence_id": "E-RENDER"},
                    {"id": "GRAPH-PRIMARY", "role": "data-producer", "path": "src/payments.py", "symbols": ["charge"], "evidence_id": "E-OWNER"},
                    {"id": "GRAPH-RETRY", "role": "data-producer", "path": "src/payments.py", "symbols": ["retry_charge"], "evidence_id": "E-RETRY"},
                    {"id": "GRAPH-PROOF", "role": "proof", "path": "tests/test_payments.py", "symbols": ["test_timeout_charge_once"], "evidence_id": "E-PROOF"},
                ],
                "edges": [
                    {"id": "GRAPH-E1", "from": "GRAPH-OUTPUT", "to": "GRAPH-RENDER", "relationship": "rendered-by"},
                    {"id": "GRAPH-E2", "from": "GRAPH-RENDER", "to": "GRAPH-PRIMARY", "relationship": "reads-from"},
                    {"id": "GRAPH-E3", "from": "GRAPH-RENDER", "to": "GRAPH-RETRY", "relationship": "reads-from"},
                    {"id": "GRAPH-E4", "from": "GRAPH-PROOF", "to": "GRAPH-RENDER", "relationship": "exercises"},
                ],
                "divergence_candidates": ["GRAPH-PRIMARY", "GRAPH-RETRY"],
                "boundary": "The graph preserves both bounded producer branches without proving either is faulty.",
            }
            raw["proposal"]["owner_evidence_ids"] = ["E-OWNER", "E-RENDER", "E-RETRY"]
            raw["proposal"]["trace_node_ids"] = ["GRAPH-RENDER", "GRAPH-PRIMARY", "GRAPH-RETRY", "GRAPH-PROOF"]
            validated = debug_diagnosis.validate(
                root,
                "payments are sometimes charged twice after timeout",
                raw,
                "codex",
            )

        topology = validated["behavior_trace"]["topology"]
        self.assertEqual(topology["shape"], "branching")
        self.assertEqual(topology["path_count"], 2)
        self.assertEqual(len(task_start.compact_behavior_graph_paths(validated["behavior_trace"])), 2)

    def test_resolved_behavior_graph_rejects_a_dead_end_branch(self):
        evidence = [
            {"id": "E-RENDER", "path": "report.py", "role": "implementation-owner", "behavior_roles": ["output-renderer"], "symbols": ["render"]},
            {"id": "E-PRODUCER", "path": "flow.py", "role": "implementation-owner", "behavior_roles": ["data-producer"], "symbols": ["produce"]},
            {"id": "E-DEAD", "path": "flow.py", "role": "implementation-owner", "behavior_roles": ["data-transfer"], "symbols": ["dead_end"]},
        ]
        graph = {
            "direction": "observed-output-to-producer",
            "state": "resolved-to-producer",
            "nodes": [
                {"id": "N-OUTPUT", "role": "observed-output", "path": "report.html", "symbols": [], "evidence_id": None},
                {"id": "N-RENDER", "role": "output-renderer", "path": "report.py", "symbols": ["render"], "evidence_id": "E-RENDER"},
                {"id": "N-PRODUCER", "role": "data-producer", "path": "flow.py", "symbols": ["produce"], "evidence_id": "E-PRODUCER"},
                {"id": "N-DEAD", "role": "data-transfer", "path": "flow.py", "symbols": ["dead_end"], "evidence_id": "E-DEAD"},
            ],
            "edges": [
                {"id": "E1", "from": "N-OUTPUT", "to": "N-RENDER", "relationship": "rendered-by"},
                {"id": "E2", "from": "N-RENDER", "to": "N-PRODUCER", "relationship": "reads-from"},
                {"id": "E3", "from": "N-RENDER", "to": "N-DEAD", "relationship": "reads-from"},
            ],
            "divergence_candidates": ["N-PRODUCER", "N-DEAD"],
            "boundary": "Evidence graph only.",
        }
        with self.assertRaisesRegex(ValueError, "every branch"):
            debug_diagnosis._validate_behavior_trace(graph, evidence)

    def test_public_cli_validates_and_persists_host_assisted_debug_diagnosis(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            diagnosis = self.diagnosis(root)
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "task-start.py"),
                    "payments are sometimes charged twice after timeout",
                    "--root", root.as_posix(),
                    "--host", "codex",
                    "--debug",
                    "--debug-diagnosis", json.dumps(diagnosis, separators=(",", ":")),
                    "--planning-run-id", "debug-host-cli",
                    "--format", "json",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            saved = json.loads(result.stdout)
            self.assertEqual(saved["debug_plan"]["host_diagnosis"]["host"], "codex")
            self.assertEqual(saved["debug_plan"]["token_estimate_confidence"], "medium")
            self.assertTrue((root / ".tailtrail" / "runs" / "debug-host-cli" / "planning" / "start-report-v1.json").is_file())

    def test_active_host_debug_start_requires_diagnosis_before_creating_a_lock(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "task-start.py"), "debug repeated report steps", "--root", root.as_posix(), "--host", "codex", "--debug"],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )

            self.assertEqual(result.returncode, 2)
            self.assertIn("# TailTrail Debug Diagnosis Required", result.stdout)
            self.assertIn("Plan detail:** `Quick`", result.stdout)
            self.assertIn("schemas/debug-host-diagnosis.schema.json", result.stdout)
            self.assertFalse((root / ".tailtrail").exists())

    def test_persisted_debug_start_uses_canonical_planning_lock_only(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = self.build(root)
            lock = task_start.planning_lock.create(root, report["goal"], run_id="debug-plan-1")
            report["planning_lock"] = lock
            report["workflow_runtime"] = {
                "enabled": False,
                "state": "deferred-to-di-4",
                "reason": "DI-4",
                "boundary": "planning only",
            }
            report["planning_report"] = task_start.planning_lock.save_start_report(root, lock["run_id"], report)
            markdown = task_start.render_markdown(report, verbose=True)

            for heading in (
                "Planning Lock",
                "Start Here",
                "Navigator Decision",
                "Scope",
                "Requirements",
                "Selected TailTrail features",
                "Required later in this run",
                "Conditional TailTrail controls",
                "Plan",
                "Focused validation",
                "Evidence posture",
                "Approval",
            ):
                self.assertIn(f"## {heading}", markdown)
            self.assertIn("debug-plan-1", markdown)
            self.assertTrue((root / ".tailtrail" / "runs" / "debug-plan-1" / "planning" / "lock-v1.json").is_file())
            self.assertTrue((root / ".tailtrail" / "runs" / "debug-plan-1" / "planning" / "start-report-v1.json").is_file())
            self.assertFalse((root / ".tailtrail" / "runs" / "debug-plan-1" / "debug").exists())

            activated = task_start.planning_lock.activate(root, "debug-plan-1", True)
            self.assertEqual(activated["state"], "reproduction-approval-required")
            self.assertEqual(activated["reproduction_contract"]["revision"], 1)
            self.assertEqual(activated["reproduction_contract"]["unresolved_fields"], ["expected", "reproduction_method"])
            self.assertFalse(task_start.planning_lock.show(root, "debug-plan-1")["writes_allowed"])
            self.assertFalse((root / ".tailtrail" / "runs" / "debug-plan-1" / "anchors" / "approved-v1.json").exists())

    def test_reproduction_revision_freezes_debug_anchor_and_investigation_only_handoff(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = self.build(root)
            lock = task_start.planning_lock.create(root, report["goal"], run_id="debug-di3")
            report["planning_lock"] = lock
            task_start.planning_lock.save_start_report(root, lock["run_id"], report)
            initial = task_start.planning_lock.activate(root, "debug-di3", True)
            requirement_uid = initial["reproduction_contract"]["requirement_uid"]

            revised = reproduction.draft(root, "debug-di3", {
                "requirement_uid": requirement_uid,
                "domain": "api-integration",
                "trigger": initial["reproduction_contract"]["trigger"],
                "expected": "One payment effect and one notification",
                "actual": "Retry creates duplicate payment and notification effects",
                "reproduction_method": "Run the timeout-after-acceptance integration test with two workers",
                "preserve_rules": ["Successful single-worker checkout remains unchanged"],
                "safety_boundary": "Use local adapters only; never call a real payment provider",
                "validation_contract": {"state": "required", "tiers": ["reproduction", "root-cause", "regression", "behaviour"]},
            })
            approved = reproduction.approve(root, "debug-di3", revised["revision"])

            anchor = json.loads((root / ".tailtrail" / "runs" / "debug-di3" / "anchors" / "approved-v1.json").read_text(encoding="utf-8"))
            self.assertEqual(anchor["requirements"][0]["requirement_uid"], requirement_uid)
            self.assertEqual(anchor["requirements"][0]["kind"], "debug-investigation")
            self.assertEqual(anchor["requirements"][0]["validation_contract"]["tiers"], ["reproduction", "root-cause", "regression", "behaviour"])
            self.assertEqual(approved["execution_handoff"]["state"], "investigation-ready")
            self.assertIn("edit project source", approved["execution_handoff"]["forbidden_actions"])
            runtime = approved["execution_handoff"]["workflow_runtime"]
            self.assertEqual(runtime["compiler"]["template_id"], "debug-investigation")
            self.assertEqual(runtime["current_stage"], "d-01-intake")
            self.assertEqual(runtime["current_stage_display"], "D-01 Intake")
            self.assertNotIn("d-08-correction-implementation", runtime["investigation_approval"]["stage_ids"])
            workflow_id = runtime["workflow_id"]
            self.assertEqual(workflow_resume.plan(root, workflow_id)["next_stage_id"], "d-01-intake")
            before = workflow_state.replay(root, workflow_id)["last_valid_projection"]
            self.assertEqual(workflow_state.pause(root, workflow_id)["workflow_status"], "paused")
            self.assertEqual(workflow_state.resume(root, workflow_id)["workflow_status"], "ready")
            after = workflow_state.replay(root, workflow_id)["last_valid_projection"]
            self.assertEqual(after["current_stage_id"], before["current_stage_id"])
            with self.assertRaisesRegex(ValueError, "blocked-missing-authority"):
                workflow_approvals.authorize_stage(root, workflow_id, "d-08-correction-implementation", None)
            self.assertTrue(task_start.planning_lock.assert_write_allowed(root, "debug-di3")["writes_allowed"])
            with self.assertRaisesRegex(ValueError, "investigation only"):
                task_start.planning_lock.assert_source_write_allowed(root, "debug-di3")

            workflow_freshness.ensure(root, workflow_id)
            approved_reproduction = root / approved["execution_handoff"]["reproduction_contract"]
            tampered = json.loads(approved_reproduction.read_text(encoding="utf-8"))
            tampered["actual"] = "externally modified after approval"
            approved_reproduction.write_text(json.dumps(tampered), encoding="utf-8")
            stale = workflow_freshness.assess(root, workflow_id)
            self.assertIn("reproduction-change", stale["change_types"])
            self.assertIn("d-05-experiment", stale["affected_stage_ids"])

    def test_reproduction_approval_is_revision_specific_and_blocks_unresolved_fields(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = self.build(root)
            lock = task_start.planning_lock.create(root, report["goal"], run_id="debug-revision")
            report["planning_lock"] = lock
            task_start.planning_lock.save_start_report(root, lock["run_id"], report)
            task_start.planning_lock.activate(root, "debug-revision", True)

            with self.assertRaisesRegex(ValueError, "fields are unresolved"):
                reproduction.approve(root, "debug-revision", 1)
            complete = reproduction.draft(root, "debug-revision", {
                "domain": "code", "trigger": "retry duplicates an effect", "expected": "one effect",
                "actual": "two effects", "reproduction_method": "run focused retry test",
                "preserve_rules": ["successful path remains valid"], "safety_boundary": "local test doubles only",
            })
            with self.assertRaisesRegex(ValueError, "revision mismatch"):
                reproduction.approve(root, "debug-revision", 1)
            reproduction.approve(root, "debug-revision", complete["revision"])
            with self.assertRaisesRegex(ValueError, "immutable"):
                reproduction.draft(root, "debug-revision", {
                    "domain": "code", "trigger": "other", "expected": "a", "actual": "b",
                    "reproduction_method": "c", "safety_boundary": "d",
                })

    def test_reproduction_revision_preserves_uid_and_renders_approval_report(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            reproduction.L.init_run(root, "debug-stable", "debug stable identity")
            first = reproduction.draft(root, "debug-stable", {
                "domain": "code", "trigger": "retry duplicates an effect", "expected": "one effect",
                "actual": "two effects", "reproduction_method": "run first command",
                "preserve_rules": ["successful path remains valid"], "safety_boundary": "local only",
            })
            second = reproduction.revise(root, "debug-stable", 1, {
                "domain": "code", "trigger": "run the precise retry fixture", "expected": "one effect",
                "actual": "two effects", "reproduction_method": "python retry_fixture.py",
                "preserve_rules": ["successful path remains valid"], "safety_boundary": "local only",
                "validation_contract": {
                    "expected_exit_code_before_fix": 1,
                    "required_output": ["effects=2"],
                    "expected_exit_code_after_fix": 0,
                    "required_output_after_fix": ["effects=1"],
                },
            })
            self.assertEqual(second["requirement_uid"], first["requirement_uid"])
            markdown = reproduction.render_markdown(second)
            self.assertIn("# TailTrail Reproduction Contract", markdown)
            self.assertIn("Before fix: failure reproduced", markdown)
            self.assertIn("Root cause proven", markdown)
            self.assertIn("After fix: behavior restored", markdown)
            self.assertIn("Approve reproduction revision 2", markdown)
            self.assertIn("## Next actions", markdown)
            self.assertIn("Revise reproduction revision 2 for run debug-stable", markdown)
            self.assertIn("Explain reproduction revision 2 for run debug-stable", markdown)
            self.assertIn("tailtrail stop", markdown)
            self.assertIn("tailtrail resume --run-id debug-stable", markdown)
            self.assertIn("## Route to a code fix", markdown)
            self.assertIn("Approve the correction for run debug-stable and implement only its approved scope", markdown)
            self.assertNotIn("| Action |", markdown)

            with self.assertRaisesRegex(ValueError, "requirement UID mismatch"):
                reproduction.revise(root, "debug-stable", 2, {
                    "requirement_uid": "req-000000000000", "domain": "code", "trigger": "other",
                    "expected": "one", "actual": "two", "reproduction_method": "command",
                    "safety_boundary": "local only",
                })

    def test_legacy_identity_drift_is_visible_and_cannot_be_approved(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            reproduction.L.init_run(root, "debug-drift", "debug identity drift")
            first = reproduction.draft(root, "debug-drift", {
                "domain": "code", "trigger": "original", "expected": "one", "actual": "two",
                "reproduction_method": "command", "safety_boundary": "local only",
            })
            drifted = {**first, "revision": 2, "requirement_uid": "req-000000000000", "trigger": "refined"}
            reproduction.L.atomic_json(reproduction.revision_path(root, "debug-drift", 2), drifted)
            reproduction.L.atomic_json(reproduction.contract_path(root, "debug-drift"), drifted)

            markdown = reproduction.render_markdown(
                drifted, reproduction.saved_canonical_requirement_uid(root, "debug-drift")
            )
            self.assertIn("Identity drift detected", markdown)
            self.assertIn("blocked by legacy identity drift", markdown)
            self.assertIn("Approval is unavailable", markdown)
            self.assertNotIn("To approve this exact contract", markdown)
            self.assertIn("Approve this exact reproduction - currently blocked", markdown)
            self.assertIn("Revise reproduction revision 2 for run debug-drift", markdown)
            with self.assertRaisesRegex(ValueError, "legacy requirement identity drift"):
                reproduction.approve(root, "debug-drift", 2)

    def test_approved_reproduction_guidance_advances_investigation_not_source_authority(self):
        contract = {
            "run_id": "debug-approved-guidance",
            "revision": 3,
            "status": "approved",
            "requirement_uid": "req-guidance",
            "unresolved_fields": [],
        }

        guidance = reproduction.next_action_guidance(contract)
        actions = {item["id"]: item for item in guidance["actions"]}

        self.assertEqual(guidance["state"], "investigation-ready")
        self.assertEqual(actions["run-approved-reproduction"]["availability"], "now")
        self.assertIn("record the factual result", actions["run-approved-reproduction"]["prompt"])
        self.assertIn("root-cause proof", actions["continue-investigation"]["prompt"])
        self.assertNotIn("approve-reproduction", actions)
        self.assertIn("separate correction approval", guidance["boundary"])

    def test_reproduction_report_keeps_multiline_and_pipe_prose_inside_table_cells(self):
        contract = {
            "run_id": "debug-markdown",
            "revision": 1,
            "status": "awaiting-approval",
            "requirement_uid": "req-markdown",
            "domain": "code",
            "trigger": "first wrapped line\nsecond | wrapped line",
            "expected": "one requirement",
            "actual": "two requirements",
            "reproduction_method": "run focused test",
            "preserve_rules": ["bullets\nremain separate"],
            "safety_boundary": "local only",
            "validation_contract": {},
            "unresolved_fields": [],
        }

        markdown = reproduction.render_markdown(contract)

        self.assertIn("| Trigger | first wrapped line second \\| wrapped line |", markdown)
        self.assertNotIn("first wrapped line\nsecond", markdown)
        self.assertIn("- bullets remain separate", markdown)

    def test_debug_start_records_presence_flags_without_raw_values(self):
        with tempfile.TemporaryDirectory() as temp:
            report = self.build(
                Path(temp),
                has_error_artifact=True,
                has_reproduction_command=True,
            )
            evidence = report["debug_plan"]["classification_evidence"]

            self.assertTrue(evidence["error_artifact_supplied"])
            self.assertTrue(evidence["reproduction_command_supplied"])
            serialized = json.dumps(report)
            self.assertNotIn("attached_error", serialized)
            self.assertNotIn("attached_command", serialized)

    def test_explicit_build_override_retains_normal_start_path(self):
        with tempfile.TemporaryDirectory() as temp:
            report = self.build(Path(temp), workflow_override="build")

            self.assertNotIn("debug_plan", report)
            self.assertEqual(report["navigator"]["workflow_classification"]["workflow_type"], "build")

    def test_debug_static_orientation_spawns_no_command_and_claims_no_root_cause(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "src" / "payments.py"
            source.parent.mkdir(parents=True)
            source.write_text("def charge():\n    return 'ok'\n", encoding="utf-8")
            with mock.patch.object(
                task_start.navigator_scope.subprocess,
                "run",
                side_effect=AssertionError("Debug Start must not spawn Git inventory"),
            ), mock.patch.object(
                task_start.navigator.discovery,
                "run_review_graph",
                side_effect=AssertionError("Debug Start must not spawn review-graph"),
            ):
                report = self.build(root, changed=["src/payments.py"])

            orientation = report["debug_plan"]["static_orientation"]
            rendered = task_start.render_markdown(report, verbose=True)
            self.assertEqual(orientation["role_label"], "orientation-candidate")
            self.assertIn("src/payments.py", {row["path"] for row in orientation["implementation_owners"]})
            self.assertIn("orientation candidate", rendered)
            self.assertIn("never correction scope or root-cause proof", rendered)
            self.assertIn("Project commands, tests, graph helpers", rendered)
            self.assertNotIn("Root cause: **proven**", rendered)

    def test_debug_start_uses_saved_graph_without_freshness_claim(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            cache = root / ".tailtrail" / "code-graph-cache.json"
            cache.parent.mkdir(parents=True)
            cache.write_text(json.dumps({
                "schema_version": "1",
                "scope": ["src/payments.py", "tests/test_payments.py"],
                "graph": {
                    "confidence": "medium",
                    "suggested_read_order": ["src/payments.py", "tests/test_payments.py"],
                },
            }), encoding="utf-8")

            report = self.build(root)

            self.assertEqual(report["debug_plan"]["scope_source"], "bounded-static-orientation")
            self.assertIn("saved-graph", report["debug_plan"]["scope_seed_sources"])
            rendered = task_start.render_markdown(report, verbose=True)
            self.assertIn("bounded static relationship decision", rendered)
            self.assertNotIn("Scope source: `saved-code-graph`", rendered)
            self.assertEqual(report["navigator"]["graph_cache"]["status"], "saved-unverified")
            self.assertEqual(
                [item["path"] for item in report["navigator"]["likely_impacted_files"][:2]],
                ["src/payments.py", "tests/test_payments.py"],
            )

    def test_debug_start_labels_user_paths_and_supplied_reproduction_without_claiming_validation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = self.build(
                root,
                changed=["debug_lab/retry_race.py", "debug_lab/run_duplicate_effect_failure.py"],
                has_reproduction_command=True,
            )
            markdown = task_start.render_markdown(report, verbose=True)

            self.assertEqual(report["debug_plan"]["scope_source"], "bounded-static-orientation")
            self.assertIn("explicit-path", report["debug_plan"]["scope_seed_sources"])
            self.assertIn("supplied by the user as inspection candidates", markdown)
            self.assertIn("Confirm that the supplied reproduction procedure", markdown)
            self.assertIn("No validation has run during Planning Lock", markdown)
            self.assertNotIn("saved graph evidence is advisory", markdown)

    def test_public_start_cli_persists_and_prints_canonical_debug_plan(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "tailtrail.py"),
                    "start",
                    "investigate why cancellation publishes two events",
                    "--root",
                    str(root),
                    "--planning-run-id",
                    "debug-cli-1",
                    "--verbose",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            self.assertIn("# TailTrail Debug Start Plan", result.stdout)
            self.assertIn("Run ID: `debug-cli-1`", result.stdout)
            self.assertIn("## Proposed reproduction questions", result.stdout)
            self.assertIn("## Proposed reproduction steps", result.stdout)
            self.assertIn("## Required later in this run", result.stdout)
            self.assertIn("Regression, preservation, and selected Harness testing", result.stdout)
            self.assertIn("mandatory", result.stdout.lower())
            self.assertNotIn("## Deferred TailTrail features", result.stdout)
            self.assertIn("Evidence state: **not run**", result.stdout)
            self.assertIn("awaiting-reproduction-input", result.stdout)
            self.assertIn("### Requirement facets", result.stdout)
            self.assertIn("REQ-DEBUG-01.D", result.stdout)
            self.assertIn("- **What it must prove:**", result.stdout)
            self.assertIn("- **Candidate evidence:**", result.stdout)
            self.assertIn("- **Activation gate:**", result.stdout)
            self.assertIn("- **Pass condition:**", result.stdout)
            self.assertIn("Approved reproduction command plus exact command-result receipt.", result.stdout)
            self.assertIn("## Token estimate", result.stdout)
            self.assertIn("Focused context estimate: **not claimed yet**", result.stdout)
            self.assertIn("Confidence: **low**", result.stdout)
            self.assertIn("Hypothesis Ledger and Bounded Experiment Loop", result.stdout)
            self.assertIn("Canonical completion and closure", result.stdout)
            self.assertNotIn("deferred until the relevant approved debug stage", result.stdout)
            self.assertTrue((root / ".tailtrail" / "runs" / "debug-cli-1" / "planning" / "start-report-v1.json").is_file())
            self.assertFalse((root / ".tailtrail" / "runs" / "debug-cli-1" / "debug").exists())

    def test_generated_report_duplication_plan_uses_specific_contract_language(self):
        goal = (
            "debug the issue in the report: first 6 steps are repeating in the report; "
            "it shouldn't have happened. Report path: "
            "file:///private/tmp/report.html?sort=result"
        )
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "src").mkdir()
            (root / "src" / "index.py").write_text("def generate_report():\n    return []\n", encoding="utf-8")
            report = task_start.build_report(
                goal,
                root,
                [],
                "python3 scripts/tailtrail.py",
            )
            rendered = task_start.render_markdown(report, verbose=False)
            detailed = task_start.render_markdown(report, verbose=True)

        debug = report["debug_plan"]
        requirement = report["navigator"]["requirement_matrix"][0]
        self.assertEqual("generated-output-duplication", debug["symptom_profile"]["profile"])
        self.assertIn("first 6 steps", requirement["statement"])
        self.assertIn("appear exactly once", requirement["statement"])
        self.assertTrue(debug["classification_evidence"]["debug_command_form_detected"])
        self.assertTrue(debug["classification_evidence"]["output_reference_supplied"])
        self.assertNotIn("approved expected-behaviour boundary", " ".join(debug["material_unknowns"]))
        self.assertIn("input data, aggregation, generation, or rendering", " ".join(debug["material_unknowns"]))
        self.assertNotIn("exact labels in the first 6 steps", rendered)
        self.assertIn("exact labels in the first 6 steps", detailed)
        self.assertIn("local report/output reference in the goal `true`", detailed)
        self.assertIn("genuine steps, order, statuses, details", rendered)
        self.assertIn("exactly one instance of every intended item", detailed)
        self.assertNotIn("external-effect invariants", rendered)
        self.assertNotIn("duplicate effect", rendered)
        self.assertEqual(7, len(report["guided_delivery"]["stages"]))
        self.assertIn("Focused estimate unavailable", rendered)
        self.assertNotIn("22500", rendered)
        self.assertLessEqual(len(rendered.splitlines()), 60)

    def test_multiline_parser_debug_plan_is_focused_consistent_and_concrete(self):
        goal = (
            "debug an issue: fix multiline requirement splitting. Example: Requirements currently "
            "render as REQ-01 Add delivery-address validation without breaking valid. and "
            "REQ-02 Addresses. Expected one requirement."
        )
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            scripts = root / "scripts"
            tests = root / "tests"
            scripts.mkdir()
            tests.mkdir()
            (scripts / "requirement_discovery.py").write_text(
                "def statements(goal):\n    return goal.splitlines()\n",
                encoding="utf-8",
            )
            (scripts / "task-start.py").write_text(
                "import requirement_discovery\n",
                encoding="utf-8",
            )
            (scripts / "planning_lock.py").write_text(
                "import requirement_discovery\n",
                encoding="utf-8",
            )
            (tests / "test_requirement_discovery.py").write_text(
                "import requirement_discovery\n# multiline splitting proof\n",
                encoding="utf-8",
            )
            (tests / "test_aidlc_requirements.py").write_text(
                "# requirements wording only\n",
                encoding="utf-8",
            )
            report = task_start.build_report(
                goal,
                root,
                [],
                "python3 scripts/tailtrail.py",
                workflow_override="debug",
            )
            rendered = task_start.render_markdown(report, verbose=True)

        orientation = report["debug_plan"]["static_orientation"]
        self.assertEqual(
            [row["path"] for row in orientation["implementation_owners"]],
            ["scripts/requirement_discovery.py"],
        )
        self.assertIn(
            "scripts/task-start.py",
            [row["path"] for row in orientation["inspection_paths"]],
        )
        self.assertIn(
            "tests/test_requirement_discovery.py",
            [row["path"] for row in orientation["proof_paths"]],
        )
        self.assertEqual(
            {
                requirement_id
                for group in ("implementation_owners", "inspection_paths", "proof_paths")
                for row in orientation[group]
                for requirement_id in row["requirement_ids"]
            },
            {"REQ-DEBUG-01"},
        )
        self.assertNotIn("scripts/aidlc-requirements.py", rendered)
        self.assertIn("## Proposed reproduction contract", rendered)
        self.assertIn("### Proposed concrete contract", rendered)
        self.assertIn(
            "Add delivery-address validation without breaking valid.\nAddresses.",
            rendered,
        )
        self.assertIn("Explicit Markdown bullets remain separate requirements.", rendered)
        self.assertEqual(len(report["guided_delivery"]["stages"]), 7)
        self.assertIn(
            "multiline requirement-splitting defect",
            report["navigator"]["requirement_matrix"][0]["statement"],
        )
        unknowns = " ".join(report["debug_plan"]["material_unknowns"]).lower()
        self.assertNotIn("confirmed failing path and callers", unknowns)
        self.assertNotIn("approved expected-behaviour boundary", unknowns)
        self.assertIn("factual receipt", unknowns)
        self.assertIn("boundary rule", unknowns)
        self.assertEqual(report["debug_plan"]["scope_source"], "bounded-static-orientation")
        self.assertIn("persist the displayed proposal as a versioned reproduction draft", rendered)
        self.assertIn("exact-revision approval remains separate", rendered)
        self.assertNotIn("allow DI-3 to draft a reproduction contract", rendered)
        self.assertNotIn("reproduction contract are not created or approved", rendered)

    def test_public_cli_loose_debug_prompt_creates_complete_single_requirement_plan(self):
        goal = """debug an - issue `fix multiline requirement splitting.`

Example:

## Requirements

- **REQ-01:** Add delivery-address validation without breaking valid.
- **REQ-02:** Addresses.

##

there are 2 requirements but ideally it should be 1; soft-wrapped prose should remain one requirement.
"""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "scripts").mkdir()
            (root / "tests").mkdir()
            (root / "scripts" / "requirement_discovery.py").write_text(
                "def statements(goal):\n    return goal.splitlines()\n",
                encoding="utf-8",
            )
            (root / "scripts" / "task-start.py").write_text(
                "import requirement_discovery\n",
                encoding="utf-8",
            )
            (root / "tests" / "test_requirement_discovery.py").write_text(
                "import requirement_discovery\n# multiline splitting proof\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "tailtrail.py"),
                    "start",
                    goal,
                    "--root",
                    str(root),
                    "--planning-run-id",
                    "debug-multiline-cli",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            saved_path = root / ".tailtrail" / "runs" / "debug-multiline-cli" / "planning" / "start-report-v1.json"
            saved = json.loads(saved_path.read_text(encoding="utf-8")) if saved_path.is_file() else {}

        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn("# TailTrail Debug Start Plan", result.stdout)
        self.assertNotIn("# TailTrail Scope Confirmation Required", result.stdout)
        for heading in (
            "Planning Lock",
            "Scope",
            "Requirements",
            "Selected TailTrail features",
            "Plan",
            "Focused validation",
            "Approval",
        ):
            self.assertIn(f"## {heading}", result.stdout)
        matrix = saved["report"]["navigator"]["requirement_matrix"]
        self.assertEqual(len(matrix), 1)
        self.assertEqual(matrix[0]["display_id"], "REQ-DEBUG-01")
        self.assertIn("multiline requirement-splitting defect", matrix[0]["statement"])
        orientation = saved["report"]["debug_plan"]["static_orientation"]
        self.assertEqual(
            [row["path"] for row in orientation["implementation_owners"]],
            ["scripts/requirement_discovery.py"],
        )
        self.assertNotIn("scripts/install-copilot.py", result.stdout)
        self.assertNotIn("scripts/planning-aidlc-question.py", result.stdout)
        self.assertNotIn("scripts/planning-feature-controls.py", result.stdout)


if __name__ == "__main__":
    unittest.main()
