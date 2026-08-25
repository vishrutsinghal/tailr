from __future__ import annotations

import copy
import importlib.util
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]


def load_script():
    path = ROOT / "scripts" / "enterprise-readiness.py"
    spec = importlib.util.spec_from_file_location("enterprise_readiness_for_ga_gate_test", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


enterprise_readiness = load_script()


def all_complete_registry() -> dict:
    registry = copy.deepcopy(enterprise_readiness.load_registry())
    for requirement in registry["requirements"]:
        requirement["status"] = "complete"
    for defect in registry.get("known_defects", []):
        defect["status"] = "closed"
    return registry


class GaReleaseGateTests(unittest.TestCase):
    """Tests for ENT-E12-001's orchestrated E0-E11 GA release gate."""

    def test_gate_blocks_on_the_real_registry_today(self) -> None:
        registry = enterprise_readiness.load_registry()

        bundle = enterprise_readiness.ga_release_gate(registry, ROOT, approved=True)

        self.assertEqual(bundle["decision"], "blocked")
        self.assertIn("incomplete-requirements", bundle["blocking_reasons"])
        self.assertIn("open-defects", bundle["blocking_reasons"])

    def test_gate_is_ready_when_every_check_is_clean_and_approved(self) -> None:
        registry = all_complete_registry()

        with mock.patch.object(enterprise_readiness, "validate_registry", return_value=[]), \
             mock.patch.object(enterprise_readiness, "candidate_readiness", return_value=[]):
            bundle = enterprise_readiness.ga_release_gate(registry, ROOT, approved=True)

        self.assertEqual(bundle["decision"], "ready")
        self.assertEqual(bundle["blocking_reasons"], [])
        self.assertEqual(bundle["defect_summary"]["open"], [])
        self.assertEqual(bundle["requirement_summary"]["incomplete"], [])

    def test_gate_stays_blocked_without_explicit_approval_even_if_otherwise_clean(self) -> None:
        registry = all_complete_registry()

        with mock.patch.object(enterprise_readiness, "validate_registry", return_value=[]), \
             mock.patch.object(enterprise_readiness, "candidate_readiness", return_value=[]):
            bundle = enterprise_readiness.ga_release_gate(registry, ROOT, approved=False)

        self.assertEqual(bundle["decision"], "blocked")
        self.assertEqual(bundle["blocking_reasons"], ["not-approved-for-publication"])

    def test_gate_blocks_on_open_defects_even_when_requirements_are_complete(self) -> None:
        registry = all_complete_registry()
        registry["known_defects"][0]["status"] = "open"

        with mock.patch.object(enterprise_readiness, "validate_registry", return_value=[]), \
             mock.patch.object(enterprise_readiness, "candidate_readiness", return_value=[]):
            bundle = enterprise_readiness.ga_release_gate(registry, ROOT, approved=True)

        self.assertEqual(bundle["decision"], "blocked")
        self.assertIn("open-defects", bundle["blocking_reasons"])

    def test_gate_blocks_on_inconsistent_release_candidate(self) -> None:
        registry = all_complete_registry()

        with mock.patch.object(enterprise_readiness, "validate_registry", return_value=[]), \
             mock.patch.object(enterprise_readiness, "candidate_readiness", return_value=["missing release file: DEMO.md"]):
            bundle = enterprise_readiness.ga_release_gate(registry, ROOT, approved=True)

        self.assertEqual(bundle["decision"], "blocked")
        self.assertIn("candidate-inconsistent", bundle["blocking_reasons"])


class GaBundleIntegrityTests(unittest.TestCase):
    """Tests for verify_ga_bundle's tamper and drift detection."""

    def _clean_bundle(self, registry: dict) -> dict:
        with mock.patch.object(enterprise_readiness, "validate_registry", return_value=[]), \
             mock.patch.object(enterprise_readiness, "candidate_readiness", return_value=[]):
            return enterprise_readiness.ga_release_gate(registry, ROOT, approved=True)

    def test_verify_passes_for_an_untampered_freshly_matching_bundle(self) -> None:
        registry = all_complete_registry()
        bundle = self._clean_bundle(registry)

        with mock.patch.object(enterprise_readiness, "validate_registry", return_value=[]), \
             mock.patch.object(enterprise_readiness, "candidate_readiness", return_value=[]):
            result = enterprise_readiness.verify_ga_bundle(bundle, registry, ROOT)

        self.assertEqual(result, {"status": "passed", "issues": []})

    def test_verify_detects_a_tampered_bundle(self) -> None:
        registry = all_complete_registry()
        bundle = self._clean_bundle(registry)
        bundle["approved"] = False

        with mock.patch.object(enterprise_readiness, "validate_registry", return_value=[]), \
             mock.patch.object(enterprise_readiness, "candidate_readiness", return_value=[]):
            result = enterprise_readiness.verify_ga_bundle(bundle, registry, ROOT)

        self.assertEqual(result["status"], "blocked")
        self.assertIn("bundle-fingerprint-invalid", result["issues"])

    def test_verify_detects_registry_drift_since_the_bundle_was_produced(self) -> None:
        clean_registry = all_complete_registry()
        bundle = self._clean_bundle(clean_registry)
        drifted_registry = enterprise_readiness.load_registry()

        with mock.patch.object(enterprise_readiness, "validate_registry", return_value=[]), \
             mock.patch.object(enterprise_readiness, "candidate_readiness", return_value=[]):
            result = enterprise_readiness.verify_ga_bundle(bundle, drifted_registry, ROOT)

        self.assertEqual(result["status"], "blocked")
        self.assertIn("registry-drift-since-bundle", result["issues"])

    def test_verify_rejects_a_bundle_of_the_wrong_type(self) -> None:
        result = enterprise_readiness.verify_ga_bundle({"type": "something-else"}, all_complete_registry(), ROOT)

        self.assertEqual(result, {"status": "blocked", "issues": ["not-a-ga-bundle"]})


if __name__ == "__main__":
    unittest.main()
