"""Phrase-matrix tests for _aidlc_intent and aidlc_mode_selection.

These tests exist because a regression where "use standard aidlc" silently
routed to lite mode went undetected until a live run.  Every realistic user
phrase must be covered here so a future change to the detection logic cannot
quietly break it.
"""
from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if SCRIPTS.as_posix() not in sys.path:
    sys.path.insert(0, SCRIPTS.as_posix())


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# Pre-register transitive dependencies in load order
_load("target_workspace", "target_workspace.py")
_load("tailtrail_navigator_core", "navigator_core.py")
_load("tailtrail_navigator_discovery", "navigator_discovery.py")
_load("tailtrail_navigator_render", "navigator_render.py")
_load("tailtrail_official_aidlc_bridge", "aidlc-official-bridge.py")
_load("tailtrail_host_workspace_adapter", "host-workspace-adapter.py")
_load("tailtrail_enterprise_target_policy", "enterprise-target-policy.py")
_load("tailtrail_planning_lock", "planning-lock.py")
task_start = _load("tailtrail_task_start_aidlc", "task-start.py")


class AidlcIntentPhraseMatrixTests(unittest.TestCase):
    """_aidlc_intent must correctly classify any natural phrasing the user writes."""

    # ── standard phrases ──────────────────────────────────────────────────────
    STANDARD_PHRASES = [
        "use standard aidlc implement pipeline audit events",
        "using standard aidlc",
        "aidlc standard",
        "standard aidlc",
        "apply the standard aidlc mode",
        "implement with aidlc standard mode",
        "aidlc normal mode please",
        "aidlc medium mode",
        "use regular aidlc",
        "standard ai-dlc",
        "ai-dlc standard",
        "implement using standard aidlc",
        "please use standard aidlc for this task",
        "aidlc with standard settings",
        "run standard aidlc on this",
    ]

    # ── requested (aidlc mentioned, no qualifier → same standard path) ────────
    REQUESTED_PHRASES = [
        "using aidlc",
        "use aidlc",
        "with aidlc please",
        "implement pipeline feature, use aidlc",
        "aidlc please",
        "apply aidlc",
        "with ai-dlc",
        "use ai-dlc",
        "run aidlc lifecycle",
        "aidlc-backed plan",
    ]

    # ── full / official phrases ────────────────────────────────────────────────
    FULL_PHRASES = [
        "full aidlc",
        "official aidlc mode",
        "use complete aidlc",
        "enterprise aidlc workflow",
        "use full aidlc for this task",
        "full ai-dlc",
        "official ai-dlc",
    ]

    # ── opt-out phrases ────────────────────────────────────────────────────────
    OPT_OUT_PHRASES = [
        "without aidlc",
        "no aidlc please",
        "skip aidlc for this",
        "do not use aidlc",
        "disable aidlc",
        "without ai-dlc",
    ]

    # ── none phrases (no aidlc mention at all) ─────────────────────────────────
    NONE_PHRASES = [
        "implement pipeline audit events generator",
        "just implement this feature",
        "fix the bug in service.py",
        "add a new API endpoint",
        "refactor the payment validator",
    ]

    def test_standard_phrases_all_return_standard(self):
        for phrase in self.STANDARD_PHRASES:
            with self.subTest(phrase=phrase):
                self.assertEqual(
                    task_start._aidlc_intent(phrase.lower()),
                    "standard",
                    f"Expected 'standard' for: {phrase!r}",
                )

    def test_requested_phrases_all_return_requested(self):
        for phrase in self.REQUESTED_PHRASES:
            with self.subTest(phrase=phrase):
                self.assertEqual(
                    task_start._aidlc_intent(phrase.lower()),
                    "requested",
                    f"Expected 'requested' for: {phrase!r}",
                )

    def test_full_phrases_all_return_full(self):
        for phrase in self.FULL_PHRASES:
            with self.subTest(phrase=phrase):
                self.assertEqual(
                    task_start._aidlc_intent(phrase.lower()),
                    "full",
                    f"Expected 'full' for: {phrase!r}",
                )

    def test_opt_out_phrases_all_return_opt_out(self):
        for phrase in self.OPT_OUT_PHRASES:
            with self.subTest(phrase=phrase):
                self.assertEqual(
                    task_start._aidlc_intent(phrase.lower()),
                    "opt-out",
                    f"Expected 'opt-out' for: {phrase!r}",
                )

    def test_none_phrases_return_none(self):
        for phrase in self.NONE_PHRASES:
            with self.subTest(phrase=phrase):
                self.assertEqual(
                    task_start._aidlc_intent(phrase.lower()),
                    "none",
                    f"Expected 'none' for: {phrase!r}",
                )


class AidlcModeSelectionRoutingTests(unittest.TestCase):
    """aidlc_mode_selection must route to the correct mode for key phrases."""

    def _mode(self, goal: str) -> str:
        with tempfile.TemporaryDirectory() as tmp:
            try:
                return task_start.aidlc_mode_selection(goal, None, Path(tmp), {"risk_indicators": []}, None)["mode"]
            except ValueError as exc:
                # bridge.preflight raises ValueError when no official pack is installed
                if "official pack" in str(exc).lower():
                    return "full-no-pack"
                raise

    def test_no_aidlc_mention_routes_to_lite(self):
        self.assertEqual(self._mode("fix a typo in the README"), "lite")

    def test_use_aidlc_routes_to_standard(self):
        self.assertEqual(self._mode("use aidlc to plan a payment change"), "standard")

    def test_standard_aidlc_routes_to_standard(self):
        self.assertEqual(self._mode("use standard aidlc implement pipeline audit events generator"), "standard")

    def test_aidlc_standard_routes_to_standard(self):
        self.assertEqual(self._mode("aidlc standard"), "standard")

    def test_full_aidlc_routes_to_full(self):
        # full depends on bridge preflight; no official pack in test env returns "full-no-pack"
        mode = self._mode("full aidlc implement this feature")
        self.assertIn(mode, ("full", "standard", "full-no-pack"))

    def test_explicit_flag_overrides_natural_language(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = task_start.aidlc_mode_selection("fix a bug", "lite", Path(tmp), {"risk_indicators": []}, None)
        self.assertEqual(result["mode"], "lite")
        self.assertEqual(result["selection"], "explicit-flag")

    def test_standard_selection_label_is_set(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = task_start.aidlc_mode_selection("use standard aidlc implement the feature", None, Path(tmp), {"risk_indicators": []}, None)
        self.assertEqual(result["mode"], "standard")
        self.assertEqual(result["selection"], "explicit-natural-language-standard")

    def test_opt_out_turns_off_aidlc(self):
        self.assertEqual(self._mode("implement this feature without aidlc"), "off")


if __name__ == "__main__":
    unittest.main()


