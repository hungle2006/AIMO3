from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.parsing import parse_solver_output, parse_critic_output

solver = r'''
[INTERPRETATION]
AMBIGUITY: NONE
Let x be an integer.

[SOLUTION]
We get x=50.

[CHECK]
Substitution works.

[TOOL_REQUESTS]
[]

[CONFIDENCE]
0.91

[FINAL]
FINAL_ANSWER: 50
'''
p = parse_solver_output(solver, truncated=False)
assert p['candidate_answer'] == 50
assert p['protocol_complete'] is True
assert p['answer_parse_mode'] == 'FINAL_SENTINEL'

trunc = solver.replace('FINAL_ANSWER: 50', '')
p2 = parse_solver_output(trunc, truncated=True)
assert p2['protocol_complete'] is False

critic_raw = '<think>long private reasoning</think>\nVERDICT: PASS\nCONFIDENCE: 0.93\nBEST_CANDIDATE: A\nERROR: NONE\nREVISION: NONE'
c = parse_critic_output(critic_raw, truncated=False)
assert c['verdict'] == 'PASS'
assert abs(c['confidence'] - 0.93) < 1e-9
assert c['best_candidate_id'] == 'A'
assert c['parse_ok'] is True

critic_close_only = 'internal reasoning without opening tag</think>\nVERDICT: REVISE\nCONFIDENCE: 0.88\nBEST_CANDIDATE: A\nERROR: gap\nREVISION: fix gap'
c2 = parse_critic_output(critic_close_only, truncated=False)
assert c2['verdict'] == 'REVISE'
assert c2['thinking_closed'] is True

critic_trunc = 'unfinished reasoning forever'
c3 = parse_critic_output(critic_trunc, truncated=True)
assert c3['thinking_status'] == 'TRUNCATED_THINKING'
assert c3['parse_ok'] is False

# Regression: unfinished thinking that mentions PASS must never be parsed as a final PASS.
critic_fake_pass = 'I might output VERDICT: PASS\nCONFIDENCE: 0.99 later, but I am still reasoning'
c4 = parse_critic_output(critic_fake_pass, truncated=True)
assert c4['parse_ok'] is False, c4
assert c4['verdict'] == 'REVISE', c4
assert c4['thinking_status'] == 'TRUNCATED_THINKING', c4

# Even a non-truncated output without the required closing </think> is not trusted.
critic_missing_close = 'VERDICT: PASS\nCONFIDENCE: 0.99\nBEST_CANDIDATE: A'
c5 = parse_critic_output(critic_missing_close, truncated=False)
assert c5['parse_ok'] is False, c5
assert c5['thinking_status'] == 'MISSING_THINK_CLOSE', c5

print('test_parsing: PASS')
