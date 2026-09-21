from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.config import load_config
from core.pipeline import FullOlympiadPipeline

PROBLEM = """Let f: Z>=1 -> Z>=1 satisfy f(m)+f(n)=f(m+n+mn) for all positive integers m,n. How many values can f(2024) take?"""

TRUNC = """[INTERPRETATION]\nAMBIGUITY: NONE\n[SOLUTION]\nA partial derivation that does not finish."""
DEEP = """private reasoning</think>
[SOLUTION]
A completed structural derivation.
[CHECK]
Checked the transformed multiplicative relation.
[TOOL_REQUESTS]
[]
[CONFIDENCE]
0.93
[FINAL]
FINAL_ANSWER: 731"""
CRIT = """critic reasoning</think>
VERDICT: PASS
CONFIDENCE: 0.95
BEST_CANDIDATE: TD1
ERROR: NONE
REVISION: NONE"""

class FakeManager:
    def __init__(self):
        self.solver_calls = 0
        self.critic_calls = 0

    def generate(self, role, prompt, system_prompt=None, overrides=None):
        if role == "solver":
            self.solver_calls += 1
            text = TRUNC
            raw = text
            out = 300
            trunc = True
            gpu = 0
        elif role == "critic":
            self.critic_calls += 1
            raw = DEEP if self.critic_calls == 1 else CRIT
            text = raw
            out = 500 if self.critic_calls == 1 else 120
            trunc = False
            gpu = 1
        else:
            raise AssertionError(role)
        return SimpleNamespace(
            text=text, raw_text=raw, input_tokens=300, output_tokens=out,
            max_new_tokens=1000, latency_sec=0.01, gpu=gpu,
            peak_allocated_gb=1.0, free_before_gb=10.0, free_after_gb=10.0,
            do_sample=True, ended_with_eos=not trunc, truncated=trunc,
            finish_reason="length" if trunc else "eos_or_stop", timed_out=False,
        )

cfg = load_config(ROOT / "config_v2_7_0.yaml")
cfg["rag"]["enabled"] = False
cfg["controller"]["easy_threshold"] = 0.0  # ensure medium route
cfg["controller"]["hard_threshold"] = 1.0
pipe = FullOlympiadPipeline(cfg, FakeManager())
r = pipe.run(PROBLEM, "mock_fe")
assert any(c.get("id") == "TD1" and c.get("candidate_answer") == 731 for c in r["candidates"]), r
assert r["candidate_answer"] == 731, r
assert r["verified_answer"] == 731, r
assert r["status"] == "VERIFIED_PASS", r
print("test_deep_escalation_v27: PASS")
