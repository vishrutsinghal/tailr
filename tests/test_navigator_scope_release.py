from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, (ROOT / "scripts").as_posix())


def load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


SCOPE = load("ns9_scope_test", "scripts/navigator_scope.py")
RELEASE = load("ns9_release_test", "scripts/navigator-scope-release.py")
CONTRACTS = load("ns9_contracts_test", "scripts/workflow_runtime/contracts.py")
MCP = load("ns9_mcp_test", "scripts/mcp-server.py")
LOCK = load("ns9_lock_test", "scripts/planning-lock.py")


class NavigatorScopeReleaseTests(unittest.TestCase):
    def test_release_policy_is_closed_sealed_and_invalid_values_fail_closed(self) -> None:
        schema = json.loads((ROOT / "schemas/navigator-scope-release-policy.schema.json").read_text(encoding="utf-8"))
        policy = SCOPE.seal_scope_policy(SCOPE.SCOPE_UNAVAILABLE, "release-incident")
        self.assertEqual([], CONTRACTS.validate_document(policy, schema))
        self.assertEqual(policy, SCOPE.validate_scope_policy(policy))

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / SCOPE.SCOPE_POLICY_PATH
            path.parent.mkdir(parents=True)
            path.write_text('{"state":"available"}\n', encoding="utf-8")
            status = SCOPE.scope_release_status(root)
        self.assertEqual(SCOPE.SCOPE_UNAVAILABLE, status["state"])
        self.assertEqual("invalid-policy", status["source"])
        self.assertEqual("none", status["fallback"])

    def test_environment_can_disable_but_cannot_override_disabled_policy(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            RELEASE.write_policy(root, SCOPE.SCOPE_UNAVAILABLE, "operator-rollback", True)
            configured = SCOPE.scope_release_status(root, {SCOPE.SCOPE_POLICY_ENV: SCOPE.SCOPE_AVAILABLE})
            environment = SCOPE.scope_release_status(root, {SCOPE.SCOPE_POLICY_ENV: "disabled"})
        self.assertEqual(SCOPE.SCOPE_UNAVAILABLE, configured["state"])
        self.assertEqual("repository-policy", configured["source"])
        self.assertEqual(SCOPE.SCOPE_UNAVAILABLE, environment["state"])
        self.assertEqual("environment", environment["source"])

    def test_kill_switch_blocks_cli_and_mcp_before_any_run_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "src").mkdir()
            (root / "src" / "service.py").write_text("def service(): return True\n", encoding="utf-8")
            RELEASE.write_policy(root, SCOPE.SCOPE_UNAVAILABLE, "release-rollback", True)
            command = [sys.executable, str(ROOT / "scripts" / "tailtrail.py"), "start", "change service", "--root", str(root), "--changed", "src/service.py", "--planning-run-id", "must-not-exist", "--format", "json"]
            result = subprocess.run(command, cwd=root, text=True, capture_output=True, check=False)
            report = json.loads(result.stdout)
            mcp = MCP.tailtrail_start({"goal": "change service", "root": str(root), "changed": ["src/service.py"], "run_id": "mcp-must-not-exist", "format": "json", "approved": True})
            runs = root / ".tailtrail" / "runs"
        self.assertEqual(2, result.returncode)
        self.assertEqual(SCOPE.SCOPE_UNAVAILABLE, report["status"])
        self.assertTrue(
            report["scope_question_precondition"]["scope_question_allowed"]
        )
        self.assertIsNone(report["planning_lock"])
        self.assertEqual(SCOPE.SCOPE_UNAVAILABLE, mcp["result"]["status"])
        self.assertTrue(
            mcp["result"]["scope_question_precondition"]["scope_question_allowed"]
        )
        self.assertIsNone(mcp["scope_contract"])
        self.assertFalse(runs.exists())

    def test_migration_audit_keeps_v1_byte_identical_and_rejects_no_lexical_upgrade(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            planning = root / ".tailtrail" / "runs" / "legacy" / "planning"
            planning.mkdir(parents=True)
            path = planning / "start-report-v1.json"
            original = b'{"report":{"navigator":{"likely_impacted_files":["tests/test_requirements.py"]}}}\n'
            path.write_bytes(original)
            report = RELEASE.migration_report(root)
            schema = json.loads((ROOT / "schemas/navigator-scope-migration-report.schema.json").read_text(encoding="utf-8"))
            issues = CONTRACTS.validate_document(report, schema)
            after = path.read_bytes()
        self.assertEqual([], issues)
        self.assertEqual(original, after)
        self.assertEqual("legacy-v1-immutable", report["records"][0]["classification"])
        self.assertEqual("not-reinterpreted", report["records"][0]["scope_interpretation"])
        self.assertTrue(report["immutability"]["content_unchanged"])
        self.assertFalse(report["shadow_comparison"]["v1_may_override_v2"])

    def test_legacy_run_can_finish_only_under_its_saved_authority(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            LOCK.create(root, "legacy saved requirement", "legacy-finish")
            saved = {"goal": "legacy saved requirement", "navigator": {"likely_impacted_files": ["tests/test_requirements.py"]}}
            LOCK.save_start_report(root, "legacy-finish", saved)
            compatibility = LOCK.validate_saved_scope_decision(root, "legacy-finish", saved)
            before = (root / ".tailtrail" / "runs" / "legacy-finish" / "planning" / "start-report-v1.json").read_bytes()
            activated = LOCK.activate(root, "legacy-finish", True)
            after = (root / ".tailtrail" / "runs" / "legacy-finish" / "planning" / "start-report-v1.json").read_bytes()
        self.assertEqual("approved", activated["planning_lock"]["status"])
        self.assertEqual("legacy", compatibility["status"])
        self.assertEqual(before, after)

    def test_rollback_mutation_is_approval_gated_and_preserves_existing_runs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            artifact = root / ".tailtrail" / "runs" / "v2" / "planning" / "start-report-v1.json"
            artifact.parent.mkdir(parents=True)
            artifact.write_text('{"saved":"v2"}\n', encoding="utf-8")
            before = artifact.read_bytes()
            with self.assertRaisesRegex(RELEASE.ScopeReleaseError, "requires --approved"):
                RELEASE.write_policy(root, SCOPE.SCOPE_UNAVAILABLE, "operator-rollback", False)
            enabled = RELEASE.write_policy(root, SCOPE.SCOPE_UNAVAILABLE, "operator-rollback", True)
            disabled = RELEASE.write_policy(root, SCOPE.SCOPE_AVAILABLE, "operator-recovery", True)
            after = artifact.read_bytes()
        self.assertEqual("enabled", enabled["status"])
        self.assertEqual("disabled", disabled["status"])
        self.assertEqual(before, after)

    def test_real_cli_mcp_closure_and_negative_release_proof(self) -> None:
        report = RELEASE.release_proof(ROOT)
        schema = json.loads((ROOT / "schemas/navigator-scope-release-proof.schema.json").read_text(encoding="utf-8"))
        self.assertEqual("passed", report["status"])
        self.assertEqual([], CONTRACTS.validate_document(report, schema))
        self.assertTrue(all(report["checks"].values()))
        self.assertEqual(["linux", "macos", "windows", "wsl"], report["platforms"])
        self.assertEqual(report["real_run"]["cli"]["decision_fingerprint"], report["real_run"]["mcp"]["decision_fingerprint"])
        self.assertEqual("complete", report["real_run"]["closure"]["overall_status"])
        self.assertTrue(report["real_run"]["closure"]["completion_report_present"])
        self.assertEqual("none", report["real_run"]["negative"]["fallback"])
        self.assertEqual("passed", report["calibration"]["status"])
        self.assertEqual(0, report["calibration"]["metrics"]["false_stop_count"])
        self.assertEqual(0, report["calibration"]["metrics"]["irrelevant_option_count"])
        self.assertEqual(0, report["calibration"]["metrics"]["unsafe_lock_count"])
        self.assertEqual(7, report["calibration"]["language_profiles"]["passed"])
        self.assertEqual("passed", report["adapter_conformance"]["status"])
        self.assertEqual("passed", report["artifact_coverage"]["status"])
        self.assertEqual([], report["artifact_coverage"]["missing_files"])
        self.assertEqual([], report["artifact_coverage"]["missing_source_release_inventory"])
        self.assertEqual([], report["artifact_coverage"]["missing_package_inventory"])
        self.assertEqual("passed", report["local_runtime_hygiene"]["status"])
        self.assertEqual(0, report["local_runtime_hygiene"]["tracked_violation_count"])

    def test_fsr6_release_artifact_inventory_fails_closed_for_missing_member(self) -> None:
        fixture = json.loads(RELEASE.RELEASE_FIXTURE.read_text(encoding="utf-8"))
        fixture["required_fsr6_artifacts"].append("schemas/not-real-fsr6.schema.json")

        coverage = RELEASE.fsr6_artifact_coverage(fixture)

        self.assertEqual("failed", coverage["status"])
        self.assertEqual(["schemas/not-real-fsr6.schema.json"], coverage["missing_files"])
        self.assertEqual(["schemas/not-real-fsr6.schema.json"], coverage["missing_source_release_inventory"])
        self.assertEqual(["schemas/not-real-fsr6.schema.json"], coverage["missing_package_inventory"])

    def test_eval_router_exposes_migration_and_rollback_status(self) -> None:
        for action in ("migration", "rollback-status"):
            result = subprocess.run([sys.executable, str(ROOT / "scripts" / "tailtrail.py"), "eval", "scope", action, "--root", str(ROOT), "--format", "json"], cwd=ROOT, text=True, capture_output=True, check=False)
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertTrue(json.loads(result.stdout)["type"].startswith("tailtrail-navigator-scope-"))


if __name__ == "__main__":
    unittest.main()
