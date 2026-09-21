from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.config import load_config
from core.pipeline import FullOlympiadPipeline

PROBLEM = """Alice and Bob are each holding some integer number of sweets. Alice says to Bob:
“If we each added the number of sweets we're holding to our positive integer age,
my answer would be double yours. If we took the product, then my answer would be four
times yours.” Bob replies: “Why don't you give me five of your sweets because then both
our sum and product would be equal.” What is the product of Alice and Bob's ages?"""

BAD = """
[INTERPRETATION]
AMBIGUITY: NONE
Let variables represent the ages and sweets.

[SOLUTION]
I started solving but did not finish.

[CHECK]
Incomplete.

[TOOL_REQUESTS]
[]

[CONFIDENCE]
0.2
"""

GOOD = r"""
[INTERPRETATION]
AMBIGUITY: NONE
Let a,b be sweets and A,B be ages. The clauses give
a+A=2(b+B), a*A=4*b*B, (a-5)+A=(b+5)+B, and (a-5)*A=(b+5)*B.

[SOLUTION]
Solving gives a=10, A=10, b=5, B=5, hence A*B=50.

[CHECK]
All four constraints hold.

[TOOL_REQUESTS]
[{"op":"check_equalities","assignments":{"a":10,"A":10,"b":5,"B":5},
"equalities":[{"lhs":"a+A","rhs":"2*(b+B)"},{"lhs":"a*A","rhs":"4*b*B"},
{"lhs":"(a-5)+A","rhs":"(b+5)+B"},{"lhs":"(a-5)*A","rhs":"(b+5)*B"}],
"answer_expr":"A*B","expected_answer":50}]

[CONFIDENCE]
0.96

[FINAL]
FINAL_ANSWER: 50
"""

CRITIC = """Reasoning complete.</think>
VERDICT: PASS
CONFIDENCE: 0.97
BEST_CANDIDATE: REC1
ERROR: NONE
REVISION: NONE"""

class FakeManager:
    def __init__(self):
        self.solver_calls = 0

    def generate(self, role, prompt, system_prompt=None, overrides=None):
        if role == "solver":
            self.solver_calls += 1
            text = BAD if self.solver_calls == 1 else GOOD
            out = 250 if self.solver_calls == 1 else 500
            gpu = 0
        elif role == "critic":
            text = CRITIC
            out = 150
            gpu = 1
        else:
            raise AssertionError(role)

        return SimpleNamespace(
            text=text, raw_text=text,
            input_tokens=400, output_tokens=out,
            max_new_tokens=1000, latency_sec=0.01, gpu=gpu,
            peak_allocated_gb=1.0, free_before_gb=10.0, free_after_gb=10.0,
            do_sample=True, ended_with_eos=True, truncated=False,
            finish_reason="eos_or_stop", timed_out=False,
        )

cfg = load_config(ROOT / "config_v2_6_2.yaml")
pipe = FullOlympiadPipeline(cfg, FakeManager())
r = pipe.run(PROBLEM, "pdf_problem_01")

assert r["candidate_answer"] == 50, r
assert r["verified_answer"] == 50, r
assert r["status"] == "VERIFIED_PASS", r
assert r["metrics"]["answer_recovery_used"] is True, r["metrics"]
assert r["metrics"]["candidate_answers"] == [None, 50], r["metrics"]
print("test_recovery_pipeline: PASS")
