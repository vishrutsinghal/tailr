from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

# Exact review dimensions named in ENT-E12-002's validation criterion.
REQUIRED_REVIEW_DIMENSIONS = (
    "compatibility",
    "dependency",
    "restore",
    "migration",
    "security",
    "host-runtime",
    "efficacy",
    "deprecation",
    "support",
)


class ContinuousReleaseGovernanceTests(unittest.TestCase):
    """Tests for ENT-E12-002's recurring review schedule definition."""

    def test_versioning_defines_a_continuous_governance_schedule(self) -> None:
        body = (ROOT / "VERSIONING.md").read_text(encoding="utf-8")

        self.assertIn("## Continuous Release Governance", body)
        section = body.split("## Continuous Release Governance", 1)[1]
        lowered = section.lower()
        for dimension in REQUIRED_REVIEW_DIMENSIONS:
            self.assertIn(dimension, lowered, f"missing '{dimension}' review row in the continuous governance schedule")

    def test_continuous_governance_schedule_does_not_claim_a_cycle_has_run(self) -> None:
        body = (ROOT / "VERSIONING.md").read_text(encoding="utf-8")
        section = body.split("## Continuous Release Governance", 1)[1]

        self.assertIn("does not claim any cycle has run yet", section)

    def test_continuous_governance_table_has_a_cadence_row_per_dimension(self) -> None:
        body = (ROOT / "VERSIONING.md").read_text(encoding="utf-8")
        section = body.split("## Continuous Release Governance", 1)[1]
        rows = [line for line in section.splitlines() if line.startswith("| ") and "---" not in line and "Review" not in line]

        # one row combines the "restore" and "migration" dimensions, so 8 rows
        # cover the 9 required review dimensions.
        self.assertGreaterEqual(len(rows), len(REQUIRED_REVIEW_DIMENSIONS) - 1)
        for row in rows:
            columns = [cell.strip() for cell in row.strip("|").split("|")]
            self.assertEqual(len(columns), 3, f"malformed governance table row: {row!r}")
            self.assertTrue(all(columns), f"empty cell in governance table row: {row!r}")


if __name__ == "__main__":
    unittest.main()
