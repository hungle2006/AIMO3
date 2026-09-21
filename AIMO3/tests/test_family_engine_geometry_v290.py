from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from core.family_engines import solve_radical_axis_angle_bisector_triangle
from core.target_spec import extract_target_spec

P='''Let ABC be an acute-angled triangle with integer side lengths and AB < AC. Points D and E lie on segments BC and AC, respectively, such that AD = AE = AB. Line DE intersects AB at X. Circles BXD and CED intersect for the second time at Y ≠ D. Suppose that Y lies on line AD. There is a unique such triangle with minimal perimeter. This triangle has side lengths a = BC, b = CA, and c = AB. Find the remainder when abc is divided by 10^{5}.'''
r=solve_radical_axis_angle_bisector_triangle(P,extract_target_spec(P))
assert r.supported and r.ok, r
assert r.engine=='radical_axis_angle_bisector_triangle', r.engine
assert r.raw_value==336 and r.answer==336, (r.raw_value,r.answer)
c=r.certificate
assert c['sides']=={'a_BC':7,'b_CA':8,'c_AB':6}, c['sides']
assert c['triangle_acute'] and c['AB_lt_AC']
assert c['cleared_relation']['equal']
assert c['angle_bisector']['AD_equals_AB']
assert c['coordinate_crosscheck']['A_on_radical_axis']
assert c['coprime_parameterization']['valid']
assert c['search']['minimal_perimeter']==21
assert c['search']['minimal_hits']==[[7,8,6]]
print('test_family_engine_geometry_v290: PASS')
