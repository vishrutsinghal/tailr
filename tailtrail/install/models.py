"""Stable models used by the TailTrail installer API and CLI."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class PlanEntry:
    path: str
    sha256: str
    size: int
    action: str
    source: str
    previous_sha256: str | None = None


@dataclass(frozen=True)
class InstallPlan:
    schema_version: str
    plan_id: str
    operation: str
    version: str
    host: str
    profile: str
    target: str
    existing_version: str | None
    entries: tuple[PlanEntry, ...]
    conflicts: tuple[str, ...] = ()
    removals: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class InstallResult:
    operation: str
    status: str
    target: str
    host: str
    profile: str
    version: str
    transaction_id: str | None = None
    changed: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    preserved: list[str] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    recovered_transactions: list[str] = field(default_factory=list)
    plan: dict[str, Any] | None = None
    diagnostics: dict[str, Any] | None = None

    @property
    def ok(self) -> bool:
        return self.status in {"passed", "current", "dry-run", "update-available"} or (
            self.status == "not-installed" and self.operation in {"status", "uninstall"}
        )

    def as_dict(self, *, details: bool = True) -> dict[str, Any]:
        payload = {"schema_version": "1", "type": "tailtrail-install-result", "ok": self.ok, **asdict(self)}
        payload["counts"] = {
            "changed": len(self.changed),
            "removed": len(self.removed),
            "preserved": len(self.preserved),
            "issues": len(self.issues),
            "recovered_transactions": len(self.recovered_transactions),
        }
        if details:
            payload["detail_level"] = "full"
            return payload
        plan = payload.pop("plan", None)
        payload["plan_summary"] = None if not isinstance(plan, dict) else {
            "plan_id": plan.get("plan_id"),
            "entry_count": len(plan.get("entries", [])) if isinstance(plan.get("entries"), list) else 0,
            "conflict_count": len(plan.get("conflicts", [])) if isinstance(plan.get("conflicts"), list) else 0,
            "removal_count": len(plan.get("removals", [])) if isinstance(plan.get("removals"), list) else 0,
        }
        for key in ("changed", "removed", "preserved", "recovered_transactions"):
            payload.pop(key, None)
        payload["detail_level"] = "summary"
        return payload
