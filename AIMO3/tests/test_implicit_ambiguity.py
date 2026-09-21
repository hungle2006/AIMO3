from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.parsing import parse_solver_output

text = """[INTERPRETATION]
Wait — no. Re-read the clause. Perhaps this means something else. Key ambiguity remains.

[SOLUTION]
unfinished

[CHECK]

[TOOL_REQUESTS]
[]

[CONFIDENCE]
0.2
"""
r = parse_solver_output(text, truncated=True)
assert r["ambiguity_detected"] is True, r
print("test_implicit_ambiguity: PASS")
