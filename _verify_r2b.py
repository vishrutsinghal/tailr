from __future__ import annotations

import re
from pathlib import Path

root = Path("d:/PD/tailr-main/tailtrail")
m_path = root / "scripts" / "metrics_extractor.py"
t_path = root / "tests" / "test_aidlc_reevaluation.py"
m_text = m_path.read_text(encoding="utf-8")
t_text = t_path.read_text(encoding="utf-8")

print("=== compute_re_evaluation definition ===")
start = m_text.find("def compute_re_evaluation")
print(m_text[start:start + 1400])

print()
print("=== test file: function/class names ===")
for m in re.finditer(r"^(class |def )", t_text, flags=re.MULTILINE):
    line_no = t_text.count("\n", 0, m.start()) + 1
    print(f"{line_no}: {t_text[m.start():m.start()+80].rstrip()}")

print()
print("=== test file: total lines ===", len(t_text.splitlines()))
