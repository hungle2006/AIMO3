from pathlib import Path
import re, sys
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from core.config import load_config
from core.pipeline import FullOlympiadPipeline

PROBLEM='''Determine the integer X satisfying the stated hard structural conditions. What is X?'''
INITIAL='''[KEY_REDUCTION]\nA speculative reduction.\n[COMMIT]\nCANDIDATE_ANSWER: 111\n[OBLIGATIONS]\n{"main_argument":"MISSING","edge_cases":"MISSING","final_check":"MISSING"}\n[SOLUTION]\nThis is only a guess.'''
REPAIR='''[KEY_REDUCTION]\nA second speculative reduction.\n[COMMIT]\nCANDIDATE_ANSWER: 222\n[CONFIDENCE]\n0.6'''
REFUTE111='''OBLIGATION: main_argument\nSTATUS: REFUTED\nEVIDENCE: The candidate 111 has no decisive structural derivation and contradicts the stated constraints.\nCANDIDATE_VALID: NO\nCORRECTED_CANDIDATE: UNKNOWN'''
REFUTE222='''OBLIGATION: main_argument\nSTATUS: REFUTED\nEVIDENCE: The repaired candidate 222 still has no decisive derivation and is invalid.\nCANDIDATE_VALID: NO\nCORRECTED_CANDIDATE: UNKNOWN'''
DEEP='''private hard reasoning</think>\n[INTERPRETATION]\nUse the decisive invariant.\n[SOLUTION]\nThe solution follows from the exact invariant; therefore X=333. All edge cases are checked and no exceptional case survives.\n[CHECK]\nCheck: substituting 333 satisfies the final condition exactly.\n[TOOL_REQUESTS]\n[]\n[CONFIDENCE]\n0.94\n[FINAL]\nFINAL_ANSWER: 333'''
CRIT='''review</think>\nVERDICT: PASS\nCONFIDENCE: 0.96\nBEST_CANDIDATE: ASM1\nERROR: NONE\nREVISION: NONE'''

class FakeManager:
    def __init__(self): self.deep_calls=0
    def generate(self,role,prompt,system_prompt=None,overrides=None):
        if role=='solver':
            if 'current candidate was REFUTED' in prompt:
                text=REPAIR
            elif 'Prove exactly ONE missing obligation' in prompt:
                if 'Committed candidate: 333' in prompt:
                    m=re.search(r'Target obligation: ([A-Za-z0-9_\-]+)',prompt)
                    name=m.group(1) if m else 'structural_reduction'
                    text=(f'OBLIGATION: {name}\nSTATUS: PROVED\nEVIDENCE: The exact invariant gives X=333; the structural reduction is complete and the arithmetic check is exact. Edge cases are explicitly excluded.\nCANDIDATE_VALID: YES\nCORRECTED_CANDIDATE: UNKNOWN')
                else:
                    text=REFUTE222 if 'Committed candidate: 222' in prompt else REFUTE111
            else:
                text=INITIAL
            raw=text; gpu=0; trunc=False; out=120
        elif role=='critic':
            self.deep_calls += 1
            raw = DEEP if self.deep_calls==1 else CRIT
            text=raw; gpu=1; trunc=False; out=300 if self.deep_calls==1 else 80
        else: raise AssertionError(role)
        return SimpleNamespace(text=text,raw_text=raw,input_tokens=180,output_tokens=out,max_new_tokens=1400,
            latency_sec=.01,gpu=gpu,peak_allocated_gb=1.0,free_before_gb=10.0,free_after_gb=10.0,
            do_sample=True,ended_with_eos=True,truncated=trunc,finish_reason='eos_or_stop',timed_out=False)

cfg=load_config(ROOT/'config_v2_10_0.yaml')
cfg['family_engines']['enabled']=False
cfg['rag']['enabled']=False
cfg['controller']['easy_threshold']=0.0
cfg['controller']['hard_threshold']=0.0
cfg['candidate_repair']['max_rounds']=1
cfg['proof_completion']['max_micro_calls_hard']=1
pipe=FullOlympiadPipeline(cfg,FakeManager())
r=pipe.run(PROBLEM,'hard_retry_mock')
assert len(r['proof_completion']['refutations'])>=2,r['proof_completion']
assert r['metrics']['hard_retry_after_refutation'] is True,r['metrics']
assert any(c.get('id')=='HR1' and c.get('candidate_answer')==333 for c in r['candidates']),r['candidates']
assert r['candidate_answer']==333,r
assert r['verified_answer']==333,r
assert r['status']=='VERIFIED_PASS',r
print('test_hard_retry_after_refutation_v210: PASS')
