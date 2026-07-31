#!/usr/bin/env python3
"""Keep local per-test outcome history; never retries or masks a failure."""
from __future__ import annotations
import argparse,importlib.util,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def ledger():
 s=importlib.util.spec_from_file_location("flaky_ledger",ROOT/"scripts"/"run-ledger.py");m=importlib.util.module_from_spec(s);assert s and s.loader;s.loader.exec_module(m);return m
L=ledger()
def record(root,run_id,test_id,outcome):
 if outcome not in {"pass","fail","blocked","timed-out","unavailable"}:raise ValueError("unsupported outcome")
 directory=L.state_dir(root,run_id)/"flaky-tests";history=[]
 for path in sorted(directory.glob("*.json")):
  item=json.loads(path.read_text(encoding="utf-8"));
  if item.get("test_id")==test_id:history.append(item["outcome"])
 outcomes=history+[outcome];status="flaky" if "pass" in outcomes and "fail" in outcomes else ("failing" if outcome=="fail" else "stable")
 payload={"schema_version":"1","type":"tailtrail-flaky-test-observation","run_id":run_id,"test_id":test_id,"outcome":outcome,"history":outcomes,"status":status,"boundary":"Observation only: TailTrail does not rerun, suppress, or downgrade a failing test."};path=directory/f"observation-{len(list(directory.glob('observation-*.json')))+1}.json";L.atomic_json(path,payload);L.append_event(root,run_id,"flaky_test_observed",{"artifact":path.relative_to(root).as_posix(),"test_id":test_id,"status":status});return {"path":path.as_posix(),**payload}
def main():
 p=argparse.ArgumentParser();p.add_argument("--root",type=Path,default=Path.cwd());p.add_argument("--run-id",required=True);p.add_argument("--test-id",required=True);p.add_argument("--outcome",required=True);a=p.parse_args()
 try:print(json.dumps(record(a.root.resolve(),a.run_id,a.test_id,a.outcome),indent=2,sort_keys=True));return 0
 except (OSError,ValueError,KeyError,json.JSONDecodeError) as e:print(f"Flaky test tracker error: {e}");return 2
if __name__=="__main__":raise SystemExit(main())
