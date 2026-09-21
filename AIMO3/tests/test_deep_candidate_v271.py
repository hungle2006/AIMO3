from pathlib import Path
import sys
from types import SimpleNamespace
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.config import load_config
from core.pipeline import FullOlympiadPipeline

PROBLEM = 'Let f be a positive-integer function satisfying a multiplicative-additive functional equation. How many target values are possible?'
TRUNC = '[COMMIT]\nCANDIDATE_ANSWER: UNKNOWN\n[KEY_REDUCTION]\npartial only'
DEEP_TRUNC = 'long private reasoning about prime weights and bounds but no closing marker'
FINISH = '[KEY_REDUCTION]\nprime weights determine the value\n[COMMIT]\nCANDIDATE_ANSWER: 731\n[CONFIDENCE]\n0.86'

class FakeManager:
    def __init__(self): self.s=0; self.c=0
    def generate(self, role, prompt, system_prompt=None, overrides=None):
        if role == 'solver':
            self.s += 1
            if 'Extract the most defensible candidate integer' in prompt:
                text=FINISH; trunc=False; out=90
            else:
                text=TRUNC; trunc=True; out=100
            raw=text; gpu=0
        elif role == 'critic':
            self.c += 1
            text=DEEP_TRUNC; raw=text; trunc=True; out=500; gpu=1
        else: raise AssertionError(role)
        return SimpleNamespace(text=text, raw_text=raw, input_tokens=180, output_tokens=out,
            max_new_tokens=800, latency_sec=.01, gpu=gpu, peak_allocated_gb=1.0,
            free_before_gb=10.0, free_after_gb=10.0, do_sample=True,
            ended_with_eos=not trunc, truncated=trunc,
            finish_reason='length' if trunc else 'eos_or_stop', timed_out=False)

cfg=load_config(ROOT/'config_v2_7_1.yaml')
cfg['rag']['enabled']=False
cfg['controller']['easy_threshold']=0.0
cfg['controller']['hard_threshold']=1.0
cfg['proof_completion']['enabled']=False
pipe=FullOlympiadPipeline(cfg, FakeManager())
r=pipe.run(PROBLEM,'mock_deep_candidate')
assert any(c.get('id') == 'TDF1' and c.get('candidate_answer') == 731 for c in r['candidates']), r
assert r['candidate_answer'] == 731, r
assert r['verified_answer'] is None, r
assert r['status'] in {'CANDIDATE_ONLY','BUDGET_EXHAUSTED'}, r
print('test_deep_candidate_v271: PASS')
