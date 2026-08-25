from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if ROOT.as_posix() in sys.path:
    sys.path.remove(ROOT.as_posix())
sys.path.insert(0, ROOT.as_posix())
loaded_tailtrail = sys.modules.get("tailtrail")
if loaded_tailtrail is not None and not hasattr(loaded_tailtrail, "__path__"):
    del sys.modules["tailtrail"]

from tailtrail.hosts.contracts import HOSTS, adapter_version, contract, contracts, core_files
from tailtrail.hosts.diagnostics import diagnose
from tailtrail.install import InstallEngine


def load_script(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


runtime = load_script("enterprise_e4_runtime", "scripts/host-runtime-conformance.py")
first_run = load_script("enterprise_e4_first_run", "scripts/first-run.py")


def ownership(target: Path, host: str) -> dict:
    return json.loads((target / ".tailtrail" / "install" / "manifests" / f"{host}.json").read_text(encoding="utf-8"))


class EnterpriseHostAdapterTests(unittest.TestCase):
    def test_closed_v3_contract_defines_exact_equal_quality_host_surfaces(self) -> None:
        matrix = contracts(ROOT)
        schema = json.loads((ROOT / "schemas" / "host-adapter-contract.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(matrix["adapter_version"], "v3")
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(tuple(item["id"] for item in matrix["hosts"]), HOSTS)
        for host in HOSTS:
            entry = contract(host, ROOT)
            self.assertEqual(entry["qualification"], "contract-tested")
            self.assertFalse(entry["supported"])
            self.assertTrue(entry["core_files"])
            self.assertTrue(entry["first_action"]["invocation"])
            self.assertEqual(entry["capabilities"]["policy_enforcement"], "ci-authoritative")
            self.assertTrue(all(entry["capabilities"][key] == "approval-required" for key in ("global_settings", "network_activity", "account_changes")))
            self.assertEqual(entry["migration"]["rollback"], "E3 transaction backup")

    def test_every_host_uses_the_common_core_install_doctor_update_rollback_uninstall_lifecycle(self) -> None:
        for host in HOSTS:
            with self.subTest(host=host), tempfile.TemporaryDirectory() as temp:
                target = Path(temp)
                installed = InstallEngine(target).apply("install", host, "core")
                self.assertTrue(installed.ok, installed.issues)
                manifest = ownership(target, host)
                self.assertEqual(manifest["adapter_version"], adapter_version(ROOT))
                self.assertEqual(set(manifest["files"]), {destination for _source, destination in core_files(host, ROOT)})
                doctor = InstallEngine(target).doctor(host)
                self.assertTrue(doctor.ok, doctor.issues)
                self.assertEqual(doctor.diagnostics["composition"], "passed")
                self.assertFalse(doctor.diagnostics["supported"])
                self.assertEqual(doctor.diagnostics["runtime_status"], "not-validated")
                update = InstallEngine(target).apply("update", host)
                self.assertEqual(update.status, "current")
                removed = InstallEngine(target).uninstall(host)
                self.assertTrue(removed.ok, removed.issues)
                restored = InstallEngine(target).rollback(removed.transaction_id or "")
                self.assertTrue(restored.ok, restored.issues)
                self.assertTrue(InstallEngine(target).verify(host).ok)

    def test_first_run_is_host_native_and_claude_cannot_false_pass(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)
            result = first_run.check(target, "claude", "tailtrail")
            self.assertEqual(result["installation"], "incomplete")
            self.assertEqual(set(result["missing"]), {"CLAUDE.md", ".claude/commands/tailtrail-start.md"})
            self.assertEqual(result["first_action"]["surface"], "Claude Code")
            self.assertTrue(result["first_action"]["command"].startswith("/tailtrail-start"))
            InstallEngine(target).apply("install", "claude", "core")
            self.assertEqual(first_run.check(target, "claude", "tailtrail")["installation"], "passed")

    def test_diagnostics_reject_stale_contract_composition_and_generic_false_positives(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)
            InstallEngine(target).apply("install", "claude", "core")
            manifest_path = target / ".tailtrail" / "install" / "manifests" / "claude.json"
            payload = ownership(target, "claude")
            payload["adapter_version"] = "v2"
            claude = target / "CLAUDE.md"
            claude.write_text("TailTrail For Claude\n", encoding="utf-8")
            payload["files"]["CLAUDE.md"]["sha256"] = hashlib.sha256(claude.read_bytes()).hexdigest()
            payload["files"]["CLAUDE.md"]["size"] = claude.stat().st_size
            manifest_path.write_text(json.dumps(payload), encoding="utf-8")
            result = diagnose(target, "claude", manifest=payload, root=ROOT, runner=lambda _command: (127, ""))
            self.assertEqual(result["installation"], "failed")
            self.assertTrue(any("adapter contract mismatch" in item for item in result["issues"]))
            self.assertTrue(any("composition marker" in item for item in result["issues"]))
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)
            (target / "CLAUDE.md").write_text("unmanaged generic file", encoding="utf-8")
            result = diagnose(target, "claude", manifest=None, root=ROOT, runner=lambda _command: (127, ""))
            self.assertEqual(result["installation"], "not-installed")
            self.assertIn(".claude/commands/tailtrail-start.md", result["missing_files"])

    def test_adapter_metadata_migration_is_transactional_and_rollback_restores_prior_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)
            InstallEngine(target).apply("install", "codex", "core")
            path = target / ".tailtrail" / "install" / "manifests" / "codex.json"
            old = ownership(target, "codex")
            old.pop("adapter_version")
            path.write_text(json.dumps(old), encoding="utf-8")
            migrated = InstallEngine(target).apply("update", "codex")
            self.assertTrue(migrated.ok, migrated.issues)
            self.assertIn("adapter:unrecorded->v3", ownership(target, "codex")["migrations"])
            rollback = InstallEngine(target).rollback(migrated.transaction_id or "")
            self.assertTrue(rollback.ok, rollback.issues)
            self.assertNotIn("adapter_version", ownership(target, "codex"))

    def test_each_host_prepares_the_same_sanitized_six_scenario_receipt_bundle(self) -> None:
        for host in HOSTS:
            with self.subTest(host=host), tempfile.TemporaryDirectory() as temp:
                target = Path(temp)
                bundle = runtime.prepare(target, host)
                self.assertEqual(bundle["host"], host)
                self.assertEqual(bundle["adapter_version"], "v3")
                self.assertEqual(len(bundle["scenarios"]), 6)
                self.assertEqual(bundle["receipt_schema"], "schemas/host-runtime-receipt.schema.json")
                self.assertNotIn("source_code", json.dumps(bundle))

    def test_cli_doctor_exposes_qualification_limits_without_claiming_support(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)
            install = subprocess.run([sys.executable, "scripts/tailtrail.py", "install", "--host", "copilot", "--profile", "core", "--target", target.as_posix()], cwd=ROOT, text=True, capture_output=True, check=False)
            doctor = subprocess.run([sys.executable, "scripts/tailtrail.py", "doctor", "--host", "copilot", "--target", target.as_posix(), "--format", "json"], cwd=ROOT, text=True, capture_output=True, check=False)
            self.assertEqual(install.returncode, 0, install.stderr + install.stdout)
            self.assertEqual(doctor.returncode, 0, doctor.stderr + doctor.stdout)
            payload = json.loads(doctor.stdout)
            self.assertEqual(payload["diagnostics"]["qualification"], "contract-tested")
            self.assertFalse(payload["diagnostics"]["supported"])
            self.assertEqual(payload["diagnostics"]["version_detection"]["state"], "host-reported-required")


if __name__ == "__main__":
    unittest.main()
