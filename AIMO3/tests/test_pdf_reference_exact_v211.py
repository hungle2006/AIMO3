from pathlib import Path
import os,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from core.pdf_reader import AIMOReferencePDFReader
from core.pipeline import FullOlympiadPipeline
from core.family_engines import try_family_engine
pdf=os.environ.get('AIMO_REFERENCE_PDF')
if not pdf:
    print('test_pdf_reference_exact_v211: SKIP (AIMO_REFERENCE_PDF not set)')
    raise SystemExit(0)
rs=AIMOReferencePDFReader(pdf,benchmark_mode=True).read()
by={r.problem_number:r for r in rs}
for n in range(2,11):
    r=by[n]
    a=FullOlympiadPipeline._analysis_dict(r.semantic_text)
    out=try_family_engine(r.semantic_text,a,a.get('target_spec'))
    assert out.supported and out.ok,(n,a,out)
    assert out.answer==r.expected_answer,(n,out.answer,r.expected_answer,out)
print('test_pdf_reference_exact_v211: PASS')
