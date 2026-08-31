#!/usr/bin/env python3
"""Privacy helpers for exact local Debug evidence and portable metadata."""
from __future__ import annotations

import hashlib
import re
from typing import Any

PATTERNS = {
    "private-key": re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----", re.I),
    "bearer-token": re.compile(r"\bbearer\s+[a-z0-9._~+/-]{12,}=*", re.I),
    "secret-assignment": re.compile(r"\b(?:api[_-]?key|access[_-]?token|auth[_-]?token|client[_-]?secret|password|passwd|secret|token)\b\s*[:=]\s*['\"]?[^'\"\s,;]{8,}", re.I),
    "aws-access-key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "github-token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    "jwt": re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"),
    "email": re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
}


def digest(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()


def inspect(values: dict[str, str | None]) -> dict[str, Any]:
    categories: set[str] = set()
    fields: list[str] = []
    for field, value in values.items():
        text = value or ""
        matched = {name for name, pattern in PATTERNS.items() if pattern.search(text)}
        if matched:
            fields.append(field); categories.update(matched)
    return {
        "sensitive": bool(categories),
        "categories": sorted(categories),
        "affected_fields": sorted(fields),
        "portable_values": False,
        "boundary": "Only categories and hashes are portable. Exact values remain in the run-local intake and are never copied into fingerprints, continuity, learning, or evaluation artifacts.",
    }


def hashed_lines(value: str | None, maximum: int = 10) -> list[str]:
    return [digest(line.strip()) for line in (value or "").splitlines() if line.strip()][:maximum]
