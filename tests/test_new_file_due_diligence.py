import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

spec = importlib.util.spec_from_file_location("nfdd_test", ROOT / "scripts" / "new_file_due_diligence.py")
nfdd = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module = nfdd
spec.loader.exec_module(nfdd)


def _write(root: Path, relative: str, body: str = "") -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


class CheckExistenceTests(unittest.TestCase):
    def test_existing_path_is_decisive(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write(root, "validate/user.py")
            finding = nfdd.check_existence(root, "validate/user.py")
        self.assertTrue(finding.decisive)
        self.assertIn("path-already-exists", finding.reason_codes)

    def test_missing_path_is_not_decisive(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            finding = nfdd.check_existence(root, "validate2/user.py")
        self.assertFalse(finding.decisive)
        self.assertIn("path-does-not-exist", finding.reason_codes)


class CheckPathEligibilityTests(unittest.TestCase):
    def test_application_path_is_eligible_not_decisive(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            finding = nfdd.check_path_eligibility(root, "schemas/example.schema.json")
        self.assertFalse(finding.decisive)

    def test_generated_path_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            finding = nfdd.check_path_eligibility(root, "node_modules/example/index.js")
        self.assertTrue(finding.decisive)


class CheckNameSymbolCollisionTests(unittest.TestCase):
    def test_3a_only_generic_filename_unrelated_directory_does_not_block(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write(root, "validate/user.py", "def validate_user():\n    return True\n")
            finding = nfdd.check_name_symbol_collision(root, "payments/user.py")
        self.assertTrue(finding.details["sub_check_3a"])
        self.assertFalse(finding.details["sub_check_3b"])
        self.assertFalse(finding.decisive)

    def test_3b_only_directory_near_duplication_different_filename(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write(root, "validate/address.py")
            finding = nfdd.check_name_symbol_collision(root, "validate2/user.py")
        self.assertFalse(finding.details["sub_check_3a"])
        self.assertTrue(finding.details["sub_check_3b"])
        self.assertIn("directory-near-duplication", finding.reason_codes)

    def test_example_d_3a_and_3b_combined_is_decisive(self) -> None:
        """Protocol Example D: validate2/user.py proposed while
        validate/user.py exists -- the strongest form of Check 3 evidence."""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write(root, "validate/user.py", "def validate_user():\n    return True\n")
            finding = nfdd.check_name_symbol_collision(root, "validate2/user.py")
        self.assertTrue(finding.details["sub_check_3a"])
        self.assertTrue(finding.details["sub_check_3b"])
        self.assertTrue(finding.decisive)
        self.assertIn("validate", finding.details["directory_matches"][0])

    def test_no_collision_when_nothing_matches(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write(root, "unrelated/other.py")
            finding = nfdd.check_name_symbol_collision(root, "payments/handler.py")
        self.assertFalse(finding.decisive)
        self.assertIn("no-collision-signal", finding.reason_codes)

    def test_symbol_match_is_detected_across_the_repository(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write(root, "validators/email.py", "def validate_email_format():\n    return True\n")
            finding = nfdd.check_name_symbol_collision(
                root, "scripts/register.py", symbols=("validate_email_format",)
            )
        self.assertIn("validators/email.py", finding.details["symbol_matches"])
        self.assertIn("symbol-match", finding.reason_codes)

    def test_excludes_non_application_paths_from_collision_search(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write(root, "node_modules/validate/user.py")
            finding = nfdd.check_name_symbol_collision(root, "validate2/user.py")
        self.assertFalse(finding.details["sub_check_3a"])
        self.assertFalse(finding.details["sub_check_3b"])


class CheckConventionPrecedentTests(unittest.TestCase):
    def test_precedent_present_with_two_or_more_siblings(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write(root, "schemas/a.schema.json")
            _write(root, "schemas/b.schema.json")
            finding = nfdd.check_convention_precedent(root, "schemas/new.schema.json")
        self.assertTrue(finding.decisive)
        self.assertEqual(finding.details["sibling_count"], 2)

    def test_precedent_absent_directory_does_not_exist_falls_through_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            finding = nfdd.check_convention_precedent(root, "brand_new_dir/thing.schema.json")
        self.assertFalse(finding.decisive)
        self.assertIn("directory-does-not-exist-yet", finding.reason_codes)

    def test_precedent_mixed_single_sibling_is_inconclusive(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write(root, "schemas/a.schema.json")
            finding = nfdd.check_convention_precedent(root, "schemas/new.schema.json")
        self.assertFalse(finding.decisive)
        self.assertEqual(finding.details["sibling_count"], 1)


class RunAllChecksTests(unittest.TestCase):
    def test_run_all_checks_returns_every_check(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write(root, "schemas/a.schema.json")
            findings = nfdd.run_all_checks(root, "schemas/new.schema.json")
        self.assertEqual(
            set(findings.keys()),
            {"existence", "path_eligibility", "name_symbol_collision", "convention_precedent"},
        )
        self.assertTrue(all(hasattr(value, "as_dict") for value in findings.values()))


class CheckExistingOwnerEvidenceTests(unittest.TestCase):
    def test_live_intake_pipeline_misfire_is_not_decisive(self) -> None:
        # Regression for the real observed bug: Navigator proposed
        # scripts/intake_pipeline.py as owner of an unrelated new file on
        # the strength of exactly these three edge kinds. None of them
        # assert ownership of the new concern; the flipped-polarity check
        # must not treat this as decisive.
        finding = nfdd.check_existing_owner_evidence(
            "scripts/intake_pipeline.py",
            ("raises-behavior-error", "imports-module", "tested-by"),
        )
        self.assertFalse(finding.decisive)
        self.assertIn("consumer-only-evidence", finding.reason_codes)
        self.assertEqual(finding.details["ownership_edge_kinds"], [])
        self.assertEqual(
            finding.details["consumer_edge_kinds"], ["imports-module", "tested-by"]
        )

    def test_genuine_ownership_edge_is_decisive(self) -> None:
        finding = nfdd.check_existing_owner_evidence(
            "scripts/real_owner.py",
            ("declares-edit-boundary", "imports-module"),
        )
        self.assertTrue(finding.decisive)
        self.assertIn("strong-ownership-evidence", finding.reason_codes)
        self.assertEqual(finding.details["ownership_edge_kinds"], ["declares-edit-boundary"])

    def test_defines_symbol_edge_is_decisive(self) -> None:
        finding = nfdd.check_existing_owner_evidence(
            "scripts/real_owner.py",
            ("defines-symbol",),
        )
        self.assertTrue(finding.decisive)

    def test_no_edges_is_not_decisive(self) -> None:
        finding = nfdd.check_existing_owner_evidence("scripts/unrelated.py", ())
        self.assertFalse(finding.decisive)
        self.assertIn("no-owner-evidence", finding.reason_codes)
        self.assertEqual(finding.details["ownership_edge_kinds"], [])
        self.assertEqual(finding.details["consumer_edge_kinds"], [])


class CombineVerdictWorkedExamplesTests(unittest.TestCase):
    """Phase N3: Worked Examples A-D from TAILTRAIL-NEW-FILE-DUE-DILIGENCE-
    PROTOCOL.md, each as a permanent automated regression."""

    def test_example_a_schema_file_resolves_new_confirmed(self) -> None:
        # schemas/ already holds two schema files -- strong convention
        # precedent; the only graph evidence found is a consumer edge
        # (the live intake_pipeline.py misfire), which must not block.
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write(root, "schemas/host-input-contract.schema.json")
            _write(root, "schemas/requirement-intake.schema.json")
            relative = "schemas/host-question-flow-event.schema.json"
            findings = nfdd.run_all_checks(root, relative)
            owner_evidence = nfdd.check_existing_owner_evidence(
                "scripts/intake_pipeline.py",
                ("raises-behavior-error", "imports-module", "tested-by"),
            )
            verdict = nfdd.combine_verdict(
                existence=findings["existence"],
                path_eligibility=findings["path_eligibility"],
                collision=findings["name_symbol_collision"],
                owner_evidence=owner_evidence,
                convention=findings["convention_precedent"],
            )
        self.assertEqual(verdict["verdict"], "new-confirmed")
        self.assertIsNone(verdict["question"])

    def test_example_b_existing_symbol_resolves_extend_recommended(self) -> None:
        # The proposed new file's primary symbol already exists elsewhere
        # (unrelated directory) -- 3a-only, weak alone -- but Check 4 finds
        # genuine ownership evidence (defines-symbol) at that existing file,
        # which is decisive regardless of 3a's weak signal.
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write(root, "scripts/validators/email.py", "def validate_email_format():\n    pass\n")
            relative = "scripts/registration/email.py"
            findings = nfdd.run_all_checks(root, relative, symbols=("validate_email_format",))
            owner_evidence = nfdd.check_existing_owner_evidence(
                "scripts/validators/email.py", ("defines-symbol",)
            )
            verdict = nfdd.combine_verdict(
                existence=findings["existence"],
                path_eligibility=findings["path_eligibility"],
                collision=findings["name_symbol_collision"],
                owner_evidence=owner_evidence,
                convention=findings["convention_precedent"],
            )
        self.assertEqual(verdict["verdict"], "extend-recommended")
        self.assertIsNotNone(verdict["question"])
        self.assertIn("scripts/validators/email.py", verdict["question"])

    def test_example_c_existing_file_claim_symmetry_resolves_unverified(self) -> None:
        # Host claims "just edit scripts/payments.py" for CryptoPayments
        # support, but the file has no qualifying ownership relationship to
        # the requirement (only a consumer edge, or none at all).
        result = nfdd.evaluate_existing_file_claim("scripts/payments.py", ("imports-module",))
        self.assertEqual(result["verdict"], "unverified")
        self.assertIsNotNone(result["question"])
        self.assertIn("scripts/payments.py", result["question"])

    def test_example_c_symmetry_accepts_genuine_owner(self) -> None:
        result = nfdd.evaluate_existing_file_claim("scripts/payments.py", ("declares-edit-boundary",))
        self.assertEqual(result["verdict"], "not-applicable")
        self.assertIsNone(result["question"])

    def test_example_d_near_duplicate_directory_resolves_extend_recommended(self) -> None:
        # validate2/user.py proposed while validate/user.py already exists:
        # Check 3's two sub-checks both fire -- the strongest form of
        # collision evidence. Must route to extend-recommended regardless
        # of what convention precedent or rationale would otherwise show,
        # even when owner_evidence independently looks weak.
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write(root, "validate/user.py")
            relative = "validate2/user.py"
            findings = nfdd.run_all_checks(root, relative)
            owner_evidence = nfdd.check_existing_owner_evidence(relative, ())
            verdict = nfdd.combine_verdict(
                existence=findings["existence"],
                path_eligibility=findings["path_eligibility"],
                collision=findings["name_symbol_collision"],
                owner_evidence=owner_evidence,
                convention=findings["convention_precedent"],
                rationale_provided=True,
            )
        self.assertEqual(verdict["verdict"], "extend-recommended")
        self.assertIsNotNone(verdict["question"])
        self.assertIn("validate", verdict["question"])

    def test_existing_path_resolves_collision_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write(root, "validate/user.py")
            findings = nfdd.run_all_checks(root, "validate/user.py")
            owner_evidence = nfdd.check_existing_owner_evidence("validate/user.py", ())
            verdict = nfdd.combine_verdict(
                existence=findings["existence"],
                path_eligibility=findings["path_eligibility"],
                collision=findings["name_symbol_collision"],
                owner_evidence=owner_evidence,
                convention=findings["convention_precedent"],
            )
        self.assertEqual(verdict["verdict"], "collision-blocked")

    def test_no_evidence_either_way_without_rationale_is_unverified(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            _write(root, "misc/other.py")
            relative = "misc/new_thing.py"
            findings = nfdd.run_all_checks(root, relative)
            owner_evidence = nfdd.check_existing_owner_evidence(relative, ())
            verdict = nfdd.combine_verdict(
                existence=findings["existence"],
                path_eligibility=findings["path_eligibility"],
                collision=findings["name_symbol_collision"],
                owner_evidence=owner_evidence,
                convention=findings["convention_precedent"],
            )
        self.assertEqual(verdict["verdict"], "unverified")
        self.assertIsNotNone(verdict["question"])


if __name__ == "__main__":
    unittest.main()
