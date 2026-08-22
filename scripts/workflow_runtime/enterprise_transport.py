"""Phase 12 pluggable state store, leases, fencing, transport, and replay."""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Protocol

from workflow_runtime import contracts, enterprise, ownership, storage

LEDGER = ownership.LEDGER
EVENT_INPUT = {"event_id", "workflow_id", "tailtrail_run_id", "tenant_id", "actor_id", "sequence", "event_kind", "lease_id", "fencing_token", "canonical_event_ref", "canonical_event_hash"}


class StateStore(Protocol):
    """Provider adapters implement metadata-only get/put/list/append operations."""
    def get(self, key: str) -> dict[str, Any] | None: ...
    def put(self, key: str, value: dict[str, Any]) -> None: ...
    def list(self, prefix: str) -> list[str]: ...
    def append_event(self, workflow_id: str, value: dict[str, Any]) -> None: ...


class LocalReferenceStore:
    """Dependency-free conformance adapter; never contacts a provider."""
    def __init__(self, root: Path): self.root = enterprise.directory(root) / "state-store"
    def _path(self, key: str) -> Path:
        if not contracts.safe_relative(key): raise ValueError("enterprise state-store key is unsafe")
        return self.root / key
    def get(self, key: str) -> dict[str, Any] | None:
        path = self._path(key); return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None
    def put(self, key: str, value: dict[str, Any]) -> None: LEDGER.atomic_json(self._path(key), value)
    def list(self, prefix: str) -> list[str]:
        base = self._path(prefix)
        if not base.exists(): return []
        return sorted(path.relative_to(self.root).as_posix() for path in base.rglob("*.json") if path.is_file())
    def append_event(self, workflow_id: str, value: dict[str, Any]) -> None:
        path = self._path(f"events/{workflow_id}.jsonl"); path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(enterprise.canonical(value) + "\n"); handle.flush(); os.fsync(handle.fileno())


def store(root: Path) -> StateStore:
    return LocalReferenceStore(root.resolve())


def _now() -> datetime: return datetime.now(timezone.utc)
def _stamp(value: datetime) -> str: return value.isoformat().replace("+00:00", "Z")
def _lease_key(workflow_id: str) -> str: return f"leases/{workflow_id}.json"
def _event_path(root: Path, workflow_id: str) -> Path: return enterprise.directory(root)/"state-store"/"events"/f"{workflow_id}.jsonl"


def _events(root: Path, workflow_id: str) -> list[dict[str, Any]]:
    path = _event_path(root, workflow_id)
    if not path.is_file(): return []
    rows = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        try: value = json.loads(line)
        except json.JSONDecodeError as error: raise ValueError(f"enterprise event journal is corrupt at line {number}") from error
        if not isinstance(value, dict): raise ValueError(f"enterprise event journal is invalid at line {number}")
        rows.append(value)
    return rows


def _valid_lease(root: Path, workflow_id: str, tenant_id: str, actor_id: str, lease_id: str, fencing_token: str) -> dict[str, Any]:
    value = store(root).get(_lease_key(workflow_id))
    if not value: raise ValueError("enterprise workflow has no active lease")
    contracts.require_valid(value)
    expected = enterprise.digest({key:item for key,item in value.items() if key != "lease_fingerprint"})
    if value["lease_fingerprint"] != expected: raise ValueError("enterprise lease fingerprint is invalid")
    if value["state"] != "active" or value["tenant_id"] != tenant_id or value["actor_id"] != actor_id or value["lease_id"] != lease_id or value["fencing_token"] != fencing_token: raise ValueError("enterprise lease or fencing token is stale or unauthorized")
    if datetime.fromisoformat(value["expires_at"].replace("Z", "+00:00")) <= _now(): raise ValueError("enterprise lease has expired")
    enterprise.authorize(root, workflow_id, tenant_id, actor_id)
    return value


def acquire(root: Path, workflow_id: str, tenant_id: str, actor_id: str, approved: bool) -> dict[str, Any]:
    if approved is not True: raise ValueError("enterprise lease acquisition requires explicit approval")
    root = root.resolve(); binding = enterprise.authorize(root, workflow_id, tenant_id, actor_id); policy = enterprise._policy(root, Path(binding["policy_ref"]).stem); state_store = store(root)
    with LEDGER.RunLock(enterprise.directory(root)/"locks"/f"{workflow_id}.lock"):
        prior = state_store.get(_lease_key(workflow_id)); epoch = int(prior.get("epoch", 0)) + 1 if prior else 1; issued = _now(); expires = issued + timedelta(seconds=policy["limits"]["lease_seconds"])
        token = "fence-" + enterprise.digest({"workflow_id":workflow_id,"epoch":epoch,"tenant_id":tenant_id}).removeprefix("sha256:")[:24]
        payload = {"schema_version":"1", "type":"tailtrail-workflow-enterprise-lease", "lease_id":f"entl-{workflow_id}-{epoch}", "workflow_id":workflow_id, "tailtrail_run_id":binding["tailtrail_run_id"], "tenant_id":tenant_id, "actor_id":actor_id, "epoch":epoch, "fencing_token":token, "issued_at":_stamp(issued), "expires_at":_stamp(expires), "state":"active", "lease_fingerprint":"", "boundary":"Bounded metadata lease only. The fencing token grants no project write, approval, provider, publish, recovery, or completion authority."}
        payload["lease_fingerprint"] = enterprise.digest({key:item for key,item in payload.items() if key != "lease_fingerprint"}); contracts.require_valid(payload); state_store.put(_lease_key(workflow_id),payload)
    LEDGER.append_event(root,binding["tailtrail_run_id"],"workflow_enterprise_lease_acquired",{"workflow_id":workflow_id,"lease_id":payload["lease_id"],"epoch":epoch}); return payload


def release_lease(root: Path, workflow_id: str, tenant_id: str, actor_id: str, lease_id: str, fencing_token: str, approved: bool) -> dict[str, Any]:
    if approved is not True: raise ValueError("enterprise lease release requires explicit approval")
    root = root.resolve(); value = _valid_lease(root,workflow_id,tenant_id,actor_id,lease_id,fencing_token); value["state"]="released"; value["lease_fingerprint"]=""; value["lease_fingerprint"]=enterprise.digest({key:item for key,item in value.items() if key!="lease_fingerprint"}); contracts.require_valid(value); store(root).put(_lease_key(workflow_id),value); return value


def ingest(root: Path, workflow_id: str, receipt_ref: str, approved: bool) -> dict[str, Any]:
    if approved is not True: raise ValueError("enterprise event ingestion requires explicit approval")
    root = root.resolve(); _source_path, source = enterprise._read_ref(root, receipt_ref)
    if set(source) != EVENT_INPUT: raise ValueError("enterprise event receipt fields do not match the closed contract")
    if source["workflow_id"] != workflow_id: raise ValueError("enterprise event receipt belongs to another workflow")
    binding = enterprise.authorize(root,workflow_id,str(source["tenant_id"]),str(source["actor_id"])); _valid_lease(root,workflow_id,binding["tenant_id"],source["actor_id"],source["lease_id"],source["fencing_token"])
    if source["tailtrail_run_id"] != binding["tailtrail_run_id"] or source["event_kind"] not in {"checkpoint","continuation","child-linked","failover","migration","rollback"}: raise ValueError("enterprise event run or kind is invalid")
    canonical_path, _canonical = enterprise._read_ref(root, source["canonical_event_ref"])
    if enterprise.file_hash(canonical_path) != source["canonical_event_hash"] or not source["canonical_event_ref"].startswith(".tailtrail/"): raise ValueError("enterprise event canonical reference is stale or outside local runtime metadata")
    policy = enterprise._policy(root,Path(binding["policy_ref"]).stem)
    with LEDGER.RunLock(enterprise.directory(root)/"locks"/f"{workflow_id}.lock"):
        rows = _events(root,workflow_id)
        matching = [row for row in rows if row.get("event_id") == source["event_id"]]
        if matching:
            comparable = {key:item for key,item in matching[0].items() if key not in {"previous_event_hash","event_hash","boundary","schema_version","type"}}
            if comparable != source: raise ValueError("duplicate enterprise event ID has different content")
            return {"idempotent":True, **matching[0]}
        if len(rows) >= policy["limits"]["max_events_per_workflow"]: raise ValueError("enterprise event cost limit reached")
        if source["sequence"] != len(rows)+1: raise ValueError("enterprise event sequence has a gap or duplicate")
        previous = rows[-1]["event_hash"] if rows else None
        payload = {"schema_version":"1", "type":"tailtrail-workflow-enterprise-event", **source, "previous_event_hash":previous, "event_hash":"", "boundary":"Sanitized explicit transport receipt only. Ingestion did not execute work, retry code, contact a provider, or change canonical local workflow state."}
        payload["event_hash"] = enterprise.digest({key:item for key,item in payload.items() if key != "event_hash"}); contracts.require_valid(payload); store(root).append_event(workflow_id,payload)
    LEDGER.append_event(root,binding["tailtrail_run_id"],"workflow_enterprise_event_ingested",{"workflow_id":workflow_id,"event_id":source["event_id"],"sequence":source["sequence"]}); return {"idempotent":False,**payload}


def replay(root: Path, workflow_id: str) -> dict[str, Any]:
    root = root.resolve(); issues=[]
    try: binding=enterprise._binding(root,workflow_id); rows=_events(root,workflow_id)
    except (OSError,ValueError,json.JSONDecodeError):
        payload={"schema_version":"1","type":"tailtrail-workflow-enterprise-replay","workflow_id":workflow_id,"status":"blocked","valid":False,"events":[],"issues":["enterprise-state-invalid"],"last_event_hash":None,"boundary":"Read-only replay; no state was repaired or rewritten."}; contracts.require_valid(payload); return payload
    previous=None
    for index,row in enumerate(rows,1):
        try: contracts.require_valid(row)
        except ValueError: issues.append(f"event-{index}-contract-invalid"); continue
        if row["workflow_id"]!=workflow_id or row["tailtrail_run_id"]!=binding["tailtrail_run_id"] or row["tenant_id"]!=binding["tenant_id"]: issues.append(f"event-{index}-identity-invalid")
        if row["sequence"]!=index or row["previous_event_hash"]!=previous: issues.append(f"event-{index}-sequence-invalid")
        if row["event_hash"]!=enterprise.digest({key:item for key,item in row.items() if key!="event_hash"}): issues.append(f"event-{index}-hash-invalid")
        previous=row.get("event_hash")
    payload={"schema_version":"1","type":"tailtrail-workflow-enterprise-replay","workflow_id":workflow_id,"status":"valid" if not issues else "blocked","valid":not issues,"events":rows if not issues else [],"issues":issues,"last_event_hash":previous if not issues else None,"boundary":"Read-only deterministic metadata replay; canonical local journal and projection remain authoritative."}; contracts.require_valid(payload); return payload


def observe(root: Path, workflow_id: str) -> dict[str, Any]:
    root=root.resolve(); binding=enterprise._binding(root,workflow_id); canonical=storage.replay(root,workflow_id); distributed=replay(root,workflow_id); links=[]
    link_dir=enterprise.directory(root)/"links"
    if link_dir.is_dir():
        for path in sorted(link_dir.glob(f"{workflow_id}-*.json")):
            value=json.loads(path.read_text(encoding="utf-8")); contracts.require_valid(value); links.append({key:value[key] for key in ("child_workflow_id","child_run_id","child_repository_id","relationship","authority")})
    payload={"schema_version":"1","type":"tailtrail-workflow-enterprise-observability", "workflow_id":workflow_id, "tailtrail_run_id":binding["tailtrail_run_id"], "tenant_id":binding["tenant_id"], "repository_id":binding["repository_id"], "continuation_mode":binding["continuation_mode"], "canonical_status":canonical["status"], "transport_status":distributed["status"], "transport_event_count":len(distributed["events"]), "last_event_hash":distributed.get("last_event_hash"), "child_links":links, "read_only":True, "boundary":"Centralized sanitized metadata projection only. No source, prompt, raw log, provider request, workflow control, or project mutation is exposed or performed."}; contracts.require_valid(payload); return payload
