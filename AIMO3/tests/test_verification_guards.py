from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.config import load_config
from core.verification import verify_candidate, critic_verification

cfg = load_config(ROOT / 'config_v2_6.yaml')

# Regression: a random true identity must NOT certify answer 999.
unrelated = {
    'candidate_answer': 999,
    'protocol_complete': True,
    'ambiguity_detected': False,
    'truncated': False,
    'tool_requests': [
        {'op': 'identity', 'lhs': '2+2', 'rhs': '4', 'variables': []}
    ],
}
v = verify_candidate(unrelated, cfg)
assert v.passed is False, v
assert v.level == 'CONSISTENCY', v

# Answer-bound equality certificate is recognized as exact evidence.
bound = {
    'candidate_answer': 50,
    'protocol_complete': True,
    'ambiguity_detected': False,
    'truncated': False,
    'tool_requests': [{
        'op': 'check_equalities',
        'assignments': {'a':10,'A':10,'b':5,'B':5},
        'equalities': [
            {'lhs':'a+A','rhs':'2*(b+B)'},
            {'lhs':'a*A','rhs':'4*b*B'},
            {'lhs':'(a-5)+A','rhs':'(b+5)+B'},
            {'lhs':'(a-5)*A','rhs':'(b+5)*B'},
        ],
        'answer_expr':'A*B',
        'expected_answer':50,
    }],
}
v2 = verify_candidate(bound, cfg)
assert v2.passed is True and v2.level == 'EXACT_TOOL', v2

# Critic is not allowed to override a failed exact check.
failed_candidate = {
    'id': 'A',
    'candidate_answer': 50,
    'protocol_complete': True,
    'ambiguity_detected': False,
    'truncated': False,
    'tool_reports': [{'ok': True, 'op': 'check_equalities', 'verified': False}],
}
critic = {
    'verdict': 'PASS', 'confidence': 0.99, 'parse_ok': True,
    'best_candidate_id': 'A'
}
cv = critic_verification(critic, 0.88, selected_candidate=failed_candidate)
assert cv.passed is False, cv
assert 'failed exact tool' in cv.reason.lower(), cv.reason

# PASS without explicit selected candidate is rejected.
cv2 = critic_verification(critic, 0.88, selected_candidate=None)
assert cv2.passed is False

print('test_verification_guards: PASS')
