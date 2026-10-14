"""TailTrail Phase N1: deterministic local checks for the New-File Due-Diligence
Protocol (TAILTRAIL-NEW-FILE-DUE-DILIGENCE-PROTOCOL.md).

These five checks need no code graph and no Navigator integration -- pure
filesystem and string operations only. Each returns a :class:`Finding`.
Combining findings into the five-state verdict taxonomy (`new-confirmed`,
`extend-recommended`, `collision-blocked`, `unverified`, `not-applicable`) is
Phase N2/N3 work, not this module's job.

Phase N2 adds ``check_existing_owner_evidence`` (Check 4): flipped-polarity
scoring over Navigator's existing relationship-edge vocabulary
(``scripts/navigator_scope.py``'s ``DEEP_EDGE_KINDS``). Navigator's
``_has_deep_support`` is calibrated to disambiguate among multiple plausible
*existing* candidates for a requirement -- there it treats ``tested-by`` as
strong (deep) evidence, which is reasonable for *that* question. Reused
as-is for the *different* question this protocol asks -- "is there real
evidence this existing path already owns the proposed new functionality" --
that same ``tested-by`` edge silently misfires: an existing file being
covered by some test, or merely importing/being imported by another path,
proves nothing about ownership of a brand-new, unrelated requirement. The
live incident this phase fixes: Navigator proposed `scripts/intake_pipeline.py`
as the owner for an unrelated new file on the strength of exactly the edges
``raises-behavior-error``, ``imports-module``, ``tested-by`` -- none of which
assert that the file defines, edits, or behaviourally implements the new
concern. ``OWNERSHIP_EDGE_KINDS``/``CONSUMER_EDGE_KINDS`` below are a
deliberately separate, narrower allowlist for this purpose; they are not a
replacement for ``DEEP_EDGE_KINDS`` and must not be merged with it.
"""
from __future__ import annotations

import importlib.util
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
_POLICY: Any = None


def _policy() -> Any:
    """Shared workspace policy, loaded once."""
    global _POLICY
    if _POLICY is None:
        spec = importlib.util.spec_from_file_location(
            "new_file_due_diligence_workspace_policy", ROOT / "scripts" / "repository_path_policy.py"
        )
        if spec is None or spec.loader is None:
            raise RuntimeError("unable to load scripts/repository_path_policy.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        _POLICY = module
    return _POLICY


@dataclass(frozen=True)
class Finding:
    """One check's evidence. Never a verdict by itself (Phase N2/N3 combine
    findings into a verdict)."""

    check: str
    decisive: bool
    reason_codes: tuple[str, ...]
    details: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "check": self.check,
            "decisive": self.decisive,
            "reason_codes": list(self.reason_codes),
            "details": dict(self.details),
        }


# Directory-name near-duplication signals (Check 3b): numeric suffix,
# version/copy markers. Deliberately conservative -- false negatives here
# just fall through to Check 3a/Check 4 instead of blocking, so there is no
# safety cost to keeping this list narrow and explicit rather than guessing
# with a generic edit-distance threshold.
_VERSION_COPY_SUFFIXES = ("_v2", "_v3", "_new", "-copy", "-old", "_old", "_copy")


def check_existence(root: Path, relative: str) -> Finding:
    """Check 1 -- does the exact proposed path already exist?"""
    exists = (root / relative).exists()
    return Finding(
        check="existence",
        decisive=exists,
        reason_codes=("path-already-exists",) if exists else ("path-does-not-exist",),
        details={"path": relative},
    )


def check_path_eligibility(root: Path, relative: str) -> Finding:
    """Check 2 -- reuses the shared classifiers; no new logic."""
    policy_role, policy_reasons = _policy().classify_path(root, relative)
    eligible = _policy().is_eligible(policy_role)
    return Finding(
        check="path-eligibility",
        decisive=not eligible,
        reason_codes=policy_reasons,
        details={"path": relative, "policy_role": policy_role},
    )


def _directory_parts(relative: str) -> tuple[str, ...]:
    parts = PurePosixPath(relative.replace("\\", "/")).parts
    return parts[:-1] if parts else ()


def _is_near_duplicate_directory_name(candidate: str, existing: str) -> bool:
    """Check 3b's name-resemblance rule: numeric suffix or a version/copy
    marker against an existing sibling directory name. Case-insensitive.
    `validate2` vs `validate` is the canonical example (protocol Example D)."""
    candidate_l, existing_l = candidate.lower(), existing.lower()
    if candidate_l == existing_l:
        return False
    if candidate_l.rstrip("0123456789") == existing_l and candidate_l != existing_l:
        return True
    for suffix in _VERSION_COPY_SUFFIXES:
        if candidate_l == existing_l + suffix:
            return True
    return False


def check_name_symbol_collision(root: Path, relative: str, *, symbols: tuple[str, ...] = ()) -> Finding:
    """Check 3 -- two independent sub-checks, never collapsed into one signal.

    3a (filename/symbol, weak alone): same filename stem elsewhere, or a
    repository-wide symbol match. 3b (directory near-duplication, strong
    alone): the proposed directory is a trivial variant of an existing
    sibling directory name.
    """
    proposed = PurePosixPath(relative.replace("\\", "/"))
    stem = proposed.stem
    proposed_dir_parts = _directory_parts(relative)

    filename_matches: list[str] = []
    symbol_matches: list[str] = []
    directory_matches: list[str] = []

    symbol_patterns = [
        re.compile(rf"(?<![A-Za-z0-9_])(?:def|class)\s+{re.escape(name)}(?![A-Za-z0-9_])")
        for name in symbols
    ]

    for path in root.rglob("*"):
        if not path.is_file():
            continue
        try:
            found_relative = path.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            continue
        if found_relative == relative:
            continue
        role, _ = _policy().classify_path(root, found_relative)
        if not _policy().is_eligible(role):
            continue

        other = PurePosixPath(found_relative)
        if other.stem == stem and other.suffix == proposed.suffix:
            filename_matches.append(found_relative)

        if symbol_patterns:
            try:
                body = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                body = ""
            if any(pattern.search(body) for pattern in symbol_patterns):
                symbol_matches.append(found_relative)

        other_dir_parts = _directory_parts(found_relative)
        if (
            proposed_dir_parts
            and other_dir_parts
            and len(proposed_dir_parts) == len(other_dir_parts)
            and proposed_dir_parts[:-1] == other_dir_parts[:-1]
            and _is_near_duplicate_directory_name(proposed_dir_parts[-1], other_dir_parts[-1])
        ):
            candidate_dir = "/".join(other_dir_parts)
            if candidate_dir not in directory_matches:
                directory_matches.append(candidate_dir)

    has_3a = bool(filename_matches or symbol_matches)
    has_3b = bool(directory_matches)
    return Finding(
        check="name-symbol-collision",
        decisive=has_3a and has_3b,
        reason_codes=tuple(
            code for code, present in (
                ("filename-match", bool(filename_matches)),
                ("symbol-match", bool(symbol_matches)),
                ("directory-near-duplication", has_3b),
            ) if present
        ) or ("no-collision-signal",),
        details={
            "path": relative,
            "filename_matches": filename_matches,
            "symbol_matches": symbol_matches,
            "directory_matches": directory_matches,
            "sub_check_3a": has_3a,
            "sub_check_3b": has_3b,
        },
    )


def check_convention_precedent(root: Path, relative: str) -> Finding:
    """Check 5 -- does the target directory already establish a real
    'one file per concern' pattern? No magic thresholds: presence of two or
    more existing sibling files with the same suffix is the precedent
    signal. Absence of precedent (empty/missing directory) is recorded as
    inconclusive, not negative -- it falls through to Check 6 per the
    protocol, it never blocks on its own."""
    proposed = PurePosixPath(relative.replace("\\", "/"))
    directory = root / "/".join(proposed.parts[:-1]) if len(proposed.parts) > 1 else root
    suffix = proposed.suffix

    if not directory.is_dir():
        return Finding(
            check="convention-precedent",
            decisive=False,
            reason_codes=("directory-does-not-exist-yet",),
            details={"path": relative, "sibling_count": 0},
        )

    siblings = [
        item.name for item in directory.iterdir()
        if item.is_file() and item.suffix == suffix and item.name != proposed.name
    ]
    supports_precedent = len(siblings) >= 2
    return Finding(
        check="convention-precedent",
        decisive=supports_precedent,
        reason_codes=("one-file-per-concern-precedent",) if supports_precedent else ("insufficient-or-mixed-precedent",),
        details={"path": relative, "sibling_count": len(siblings), "siblings": sorted(siblings)},
    )


# Phase N2 -- Check 4: flipped-polarity existing-owner evidence.
#
# Deliberately NOT `navigator_scope.py`'s `DEEP_EDGE_KINDS` (used by the
# private `_has_deep_support`/`_owner_strong_support` helpers there to rank
# *existing* candidates against each other for behaviour-shaped
# requirements). This allowlist answers a narrower question instead: does
# this specific edge kind, on its own, assert that an existing path already
# *implements* or *defines* the thing the new-file requirement describes?
# `tested-by` is excluded on purpose -- an existing file being covered by
# some test says nothing about whether it owns an unrelated new concern,
# and counting it as ownership evidence is exactly what produced the live
# `scripts/intake_pipeline.py` misfire this check exists to prevent.
OWNERSHIP_EDGE_KINDS = frozenset({
    "declares-edit-boundary",
    "defines-symbol",
    "calls-symbol",
    "captures-returned-value",
    "catches-error",
    "writes-ui-state",
    "renders-ui-state",
    "renders-caught-error",
    "renders-destination",
    "emits-user-visible-literal",
    "writes-navigation-state",
    "defines-ui-handler",
    "binds-ui-action",
    "defines-behavior-handler",
})

# Edge kinds that only assert the candidate is near or used by other code --
# never ownership on their own. `tested-by` lives here, not in
# OWNERSHIP_EDGE_KINDS, for the reason documented above.
CONSUMER_EDGE_KINDS = frozenset({
    "imports-module",
    "loads-module",
    "tested-by",
})


def check_existing_owner_evidence(candidate_path: str, edge_kinds: tuple[str, ...]) -> Finding:
    """Check 4 -- flipped polarity. Weak-or-no ownership evidence supports
    `new-confirmed` (the candidate does not already own this concern);
    only a genuine ownership-grade edge kind is decisive against treating
    the path as new. Consumer-only edges (imports/loads/tested-by) are
    recorded for transparency but never count as decisive ownership."""
    ownership_hits = sorted({kind for kind in edge_kinds if kind in OWNERSHIP_EDGE_KINDS})
    consumer_hits = sorted({kind for kind in edge_kinds if kind in CONSUMER_EDGE_KINDS})
    has_ownership = bool(ownership_hits)
    if has_ownership:
        reason_codes: tuple[str, ...] = ("strong-ownership-evidence",)
    elif consumer_hits:
        reason_codes = ("consumer-only-evidence",)
    else:
        reason_codes = ("no-owner-evidence",)
    return Finding(
        check="existing-owner-evidence",
        decisive=has_ownership,
        reason_codes=reason_codes,
        details={
            "path": candidate_path,
            "ownership_edge_kinds": ownership_hits,
            "consumer_edge_kinds": consumer_hits,
        },
    )


# Phase N3 -- verdict taxonomy (TAILTRAIL-NEW-FILE-DUE-DILIGENCE-PROTOCOL.md
# "Verdict taxonomy" section). Fixed order, exported for callers/tests that
# need to validate against the full enum rather than a bare string.
VERDICTS = ("new-confirmed", "extend-recommended", "collision-blocked", "unverified", "not-applicable")


def _verdict(verdict: str, reason_codes: tuple[str, ...], question: str | None) -> dict[str, Any]:
    return {"verdict": verdict, "reason_codes": tuple(reason_codes), "question": question}


def _proposed_directory(path: str) -> str:
    parts = PurePosixPath(path.replace("\\", "/")).parts[:-1]
    return "/".join(parts)


def combine_verdict(
    *,
    existence: Finding,
    path_eligibility: Finding,
    collision: Finding,
    owner_evidence: Finding,
    convention: Finding,
    rationale_provided: bool = False,
    rationale_contradicts_evidence: bool = False,
) -> dict[str, Any]:
    """Check 6 + verdict combination (Phase N3). Combines Phase N1's four
    checks and Phase N2's owner-evidence check into the five-state verdict
    taxonomy. `rationale_provided`/`rationale_contradicts_evidence` are
    Check 6 -- a tie-breaker for the `insufficient-or-mixed-precedent` case
    only; they never override a result Checks 1-5 already decided."""
    if existence.decisive:
        return _verdict("collision-blocked", ("path-already-exists",), None)

    if path_eligibility.decisive:
        return _verdict("collision-blocked", path_eligibility.reason_codes, None)

    details = collision.details
    has_3a = bool(details.get("sub_check_3a"))
    has_3b = bool(details.get("sub_check_3b"))
    proposed_dir = _proposed_directory(str(details.get("path", "")))
    directory_matches = details.get("directory_matches") or []

    if has_3a and has_3b:
        question = (
            f"`{proposed_dir}` closely resembles the existing directory "
            f"`{directory_matches[0] if directory_matches else '?'}`, and a matching name/symbol "
            f"already exists there (filename: {details.get('filename_matches')}, "
            f"symbol: {details.get('symbol_matches')}) -- why does this need to be separate, "
            "and why can't the existing file be extended or reused instead?"
        )
        return _verdict("extend-recommended", ("directory-and-name-collision",), question)

    if has_3b and not has_3a:
        question = (
            f"`{proposed_dir}` closely resembles the existing directory "
            f"`{directory_matches[0] if directory_matches else '?'}` -- why does `{proposed_dir}` "
            "need to exist alongside it?"
        )
        return _verdict("unverified", ("directory-near-duplication-only",), question)

    if owner_evidence.decisive:
        candidate = owner_evidence.details.get("path")
        kinds = owner_evidence.details.get("ownership_edge_kinds") or []
        question = (
            f"`{candidate}` already appears to own this responsibility (evidence: "
            f"{', '.join(kinds)}) -- extend it, or state why this must be a separate new file?"
        )
        return _verdict("extend-recommended", owner_evidence.reason_codes, question)

    if convention.decisive:
        return _verdict("new-confirmed", convention.reason_codes, None)

    convention_reason = convention.reason_codes[0] if convention.reason_codes else ""
    if convention_reason == "directory-does-not-exist-yet":
        return _verdict("new-confirmed", ("no-precedent-directory-not-yet-created",), None)

    if rationale_contradicts_evidence:
        return _verdict(
            "unverified",
            ("rationale-contradicts-evidence",),
            "The stated rationale contradicts already-found evidence; please reconcile and resubmit.",
        )
    if rationale_provided:
        return _verdict("new-confirmed", ("rationale-accepted-as-tiebreaker",), None)
    question = (
        f"No clear existing-owner evidence and no strong directory convention either way for "
        f"`{convention.details.get('path')}` -- state why this needs to be a separate new file "
        "(new integration, new data entity, unrelated feature surface, or a named governing convention)."
    )
    return _verdict("unverified", ("no-decisive-evidence-either-way",), question)


def evaluate_existing_file_claim(candidate_path: str, edge_kinds: tuple[str, ...]) -> dict[str, Any]:
    """Symmetry check (Example C): the same scrutiny applied to a host
    claim of 'just edit existing file X'. Reuses `check_existing_owner_evidence`
    unchanged -- the claim is accepted only when genuine ownership-grade
    evidence backs it, never because 'existing' sounds safer than 'new'."""
    finding = check_existing_owner_evidence(candidate_path, edge_kinds)
    if finding.decisive:
        result = _verdict("not-applicable", ("existing-owner-claim-confirmed",), None)
    else:
        result = _verdict(
            "unverified",
            ("existing-owner-claim-unsupported",),
            (
                f"`{candidate_path}` has no qualifying ownership relationship to this requirement "
                "(only consumer/no edges found) -- confirm this is really the right file to edit, "
                "or name the correct owner."
            ),
        )
    result["finding"] = finding.as_dict()
    return result


def run_all_checks(root: Path, relative: str, *, symbols: tuple[str, ...] = ()) -> dict[str, Finding]:
    """Convenience entry point running every Phase N1 check for one path."""
    return {
        "existence": check_existence(root, relative),
        "path_eligibility": check_path_eligibility(root, relative),
        "name_symbol_collision": check_name_symbol_collision(root, relative, symbols=symbols),
        "convention_precedent": check_convention_precedent(root, relative),
    }

