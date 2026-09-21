from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from core.family_engines import solve_binary_weighted_tournament
from core.target_spec import extract_target_spec

P='''A tournament is held with 2^{20} runners each of which has a different running speed. In each race, two runners compete against each other with the faster runner always winning the race. The competition consists of 20 rounds with each runner starting with a score of 0. In each round, the runners are paired in such a way that in each pair, both runners have the same score at the beginning of the round. The winner of each race in the ith round receives 2^{20-i} points and the loser gets no points. At the end of the tournament, we rank the competitors according to their scores. Let N denote the number of possible orderings of the competitors at the end of the tournament. Let k be the largest positive integer such that 10^{k} divides N. What is the remainder when k is divided by 10^{5}?'''
r=solve_binary_weighted_tournament(P, extract_target_spec(P))
assert r.supported and r.ok, r
assert r.raw_value == 121818, r
assert r.answer == 21818, r
assert r.certificate['valuations']=={2:524287,5:121818}, r.certificate
print('test_family_engine_tournament_v280: PASS')
