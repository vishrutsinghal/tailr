import sys, pathlib
sys.stdout.reconfigure(encoding='utf-8')
root = pathlib.Path('d:/PD/tailr-main/tailtrail')
docs = root / 'docs' / 'arch' / 'navigator_aidlc_improvements.md'
docs_lines = docs.read_text(encoding='utf-8').splitlines()

print("=== DOC: R2 / Phase 6 lines ===")
for i,l in enumerate(docs_lines):
    s = l.strip()
    if i>=1190 and i<=1340 and (
        s.startswith('### ') or s.startswith('|  ') or s.startswith('|-') or
        'R2' in l or 'Phase 6' in l or 'Re-Evaluation' in l or 're_eval' in l.lower()
    ):
        print(f"{i+1:>5}: {l.rstrip()}")

print()
print("=== metrics_extractor.py state ===")
me = root / 'scripts' / 'metrics_extractor.py'
me_text = me.read_text(encoding='utf-8')
me_lines = me_text.splitlines()
print(f"size={me.stat().st_size} lines={len(me_lines)}")
for i,l in enumerate(me_lines):
    s=l.strip()
    if s.startswith('def ') and ('re_eval' in s or 'compute' in s or 'schedule' in s):
        print(f"{i+1}: {l.rstrip()}")
print("Has re_evaluation_suggestion:", 're_evaluation_suggestion' in me_text)
print("Has re_evaluation_suggested field:", 're_evaluation_suggested' in me_text)
print("Has threshold line:", 'DEFAULT_THRESHOLDS' in me_text, "|", 'THRESHOLD' in me_text)

print()
print("=== planning_lock.py state ===")
pl = root / 'scripts' / 'planning_lock.py'
pl_text = pl.read_text(encoding='utf-8')
pl_lines = pl_text.splitlines()
print(f"size={pl.stat().st_size} lines={len(pl_lines)}")
for i,l in enumerate(pl_lines):
    s=l.strip()
    if s.startswith('def ') and ('create' in s or 'approve' in s):
        print(f"{i+1}: {l.rstrip()}")
print("Has re_evaluation_suggestion in create sig:", 're_evaluation_suggestion' in pl_text)
print("Has _re_evaluation_suggested in class:", '_re_evaluation_suggested' in pl_text)

print()
print("=== task-start.py re_eval wiring ===")
ts = root / 'scripts' / 'task-start.py'
ts_text = ts.read_text(encoding='utf-8')
ts_lines = ts_text.splitlines()
print(f"size={ts.stat().st_size} lines={len(ts_lines)}")
for i,l in enumerate(ts_lines):
    s=l.strip()
    if s.startswith('def ') and ('aidlc_mode' in s):
        print(f"{i+1}: {l.rstrip()}")
    if s.startswith('schedule_re_evaluation') or (s.startswith('re_evaluation_suggestion')):
        print(f"{i+1}: {l.rstrip()}")
print("Pending flag logic present:", 'pending' in ts_text.lower() and 're_eval' in ts_text.lower())
print("SCHEMA_PATH / lock-v1 references:", 'SCHEMA_PATH' in ts_text, 'lock-v1' in ts_text)

print()
print("=== test_aidlc_reevaluation.py state ===")
tst = root / 'tests' / 'test_aidlc_reevaluation.py'
if tst.exists():
    tst_text = tst.read_text(encoding='utf-8')
    print(f"size={tst.stat().st_size} lines={len(tst_text.splitlines())}")
    for i,l in enumerate(tst_text.splitlines()):
        if l.strip().startswith('def ') or l.strip().startswith('class '):
            print(f"{i+1}: {l.rstrip()}")
else:
    print("FILE MISSING")
