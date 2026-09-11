from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]


def load_runner():
    spec = importlib.util.spec_from_file_location("tailtrail_parallel_test_runner_test", ROOT / "scripts" / "run-tests.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


RUNNER = load_runner()


class ParallelTestRunnerTests(unittest.TestCase):
    def project(self, root: Path, *, failing: bool = False) -> None:
        tests = root / "tests"
        tests.mkdir()
        (tests / "__init__.py").write_text("", encoding="utf-8")
        (tests / "test_alpha.py").write_text(
            "import unittest\n\n"
            "class AlphaTests(unittest.TestCase):\n"
            "    def test_alpha(self):\n"
            "        self.assertTrue(True)\n",
            encoding="utf-8",
        )
        assertion = "self.assertEqual(1, 2)" if failing else "self.assertEqual(2, 2)"
        (tests / "test_beta.py").write_text(
            "import unittest\n\n"
            "class BetaTests(unittest.TestCase):\n"
            "    def test_beta(self):\n"
            f"        {assertion}\n",
            encoding="utf-8",
        )

    def command(self, root: Path, *extra: str, tailtrail: bool = False) -> subprocess.CompletedProcess[str]:
        if tailtrail:
            command = [
                sys.executable,
                (ROOT / "scripts" / "tailtrail.py").as_posix(),
                "test",
                "run",
                "--root",
                root.as_posix(),
            ]
        else:
            command = [
                sys.executable,
                (ROOT / "scripts" / "run-tests.py").as_posix(),
                "--root",
                root.as_posix(),
            ]
        return subprocess.run(
            [*command, *extra],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_discovery_selection_and_repository_preflight_are_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.project(root)
            modules = RUNNER.discover_modules(root, "tests", "test_*.py")

        self.assertEqual(modules, ["tests.test_alpha", "tests.test_beta"])
        self.assertEqual(RUNNER.select_modules(modules, ["test_beta"], []), ["tests.test_beta"])
        self.assertEqual(RUNNER.select_modules(modules, [], ["tests.test_alpha"]), ["tests.test_beta"])
        preflight, parallel = RUNNER.split_phases(
            ["tests.test_navigator_scope", "tests.test_enterprise_readiness", "tests.test_product_maturity"]
        )
        self.assertEqual(preflight, ["tests.test_enterprise_readiness", "tests.test_product_maturity"])
        self.assertEqual(parallel, ["tests.test_navigator_scope"])

    def test_default_jobs_is_bounded_and_honors_the_environment(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True), mock.patch.object(RUNNER.os, "cpu_count", return_value=32):
            self.assertEqual(RUNNER.default_jobs(), 4)
        with mock.patch.dict(os.environ, {"TAILTRAIL_TEST_JOBS": "2"}, clear=True):
            self.assertEqual(RUNNER.default_jobs(), 2)
        with mock.patch.dict(os.environ, {"TAILTRAIL_TEST_JOBS": "invalid"}, clear=True):
            with self.assertRaisesRegex(ValueError, "positive integer"):
                RUNNER.default_jobs()
        with mock.patch.dict(os.environ, {"TAILTRAIL_TEST_JOBS": "0"}, clear=True):
            with self.assertRaisesRegex(ValueError, "positive integer"):
                RUNNER.default_jobs()

    def test_parallel_json_run_reports_exact_modules_and_tests(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.project(root)
            result = self.command(root, "--jobs", "2", "--format", "json")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "passed")
        self.assertEqual(payload["jobs"], 2)
        self.assertEqual(payload["module_count"], 2)
        self.assertEqual(payload["tests"], 2)
        self.assertEqual(payload["failures"], [])
        self.assertEqual(
            [item["label"] for item in payload["results"]],
            ["tests.test_alpha", "tests.test_beta"],
        )

    def test_failure_is_nonzero_and_preserves_unittest_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.project(root, failing=True)
            result = self.command(root, "--jobs", "2", "--format", "json")

        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["status"], "failed")
        self.assertEqual(len(payload["failures"]), 1)
        self.assertEqual(payload["failures"][0]["label"], "tests.test_beta")
        self.assertIn("AssertionError", payload["failures"][0]["stderr"])

    def test_serial_fallback_and_tailtrail_cli_dispatch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.project(root)
            serial = self.command(root, "--serial", "--format", "json")
            dispatched = self.command(
                root,
                "--jobs",
                "2",
                "--include",
                "test_alpha",
                "--format",
                "json",
                tailtrail=True,
            )

        self.assertEqual(serial.returncode, 0, serial.stdout + serial.stderr)
        self.assertTrue(json.loads(serial.stdout)["serial"])
        self.assertEqual(dispatched.returncode, 0, dispatched.stdout + dispatched.stderr)
        payload = json.loads(dispatched.stdout)
        self.assertEqual(payload["module_count"], 1)
        self.assertEqual(payload["tests"], 1)

    def test_invalid_root_and_unknown_include_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.project(root)
            missing = self.command(root, "--include", "test_missing", "--format", "json")
            outside = self.command(root, "--start-directory", "../outside", "--format", "json")

        self.assertEqual(missing.returncode, 2)
        self.assertIn("unknown included test", json.loads(missing.stdout)["error"])
        self.assertEqual(outside.returncode, 2)
        self.assertIn("inside the test root", json.loads(outside.stdout)["error"])


if __name__ == "__main__":
    unittest.main()
