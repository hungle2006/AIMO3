from __future__ import annotations
from pathlib import Path
import os
import random
import yaml


def load_config(path: str | Path) -> dict:
    path = Path(path)
    cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
    cfg["_config_path"] = str(path.resolve())
    cfg["_project_root"] = str(path.resolve().parent)
    return cfg


def resolve_model_root(cfg: dict) -> Path:
    candidates = [cfg["paths"]["model_dataset_root"], *cfg["paths"].get("model_root_fallbacks", [])]
    for p in candidates:
        root = Path(p)
        if root.exists():
            return root
    raise FileNotFoundError(
        "Could not find model dataset root. Checked:\n" + "\n".join(f"- {p}" for p in candidates)
    )


def model_paths(cfg: dict) -> dict[str, Path]:
    root = resolve_model_root(cfg)
    return {
        "proposer": root / cfg["paths"]["proposer_dir"],
        "solver": root / cfg["paths"]["solver_dir"],
        "critic": root / cfg["paths"]["critic_dir"],
    }


def prepare_environment(cfg: dict) -> None:
    if cfg.get("runtime", {}).get("offline", True):
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    os.environ["PYTORCH_CUDA_ALLOC_CONF"] = cfg.get("runtime", {}).get(
        "cuda_alloc_conf", "expandable_segments:True"
    )
    seed = int(cfg.get("project", {}).get("seed", 42))
    random.seed(seed)
    try:
        import numpy as np
        np.random.seed(seed)
    except Exception:
        pass
    try:
        import torch
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
    except Exception:
        pass
