from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ledger = load("completion_review_ledger", "scripts/run-ledger.py")
anchor = load("completion_review_anchor", "scripts/change-intent-anchor.py")
checkpoint = load("completion_review_checkpoint", "scripts/harness-checkpoint.py")
review = load("completion_review_script", "scripts/completion-review.py")


class CompletionReviewTests(unittest.TestCase):
    def test_missing_requirement_is_named_as_scope_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            ledger.init_run(root, "review", "demo")
            proposal = root / "proposal.json"
            proposal.write_text(json.dumps({"requirements": [{"statement": "A", "acceptance_criteria": [], "preserve_rules": [], "likely_paths": [], "evidence_plan": []}]}), encoding="utf-8")
            anchor.draft(root, "review", proposal)
            anchor.approve(root, "review")
            directory = ledger.state_dir(root, "review") / "checkpoints"
            directory.mkdir(parents=True)
            (directory / "checkpoint-1.json").write_text(json.dumps({"checkpoint": 1, "requirements": []}), encoding="utf-8")
            result = review.review(root, "review")
        self.assertEqual(result["findings"][0]["classification"], "new-drift")
