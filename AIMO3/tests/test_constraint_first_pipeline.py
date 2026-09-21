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

FORMAL = r'''{
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
  "events":[{"type":"transfer","asset":"sweets","amount":5,"from":"Alice","to":"Bob"}],
  "post_equalities":[
    {"type":"sum_equal","left":"Alice","right":"Bob","operands":["age","sweets"]},
    {"type":"product_equal","left":"Alice","right":"Bob","operands":["age","sweets"]}
  ],
  "goal":{"type":"product","terms":["Alice.age","Bob.age"]},
  "ambiguity":"NONE"
}'''

class FakeManager:
    def generate(self, role, prompt, system_prompt=None, overrides=None):
        assert role == "solver", role
        text = FORMAL
        return SimpleNamespace(
            text=text, raw_text=text,
            input_tokens=350, output_tokens=220, max_new_tokens=520,
            latency_sec=0.01, gpu=0, peak_allocated_gb=1.0,
            free_before_gb=10.0, free_after_gb=10.0,
            do_sample=False, ended_with_eos=True, truncated=False,
            finish_reason="eos_or_stop", timed_out=False,
        )

cfg = load_config(ROOT / "config_v2_6_4.yaml")
pipe = FullOlympiadPipeline(cfg, FakeManager())
r = pipe.run(PROBLEM, "pdf_problem_01")

assert r["constraint_formalization"]["parse_ok"] is True, r
assert r["semantic_compilation"]["ok"] is True, r
assert r["metrics"]["semantic_certificate_ok"] is True, r["metrics"]
assert r["metrics"]["deterministic_semantic_solve"] is True, r["metrics"]
assert r["candidate_answer"] == 50, r
assert r["verified_answer"] == 50, r
assert r["status"] == "VERIFIED_PASS", r
assert r["verification"]["level"] == "SEMANTIC_EXACT", r["verification"]
assert r["metrics"]["rag_used"] is False, r["metrics"]
assert r["metrics"]["model_calls"] == 1, r["metrics"]
print("test_constraint_first_pipeline: PASS")
