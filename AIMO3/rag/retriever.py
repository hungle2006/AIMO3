from __future__ import annotations

import json
from pathlib import Path
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer


class HybridRetriever:
    """
    Small seed retriever rebuilt in the CURRENT sklearn runtime.
    This intentionally avoids loading pickled sklearn estimators from another version.
    """

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.docs = []
        path = self.root / "data/knowledge_chunks.jsonl"
        if not path.exists():
            raise FileNotFoundError(path)
        with path.open(encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    self.docs.append(json.loads(line))

        texts = [self._doc_text(d) for d in self.docs]
        self.word_vec = TfidfVectorizer(
            ngram_range=(1, 2), min_df=1, max_df=1.0,
            lowercase=True, sublinear_tf=True, norm="l2",
        )
        self.char_vec = TfidfVectorizer(
            analyzer="char_wb", ngram_range=(3, 5), min_df=1,
            lowercase=True, sublinear_tf=True, norm="l2",
        )
        self.Xw = self.word_vec.fit_transform(texts)
        self.Xc = self.char_vec.fit_transform(texts)

    @staticmethod
    def _doc_text(d: dict) -> str:
        return " ".join(str(d.get(k, "")) for k in [
            "title", "name", "text", "statement", "use_when", "domain", "tags"
        ])

    def search(self, query: str, domain: str = "general", top_k: int = 8):
        if not self.docs:
            return []
        qw = self.word_vec.transform([query])
        qc = self.char_vec.transform([query])
        sw = (self.Xw @ qw.T).toarray().ravel()
        sc = (self.Xc @ qc.T).toarray().ravel()
        domain_boost = np.array([
            1.0 if domain != "general" and str(d.get("domain", "")) == domain else 0.0
            for d in self.docs
        ], dtype=np.float32)
        score = 0.68 * sw + 0.27 * sc + 0.05 * domain_boost
        idx = np.argsort(-score)[:min(int(top_k), len(self.docs))]
        out = []
        for rank, i in enumerate(idx, 1):
            r = dict(self.docs[int(i)])
            r.update({
                "score": float(score[int(i)]),
                "word_score": float(sw[int(i)]),
                "char_score": float(sc[int(i)]),
                "rank": rank,
            })
            out.append(r)
        return out

    def health(self) -> dict:
        return {
            "mode": "seed_runtime_tfidf",
            "documents": len(self.docs),
            "word_features": len(self.word_vec.vocabulary_),
            "char_features": len(self.char_vec.vocabulary_),
            "healthy": bool(self.docs),
        }
