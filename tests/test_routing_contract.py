"""Routing consistency contract: the two AIDLC decision points must agree.

`navigator_requirement_route` (pre-scope questioning) and
`aidlc_mode_selection` (lifecycle depth) consume the same goal and must
produce compatible pairs. Three routing bugs lived here because nothing
pinned the pairs: a missing `return` clobbered Full escalation on pack
fallback, the scope floor vetoed explicit bare-"using AIDLC" requests, and
risk-selected evidence never escalated the mode. Each case below names the
(route, effective mode) pair plus both selection labels; effective mode is
`requested_mode` on transparent Lite fallback, else `mode`.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FALLBACK = "official-pack-unavailable-fallback"


def load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


task_start = load("routing_contract_task_start", "scripts/task-start.py")

HANDS_FREE_GOAL = (
    "hands-free: add an order-amendment capability. Before fulfilment a customer may change quantity and delivery address; "
    "after allocation quantity may only decrease and release excess inventory; after shipment only an authorized address correction is allowed. "
    "Use idempotent payment delta, audit, notification, API, tests, migration, CI, and rollout evidence. Preserve create-order and cancellation behavior."
)


def decisions(count: int = 2) -> list[dict[str, object]]:
    return [{"id": f"D-0{index + 1}", "class": "material"} for index in range(count)]


def compatible_pack(root: Path) -> None:
    pack = root / ".tailtrail" / "official-aidlc"
    pack.mkdir(parents=True)
    (pack / "LICENSE").write_text("MIT-0\n", encoding="utf-8")
    (pack / "core-workflow.md").write_text("# workflow\n", encoding="utf-8")
    rules = {
        "aws-aidlc-rules/core-workflow.md": "# Requirements Analysis\n",
        "aws-aidlc-rule-details/inception/requirements-analysis.md": "# Generate Clarifying Questions\n",
        "aws-aidlc-rule-details/common/question-format-guide.md": "# Other\n",
        "aws-aidlc-rule-details/common/content-validation.md": "# Content Validation\n",
        "aws-aidlc-rule-details/common/session-continuity.md": "# Session\n",
    }
    for relative, content in rules.items():
        path = pack / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def digest(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    (pack / "manifest.json").write_text(
        json.dumps(
            {
                "schema_version": "1",
                "type": "tailtrail-official-aidlc-pack",
                "official": {
                    "source": "https://github.com/awslabs/aidlc-workflows",
                    "revision": "v2.0.0",
                    "license": {"spdx": "MIT-0", "file": "LICENSE"},
                },
                "host_adapter": {"host": "codex", "rules_path": "core-workflow.md"},
                "integrity": {
                    "algorithm": "sha256",
                    "files": [
                        {"path": "LICENSE", "sha256": digest(pack / "LICENSE")},
                        {
                            "path": "core-workflow.md",
                            "sha256": digest(pack / "core-workflow.md"),
                        },
                    ]
                    + [
                        {"path": relative, "sha256": digest(pack / relative)}
                        for relative in rules
                    ],
                },
            }
        ),
        encoding="utf-8",
    )


# (name, goal, requested, risks, decision_count, pack,
#  expected_route, expected_route_selection_or_None,
#  expected_effective_mode, expected_mode_selection)
CASES = (
    ("trivial stays lite", "fix a typo", None, [], 0, False,
     "scope", None, "lite", "default"),
    ("explicit standard phrase with pack", "use standard AIDLC: add a page", None, [], 0, True,
     "scope", None, "standard", "explicit-natural-language-standard"),
    ("bare using-AIDLC with pack", "using AIDLC: add a page", None, [], 0, True,
     "scope", None, "standard", "explicit-natural-language-standard"),
    ("bare using-AIDLC without pack falls back transparently", "using AIDLC: add a page", None, [], 0, False,
     "scope", None, "standard", "explicit-natural-language-standard"),
    ("explicit flag", "add a page", "standard", [], 2, True,
     "aidlc-standard", "explicit-mode", "standard", "explicit-flag"),
    ("hands-free with programme signals and pack escalates full", HANDS_FREE_GOAL, None,
     ["ci/sonar", "data migration", "release"], 2, True,
     "aidlc-full", "navigator-hands-free-escalation", "full", "navigator-hands-free-escalation"),
    ("hands-free with programme signals and no pack stays eligible", HANDS_FREE_GOAL, None,
     ["ci/sonar", "data migration", "release"], 2, False,
     "aidlc-full", "navigator-hands-free-escalation", "full", "navigator-hands-free-escalation"),
    ("hands-free without signals defaults standard", "hands-free: add an API and rollout plan", None, [], 0, True,
     "scope", None, "standard", "hands-free-default"),
    ("risk-selected evidence routes standard with pack",
     "Create the dapdes-act/dev/auditlogging/apigee-client-credentials resource in service-infrastructure because it does not exist in AWS",
     None, ["infrastructure", "security"], 2, True,
     "aidlc-standard", "navigator-risk-routing", "standard", "navigator-risk-routing"),
    ("risk-selected evidence without pack requests standard transparently",
     "Create the dapdes-act/dev/auditlogging/apigee-client-credentials resource in service-infrastructure because it does not exist in AWS",
     None, ["infrastructure", "security"], 2, False,
     "aidlc-standard", "navigator-risk-routing", "standard", "navigator-risk-routing"),
    ("opt-out stays out", "no AIDLC, just fix the typo", None, [], 0, False,
     "scope", None, "off", "explicit-natural-language-opt-out"),
)


class RoutingContractTests(unittest.TestCase):
    def test_route_and_mode_agree_on_every_blessed_pair(self) -> None:
        for (name, goal, requested, risks, decision_count, pack,
             route, route_selection, mode, mode_selection) in CASES:
            with self.subTest(case=name):
                with tempfile.TemporaryDirectory() as temp:
                    root = Path(temp)
                    if pack:
                        compatible_pack(root)
                    routed = task_start.navigator_requirement_route(
                        goal, requested, {"material_decisions": decisions(decision_count)}
                    )
                    selected = task_start.aidlc_mode_selection(
                        goal, requested, root,
                        {"risk_indicators": risks, "likely_impacted_files": []}, None,
                    )
                effective = (
                    selected["requested_mode"]
                    if selected.get("state") == FALLBACK
                    else selected["mode"]
                )
                self.assertEqual(routed["recommended_route"], route)
                self.assertEqual(routed.get("routing_selection"), route_selection)
                self.assertEqual(effective, mode)
                self.assertEqual(selected["selection"], mode_selection)

    def test_full_escalation_survives_pack_fallback(self) -> None:
        # Regression pin for the missing-return fall-through: the eligible
        # Full escalation must reach the report even when Lite stays active.
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            selected = task_start.aidlc_mode_selection(
                HANDS_FREE_GOAL, None, root,
                {"risk_indicators": ["ci/sonar", "data migration", "release"],
                 "likely_impacted_files": []}, None,
            )
        escalation = selected["full_escalation"]
        self.assertEqual(escalation["state"], "eligible-awaiting-compatible-pack")
        self.assertIn("new Full-mode Planning Lock", escalation["reason"])


if __name__ == "__main__":
    unittest.main()
