"""Record categorical workflow denials without retaining hostile input or errors."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from workflow_runtime import contracts, ownership


LEDGER = ownership.LEDGER
REASONS = {
    "authority":"approval-denied", "integrity":"artifact-invalid", "path":"unsafe-reference",
    "privacy":"privacy-blocked", "retry":"retry-prohibited", "provider":"provider-not-authorized",
    "freshness":"input-stale", "contract":"unknown-contract", "cross-boundary":"cross-boundary-substitution",
    "completion":"completion-not-proven", "host-boundary":"host-stop-required", "retention":"retention-not-authorized",
}


def _hash(value: Any) -> str:
    return "sha256:" + hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def path(root: Path, workflow_id: str) -> Path:
    return ownership.binding_path(root.resolve(), workflow_id).parent / "denial-audit-v1.json"


def show(root: Path, workflow_id: str) -> dict[str, Any]:
    root=root.resolve(); destination=path(root,workflow_id)
    if not destination.is_file():
        binding=ownership.show(root,workflow_id); payload={"schema_version":"1","type":"tailtrail-workflow-denial-audit","workflow_id":workflow_id,"tailtrail_run_id":binding["tailtrail_run_id"],"denials":[],"boundary":"Categorical denial metadata only; hostile values and raw error text are never retained."}; payload["audit_fingerprint"]=_hash({key:value for key,value in payload.items() if key!="audit_fingerprint"}); return payload
    payload=json.loads(destination.read_text(encoding="utf-8")); contracts.require_valid(payload)
    expected=_hash({key:value for key,value in payload.items() if key!="audit_fingerprint"})
    if payload["audit_fingerprint"]!=expected: raise ValueError("denial audit fingerprint is invalid")
    return {"artifact":destination.relative_to(root).as_posix(),**payload}


def categorize(message: str) -> str:
    value=message.lower()
    if "approval" in value or "author" in value: return "authority"
    if "safe relative" in value or "path" in value or "reference" in value: return "path"
    if any(term in value for term in ("privacy","secret","credential","raw_")): return "privacy"
    if "retry" in value: return "retry"
    if "provider" in value: return "provider"
    if "stale" in value or "fresh" in value or "policy" in value: return "freshness"
    if "cross-" in value or "another run" in value or "another workflow" in value: return "cross-boundary"
    if "completion" in value or "evidence" in value or "closure" in value: return "completion"
    if "integrity" in value or "hash" in value or "fingerprint" in value: return "integrity"
    return "contract"


def record(root: Path, workflow_id: str, operation: str, category: str, source: str) -> dict[str, Any]:
    if category not in REASONS: raise ValueError("denial category is unsupported")
    if source not in {"mcp","cli","retention"}: raise ValueError("denial source is unsupported")
    if not operation or any(char not in "abcdefghijklmnopqrstuvwxyz0123456789_-" for char in operation.lower()): raise ValueError("denial operation is not categorical")
    root=root.resolve(); current=show(root,workflow_id); clean={key:value for key,value in current.items() if key!="artifact"}
    row={"sequence":len(clean["denials"])+1,"operation":operation.lower(),"category":category,"reason_code":REASONS[category],"source":source}
    clean["denials"].append(row); clean["audit_fingerprint"]=_hash({key:value for key,value in clean.items() if key!="audit_fingerprint"}); contracts.require_valid(clean); LEDGER.atomic_json(path(root,workflow_id),clean)
    binding=ownership.show(root,workflow_id); LEDGER.append_event(root,binding["tailtrail_run_id"],"workflow_action_denied",{"workflow_id":workflow_id,**row})
    return {"artifact":path(root,workflow_id).relative_to(root).as_posix(),**clean,"record":row}


def best_effort(root: Path, workflow_id: str | None, operation: str, message: str, source: str) -> None:
    if not workflow_id: return
    try:
        if ownership.binding_path(root.resolve(),workflow_id).is_file(): record(root,workflow_id,operation,categorize(message),source)
    except (OSError,ValueError,json.JSONDecodeError):
        return
