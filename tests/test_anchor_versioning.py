from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATTERN = re.compile(r"approved-v1\.json")

# Raw `approved-v1.json` reads that remain legitimate after the Issue 13/13a
# migration: fresh-run creators, missing-file fallbacks, debug-domain
# artifacts, test fixtures, and docstring mentions. Counts are exact: any
# ADDED occurrence fails, forcing the author to use latest_approved() or
# justify a new allowlist entry.
EXPECTED_COUNTS = {
    "scripts/change-intent-anchor.py": 1,  # approve() creates v1 for fresh runs
    "scripts/debug-correction.py": 2,  # debug-domain correction packet paths
    "scripts/debug-evaluation.py": 2,  # debug-domain existence probes
    "scripts/debug-reproduction.py": 1,  # missing-file fallback label
    "scripts/docs-only.py": 1,  # creates v1 for fresh doc runs
    "scripts/host-runtime-conformance.py": 1,  # existence probe (v1 always exists)
    "scripts/navigator-scope-release.py": 1,  # release-fixture path
    "scripts/official-aidlc-checkpoint.py": 1,  # missing-file fallback
    "scripts/official-aidlc-runtime.py": 1,  # missing-file fallback
    "scripts/official-aidlc-state.py": 1,  # missing-file fallback
    "scripts/phase8-advanced.py": 1,  # missing-file fallback
    "scripts/planning_lock.py": 2,  # just-created v1 labels (correct by construction)
    "scripts/program-plan.py": 1,  # program-state artifact, not the anchor
    "scripts/session_control.py": 1,  # missing-file fallback ref
    "scripts/spec-kit-slices.py": 1,  # missing-file fallback
    "scripts/task-recovery-boundary.py": 1,  # missing-file fallback
    "scripts/workflow_runtime/compiler.py": 1,  # missing-file fallback
    "scripts/workflow_runtime/freshness.py": 1,  # debug-domain glob
    "scripts/workflow_runtime/mcp_bridge.py": 1,  # missing-file fallback
    "scripts/workflow_runtime/ownership.py": 1,  # missing-file fallback
    "scripts/write_guardian.py": 1,  # docstring mention
}

# Files that must resolve the latest approved anchor (not frozen v1).
MUST_USE_LATEST = [
    "scripts/architecture-fitness.py",
    "scripts/behavior-harness.py",
    "scripts/change-intent-anchor.py",  # invalidate + graph_receipt
    "scripts/closure-close.py",
    "scripts/closure-contract.py",
    "scripts/closure-correction.py",
    "scripts/closure-finalizer.py",
    "scripts/closure-recorder.py",
    "scripts/completion-report.py",
    "scripts/completion-review.py",
    "scripts/context-continuity.py",
    "scripts/debug-correction.py",  # approved_anchor_path helper
    "scripts/debug-reproduction.py",  # compat check + handoff label
    "scripts/delivery-record.py",
    "scripts/drift_analysis.py",
    "scripts/execution-evidence.py",
    "scripts/execution-failure.py",
    "scripts/harness-checkpoint.py",
    "scripts/harness-convergence.py",
    "scripts/harness-template.py",
    "scripts/maintainability-harness.py",
    "scripts/mcp-server.py",  # anchor_show
    "scripts/official-aidlc-checkpoint.py",
    "scripts/official-aidlc-runtime.py",
    "scripts/official-aidlc-state.py",
    "scripts/requirement-completion.py",
    "scripts/requirement-impact-map.py",
    "scripts/requirement-recovery-manifest.py",
    "scripts/session_control.py",
    "scripts/spec-kit-slices.py",
    "scripts/task-recovery-boundary.py",
    "scripts/test-tier-selector.py",
    "scripts/workflow-dashboard.py",
    "scripts/workflow_runtime/compiler.py",
    "scripts/workflow_runtime/mcp_bridge.py",
    "scripts/workflow_runtime/ownership.py",
]


class AnchorVersioningTests(unittest.TestCase):
    def test_no_new_raw_v1_reads(self) -> None:
        failures = []
        for relative, expected in sorted(EXPECTED_COUNTS.items()):
            text = (ROOT / relative).read_text(encoding="utf-8")
            found = sum(1 for line in text.splitlines() if PATTERN.search(line))
            if found != expected:
                failures.append(f"{relative}: expected {expected}, found {found}")
        extra = []
        for path in sorted((ROOT / "scripts").rglob("*.py")):
            relative = path.relative_to(ROOT).as_posix()
            if relative in EXPECTED_COUNTS:
                continue
            if any(PATTERN.search(line) for line in path.read_text(encoding="utf-8").splitlines()):
                extra.append(relative)
        if failures or extra:
            self.fail("raw approved-v1.json reads changed; use latest_approved() or justify a new allowlist entry: "
                      + "; ".join(failures + [f"unexpected file: {item}" for item in extra]))

    def test_migrated_files_resolve_latest(self) -> None:
        missing = []
        for relative in MUST_USE_LATEST:
            text = (ROOT / relative).read_text(encoding="utf-8")
            if "latest_approved" not in text and "approved-v*.json" not in text:
                missing.append(relative)
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
