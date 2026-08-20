from __future__ import annotations

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "scripts" / "workflow_runtime"


class WorkflowModuleBoundaryTests(unittest.TestCase):
    def test_runtime_modules_have_one_sentence_responsibility_and_at_most_300_lines(self) -> None:
        for path in sorted(RUNTIME.glob("*.py")):
            lines = path.read_text(encoding="utf-8").splitlines()
            tree = ast.parse("\n".join(lines)); docstring = ast.get_docstring(tree)
            with self.subTest(module=path.name):
                self.assertLessEqual(len(lines), 300)
                self.assertTrue(docstring)
                first_paragraph = docstring.split("\n\n", 1)[0]
                self.assertTrue(first_paragraph.rstrip().endswith("."))
                self.assertNotIn("\n", first_paragraph)


if __name__ == "__main__": unittest.main()
