from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "repository-enforcement.py"


def load_module():
    spec = importlib.util.spec_from_file_location("tailtrail_repository_enforcement_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


ENFORCEMENT = load_module()


def unified(path: str, added: list[str] | None = None, removed: list[str] | None = None) -> str:
    added = added or []
    removed = removed or []
    old_count = max(1, len(removed))
    new_count = max(1, len(added))
    body = [*(f"-{line}" for line in removed), *(f"+{line}" for line in added)]
    return "\n".join((f"diff --git a/{path} b/{path}", f"--- a/{path}", f"+++ b/{path}", f"@@ -1,{old_count} +1,{new_count} @@", *body, ""))


class RepositoryEnforcementTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.policy = json.loads((ROOT / "tailtrail-enforcement-policy.json").read_text(encoding="utf-8"))
        for name in ("tailtrail-enforcement-policy.json", "tailtrail-enforcement-baseline.json", "tailtrail-enforcement-suppressions.json"):
            (self.root / name).write_bytes((ROOT / name).read_bytes())

    def tearDown(self):
        self.temp.cleanup()

    def evaluate(self, diff: str):
        return ENFORCEMENT.evaluate(self.root, copy.deepcopy(self.policy), diff, "file", "")

    def rules(self, report):
        return {item["rule_id"] for item in report["findings"]}

    def approval(self, paths: list[str]):
        directory = self.root / "tailtrail-meta" / "approvals"
        directory.mkdir(parents=True, exist_ok=True)
        value = {
            "schema_version": "1", "type": "tailtrail-repository-approval", "policy_version": 1,
            "approval_id": "test-approval", "approved": True, "owner": "test-owner",
            "reason": "Exercise the closed approval contract.", "paths": paths,
            "expires": (date.today() + timedelta(days=7)).isoformat(),
        }
        (directory / "test.json").write_text(json.dumps(value), encoding="utf-8")

    def test_policy_is_closed_and_core_rules_are_locked(self):
        self.assertEqual([], ENFORCEMENT.validate_policy(self.policy))
        invalid = copy.deepcopy(self.policy)
        invalid["unknown"] = True
        invalid["rules"]["redaction"]["enabled"] = False
        invalid["limits"]["maximum_findings"] = 0
        issues = ENFORCEMENT.validate_policy(invalid)
        self.assertTrue(any("policy fields" in item for item in issues))
        self.assertTrue(any("redaction" in item for item in issues))
        self.assertTrue(any("supported integer range" in item for item in issues))

    def test_override_can_tighten_but_not_weaken_policy(self):
        valid = {"schema_version": "1", "type": "tailtrail-repository-enforcement-override", "policy_version": 1, "rules": {"approval-scope": {"protected_paths": ["infra/"]}}, "limits": {"maximum_findings": 100}}
        merged, issues = ENFORCEMENT.merge_override(self.policy, valid)
        self.assertEqual([], issues)
        self.assertIn("infra/", merged["rules"]["approval-scope"]["protected_paths"])
        self.assertEqual(100, merged["limits"]["maximum_findings"])
        invalid = copy.deepcopy(valid)
        invalid["rules"]["approval-scope"] = {"enabled": False, "severity": "low"}
        _merged, issues = ENFORCEMENT.merge_override(self.policy, invalid)
        self.assertTrue(any("disable locked" in item for item in issues))
        self.assertTrue(any("lower severity" in item for item in issues))

    def test_safe_change_passes(self):
        report = self.evaluate(unified("src/example.py", ["value = 1"]))
        self.assertEqual("passed", report["status"])
        self.assertEqual(0, report["finding_count"])

    def test_every_core_rule_has_a_negative_fixture(self):
        cases = {
            "approval-scope": unified("schemas/new.schema.json", ["{}"]),
            "evidence-truth": unified("README.md", ["All tests passed"]),
            "stale-completion": unified("completion-report.json", ['"status": "complete"']),
            "dependency-decision": unified("requirements.txt", ["requests==2.32.0"]),
            "safeguard-preservation": unified("src/app.py", removed=["validate(request)"]),
            "local-state": unified(".tailtrail/state.json", ["{}"]),
            "redaction": unified("fixture.txt", ["token = 'ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ123456'"]),
            "release-manifest": unified(".github/workflows/new.yml", ["name: New"]),
        }
        for rule_id, diff in cases.items():
            with self.subTest(rule_id=rule_id):
                report = self.evaluate(diff)
                self.assertIn(rule_id, self.rules(report))
                self.assertEqual("failed", report["status"])

    def test_exact_approval_covers_only_its_scope(self):
        self.approval(["schemas/"])
        allowed = self.evaluate(unified("schemas/new.schema.json", ["{}"] ))
        self.assertNotIn("approval-scope", self.rules(allowed))
        denied = self.evaluate(unified(".github/actions/new/action.yml", ["name: New"] ))
        self.assertIn("approval-scope", self.rules(denied))

    def test_expired_approval_is_inactive_without_poisoning_unrelated_changes(self):
        self.approval(["schemas/"])
        path = self.root / "tailtrail-meta" / "approvals" / "test.json"
        value = json.loads(path.read_text(encoding="utf-8"))
        value["expires"] = (date.today() - timedelta(days=1)).isoformat()
        path.write_text(json.dumps(value), encoding="utf-8")
        safe = self.evaluate(unified("src/example.py", ["value = 1"]))
        self.assertEqual("passed", safe["status"])
        protected = self.evaluate(unified("schemas/new.schema.json", ["{}"] ))
        self.assertIn("approval-scope", self.rules(protected))
        self.assertEqual("failed", protected["status"])

    def test_baseline_is_visible_exact_and_changed_finding_blocks(self):
        first = self.evaluate(unified("src/app.py", removed=["validate(request)"]))
        finding = next(item for item in first["findings"] if item["rule_id"] == "safeguard-preservation")
        baseline = {"schema_version": "1", "type": "tailtrail-enforcement-baseline", "policy_version": 1, "generated_at": "2026-08-24T00:00:00Z", "findings": [{"fingerprint": finding["fingerprint"], "rule_id": finding["rule_id"], "path": finding["path"]}]}
        (self.root / "tailtrail-enforcement-baseline.json").write_text(json.dumps(baseline), encoding="utf-8")
        repeated = self.evaluate(unified("src/app.py", removed=["validate(request)"]))
        item = next(item for item in repeated["findings"] if item["rule_id"] == "safeguard-preservation")
        self.assertEqual("baseline", item["state"])
        self.assertFalse(item["blocking"])
        changed = self.evaluate(unified("src/app.py", removed=["validate(other_request)"]))
        item = next(item for item in changed["findings"] if item["rule_id"] == "safeguard-preservation")
        self.assertEqual("new", item["state"])
        self.assertTrue(item["blocking"])

    def test_baseline_cannot_make_a_high_finding_nonblocking(self):
        diff = unified("fixture.txt", ["password = 'not-a-real-secret-value'"])
        first = self.evaluate(diff)
        finding = next(item for item in first["findings"] if item["rule_id"] == "redaction")
        baseline = {"schema_version": "1", "type": "tailtrail-enforcement-baseline", "policy_version": 1, "generated_at": "2026-08-24T00:00:00Z", "findings": [{"fingerprint": finding["fingerprint"], "rule_id": finding["rule_id"], "path": finding["path"]}]}
        (self.root / "tailtrail-enforcement-baseline.json").write_text(json.dumps(baseline), encoding="utf-8")
        repeated = self.evaluate(diff)
        item = next(item for item in repeated["findings"] if item["rule_id"] == "redaction")
        self.assertEqual("baseline", item["state"])
        self.assertTrue(item["blocking"])
        self.assertEqual("failed", repeated["status"])

    def test_suppression_is_exact_expiring_and_cannot_hide_high(self):
        medium = self.evaluate(unified("src/app.py", removed=["validate(request)"]))
        finding = next(item for item in medium["findings"] if item["rule_id"] == "safeguard-preservation")
        suppression = {"schema_version": "1", "type": "tailtrail-enforcement-suppressions", "policy_version": 1, "suppressions": [{"fingerprint": finding["fingerprint"], "rule_id": finding["rule_id"], "path": finding["path"], "owner": "security-owner", "reason": "Reviewed compatibility fixture.", "expires": (date.today() + timedelta(days=7)).isoformat()}]}
        (self.root / "tailtrail-enforcement-suppressions.json").write_text(json.dumps(suppression), encoding="utf-8")
        suppressed = self.evaluate(unified("src/app.py", removed=["validate(request)"]))
        item = next(item for item in suppressed["findings"] if item["rule_id"] == "safeguard-preservation")
        self.assertEqual("suppressed", item["state"])
        self.assertFalse(item["blocking"])

        high = self.evaluate(unified("fixture.txt", ["password = 'not-a-real-secret-value'"]))
        finding = next(item for item in high["findings"] if item["rule_id"] == "redaction")
        suppression["suppressions"][0].update({"fingerprint": finding["fingerprint"], "rule_id": finding["rule_id"], "path": finding["path"]})
        (self.root / "tailtrail-enforcement-suppressions.json").write_text(json.dumps(suppression), encoding="utf-8")
        unsuppressed = self.evaluate(unified("fixture.txt", ["password = 'not-a-real-secret-value'"]))
        item = next(item for item in unsuppressed["findings"] if item["rule_id"] == "redaction")
        self.assertEqual("new", item["state"])
        self.assertTrue(item["blocking"])

        suppression["suppressions"][0]["expires"] = (date.today() - timedelta(days=1)).isoformat()
        (self.root / "tailtrail-enforcement-suppressions.json").write_text(json.dumps(suppression), encoding="utf-8")
        expired = self.evaluate(unified("src/example.py", ["value = 1"]))
        self.assertEqual("failed", expired["status"])
        self.assertTrue(any("expired" in item["evidence"] for item in expired["findings"]))

    def test_sarif_preserves_location_state_evidence_and_fingerprint(self):
        report = self.evaluate(unified("fixture.txt", ["password = 'not-a-real-secret-value'"]))
        rendered = ENFORCEMENT.sarif(report)
        result = rendered["runs"][0]["results"][0]
        self.assertEqual("2.1.0", rendered["version"])
        self.assertEqual("fixture.txt", result["locations"][0]["physicalLocation"]["artifactLocation"]["uri"])
        self.assertIn("tailtrailFingerprint", result["partialFingerprints"])
        self.assertIn("evidence", result["properties"])
        self.assertTrue(result["properties"]["blocking"])

    def test_strong_secret_detection_avoids_environment_reference_false_positive(self):
        report = self.evaluate(unified("src/settings.py", ['secret_name = os.environ["API_SECRET_NAME"]']))
        self.assertNotIn("redaction", self.rules(report))

    def test_negative_validation_status_and_phase_docs_are_not_runtime_state(self):
        report = self.evaluate(unified("aidlc-docs/phase-e6-design.md", ["Status: not-validated"] ))
        self.assertNotIn("evidence-truth", self.rules(report))
        self.assertNotIn("local-state", self.rules(report))

    def test_unavailable_base_uses_initial_commit_diff(self):
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=self.root, check=True)
        (self.root / "sample.txt").write_text("sample\n", encoding="utf-8")
        subprocess.run(["git", "add", "sample.txt"], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-qm", "initial"], cwd=self.root, check=True)
        args = type("Args", (), {"diff": None, "initial": False, "base": "deadbeef", "head": "HEAD"})()
        diff, mode = ENFORCEMENT.resolve_diff(self.root, args)
        self.assertEqual("initial", mode)
        self.assertIn("sample.txt", diff)

    def test_migration_is_closed_and_non_overwriting(self):
        source = self.root / "v0.json"
        output = self.root / "v1.json"
        source.write_text(json.dumps({"version": 0, "enforce": ["maintainability-guidance"]}), encoding="utf-8")
        self.assertEqual(0, ENFORCEMENT.migrate(source, output))
        migrated = json.loads(output.read_text(encoding="utf-8"))
        self.assertTrue(all(migrated["rules"][item]["enabled"] for item in ENFORCEMENT.LOCKED_RULES))
        with self.assertRaisesRegex(ValueError, "already exists"):
            ENFORCEMENT.migrate(source, output)

    def test_github_integration_is_pinned_read_only_and_versioned(self):
        workflow = (ROOT / ".github/workflows/repository-enforcement.yml").read_text(encoding="utf-8")
        action = (ROOT / ".github/actions/enforce/action.yml").read_text(encoding="utf-8")
        self.assertIn("contents: read", workflow)
        self.assertNotIn("pull-requests: write", workflow)
        self.assertIn("actions/checkout@", workflow)
        self.assertIn("actions/upload-artifact@", workflow)
        self.assertIn('version: "0.6.0"', workflow)
        self.assertIn("TailTrail version must be exact", action)
        self.assertIn("report.sarif", action)
        self.assertIn("TAILTRAIL_PR_BODY_INPUT", action)
        self.assertIn("github.event.pull_request.body", workflow)


if __name__ == "__main__":
    unittest.main()
