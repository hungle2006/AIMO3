from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from core.family_engines import solve_shifted_multiplicative_function

P='''Let f : Z≥1 → Z≥1 be a function such that for all positive integers m and n, f(m) + f(n) = f(m + n + mn). Across all functions f such that f(n) ≤ 1000 for all n ≤ 1000, how many different values can f(2024) take?'''
r=solve_shifted_multiplicative_function(P, {})
assert r.supported and r.ok, r
assert r.answer == 580 and r.raw_value == 580, r
c=r.certificate
assert c['target_factorization']=={3:4,5:2}, c
assert c['feasible_value_count']==580, c
assert c['compressed_constraints'] < 50, c
print('test_family_engine_functional_v280: PASS')
