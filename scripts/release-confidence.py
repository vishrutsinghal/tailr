#!/usr/bin/env python3
"""Assess tier-labelled delivery confidence from saved local receipts."""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TIERS = ("unit", "component", "integration", "contract", "e2e", "infrastructure", "release-smoke")


def ledger() -> Any:
    spec = importlib.util.spec_from_file_location("release_confidence_ledger", ROOT / "scripts" / "run-ledger.py")
    module = importlib.util.module_from_spec(spec); assert spec and spec.loader; spec.loader.exec_module(module); return module


LEDGER = ledger()


def assess(root: Path, run_id: str, receipts_path: Path) -> dict[str, Any]:
    anchor = json.loads((LEDGER.state_dir(root, run_id) / "anchors" / "approved-v1.json").read_text(encoding="utf-8"))
    raw = json.loads(receipts_path.read_text(encoding="utf-8")); receipts = raw.get("receipts", raw)
    rows: list[dict[str, Any]] = []; findings: list[dict[str, Any]] = []
    for requirement in anchor["requirements"]:
        required = requirement.get("validation_contract", {"state": "required", "tiers": ["unit"]})
        selected = [item for item in receipts if item.get("requirement_uid") == requirement["requirement_uid"]]
        evidence = {tier: next((item.get("outcome") for item in selected if item.get("tier") == tier), "not-recorded") for tier in TIERS}
        rows.append({"requirement_uid": requirement["requirement_uid"], "statement": requirement["statement"], "required_tiers": required.get("tiers", []), "evidence_by_tier": evidence})
        if required.get("state") not in {"conditional", "not-applicable"}:
            for tier in required.get("tiers", []):
                if evidence.get(tier) != "pass": findings.append({"requirement_uid": requirement["requirement_uid"], "tier": tier, "outcome": evidence.get(tier, "not-recorded"), "message": "required tier is not passing; confidence remains incomplete"})
    payload = {"schema_version": "1", "type": "tailtrail-release-confidence", "run_id": run_id, "requirements": rows, "findings": findings, "confidence_complete": not findings, "tier_vocabulary": list(TIERS), "boundary": "confidence is receipt-based; it is not deployment approval, production behavior proof, or a release authorization"}
    directory = LEDGER.state_dir(root, run_id) / "release-confidence"; artifact = directory / f"assessment-{len(list(directory.glob('assessment-*.json'))) + 1}.json"; LEDGER.atomic_json(artifact, payload); LEDGER.append_event(root, run_id, "release_confidence_assessed", {"artifact": artifact.relative_to(LEDGER.state_dir(root, run_id)).as_posix(), "confidence_complete": payload["confidence_complete"], "findings": len(findings)}); return payload


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--root", type=Path, default=Path.cwd()); parser.add_argument("--run-id", required=True); parser.add_argument("--receipts", type=Path, required=True); args = parser.parse_args()
    try: print(json.dumps(assess(args.root.resolve(), args.run_id, args.receipts), indent=2, sort_keys=True)); return 0
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error: print(f"Release confidence error: {error}"); return 2


if __name__ == "__main__": raise SystemExit(main())
