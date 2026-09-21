from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from rag.system import OlympiadRAG

cfg = {"rag":{"top_k":8,"accept_top1":0.30,"weak_top1":0.18,"min_margin":0.02,"max_contexts":3}}
r = OlympiadRAG(ROOT, cfg)
q1 = r.query("functional equation transformed into completely additive arithmetic function g(ab)=g(a)+g(b) prime weights")
assert any(h.get("chunk_id") == "nt_completely_additive_arithmetic" for h in q1["hits"][:4]), q1["hits"]
q2 = r.query("tiling rectangles distinct perimeter largest possible extremal construction")
assert any(h.get("chunk_id") == "sp_extremal_tiling_bound_construction" for h in q2["hits"][:4]), q2["hits"]
print("test_rag_refinement_v27: PASS")
