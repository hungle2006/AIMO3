from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.budget import BudgetManager, BudgetExhausted

b = BudgetManager({'max_calls':2,'max_total_tokens':100,'max_seconds':100})
b.require_call(); b.register(10,10)
b.require_call(); b.register(10,10)
try:
    b.require_call()
    raise AssertionError('expected BudgetExhausted')
except BudgetExhausted:
    pass
print('test_budget: PASS')
