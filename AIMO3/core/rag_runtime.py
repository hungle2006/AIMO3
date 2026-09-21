from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json


@dataclass
class RAGRuntimeStatus:
    mode: str
    root: str
    available: bool
    details: dict


def detect_rag_runtime(cfg: dict, project_root: str | Path) -> RAGRuntimeStatus:
    """
    Modes:
      - v3_hybrid: external large RAG dataset exists
      - seed_sparse: fall back to bundled TF-IDF seed RAG
    """
    project_root = Path(project_root)
    v3 = cfg.get("rag_v3", {})
    v3_root = Path(v3.get("root", ""))

    required = [
        v3_root / "corpus/problem_store.parquet",
        v3_root / "index/problem.faiss",
    ]

    if v3_root.exists() and all(p.exists() for p in required):
        return RAGRuntimeStatus(
            mode="v3_hybrid",
            root=str(v3_root),
            available=True,
            details={
                "problem_store": str(v3_root / "corpus/problem_store.parquet"),
                "theorem_store": str(v3_root / "corpus/theorem_store.parquet"),
                "formal_store": str(v3_root / "corpus/formal_store.parquet"),
                "problem_index": str(v3_root / "index/problem.faiss"),
            },
        )

    return RAGRuntimeStatus(
        mode="seed_sparse",
        root=str(project_root),
        available=True,
        details={
            "warning": "External RAG V3 dataset not attached; using bundled seed TF-IDF RAG.",
            "data": str(project_root / "data"),
            "index": str(project_root / "index"),
        },
    )
