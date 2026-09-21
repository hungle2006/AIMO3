from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from core.family_engines import solve_extremal_rectangle_partition
from core.target_spec import extract_target_spec

P='''A 500 × 500 square is divided into k rectangles, each having integer side lengths. Given that no two of these rectangles have the same perimeter, the largest possible value of k is K. What is the remainder when K is divided by 10^{5}?'''
r=solve_extremal_rectangle_partition(P, extract_target_spec(P))
assert r.supported and r.ok, r
assert r.raw_value == 520, r
assert r.answer == 520, r
c=r.certificate
assert c['upper_bound']==520 and c['construction_count']==520, c
assert c['construction_verified']['ok'] is True, c
assert c['construction_verified']['perimeter_count']==520, c
print('test_family_engine_extremal_v280: PASS')
