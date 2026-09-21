from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.parsing import parse_thinking_solver_output

ok = r'''internal analysis and rejected guesses</think>
[SOLUTION]
A concise solution.
[CHECK]
Checked.
[TOOL_REQUESTS]
[]
[CONFIDENCE]
0.91
[FINAL]
FINAL_ANSWER: 731'''
r = parse_thinking_solver_output(ok, truncated=False)
assert r["candidate_answer"] == 731, r
assert r["thinking_closed"] is True, r

bad = r'''thinking... maybe FINAL_ANSWER: 999 but still reasoning'''
r2 = parse_thinking_solver_output(bad, truncated=True)
assert r2["candidate_answer"] is None, r2
assert r2["thinking_closed"] is False, r2
print("test_thinking_solver_parser_v27: PASS")
