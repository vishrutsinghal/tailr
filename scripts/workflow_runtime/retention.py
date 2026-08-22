"""Plan count-based local retention and perform only explicit terminal cleanup."""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from workflow_runtime import contracts, ownership, storage


LEDGER=ownership.LEDGER
TERMINAL={"completed","cancelled","superseded"}


def _hash(value: Any) -> str:
    return "sha256:"+hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":")).encode()).hexdigest()


def policy_fingerprint(value: dict[str,Any]) -> str:
    return _hash({key:item for key,item in value.items() if key!="policy_fingerprint"})


def default_policy() -> dict[str,Any]:
    value={"schema_version":"1","type":"tailtrail-workflow-retention-policy","policy_id":"wfret-local-default","max_terminal_workflows":100,"manual_cleanup_only":True,"preserve_nonterminal":True,"background_deletion":False,"upload":False,"policy_fingerprint":"","boundary":"Count-based local retention with explicit manual cleanup only; no background deletion or upload."}; value["policy_fingerprint"]=policy_fingerprint(value); return value


def _policy(root: Path, policy_ref: str|None) -> tuple[dict[str,Any],str|None]:
    if policy_ref is None: value=default_policy(); return value,None
    path,pointer=ownership._resolve_ref(root,policy_ref)
    if pointer: raise ValueError("retention policy reference cannot use a JSON pointer")
    value=json.loads(path.read_text(encoding="utf-8")); contracts.require_valid(value)
    if value["policy_fingerprint"]!=policy_fingerprint(value): raise ValueError("retention policy fingerprint is invalid")
    return value,policy_ref


def show(root: Path, policy_ref: str|None=None) -> dict[str,Any]:
    root=root.resolve(); value,ref=_policy(root,policy_ref)
    return {"policy_ref":ref,"policy":value,"boundary":"Read-only retention policy; no directory is scanned, deleted, uploaded, or changed."}


def plan(root: Path, policy_ref: str|None=None) -> dict[str,Any]:
    root=root.resolve(); policy,ref=_policy(root,policy_ref); directory=root/".tailtrail"/"workflows"; terminal=[]
    if directory.is_dir():
        for item in sorted(directory.iterdir()):
            if not item.is_dir() or not item.name.startswith("ttw-"): continue
            try: status=storage.status(root,item.name)["last_valid_projection"]["workflow_status"]
            except (OSError,ValueError,json.JSONDecodeError): continue
            if status in TERMINAL: terminal.append(item.name)
    keep=policy["max_terminal_workflows"]; retained=terminal[-keep:]; candidates=terminal[:-keep] if len(terminal)>keep else []
    payload={"schema_version":"1","type":"tailtrail-workflow-retention-plan","policy_ref":ref,"policy_fingerprint":policy["policy_fingerprint"],"terminal_workflow_ids":terminal,"retained_workflow_ids":retained,"candidate_workflow_ids":candidates,"plan_fingerprint":"","boundary":"Read-only count plan. Cleanup requires exact candidate ID, this fingerprint, and explicit approval; active/failed workflows and canonical run history remain preserved."}; payload["plan_fingerprint"]=_hash({key:value for key,value in payload.items() if key!="plan_fingerprint"}); contracts.require_valid(payload); return payload


def cleanup(root: Path, workflow_id: str, plan_fingerprint: str, policy_ref: str|None, approved: bool) -> dict[str,Any]:
    root=root.resolve()
    if approved is not True:
        raise ValueError("manual retention cleanup requires explicit approval")
    current=plan(root,policy_ref)
    if current["plan_fingerprint"]!=plan_fingerprint or workflow_id not in current["candidate_workflow_ids"]:
        raise ValueError("manual cleanup target is not an exact current retention candidate")
    binding=ownership.show(root,workflow_id); destination=ownership.binding_path(root,workflow_id).parent.resolve(); workflows=(root/".tailtrail"/"workflows").resolve()
    if destination.parent!=workflows or not destination.is_dir(): raise ValueError("manual cleanup target is outside the workflow retention root")
    receipt={"schema_version":"1","type":"tailtrail-workflow-retention-cleanup","workflow_id":workflow_id,"tailtrail_run_id":binding["tailtrail_run_id"],"policy_fingerprint":current["policy_fingerprint"],"plan_fingerprint":plan_fingerprint,"state":"removed-local-workflow-runtime","boundary":"Explicit manual cleanup removed only the selected terminal workflow runtime directory. Canonical run history was preserved; no upload or background deletion occurred."}
    contracts.require_valid(receipt)
    shutil.rmtree(destination)
    receipt_path=root/".tailtrail"/"retention"/f"cleanup-{workflow_id}.json"; LEDGER.atomic_json(receipt_path,receipt); LEDGER.append_event(root,binding["tailtrail_run_id"],"workflow_retention_cleanup_completed",{"workflow_id":workflow_id,"artifact":receipt_path.relative_to(root).as_posix(),"state":receipt["state"]})
    return {"artifact":receipt_path.relative_to(root).as_posix(),**receipt}
