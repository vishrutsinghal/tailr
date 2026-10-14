"""Builds a synthetic near-empty repository fixture for the greenfield
end-to-end regression proof (see TAILTRAIL-NEW-FILE-DUE-DILIGENCE-PROTOCOL.md,
Phase N5/N6). The fixture mirrors the manual /tmp/tailtrail-greenfield-demo
proof performed live during this project's dogfooding session.
"""

from __future__ import annotations

from pathlib import Path

GREETING_MODULE = '''def greet(name: str) -> str:
    return f"Hello, {name}!"
'''

GREETING_TEST_MODULE = '''import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from greeting import greet


class GreetTests(unittest.TestCase):
    def test_greet_returns_a_friendly_message(self) -> None:
        self.assertEqual(greet("World"), "Hello, World!")


if __name__ == "__main__":
    unittest.main()
'''


def build_fixture(root: Path) -> None:
    """Create a near-empty repository containing only a README, so the first
    requirement in it has zero pre-existing graph evidence to search."""
    root.mkdir(parents=True, exist_ok=True)
    (root / "README.md").write_text(
        "# Greenfield Demo\n\nA synthetic near-empty repository fixture.\n",
        encoding="utf-8",
    )


def write_greeting_module(root: Path) -> Path:
    """Write the fixture's new implementation file and return its path."""
    path = root / "greeting.py"
    path.write_text(GREETING_MODULE, encoding="utf-8")
    return path


def write_greeting_test_module(root: Path) -> Path:
    """Write the fixture's new test file and return its path."""
    path = root / "tests" / "test_greeting.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(GREETING_TEST_MODULE, encoding="utf-8")
    return path
