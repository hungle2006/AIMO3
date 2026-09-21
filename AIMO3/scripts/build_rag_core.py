from __future__ import annotations

"""
One-time ONLINE builder for the primary AIMO/Olympiad RAG corpus.

Core policy:
- MATH train: include
- NuminaMath-CoT: include only source in {"olympiads", "amc_aime"}
- benchmark/test sets: never index
- OpenMathInstruct-2: off by default
"""

from pathlib import Path
import argparse
import hashlib
import json
import re

import pandas as pd


def norm_text(s: str) -> str:
    s = str(s or "")
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s


def sha256_text(s: str) -> str:
    return hashlib.sha256(norm_text(s).encode("utf-8")).hexdigest()


def load_hf_stream(repo: str, split: str = "train"):
    from datasets import load_dataset
    return load_dataset(repo, split=split, streaming=True)


def normalize_math(row, idx):
    problem = str(row.get("problem", ""))
    solution = str(row.get("solution", ""))
    return {
        "doc_id": f"math_{idx}",
        "store": "problem",
        "source_id": "math_train",
        "source_split": "train",
        "original_id": str(row.get("id", idx)),
        "domain": str(row.get("type", "") or ""),
        "subdomain": None,
        "problem": problem,
        "solution": solution,
        "theorem_name": None,
        "formal_statement": None,
        "retrieval_text": problem,
        "symbol_features": [],
        "quality_prior": 1.0,
        "source_url": "https://huggingface.co/datasets/jeggers/competition_math",
        "license_snapshot": "MIT per dataset card snapshot; verify/pin before publication",
        "content_hash": sha256_text(problem),
        "benchmark_overlap": False,
    }


def normalize_numina(row, idx):
    source = str(row.get("source", "") or "")
    problem = str(row.get("problem", "") or "")
    solution = str(row.get("solution", row.get("answer", "")) or "")
    prior = 0.95 if source == "olympiads" else 0.90
    return {
        "doc_id": f"numina_{idx}",
        "store": "problem",
        "source_id": f"numina_{source}",
        "source_split": "train",
        "original_id": str(row.get("id", idx)),
        "domain": str(row.get("problem_type", "") or ""),
        "subdomain": None,
        "problem": problem,
        "solution": solution,
        "theorem_name": None,
        "formal_statement": None,
        "retrieval_text": problem,
        "symbol_features": [],
        "quality_prior": prior,
        "source_url": "https://huggingface.co/datasets/AI-MO/NuminaMath-CoT",
        "license_snapshot": "Pin exact revision/license snapshot before redistribution",
        "content_hash": sha256_text(problem),
        "benchmark_overlap": False,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default="/kaggle/working/olympiad_rag_v3_build")
    ap.add_argument("--max-math", type=int, default=7500)
    ap.add_argument("--max-numina", type=int, default=200000)
    args = ap.parse_args()

    out = Path(args.output)
    (out / "corpus").mkdir(parents=True, exist_ok=True)
    (out / "metadata").mkdir(parents=True, exist_ok=True)

    rows = []

    print("Streaming MATH train...")
    for i, r in enumerate(load_hf_stream("jeggers/competition_math", "train")):
        if i >= args.max_math:
            break
        rows.append(normalize_math(r, i))

    print("Streaming filtered NuminaMath-CoT...")
    kept = 0
    seen = set(x["content_hash"] for x in rows)
    for i, r in enumerate(load_hf_stream("AI-MO/NuminaMath-CoT", "train")):
        source = str(r.get("source", "") or "")
        if source not in {"olympiads", "amc_aime"}:
            continue
        row = normalize_numina(r, i)
        if row["content_hash"] in seen:
            continue
        seen.add(row["content_hash"])
        rows.append(row)
        kept += 1
        if kept >= args.max_numina:
            break

    df = pd.DataFrame(rows)
    path = out / "corpus/problem_store.parquet"
    df.to_parquet(path, index=False)

    stats = {
        "rows": len(df),
        "math_rows": int((df.source_id == "math_train").sum()),
        "numina_rows": int(df.source_id.str.startswith("numina_").sum()),
        "unique_hashes": int(df.content_hash.nunique()),
    }
    (out / "metadata/corpus_stats.json").write_text(
        json.dumps(stats, indent=2), encoding="utf-8"
    )

    print("Saved:", path)
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
