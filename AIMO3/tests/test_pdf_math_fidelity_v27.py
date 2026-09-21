from pathlib import Path
import os, sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.input_adapter import AIMOInputAdapter

pdf = os.environ.get("AIMO_REFERENCE_PDF", "/mnt/data/AIMO3_Reference_Problems.pdf")
if not Path(pdf).exists():
    print("test_pdf_math_fidelity_v27: SKIP (set AIMO_REFERENCE_PDF)")
    raise SystemExit(0)

problems = AIMOInputAdapter.from_pdf(pdf, benchmark_mode=True)
assert len(problems) >= 5

p2 = problems[1]
p3 = problems[2]
p5 = problems[4]

assert "10^{5}" in p2.solver_text, p2.solver_text
assert "10^{5}" in p3.solver_text, p3.solver_text
assert "2^{20}" in p5.solver_text, p5.solver_text
assert "2^{20−i}" in p5.solver_text or "2^{20-i}" in p5.solver_text, p5.solver_text
assert "10^{k}" in p5.solver_text, p5.solver_text
assert "10^{5}" in p5.solver_text, p5.solver_text

# Benchmark answers/solutions must not leak into model-facing text.
for p in problems[:5]:
    low = p.solver_text.lower()
    assert "answer:" not in low
    assert "solution:" not in low

print("test_pdf_math_fidelity_v27: PASS")
