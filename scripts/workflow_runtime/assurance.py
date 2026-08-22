"""Inspect canonical runtime integrity, privacy, and governance without mutation."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any,Callable

from workflow_runtime import approvals, compiler, contracts, denials, ownership, storage, task_scope


def _hash(value: Any) -> str:
    return "sha256:"+hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":")).encode()).hexdigest()


def _check(check_id: str, operation: Callable[[],dict[str,Any]]) -> dict[str,Any]:
    try:
        result=operation(); valid=result.get("valid",result.get("fresh",True)); issues=[] if valid else ["validation-failed"]
        return {"check_id":check_id,"status":"passed" if valid else "blocked","issue_codes":issues}
    except (OSError,ValueError,json.JSONDecodeError): return {"check_id":check_id,"status":"blocked","issue_codes":["validation-failed"]}


def _privacy(root: Path, workflow_id: str, run_id: str) -> dict[str,Any]:
    directories=[ownership.binding_path(root,workflow_id).parent,ownership.LEDGER.state_dir(root,run_id)]; inspected=0; blocked=[]; codes=set()
    for directory in directories:
        if not directory.is_dir(): continue
        for path in sorted({*directory.rglob("*.json"),*directory.rglob("*.jsonl")}):
            relative=path.relative_to(root).as_posix(); inspected+=1
            if path.stat().st_size>contracts.MAX_ARTIFACT_BYTES: blocked.append(relative); codes.add("oversized-artifact"); continue
            try:
                values=[json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()] if path.suffix==".jsonl" else [json.loads(path.read_text(encoding="utf-8"))]
            except (UnicodeDecodeError,json.JSONDecodeError): blocked.append(relative); codes.add("invalid-json"); continue
            if any(contracts.privacy_issues(value) for value in values): blocked.append(relative); codes.add("privacy-violation")
    return {"files_inspected":inspected,"blocked_artifact_refs":sorted(set(blocked)),"issue_codes":sorted(codes)}


def inspect(root: Path, workflow_id: str) -> dict[str,Any]:
    root=root.resolve(); binding=ownership.show(root,workflow_id)
    checks=[_check("ownership",lambda:ownership.validate(root,workflow_id)),_check("compiler",lambda:compiler.validate(root,workflow_id)),_check("scope",lambda:task_scope.freshness(root,workflow_id)),_check("storage",lambda:storage.replay(root,workflow_id)),_check("approvals",lambda:approvals.validate(root,workflow_id))]
    if denials.path(root,workflow_id).is_file(): checks.append(_check("denial-audit",lambda:{"valid":bool(denials.show(root,workflow_id))}))
    privacy=_privacy(root,workflow_id,binding["tailtrail_run_id"]); blocked=any(row["status"]=="blocked" for row in checks) or bool(privacy["issue_codes"])
    payload={"schema_version":"1","type":"tailtrail-workflow-assurance-report","workflow_id":workflow_id,"status":"blocked" if blocked else "passed","checks":checks,"privacy":privacy,"report_fingerprint":"","boundary":"Read-only categorical assurance. It reports local references and issue codes only; no hostile content, source, prompt, log, credential, command, deletion, upload, repair, retry, provider, or completion action is produced."}; payload["report_fingerprint"]=_hash({key:value for key,value in payload.items() if key!="report_fingerprint"}); contracts.require_valid(payload); return payload


def _module(name: str, path: Path) -> Any:
    spec=importlib.util.spec_from_file_location(name,path); module=importlib.util.module_from_spec(spec); assert spec and spec.loader; spec.loader.exec_module(module); return module


def governance(root: Path) -> dict[str,Any]:
    root=root.resolve(); registry=json.loads((root/"tailtrail-registry.json").read_text(encoding="utf-8")); features=registry.get("features",[]); ids=[row.get("id") for row in features]; scripts=[item for row in features for item in row.get("scripts",[])]
    registry_ok=len(ids)==len(set(ids)) and len(scripts)==len(set(scripts)) and all(row.get("owner") for row in features)
    host=_module("phase10_host_conformance",root/"scripts"/"host-adapter-conformance.py"); host_ok=not host.check(root,host.load(root))
    sync=_module("phase10_adapter_sync",root/"scripts"/"sync-adapters.py"); adapter_ok=not sync.check()
    installer=_module("phase10_installer",root/"scripts"/"install-copilot.py"); entries=set(installer.pack_entries_for(installer.PACK_FILES,installer.PACK_DIRS,installer.PACK_SCRIPTS)); required={"scripts/workflow_runtime/assurance.py","scripts/workflow_runtime/denials.py","scripts/workflow_runtime/retention.py","schemas/workflow-denial-audit.schema.json","schemas/workflow-retention-policy.schema.json","schemas/workflow-retention-plan.schema.json","schemas/workflow-retention-cleanup.schema.json","schemas/workflow-assurance-report.schema.json"}
    commands=(root/"TAILTRAIL-COMMANDS.md").read_text(encoding="utf-8")
    documented=all(value in commands for value in ("workflow assurance inspect","workflow assurance governance","workflow retention cleanup"))
    checks={"registry-ownership-and-duplicate-scripts":"passed" if registry_ok else "blocked","adapter-synchronization":"passed" if host_ok and adapter_ok else "blocked","installed-pack-manifest":"passed" if required<=entries else "blocked","schema-command-documentation":"passed" if documented else "blocked"}
    return {"type":"tailtrail-workflow-governance-assurance","status":"passed" if set(checks.values())=={"passed"} else "blocked","checks":checks,"boundary":"Read-only local governance inspection; no adapter, manifest, registry, schema, documentation, installation, deletion, or upload was changed."}
