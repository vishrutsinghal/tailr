#!/usr/bin/env python3
"""Bounded, configuration-aware repository module resolution.

The resolver is intentionally static and dependency-free.  It understands the
repository-local parts of JavaScript and TypeScript resolution that Navigator
can safely use before a Planning Lock: relative references, ``baseUrl``,
``paths`` aliases, and repository-local ``extends`` chains.  It never executes
project configuration or resolves packages from dependency directories.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


SOURCE_SUFFIXES = (".ts", ".tsx", ".mts", ".cts", ".js", ".jsx", ".mjs", ".cjs", ".json")
CONFIG_PATTERN = re.compile(r"^(?:tsconfig|jsconfig)(?:\.[A-Za-z0-9_-]+)*\.json$")


@dataclass(frozen=True)
class ModuleResolutionLimits:
    max_config_files: int = 16
    max_config_bytes: int = 262_144
    max_extends_depth: int = 8
    max_alias_targets: int = 16


@dataclass(frozen=True)
class AliasRule:
    pattern: str
    targets: tuple[str, ...]
    base_directory: Path
    config_path: str


@dataclass(frozen=True)
class ResolutionResult:
    state: str
    candidates: tuple[str, ...]
    reason_codes: tuple[str, ...]
    config_paths: tuple[str, ...] = ()
    profile: str = "javascript-typescript"

    def as_dict(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "candidates": list(self.candidates),
            "reason_codes": list(self.reason_codes),
            "config_paths": list(self.config_paths),
            "profile": self.profile,
        }


@dataclass(frozen=True)
class _ConfigProfile:
    alias_rules: tuple[AliasRule, ...]
    base_directories: tuple[tuple[Path, str], ...]
    config_paths: tuple[str, ...]
    reason_codes: tuple[str, ...]


def _strip_json_comments_and_trailing_commas(text: str) -> str:
    """Convert the bounded JSONC subset used by tsconfig/jsconfig to JSON."""
    output: list[str] = []
    index = 0
    in_string = False
    escaped = False
    while index < len(text):
        char = text[index]
        following = text[index + 1] if index + 1 < len(text) else ""
        if in_string:
            output.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            index += 1
            continue
        if char == '"':
            in_string = True
            output.append(char)
            index += 1
            continue
        if char == "/" and following == "/":
            index += 2
            while index < len(text) and text[index] not in "\r\n":
                index += 1
            continue
        if char == "/" and following == "*":
            index += 2
            while index + 1 < len(text) and text[index:index + 2] != "*/":
                index += 1
            index = min(len(text), index + 2)
            continue
        output.append(char)
        index += 1
    return re.sub(r",\s*([}\]])", r"\1", "".join(output))


class RepositoryModuleResolver:
    """Resolve repository-local module references with typed evidence."""

    def __init__(
        self,
        root: Path,
        known_paths: Iterable[str],
        *,
        limits: ModuleResolutionLimits = ModuleResolutionLimits(),
    ) -> None:
        self.root = root.resolve()
        self.known_paths = frozenset(PurePosixPath(str(path)).as_posix() for path in known_paths)
        self.limits = limits
        self._profiles: dict[str, _ConfigProfile] = {}
        self._config_reads = 0
        self._config_bytes = 0
        self._config_candidates = tuple(
            sorted(
                path for path in self.known_paths
                if CONFIG_PATTERN.match(PurePosixPath(path).name)
            )
        )

    def diagnostics(self) -> dict[str, Any]:
        """Return source-free bounded configuration-read diagnostics."""
        return {
            "files_read": self._config_reads,
            "bytes_read": self._config_bytes,
            "limits": {
                "max_config_files": self.limits.max_config_files,
                "max_config_bytes": self.limits.max_config_bytes,
                "max_extends_depth": self.limits.max_extends_depth,
                "max_alias_targets": self.limits.max_alias_targets,
            },
        }

    def resolve(self, importer: str, reference: str, kind: str = "import") -> ResolutionResult:
        raw = reference.replace("\\", "/").strip()
        suffix = PurePosixPath(importer).suffix.casefold()
        if suffix not in SOURCE_SUFFIXES[:-1]:
            return ResolutionResult("not-applicable", (), ("module-resolution-profile-not-applicable",))
        if not raw:
            return ResolutionResult("unresolved", (), ("module-reference-empty",))
        if kind == "loader" or raw.startswith(("./", "../", "/")):
            base = PurePosixPath(importer).parent
            candidate = PurePosixPath(raw.lstrip("/")) if raw.startswith("/") else base / raw
            resolved, reasons = self._resolve_candidate(self.root / candidate.as_posix())
            state = "resolved" if len(resolved) == 1 else "ambiguous" if len(resolved) > 1 else "unresolved"
            code = "relative-module-reference-resolved" if state == "resolved" else "relative-module-reference-unresolved"
            return ResolutionResult(state, tuple(resolved), tuple(dict.fromkeys([code, *reasons])))

        profiles = self._applicable_profiles(importer)
        if not profiles:
            return ResolutionResult("unresolved", (), ("module-alias-config-missing",))

        candidates: list[str] = []
        reasons: list[str] = []
        config_paths: list[str] = []
        matched_alias = False
        for profile in profiles:
            reasons.extend(profile.reason_codes)
            config_paths.extend(profile.config_paths)
            rules = self._matching_rules(profile.alias_rules, raw)
            if rules:
                matched_alias = True
                for rule, wildcard in rules:
                    for target in rule.targets[: self.limits.max_alias_targets]:
                        substituted = target.replace("*", wildcard) if "*" in target else target
                        resolved, failure_reasons = self._resolve_candidate(rule.base_directory / substituted)
                        candidates.extend(resolved)
                        reasons.extend(failure_reasons)
            else:
                for base_directory, _ in profile.base_directories:
                    resolved, failure_reasons = self._resolve_candidate(base_directory / raw)
                    candidates.extend(resolved)
                    reasons.extend(failure_reasons)

        unique = tuple(sorted(dict.fromkeys(candidates)))
        if len(unique) == 1:
            reasons.append("module-alias-reference-resolved" if matched_alias else "module-base-url-reference-resolved")
            return ResolutionResult(
                "resolved", unique, tuple(sorted(dict.fromkeys(reasons))),
                tuple(sorted(dict.fromkeys(config_paths))),
            )
        if len(unique) > 1:
            reasons.append("module-alias-ambiguous")
            return ResolutionResult(
                "ambiguous", unique, tuple(sorted(dict.fromkeys(reasons))),
                tuple(sorted(dict.fromkeys(config_paths))),
            )
        reasons.append("module-alias-unresolved" if matched_alias else "module-base-url-unresolved")
        return ResolutionResult(
            "unresolved", (), tuple(sorted(dict.fromkeys(reasons))),
            tuple(sorted(dict.fromkeys(config_paths))),
        )

    def _applicable_profiles(self, importer: str) -> list[_ConfigProfile]:
        importer_parent = PurePosixPath(importer).parent
        ranked: list[tuple[int, str]] = []
        for config_path in self._config_candidates:
            parent = PurePosixPath(config_path).parent
            try:
                importer_parent.relative_to(parent)
            except ValueError:
                continue
            # Prefer the nearest configuration, but retain sibling project
            # configs (for example tsconfig.app.json) at that same boundary.
            ranked.append((-len(parent.parts), config_path))
        if not ranked:
            return []
        nearest_depth = min(value[0] for value in ranked)
        paths = [
            path for depth, path in sorted(ranked)
            if depth == nearest_depth
        ][: self.limits.max_config_files]
        profiles: list[_ConfigProfile] = []
        for path in paths:
            profile = self._load_profile(path, (), 0)
            if profile.alias_rules or profile.base_directories or profile.reason_codes:
                profiles.append(profile)
        return profiles

    def _load_profile(self, relative: str, stack: tuple[str, ...], depth: int) -> _ConfigProfile:
        if relative in self._profiles:
            return self._profiles[relative]
        if relative in stack:
            return _ConfigProfile((), (), tuple((*stack, relative)), ("module-alias-config-cycle",))
        if depth > self.limits.max_extends_depth:
            return _ConfigProfile((), (), (relative,), ("module-alias-extends-depth-exceeded",))
        if self._config_reads >= self.limits.max_config_files:
            return _ConfigProfile((), (), (relative,), ("module-alias-config-file-limit-reached",))
        config = self.root / relative
        try:
            resolved_config = config.resolve(strict=True)
            resolved_config.relative_to(self.root)
            size = resolved_config.stat().st_size
            if size > self.limits.max_config_bytes or self._config_bytes + size > self.limits.max_config_bytes:
                raise ValueError("config byte limit")
            body = resolved_config.read_text(encoding="utf-8")
            payload = json.loads(_strip_json_comments_and_trailing_commas(body))
            if not isinstance(payload, dict):
                raise ValueError("configuration is not an object")
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
            return _ConfigProfile((), (), (relative,), ("module-alias-config-invalid",))
        self._config_reads += 1
        self._config_bytes += size

        parent_profile = _ConfigProfile((), (), (), ())
        extends = payload.get("extends")
        if extends is not None:
            parent_path, failure = self._extends_path(relative, extends)
            if failure:
                parent_profile = _ConfigProfile((), (), (relative,), (failure,))
            elif parent_path:
                parent_profile = self._load_profile(parent_path, (*stack, relative), depth + 1)

        compiler = payload.get("compilerOptions", {})
        if not isinstance(compiler, dict):
            compiler = {}
        config_directory = (self.root / PurePosixPath(relative).parent).resolve()
        base_url = compiler.get("baseUrl")
        local_base: Path | None = None
        reasons = list(parent_profile.reason_codes)
        if isinstance(base_url, str):
            local_base, failure = self._safe_directory(config_directory / base_url)
            if failure:
                reasons.append(failure)
        inherited_bases = list(parent_profile.base_directories)
        bases = [(local_base, relative)] if local_base else inherited_bases

        inherited_rules = {rule.pattern: rule for rule in parent_profile.alias_rules}
        paths = compiler.get("paths")
        if isinstance(paths, dict):
            rule_base = local_base or config_directory
            for pattern, values in paths.items():
                if not isinstance(pattern, str) or pattern.count("*") > 1:
                    reasons.append("module-alias-pattern-unsupported")
                    continue
                if not isinstance(values, list) or not values or not all(isinstance(value, str) for value in values):
                    reasons.append("module-alias-target-invalid")
                    continue
                inherited_rules[pattern] = AliasRule(pattern, tuple(values), rule_base, relative)
        if paths is not None and not isinstance(paths, dict):
            reasons.append("module-alias-paths-invalid")
        reasons.append("module-alias-config-resolved")
        profile = _ConfigProfile(
            tuple(inherited_rules[key] for key in sorted(inherited_rules)),
            tuple(bases),
            tuple(dict.fromkeys((*parent_profile.config_paths, relative))),
            tuple(sorted(dict.fromkeys(reasons))),
        )
        self._profiles[relative] = profile
        return profile

    def _extends_path(self, config_path: str, value: Any) -> tuple[str | None, str | None]:
        if not isinstance(value, str) or not value.startswith("."):
            return None, "module-alias-extends-unsupported"
        parent = PurePosixPath(config_path).parent / value
        variants = [parent] if parent.suffix else [parent, PurePosixPath(str(parent) + ".json")]
        for variant in variants:
            normalized = self._safe_relative(self.root / variant.as_posix())
            if normalized and normalized in self.known_paths:
                return normalized, None
        if self._safe_relative(self.root / parent.as_posix()) is None:
            return None, "module-alias-target-outside-root"
        return None, "module-alias-extends-unresolved"

    @staticmethod
    def _matching_rules(rules: tuple[AliasRule, ...], reference: str) -> list[tuple[AliasRule, str]]:
        matches: list[tuple[int, AliasRule, str]] = []
        for rule in rules:
            if "*" not in rule.pattern:
                if rule.pattern == reference:
                    matches.append((len(rule.pattern) + 10_000, rule, ""))
                continue
            prefix, suffix = rule.pattern.split("*", 1)
            if reference.startswith(prefix) and reference.endswith(suffix) and len(reference) >= len(prefix) + len(suffix):
                wildcard = reference[len(prefix): len(reference) - len(suffix) if suffix else None]
                matches.append((len(prefix) + len(suffix), rule, wildcard))
        if not matches:
            return []
        best = max(score for score, _, _ in matches)
        return [(rule, wildcard) for score, rule, wildcard in matches if score == best]

    def _safe_directory(self, candidate: Path) -> tuple[Path | None, str | None]:
        try:
            resolved = candidate.resolve()
            resolved.relative_to(self.root)
            return resolved, None
        except (OSError, ValueError):
            return None, "module-alias-target-outside-root"

    def _safe_relative(self, candidate: Path) -> str | None:
        try:
            return candidate.resolve().relative_to(self.root).as_posix()
        except (OSError, ValueError):
            return None

    def _resolve_candidate(self, candidate: Path) -> tuple[list[str], list[str]]:
        safe_base = self._safe_relative(candidate)
        if safe_base is None:
            return [], ["module-alias-target-outside-root"]
        base = self.root / safe_base
        variants = [base]
        if not PurePosixPath(safe_base).suffix:
            variants.extend(Path(str(base) + suffix) for suffix in SOURCE_SUFFIXES)
            variants.extend(base / ("index" + suffix) for suffix in SOURCE_SUFFIXES)
        resolved: list[str] = []
        reasons: list[str] = []
        for variant in variants:
            relative = self._safe_relative(variant)
            if relative is None:
                reasons.append("module-alias-target-outside-root")
                continue
            if relative in self.known_paths:
                resolved.append(relative)
        return sorted(dict.fromkeys(resolved)), reasons
