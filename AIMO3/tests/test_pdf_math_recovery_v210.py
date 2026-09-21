from pathlib import Path
import os, sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from core.pdf_reader import AIMOReferencePDFReader
from core.target_spec import extract_target_spec

pdf=os.environ.get('AIMO_REFERENCE_PDF','/mnt/data/AIMO3_Reference_Problems.pdf')
if not Path(pdf).exists():
    print('test_pdf_math_recovery_v210: SKIP (set AIMO_REFERENCE_PDF)')
    raise SystemExit(0)
rs=AIMOReferencePDFReader(pdf,benchmark_mode=True).read()
by={r.problem_number:r for r in rs}

p6=by[6].semantic_text
assert 'sum_{i=1}^{n} sum_{j=1}^{n}' in p6, p6
assert 'floor((1)/(j) + (n-i)/(n))' in p6, p6
assert 'f(M^{15}) - f(M^{15}-1)' in p6, p6
assert '5^{7}' in p6, p6
sp6=extract_target_spec(p6)
assert sp6['kind']=='remainder' and sp6['modulus']==78125 and sp6['quantity_text']=='2^{k}', sp6

p7=by[7].semantic_text
assert '(CT·NB)/(BT·NE)' in p7, p7
assert 'sqrt(q)' in p7, p7
assert 'floor(p^{q^{p}})' in p7, p7
sp7=extract_target_spec(p7)
assert sp7['kind']=='remainder' and sp7['modulus']==99991, sp7
assert sp7['quantity_text']=='floor(p^{q^{p}})', sp7

p8=by[8].semantic_text
assert 'm = sum_{k=0}^{∞} a_{k} · b^{k}' in p8, p8
assert 'replaces it with sum_{k=0}^{∞} a_{k}' in p8, p8

p9=by[9].semantic_text
assert 'sum_{n∈Z} α(n)·β(n)' in p9, p9

p10=by[10].semantic_text
assert 'M = 3^{2025!}' in p10, p10
assert 'g(c) = (1)/(2025!) * floor((2025! * f(M + c))/(M))' in p10, p10
assert '= (p)/(q)' in p10, p10
sp10=extract_target_spec(p10)
assert sp10['kind']=='remainder' and sp10['modulus']==99991, sp10
print('test_pdf_math_recovery_v210: PASS')
