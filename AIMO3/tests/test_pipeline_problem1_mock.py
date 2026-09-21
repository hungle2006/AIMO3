from pathlib import Path
import sys
from types import SimpleNamespace
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.config import load_config
from core.pipeline import FullOlympiadPipeline

PROBLEM = '''Alice and Bob are each holding some integer number of sweets. Alice says to Bob: “If
we each added the number of sweets we’re holding to our (positive integer) age, my answer would
be double yours. If we took the product, then my answer would be four times yours.” Bob replies:
“Why don’t you give me five of your sweets because then both our sum and product would be equal.”
What is the product of Alice and Bob’s ages?'''

SOLVER = r'''
[INTERPRETATION]
AMBIGUITY: NONE
Let a,b be Alice/Bob sweets before transfer and A,B their ages. The clauses give
 a+A=2(b+B), aA=4bB. After Alice gives 5 sweets to Bob, the two persons' sums are equal
and the two persons' products are equal, so (a-5)+A=(b+5)+B and (a-5)A=(b+5)B.

[SOLUTION]
Solving these integer constraints gives a=10,A=10,b=5,B=5, hence AB=50.

[CHECK]
All four original constraints hold after substitution.

[TOOL_REQUESTS]
[{"op":"check_equalities","assignments":{"a":10,"A":10,"b":5,"B":5},"equalities":[{"lhs":"a+A","rhs":"2*(b+B)"},{"lhs":"a*A","rhs":"4*b*B"},{"lhs":"(a-5)+A","rhs":"(b+5)+B"},{"lhs":"(a-5)*A","rhs":"(b+5)*B"}],"answer_expr":"A*B","expected_answer":50}]

[CONFIDENCE]
0.95

[FINAL]
FINAL_ANSWER: 50
'''

CRITIC = r'''The constraints and answer-bound exact certificate are consistent.</think>
VERDICT: PASS
CONFIDENCE: 0.97
BEST_CANDIDATE: A
ERROR: NONE
REVISION: NONE'''

class FakeManager:
    def __init__(self):
        self.n = 0

    def generate(self, role, prompt, system_prompt=None, overrides=None):
        self.n += 1
        if role == 'solver':
            text = SOLVER
            raw = SOLVER
            gpu = 0
            out = 450
        elif role == 'critic':
            text = CRITIC
            raw = CRITIC
            gpu = 1
            out = 180
        else:
            raise AssertionError(role)
        return SimpleNamespace(
            text=text, raw_text=raw, input_tokens=500, output_tokens=out,
            max_new_tokens=1800 if role == 'solver' else 3072,
            latency_sec=0.01, gpu=gpu, peak_allocated_gb=1.0,
            free_before_gb=10.0, free_after_gb=10.0,
            do_sample=False, ended_with_eos=True, truncated=False,
            finish_reason='eos_or_stop', timed_out=False,
        )

cfg = load_config(ROOT/'config_v2_6.yaml')
pipe = FullOlympiadPipeline(cfg, FakeManager())
r = pipe.run(PROBLEM, problem_id='pdf_problem_01')
assert r['candidate_answer'] == 50, r
assert r['verified_answer'] == 50, r
assert r['status'] == 'VERIFIED_PASS', r
assert r['verification']['level'] == 'CRITIC', r
assert r['metrics']['model_calls'] == 2, r['metrics']
# Exact tool evidence exists, but default audit policy requires semantic critic confirmation.
assert r['candidates'][0]['verification']['level'] == 'EXACT_TOOL'
assert r['candidates'][0]['verification']['passed'] is True
print('test_pipeline_problem1_mock: PASS')
