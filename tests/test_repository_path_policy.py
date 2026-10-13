import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import repository_path_policy as policy  # noqa: E402


def _git(*args: str, cwd: Path) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env.update({
        "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t.test",
        "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t.test",
    })
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True, env=env)


class GitWorktreeRootsTests(unittest.TestCase):
    """Real `git worktree add` fixture: the design requires resolving actual
    linked worktree roots, not just matching a literal `worktrees` path
    component, since a developer or agent can name a nested worktree
    anything."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = Path(self._tmp.name) / "repo"
        self.repo.mkdir()
        _git("init", "-q", cwd=self.repo)
        (self.repo / "scripts").mkdir()
        (self.repo / "scripts" / "ghost.py").write_text("print('real')\n")
        _git("add", "-A", cwd=self.repo)
        _git("commit", "-q", "-m", "init", cwd=self.repo)

    def test_resolves_arbitrarily_named_nested_worktree(self) -> None:
        _git("worktree", "add", "-q", "nested-worktree", "-b", "nested-branch", cwd=self.repo)
        roots = policy.git_worktree_roots(self.repo)
        self.assertEqual(roots, ("nested-worktree",))

    def test_omits_primary_checkout_and_external_worktree(self) -> None:
        sibling = Path(self._tmp.name) / "sibling-worktree"
        _git("worktree", "add", "-q", str(sibling), "-b", "sibling-branch", cwd=self.repo)
        roots = policy.git_worktree_roots(self.repo)
        self.assertEqual(roots, ())

    def test_empty_when_not_a_git_repository(self) -> None:
        plain = Path(self._tmp.name) / "plain"
        plain.mkdir()
        self.assertEqual(policy.git_worktree_roots(plain), ())

    def test_classify_path_excludes_real_nested_worktree_via_resolved_roots(self) -> None:
        _git("worktree", "add", "-q", "nested-worktree", "-b", "nested-branch", cwd=self.repo)
        roots = policy.git_worktree_roots(self.repo)
        role, reasons = policy.classify_path(
            self.repo, "nested-worktree/scripts/ghost.py", worktree_roots=roots,
        )
        self.assertEqual(role, "managed-worktree")
        self.assertEqual(reasons, ("git-worktree-copy",))

    def test_real_file_stays_application_without_worktree_roots_confusion(self) -> None:
        _git("worktree", "add", "-q", "nested-worktree", "-b", "nested-branch", cwd=self.repo)
        roots = policy.git_worktree_roots(self.repo)
        role, _ = policy.classify_path(self.repo, "scripts/ghost.py", worktree_roots=roots)
        self.assertEqual(role, "application")


class RepositoryPathPolicyTests(unittest.TestCase):
    def test_cross_agent_worktree_matrix(self) -> None:
        cases = [
            ".claude/worktrees/run-a/scripts/ghost.py",
            ".codex/worktrees/run-b/scripts/ghost.py",
            ".copilot/worktrees/run-c/scripts/ghost.py",
            ".git/worktrees/run-d/scripts/ghost.py",
            "custom-agent/worktrees/run-e/scripts/ghost.py",
        ]
        for path in cases:
            with self.subTest(path=path):
                role, reasons = policy.classify_path(Path("/repo"), path)
                self.assertEqual(role, "managed-worktree")
                self.assertFalse(policy.is_eligible(role))
                self.assertTrue(reasons)

    def test_real_files_stay_eligible(self) -> None:
        for path in ["src/real.py", "scripts/task-start.py", "tailtrail-registry.json"]:
            with self.subTest(path=path):
                role, reasons = policy.classify_path(Path("/repo"), path)
                self.assertEqual(role, "application")
                self.assertTrue(policy.is_eligible(role))
                self.assertEqual(list(reasons), ["application-path"])

    def test_git_worktree_list_roots_win(self) -> None:
        role, reasons = policy.classify_path(
            Path("/repo"), "linked/scripts/ghost.py",
            worktree_roots=["linked"])
        self.assertEqual(role, "managed-worktree")
        self.assertEqual(list(reasons), ["git-worktree-copy"])

    def test_first_match_wins_deterministically(self) -> None:
        # Under both an agent root and a worktrees component: worktrees wins.
        role, _ = policy.classify_path(Path("/repo"), ".claude/worktrees/x/a.py")
        self.assertEqual(role, "managed-worktree")

    def test_case_insensitive(self) -> None:
        self.assertEqual(policy.classify_path(Path("/repo"), ".CLAUDE/worktrees/X/a.py")[0], "managed-worktree")
        self.assertEqual(policy.classify_path(Path("/repo"), "SRC/Real.PY")[0], "application")

    def test_tailtrail_state_generated_vendor_external_unknown(self) -> None:
        self.assertEqual(policy.classify_path(Path("/repo"), ".tailtrail/runs/x")[0], "tailtrail-managed")
        self.assertEqual(policy.classify_path(Path("/repo"), "src/__pycache__/a.pyc")[0], "generated")
        self.assertEqual(policy.classify_path(Path("/repo"), "vendor/lib/a.py")[0], "generated")
        self.assertEqual(policy.classify_path(Path("/repo"), "../outside.py")[0], "external")
        self.assertEqual(policy.classify_path(Path("/repo"), "")[0], "unknown")
        self.assertEqual(policy.classify_path(Path("/repo"), ".git/config")[0], "generated")

    def test_no_disk_access(self) -> None:
        # Pure path logic: works against roots that do not exist.
        role, _ = policy.classify_path(Path("/definitely/not/here"), "src/a.py")
        self.assertEqual(role, "application")
        self.assertFalse(Path("/definitely/not/here").exists())

    def test_audit_record_shape(self) -> None:
        record = policy.audit_record(Path("/repo"), ".codex/worktrees/r/a.py")
        self.assertEqual(record["status"], "excluded")
        self.assertIn("role", record)
        self.assertTrue(record["reason_codes"])

    def test_nested_state_agent_vcs_roots_excluded(self) -> None:
        cases = {
            "sub/.tailtrail/x": "tailtrail-managed",
            "sub/tailtrail-meta/x": "tailtrail-managed",
            "sub/.claude/y.py": "agent-managed",
            "sub/.codex/y.py": "agent-managed",
            "sub/.copilot/y.py": "agent-managed",
            "sub/.git/y": "generated",
            "sub/.hg/y": "generated",
            "sub/.svn/y": "generated",
        }
        for relative, role in cases.items():
            actual, reasons = policy.classify_path(Path("/repo"), relative)
            self.assertEqual(actual, role, relative)
            self.assertTrue(reasons, relative)

    def test_nested_reason_codes(self) -> None:
        self.assertEqual(
            list(policy.classify_path(Path("/repo"), "sub/.tailtrail/x")[1]),
            ["tailtrail-state-nested"],
        )
        self.assertEqual(
            list(policy.classify_path(Path("/repo"), "sub/.claude/y.py")[1]),
            ["agent-managed-nested"],
        )
        self.assertEqual(
            list(policy.classify_path(Path("/repo"), "sub/.git/y")[1]),
            ["vcs-metadata-nested"],
        )

    def test_nested_checks_do_not_outrank_worktrees(self) -> None:
        role, _ = policy.classify_path(Path("/repo"), ".claude/worktrees/x/.tailtrail/y")
        self.assertEqual(role, "managed-worktree")

    def test_convention_ide_and_runtime_roots_excluded(self) -> None:
        cases = {
            "tailtrail/api.py": "tailtrail-managed",
            "sub/tailtrail/cli.py": "tailtrail-managed",
            "aidlc-rules/core-workflow.md": "tailtrail-managed",
            "sub/aidlc-rules/x.md": "tailtrail-managed",
            ".idea/workspace.xml": "generated",
            "sub/.idea/x.xml": "generated",
        }
        for relative, role in cases.items():
            actual, reasons = policy.classify_path(Path("/repo"), relative)
            self.assertEqual(actual, role, relative)
            self.assertTrue(reasons, relative)
        self.assertEqual(
            list(policy.classify_path(Path("/repo"), "aidlc-rules/x.md")[1]),
            ["managed-conventions"],
        )
        self.assertEqual(
            list(policy.classify_path(Path("/repo"), ".idea/x.xml")[1]),
            ["ide-metadata"],
        )


if __name__ == "__main__":
    unittest.main()
