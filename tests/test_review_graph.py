import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


graph = load("review_graph_test", "scripts/review-graph.py")
astmap = load("ast_map_test", "scripts/ast-map.py")


class MissingRootTests(unittest.TestCase):
    def test_review_graph_rejects_missing_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, "does not exist"):
                graph.graph(Path(temp) / "nope", ["src/a.py"], 8)

    def test_ast_map_rejects_missing_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, "does not exist"):
                astmap.build(Path(temp) / "nope", ["x.py"], "lite", 20)

    def test_review_graph_cli_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            result = subprocess.run(
                [sys.executable, (ROOT / "scripts" / "review-graph.py").as_posix(),
                 "--root", str(Path(temp) / "nope"), "--changed", "x.py", "--format", "json"],
                text=True, capture_output=True, check=False)
            self.assertNotEqual(result.returncode, 0)

    def test_ast_map_cli_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            result = subprocess.run(
                [sys.executable, (ROOT / "scripts" / "ast-map.py").as_posix(),
                 "--root", str(Path(temp) / "nope"), "--changed", "x.py",
                 "--depth", "lite", "--format", "json"],
                text=True, capture_output=True, check=False)
            self.assertNotEqual(result.returncode, 0)

    def test_empty_but_real_root_still_works(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.assertEqual(graph.graph(root, [], 8)["files"], [])
            self.assertEqual(astmap.build(root, [], "lite", 20)["symbols"], [])


if __name__ == "__main__":
    unittest.main()
