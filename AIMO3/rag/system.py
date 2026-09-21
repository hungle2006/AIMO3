from __future__ import annotations
from pathlib import Path

from .analyzer import analyze, aimo_structure_features
from .retriever import HybridRetriever
from .gate import RetrievalGate
from .context import build_context


class OlympiadRAG:
    def __init__(self, root: str | Path, cfg: dict | None = None):
        self.root = Path(root)
        self.cfg = cfg or {}
        rcfg = self.cfg.get("rag", {})
        self.retriever = HybridRetriever(self.root)
        self.gate = RetrievalGate(
            accept_top1=float(rcfg.get("accept_top1", 0.30)),
            weak_top1=float(rcfg.get("weak_top1", 0.18)),
            min_margin=float(rcfg.get("min_margin", 0.02)),
            max_contexts=int(rcfg.get("max_contexts", 3)),
            dominance_margin=float(rcfg.get("dominance_margin", 0.10)),
            relative_score_floor=float(rcfg.get("relative_score_floor", 0.72)),
        )

    def query(self, problem: str, top_k: int | None = None):
        analysis = analyze(problem)
        features = aimo_structure_features(problem)
        query = " ".join(list(dict.fromkeys([analysis.query, *features])))
        hits = self.retriever.search(
            query,
            domain=analysis.domain,
            top_k=int(top_k or self.cfg.get("rag", {}).get("top_k", 8)),
        )
        decision = self.gate.evaluate(hits)
        context = build_context(decision, max_chars=int(self.cfg.get("rag", {}).get("context_char_limit", 4500)))
        return {
            "analysis": {
                "domain": analysis.domain,
                "keywords": analysis.keywords,
                "query": query,
                "structure_features": features,
            },
            "gate": {
                "status": decision.status,
                "confidence": decision.confidence,
                "reason": decision.reason,
            },
            "hits": hits,
            "context": context,
        }

    def health(self) -> dict:
        return self.retriever.health()
