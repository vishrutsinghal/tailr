from __future__ import annotations

import hashlib
import copy
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if SCRIPTS.as_posix() not in sys.path:
    sys.path.insert(0, SCRIPTS.as_posix())

import navigator  # noqa: E402
import navigator_discovery  # noqa: E402
import navigator_graph_lifecycle  # noqa: E402
import navigator_scope  # noqa: E402
import code_relationships  # noqa: E402
import requirement_discovery  # noqa: E402
from workflow_runtime import contracts  # noqa: E402


TASK_START_SPEC = importlib.util.spec_from_file_location(
    "navigator_scope_task_start_test", ROOT / "scripts" / "task-start.py"
)
assert TASK_START_SPEC and TASK_START_SPEC.loader
task_start = importlib.util.module_from_spec(TASK_START_SPEC)
sys.modules[TASK_START_SPEC.name] = task_start
TASK_START_SPEC.loader.exec_module(task_start)


FIXTURE_ROOT = ROOT / "tests" / "fixtures" / "navigator-scope"
BASELINE_PATH = ROOT / "tailtrail-meta" / "navigator-scope-baseline-v1.json"
SCHEMA_PATH = ROOT / "schemas" / "navigator-scope-baseline.schema.json"
EVIDENCE_SCHEMA_PATH = ROOT / "schemas" / "navigator-scope-evidence.schema.json"
HOST_PROPOSAL_SCHEMA_PATH = ROOT / "schemas" / "navigator-host-scope-proposal.schema.json"
SCOPE_QUALITY_SCHEMA_PATH = ROOT / "schemas" / "navigator-scope-quality.schema.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def build_requirement_interpretation(goal: str, host: str = "codex") -> dict[str, Any]:
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


def build_host_proposal(packet: dict[str, Any], host: str = "codex") -> dict[str, Any]:
    candidates = {row["path"]: row for row in packet["candidates"]}
    requirement = packet["requirements"][0]
    chosen = packet["route"]["eligible_candidates"][0]["path"]
    alternative = packet["route"]["eligible_candidates"][1]["path"]
    inspection_rows = [row for row in packet["candidates"] if row["role"] == "literal-emitter"]
    material = [(chosen, "implementation-owner")]
    inspection_paths: list[str] = []
    if inspection_rows:
        inspection_paths = [inspection_rows[0]["path"]]
        material.append((inspection_paths[0], "inspection"))
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
            "inspection_paths": inspection_paths,
            "proof_paths": [],
            "excluded_candidates": [row["path"] for row in requirement["excluded_candidates"]],
            "path_claims": claims,
            "preservation_boundaries": ["Preserve the unselected renderer unless its runtime path is requested."],
            "evidence_edge_ids": sorted({edge for claim in claims for edge in claim["evidence_edge_ids"]}),
            "confidence": "high",
            "decision_reasons": ["The request context selects one strongly evidenced renderer."],
            "alternatives": [alternative],
            "uncertainties": [],
        }],
        "private_reasoning_excluded": True,
    }


def fingerprint(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_bytes(value)).hexdigest()


class NavigatorScopeBaselineTests(unittest.TestCase):
    def fixture(self, fixture_id: str) -> dict[str, Any]:
        return load_json(FIXTURE_ROOT / f"{fixture_id}.json")

    @staticmethod
    def materialize(repository: Path, fixture: dict[str, Any]) -> None:
        for relative, body in fixture.get("repository_files", {}).items():
            target = repository / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(body, encoding="utf-8")

    @staticmethod
    def observed_false_stop(report: dict[str, Any]) -> dict[str, Any]:
        evidence = report["scope_evidence"]
        quality = report["scope_quality"]
        question = quality.get("question")
        return {
            "scope_state": evidence["state"],
            "implementation_owners": evidence["requirements"][0]["implementation_owners"],
            "stop_reason": evidence["investigation"]["stop_reason"],
            "files_read": evidence["investigation"]["files_read"],
            "bytes_read": evidence["investigation"]["bytes_read"],
            "graph_cache_status": evidence["investigation"]["cache"]["status"],
            "graph_reason_codes": evidence["investigation"]["cache"]["reason_codes"],
            "scope_quality_status": quality["status"],
            "scope_quality_reason_codes": quality["reason_codes"],
            "scope_question_options": question["options"] if question else [],
            "planning_lock_created": False,
        }

    def test_ns3_resolves_owner_callers_and_proof_while_excluding_lexical_false_positive(self) -> None:
        fixture = self.fixture("wrong-file-selection")
        with tempfile.TemporaryDirectory() as temporary:
            repository = Path(temporary)
            for relative, body in fixture["repository_files"].items():
                target = repository / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(body, encoding="utf-8")

            report = navigator.decide(
                fixture["goal"],
                repository,
                [],
                "python3 scripts/tailtrail.py",
                detect_git_changes=False,
            )
            impacted = report["likely_impacted_files"]
            actual_paths = [item["path"] for item in impacted]

        self.assertEqual(report["target_origin"], "goal-discovery")
        self.assertEqual(report["scope_evidence"]["state"], "resolved")
        self.assertEqual(
            report["scope_evidence"]["requirements"][0]["implementation_owners"],
            fixture["desired_expected"]["implementation_owners"],
        )
        self.assertEqual(
            report["scope_evidence"]["requirements"][0]["inspection_paths"],
            fixture["desired_expected"]["callers"],
        )
        self.assertEqual(
            report["scope_evidence"]["requirements"][0]["proof_paths"],
            fixture["desired_expected"]["proof_paths"],
        )
        self.assertEqual(
            report["scope_evidence"]["requirements"][0]["reason_codes"],
            ["bounded-static-owner-resolved"],
        )
        self.assertEqual(
            actual_paths,
            [
                "scripts/planning_lock.py",
                "scripts/requirement_discovery.py",
                "scripts/task-start.py",
                "tests/test_requirement_discovery.py",
            ],
        )
        excluded = {row["path"]: row for row in report["scope_evidence"]["candidates"] if row["status"] == "excluded"}
        self.assertIn("lexical-only-no-owner-edge", excluded["tests/test_aidlc_requirements.py"]["reason_codes"])
        self.assertTrue(report["scope_evidence"]["edges"])
        self.assertLessEqual(report["scope_evidence"]["investigation"]["files_read"], 32)
        self.assertEqual(
            [item["name"] for item in report["selected_features"]].count("Code Review Graph Lite"),
            1,
        )
        self.assertEqual(report["scope_host_packet"]["scope_evidence_fingerprint"], report["scope_evidence"]["decision_fingerprint"])

    def test_ns1_closes_the_recorded_multiline_known_gap(self) -> None:
        fixture = self.fixture("multiline-requirement-splitting")
        rows = requirement_discovery.statements(fixture["goal"])
        actual = {"requirement_count": len(rows), "statements": rows}

        self.assertEqual(actual, fixture["desired_expected"])
        self.assertNotEqual(actual, fixture["current_expected"])
        self.assertEqual(actual["statements"][-1], "Add delivery-address validation without breaking valid addresses.")

    def test_baseline_validates_and_has_a_valid_integrity_seal(self) -> None:
        baseline = load_json(BASELINE_PATH)
        schema = load_json(SCHEMA_PATH)

        self.assertEqual(contracts.validate_document(baseline, schema), [])
        integrity = baseline.pop("integrity")
        self.assertEqual(
            integrity,
            {
                "algorithm": "sha256",
                "canonicalization": "sorted compact JSON excluding integrity",
                "digest": hashlib.sha256(canonical_bytes(baseline)).hexdigest(),
            },
        )

    def test_baseline_fingerprints_bind_each_fixture_and_result(self) -> None:
        baseline = load_json(BASELINE_PATH)
        rows = {row["id"]: row for row in baseline["fixtures"]}

        self.assertEqual(
            set(rows),
            {
                "wrong-file-selection",
                "multiline-requirement-splitting",
                "typescript-alias-ui-literal-false-stop",
                "typescript-genuine-renderer-ambiguity",
            },
        )
        for fixture_id, row in rows.items():
            fixture_path = ROOT / row["fixture"]
            fixture = load_json(fixture_path)
            with self.subTest(fixture=fixture_id):
                self.assertEqual(row["state"], "known-gap")
                self.assertEqual(row["input_fingerprint"], fingerprint(fixture))
                self.assertEqual(row["current_result"], fixture["current_expected"])
                self.assertEqual(row["current_result_fingerprint"], fingerprint(row["current_result"]))
                self.assertEqual(row["expected_result"], fixture["desired_expected"])
                self.assertEqual(row["expected_result_fingerprint"], fingerprint(row["expected_result"]))

    def test_baseline_contains_no_fixture_source_bodies(self) -> None:
        baseline_text = BASELINE_PATH.read_text(encoding="utf-8")
        self.assertNotIn('"repository_files"', baseline_text)
        for fixture_path in sorted(FIXTURE_ROOT.glob("*.json")):
            fixture = load_json(fixture_path)
            for source_body in fixture.get("repository_files", {}).values():
                with self.subTest(fixture=fixture_path.name, source=source_body.splitlines()[0]):
                    self.assertNotIn(source_body, baseline_text)

    def test_baseline_records_the_canonical_scope_owners(self) -> None:
        baseline = load_json(BASELINE_PATH)

        self.assertEqual(
            baseline["ownership"],
            {
                "scope_decision": "Navigator",
                "target_identity": "Target Workspace",
                "relationship_evidence": "Code Graph",
                "validated_persistence": "Planning Lock",
            },
        )
        self.assertEqual(baseline["program_extensions"], ["FSR-0"])
        self.assertEqual(
            baseline["calibration"],
            {
                "known_false_stop_ids": ["typescript-alias-ui-literal-false-stop"],
                "safe_stop_control_ids": ["typescript-genuine-renderer-ambiguity"],
                "metrics": {
                    "known_false_stop_count": 1,
                    "safe_stop_control_count": 1,
                    "observed_irrelevant_option_count": 9,
                    "unsafe_lock_count": 0,
                },
                "release_posture": "known-gap-not-release-proof",
            },
        )

    def test_fsr1_resolves_frozen_alias_false_stop_through_start_boundary(self) -> None:
        fixture = self.fixture("typescript-alias-ui-literal-false-stop")
        with tempfile.TemporaryDirectory() as temporary:
            repository = Path(temporary)
            self.materialize(repository, fixture)
            created = navigator_graph_lifecycle.manage(
                repository,
                fixture["goal"],
                mode="auto",
                attempt_id="fsr0-graph",
            )
            report = navigator.decide(
                fixture["goal"],
                repository,
                [],
                "tailtrail",
                detect_git_changes=False,
            )
            evidence = report["scope_evidence"]
            requirement = evidence["requirements"][0]
            active_candidates = {
                row["path"]: row
                for row in evidence["candidates"]
                if row["status"] != "excluded"
            }
            start = subprocess.run(
                [
                    sys.executable,
                    (ROOT / "scripts" / "task-start.py").as_posix(),
                    fixture["goal"],
                    "--root",
                    repository.as_posix(),
                    "--format",
                    "json",
                    "--planning-run-id",
                    "fsr0-false-stop",
                ],
                cwd=repository,
                text=True,
                capture_output=True,
                check=False,
            )
            start_payload = json.loads(start.stdout)
            run_exists = (repository / ".tailtrail" / "runs" / "fsr0-false-stop").exists()

        self.assertEqual("create", created["action"])
        self.assertEqual("fresh", created["after_status"]["status"])
        # The sealed FSR-0 result remains historical evidence; FSR-1 now meets
        # the desired boundary without rewriting that captured baseline.
        baseline = load_json(BASELINE_PATH)
        baseline_row = next(row for row in baseline["fixtures"] if row["id"] == fixture["id"])
        self.assertEqual(fixture["current_expected"], baseline_row["current_result"])
        self.assertEqual("resolved", evidence["state"])
        self.assertEqual(fixture["desired_expected"]["implementation_owners"], requirement["implementation_owners"])
        self.assertEqual(fixture["desired_expected"]["proof_paths"], requirement["proof_paths"])
        self.assertEqual("literal-emitter", active_candidates["src/pages/eventGenerator/telemetryService.ts"]["role"])
        self.assertEqual("owner-resolved", evidence["investigation"]["stop_reason"])
        self.assertEqual("owner-resolved", evidence["investigation"]["decision_reason"])
        self.assertIsNone(evidence["investigation"]["resolution_failure_reason"])
        self.assertEqual("broad-limit-reached", evidence["investigation"]["limit_state"]["state"])
        self.assertGreater(evidence["investigation"]["limit_state"]["cache_validation_files_read"], 0)
        self.assertEqual(20, evidence["investigation"]["limit_state"]["broad_files_read"])
        self.assertGreaterEqual(evidence["investigation"]["limit_state"]["relationship_files_read"], 1)
        self.assertEqual(1, evidence["investigation"]["module_resolution"]["config_files_read"])
        self.assertEqual("configured", evidence["investigation"]["module_resolution"]["state"])
        self.assertIn(
            "module-alias-reference-resolved",
            evidence["investigation"]["module_resolution"]["reason_codes"],
        )
        self.assertEqual(0, start.returncode, start.stderr)
        self.assertEqual("reuse", start_payload["graph_lifecycle"]["action"])
        self.assertEqual("awaiting-approval", start_payload["planning_lock"]["status"])
        self.assertTrue(run_exists)

    def test_fsr0_preserves_safe_stop_for_two_equally_supported_renderers(self) -> None:
        fixture = self.fixture("typescript-genuine-renderer-ambiguity")
        with tempfile.TemporaryDirectory() as temporary:
            repository = Path(temporary)
            self.materialize(repository, fixture)
            navigator_graph_lifecycle.manage(repository, fixture["goal"], mode="auto")
            report = navigator.decide(
                fixture["goal"],
                repository,
                [],
                "tailtrail",
                detect_git_changes=False,
            )
            evidence = report["scope_evidence"]
            quality = report["scope_quality"]
            question = quality.get("question")
            actual = {
                "scope_state": evidence["state"],
                "implementation_owners": evidence["requirements"][0]["implementation_owners"],
                "stop_reason": evidence["investigation"]["stop_reason"],
                "scope_quality_status": quality["status"],
                "scope_question_options": question["options"] if question else [],
                "planning_lock_created": False,
            }
            start = subprocess.run(
                [
                    sys.executable,
                    (ROOT / "scripts" / "task-start.py").as_posix(),
                    fixture["goal"],
                    "--root",
                    repository.as_posix(),
                    "--format",
                    "json",
                    "--planning-run-id",
                    "fsr0-genuine-ambiguity",
                ],
                cwd=repository,
                text=True,
                capture_output=True,
                check=False,
            )
            run_exists = (repository / ".tailtrail" / "runs" / "fsr0-genuine-ambiguity").exists()

        expected = dict(fixture["current_expected"])
        expected["stop_reason"] = "multiple-evidence-backed-owners"
        self.assertEqual(expected, actual)
        self.assertEqual("ambiguous", evidence["state"])
        self.assertEqual(2, len(actual["implementation_owners"]))
        self.assertEqual(2, start.returncode, start.stderr)
        self.assertFalse(run_exists)

    def test_fsr0_fixtures_are_synthetic_and_identity_free(self) -> None:
        for fixture_id in (
            "typescript-alias-ui-literal-false-stop",
            "typescript-genuine-renderer-ambiguity",
        ):
            fixture = self.fixture(fixture_id)
            with self.subTest(fixture=fixture_id):
                self.assertEqual("synthetic", fixture["privacy"]["classification"])
                self.assertFalse(fixture["privacy"]["derived_from_proprietary_source"])
                self.assertFalse(fixture["privacy"]["contains_raw_prompt"])
                self.assertFalse(fixture["privacy"]["contains_raw_source"])
                self.assertFalse(fixture["privacy"]["contains_identity_fields"])


class NavigatorScopeEvidenceV2Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write(self, relative: str, body: bytes | str = "pass\n") -> Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(body, bytes):
            path.write_bytes(body)
        else:
            path.write_text(body, encoding="utf-8")
        return path

    def role(self, relative: str) -> tuple[str, tuple[str, ...]]:
        return navigator_scope.classify_repository_role(self.root, relative)

    def test_repository_roles_cover_source_test_docs_config_manifest_generated_and_vendor(self) -> None:
        self.write("src/service.py")
        self.write("tests/test_service.py")
        self.write("docs/service.md")
        self.write("config/service.yaml")
        self.write("pyproject.toml")
        self.write("generated/client.py")
        self.write("vendor/client.py")

        self.assertEqual(self.role("src/service.py")[0], "implementation-owner")
        self.assertEqual(self.role("tests/test_service.py")[0], "test")
        self.assertEqual(self.role("docs/service.md")[0], "documentation")
        self.assertEqual(self.role("config/service.yaml")[0], "configuration")
        self.assertEqual(self.role("pyproject.toml")[0], "manifest")
        self.assertEqual(self.role("generated/client.py")[0], "generated")
        self.assertEqual(self.role("vendor/client.py")[0], "generated")

    def test_tailtrail_source_scripts_are_production_but_installed_payload_is_managed(self) -> None:
        self.write("tailtrail-registry.json", "{}\n")
        self.write("package-manifest.json", "{}\n")
        self.write("scripts/tailtrail.py")
        self.write("scripts/requirement_discovery.py")
        self.assertEqual(self.role("scripts/requirement_discovery.py"), (
            "implementation-owner", ("tailtrail-source-checkout-production",)
        ))

        installed = Path(self.temporary.name) / "application"
        (installed / "tailtrail" / "scripts").mkdir(parents=True)
        (installed / "tailtrail" / ".tailtrail-install.json").write_text("{}\n", encoding="utf-8")
        (installed / "tailtrail" / "scripts" / "navigator.py").write_text("pass\n", encoding="utf-8")
        self.assertEqual(
            navigator_scope.classify_repository_role(installed, "tailtrail/scripts/navigator.py")[0],
            "managed-tooling",
        )

    def test_path_normalization_is_cross_platform_case_preserving_and_unicode_stable(self) -> None:
        self.assertEqual(
            navigator_scope.normalize_repository_path(self.root, r"Src\Order\Service.py"),
            ("Src/Order/Service.py", None),
        )
        decomposed = "docs/Cafe\u0301.md"
        self.assertEqual(
            navigator_scope.normalize_repository_path(self.root, decomposed),
            ("docs/Caf\u00e9.md", None),
        )
        self.assertEqual(navigator_scope.normalize_repository_path(self.root, "../secret.py")[1], "path-traversal-rejected")
        self.assertEqual(navigator_scope.normalize_repository_path(self.root, r"C:\secret.py")[1], "absolute-path-rejected")

    def test_symlink_binary_non_utf8_oversized_credentials_and_traversal_fail_closed(self) -> None:
        self.write("src/binary.py", b"abc\x00def")
        self.write("src/non_utf8.py", b"\xff\xfe")
        self.write("src/huge.py", b"x" * (navigator_scope.LIMITS["max_file_bytes"] + 1))
        self.write(".env", "PASSWORD=hidden\n")
        outside = Path(self.temporary.name).parent / "tailtrail-ns2-outside.txt"
        outside.write_text("outside\n", encoding="utf-8")
        link = self.root / "src" / "link.py"
        link.parent.mkdir(parents=True, exist_ok=True)
        symlink_created = True
        try:
            link.symlink_to(outside)
        except OSError:
            # Windows without admin rights/Developer Mode cannot create symlinks
            # (WinError 1314). Skip only the symlink assertion; the remaining
            # fail-closed checks below are unaffected. On Linux CI this runs.
            symlink_created = False
        finally:
            outside.unlink(missing_ok=True)

        if symlink_created:
            self.assertEqual(navigator_scope.safe_text(self.root, "src/link.py")[1], "symlink-rejected")

        self.assertEqual(navigator_scope.safe_text(self.root, "src/binary.py")[1], "binary-file-rejected")
        self.assertEqual(navigator_scope.safe_text(self.root, "src/non_utf8.py")[1], "non-utf8-file-rejected")
        self.assertEqual(navigator_scope.safe_text(self.root, "src/huge.py")[1], "oversized-file-rejected")
        self.assertEqual(navigator_scope.safe_text(self.root, ".env")[1], "sensitive-path-rejected")
        self.assertEqual(navigator_scope.safe_text(self.root, "../../secret.py")[1], "path-traversal-rejected")
        unsafe_candidates = navigator_scope.candidates_from_seeds(
            self.root,
            [
                navigator_scope.seed("src/binary.py", "explicit-path", "user-provided-path"),
                navigator_scope.seed("src/huge.py", "explicit-path", "user-provided-path"),
                navigator_scope.seed(".env", "explicit-path", "user-provided-path"),
            ],
            ["implementation"],
        )
        self.assertTrue(all(item["status"] == "rejected" for item in unsafe_candidates))

    def test_lexical_discovery_returns_typed_seeds_not_selected_paths(self) -> None:
        self.write("src/address_validation.py", "def validate_address(value):\n    return bool(value)\n")
        seeds = navigator_discovery.goal_discovered_paths(
            self.root,
            "address validation",
            query_terms=["address", "validation"],
        )

        self.assertTrue(seeds)
        self.assertTrue(all(isinstance(item, dict) for item in seeds))
        self.assertTrue(all(item["seed_sources"] for item in seeds))
        candidates = navigator_scope.candidates_from_seeds(self.root, seeds, ["bug"])
        self.assertEqual(candidates[0]["status"], "inspection-only")
        self.assertIn("lexical-seed-needs-relationship-evidence", candidates[0]["reason_codes"])

    def test_explicit_path_is_an_owner_candidate_until_investigation_qualifies_it(self) -> None:
        self.write("src/service.py")
        self.write("tests/test_service.py")
        seeds = [
            navigator_scope.seed("src/service.py", "explicit-path", "user-provided-path"),
            navigator_scope.seed("tests/test_service.py", "lexical-path", "query-term-in-path"),
        ]
        rows = {row["path"]: row for row in navigator_scope.candidates_from_seeds(self.root, seeds, ["bug"])}

        self.assertEqual(rows["src/service.py"]["status"], "inspection-only")
        self.assertEqual(rows["src/service.py"]["confidence"], "high")
        self.assertIn("explicit-path-owner-candidate", rows["src/service.py"]["reason_codes"])
        self.assertEqual(rows["tests/test_service.py"]["status"], "proof-only")
        for row in rows.values():
            self.assertIn(row["role"], navigator_scope.ROLES)
            self.assertIn(row["status"], navigator_scope.STATUSES)
            self.assertTrue(row["reason_codes"])
            self.assertTrue(row["evidence_provenance"])

        frames = requirement_discovery.frames("change service behavior")
        investigated, _, evidence = navigator_scope.investigate(
            self.root, frames, list(rows.values()), ["bug"]
        )
        investigated_by_path = {row["path"]: row for row in investigated}
        self.assertEqual("resolved", evidence["state"])
        self.assertEqual("included", investigated_by_path["src/service.py"]["status"])
        self.assertIn(
            "owner-qualified-by-explicit-user-scope",
            investigated_by_path["src/service.py"]["reason_codes"],
        )
        self.assertEqual(
            "explicit-user-scope",
            evidence["ownership_selection"]["selected_rule"],
        )

    def test_qa_test_candidate_without_strong_edges_is_not_high_confidence(self) -> None:
        # Same-module-name yields a medium tested-by edge only. A test-role
        # row must not claim high confidence without a strong edge, matching
        # the production-owner rule.
        self.write("src/service.py", "def serve():\n    return True\n")
        self.write("tests/test_service.py", "def test_serve():\n    assert True\n")
        seeds = [
            navigator_scope.seed("src/service.py", "lexical-path", "query-term-in-path"),
            navigator_scope.seed("tests/test_service.py", "lexical-path", "query-term-in-path"),
        ]
        candidates = navigator_scope.candidates_from_seeds(self.root, seeds, ["qa"])
        frames = requirement_discovery.frames("Summarize test coverage.")
        investigated, edges, _ = navigator_scope.investigate(
            self.root, frames, candidates, ["qa"]
        )
        by_path = {row["path"]: row for row in investigated}
        test_row = by_path["tests/test_service.py"]
        strengths = {
            edge["strength"]
            for edge in edges
            if edge["edge_id"] in set(test_row["evidence_edge_ids"])
        }
        self.assertEqual(test_row["role"], "test")
        self.assertTrue(test_row["evidence_edge_ids"])
        self.assertNotIn("strong", strengths)
        self.assertNotEqual(test_row["confidence"], "high")

    def test_schema_and_fingerprint_are_deterministic(self) -> None:
        self.write("src/service.py")
        seeds = [navigator_scope.seed("src/service.py", "explicit-path", "user-provided-path")]
        candidates = navigator_scope.candidates_from_seeds(self.root, seeds, ["implementation"])
        frames = requirement_discovery.frames("Add service validation.")
        first = navigator_scope.evidence_document(self.root, "Add service validation.", frames, candidates)
        second = navigator_scope.evidence_document(self.root, "Add service validation.", frames, list(reversed(candidates)))
        schema = load_json(EVIDENCE_SCHEMA_PATH)

        self.assertEqual(first, second)
        self.assertTrue(navigator_scope.verify_decision_fingerprint(first))
        self.assertEqual(contracts.validate_document(first, schema), [])
        self.assertNotIn("Add service validation.", json.dumps(first))


class NavigatorScopeInvestigationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write(self, relative: str, body: str) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")

    def ambiguous_host_case(self, host: str = "codex") -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        fixture = load_json(FIXTURE_ROOT / "typescript-genuine-renderer-ambiguity.json")
        for relative, body in fixture["repository_files"].items():
            self.write(relative, body)
        evidence = navigator.decide(
            fixture["goal"], self.root, [], "tailtrail", detect_git_changes=False
        )["scope_evidence"]
        packet = navigator_scope.host_reasoning_packet(evidence)
        candidates = {row["path"]: row for row in packet["candidates"]}
        requirement = packet["requirements"][0]
        chosen = packet["route"]["eligible_candidates"][0]["path"]
        alternative = packet["route"]["eligible_candidates"][1]["path"]
        inspection = next(
            row["path"] for row in packet["candidates"]
            if row["role"] == "literal-emitter"
        )
        material = [(chosen, "implementation-owner"), (inspection, "inspection")]
        claims = [{
            "path": path,
            "candidate_id": candidates[path]["candidate_id"],
            "content_fingerprint": candidates[path]["content_fingerprint"],
            "claim_role": role,
            "evidence_edge_ids": candidates[path]["evidence_edge_ids"],
        } for path, role in material]
        proposal = {
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
                "preservation_boundaries": ["Preserve the alternate renderer unless its runtime path is selected."],
                "evidence_edge_ids": sorted({edge for claim in claims for edge in claim["evidence_edge_ids"]}),
                "confidence": "high",
                "decision_reasons": ["The request context selects one strongly evidenced renderer."],
                "alternatives": [alternative],
                "uncertainties": [],
            }],
            "private_reasoning_excluded": True,
        }
        return evidence, packet, proposal

    def test_shared_static_extractor_covers_supported_relationship_languages(self) -> None:
        fixtures = {
            "tests/test_owner.py": (
                "from app.owner import validate\n"
                "import importlib.util\n"
                "SPEC = importlib.util.spec_from_file_location('owner', 'app/owner.py')\n",
                {"imports": "app.owner", "loaders": "app/owner.py"},
            ),
            "web/view.ts": (
                "import {render} from './renderer'; const x = require('./legacy');\n",
                {"imports": "./renderer"},
            ),
            "src/main/java/acme/App.java": (
                "package acme;\nimport acme.service.Owner;\nclass App {}\n",
                {"imports": "acme.service.Owner", "registrations": "acme"},
            ),
            "src/App.cs": (
                "namespace Acme.App;\nusing Acme.Services;\npublic class App {}\n",
                {"imports": "Acme.Services", "registrations": "Acme.App"},
            ),
            "cmd/app/main.go": (
                'package main\nimport "example.com/acme/owner"\nfunc main() {}\n',
                {"imports": "example.com/acme/owner", "registrations": "main"},
            ),
        }
        for relative, (body, expected) in fixtures.items():
            with self.subTest(path=relative):
                self.write(relative, body)
                facts = code_relationships.extract(self.root / relative, self.root, body)
                for group, value in expected.items():
                    self.assertIn(value, {row["value"] for row in facts[group]})

    def test_fsr3_extractor_emits_sanitized_typed_behavior_facts(self) -> None:
        body = (
            "import { useState } from 'react';\n"
            "import { getTrace as loadTrace } from '@/trace/service';\n"
            "export function TracePage() {\n"
            "  const [traceError, setTraceError] = useState('');\n"
            "  const refresh = async () => {\n"
            "    try { await loadTrace(); } catch (error) { setTraceError(error.message); }\n"
            "  };\n"
            "  return <main>{traceError && <aside>{traceError}</aside>}</main>;\n"
            "}\n"
        )
        self.write("src/TracePage.tsx", body)

        facts = code_relationships.extract(
            self.root / "src" / "TracePage.tsx", self.root, body
        )
        behavior = facts["behavior"]
        kinds = {row["kind"] for row in behavior}

        self.assertTrue({
            "import-binding", "call", "catch-binding", "state-binding",
            "state-write", "render-use",
        }.issubset(kinds))
        self.assertIn(
            {"kind": "import-binding", "value": "loadTrace", "line": 2, "detail": "@/trace/service"},
            behavior,
        )
        self.assertNotIn("setTraceError(error.message)", json.dumps(behavior))

    def test_python_loader_extracts_static_root_path_chain(self) -> None:
        body = (
            "import importlib.util\nfrom pathlib import Path\n"
            "ROOT = Path(__file__).resolve().parents[1]\n"
            "SPEC = importlib.util.spec_from_file_location(\n"
            "    'requirements', ROOT / 'scripts' / 'requirement_discovery.py'\n"
            ")\n"
        )
        self.write("scripts/planning_lock.py", body)
        facts = code_relationships.extract(
            self.root / "scripts" / "planning_lock.py",
            self.root,
            body,
        )
        self.assertIn(
            "scripts/requirement_discovery.py",
            {row["value"] for row in facts["loaders"]},
        )

    def test_ambiguous_same_name_monorepo_and_no_owner_fail_closed(self) -> None:
        self.write("services/a/parser.py", "def parse_multiline(value):\n    return value\n")
        self.write("services/b/parser.py", "def parse_multiline(value):\n    return value\n")
        self.write("tests/test_parser.py", "# parser multiline proof\n")
        frames = requirement_discovery.frames("fix parser multiline splitting")
        seeds = navigator_discovery.goal_discovered_paths(
            self.root, "fix parser multiline splitting", limit=3,
            query_terms=frames[0]["query_terms"],
        )
        candidates = navigator_scope.candidates_from_seeds(self.root, seeds, ["bug"])
        _, _, investigation = navigator_scope.investigate(self.root, frames, candidates, ["bug"])
        self.assertEqual(investigation["state"], "ambiguous")

        with tempfile.TemporaryDirectory() as temporary:
            no_owner = Path(temporary)
            (no_owner / "tests").mkdir()
            (no_owner / "tests" / "test_requirement.py").write_text("# requirement splitting\n", encoding="utf-8")
            seeds = [navigator_scope.seed("tests/test_requirement.py", "lexical-path", "query-term-in-path")]
            candidates = navigator_scope.candidates_from_seeds(no_owner, seeds, ["bug"])
            rows, _, investigation = navigator_scope.investigate(no_owner, frames, candidates, ["bug"])
        self.assertEqual(investigation["state"], "unresolved")
        self.assertEqual(rows[0]["status"], "excluded")

    def test_fsr2_structural_and_action_terms_rank_reads_but_never_qualify_owners(self) -> None:
        self.write("src/pages/account/AccountPage.tsx", "export function AccountPage() { return <main>Account</main>; }\n")
        self.write("src/pages/dashboard/DashboardPage.tsx", "export function DashboardPage() { return <main>Dashboard</main>; }\n")
        self.write("src/components/RemoveButton.tsx", "export function RemoveButton() { return <button>Remove</button>; }\n")
        goal = "remove the banner from the page"
        frames = requirement_discovery.frames(goal)
        seeds = navigator_discovery.goal_discovered_paths(
            self.root,
            goal,
            query_terms=frames[0]["query_terms"],
        )
        candidates = navigator_scope.candidates_from_seeds(self.root, seeds, ["bug"])

        rows, edges, investigation = navigator_scope.investigate(self.root, frames, candidates, ["bug"])
        evidence = navigator_scope.evidence_document(
            self.root, goal, frames, rows, edges=edges, investigation=investigation
        )
        quality = navigator_scope.assess_scope_quality(self.root, goal, ["bug"], evidence)

        self.assertEqual("unresolved", evidence["state"])
        self.assertEqual([], evidence["requirements"][0]["implementation_owners"])
        self.assertEqual([], quality["question"]["options"])
        self.assertEqual(
            "scope-question-has-no-supported-owner-options",
            quality["question_validation"]["reason_codes"][0],
        )
        self.assertIsNone(investigation["ownership_selection"]["selected_rule"])
        self.assertEqual(0, investigation["ownership_selection"]["qualified_candidates"])
        self.assertNotIn("query-matched-definition-symbol", {
            reason
            for edge in edges
            for reason in edge["reason_codes"]
        })

    def test_fsr2_definition_only_match_cannot_qualify_owner(self) -> None:
        self.write(
            "src/order_quantity.py",
            "def validate_quantity(value):\n    return value > 0\n",
        )
        self.write(
            "src/pages/DashboardPage.py",
            "def render_page():\n    return 'dashboard'\n",
        )
        goal = "reject zero order quantity while preserving positive quantities"
        frames = requirement_discovery.frames(goal)
        seeds = navigator_discovery.goal_discovered_paths(
            self.root, goal, query_terms=frames[0]["query_terms"]
        )
        candidates = navigator_scope.candidates_from_seeds(self.root, seeds, ["bug"])

        rows, edges, investigation = navigator_scope.investigate(self.root, frames, candidates, ["bug"])
        owners = [row["path"] for row in rows if row["status"] == "included"]

        # A name match with no behavior, caller, or proof edge must not
        # mint an owner; the host is asked for a concrete clue instead.
        self.assertEqual([], owners)
        self.assertIsNone(investigation["ownership_selection"]["selected_rule"])
        self.assertEqual(0, investigation["ownership_selection"]["qualified_candidates"])
        # Definition evidence still prioritizes bounded reads and stays
        # diagnostic for the question path.
        self.assertIn("query-matched-definition-symbol", {
            reason
            for edge in edges
            for reason in edge["reason_codes"]
        })

    def test_fsr2_ui_literal_emitter_cannot_override_renderer_requirement(self) -> None:
        goal = "in the status page there is a banner Trace endpoint is not configured. we need to remove it"
        self.write(
            "src/traceService.ts",
            "export function traceWarning() { throw new Error('Trace endpoint is not configured.'); }\n",
        )
        report = navigator.decide(
            goal,
            self.root,
            ["src/traceService.ts"],
            "tailtrail",
            detect_git_changes=False,
        )
        evidence = report["scope_evidence"]
        emitter = next(row for row in evidence["candidates"] if row["path"] == "src/traceService.ts")

        self.assertEqual("unresolved", evidence["state"])
        self.assertEqual([], evidence["requirements"][0]["implementation_owners"])
        self.assertEqual("literal-emitter", emitter["role"])
        self.assertEqual("inspection-only", emitter["status"])
        self.assertIn("literal-emitter-is-not-ui-visibility-owner", emitter["reason_codes"])
        self.assertNotIn("bounded-static-owner-evidence", emitter["reason_codes"])

    def test_owner_expansion_includes_registration_caller_and_configuration_reference(self) -> None:
        self.write("src/owner.py", "def owner():\n    return True\n")
        self.write("src/registry.py", "from src.owner import owner\nregister(owner)\n")
        self.write("config/runtime.yaml", "handler: src.owner\n")
        frames = requirement_discovery.frames("change owner behavior")
        candidates = navigator_scope.candidates_from_seeds(
            self.root,
            [navigator_scope.seed("src/owner.py", "lexical-path", "query-term-in-path")],
            ["implementation"],
        )

        rows, edges, investigation = navigator_scope.investigate(
            self.root, frames, candidates, ["implementation"]
        )
        by_path = {row["path"]: row for row in rows}

        self.assertEqual(investigation["state"], "resolved")
        self.assertEqual(by_path["src/owner.py"]["status"], "included")
        self.assertEqual(by_path["src/registry.py"]["status"], "inspection-only")
        self.assertEqual(by_path["src/registry.py"]["role"], "caller")
        self.assertEqual(by_path["config/runtime.yaml"]["status"], "inspection-only")
        self.assertEqual(by_path["config/runtime.yaml"]["role"], "configuration")
        self.assertIn("registered-by", {edge["kind"] for edge in edges})
        self.assertIn("configures-owner", {edge["kind"] for edge in edges})

    def test_investigation_obeys_injected_file_and_byte_caps(self) -> None:
        for index in range(8):
            self.write(f"src/owner_{index}.py", f"def owner_{index}():\n    return 'scope'\n")
        frames = requirement_discovery.frames("fix owner scope")
        candidates = navigator_scope.candidates_from_seeds(
            self.root,
            [navigator_scope.seed("src/owner_0.py", "lexical-path", "query-term-in-path")],
            ["bug"],
        )
        limits = navigator_scope.InvestigationLimits(
            candidate_files=8,
            initial_file_reads=1,
            escalation_file_reads=1,
            relationship_file_reads=0,
            max_file_bytes=1024,
            max_total_read_bytes=2048,
            relationship_hops=1,
            retained_owners=1,
        )
        rows, edges, investigation = navigator_scope.investigate(
            self.root, frames, candidates, ["bug"], limits=limits
        )
        self.assertLessEqual(investigation["files_read"], 2)
        self.assertLessEqual(investigation["bytes_read"], 2048)
        self.assertEqual(investigation["limits"], limits.as_dict())
        evidence = navigator_scope.evidence_document(
            self.root,
            "fix owner scope",
            frames,
            rows,
            edges=edges,
            investigation=investigation,
        )
        self.assertEqual(evidence["limits"], limits.as_dict())
        self.assertEqual(navigator_scope.host_reasoning_packet(evidence)["limits"], limits.as_dict())

    def test_fsr4_relationship_reserve_resolves_after_broad_limit(self) -> None:
        goal = (
            "in the status page there is a banner Trace endpoint is not configured. "
            "we need to remove it"
        )
        self.write(
            "src/traceService.ts",
            "export function traceWarning() { return 'Trace endpoint is not configured.'; }\n",
        )
        self.write(
            "src/StatusPage.tsx",
            "import { traceWarning } from './traceService';\n"
            "export function StatusPage() { const warning = traceWarning(); "
            "return <main>{warning && <aside>{warning}</aside>}</main>; }\n",
        )
        frames = requirement_discovery.frames(goal)
        candidates = navigator_scope.candidates_from_seeds(
            self.root,
            [
                navigator_scope.seed(
                    "src/traceService.ts", "lexical-body", "exact-phrase-in-bounded-body"
                ),
                navigator_scope.seed(
                    "src/StatusPage.tsx", "lexical-path", "query-term-in-path"
                ),
            ],
            ["bug"],
        )
        limits = navigator_scope.InvestigationLimits(
            initial_file_reads=1,
            escalation_file_reads=0,
            relationship_file_reads=1,
        )

        rows, _, investigation = navigator_scope.investigate(
            self.root, frames, candidates, ["bug"], limits=limits
        )

        self.assertEqual(
            ["src/StatusPage.tsx"],
            [row["path"] for row in rows if row["status"] == "included"],
        )
        self.assertEqual("resolved", investigation["state"])
        self.assertEqual("owner-resolved", investigation["decision_reason"])
        self.assertEqual("broad-limit-reached", investigation["limit_state"]["state"])
        self.assertEqual(1, investigation["limit_state"]["broad_files_read"])
        self.assertEqual(1, investigation["limit_state"]["relationship_files_read"])

    def test_fsr4_limit_before_chain_reports_missing_evidence_not_capacity_as_decision(self) -> None:
        goal = (
            "in the status page there is a banner Trace endpoint is not configured. "
            "we need to remove it"
        )
        self.write(
            "src/traceService.ts",
            "export function traceWarning() { return 'Trace endpoint is not configured.'; }\n",
        )
        self.write(
            "src/StatusPage.tsx",
            "import { traceWarning } from './traceService';\n"
            "export function StatusPage() { const warning = traceWarning(); "
            "return <main>{warning && <aside>{warning}</aside>}</main>; }\n",
        )
        frames = requirement_discovery.frames(goal)
        candidates = navigator_scope.candidates_from_seeds(
            self.root,
            [navigator_scope.seed(
                "src/traceService.ts", "lexical-body", "exact-phrase-in-bounded-body"
            )],
            ["bug"],
        )
        limits = navigator_scope.InvestigationLimits(
            initial_file_reads=1,
            escalation_file_reads=0,
            relationship_file_reads=0,
        )

        rows, edges, investigation = navigator_scope.investigate(
            self.root, frames, candidates, ["bug"], limits=limits
        )
        evidence = navigator_scope.evidence_document(
            self.root, goal, frames, rows, edges=edges, investigation=investigation
        )
        quality = navigator_scope.assess_scope_quality(self.root, goal, ["bug"], evidence)

        self.assertEqual("blocked-by-limits", investigation["state"])
        self.assertEqual("renderer-caller-edge-not-found", investigation["decision_reason"])
        self.assertEqual(
            "renderer-caller-edge-not-found", investigation["resolution_failure_reason"]
        )
        self.assertEqual("relationship-limit-reached", investigation["limit_state"]["state"])
        self.assertEqual("renderer-caller-edge-not-found", quality["primary_reason"])
        self.assertNotIn("investigation-file-read-limit-reached", quality["reason_codes"])
        self.assertEqual([], quality["question"]["options"])

    def test_fsr4_scope_question_caps_and_validates_strong_owner_options(self) -> None:
        changed: list[str] = []
        for index in range(5):
            path = f"src/parser_{index}.py"
            changed.append(path)
            self.write(path, f"def parse_multiline_{index}(value):\n    return value\n")

        report = navigator.decide(
            "fix parser multiline splitting",
            self.root,
            changed,
            "tailtrail",
            detect_git_changes=False,
        )
        evidence = report["scope_evidence"]
        quality = report["scope_quality"]
        question = quality["question"]

        self.assertEqual("ambiguous", evidence["state"])
        self.assertEqual(3, len(question["options"]))
        self.assertEqual(question["options"], [row["path"] for row in question["option_evidence"]])
        self.assertEqual("validated", quality["question_validation"]["state"])
        self.assertEqual(5, quality["question_validation"]["eligible_options"])
        self.assertTrue(quality["question_validation"]["truncated"])
        edge_ids = {row["edge_id"] for row in evidence["edges"]}
        self.assertTrue(all(
            set(row["evidence_edge_ids"]) <= edge_ids
            for row in question["option_evidence"]
        ))
        self.assertEqual(
            [], contracts.validate_document(quality, load_json(SCOPE_QUALITY_SCHEMA_PATH))
        )

    def test_graph_cache_is_reused_only_while_root_hashes_and_inventory_are_fresh(self) -> None:
        self.write("src/owner.py", "def owner():\n    return True\n")
        self.write("tests/test_owner.py", "from src.owner import owner\n")
        source = self.root / "src" / "owner.py"
        cache = {
            "schema_version": "1",
            "root": self.root.as_posix(),
            "source_files": {
                "src/owner.py": {"sha256": hashlib.sha256(source.read_bytes()).hexdigest()}
            },
            "watch_files": {},
            "inventory": navigator_scope.inventory_snapshot(self.root),
            "graph": {
                "suggested_read_order": ["src/owner.py", "tests/test_owner.py"],
                "likely_callers": [],
                "likely_tests": ["tests/test_owner.py"],
                "nearby_manifests": [],
            },
        }
        cache_path = self.root / "tailtrail-meta" / "code-graph-cache.json"
        cache_path.parent.mkdir()
        cache_path.write_text(json.dumps(cache), encoding="utf-8")
        original = cache_path.read_bytes()

        paths, status = navigator_scope._cache_evidence(self.root, navigator_scope.DEFAULT_LIMITS)
        self.assertEqual(status["status"], "fresh")
        self.assertEqual(paths, ["src/owner.py", "tests/test_owner.py"])
        source.write_text("def owner():\n    return False\n", encoding="utf-8")
        paths, status = navigator_scope._cache_evidence(self.root, navigator_scope.DEFAULT_LIMITS)
        self.assertEqual(paths, [])
        self.assertEqual(status["status"], "stale")
        self.assertEqual(cache_path.read_bytes(), original)

    def test_missing_graph_builds_bounded_ephemeral_ui_evidence_and_selects_handler_owner(self) -> None:
        fixture = load_json(FIXTURE_ROOT / "ui-handler-import-ownership.json")
        for relative, body in fixture["repository_files"].items():
            self.write(relative, body)

        report = navigator.decide(
            fixture["goal"], self.root, [], "tailtrail", detect_git_changes=False
        )
        evidence = report["scope_evidence"]
        requirement = evidence["requirements"][0]
        candidates = {row["path"]: row for row in evidence["candidates"]}

        self.assertEqual(evidence["state"], "resolved")
        self.assertEqual(requirement["implementation_owners"], [fixture["expected_owner"]])
        self.assertEqual(report["scope_quality"]["status"], "passed")
        self.assertIsNone(report["scope_quality"]["question"])
        self.assertEqual(evidence["investigation"]["stop_reason"], "owner-resolved")
        self.assertLessEqual(
            evidence["investigation"]["files_read"],
            navigator_scope.DEFAULT_LIMITS.initial_file_reads,
        )
        self.assertEqual(evidence["investigation"]["cache"]["status"], "missing")
        self.assertIn(
            "bounded-ephemeral-graph-built",
            evidence["investigation"]["cache"]["reason_codes"],
        )
        self.assertIn(
            "behavior-specific-owner-evidence",
            candidates[fixture["expected_owner"]]["reason_codes"],
        )
        self.assertTrue(all(
            path not in requirement["implementation_owners"]
            for path in fixture["expected_helpers"] + fixture["unrelated_candidates"]
        ))
        self.assertEqual(candidates["src/components/Button.cy.tsx"]["role"], "test")
        self.assertFalse((self.root / "tailtrail-meta" / "code-graph-cache.json").exists())

    def test_ui_visibility_change_selects_renderer_not_literal_emitter(self) -> None:
        goal = (
            "in the push to dom page after the push to dom there is a banner "
            "CloudWatch trace endpoint is not configured. we need to remove it"
        )
        self.write(
            "src/pages/pushToDom/deploymentService.ts",
            "export function cloudWatchWarning() { return 'CloudWatch trace endpoint is not configured.'; }\n",
        )
        self.write(
            "src/pages/pushToDom/PushToDomPage.tsx",
            "import { cloudWatchWarning } from './deploymentService';\n"
            "export function PushToDomPage() {\n"
            "  const warning = cloudWatchWarning();\n"
            "  return <section><h1>Push to DOM</h1>{warning && <div role='alert'>{warning}</div>}</section>;\n"
            "}\n",
        )

        report = navigator.decide(goal, self.root, [], "tailtrail", detect_git_changes=False)
        requirement = report["scope_evidence"]["requirements"][0]
        candidates = {row["path"]: row for row in report["scope_evidence"]["candidates"]}

        self.assertEqual([row["statement"] for row in report["requirement_query_frame"]["requirements"]], [
            'Remove the "CloudWatch trace endpoint is not configured." banner from the push to dom page.'
        ])
        self.assertEqual(requirement["implementation_owners"], ["src/pages/pushToDom/PushToDomPage.tsx"])
        self.assertEqual(candidates["src/pages/pushToDom/deploymentService.ts"]["role"], "literal-emitter")
        self.assertEqual(candidates["src/pages/pushToDom/deploymentService.ts"]["status"], "inspection-only")

    def test_ui_visibility_owner_is_stable_across_literal_presentation_variants(self) -> None:
        self.write(
            "src/pages/pushToDom/deploymentService.ts",
            "export async function getDeploymentTrace() { "
            "throw new Error('CloudWatch trace endpoint is not configured.'); }\n",
        )
        self.write(
            "src/pages/pushToDom/PushToDomPage.tsx",
            "import { useState } from 'react';\n"
            "import { getDeploymentTrace } from './deploymentService';\n"
            "export function PushToDomPage() {\n"
            "  const [traceError, setTraceError] = useState('');\n"
            "  async function refreshTrace() {\n"
            "    try { await getDeploymentTrace(); }\n"
            "    catch (error) { setTraceError(error instanceof Error ? error.message : 'Trace unavailable'); }\n"
            "  }\n"
            "  return <main><h1>Push to DOM</h1><button onClick={refreshTrace}>Refresh</button>"
            "{traceError && <aside>{traceError}</aside>}</main>;\n"
            "}\n",
        )
        self.write(
            "src/pages/pushToDom/PushToDomPage.cy.tsx",
            "import { PushToDomPage } from './PushToDomPage';\n"
            "it('does not show the unavailable trace banner', () => void PushToDomPage);\n",
        )
        variants = [
            "CloudWatch trace endpoint is not configured.",
            "*CloudWatch trace endpoint is not configured.*",
            "_CloudWatch trace endpoint is not configured._",
            "**CloudWatch trace endpoint is not configured.**",
            "__CloudWatch trace endpoint is not configured.__",
            "`CloudWatch trace endpoint is not configured.`",
            "'CloudWatch trace endpoint is not configured.'",
            '"CloudWatch trace endpoint is not configured."',
        ]

        reports = [
            navigator.decide(
                f"in the push to dom page there is a banner {literal} we need to remove it",
                self.root,
                [],
                "tailtrail",
                detect_git_changes=False,
            )
            for literal in variants
        ]

        for report in reports:
            evidence = report["scope_evidence"]
            requirement = evidence["requirements"][0]
            self.assertEqual("resolved", evidence["state"])
            self.assertEqual(
                ["src/pages/pushToDom/PushToDomPage.tsx"],
                requirement["implementation_owners"],
            )
            self.assertEqual(
                ["src/pages/pushToDom/deploymentService.ts"],
                requirement["inspection_paths"],
            )
            self.assertEqual(
                ["src/pages/pushToDom/PushToDomPage.cy.tsx"],
                requirement["proof_paths"],
            )
            self.assertEqual("complete", evidence["investigation"]["behavior_chains"]["state"])
            self.assertNotEqual(
                "implementation-owner-evidence-not-found-before-limit",
                evidence["investigation"]["decision_reason"],
            )

    def test_host_assisted_banner_plan_traces_renderer_and_existing_page_proof(self) -> None:
        goal = (
            "in the push to dom page there is a banner "
            "CloudWatch trace endpoint is not configured. we need to remove it"
        )
        self.write(
            "src/pages/pushToDom/deploymentService.ts",
            "export async function getDeploymentTrace() { "
            "throw new Error('CloudWatch trace endpoint is not configured.'); }\n",
        )
        self.write(
            "src/pages/pushToDom/PushToDomPage.tsx",
            "import { useState } from 'react';\n"
            "import { getDeploymentTrace } from './deploymentService';\n"
            "export function PushToDomPage() {\n"
            "  const [traceError, setTraceError] = useState('');\n"
            "  async function refreshTrace() {\n"
            "    try { await getDeploymentTrace(); }\n"
            "    catch (error) { setTraceError(error instanceof Error ? error.message : 'Trace unavailable'); }\n"
            "  }\n"
            "  return <main><button onClick={refreshTrace}>Refresh</button>"
            "{traceError && <aside>{traceError}</aside>}</main>;\n"
            "}\n",
        )
        self.write(
            "src/pages/pushToDom/PushToDomPage.cy.tsx",
            "import { PushToDomPage } from './PushToDomPage';\n"
            "it('preserves deployment feedback', () => void PushToDomPage);\n",
        )
        self.write(
            "package.json",
            '{"scripts":{"cypress:component":"cypress run --component","lint":"eslint . --cache","build":"tsc --noEmit"}}\n',
        )
        proposal = {
            "schema_version": "1",
            "type": "tailtrail-host-requirement-interpretation",
            "host": "codex",
            "goal": goal,
            "private_reasoning_excluded": True,
            "clauses": [
                {"clause_id": "C-01", "role": "context", "text": "in the push to dom page there is a banner CloudWatch trace endpoint is not configured."},
                {"clause_id": "C-02", "role": "outcome", "text": "we need to remove it"},
            ],
            "requirements": [{
                "display_id": "REQ-01",
                "statement": "Remove the CloudWatch trace endpoint configuration banner from the Push to DOM page.",
                "kind": "change",
                "source_clause_ids": ["C-01", "C-02"],
                "intent_terms": ["push", "dom", "remove"],
                "quoted_literals": ["CloudWatch trace endpoint is not configured."],
                "intent_class": "general",
                "confidence": "high",
            }],
            "material_questions": [],
        }
        interpreted = requirement_discovery.interpretation(goal, proposal, "codex")

        report = task_start.build_report(
            goal,
            self.root,
            [],
            "tailtrail",
            aidlc_mode="lite",
            requirement_interpretation=interpreted,
        )
        plan = report["navigator"]
        scope = plan["scope_evidence"]["requirements"][0]
        selected = {row["name"] for row in report["guided_delivery"]["selected"]}
        rendered = task_start.verbose_start_report(report)
        workflow_binding = task_start.workflow_start_integration.scope_binding(report)
        task_start.planning_lock.create(self.root, goal, "ui-existing-proof-authority")
        task_start.planning_lock.save_start_report(self.root, "ui-existing-proof-authority", report)
        activated = task_start.planning_lock.activate(self.root, "ui-existing-proof-authority", True)

        self.assertEqual("ui-visibility", plan["requirement_query_frame"]["requirements"][0]["intent_class"])
        self.assertEqual(["src/pages/pushToDom/PushToDomPage.tsx"], scope["implementation_owners"])
        self.assertEqual(["src/pages/pushToDom/deploymentService.ts"], scope["inspection_paths"])
        self.assertEqual(["src/pages/pushToDom/PushToDomPage.cy.tsx"], scope["proof_paths"])
        self.assertEqual("complete", plan["scope_evidence"]["investigation"]["behavior_chains"]["state"])
        self.assertEqual(["implementation"], plan["task_types"])
        self.assertNotIn("Architecture Fitness Harness", selected)
        self.assertIn("over-broad UI feedback suppression", plan["risk_indicators"])
        self.assertIn(
            "Scope state: `resolved` - 1 high-confidence implementation owner covers `REQ-01`",
            rendered,
        )
        self.assertIn("strong relationship edge", rendered)
        self.assertIn("distinct relationship type(s)", rendered)
        self.assertIn("**Relationship types:**", rendered)
        self.assertNotRegex(rendered, r"\+\d+ more")
        self.assertIn("no unresolved owner conflict remains", rendered)
        self.assertIn("Do not render the named banner or message", rendered)
        self.assertIn("other genuine errors", rendered)
        self.assertNotIn("The user-facing scenario must be clarified", rendered)
        self.assertIn("primary flow remains usable", rendered)
        self.assertIn("src/pages/pushToDom/PushToDomPage.cy.tsx", rendered)
        self.assertNotIn("resolve the exact project-owned component or behaviour test", rendered)
        self.assertIn("use the approved page/component proof", rendered)
        self.assertNotIn("map impacted paths", rendered)
        self.assertNotIn("run selected computational checks", rendered)
        self.assertIn("npm run lint", rendered)
        self.assertIn("npm run build", rendered)
        self.assertIn("## Testing plan", rendered)
        test_precision = next(
            row
            for row in report["guided_delivery"]["selected"]
            if row["name"] == "Test Precision Planner"
        )
        self.assertEqual(
            "Planning now and after implementation",
            test_precision["when"],
        )
        self.assertIn("assertion-level test cases", test_precision["why"])
        self.assertIn("focused proof path", test_precision["why"])
        self.assertIn(
            "**Test Precision Planner**\n"
            "  - **When:** Planning now and after implementation",
            rendered,
        )
        self.assertIn("**TC-01** (covers `REQ-01`)", rendered)
        self.assertIn("**TC-04** (covers `REQ-01`)", rendered)
        self.assertNotIn("1. **REQ-01:**", rendered)
        self.assertEqual(
            ["TC-01", "TC-02", "TC-03", "TC-04"],
            [row["test_case_id"] for row in report["testing_plan"]["test_cases"]],
        )
        self.assertEqual(
            {"REQ-01"},
            {row["requirement_id"] for row in report["testing_plan"]["test_cases"]},
        )
        self.assertIn(
            'The exact "CloudWatch trace endpoint is not configured." is absent on the Push to DOM page.',
            rendered,
        )
        self.assertIn("Other genuine deployment errors remain visible.", rendered)
        self.assertIn("Successful Push to DOM behavior remains unchanged.", rendered)
        self.assertIn("Unrelated warnings and notifications are not suppressed.", rendered)
        self.assertIn(
            "update the existing linked page/component proof when any required assertion is missing; otherwise run it unchanged",
            rendered,
        )
        self.assertIn("Run the focused page/component proof", rendered)
        self.assertIn("Run project lint", rendered)
        self.assertIn("Run the project build/type check", rendered)
        self.assertIn("**Question Orchestrator**\n  - **When:** Planning now", rendered)
        self.assertIn("existing requirement-linked proof", rendered)
        self.assertIn("after this exact plan is approved, run it unchanged or edit it only for approved proof assertions", rendered)
        self.assertNotIn("read-only unless separately approved", rendered)
        contract = plan["requirement_matrix"][0]["validation_contract"]
        self.assertEqual({"component", "behaviour", "static"}, set(contract["tiers"]))
        self.assertEqual(["src/pages/pushToDom/PushToDomPage.cy.tsx"], contract["editable_paths"])
        self.assertEqual(
            {
                'npm run cypress:component -- --spec "src/pages/pushToDom/PushToDomPage.cy.tsx"',
                "npm run lint",
                "npm run build",
            },
            set(contract["commands"]),
        )
        self.assertEqual(2, len([row for row in contract["checks"] if row["kind"] == "static"]))
        checks = {row["kind"]: row for row in contract["checks"]}
        self.assertEqual(["component", "behaviour"], checks["proof"]["tiers"])
        self.assertEqual(["static"], checks["static"]["tiers"])
        drift_rule = activated["execution_handoff"]["scope_drift_rule"]
        self.assertIn("src/pages/pushToDom/PushToDomPage.cy.tsx", drift_rule["approved_editable_paths"])
        self.assertIn("src/pages/pushToDom/PushToDomPage.cy.tsx", drift_rule["approved_validation_paths"])
        self.assertNotIn("src/pages/pushToDom/PushToDomPage.cy.tsx", drift_rule["approved_implementation_paths"])
        self.assertIn("src/pages/pushToDom/PushToDomPage.cy.tsx", workflow_binding["validation_edit_paths"])
        self.assertIn("src/pages/pushToDom/PushToDomPage.cy.tsx", workflow_binding["editable_paths"])
        self.assertNotIn("NotFoundPage", rendered)

    def test_fsr3_joins_complete_behavior_chain_and_selects_direct_page_proof(self) -> None:
        fixture = load_json(FIXTURE_ROOT / "typescript-alias-ui-literal-false-stop.json")
        for relative, body in fixture["repository_files"].items():
            self.write(relative, body)
        navigator_graph_lifecycle.manage(self.root, fixture["goal"], mode="auto")

        report = navigator.decide(
            fixture["goal"], self.root, [], "tailtrail", detect_git_changes=False
        )
        evidence = report["scope_evidence"]
        requirement = evidence["requirements"][0]
        chains = evidence["investigation"]["behavior_chains"]
        edge_kinds = {row["kind"] for row in evidence["edges"]}

        self.assertEqual("complete", chains["state"])
        self.assertEqual(1, len(chains["chains"]))
        self.assertEqual("caught-error-state-render", chains["chains"][0]["variant"])
        self.assertEqual(
            ["src/pages/eventGenerator/EventGeneratorPage.tsx"],
            requirement["implementation_owners"],
        )
        self.assertEqual(
            ["src/pages/eventGenerator/EventGeneratorPage.cy.tsx"],
            requirement["proof_paths"],
        )
        self.assertTrue({
            "calls-symbol", "catches-error", "writes-ui-state", "renders-ui-state",
        }.issubset(edge_kinds))
        self.assertNotIn(
            "src/pages/eventGenerator/telemetryService.cy.ts",
            requirement["proof_paths"],
        )
        self.assertEqual(
            [],
            contracts.validate_document(evidence, load_json(EVIDENCE_SCHEMA_PATH)),
        )

    def test_fsr3_indirect_and_dynamic_flows_remain_uncertain(self) -> None:
        goal = (
            "in the status page there is a banner Trace endpoint is not configured. "
            "we need to remove it"
        )
        variants = {
            "indirect": (
                "import { traceWarning } from './traceService';\n"
                "export function StatusPage() {\n"
                "  const invoke = traceWarning; const warning = invoke();\n"
                "  return <main>{warning && <aside>{warning}</aside>}</main>;\n"
                "}\n"
            ),
            "dynamic": (
                "import * as traceService from './traceService';\n"
                "export function StatusPage({name}) {\n"
                "  const warning = traceService[name]();\n"
                "  return <main>{warning && <aside>{warning}</aside>}</main>;\n"
                "}\n"
            ),
            "cross-function": (
                "import { traceWarning } from './traceService';\n"
                "function prefetchTrace() { traceWarning(); }\n"
                "export function StatusPage() {\n"
                "  const [warning, setWarning] = useState('');\n"
                "  try { loadLocalState(); } catch (error) { setWarning(error.message); }\n"
                "  return <main>{warning && <aside>{warning}</aside>}</main>;\n"
                "}\n"
            ),
        }
        for variant, page_body in variants.items():
            with self.subTest(variant=variant), tempfile.TemporaryDirectory() as temporary:
                repository = Path(temporary)
                service = repository / "src" / "traceService.ts"
                service.parent.mkdir(parents=True)
                service.write_text(
                    "export function traceWarning() { return 'Trace endpoint is not configured.'; }\n",
                    encoding="utf-8",
                )
                page = repository / "src" / "StatusPage.tsx"
                page.write_text(page_body, encoding="utf-8")

                report = navigator.decide(
                    goal, repository, [], "tailtrail", detect_git_changes=False
                )
                evidence = report["scope_evidence"]
                chains = evidence["investigation"]["behavior_chains"]

                self.assertIn(evidence["state"], {"unresolved", "blocked-by-limits"})
                self.assertEqual([], evidence["requirements"][0]["implementation_owners"])
                self.assertIn(chains["state"], {"partial", "unresolved"})
                self.assertNotIn("single-complete-renderer-chain", chains["reason_codes"])

    def test_fsr3_conflicting_complete_renderers_are_explicitly_uncertain(self) -> None:
        fixture = load_json(FIXTURE_ROOT / "typescript-genuine-renderer-ambiguity.json")
        for relative, body in fixture["repository_files"].items():
            self.write(relative, body)

        report = navigator.decide(
            fixture["goal"], self.root, [], "tailtrail", detect_git_changes=False
        )
        evidence = report["scope_evidence"]

        self.assertEqual("ambiguous", evidence["state"])
        self.assertEqual("conflicting", evidence["investigation"]["behavior_chains"]["state"])
        self.assertEqual(
            "multiple-complete-renderer-chains",
            evidence["investigation"]["behavior_chains"]["reason_codes"][0],
        )

    def test_fsr3_service_contract_request_still_selects_service_owner(self) -> None:
        self.write(
            "src/telemetryContract.ts",
            "export function telemetryContract() { return { enabled: false }; }\n",
        )
        self.write(
            "tests/telemetryContract.test.ts",
            "import { telemetryContract } from '../src/telemetryContract';\n"
            "test('contract', () => telemetryContract());\n",
        )
        goal = "update the telemetry contract while preserving disabled behavior"

        report = navigator.decide(
            goal, self.root, [], "tailtrail", detect_git_changes=False
        )
        evidence = report["scope_evidence"]

        self.assertEqual("resolved", evidence["state"])
        self.assertEqual(
            ["src/telemetryContract.ts"],
            evidence["requirements"][0]["implementation_owners"],
        )
        self.assertEqual("not-exercised", evidence["investigation"]["behavior_chains"]["state"])

    def test_fresh_graph_helper_hint_cannot_override_direct_ui_behavior_owner(self) -> None:
        fixture = load_json(FIXTURE_ROOT / "ui-handler-import-ownership.json")
        for relative, body in fixture["repository_files"].items():
            self.write(relative, body)
        helper = fixture["expected_helpers"][0]
        helper_path = self.root / helper
        cache = {
            "schema_version": "1",
            "root": self.root.as_posix(),
            "source_files": {
                helper: {"sha256": hashlib.sha256(helper_path.read_bytes()).hexdigest()}
            },
            "watch_files": {},
            "inventory": navigator_scope.inventory_snapshot(self.root),
            "graph": {
                "suggested_read_order": [helper],
                "likely_callers": [],
                "likely_tests": [],
                "nearby_manifests": [],
            },
        }
        cache_path = self.root / "tailtrail-meta" / "code-graph-cache.json"
        cache_path.parent.mkdir()
        cache_path.write_text(json.dumps(cache), encoding="utf-8")

        report = navigator.decide(
            fixture["goal"], self.root, [], "tailtrail", detect_git_changes=False
        )

        self.assertEqual(report["scope_evidence"]["investigation"]["cache"]["status"], "fresh")
        self.assertEqual(
            report["scope_evidence"]["requirements"][0]["implementation_owners"],
            [fixture["expected_owner"]],
        )

    def test_stale_graph_helper_hint_is_rejected_before_ui_owner_resolution(self) -> None:
        fixture = load_json(FIXTURE_ROOT / "ui-handler-import-ownership.json")
        for relative, body in fixture["repository_files"].items():
            self.write(relative, body)
        helper = fixture["expected_helpers"][0]
        cache = {
            "schema_version": "1",
            "root": self.root.as_posix(),
            "source_files": {helper: {"sha256": "0" * 64}},
            "watch_files": {},
            "inventory": navigator_scope.inventory_snapshot(self.root),
            "graph": {
                "suggested_read_order": [helper],
                "likely_callers": [],
                "likely_tests": [],
                "nearby_manifests": [],
            },
        }
        cache_path = self.root / "tailtrail-meta" / "code-graph-cache.json"
        cache_path.parent.mkdir()
        cache_path.write_text(json.dumps(cache), encoding="utf-8")

        report = navigator.decide(
            fixture["goal"], self.root, [], "tailtrail", detect_git_changes=False
        )

        self.assertEqual(report["scope_evidence"]["investigation"]["cache"]["status"], "stale")
        self.assertIn(
            "bounded-ephemeral-graph-built",
            report["scope_evidence"]["investigation"]["cache"]["reason_codes"],
        )
        self.assertEqual(
            report["scope_evidence"]["requirements"][0]["implementation_owners"],
            [fixture["expected_owner"]],
        )

    def test_identical_ui_behavior_evidence_in_two_components_remains_ambiguous(self) -> None:
        goal = "fix validate click showing 'Inputs are valid' so it moves to session summary"
        component = (
            "export function {name}() {{\n"
            "  const [showSummary, setShowSummary] = useState(false);\n"
            "  const validateInput = () => {{ toast.success('Inputs are valid'); setShowSummary(true); }};\n"
            "  return showSummary ? <h2>Session Summary</h2> : <Button onPress={{validateInput}}>Validate</Button>;\n"
            "}}\n"
        )
        self.write("src/pages/alpha/ValidatePage.tsx", component.format(name="AlphaValidatePage"))
        self.write("src/pages/beta/ValidatePage.tsx", component.format(name="BetaValidatePage"))

        report = navigator.decide(goal, self.root, [], "tailtrail", detect_git_changes=False)

        self.assertEqual(report["scope_evidence"]["state"], "ambiguous")
        self.assertEqual(report["scope_quality"]["status"], "blocked")
        self.assertEqual(
            report["scope_quality"]["question"]["options"],
            ["src/pages/alpha/ValidatePage.tsx", "src/pages/beta/ValidatePage.tsx"],
        )

    def test_python_validation_behavior_wins_over_ui_distractor(self) -> None:
        self.write(
            "shop/orders/service.py",
            '"""Order quantity validation."""\n'
            "\n"
            "\n"
            "class OrderValidator:\n"
            '    """Validates order quantities before checkout."""\n'
            "\n"
            "    def reject_zero_quantity(self, order):\n"
            '        """Reject zero quantities but keep positive quantities working."""\n'
            "        assert order is not None\n"
            "        if order.quantity == 0:\n"
            '            raise ValueError("quantity must be positive")\n'
            "        return True\n",
        )
        self.write(
            "shop/orders/tests/test_service.py",
            "from shop.orders.service import OrderValidator\n",
        )
        self.write(
            "shop/ui/order_page.tsx",
            "export function OrderPage({ order }) {\n"
            "  const [error, setError] = useState(null);\n"
            "  async function handleQuantitySubmit() {\n"
            "    if (order.quantity === 0) {\n"
            '      setError("quantity must be positive");\n'
            "      return;\n"
            "    }\n"
            "  }\n"
            "  return (\n"
            "    <form onSubmit={handleQuantitySubmit}>\n"
            "      <button type=\"submit\">quantity checkout</button>\n"
            "      {error && <aside>{error}</aside>}\n"
            "    </form>\n"
            "  );\n"
            "}\n",
        )

        report = navigator.decide(
            "reject zero quantities but keep positive quantities working",
            self.root, [], "tailtrail", detect_git_changes=False,
        )

        self.assertEqual(
            report["scope_evidence"]["requirements"][0]["implementation_owners"],
            ["shop/orders/service.py"],
        )
        owners = {
            row["path"]: row
            for row in navigator_scope.role_projection(
                report["scope_evidence"]
            )["implementation_owners"]
        }
        # Language-blind behavior evidence: the backend validator qualifies
        # through its guard/assertion/error rows, not just its symbol names.
        self.assertIn(
            "behavior-specific-owner-evidence",
            owners["shop/orders/service.py"].get("reason_codes", []),
        )
        self.assertIn(
            "owner-qualified-by-task-specific-behavior",
            owners["shop/orders/service.py"].get("reason_codes", []),
        )

    def test_host_proposals_validate_for_all_hosts_and_reject_unsupported_confidence(self) -> None:
        fixture = load_json(FIXTURE_ROOT / "typescript-genuine-renderer-ambiguity.json")
        for relative, body in fixture["repository_files"].items():
            self.write(relative, body)
        report = navigator.decide(fixture["goal"], self.root, [], "tailtrail", detect_git_changes=False)
        evidence = report["scope_evidence"]
        packet = navigator_scope.host_reasoning_packet(evidence)
        requirement = evidence["requirements"][0]
        self.assertEqual(packet["route"]["state"], "requested")
        candidates = {row["path"]: row for row in evidence["candidates"]}
        chosen = packet["route"]["eligible_candidates"][0]["path"]
        alternative = packet["route"]["eligible_candidates"][1]["path"]
        inspection = next(
            row["path"] for row in evidence["candidates"]
            if row["role"] == "literal-emitter"
        )
        material = [(chosen, "implementation-owner"), (inspection, "inspection")]
        path_claims = [{
            "path": path,
            "candidate_id": candidates[path]["candidate_id"],
            "content_fingerprint": candidates[path]["content_fingerprint"],
            "claim_role": role,
            "evidence_edge_ids": candidates[path]["evidence_edge_ids"],
        } for path, role in material]
        edge_ids = sorted({edge_id for row in path_claims for edge_id in row["evidence_edge_ids"]})
        fingerprints: set[str] = set()
        decision_fingerprints: set[str] = set()
        schema = load_json(HOST_PROPOSAL_SCHEMA_PATH)
        for host in ("codex", "claude", "copilot"):
            proposal = {
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
                    "path_claims": path_claims,
                    "preservation_boundaries": ["Preserve the alternate renderer until runtime context selects it."],
                    "evidence_edge_ids": edge_ids,
                    "confidence": "high",
                    "decision_reasons": ["The requested page context selects one of two strongly evidenced renderers."],
                    "alternatives": [alternative],
                    "uncertainties": [],
                }],
                "private_reasoning_excluded": True,
            }
            self.assertEqual(contracts.validate_document(proposal, schema), [])
            validation = navigator_scope.validate_host_proposal(self.root, packet, proposal)
            self.assertEqual(validation["status"], "accepted", validation["errors"])
            fingerprints.add(validation["normalized_scope_fingerprint"])
            recorded = navigator_scope.record_host_proposal(self.root, evidence, proposal)
            self.assertEqual(recorded["host_reasoning"]["state"], "recorded")
            self.assertEqual(recorded["state"], "resolved")
            self.assertEqual(recorded["requirements"][0]["implementation_owners"], [chosen])
            self.assertTrue(navigator_scope.verify_decision_fingerprint(recorded))
            decision_fingerprints.add(recorded["decision_fingerprint"])
        self.assertEqual(len(fingerprints), 1)
        self.assertEqual(len(decision_fingerprints), 1)
        self.assertEqual(evidence["state"], "ambiguous")

        unsupported = dict(proposal)
        unsupported["requirements"] = [dict(proposal["requirements"][0])]
        unsupported["requirements"][0]["implementation_owners"] = ["tests/test_aidlc_requirements.py"]
        rejected = navigator_scope.validate_host_proposal(self.root, packet, unsupported)
        self.assertEqual(rejected["status"], "rejected")
        self.assertTrue(any("unsupported-owner" in error for error in rejected["errors"]))

    def test_fsr5_host_proposals_reject_invention_missing_edges_staleness_and_authority(self) -> None:
        evidence, packet, proposal = self.ambiguous_host_case()
        self.assertEqual(packet["route"]["state"], "requested")
        self.assertEqual(evidence["host_reasoning"]["state"], "requested")

        invented = copy.deepcopy(proposal)
        invented["requirements"][0]["implementation_owners"] = ["src/pages/InventedPage.tsx"]
        invented["requirements"][0]["path_claims"][0]["path"] = "src/pages/InventedPage.tsx"
        invented_result = navigator_scope.host_proposal_decision(self.root, evidence, invented)
        self.assertEqual(invented_result["status"], "rejected")
        self.assertTrue(any("unknown-paths" in code for code in invented_result["reason_codes"]))

        unsupported_edge = copy.deepcopy(proposal)
        fake_edge = "edge-000000000000"
        unsupported_edge["requirements"][0]["path_claims"][0]["evidence_edge_ids"] = [fake_edge]
        unsupported_edge["requirements"][0]["evidence_edge_ids"] = sorted({
            edge
            for claim in unsupported_edge["requirements"][0]["path_claims"]
            for edge in claim["evidence_edge_ids"]
        })
        edge_result = navigator_scope.host_proposal_decision(self.root, evidence, unsupported_edge)
        self.assertEqual(edge_result["status"], "rejected")
        self.assertTrue(any("unknown-edges" in code for code in edge_result["reason_codes"]))

        selected = proposal["requirements"][0]["implementation_owners"][0]
        self.write(selected, "export function changedAfterPacket() { return false; }\n")
        stale_result = navigator_scope.host_proposal_decision(self.root, evidence, proposal)
        self.assertEqual(stale_result["status"], "rejected")
        self.assertTrue(any("stale-path-content" in code for code in stale_result["reason_codes"]))

        # Restore the exact packet-bound content before testing authority fields.
        fixture = load_json(FIXTURE_ROOT / "typescript-genuine-renderer-ambiguity.json")
        self.write(selected, fixture["repository_files"][selected])
        escalation = copy.deepcopy(proposal)
        escalation["approved"] = True
        escalation["authority"] = "implementation-authority"
        authority_result = navigator_scope.host_proposal_decision(self.root, evidence, escalation)
        self.assertEqual(authority_result["status"], "rejected")
        self.assertIn("host-authority-escalation-rejected", authority_result["reason_codes"])

        for result in (invented_result, edge_result, stale_result, authority_result):
            self.assertFalse(result["run_created"])
            self.assertFalse(result["planning_lock_created"])
            self.assertTrue(result["execution_blocked"])
        self.assertFalse((self.root / ".tailtrail" / "runs").exists())

    def test_proposed_new_path_accepts_anchor_and_convention_link(self) -> None:
        evidence, packet, _ = self.ambiguous_host_case()
        requirement = packet["requirements"][0]
        candidates = {row["path"]: row for row in packet["candidates"]}
        anchor = next(
            row["path"] for row in packet["candidates"] if row.get("status") == "included"
        )
        convention_edge = next(
            row["edge_id"] for row in packet["edges"]
            if row.get("kind") in {"imports-module", "loads-module", "registered-by", "configures-owner"}
            or "convention" in str(row.get("reason", ""))
            or str(row.get("reason", "")) in {"static-configuration-reference", "static-registration-reference"}
        )
        anchor_claim = {
            "path": anchor,
            "candidate_id": candidates[anchor]["candidate_id"],
            "content_fingerprint": candidates[anchor]["content_fingerprint"],
            "claim_role": "inspection",
            "evidence_edge_ids": candidates[anchor]["evidence_edge_ids"],
        }
        edge_ids = sorted(set(candidates[anchor]["evidence_edge_ids"]) | {convention_edge})
        alternative = packet["route"]["eligible_candidates"][1]["path"]
        proposal = {
            "schema_version": "2",
            "type": "tailtrail-navigator-host-scope-proposal",
            "host": "codex",
            "evidence_packet_fingerprint": packet["packet_fingerprint"],
            "scope_evidence_fingerprint": packet["scope_evidence_fingerprint"],
            "target_identity_fingerprint": packet["target_identity_fingerprint"],
            "goal_fingerprint": packet["goal_fingerprint"],
            "scope_state": "proposed-resolved",
            "authority": "evidence-refinement-only",
            "requirements": [{
                "requirement_id": requirement["requirement_id"],
                "statement_fingerprint": requirement["statement_fingerprint"],
                "implementation_owners": [],
                "callers": [],
                "inspection_paths": [anchor],
                "proof_paths": [],
                "excluded_candidates": [row["path"] for row in requirement["excluded_candidates"]],
                "path_claims": [anchor_claim],
                "preservation_boundaries": ["Keep the proposed page out of the build until approved."],
                "evidence_edge_ids": edge_ids,
                "confidence": "medium",
                "decision_reasons": ["Host proposes a new page anchored to included evidence with convention linkage."],
                "alternatives": [alternative],
                "uncertainties": [],
                "proposed_new_path": "src/pages/NewPage.tsx",
                "anchor_paths": [anchor],
                "convention_refs": [convention_edge],
            }],
            "private_reasoning_excluded": True,
        }
        schema = load_json(HOST_PROPOSAL_SCHEMA_PATH)
        self.assertEqual(contracts.validate_document(proposal, schema), [])
        validation = navigator_scope.validate_host_proposal(self.root, packet, proposal)
        self.assertEqual(validation["status"], "accepted", validation["errors"])
        normalized = validation["normalized_proposal"]["requirements"][0]
        self.assertEqual(normalized["decision"], "host-proposed-new-path")
        self.assertEqual(normalized["proposed_new_path"], "src/pages/NewPage.tsx")
        self.assertEqual(normalized["anchor_paths"], [anchor])
        recorded = navigator_scope.record_host_proposal(self.root, evidence, proposal)
        self.assertEqual(recorded["host_reasoning"]["state"], "recorded")
        self.assertNotEqual(recorded["state"], "resolved")
        marker = recorded["requirements"][0].get("host_proposed_new_path", {})
        self.assertEqual(marker.get("path"), "src/pages/NewPage.tsx")
        self.assertEqual(marker.get("decision"), "host-proposed-new-path")
        self.assertTrue(navigator_scope.verify_decision_fingerprint(recorded))
        self.assertEqual(
            recorded["requirements"][0]["implementation_owners"],
            evidence["requirements"][0]["implementation_owners"],
        )
        self.assertEqual(
            recorded["requirements"][0].get("confidence"),
            evidence["requirements"][0].get("confidence"),
        )

    def test_proposed_new_path_rejects_unsafe_unlinked_and_overprivileged(self) -> None:
        evidence, packet, _ = self.ambiguous_host_case()
        requirement = packet["requirements"][0]
        candidates = {row["path"]: row for row in packet["candidates"]}
        anchor = next(
            row["path"] for row in packet["candidates"] if row.get("status") == "included"
        )
        edge_id = packet["edges"][0]["edge_id"]
        alternative = packet["route"]["eligible_candidates"][1]["path"]

        def row_with(**overrides: Any) -> dict[str, Any]:
            base: dict[str, Any] = {
                "requirement_id": requirement["requirement_id"],
                "statement_fingerprint": requirement["statement_fingerprint"],
                "implementation_owners": [],
                "callers": [],
                "inspection_paths": [anchor],
                "proof_paths": [],
                "excluded_candidates": [],
                "path_claims": [{
                    "path": anchor,
                    "candidate_id": candidates[anchor]["candidate_id"],
                    "content_fingerprint": candidates[anchor]["content_fingerprint"],
                    "claim_role": "inspection",
                    "evidence_edge_ids": candidates[anchor]["evidence_edge_ids"],
                }],
                "preservation_boundaries": ["Hold."],
                "evidence_edge_ids": sorted(set(candidates[anchor]["evidence_edge_ids"]) | {edge_id}),
                "confidence": "medium",
                "decision_reasons": ["Hold."],
                "alternatives": [alternative],
                "uncertainties": [],
                "proposed_new_path": "src/pages/NewPage.tsx",
                "anchor_paths": [anchor],
                "convention_refs": [edge_id],
            }
            base.update(overrides)
            return base

        def validate(row: dict[str, Any]) -> list[str]:
            proposal = {
                "schema_version": "2",
                "type": "tailtrail-navigator-host-scope-proposal",
                "host": "codex",
                "evidence_packet_fingerprint": packet["packet_fingerprint"],
                "scope_evidence_fingerprint": packet["scope_evidence_fingerprint"],
                "target_identity_fingerprint": packet["target_identity_fingerprint"],
                "goal_fingerprint": packet["goal_fingerprint"],
                "scope_state": "needs-confirmation",
                "authority": "evidence-refinement-only",
                "requirements": [row],
                "private_reasoning_excluded": True,
            }
            result = navigator_scope.validate_host_proposal(self.root, packet, proposal)
            self.assertEqual(result["status"], "rejected")
            return result["errors"]

        self.assertTrue(any("invalid-proposed-path" in code for code in validate(row_with(proposed_new_path="../escape.tsx"))))
        self.assertTrue(any("proposed-path-already-candidate" in code for code in validate(row_with(proposed_new_path=anchor))))
        chosen = packet["route"]["eligible_candidates"][0]["path"]
        self.assertTrue(any("new-path-cannot-claim-owner" in code for code in validate(row_with(implementation_owners=[chosen]))))
        self.assertTrue(any("anchor-paths-required" in code for code in validate(row_with(anchor_paths=[]))))
        self.assertTrue(any("unknown-anchor-path" in code for code in validate(row_with(
            anchor_paths=["src/pages/Missing.tsx"],
            inspection_paths=[anchor, "src/pages/Missing.tsx"],
        ))))
        self.assertTrue(any("unknown-convention-ref" in code for code in validate(row_with(convention_refs=["edge-000000000000"]))))
        dense = row_with()
        dense["confidence"] = "high"
        self.assertTrue(any("confidence-promotion-rejected" in code for code in validate(dense)))

    def test_convention_link_helper_grades_edges_and_anchors(self) -> None:
        edges = {
            "edge-000000000001": {"kind": "imports-module", "reason": "static-import-reference"},
            "edge-000000000002": {"kind": "discovery-seed", "reason": "lexical-match"},
        }
        self.assertTrue(navigator_scope._convention_link_present({}, edges, [], ["edge-000000000001"]))
        self.assertFalse(navigator_scope._convention_link_present({}, edges, [], ["edge-000000000002"]))
        self.assertFalse(navigator_scope._convention_link_present({}, edges, [], ["edge-ffffffffffff"]))
        candidates = {"src/a.py": {"reason_codes": ["test-path-convention"]}}
        self.assertTrue(navigator_scope._convention_link_present(candidates, edges, ["src/a.py"], ["edge-000000000002"]))

    def test_investigate_reports_role_labeled_anchors(self) -> None:
        evidence, packet, _ = self.ambiguous_host_case()
        candidates = {row["path"]: row for row in packet["candidates"]}
        investigation = evidence["investigation"]
        report_anchors = investigation.get("anchors", [])
        self.assertTrue(report_anchors)
        for anchor in report_anchors:
            self.assertIn(anchor["role"], navigator_scope.ANCHOR_ROLES)
            self.assertIn(anchor["confidence"], {"high", "medium", "low"})
            self.assertTrue(anchor["evidence_refs"])
            self.assertNotEqual(anchor["role"], "implementation-owner")
        self.assertIn(investigation.get("anchor_state"), {"sufficient", "insufficient"})
        self.assertEqual(
            [],
            contracts.validate_document(evidence, load_json(EVIDENCE_SCHEMA_PATH)),
        )

    def test_lexical_only_seeds_mint_no_anchors(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.write("src/a.py", "def a():\n    return 1\n")
            seeds = navigator_scope.candidates_from_seeds(
                root, [navigator_scope.seed("src/a.py", "lexical-path", "lexical-path-match")]
            )
            _, _, report = navigator_scope.investigate(
                root,
                [{"requirement_id": "r1", "statement": "a", "query_terms": ["a"], "quoted_literals": []}],
                seeds,
                [],
            )
        self.assertEqual(report["anchors"], [])
        self.assertEqual(report["anchor_state"], "insufficient")

    def test_anchor_path_query_is_bounded_and_directed(self) -> None:
        adjacency = {"a": ["b"], "b": ["c"], "c": ["a"]}
        self.assertEqual(
            navigator_scope.connected_files(["a"], adjacency, max_hops=1), ["a", "b"]
        )
        self.assertEqual(
            navigator_scope.connected_files(["b"], adjacency, max_hops=1), ["b", "c"]
        )
        self.assertEqual(
            navigator_scope.connected_files(["a"], adjacency, max_hops=10, limit=2), ["a", "b"]
        )

    def test_anchor_slice_contract_is_stable(self) -> None:
        anchors = [
            {"anchor_id": "anchor:entrypoint:src/a.py", "role": "entrypoint", "path": "src/a.py",
             "confidence": "high", "reason_codes": ["anchor-exact-task-reference"], "evidence_refs": {}},
        ]
        first = navigator_scope.anchor_slice(anchors, coverage_required=["entrypoint"])
        second = navigator_scope.anchor_slice(list(reversed(anchors)), coverage_required=["entrypoint"])
        self.assertEqual(first["anchor_ids"], ["anchor:entrypoint:src/a.py"])
        self.assertEqual(first["paths"], ["src/a.py"])
        self.assertEqual(first["coverage_required"], ["entrypoint"])
        self.assertEqual(first["fingerprint"], second["fingerprint"])

    def test_host_packet_v2_is_superset_validated_and_sanitized(self) -> None:
        evidence, packet, _ = self.ambiguous_host_case()
        candidate_paths = {row["path"] for row in packet["candidates"]}
        self.assertEqual(packet.get("packet_version"), 2)
        for section in ("anchors", "relationships", "existing_candidates", "conventions",
                        "excluded_candidates", "suggested_read_order", "read_budget", "cache"):
            self.assertIn(section, packet)
        for anchor in packet["anchors"]:
            self.assertEqual(set(anchor), {"id", "role", "path"})
        for rel in packet["relationships"]:
            self.assertEqual(set(rel), {"from", "to", "kind"})
            self.assertIn(rel["from"], candidate_paths)
            self.assertIn(rel["to"], candidate_paths)
        self.assertIn(packet["cache"]["state"],
                      {"fresh-relevant", "fresh-insufficient", "stale-relevant", "stale-insufficient",
                       "missing", "not-checked", "disabled", "invalid", "not-run"})
        self.assertEqual(
            [], contracts.validate_document(packet, load_json(ROOT / "schemas" / "navigator-host-scope-packet-v2.schema.json")),
        )
        dumped = json.dumps(packet)
        self.assertNotIn("return True", dumped)
        self.assertNotIn("SECRET", dumped)

    def test_packet_v1_projection_is_byte_stable(self) -> None:
        _, packet, _ = self.ambiguous_host_case()
        projected = navigator_scope.packet_v1_projection(packet)
        self.assertEqual(
            set(projected),
            {"schema_version", "type", "scope_evidence_fingerprint", "evidence_packet_fingerprint",
             "target_identity_fingerprint", "goal_fingerprint", "requirements", "candidates",
             "edges", "limits", "route", "instructions"},
        )
        for key, value in projected.items():
            self.assertIs(value, packet[key])
        self.assertNotIn("packet_version", projected)
        with self.assertRaises(ValueError):
            navigator_scope.packet_v1_projection(None)  # type: ignore[arg-type]

    def test_packet_version_negotiation_fails_closed(self) -> None:
        evidence, packet, proposal = self.ambiguous_host_case()
        self.assertEqual(navigator_scope.negotiate_packet_version(packet), 2)
        legacy = {key: value for key, value in packet.items() if key != "packet_version"}
        self.assertEqual(navigator_scope.negotiate_packet_version(legacy), 1)
        forged = dict(packet)
        forged["packet_version"] = 99
        body = {key: value for key, value in forged.items() if key != "packet_fingerprint"}
        forged["packet_fingerprint"] = navigator_scope.fingerprint(body)
        proposal = dict(proposal)
        proposal["evidence_packet_fingerprint"] = forged["packet_fingerprint"]
        validation = navigator_scope.validate_host_proposal(self.root, forged, proposal)
        self.assertEqual(validation["status"], "rejected")
        self.assertIn("unsupported-packet-version", validation["errors"])
        with self.assertRaises(ValueError):
            navigator_scope.negotiate_packet_version(None)  # type: ignore[arg-type]

    def test_resolve_anchor_slice_uses_task_paths_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "src").mkdir()
            (root / "src" / "a.py").write_text("def a():\n    return 1\n", encoding="utf-8")
            aslice = navigator_scope.resolve_anchor_slice(
                root, ["src/a.py", "src/missing.py", "../escape.py", ".env"],
                literals=["src/a.py", "not a path"],
            )
        self.assertEqual(aslice["paths"], ["src/a.py"])
        self.assertEqual(aslice["coverage_required"], [])
        empty = navigator_scope.resolve_anchor_slice(root, ["src/missing.py"])
        self.assertEqual(empty["paths"], [])

    def test_anchor_gap_yields_scope_qa_not_file_choice(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "src").mkdir()
            (root / "src" / "a.py").write_text("def a():\n    return 1\n", encoding="utf-8")
            seeds = navigator_scope.candidates_from_seeds(
                root, [navigator_scope.seed("src/a.py", "lexical-path", "lexical-path-match")]
            )
            candidates, edges, investigation = navigator_scope.investigate(
                root,
                [{"requirement_id": "r1", "statement": "fix the a bug",
                  "query_terms": ["bug"], "quoted_literals": []}],
                seeds,
                [],
            )
            self.assertEqual(investigation["anchor_state"], "insufficient")
            evidence = navigator_scope.evidence_document(
                root, "fix the a bug",
                [{"requirement_id": "r1", "statement": "fix the a bug",
                  "query_terms": ["bug"], "quoted_literals": []}],
                candidates, edges=edges, investigation=investigation,
            )
            quality = navigator_scope.assess_scope_quality(root, "fix the a bug", ["bug"], evidence)
        self.assertEqual(quality["status"], "blocked")
        self.assertEqual(quality["question"]["question_id"], "SCOPE-QA")
        self.assertEqual(quality["question"]["options"], [])

    def test_topology_roles_project_onto_exactly_one_candidate_role(self) -> None:
        self.assertEqual(
            set(navigator_scope.TOPOLOGY_TO_CANDIDATE_ROLES), set(navigator_scope.ANCHOR_ROLES)
        )
        for role in navigator_scope.ANCHOR_ROLES:
            projected = navigator_scope.project_topology_role(role)
            self.assertIsInstance(projected, str)
            self.assertIn(projected, navigator_scope.ROLES)
        with self.assertRaises(ValueError):
            navigator_scope.project_topology_role("not-a-role")

    def test_layout_roles_are_language_neutral(self) -> None:
        cases = [
            ("src/App.tsx", "implementation-owner"),
            ("src/App.test.tsx", "test"),
            ("src/handler.py", "implementation-owner"),
            ("tests/test_handler.py", "test"),
            ("worker/consumer.go", "implementation-owner"),
            ("worker/consumer_test.go", "test"),
            ("src/cli.ts", "implementation-owner"),
            ("src/command.java", "implementation-owner"),
            ("deploy/app.yaml", "configuration"),
            ("docs/guide.md", "documentation"),
            ("package.json", "manifest"),
        ]
        for relative, expected in cases:
            self.write(relative, "placeholder\n")
            role, _ = navigator_scope.classify_repository_role(self.root, relative)
            self.assertEqual(role, expected, relative)

    def test_scope_cli_is_non_persisting_and_uses_the_same_evidence(self) -> None:
        fixture = load_json(FIXTURE_ROOT / "wrong-file-selection.json")
        for relative, body in fixture["repository_files"].items():
            self.write(relative, body)
        result = subprocess.run(
            [
                sys.executable,
                (ROOT / "scripts" / "tailtrail.py").as_posix(),
                "navigator",
                "scope",
                "inspect",
                "--root",
                self.root.as_posix(),
                "--goal",
                fixture["goal"],
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertFalse(payload["persisted"])
        self.assertTrue(payload["execution_blocked"])
        self.assertEqual(
            payload["scope_evidence"]["requirements"][0]["implementation_owners"],
            fixture["desired_expected"]["implementation_owners"],
        )
        self.assertFalse((self.root / ".tailtrail").exists())


class NavigatorScopeAtomicStartTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write(self, relative: str, body: str) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")

    def run_start(self, goal: str, run_id: str, *extra: str, explicit_root: bool = True) -> subprocess.CompletedProcess[str]:
        command = [
            sys.executable,
            (ROOT / "scripts" / "task-start.py").as_posix(),
            goal,
        ]
        if explicit_root:
            command.extend(["--root", self.root.as_posix()])
        command.extend(["--format", "json", "--planning-run-id", run_id, *extra])
        return subprocess.run(command, cwd=self.root, text=True, capture_output=True, check=False)

    def test_fsr5_active_host_refines_supported_scope_before_atomic_lock(self) -> None:
        fixture = load_json(FIXTURE_ROOT / "typescript-genuine-renderer-ambiguity.json")
        for relative, body in fixture["repository_files"].items():
            self.write(relative, body)

        interpretation = json.dumps(
            build_requirement_interpretation(fixture["goal"]),
            separators=(",", ":"),
        )
        first = self.run_start(
            fixture["goal"],
            "fsr5-host-start",
            "--host", "codex",
            "--requirement-interpretation", interpretation,
        )
        self.assertEqual(first.returncode, 2, first.stderr)
        blocked = json.loads(first.stdout)
        packet = blocked["scope_host_packet"]
        self.assertEqual(packet["route"]["state"], "requested")
        self.assertFalse((self.root / ".tailtrail" / "runs" / "fsr5-host-start").exists())

        proposal = build_host_proposal(packet, "codex")
        second = self.run_start(
            fixture["goal"],
            "fsr5-host-start",
            "--host", "codex",
            "--requirement-interpretation", interpretation,
            "--host-scope-proposal", json.dumps(proposal, separators=(",", ":")),
        )
        self.assertEqual(second.returncode, 0, second.stderr + second.stdout)
        started = json.loads(second.stdout)
        evidence = started["navigator"]["scope_evidence"]
        self.assertEqual(evidence["state"], "resolved")
        self.assertEqual(evidence["investigation"]["decision_reason"], "host-evidence-supported-owner-resolved")
        self.assertEqual(
            evidence["requirements"][0]["implementation_owners"],
            proposal["requirements"][0]["implementation_owners"],
        )
        self.assertEqual(started["planning_lock"]["status"], "awaiting-approval")
        self.assertTrue((self.root / ".tailtrail" / "runs" / "fsr5-host-start").is_dir())

    def test_explicit_and_implicit_test_only_false_matches_block_without_any_run(self) -> None:
        self.write("tests/test_requirement_discovery.py", "def test_requirement():\n    assert True\n")
        decisions = []
        for explicit, run_id in ((True, "ns4-explicit-block"), (False, "ns4-implicit-block")):
            result = self.run_start(
                "fix multiline requirement splitting", run_id, explicit_root=explicit
            )
            self.assertEqual(result.returncode, 2, result.stderr)
            payload = json.loads(result.stdout)
            self.assertTrue(payload["scope_quality_boundary"])
            self.assertEqual(payload["scope_quality"]["status"], "blocked")
            self.assertFalse((self.root / ".tailtrail" / "runs" / run_id).exists())
            decisions.append(payload["scope_quality"]["reason_codes"])
        self.assertEqual(decisions[0], decisions[1])
        self.assertTrue((self.root / "tailtrail-meta" / "code-graph-cache.json").is_file())
        self.assertEqual(payload["graph_lifecycle"]["action"], "reuse")
        self.assertFalse(payload["graph_lifecycle"]["implementation_authority"])

    def test_ui_behavior_owner_without_cache_creates_complete_start_plan(self) -> None:
        fixture = load_json(FIXTURE_ROOT / "ui-handler-import-ownership.json")
        for relative, body in fixture["repository_files"].items():
            self.write(relative, body)

        result = self.run_start(fixture["goal"], "ui-owner-resolved")

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        navigator_report = payload["navigator"]
        self.assertEqual(navigator_report["scope_quality"]["status"], "passed")
        self.assertEqual(
            navigator_report["scope_evidence"]["requirements"][0]["implementation_owners"],
            [fixture["expected_owner"]],
        )
        self.assertTrue(
            (self.root / ".tailtrail" / "runs" / "ui-owner-resolved" / "planning" / "start-report-v1.json").is_file()
        )
        rendered = task_start.render_markdown(payload)
        for section in (
            "## Planning Lock", "## Scope", "## Requirements",
            "## Selected TailTrail features", "## Plan", "Focused validation", "## Approval",
        ):
            self.assertIn(section, rendered)
        self.assertNotIn("TailTrail Scope Confirmation Required", rendered)

    def test_valid_changed_owner_persists_requirement_specific_scope_and_v2_fingerprint(self) -> None:
        self.write("src/requirement_discovery.py", "def split_requirement(value):\n    return value.splitlines()\n")
        self.write("tests/test_requirement_discovery.py", "from src.requirement_discovery import split_requirement\n")
        result = self.run_start(
            "fix multiline requirement splitting",
            "ns4-resolved",
            "--changed",
            "src/requirement_discovery.py",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        plan = payload["navigator"]
        decision = plan["scope_evidence"]["decision_fingerprint"]
        self.assertEqual(plan["scope_quality"]["status"], "passed")
        self.assertEqual(
            contracts.validate_document(plan["scope_quality"], load_json(SCOPE_QUALITY_SCHEMA_PATH)),
            [],
        )
        self.assertEqual(payload["planning_lock"]["scope_decision"]["decision_fingerprint"], decision)
        requirement = plan["requirement_matrix"][0]
        self.assertEqual(requirement["likely_paths"], ["src/requirement_discovery.py"])
        self.assertEqual(requirement["scope_evidence"]["proof_paths"], ["tests/test_requirement_discovery.py"])
        self.assertEqual(requirement["validation_contract"]["candidate_paths"], ["tests/test_requirement_discovery.py"])
        self.assertTrue((self.root / ".tailtrail" / "runs" / "ns4-resolved" / "planning" / "start-report-v1.json").is_file())
        rendered = task_start.render_markdown(payload)
        for section in (
            "## Planning Lock", "## Scope", "## Requirements",
            "## Selected TailTrail features", "## Plan", "Focused validation", "## Approval",
        ):
            self.assertIn(section, rendered)
        self.assertIn(decision, rendered)

    def test_changed_test_is_proof_only_but_explicit_test_and_documentation_only_scopes_are_valid(self) -> None:
        self.write("src/owner.py", "def owner():\n    return True\n")
        self.write("tests/test_owner.py", "from src.owner import owner\n")
        code = navigator.decide(
            "fix owner behavior", self.root, ["tests/test_owner.py"], "tailtrail", detect_git_changes=False
        )
        test_candidate = next(row for row in code["scope_candidates"] if row["path"] == "tests/test_owner.py")
        self.assertEqual(test_candidate["role"], "test")
        self.assertEqual(test_candidate["status"], "proof-only")

        test_only = self.run_start(
            "update tests only", "ns4-test-only", "--changed", "tests/test_owner.py"
        )
        self.assertEqual(test_only.returncode, 0, test_only.stderr)
        test_payload = json.loads(test_only.stdout)
        self.assertEqual(test_payload["navigator"]["scope_quality"]["mode"], "test-only")
        self.assertEqual(test_payload["navigator"]["requirement_matrix"][0]["likely_paths"], ["tests/test_owner.py"])

        self.write("README.md", "# Demo\n")
        docs_only = self.run_start(
            "documentation only: update readme", "ns4-docs-only", "--changed", "README.md"
        )
        self.assertEqual(docs_only.returncode, 0, docs_only.stderr)
        docs_payload = json.loads(docs_only.stdout)
        self.assertEqual(docs_payload["navigator"]["scope_quality"]["mode"], "documentation-only")
        self.assertEqual(docs_payload["navigator"]["requirement_matrix"][0]["likely_paths"], ["README.md"])

    def test_conftest_and_definition_bearing_tests_never_own_production_changes(self) -> None:
        self.write("conftest.py", "def repeated_steps_fixture():\n    return ['step', 'step']\n")
        self.write(
            "tests/test_report_steps.py",
            "def deduplicate_report_steps(values):\n    return list(dict.fromkeys(values))\n",
        )

        for changed_path in ("conftest.py", "tests/test_report_steps.py"):
            with self.subTest(path=changed_path):
                report = navigator.decide(
                    "fix repeated report steps",
                    self.root,
                    [changed_path],
                    "tailtrail",
                    detect_git_changes=False,
                )
                candidate = next(
                    row
                    for row in report["scope_candidates"]
                    if row["path"] == changed_path
                )
                self.assertEqual(candidate["role"], "test")
                self.assertNotEqual(candidate["status"], "included")
                self.assertEqual(
                    report["scope_evidence"]["requirements"][0]["implementation_owners"],
                    [],
                )
                self.assertEqual(report["scope_quality"]["status"], "blocked")

    def test_conftest_is_editable_only_for_an_explicit_test_only_request(self) -> None:
        self.write("conftest.py", "def report_fixture():\n    return []\n")
        result = self.run_start(
            "update tests only",
            "ns6-root-conftest-test-only",
            "--changed",
            "conftest.py",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["navigator"]["scope_quality"]["mode"], "test-only")
        self.assertEqual(
            payload["navigator"]["requirement_matrix"][0]["likely_paths"],
            ["conftest.py"],
        )

    def test_ambiguous_owners_return_exactly_one_question_and_create_no_run(self) -> None:
        self.write("services/a/parser.py", "def parse_multiline(value):\n    return value\n")
        self.write("services/b/parser.py", "def parse_multiline(value):\n    return value\n")
        self.write("tests/test_parser.py", "# parser multiline proof\n")
        result = self.run_start("fix parser multiline splitting", "ns4-ambiguous")
        self.assertEqual(result.returncode, 2, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(
            payload["scope_question_precondition"]["state"], "eligible"
        )
        question = payload["scope_quality"]["question"]
        self.assertEqual(question["question_id"], "SCOPE-Q1")
        self.assertEqual(len(question["options"]), 2)
        self.assertEqual(len(question["option_evidence"]), 2)
        default_report = task_start.render_markdown(payload)
        verbose_report = task_start.render_markdown(payload, verbose=True)
        self.assertIn("## Why TailTrail stopped", default_report)
        self.assertIn("Missing discriminator", default_report)
        self.assertNotIn("## Complete scope diagnostics", default_report)
        self.assertNotIn("Scope reason codes:", default_report)
        self.assertIn("## Complete scope diagnostics", verbose_report)
        self.assertIn("Read-loop termination:", verbose_report)
        self.assertIn("Scope-question validation:", verbose_report)
        self.assertIn("### Candidate diagnostics", verbose_report)
        self.assertFalse((self.root / ".tailtrail" / "runs" / "ns4-ambiguous").exists())

    def test_start_transaction_rolls_back_when_post_lock_persistence_fails(self) -> None:
        self.write("src/owner.py", "def owner():\n    return True\n")
        original = task_start.planning_lock.save_start_report
        original_argv = sys.argv
        try:
            task_start.planning_lock.save_start_report = lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("injected persistence failure"))
            sys.argv = [
                "task-start.py", "change owner behavior", "--root", self.root.as_posix(),
                "--changed", "src/owner.py", "--format", "json", "--planning-run-id", "ns4-rollback",
            ]
            with self.assertRaises(SystemExit) as raised, redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                task_start.main()
            self.assertEqual(raised.exception.code, 2)
        finally:
            sys.argv = original_argv
            task_start.planning_lock.save_start_report = original
        self.assertFalse((self.root / ".tailtrail" / "runs" / "ns4-rollback").exists())

    def test_activation_rejects_tampered_scope_before_anchor_creation(self) -> None:
        self.write("src/owner.py", "def owner():\n    return True\n")
        started = self.run_start(
            "change owner behavior", "ns4-tamper", "--changed", "src/owner.py"
        )
        self.assertEqual(started.returncode, 0, started.stderr)
        report_path = self.root / ".tailtrail" / "runs" / "ns4-tamper" / "planning" / "start-report-v1.json"
        saved = json.loads(report_path.read_text(encoding="utf-8"))
        saved["report"]["navigator"]["scope_evidence"]["candidates"][0]["status"] = "excluded"
        report_path.write_text(json.dumps(saved), encoding="utf-8")
        activated = subprocess.run(
            [
                sys.executable, (ROOT / "scripts" / "planning_lock.py").as_posix(), "activate",
                "--root", self.root.as_posix(), "--run-id", "ns4-tamper", "--approved", "--format", "json",
            ],
            cwd=self.root, text=True, capture_output=True, check=False,
        )
        self.assertEqual(activated.returncode, 2)
        self.assertIn("scope evidence fingerprint is invalid", activated.stdout)
        self.assertFalse((self.root / ".tailtrail" / "runs" / "ns4-tamper" / "anchors" / "approved-v1.json").exists())

    def test_ns5_renderers_separate_roles_and_keep_exclusions_verbose_only(self) -> None:
        fixture = load_json(FIXTURE_ROOT / "wrong-file-selection.json")
        for relative, body in fixture["repository_files"].items():
            self.write(relative, body)
        result = self.run_start(
            fixture["goal"], "ns5-render",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        normal = task_start.compact_start_report(payload)
        verbose = task_start.verbose_start_report(payload)

        for rendered in (normal, verbose):
            self.assertIn("### Implementation owners", rendered)
            self.assertIn("### Inspection paths", rendered)
            self.assertIn("### Existing proof paths", rendered)
            self.assertNotIn("+--------------------------------------------+", rendered)
        self.assertNotIn("| Path | Requirements | Confidence | Evidence |", normal)
        self.assertNotIn("| Path | Requirements | Confidence | Evidence |", verbose)
        for rendered in (normal, verbose):
            self.assertIn("- **Requirements:**", rendered)
            self.assertIn("- **Confidence:**", rendered)
            self.assertIn("- **Evidence:**", rendered)
        self.assertNotIn("### Excluded candidates", normal)
        self.assertNotIn("tests/test_aidlc_requirements.py", normal)
        self.assertIn("### Excluded candidates", verbose)
        self.assertIn("tests/test_aidlc_requirements.py", verbose)
        self.assertIn("### Investigation limits", verbose)
        self.assertNotIn("| --- | --- | --- | --- |", verbose)


if __name__ == "__main__":
    unittest.main()
