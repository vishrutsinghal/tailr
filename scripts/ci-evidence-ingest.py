#!/usr/bin/env python3
"""Normalize saved CI result JSON into requirement-linked local receipts."""
from __future__ import annotations
import argparse,importlib.util,json
from pathlib import Path
from typing import Any
ROOT=Path(__file__).resolve().parents[1];TIERS={"unit","component","integration","contract","e2e","infrastructure","release-smoke"};OUTCOMES={"pass","fail","blocked","timed-out","unavailable"}
def ledger():
 s=importlib.util.spec_from_file_location("ci_ledger",ROOT/"scripts"/"run-ledger.py");m=importlib.util.module_from_spec(s);assert s and s.loader;s.loader.exec_module(m);return m
L=ledger()
def ingest(root:Path,run_id:str,input_path:Path)->dict[str,Any]:
 raw=json.loads(input_path.read_text(encoding="utf-8"));items=raw.get("results",raw) if isinstance(raw,dict) else raw;provenance=raw.get("provenance",{}) if isinstance(raw,dict) else {}
 if not isinstance(items,list):raise ValueError("CI input needs a results list")
 known={r["requirement_uid"] for r in json.loads((L.state_dir(root,run_id)/"anchors"/"approved-v1.json").read_text(encoding="utf-8"))["requirements"]};receipts=[];directory=L.state_dir(root,run_id)/"validation-receipts"
 for item in items:
  required={"requirement_uid","tier","outcome","command","environment","asserted_behavior"}
  if not isinstance(item,dict) or required-set(item):raise ValueError("every CI result needs requirement_uid, tier, outcome, command, environment, asserted_behavior")
  if item["requirement_uid"] not in known or item["tier"] not in TIERS or item["outcome"] not in OUTCOMES:raise ValueError("CI result has unknown requirement, tier, or outcome")
  receipt={**item,"schema_version":"1","type":"tailtrail-validation-evidence-receipt","evidence_label":"ci-artifact","artifact_path":str(item.get("artifact_path","")),"ci_provenance":provenance,"boundary":"Saved CI JSON is ingested locally; no CI network request was made."};path=directory/f"{item['requirement_uid']}-{item['tier']}-{len(list(directory.glob('*.json')))+1}.json";L.atomic_json(path,receipt);receipts.append({"path":path.as_posix(),**receipt})
 provenance_fields={"run_id","run_url","commit_sha","job","environment","expires_at"};artifact=L.state_dir(root,run_id)/"ci-ingestion"/f"ingestion-{len(list((L.state_dir(root,run_id)/'ci-ingestion').glob('ingestion-*.json')))+1}.json";payload={"schema_version":"1","type":"tailtrail-ci-evidence-ingestion","run_id":run_id,"source":input_path.as_posix(),"provenance":provenance,"provenance_missing":sorted(provenance_fields-set(provenance)),"receipts":receipts,"boundary":"Ingestion records supplied CI evidence; it does not assert that CI is current or authoritative."};L.atomic_json(artifact,payload);L.append_event(root,run_id,"ci_evidence_ingested",{"artifact":artifact.relative_to(root).as_posix(),"receipts":len(receipts)});return {"path":artifact.as_posix(),**payload}
def main():
 p=argparse.ArgumentParser();p.add_argument("--root",type=Path,default=Path.cwd());p.add_argument("--run-id",required=True);p.add_argument("--input",type=Path,required=True);a=p.parse_args()
 try:print(json.dumps(ingest(a.root.resolve(),a.run_id,a.input),indent=2,sort_keys=True));return 0
 except (OSError,ValueError,KeyError,json.JSONDecodeError) as e:print(f"CI evidence ingestion error: {e}");return 2
if __name__=="__main__":raise SystemExit(main())
