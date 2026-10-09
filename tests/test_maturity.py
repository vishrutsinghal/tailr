"""Tests for scripts/maturity.py -- the CLI/MCP maturity classification
lookup backing the gating added in the "maturity-gating" registry feature.
"""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


maturity = load("maturity_module", "scripts/maturity.py")


class MaturityLookupTests(unittest.TestCase):
    def test_unregistered_command_defaults_to_stable(self) -> None:
        level, reason = maturity.cli_command_maturity("review")
        self.assertEqual(level, "stable")
        self.assertIsNone(reason)

    def test_registered_bare_command_returns_its_level(self) -> None:
        level, reason = maturity.cli_command_maturity("spec-kit")
        self.assertEqual(level, "incubating")
        self.assertTrue(reason)

    def test_specific_command_action_key_checked_before_bare_command(self) -> None:
        # "aidlc official" is registered; the bare "aidlc" command is not, so
        # it must fall back to stable rather than inheriting "official"'s level.
        level, _ = maturity.cli_command_maturity("aidlc", "official")
        self.assertEqual(level, "experimental")
        bare_level, _ = maturity.cli_command_maturity("aidlc")
        self.assertEqual(bare_level, "stable")

    def test_registered_mcp_tool_returns_its_level(self) -> None:
        level, reason = maturity.mcp_tool_maturity("spec_kit_detect")
        self.assertEqual(level, "incubating")
        self.assertTrue(reason)

    def test_unregistered_mcp_tool_defaults_to_stable(self) -> None:
        level, reason = maturity.mcp_tool_maturity("some_future_tool")
        self.assertEqual(level, "stable")
        self.assertIsNone(reason)

    def test_is_gated_matches_the_two_non_stable_levels(self) -> None:
        self.assertFalse(maturity.is_gated("stable"))
        self.assertTrue(maturity.is_gated("incubating"))
        self.assertTrue(maturity.is_gated("experimental"))

    def test_allow_flag_for_matches_level(self) -> None:
        self.assertEqual(maturity.allow_flag_for("incubating"), "--allow-incubating")
        self.assertEqual(maturity.allow_flag_for("experimental"), "--allow-experimental")

    def test_strip_allow_flags_removes_only_the_two_known_flags(self) -> None:
        args = ["spec-kit", "import", "--allow-incubating", "--file", "spec.json", "--allow-experimental"]
        self.assertEqual(maturity.strip_allow_flags(args), ["spec-kit", "import", "--file", "spec.json"])


if __name__ == "__main__":
    unittest.main()
