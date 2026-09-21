from pathlib import Path
import sys
from types import SimpleNamespace
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.config import load_config
from core.pipeline import FullOlympiadPipeline

PROBLEM = 'A 500 by 500 square is divided into rectangles with integer side lengths and distinct perimeters. The largest possible number is K. What is the remainder when K is divided by 10^{5}?'

BAD = '''[KEY_REDUCTION]\nNeed maximize the number of pieces.\n[COMMIT]\nCANDIDATE_ANSWER: 100000\n[OBLIGATIONS]\n{"upper_bound":"DONE","construction":"DONE","arithmetic_check":"DONE"}\n[SOLUTION]\nincomplete\n'''
UNKNOWN = '''[KEY_REDUCTION]\nThe modulus is not the answer; more work is needed.\n[COMMIT]\nCANDIDATE_ANSWER: UNKNOWN\n[CONFIDENCE]\n0.2'''
DEEP = '''compact reasoning</think>\nCANDIDATE_ANSWER: 520\nCONFIDENCE: 0.91\nKEY_REASON: upper and lower extremal certificates should meet at this value'''

def obl(name):
    if name == 'upper_bound':
        ev = 'A rigorous ordered-semiperimeter area lower bound shows that any 521 pieces would require area strictly greater than the board, so at most 520 rectangles are possible.'
    elif name == 'construction':
        ev = 'Construct 520 integer-sided rectangles by an explicit strip partition; the pieces are disjoint, cover the whole board, and their semiperimeters are pairwise distinct. The dimensions are checked row by row.'
    else:
        ev = 'The established extremal value is 520 and 520 mod 100000 = 520, so the requested remainder is exactly 520.'
    return f'''OBLIGATION: {name}\nSTATUS: PROVED\nEVIDENCE: {ev}\nCANDIDATE_VALID: YES\nCORRECTED_CANDIDATE: UNKNOWN'''

FINAL_CRIT = '''brief review</think>\nVERDICT: PASS\nCONFIDENCE: 0.96\nBEST_CANDIDATE: ASM1\nERROR: NONE\nREVISION: NONE'''

class FakeManager:
    def generate(self, role, prompt, system_prompt=None, overrides=None):
        if role == 'solver':
            if 'previous olympiad attempt ended' in prompt:
                text, trunc, out = UNKNOWN, False, 80
            elif 'Prove exactly ONE missing obligation' in prompt:
                import re
                m = re.search(r'Target obligation: ([A-Za-z0-9_\-]+)', prompt)
                text, trunc, out = obl(m.group(1)), False, 150
            else:
                text, trunc, out = BAD, True, 120
            gpu = 0; raw = text
        elif role == 'critic':
            if 'deep-reasoning model' in prompt:
                text, raw, trunc, out = DEEP, DEEP, False, 160
            else:
                text, raw, trunc, out = FINAL_CRIT, FINAL_CRIT, False, 100
            gpu = 1
        else:
            raise AssertionError(role)
        return SimpleNamespace(
            text=text, raw_text=raw, input_tokens=220, output_tokens=out,
            max_new_tokens=900, latency_sec=.01, gpu=gpu, peak_allocated_gb=1.0,
            free_before_gb=10.0, free_after_gb=10.0, do_sample=True,
            ended_with_eos=not trunc, truncated=trunc,
            finish_reason='length' if trunc else 'eos_or_stop', timed_out=False,
        )

cfg = load_config(ROOT/'config_v2_7_2.yaml')
cfg['rag']['enabled'] = False
cfg['controller']['easy_threshold'] = 0.0
cfg['controller']['hard_threshold'] = 1.0
pipe = FullOlympiadPipeline(cfg, FakeManager())
r = pipe.run(PROBLEM, 'mock_target_gate')

assert r['target_spec']['modulus'] == 100000, r['target_spec']
assert 100000 in r['metrics']['rejected_candidate_values'], r['metrics']
assert r['candidate_answer'] == 520, r
assert r['verified_answer'] == 520, r
assert r['status'] == 'VERIFIED_PASS', r
assert all(c.get('candidate_answer') != 100000 or c.get('target_valid') is False for c in r['candidates'])
print('test_invalid_modulus_commit_v272: PASS')
