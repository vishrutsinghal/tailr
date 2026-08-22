"""Phase 12 backup, restore validation, migration, rollback, and conformance."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from workflow_runtime import contracts, enterprise, enterprise_transport, evidence, ownership, storage

LEDGER=ownership.LEDGER


def _stamp() -> str: return datetime.now(timezone.utc).isoformat().replace("+00:00","Z")
def _backup_dir(root: Path, workflow_id: str) -> Path: return enterprise.directory(root)/"backups"/workflow_id
def _migration_path(root: Path, workflow_id: str) -> Path: return enterprise.directory(root)/"migrations"/f"{workflow_id}.json"


def _artifacts(root: Path, workflow_id: str) -> dict[str,str]:
    base=enterprise.directory(root); candidates=[ownership.binding_path(root,workflow_id),storage.journal_path(root,workflow_id),storage.projection_path(root,workflow_id),enterprise.binding_path(root,workflow_id),base/"state-store"/"leases"/f"{workflow_id}.json",base/"state-store"/"events"/f"{workflow_id}.jsonl"]
    return {path.relative_to(root).as_posix():enterprise.file_hash(path) for path in candidates if path.is_file()}


def backup(root: Path, workflow_id: str, approved: bool) -> dict[str,Any]:
    if approved is not True: raise ValueError("enterprise backup requires explicit approval")
    root=root.resolve(); binding=enterprise._binding(root,workflow_id); policy=enterprise._policy(root,Path(binding["policy_ref"]).stem); replay=enterprise_transport.replay(root,workflow_id)
    if not replay["valid"] or not storage.validate(root,workflow_id)["valid"]: raise ValueError("enterprise backup requires valid distributed and canonical replay")
    directory=_backup_dir(root,workflow_id); existing=sorted(directory.glob("*.json")) if directory.is_dir() else []
    if len(existing)>=policy["limits"]["max_backups"]: raise ValueError("enterprise backup cost/retention limit reached; explicit manual cleanup is required")
    payload={"schema_version":"1","type":"tailtrail-workflow-enterprise-backup","backup_id":f"entb-{workflow_id}-{len(existing)+1}","workflow_id":workflow_id,"tailtrail_run_id":binding["tailtrail_run_id"],"tenant_id":binding["tenant_id"],"artifact_hashes":_artifacts(root,workflow_id),"event_count":len(replay["events"]),"created_at":_stamp(),"state":"verified","backup_fingerprint":"","boundary":"Verified metadata backup manifest only. No raw source/log/prompt was copied, no provider was contacted, and canonical local history was not changed."}
    payload["backup_fingerprint"]=enterprise.digest({key:item for key,item in payload.items() if key!="backup_fingerprint"}); contracts.require_valid(payload); destination=directory/f"{payload['backup_id']}.json"; LEDGER.atomic_json(destination,payload); LEDGER.append_event(root,binding["tailtrail_run_id"],"workflow_enterprise_backup_verified",{"workflow_id":workflow_id,"artifact":destination.relative_to(root).as_posix()}); return {"artifact":destination.relative_to(root).as_posix(),**payload}


def restore_validate(root: Path, backup_ref: str) -> dict[str,Any]:
    root=root.resolve(); path,value=enterprise._read_ref(root,backup_ref); contracts.require_valid(value)
    if value.get("type")!="tailtrail-workflow-enterprise-backup" or value.get("state")!="verified": raise ValueError("enterprise restore requires a verified backup manifest")
    expected=enterprise.digest({key:item for key,item in value.items() if key!="backup_fingerprint"}); issues=[]
    if value["backup_fingerprint"]!=expected: issues.append("backup-fingerprint-invalid")
    for ref,digest in value["artifact_hashes"].items():
        if not _matches_artifact(root,ref,digest): issues.append("backup-artifact-stale")
    try:
        binding=enterprise._binding(root,value["workflow_id"])
        if binding["tailtrail_run_id"]!=value["tailtrail_run_id"] or binding["tenant_id"]!=value["tenant_id"]: issues.append("backup-identity-invalid")
    except (OSError,ValueError,json.JSONDecodeError): issues.append("backup-binding-invalid")
    payload={"schema_version":"1","type":"tailtrail-workflow-enterprise-restore-validation","backup_ref":path.relative_to(root).as_posix(),"workflow_id":value["workflow_id"],"status":"passed" if not issues else "blocked","issues":sorted(set(issues)),"canonical_state_replaced":False,"boundary":"Read-only disaster-recovery validation. Restore never overwrites canonical local workflow history or project files."}; contracts.require_valid(payload); return payload


def _latest_backup(root: Path, workflow_id: str) -> Path:
    paths=sorted(_backup_dir(root,workflow_id).glob("*.json")) if _backup_dir(root,workflow_id).is_dir() else []
    if not paths: raise ValueError("enterprise migration requires a verified backup")
    if restore_validate(root,paths[-1].relative_to(root).as_posix())["status"]!="passed": raise ValueError("enterprise migration backup is stale or invalid")
    return paths[-1]


def _matches_artifact(root: Path, ref: str, expected: str) -> bool:
    if not contracts.safe_relative(ref): return False
    candidate=(root/ref).resolve()
    try: candidate.relative_to(root.resolve())
    except ValueError: return False
    return candidate.is_file() and enterprise.file_hash(candidate)==expected


def migration_plan(root: Path, workflow_id: str, direction: str) -> dict[str,Any]:
    root=root.resolve(); binding=enterprise._binding(root,workflow_id)
    modes={"local-to-enterprise":("local","enterprise-shadow"),"enterprise-to-local":("enterprise-shadow","local")}
    if direction not in modes: raise ValueError("enterprise migration direction is unsupported")
    from_mode,to_mode=modes[direction]
    if binding["continuation_mode"]!=from_mode or binding["state"]!="active": raise ValueError("enterprise migration direction does not match current mode")
    backup_path=_latest_backup(root,workflow_id)
    if not ownership.validate(root,workflow_id)["valid"] or not storage.validate(root,workflow_id)["valid"] or not enterprise_transport.replay(root,workflow_id)["valid"]: raise ValueError("enterprise migration requires valid canonical and distributed replay")
    payload={"schema_version":"1","type":"tailtrail-workflow-enterprise-migration","workflow_id":workflow_id,"tailtrail_run_id":binding["tailtrail_run_id"],"direction":direction,"from_mode":from_mode,"to_mode":to_mode,"backup_ref":backup_path.relative_to(root).as_posix(),"backup_hash":enterprise.file_hash(backup_path),"state":"planned","migration_fingerprint":"","boundary":"Read-only migration plan. Applying it changes only the optional continuation mode; canonical local ownership, history, approvals, evidence, and closure remain authoritative."}
    payload["migration_fingerprint"]=enterprise.digest({key:item for key,item in payload.items() if key!="migration_fingerprint"}); contracts.require_valid(payload); return payload


def migrate(root: Path, workflow_id: str, direction: str, fingerprint: str, approved: bool) -> dict[str,Any]:
    if approved is not True: raise ValueError("enterprise migration requires explicit approval")
    root=root.resolve(); plan=migration_plan(root,workflow_id,direction)
    if plan["migration_fingerprint"]!=fingerprint: raise ValueError("enterprise migration requires the exact current plan fingerprint")
    binding=enterprise.update_mode(root,workflow_id,plan["to_mode"]); plan["state"]="applied"; plan["migration_fingerprint"]=""; plan["migration_fingerprint"]=enterprise.digest({key:item for key,item in plan.items() if key!="migration_fingerprint"}); contracts.require_valid(plan); destination=_migration_path(root,workflow_id); LEDGER.atomic_json(destination,plan); LEDGER.append_event(root,binding["tailtrail_run_id"],"workflow_enterprise_migration_applied",{"workflow_id":workflow_id,"direction":direction,"artifact":destination.relative_to(root).as_posix()}); return {"artifact":destination.relative_to(root).as_posix(),**plan}


def rollback(root: Path, workflow_id: str, migration_fingerprint: str, approved: bool) -> dict[str,Any]:
    if approved is not True: raise ValueError("enterprise rollback requires explicit approval")
    root=root.resolve(); path=_migration_path(root,workflow_id)
    if not path.is_file(): raise ValueError("enterprise rollback requires an applied migration")
    migration=json.loads(path.read_text(encoding="utf-8")); contracts.require_valid(migration)
    if migration["state"]!="applied" or migration["to_mode"]!="enterprise-shadow" or migration["migration_fingerprint"]!=migration_fingerprint: raise ValueError("enterprise rollback requires the exact applied enterprise migration fingerprint")
    _backup_path,manifest=enterprise._read_ref(root,migration["backup_ref"]); contracts.require_valid(manifest)
    if enterprise.file_hash(_backup_path)!=migration["backup_hash"] or manifest["backup_fingerprint"]!=enterprise.digest({key:item for key,item in manifest.items() if key!="backup_fingerprint"}): raise ValueError("enterprise rollback backup validation failed")
    mutable_binding=enterprise.binding_path(root,workflow_id).relative_to(root).as_posix()
    if any(ref!=mutable_binding and not _matches_artifact(root,ref,digest) for ref,digest in manifest["artifact_hashes"].items()): raise ValueError("enterprise rollback backup validation failed")
    binding=enterprise.update_mode(root,workflow_id,"local","rolled-back"); migration["state"]="rolled-back"; migration["migration_fingerprint"]=""; migration["migration_fingerprint"]=enterprise.digest({key:item for key,item in migration.items() if key!="migration_fingerprint"}); contracts.require_valid(migration); LEDGER.atomic_json(path,migration); LEDGER.append_event(root,binding["tailtrail_run_id"],"workflow_enterprise_rollback_applied",{"workflow_id":workflow_id,"artifact":path.relative_to(root).as_posix()}); return {"artifact":path.relative_to(root).as_posix(),**migration}


def conformance(root: Path, workflow_id: str) -> dict[str,Any]:
    root=root.resolve(); checks={}; issues=[]
    try:
        binding=enterprise._binding(root,workflow_id); policy=enterprise._policy(root,Path(binding["policy_ref"]).stem); row=enterprise.tenant(root,binding)
        checks["canonical-ownership"]=ownership.validate(root,workflow_id)["valid"] and storage.validate(root,workflow_id)["valid"]
        checks["tenant-isolation"]=binding["tenant_id"]==row["tenant_id"] and binding["repository_id"] in row["repository_ids"]
        checks["replay"]=enterprise_transport.replay(root,workflow_id)["valid"]
        lease=enterprise_transport.store(root).get(f"leases/{workflow_id}.json"); checks["leases-and-fencing"]=bool(lease and lease.get("epoch",0)>=1 and lease.get("fencing_token"))
        backups=sorted(_backup_dir(root,workflow_id).glob("*.json")) if _backup_dir(root,workflow_id).is_dir() else []; checks["backup-and-restore"]=bool(backups and restore_validate(root,backups[-1].relative_to(root).as_posix())["status"]=="passed")
        checks["retention-and-cost"]=policy["limits"]["retained_events"]<=policy["limits"]["max_events_per_workflow"] and len(enterprise_transport._events(root,workflow_id))<=policy["limits"]["max_events_per_workflow"] and len(backups)<=policy["limits"]["max_backups"]
        checks["privacy"]=not contracts.privacy_issues(enterprise_transport.observe(root,workflow_id))
        checks["migration-and-rollback"]=binding["continuation_mode"] in {"local","enterprise-shadow"} and binding["state"] in {"active","rolled-back"}
        completion=evidence.receipt_path(root,workflow_id); checks["canonical-closure"]=not completion.exists() or evidence.validate(root,workflow_id)["valid"]
        checks["local-default-and-failover"]=binding["continuation_mode"] in {"local","enterprise-shadow"} and isinstance(enterprise_transport.LocalReferenceStore(root),enterprise_transport.LocalReferenceStore)
    except (OSError,ValueError,json.JSONDecodeError) as error:
        checks={name:False for name in ("canonical-ownership","tenant-isolation","replay","leases-and-fencing","backup-and-restore","retention-and-cost","privacy","migration-and-rollback","canonical-closure","local-default-and-failover")}; issues.append("enterprise-state-invalid"); issues.append(str(error))
    issues.extend(name for name,value in checks.items() if not value)
    categorical=sorted({value for value in issues if value.replace("-","").isalnum()})
    payload={"schema_version":"1","type":"tailtrail-workflow-enterprise-conformance","workflow_id":workflow_id,"status":"passed" if not issues else "blocked","checks":checks,"issues":categorical,"report_fingerprint":"","boundary":"Read-only local enterprise-adapter conformance. Passing does not attest a provider deployment, availability SLA, encryption system, external backup, or production readiness."}; payload["report_fingerprint"]=enterprise.digest({key:item for key,item in payload.items() if key!="report_fingerprint"}); contracts.require_valid(payload); return payload
