import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


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
    def test_review_graph_excludes_nested_worktrees_but_keeps_real_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "src").mkdir()
            (root / "src" / "real.py").write_text("VALUE = 1\n", encoding="utf-8")
            nested = root / ".claude" / "worktrees" / "stale" / "src" / "ghost.py"
            nested.parent.mkdir(parents=True)
            nested.write_text("VALUE = 2\n", encoding="utf-8")

            paths = {path.relative_to(root).as_posix() for path in graph.list_candidates(root)}

        self.assertIn("src/real.py", paths)
        self.assertNotIn(".claude/worktrees/stale/src/ghost.py", paths)

    def test_ast_map_excludes_nested_worktrees_but_keeps_real_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "src").mkdir()
            (root / "src" / "real.py").write_text("def real():\n    return 1\n", encoding="utf-8")
            nested = root / ".claude" / "worktrees" / "stale" / "src" / "ghost.py"
            nested.parent.mkdir(parents=True)
            nested.write_text("def ghost():\n    return 2\n", encoding="utf-8")

            result = astmap.build(root, [], "lite", 20)
            files = {str(item.get("file", "")) for item in result["symbols"]}

        self.assertIn("src/real.py", files)
        self.assertNotIn(".claude/worktrees/stale/src/ghost.py", files)

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

    def test_review_graph_policy_excluded_carries_reasons(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "src").mkdir()
            (root / "src" / "real.py").write_text("VALUE = 1\n", encoding="utf-8")
            nested = root / ".claude" / "worktrees" / "stale" / "src" / "ghost.py"
            nested.parent.mkdir(parents=True)
            nested.write_text("VALUE = 2\n", encoding="utf-8")

            records = {row["path"]: row for row in graph.policy_excluded(root)}

        self.assertNotIn("src/real.py", records)
        self.assertIn(".claude/worktrees/stale/src/ghost.py", records)
        ghost = records[".claude/worktrees/stale/src/ghost.py"]
        self.assertEqual(ghost["role"], "managed-worktree")
        self.assertTrue(ghost["reason_codes"])

    def test_ast_map_policy_excluded_carries_reasons(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "src").mkdir()
            (root / "src" / "real.py").write_text("def real():\n    return 1\n", encoding="utf-8")
            nested = root / ".claude" / "worktrees" / "stale" / "src" / "ghost.py"
            nested.parent.mkdir(parents=True)
            nested.write_text("def ghost():\n    return 2\n", encoding="utf-8")

            records = {row["path"]: row for row in astmap.policy_excluded(root)}

        self.assertNotIn("src/real.py", records)
        self.assertIn(".claude/worktrees/stale/src/ghost.py", records)
        ghost = records[".claude/worktrees/stale/src/ghost.py"]
        self.assertEqual(ghost["role"], "managed-worktree")
        self.assertTrue(ghost["reason_codes"])


if __name__ == "__main__":
    unittest.main()
