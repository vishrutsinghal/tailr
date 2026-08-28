#!/usr/bin/env python3
"""Project a verified official AI-DLC pack into a safe Codex host surface.

The official pack stays immutable under ``.tailtrail/official-aidlc``.  Codex
loads a short managed block from ``AGENTS.md`` only when a TailTrail Full-mode
run is active; that block points at the exact official core rule file.  The
official detail files are copied to their upstream-recognised location so the
unmodified core workflow can resolve them.  Existing user AI-DLC files are
never overwritten.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PACK = Path(".tailtrail") / "official-aidlc"
CORE = PACK / "aws-aidlc-rules" / "core-workflow.md"
DETAILS = PACK / "aws-aidlc-rule-details"
PROJECTED_ROOT = Path(".aidlc") / "aidlc-rules"
PROJECTED_CORE = PROJECTED_ROOT / "aws-aidlc-rules" / "core-workflow.md"
PROJECTED_DETAILS = PROJECTED_ROOT / "aws-aidlc-rule-details"
START = "<!-- tailtrail-official-aidlc:codex:start -->"
END = "<!-- tailtrail-official-aidlc:codex:end -->"


def _load(relative: str, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {relative}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


DETECT = _load("scripts/aidlc-official-detect.py", "official_aidlc_host_detect")


def _digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_root(root: Path) -> Path:
    return root.resolve()


def _block(manifest: dict[str, Any]) -> str:
    official = manifest["official"]
    return "\n".join((
        START,
        "## Official AI-DLC Standard/Full bridge (TailTrail managed)",
        "",
        "This project has a pinned, integrity-verified official AI-DLC pack.",
        "Apply its Requirements Analysis workflow only for an explicit TailTrail",
        "`--aidlc standard` or `--aidlc full` run with an official bridge. Full",
        "continues through the official lifecycle; Standard ends after requirements.",
        "Do not load it for TailTrail Lite or Off runs.",
        "",
        f"- Source: `{official['source']}`",
        f"- Revision: `{official['revision']}`",
        f"- Exact core rule: `{PROJECTED_CORE.as_posix()}`",
        f"- Rule details root: `{PROJECTED_DETAILS.as_posix()}`",
        "",
        "For an active Standard or Full run, read the exact core rule, active",
        "stage rules, and saved Question Orchestrator context before generating",
        "questions. The host generates the official questions and meaningful options",
        "required by that stage. Each question includes requirement IDs, decision",
        "class and impact, known context, evidence references, an advisory",
        "recommendation, and evidence-grounded reasoning. TailTrail validates",
        "grounding and traceability, then records the sanitized artifact without",
        "replacing official AIDLC authority. The user may choose any option",
        "or Other with detail. Host safety and the",
        "user request still take precedence; TailTrail retains its approved-anchor,",
        "evidence, drift, recovery, and closure controls.",
        END,
    )) + "\n"


def _replace_managed_block(content: str, block: str) -> str:
    has_start, has_end = START in content, END in content
    if has_start != has_end:
        raise ValueError("AGENTS.md has an incomplete TailTrail official AI-DLC managed block; repair it before reinstalling")
    if has_start:
        before, after = content.split(START, 1)
        _, suffix = after.split(END, 1)
        return before.rstrip() + "\n\n" + block + suffix.lstrip("\r\n")
    return content.rstrip() + "\n\n" + block


def _atomic_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=path.parent, newline="") as handle:
        handle.write(content)
        temporary = Path(handle.name)
    os.replace(temporary, path)


def _copy_projection(root: Path) -> list[str]:
    source_core, source_details = root / CORE, root / DETAILS
    target_core, target_details = root / PROJECTED_CORE, root / PROJECTED_DETAILS
    if target_core.exists() or target_details.exists():
        raise ValueError("official AI-DLC host projection already exists; validate it or remove it explicitly before reinstalling")
    target_core.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_core, target_core)
    shutil.copytree(source_details, target_details)
    return [PROJECTED_CORE.as_posix(), PROJECTED_DETAILS.as_posix()]


def _manifest(root: Path) -> dict[str, Any]:
    result = DETECT.status(root)
    if result.get("state") != "compatible":
        raise ValueError("a compatible pinned official AI-DLC pack is required; run `tailtrail aidlc official status --root .` first")
    manifest = root / str(result["manifest"])
    return json.loads(manifest.read_text(encoding="utf-8"))


def install(root: Path, host: str = "codex") -> dict[str, Any]:
    root = _safe_root(root)
    if host != "codex":
        raise ValueError("the first real host projection supports Codex only; use the portable bridge for Copilot or Claude")
    manifest = _manifest(root)
    agents = root / "AGENTS.md"
    if not agents.is_file():
        raise ValueError("Codex host projection requires an existing AGENTS.md; install TailTrail's Codex profile first")
    original = agents.read_text(encoding="utf-8")
    if START in original:
        return status(root, host)
    projected = _copy_projection(root)
    _atomic_text(agents, _replace_managed_block(original, _block(manifest)))
    return {**status(root, host), "state": "installed", "projected": projected}


def status(root: Path, host: str = "codex") -> dict[str, Any]:
    root = _safe_root(root)
    compatibility = DETECT.status(root)
    agents = root / "AGENTS.md"
    core, details = root / PROJECTED_CORE, root / PROJECTED_DETAILS
    block_present = agents.is_file() and START in agents.read_text(encoding="utf-8") and END in agents.read_text(encoding="utf-8")
    source_core = root / CORE
    projection_matches = core.is_file() and source_core.is_file() and _digest(core) == _digest(source_core)
    details_present = details.is_dir()
    state = "installed" if compatibility.get("state") == "compatible" and block_present and projection_matches and details_present else "not-installed"
    return {
        "type": "tailtrail-official-aidlc-host-projection",
        "schema_version": "1",
        "host": host,
        "state": state,
        "compatible_pack": compatibility.get("state") == "compatible",
        "managed_block": block_present,
        "projected_core": PROJECTED_CORE.as_posix(),
        "projected_core_matches_pinned_pack": projection_matches,
        "projected_rule_details": PROJECTED_DETAILS.as_posix(),
        "projected_rule_details_present": details_present,
        "boundary": "The official workflow is conditionally loaded only for explicit approved Standard or Full runs. This projection does not fabricate a host session or lifecycle receipt.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    for action in ("install", "status"):
        command = sub.add_parser(action)
        command.add_argument("--root", type=Path, default=Path.cwd())
        command.add_argument("--host", choices=("codex",), default="codex")
    args = parser.parse_args()
    try:
        result = install(args.root, args.host) if args.action == "install" else status(args.root, args.host)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"Official AI-DLC host projection error: {error}")
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["state"] == "installed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
