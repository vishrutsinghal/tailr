from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from workflow_runtime import capabilities, compiler, enterprise, ownership, state, storage, task_scope


def write(root: Path, name: str, value: dict) -> str:
    path=root/name; path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(value),encoding="utf-8"); return path.relative_to(root).as_posix()


def workflow(root: Path, run_id: str="enterprise-run") -> str:
    lock=ownership.LOCK; wid=ownership.suggested_id(run_id)
    lock.create(root,"enterprise workflow",run_id)
    lock.save_start_report(root,run_id,{"goal":"enterprise workflow","guided_delivery":{"mode":"guided-delivery"},"navigator":{"requirement_matrix":[{"display_id":"REQ-01","statement":"Continue safely.","kind":"change","acceptance_criteria":[],"preserve_rules":[],"likely_paths":["src/service.py"],"evidence_plan":[]}]}})
    lock.activate(root,run_id,True); ownership.bind(root,run_id,wid); capabilities.propose(root,wid,["code-graph-mapper","requirement-completion-harness","evidence-aware-testing","review"]); task_scope.initialize(root,wid); storage.initialize(root,wid); compiler.compile(root,wid); state.create(root,run_id,wid); return wid


def policy_source(root: Path, controls: dict | None=None, limits: dict | None=None) -> str:
    evidence=write(root,"enterprise-need.json",{"category":"cross-repository-continuation","observed":True})
    all_controls={key:True for key in enterprise.CONTROL_NAMES}
    return write(root,"enterprise-policy-input.json",{"policy_id":"entp-reference","adapter_id":"local-reference","need":"cross-repository","evidence_refs":[evidence],"controls":controls or all_controls,"tenants":[{"tenant_id":"tenant-alpha","actor_ids":["actor-operator"],"repository_ids":["repo-primary","repo-child"]}],"limits":limits or {"lease_seconds":300,"max_events_per_workflow":20,"max_backups":3,"retained_events":20}})


def activate(root: Path, wid: str, limits: dict | None=None) -> dict:
    enterprise.record_policy(root,policy_source(root,limits=limits),True)
    passed={"status":"passed","gate_fingerprint":"sha256:"+"a"*64}
    with patch.object(enterprise.release,"evaluate",return_value=passed):
        return enterprise.activate(root,wid,"entp-reference","tenant-alpha","repo-primary","actor-operator",True)


def event(root: Path, wid: str, lease: dict, sequence: int=1, event_id: str="ente-checkpoint-1") -> str:
    owner=ownership.show(root,wid); ref=owner["artifact"]
    return write(root,f"event-{sequence}.json",{"event_id":event_id,"workflow_id":wid,"tailtrail_run_id":owner["tailtrail_run_id"],"tenant_id":"tenant-alpha","actor_id":"actor-operator","sequence":sequence,"event_kind":"checkpoint","lease_id":lease["lease_id"],"fencing_token":lease["fencing_token"],"canonical_event_ref":ref,"canonical_event_hash":enterprise.file_hash(root/ref)})
