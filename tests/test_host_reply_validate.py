"""Golden transcript tests: hosts must follow the Start/hello contract.

The entrypoint tests assert instruction files *contain* rules. These tests
assert hosts *follow* them on scripted transcripts: given a real Start
(or hello, or scope-confirmation) stdout, the host reply must carry the run
ID, the headings, and the fenced banner with nothing added or removed.

Baseline sample v1 (this file): 3 compliant replies score clean, 7 real
failure shapes from the session (emoji greeting, stripped fence,
synthesized plan, missing run ID, invented lock, dropped scope question,
narrated hello) each score exactly their expected violations. When a new
violation class appears twice in real sessions, add it here as a fixture
before touching any instruction wording.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "tests" / "golden" / "host-replies"

# (stdout fixture, reply fixture, expected violation codes in order)
CASES = (
    ("start_plan_stdout.md", "reply_ok.md", ()),
    ("hello_stdout.md", "hello_ok.md", ()),
    ("scope_stdout.md", "scope_ok.md", ()),
    ("start_plan_stdout.md", "reply_emoji.md", ("report-start", "content-added")),
    (
        "start_plan_stdout.md",
        "reply_stripped_fence.md",
        ("report-start", "fence-altered", "content-removed"),
    ),
    ("start_plan_stdout.md", "reply_synthesized_plan.md", ("content-added",)),
    (
        "start_plan_stdout.md",
        "reply_missing_run_id.md",
        ("run-id-missing", "content-removed"),
    ),
    ("scope_stdout.md", "reply_claims_lock.md", ("lock-claimed", "content-added")),
    ("scope_stdout.md", "reply_dropped_question.md", ("content-removed",)),
    ("hello_stdout.md", "hello_narrated.md", ("report-start", "content-added")),
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "tailtrail_host_reply_validate_test",
        ROOT / "scripts" / "host-reply-validate.py",
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class HostReplyValidateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_module()

    def test_golden_replies_score_exactly_their_expected_violations(self) -> None:
        for stdout_name, reply_name, expected in CASES:
            with self.subTest(reply=reply_name):
                stdout = (GOLDEN / stdout_name).read_text(encoding="utf-8")
                reply = (GOLDEN / reply_name).read_text(encoding="utf-8")
                codes = tuple(
                    violation["code"]
                    for violation in self.module.validate_host_reply(stdout, reply)
                )
                self.assertEqual(codes, expected)

    def test_every_violation_names_its_core_rule(self) -> None:
        stdout = (GOLDEN / "start_plan_stdout.md").read_text(encoding="utf-8")
        reply = (GOLDEN / "reply_emoji.md").read_text(encoding="utf-8")
        for violation in self.module.validate_host_reply(stdout, reply):
            with self.subTest(code=violation["code"]):
                self.assertTrue({"code", "rule", "detail"} <= set(violation))
                self.assertTrue(violation["rule"])
                self.assertTrue(violation["detail"])

    def test_score_payload_marks_compliance(self) -> None:
        stdout = (GOLDEN / "start_plan_stdout.md").read_text(encoding="utf-8")
        good = (GOLDEN / "reply_ok.md").read_text(encoding="utf-8")
        bad = (GOLDEN / "reply_synthesized_plan.md").read_text(encoding="utf-8")
        self.assertTrue(self.module.score_payload(stdout, good)["compliant"])
        self.assertFalse(self.module.score_payload(stdout, bad)["compliant"])
        self.assertEqual(
            self.module.score_payload(stdout, good)["run_id"], "golden-run-1"
        )


    def test_cli_scores_golden_replies_with_matching_exit_codes(self) -> None:
        good = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "tailtrail.py"),
                "host-reply",
                "score",
                "--report",
                str(GOLDEN / "start_plan_stdout.md"),
                "--reply",
                str(GOLDEN / "reply_ok.md"),
                "--format",
                "json",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        bad = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "tailtrail.py"),
                "host-reply",
                "score",
                "--report",
                str(GOLDEN / "start_plan_stdout.md"),
                "--reply",
                str(GOLDEN / "reply_emoji.md"),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(good.returncode, 0, good.stderr)
        self.assertTrue(json.loads(good.stdout)["compliant"])
        self.assertEqual(bad.returncode, 1, bad.stderr)
        self.assertIn("report-start", bad.stdout)


if __name__ == "__main__":
    unittest.main()
