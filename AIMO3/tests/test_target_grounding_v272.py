from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.target_spec import extract_target_spec, validate_candidate_for_target

p = 'The largest possible value is K. What is the remainder when K is divided by 10^{5}?'
s = extract_target_spec(p)
assert s['kind'] == 'remainder', s
assert s['modulus'] == 100000, s
assert validate_candidate_for_target(100000, s)['valid'] is False
assert validate_candidate_for_target(520, s)['valid'] is True

s2 = extract_target_spec('The maximum number is M. Find M modulo 1000.')
assert s2['kind'] == 'remainder' and s2['modulus'] == 1000, s2
assert validate_candidate_for_target(1000, s2)['valid'] is False
assert validate_candidate_for_target(37, s2)['valid'] is True
print('test_target_grounding_v272: PASS')
