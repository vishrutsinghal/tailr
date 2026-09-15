import unittest
from pathlib import Path
import shutil
import json

from scripts.drift_analysis import analyze


def _write_anchor(root: Path, run_id: str, requirements: list[dict]) -> None:
    anchor_dir = root / ".tailtrail" / "runs" / run_id / "anchors"
    anchor_dir.mkdir(parents=True, exist_ok=True)
    anchor = {
        "schema_version": "1",
        "type": "tailtrail-change-intent-anchor",
        "run_id": run_id,
        "status": "approved",
        "approved_fingerprint": "sha256:test-anchor",
        "requirements": requirements,
    }
    (anchor_dir / "approved-v1.json").write_text(
        json.dumps(anchor, indent=2), encoding="utf-8"
    )


def _requirement(
    uid: str,
    display_id: str,
    likely_paths: list[str],
    kind: str = "change",
) -> dict:
    row = {
        "requirement_uid": uid,
        "display_id": display_id,
        "statement": display_id,
        "kind": kind,
        "status": "approved",
        "likely_paths": likely_paths,
        "acceptance_criteria": [f"{display_id} is observably satisfied."],
        "validation_contract": {"state": "required", "tiers": ["unit"]},
    }
    if kind == "preserve":
        row["preserve_rules"] = [f"Preserve {display_id} behavior."]
    return row


def _passing_evidence(uids: list[str], tier: str = "unit") -> dict:
    """Authoritative, passing, tier-complete evidence linked to requirements."""
    return {
        "requirement_uids": uids,
        "evidence_quality": "trusted",
        "outcome": "pass",
        "tiers": [tier],
    }


class TestDriftAnalysis(unittest.TestCase):
    def setUp(self):
        self.root = Path("temp_drift_test_root").absolute()
        self.root.mkdir(parents=True, exist_ok=True)
        self.run_id = "drift-test-run"

    def tearDown(self):
        if self.root.exists():
            shutil.rmtree(self.root)

    def test_no_drift_when_changes_match_approved_paths(self):
        """Case A: changes inside approved scope and all requirements implemented."""
        _write_anchor(
            self.root,
            self.run_id,
            [
                _requirement("req-1", "REQ-01", ["src/auth.py"]),
                _requirement("req-2", "REQ-02", ["src/rate_limit.py"]),
            ],
        )
        evidence = {
            "change_manifest": ["src/auth.py:L20-L45", "src/rate_limit.py"],
            "evidence": [
                _passing_evidence(["req-1"]),
                _passing_evidence(["req-2"]),
            ],
        }
        result = analyze(self.root, self.run_id, evidence)
        self.assertFalse(result["drift_detected"], result["findings"])
        self.assertEqual(result["scope_assessment"]["status"], "within-approved-scope")
        self.assertEqual(result["evidence"]["source"], "handoff-manifest")

    def test_scope_drift_when_path_outside_approved(self):
        """Case B: a changed path outside the approved editable union is new-drift."""
        _write_anchor(
            self.root,
            self.run_id,
            [
                _requirement("req-1", "REQ-01", ["src/auth.py"]),
                _requirement("req-2", "REQ-02", ["src/rate_limit.py"]),
            ],
        )
        evidence = {"change_manifest": ["src/auth.py", "infra/terraform/main.tf"]}
        result = analyze(self.root, self.run_id, evidence)
        self.assertTrue(result["drift_detected"])
        classifications = {finding["classification"] for finding in result["findings"]}
        self.assertIn("new-drift", classifications)
        self.assertEqual(
            result["scope_assessment"]["unexpected_paths"],
            ["infra/terraform/main.tf"],
        )

    def test_requirement_unimplemented_when_untouched(self):
        """Case C: a change requirement with zero changes is requirement-unimplemented."""
        _write_anchor(
            self.root,
            self.run_id,
            [
                _requirement("req-1", "REQ-01", ["src/auth.py"]),
                _requirement("req-2", "REQ-02", ["src/rate_limit.py"]),
            ],
        )
        # Only tests changed: the classic "coding for the test" shape.
        evidence = {"change_manifest": ["src/auth.py", "tests/test_auth.py"]}
        result = analyze(self.root, self.run_id, evidence)
        self.assertTrue(result["drift_detected"])
        unimplemented = [
            finding
            for finding in result["findings"]
            if finding["classification"] == "requirement-unimplemented"
        ]
        self.assertEqual(len(unimplemented), 1)
        self.assertEqual(unimplemented[0]["display_id"], "REQ-02")

    def test_preserve_requirement_exempt_from_unimplemented(self):
        """A preserve requirement with no changes must not be flagged as drift."""
        _write_anchor(
            self.root,
            self.run_id,
            [
                _requirement("req-1", "REQ-01", ["src/auth.py"], kind="change"),
                _requirement("req-2", "REQ-02", ["src/other.py"], kind="preserve"),
            ],
        )
        evidence = {
            "change_manifest": ["src/auth.py"],
            "evidence": [_passing_evidence(["req-1"])],
        }
        result = analyze(self.root, self.run_id, evidence)
        self.assertFalse(result["drift_detected"], result["findings"])
        preserve_row = next(
            row
            for row in result["requirements"]
            if row["display_id"] == "REQ-02"
        )
        self.assertEqual(preserve_row["mapping"], "preserved")

    def test_missing_anchor_fails_closed(self):
        """Case D: no approved baseline means drift, never an automatic pass."""
        result = analyze(
            self.root, "no-such-run", {"change_manifest": ["src/auth.py"]}
        )
        self.assertTrue(result["drift_detected"])
        self.assertEqual(result["findings"][0]["classification"], "anchor-missing")

    def test_no_change_evidence_fails_closed(self):
        """No changed paths anywhere means drift, never an automatic pass."""
        _write_anchor(
            self.root,
            self.run_id,
            [_requirement("req-1", "REQ-01", ["src/auth.py"])],
        )
        result = analyze(self.root, self.run_id, None)
        self.assertTrue(result["drift_detected"])
        self.assertEqual(
            result["findings"][0]["classification"], "no-change-evidence"
        )


    def test_fulfillment_unverified_without_linked_evidence(self):
        """Passing tests are not proof: a change requirement with no linked
        authoritative evidence is implemented-unverified (design §10.2)."""
        _write_anchor(
            self.root,
            self.run_id,
            [_requirement("req-1", "REQ-01", ["src/auth.py"])],
        )
        evidence = {"change_manifest": ["src/auth.py"], "evidence": []}
        result = analyze(self.root, self.run_id, evidence)
        self.assertTrue(result["drift_detected"])
        fulfillment = [
            finding
            for finding in result["findings"]
            if finding["classification"] == "fulfillment-unverified"
        ]
        self.assertEqual(len(fulfillment), 1)
        self.assertEqual(fulfillment[0]["display_id"], "REQ-01")

    def test_fulfillment_unverified_when_evidence_fails(self):
        """A failing (non-passing) evidence item blocks validation."""
        _write_anchor(
            self.root,
            self.run_id,
            [_requirement("req-1", "REQ-01", ["src/auth.py"])],
        )
        evidence = {
            "change_manifest": ["src/auth.py"],
            "evidence": [
                {
                    "requirement_uids": ["req-1"],
                    "evidence_quality": "trusted",
                    "outcome": "fail",
                    "tiers": ["unit"],
                }
            ],
        }
        result = analyze(self.root, self.run_id, evidence)
        self.assertTrue(result["drift_detected"])
        classifications = {finding["classification"] for finding in result["findings"]}
        self.assertIn("fulfillment-unverified", classifications)

    def test_anchor_not_concrete_fails_closed(self):
        """A vague anchor cannot be drift-checked; it fails closed (§10.3)."""
        anchor_dir = self.root / ".tailtrail" / "runs" / self.run_id / "anchors"
        anchor_dir.mkdir(parents=True, exist_ok=True)
        vague = {
            "requirement_uid": "req-1",
            "display_id": "REQ-01",
            "statement": "Make it work",
            "kind": "change",
            "status": "approved",
            "likely_paths": [],
            "acceptance_criteria": [],
        }
        (anchor_dir / "approved-v1.json").write_text(
            json.dumps(
                {
                    "schema_version": "1",
                    "type": "tailtrail-change-intent-anchor",
                    "run_id": self.run_id,
                    "status": "approved",
                    "requirements": [vague],
                }
            ),
            encoding="utf-8",
        )
        evidence = {"change_manifest": ["src/auth.py"]}
        result = analyze(self.root, self.run_id, evidence)
        self.assertTrue(result["drift_detected"])
        self.assertEqual(
            result["findings"][0]["classification"], "anchor-not-concrete"
        )
        self.assertIn("acceptance_criteria", result["findings"][0]["message"])


if __name__ == "__main__":
    unittest.main()
