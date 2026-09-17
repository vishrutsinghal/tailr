import sys
sys.stdout.reconfigure(encoding='utf-8')
import pathlib, subprocess

p = pathlib.Path('d:/PD/tailr-main/tailtrail/docs/arch/navigator_aidlc_improvements.md')
content = p.read_text(encoding='utf-8')
lines = content.splitlines()

print('=== Phase Summary Table (lines 1263-1271) ===')
for i in range(1262, 1271):
    print(f'{i+1}: {lines[i]}')

print()
print('=== R-series table (lines 1272-1282) ===')
for i in range(1271, 1282):
    print(f'{i+1}: {lines[i]}')

print()
print('=== Tests ===')
out = subprocess.run(
    [sys.executable, '-m', 'unittest', 'tests.test_metrics_extractor', 'tests.test_aidlc_reevaluation', '-q'],
    cwd=str(p.parent), capture_output=True, text=True, timeout=120,
    env={**__import__('os').environ, 'PYTHONIOENCODING': 'utf-8'}
)
if out.stdout:
    print(out.stdout[-1500:])
if out.stderr:
    print('STDERR LAST 1200:', out.stderr[-1200:])
print('EXIT:', out.returncode)

print()
print('=== Compile check ===')
for f in ['scripts/metrics_extractor.py', 'scripts/planning_lock.py', 'scripts/task-start.py', 'tests/test_aidlc_reevaluation.py']:
    cp = subprocess.run([sys.executable, '-m', 'py_compile', str(p.parent / f)], capture_output=True, text=True)
    status = 'OK' if cp.returncode == 0 else 'FAIL'
    print(f'{f}: {status}')
