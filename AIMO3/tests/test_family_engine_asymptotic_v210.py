from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from core.family_engines import solve_incicle_fibonacci_asymptotic
from core.target_spec import extract_target_spec
from core.problem_family import classify_problem_family
from core.controller import apply_family_difficulty_floor

P='''Let ABC be a triangle with circumcircle Omega and incircle omega. Let D,E,F be the incircle contact points. Let K be the spiral-similarity point described by the two circles, K' its reflection in EF, N the foot from D to EF, and T the second point on BC of the circle through B,K tangent to BN. Let F_n be Fibonacci numbers. Call ABC n-tastic if BD=F_{n}, CD=F_{n+1}, and KNK'B is cyclic. Across all n-tastic triangles, let a_{n} be the maximum possible value of (CT·NB)/(BT·NE). Let alpha be the smallest real number such that for all sufficiently large n, a_{2n}<alpha. Given alpha=p+sqrt(q), find the remainder when floor(p^{q^{p}}) is divided by 99991.'''
analysis={'domain':'geometry'}
fam=classify_problem_family(P,analysis)
assert fam=='geometry_sequence_asymptotic', fam
assert apply_family_difficulty_floor(.55,{'family':fam})>=.78
r=solve_incicle_fibonacci_asymptotic(P,extract_target_spec(P))
assert r.supported and r.ok, r
assert r.engine=='incircle_fibonacci_asymptotic'
assert r.raw_value==2**25, r.raw_value
assert r.answer==57447, r.answer
c=r.certificate
assert c['fibonacci_substitution']['a_n']=='F_{n+2}/F_{n-1}'
assert c['alpha']=='2 + sqrt(5)'
assert c['p']==2 and c['q']==5
print('test_family_engine_asymptotic_v210: PASS')
