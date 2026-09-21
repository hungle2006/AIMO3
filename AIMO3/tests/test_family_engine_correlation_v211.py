from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from core.family_engines import solve_finite_correlation_polynomial
from core.target_spec import extract_target_spec
P='''Let F be the set of functions α: Z → Z with finite support. For α,β in F define α ⋆ β to be sum_{t∈Z} α(t)·β(t). For n∈Z define S_{n}(α)(t)=α(t+n). A function α is called shifty if α(m)=0 for all integers m<0 and m>8, and there exist β∈F and integers k≠l such that for all n∈Z, S_{n}(α) ⋆ β = {1 if n∈{k,l}; 0 if n∉{k,l}}. How many shifty functions are there in F?'''
r=solve_finite_correlation_polynomial(P,extract_target_spec(P))
assert r.supported and r.ok,r
assert r.raw_value==160,r
assert r.certificate['total_distinct_polynomials']==160,r.certificate
print('test_family_engine_correlation_v211: PASS')
