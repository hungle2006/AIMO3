from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from core.pdf_math_recovery import recover_statement_math
BROKEN='''Let F be the set of functions α: Z →Z for which there are only finitely many n ∈Z such that α(n)≠0.
α(n) · β(n). Also, for n ∈Z,
For two functions α and β in F, define their product α ⋆β to be ^{P}
n∈Z
define a shift operator S_{n}: F →F by S_{n}(α)(t) = α(t + n) for all t ∈Z.
A function α ∈F is called shifty if α(m)=0 for all integers m<0 and m>8 and there exists β∈F and integers k≠l such that for all n∈Z S_{n}(α) ⋆β = 1 n∈{k,l} 0 n∉{k,l}. How many shifty functions are there in F?'''
r=recover_statement_math(9,BROKEN,'')
compact=''.join(r.text.split())
assert 'sum_{n∈Z}α(n)·β(n)' in compact,r.text
assert 'S_{n}(α)⋆β={1ifn∈{k,l};0ifn∉{k,l}}' in compact,r.text
assert 'p9_bilateral_sum' in r.rules,r.rules
print('test_pdf_math_recovery_p9_v211: PASS')
