from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from core.config import load_config
from core.pipeline import FullOlympiadPipeline

P='''Let ABC be an acute-angled triangle with integer side lengths and AB < AC. Points D and E lie on segments BC and AC, respectively, such that AD = AE = AB. Line DE intersects AB at X. Circles BXD and CED intersect for the second time at Y ≠ D. Suppose that Y lies on line AD. There is a unique such triangle with minimal perimeter. This triangle has side lengths a = BC, b = CA, and c = AB. Find the remainder when abc is divided by 10^{5}.'''
class NoModel:
    def generate(self,*a,**k): raise AssertionError('LLM should not be called')
cfg=load_config(ROOT/'config_v2_9_0.yaml')
r=FullOlympiadPipeline(cfg,NoModel()).run(P,'geo_exact')
assert r['status']=='VERIFIED_PASS',r
assert r['verified_answer']==336,r
assert r['verification']['level']=='FAMILY_EXACT',r['verification']
assert r['metrics']['model_calls']==0,r['metrics']
assert r['metrics']['family_engine_name']=='radical_axis_angle_bisector_triangle',r['metrics']
print('test_pipeline_family_exact_geometry_v290: PASS')
