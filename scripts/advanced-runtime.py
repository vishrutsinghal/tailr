#!/usr/bin/env python3
"""Opt-in advanced runtime: graph plans, declared remote plans, live-eval receipts, claim auditing."""
from __future__ import annotations
import argparse,importlib.util,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def ledger():
 s=importlib.util.spec_from_file_location("advanced_ledger",ROOT/"scripts"/"run-ledger.py");m=importlib.util.module_from_spec(s);assert s and s.loader;s.loader.exec_module(m);return m
L=ledger()
def read(p):return json.loads(p.read_text(encoding="utf-8"))
def save(root,run,folder,event,payload):
 d=L.state_dir(root,run)/folder;p=d/f"{folder}-{len(list(d.glob('*.json')))+1}.json";L.atomic_json(p,payload);L.append_event(root,run,event,{"artifact":p.relative_to(root).as_posix()});return {"path":p.as_posix(),**payload}
def graph(root,run,input_path):
 raw=read(input_path);nodes=raw.get("nodes",[]);ids={x.get("id") for x in nodes}
 if not nodes or len(ids)!=len(nodes):raise ValueError("graph needs unique nodes")
 for x in nodes:
  if x.get("role") not in {"navigator","implementer","reviewer","harness","diagnostician"} or not set(x.get("depends_on",[])).issubset(ids-{x.get("id")}):raise ValueError("invalid graph role or dependency")
 return save(root,run,"agent-graphs","agent_graph_planned",{"schema_version":"1","type":"tailtrail-agent-graph","run_id":run,"nodes":nodes,"execution":"opt-in only; this artifact assigns bounded roles but does not start agents or edit source."})
def cloud(root,run,input_path,approved,remote_approved):
 raw=read(input_path);commands=raw.get("commands",[])
 if not isinstance(commands,list) or any(not isinstance(x,dict) or not x.get("repository_owned") or not isinstance(x.get("command"),list) for x in commands):raise ValueError("cloud manifest needs repository_owned argv commands")
 results=[]
 for x in commands:
  if not (approved and remote_approved):results.append({"id":x.get("id","command"),"outcome":"blocked","reason":"requires --approved and --remote-approved"});continue
  # This is intentionally a declared-runner boundary; callers choose whether to allow it.
  try:r=subprocess.run(x["command"],cwd=root,capture_output=True,text=True,timeout=int(x.get("timeout_seconds",120)),check=False);results.append({"id":x.get("id","command"),"outcome":"pass" if r.returncode==0 else "fail","exit_code":r.returncode})
  except (FileNotFoundError,subprocess.TimeoutExpired) as e:results.append({"id":x.get("id","command"),"outcome":"unavailable" if isinstance(e,FileNotFoundError) else "timed-out"})
 return save(root,run,"cloud-runs","cloud_runner_assessed",{"schema_version":"1","type":"tailtrail-declared-cloud-run","run_id":run,"results":results,"boundary":"No provider integration or credentials are created; only explicit repository-owned argv commands may run."})
def live_eval(root,run,input_path,approved):
 raw=read(input_path)
 if not approved:raise ValueError("live evaluation receipt recording requires --approved")
 if raw.get("model_result") not in {"pass","fail","inconclusive"} or not raw.get("model") or not raw.get("artifact_path"):raise ValueError("live evaluation needs model, model_result, and artifact_path")
 return save(root,run,"live-evaluations","live_evaluation_recorded",{"schema_version":"1","type":"tailtrail-live-model-evaluation","run_id":run,"model":raw["model"],"model_result":raw["model_result"],"artifact_path":raw["artifact_path"],"default":False,"boundary":"An explicitly supplied result is recorded; TailTrail does not call a model by default."})
def claims(root,run,input_path):
 raw=read(input_path);claims=raw.get("claims",[]);findings=[]
 for x in claims:
  if not isinstance(x,dict) or not x.get("claim"):raise ValueError("each claim needs claim text")
  quantitative=any(w in x["claim"].lower() for w in ("%","token","faster","time","quality","reduction"))
  measured=x.get("evidence_label")=="measured" and bool(x.get("artifact_path"))
  if quantitative and not measured:findings.append({"claim":x["claim"],"status":"rejected","reason":"quantitative claim lacks measured artifact evidence"})
  else:findings.append({"claim":x["claim"],"status":"allowed","reason":"non-quantitative or measured with artifact"})
 return save(root,run,"claim-audits","claim_audited",{"schema_version":"1","type":"tailtrail-claim-audit","run_id":run,"findings":findings,"boundary":"Unmeasured quality, time, and token-savings claims are rejected."})
def main():
 p=argparse.ArgumentParser();s=p.add_subparsers(dest="action",required=True)
 for name in ("graph","cloud","live-eval","claims"):
  x=s.add_parser(name);x.add_argument("--root",type=Path,default=Path.cwd());x.add_argument("--run-id",required=True);x.add_argument("--input",type=Path,required=True)
  if name=="cloud":x.add_argument("--approved",action="store_true");x.add_argument("--remote-approved",action="store_true")
  if name=="live-eval":x.add_argument("--approved",action="store_true")
 a=p.parse_args()
 try:
  r=a.root.resolve();out=graph(r,a.run_id,a.input) if a.action=="graph" else cloud(r,a.run_id,a.input,a.approved,a.remote_approved) if a.action=="cloud" else live_eval(r,a.run_id,a.input,a.approved) if a.action=="live-eval" else claims(r,a.run_id,a.input);print(json.dumps(out,indent=2,sort_keys=True));return 0
 except (OSError,ValueError,KeyError,json.JSONDecodeError) as e:print(f"Advanced runtime error: {e}");return 2
if __name__=="__main__":raise SystemExit(main())
