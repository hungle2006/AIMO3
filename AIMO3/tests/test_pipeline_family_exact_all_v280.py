from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from core.config import load_config
from core.pipeline import FullOlympiadPipeline

CASES=[
('''Let ABC be an acute-angled triangle with integer side lengths and AB < AC. Points D and E lie on segments BC and AC, respectively, such that AD = AE = AB. Line DE intersects AB at X. Circles BXD and CED intersect for the second time at Y ≠ D. Suppose that Y lies on line AD. There is a unique such triangle with minimal perimeter. This triangle has side lengths a = BC, b = CA, and c = AB. Find the remainder when abc is divided by 10^{5}.''',336),
('''A 500 × 500 square is divided into k rectangles, each having integer side lengths. Given that no two of these rectangles have the same perimeter, the largest possible value of k is K. What is the remainder when K is divided by 10^{5}?''',520),
('''Let f : Z≥1 → Z≥1 be a function such that for all positive integers m and n, f(m) + f(n) = f(m + n + mn). Across all functions f such that f(n) ≤ 1000 for all n ≤ 1000, how many different values can f(2024) take?''',580),
('''A tournament is held with 2^{20} runners each of which has a different running speed. In each race, two runners compete against each other with the faster runner always winning the race. The competition consists of 20 rounds with each runner starting with a score of 0. In each round, the runners are paired in such a way that in each pair, both runners have the same score at the beginning of the round. The winner of each race in the ith round receives 2^{20-i} points and the loser gets no points. At the end of the tournament, we rank the competitors according to their scores. Let N denote the number of possible orderings of the competitors at the end of the tournament. Let k be the largest positive integer such that 10^{k} divides N. What is the remainder when k is divided by 10^{5}?''',21818),
]
class NoModel:
    def generate(self,*a,**k): raise AssertionError('LLM should not be called')
cfg=load_config(ROOT/'config_v2_9_0.yaml')
for i,(p,ans) in enumerate(CASES,1):
    r=FullOlympiadPipeline(cfg,NoModel()).run(p,f'fam{i}')
    assert r['status']=='VERIFIED_PASS',r
    assert r['verified_answer']==ans,r
    assert r['verification']['level']=='FAMILY_EXACT',r['verification']
    assert r['metrics']['model_calls']==0,r['metrics']
print('test_pipeline_family_exact_all_v280: PASS')
