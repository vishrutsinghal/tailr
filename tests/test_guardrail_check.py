import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module():
    spec = importlib.util.spec_from_file_location(
        "tailtrail_guardrail_check_test", ROOT / "scripts" / "guardrail-check.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


check = load_module()


def added(path, text, line=1):
    return check.DiffLine("added", path, line, text)


def removed(path, text, line=1):
    return check.DiffLine("removed", path, line, text)


def gate_paths(diff_lines):
    return [(finding.path, finding.evidence) for finding in
            check.check_dependency_gate(diff_lines, "", []) if finding.rule == "dependency-gate-required"]


class DependencyGatePrecisionTests(unittest.TestCase):
    def test_metadata_version_bump_is_not_a_dependency(self) -> None:
        diff = [removed("package.json", '  "version": "1.2.3",'),
                added("package.json", '  "version": "1.2.4",')]
        self.assertEqual(gate_paths(diff), [])

    def test_metadata_keys_never_fire(self) -> None:
        diff = [added("package.json", '  "description": "cool 1.2.3 tool",'),
                added("package.json", '  "name": "my-app",')]
        self.assertEqual(gate_paths(diff), [])

    def test_new_dependency_still_fires(self) -> None:
        diff = [added("package.json", '    "lodash": "^4.17.21",')]
        found = gate_paths(diff)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0][0], "package.json")

    def test_new_pin_in_requirements_still_fires(self) -> None:
        diff = [added("requirements.txt", "requests==2.31.0")]
        self.assertEqual(len(gate_paths(diff)), 1)

    def test_added_key_without_removal_still_fires(self) -> None:
        diff = [added("package.json", '    "chalk": "5.3.0",')]
        self.assertEqual(len(gate_paths(diff)), 1)


if __name__ == "__main__":
    unittest.main()
