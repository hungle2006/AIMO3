from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from core.config import load_config
from core.pipeline import FullOlympiadPipeline

P='''A 500 × 500 square is divided into k rectangles, each having integer side lengths. Given that no two of these rectangles have the same perimeter, the largest possible value of k is K. What is the remainder when K is divided by 10^{5}?'''
class NoModelManager:
    def generate(self,*a,**k):
        raise AssertionError('family exact route must not call an LLM')
cfg=load_config(ROOT/'config_v2_8_0.yaml')
r=FullOlympiadPipeline(cfg,NoModelManager()).run(P,'p2')
assert r['status']=='VERIFIED_PASS',r
assert r['candidate_answer']==520 and r['verified_answer']==520,r
assert r['verification']['level']=='FAMILY_EXACT',r['verification']
assert r['metrics']['model_calls']==0,r['metrics']
assert r['metrics']['deterministic_family_solve'] is True,r['metrics']
print('test_pipeline_family_exact_v280: PASS')
