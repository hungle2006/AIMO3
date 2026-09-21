from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from core.family_engines import solve_radical_axis_angle_bisector_triangle
from core.target_spec import extract_target_spec

BASE='''Let ABC be an acute-angled triangle with integer side lengths and AB < AC. Points D and E lie on segments BC and AC, respectively, such that AD = AE = AB. Line DE intersects AB at X. Circles BXD and CED intersect for the second time at Y ≠ D. Suppose that Y lies on line AD. There is a unique such triangle with minimal perimeter. This triangle has side lengths a = BC, b = CA, and c = AB. Find the remainder when abc is divided by 10^{5}.'''
for bad in [
    BASE.replace('Y lies on line AD','Y lies on line AC'),
    BASE.replace('AD = AE = AB','AD = AE = AC'),
    BASE.replace('Circles BXD and CED','Circles BXC and CED'),
    BASE.replace('acute-angled','obtuse-angled'),
]:
    r=solve_radical_axis_angle_bisector_triangle(bad,extract_target_spec(bad))
    assert not r.supported and not r.ok, r
print('test_family_engine_geometry_fail_closed_v290: PASS')
