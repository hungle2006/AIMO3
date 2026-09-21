from pathlib import Path
import sys, json
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.config import load_config, resolve_model_root
from rag.system import OlympiadRAG
from core.input_adapter import AIMOInputAdapter

cfg = load_config(ROOT / "config_v2_7_0.yaml")
print("="*72); print("AIMO3 v2.7.0 FIDELITY + ADAPTIVE PRE-FLIGHT"); print("="*72)
try:
    import torch
    print("CUDA devices:", torch.cuda.device_count())
    for i in range(torch.cuda.device_count()): print(i, torch.cuda.get_device_name(i))
except Exception as e:
    print("torch check failed:", e)
root = resolve_model_root(cfg)
for role,key in [("proposer","proposer_dir"),("solver","solver_dir"),("critic","critic_dir")]:
    p = root / cfg["paths"][key]
    print(role, "OK" if p.exists() else "MISSING", p)
r = OlympiadRAG(ROOT, cfg)
print("RAG:", json.dumps(r.health(), indent=2))
print("preload_roles:", cfg.get("runtime",{}).get("preload_roles"))
print("default_config: config_v2_7_0.yaml")
print("STATUS: READY")
