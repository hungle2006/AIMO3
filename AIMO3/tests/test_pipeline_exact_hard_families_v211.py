from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from core.config import load_config
from core.pipeline import FullOlympiadPipeline
class NoModel:
    def generate(self,*a,**k): raise AssertionError('LLM must not be called for exact hard-family route')
CASES=[
('''Define a function f: Z_{≥1} → Z_{≥1} by f(n) = sum_{i=1}^{n} sum_{j=1}^{n} j^{1024} floor((1)/(j) + (n-i)/(n)). Let M = 2 · 3 · 5 · 7 · 11 · 13 and let N = f(M^{15}) - f(M^{15}-1). Let k be the largest non-negative integer such that 2^{k} divides N. What is the remainder when 2^{k} is divided by 5^{7}?''',32951,'floor_sum_valuation'),
('''On a blackboard, Ken starts off by writing a positive integer n and then applies the following move until he first reaches 1. Given m he chooses a base b, 2≤b≤m, with unique base-b representation m = sum_{k=0}^{∞} a_{k} · b^{k}, and replaces m with sum_{k=0}^{∞} a_{k}. Across all choices of 1 ≤ n ≤ 10^{10^{5}}, the largest possible number of moves is M. What is the remainder when M is divided by 10^{5}?''',32193,'adaptive_digit_sum_dynamics'),
('''Let F be the set of functions α: Z→Z with finite support. For α,β∈F define α ⋆ β = sum_{t∈Z} α(t)·β(t). Define S_{n}(α)(t)=α(t+n). A function α is called shifty if α(m)=0 for m<0 and m>8 and there exist β∈F and k≠l such that S_{n}(α) ⋆ β = {1 if n∈{k,l}; 0 if n∉{k,l}} for every n∈Z. How many shifty functions are there in F?''',160,'finite_correlation_polynomial'),
('''Let n ≥6 be a positive integer. We call a positive integer n-Norwegian if it has three distinct positive divisors whose sum is n. Let f(n) be the smallest n-Norwegian positive integer. Let M = 3^{2025!} and g(c) = (1)/(2025!) * floor((2025! * f(M + c))/(M)). We can write g(0)+g(4M)+g(1848374)+g(10162574)+g(265710644)+g(44636594)=(p)/(q) where p and q are coprime positive integers. What is the remainder when p+q is divided by 99991?''',8687,'norwegian_divisor_asymptotic'),
]
cfg=load_config(ROOT/'config_v2_11_0.yaml')
for i,(p,ans,engine) in enumerate(CASES,1):
    r=FullOlympiadPipeline(cfg,NoModel()).run(p,f'v211_{i}')
    assert r['status']=='VERIFIED_PASS',r
    assert r['verified_answer']==ans,r
    assert r['verification']['level']=='FAMILY_EXACT',r['verification']
    assert r['metrics']['model_calls']==0,r['metrics']
    assert r['metrics']['family_engine_name']==engine,r['metrics']
print('test_pipeline_exact_hard_families_v211: PASS')
