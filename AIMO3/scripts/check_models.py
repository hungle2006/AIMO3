from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.config import load_config, model_paths, prepare_environment

cfg = load_config(ROOT / "config.yaml")
prepare_environment(cfg)
paths = model_paths(cfg)

print("Project root:", ROOT)
print("Resolved model dataset root:", next(iter(paths.values())).parent)

ok = True
for role, p in paths.items():
    print("\n", role.upper(), "->", p)
    if not p.exists():
        print("  ❌ missing directory")
        ok = False
        continue
    required = ["config.json", "tokenizer_config.json"]
    for r in required:
        flag = (p / r).exists()
        print(" ", "✅" if flag else "❌", r)
        ok &= flag
    shards = sorted(p.glob("*.safetensors"))
    print(f"  safetensors files: {len(shards)}")
    if not shards:
        ok = False
    size = sum(f.stat().st_size for f in p.rglob("*") if f.is_file()) / 1024**3
    print(f"  size: {size:.2f} GiB")

try:
    import torch
    print("\nCUDA available:", torch.cuda.is_available())
    print("GPU count:", torch.cuda.device_count())
    for i in range(torch.cuda.device_count()):
        prop = torch.cuda.get_device_properties(i)
        print(f"  GPU{i}: {prop.name}, {prop.total_memory/1024**3:.1f} GiB")
except Exception as e:
    print("Torch check failed:", e)
    ok = False

print("\nSTATUS:", "READY ✅" if ok else "NOT READY ❌")
raise SystemExit(0 if ok else 2)
