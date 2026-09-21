from pathlib import Path
import os, sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from core.input_adapter import AIMOInputAdapter
from core.family_engines import try_family_engine
from core.pipeline import FullOlympiadPipeline

pdf=os.environ.get('AIMO_REFERENCE_PDF')
if not pdf:
    print('test_family_engine_pdf_reference_v280: SKIP (AIMO_REFERENCE_PDF not set)')
    raise SystemExit(0)
probs=AIMOInputAdapter.load(pdf, benchmark_mode=True)
for idx, expected in [(2,520),(3,336),(4,580),(5,21818)]:
    p=probs[idx-1]
    a=FullOlympiadPipeline._analysis_dict(p.semantic_text)
    r=try_family_engine(p.solver_text,a,a['target_spec'])
    assert r.supported and r.ok, (idx,r)
    assert r.answer==expected, (idx,r.answer,expected,r)
print('test_family_engine_pdf_reference_v280: PASS')
