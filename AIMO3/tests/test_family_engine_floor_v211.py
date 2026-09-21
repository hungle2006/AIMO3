from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from core.family_engines import solve_floor_sum_valuation
from core.target_spec import extract_target_spec
P='''Define a function f: Z_{≥1} → Z_{≥1} by
f(n) = sum_{i=1}^{n} sum_{j=1}^{n} j^{1024} floor((1)/(j) + (n-i)/(n)).
Let M = 2 · 3 · 5 · 7 · 11 · 13 and let N = f(M^{15}) - f(M^{15}-1). Let k be the largest non-negative integer such that 2^{k} divides N. What is the remainder when 2^{k} is divided by 5^{7}?'''
r=solve_floor_sum_valuation(P,extract_target_spec(P))
assert r.supported and r.ok,r
assert r.certificate['k']==20,r.certificate
assert r.answer==32951,r
print('test_family_engine_floor_v211: PASS')
