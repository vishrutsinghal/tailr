import pathlib, re

root = pathlib.Path(__file__).resolve().parents[1]

scripts_content = (root / "scripts" / "task-start.py").read_text(encoding="utf-8")
scripts_lines = scripts_content.splitlines()
print("=== task-start.py line count:", len(scripts_lines))
print("=== re_evaluation/suggestion/metrics_extractor/scope_quality/scopes:")
for i, line in enumerate(scripts_lines, 1):
    low = line.lower()
    if (re.search(r're_evaluation|suggestion|metrics_extractor|scope_quality|scope_evidence|investigate|ModeDecisionLog|helix_mode_decision_log|thresholds', line)
        or 'compute_complexity' in low
        or 'build_report' in low
        or 'aidlc_mode' in low):
        print(f"  scripts/task-start.py:{i}: {line.rstrip()}")

extra = (root / "scripts" / "navigator_scope.py").read_text(encoding="utf-8")
for i, line in enumerate(extra.splitlines(), 1):
    low = line.lower()
    if (re.search(r're_evaluation|suggestion|scope_quality|compute_complexity', line)
        or 'aidlc_mode' in low):
        print(f"  scripts/navigator_scope.py:{i}: {line.rstrip()}")

for pyfile in (root / "tests").glob("*.py"):
    file_lines = pyfile.read_text(encoding="utf-8").splitlines()
    if any('re_evaluation' in l.lower() or 'ReEvaluation' in l for l in file_lines):
        print(f"\n=== {pyfile.name} line count: {len(file_lines)}")
        for i, line in enumerate(file_lines, 1):
            low = line.lower()
            if (re.search(r're_evaluation|ReEvaluation|suggestion|ModeDecisionLog|helix_mode_decision_log', line)
                or 'compute_complexity' in low
                or 'suggest' in low):
                print(f"  {pyfile.name}:{i}: {line.rstrip()}")
