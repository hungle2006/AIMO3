from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.evaluation import benchmark_record

# Runtime may claim verified; benchmark evaluation must expose a false certification.
r = {
    'candidate_answer': 999,
    'verified_answer': 999,
    'metrics': {'verified_pass': True},
}
b = benchmark_record(r, 50)
assert b['verification_false_positive'] is True, b
assert b['verified_correct'] is False
assert b['answer_was_not_exposed_to_model'] is True

# Correct candidate but not runtime-verified is recorded separately.
r2 = {
    'candidate_answer': 50,
    'verified_answer': None,
    'metrics': {'verified_pass': False},
}
b2 = benchmark_record(r2, 50)
assert b2['candidate_correct_but_unverified'] is True, b2

print('test_evaluation: PASS')
