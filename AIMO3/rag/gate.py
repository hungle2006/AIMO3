from __future__ import annotations
from dataclasses import dataclass


@dataclass
class GateDecision:
    status: str
    confidence: float
    reason: str
    selected: list[dict]


class RetrievalGate:
    def __init__(
        self,
        accept_top1: float = 0.30,
        weak_top1: float = 0.18,
        min_margin: float = 0.02,
        conflict_similarity: float = 0.22,
        max_contexts: int = 3,
        dominance_margin: float = 0.10,
        relative_score_floor: float = 0.72,
    ):
        self.accept_top1 = accept_top1
        self.weak_top1 = weak_top1
        self.min_margin = min_margin
        self.conflict_similarity = conflict_similarity
        self.max_contexts = max_contexts
        self.dominance_margin = dominance_margin
        self.relative_score_floor = relative_score_floor

    def _select_accept_contexts(self, hits: list[dict]) -> list[dict]:
        """Prefer a single dominant hit; otherwise keep only near-top contexts.

        This prevents a highly relevant theorem/strategy from being diluted by
        unrelated lower-ranked items merely because they share a broad domain.
        """
        if not hits:
            return []
        top1 = float(hits[0].get("score", 0.0))
        top2 = float(hits[1].get("score", 0.0)) if len(hits) > 1 else 0.0
        if len(hits) == 1 or (top1 - top2) >= self.dominance_margin:
            return hits[:1]
        cutoff = top1 * self.relative_score_floor
        selected = [h for h in hits if float(h.get("score", 0.0)) >= cutoff]
        return selected[: self.max_contexts]

    def evaluate(self, hits: list[dict]) -> GateDecision:
        if not hits:
            return GateDecision("NO_CONTEXT", 0.0, "retriever returned no candidates", [])

        s1 = float(hits[0]["score"])
        s2 = float(hits[1]["score"]) if len(hits) > 1 else 0.0
        margin = s1 - s2

        top_text = " ".join(h.get("text", "").lower() for h in hits[:4])
        contradiction_terms = [
            ("use lte", "lte does not apply"),
            ("convex", "concave"),
            ("cyclic quadrilateral", "noncyclic"),
        ]
        has_conflict = any(a in top_text and b in top_text for a, b in contradiction_terms)

        if has_conflict and s1 >= self.conflict_similarity:
            return GateDecision(
                "CONFLICT",
                min(0.95, s1),
                "retrieved candidates contain potentially conflicting applicability cues",
                hits[: self.max_contexts],
            )

        if s1 >= self.accept_top1:
            conf = min(0.99, 0.65 + 0.7 * s1 + 0.15 * max(margin, 0))
            selected = self._select_accept_contexts(hits)
            reason = "top retrieval score is high"
            if len(selected) == 1 and len(hits) > 1 and margin >= self.dominance_margin:
                reason += "; top hit dominates, lower contexts suppressed"
            return GateDecision("ACCEPT", conf, reason, selected)

        if s1 >= self.weak_top1:
            conf = min(0.75, 0.35 + s1 + 0.10 * max(margin, 0))
            return GateDecision(
                "WEAK",
                conf,
                "some related knowledge found; use only as hints",
                hits[: min(2, self.max_contexts)],
            )

        return GateDecision("NO_CONTEXT", max(0.0, s1), "no sufficiently relevant context found", [])
