from pathlib import Path
import re, sys
from types import SimpleNamespace
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.config import load_config
from core.pipeline import FullOlympiadPipeline

PROBLEM = 'A 500 by 500 square is tiled by integer-sided rectangles with distinct perimeters. The largest possible number is K. What is the remainder when K is divided by 10^{5}?'
INITIAL = '''[KEY_REDUCTION]\nArea bound suggests a candidate but construction is uncertain.\n[COMMIT]\nCANDIDATE_ANSWER: 707\n[OBLIGATIONS]\n{"upper_bound":"DONE","construction":"MISSING","arithmetic_check":"DONE"}\n[SOLUTION]\nUpper bound: a rough area argument gives at most 707 pieces.\n[CHECK]\n707 mod 100000 = 707. Construction still needs proof.'''
REFUTE = '''OBLIGATION: construction\nSTATUS: REFUTED\nEVIDENCE: No construction attains 707; the candidate used independently minimal rectangles as though they automatically tile the square. This does not establish realizability and the claimed candidate is therefore invalid.\nCANDIDATE_VALID: NO\nCORRECTED_CANDIDATE: 999'''
REPAIR = '''[KEY_REDUCTION]\nUse a sharp area upper bound together with a matching explicit tiling count.\n[COMMIT]\nCANDIDATE_ANSWER: 520\n[CONFIDENCE]\n0.88'''

def proved(name):
    evs = {
        'upper_bound': 'Order the distinct semiperimeters and sum the exact minimum-area lower bounds; 521 rectangles force total area above 250000, hence at most 520 are possible.',
        'construction': 'An explicit 520-piece strip tiling uses integer dimensions, covers the 500 by 500 square exactly, and has pairwise distinct semiperimeters; therefore 520 is attained.',
        'arithmetic_check': 'The proven extremal value is 520, and 520 modulo 100000 equals 520 exactly.'
    }
    return f'OBLIGATION: {name}\nSTATUS: PROVED\nEVIDENCE: {evs[name]}\nCANDIDATE_VALID: YES\nCORRECTED_CANDIDATE: UNKNOWN'
CRIT = 'review</think>\nVERDICT: PASS\nCONFIDENCE: 0.97\nBEST_CANDIDATE: ASM2\nERROR: NONE\nREVISION: NONE'

class FakeManager:
    def generate(self, role, prompt, system_prompt=None, overrides=None):
        if role == 'solver':
            if 'current candidate was REFUTED' in prompt:
                text, trunc, out = REPAIR, False, 100
            elif 'Prove exactly ONE missing obligation' in prompt:
                m = re.search(r'Target obligation: ([A-Za-z0-9_\-]+)', prompt)
                name = m.group(1)
                if name == 'construction' and 'Committed candidate: 707' in prompt:
                    text = REFUTE
                else:
                    text = proved(name)
                trunc, out = False, 150
            else:
                text, trunc, out = INITIAL, True, 180
            raw=text; gpu=0
        elif role == 'critic':
            text=raw=CRIT; trunc=False; out=90; gpu=1
        else: raise AssertionError(role)
        return SimpleNamespace(text=text, raw_text=raw, input_tokens=220, output_tokens=out,
            max_new_tokens=900, latency_sec=.01, gpu=gpu, peak_allocated_gb=1.0,
            free_before_gb=10.0, free_after_gb=10.0, do_sample=False,
            ended_with_eos=not trunc, truncated=trunc,
            finish_reason='length' if trunc else 'eos_or_stop', timed_out=False)

cfg=load_config(ROOT/'config_v2_7_2.yaml')
cfg['rag']['enabled']=False
cfg['controller']['easy_threshold']=0.0
cfg['controller']['hard_threshold']=1.0
pipe=FullOlympiadPipeline(cfg, FakeManager())
r=pipe.run(PROBLEM,'mock_refute_repair')
assert any(x['candidate_answer']==707 for x in r['proof_completion']['refutations']), r['proof_completion']
assert any(x['candidate_answer']==520 for x in r['proof_completion']['repair_candidates']), r['proof_completion']
assert all(c.get('candidate_answer') != 999 for c in r['candidates']), r['candidates']
assert r['candidate_answer']==520, r
assert r['verified_answer']==520, r
assert r['status']=='VERIFIED_PASS', r
print('test_refutation_repair_v272: PASS')
