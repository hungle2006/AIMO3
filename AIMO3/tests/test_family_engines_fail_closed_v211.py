from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from core.family_engines import (
    solve_floor_sum_valuation, solve_adaptive_digit_sum_dynamics,
    solve_finite_correlation_polynomial, solve_norwegian_divisor_asymptotic,
)
assert not solve_floor_sum_valuation('Define a function f(n)=n^2; largest non-negative integer k such that 2^k divides N.').ok
assert not solve_adaptive_digit_sum_dynamics('A blackboard process chooses a base, but no digit-sum representation or extremal move question is given.').ok
assert not solve_finite_correlation_polynomial('A function is called shifty and there is a shift operator, but star is undefined.').ok
r=solve_norwegian_divisor_asymptotic('''Let n ≥6. A positive integer is n-Norwegian if three divisors sum to n. Let f(n) be the smallest n-Norwegian. Let M=5^{2025!}. Define g(c) and write a rational sum p/q where p and q are coprime positive integers.''')
assert not r.ok
print('test_family_engines_fail_closed_v211: PASS')
