from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from core.family_engines import solve_adaptive_digit_sum_dynamics
from core.target_spec import extract_target_spec
P='''On a blackboard, Ken starts off by writing a positive integer n and then applies the following move until he first reaches 1. Given that the number on the board is m, he chooses a base b, where 2 ≤ b ≤ m, and considers the unique base-b representation of m,
m = sum_{k=0}^{∞} a_{k} · b^{k}, where 0 ≤ a_k < b. Ken replaces m with sum_{k=0}^{∞} a_{k}. Across all choices of 1 ≤ n ≤ 10^{10^{5}}, the largest possible number of moves Ken could make is M. What is the remainder when M is divided by 10^{5}?'''
r=solve_adaptive_digit_sum_dynamics(P,extract_target_spec(P))
assert r.supported and r.ok,r
assert r.raw_value==332193,r
assert r.answer==32193,r
print('test_family_engine_digit_dynamics_v211: PASS')
