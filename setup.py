from __future__ import annotations

import hashlib
import gzip
import json
import os
import shutil
import tarfile
from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py as _build_py
from setuptools.command.sdist import sdist as _sdist


ROOT = Path(__file__).resolve().parent
MANIFEST = json.loads((ROOT / "package-manifest.json").read_text(encoding="utf-8"))


def package_sources() -> list[tuple[str, Path]]:
    excluded_names = set(MANIFEST["excluded_names"])
    excluded_suffixes = tuple(MANIFEST["excluded_suffixes"])
    selected: dict[str, Path] = {}
    for relative in MANIFEST["required_files"]:
        source = ROOT / relative
        if source.is_symlink() or not source.is_file():
            raise RuntimeError(f"package manifest required file is missing: {relative}")
        selected[relative] = source
    for relative in MANIFEST["required_directories"]:
        directory = ROOT / relative
        if not directory.is_dir():
            raise RuntimeError(f"package manifest required directory is missing: {relative}")
        for source in directory.rglob("*"):
            if source.is_symlink():
                raise RuntimeError(f"package resources may not contain symbolic links: {source.relative_to(ROOT).as_posix()}")
            if not source.is_file():
                continue
            path = source.relative_to(ROOT)
            if excluded_names.intersection(path.parts) or source.suffix in excluded_suffixes:
                continue
            selected[path.as_posix()] = source
    return sorted(selected.items())


class TailTrailBuildPy(_build_py):
    def run(self) -> None:
        super().run()
        package_root = Path(self.build_lib) / "tailtrail"
        inventory: dict[str, str] = {}
        for relative, source in package_sources():
            destination = package_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            inventory[relative] = hashlib.sha256(destination.read_bytes()).hexdigest()
        integrity = {
            "schema_version": "1",
            "algorithm": "sha256",
            "files": inventory,
        }
        (package_root / "package-integrity.json").write_text(
            json.dumps(integrity, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


def normalize_sdist(path: Path, epoch: int) -> None:
    temporary = path.with_name(path.name + ".normalized")
    with tarfile.open(path, "r:gz") as source:
        members = sorted(source.getmembers(), key=lambda item: item.name)
        with temporary.open("wb") as raw:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=9, mtime=epoch) as compressed:
                with tarfile.open(fileobj=compressed, mode="w", format=tarfile.GNU_FORMAT) as target:
                    for member in members:
                        data = source.extractfile(member) if member.isfile() else None
                        member.mtime = epoch
                        member.uid = 0
                        member.gid = 0
                        member.uname = ""
                        member.gname = ""
                        member.pax_headers = {}
                        target.addfile(member, data)
    temporary.replace(path)


class TailTrailSdist(_sdist):
    def run(self) -> None:
        super().run()
        epoch = int(os.environ.get("SOURCE_DATE_EPOCH", "0"))
        for value in self.archive_files:
            path = Path(value)
            if path.name.endswith(".tar.gz"):
                normalize_sdist(path, epoch)


setup(cmdclass={"build_py": TailTrailBuildPy, "sdist": TailTrailSdist})
