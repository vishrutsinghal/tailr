from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("tailtrail_expand_intent_test", ROOT / "scripts" / "expand-intent.py")
assert SPEC and SPEC.loader
expand = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = expand
SPEC.loader.exec_module(expand)


class ExpandIntentTests(unittest.TestCase):
    def test_full_aidlc_phrase_does_not_fall_back_to_standard(self) -> None:
        self.assertEqual(expand.resolve_intent("use full AIDLC mode"), "aidlc_full")
        flow = expand.FLOWS["aidlc_full"]
        self.assertIn("--aidlc full", flow.prompt)
        self.assertIn("Do not silently downgrade", flow.prompt)


if __name__ == "__main__":
    unittest.main()
