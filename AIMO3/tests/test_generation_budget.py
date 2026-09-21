from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.budget import BudgetExhausted, cap_generation_budget

max_new, max_time = cap_generation_budget(
    input_tokens=700,
    configured_max_new=1800,
    remaining_total_tokens=1000,
    remaining_seconds=12.0,
    safety_seconds=1.0,
)
assert max_new == 300, max_new
assert 10.9 <= max_time <= 11.1, max_time

try:
    cap_generation_budget(
        input_tokens=1000,
        configured_max_new=100,
        remaining_total_tokens=900,
        remaining_seconds=12.0,
    )
    raise AssertionError('expected token budget failure')
except BudgetExhausted:
    pass

try:
    cap_generation_budget(
        input_tokens=10,
        configured_max_new=100,
        remaining_total_tokens=1000,
        remaining_seconds=0.5,
        safety_seconds=1.0,
    )
    raise AssertionError('expected time budget failure')
except BudgetExhausted:
    pass

print('test_generation_budget: PASS')
