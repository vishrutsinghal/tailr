#!/usr/bin/env python3
"""Install a pinned official AWS AI-DLC rules pack into one project.

The installer deliberately downloads a specific release archive rather than a
branch.  It extracts only the published rules, records hashes for every file,
and leaves Full mode disabled unless the resulting manifest validates.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OFFICIAL_SOURCE = "https://github.com/awslabs/aidlc-workflows"
DEFAULT_REVISION = "v1.0.1"
DEFAULT_COMMIT = "e49341d"
ARCHIVE_PREFIX = "aidlc-rules/"


def release_urls(revision: str) -> tuple[str, str]:
    if not revision.startswith("v"):
        raise ValueError("revision must be a published version tag such as v1.0.1")
    version = revision[1:]
    base = f"{OFFICIAL_SOURCE}/releases/download/{revision}/ai-dlc-rules-v{version}.zip"
    license_url = f"https://raw.githubusercontent.com/awslabs/aidlc-workflows/{revision}/LICENSE"
    return base, license_url


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "TailTrail-official-aidlc-installer/1"})
    with urllib.request.urlopen(request, timeout=60) as response:  # nosec B310: fixed official HTTPS source
        return response.read()


def safe_member(name: str) -> PurePosixPath | None:
    path = PurePosixPath(name)
    if not name.startswith(ARCHIVE_PREFIX) or name.endswith("/"):
        return None
    relative = PurePosixPath(*path.parts[1:])
    if not relative.parts or relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"official archive contains an unsafe path: {name}")
    return relative


def extract_rules(archive: Path, destination: Path) -> list[str]:
    extracted: list[str] = []
    with zipfile.ZipFile(archive) as bundle:
        for member in bundle.infolist():
            relative = safe_member(member.filename)
            if relative is None:
                continue
            target = destination.joinpath(*relative.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            with bundle.open(member) as source, target.open("wb") as output:
                shutil.copyfileobj(source, output)
            extracted.append(relative.as_posix())
    required = "aws-aidlc-rules/core-workflow.md"
    if required not in extracted:
        raise ValueError(f"official archive is missing `{required}`")
    return sorted(extracted)


def write_manifest(destination: Path, revision: str, files: list[str], host: str, *, commit: str | None = None) -> Path:
    manifest = {
        "schema_version": "1",
        "type": "tailtrail-official-aidlc-pack",
        "official": {
            "source": OFFICIAL_SOURCE,
            "revision": revision,
            "commit": commit or "",
            "license": {"spdx": "MIT-0", "file": "LICENSE"},
        },
        "host_adapter": {"host": host, "rules_path": "aws-aidlc-rules/core-workflow.md"},
        "integrity": {
            "algorithm": "sha256",
            "files": [
                {"path": path, "sha256": sha256_bytes((destination / path).read_bytes())}
                for path in sorted(files)
            ],
        },
    }
    path = destination / "manifest.json"
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return path


def install(root: Path, *, revision: str, host: str, archive_bytes: bytes, license_bytes: bytes, commit: str | None = None, dry_run: bool = False) -> dict[str, Any]:
    root = root.resolve()
    destination = root / ".tailtrail" / "official-aidlc"
    if destination.exists():
        raise ValueError(f"official AI-DLC destination already exists: {destination}. Validate it with `tailtrail aidlc official status --root .`; do not overwrite a pinned pack.")
    if not archive_bytes.startswith(b"PK"):
        raise ValueError("downloaded official AI-DLC archive is not a ZIP file")
    if not license_bytes.strip():
        raise ValueError("downloaded official AI-DLC license is empty")
    plan = {
        "type": "tailtrail-official-aidlc-install",
        "root": root.as_posix(),
        "destination": destination.relative_to(root).as_posix(),
        "official_source": OFFICIAL_SOURCE,
        "revision": revision,
        "commit": commit or "",
        "host": host,
        "archive_sha256": sha256_bytes(archive_bytes),
        "license_sha256": sha256_bytes(license_bytes),
        "dry_run": dry_run,
    }
    if dry_run:
        return {**plan, "state": "planned"}
    with tempfile.TemporaryDirectory(prefix="tailtrail-aidlc-") as temp:
        work = Path(temp)
        archive = work / "official-aidlc.zip"
        stage = work / "official-aidlc"
        archive.write_bytes(archive_bytes)
        files = extract_rules(archive, stage)
        (stage / "LICENSE").write_bytes(license_bytes)
        files.append("LICENSE")
        write_manifest(stage, revision, files, host, commit=commit)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(stage.as_posix(), destination.as_posix())
    return {**plan, "state": "installed", "manifest": (destination / "manifest.json").relative_to(root).as_posix(), "file_count": len(files)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Target project root.")
    parser.add_argument("--revision", default=DEFAULT_REVISION, help="Pinned official release tag (default: v1.0.1).")
    parser.add_argument("--host", choices=("codex", "copilot", "claude", "generic"), default="generic", help="Host that will consume the installed rules.")
    parser.add_argument("--dry-run", action="store_true", help="Verify inputs and show the installation target without writing it.")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    args = parser.parse_args()
    try:
        archive_url, license_url = release_urls(args.revision)
        archive = fetch(archive_url)
        license_text = fetch(license_url)
        commit = DEFAULT_COMMIT if args.revision == DEFAULT_REVISION else None
        result = install(args.root, revision=args.revision, host=args.host, archive_bytes=archive, license_bytes=license_text, commit=commit, dry_run=args.dry_run)
    except (OSError, ValueError, urllib.error.URLError, zipfile.BadZipFile) as error:
        print(f"Official AI-DLC install error: {error}")
        return 2
    if args.format == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print("# TailTrail Official AI-DLC Install")
        print()
        print(f"**State:** `{result['state']}`")
        print(f"**Release:** `{result['revision']}`" + (f" (`{result['commit']}`)" if result["commit"] else ""))
        print(f"**Host:** `{result['host']}`")
        print(f"**Destination:** `{result['destination']}`")
        print(f"**Archive SHA-256:** `{result['archive_sha256']}`")
        if result["state"] == "installed":
            print(f"**Verified files:** `{result['file_count']}`")
            print()
            print(f"Next: `tailtrail aidlc official status --root {args.root}`")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
