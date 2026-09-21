from pathlib import Path
import sys
from types import SimpleNamespace
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.config import load_config
from core.pipeline import FullOlympiadPipeline

PROBLEM = '''A 30 by 30 board is tiled by rectangles with integer side lengths and distinct perimeters. The maximum number is M. Find M modulo 1000.'''

INITIAL = '''[COMMIT]
CANDIDATE_ANSWER: 37
[KEY_REDUCTION]
Use distinct semiperimeters and an area lower bound.
[OBLIGATIONS]
{"upper_bound":"DONE","construction":"MISSING","arithmetic_check":"DONE"}
[SOLUTION]
Upper bound: ordering the distinct semiperimeters gives an area lower bound, so at most 37 pieces are possible.
[CHECK]
The requested remainder is 37 modulo 1000. The construction still needs to be shown.
'''

OBL = '''OBLIGATION: construction
STATUS: PROVED
EVIDENCE: Construct 37 strips/blocks with the required integer dimensions; the cuts are disjoint, cover the board, and their semiperimeters are pairwise distinct. This is focused mock evidence for the routing test.
CANDIDATE_VALID: YES
CORRECTED_CANDIDATE: UNKNOWN'''

CRIT = '''brief critic reasoning</think>
VERDICT: PASS
CONFIDENCE: 0.96
BEST_CANDIDATE: ASM1
ERROR: NONE
REVISION: NONE'''

class FakeManager:
    def __init__(self):
        self.solver_calls = 0
        self.critic_calls = 0
    def generate(self, role, prompt, system_prompt=None, overrides=None):
        if role == 'solver':
            self.solver_calls += 1
            if 'Prove exactly ONE missing obligation' in prompt:
                text = OBL; trunc=False; out=180
            else:
                text = INITIAL; trunc=True; out=260
            raw=text; gpu=0
        elif role == 'critic':
            self.critic_calls += 1
            text=CRIT; raw=CRIT; trunc=False; out=100; gpu=1
        else:
            raise AssertionError(role)
        return SimpleNamespace(
            text=text, raw_text=raw, input_tokens=250, output_tokens=out,
            max_new_tokens=850, latency_sec=0.01, gpu=gpu,
            peak_allocated_gb=1.0, free_before_gb=10.0, free_after_gb=10.0,
            do_sample=False, ended_with_eos=not trunc, truncated=trunc,
            finish_reason='length' if trunc else 'eos_or_stop', timed_out=False,
        )

cfg = load_config(ROOT / 'config_v2_7_1.yaml')
cfg['rag']['enabled'] = False
cfg['controller']['easy_threshold'] = 0.0
cfg['controller']['hard_threshold'] = 1.0
pipe = FullOlympiadPipeline(cfg, FakeManager())
r = pipe.run(PROBLEM, 'mock_partition')
assert r['candidate_answer'] == 37, r
assert r['verified_answer'] == 37, r
assert r['status'] == 'VERIFIED_PASS', r
assert r['metrics']['answer_commit_survived_truncation'] is True, r['metrics']
assert r['metrics']['proof_micro_calls'] == 1, r['metrics']
assert r['proof_completion']['final_missing'] == [], r['proof_completion']
assert any(c.get('id') == 'ASM1' and c.get('protocol_complete') for c in r['candidates']), r
print('test_commit_verify_pipeline_v271: PASS')
