from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) in sys.path:
    sys.path.remove(str(ROOT))
sys.path.insert(0, str(ROOT))
loaded_tailtrail = sys.modules.get("tailtrail")
if loaded_tailtrail is not None and Path(getattr(loaded_tailtrail, "__file__", "")).resolve() == ROOT / "scripts" / "tailtrail.py":
    del sys.modules["tailtrail"]

from tailtrail import ExitCode  # noqa: E402
from tailtrail.kernel import python_compatibility  # noqa: E402
from tailtrail.migrations import required_migrations  # noqa: E402
from tailtrail.resources import verify_package  # noqa: E402


def load_proof():
    spec = importlib.util.spec_from_file_location("package_release_proof_test", ROOT / "scripts" / "package-release-proof.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


PROOF = load_proof()


def run(command: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None, expected: int = 0) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, cwd=cwd, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != expected:
        raise AssertionError(f"command returned {result.returncode}, expected {expected}: {command}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}")
    return result


class SelfContainedPackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp = tempfile.TemporaryDirectory()
        cls.output = Path(cls.temp.name)
        cls.repro_output = cls.output / "repro"
        cls.repro_output.mkdir()
        cls.build_preexisting = (ROOT / "build").exists()
        env = {**os.environ, "SOURCE_DATE_EPOCH": "1704067200"}
        run([sys.executable, "-m", "pip", "wheel", ".", "--no-deps", "--no-build-isolation", "--wheel-dir", str(cls.output)], cwd=ROOT, env=env)
        run([sys.executable, "setup.py", "sdist", "--dist-dir", str(cls.output)], cwd=ROOT, env=env)
        cls.wheel = next(cls.output.glob("*.whl"))
        cls.sdist = next(cls.output.glob("*.tar.gz"))
        run([sys.executable, "-m", "pip", "wheel", ".", "--no-deps", "--no-build-isolation", "--wheel-dir", str(cls.repro_output)], cwd=ROOT, env=env)
        run([sys.executable, "setup.py", "sdist", "--dist-dir", str(cls.repro_output)], cwd=ROOT, env=env)

    @classmethod
    def tearDownClass(cls) -> None:
        if not cls.build_preexisting:
            shutil.rmtree(ROOT / "build", ignore_errors=True)
        cls.temp.cleanup()

    def test_declared_python_and_exit_contract(self) -> None:
        self.assertTrue(python_compatibility((3, 12))[0])
        self.assertTrue(python_compatibility((3, 13))[0])
        supported, message = python_compatibility((3, 11))
        self.assertFalse(supported)
        self.assertIn(">=3.12,<3.14", message)
        self.assertEqual({int(item) for item in ExitCode}, {0, 1, 2, 3, 70})

    def test_migration_contract_is_versioned_and_fail_closed(self) -> None:
        self.assertEqual(required_migrations(1), ())
        with self.assertRaisesRegex(ValueError, "downgrade"):
            required_migrations(2, 1)
        with self.assertRaisesRegex(ValueError, "not supported"):
            required_migrations(1, 2)

    def test_launcher_has_no_checkout_discovery(self) -> None:
        body = (ROOT / "tailtrail_cli.py").read_text(encoding="utf-8")
        self.assertNotIn("Path.cwd", body)
        self.assertNotIn(".parents", body)
        self.assertIn("TAILTRAIL_SOURCE_COMPAT_ROOT", body)

    def test_wheel_and_sdist_inventory_and_hashes(self) -> None:
        wheel = PROOF.inspect_wheel(self.wheel)
        sdist = PROOF.inspect_sdist(self.sdist)
        self.assertTrue(wheel["valid"], wheel["issues"])
        self.assertTrue(sdist["valid"], sdist["issues"])
        self.assertGreater(wheel["integrity_files"], 400)
        with zipfile.ZipFile(self.wheel) as archive:
            self.assertIn("tailtrail/PACKAGE-CONTRACT.md", archive.namelist())
        with tarfile.open(self.sdist) as archive:
            names = archive.getnames()
        self.assertFalse(any("/tests/" in name for name in names))
        self.assertEqual(self.wheel.read_bytes(), next(self.repro_output.glob("*.whl")).read_bytes())
        self.assertEqual(self.sdist.read_bytes(), next(self.repro_output.glob("*.tar.gz")).read_bytes())

    def test_missing_and_corrupt_resources_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "required.txt").write_text("safe", encoding="utf-8")
            (root / "package-manifest.json").write_text(json.dumps({"runtime_required": ["required.txt"]}), encoding="utf-8")
            (root / "package-integrity.json").write_text(json.dumps({"schema_version": "1", "algorithm": "sha256", "files": {"required.txt": "0" * 64}}), encoding="utf-8")
            self.assertEqual(verify_package(root), ["corrupt package resource: required.txt"])
            (root / "required.txt").unlink()
            issues = verify_package(root)
            self.assertIn("missing package resource: required.txt", issues)
            (root / "package-integrity.json").write_text(json.dumps({"schema_version": "1", "algorithm": "sha256", "files": {"../outside": "0" * 64}}), encoding="utf-8")
            self.assertIn("corrupt package resource: package-integrity.json", verify_package(root))

    def _installed_venv(self, artifact: Path) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        run([sys.executable, "-m", "venv", str(root / "venv")])
        python = root / "venv" / "bin" / "python"
        run([str(python), "-m", "pip", "install", "--no-index", "--no-deps", str(artifact)])
        return temp, root

    def test_wheel_runs_core_lifecycle_without_checkout(self) -> None:
        temp, sandbox = self._installed_venv(self.wheel)
        try:
            executable = sandbox / "venv" / "bin" / "tailtrail"
            project = sandbox / "project"
            project.mkdir()
            run(["git", "init", "-q"], cwd=project)
            run(["git", "config", "user.email", "tailtrail@example.invalid"], cwd=project)
            run(["git", "config", "user.name", "TailTrail"], cwd=project)
            (project / "README.md").write_text("before\n", encoding="utf-8")
            run(["git", "add", "README.md"], cwd=project)
            run(["git", "commit", "-qm", "baseline"], cwd=project)

            version = json.loads(run([str(executable), "version", "--format", "json"], cwd=sandbox).stdout)
            hello = json.loads(run([str(executable), "hello", "--format", "json"], cwd=sandbox).stdout)
            self.assertTrue(version["python_supported"])
            self.assertTrue(hello["installed"])
            self.assertIn("installed-package doctor passed", run([str(executable), "doctor"], cwd=sandbox).stdout)

            started = json.loads(run([str(executable), "start", "fix README documentation validation and add a regression test", "--root", str(project), "--changed", "README.md", "--format", "json"], cwd=sandbox).stdout)
            run_id = started["planning_lock"]["run_id"]
            self.assertTrue(started["setup_posture"]["installed_package"])
            self.assertFalse(started["setup_posture"]["source_checkout"])
            activated = json.loads(run([str(executable), "planning", "activate", "--root", str(project), "--run-id", run_id, "--approved", "--format", "json"], cwd=sandbox).stdout)
            self.assertEqual(activated["planning_lock"]["status"], "approved")
            anchor = json.loads((project / ".tailtrail" / "runs" / run_id / "anchors" / "approved-v1.json").read_text(encoding="utf-8"))
            requirement_uids = [item["requirement_uid"] for item in anchor["requirements"]]
            requirement_uid = requirement_uids[0]

            run([str(executable), "harness", "mode-b", "capture", "--root", str(project), "--run-id", run_id, "--requirement-uid", requirement_uid, "--approved"], cwd=sandbox)
            (project / "README.md").write_text("after\n", encoding="utf-8")
            receipt = project / "proof.json"
            receipt.write_text('{"outcome":"pass"}\n', encoding="utf-8")
            run([str(executable), "harness", "mode-b", "seal", "--root", str(project), "--run-id", run_id, "--requirement-uid", requirement_uid, "--preservation-receipt", str(receipt), "--approved"], cwd=sandbox)
            recovery = json.loads(run([str(executable), "harness", "mode-b", "plan", "--root", str(project), "--run-id", run_id, "--requirement-uid", requirement_uid], cwd=sandbox).stdout)
            self.assertTrue(recovery["safe_to_apply"])
            run([str(executable), "harness", "mode-b", "apply", "--root", str(project), "--run-id", run_id, "--requirement-uid", requirement_uid, "--approved"], cwd=sandbox)
            self.assertEqual((project / "README.md").read_text(encoding="utf-8"), "before\n")
            (project / "README.md").write_text("after\n", encoding="utf-8")

            source_event = {"kind": "source-edit", "requirement_uids": requirement_uids, "changed_paths": ["README.md"]}
            command_event = {"kind": "command-result", "requirement_uids": requirement_uids, "changed_paths": ["README.md"], "tier": "unit", "command_label": "README proof", "command": "test README.md", "outcome": "pass", "environment": "isolated-wheel", "asserted_behavior": "README wording and its regression contract are validated", "artifact": "proof.json", "evidence_label": "local-command"}
            for event in (source_event, command_event):
                run([str(executable), "execution-evidence", "record", "--root", str(project), "--run-id", run_id, "--event", json.dumps(event), "--approved"], cwd=sandbox)
            finalized = json.loads(run([str(executable), "closure", "finalize", "--root", str(project), "--run-id", run_id], cwd=sandbox).stdout)
            self.assertEqual(finalized["overall_status"], "complete", finalized)

            migration = run([str(sandbox / "venv" / "bin" / "python"), "-c", "from tailtrail.migrations import required_migrations; assert required_migrations(1) == ()"], cwd=sandbox)
            self.assertEqual(migration.returncode, 0)
            error = json.loads(run([str(executable), "closure", "unknown-action", "--format", "json"], cwd=sandbox, expected=2).stdout)
            self.assertEqual(error["type"], "tailtrail-command-result")
            self.assertFalse(error["ok"])
        finally:
            temp.cleanup()

    def test_wheel_runs_repository_enforcement_without_checkout(self) -> None:
        temp, sandbox = self._installed_venv(self.wheel)
        try:
            executable = sandbox / "venv" / "bin" / "tailtrail"
            project = sandbox / "policy-project"
            project.mkdir()
            for name in ("tailtrail-enforcement-policy.json", "tailtrail-enforcement-baseline.json", "tailtrail-enforcement-suppressions.json"):
                (project / name).write_bytes((ROOT / name).read_bytes())
            validated = json.loads(run([str(executable), "enforce", "validate", "--root", str(project)], cwd=sandbox).stdout)
            self.assertEqual("passed", validated["status"])
            diff = project / "safe.patch"
            diff.write_text("diff --git a/src/example.py b/src/example.py\n--- a/src/example.py\n+++ b/src/example.py\n@@ -1 +1 @@\n-value = 0\n+value = 1\n", encoding="utf-8")
            checked = json.loads(run([str(executable), "enforce", "check", "--root", str(project), "--diff", str(diff), "--format", "json"], cwd=sandbox).stdout)
            self.assertEqual("passed", checked["status"])
            self.assertEqual(0, checked["blocking_count"])
        finally:
            temp.cleanup()

    def test_sdist_builds_and_installs_to_isolated_target(self) -> None:
        target = self.output / "sdist-target"
        run([sys.executable, "-m", "pip", "install", "--no-index", "--no-deps", "--no-build-isolation", "--target", str(target), str(self.sdist)])
        env = {**os.environ, "PYTHONPATH": str(target)}
        status = json.loads(run([sys.executable, "-m", "tailtrail.cli", "package-info", "--format", "json"], cwd=self.output, env=env).stdout)
        self.assertTrue(status["valid"], status["issues"])

    def test_wheel_runs_transactional_installer_without_checkout(self) -> None:
        temp, sandbox = self._installed_venv(self.wheel)
        try:
            executable = sandbox / "venv" / "bin" / "tailtrail"
            for host in ("codex", "copilot", "claude"):
                target = sandbox / f"target-{host}"
                target.mkdir()
                installed = json.loads(run([str(executable), "install", "--host", host, "--profile", "core", "--target", str(target), "--format", "json"], cwd=sandbox).stdout)
                self.assertTrue(installed["ok"], installed)
                self.assertEqual(installed["status"], "passed")
                verified = json.loads(run([str(executable), "verify", "--host", host, "--target", str(target), "--format", "json"], cwd=sandbox).stdout)
                self.assertTrue(verified["ok"], verified)
                doctor = json.loads(run([str(executable), "doctor", "--host", host, "--target", str(target), "--format", "json"], cwd=sandbox).stdout)
                self.assertEqual(doctor["diagnostics"]["qualification"], "contract-tested")
                self.assertFalse(doctor["diagnostics"]["supported"])
                prepared = json.loads(run([str(executable), "adapters", "runtime", "prepare", "--host", host, "--root", str(target)], cwd=sandbox).stdout)
                self.assertEqual(len(prepared["scenarios"]), 6)
                preview = json.loads(run([str(executable), "update", "--host", host, "--profile", "extended", "--target", str(target), "--dry-run", "--format", "json"], cwd=sandbox).stdout)
                self.assertEqual(preview["status"], "dry-run")
                removed = json.loads(run([str(executable), "uninstall", "--host", host, "--target", str(target), "--force", "--format", "json"], cwd=sandbox).stdout)
                self.assertTrue(removed["ok"], removed)
                rolled_back = json.loads(run([str(executable), "rollback", "--to", removed["transaction_id"], "--target", str(target), "--format", "json"], cwd=sandbox).stdout)
                self.assertTrue(rolled_back["ok"], rolled_back)
                self.assertTrue(json.loads(run([str(executable), "verify", "--host", host, "--target", str(target), "--format", "json"], cwd=sandbox).stdout)["ok"])
        finally:
            temp.cleanup()


if __name__ == "__main__":
    unittest.main()
