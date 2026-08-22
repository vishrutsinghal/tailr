"""Deferred Phase 11 deterministic, sanitized real-run and release proof."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

from workflow_runtime import assurance, compiler, contracts, evidence, ownership, retention, storage

LEDGER=ownership.LEDGER
PROJECT=Path(__file__).resolve().parents[2]
TEMPLATES={"small-change","delivery","risk-sensitive","review-only","ci-scanner-remediation","repository-discovery"}
SCENARIOS={
    "small-bug-focused-proof":("focused-unit-proof",),
    "delivery-aidlc-handoff":("aidlc-clarification","handoff-recorded"),
    "risk-sensitive-change":("risk-authority-preserved","guarded-validation"),
    "review-fix-rejected":("optional-fix-rejected","review-only-preserved"),
    "ci-graph-recheck":("graph-overlay","linked-recheck"),
    "vulnerability-scan-fix":("scan-approved","fix-separately-approved"),
    "dependency-policy-rejection":("dependency-rejected","project-unchanged"),
    "repository-discovery-summary":("read-only-discovery","architecture-summary"),
    "interrupted-resume-source-change":("interruption-recorded","source-change-detected","bounded-resume"),
    "stale-graph-refresh":("graph-stale","explicit-refresh","fresh-graph"),
    "policy-change-during-pause":("paused","policy-change-detected","approval-invalidated"),
    "repeated-correction-replan":("correction-limit","recovery-replan"),
    "recovery-conflict-preservation":("conflict-detected","unrelated-work-preserved"),
    "cross-repository-reference":("reference-read-only","target-authority-preserved"),
    "accepted-incomplete-closure":("incomplete-visible","explicit-acceptance","no-positive-learning"),
}
SCENARIO_TEMPLATES={
    "small-bug-focused-proof":{"small-change"}, "delivery-aidlc-handoff":{"delivery"}, "risk-sensitive-change":{"risk-sensitive"},
    "review-fix-rejected":{"review-only"}, "ci-graph-recheck":{"ci-scanner-remediation"}, "vulnerability-scan-fix":{"risk-sensitive"},
    "dependency-policy-rejection":{"risk-sensitive"}, "repository-discovery-summary":{"repository-discovery"},
    "interrupted-resume-source-change":{"small-change","delivery"}, "stale-graph-refresh":{"repository-discovery"},
    "policy-change-during-pause":{"risk-sensitive"}, "repeated-correction-replan":{"delivery","risk-sensitive"},
    "recovery-conflict-preservation":{"risk-sensitive"}, "cross-repository-reference":{"repository-discovery"},
    "accepted-incomplete-closure":{"small-change","review-only"},
}


def _load(name: str, relative: str) -> Any:
    path=Path(__file__).resolve().parents[1]/relative; spec=importlib.util.spec_from_file_location(name,path); module=importlib.util.module_from_spec(spec); assert spec and spec.loader; spec.loader.exec_module(module); return module


HOST=_load("dwr11_host_runtime","host-runtime-conformance.py")


def _hash(value: Any) -> str:
    return "sha256:"+hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":")).encode()).hexdigest()


def _file_hash(path: Path) -> str:
    return "sha256:"+hashlib.sha256(path.read_bytes()).hexdigest()


def _read_ref(root: Path, ref: str) -> tuple[Path,dict[str,Any]]:
    if not contracts.safe_relative(ref): raise ValueError("release evidence reference must be safe and repository-relative")
    path=(root/ref).resolve()
    try: path.relative_to(root.resolve())
    except ValueError as error: raise ValueError("release evidence reference escapes the repository") from error
    if not path.is_file() or path.stat().st_size>contracts.MAX_ARTIFACT_BYTES: raise ValueError("release evidence reference is missing or oversized")
    value=json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value,dict) or contracts.privacy_issues(value): raise ValueError("release evidence must be one privacy-safe JSON object")
    return path,value


def _directory(root: Path) -> Path: return root.resolve()/".tailtrail"/"release-proof"
def catalog() -> dict[str,Any]: return {"type":"tailtrail-workflow-release-scenario-catalog","scenario_count":len(SCENARIOS),"scenarios":[{"scenario_id":key,"required_observations":list(value),"allowed_templates":sorted(SCENARIO_TEMPLATES[key])} for key,value in SCENARIOS.items()],"templates":sorted(TEMPLATES),"boundary":"Closed deterministic evidence catalog only; listing does not run a scenario or claim release readiness."}


def _linked(root: Path, workflow_id: str, refs: list[str]) -> dict[str,str]:
    binding=ownership.show(root,workflow_id); bases=[ownership.binding_path(root,workflow_id).parent.resolve(),LEDGER.state_dir(root,binding["tailtrail_run_id"]).resolve()]; hashes={}; linked=False
    for ref in sorted(set(refs)):
        path,_value=_read_ref(root,ref); hashes[ref]=_file_hash(path)
        if any(path==base or base in path.parents for base in bases): linked=True
    if not refs or not linked: raise ValueError("release proof needs at least one canonical workflow/run evidence reference")
    return hashes


def record_scenario(root: Path, workflow_id: str, observation_ref: str, approved: bool) -> dict[str,Any]:
    if approved is not True: raise ValueError("scenario proof recording requires explicit approval")
    root=root.resolve(); _path,source=_read_ref(root,observation_ref); allowed={"scenario_id","workflow_id","tailtrail_run_id","outcome","observations","evidence_refs"}
    if set(source)!=allowed: raise ValueError("scenario observation fields do not match the closed contract")
    if not isinstance(source.get("observations"),list) or not isinstance(source.get("evidence_refs"),list) or not all(isinstance(item,str) for item in [*source["observations"],*source["evidence_refs"]]): raise ValueError("scenario observations and evidence references must be string arrays")
    scenario=str(source["scenario_id"]); binding=ownership.show(root,workflow_id); plan=compiler.show(root,workflow_id)
    if scenario not in SCENARIOS or source["workflow_id"]!=workflow_id or source["tailtrail_run_id"]!=binding["tailtrail_run_id"] or source["outcome"]!="passed": raise ValueError("scenario observation identity or outcome is invalid")
    if plan["template_id"] not in SCENARIO_TEMPLATES[scenario]: raise ValueError("scenario observation uses an incompatible compiler template")
    observations=sorted(set(source["observations"])); missing=set(SCENARIOS[scenario])-set(observations)
    if missing or not all(isinstance(item,str) and item.replace("-","").isalnum() for item in observations): raise ValueError("scenario observation is incomplete or non-categorical")
    if not ownership.validate(root,workflow_id)["valid"] or not compiler.validate(root,workflow_id)["valid"] or not storage.replay(root,workflow_id)["valid"]: raise ValueError("scenario canonical workflow checks failed")
    hashes=_linked(root,workflow_id,list(source["evidence_refs"])); payload={"schema_version":"1","type":"tailtrail-workflow-release-scenario","scenario_id":scenario,"workflow_id":workflow_id,"tailtrail_run_id":binding["tailtrail_run_id"],"template_id":plan["template_id"],"outcome":"passed","observations":observations,"evidence_refs":sorted(hashes),"evidence_hashes":hashes,"receipt_fingerprint":"","boundary":"Sanitized deterministic scenario evidence only. Recording did not execute, retry, migrate, call a provider, or infer release readiness."}; payload["receipt_fingerprint"]=_hash({k:v for k,v in payload.items() if k!="receipt_fingerprint"}); contracts.require_valid(payload)
    destination=_directory(root)/"scenarios"/f"{scenario}-{workflow_id}.json"; LEDGER.atomic_json(destination,payload); LEDGER.append_event(root,binding["tailtrail_run_id"],"workflow_release_scenario_recorded",{"workflow_id":workflow_id,"scenario_id":scenario,"artifact":destination.relative_to(root).as_posix()}); return {"artifact":destination.relative_to(root).as_posix(),**payload}


def record_real_run(root: Path, workflow_id: str, observation_ref: str, approved: bool) -> dict[str,Any]:
    if approved is not True: raise ValueError("real-run proof recording requires explicit approval")
    root=root.resolve(); _path,source=_read_ref(root,observation_ref); allowed={"proof_id","workflow_id","tailtrail_run_id","host_receipt_refs","requirements","metrics"}
    if set(source)!=allowed: raise ValueError("real-run observation fields do not match the closed contract")
    if not isinstance(source.get("host_receipt_refs"),list) or not all(isinstance(item,str) for item in source["host_receipt_refs"]) or not isinstance(source.get("requirements"),dict) or not isinstance(source.get("metrics"),dict): raise ValueError("real-run hosts, requirements, and metrics have invalid types")
    binding=ownership.show(root,workflow_id); plan=compiler.show(root,workflow_id)
    if source["workflow_id"]!=workflow_id or source["tailtrail_run_id"]!=binding["tailtrail_run_id"]: raise ValueError("real-run observation identity is cross-boundary")
    receipt_path=evidence.receipt_path(root,workflow_id)
    if not receipt_path.is_file(): raise ValueError("real-run proof requires canonical completion")
    completion=json.loads(receipt_path.read_text()); contracts.require_valid(completion)
    if completion["state"]!="completed" or not evidence.validate(root,workflow_id)["valid"] or assurance.inspect(root,workflow_id)["status"]!="passed": raise ValueError("real-run proof requires completed canonical privacy-safe assurance")
    host_refs=list(source["host_receipt_refs"]); hosts=set(); host_hashes={}
    for ref in host_refs:
        _host_path,host_receipt=_read_ref(root,ref); host_hashes[ref]=_file_hash(_host_path)
        if host_receipt.get("run_id")!=binding["tailtrail_run_id"]: raise ValueError("host receipt belongs to another run")
        result=HOST.validate_receipt(root,str(host_receipt.get("host")),host_receipt)
        if result["evaluation"]!="passed": raise ValueError("real-run host receipt is not currently passed")
        hosts.add(result["host"])
    if hosts!=HOST.HOSTS: raise ValueError("real-run proof requires passed Codex, Copilot, and Claude receipts")
    requirements=source["requirements"]; metrics=source["metrics"]
    if requirements!={"complete":True,"preserved":True,"unresolved_drift":0}: raise ValueError("real-run requirements must be complete, preserved, and drift-free")
    if metrics.get("false_approvals") or metrics.get("duplicate_executions") or metrics.get("false_interventions") or metrics.get("recovery_safe") is not True or (metrics.get("resume_checks",0)>0 and metrics.get("resume_accurate") is not True): raise ValueError("real-run proof contains a material safety issue")
    payload={"schema_version":"1","type":"tailtrail-workflow-real-run-proof","proof_id":source["proof_id"],"workflow_id":workflow_id,"tailtrail_run_id":binding["tailtrail_run_id"],"template_id":plan["template_id"],"target_identity_fingerprint":binding["target_identity_fingerprint"],"compiler_plan_fingerprint":plan["plan_fingerprint"],"completion_receipt_ref":receipt_path.relative_to(root).as_posix(),"completion_receipt_hash":_file_hash(receipt_path),"host_receipt_refs":sorted(host_refs),"host_receipt_hashes":host_hashes,"requirements":requirements,"metrics":metrics,"status":"accepted","proof_fingerprint":"","boundary":"Sanitized accepted local real-run facts only. Counts are observations, not productivity, quality, time, or token-savings claims."}; payload["proof_fingerprint"]=_hash({k:v for k,v in payload.items() if k!="proof_fingerprint"}); contracts.require_valid(payload)
    destination=_directory(root)/"real-runs"/f"{plan['template_id']}-{workflow_id}.json"; LEDGER.atomic_json(destination,payload); LEDGER.append_event(root,binding["tailtrail_run_id"],"workflow_real_run_proof_recorded",{"workflow_id":workflow_id,"template_id":plan["template_id"],"artifact":destination.relative_to(root).as_posix()}); return {"artifact":destination.relative_to(root).as_posix(),**payload}


def _saved(root: Path, path: Path, kind: str, fingerprint: str) -> dict[str,Any]:
    value=json.loads(path.read_text()); contracts.require_valid(value)
    expected=_hash({key:item for key,item in value.items() if key!=fingerprint})
    if value.get(fingerprint)!=expected: raise ValueError("saved release evidence fingerprint is invalid")
    if kind=="scenario":
        for ref,digest in value["evidence_hashes"].items():
            evidence_path,_payload=_read_ref(root,ref)
            if _file_hash(evidence_path)!=digest: raise ValueError("saved scenario evidence is stale")
    else:
        binding=ownership.show(root,value["workflow_id"]); plan=compiler.show(root,value["workflow_id"])
        if binding["tailtrail_run_id"]!=value["tailtrail_run_id"] or binding["target_identity_fingerprint"]!=value["target_identity_fingerprint"] or plan["plan_fingerprint"]!=value["compiler_plan_fingerprint"]: raise ValueError("saved real-run proof is stale or cross-boundary")
        completion_path,_completion=_read_ref(root,value["completion_receipt_ref"])
        if _file_hash(completion_path)!=value["completion_receipt_hash"]: raise ValueError("saved real-run completion evidence is stale")
        for ref,digest in value["host_receipt_hashes"].items():
            host_path,_host=_read_ref(root,ref)
            if _file_hash(host_path)!=digest: raise ValueError("saved real-run host evidence is stale")
        if set(value["host_receipt_refs"])!=set(value["host_receipt_hashes"]): raise ValueError("saved real-run host evidence set is inconsistent")
    return value


def show(root: Path) -> dict[str,Any]:
    root=root.resolve(); directory=_directory(root); scenarios=[_saved(root,p,"scenario","receipt_fingerprint") for p in sorted((directory/"scenarios").glob("*.json"))] if (directory/"scenarios").is_dir() else []; proofs=[_saved(root,p,"real","proof_fingerprint") for p in sorted((directory/"real-runs").glob("*.json"))] if (directory/"real-runs").is_dir() else []
    return {"type":"tailtrail-workflow-release-evidence","scenarios":scenarios,"real_runs":proofs,"boundary":"Read-only sanitized release evidence; no scenario, host, migration, retirement, or project action was run."}


def compatibility(root: Path) -> dict[str,Any]:
    root=root.resolve(); host_check=_load("dwr11_host_instruction","host-adapter-conformance.py"); matrix=host_check.load(host_check.ROOT); host={item["id"]:(not host_check.check(host_check.ROOT,matrix)) for item in matrix["hosts"]}; installer=_load("dwr11_installer","install-copilot.py"); entries=set(installer.pack_entries_for(installer.PACK_FILES,installer.PACK_DIRS,installer.PACK_SCRIPTS)); required_pack={"scripts/workflow_runtime/release.py","docs/workflow-release-migration.md","schemas/workflow-release-scenario.schema.json","schemas/workflow-real-run-proof.schema.json","schemas/workflow-release-gate.schema.json","schemas/workflow-compatibility-report.schema.json","schemas/workflow-retirement-decision.schema.json"}; pack_complete=required_pack<=entries; commands=(PROJECT/"TAILTRAIL-COMMANDS.md").read_text(); roadmap=(PROJECT/"ROADMAP.md").read_text(); changelog=(PROJECT/"CHANGELOG.md").read_text(); migration=PROJECT/"docs"/"workflow-release-migration.md"; rollback=migration.is_file() and "Rollback" in migration.read_text(); policy=retention.default_policy(); no_workflow=all("--no-workflow" in body for body in (commands,roadmap,changelog)); passed=all(host.values()) and pack_complete and no_workflow and policy["manual_cleanup_only"] and not policy["background_deletion"] and rollback
    payload={"schema_version":"1","type":"tailtrail-workflow-compatibility-report","status":"passed" if passed else "blocked","existing_commands_authoritative":True,"existing_artifacts_authoritative":True,"automatic_history_migration":False,"explicit_compatible_adapters_only":True,"host_guidance":host,"installed_pack_complete":pack_complete,"no_workflow_documented":no_workflow,"retention_manual_only":policy["manual_cleanup_only"] and not policy["background_deletion"],"aliases":[],"rollback_documented":rollback,"report_fingerprint":"","boundary":"Read-only compatibility assessment. No old workflow history is migrated, converted, deleted, aliased, or uploaded."}; payload["report_fingerprint"]=_hash({k:v for k,v in payload.items() if k!="report_fingerprint"}); contracts.require_valid(payload); return payload


def evaluate(root: Path) -> dict[str,Any]:
    root=root.resolve(); issues=[]
    try: saved=show(root)
    except (OSError,ValueError,json.JSONDecodeError): saved={"scenarios":[],"real_runs":[]}; issues.append("release-evidence-invalid")
    scenario_ids={row.get("scenario_id") for row in saved["scenarios"] if row.get("outcome")=="passed"}; template_ids={row.get("template_id") for row in saved["real_runs"] if row.get("status")=="accepted"}; host_report=HOST.report(root); hosts={row["host"]:row["runtime_status"] for row in host_report["runtime_conformance"]}; proofs=saved["real_runs"]; quality={"approval_prompts":sum(row["metrics"]["approval_prompts"] for row in proofs),"false_approvals":sum(row["metrics"]["false_approvals"] for row in proofs),"stale_recomputations":sum(row["metrics"]["stale_recomputations"] for row in proofs),"resume_checks":sum(row["metrics"]["resume_checks"] for row in proofs),"inaccurate_resumes":sum(row["metrics"]["resume_checks"]>0 and row["metrics"]["resume_accurate"] is not True for row in proofs),"duplicate_executions":sum(row["metrics"]["duplicate_executions"] for row in proofs),"false_interventions":sum(row["metrics"]["false_interventions"] for row in proofs),"correction_cycles":sum(row["metrics"]["correction_cycles"] for row in proofs),"unsafe_recoveries":sum(row["metrics"]["recovery_safe"] is not True for row in proofs),"review_observations":sum(row["metrics"]["review_effort"]!="not-measured" for row in proofs),"measured_token_receipts":sum(row["metrics"]["measured_token_receipts"] for row in proofs),"estimated_token_receipts":sum(row["metrics"]["estimated_token_receipts"] for row in proofs)}; compat=compatibility(root)
    if scenario_ids!=set(SCENARIOS): issues.append("scenario-coverage-incomplete")
    if template_ids!=TEMPLATES: issues.append("template-coverage-incomplete")
    if set(hosts)!=HOST.HOSTS or any(value!="passed" for value in hosts.values()): issues.append("host-conformance-incomplete")
    if any(quality[key] for key in ("false_approvals","inaccurate_resumes","duplicate_executions","false_interventions","unsafe_recoveries")): issues.append("material-safety-observation")
    if proofs and (quality["approval_prompts"]==0 or quality["stale_recomputations"]==0 or quality["resume_checks"]==0 or quality["review_observations"]==0): issues.append("operational-observation-coverage-missing")
    if not proofs or quality["measured_token_receipts"]+quality["estimated_token_receipts"]==0: issues.append("token-coverage-missing")
    if compat["status"]!="passed": issues.append("compatibility-incomplete")
    payload={"schema_version":"1","type":"tailtrail-workflow-release-gate","status":"passed" if not issues else "blocked","scenario_coverage":{"passed":len(scenario_ids),"required":len(SCENARIOS),"missing":sorted(set(SCENARIOS)-scenario_ids)},"template_coverage":{"passed":len(template_ids),"required":len(TEMPLATES),"missing":sorted(TEMPLATES-template_ids)},"host_conformance":hosts,"quality":quality,"compatibility":{"status":compat["status"],"report_fingerprint":compat["report_fingerprint"]},"retirement_requires_separate_approval":True,"issues":issues,"gate_fingerprint":"","boundary":"Read-only fail-closed release assessment. Passing does not retire --no-workflow; a separate exact-fingerprint approval and release change are required."}; payload["gate_fingerprint"]=_hash({k:v for k,v in payload.items() if k!="gate_fingerprint"}); contracts.require_valid(payload); return payload


def retire(root: Path, gate_fingerprint: str, approved: bool) -> dict[str,Any]:
    if approved is not True: raise ValueError("compatibility retirement requires separate explicit approval")
    root=root.resolve(); gate=evaluate(root)
    if gate["status"]!="passed" or gate["gate_fingerprint"]!=gate_fingerprint: raise ValueError("compatibility retirement requires the exact current passing release gate")
    payload={"schema_version":"1","type":"tailtrail-workflow-retirement-decision","gate_fingerprint":gate_fingerprint,"decision":"retire-no-workflow","approved":True,"state":"approved-for-separate-release-change","boundary":"Decision evidence only. This command does not remove --no-workflow, migrate history, change source, publish, deploy, or release."}; contracts.require_valid(payload); path=_directory(root)/"retirement-decision-v1.json"; LEDGER.atomic_json(path,payload); return {"artifact":path.relative_to(root).as_posix(),**payload}
