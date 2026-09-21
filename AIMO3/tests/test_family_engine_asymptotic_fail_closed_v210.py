from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from core.family_engines import solve_incicle_fibonacci_asymptotic
from core.target_spec import extract_target_spec

# Missing the exact target ratio and cyclic condition: must not activate merely
# because the prompt mentions Fibonacci, a circle, and a limit.
P='''A triangle has an incircle. Let F_n be Fibonacci numbers and suppose a_n has a limit. Find the remainder when floor(p^{q^{p}}) is divided by 99991.'''
r=solve_incicle_fibonacci_asymptotic(P,extract_target_spec(P))
assert not r.supported and not r.ok, r
print('test_family_engine_asymptotic_fail_closed_v210: PASS')
