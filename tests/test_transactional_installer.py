from __future__ import annotations

import json
import os
import shutil
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

from tailtrail.install import InstallEngine, InstallFailure, UncleanInterruption


def run(*args: str, cwd: Path = ROOT, expected: int = 0) -> subprocess.CompletedProcess[str]:
    result = subprocess.run([sys.executable, *args], cwd=cwd, text=True, capture_output=True, check=False)
    if result.returncode != expected:
        raise AssertionError(f"expected {expected}, got {result.returncode}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}")
    return result


def manifest(target: Path, host: str) -> dict[str, object]:
    return json.loads((target / ".tailtrail" / "install" / "manifests" / f"{host}.json").read_text(encoding="utf-8"))


def changed_source(base: Path, name: str, body: str) -> Path:
    source = base / name
    for relative in (
        "AGENTS.md",
        ".codex-plugin/plugin.json",
        "skills/tailtrail/SKILL.md",
        "skills/tailtrail-review/SKILL.md",
        "skills/tailtrail-start/SKILL.md",
    ):
        destination = source / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, destination)
    (source / "AGENTS.md").write_text(body, encoding="utf-8")
    return source


class TransactionalInstallerTests(unittest.TestCase):
    def test_plan_and_ownership_schemas_are_versioned_and_closed(self) -> None:
        for name in ("install-plan.schema.json", "install-ownership-manifest.schema.json", "install-journal-event.schema.json"):
            schema = json.loads((ROOT / "schemas" / name).read_text(encoding="utf-8"))
            self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
            self.assertEqual(schema["type"], "object")
        ownership = json.loads((ROOT / "schemas" / "install-ownership-manifest.schema.json").read_text(encoding="utf-8"))
        self.assertFalse(ownership["additionalProperties"])

    def test_dry_run_is_deterministic_and_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)
            first = InstallEngine(target).apply("install", "codex", "core", dry_run=True)
            second = InstallEngine(target).apply("install", "codex", "core", dry_run=True)
            self.assertEqual(first.plan, second.plan)
            self.assertEqual(first.status, "dry-run")
            self.assertEqual(list(target.iterdir()), [])

    def test_all_hosts_use_one_engine_and_write_per_host_manifests(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)
            for host in ("codex", "copilot", "claude"):
                result = InstallEngine(target).apply("install", host, "core")
                self.assertTrue(result.ok, result.issues)
                installed = manifest(target, host)
                self.assertEqual(installed["schema_version"], "1")
                self.assertEqual(installed["host"], host)
                self.assertEqual(installed["ownership"], "tailtrail-managed")
                self.assertTrue(installed["files"])
                self.assertTrue(InstallEngine(target).verify(host).ok)
            for script in ("install-local.py", "install-copilot.py", "update-copilot.py", "update-tailtrail.py"):
                body = (ROOT / "scripts" / script).read_text(encoding="utf-8")
                self.assertIn("tailtrail.install.cli", body)

    def test_idempotent_reinstall_has_no_transaction_or_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)
            first = InstallEngine(target).apply("install", "claude", "core")
            second = InstallEngine(target).apply("install", "claude", "core")
            self.assertIsNotNone(first.transaction_id)
            self.assertEqual(second.status, "current")
            self.assertIsNone(second.transaction_id)
            self.assertEqual(second.changed, [])

    def test_unrelated_and_conflicting_user_files_are_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)
            (target / "notes.txt").write_text("user\n", encoding="utf-8")
            (target / "AGENTS.md").write_text("existing\n", encoding="utf-8")
            result = InstallEngine(target).apply("install", "codex", "core")
            self.assertEqual(result.status, "conflict")
            self.assertEqual((target / "AGENTS.md").read_text(encoding="utf-8"), "existing\n")
            self.assertEqual((target / "notes.txt").read_text(encoding="utf-8"), "user\n")
            self.assertFalse((target / ".codex-plugin").exists())

    def test_force_backs_up_conflict_and_rollback_restores_user_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)
            (target / "AGENTS.md").write_text("user-owned\n", encoding="utf-8")
            result = InstallEngine(target).apply("install", "codex", "core", force=True)
            self.assertTrue(result.ok, result.issues)
            self.assertNotEqual((target / "AGENTS.md").read_text(encoding="utf-8"), "user-owned\n")
            rollback = InstallEngine(target).rollback(result.transaction_id or "")
            self.assertTrue(rollback.ok, rollback.issues)
            self.assertEqual((target / "AGENTS.md").read_text(encoding="utf-8"), "user-owned\n")
            self.assertFalse((target / ".tailtrail" / "install" / "manifests" / "codex.json").exists())

    def test_update_replaces_only_previous_managed_hash_and_rolls_back(self) -> None:
        with tempfile.TemporaryDirectory() as temp, tempfile.TemporaryDirectory() as sources:
            target = Path(temp)
            InstallEngine(target).apply("install", "codex", "core")
            old = (target / "AGENTS.md").read_bytes()
            source = changed_source(Path(sources), "v2", "new managed guidance\n")
            update = InstallEngine(target, package_root=source).apply("update", "codex")
            self.assertTrue(update.ok, update.issues)
            self.assertEqual((target / "AGENTS.md").read_text(encoding="utf-8"), "new managed guidance\n")
            rollback = InstallEngine(target).rollback(update.transaction_id or "")
            self.assertTrue(rollback.ok, rollback.issues)
            self.assertEqual((target / "AGENTS.md").read_bytes(), old)

    def test_modified_managed_file_blocks_update_and_force_preserves_backup(self) -> None:
        with tempfile.TemporaryDirectory() as temp, tempfile.TemporaryDirectory() as sources:
            target = Path(temp)
            InstallEngine(target).apply("install", "codex", "core")
            (target / "AGENTS.md").write_text("local modification\n", encoding="utf-8")
            source = changed_source(Path(sources), "v2", "new upstream\n")
            blocked = InstallEngine(target, package_root=source).apply("update", "codex")
            self.assertEqual(blocked.status, "conflict")
            self.assertEqual((target / "AGENTS.md").read_text(encoding="utf-8"), "local modification\n")
            forced = InstallEngine(target, package_root=source).apply("update", "codex", force=True)
            self.assertTrue(forced.ok, forced.issues)
            backup = target / ".tailtrail" / "install" / "transactions" / str(forced.transaction_id) / "backup" / "AGENTS.md"
            self.assertEqual(backup.read_text(encoding="utf-8"), "local modification\n")

    def test_failed_update_restores_every_prior_file_and_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp, tempfile.TemporaryDirectory() as sources:
            target = Path(temp)
            InstallEngine(target).apply("install", "codex", "core")
            before_file = (target / "AGENTS.md").read_bytes()
            before_manifest = (target / ".tailtrail" / "install" / "manifests" / "codex.json").read_bytes()
            source = changed_source(Path(sources), "v2", "must roll back\n")

            def fail(checkpoint: str) -> None:
                if checkpoint == "before-verify":
                    raise RuntimeError("verification injection")

            failed = InstallEngine(target, package_root=source, fault=fail).apply("update", "codex")
            self.assertEqual(failed.status, "restored")
            self.assertEqual((target / "AGENTS.md").read_bytes(), before_file)
            self.assertEqual((target / ".tailtrail" / "install" / "manifests" / "codex.json").read_bytes(), before_manifest)

    def test_corrupt_staging_fails_verification_and_restores(self) -> None:
        with tempfile.TemporaryDirectory() as temp, tempfile.TemporaryDirectory() as sources:
            target = Path(temp)
            InstallEngine(target).apply("install", "codex", "core")
            before = (target / "AGENTS.md").read_bytes()
            source = changed_source(Path(sources), "v2", "corruption target\n")
            engine: InstallEngine

            def corrupt(checkpoint: str) -> None:
                if checkpoint == "staged:AGENTS.md":
                    staged = next(engine.transactions_root.glob("*/staging/AGENTS.md"))
                    staged.write_text("corrupt\n", encoding="utf-8")

            engine = InstallEngine(target, package_root=source, fault=corrupt)
            result = engine.apply("update", "codex")
            self.assertEqual(result.status, "restored")
            self.assertEqual((target / "AGENTS.md").read_bytes(), before)

    def test_unclean_interruption_is_recovered_by_next_operation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)
            interrupted = False

            def stop(checkpoint: str) -> None:
                nonlocal interrupted
                if checkpoint.startswith("applied:") and not interrupted:
                    interrupted = True
                    raise UncleanInterruption()

            with self.assertRaises(UncleanInterruption):
                InstallEngine(target, fault=stop).apply("install", "codex", "core")
            resumed = InstallEngine(target).apply("install", "codex", "core")
            self.assertTrue(resumed.ok, resumed.issues)
            self.assertEqual(len(resumed.recovered_transactions), 1)
            self.assertTrue(InstallEngine(target).verify("codex").ok)

    def test_repair_restores_missing_managed_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)
            InstallEngine(target).apply("install", "claude", "core")
            command = target / ".claude" / "commands" / "tailtrail-start.md"
            command.unlink()
            self.assertFalse(InstallEngine(target).verify("claude").ok)
            repaired = InstallEngine(target).apply("repair", "claude")
            self.assertTrue(repaired.ok, repaired.issues)
            self.assertTrue(command.is_file())

    def test_uninstall_preserves_modified_files_and_force_is_rollbackable(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)
            InstallEngine(target).apply("install", "claude", "core")
            (target / "CLAUDE.md").write_text("user change\n", encoding="utf-8")
            blocked = InstallEngine(target).uninstall("claude")
            self.assertEqual(blocked.status, "conflict")
            self.assertTrue((target / ".claude" / "commands" / "tailtrail-start.md").exists())
            forced = InstallEngine(target).uninstall("claude", force=True)
            self.assertTrue(forced.ok, forced.issues)
            self.assertFalse((target / "CLAUDE.md").exists())
            restored = InstallEngine(target).rollback(forced.transaction_id or "")
            self.assertTrue(restored.ok, restored.issues)
            self.assertEqual((target / "CLAUDE.md").read_text(encoding="utf-8"), "user change\n")
            InstallEngine(target).uninstall("claude", force=True)
            repeated = InstallEngine(target).uninstall("claude")
            self.assertEqual(repeated.status, "not-installed")
            self.assertTrue(repeated.ok)

    def test_symlink_traversal_and_inaccessible_targets_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp, tempfile.TemporaryDirectory() as outside:
            target = Path(temp)
            (target / ".codex-plugin").symlink_to(Path(outside), target_is_directory=True)
            with self.assertRaisesRegex(InstallFailure, "symlink"):
                InstallEngine(target).plan("install", "codex", "core")
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)
            target.chmod(0o555)
            try:
                with self.assertRaisesRegex(InstallFailure, "not writable"):
                    InstallEngine(target)
            finally:
                target.chmod(0o755)

    def test_live_lock_blocks_and_stale_lock_recovers(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)
            lock = target / ".tailtrail" / "install" / "lifecycle.lock"
            lock.parent.mkdir(parents=True)
            lock.write_text(json.dumps({"pid": os.getpid()}), encoding="utf-8")
            with self.assertRaisesRegex(InstallFailure, "another installer"):
                InstallEngine(target).apply("install", "claude", "core")
            lock.write_text(json.dumps({"pid": 99999999}), encoding="utf-8")
            result = InstallEngine(target).apply("install", "claude", "core")
            self.assertTrue(result.ok, result.issues)

    def test_cli_text_json_exit_codes_and_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)
            dry = run("scripts/tailtrail.py", "install", "--host", "copilot", "--profile", "core", "--target", target.as_posix(), "--dry-run", "--format", "json")
            payload = json.loads(dry.stdout)
            self.assertEqual(payload["type"], "tailtrail-install-result")
            self.assertEqual(payload["status"], "dry-run")
            self.assertEqual(list(target.iterdir()), [])
            applied = run("scripts/tailtrail.py", "install", "--host", "copilot", "--profile", "core", "--target", target.as_posix())
            self.assertIn("TailTrail install: passed", applied.stdout)
            missing = run("scripts/tailtrail.py", "verify", "--host", "claude", "--target", target.as_posix(), "--format", "json", expected=3)
            self.assertFalse(json.loads(missing.stdout)["ok"])

    def test_extended_payload_runs_its_own_lifecycle_cli(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)
            installed = InstallEngine(target).apply("install", "codex", "extended")
            self.assertTrue(installed.ok, installed.issues)
            launcher = target / ".tailtrail" / "install" / "payload" / "codex" / "scripts" / "tailtrail.py"
            status = run(
                launcher.as_posix(),
                "status",
                "--host",
                "codex",
                "--target",
                target.as_posix(),
                "--format",
                "json",
                cwd=target,
            )
            payload = json.loads(status.stdout)
            self.assertTrue(payload["ok"], payload)
            self.assertEqual(payload["profile"], "extended")
            common = launcher.parents[2] / "common" / installed.version
            self.assertTrue((common / "tailtrail" / "install" / "cli.py").is_file())
            for name in ("plan-report.json", "debug-report.json", "closure-report.json"):
                self.assertTrue((common / "benchmarks" / "product-maturity" / "presentation-v1" / name).is_file())
            conformance = run(
                launcher.as_posix(),
                "presentation",
                "conformance",
                cwd=target,
            )
            conformance_payload = json.loads(conformance.stdout)
            self.assertEqual(conformance_payload["status"], "passed")
            self.assertEqual(conformance_payload["scenario_count"], 3)
            self.assertFalse((launcher.parents[1] / "tailtrail" / "install" / "cli.py").exists())

    def test_retention_keeps_only_five_completed_transactions_per_host(self) -> None:
        with tempfile.TemporaryDirectory() as temp, tempfile.TemporaryDirectory() as sources:
            target = Path(temp)
            InstallEngine(target).apply("install", "codex", "core")
            for index in range(7):
                source = changed_source(Path(sources), f"v{index}", f"managed {index}\n")
                result = InstallEngine(target, package_root=source).apply("update", "codex")
                self.assertTrue(result.ok, result.issues)
            transactions = [path for path in (target / ".tailtrail" / "install" / "transactions").iterdir() if path.is_dir()]
            self.assertLessEqual(len(transactions), 5)


if __name__ == "__main__":
    unittest.main()
