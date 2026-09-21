from pathlib import Path
import os, sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.input_adapter import AIMOInputAdapter

pdf = os.environ.get('AIMO_REFERENCE_PDF')
if not pdf:
    print('test_pdf_reader: SKIP (set AIMO_REFERENCE_PDF)')
    raise SystemExit(0)
items = AIMOInputAdapter.load(pdf, benchmark_mode=True)
assert len(items) == 10, len(items)
assert [x.expected_answer for x in items] == [50,520,336,580,21818,32951,57447,32193,160,8687]
for x in items:
    low = x.problem_text.lower()
    assert 'solution:' not in low
    assert 'answer:' not in low
print('test_pdf_reader: PASS')
