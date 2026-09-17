from __future__ import annotations

import sys
import importlib.util
from pathlib import Path

root = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
scripts = root / "scripts"

def load_module(name, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot spec {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

m = load_module("metrics_extractor", scripts / "metrics_extractor.py")
pl = load_module("planning_lock", scripts / "planning_lock.py")

print("metrics_extractor.py:")
for name in (
    "compute_re_evaluation",
    "evaluate_scope_signal",
    "evaluate_scope_floor",
    "compute_complexity",
):
    print(f"  {name}: {'exists' if hasattr(m, name) else 'MISSING'}")

print("planning_lock.py:")
for name in ("create",):
    print(f"  {name}: {'exists' if hasattr(pl, name) else 'MISSING'}")

# inspect create's accepted params quickly
import inspect
sig = inspect.signature(pl.create)
print("planning_lock.create params:", list(sig.parameters.keys()))

import sys
sys.stdout.reconfigure(encoding='utf-8')
import pathlib

root = pathlib.Path('d:/PD/tailr-main/tailtrail')

results = {}

# 1. metrics_extractor.py - check for re-eval function
m = root / 'scripts' / 'metrics_extractor.py'
if m.exists():
    m_text = m.read_text(encoding='utf-8')
    m_lines = m_text.splitlines()
    reeval_funcs = []
    sec_headers = []
    for i, line in enumerate(m_lines, 1):
        s = line.strip()
        if 're_evaluate' in line or 'reevaluation' in line.lower():
            reeval_funcs.append(f'{i}: {s}')
        if s.startswith('### ') and len(s) < 120:
            sec_headers.append(f'{i}: {s}')
    results['metrics_extractor_functions'] = reeval_funcs
    results['metrics_extractor_sections'] = sec_headers
    results['metrics_extractor_lines'] = len(m_lines)
else:
    results['metrics_extractor_error'] = 'FILE NOT FOUND'

# 2. test_aidlc_reevaluation.py
t = root / 'tests' / 'test_aidlc_reevaluation.py'
if t.exists():
    t_text = t.read_text(encoding='utf-8')
    t_lines = t_text.splitlines()
    test_funcs = []
    for i, l in enumerate(t_lines, 1):
        stripped = l.strip()
        if 'def test' in stripped:
            test_funcs.append(f'{i}: {stripped[:120]}')
    results['test_functions'] = test_funcs
    results['test_total_lines'] = len(t_lines)
    results['test_count'] = len(test_funcs)
else:
    results['test_error'] = 'FILE NOT FOUND'

# 3. task-start.py wiring
ts = root / 'scripts' / 'task-start.py'
if ts.exists():
    ts_text = ts.read_text(encoding='utf-8')
    ts_lines = ts_text.splitlines()
    wiring = []
    for i, line in enumerate(ts_lines, 1):
        lowered = line.lower()
        if any(kw in lowered for kw in ['re_evaluate', 'reevaluation', '_reevaluate', 'lock_re_evaluation_suggested', 're_evaluation_snapshot']):
            wiring.append(f'{i}: {line.strip()[:150]}')
    results['task_start_wiring'] = wiring
else:
    results['ts_error'] = 'FILE NOT FOUND'

# 4. planning_lock.py approve/suggest
pl = root / 'scripts' / 'planning_lock.py'
if pl.exists():
    pl_text = pl.read_text(encoding='utf-8')
    pl_lines = pl_text.splitlines()
    approve = []
    for i, line in enumerate(pl_lines, 1):
        if any(kw in line.lower() for kw in ['re_evaluate', 're_evaluation', 'lock_re_evaluation_suggested']):
            approve.append(f'{i}: {line.strip()[:150]}')
    results['planning_lock_wiring'] = approve
else:
    results['pl_error'] = 'FILE NOT FOUND'

for k, v in results.items():
    if isinstance(v, list):
        print(f'=== {k} ===')
        for item in v:
            print(item)
    else:
        print(f'{k}: {v}')
print()
print('--- SUMMARY ---')
mll = results.get('metrics_extractor_lines')
print(f'metrics_extractor.py: {mll} lines' if mll else 'metrics_extractor.py: MISSING')
print(f're-eval functions found: {len(results.get("metrics_extractor_functions", []))}')
print(f'sections found: {len(results.get("metrics_extractor_sections", []))}')
ttl = results.get('test_total_lines')
print(f'test_aidlc_reevaluation.py: {ttl} lines, {results.get("test_count", "MISSING")} tests' if ttl else 'test file: MISSING')
print(f'task-start.py wiring sites: {len(results.get("task_start_wiring", []))}')
print(f'planning_lock.py approve sites: {len(results.get("planning_lock_wiring", []))}')
