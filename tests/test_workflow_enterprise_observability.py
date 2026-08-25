from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.workflow_enterprise_helpers import activate, event, workflow
from workflow_runtime import enterprise, enterprise_recovery, enterprise_transport


ROOT = Path(__file__).resolve().parents[1]


def load_enforcement():
    spec = importlib.util.spec_from_file_location("tailtrail_e9_enforcement", ROOT / "scripts" / "repository-enforcement.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


ENFORCEMENT = load_enforcement()


class WorkflowEnterpriseObservabilityGovernanceTests(unittest.TestCase):
    """Phase E9 (ENT-E9-001): closes the effective-policy, support-bundle,
    audit round-trip, access-review, observability-cardinality, and
    tabletop-drill gaps against the existing local enterprise adapter and
    repository-enforcement policy engine.
    """

    # Effective policy
    def test_effective_policy_reports_merged_classification_and_counts(self) -> None:
        policy = json.loads((ROOT / "tailtrail-enforcement-policy.json").read_text(encoding="utf-8"))
        explained = ENFORCEMENT.explain_policy(policy)
        self.assertEqual(explained["type"], "tailtrail-repository-effective-policy")
        self.assertEqual(set(explained["rules"]), set(policy["rules"]))
        for rule_id in ENFORCEMENT.LOCKED_RULES:
            self.assertTrue(explained["rules"][rule_id]["locked"])
            self.assertEqual(explained["rules"][rule_id]["classification"], "enforced")
        self.assertEqual(sum(explained["counts"].values()), sum(1 for r in explained["rules"].values() if r["enabled"]))

        # a tightening override is reflected in the effective view
        override = {"schema_version": "1", "type": "tailtrail-repository-enforcement-override", "policy_version": 1, "rules": {"host-instruction-conformance": {"severity": "high"}}, "limits": {}}
        merged, issues = ENFORCEMENT.merge_override(policy, override)
        self.assertEqual(issues, [])
        self.assertEqual(ENFORCEMENT.explain_policy(merged)["rules"]["host-instruction-conformance"]["severity"], "high")

    def test_cli_explain_matches_the_python_effective_policy_view(self) -> None:
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "repository-enforcement.py"), "explain", "--root", ROOT.as_posix()],
            cwd=ROOT, text=True, capture_output=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        policy = json.loads((ROOT / "tailtrail-enforcement-policy.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["rules"], ENFORCEMENT.explain_policy(policy)["rules"])

    # Access review
    def test_access_review_reports_the_approved_allowlist_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            wid = workflow(root)
            activate(root, wid)
            review = enterprise_recovery.access_review(root, wid)
        self.assertEqual(review["authorized_actor_ids"], ["actor-operator"])
        self.assertIn("repo-primary", review["authorized_repository_ids"])
        self.assertTrue(review["binding_repository_authorized"])
        self.assertNotIn("fencing_token", review)
        self.assertNotIn("lease_id", review)

    # Support bundle / audit round-trip
    def test_support_bundle_round_trips_and_detects_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            wid = workflow(root)
            activate(root, wid)
            lease = enterprise_transport.acquire(root, wid, "tenant-alpha", "actor-operator", True)
            enterprise_transport.ingest(root, wid, event(root, wid, lease), True)
            enterprise_recovery.backup(root, wid, True)

            with self.assertRaisesRegex(ValueError, "explicit approval"):
                enterprise_recovery.support_bundle(root, wid, False)

            bundle = enterprise_recovery.support_bundle(root, wid, True)
            verified = enterprise_recovery.verify_support_bundle(root, bundle["artifact"])
            self.assertEqual(verified["status"], "passed")

            bundle_path = root / bundle["artifact"]
            tampered = json.loads(bundle_path.read_text(encoding="utf-8"))
            tampered["conformance"]["status"] = "passed-forged"
            bundle_path.write_text(json.dumps(tampered), encoding="utf-8")
            retampered = enterprise_recovery.verify_support_bundle(root, bundle["artifact"])
        self.assertEqual(retampered["status"], "blocked")
        self.assertIn("bundle-fingerprint-invalid", retampered["issues"])

    # Observability cardinality
    def test_observability_projection_shape_stays_bounded_as_events_grow(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            wid = workflow(root)
            activate(root, wid, {"lease_seconds": 3600, "max_events_per_workflow": 30, "max_backups": 3, "retained_events": 30})
            lease = enterprise_transport.acquire(root, wid, "tenant-alpha", "actor-operator", True)

            small = enterprise_transport.observe(root, wid)
            for sequence in range(1, 21):
                enterprise_transport.ingest(root, wid, event(root, wid, lease, sequence, f"ente-cardinality-{sequence}"), True)
            large = enterprise_transport.observe(root, wid)

        # the sanitized projection's shape (key set) never grows with event count;
        # only the bounded integer counter changes
        self.assertEqual(set(small), set(large))
        self.assertEqual(large["transport_event_count"], 20)
        self.assertLess(len(json.dumps(large)), 2000, "observability projection must stay small regardless of event volume")

    # Tabletop drill (documented in SUPPORT.md)
    def test_tabletop_drill_diagnose_then_export_support_bundle(self) -> None:
        """Exercises the exact SUPPORT.md administrator runbook sequence:
        diagnose a blocked workflow with conformance, then capture a support
        bundle that reflects the blocked state for handoff/escalation.
        """
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            wid = workflow(root)
            activate(root, wid)
            lease = enterprise_transport.acquire(root, wid, "tenant-alpha", "actor-operator", True)
            enterprise_transport.ingest(root, wid, event(root, wid, lease), True)

            # simulate an incident: corrupt the live event journal
            event_journal = enterprise.directory(root) / "state-store" / "events" / f"{wid}.jsonl"
            event_journal.write_text(event_journal.read_text(encoding="utf-8") + "{broken\n", encoding="utf-8")

            diagnosis = enterprise_recovery.conformance(root, wid)
            self.assertEqual(diagnosis["status"], "blocked")

            bundle = enterprise_recovery.support_bundle(root, wid, True)
            self.assertEqual(bundle["conformance"]["status"], "blocked")
            verified = enterprise_recovery.verify_support_bundle(root, bundle["artifact"])
        self.assertEqual(verified["status"], "passed", "the bundle itself must still be intact even though it truthfully reports a blocked workflow")


if __name__ == "__main__":
    unittest.main()
