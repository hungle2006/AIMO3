from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.tools import run_one

# Ordinary arithmetic still works.
r = run_one({'op':'identity','lhs':'(x+1)^2','rhs':'x^2+2*x+1','variables':['x']})
assert r['ok'] and r['verified'], r

# Model-generated expressions must not get Python eval capabilities.
attacks = [
    "__import__('os').system('echo PWNED')",
    "(1).__class__",
    "open('/etc/passwd').read()",
    "[x for x in [1,2,3]]",
]
for expr in attacks:
    out = run_one({'op':'simplify','expr':expr,'variables':['x']})
    assert not out['ok'], (expr, out)

print('test_safe_tools: PASS')
