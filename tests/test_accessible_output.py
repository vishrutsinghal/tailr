from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from workflow_runtime import denials

ANSI_ESCAPE = re.compile(r"\x1b\[|\\x1b\[|\\033\[")


def install_cli(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", "from tailtrail.install.cli import main; import sys; sys.exit(main(sys.argv[1:]))", *args],
        cwd=cwd, text=True, capture_output=True, check=False,
    )


class AccessibleOutputTests(unittest.TestCase):
    """Phase E7 (ENT-E7-002): machine-readable output must not be the only
    explanation of a block. These are structural, automatable proxies for the
    accessibility requirement in ENTERPRISE-READINESS-ASSESSMENT.md section
    14.4; they do not replace an actual screen-reader or keyboard-navigation
    review.
    """

    def _symlink_trap(self, target: Path) -> None:
        outside = target.parent / "outside"
        outside.mkdir(exist_ok=True)
        (target / ".codex-plugin").symlink_to(outside, target_is_directory=True)

    def test_json_error_envelope_includes_a_human_readable_message_alongside_the_machine_code(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)
            self._symlink_trap(target)
            result = install_cli("install", "--host", "codex", "--profile", "core", "--target", target.as_posix(), "--format", "json", cwd=ROOT)
            self.assertEqual(result.returncode, 3, result.stderr)
            payload = json.loads(result.stdout)
            self.assertFalse(payload["ok"])
            self.assertTrue(payload["error"])  # machine-readable category
            self.assertTrue(payload["message"])  # human-readable explanation
            self.assertNotEqual(payload["error"], payload["message"])
            self.assertIn("symlink", payload["message"].lower())

    def test_text_error_output_repeats_the_same_explanation_without_relying_on_color(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)
            self._symlink_trap(target)
            result = install_cli("install", "--host", "codex", "--profile", "core", "--target", target.as_posix(), cwd=ROOT)
            self.assertEqual(result.returncode, 3, result.stderr)
            self.assertIn("TailTrail installer failed", result.stdout)
            self.assertIn("symlink", result.stdout.lower())
            self.assertNotIn("\x1b[", result.stdout)

    def test_no_ansi_color_escape_codes_in_shipped_runtime_source(self) -> None:
        offenders: list[str] = []
        for directory in ("tailtrail", "scripts"):
            for path in sorted((ROOT / directory).rglob("*.py")):
                if "__pycache__" in path.parts:
                    continue
                if ANSI_ESCAPE.search(path.read_text(encoding="utf-8", errors="ignore")):
                    offenders.append(path.relative_to(ROOT).as_posix())
        self.assertEqual(offenders, [], "CLI output must not depend on ANSI color escapes for meaning")

    def test_denial_reason_codes_are_human_readable_slugs_not_opaque_numbers(self) -> None:
        slug = re.compile(r"^[a-z][a-z-]*[a-z]$")
        for category, reason_code in denials.REASONS.items():
            with self.subTest(category=category):
                self.assertRegex(reason_code, slug, f"reason_code for `{category}` must be a readable hyphenated phrase, not an opaque code")


if __name__ == "__main__":
    unittest.main()
