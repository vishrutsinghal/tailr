from __future__ import annotations

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

# Just-in-time instruction: every fail-closed refusal a host can hit must
# contain the exact corrective `tailtrail ...` command plus the one-line rule.
# The host that just failed is maximally attentive — teach at that moment,
# not in a preamble it skimmed. Original message text is preserved verbatim
# as a prefix so existing substring assertions keep passing; the corrective
# command is appended.
BOUNDARY_MODULES = (
    "scripts/planning_lock.py",
    "scripts/execution-evidence.py",
    "scripts/closure-close.py",
    "scripts/closure-finalizer.py",
)

# task-start.py Start/authority refusals follow the same pattern opportunistically
# but the 6000-line dispatcher is excluded from the strict scan: most of its
# raises are internal argument-shape validations, not host-action refusals.


def refusal_messages(path: Path) -> list[tuple[int, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Raise):
            continue
        exc = node.exc
        if not isinstance(exc, ast.Call) or not exc.args:
            continue
        first = exc.args[0]
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            found.append((node.lineno, first.value))
        elif isinstance(first, ast.JoinedStr):
            literal = "".join(
                part.value for part in first.values if isinstance(part, ast.Constant)
            )
            found.append((node.lineno, literal))
        # Non-literal raises re-raise dynamic external errors (`from error`
        # with computed text); no static corrective command can be attached.
    return found


class JustInTimeErrorTests(unittest.TestCase):
    def test_every_boundary_refusal_names_its_corrective_command(self) -> None:
        violations: list[str] = []
        for relative in BOUNDARY_MODULES:
            for lineno, message in refusal_messages(ROOT / relative):
                if "`tailtrail " not in message:
                    violations.append(f"{relative}:{lineno}: {message[:100]}")
        self.assertEqual(
            violations,
            [],
            "fail-closed refusals without an exact corrective `tailtrail ...` command:\n"
            + "\n".join(violations),
        )

    def test_corrective_commands_are_not_bare_flags(self) -> None:
        # A bare "--run-id" tells the host nothing; the command must be runnable.
        import re

        for relative in BOUNDARY_MODULES:
            for lineno, message in refusal_messages(ROOT / relative):
                for command in re.findall(r"`(tailtrail [^`]+)`", message):
                    with self.subTest(path=f"{relative}:{lineno}"):
                        self.assertGreater(
                            len(command.split()),
                            1,
                            f"corrective command is not runnable: `{command}`",
                        )
