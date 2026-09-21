from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.config import load_config
from core.pipeline import FullOlympiadPipeline

PROBLEM = """Let f: Z>=1 -> Z>=1 satisfy f(m)+f(n)=f(m+n+mn) for all positive integers m,n. How many values can f(2024) take?"""
TRUNC = """[INTERPRETATION]\nAMBIGUITY: NONE\n[SOLUTION]\nPartial reasoning only."""
# Thinking model never closes </think>, so strict parser must refuse an answer.
DEEP_TRUNC = """working... transform with n+1 and prime weights; continue counting possible values"""
FINISH = """[SOLUTION]\nUse the transformed completely additive function and finish the counting.\n[CHECK]\nBounds checked.\n[TOOL_REQUESTS]\n[]\n[CONFIDENCE]\n0.91\n[FINAL]\nFINAL_ANSWER: 731"""
CRIT = """critic reasoning</think>\nVERDICT: PASS\nCONFIDENCE: 0.95\nBEST_CANDIDATE: TDF1\nERROR: NONE\nREVISION: NONE"""

class FakeManager:
    def __init__(self):
        self.solver_calls = 0
        self.critic_calls = 0

    def generate(self, role, prompt, system_prompt=None, overrides=None):
        if role == "solver":
            self.solver_calls += 1
            # first direct, second continuation, third deep-finish
            text = FINISH if self.solver_calls >= 3 else TRUNC
            raw = text
            trunc = self.solver_calls < 3
            out = 220
            gpu = 0
        elif role == "critic":
            self.critic_calls += 1
            raw = DEEP_TRUNC if self.critic_calls == 1 else CRIT
            text = raw
            trunc = self.critic_calls == 1
            out = 500 if trunc else 100
            gpu = 1
        else:
            raise AssertionError(role)
        return SimpleNamespace(
            text=text, raw_text=raw, input_tokens=250, output_tokens=out,
            max_new_tokens=800, latency_sec=0.01, gpu=gpu,
            peak_allocated_gb=1.0, free_before_gb=10.0, free_after_gb=10.0,
            do_sample=True, ended_with_eos=not trunc, truncated=trunc,
            finish_reason="length" if trunc else "eos_or_stop", timed_out=False,
        )

cfg = load_config(ROOT / "config_v2_7_0.yaml")
cfg["rag"]["enabled"] = False
cfg["controller"]["easy_threshold"] = 0.0
cfg["controller"]["hard_threshold"] = 1.0
pipe = FullOlympiadPipeline(cfg, FakeManager())
r = pipe.run(PROBLEM, "mock_deep_finish")
assert any(c.get("id") == "TD1" and c.get("candidate_answer") is None for c in r["candidates"]), r
assert any(c.get("id") == "TDF1" and c.get("candidate_answer") == 731 for c in r["candidates"]), r
assert r["verified_answer"] == 731, r
assert r["status"] == "VERIFIED_PASS", r
print("test_deep_finish_v27: PASS")
