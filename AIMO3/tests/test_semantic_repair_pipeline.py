from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.config import load_config
from core.pipeline import FullOlympiadPipeline

PROBLEM = """Alice and Bob are each holding some integer number of sweets. Alice says to Bob:
“If we each added the number of sweets we're holding to our positive integer age, my answer
would be double yours. If we took the product, then my answer would be four times yours.”
Bob replies: “Why don't you give me five of your sweets because then both our sum and product
would be equal.” What is the product of Alice and Bob's ages?"""

WRONG = r'''{
  "entities":["Alice","Bob"],
  "variables":[
    {"name":"a","owner":"Alice","kind":"sweets","domain":"integer"},
    {"name":"b","owner":"Bob","kind":"sweets","domain":"integer"},
    {"name":"x","owner":"Alice","kind":"age","domain":"positive integer"},
    {"name":"y","owner":"Bob","kind":"age","domain":"positive integer"}
  ],
  "pre_relations":[
    {"type":"sum_ratio","left":"Alice","right":"Bob","factor":2,"operands":["age","sweets"]},
    {"type":"product_ratio","left":"Alice","right":"Bob","factor":4,"operands":["age","sweets"]}
  ],
  "events":[{"type":"transfer","asset":"sweets","amount":5,"from":"Bob","to":"Alice"}],
  "post_equalities":[
    {"type":"sum_equal","left":"Alice","right":"Bob","operands":["age","sweets"]},
    {"type":"product_equal","left":"Alice","right":"Bob","operands":["age","sweets"]}
  ],
  "goal":{"type":"product","terms":["Alice.age","Bob.age"]},
  "ambiguity":"NONE"
}'''

GOOD = WRONG.replace('"from":"Bob","to":"Alice"', '"from":"Alice","to":"Bob"')

class FakeManager:
    def __init__(self):
        self.n = 0
    def generate(self, role, prompt, system_prompt=None, overrides=None):
        assert role == 'solver'
        self.n += 1
        text = WRONG if self.n == 1 else GOOD
        return SimpleNamespace(
            text=text, raw_text=text,
            input_tokens=300, output_tokens=220, max_new_tokens=520,
            latency_sec=0.01, gpu=0, peak_allocated_gb=1.0,
            free_before_gb=10.0, free_after_gb=10.0,
            do_sample=False, ended_with_eos=True, truncated=False,
            finish_reason='eos_or_stop', timed_out=False,
        )

cfg = load_config(ROOT/'config_v2_6_4.yaml')
r = FullOlympiadPipeline(cfg, FakeManager()).run(PROBLEM, 'pdf_problem_01')
assert r['status'] == 'VERIFIED_PASS', r
assert r['verified_answer'] == 50, r
assert r['metrics']['semantic_repairs'] == 1, r['metrics']
assert r['metrics']['model_calls'] == 2, r['metrics']
assert r['metrics']['semantic_certificate_ok'] is True, r['metrics']
print('test_semantic_repair_pipeline: PASS')
