#!/usr/bin/env python3
"""Typed, deterministic repository-scope evidence for Navigator.

NS-2 deliberately separates cheap discovery from scope meaning. Discovery
produces :class:`ScopeSeed` values; this module validates their paths, assigns a
repository role, and emits candidates with an explicit status and provenance.
Lexical evidence is weak by construction and never establishes an
implementation owner on its own.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import subprocess
import unicodedata
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

import capture_hooks
import code_relationships
import requirement_discovery
from code_graph_inventory import snapshot as inventory_snapshot
from module_resolution import RepositoryModuleResolver, ResolutionResult


SCHEMA_VERSION = "2"
EVIDENCE_TYPE = "tailtrail-navigator-scope-evidence"
SCOPE_POLICY_TYPE = "tailtrail-navigator-scope-release-policy"
SCOPE_POLICY_VERSION = "1"
SCOPE_POLICY_PATH = Path(".tailtrail/navigator-scope-policy-v1.json")
SCOPE_POLICY_ENV = "TAILTRAIL_NAVIGATOR_SCOPE_V2"
SCOPE_AVAILABLE = "available"
SCOPE_UNAVAILABLE = "scope-investigation-unavailable"

@dataclass(frozen=True)
class InvestigationLimits:
    """Deterministic pre-lock read and relationship budget."""

    candidate_files: int = 10_000
    initial_file_reads: int = 20
    escalation_file_reads: int = 12
    cache_validation_file_reads: int = 12
    relationship_file_reads: int = 8
    max_file_bytes: int = 262_144
    max_total_read_bytes: int = 3_145_728
    max_cache_validation_bytes: int = 1_048_576
    relationship_hops: int = 2
    retained_owners: int = 10
    scope_question_options: int = 3

    def as_dict(self) -> dict[str, int]:
        return {
            "candidate_files": self.candidate_files,
            "initial_file_reads": self.initial_file_reads,
            "escalation_file_reads": self.escalation_file_reads,
            "cache_validation_file_reads": self.cache_validation_file_reads,
            "relationship_file_reads": self.relationship_file_reads,
            "max_file_bytes": self.max_file_bytes,
            "max_total_read_bytes": self.max_total_read_bytes,
            "max_cache_validation_bytes": self.max_cache_validation_bytes,
            "relationship_hops": self.relationship_hops,
            "retained_owners": self.retained_owners,
            "scope_question_options": self.scope_question_options,
        }


DEFAULT_LIMITS = InvestigationLimits()
# Compatibility projection used by NS-2 callers. New investigation code takes
# an explicit immutable InvestigationLimits value so tests can reduce budgets.
LIMITS: dict[str, int] = DEFAULT_LIMITS.as_dict()

ROLES = {
    "implementation-owner",
    "caller",
    "literal-emitter",
    "test",
    "configuration",
    "manifest",
    "documentation",
    "reference",
    "generated",
    "managed-tooling",
    "unknown",
}

@dataclass(frozen=True)
class WorkerContract:
    """Permission boundary for a specific pipeline stage."""
    allowed_write_roles: set[str]
    prohibited_write_roles: set[str]
    read_access: str = "all"

WORKER_CONTRACTS = {
    "IMPLEMENTATION": WorkerContract(
        allowed_write_roles={"implementation-owner", "supporting-assets"},
        prohibited_write_roles={"test", "managed-tooling"},
    ),
    "TESTING": WorkerContract(
        allowed_write_roles={"test"},
        prohibited_write_roles={"implementation-owner", "supporting-assets"},
    ),
    "INFRA": WorkerContract(
        allowed_write_roles={"configuration", "manifest"},
        prohibited_write_roles={"implementation-owner", "test"},
    ),
}
STATUSES = {"included", "inspection-only", "proof-only", "excluded", "rejected"}
SEED_SOURCES = {
    "explicit-path",
    "fresh-graph",
    "git-change",
    "host-diagnosis",
    "lexical-body",
    "lexical-path",
    "module-name",
    "repository-structure",
    "saved-graph",
    "symbol-name",
}

SOURCE_SUFFIXES = {
    ".c", ".cc", ".cpp", ".cs", ".css", ".go", ".h", ".hpp", ".html",
    ".java", ".js", ".jsx", ".kt", ".kts", ".php", ".py", ".rb", ".rs",
    ".scala", ".scss", ".sh", ".sql", ".svelte", ".swift", ".tf", ".ts",
    ".tsx", ".vue",
}
DOCUMENT_SUFFIXES = {".adoc", ".md", ".mdx", ".rst"}
CONFIG_SUFFIXES = {".cfg", ".conf", ".ini", ".properties", ".toml", ".yaml", ".yml"}
MANIFEST_NAMES = {
    "build.gradle", "build.gradle.kts", "cargo.toml", "composer.json", "deno.json",
    "deno.jsonc", "directory.build.props", "directory.build.targets", "dockerfile",
    "gemfile", "go.mod", "makefile", "package.json", "pom.xml", "pyproject.toml",
    "requirements.txt", "setup.cfg", "setup.py",
}
TEST_PARTS = {"__tests__", "spec", "specs", "test", "tests"}
DOCUMENT_PARTS = {"doc", "docs", "documentation", "example", "examples"}
CONFIG_PARTS = {".github", ".gitlab", "config", "configs", "configuration"}
GENERATED_PARTS = {
    ".cache", ".gradle", ".next", ".nuxt", ".pytest_cache", ".tox", ".venv",
    "__pycache__", "bin", "build", "coverage", "dist", "generated", "node_modules",
    "obj", "out", "target", "venv",
}
VENDOR_PARTS = {"deps", "third_party", "third-party", "vendor"}
SENSITIVE_EXACT_NAMES = {
    ".env", ".npmrc", ".pypirc", "credentials", "credentials.json", "id_dsa",
    "id_ecdsa", "id_ed25519", "id_rsa", "known_hosts", "netrc", "secrets.json",
}
SENSITIVE_SUFFIXES = {".cer", ".crt", ".der", ".jks", ".key", ".p12", ".pem", ".pfx"}
SENSITIVE_STEMS = {"credential", "credentials", "private-key", "private_key", "secret", "secrets"}
WINDOWS_ABSOLUTE = re.compile(r"^[A-Za-z]:[/\\]")

# These terms remain useful for bounded read ordering, but are too common or
# too structural to establish implementation ownership. Ownership matching is
# limited to behavior-specific terms against a local basename or a definition.
LOW_SIGNAL_OWNER_TERMS = {
    "add", "app", "application", "banner", "bug", "change", "click",
    "component", "components", "create", "debug", "display", "dom", "file",
    "fix", "implement", "issue", "lib", "module", "move", "page", "pages",
    "push", "remove", "render", "service", "services", "show", "source",
    "src", "test", "tests", "update", "user", "view",
}
GENERIC_PATH_SEGMENTS = {
    "app", "apps", "component", "components", "config", "configs", "lib",
    "libs", "page", "pages", "service", "services", "source", "src", "test",
    "tests", "util", "utils",
}
UI_REQUEST_TERMS = {
    "frontend", "interface", "page", "screen", "ui", "view",
}
UI_PATH_SEGMENTS = {
    "client", "component", "components", "frontend", "page", "pages", "route",
    "routes", "screen", "screens", "ui", "view", "views",
}
UI_SOURCE_SUFFIXES = {".css", ".html", ".jsx", ".scss", ".svelte", ".tsx", ".vue"}
OWNER_QUALIFICATION_PRECEDENCE = (
    "explicit-user-scope",
    "ui-renderer-behavior",
    "task-specific-behavior",
    "unique-exact-literal",
    "task-specific-relationship",
    "definition-with-edges",
    "ambiguous-definition-fork",
)
BEHAVIOR_CHAIN_LINE_SPAN = 160
SCOPE_QUESTION_OPTION_CAP = 3


def canonical_bytes(value: Any) -> bytes:
    """Return the product-wide stable JSON representation used for hashes."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def fingerprint(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_bytes(value)).hexdigest()


def _scope_policy_unsigned(value: dict[str, Any]) -> dict[str, Any]:
    return {key: nested for key, nested in value.items() if key != "integrity"}


def seal_scope_policy(state: str, reason_code: str) -> dict[str, Any]:
    """Build the closed, integrity-bound release kill-switch document."""
    if state not in {SCOPE_AVAILABLE, SCOPE_UNAVAILABLE}:
        raise ValueError("scope release policy state is invalid")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{2,63}", reason_code):
        raise ValueError("scope release policy reason code is invalid")
    policy: dict[str, Any] = {
        "schema_version": SCOPE_POLICY_VERSION,
        "type": SCOPE_POLICY_TYPE,
        "state": state,
        "reason_code": reason_code,
        "fallback": "none",
        "boundary": "Start fails closed before repository investigation or Planning Lock persistence; lexical-only scope is never restored.",
    }
    policy["integrity"] = {
        "algorithm": "sha256",
        "canonicalization": "sorted compact JSON excluding integrity",
        "digest": fingerprint(_scope_policy_unsigned(policy)),
    }
    return policy


def validate_scope_policy(value: Any) -> dict[str, Any]:
    """Validate a policy without treating malformed configuration as enabled."""
    expected = {"schema_version", "type", "state", "reason_code", "fallback", "boundary", "integrity"}
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError("scope release policy contract is not closed")
    if value["schema_version"] != SCOPE_POLICY_VERSION or value["type"] != SCOPE_POLICY_TYPE:
        raise ValueError("scope release policy identity is invalid")
    if value["state"] not in {SCOPE_AVAILABLE, SCOPE_UNAVAILABLE} or value["fallback"] != "none":
        raise ValueError("scope release policy state is invalid")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{2,63}", str(value["reason_code"])):
        raise ValueError("scope release policy reason code is invalid")
    integrity = value["integrity"]
    if not isinstance(integrity, dict) or set(integrity) != {"algorithm", "canonicalization", "digest"}:
        raise ValueError("scope release policy integrity is invalid")
    if integrity["algorithm"] != "sha256" or integrity["canonicalization"] != "sorted compact JSON excluding integrity":
        raise ValueError("scope release policy integrity is invalid")
    if integrity["digest"] != fingerprint(_scope_policy_unsigned(value)):
        raise ValueError("scope release policy digest mismatch")
    return value


def scope_release_status(root: Path, environ: dict[str, str] | None = None) -> dict[str, Any]:
    """Resolve the v2 release switch. Invalid configuration always fails closed.

    The environment override is intentionally one-way: it may disable the
    investigation in an emergency, but cannot override a disabled repository
    policy back to available.
    """
    environment = os.environ if environ is None else environ
    env_value = str(environment.get(SCOPE_POLICY_ENV, "")).strip().lower()
    if env_value and env_value not in {SCOPE_AVAILABLE, SCOPE_UNAVAILABLE, "disabled"}:
        return {
            "state": SCOPE_UNAVAILABLE,
            "source": "invalid-environment",
            "reason_code": "invalid-release-override",
            "policy_path": SCOPE_POLICY_PATH.as_posix(),
            "fallback": "none",
        }
    if env_value in {SCOPE_UNAVAILABLE, "disabled"}:
        return {
            "state": SCOPE_UNAVAILABLE,
            "source": "environment",
            "reason_code": "release-kill-switch",
            "policy_path": SCOPE_POLICY_PATH.as_posix(),
            "fallback": "none",
        }
    path = root / SCOPE_POLICY_PATH
    if not path.is_file():
        return {"state": SCOPE_AVAILABLE, "source": "default", "reason_code": "v2-default", "policy_path": SCOPE_POLICY_PATH.as_posix(), "fallback": "none"}
    try:
        policy = validate_scope_policy(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError, ValueError):
        return {"state": SCOPE_UNAVAILABLE, "source": "invalid-policy", "reason_code": "invalid-release-policy", "policy_path": SCOPE_POLICY_PATH.as_posix(), "fallback": "none"}
    return {
        "state": policy["state"],
        "source": "repository-policy",
        "reason_code": policy["reason_code"],
        "policy_path": SCOPE_POLICY_PATH.as_posix(),
        "fallback": "none",
    }


def _stable_strings(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted(dict.fromkeys(str(value) for value in values if str(value))))


@dataclass(frozen=True)
class ScopeSeed:
    """A discovery hint. A seed is not an ownership or write-scope decision."""

    path: str
    seed_sources: tuple[str, ...]
    reason_codes: tuple[str, ...]
    matched_terms: tuple[str, ...] = ()
    score: int = 0
    content_fingerprint: str | None = None

    def __post_init__(self) -> None:
        if not self.path:
            raise ValueError("scope seed path must not be empty")
        unknown = set(self.seed_sources) - SEED_SOURCES
        if unknown:
            raise ValueError("unknown scope seed source: " + ", ".join(sorted(unknown)))
        if not self.seed_sources or not self.reason_codes:
            raise ValueError("scope seed requires source and reason evidence")

    def as_dict(self) -> dict[str, Any]:
        row: dict[str, Any] = {
            "path": self.path,
            "seed_sources": list(_stable_strings(self.seed_sources)),
            "reason_codes": list(_stable_strings(self.reason_codes)),
            "matched_terms": list(_stable_strings(self.matched_terms)),
            "score": self.score,
        }
        if self.content_fingerprint:
            row["content_fingerprint"] = self.content_fingerprint
        return row

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ScopeSeed":
        return cls(
            path=str(value.get("path", "")),
            seed_sources=_stable_strings(value.get("seed_sources", [])),
            reason_codes=_stable_strings(value.get("reason_codes", [])),
            matched_terms=_stable_strings(value.get("matched_terms", [])),
            score=int(value.get("score", 0)),
            content_fingerprint=str(value["content_fingerprint"]) if value.get("content_fingerprint") else None,
        )


@dataclass(frozen=True)
class ScopeCandidate:
    """A validated, repository-aware interpretation of one or more seeds."""

    candidate_id: str
    path: str
    role: str
    status: str
    seed_sources: tuple[str, ...]
    evidence_edge_ids: tuple[str, ...]
    confidence: str
    reason_codes: tuple[str, ...]
    evidence_provenance: tuple[dict[str, str], ...]
    content_fingerprint: str | None = None

    def __post_init__(self) -> None:
        if self.role not in ROLES:
            raise ValueError(f"unknown repository role: {self.role}")
        if self.status not in STATUSES:
            raise ValueError(f"unknown scope candidate status: {self.status}")
        if not self.reason_codes or not self.evidence_provenance:
            raise ValueError("scope candidate requires reason codes and evidence provenance")

    def as_dict(self) -> dict[str, Any]:
        row: dict[str, Any] = {
            "candidate_id": self.candidate_id,
            "path": self.path,
            "role": self.role,
            "status": self.status,
            "seed_sources": list(self.seed_sources),
            "evidence_edge_ids": list(self.evidence_edge_ids),
            "confidence": self.confidence,
            "reason_codes": list(self.reason_codes),
            "evidence_provenance": list(self.evidence_provenance),
        }
        if self.content_fingerprint:
            row["content_fingerprint"] = self.content_fingerprint
        return row


def seed(
    path: str,
    source: str,
    reason_code: str,
    *,
    matched_terms: Iterable[str] = (),
    score: int = 0,
    content_fingerprint: str | None = None,
) -> dict[str, Any]:
    return ScopeSeed(
        path=path,
        seed_sources=(source,),
        reason_codes=(reason_code,),
        matched_terms=_stable_strings(matched_terms),
        score=score,
        content_fingerprint=content_fingerprint,
    ).as_dict()


def normalize_repository_path(root: Path, value: str) -> tuple[str | None, str | None]:
    """Normalize a repository-relative path or return a stable rejection code."""
    raw = str(value)
    if not raw or "\x00" in raw:
        return None, "invalid-path"
    if raw.startswith(("/", "\\", "//")) or WINDOWS_ABSOLUTE.match(raw):
        return None, "absolute-path-rejected"
    normalized = unicodedata.normalize("NFC", raw.replace("\\", "/"))
    pure = PurePosixPath(normalized)
    if not pure.parts or any(part in {"", ".", ".."} for part in pure.parts):
        return None, "path-traversal-rejected"
    root_resolved = root.resolve()
    current = root_resolved
    for part in pure.parts:
        current = current / part
        try:
            if current.is_symlink():
                return None, "symlink-rejected"
        except OSError:
            return None, "path-inspection-failed"
    candidate = root_resolved.joinpath(*pure.parts)
    try:
        candidate.resolve(strict=False).relative_to(root_resolved)
    except (OSError, ValueError):
        return None, "out-of-root-rejected"
    return pure.as_posix(), None


def sensitive_path_reason(path: str) -> str | None:
    pure = PurePosixPath(path)
    lowered_parts = [part.lower() for part in pure.parts]
    name = lowered_parts[-1] if lowered_parts else ""
    suffix = PurePosixPath(name).suffix.lower()
    stem = PurePosixPath(name).stem.lower()
    if name in SENSITIVE_EXACT_NAMES or suffix in SENSITIVE_SUFFIXES or stem in SENSITIVE_STEMS:
        return "sensitive-path-rejected"
    if any(part in {".aws", ".gnupg", ".ssh"} for part in lowered_parts):
        return "credential-directory-rejected"
    return None


def safe_text(
    root: Path,
    relative: str,
    *,
    max_bytes: int | None = None,
) -> tuple[str | None, str | None, str | None]:
    """Read a bounded UTF-8 text file without following unsafe paths.

    Returns ``(text, rejection_reason, content_fingerprint)``. The source body
    never enters a scope artifact.
    """
    effective_max_bytes = LIMITS["max_file_bytes"] if max_bytes is None else max_bytes
    normalized, rejection = normalize_repository_path(root, relative)
    if rejection or normalized is None:
        return None, rejection, None
    sensitive = sensitive_path_reason(normalized)
    if sensitive:
        return None, sensitive, None
    path = root.resolve().joinpath(*PurePosixPath(normalized).parts)
    try:
        if not path.is_file():
            return None, "not-a-file", None
        size = path.stat().st_size
        if size > effective_max_bytes:
            return None, "oversized-file-rejected", None
        body = path.read_bytes()
    except OSError:
        return None, "file-read-failed", None
    if len(body) > effective_max_bytes:
        return None, "oversized-file-rejected", None
    if b"\x00" in body:
        return None, "binary-file-rejected", None
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError:
        return None, "non-utf8-file-rejected", None
    return text, None, "sha256:" + hashlib.sha256(body).hexdigest()


def _is_test_path(path: PurePosixPath) -> bool:
    parts = {part.lower() for part in path.parts[:-1]}
    lowered = path.name.lower()
    return bool(
        parts & TEST_PARTS
        or lowered == "conftest.py"
        or lowered.startswith("test_")
        or re.search(r"(?:^|[._-])(test|spec|cy)(?:[._-]|$)", lowered)
        or lowered.endswith("tests.py")
    )


def _managed_pack_root(root: Path, path: PurePosixPath) -> bool:
    lowered = [part.lower() for part in path.parts]
    if len(lowered) >= 4 and lowered[:3] == [".tailtrail", "install", "payload"]:
        return True
    current = root.resolve()
    for part in path.parts[:-1]:
        current = current / part
        if (current / ".tailtrail-install.json").is_file():
            return True
    return (root / ".tailtrail-install.json").is_file()


def _tailtrail_source_checkout(root: Path) -> bool:
    return (
        (root / "tailtrail-registry.json").is_file()
        and (root / "scripts" / "tailtrail.py").is_file()
        and (root / "package-manifest.json").is_file()
    )


def classify_repository_role(root: Path, relative: str) -> tuple[str, tuple[str, ...]]:
    """Assign a repository role without executing project code."""
    path = PurePosixPath(relative)
    parts = {part.lower() for part in path.parts[:-1]}
    lowered_name = path.name.lower()
    suffix = path.suffix.lower()

    if path.parts and path.parts[0].lower() in {".tailtrail", "tailtrail-meta"}:
        return "managed-tooling", ("tailtrail-state-boundary",)
    if _managed_pack_root(root, path):
        return "managed-tooling", ("managed-pack-boundary",)
    if parts & VENDOR_PARTS:
        return "generated", ("vendored-path",)
    if parts & GENERATED_PARTS:
        return "generated", ("generated-or-build-path",)
    if _is_test_path(path):
        return "test", ("test-path-convention",)
    if lowered_name in MANIFEST_NAMES:
        return "manifest", ("manifest-name",)
    if parts & DOCUMENT_PARTS or suffix in DOCUMENT_SUFFIXES:
        return "documentation", ("documentation-path-convention",)
    if (
        parts & CONFIG_PARTS
        or suffix in CONFIG_SUFFIXES
        or lowered_name.startswith(".")
        or re.fullmatch(r"(?:tsconfig|jsconfig)(?:\.[a-z0-9_-]+)*\.json", lowered_name)
    ):
        return "configuration", ("configuration-path-convention",)
    if path.parts and path.parts[0].lower() == "scripts" and _tailtrail_source_checkout(root):
        return "implementation-owner", ("tailtrail-source-checkout-production",)
    if suffix in SOURCE_SUFFIXES:
        return "implementation-owner", ("production-source-suffix",)
    return "unknown", ("unclassified-repository-path",)


def _candidate_status(role: str, sources: tuple[str, ...], task_types: set[str], rejected: bool) -> tuple[str, str, str]:
    if rejected:
        return "rejected", "none", "path-safety-rejection"
    if role in {"generated", "managed-tooling"}:
        return "excluded", "none", "non-application-scope"
    explicit = "explicit-path" in sources
    git_observed = "git-change" in sources
    strong_graph = "fresh-graph" in sources
    if role == "test":
        if "qa" in task_types and not ({"feature", "implementation", "bug", "refactor"} & task_types):
            return "included", "medium", "test-only-task"
        return "proof-only", "medium" if explicit or strong_graph else "low", "test-is-proof-not-owner"
    if role == "documentation":
        if "documentation" in task_types:
            return "included", "high" if explicit else "medium", "documentation-task-role"
        return "excluded", "none", "documentation-not-implementation-scope"
    if explicit:
        return "inspection-only", "high", "explicit-path-owner-candidate"
    if git_observed and role == "implementation-owner":
        return "inspection-only", "medium", "git-change-needs-task-specific-evidence"
    if role == "implementation-owner":
        if strong_graph:
            return "inspection-only", "medium", "graph-seed-needs-task-specific-evidence"
        return "inspection-only", "low", "lexical-seed-needs-relationship-evidence"
    if role in {"configuration", "manifest"}:
        return "inspection-only", "low", "supporting-repository-role"
    return "inspection-only", "low", "unknown-role-needs-investigation"


def candidates_from_seeds(root: Path, seeds: Iterable[dict[str, Any] | ScopeSeed], task_types: Iterable[str] = ()) -> list[dict[str, Any]]:
    """Validate, merge, classify, and deterministically order discovery seeds."""
    grouped: dict[str, list[ScopeSeed]] = {}
    rejected: list[ScopeCandidate] = []
    for raw in seeds:
        item = raw if isinstance(raw, ScopeSeed) else ScopeSeed.from_dict(raw)
        normalized, path_rejection = normalize_repository_path(root, item.path)
        if normalized is None:
            stable_path = unicodedata.normalize("NFC", item.path.replace("\\", "/"))
            sources = _stable_strings(item.seed_sources)
            reasons = _stable_strings((*item.reason_codes, path_rejection or "invalid-path"))
            candidate_key = {"path": stable_path, "role": "unknown", "sources": sources, "reasons": reasons}
            rejected.append(
                ScopeCandidate(
                    candidate_id="cand-" + fingerprint(candidate_key).split(":", 1)[1][:12],
                    path=stable_path,
                    role="unknown",
                    status="rejected",
                    seed_sources=sources,
                    evidence_edge_ids=(),
                    confidence="none",
                    reason_codes=reasons,
                    evidence_provenance=tuple(
                        {"source": source, "strength": "none", "kind": "discovery-seed"}
                        for source in sources
                    ),
                )
            )
            continue
        grouped.setdefault(normalized, []).append(item)

    task_set = {str(value).lower() for value in task_types}
    rows: list[ScopeCandidate] = []
    safety_reads = 0
    safety_bytes = 0
    for path in sorted(grouped):
        items = grouped[path]
        sources = _stable_strings(source for item in items for source in item.seed_sources)
        seed_reasons = _stable_strings(reason for item in items for reason in item.reason_codes)
        sensitive = sensitive_path_reason(path)
        content_hashes = sorted({item.content_fingerprint for item in items if item.content_fingerprint})
        file_rejection: str | None = None
        if not sensitive and not content_hashes and safety_reads < LIMITS["initial_file_reads"]:
            target = root.resolve().joinpath(*PurePosixPath(path).parts)
            try:
                size = target.stat().st_size if target.is_file() else 0
            except OSError:
                size = 0
                file_rejection = "file-read-failed"
            if size > LIMITS["max_file_bytes"]:
                file_rejection = "oversized-file-rejected"
            elif size and safety_bytes + size <= LIMITS["max_total_read_bytes"]:
                text, file_rejection, inspected_fingerprint = safe_text(root, path)
                safety_reads += 1
                if text is not None:
                    safety_bytes += len(text.encode("utf-8"))
                if inspected_fingerprint:
                    content_hashes = [inspected_fingerprint]
        role, role_reasons = classify_repository_role(root, path)
        unsafe = sensitive or (file_rejection if file_rejection not in {None, "not-a-file"} else None)
        status, confidence, status_reason = _candidate_status(role, sources, task_set, bool(unsafe))
        reasons = _stable_strings((*seed_reasons, *role_reasons, status_reason, *(tuple([unsafe]) if unsafe else ())))
        candidate_key = {"path": path, "role": role, "sources": sources, "reasons": reasons}
        rows.append(
            ScopeCandidate(
                candidate_id="cand-" + fingerprint(candidate_key).split(":", 1)[1][:12],
                path=path,
                role=role,
                status=status,
                seed_sources=sources,
                evidence_edge_ids=(),
                confidence=confidence,
                reason_codes=reasons,
                evidence_provenance=tuple(
                    {
                        "source": source,
                        "strength": "strong" if source == "explicit-path" else "medium" if source in {"fresh-graph", "git-change", "saved-graph", "host-diagnosis"} else "weak",
                        "kind": "discovery-seed",
                    }
                    for source in sources
                ),
                content_fingerprint=content_hashes[0] if len(content_hashes) == 1 else None,
            )
        )
    return [item.as_dict() for item in sorted([*rows, *rejected], key=lambda row: (row.path, row.candidate_id))]


def impact_reason(candidate: dict[str, Any]) -> str:
    role = candidate["role"]
    status = candidate["status"]
    sources = set(candidate["seed_sources"])
    reasons = set(candidate.get("reason_codes", []))
    if "bounded-static-owner-evidence" in reasons:
        return f"bounded static ownership evidence; role={role}; status={status}"
    if "direct-runtime-caller" in reasons:
        return f"direct static caller edge; role={role}; status={status}"
    if "focused-proof-owner-edge" in reasons:
        return f"focused proof linked to implementation owner; role={role}; status={status}"
    if "explicit-path" in sources:
        return f"user-provided target; role={role}; status={status}"
    if "git-change" in sources:
        return f"detected Git change; role={role}; status={status}"
    if "fresh-graph" in sources:
        return f"Code Review Graph candidate; role={role}; status={status}"
    if "saved-graph" in sources:
        return f"saved Code Graph candidate; role={role}; status={status}"
    if "repository-structure" in sources:
        return f"repository structure candidate; role={role}; status={status}"
    return f"lexical seed only; role={role}; status={status}; ownership not established"


def project_likely_impacted(candidates: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Project safe typed candidates for compatibility report surfaces."""
    rows: list[dict[str, Any]] = []
    for candidate in candidates:
        if candidate.get("status") in {"excluded", "rejected"}:
            continue
        rows.append(
            {
                "path": candidate["path"],
                "reason": impact_reason(candidate),
                "candidate_id": candidate["candidate_id"],
                "role": candidate["role"],
                "status": candidate["status"],
                "reason_codes": list(candidate["reason_codes"]),
                "seed_sources": list(candidate["seed_sources"]),
                "evidence_provenance": list(candidate["evidence_provenance"]),
            }
        )
    return rows


def role_projection(document: dict[str, Any], *, include_excluded: bool = False) -> dict[str, Any]:
    """Return one canonical, source-body-free projection for every renderer.

    Candidate role and status are global evidence facts; requirement mappings
    remain requirement-specific.  Keeping the projection here prevents Start,
    explanation, revision, and anchor-facing displays from independently
    reclassifying paths.
    """
    candidates = [row for row in document.get("candidates", []) if isinstance(row, dict)]
    by_path = {str(row.get("path")): row for row in candidates if row.get("path")}
    requirements = [row for row in document.get("requirements", []) if isinstance(row, dict)]

    def rows_for(field: str) -> list[dict[str, Any]]:
        requirement_ids: dict[str, list[str]] = {}
        for requirement in requirements:
            display_id = str(requirement.get("display_id") or requirement.get("requirement_id") or "REQ")
            for path in requirement.get(field, []):
                if isinstance(path, str):
                    requirement_ids.setdefault(path, []).append(display_id)
        rows: list[dict[str, Any]] = []
        for path in sorted(requirement_ids):
            candidate = by_path.get(path, {})
            rows.append({
                "path": path,
                "candidate_id": candidate.get("candidate_id"),
                "candidate_role": candidate.get("role", "unknown"),
                "status": candidate.get("status", "unknown"),
                "confidence": candidate.get("confidence", "none"),
                "requirement_ids": sorted(dict.fromkeys(requirement_ids[path])),
                "reason_codes": list(candidate.get("reason_codes", [])),
                "evidence_edge_ids": list(candidate.get("evidence_edge_ids", [])),
            })
        return rows

    excluded: list[dict[str, Any]] = []
    if include_excluded:
        excluded = [{
            "path": str(row.get("path")),
            "candidate_id": row.get("candidate_id"),
            "candidate_role": row.get("role", "unknown"),
            "status": row.get("status", "excluded"),
            "confidence": row.get("confidence", "none"),
            "reason_codes": list(row.get("reason_codes", [])),
            "evidence_edge_ids": list(row.get("evidence_edge_ids", [])),
        } for row in candidates if row.get("status") in {"excluded", "rejected"}]
    return {
        "schema_version": str(document.get("schema_version", "legacy")),
        "decision_fingerprint": document.get("decision_fingerprint"),
        "state": document.get("state", "unknown"),
        "implementation_owners": rows_for("implementation_owners"),
        "inspection_paths": rows_for("inspection_paths"),
        "proof_paths": rows_for("proof_paths"),
        "excluded_candidates": sorted(excluded, key=lambda row: row["path"]),
        "investigation": dict(document.get("investigation", {})) if isinstance(document.get("investigation"), dict) else {},
        "limits": dict(document.get("limits", {})) if isinstance(document.get("limits"), dict) else {},
    }


def normalized_scope_contract(value: dict[str, Any]) -> dict[str, Any]:
    """Return the host-neutral v2 scope projection used by CLI and MCP.

    ``value`` may be the evidence document itself, a Navigator report, a Start
    report, or the persisted Start-report envelope.  The projection retains
    the canonical decision fingerprint instead of calculating a transport- or
    host-specific substitute.  This is intentionally public evidence, not
    private reasoning.
    """
    candidates = [value]
    report = value.get("report") if isinstance(value, dict) else None
    if isinstance(report, dict):
        candidates.append(report)
    evidence: dict[str, Any] | None = None
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        if candidate.get("type") == EVIDENCE_TYPE:
            evidence = candidate
            break
        navigator = candidate.get("navigator")
        if isinstance(navigator, dict) and isinstance(navigator.get("scope_evidence"), dict):
            evidence = navigator["scope_evidence"]
            break
        if isinstance(candidate.get("scope_evidence"), dict):
            evidence = candidate["scope_evidence"]
            break
    if evidence is None:
        raise ValueError("v2 scope evidence is absent from the supplied report")
    if not verify_decision_fingerprint(evidence):
        raise ValueError("v2 scope evidence decision fingerprint is invalid")

    roles = role_projection(evidence, include_excluded=True)
    investigation = evidence.get("investigation", {}) if isinstance(evidence.get("investigation"), dict) else {}
    host_reasoning = evidence.get("host_reasoning", {}) if isinstance(evidence.get("host_reasoning"), dict) else {}
    requirements = []
    for row in evidence.get("requirements", []):
        if not isinstance(row, dict):
            continue
        requirements.append({
            "requirement_id": str(row.get("requirement_id", "")),
            "display_id": str(row.get("display_id", "")),
            "scope_state": str(row.get("scope_state", evidence.get("state", "unresolved"))),
            "implementation_owners": sorted(str(path) for path in row.get("implementation_owners", []) if str(path)),
            "inspection_paths": sorted(str(path) for path in row.get("inspection_paths", []) if str(path)),
            "proof_paths": sorted(str(path) for path in row.get("proof_paths", []) if str(path)),
            "reason_codes": sorted(str(code) for code in row.get("reason_codes", []) if str(code)),
        })
    return {
        "schema_version": SCHEMA_VERSION,
        "type": "tailtrail-navigator-scope-contract",
        "state": str(evidence.get("state", "unresolved")),
        "decision_fingerprint": evidence["decision_fingerprint"],
        "normalized_decision_fingerprint": evidence["decision_fingerprint"],
        "target_identity_fingerprint": evidence["target_identity_fingerprint"],
        "requirements": requirements,
        "roles": {
            "implementation_owners": roles["implementation_owners"],
            "inspection_paths": roles["inspection_paths"],
            "proof_paths": roles["proof_paths"],
            "excluded_candidates": roles["excluded_candidates"],
        },
        "decision_reason": str(investigation.get("decision_reason") or investigation.get("stop_reason") or "not-recorded"),
        "resolution_failure_reason": investigation.get("resolution_failure_reason"),
        "host_reasoning_state": str(host_reasoning.get("state", "not-requested")),
        "scope_gate": "pass" if evidence.get("state") == "resolved" else "block",
        "run_creation_allowed": evidence.get("state") == "resolved",
        "execution_blocked": True,
        "boundary": "Canonical v2 scope evidence projection. Hosts may explain it but cannot reclassify paths, replace its fingerprint, or grant execution authority.",
    }


def host_scope_contract(host: str, value: dict[str, Any]) -> dict[str, Any]:
    """Bind a supported host label without changing canonical scope truth."""
    if host not in {"codex", "copilot", "claude"}:
        raise ValueError("host must be codex, copilot, or claude")
    return {
        "host": host,
        "contract": normalized_scope_contract(value),
        "authority": "host-explanation-only",
        "boundary": "The host label is transport metadata and is excluded from the normalized decision fingerprint.",
    }


def candidate_trace(document: dict[str, Any], path: str) -> dict[str, Any] | None:
    """Explain one saved candidate with exact edge IDs and confidence."""
    candidates = [row for row in document.get("candidates", []) if isinstance(row, dict)]
    candidate = next((row for row in candidates if str(row.get("path")) == path), None)
    if candidate is None:
        return None
    by_id = {str(row.get("candidate_id")): row for row in candidates}
    edge_ids = set(str(value) for value in candidate.get("evidence_edge_ids", []))
    edges: list[dict[str, Any]] = []
    for edge in document.get("edges", []):
        if not isinstance(edge, dict) or str(edge.get("edge_id")) not in edge_ids:
            continue
        source = by_id.get(str(edge.get("from_candidate_id")), {})
        target = by_id.get(str(edge.get("to_candidate_id")), {})
        edges.append({
            "edge_id": edge.get("edge_id"),
            "kind": edge.get("kind"),
            "strength": edge.get("strength"),
            "from_path": source.get("path", edge.get("from_candidate_id")),
            "to_path": target.get("path", edge.get("to_candidate_id")),
            "reason_codes": list(edge.get("reason_codes", [])),
        })
    requirement_roles: list[dict[str, str]] = []
    role_fields = (
        ("implementation_owners", "implementation-owner"),
        ("inspection_paths", "inspection"),
        ("proof_paths", "proof"),
    )
    for requirement in document.get("requirements", []):
        if not isinstance(requirement, dict):
            continue
        for field, role in role_fields:
            if path in requirement.get(field, []):
                requirement_roles.append({
                    "requirement_id": str(requirement.get("display_id") or requirement.get("requirement_id")),
                    "role": role,
                })
    return {
        "path": path,
        "candidate_id": candidate.get("candidate_id"),
        "role": candidate.get("role", "unknown"),
        "status": candidate.get("status", "unknown"),
        "confidence": candidate.get("confidence", "none"),
        "reason_codes": list(candidate.get("reason_codes", [])),
        "seed_sources": list(candidate.get("seed_sources", [])),
        "requirement_roles": requirement_roles,
        "edges": sorted(edges, key=lambda row: str(row.get("edge_id"))),
        "decision_fingerprint": document.get("decision_fingerprint"),
    }


def authority_requirement_mappings(
    document: dict[str, Any],
    requirements: Iterable[dict[str, Any]],
    *,
    authority: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Map authority-owned requirement IDs onto the saved local scope truth.

    Imported Intent Bridge and official AIDLC requirements retain their exact
    wording, IDs, and source revision. This function attaches local path roles
    by reference only. It never writes into the v2 evidence document or treats
    an authority requirement as new ownership evidence.
    """
    if not verify_decision_fingerprint(document):
        raise ValueError("authority requirement mapping requires valid v2 scope evidence")
    local = [row for row in document.get("requirements", []) if isinstance(row, dict)]
    by_key: dict[str, dict[str, Any]] = {}
    for row in local:
        for key in (row.get("requirement_id"), row.get("display_id")):
            if key:
                by_key[str(key)] = row

    ignored = {
        "add", "and", "existing", "feature", "for", "from", "into", "only",
        "preserve", "requirement", "requirements", "the", "this", "through",
        "use", "using", "with", "without",
    }

    def terms(row: dict[str, Any]) -> set[str]:
        supplied = {str(value).lower() for value in row.get("query_terms", []) if str(value).strip()}
        if supplied:
            return supplied
        return {
            value.lower()
            for value in re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", str(row.get("statement", "")))
            if value.lower() not in ignored
        }

    def role_signature(row: dict[str, Any]) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
        return (
            tuple(sorted(str(value) for value in row.get("implementation_owners", []) if str(value))),
            tuple(sorted(str(value) for value in row.get("inspection_paths", []) if str(value))),
            tuple(sorted(str(value) for value in row.get("proof_paths", []) if str(value))),
        )

    mappings: list[dict[str, Any]] = []
    for index, requirement in enumerate(requirements, start=1):
        external_id = str(
            requirement.get("display_id")
            or requirement.get("requirement_id")
            or f"REQ-{index:02d}"
        )
        direct = (
            by_key.get(str(requirement.get("requirement_id", "")))
            or by_key.get(external_id)
        )
        selected: list[dict[str, Any]] = [direct] if isinstance(direct, dict) else []
        reason = "authority-id-matched-local-scope"
        if not selected and local:
            wanted = terms(requirement)
            scored = [
                (len(wanted & {str(value).lower() for value in row.get("query_terms", [])}), row)
                for row in local
            ]
            best = max((score for score, _ in scored), default=0)
            strongest = [row for score, row in scored if score == best and score > 0]
            if len(strongest) == 1:
                selected = strongest
                reason = "authority-terms-matched-local-scope"
            elif len(local) == 1:
                selected = [local[0]]
                reason = "single-local-scope-boundary"
            elif strongest and len({role_signature(row) for row in strongest}) == 1:
                selected = strongest
                reason = "authority-terms-share-one-local-scope-boundary"

        owners = sorted({str(value) for row in selected for value in row.get("implementation_owners", []) if str(value)})
        inspection = sorted({str(value) for row in selected for value in row.get("inspection_paths", []) if str(value)})
        proof = sorted({str(value) for row in selected for value in row.get("proof_paths", []) if str(value)})
        states = {str(row.get("scope_state", "unresolved")) for row in selected}
        mapping_state = "mapped" if selected and states <= {"resolved", "partially-resolved"} else "unresolved"
        mappings.append({
            "authority_requirement_id": external_id,
            "authority": dict(authority or {"type": "tailtrail-local-requirements"}),
            "local_scope_requirement_ids": sorted({
                str(row.get("requirement_id") or row.get("display_id")) for row in selected
            }),
            "mapping_state": mapping_state,
            "mapping_reason": reason if selected else "no-unambiguous-local-scope-mapping",
            "implementation_owners": owners,
            "inspection_paths": inspection,
            "proof_paths": proof,
            "decision_fingerprint": document.get("decision_fingerprint"),
            "boundary": "Authority wording and identity are unchanged; local paths are a projection of the saved Navigator decision and grant no additional authority.",
        })
    return mappings


def reconcile_projected_candidates(
    root: Path,
    projected: Iterable[dict[str, Any]],
    existing_candidates: Iterable[dict[str, Any]],
    task_types: Iterable[str] = (),
) -> list[dict[str, Any]]:
    """Re-type compatibility-layer additions before they enter Start scope.

    Architecture, behaviour, and UI planners may add path-inventory hypotheses
    after Navigator's initial decision. This adapter prevents those legacy
    dictionaries from bypassing the v2 domain boundary.
    """
    wanted = {
        str(item.get("path"))
        for item in projected
        if isinstance(item, dict) and item.get("path")
    }
    seeds: list[dict[str, Any]] = []
    existing_paths: set[str] = set()
    for candidate in existing_candidates:
        path = str(candidate.get("path", ""))
        if not path or path not in wanted:
            continue
        existing_paths.add(path)
        seeds.append(
            ScopeSeed(
                path=path,
                seed_sources=_stable_strings(candidate.get("seed_sources", [])),
                reason_codes=_stable_strings(candidate.get("reason_codes", [])),
                content_fingerprint=str(candidate["content_fingerprint"]) if candidate.get("content_fingerprint") else None,
            ).as_dict()
        )
    for item in projected:
        path = str(item.get("path", "")) if isinstance(item, dict) else ""
        if not path or path in existing_paths:
            continue
        seeds.append(seed(path, "repository-structure", "post-navigator-inventory-candidate"))
        existing_paths.add(path)
    return candidates_from_seeds(root, seeds, task_types)


def _repository_inventory(
    root: Path,
    limits: InvestigationLimits,
    *,
    allow_git_inventory: bool = True,
) -> list[str]:
    """Inventory repository files without executing project code.

    Debug Start passes ``allow_git_inventory=False`` so its static-orientation
    contract performs filesystem reads only and cannot spawn even a read-only
    Git command before reproduction approval. Normal build planning retains
    the existing bounded Git inventory and filesystem fallback.
    """
    values: list[str] = []
    if allow_git_inventory:
        try:
            tracked = subprocess.run(
                ["git", "ls-files"], cwd=root, text=True, capture_output=True, check=False
            )
            if tracked.returncode == 0:
                values.extend(line.strip() for line in tracked.stdout.splitlines() if line.strip())
                untracked = subprocess.run(
                    ["git", "ls-files", "--others", "--exclude-standard"],
                    cwd=root,
                    text=True,
                    capture_output=True,
                    check=False,
                )
                if untracked.returncode == 0:
                    values.extend(line.strip() for line in untracked.stdout.splitlines() if line.strip())
        except OSError:
            values = []
    if not values:
        for path in root.rglob("*"):
            if path.is_file():
                try:
                    relative = path.relative_to(root).as_posix()
                except ValueError:
                    continue
                parts = PurePosixPath(relative).parts
                if parts and parts[0].lower() in {".tailtrail", "tailtrail-meta"}:
                    continue
                values.append(relative)
            if len(values) >= limits.candidate_files:
                break
    safe: list[str] = []
    for raw in sorted(dict.fromkeys(values)):
        normalized, rejection = normalize_repository_path(root, raw)
        if rejection or normalized is None or sensitive_path_reason(normalized):
            continue
        role, _ = classify_repository_role(root, normalized)
        suffix = PurePosixPath(normalized).suffix.lower()
        if role in {"generated", "managed-tooling", "documentation"}:
            continue
        if suffix not in code_relationships.LANGUAGE_BY_SUFFIX and role not in {"configuration", "manifest"}:
            continue
        safe.append(normalized)
        if len(safe) >= limits.candidate_files:
            break
    return safe


def _cache_evidence(
    root: Path,
    limits: InvestigationLimits,
    query_terms: Iterable[str] = (),
    anchor_paths: Iterable[str] = (),
) -> tuple[list[str], dict[str, Any]]:
    """Return a freshness-checked, task-relevant slice of the graph cache.

    Repository inventory proves whether the complete cache is current. Only
    paths relevant to this request are content-hash checked and charged to the
    bounded source-read budget. This prevents a useful cross-run cache from
    eventually consuming every read allowed to one Start investigation.
    """
    cache_path = root / "tailtrail-meta" / "code-graph-cache.json"
    if not cache_path.is_file():
        return [], {"status": "missing", "reason_codes": ["graph-cache-missing"]}
    try:
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return [], {"status": "invalid", "reason_codes": ["graph-cache-invalid"]}
    if not isinstance(cache, dict) or cache.get("schema_version") != "1":
        return [], {"status": "invalid", "reason_codes": ["graph-cache-schema-invalid"]}
    try:
        if Path(str(cache.get("root", ""))).resolve() != root.resolve():
            return [], {"status": "invalid", "reason_codes": ["graph-cache-root-mismatch"]}
    except OSError:
        return [], {"status": "invalid", "reason_codes": ["graph-cache-root-mismatch"]}
    saved_inventory = cache.get("inventory")
    current_inventory = inventory_snapshot(root)
    if not isinstance(saved_inventory, dict) or saved_inventory.get("algorithm") != current_inventory["algorithm"]:
        return [], {"status": "stale", "reason_codes": ["graph-cache-inventory-missing-or-unsupported"]}
    if saved_inventory.get("fingerprint") != current_inventory["fingerprint"]:
        return [], {"status": "stale", "reason_codes": ["graph-cache-inventory-drift"]}
    graph = cache.get("graph", {})
    if not isinstance(graph, dict):
        return [], {"status": "invalid", "reason_codes": ["graph-cache-graph-invalid"]}
    paths: list[str] = []
    for key in ("suggested_read_order", "likely_callers", "likely_tests", "nearby_manifests"):
        for item in graph.get(key, []) if isinstance(graph.get(key, []), list) else []:
            value = item.get("path") if isinstance(item, dict) else item
            if isinstance(value, str):
                normalized, rejection = normalize_repository_path(root, value)
                if normalized and not rejection:
                    paths.append(normalized)

    all_paths = sorted(dict.fromkeys(paths))
    wanted_terms = {str(value).casefold() for value in query_terms if len(str(value)) >= 3}
    wanted_anchors = {
        normalized
        for value in anchor_paths
        for normalized, rejection in [normalize_repository_path(root, str(value))]
        if normalized and not rejection
    }
    if wanted_terms or wanted_anchors:
        anchor_stems = _module_stems(wanted_anchors)

        def relevance(path: str) -> tuple[int, str]:
            lowered = path.casefold()
            score = 100 if path in wanted_anchors else 0
            score += 10 * sum(term in lowered for term in wanted_terms)
            score += 8 * sum(stem and stem in lowered for stem in anchor_stems)
            return (-score, path)

        selected = [
            path for path in sorted(all_paths, key=relevance)
            if relevance(path)[0] < 0
        ][: limits.cache_validation_file_reads]
    else:
        # Compatibility for direct status callers that did not supply a task
        # frame. Start investigations always provide terms and/or anchors.
        selected = all_paths[: limits.cache_validation_file_reads]

    metadata_by_path: dict[str, dict[str, Any]] = {}
    for group in ("source_files", "watch_files"):
        rows = cache.get(group, {})
        if not isinstance(rows, dict):
            return [], {"status": "invalid", "reason_codes": ["graph-cache-metadata-invalid"]}
        for relative, metadata in rows.items():
            if not isinstance(metadata, dict) or not isinstance(metadata.get("sha256"), str):
                return [], {"status": "invalid", "reason_codes": ["graph-cache-metadata-invalid"]}
            metadata_by_path[str(relative)] = metadata

    validated_files = 0
    validated_bytes = 0
    for relative in selected:
        metadata = metadata_by_path.get(relative)
        if metadata is None:
            continue
        text, rejection, observed = safe_text(root, relative, max_bytes=limits.max_file_bytes)
        if rejection or observed != "sha256:" + str(metadata["sha256"]):
            return [], {
                "status": "stale",
                "reason_codes": ["graph-cache-file-drift"],
                "files_read": validated_files,
                "bytes_read": validated_bytes,
            }
        size = len((text or "").encode("utf-8"))
        if validated_bytes + size > limits.max_cache_validation_bytes:
            return [], {
                "status": "invalid",
                "reason_codes": ["graph-cache-validation-byte-limit-reached"],
                "files_read": validated_files,
                "bytes_read": validated_bytes,
            }
        validated_files += 1
        validated_bytes += size
    return selected, {
        "status": "fresh",
        "reason_codes": ["graph-cache-root-and-hashes-match", "graph-cache-task-slice-selected"],
        "files_read": validated_files,
        "bytes_read": validated_bytes,
        "eligible_paths": len(all_paths),
        "selected_paths": len(selected),
    }


def _module_stems(paths: Iterable[str]) -> set[str]:
    stems: set[str] = set()
    for value in paths:
        stem = PurePosixPath(value).stem.lower()
        stem = re.sub(r"^(?:test_|spec_)", "", stem)
        stem = re.sub(r"(?:_test|_tests|\.test|\.spec|\.cy)$", "", stem)
        if stem:
            stems.add(stem)
    return stems


def _read_rank(
    path: str,
    seed_paths: set[str],
    anchor_paths: set[str],
    anchor_directories: set[str],
    query_terms: set[str],
    module_stems: set[str],
    cached: set[str],
    *,
    prefer_entrypoints: bool = False,
) -> tuple[int, str]:
    lowered = path.lower()
    stem = PurePosixPath(path).stem.lower()
    role_bonus = 20 if _is_test_path(PurePosixPath(path)) else 30
    score = role_bonus + sum(12 for term in query_terms if term in lowered)
    if path in anchor_paths:
        score += 10_000
    elif path in seed_paths:
        score += 500
    parent = PurePosixPath(path).parent.as_posix()
    if parent in anchor_directories:
        score += 1_500
    if path in cached:
        score += 2_000
    if stem in module_stems or any(module in stem for module in module_stems if len(module) >= 4):
        score += 1_000
    if prefer_entrypoints and stem in {"app", "cli", "index", "main", "planning-lock", "task-start"}:
        # Prefer conventional runtime composition points within the existing
        # Debug read cap. They remain candidates until a real import/load edge
        # is extracted, so this ranking bonus is never ownership evidence.
        score += 500
    return -score, path


def _quoted_phrases(requirement_frames: Iterable[dict[str, Any]]) -> tuple[str, ...]:
    phrases: list[str] = []
    for frame in requirement_frames:
        statement = str(frame.get("statement", ""))
        canonical = frame.get("quoted_literals", [])
        if isinstance(canonical, list):
            for literal in canonical:
                value = requirement_discovery.normalize_quoted_literal(str(literal)).casefold()
                if 4 <= len(value) <= 160 and value not in phrases:
                    phrases.append(value)
        for pattern in (
            r"`([^`\n]+)`",
            r"\*\*([^*\n]+)\*\*",
            r"__([^_\n]+)__",
            r"(?<!\*)\*(?!\s)([^*\n]*?\S)\*(?!\*)",
            r"(?<!_)_(?!\s)([^_\n]*?\S)_(?!_)",
            r"'([^'\n]+)'",
            r'"([^"\n]+)"',
        ):
            for match in re.finditer(pattern, statement):
                value = " ".join(match.group(1).strip(" `*_'").casefold().split())
                if 4 <= len(value) <= 160 and value not in phrases:
                    phrases.append(value)
        if not canonical:
            contextual_statement = re.sub(
                r"(?<!\*)\*(?!\s)([^*\n]*?\S)\*(?!\*)",
                r"\1",
                statement,
            )
            for match in re.finditer(
                r"\b(?:banner|error|message|warning)\b\s*(?:says?|shows?|showing|is|reads?|:|-)?\s*"
                r"([^\n]{4,160}?)(?=\.\s+(?:we|it|this|that|please|remove|since)\b|\n|$)",
                contextual_statement,
                re.IGNORECASE,
            ):
                value = " ".join(match.group(1).strip(" `*'\". ").casefold().split())
                if 4 <= len(value) <= 160 and value not in phrases:
                    phrases.append(value)
    return tuple(phrases[:8])


def _behavior_evidence(
    path: str,
    text: str,
    ordered_query_terms: tuple[str, ...],
    exact_phrases: tuple[str, ...],
    behavior: Iterable[dict[str, Any]] | None = None,
    definitions: Iterable[dict[str, Any]] | None = None,
) -> tuple[tuple[tuple[str, str], ...], int, bool]:
    """Return static ownership signals without retaining source text.

    Language-blind: every signal below is computed from uniform behavior
    rows (see code_relationships.BEHAVIOR_ROW_KINDS) and plain text, never
    from a file suffix. UI flows (bindings, handlers, navigation, render
    destinations) and backend flows (behavior handlers, error emissions,
    guard assertions) earn the same qualification.

    Imports describe dependency direction, not necessarily behavioral
    ownership.  A component that binds the requested action, defines its
    handler, changes navigation state, and renders the destination is stronger
    evidence for an interaction defect than a helper imported by that page.
    The same holds for a backend handler that guards input and rejects it:
    the raise site, not the importer, owns the behavior.
    """
    lowered = text.casefold()
    action_terms = {
        term for term in ordered_query_terms
        if term in {"click", "copy", "download", "export", "generate", "next", "open", "submit", "validate"}
    }
    phrase_matches = [phrase for phrase in exact_phrases if phrase in lowered]
    adjacent_phrases = [
        f"{left} {right}"
        for left, right in zip(ordered_query_terms, ordered_query_terms[1:])
        if len(left) >= 3 and len(right) >= 3 and f"{left} {right}" in lowered
    ]
    has_binding = bool(action_terms) and bool(re.search(r"\b(?:onpress|onclick|onaction|onsubmit)\s*=", lowered))
    has_handler = bool(action_terms) and any(
        re.search(rf"\b(?:async\s+)?(?:function|const|let)\s+[a-z0-9_$]*{re.escape(term)}[a-z0-9_$]*\b", lowered)
        for term in action_terms
    )
    has_navigation = bool(re.search(
        r"\b(?:navigate|router\.push|history\.push|scrollintoview)\s*\(|\bset(?:show|active|current|selected)[a-z0-9_$]*\s*\(",
        lowered,
    ))
    has_rendered_destination = bool(adjacent_phrases) and bool(re.search(r"<[/]?[a-z][^>]*>|\breturn\s*\(", lowered))
    evidence: list[tuple[str, str]] = []
    if phrase_matches:
        evidence.append(("contains-user-visible-literal", "exact-user-visible-literal"))
    if has_binding:
        evidence.append(("binds-ui-action", "query-matched-ui-action-binding"))
    if has_handler:
        evidence.append(("defines-ui-handler", "query-matched-ui-handler"))
    if has_navigation:
        evidence.append(("writes-navigation-state", "static-navigation-state-write"))
    if has_rendered_destination:
        evidence.append(("renders-destination", "query-matched-rendered-destination"))
    # Backend behavior rows: a handler definition that both matches the
    # query and guards or rejects (same-scope raise/assert), plus the
    # error-emission and guard rows themselves. These require query terms
    # in the file text so unrelated raising code cannot qualify.
    terms_in_text = {term for term in ordered_query_terms if term in lowered}
    backend_rows: list[tuple[str, str]] = []
    behavior_rows = [row for row in (behavior or []) if isinstance(row, dict)]
    if terms_in_text:
        guard_scopes = {
            str(row.get("scope"))
            for row in behavior_rows
            if row.get("kind") in {"raise", "assert"} and row.get("scope")
        }
        for row in behavior_rows:
            if row.get("kind") == "raise":
                backend_rows.append(("raises-behavior-error", "query-matched-error-emission"))
            elif row.get("kind") == "assert":
                backend_rows.append(("asserts-behavior-guard", "query-matched-guard-assertion"))
        for item in definitions or []:
            if not isinstance(item, dict):
                continue
            name = str(item.get("value", "")).lower()
            if (
                item.get("kind") in {"functiondef", "asyncfunctiondef", "definition"}
                and any(len(term) >= 4 and term in name for term in terms_in_text)
                and name in guard_scopes
            ):
                backend_rows.append(("defines-behavior-handler", "query-matched-behavior-handler"))
    evidence.extend(backend_rows)
    qualifies = (
        bool(phrase_matches) and sum((has_binding, has_handler, has_navigation, has_rendered_destination)) >= 2
    ) or (has_binding and has_handler and has_navigation and has_rendered_destination)
    if not qualifies:
        qualifies = bool(phrase_matches) and len(backend_rows) >= 1 or len(backend_rows) >= 2
    score = 200 + 40 * len(evidence) + 20 * len(adjacent_phrases) if qualifies else 0
    return tuple(evidence), score, qualifies


def _bounded_behavior_chain(
    importer_facts: dict[str, Any],
    module_reference: str,
) -> dict[str, Any]:
    """Trace one conservative, source-free UI behavior chain.

    A module edge establishes where a value originates. It becomes renderer
    ownership evidence only when bounded intra-file facts also establish one
    of the supported preservation-safe flows:

    * imported call -> returned value -> render use; or
    * imported call -> catch binding -> state write -> render use.

    Unsupported indirection and incomplete flows are retained as uncertainty;
    they never qualify an implementation owner.
    """
    behavior = list(importer_facts.get("behavior", []))
    bindings = {
        str(row.get("value")): int(row.get("line", 0))
        for row in behavior
        if row.get("kind") == "import-binding"
        and str(row.get("detail", "")) == module_reference
    }
    if not bindings:
        return {
            "state": "unresolved",
            "variant": "none",
            "fact_kinds": [],
            "reason_codes": ["static-import-binding-not-extracted"],
        }

    calls = [
        row for row in behavior
        if row.get("kind") == "call" and str(row.get("value")) in bindings
    ]
    if not calls:
        return {
            "state": "incomplete",
            "variant": "none",
            "fact_kinds": ["import-binding"],
            "reason_codes": ["imported-symbol-call-not-proven"],
        }

    def shares_scope(*rows: dict[str, Any]) -> bool:
        scopes = {str(row.get("scope", "module")) for row in rows}
        return len(scopes) == 1

    render_uses = [row for row in behavior if row.get("kind") == "render-use"]
    call_results = [
        row for row in behavior
        if row.get("kind") == "call-result"
        and str(row.get("detail", "")) in bindings
    ]
    for result in call_results:
        result_line = int(result.get("line", 0))
        rendered = next((
            row for row in render_uses
            if row.get("value") == result.get("value")
            and shares_scope(result, row)
            and 0 <= int(row.get("line", 0)) - result_line <= BEHAVIOR_CHAIN_LINE_SPAN
        ), None)
        if rendered:
            return {
                "state": "complete",
                "variant": "returned-value-render",
                "fact_kinds": ["import-binding", "call", "call-result", "render-use"],
                "reason_codes": ["bounded-returned-value-render-chain"],
            }

    catch_bindings = [row for row in behavior if row.get("kind") == "catch-binding"]
    state_writes = [row for row in behavior if row.get("kind") == "state-write"]
    for call in calls:
        call_line = int(call.get("line", 0))
        for caught in catch_bindings:
            catch_line = int(caught.get("line", 0))
            if not 0 <= catch_line - call_line <= BEHAVIOR_CHAIN_LINE_SPAN:
                continue
            if not shares_scope(call, caught):
                continue
            caught_name = str(caught.get("value", ""))
            direct_render = next((
                row for row in render_uses
                if row.get("value") == caught_name
                and shares_scope(caught, row)
                and 0 <= int(row.get("line", 0)) - catch_line <= BEHAVIOR_CHAIN_LINE_SPAN
            ), None)
            if direct_render:
                return {
                    "state": "complete",
                    "variant": "caught-error-render",
                    "fact_kinds": [
                        "import-binding", "call", "catch-binding", "render-use",
                    ],
                    "reason_codes": ["bounded-caught-error-render-chain"],
                }
            for write in state_writes:
                write_line = int(write.get("line", 0))
                write_inputs = set(filter(None, str(write.get("detail", "")).split(",")))
                if not (
                    caught_name in write_inputs
                    and shares_scope(caught, write)
                    and 0 <= write_line - catch_line <= BEHAVIOR_CHAIN_LINE_SPAN
                ):
                    continue
                rendered = next((
                    row for row in render_uses
                    if row.get("value") == write.get("value")
                    and shares_scope(write, row)
                    and 0 <= int(row.get("line", 0)) - write_line <= BEHAVIOR_CHAIN_LINE_SPAN
                ), None)
                if rendered:
                    return {
                        "state": "complete",
                        "variant": "caught-error-state-render",
                        "fact_kinds": [
                            "import-binding", "call", "catch-binding",
                            "state-write", "render-use",
                        ],
                        "reason_codes": ["bounded-caught-error-state-render-chain"],
                    }

    return {
        "state": "partial",
        "variant": "none",
        "fact_kinds": ["import-binding", "call"],
        "reason_codes": ["rendered-output-link-not-proven"],
    }


def _identities(path: str, facts: dict[str, Any]) -> set[str]:
    pure = PurePosixPath(path)
    without_suffix = pure.with_suffix("").as_posix()
    values = {without_suffix, without_suffix.replace("/", "."), pure.stem}
    definitions = {str(row.get("value")) for row in facts.get("definitions", []) if row.get("value")}
    containers = {
        str(row.get("value"))
        for row in facts.get("registrations", [])
        if row.get("kind") in {"package", "namespace"} and row.get("value")
    }
    values.update(definitions)
    values.update(containers)
    values.update(f"{container}.{definition}" for container in containers for definition in definitions)
    return {value.strip(".") for value in values if value}


def _module_identities(path: str) -> set[str]:
    pure = PurePosixPath(path)
    without_suffix = pure.with_suffix("").as_posix()
    return {
        without_suffix,
        without_suffix.replace("/", "."),
        pure.stem,
    }


def _identifier_terms(value: str) -> set[str]:
    expanded = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    return {
        token.casefold()
        for token in re.findall(r"[A-Za-z0-9]+", expanded)
        if len(token) >= 3
    }


def _owner_query_terms(query_terms: Iterable[str]) -> set[str]:
    return {
        str(term).casefold()
        for term in query_terms
        if len(str(term)) >= 3 and str(term).casefold() not in LOW_SIGNAL_OWNER_TERMS
    }


def _local_owner_identity_terms(path: str, facts: dict[str, Any]) -> set[str]:
    pure = PurePosixPath(path)
    basename_terms = _identifier_terms(pure.stem) - GENERIC_PATH_SEGMENTS
    definition_terms = {
        token
        for row in facts.get("definitions", [])
        for token in _identifier_terms(str(row.get("value", "")))
    }
    return basename_terms | definition_terms


def _select_qualified_owners(qualifications: dict[str, set[str]]) -> tuple[set[str], str | None]:
    """Select owners by an explicit evidence-rule tier, never seed weight."""
    for rule in OWNER_QUALIFICATION_PRECEDENCE:
        selected = {
            path for path, path_rules in qualifications.items()
            if rule in path_rules
        }
        if selected:
            return selected, rule
    return set(), None


def _is_ui_implementation_path(path: str) -> bool:
    pure = PurePosixPath(path)
    return pure.suffix.casefold() in UI_SOURCE_SUFFIXES or bool(
        {part.casefold() for part in pure.parts[:-1]} & UI_PATH_SEGMENTS
    )


def _resolve_reference(
    root: Path,
    importer: str,
    reference: str,
    kind: str,
    identities: dict[str, set[str]],
    *,
    module_resolver: RepositoryModuleResolver | None = None,
    resolution_events: list[ResolutionResult] | None = None,
) -> list[str]:
    raw = reference.replace("\\", "/").strip()
    if not raw:
        return []
    if module_resolver is not None:
        resolution = module_resolver.resolve(importer, raw, kind)
        if resolution_events is not None:
            resolution_events.append(resolution)
        if resolution.state in {"resolved", "ambiguous"}:
            return [path for path in resolution.candidates if path != importer]
    importer_parent = PurePosixPath(importer).parent
    candidates: list[str] = []
    if kind == "loader" or raw.startswith(("./", "../", "/")):
        raw_path = PurePosixPath(raw.lstrip("/")) if raw.startswith("/") else importer_parent / raw
        variants = [raw_path, PurePosixPath(raw.lstrip("/"))]
        if not raw_path.suffix:
            variants.extend(PurePosixPath(str(raw_path) + suffix) for suffix in code_relationships.LANGUAGE_BY_SUFFIX)
            variants.extend(
                raw_path / ("index" + suffix)
                for suffix in code_relationships.LANGUAGE_BY_SUFFIX
                if suffix not in code_relationships.CONFIGURATION_SUFFIXES
            )
        for value in variants:
            normalized, rejection = normalize_repository_path(root, value.as_posix())
            if normalized and not rejection and normalized in identities:
                candidates.append(normalized)
    normalized_ref = raw.lstrip(".").removesuffix(".*")
    # Prefer an exact module/path identity over a symbol with the same name.
    # A helper function or test class named after a module must not make a
    # concrete import ambiguous and hide its runtime caller edge.
    module_candidates = [
        path
        for path in identities
        if raw in _module_identities(path)
        or normalized_ref in _module_identities(path)
        or any(name.endswith("." + normalized_ref) for name in _module_identities(path))
    ]
    if module_candidates:
        candidates.extend(module_candidates)
        return sorted(dict.fromkeys(path for path in candidates if path != importer))
    for path, names in identities.items():
        if raw in names or normalized_ref in names or any(name.endswith("." + normalized_ref) for name in names):
            candidates.append(path)
        elif "/" not in raw and "." not in raw and PurePosixPath(path).stem == raw:
            candidates.append(path)
    return sorted(dict.fromkeys(path for path in candidates if path != importer))


def _edge(from_id: str, to_id: str, kind: str, strength: str, reason: str) -> dict[str, Any]:
    key = {"from": from_id, "to": to_id, "kind": kind, "strength": strength, "reason": reason}
    return {
        "edge_id": "edge-" + fingerprint(key).split(":", 1)[1][:12],
        "from_candidate_id": from_id,
        "to_candidate_id": to_id,
        "kind": kind,
        "strength": strength,
        "reason_codes": [reason],
    }


ANCHOR_ROLES = (
    "entrypoint",
    "orchestrator",
    "domain-owner",
    "integration-owner",
    "verification-owner",
    "convention-owner",
)

TOPOLOGY_TO_CANDIDATE_ROLES = {
    "entrypoint": "implementation-owner",
    "orchestrator": "implementation-owner",
    "domain-owner": "implementation-owner",
    "integration-owner": "implementation-owner",
    "verification-owner": "test",
    "convention-owner": "reference",
}


def project_topology_role(topology_role: str) -> str:
    """Project one packet topology role onto exactly one candidate role (Stage 6).

    Behavior-flow positions that own durable behavior map to the editable
    implementation-owner posture; verification maps to test; the reusable
    convention pattern maps to read-only reference.
    """
    try:
        return TOPOLOGY_TO_CANDIDATE_ROLES[str(topology_role)]
    except KeyError:
        raise ValueError(f"unknown packet topology role: {topology_role}") from None

_ANCHOR_CROSS_BOUNDARY_KINDS = {"imports-module", "loads-module", "registered-by", "configures-owner"}


def derive_anchors(
    exact_paths: Iterable[str],
    explicit_paths: Iterable[str],
    candidates_by_path: dict[str, Any],
    edges: list[dict[str, Any]],
    candidate_by_id: dict[str, Any],
) -> tuple[list[dict[str, Any]], str]:
    """Derive role-labeled anchor hypotheses from existing seed evidence (Stage 3).

    Anchors carry confidence and evidence references and are never owners or
    implementation authority. Pure lexical seeds never mint anchors.
    Returns (anchors sorted by role and path, "sufficient" | "insufficient").
    """
    anchors: dict[str, dict[str, Any]] = {}

    def add(role: str, path: str, confidence: str, reason: str, evidence: dict[str, Any]) -> None:
        anchor_id = f"anchor:{role}:{path}"
        if anchor_id not in anchors:
            anchors[anchor_id] = {
                "anchor_id": anchor_id,
                "role": role,
                "path": path,
                "confidence": confidence,
                "reason_codes": [reason],
                "evidence_refs": evidence,
            }

    for path in sorted(set(exact_paths)):
        add("entrypoint", path, "high", "anchor-exact-task-reference",
            {"seeds": ["exact-phrase-in-bounded-body"]})
    for path in sorted(set(explicit_paths) - set(exact_paths)):
        add("entrypoint", path, "medium", "anchor-explicit-task-path",
            {"seeds": ["explicit-path", "fresh-graph", "saved-graph"]})
    for path in sorted(candidates_by_path):
        row = candidates_by_path[path]
        if not isinstance(row, dict) or row.get("status") != "included":
            continue
        if not (set(row.get("seed_sources", [])) - {"lexical-body", "lexical-path"}):
            continue
        reasons = [str(code) for code in row.get("reason_codes", [])]
        candidate_id = str(row.get("candidate_id", ""))
        if any("convention" in code for code in reasons):
            add("convention-owner", path, "medium", "anchor-convention",
                {"candidates": [candidate_id], "seeds": sorted({code for code in reasons if "convention" in code})})
        if row.get("role") == "test":
            add("verification-owner", path, "medium", "anchor-test", {"candidates": [candidate_id]})
        if row.get("role") in {"configuration", "manifest"}:
            add("domain-owner", path, "medium", "anchor-config", {"candidates": [candidate_id]})
    id_to_path = {
        str(candidate_id): str(row.get("path", ""))
        for candidate_id, row in candidate_by_id.items()
        if isinstance(row, dict) and row.get("path")
    }
    entrypoint_paths = {anchor["path"] for anchor in anchors.values() if anchor["role"] == "entrypoint"}
    for edge in edges or []:
        if not isinstance(edge, dict):
            continue
        frm = id_to_path.get(str(edge.get("from_candidate_id", "")))
        to = id_to_path.get(str(edge.get("to_candidate_id", "")))
        if not frm or not to:
            continue
        kind = str(edge.get("kind", ""))
        edge_id = str(edge.get("edge_id", ""))
        for path, other in ((frm, to), (to, frm)):
            prow = candidates_by_path.get(path)
            if (
                isinstance(prow, dict)
                and prow.get("status") == "included"
                and prow.get("role") == "caller"
                and set(prow.get("seed_sources", [])) - {"lexical-body", "lexical-path"}
                and other in entrypoint_paths
            ):
                add("orchestrator", path, "medium", "anchor-caller-edge",
                    {"candidates": [str(prow.get("candidate_id", ""))], "edges": [edge_id] if edge_id else []})
        if kind in _ANCHOR_CROSS_BOUNDARY_KINDS:
            if PurePosixPath(frm).parent.as_posix() != PurePosixPath(to).parent.as_posix():
                for path in (frm, to):
                    prow = candidates_by_path.get(path)
                    if (
                        isinstance(prow, dict)
                        and prow.get("status") == "included"
                        and set(prow.get("seed_sources", [])) - {"lexical-body", "lexical-path"}
                    ):
                        add("integration-owner", path, "medium", "anchor-cross-boundary-edge",
                            {"candidates": [str(prow.get("candidate_id", ""))], "edges": [edge_id] if edge_id else []})
    ordered = sorted(anchors.values(), key=lambda row: (row["role"], row["path"]))
    return ordered, "sufficient" if ordered else "insufficient"


def candidate_edge_adjacency(
    edges: list[dict[str, Any]] | None,
    candidate_by_id: dict[str, Any] | None,
) -> dict[str, list[str]]:
    """Build a directed path adjacency from candidate-ID relationship edges (Stage 3)."""
    adjacency: dict[str, set[str]] = {}
    for edge in edges or []:
        if not isinstance(edge, dict):
            continue
        frm = (candidate_by_id or {}).get(str(edge.get("from_candidate_id", "")))
        to = (candidate_by_id or {}).get(str(edge.get("to_candidate_id", "")))
        frm_path = frm.get("path") if isinstance(frm, dict) else None
        to_path = to.get("path") if isinstance(to, dict) else None
        if frm_path and to_path:
            adjacency.setdefault(str(frm_path), set()).add(str(to_path))
    return {path: sorted(targets) for path, targets in adjacency.items()}


def reference_adjacency(references: list[dict[str, Any]] | None) -> dict[str, list[str]]:
    """Build a directed adjacency from mapper graph references (Stage 3).

    Follows resolved repository-relative targets; raw specifiers that are not
    paths never match cached scope and are harmless.
    """
    adjacency: dict[str, set[str]] = {}
    for ref in references or []:
        if not isinstance(ref, dict):
            continue
        source = ref.get("referring_file")
        if not isinstance(source, str) or not source:
            continue
        targets: set[str] = set()
        resolved = ref.get("module_resolution", {})
        if isinstance(resolved, dict):
            for target in resolved.get("resolved_targets", []) or []:
                if isinstance(target, str) and target:
                    targets.add(target.replace("\\", "/"))
        raw = ref.get("target", "")
        if isinstance(raw, str) and "/" in raw:
            candidate = raw.strip().replace("\\", "/")
            if candidate and "://" not in candidate:
                targets.add(candidate)
        if targets:
            adjacency.setdefault(source.replace("\\", "/"), set()).update(targets)
    return {path: sorted(targets) for path, targets in adjacency.items()}


def connected_files(
    seed_paths: Iterable[str],
    adjacency: dict[str, list[str]] | None,
    max_hops: int = 3,
    limit: int = 200,
) -> list[str]:
    """Bounded directed BFS from anchor paths over collected edges (Stage 3)."""
    seeds = [path for path in dict.fromkeys(str(item) for item in seed_paths or []) if path]
    seen: set[str] = set(seeds)
    frontier = list(seeds)
    hops = 0
    graph = adjacency or {}
    while frontier and hops < max(0, max_hops) and len(seen) < limit:
        nxt: list[str] = []
        for path in frontier:
            for target in graph.get(path, []):
                if target not in seen and len(seen) < limit:
                    seen.add(target)
                    nxt.append(target)
        frontier = nxt
        hops += 1
    return sorted(seen)[:limit]


def anchor_slice(
    anchors: list[dict[str, Any]] | None,
    edges: list[dict[str, Any]] | None = None,
    candidate_by_id: dict[str, Any] | None = None,
    coverage_required: Iterable[str] = (),
) -> dict[str, Any]:
    """Project anchors into the lifecycle anchor-slice contract (Stage 3)."""
    anchor_list = [dict(item) for item in anchors or [] if isinstance(item, dict)]
    relations: set[str] = set()
    if edges and candidate_by_id:
        id_to_role = {
            str(candidate_id): str(row.get("role", "unknown"))
            for candidate_id, row in candidate_by_id.items()
            if isinstance(row, dict)
        }
        anchor_paths = {str(item.get("path", "")) for item in anchor_list}
        id_to_path = {
            str(candidate_id): str(row.get("path", ""))
            for candidate_id, row in candidate_by_id.items()
            if isinstance(row, dict)
        }
        for edge in edges:
            if not isinstance(edge, dict):
                continue
            frm = id_to_path.get(str(edge.get("from_candidate_id", "")))
            to = id_to_path.get(str(edge.get("to_candidate_id", "")))
            if frm in anchor_paths or to in anchor_paths:
                relations.add(
                    f"{id_to_role.get(str(edge.get('from_candidate_id', '')), 'unknown')}"
                    f"->{id_to_role.get(str(edge.get('to_candidate_id', '')), 'unknown')}"
                )
    ordered_ids = sorted(str(item.get("anchor_id", "")) for item in anchor_list)
    ordered_paths = sorted({str(item.get("path", "")) for item in anchor_list if item.get("path")})
    coverage = sorted(dict.fromkeys(str(item) for item in coverage_required if str(item).strip()))
    body = {
        "anchor_ids": ordered_ids,
        "paths": ordered_paths,
        "relations": sorted(relations),
        "coverage_required": coverage,
    }
    return {**body, "fingerprint": fingerprint(body)}


def investigate(
    root: Path,
    requirement_frames: Iterable[dict[str, Any]],
    candidates: Iterable[dict[str, Any]],
    task_types: Iterable[str] = (),
    *,
    limits: InvestigationLimits = DEFAULT_LIMITS,
    allow_git_inventory: bool = True,
    allow_persistent_cache: bool = True,
    allow_passive_capture: bool = True,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Resolve implementation ownership with bounded, static local evidence.

    When ``allow_passive_capture`` is true (default), every file actually
    read above is queued via ``capture_hooks`` and merged into the Phase 1
    code-graph cache in one batched ``flush`` — passive capture as a side
    effect of discovery (docs/arch/code-graphing.md §3.2). Best-effort and
    never raises; investigation results are unaffected.
    """
    frames = [dict(frame) for frame in requirement_frames]
    initial = [dict(row) for row in candidates]
    seed_paths = {str(row["path"]) for row in initial if row.get("status") not in {"excluded", "rejected"}}
    ordered_query_terms = tuple(dict.fromkeys(
        str(term).lower()
        for frame in frames
        for term in frame.get("query_terms", [])
        if len(str(term)) >= 3
    ))
    query_terms = set(ordered_query_terms)
    exact_phrases = _quoted_phrases(frames)
    ui_visibility_change = any(str(frame.get("intent_class")) == "ui-visibility" for frame in frames)
    ui_surface_requested = ui_visibility_change or any(
        _identifier_terms(str(frame.get("statement", ""))) & UI_REQUEST_TERMS
        for frame in frames
    )
    exact_anchor_paths = {
        str(row["path"])
        for row in initial
        if "exact-phrase-in-bounded-body" in set(row.get("reason_codes", []))
    }
    explicit_anchor_paths = {
        str(row["path"])
        for row in initial
        if set(row.get("seed_sources", [])) & {"explicit-path", "fresh-graph", "saved-graph"}
    }
    anchor_paths = exact_anchor_paths or explicit_anchor_paths or seed_paths
    anchor_directories = {PurePosixPath(path).parent.as_posix() for path in anchor_paths}
    cached_paths, cache_status = (
        _cache_evidence(root, limits, query_terms, anchor_paths)
        if allow_persistent_cache
        else ([], {"status": "disabled", "reason_codes": ["graph-cache-disabled-by-user"]})
    )
    inventory = _repository_inventory(root, limits, allow_git_inventory=allow_git_inventory)
    module_stems = _module_stems(anchor_paths)
    prefer_entrypoints = "debug" in {str(value) for value in task_types}
    ranked = sorted(
        inventory,
        key=lambda path: _read_rank(
            path,
            seed_paths,
            anchor_paths,
            anchor_directories,
            query_terms,
            module_stems,
            set(cached_paths),
            prefer_entrypoints=prefer_entrypoints,
        ),
    )
    # Broad discovery and direct-neighbor resolution have independent caps.
    # Cache hash checks are also reported independently and cannot consume the
    # source-fact budget needed to prove a relationship.
    broad_read_limit = (
        limits.initial_file_reads
        if exact_anchor_paths
        else limits.initial_file_reads + limits.escalation_file_reads
    )
    facts: dict[str, dict[str, Any]] = {}
    content_hashes: dict[str, str] = {}
    semantic_matches: dict[str, set[str]] = {}
    behavior_evidence: dict[str, tuple[tuple[tuple[str, str], ...], int, bool]] = {}
    exact_literal_emission_paths: set[str] = set()
    cache_files_read = int(cache_status.get("files_read", 0))
    total_bytes = int(cache_status.get("bytes_read", 0))
    broad_files_read = 0
    relationship_files_read = 0
    byte_limit_reached = False

    def read_facts(path: str) -> bool:
        nonlocal total_bytes, byte_limit_reached
        if path in facts:
            return False
        text, rejection, content_hash = safe_text(root, path)
        if rejection or text is None or content_hash is None:
            return False
        size = len(text.encode("utf-8"))
        if total_bytes + size > limits.max_total_read_bytes:
            byte_limit_reached = True
            return False
        total_bytes += size
        facts[path] = code_relationships.extract(root / path, root, text)
        content_hashes[path] = content_hash
        lowered_text = text.lower()
        semantic_matches[path] = {term for term in query_terms if term in lowered_text or term in path.lower()}
        behavior_evidence[path] = _behavior_evidence(
            path, text, ordered_query_terms, exact_phrases,
            facts[path].get("behavior", []), facts[path].get("definitions", []),
        )
        if any(phrase in lowered_text for phrase in exact_phrases) and re.search(
            r"\b(?:throw\s+new\s+error|raise\s+[a-z_]*error|toast\.(?:error|warning|info)|"
            r"set(?:error|message|banner)|render|return)\b",
            lowered_text,
        ):
            exact_literal_emission_paths.add(path)
        return True

    broad_paths_considered = 0
    for path in ranked:
        if broad_files_read >= broad_read_limit or byte_limit_reached:
            break
        broad_paths_considered += 1
        if read_facts(path):
            broad_files_read += 1
    broad_limit_reached = (
        not byte_limit_reached
        and broad_files_read >= broad_read_limit
        and broad_paths_considered < len(ranked)
    )

    def targeted_rank(path: str) -> tuple[int, str]:
        pure = PurePosixPath(path)
        parent = pure.parent.as_posix()
        stem = pure.stem.casefold()
        score = 0
        if parent in anchor_directories:
            score += 10_000
        if path in cached_paths:
            score += 8_000
        if stem in module_stems or any(value in stem for value in module_stems if len(value) >= 4):
            score += 6_000
        if pure.name.startswith(("tsconfig", "jsconfig")):
            score += 4_000
        if _is_test_path(pure) and any(value in stem for value in module_stems):
            score += 2_000
        return -score, path

    targeted_paths = [
        path for path in inventory
        if path not in facts
        and (
            PurePosixPath(path).parent.as_posix() in anchor_directories
            or path in cached_paths
            or PurePosixPath(path).stem.casefold() in module_stems
            or any(
                value in PurePosixPath(path).stem.casefold()
                for value in module_stems if len(value) >= 4
            )
            or PurePosixPath(path).name.startswith(("tsconfig", "jsconfig"))
        )
    ]
    targeted_paths = sorted(dict.fromkeys(targeted_paths), key=targeted_rank)
    targeted_paths_considered = 0
    for path in targeted_paths:
        if relationship_files_read >= limits.relationship_file_reads or byte_limit_reached:
            break
        targeted_paths_considered += 1
        if read_facts(path):
            relationship_files_read += 1
    relationship_limit_reached = (
        not byte_limit_reached
        and relationship_files_read >= limits.relationship_file_reads
        and targeted_paths_considered < len(targeted_paths)
    )
    loop_termination_reason = (
        "total-byte-limit-reached" if byte_limit_reached
        else "relationship-file-read-limit-reached" if relationship_limit_reached
        else "broad-file-read-limit-reached" if broad_limit_reached
        else "inventory-exhausted"
    )

    if allow_passive_capture and facts:
        try:
            for read_path in facts:
                capture_hooks.on_file_read(root, read_path)
            capture_hooks.flush(root)
        except Exception:
            pass

    if cache_status.get("status") != "fresh" and facts:
        cache_status = dict(cache_status)
        cache_status["reason_codes"] = list(dict.fromkeys([
            *cache_status.get("reason_codes", []),
            "bounded-ephemeral-graph-built",
            "ephemeral-graph-not-persisted",
        ]))

    identities = {path: _identities(path, value) for path, value in facts.items()}
    module_resolver = RepositoryModuleResolver(root, inventory)
    module_resolution_events: list[ResolutionResult] = []
    renderer_resolution_events: list[ResolutionResult] = []
    behavior_chain_rows: list[dict[str, Any]] = []
    relationship_rows: list[tuple[str, str, str, str, str]] = []
    owner_qualifications: dict[str, set[str]] = {}
    owner_paths: set[str] = set()
    proof_paths: set[str] = set()
    caller_paths: set[str] = set()
    configuration_paths: set[str] = set()
    relevant_paths = set(seed_paths)
    focus_eligible = {
        str(row["path"])
        for row in initial
        if set(row.get("seed_sources", [])) & {"explicit-path", "lexical-body", "lexical-path"}
    }
    seeded_tests = [path for path in focus_eligible if classify_repository_role(root, path)[0] == "test"]
    max_seed_match = max((len(semantic_matches.get(path, set())) for path in seeded_tests), default=0)
    focus_seeds = {
        path for path in focus_eligible
        if classify_repository_role(root, path)[0] != "test"
        or len(semantic_matches.get(path, set())) == max_seed_match
    }
    def qualify_owner(path: str, rule: str) -> None:
        owner_qualifications.setdefault(path, set()).add(rule)

    for row in initial:
        path = str(row["path"])
        if (
            row.get("role") == "implementation-owner"
            and "explicit-path" in set(row.get("seed_sources", []))
        ):
            qualify_owner(path, "explicit-user-scope")
            relevant_paths.add(path)
            relationship_rows.append((path, path, "declares-edit-boundary", "strong", "explicit-scope-owner-qualification"))

    behavior_owner_paths: set[str] = set()
    ui_renderer_paths: set[str] = set()
    for path, (evidence_rows, _score, qualifies) in behavior_evidence.items():
        if not qualifies or classify_repository_role(root, path)[0] != "implementation-owner":
            continue
        behavior_owner_paths.add(path)
        qualify_owner(path, "task-specific-behavior")
        relevant_paths.add(path)
        for kind, reason in evidence_rows:
            relationship_rows.append((path, path, kind, "strong", reason))

    # A unique exact literal emitted by production code normally provides
    # direct behavioral ownership evidence. For a UI visibility request it is
    # only the literal source until a rendering caller is traced.
    exact_emitters: list[str] = []
    for path in sorted(exact_literal_emission_paths):
        if classify_repository_role(root, path)[0] == "implementation-owner":
            exact_emitters.append(path)
    if len(exact_emitters) == 1:
        path = exact_emitters[0]
        if not ui_visibility_change:
            qualify_owner(path, "unique-exact-literal")
        relevant_paths.add(path)
        relationship_rows.append((
            path,
            path,
            "emits-user-visible-literal",
            "strong",
            "ui-literal-source-needs-render-owner" if ui_visibility_change else "unique-exact-literal-emitter",
        ))

    for importer, value in facts.items():
        importer_role, _ = classify_repository_role(root, importer)
        for relation_kind in ("imports", "loaders"):
            for relation in value.get(relation_kind, []):
                event_offset = len(module_resolution_events)
                reference_value = str(relation.get("value", ""))
                targets = _resolve_reference(
                    root,
                    importer,
                    reference_value,
                    relation_kind[:-1],
                    identities,
                    module_resolver=module_resolver,
                    resolution_events=module_resolution_events,
                )
                new_resolution_events = module_resolution_events[event_offset:]
                reference_stem = PurePosixPath(reference_value.replace("\\", "/")).name.casefold()
                if any(PurePosixPath(path).stem.casefold() == reference_stem for path in exact_emitters):
                    renderer_resolution_events.extend(new_resolution_events)
                if len(targets) != 1:
                    continue
                target = targets[0]
                target_role, _ = classify_repository_role(root, target)
                if target_role != "implementation-owner":
                    continue
                edge_kind = "loads-module" if relation_kind == "loaders" else "imports-module"
                resolution_reason = "static-module-reference"
                if any(
                    "module-alias-reference-resolved" in event.reason_codes
                    for event in module_resolution_events[event_offset:]
                ):
                    resolution_reason = "configured-module-alias-reference"
                elif any(
                    "module-base-url-reference-resolved" in event.reason_codes
                    for event in module_resolution_events[event_offset:]
                ):
                    resolution_reason = "configured-base-url-reference"
                relationship_rows.append((importer, target, edge_kind, "strong", resolution_reason))
                relevant_paths.update({importer, target})
                if ui_visibility_change and target in exact_emitters and importer_role == "implementation-owner":
                    renderer_resolution_events.extend(new_resolution_events)
                    behavior_chain = _bounded_behavior_chain(
                        value,
                        str(relation.get("value", "")),
                    )
                    chain_row = {
                        "renderer_path": importer,
                        "source_path": target,
                        **behavior_chain,
                    }
                    behavior_chain_rows.append(chain_row)
                    if behavior_chain["state"] == "complete":
                        qualify_owner(importer, "ui-renderer-behavior")
                        ui_renderer_paths.add(importer)
                        behavior_owner_paths.add(importer)
                        relationship_rows.append((importer, target, "calls-symbol", "strong", "behavior-chain-imported-symbol-call"))
                        if behavior_chain["variant"] == "returned-value-render":
                            relationship_rows.append((importer, target, "captures-returned-value", "strong", "behavior-chain-call-result"))
                            relationship_rows.append((importer, target, "renders-returned-value", "strong", "behavior-chain-render-use"))
                        elif behavior_chain["variant"] == "caught-error-state-render":
                            relationship_rows.append((importer, target, "catches-error", "strong", "behavior-chain-catch-binding"))
                            relationship_rows.append((importer, target, "writes-ui-state", "strong", "behavior-chain-state-write"))
                            relationship_rows.append((importer, target, "renders-ui-state", "strong", "behavior-chain-render-use"))
                        elif behavior_chain["variant"] == "caught-error-render":
                            relationship_rows.append((importer, target, "catches-error", "strong", "behavior-chain-catch-binding"))
                            relationship_rows.append((importer, target, "renders-caught-error", "strong", "behavior-chain-render-use"))
                owner_terms = _owner_query_terms(query_terms)
                target_identity_matches = owner_terms & _local_owner_identity_terms(target, facts.get(target, {}))
                if importer in focus_seeds:
                    importer_matches = len(semantic_matches.get(importer, set()))
                    target_matches = len(semantic_matches.get(target, set()))
                    if (
                        target_identity_matches
                        and (not ui_surface_requested or _is_ui_implementation_path(target))
                        and (
                        importer_role == "test" or target_matches > importer_matches
                        )
                    ):
                        qualify_owner(target, "task-specific-relationship")
                if importer_role == "test":
                    proof_paths.add(importer)
                    relationship_rows.append((target, importer, "tested-by", "strong", "test-module-reference"))
                elif importer != target:
                    caller_paths.add(importer)
        for relation in value.get("registrations", []):
            targets = _resolve_reference(
                root,
                importer,
                str(relation.get("value", "")),
                "registration",
                identities,
                module_resolver=module_resolver,
                resolution_events=module_resolution_events,
            )
            if len(targets) != 1:
                continue
            target = targets[0]
            if classify_repository_role(root, target)[0] != "implementation-owner":
                continue
            relationship_rows.append((importer, target, "registered-by", "strong", "static-registration-reference"))
            relevant_paths.update({importer, target})
            if importer in focus_seeds and (
                _owner_query_terms(query_terms) & _local_owner_identity_terms(target, facts.get(target, {}))
            ) and (not ui_surface_requested or _is_ui_implementation_path(target)):
                qualify_owner(target, "task-specific-relationship")
            if importer_role == "test":
                proof_paths.add(importer)
                relationship_rows.append((target, importer, "tested-by", "strong", "test-registration-reference"))
            elif importer != target:
                caller_paths.add(importer)

    # A focused test naming the exact production module is useful bounded proof,
    # but remains medium evidence and never creates an owner by itself.
    production_by_stem = {
        PurePosixPath(path).stem.lower(): path
        for path in facts
        if classify_repository_role(root, path)[0] == "implementation-owner"
    }
    for path in facts:
        if classify_repository_role(root, path)[0] != "test":
            continue
        test_stem = next(iter(_module_stems([path])), "")
        owner = production_by_stem.get(test_stem)
        if owner:
            relevant_paths.update({path, owner})
            proof_paths.add(path)
            relationship_rows.append((owner, path, "tested-by", "medium", "same-module-name"))

    # A production candidate needs a behavior-specific term in its local
    # basename or an extracted definition. Generic directory segments and
    # action words remain read-ranking inputs. Definition matches prioritize
    # bounded reads and stay diagnostic (query-specific-definition-evidence),
    # but a name match alone never qualifies ownership: only behavior,
    # relationship, literal, or explicit-scope evidence mints owners.
    definition_owner_paths: set[str] = set()
    definition_match_terms: dict[str, frozenset[str]] = {}
    semantic_owner_terms = _owner_query_terms(query_terms)
    for path, value in facts.items():
        if classify_repository_role(root, path)[0] != "implementation-owner" or not value.get("definitions"):
            continue
        if ui_surface_requested and not _is_ui_implementation_path(path):
            continue
        matching = semantic_owner_terms & _local_owner_identity_terms(path, value)
        if matching:
            definition_owner_paths.add(path)
            definition_match_terms[path] = frozenset(matching)
            relevant_paths.add(path)
            relationship_rows.append((path, path, "defines-symbol", "strong", "query-matched-definition-symbol"))

    # UI requests cannot select a literal source merely because it was seeded,
    # named similarly, or explicitly observed. It must independently prove
    # that it controls presentation.
    if ui_visibility_change:
        for path in exact_emitters:
            if path not in behavior_owner_paths and path not in ui_renderer_paths:
                owner_qualifications.pop(path, None)
        # Once a renderer-to-emitter module edge is known, a local name match
        # cannot override an incomplete behavior chain. Keep independently
        # proven UI behavior and explicit user scope, but fail closed on
        # definition/relationship fallbacks for that renderer.
        for chain in behavior_chain_rows:
            if chain["state"] == "complete":
                continue
            path = str(chain["renderer_path"])
            rules = owner_qualifications.get(path)
            if rules is None:
                continue
            rules.difference_update({"task-specific-definition", "task-specific-relationship"})
            if not rules:
                owner_qualifications.pop(path, None)

    # Definition matches alone never qualify ownership. As a last resort,
    # when no behavior, relationship, literal, or explicit evidence qualified
    # anything, a sole definition-backed candidate with caller or proof edges
    # may resolve instead of asking a question with no options. Contested
    # definitions (any other qualified evidence exists) stay unqualified.
    if not owner_qualifications and len(definition_owner_paths) == 1:
        sole = next(iter(definition_owner_paths))
        supported = any(
            (target == sole and kind in {"imports-module", "loads-module", "registered-by"})
            or (source == sole and kind == "tested-by")
            for source, target, kind, _, _ in relationship_rows
        )
        if supported:
            qualify_owner(sole, "definition-with-edges")
    if not owner_qualifications and definition_owner_paths:
        # Genuine fork: several files share the same matched definition
        # identity with no stronger evidence separating them. Surface the
        # fork as ambiguity (asking which one) instead of silently
        # dropping every candidate or picking by path order.
        by_signature: dict[frozenset[str], list[str]] = {}
        for path in sorted(definition_owner_paths):
            signature = definition_match_terms.get(path, frozenset())
            by_signature.setdefault(signature, []).append(path)
        for signature, paths in by_signature.items():
            if signature and len(paths) >= 2:
                for path in paths:
                    qualify_owner(path, "ambiguous-definition-fork")

    owner_paths, selected_qualification = _select_qualified_owners(owner_qualifications)
    owner_paths = set(sorted(owner_paths)[: limits.retained_owners])
    if len(owner_paths) == 1:
        owner = next(iter(owner_paths))
        relevant_paths.add(owner)
        owner_identity_tokens = {
            value.lower()
            for value in identities.get(owner, set())
            if len(value) >= 3
        }
        for path, value in facts.items():
            if classify_repository_role(root, path)[0] != "configuration":
                continue
            reference_values = {
                str(reference.get("value", "")).lower()
                for reference in value.get("references", [])
            }
            if owner_identity_tokens & reference_values:
                configuration_paths.add(path)
                relevant_paths.add(path)
                relationship_rows.append((path, owner, "configures-owner", "medium", "static-configuration-reference"))
        # Keep only callers/tests linked to the resolved owner.
        caller_paths = {
            source for source, target, kind, _, _ in relationship_rows
            if target == owner
            and source != owner
            and kind in {"imports-module", "loads-module", "registered-by"}
            and classify_repository_role(root, source)[0] != "test"
        }
        owner_stem = PurePosixPath(owner).stem.lower()
        direct_proof_paths = {
            target for source, target, kind, _, reason in relationship_rows
            if source == owner
            and kind == "tested-by"
            and reason in {"test-module-reference", "test-registration-reference"}
        }
        fallback_proof_paths = {
            target for source, target, kind, _, _ in relationship_rows
            if source == owner
            and kind == "tested-by"
            and (target in focus_seeds or owner_stem in _module_stems([target]))
        }
        # Direct executable test-to-owner evidence is the focused proof. A
        # naming convention is retained only when no direct edge exists.
        proof_paths = direct_proof_paths or fallback_proof_paths

    extra_seeds: list[dict[str, Any]] = []
    existing_paths = {str(row["path"]) for row in initial}
    for path in sorted(relevant_paths - existing_paths):
        source = "fresh-graph" if path in cached_paths else "symbol-name" if path in owner_paths else "module-name"
        reason = "fresh-cache-relationship" if source == "fresh-graph" else "static-owner-candidate" if source == "symbol-name" else "static-relationship-candidate"
        extra_seeds.append(seed(path, source, reason, content_fingerprint=content_hashes.get(path)))
    merged = candidates_from_seeds(root, [
        *[
            ScopeSeed(
                path=str(row["path"]),
                seed_sources=_stable_strings(row.get("seed_sources", [])),
                reason_codes=_stable_strings(row.get("reason_codes", [])),
                content_fingerprint=str(row["content_fingerprint"]) if row.get("content_fingerprint") else content_hashes.get(str(row["path"])),
            ).as_dict()
            for row in initial
        ],
        *extra_seeds,
    ], task_types)
    by_path = {str(row["path"]): row for row in merged}
    edges: list[dict[str, Any]] = []
    for source, target, kind, strength, reason in sorted(set(relationship_rows)):
        if source in by_path and target in by_path:
            edges.append(_edge(by_path[source]["candidate_id"], by_path[target]["candidate_id"], kind, strength, reason))
    edge_ids: dict[str, list[str]] = {path: [] for path in by_path}
    ids_to_path = {row["candidate_id"]: path for path, row in by_path.items()}
    for row in edges:
        for candidate_id in (row["from_candidate_id"], row["to_candidate_id"]):
            edge_ids[ids_to_path[candidate_id]].append(row["edge_id"])

    for path, row in by_path.items():
        reasons = set(row["reason_codes"])
        row["evidence_edge_ids"] = sorted(set(edge_ids[path]))
        presentation_owner = path in behavior_owner_paths or path in ui_renderer_paths
        repository_role = classify_repository_role(root, path)[0]
        test_only_task = (
            "qa" in {str(value) for value in task_types}
            and not ({"feature", "implementation", "bug", "refactor"} & {str(value) for value in task_types})
        )
        if path in exact_emitters and ui_visibility_change and not presentation_owner:
            row["role"] = "literal-emitter"
            row["status"] = "inspection-only"
            row["confidence"] = "high"
            reasons.add("literal-emitter-is-not-ui-visibility-owner")
        elif path in owner_paths and repository_role == "implementation-owner":
            row["role"] = "implementation-owner"
            row["status"] = "included"
            row["confidence"] = "high" if any(edge["strength"] == "strong" and row["candidate_id"] in {edge["from_candidate_id"], edge["to_candidate_id"]} for edge in edges) else "medium"
            reasons.add("bounded-static-owner-evidence")
            if selected_qualification:
                reasons.add(f"owner-qualified-by-{selected_qualification}")
            if "explicit-user-scope" in owner_qualifications.get(path, set()):
                reasons.add("explicit-scope-owner-evidence")
            if path in behavior_owner_paths:
                reasons.add("behavior-specific-owner-evidence")
            if path in definition_owner_paths:
                reasons.add("query-specific-definition-evidence")
        elif repository_role == "test" and path in owner_paths:
            row["role"] = "test"
            row["status"] = "included" if test_only_task else "proof-only"
            row["confidence"] = "high" if any(edge["strength"] == "strong" and row["candidate_id"] in {edge["from_candidate_id"], edge["to_candidate_id"]} for edge in edges) else "medium"
            reasons.add(
                "test-only-task-owner"
                if test_only_task
                else "test-path-cannot-own-production-change"
            )
        elif path in caller_paths:
            row["role"] = "caller"
            row["status"] = "inspection-only"
            row["confidence"] = "high"
            reasons.add("direct-runtime-caller")
        elif path in configuration_paths:
            row["role"] = "configuration"
            row["status"] = "inspection-only"
            row["confidence"] = "medium"
            reasons.add("direct-configuration-reference")
        elif path in proof_paths:
            row["role"] = "test"
            row["status"] = "proof-only"
            row["confidence"] = "high" if any(edge["strength"] == "strong" and edge["to_candidate_id"] == row["candidate_id"] for edge in edges) else "medium"
            reasons.add("focused-proof-owner-edge")
        elif repository_role == "test" and test_only_task:
            # A qa-only task already qualifies its own test-role candidates in
            # candidates_from_seeds(); nothing imports a test file, so requiring
            # the same relationship-edge proof that production code needs would
            # silently discard every lexically-discovered test candidate below.
            row["role"] = "test"
            row["status"] = "included"
            row["confidence"] = "high" if any(edge["strength"] == "strong" and row["candidate_id"] in {edge["from_candidate_id"], edge["to_candidate_id"]} for edge in edges) else "medium"
            reasons.add("test-only-task")
        elif row["role"] == "test" and set(row["seed_sources"]) <= {"lexical-body", "lexical-path", "repository-structure"}:
            row["status"] = "excluded"
            row["confidence"] = "none"
            reasons.add("lexical-only-no-owner-edge")
        elif len(owner_paths) == 1 and row["status"] not in {"rejected"}:
            row["status"] = "excluded"
            row["confidence"] = "none"
            reasons.add("no-selected-owner-edge")
        row["reason_codes"] = sorted(reasons)

    resolution_rejection_codes = {
        "module-alias-config-cycle",
        "module-alias-config-file-limit-reached",
        "module-alias-config-invalid",
        "module-alias-extends-depth-exceeded",
        "module-alias-extends-unsupported",
        "module-alias-pattern-unsupported",
        "module-alias-paths-invalid",
        "module-alias-target-invalid",
        "module-alias-target-outside-root",
    }
    resolution_reason_codes = sorted({
        code
        for event in module_resolution_events
        for code in event.reason_codes
    }) or ["module-resolution-not-exercised"]
    resolution_config_paths = sorted({
        path
        for event in module_resolution_events
        for path in event.config_paths
    })
    resolver_diagnostics = module_resolver.diagnostics()
    module_resolution = {
        "profile": "javascript-typescript",
        "state": (
            "ambiguous" if any(event.state == "ambiguous" for event in module_resolution_events)
            else "configured" if resolution_config_paths
            else "not-configured"
        ),
        "references_checked": len(module_resolution_events),
        "resolved": sum(event.state == "resolved" for event in module_resolution_events),
        "ambiguous": sum(event.state == "ambiguous" for event in module_resolution_events),
        "unresolved": sum(event.state == "unresolved" for event in module_resolution_events),
        "rejected": sum(bool(set(event.reason_codes) & resolution_rejection_codes) for event in module_resolution_events),
        "config_paths": resolution_config_paths,
        "config_files_read": resolver_diagnostics["files_read"],
        "config_bytes_read": resolver_diagnostics["bytes_read"],
        "config_limits": resolver_diagnostics["limits"],
        "reason_codes": resolution_reason_codes,
    }
    complete_behavior_chains = [
        row for row in behavior_chain_rows if row["state"] == "complete"
    ]
    complete_renderer_paths = {
        str(row["renderer_path"]) for row in complete_behavior_chains
    }
    behavior_chain_state = (
        "not-exercised" if not behavior_chain_rows
        else "conflicting" if len(complete_renderer_paths) > 1
        else "complete" if len(complete_renderer_paths) == 1
        else "partial" if any(row["state"] in {"partial", "incomplete"} for row in behavior_chain_rows)
        else "unresolved"
    )
    behavior_chains = {
        "state": behavior_chain_state,
        "chains": sorted(
            behavior_chain_rows,
            key=lambda row: (row["renderer_path"], row["source_path"], row["variant"]),
        ),
        "reason_codes": (
            ["behavior-chain-not-exercised"] if behavior_chain_state == "not-exercised"
            else ["multiple-complete-renderer-chains"] if behavior_chain_state == "conflicting"
            else ["single-complete-renderer-chain"] if behavior_chain_state == "complete"
            else ["behavior-chain-incomplete"] if behavior_chain_state == "partial"
            else ["behavior-chain-unresolved"]
        ),
    }
    limit_state_value = (
        "byte-limit-reached" if byte_limit_reached
        else "relationship-limit-reached" if relationship_limit_reached
        else "broad-limit-reached" if broad_limit_reached
        else "not-reached"
    )
    limit_state = {
        "state": limit_state_value,
        "termination_reason": loop_termination_reason,
        "cache_validation_files_read": cache_files_read,
        "broad_files_read": broad_files_read,
        "broad_file_limit": broad_read_limit,
        "relationship_files_read": relationship_files_read,
        "relationship_file_limit": limits.relationship_file_reads,
        "relationship_candidates": len(targeted_paths),
        "config_files_read": resolver_diagnostics["files_read"],
        "config_file_limit": resolver_diagnostics["limits"]["max_config_files"],
        "reason_codes": [
            "investigation-limits-not-reached"
            if limit_state_value == "not-reached"
            else f"investigation-{limit_state_value}"
        ],
    }
    alias_reason_codes = {
        code for event in renderer_resolution_events for code in event.reason_codes
    }
    if len(owner_paths) == 1:
        decision_reason = "owner-resolved"
        resolution_failure_reason: str | None = None
        status = "resolved"
    elif len(owner_paths) > 1:
        decision_reason = "multiple-evidence-backed-owners"
        resolution_failure_reason = decision_reason
        status = "ambiguous"
    elif behavior_chain_state == "conflicting":
        decision_reason = "multiple-complete-renderer-chains"
        resolution_failure_reason = decision_reason
        status = "ambiguous"
    elif behavior_chain_state == "partial":
        decision_reason = "renderer-behavior-chain-incomplete"
        resolution_failure_reason = decision_reason
        status = "unresolved"
    elif exact_emitters and "module-alias-ambiguous" in alias_reason_codes:
        decision_reason = "renderer-edge-ambiguous-module-alias"
        resolution_failure_reason = decision_reason
        status = "ambiguous"
    elif exact_emitters and alias_reason_codes & {
        "module-alias-unresolved", "module-base-url-unresolved",
        "module-alias-config-missing", "relative-module-reference-unresolved",
    }:
        decision_reason = "renderer-edge-unresolved-module-alias"
        resolution_failure_reason = decision_reason
        status = "unresolved"
    elif exact_emitters:
        decision_reason = "renderer-caller-edge-not-found"
        resolution_failure_reason = decision_reason
        status = "unresolved"
    elif limit_state_value != "not-reached":
        decision_reason = "implementation-owner-evidence-not-found-before-limit"
        resolution_failure_reason = decision_reason
        status = "blocked-by-limits"
    else:
        decision_reason = "implementation-owner-evidence-not-found"
        resolution_failure_reason = decision_reason
        status = "unresolved"
    if not owner_paths and status == "unresolved" and limit_state_value != "not-reached":
        status = "blocked-by-limits"
    candidate_by_id = {
        str(row["candidate_id"]): row for path, row in by_path.items() if row.get("candidate_id")
    }
    anchors, anchor_state = derive_anchors(
        exact_anchor_paths, explicit_anchor_paths, by_path, edges, candidate_by_id
    )
    ownership_selection = {
        "strategy": "qualification-precedence",
        "selected_rule": selected_qualification,
        "qualified_candidates": len(owner_qualifications),
        "selected_candidates": len(owner_paths),
        "rule_counts": {
            rule: sum(rule in rules for rules in owner_qualifications.values())
            for rule in OWNER_QUALIFICATION_PRECEDENCE
        },
        "reason_codes": [
            "owner-selected-by-qualifying-evidence" if owner_paths
            else "no-owner-qualifying-evidence"
        ],
    }
    report = {
        "state": status,
        "files_read": cache_files_read + len(facts),
        "bytes_read": total_bytes,
        "relationship_hops": min(limits.relationship_hops, 2 if edges else 0),
        # Compatibility alias. FSR-4 consumers should use decision_reason and
        # limit_state instead of interpreting a read-loop outcome as a scope
        # decision.
        "stop_reason": decision_reason,
        "decision_reason": decision_reason,
        "resolution_failure_reason": resolution_failure_reason,
        "limit_state": limit_state,
        "cache": cache_status,
        "module_resolution": module_resolution,
        "behavior_chains": behavior_chains,
        "ownership_selection": ownership_selection,
        "anchors": anchors,
        "anchor_state": anchor_state,
        "limits": limits.as_dict(),
        "evidence_packet_fingerprint": fingerprint({
            "requirements": [str(frame.get("requirement_id")) for frame in frames],
            "candidates": sorted((path, row["candidate_id"]) for path, row in by_path.items()),
            "edges": sorted(edge["edge_id"] for edge in edges),
            "anchors": sorted(row["anchor_id"] for row in anchors),
            "module_resolution": module_resolution,
            "behavior_chains": behavior_chains,
            "decision_reason": decision_reason,
            "resolution_failure_reason": resolution_failure_reason,
            "limit_state": limit_state,
            "ownership_selection": ownership_selection,
            "limits": limits.as_dict(),
        }),
    }
    return [by_path[path] for path in sorted(by_path)], sorted(edges, key=lambda row: row["edge_id"]), report


def evidence_document(
    root: Path,
    goal: str,
    requirement_frames: Iterable[dict[str, Any]],
    candidates: Iterable[dict[str, Any]],
    *,
    edges: Iterable[dict[str, Any]] = (),
    investigation: dict[str, Any] | None = None,
    host_reasoning: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the canonical v2 artifact and bind it with a decision hash."""
    candidate_rows = sorted((dict(row) for row in candidates), key=lambda row: (row["path"], row["candidate_id"]))
    edge_rows = sorted((dict(row) for row in edges), key=lambda row: str(row.get("edge_id", "")))
    included = [row["path"] for row in candidate_rows if row["status"] == "included"]
    # "included" already means "this is the editable scope for its
    # requirement" (candidates_from_seeds() only sets it for a role/task
    # combination it has already qualified, e.g. implementation-owner,
    # qa-only test, or documentation-only doc). Restricting this projection
    # to role == "implementation-owner" silently hid every other included
    # role from the Scope section even though scope_quality already accepted
    # it as the real editable set.
    implementation_owners = list(included)
    inspection = [row["path"] for row in candidate_rows if row["status"] == "inspection-only"]
    proof = [row["path"] for row in candidate_rows if row["status"] == "proof-only"]
    excluded = [
        {"path": row["path"], "reason_codes": row["reason_codes"]}
        for row in candidate_rows
        if row["status"] in {"excluded", "rejected"}
    ]
    investigation_row = dict(investigation or {
        "state": "not-run",
        "files_read": 0,
        "bytes_read": 0,
        "relationship_hops": 0,
        "stop_reason": "not-run",
        "cache": {"status": "not-checked", "reason_codes": ["graph-cache-not-checked"]},
        "module_resolution": {
            "profile": "javascript-typescript",
            "state": "not-configured",
            "references_checked": 0,
            "resolved": 0,
            "ambiguous": 0,
            "unresolved": 0,
            "rejected": 0,
            "config_paths": [],
            "reason_codes": ["module-resolution-not-exercised"],
        },
        "ownership_selection": {
            "strategy": "qualification-precedence",
            "selected_rule": None,
            "qualified_candidates": 0,
            "selected_candidates": 0,
            "rule_counts": {rule: 0 for rule in OWNER_QUALIFICATION_PRECEDENCE},
            "reason_codes": ["owner-selection-not-exercised"],
        },
        "limits": dict(LIMITS),
        "evidence_packet_fingerprint": fingerprint({"requirements": [], "candidates": [], "edges": [], "limits": LIMITS}),
    })
    state = str(investigation_row.get("state", "resolved" if implementation_owners else "unresolved"))
    if state == "not-run":
        state = "resolved" if implementation_owners else "unresolved"
    requirements = []
    resolved_reason_codes = (
        ["bounded-static-owner-resolved"]
        if implementation_owners and state == "resolved"
        else ["explicit-included-candidate"]
        if included
        else ["ownership-evidence-required"]
    )
    for frame in requirement_frames:
        requirements.append(
            {
                "requirement_id": str(frame.get("requirement_id") or frame.get("display_id")),
                "display_id": str(frame.get("display_id", "")),
                "statement_fingerprint": fingerprint(str(frame.get("statement", ""))),
                "query_terms": list(frame.get("query_terms", [])),
                "scope_state": state,
                "implementation_owners": implementation_owners,
                "inspection_paths": inspection,
                "proof_paths": proof,
                "excluded_candidates": excluded,
                "confidence": "high" if included else "low" if candidate_rows else "none",
                "reason_codes": resolved_reason_codes,
            }
        )
    document: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "type": EVIDENCE_TYPE,
        "target_identity_fingerprint": fingerprint({"root": root.resolve().as_posix()}),
        "goal_fingerprint": fingerprint(goal),
        "state": state,
        "requirements": requirements,
        "candidates": candidate_rows,
        "edges": edge_rows,
        "host_reasoning": host_reasoning or {"state": "not-requested", "proposal": None},
        "investigation": investigation_row,
        "limits": dict(investigation_row.get("limits", LIMITS)),
        "summary": {
            "included": len(included),
            "inspection_only": len(inspection),
            "proof_only": len(proof),
            "excluded": sum(row["status"] == "excluded" for row in candidate_rows),
            "rejected": sum(row["status"] == "rejected" for row in candidate_rows),
        },
    }
    if host_reasoning is None:
        route = host_reasoning_route(document)
        document["host_reasoning"] = {
            "state": "requested" if route["state"] == "requested" else "not-requested",
            "proposal": None,
        }
    document["decision_fingerprint"] = fingerprint(document)
    return document


def verify_decision_fingerprint(document: dict[str, Any]) -> bool:
    candidate = dict(document)
    observed = candidate.pop("decision_fingerprint", None)
    return isinstance(observed, str) and observed == fingerprint(candidate)


def requested_scope_mode(goal: str, task_types: Iterable[str]) -> str:
    """Classify the editable scope contract without inferring it from target selection."""
    lowered = " ".join(str(goal).lower().split())
    production_terms = (
        "implement", "feature", "endpoint", "refactor", "production", "service",
        "application", "source code", "end to end", "end-to-end",
    )
    documentation_signal = any(term in lowered for term in (
        "documentation only", "docs only", "readme only", "changelog only",
        "markdown documentation", "readme documentation",
    ))
    test_signal = any(term in lowered for term in (
        "test only", "tests only", "add tests", "add a regression test", "update tests", "test coverage only",
    ))
    production_signal = any(term in lowered for term in production_terms)
    if documentation_signal and test_signal and not production_signal:
        return "supporting-assets-only"
    if documentation_signal and not production_signal:
        return "documentation-only"
    if test_signal and not production_signal:
        return "test-only"
    task_set = {str(value).lower() for value in task_types}
    if task_set == {"documentation"}:
        return "documentation-only"
    if task_set == {"qa"}:
        return "test-only"
    return "code-change"


def _validated_scope_question_options(
    document: dict[str, Any],
    maximum: int,
) -> tuple[list[str], list[dict[str, Any]], dict[str, Any]]:
    """Return only strong, role-correct owner alternatives.

    Read hints, callers, emitters, proof paths, and lexical-only candidates can
    never become question options. Every offered path must cite a strong edge
    from the same evidence document and an owner-qualification rule.
    """
    edges = {
        str(row.get("edge_id")): row
        for row in document.get("edges", [])
        if isinstance(row, dict)
    }
    allowed_qualifications = {
        f"owner-qualified-by-{rule}" for rule in OWNER_QUALIFICATION_PRECEDENCE
    }
    eligible: list[dict[str, Any]] = []
    rejected = 0
    for candidate in document.get("candidates", []):
        if not isinstance(candidate, dict):
            continue
        reasons = {str(value) for value in candidate.get("reason_codes", [])}
        candidate_id = str(candidate.get("candidate_id", ""))
        supporting_edges = sorted(
            edge_id for edge_id in candidate.get("evidence_edge_ids", [])
            if edge_id in edges
            and str(edges[edge_id].get("strength")) == "strong"
            and candidate_id in {
                str(edges[edge_id].get("from_candidate_id", "")),
                str(edges[edge_id].get("to_candidate_id", "")),
            }
        )
        valid = (
            candidate.get("role") == "implementation-owner"
            and candidate.get("status") == "included"
            and candidate.get("confidence") == "high"
            and "bounded-static-owner-evidence" in reasons
            and bool(reasons & allowed_qualifications)
            and bool(supporting_edges)
        )
        if not valid:
            if candidate.get("status") == "included":
                rejected += 1
            continue
        qualification = next(
            (value for value in sorted(reasons) if value in allowed_qualifications),
            "owner-qualified-by-static-evidence",
        )
        eligible.append({
            "path": str(candidate.get("path")),
            "evidence": qualification.removeprefix("owner-qualified-by-").replace("-", " "),
            "missing_discriminator": "which runtime path reproduces the requested behavior",
            "evidence_edge_ids": supporting_edges,
        })
    eligible = sorted(eligible, key=lambda row: row["path"])
    offered = eligible[:max(1, min(maximum, SCOPE_QUESTION_OPTION_CAP))]
    validation = {
        "state": "validated" if offered else "no-supported-options",
        "eligible_options": len(eligible),
        "offered_options": len(offered),
        "rejected_candidates": rejected,
        "truncated": len(eligible) > len(offered),
        "reason_codes": [
            "scope-question-options-evidence-validated"
            if offered else "scope-question-has-no-supported-owner-options"
        ],
    }
    return [row["path"] for row in offered], offered, validation


def _complexity_metrics(
    root: Path,
    document: dict[str, Any],
) -> dict[str, Any]:
    """Extract quantitative scope-complexity metrics from scope evidence.

    Delegates to :mod:`metrics_extractor` so the same three-tier pipeline
    (likely_impacted_files → scope_evidence → mapper cache) is used by
    both the standalone extraction path and the consolidated
    ``assess_scope_quality()`` path.
    """
    try:
        import metrics_extractor as _m
    except Exception:
        return {"source": "unavailable", "error": "metrics_extractor-unavailable"}
    return _m.extract_scope_complexity_metrics(root, document)


def assess_scope_quality(
    root: Path,
    goal: str,
    task_types: Iterable[str],
    document: dict[str, Any],
    *,
    compute_complexity: bool = False,
) -> dict[str, Any]:
    """Fail closed unless the evidence supports this request's repository role.

    Target selection and scope quality are deliberately independent: an
    explicit ``--root`` proves where to inspect, never which file owns a
    requested behavior.

    When ``compute_complexity`` is True, quantitative scope-complexity
    metrics are extracted alongside the scope-quality verdict and returned
    in the ``complexity_metrics`` field. This is the consolidated path for
    AIDLC mode selection (Phase 4); the standalone
    :func:`~metrics_extractor.extract_scope_complexity_metrics` remains the
    primary path for ``task-start.py``.
    """
    mode = requested_scope_mode(goal, task_types)
    errors: list[str] = []
    if not verify_decision_fingerprint(document):
        errors.append("scope-decision-fingerprint-invalid")
    expected_target = fingerprint({"root": root.resolve().as_posix()})
    if document.get("target_identity_fingerprint") != expected_target:
        errors.append("scope-target-identity-mismatch")
    candidates = [row for row in document.get("candidates", []) if isinstance(row, dict)]
    requirements = [row for row in document.get("requirements", []) if isinstance(row, dict)]
    evidence_state = str(document.get("state", "unresolved"))
    accepted_paths: list[str] = []
    missing_requirements: list[str] = []

    if mode == "supporting-assets-only":
        accepted_paths = sorted({
            str(row.get("path")) for row in candidates
            if row.get("role") in {"documentation", "test"}
            and row.get("status") in {"included", "proof-only"}
        })
        roles_by_path = {
            str(row.get("path")): str(row.get("role")) for row in candidates
            if str(row.get("path")) in accepted_paths
        }
        for requirement in requirements:
            terms = {str(value).lower() for value in requirement.get("query_terms", [])}
            required_role = "test" if terms & {"test", "tests", "regression", "coverage"} else "documentation" if terms & {"readme", "documentation", "docs", "changelog", "markdown"} else None
            if required_role and required_role not in set(roles_by_path.values()):
                missing_requirements.append(str(requirement.get("requirement_id", "unknown")))
        if not accepted_paths or missing_requirements:
            errors.append("supporting-asset-owner-required")
    elif mode == "documentation-only":
        accepted_paths = sorted({
            str(row.get("path")) for row in candidates
            if row.get("role") == "documentation" and row.get("status") == "included"
        })
        if not accepted_paths:
            errors.append("documentation-owner-required")
    elif mode == "test-only":
        accepted_paths = sorted({
            str(row.get("path")) for row in candidates
            if row.get("role") == "test" and row.get("status") in {"included", "proof-only"}
        })
        if not accepted_paths:
            errors.append("test-owner-required")
    else:
        if evidence_state not in {"resolved"}:
            errors.append(f"scope-state-{evidence_state}")
        for requirement in requirements:
            owners = sorted({str(value) for value in requirement.get("implementation_owners", []) if str(value)})
            if not owners:
                missing_requirements.append(str(requirement.get("requirement_id", "unknown")))
            accepted_paths.extend(owners)
        if missing_requirements:
            errors.append("implementation-owner-required")
    investigation = document.get("investigation", {}) if isinstance(document.get("investigation"), dict) else {}
    anchor_insufficient = (
        str(investigation.get("anchor_state", "")) == "insufficient" and mode == "code-change"
    )
    decision_reason = str(investigation.get("decision_reason") or investigation.get("stop_reason") or "")
    resolution_failure = investigation.get("resolution_failure_reason")
    if errors:
        if resolution_failure and str(resolution_failure) not in errors:
            integrity_prefix = sum(
                value in {"scope-decision-fingerprint-invalid", "scope-target-identity-mismatch"}
                for value in errors[:2]
            )
            errors.insert(integrity_prefix, str(resolution_failure))
        errors = list(dict.fromkeys(errors))

    status = "passed" if not errors else "blocked"
    question = None
    question_validation = {
        "state": "not-required",
        "eligible_options": 0,
        "offered_options": 0,
        "rejected_candidates": 0,
        "truncated": False,
        "reason_codes": ["scope-question-not-required"],
    }
    if status == "blocked" and mode == "code-change":
        question_limit = int(document.get("limits", {}).get("scope_question_options", 3))
        options, option_evidence, question_validation = _validated_scope_question_options(
            document, question_limit
        )
        if evidence_state in {"ambiguous", "conflicting"} and options:
            question = {
                "question_id": "SCOPE-Q1",
                "question": "Which evidence-backed implementation owner is the intended editable boundary?",
                "options": options,
                "option_evidence": option_evidence,
                "answer_format": "Reply with one listed path, or provide a different known implementation-owner path.",
                "boundary": "Every listed path has a strong owner-qualification edge. Read hints, callers, emitters, proof paths, and lexical-only matches are excluded. This confirms scope only; it does not approve implementation or create a Planning Lock.",
            }
        elif anchor_insufficient:
            question = {
                "question_id": "SCOPE-QA",
                "question": "Which named command, route, symbol, or existing path anchors this behavior? No task anchor could be derived from the request, so no file is promoted.",
                "options": [],
                "option_evidence": [],
                "answer_format": "Provide one known module, symbol, path, or behavior label grounded in the request or repository; do not invent paths.",
                "boundary": "This evidence-gap clarification grants no implementation authority or Planning Lock.",
            }
        else:
            question = {
                "question_id": "SCOPE-Q1",
                "question": "What concrete module, symbol, caller, or reproduction entry point owns this behavior?",
                "options": [],
                "option_evidence": [],
                "answer_format": "Provide one known module, symbol, caller, or reproduction clue; do not choose from unsupported repository candidates.",
                "boundary": "TailTrail found no query- or relationship-grounded, high-confidence owner option. This clarification grants no implementation authority or Planning Lock.",
            }
    primary_reason = errors[0] if errors else f"{mode}-scope-supported"
    complexity_metrics: dict[str, Any] = {}
    if compute_complexity:
        complexity_metrics = _complexity_metrics(root, document)
    return {
        "schema_version": "1",
        "type": "tailtrail-scope-quality-assessment",
        "status": status,
        "blocking": bool(errors),
        "mode": mode,
        "evidence_state": evidence_state,
        "decision_fingerprint": document.get("decision_fingerprint"),
        "target_identity_fingerprint": document.get("target_identity_fingerprint"),
        "accepted_paths": sorted(dict.fromkeys(accepted_paths)),
        "missing_requirement_ids": missing_requirements,
        "reason_codes": errors or [f"{mode}-scope-supported"],
        "primary_reason": primary_reason,
        "question": question,
        "question_validation": question_validation,
        "complexity_metrics": complexity_metrics,
        "boundary": "Scope quality is evidence-based and independent of target-root selection. Passing this gate grants no execution authority.",
    }


def decision_binding(root: Path, document: dict[str, Any], target_identity: dict[str, Any]) -> dict[str, Any]:
    """Bind one verified scope decision to the exact Planning Lock target."""
    if not verify_decision_fingerprint(document):
        raise ValueError("scope evidence decision fingerprint is invalid")
    expected_target = fingerprint({"root": root.resolve().as_posix()})
    if document.get("target_identity_fingerprint") != expected_target:
        raise ValueError("scope evidence belongs to a different target root")
    target_fingerprint = str(target_identity.get("fingerprint", ""))
    if not target_fingerprint.startswith("sha256:"):
        raise ValueError("target identity fingerprint is missing")
    return {
        "schema_version": "1",
        "type": "tailtrail-scope-decision-binding",
        "state": document.get("state"),
        "decision_fingerprint": document["decision_fingerprint"],
        "evidence_packet_fingerprint": document.get("investigation", {}).get("evidence_packet_fingerprint"),
        "scope_target_identity_fingerprint": document.get("target_identity_fingerprint"),
        "planning_target_identity_fingerprint": target_fingerprint,
    }


def _host_reasoning_eligible_candidates(document: dict[str, Any]) -> list[dict[str, Any]]:
    """Return strong, hash-bound alternatives a host is allowed to compare."""
    edges = {
        str(row.get("edge_id")): row
        for row in document.get("edges", [])
        if isinstance(row, dict) and row.get("strength") == "strong"
    }
    eligible: list[dict[str, Any]] = []
    for candidate in document.get("candidates", []):
        if not isinstance(candidate, dict):
            continue
        candidate_id = str(candidate.get("candidate_id", ""))
        edge_ids = sorted(
            str(edge_id) for edge_id in candidate.get("evidence_edge_ids", [])
            if str(edge_id) in edges
            and candidate_id in {
                str(edges[str(edge_id)].get("from_candidate_id", "")),
                str(edges[str(edge_id)].get("to_candidate_id", "")),
            }
        )
        reasons = {str(value) for value in candidate.get("reason_codes", [])}
        if not (
            candidate.get("role") == "implementation-owner"
            and candidate.get("status") == "included"
            and candidate.get("confidence") == "high"
            and isinstance(candidate.get("content_fingerprint"), str)
            and str(candidate["content_fingerprint"]).startswith("sha256:")
            and "bounded-static-owner-evidence" in reasons
            and edge_ids
        ):
            continue
        eligible.append({
            "path": str(candidate.get("path")),
            "candidate_id": candidate_id,
            "content_fingerprint": str(candidate["content_fingerprint"]),
            "evidence_edge_ids": edge_ids,
        })
    return sorted(eligible, key=lambda row: row["path"])


def host_reasoning_route(document: dict[str, Any]) -> dict[str, Any]:
    """Describe whether deterministic evidence needs one active-host decision."""
    eligible = _host_reasoning_eligible_candidates(document)
    state = str(document.get("state", "unresolved"))
    if state == "resolved":
        route_state = "not-required"
        reason = "deterministic-scope-already-resolved"
    elif state in {"ambiguous", "partially-resolved"} and len(eligible) >= 2:
        route_state = "requested"
        reason = "supported-owner-alternatives-require-host-reasoning"
    else:
        route_state = "unavailable"
        reason = "host-reasoning-has-no-supported-owner-alternatives"
    return {
        "state": route_state,
        "reason_code": reason,
        "eligible_candidates": eligible,
        "requirement_ids": sorted(
            str(row.get("requirement_id"))
            for row in document.get("requirements", [])
            if isinstance(row, dict) and row.get("requirement_id")
        ),
        "authority": "evidence-refinement-only",
        "boundary": "The active host may select only a hash-bound, strongly evidenced alternative. It cannot create evidence, approve work, create a Planning Lock, or grant execution authority.",
    }


def host_reasoning_packet(document: dict[str, Any]) -> dict[str, Any]:
    """Project a sanitized, source-body-free packet for the active host.

    v2 (Stage 5) is a strict superset of v1: every v1 field is byte-stable
    and new evidence sections are additive. Use packet_v1_projection() for
    v1-only consumers.
    """
    if not verify_decision_fingerprint(document):
        raise ValueError("scope evidence decision fingerprint is invalid")
    investigation = document.get("investigation", {}) if isinstance(document.get("investigation"), dict) else {}
    cache_section, v2_sections = _packet_v2_sections(document, investigation)
    packet = {
        "schema_version": "1",
        "type": "tailtrail-navigator-host-scope-packet",
        "scope_evidence_fingerprint": document.get("decision_fingerprint"),
        "evidence_packet_fingerprint": document.get("investigation", {}).get("evidence_packet_fingerprint"),
        "target_identity_fingerprint": document.get("target_identity_fingerprint"),
        "goal_fingerprint": document.get("goal_fingerprint"),
        "requirements": document.get("requirements", []),
        "candidates": document.get("candidates", []),
        "edges": document.get("edges", []),
        "limits": document.get("limits", {}),
        "route": host_reasoning_route(document),
        "instructions": {
            "required": [
                "map every change requirement to supported implementation ownership",
                "identify callers, proof, alternatives, preservation boundaries, and uncertainty",
                "reference saved edge IDs for every material path claim",
            ],
            "forbidden": [
                "private chain-of-thought",
                "invented paths or evidence",
                "approval or execution authority",
                "raw source bodies",
            ],
        },
        "packet_version": _PACKET_VERSION,
        **v2_sections,
        "cache": cache_section,
    }
    packet["packet_fingerprint"] = fingerprint(packet)
    return packet


_PACKET_VERSION = 2
_SUPPORTED_PACKET_MAJORS = (1, 2)

_V1_PACKET_KEYS = (
    "schema_version", "type", "scope_evidence_fingerprint",
    "evidence_packet_fingerprint", "target_identity_fingerprint",
    "goal_fingerprint", "requirements", "candidates", "edges", "limits",
    "route", "instructions",
)


def packet_v1_projection(packet: dict[str, Any]) -> dict[str, Any]:
    """Server-side v1 projection: v1 fields byte-stable, v2 sections dropped (Stage 5)."""
    if not isinstance(packet, dict):
        raise ValueError("host packet must be an object")
    return {key: packet[key] for key in _V1_PACKET_KEYS if key in packet}


def negotiate_packet_version(packet: dict[str, Any]) -> int:
    """Fail closed on unknown host packet major versions (Stage 5)."""
    if not isinstance(packet, dict):
        raise ValueError("host packet must be an object")
    version = packet.get("packet_version", 1)
    if version not in _SUPPORTED_PACKET_MAJORS:
        raise ValueError(f"unsupported host packet version: {version!r}")
    return int(version)


def _packet_v2_sections(
    document: dict[str, Any], investigation: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build the additive v2 evidence sections (Stage 5).

    Paths, hashes, relation kinds, and role labels only — never source
    bodies, credentials, or untrusted instructions.
    """
    candidates = [row for row in document.get("candidates", []) if isinstance(row, dict)]
    edges = [row for row in document.get("edges", []) if isinstance(row, dict)]
    candidate_by_id = {
        str(row.get("candidate_id")): row for row in candidates if row.get("candidate_id")
    }
    by_path = {str(row.get("path")): row for row in candidates if row.get("path")}
    anchors = [
        {"id": str(item.get("anchor_id", "")), "role": str(item.get("role", "")),
         "path": str(item.get("path", ""))}
        for item in investigation.get("anchors", [])
        if isinstance(item, dict) and item.get("anchor_id") and item.get("path")
    ]
    anchor_paths = {item["path"] for item in anchors}
    adjacency = candidate_edge_adjacency(edges, candidate_by_id)
    reached: set[str] = set()
    for path in anchor_paths:
        reached.update(p for p in connected_files([path], adjacency) if p != path)
    covered_roles = sorted({
        item["role"] for item in anchors
        if item["path"] in by_path or item["path"] in reached
    })
    cache_status = str(investigation.get("cache", {}).get("status", "not-checked"))
    if cache_status == "missing":
        state = "missing"
    elif cache_status in {"fresh", "stale", "invalid"}:
        base = "stale" if cache_status == "invalid" else cache_status
        state = f"{base}-relevant" if covered_roles else f"{base}-insufficient"
    else:
        state = cache_status
    graph_fingerprint = fingerprint({
        "candidates": sorted((str(row.get("path", "")), str(row.get("candidate_id", ""))) for row in candidates),
        "edges": sorted(str(row.get("edge_id", "")) for row in edges),
    })
    slice_fingerprint = fingerprint({
        "anchors": sorted(item["id"] for item in anchors),
        "coverage": covered_roles,
    })
    relationships = []
    for row in edges:
        frm = candidate_by_id.get(str(row.get("from_candidate_id", "")), {})
        to = candidate_by_id.get(str(row.get("to_candidate_id", "")), {})
        if isinstance(frm, dict) and isinstance(to, dict) and frm.get("path") and to.get("path"):
            relationships.append({
                "from": str(frm["path"]), "to": str(to["path"]), "kind": str(row.get("kind", "")),
            })
    relationships.sort(key=lambda row: (row["from"], row["to"], row["kind"]))
    existing = [
        {"path": path, "roles": [str(by_path[path].get("role", "unknown"))]}
        for path in sorted(by_path) if by_path[path].get("status") == "included"
    ]
    conventions = []
    for path in sorted(by_path):
        codes = [str(code) for code in by_path[path].get("reason_codes", []) if "convention" in str(code)]
        if codes and by_path[path].get("status") in {"included", "inspection-only"}:
            conventions.append({"path": path, "reason": sorted(codes)[0]})
    excluded = []
    for path in sorted(by_path):
        row = by_path[path]
        if row.get("status") in {"excluded", "rejected"}:
            codes = [str(code) for code in row.get("reason_codes", [])]
            excluded.append({"path": path, "reason": sorted(codes)[0] if codes else str(row.get("status"))})
    read_order = list(dict.fromkeys(
        [row["path"] for row in existing]
        + [row["path"] for row in conventions if row["path"] not in {item["path"] for item in existing}]
    ))
    doc_limits = document.get("limits", {}) if isinstance(document.get("limits"), dict) else {}
    read_budget = {
        "files_read": int(investigation.get("files_read", 0) or 0),
        "max_files": int(doc_limits.get("initial_file_reads", 0) or 0)
        + int(doc_limits.get("escalation_file_reads", 0) or 0),
    }
    cache_section = {
        "state": state,
        "graph_fingerprint": graph_fingerprint,
        "slice_fingerprint": slice_fingerprint,
        "coverage": covered_roles,
    }
    sections = {
        "anchors": anchors,
        "relationships": relationships,
        "existing_candidates": existing,
        "conventions": conventions,
        "excluded_candidates": excluded,
        "suggested_read_order": read_order,
        "read_budget": read_budget,
    }
    return cache_section, sections


def resolve_anchor_slice(
    root: Path,
    paths: Iterable[str],
    literals: Iterable[str] = (),
    coverage_required: Iterable[str] = (),
) -> dict[str, Any]:
    """Build a lifecycle anchor slice from task-supported paths (Stage 5).

    No discovery: only existing files from explicit paths plus path-like
    quoted literals. Sensitive and non-file inputs are skipped.
    """
    anchors: dict[str, dict[str, Any]] = {}

    def add(path: str, confidence: str, reason: str, evidence: list[str]) -> None:
        anchor_id = f"anchor:entrypoint:{path}"
        if anchor_id not in anchors:
            anchors[anchor_id] = {
                "anchor_id": anchor_id,
                "role": "entrypoint",
                "path": path,
                "confidence": confidence,
                "reason_codes": [reason],
                "evidence_refs": {"seeds": evidence},
            }

    for value in paths:
        normalized, rejection = normalize_repository_path(root, str(value))
        if rejection or not normalized or sensitive_path_reason(normalized):
            continue
        if (root.resolve() / normalized).is_file():
            add(normalized, "medium", "anchor-explicit-task-path", ["explicit-path"])
    for value in literals:
        normalized, rejection = normalize_repository_path(root, str(value))
        if rejection or not normalized or sensitive_path_reason(normalized):
            continue
        if (root.resolve() / normalized).is_file():
            add(normalized, "high", "anchor-exact-task-reference", ["exact-phrase-in-bounded-body"])
    ordered = sorted(anchors.values(), key=lambda row: (row["role"], row["path"]))
    return anchor_slice(ordered, coverage_required=coverage_required)
_CONVENTION_INTEGRATION_KINDS = {"imports-module", "loads-module", "registered-by", "configures-owner"}
_CONVENTION_INTEGRATION_REASONS = {"static-configuration-reference", "static-registration-reference"}

_NEW_PATH_DECISION = "host-proposed-new-path"


def _convention_link_present(
    candidates: dict[str, Any],
    edges: dict[str, Any],
    anchor_paths: list[str],
    convention_refs: list[str],
) -> bool:
    """Check a proposed new path links to convention or integration evidence (Stage 2)."""
    for ref in convention_refs:
        edge = edges.get(ref, {})
        if edge.get("kind") in _CONVENTION_INTEGRATION_KINDS:
            return True
        if edge.get("reason") in _CONVENTION_INTEGRATION_REASONS or "convention" in str(edge.get("reason", "")):
            return True
    for anchor in anchor_paths:
        reason_codes = candidates.get(anchor, {}).get("reason_codes", [])
        if any("convention" in str(code) for code in reason_codes):
            return True
    return False


def validate_host_proposal(root: Path, packet: dict[str, Any], proposal: dict[str, Any]) -> dict[str, Any]:
    """Validate a host scope proposal without trusting host confidence."""
    errors: list[str] = []
    packet_body = dict(packet)
    observed_packet_fingerprint = packet_body.pop("packet_fingerprint", None)
    if not isinstance(observed_packet_fingerprint, str) or fingerprint(packet_body) != observed_packet_fingerprint:
        errors.append("host-evidence-packet-integrity-invalid")
    try:
        negotiate_packet_version(packet)
    except ValueError:
        errors.append("unsupported-packet-version")
    if proposal.get("schema_version") != "2" or proposal.get("type") != "tailtrail-navigator-host-scope-proposal":
        errors.append("host-proposal-contract-version-invalid")
    proposal_fields = {
        "schema_version", "type", "host", "evidence_packet_fingerprint",
        "scope_evidence_fingerprint", "target_identity_fingerprint", "goal_fingerprint",
        "scope_state", "authority", "requirements", "private_reasoning_excluded",
    }
    missing_proposal_fields = proposal_fields - set(proposal)
    unexpected_proposal_fields = set(proposal) - proposal_fields
    if missing_proposal_fields:
        errors.append("host-proposal-required-fields-missing")
    if unexpected_proposal_fields:
        errors.append("host-proposal-additional-fields-rejected")
    host = str(proposal.get("host", ""))
    if host not in {"codex", "claude", "copilot"}:
        errors.append("unsupported-host")
    if proposal.get("evidence_packet_fingerprint") != packet.get("packet_fingerprint"):
        errors.append("evidence-packet-fingerprint-mismatch")
    for field in ("scope_evidence_fingerprint", "target_identity_fingerprint", "goal_fingerprint"):
        packet_field = {
            "scope_evidence_fingerprint": "scope_evidence_fingerprint",
            "target_identity_fingerprint": "target_identity_fingerprint",
            "goal_fingerprint": "goal_fingerprint",
        }[field]
        if proposal.get(field) != packet.get(packet_field):
            errors.append(f"{field.replace('_', '-')}-mismatch")
    if proposal.get("authority") != "evidence-refinement-only":
        errors.append("host-authority-escalation-rejected")
    forbidden_authority_fields = {
        "approved", "approval", "execution_authority", "implementation_authority",
        "planning_lock", "planning_lock_created", "run_id", "execute", "write_scope",
    }
    if any(str(key) in forbidden_authority_fields for key in proposal):
        errors.append("host-authority-escalation-rejected")
    route = packet.get("route", {}) if isinstance(packet.get("route"), dict) else {}
    if route.get("state") != "requested":
        errors.append("host-reasoning-not-requested")
    scope_state = str(proposal.get("scope_state", ""))
    if scope_state not in {"proposed-resolved", "needs-confirmation", "unresolved", "conflicting"}:
        errors.append("invalid-scope-state")
    if proposal.get("private_reasoning_excluded") is not True:
        errors.append("private-reasoning-boundary-missing")

    candidates = {str(row.get("path")): row for row in packet.get("candidates", []) if isinstance(row, dict)}
    edges = {str(row.get("edge_id")): row for row in packet.get("edges", []) if isinstance(row, dict)}
    candidate_by_id = {str(row.get("candidate_id")): row for row in candidates.values()}
    expected_requirements = {str(row.get("requirement_id")) for row in packet.get("requirements", [])}
    packet_requirements = {
        str(row.get("requirement_id")): row
        for row in packet.get("requirements", [])
        if isinstance(row, dict)
    }
    proposed_requirements = proposal.get("requirements", [])
    if not isinstance(proposed_requirements, list):
        proposed_requirements = []
        errors.append("requirements-must-be-array")
    observed_requirements = {str(row.get("requirement_id")) for row in proposed_requirements if isinstance(row, dict)}
    if observed_requirements != expected_requirements:
        errors.append("requirement-coverage-mismatch")
    if len(observed_requirements) != len(proposed_requirements):
        errors.append("duplicate-requirement-proposal")

    eligible_owner_paths = {
        str(row.get("path"))
        for row in route.get("eligible_candidates", [])
        if isinstance(row, dict)
    }

    normalized_requirements: list[dict[str, Any]] = []
    for row in proposed_requirements:
        if not isinstance(row, dict):
            errors.append("requirement-proposal-invalid")
            continue
        requirement_fields = {
            "requirement_id", "statement_fingerprint", "implementation_owners",
            "callers", "inspection_paths", "proof_paths", "excluded_candidates",
            "path_claims", "preservation_boundaries", "evidence_edge_ids",
            "confidence", "decision_reasons", "alternatives", "uncertainties",
        }
        requirement_optional_fields = {"proposed_new_path", "anchor_paths", "convention_refs"}
        if requirement_fields - set(row):
            errors.append("requirement-proposal-required-fields-missing")
        if set(row) - requirement_fields - requirement_optional_fields:
            errors.append("requirement-proposal-additional-fields-rejected")
        requirement_id = str(row.get("requirement_id", ""))
        expected_statement = packet_requirements.get(requirement_id, {}).get("statement_fingerprint")
        if row.get("statement_fingerprint") != expected_statement:
            errors.append(f"{requirement_id}:statement-fingerprint-mismatch")
        owners = sorted(dict.fromkeys(str(value) for value in row.get("implementation_owners", [])))
        callers = sorted(dict.fromkeys(str(value) for value in row.get("callers", [])))
        inspection = sorted(dict.fromkeys(str(value) for value in row.get("inspection_paths", [])))
        proof = sorted(dict.fromkeys(str(value) for value in row.get("proof_paths", [])))
        excluded = sorted(dict.fromkeys(str(value) for value in row.get("excluded_candidates", [])))
        references = sorted(dict.fromkeys(str(value) for value in row.get("evidence_edge_ids", [])))
        alternatives = [str(value) for value in row.get("alternatives", []) if str(value).strip()]
        uncertainties = [str(value) for value in row.get("uncertainties", []) if str(value).strip()]
        decision_reasons = [str(value) for value in row.get("decision_reasons", []) if str(value).strip()]
        preservation = [str(value) for value in row.get("preservation_boundaries", []) if str(value).strip()]
        raw_new_path = row.get("proposed_new_path")
        if "anchor_paths" in row and not isinstance(row.get("anchor_paths"), list):
            errors.append(f"{requirement_id}:anchor-paths-invalid")
        if "convention_refs" in row and not isinstance(row.get("convention_refs"), list):
            errors.append(f"{requirement_id}:convention-refs-invalid")
        anchor_paths = (
            sorted(dict.fromkeys(
                str(value).replace("\\", "/") for value in row.get("anchor_paths", [])
                if isinstance(value, str) and str(value).strip()
            )) if isinstance(row.get("anchor_paths"), list) else []
        )
        convention_refs = (
            sorted(dict.fromkeys(str(value) for value in row.get("convention_refs", []) if isinstance(value, str)))
            if isinstance(row.get("convention_refs"), list) else []
        )
        has_new_path_fields = "proposed_new_path" in row or "anchor_paths" in row or "convention_refs" in row
        new_path: str | None = None
        new_path_decision = "existing-candidate"
        if has_new_path_fields:
            new_path_decision = _NEW_PATH_DECISION
            if not isinstance(raw_new_path, str) or not raw_new_path.strip():
                errors.append(f"{requirement_id}:invalid-proposed-path")
            else:
                normalized_new, path_rejection = normalize_repository_path(root, raw_new_path.strip())
                if path_rejection:
                    errors.append(f"{requirement_id}:invalid-proposed-path:{path_rejection}")
                elif sensitive_path_reason(normalized_new or ""):
                    errors.append(f"{requirement_id}:sensitive-proposed-path")
                elif (normalized_new or "") in candidates:
                    errors.append(f"{requirement_id}:proposed-path-already-candidate")
                else:
                    new_path = normalized_new
            if owners:
                errors.append(f"{requirement_id}:new-path-cannot-claim-owner")
            if not anchor_paths:
                errors.append(f"{requirement_id}:anchor-paths-required")
            for anchor in anchor_paths:
                anchor_candidate = candidates.get(anchor)
                if anchor_candidate is None:
                    errors.append(f"{requirement_id}:unknown-anchor-path:{anchor}")
                elif anchor_candidate.get("status") != "included":
                    errors.append(f"{requirement_id}:anchor-not-included:{anchor}")
            if anchor_paths and not set(anchor_paths).issubset(set(inspection)):
                errors.append(f"{requirement_id}:anchor-missing-inspection-claim")
            if not convention_refs:
                errors.append(f"{requirement_id}:convention-refs-required")
            for ref in convention_refs:
                if ref not in edges:
                    errors.append(f"{requirement_id}:unknown-convention-ref:{ref}")
                elif ref not in references:
                    errors.append(f"{requirement_id}:convention-ref-not-evidenced:{ref}")
            if convention_refs and not _convention_link_present(candidates, edges, anchor_paths, convention_refs):
                errors.append(f"{requirement_id}:convention-link-missing")
        claims = row.get("path_claims", [])
        if not isinstance(claims, list):
            claims = []
            errors.append(f"{requirement_id}:path-claims-must-be-array")
        claim_by_path: dict[str, dict[str, Any]] = {}
        for claim in claims:
            if not isinstance(claim, dict):
                errors.append(f"{requirement_id}:path-claim-invalid")
                continue
            claim_fields = {
                "path", "candidate_id", "content_fingerprint", "claim_role",
                "evidence_edge_ids",
            }
            if claim_fields - set(claim) or set(claim) - claim_fields:
                errors.append(f"{requirement_id}:path-claim-contract-invalid")
            claim_path = str(claim.get("path", ""))
            if claim_path in claim_by_path:
                errors.append(f"{requirement_id}:duplicate-path-claim:{claim_path}")
            claim_by_path[claim_path] = claim
        if not alternatives:
            errors.append(f"{requirement_id}:alternatives-required")
        unsupported_alternatives = sorted(set(alternatives) - eligible_owner_paths)
        if unsupported_alternatives:
            errors.append(f"{requirement_id}:unsupported-alternatives:" + ",".join(unsupported_alternatives))
        if set(alternatives) & set(owners):
            errors.append(f"{requirement_id}:selected-owner-cannot-be-alternative")
        if not decision_reasons:
            errors.append(f"{requirement_id}:decision-reasons-required")
        if not isinstance(row.get("uncertainties"), list):
            errors.append(f"{requirement_id}:uncertainties-required")
        unknown_paths = sorted(set([*owners, *callers, *inspection, *proof, *excluded]) - set(candidates))
        if unknown_paths:
            errors.append(f"{requirement_id}:unknown-paths:" + ",".join(unknown_paths))
        unknown_edges = sorted(set(references) - set(edges))
        if unknown_edges:
            errors.append(f"{requirement_id}:unknown-edges:" + ",".join(unknown_edges))
        referenced_ids = {
            candidate_id
            for edge_id in references
            for candidate_id in (
                str(edges.get(edge_id, {}).get("from_candidate_id", "")),
                str(edges.get(edge_id, {}).get("to_candidate_id", "")),
            )
        }
        referenced_paths = {str(candidate_by_id.get(value, {}).get("path", "")) for value in referenced_ids}
        unsupported = sorted(set([*owners, *callers, *proof]) - referenced_paths)
        if unsupported:
            errors.append(f"{requirement_id}:unsupported-path-claims:" + ",".join(unsupported))
        for owner in owners:
            candidate = candidates.get(owner, {})
            if candidate.get("role") != "implementation-owner" or candidate.get("status") != "included":
                errors.append(f"{requirement_id}:unsupported-owner:{owner}")
            if owner not in eligible_owner_paths:
                errors.append(f"{requirement_id}:owner-not-host-eligible:{owner}")
        if scope_state == "proposed-resolved" and not owners and new_path_decision != _NEW_PATH_DECISION:
            errors.append(f"{requirement_id}:resolved-without-owner")
        if scope_state == "proposed-resolved" and len(owners) != 1 and new_path_decision != _NEW_PATH_DECISION:
            errors.append(f"{requirement_id}:resolved-owner-must-be-singular")
        confidence = str(row.get("confidence", "none"))
        if confidence not in {"none", "low", "medium", "high"}:
            errors.append(f"{requirement_id}:invalid-confidence")
        elif owners and confidence != "high":
            errors.append(f"{requirement_id}:confidence-does-not-match-supported-owner")
        elif not owners and confidence == "high":
            errors.append(f"{requirement_id}:confidence-promotion-rejected")

        material_roles: dict[str, set[str]] = {}
        for role_name, values in (
            ("implementation-owner", owners), ("caller", callers),
            ("inspection", inspection), ("proof", proof),
        ):
            for path in values:
                material_roles.setdefault(path, set()).add(role_name)
        if set(claim_by_path) != set(material_roles):
            errors.append(f"{requirement_id}:path-claim-coverage-mismatch")
        claim_edge_union: set[str] = set()
        for path, expected_roles in material_roles.items():
            claim = claim_by_path.get(path, {})
            candidate = candidates.get(path, {})
            if claim.get("candidate_id") != candidate.get("candidate_id"):
                errors.append(f"{requirement_id}:candidate-id-mismatch:{path}")
            expected_hash = candidate.get("content_fingerprint")
            if not isinstance(expected_hash, str) or claim.get("content_fingerprint") != expected_hash:
                errors.append(f"{requirement_id}:content-fingerprint-mismatch:{path}")
            else:
                _text, rejection, current_hash = safe_text(root, path)
                if rejection or current_hash != expected_hash:
                    errors.append(f"{requirement_id}:stale-path-content:{path}")
            if claim.get("claim_role") not in expected_roles:
                errors.append(f"{requirement_id}:path-claim-role-mismatch:{path}")
            claim_edges = {
                str(value) for value in claim.get("evidence_edge_ids", [])
                if isinstance(value, str)
            }
            if not claim_edges:
                errors.append(f"{requirement_id}:path-claim-edge-required:{path}")
            if not claim_edges.issubset(set(references)) or not claim_edges.issubset(set(edges)):
                errors.append(f"{requirement_id}:path-claim-edge-mismatch:{path}")
            if claim_edges and not all(
                str(candidate.get("candidate_id", "")) in {
                    str(edges.get(edge_id, {}).get("from_candidate_id", "")),
                    str(edges.get(edge_id, {}).get("to_candidate_id", "")),
                }
                for edge_id in claim_edges
            ):
                errors.append(f"{requirement_id}:path-claim-edge-unsupported:{path}")
            claim_edge_union.update(claim_edges)
        covered_edges = set(claim_edge_union)
        if new_path_decision == _NEW_PATH_DECISION:
            covered_edges |= set(convention_refs) & set(edges)
        if covered_edges != set(references):
            errors.append(f"{requirement_id}:evidence-edge-claim-coverage-mismatch")

        role_expectations = (
            (callers, {"caller"}, "caller"),
            (proof, {"test"}, "proof"),
        )
        for values, allowed_roles, label in role_expectations:
            for path in values:
                if candidates.get(path, {}).get("role") not in allowed_roles:
                    errors.append(f"{requirement_id}:unsupported-{label}:{path}")
        for path in excluded:
            if candidates.get(path, {}).get("status") not in {"excluded", "rejected"}:
                errors.append(f"{requirement_id}:unsupported-exclusion:{path}")
        for path in [*owners, *callers, *inspection, *proof, *excluded]:
            _, rejection = normalize_repository_path(root, path)
            if rejection:
                errors.append(f"{requirement_id}:unsafe-path:{path}")
        normalized_requirements.append({
            "requirement_id": requirement_id,
            "statement_fingerprint": row.get("statement_fingerprint"),
            "implementation_owners": owners,
            "callers": callers,
            "inspection_paths": inspection,
            "proof_paths": proof,
            "excluded_candidates": excluded,
            "path_claims": sorted((dict(value) for value in claims if isinstance(value, dict)), key=lambda value: str(value.get("path", ""))),
            "preservation_boundaries": preservation,
            "evidence_edge_ids": references,
            "confidence": confidence,
            "decision_reasons": decision_reasons,
            "alternatives": alternatives,
            "uncertainties": uncertainties,
            "proposed_new_path": new_path,
            "anchor_paths": anchor_paths,
            "convention_refs": convention_refs,
            "decision": new_path_decision,
        })
    normalized = {
        "schema_version": "2",
        "type": "tailtrail-navigator-host-scope-proposal",
        "host": host,
        "evidence_packet_fingerprint": proposal.get("evidence_packet_fingerprint"),
        "scope_evidence_fingerprint": proposal.get("scope_evidence_fingerprint"),
        "target_identity_fingerprint": proposal.get("target_identity_fingerprint"),
        "goal_fingerprint": proposal.get("goal_fingerprint"),
        "scope_state": scope_state,
        "authority": proposal.get("authority"),
        "requirements": sorted(normalized_requirements, key=lambda row: row["requirement_id"]),
        "private_reasoning_excluded": proposal.get("private_reasoning_excluded") is True,
    }
    normalized_scope = dict(normalized)
    normalized_scope.pop("host", None)
    return {
        "status": "accepted" if not errors else "rejected",
        "errors": sorted(dict.fromkeys(errors)),
        "normalized_proposal": normalized,
        "proposal_fingerprint": fingerprint(normalized),
        "normalized_scope_fingerprint": fingerprint(normalized_scope),
    }


def record_host_proposal(root: Path, document: dict[str, Any], proposal: dict[str, Any]) -> dict[str, Any]:
    """Apply one validated evidence refinement without creating authority."""
    if not verify_decision_fingerprint(document):
        raise ValueError("scope evidence decision fingerprint is invalid")
    packet = host_reasoning_packet(document)
    validation = validate_host_proposal(root, packet, proposal)
    updated = copy.deepcopy(document)
    updated.pop("decision_fingerprint", None)
    host_neutral = dict(validation["normalized_proposal"])
    host_neutral.pop("host", None)
    if validation["status"] == "accepted" and proposal.get("scope_state") == "proposed-resolved":
        proposed_by_requirement = {
            str(row["requirement_id"]): row
            for row in validation["normalized_proposal"]["requirements"]
        }
        selected_paths = {
            path
            for row in proposed_by_requirement.values()
            for path in row["implementation_owners"]
        }
        owner_selected = bool(selected_paths)
        eligible_paths = {
            str(row.get("path"))
            for row in packet.get("route", {}).get("eligible_candidates", [])
            if isinstance(row, dict)
        }
        if owner_selected:
            candidates = []
            for source in updated.get("candidates", []):
                candidate = dict(source)
                path = str(candidate.get("path", ""))
                reasons = list(candidate.get("reason_codes", []))
                if path in selected_paths:
                    candidate["status"] = "included"
                    reasons.append("host-evidence-supported-selection")
                elif path in eligible_paths:
                    candidate["status"] = "inspection-only"
                    reasons.append("host-supported-alternative-not-selected")
                candidate["reason_codes"] = sorted(dict.fromkeys(reasons))
                candidates.append(candidate)
            updated["candidates"] = candidates
        for requirement in updated.get("requirements", []):
            if not isinstance(requirement, dict):
                continue
            selected = proposed_by_requirement.get(str(requirement.get("requirement_id")))
            if selected is None:
                continue
            if selected.get("decision") == _NEW_PATH_DECISION:
                requirement["host_proposed_new_path"] = {
                    "path": selected["proposed_new_path"],
                    "anchor_paths": list(selected["anchor_paths"]),
                    "convention_refs": list(selected["convention_refs"]),
                    "decision": _NEW_PATH_DECISION,
                }
                requirement["reason_codes"] = sorted(dict.fromkeys(
                    [*requirement.get("reason_codes", []), _NEW_PATH_DECISION]
                ))
                continue
            if not owner_selected:
                continue
            requirement["implementation_owners"] = list(selected["implementation_owners"])
            requirement["inspection_paths"] = sorted(dict.fromkeys([
                *selected["inspection_paths"],
                *(path for path in eligible_paths if path not in selected_paths),
            ]))
            requirement["proof_paths"] = list(selected["proof_paths"])
            requirement["scope_state"] = "resolved"
            requirement["confidence"] = "high"
            requirement["reason_codes"] = ["host-evidence-supported-owner-resolved"]
        if owner_selected:
            updated["state"] = "resolved"
            investigation = dict(updated.get("investigation", {}))
            investigation["state"] = "resolved"
            investigation["stop_reason"] = "host-evidence-supported-owner-resolved"
            investigation["decision_reason"] = "host-evidence-supported-owner-resolved"
            investigation["resolution_failure_reason"] = None
            updated["investigation"] = investigation
    updated["host_reasoning"] = {
        "state": "recorded" if validation["status"] == "accepted" else "rejected",
        "proposal": {
            "status": validation["status"],
            "reason_codes": validation["errors"] or ["host-proposal-evidence-validated"],
            "source_packet_fingerprint": packet["packet_fingerprint"],
            "normalized_scope_proposal": host_neutral if validation["status"] == "accepted" else None,
            "normalized_scope_fingerprint": validation["normalized_scope_fingerprint"],
            "authority": "evidence-refinement-only",
        },
    }
    updated["summary"] = {
        "included": sum(row.get("status") == "included" for row in updated.get("candidates", [])),
        "inspection_only": sum(row.get("status") == "inspection-only" for row in updated.get("candidates", [])),
        "proof_only": sum(row.get("status") == "proof-only" for row in updated.get("candidates", [])),
        "excluded": sum(row.get("status") == "excluded" for row in updated.get("candidates", [])),
        "rejected": sum(row.get("status") == "rejected" for row in updated.get("candidates", [])),
    }
    updated["decision_fingerprint"] = fingerprint(updated)
    return updated


def host_proposal_decision(root: Path, document: dict[str, Any], proposal: dict[str, Any]) -> dict[str, Any]:
    """Return the shared CLI/MCP result for a host proposal; never persist a run."""
    updated = record_host_proposal(root, document, proposal)
    host_result = updated.get("host_reasoning", {}).get("proposal", {})
    accepted = host_result.get("status") == "accepted"
    return {
        "schema_version": "1",
        "type": "tailtrail-navigator-host-scope-decision",
        "status": "accepted" if accepted else "rejected",
        "reason_codes": list(host_result.get("reason_codes", [])),
        "scope_evidence": updated,
        "scope_contract": normalized_scope_contract(updated),
        "planning_lock_created": False,
        "run_created": False,
        "persisted": False,
        "execution_blocked": True,
        "authority": "none",
        "boundary": "Host reasoning may refine only supported scope evidence. This validation creates no Planning Lock, run, approval, write authority, or execution authority.",
    }


def host_packet_proposal_decision(root: Path, packet: dict[str, Any], proposal: dict[str, Any]) -> dict[str, Any]:
    """Validate a packet proposal identically for CLI and MCP transports."""
    validation = validate_host_proposal(root, packet, proposal)
    return {
        "schema_version": "1",
        "type": "tailtrail-navigator-host-scope-proposal-validation",
        "status": validation["status"],
        "reason_codes": validation["errors"] or ["host-proposal-evidence-validated"],
        "proposal_fingerprint": validation["proposal_fingerprint"],
        "normalized_scope_fingerprint": validation["normalized_scope_fingerprint"],
        "planning_lock_created": False,
        "run_created": False,
        "persisted": False,
        "execution_blocked": True,
        "authority": "none",
        "boundary": "Packet validation only; submit an accepted proposal to the same explicit Start request. No run or authority was created.",
    }


SCOPE_ANSWER_MAX_ROUNDS = 3


def parse_scope_answer(value: str) -> tuple[str | None, str]:
    """Split a scope answer into an optional requirement reference and a path.

    Accepts `REQ-ID=path` (requirement_id or display_id) or a bare path,
    which applies only when exactly one requirement is unresolved.
    """
    text = str(value).strip()
    head, separator, tail = text.partition("=")
    if separator and head.strip() and tail.strip() and "/" not in head and "\\" not in head:
        return head.strip(), tail.strip()
    return None, text


def proposal_from_scope_answers(
    root: Path,
    packet: dict[str, Any],
    raw_answers: list[str],
    answer_round: int,
    host: str,
) -> tuple[dict[str, Any] | None, list[str]]:
    """Build a host-scope proposal from plain-text scope answers.

    Answers bind to the exact supplied packet: every unresolved packet
    requirement must be mapped (all-or-nothing per round), each answered
    path must be a route-eligible evidence-backed candidate, and rounds are
    capped so the dialogue fails closed instead of looping. Returns
    (proposal, []) on success or (None, reason codes) for the next round.
    Rounds always bind the fresh evidence packet, never a post-record one.
    """
    if host not in {"codex", "claude", "copilot"}:
        return None, ["unsupported-host"]
    if answer_round > SCOPE_ANSWER_MAX_ROUNDS:
        return None, ["scope-answer-rounds-exhausted", f"round-{answer_round}-exceeds-max-{SCOPE_ANSWER_MAX_ROUNDS}", "restart-with-a-refined-goal"]
    packet_body = {key: value for key, value in packet.items() if key != "packet_fingerprint"}
    if not isinstance(packet.get("packet_fingerprint"), str) or fingerprint(packet_body) != packet.get("packet_fingerprint"):
        return None, ["host-evidence-packet-integrity-invalid"]
    try:
        negotiate_packet_version(packet)
    except ValueError:
        return None, ["unsupported-packet-version"]
    route = packet.get("route", {}) if isinstance(packet.get("route"), dict) else {}
    if route.get("state") != "requested":
        return None, ["host-reasoning-not-requested"]
    candidates = {str(row.get("path")): row for row in packet.get("candidates", []) if isinstance(row, dict)}
    edges = {str(row.get("edge_id")): row for row in packet.get("edges", []) if isinstance(row, dict)}
    eligible = {str(row.get("path")) for row in route.get("eligible_candidates", []) if isinstance(row, dict)}
    packet_requirements = [row for row in packet.get("requirements", []) if isinstance(row, dict)]
    if not packet_requirements:
        return None, ["answer-requires-packet-requirements"]
    by_id = {str(row.get("requirement_id", "")): row for row in packet_requirements}
    by_display = {str(row.get("display_id", "")): row for row in packet_requirements if str(row.get("display_id", ""))}
    unresolved = [str(row.get("requirement_id", "")) for row in packet_requirements if str(row.get("scope_state", "")) != "resolved"]
    if not unresolved:
        return None, ["scope-already-resolved"]
    if not raw_answers:
        return None, ["answer-required"]
    parsed: list[tuple[str | None, str]] = [parse_scope_answer(value) for value in raw_answers]
    mapped: dict[str, str] = {}
    errors: list[str] = []
    for reference, raw_path in parsed:
        normalized, rejection = normalize_repository_path(root, raw_path)
        if normalized is None:
            errors.append(f"answer-path-rejected:{raw_path}:{rejection}")
            continue
        if reference is None:
            if len(unresolved) != 1:
                errors.append(f"answer-needs-requirement:{raw_path}:provide-REQ-ID=path")
                continue
            requirement_id = unresolved[0]
        else:
            match = by_id.get(reference, by_display.get(reference))
            if match is None:
                errors.append(f"unknown-requirement:{reference}")
                continue
            requirement_id = str(match.get("requirement_id", ""))
            if requirement_id not in unresolved:
                errors.append(f"requirement-already-resolved:{reference}")
                continue
        if requirement_id in mapped:
            errors.append(f"duplicate-requirement-answer:{requirement_id}")
            continue
        candidate = candidates.get(normalized)
        if candidate is None or candidate.get("role") != "implementation-owner" or candidate.get("status") != "included":
            errors.append(f"answer-not-evidence-backed:{normalized}:ground-it-in-the-goal-or---changed")
            continue
        if normalized not in eligible:
            errors.append(f"answer-not-host-eligible:{normalized}:ground-it-in-the-goal-or---changed")
            continue
        touching = sorted({
            str(edge_id) for edge_id in candidate.get("evidence_edge_ids", [])
            if str(edge_id) in edges and str(candidate.get("candidate_id", "")) in {
                str(edges[str(edge_id)].get("from_candidate_id", "")),
                str(edges[str(edge_id)].get("to_candidate_id", "")),
            }
        })
        if not touching:
            errors.append(f"answer-without-relationship-evidence:{normalized}")
            continue
        mapped[requirement_id] = normalized
    missing = sorted(set(unresolved) - set(mapped))
    if missing and not errors:
        errors.append(f"answer-incomplete:unmapped-requirements:{','.join(missing)}")
    if errors:
        return None, sorted(dict.fromkeys(errors))
    proposal_requirements: list[dict[str, Any]] = []
    for row in packet_requirements:
        requirement_id = str(row.get("requirement_id", ""))
        owner = mapped[requirement_id]
        candidate = candidates[owner]
        claim_edges = sorted({
            str(edge_id) for edge_id in candidate.get("evidence_edge_ids", [])
            if str(edge_id) in edges and str(candidate.get("candidate_id", "")) in {
                str(edges[str(edge_id)].get("from_candidate_id", "")),
                str(edges[str(edge_id)].get("to_candidate_id", "")),
            }
        })
        alternatives = sorted(path for path in eligible if path != owner)
        if not alternatives:
            return None, [f"answer-has-no-alternative:{requirement_id}"]
        proposal_requirements.append({
            "requirement_id": requirement_id,
            "statement_fingerprint": row.get("statement_fingerprint"),
            "implementation_owners": [owner],
            "callers": [],
            "inspection_paths": [],
            "proof_paths": [],
            "excluded_candidates": [],
            "path_claims": [{
                "path": owner,
                "candidate_id": str(candidate.get("candidate_id", "")),
                "content_fingerprint": str(candidate.get("content_fingerprint", "")),
                "claim_role": "implementation-owner",
                "evidence_edge_ids": claim_edges,
            }],
            "preservation_boundaries": ["An answered scope owner records explicit host selection; it grants no execution authority."],
            "evidence_edge_ids": claim_edges,
            "confidence": "high",
            "decision_reasons": [
                f"Host scope answer round {answer_round} selects {owner} for {requirement_id}.",
                f"The answered path is evidence-backed with {len(claim_edges)} relationship edge(s).",
            ],
            "alternatives": alternatives,
            "uncertainties": [],
        })
    return {
        "schema_version": "2",
        "type": "tailtrail-navigator-host-scope-proposal",
        "host": host,
        "evidence_packet_fingerprint": packet.get("packet_fingerprint"),
        "scope_evidence_fingerprint": packet.get("scope_evidence_fingerprint"),
        "target_identity_fingerprint": packet.get("target_identity_fingerprint"),
        "goal_fingerprint": packet.get("goal_fingerprint"),
        "scope_state": "proposed-resolved",
        "authority": "evidence-refinement-only",
        "requirements": proposal_requirements,
        "private_reasoning_excluded": True,
    }, []
