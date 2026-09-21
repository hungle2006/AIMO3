from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.tools import run_one

req = {
    'op':'check_equalities',
    'assignments': {'a':10,'A':10,'b':5,'B':5},
    'equalities': [
        {'lhs':'a+A','rhs':'2*(b+B)'},
        {'lhs':'a*A','rhs':'4*b*B'},
        {'lhs':'(a-5)+A','rhs':'(b+5)+B'},
        {'lhs':'(a-5)*A','rhs':'(b+5)*B'},
    ],
    'answer_expr':'A*B',
    'expected_answer':50,
}
r = run_one(req)
assert r['ok'] and r['verified'], r

bad = dict(req)
bad['assignments'] = {'a':10,'A':12,'b':5,'B':5}
r2 = run_one(bad)
assert r2['ok'] and not r2['verified'], r2
print('test_tools: PASS')
