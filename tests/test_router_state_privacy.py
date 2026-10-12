import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SECRET = "AKIAIOSFODNN7EXAMPLE"


class RouterStatePrivacyTests(unittest.TestCase):
    def test_auto_state_never_contains_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            state = Path(temp) / "auto-state.json"
            result = subprocess.run(
                [sys.executable, (ROOT / "scripts" / "token-auto.py").as_posix(),
                 f"rotate {SECRET} now", "--state", state.as_posix(), "--format", "json"],
                text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(state.read_text(encoding="utf-8"))
            self.assertNotIn("prompt", payload)
            self.assertNotIn(SECRET, state.read_text(encoding="utf-8"))
            self.assertIn("prompt_words", payload)

    def test_route_state_never_contains_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            state = Path(temp) / "router-state.json"
            result = subprocess.run(
                [sys.executable, (ROOT / "scripts" / "route-context.py").as_posix(),
                 "auto", f"fix {SECRET} bug", "--state", state.as_posix(), "--format", "json"],
                text=True, capture_output=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(state.read_text(encoding="utf-8"))
            self.assertNotIn("prompt", payload)
            self.assertNotIn(SECRET, state.read_text(encoding="utf-8"))
            self.assertIn("last_route", payload)


if __name__ == "__main__":
    unittest.main()
