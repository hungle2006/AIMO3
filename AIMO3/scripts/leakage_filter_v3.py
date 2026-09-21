from __future__ import annotations
from pathlib import Path
import argparse
import hashlib
import re
import pandas as pd


def normalize(s):
    s = str(s or "").lower()
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"\\left|\\right", "", s)
    return s


def h(s):
    return hashlib.sha256(normalize(s).encode("utf-8")).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--benchmark", action="append", required=True)
    ap.add_argument("--benchmark-problem-column", default="problem")
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    corpus = pd.read_parquet(args.corpus)
    heldout = set()

    for bp in args.benchmark:
        p = Path(bp)
        if p.suffix == ".parquet":
            b = pd.read_parquet(p)
        elif p.suffix == ".csv":
            b = pd.read_csv(p)
        else:
            raise ValueError(f"Unsupported benchmark file: {p}")
        heldout.update(h(x) for x in b[args.benchmark_problem_column].fillna(""))

    corpus["benchmark_overlap"] = corpus["problem"].fillna("").map(
        lambda x: h(x) in heldout
    )
    clean = corpus[~corpus["benchmark_overlap"]].copy()
    clean.to_parquet(args.output, index=False)

    print("Rows before:", len(corpus))
    print("Exact benchmark overlaps removed:", int(corpus["benchmark_overlap"].sum()))
    print("Rows after:", len(clean))


if __name__ == "__main__":
    main()
