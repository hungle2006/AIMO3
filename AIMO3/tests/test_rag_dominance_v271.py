from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from rag.gate import RetrievalGate

g = RetrievalGate(accept_top1=0.2, weak_top1=0.14, max_contexts=3, dominance_margin=0.10, relative_score_floor=0.72)
hits = [
    {'score':0.336, 'text':'extremal tiling', 'title':'good', 'domain':'combinatorics', 'rank':1},
    {'score':0.153, 'text':'cyclic geometry', 'title':'noise1', 'domain':'geometry', 'rank':2},
    {'score':0.111, 'text':'binary process', 'title':'noise2', 'domain':'combinatorics', 'rank':3},
]
d = g.evaluate(hits)
assert d.status == 'ACCEPT', d
assert len(d.selected) == 1, d.selected
assert d.selected[0]['title'] == 'good'
print('test_rag_dominance_v271: PASS')
