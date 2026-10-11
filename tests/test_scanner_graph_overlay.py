from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


sgo = load("sgo_test", "scripts/scanner-graph-overlay.py")


class ScannerGraphOverlayRedactionTests(unittest.TestCase):
    def test_multiline_private_key_is_redacted_before_line_splitting(self) -> None:
        """Regression test: a real PEM block spans several physical lines, so
        per-line redaction alone can never match PRIVATE_KEY_PATTERN's
        multi-line (DOTALL) span. read_lines() must redact it first, while
        the text is still whole, before splitting into individual lines.
        """
        report_text = (
            "Secret found in src/config.py:\n"
            "-----BEGIN RSA PRIVATE KEY-----\n"
            "MIIEpAIBAAKCAQEA1234567890abcdefghijklmnopqrstuvwxyzABCDEFGH\n"
            "-----END RSA PRIVATE KEY-----\n"
            "CWE-798 hardcoded credential\n"
        )
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = root / "vuln.txt"
            report.write_text(report_text, encoding="utf-8")
            lines = sgo.read_lines(report)
        self.assertFalse(any("MIIEpAIBAAKCAQEA" in line for line in lines))
        self.assertTrue(any("[REDACTED_PRIVATE_KEY]" in line for line in lines))

    def test_multiline_private_key_never_leaks_through_the_full_overlay_pipeline(self) -> None:
        report_text = (
            "Secret found in src/config.py:\n"
            "-----BEGIN RSA PRIVATE KEY-----\n"
            "MIIEpAIBAAKCAQEA1234567890abcdefghijklmnopqrstuvwxyzABCDEFGH\n"
            "-----END RSA PRIVATE KEY-----\n"
            "CWE-798 hardcoded credential\n"
        )
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = root / "vuln.txt"
            report.write_text(report_text, encoding="utf-8")
            result = sgo.overlay(root, [], [report], [], False, 40, 12)
        serialized = json.dumps(result)
        self.assertNotIn("MIIEpAIBAAKCAQEA", serialized)

    def test_single_line_secret_patterns_still_redact_correctly(self) -> None:
        """Guards against a regression in the pre-existing single-line
        redaction paths (bearer token, key=value assignment, long base64-like
        secret) while fixing the multi-line case.
        """
        report_text = (
            "CVE-2024-11111 leaked Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.payload\n"
            "CVE-2024-22222 password=SuperSecretValue123 found in config\n"
            "CVE-2024-33333 leaked value aGVsbG8gdGhpcyBpcyBhIHZlcnkgbG9uZ3NlY3JldHRva2Vu in log\n"
        )
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = root / "vuln.txt"
            report.write_text(report_text, encoding="utf-8")
            result = sgo.overlay(root, [], [report], [], False, 40, 12)
        serialized = json.dumps(result)
        self.assertNotIn("eyJhbGciOiJIUzI1NiJ9.payload", serialized)
        self.assertNotIn("SuperSecretValue123", serialized)
        self.assertNotIn("aGVsbG8gdGhpcyBpcyBhIHZlcnkgbG9uZ3NlY3JldHRva2Vu", serialized)
        self.assertIn("Bearer [REDACTED_TOKEN]", serialized)
        self.assertIn("password=[REDACTED]", serialized)
        self.assertIn("[REDACTED_SECRET]", serialized)


class ScannerGraphOverlayParsingTests(unittest.TestCase):
    def test_sarif_input_is_parsed_into_a_finding_with_correct_fields(self) -> None:
        sarif = {
            "version": "2.1.0",
            "runs": [{
                "tool": {"driver": {"rules": [{"id": "py/sql-injection", "name": "SQL Injection"}]}},
                "results": [{
                    "ruleId": "py/sql-injection",
                    "level": "error",
                    "message": {"text": "Possible SQL injection via unsanitized input."},
                    "locations": [{"physicalLocation": {
                        "artifactLocation": {"uri": "src/db.py"},
                        "region": {"startLine": 15},
                    }}],
                }],
            }],
        }
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = root / "codeql.sarif.json"
            report.write_text(json.dumps(sarif), encoding="utf-8")
            result = sgo.overlay(root, [], [report], [], False, 40, 12)
        self.assertEqual(result["finding_count"], 1)
        finding = result["findings"][0]
        self.assertEqual(finding["rules"], ["py/sql-injection"])
        self.assertEqual(finding["severities"], ["HIGH"])
        self.assertIn("src/db.py", finding["affected_paths"])

    def test_trivy_dependency_vulnerability_is_parsed_correctly(self) -> None:
        trivy = {
            "Results": [{
                "Target": "package-lock.json",
                "Class": "lang-pkgs",
                "Type": "npm",
                "Vulnerabilities": [{
                    "VulnerabilityID": "CVE-2023-45678",
                    "PkgName": "lodash",
                    "Severity": "HIGH",
                    "Title": "Prototype pollution in lodash",
                }],
            }],
        }
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = root / "trivy.json"
            report.write_text(json.dumps(trivy), encoding="utf-8")
            result = sgo.overlay(root, [], [report], [], False, 40, 12)
        self.assertEqual(result["finding_count"], 1)
        finding = result["findings"][0]
        self.assertEqual(finding["vulnerability_ids"], ["CVE-2023-45678"])
        self.assertEqual(finding["kind"], "dependency vulnerability")
        self.assertEqual(finding["components"], ["lodash"])

    def test_oversized_report_is_rejected_before_parsing(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = root / "huge.txt"
            report.write_text("x" * 1000, encoding="utf-8")
            with self.assertRaises(ValueError):
                sgo.overlay(root, [], [report], [], False, 40, 12, max_input_bytes=100)


if __name__ == "__main__":
    unittest.main()
