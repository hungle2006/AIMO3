from __future__ import annotations
from pathlib import Path
import argparse
import json
import numpy as np
import pandas as pd


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--model", default="BAAI/bge-small-en-v1.5")
    ap.add_argument("--output-root", required=True)
    ap.add_argument("--batch-size", type=int, default=256)
    args = ap.parse_args()

    from sentence_transformers import SentenceTransformer
    import faiss

    df = pd.read_parquet(args.corpus)
    texts = df["retrieval_text"].fillna("").astype(str).tolist()

    model = SentenceTransformer(args.model, device="cpu")
    emb = model.encode(
        texts,
        batch_size=args.batch_size,
        show_progress_bar=True,
        normalize_embeddings=True,
        convert_to_numpy=True,
    ).astype("float32")

    out = Path(args.output_root)
    (out / "index").mkdir(parents=True, exist_ok=True)
    (out / "retriever_model").mkdir(parents=True, exist_ok=True)

    index = faiss.IndexFlatIP(emb.shape[1])
    index.add(emb)
    faiss.write_index(index, str(out / "index/problem.faiss"))

    meta = df[[
        "doc_id", "source_id", "domain", "quality_prior", "content_hash"
    ]].copy()
    meta["faiss_row"] = np.arange(len(meta))
    meta.to_parquet(out / "index/doc_metadata.parquet", index=False)

    model.save(str(out / "retriever_model/bge-small-en-v1.5"))

    manifest = {
        "rows": len(df),
        "dim": int(emb.shape[1]),
        "metric": "cosine via normalized inner product",
        "model": args.model,
    }
    (out / "index/index_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
