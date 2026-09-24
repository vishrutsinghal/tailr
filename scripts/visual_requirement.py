#!/usr/bin/env python3
"""Visual requirement intake and scope gate.

The host agent sees attached images; TailTrail only binds and gates.
This module provides the pieces Phase 1 will wire into planning:

- attachment awareness: were files attached, and are they bound?
- streaming SHA-256 of original image bytes (chunked reads, never
  whole-file; no size caps — host platforms bound uploads upstream);
- observation-contract validation (host summary + open questions with a
  ban on embedded data blobs).

The gate is intentionally language- and framework-agnostic. It acts on the
request contract before source discovery, never on project source syntax.
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import urlparse

CHUNK_BYTES = 1024 * 1024
MAX_STAGED_ATTACHMENT_BYTES = 50 * 1024 * 1024

REMOTE_SCHEMES = {"http", "https", "ftp", "data"}

# Matches embedded payloads (data: URIs). Naked base64 without a scheme
# prefix is indistinguishable from dense prose without length heuristics,
# so it is a documented residual risk, not an enforced rule.
DATA_URI_PATTERN = re.compile(r"data:[A-Za-z0-9.+-]+/[A-Za-z0-9.+-]+;base64,", re.IGNORECASE)

# These phrases say that acceptance criteria live outside the text request.
# Keep this intentionally narrow: asking to add an image upload or a CSS
# background is not itself a request to inspect an external visual reference.
VISUAL_REFERENCE_PATTERN = re.compile(
    r"\b(?:"
    r"(?:attached|provided|shared)\s+(?:image|screenshot|mockup|design)|"
    r"(?:see|check|review|use|follow)\s+(?:the\s+)?(?:attached\s+)?(?:image|screenshot|mockup|design)|"
    r"(?:shown|specified|described)\s+in\s+(?:the\s+)?(?:attached\s+)?(?:image|screenshot|mockup|design)|"
    r"(?:as\s+(?:shown|specified)\s+(?:in|on)|according\s+to)\s+(?:the\s+)?(?:attached\s+)?(?:image|screenshot|mockup|design)|"
    r"following\s+(?:columns|fields|controls|layout)\s*(?:-|:)?\s*(?:check|see)\b"
    r")",
    re.IGNORECASE,
)


def normalize_attachment(value: object) -> Path | None:
    """Return a local path for an attachment value, or None when remote."""
    text = str(value or "").strip()
    if not text:
        return None
    parsed = urlparse(text)
    if parsed.scheme.casefold() in REMOTE_SCHEMES:
        return None
    return Path(text)


def normalize_visual_attachments(value: object) -> list[dict[str, str]]:
    """Validate the host-neutral visual attachment transport contract.

    Hosts resolve their own chat attachment identifiers to local, read-only
    paths. TailTrail accepts no remote URL or image bytes and does not invent
    a path from an attachment ID.
    """
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("visual_attachments must be an array")
    normalized: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    for index, item in enumerate(value, start=1):
        if not isinstance(item, dict):
            raise ValueError("every visual attachment must be an object")
        attachment_id = str(item.get("attachment_id") or "").strip()
        local_path = str(item.get("local_path") or "").strip()
        media_type = str(item.get("media_type") or "").strip().lower()
        if not attachment_id or len(attachment_id) > 256:
            raise ValueError(f"visual attachment {index} needs an attachment_id")
        if attachment_id in seen_ids:
            raise ValueError("visual attachment IDs must be unique")
        if normalize_attachment(local_path) is None:
            raise ValueError(f"visual attachment {attachment_id} needs a local_path")
        if media_type and not media_type.startswith("image/"):
            raise ValueError(f"visual attachment {attachment_id} has a non-image media_type")
        seen_ids.add(attachment_id)
        normalized.append({
            "attachment_id": attachment_id,
            "local_path": Path(local_path).expanduser().as_posix(),
            **({"media_type": media_type} if media_type else {}),
        })
    return normalized


@contextmanager
def staged_attachments(attachments: list[dict[str, str]]) -> Iterator[list[dict[str, str]]]:
    """Copy host-resolved attachments into a private, short-lived directory.

    The host owns attachment resolution. This function accepts only its local
    path, creates an unreadable-to-other-users temporary copy for TailTrail,
    and removes all copies on every exit path.
    """
    if not attachments:
        yield []
        return
    directory = Path(tempfile.mkdtemp(prefix="tailtrail-visual-"))
    os.chmod(directory, 0o700)
    staged: list[dict[str, str]] = []
    try:
        for index, attachment in enumerate(attachments, start=1):
            source = Path(attachment["local_path"])
            try:
                size = source.stat().st_size
            except OSError as error:
                raise ValueError(f"visual attachment {attachment['attachment_id']} is unavailable") from error
            if not source.is_file() or size > MAX_STAGED_ATTACHMENT_BYTES:
                raise ValueError(f"visual attachment {attachment['attachment_id']} is not a permitted local file")
            destination = directory / f"attachment-{index:02d}.bin"
            try:
                with source.open("rb") as reader, destination.open("xb") as writer:
                    os.chmod(destination, 0o600)
                    for chunk in iter(lambda: reader.read(CHUNK_BYTES), b""):
                        writer.write(chunk)
            except OSError as error:
                raise ValueError(f"visual attachment {attachment['attachment_id']} could not be staged") from error
            staged.append({**attachment, "local_path": destination.as_posix()})
        yield staged
    finally:
        shutil.rmtree(directory, ignore_errors=True)


def hash_visual_artifact(path: Path) -> dict[str, Any]:
    """Hash original image bytes with a streaming read.

    Returns either {"sha256", "size_bytes"} or {"status", "reason_code"}.
    Raw bytes are never retained — only the digest leaves this function.
    """
    try:
        size = path.stat().st_size
    except OSError:
        return {"status": "unavailable", "reason_code": "visual-artifact-missing"}
    if not path.is_file():
        return {"status": "unreadable", "reason_code": "visual-artifact-not-a-file"}
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(CHUNK_BYTES), b""):
                digest.update(chunk)
    except OSError:
        return {"status": "unreadable", "reason_code": "visual-artifact-read-failed"}
    return {"sha256": "sha256:" + digest.hexdigest(), "size_bytes": size}


# Magic-byte signatures: format is observed, never parsed. Unknown bytes
# are not an image; mislabeled extensions never promote a file.
IMAGE_SIGNATURES = (
    ("image/png", bytes.fromhex("89504e470d0a1a0a")),
    ("image/jpeg", bytes.fromhex("ffd8ff")),
    ("image/gif", b"GIF87a"),
    ("image/gif", b"GIF89a"),
)
WEBP_SIGNATURE = (b"RIFF", b"WEBP")


def sniff_image_media(path: Path) -> str | None:
    """Return an image media type from magic bytes, or None when unknown."""
    try:
        with path.open("rb") as handle:
            head = handle.read(32)
    except OSError:
        return None
    for media_type, signature in IMAGE_SIGNATURES:
        if head.startswith(signature):
            return media_type
    if head.startswith(WEBP_SIGNATURE[0]) and WEBP_SIGNATURE[1] in head[:32]:
        return "image/webp"
    return None


def inspect_visual_artifact(locator: str) -> dict[str, Any]:
    """Inspect a local image file into a hash-bound receipt without content.

    Returns an inspected receipt carrying input ID binding, byte hash,
    size, and media type — never raw bytes, pixels, or observations.
    Observations travel separately through `validate_observations`.
    """
    path = Path(locator)
    if not path.exists():
        return {"status": "unavailable", "reason_code": "visual-artifact-missing"}
    if not path.is_file():
        return {"status": "unreadable", "reason_code": "visual-artifact-not-a-file"}
    media_type = sniff_image_media(path)
    if media_type is None:
        return {"status": "unsupported", "reason_code": "visual-artifact-not-an-image"}
    hashed = hash_visual_artifact(path)
    if "sha256" not in hashed:
        return {"status": hashed.get("status", "unreadable"), "reason_code": hashed.get("reason_code", "visual-artifact-read-failed")}
    return {
        "status": "inspected",
        "inspection": "hash-bound-visual-metadata",
        "kind": "visual-artifact",
        "media_type": media_type,
        "sha256": hashed["sha256"],
        "size_bytes": hashed["size_bytes"],
        "reason_code": "visual-artifact-inspected",
    }


def attachment_state(session_attachments: list[str], bound_paths: list[str]) -> str:
    """Classify session attachments as none, bound, or unbound.

    Only local paths count as attachments; remote references are reported
    separately by normalize_attachment and never reach binding.
    """
    local = [path for path in (str(value or "").strip() for value in session_attachments) if path and normalize_attachment(path) is not None]
    if not local:
        return "none"
    bound = {str(value or "").strip() for value in bound_paths}
    if all(path in bound for path in local):
        return "bound"
    return "unbound"


def requires_visual_contract(goal: str) -> bool:
    """Return whether the request delegates material details to a visual."""
    return bool(VISUAL_REFERENCE_PATTERN.search(str(goal or "")))


def intake_decisions(
    goal: str,
    *,
    visual_artifact_declared: bool,
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return pre-scope visual decisions for a visual-dependent request.

    A readable image still needs a host-produced, hash-bound observation
    contract. TailTrail hashes bytes but does not infer pixels, so a missing
    observation is a material requirement gap rather than a scope problem.
    """
    if not requires_visual_contract(goal):
        return []
    if not visual_artifact_declared:
        return [visual_material_decision(
            "Attach the referenced image or provide the missing visual contract, including the exact table columns, controls, row actions, and validations."
        )]
    if not records:
        return [visual_material_decision(
            "Provide a hash-bound visual observation for the attached image: summarize the UI contract and list any unreadable or unspecified controls, columns, row actions, or validations."
        )]
    return []


# Decision class for unbound-visual material decisions. Hosts may submit
# the question text directly as a `question` clause (it becomes a MAT-*
# decision through the sufficiency contract); this helper pre-forms the
# equivalent decision for tool callers that build it explicitly.
VISUAL_DECISION_CLASS = "visual-artifact-required"


def visual_material_decision(question: str, evidence_ref: str = "host-interpretation", decision_id: str = "VIS-01") -> dict[str, Any]:
    """Pre-form the VIS material decision for an unbound visual.

    The question must name what has to be specified from the image before
    scope discovery (e.g. table headers, dropdown option source). An open
    VIS decision keeps requirements non-sufficient, which defers the scope
    precondition and blocks graph, scope, lock, and authority work.
    """
    text = str(question or "").strip()
    if not text:
        raise ValueError("visual material decision requires a question")
    return {
        "id": decision_id,
        "decision_class": VISUAL_DECISION_CLASS,
        "question": text,
        "impact": ["acceptance-criteria", "implementation-scope"],
        "evidence_refs": [evidence_ref],
    }


def validate_observations(payload: Any) -> list[str]:
    """Check a host-supplied visual observation record. Empty means valid.

    The record names its artifact by local `locator`; TailTrail assigns the
    input ID and hash at bind time, so neither is accepted as input.
    """
    if not isinstance(payload, dict):
        return ["visual-observations-must-be-an-object"]
    issues: list[str] = []
    locator = payload.get("locator")
    if locator is not None and (not isinstance(locator, str) or not locator.strip()):
        issues.append("visual-observations-locator-must-be-a-path")
    summary = payload.get("summary")
    if not isinstance(summary, str) or not summary.strip():
        issues.append("visual-observations-require-summary")
    questions = payload.get("open_questions", [])
    if not isinstance(questions, list) or not all(isinstance(item, str) and item.strip() for item in questions):
        issues.append("visual-questions-must-be-non-empty-strings")
    complete = payload.get("complete", False)
    if not isinstance(complete, bool):
        issues.append("visual-complete-must-be-boolean")
    elif complete and questions:
        issues.append("visual-complete-forbids-open-questions")
    elif not complete and not questions:
        issues.append("visual-incomplete-requires-open-questions")
    for key in ("summary",):
        value = payload.get(key)
        if isinstance(value, str) and DATA_URI_PATTERN.search(value):
            issues.append("visual-observations-must-not-embed-data")
    for question in questions if isinstance(questions, list) else []:
        if isinstance(question, str) and DATA_URI_PATTERN.search(question):
            issues.append("visual-observations-must-not-embed-data")
            break
    return issues


def bind_observations(
    payloads: dict[str, Any] | list[dict[str, Any]] | None,
    inspected: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Match observation payloads to inspected visual receipts by locator.

    Returns (bound_records, issues). A bound record carries the registry
    input ID, locator, byte hash, size, media type, summary, open
    questions, and completeness claim — everything closure needs without
    ever touching pixels. A payload without a locator binds only when it
    is the single payload for a single inspected artifact; otherwise the
    host must name its artifact explicitly.
    """
    if payloads is None:
        return [], []
    items = [payloads] if isinstance(payloads, dict) else list(payloads)
    if not isinstance(items, list) or any(not isinstance(item, dict) for item in items):
        return [], ["visual-observations-must-be-objects"]
    bound: list[dict[str, Any]] = []
    for payload in items:
        issues = validate_observations(payload)
        if issues:
            return [], issues
        locator = str(payload.get("locator") or "").strip()
        candidates = [row for row in inspected if row.get("status") == "inspected"]
        target = None
        if locator:
            for row in candidates:
                try:
                    same = Path(str(row.get("locator", ""))).resolve() == Path(locator).resolve()
                except OSError:
                    same = str(row.get("locator", "")) == locator
                if same:
                    target = row
                    break
            if target is None:
                return [], ["visual-observations-reference-unknown-artifact"]
        elif len(candidates) == 1 and len(items) == 1:
            target = candidates[0]
        else:
            return [], ["visual-observations-must-name-artifact"]
        bound.append({
            "input_id": target.get("input_id"),
            "locator": target.get("locator"),
            "sha256": target.get("sha256"),
            "size_bytes": target.get("size_bytes"),
            "media_type": target.get("media_type"),
            "summary": str(payload.get("summary", "")).strip(),
            "open_questions": [str(item).strip() for item in payload.get("open_questions", [])],
            "complete": bool(payload.get("complete", False)),
        })
    return bound, []
