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


if __name__ == "__main__":
    unittest.main()
