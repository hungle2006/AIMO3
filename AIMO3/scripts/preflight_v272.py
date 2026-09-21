from pathlib import Path
import sys, json
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.config import load_config, resolve_model_root
from core.target_spec import extract_target_spec
from rag.system import OlympiadRAG

cfg = load_config(ROOT / "config_v2_7_2.yaml")
print("="*72)
print("AIMO3 v2.7.2 TARGET-GROUNDED COMMIT/VERIFY PRE-FLIGHT")
print("="*72)
try:
    import torch
    print("CUDA devices:", torch.cuda.device_count())
    for i in range(torch.cuda.device_count()):
        print(i, torch.cuda.get_device_name(i))
except Exception as e:
    print("torch check failed:", e)

root = resolve_model_root(cfg)
for role,key in [("proposer","proposer_dir"),("solver","solver_dir"),("critic","critic_dir")]:
    p = root / cfg["paths"][key]
    print(role, "OK" if p.exists() else "MISSING", p)

r = OlympiadRAG(ROOT, cfg)
print("RAG:", json.dumps(r.health(), indent=2))
print("preload_roles:", cfg.get("runtime",{}).get("preload_roles"))
print("proof_completion:", json.dumps(cfg.get("proof_completion",{}), indent=2))
print("candidate_repair:", json.dumps(cfg.get("candidate_repair",{}), indent=2))
print("target_grounding:", json.dumps(cfg.get("target_grounding",{}), indent=2))

probe = "What is the remainder when K is divided by 10^{5}?"
print("target_spec_probe:", json.dumps(extract_target_spec(probe), indent=2))
print("default_config: config_v2_7_2.yaml")
print("STATUS: READY")
