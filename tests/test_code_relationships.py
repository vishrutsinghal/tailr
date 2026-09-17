"""Phase 9 focused check: language capability registry + extractors.

Run: python -m unittest tests.test_code_relationships -v
"""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import code_relationships as cr  # noqa: E402


def _extract(name: str, text: str) -> dict:
    root = Path("/repo")
    return cr.extract(root / name, root, text)


class RegistryTests(unittest.TestCase):
    def test_python_leads_terraform_follows(self) -> None:
        self.assertEqual(cr.support_level("python"), 2)
        self.assertEqual(cr.support_level("terraform"), 2)

    def test_level1_languages_declared(self) -> None:
        for language in ("javascript", "typescript", "java", "csharp", "go"):
            self.assertEqual(cr.support_level(language), 1, language)

    def test_unlisted_language_returns_none(self) -> None:
        self.assertIsNone(cr.support_level("vue"))
        self.assertIsNone(cr.support_level("svelte"))
        self.assertIsNone(cr.support_level("sql"))
        self.assertIsNone(cr.support_level(""))

    def test_entries_name_parser_and_techniques(self) -> None:
        entry = cr.support_for("python")
        self.assertEqual(entry["parser"], "ast")
        self.assertIn("imports", entry["techniques"])


class PythonExtractorTests(unittest.TestCase):
    def test_definitions_and_imports(self) -> None:
        facts = _extract("a.py", "import os\nfrom src.b import thing\n\n\ndef f():\n    return 1\n")
        self.assertEqual(facts["language"], "python")
        self.assertIn("f", [row["value"] for row in facts["definitions"]])
        self.assertIn("os", [row["value"] for row in facts["imports"]])

    def test_syntax_error_yields_empty_not_crash(self) -> None:
        facts = _extract("a.py", "def broken(:\n")
        self.assertEqual(facts["definitions"], [])


class JavascriptExtractorTests(unittest.TestCase):
    BODIES = {
        "arrow": "const run = async (value) => func(value);\n",
        "exported": "export function validate(order) { return true; }\n",
        "export_default": "export default class Store {}\n",
        "plain": "function legacy() { return 0; }\n",
    }

    def test_arrow_consts_are_definitions(self) -> None:
        facts = _extract("a.js", self.BODIES["arrow"])
        self.assertIn("run", [row["value"] for row in facts["definitions"]])

    def test_export_prefixed_declarations_found_once(self) -> None:
        for key in ("exported", "export_default", "plain"):
            facts = _extract("a.ts", self.BODIES[key])
            values = [row["value"] for row in facts["definitions"]]
            self.assertEqual(len(values), len(set(values)), key)
        self.assertIn("validate", [row["value"] for row in _extract("a.ts", self.BODIES["exported"])["definitions"]])
        self.assertIn("Store", [row["value"] for row in _extract("a.ts", self.BODIES["export_default"])["definitions"]])

    def test_garbage_never_crashes(self) -> None:
        facts = _extract("a.js", "const = => ;;; export function ({\n")
        self.assertIsInstance(facts["definitions"], list)


class MapperProfileTests(unittest.TestCase):
    def _mapper(self):
        path = REPO / "scripts" / "code-graph-mapper.py"
        spec = importlib.util.spec_from_file_location("mapper_profile_test", path)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module

    def test_levels_come_from_registry(self) -> None:
        mapper = self._mapper()
        profiles = mapper.language_profiles([
            Path("a.py"), Path("b.ts"), Path("c.tf"), Path("d.vue"),
        ])
        self.assertEqual(profiles["python"]["level"], 2)
        self.assertEqual(profiles["terraform"]["level"], 2)
        self.assertEqual(profiles["typescript"]["level"], 1)
        self.assertEqual(profiles["vue"]["level"], 1)


if __name__ == "__main__":
    unittest.main()
