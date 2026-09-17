import sys, pathlib, subprocess
sys.stdout.reconfigure(encoding='utf-8')

root = pathlib.Path('d:/PD/tailr-main/tailtrail')

# Compile check
print("=== Compile check ===")
for name in ['scripts/metrics_extractor.py', 'scripts/planning_lock.py', 'scripts/task-start.py', 'tests/test_aidlc_reevaluation.py']:
    p = root / name
    ok = subprocess.run([sys.executable, '-m', 'py_compile', str(p)], capture_output=True, text=True).returncode == 0
    print(f"  {name}: {'OK' if ok else 'FAIL'}")

print("\n=== Run tests ===")
for cmd_name, desc in [
    ('unittest tests.test_metrics_extractor tests.test_aidlc_reevaluation tests.test_navigator_scope',
     'metrics + R2 + navigator_scope'),
]:
    r = subprocess.run([sys.executable, '-m'] + cmd_name.split(),
                       cwd=str(root), capture_output=True, text=True, timeout=180)
    out = r.stdout + r.stderr
    # Show last 40 lines
    lines = out.splitlines()
    print(f"\n--- {desc} (rc={r.returncode}) ---")
    print('\n'.join(lines[-40:]))
    # Show key summary line
    for line in lines:
        if 'Ran' in line and 'OK' in line or 'FAIL' in line or 'ERROR' in line:
            print(f"SUMMARY: {line}")

print("\n=== Git status ===")
print(subprocess.run(['git','-C',str(root),'status','--short'], capture_output=True, text=True, timeout=30).stdout)

print("\n=== Temp files ===")
for p in root.glob('._tmp*'):
    print(f"  {p.name}")
print(subprocess.run(['cmd','/c','dir','_tmp*.py','_fix*.py','r2_*.txt','/b'],
                    cwd=str(root), capture_output=True, text=True, timeout=15).stdout)
