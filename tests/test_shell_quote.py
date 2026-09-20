from __future__ import annotations

import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]


def load_quote():
    spec = importlib.util.spec_from_file_location(
        "tailtrail_shell_quote_test", ROOT / "scripts" / "shell_quote.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class ShellQuoteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_quote()

    def test_posix_uses_shlex_single_quotes(self) -> None:
        with mock.patch.object(self.module.os, "name", "posix"):
            self.assertEqual(
                self.module.quote('print("proof ok")'), '\'print("proof ok")\''
            )
            self.assertEqual(self.module.quote("simple"), "simple")

    def test_windows_uses_cmd_compatible_quoting(self) -> None:
        with mock.patch.object(self.module.os, "name", "nt"):
            self.assertEqual(
                self.module.quote('print("proof ok")'),
                subprocess.list2cmdline(['print("proof ok")']),
            )
            self.assertNotIn("'", self.module.quote("needs quoting here"))

    def test_windows_quoted_command_runs_under_cmd(self) -> None:
        if self.module.os.name != "nt":
            self.skipTest("cmd.exe execution check runs on Windows only")
        command = f"{self.module.quote(sys.executable)} -c {self.module.quote('print(\"proof ok\")')}"
        completed = subprocess.run(
            command, shell=True, text=True, capture_output=True
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout, "proof ok\n")

    def test_tests_reexport_matches_canonical_module(self) -> None:
        from tests.proc_quote import quote as test_quote

        for sample in ("simple", "needs quoting here", 'print("x")'):
            with self.subTest(sample=sample):
                self.assertEqual(test_quote(sample), self.module.quote(sample))


if __name__ == "__main__":
    unittest.main()
