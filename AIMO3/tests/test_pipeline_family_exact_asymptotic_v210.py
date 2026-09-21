from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from core.config import load_config
from core.pipeline import FullOlympiadPipeline

P='''Let ABC be a triangle with circumcircle Omega and incircle omega. Let D,E,F be the incircle contact points. Let K be the spiral-similarity point described by the two circles, K' its reflection in EF, N the foot from D to EF, and T the second point on BC of the circle through B,K tangent to BN. Let F_n be Fibonacci numbers. Call ABC n-tastic if BD=F_{n}, CD=F_{n+1}, and KNK'B is cyclic. Across all n-tastic triangles, let a_{n} be the maximum possible value of (CT·NB)/(BT·NE). Let alpha be the smallest real number such that for all sufficiently large n, a_{2n}<alpha. Given alpha=p+sqrt(q), find the remainder when floor(p^{q^{p}}) is divided by 99991.'''
class NoModel:
    def generate(self,*a,**k): raise AssertionError('model must not be called')
cfg=load_config(ROOT/'config_v2_10_0.yaml')
pipe=FullOlympiadPipeline(cfg,NoModel())
r=pipe.run(P,'p7_exact')
assert r['status']=='VERIFIED_PASS',r
assert r['candidate_answer']==57447 and r['verified_answer']==57447,r
assert r['verification']['level']=='FAMILY_EXACT',r['verification']
assert r['metrics']['model_calls']==0,r['metrics']
assert r['metrics']['family_engine_name']=='incircle_fibonacci_asymptotic'
print('test_pipeline_family_exact_asymptotic_v210: PASS')
