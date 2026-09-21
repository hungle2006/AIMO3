from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from rag.system import OlympiadRAG

cfg = {'rag': {'top_k':4,'accept_top1':0.30,'weak_top1':0.18,'min_margin':0.02,'max_contexts':3}}
r = OlympiadRAG(ROOT, cfg)
h = r.health()
assert h['healthy'] and h['documents'] > 0, h
q = r.query('Prove an integer divisibility statement using powers and congruences', top_k=4)
assert 'gate' in q and 'hits' in q
print('test_rag_runtime: PASS', h)
