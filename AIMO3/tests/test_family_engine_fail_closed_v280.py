from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from core.family_engines import solve_extremal_rectangle_partition, solve_shifted_multiplicative_function, solve_binary_weighted_tournament

# Similar words but missing essential structure => must not certify.
a=solve_extremal_rectangle_partition('A 10 x 10 square contains some rectangles with integer sides.', {})
assert not a.supported or not a.ok
b=solve_shifted_multiplicative_function('Find f(10) where f is an arbitrary function.', {})
assert not b.supported
c=solve_binary_weighted_tournament('A tournament has 20 rounds and runners with same score.', {})
assert not c.ok
print('test_family_engine_fail_closed_v280: PASS')
