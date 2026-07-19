#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

COPILOT_SOURCE = ROOT / "adapters" / "copilot-instructions.md"

PACK_FILES = [
    "AGENTS.md",
    "AIDLC.md",
    "DEPENDENCY-GATE.md",
    "GUARDRAILS.md",
    "GOVERNANCE.md",
    "TOKEN-AUTOPILOT.md",
    "TOKEN-SLICER.md",
    "TAILTRAIL-COMMANDS.md",
    "tailtrail-policy.example.md",
    "USEFUL-PROMPTS.md",
    "USER-GUIDE.md",
]

PACK_DIRS = [
    "adapters",
    "aidlc",
    "assets",
    "benchmarks",
    "context",
    "hooks",
    "templates",
]

PACK_SCRIPTS = [
    "scripts/aidlc-check.py",
    "scripts/aidlc-init.py",
    "scripts/analyze-benchmark.py",
    "scripts/benchmark-tailtrail.py",
    "scripts/ci-summary.py",
    "scripts/code-graph-mapper.py",
    "scripts/context-receipt.py",
    "scripts/context_receipt.py",
    "scripts/cross-repo-reference.py",
    "scripts/expand-intent.py",
    "scripts/graph-learning.py",
    "scripts/install-copilot.py",
    "scripts/install-launcher.py",
    "scripts/install-local.py",
    "scripts/learning-agent.py",
    "scripts/learning-refresh.py",
    "scripts/learnings.py",
    "scripts/navigator.py",
    "scripts/navigator_core.py",
    "scripts/navigator_render.py",
    "scripts/policy-check.py",
    "scripts/prompt-profile.py",
    "scripts/prompt_profile.py",
    "scripts/quality-loop.py",
    "scripts/quality-run.py",
    "scripts/quality-scan.py",
    "scripts/review-graph.py",
    "scripts/route-context.py",
    "scripts/sonar-summary.py",
    "scripts/tailtrail.py",
    "scripts/tailtrail-report.py",
    "scripts/sync-governance.py",
    "scripts/token-auto.py",
    "scripts/token-budget-coach.py",
    "scripts/token_budget_coach.py",
    "scripts/token-savings.py",
    "scripts/update-copilot.py",
    "scripts/team-init.py",
    "scripts/update-tailtrail.py",
    "scripts/validation-summary.py",
    "scripts/vulnerability-run.py",
    "scripts/vulnerability-scan.py",
    "scripts/vulnerability-summary.py",
]

MANIFEST_NAME = ".tailtrail-install.json"


def copy_file(source: Path, destination: Path, force: bool, written: list[str], skipped: list[str]) -> None:
    if destination.exists() and not force:
        skipped.append(destination.as_posix())
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    written.append(destination.as_posix())


def pack_ignore(directory: str, names: list[str]) -> set[str]:
    ignored = {"__pycache__", ".DS_Store"}.intersection(names)
    if Path(directory).name == "results" and "benchmarks" in Path(directory).parts:
        ignored.update(name for name in names if name.endswith(".md"))
    return ignored


def copy_dir(source: Path, destination: Path, force: bool, written: list[str], skipped: list[str]) -> None:
    if destination.exists() and not force:
        skipped.append(destination.as_posix())
        return
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination, ignore=pack_ignore)
    written.append(destination.as_posix())


def pack_entries() -> list[str]:
    entries: list[str] = []
    entries.extend(PACK_FILES)
    for relative_dir in PACK_DIRS:
        source_dir = ROOT / relative_dir
        for path in sorted(source_dir.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts and path.name != ".DS_Store":
                if relative_dir == "benchmarks" and "results" in path.parts and path.suffix == ".md":
                    continue
                entries.append(path.relative_to(ROOT).as_posix())
    entries.extend(PACK_SCRIPTS)
    return sorted(entries)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_manifest(pack_root: Path, pack_dir: Path, written: list[str]) -> None:
    if pack_dir.as_posix() == ".":
        location = "repository root"
    else:
        location = pack_dir.as_posix()
    files = {
        relative_path: {
            "sha256": sha256(ROOT / relative_path),
        }
        for relative_path in pack_entries()
    }
    files[".github/copilot-instructions.md"] = {
        "sha256": hashlib.sha256(copilot_body(pack_dir).encode("utf-8")).hexdigest(),
    }
    manifest = {
        "version": 1,
        "tool": "tailtrail",
        "pack_dir": pack_dir.as_posix(),
        "pack_location": location,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "files": files,
        "customization": {
            "preferred_override_files": [
                ".tailtrail/intent-overrides.json",
                f"{pack_dir.as_posix()}/intent-overrides.json" if pack_dir.as_posix() != "." else "intent-overrides.json",
            ],
            "note": "Customize TailTrail through override files instead of editing managed core files.",
        },
    }
    destination = pack_root / MANIFEST_NAME
    destination.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    written.append(destination.as_posix())


def validate_pack_dir(pack_dir: str) -> Path:
    path = Path(pack_dir)
    if path.is_absolute():
        raise SystemExit("--pack-dir must be relative to the target project root")
    if any(part == ".." for part in path.parts):
        raise SystemExit("--pack-dir must not contain '..'")
    return path


def copilot_body(pack_dir: Path | None) -> str:
    body = COPILOT_SOURCE.read_text(encoding="utf-8")
    if pack_dir is None:
        return body

    pack_label = pack_dir.as_posix()
    if pack_label == ".":
        pack_label = "repository root"
        prefix = ""
        script_prefix = "scripts"
    else:
        prefix = f"{pack_dir.as_posix()}/"
        script_prefix = f"{pack_dir.as_posix()}/scripts"

    return (
        body
        + "\n\n"
        + "## Installed TailTrail Pack Location\n\n"
        + f"TailTrail support files are installed under `{pack_label}`.\n\n"
        + "When using TailTrail support files, resolve them from this location:\n\n"
        + f"- `{prefix}AGENTS.md`\n"
        + f"- `{prefix}AIDLC.md`\n"
        + f"- `{prefix}DEPENDENCY-GATE.md`\n"
        + f"- `{prefix}GUARDRAILS.md`\n"
        + f"- `{prefix}GOVERNANCE.md`\n"
        + f"- `{prefix}tailtrail-policy.example.md`\n"
        + f"- `{prefix}context/flow-catalog.md`\n"
        + f"- `{prefix}context/guardrail-layers.md`\n"
        + f"- `{prefix}context/intent-aliases.md`\n"
        + f"- `{prefix}context/navigator.md`\n"
        + f"- `{prefix}context/code-graph-mapper.md`\n"
        + f"- `{prefix}context/review-lenses.md`\n"
        + f"- `{prefix}context/TailTrail.map.md`\n"
        + f"- `{prefix}context/slices.md`\n"
        + f"- `{prefix}TAILTRAIL-COMMANDS.md`\n"
        + f"- `{prefix}USEFUL-PROMPTS.md`\n"
        + f"- `{prefix}hooks/`\n"
        + f"- `{prefix}benchmarks/`\n"
        + f"- `{prefix}aidlc/stages/`\n"
        + f"- `{prefix}templates/`\n\n"
        + "When scripts are needed, use:\n\n"
        + f"- `python3 {script_prefix}/tailtrail.py help`\n"
        + f"- `python3 {script_prefix}/tailtrail.py guide \"fix Sonar issue and prepare PR\"`\n"
        + f"- `python3 {script_prefix}/navigator.py \"fix Sonar issue and prepare PR\"`\n"
        + f"- `python3 {script_prefix}/tailtrail.py graph --changed path/to/file`\n"
        + f"- `python3 {script_prefix}/tailtrail.py graph map --changed path/to/file`\n"
        + f"- `python3 {script_prefix}/tailtrail.py graph status --changed path/to/file`\n"
        + f"- `python3 {script_prefix}/tailtrail.py ci summarize --file ci.log`\n"
        + f"- `python3 {script_prefix}/tailtrail.py sonar summarize --file sonar.log`\n"
        + f"- `python3 {script_prefix}/tailtrail.py validation summarize --ci ci.log --sonar sonar.log`\n"
        + f"- `python3 {script_prefix}/tailtrail.py quality scan --changed path/to/file`\n"
        + f"- `python3 {script_prefix}/tailtrail.py quality run --approved --command \"npm run lint\"`\n"
        + f"- `python3 {script_prefix}/tailtrail.py quality-loop review --month 2026-07`\n"
        + f"- `python3 {script_prefix}/tailtrail.py report --month 2026-07`\n"
        + f"- `python3 {script_prefix}/tailtrail.py report value --month 2026-07`\n"
        + f"- `python3 {script_prefix}/tailtrail.py policy check --root .`\n"
        + f"- `python3 {script_prefix}/tailtrail.py governance check`\n"
        + f"- `python3 {script_prefix}/tailtrail.py vulnerability scan --changed package.json`\n"
        + f"- `python3 {script_prefix}/tailtrail.py vulnerability summarize --file audit.log`\n"
        + f"- `python3 {script_prefix}/tailtrail.py vulnerability run --approved --command \"npm audit\"`\n"
        + f"- `python3 {script_prefix}/expand-intent.py \"use AIDLC and review\"`\n"
        + f"- `python3 {script_prefix}/install-local.py --inspect`\n"
        + f"- `python3 {script_prefix}/benchmark-tailtrail.py`\n"
        + f"- `python3 {script_prefix}/analyze-benchmark.py {prefix}benchmarks/results/latest.json`\n"
        + f"- `python3 {script_prefix}/team-init.py --root . --mode optional`\n"
        + f"- `python3 {script_prefix}/learnings.py init --root .`\n"
        + f"- `python3 {script_prefix}/learning-agent.py search --tags sonar,java --limit 3`\n"
        + f"- `python3 {script_prefix}/learning-refresh.py recommend --root .`\n"
        + f"- `python3 {script_prefix}/graph-learning.py search --changed path/to/file --tags sonar,java`\n"
        + f"- `python3 {prefix}hooks/learning-capture-hook.py \"Fixed validator complexity\" --candidate \"Extract named guard methods while preserving validation order.\"`\n"
        + f"- `python3 {script_prefix}/review-graph.py --changed path/to/file`\n"
        + f"- `python3 {script_prefix}/code-graph-mapper.py map --changed path/to/file`\n"
        + f"- `python3 {script_prefix}/token-auto.py \"review this diff\"`\n"
        + f"- `python3 {script_prefix}/token-savings.py estimate --used {prefix}context/slices.md --avoided {prefix}ROADMAP.md {prefix}USER-GUIDE.md`\n"
        + f"- `python3 {script_prefix}/route-context.py review`\n"
        + f"- `python3 {script_prefix}/aidlc-init.py --root . --depth standard`\n"
        + f"- `python3 {script_prefix}/aidlc-check.py --root .`\n"
        + f"- `python3 {prefix}hooks/tailtrail-lifecycle-hook.py \"use AIDLC and review\"`\n"
    )


def write_copilot(destination: Path, pack_dir: Path | None, force: bool, written: list[str], skipped: list[str]) -> None:
    if destination.exists() and not force:
        skipped.append(destination.as_posix())
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(copilot_body(pack_dir), encoding="utf-8")
    written.append(destination.as_posix())


def main() -> int:
    parser = argparse.ArgumentParser(description="Install TailTrail GitHub Copilot support into a target project.")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Target project root.")
    parser.add_argument("--with-tailtrail-pack", action="store_true", help="Copy TailTrail support docs, templates, context, AIDLC, and scripts.")
    parser.add_argument("--pack-dir", default="tailtrail", help="Folder for TailTrail support files when --with-tailtrail-pack is used. Use '.' for root layout.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing target files.")
    args = parser.parse_args()

    target_root = args.root.resolve()
    pack_dir = validate_pack_dir(args.pack_dir) if args.with_tailtrail_pack else None
    pack_root = target_root / pack_dir if pack_dir is not None else target_root
    written: list[str] = []
    skipped: list[str] = []

    write_copilot(
        target_root / ".github" / "copilot-instructions.md",
        pack_dir,
        args.force,
        written,
        skipped,
    )

    if args.with_tailtrail_pack:
        for relative_path in PACK_FILES:
            copy_file(ROOT / relative_path, pack_root / relative_path, args.force, written, skipped)
        for relative_path in PACK_DIRS:
            copy_dir(ROOT / relative_path, pack_root / relative_path, args.force, written, skipped)
        for relative_path in PACK_SCRIPTS:
            copy_file(ROOT / relative_path, pack_root / relative_path, args.force, written, skipped)
        write_manifest(pack_root, pack_dir, written)

    print(f"TailTrail Copilot setup target: {target_root}")
    if pack_dir is not None:
        print(f"TailTrail pack folder: {(target_root / pack_dir).resolve()}")
    if written:
        print("Written:")
        for path in written:
            print(f"- {path}")
    if skipped:
        print("Skipped existing files:")
        for path in skipped:
            print(f"- {path}")
    print("Next: review the files, then commit them in the target project.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
