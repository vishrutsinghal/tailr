#!/usr/bin/env python3
"""Structured, local Phase 8.2-8.8 evidence controls; no provider calls."""
from __future__ import annotations
import argparse,importlib.util,json,subprocess
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[1];OUTCOMES={"pass","fail","blocked","timed-out","unavailable"}
def ledger():
 s=importlib.util.spec_from_file_location("phase8_ledger",ROOT/"scripts"/"run-ledger.py");m=importlib.util.module_from_spec(s);assert s and s.loader;s.loader.exec_module(m);return m
L=ledger()
def read(p):return json.loads(p.read_text(encoding="utf-8"))
def anchor(root,run):return read(L.state_dir(root,run)/"anchors"/"approved-v1.json")
def save(root,run,kind,event,payload):
 directory=L.state_dir(root,run)/kind;path=directory/f"{kind}-{len(list(directory.glob('*.json')))+1}.json";L.atomic_json(path,payload);L.append_event(root,run,event,{"artifact":path.relative_to(root).as_posix()});return {"path":path.as_posix(),**payload}
def journey(root,run,input_path):
 raw=read(input_path);items=raw.get("journeys",raw);known={x["requirement_uid"] for x in anchor(root,run)["requirements"]};rows=[]
 if not isinstance(items,list):raise ValueError("journey input needs a journeys list")
 for item in items:
  required={"requirement_uid","test_id","framework","outcome","environment","steps","fixtures","preservation"}
  if not isinstance(item,dict) or required-set(item) or item["requirement_uid"] not in known:raise ValueError("journey row is missing fields or references an unknown requirement")
  if item["framework"] not in {"playwright","cypress","webdriver"} or item["outcome"] not in OUTCOMES:raise ValueError("unsupported journey framework or outcome")
  rows.append(item)
 return save(root,run,"journeys","journey_mapped",{"schema_version":"1","type":"tailtrail-journey-mapping","run_id":run,"journeys":rows,"boundary":"Imported local journey results are requirement-linked evidence, not a live browser run."})
def contracts(root,run,input_path):
 raw=read(input_path);kind=raw.get("format","").lower();known={x["requirement_uid"] for x in anchor(root,run)["requirements"]};rows=[]
 if kind in {"openapi","asyncapi"}:
  units=raw.get("paths",{}) if kind=="openapi" else raw.get("channels",{})
  rows=[{"contract_id":f"{kind}:{key}","compatibility":"not-evaluated","boundary":key} for key in units]
 elif kind=="pact": rows=[{"contract_id":str(x.get("description","pact-interaction")),"compatibility":x.get("outcome","not-evaluated"),"boundary":"producer-consumer"} for x in raw.get("interactions",[])]
 elif kind=="schema": rows=[{"contract_id":str(x.get("id","schema")),"compatibility":x.get("outcome","not-evaluated"),"boundary":x.get("boundary","")} for x in raw.get("contracts",[])]
 else:raise ValueError("format must be openapi, asyncapi, pact, or schema")
 for item in rows:
  item["requirement_uid"]=raw.get("requirement_uid","")
  if item["requirement_uid"] and item["requirement_uid"] not in known:raise ValueError("contract requirement_uid is not approved")
 return save(root,run,"contracts","contract_parsed",{"schema_version":"1","type":"tailtrail-contract-evidence","run_id":run,"format":kind,"contracts":rows,"boundary":"Parser describes supplied local contract structure/results; compatibility is not inferred when absent."})
def lifecycle(root,run,input_path,approved):
 raw=read(input_path);items=raw.get("adapters",raw)
 if not isinstance(items,list):raise ValueError("lifecycle input needs adapters list")
 rows=[]
 for item in items:
  required={"id","phase","command","environment","remote","repository_owned"}
  if not isinstance(item,dict) or required-set(item) or item["phase"] not in {"setup","health","cleanup"} or not isinstance(item["command"],list) or item["repository_owned"] is not True:raise ValueError("lifecycle adapter must be repository-owned and valid")
  if not approved: rows.append({"id":item["id"],"phase":item["phase"],"outcome":"blocked","reason":"requires --approved"});continue
  if item["remote"]:rows.append({"id":item["id"],"phase":item["phase"],"outcome":"blocked","reason":"remote lifecycle adapters are plan-only"});continue
  try:r=subprocess.run(item["command"],cwd=root,capture_output=True,text=True,timeout=int(item.get("timeout_seconds",120)),check=False);rows.append({"id":item["id"],"phase":item["phase"],"outcome":"pass" if r.returncode==0 else "fail","exit_code":r.returncode})
  except (FileNotFoundError,subprocess.TimeoutExpired) as e:rows.append({"id":item["id"],"phase":item["phase"],"outcome":"unavailable" if isinstance(e,FileNotFoundError) else "timed-out"})
 return save(root,run,"lifecycle","environment_lifecycle_assessed",{"schema_version":"1","type":"tailtrail-environment-lifecycle","run_id":run,"results":rows,"boundary":"Only supplied local repository commands run with --approved; no environment is provisioned by TailTrail."})
def deployment(root,run,input_path):
 raw=read(input_path);required={"deployment","migration","rollback"}
 if required-set(raw):raise ValueError("deployment plan needs deployment, migration, rollback")
 for key in required:
  if not isinstance(raw[key],dict) or not raw[key].get("command"):raise ValueError(f"{key} needs a repository-owned command")
 return save(root,run,"deployment-safety","deployment_safety_planned",{"schema_version":"1","type":"tailtrail-deployment-safety-plan","run_id":run,"plan":raw,"status":"planned","requires_approval":True,"boundary":"Plan only: TailTrail does not deploy, migrate, or roll back from this command."})
def policy(root,run,policy_path,receipts_path,signer,approved):
 policy=read(policy_path);raw_receipts=read(receipts_path);receipts=raw_receipts.get("receipts",raw_receipts) if isinstance(raw_receipts,dict) else raw_receipts;required=set(policy.get("required_tiers",[]));passed={x.get("tier") for x in receipts if x.get("outcome")=="pass"};missing=sorted(required-passed);result={"schema_version":"1","type":"tailtrail-release-policy","run_id":run,"policy_id":policy.get("id","local-policy"),"missing_tiers":missing,"rollback_required":bool(policy.get("require_rollback",False)),"eligible":not missing,"sign_off":None,"boundary":"Policy evaluation is evidence completeness, never release authorization."}
 if signer:
  if not approved:raise ValueError("sign-off requires --approved")
  if missing:raise ValueError("cannot sign off while required tiers are missing")
  result["sign_off"]={"signer":signer,"status":"recorded-local"}
 return save(root,run,"release-policy","release_policy_evaluated",result)
def calibration(root,run,input_path):
 raw=read(input_path);items=raw.get("runs",raw)
 if not isinstance(items,list):raise ValueError("calibration input needs runs list")
 baseline=sum(float(x.get("baseline_completion",0)) for x in items);harness=sum(float(x.get("harness_completion",0)) for x in items);payload={"schema_version":"1","type":"tailtrail-real-run-calibration","run_id":run,"runs":len(items),"baseline_completion_total":baseline,"harness_completion_total":harness,"delta":harness-baseline,"evidence_label":"measured" if raw.get("measured",False) else "local-evidence","boundary":"Metrics summarize supplied run artifacts only; no general quality claim is inferred."};return save(root,run,"evaluation-calibration","evaluation_calibrated",payload)
def main():
 p=argparse.ArgumentParser();sub=p.add_subparsers(dest="action",required=True)
 for action in ("journey","contracts","lifecycle","deployment","calibration"):
  x=sub.add_parser(action);x.add_argument("--root",type=Path,default=Path.cwd());x.add_argument("--run-id",required=True);x.add_argument("--input",type=Path,required=True)
  if action=="lifecycle":x.add_argument("--approved",action="store_true")
 x=sub.add_parser("release-policy");x.add_argument("--root",type=Path,default=Path.cwd());x.add_argument("--run-id",required=True);x.add_argument("--policy",type=Path,required=True);x.add_argument("--receipts",type=Path,required=True);x.add_argument("--signer");x.add_argument("--approved",action="store_true")
 a=p.parse_args()
 try:
  root=a.root.resolve();result=journey(root,a.run_id,a.input) if a.action=="journey" else contracts(root,a.run_id,a.input) if a.action=="contracts" else lifecycle(root,a.run_id,a.input,a.approved) if a.action=="lifecycle" else deployment(root,a.run_id,a.input) if a.action=="deployment" else calibration(root,a.run_id,a.input) if a.action=="calibration" else policy(root,a.run_id,a.policy,a.receipts,a.signer,a.approved);print(json.dumps(result,indent=2,sort_keys=True));return 0
 except (OSError,ValueError,KeyError,json.JSONDecodeError) as e:print(f"Phase 8 advanced error: {e}");return 2
if __name__=="__main__":raise SystemExit(main())
