#!/usr/bin/env python3
"""Generate and validate the versioned TailTrail host-composition surface."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_SCENARIOS = {"small-bug", "hands-free-feature", "rejected-requirement", "evidence-failure", "recovery", "ci-wait"}
PRECEDENCE = ["host safety", "user request", "official stage rules", "tailtrail assurance rules"]


def load(root: Path) -> dict:
    path = root / "adapters" / "host-compatibility-v1.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("type") != "tailtrail-host-adapter-compatibility" or payload.get("adapter_version") != "v1":
        raise ValueError("host compatibility matrix must be a v1 TailTrail adapter matrix")
    if payload.get("precedence") != PRECEDENCE:
        raise ValueError("host compatibility precedence is not the required safety order")
    if {item.get("id") for item in payload.get("conformance_scenarios", [])} != REQUIRED_SCENARIOS:
        raise ValueError("host compatibility matrix must define the six required conformance scenarios")
    return payload


def render(host: dict, matrix: dict) -> str:
    scenarios = "\n".join(f"- **{item['id']}:** {item['expected']}" for item in matrix["conformance_scenarios"])
    return f"""# TailTrail Composed Host Surface — {host['id'].title()}\n\n**Adapter version:** `{matrix['adapter_version']}`\n**Host source:** `{host['source']}`\n\n## Precedence\n\n1. Host safety\n2. User request\n3. Official AI-DLC stage rules for a verified Full-mode run\n4. TailTrail assurance rules\n\nA lower layer cannot weaken a higher layer. Official rules select lifecycle\nstages; TailTrail preserves the approved anchor, evidence, drift, recovery, and\nclosure boundaries.\n\n## Host contract\n\n- `tailtrail start` is planning-only and requires approval before implementation.\n- A rejected requirement preserves its run and routes to requirements/design.\n- Completion uses saved requirement-linked evidence; do not invent command or CI results.\n- `wait-ci` does not create learning. Linked CI acceptance may create a\n  candidate-only learning artifact and deterministic evaluation.\n- {host['official_full_mode']}.\n\n## Conformance scenarios\n\n{scenarios}\n\n## Boundary\n\nThis generated surface validates local instruction composition only. It does not\nguarantee runtime behavior by the host or replace host safety policy.\n"""


def generate(root: Path, matrix: dict) -> list[str]:
    outputs = []
    for host in matrix["hosts"]:
        path = root / host["generated"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render(host, matrix), encoding="utf-8")
        outputs.append(path.relative_to(root).as_posix())
    return outputs


def check(root: Path, matrix: dict) -> list[str]:
    errors = []
    for host in matrix["hosts"]:
        source = root / host["source"]
        generated = root / host["generated"]
        if not source.is_file(): errors.append(f"{host['id']}: source missing: {host['source']}")
        if not generated.is_file():
            errors.append(f"{host['id']}: generated surface missing: {host['generated']}")
        elif generated.read_text(encoding="utf-8") != render(host, matrix):
            errors.append(f"{host['id']}: generated surface is stale")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--write", action="store_true", help="Regenerate composed host surfaces from the versioned matrix.")
    args = parser.parse_args(); root = args.root.resolve()
    try:
        matrix = load(root)
        generated = generate(root, matrix) if args.write else []
        errors = check(root, matrix)
        if errors:
            for error in errors: print(f"Host adapter conformance failed: {error}")
            return 1
        print(json.dumps({"status": "passed", "adapter_version": matrix["adapter_version"], "hosts": [item["id"] for item in matrix["hosts"]], "scenarios": [item["id"] for item in matrix["conformance_scenarios"]], "generated": generated, "boundary": matrix["boundary"]}, indent=2))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"Host adapter conformance error: {error}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
