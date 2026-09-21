# Kaggle Build Steps — Custom RAG V3

This is a one-time ONLINE build. Final inference remains offline.

## 1. Create workspace

```python
from pathlib import Path
ROOT = Path("/kaggle/working/olympiad_rag_v3_build")
ROOT.mkdir(parents=True, exist_ok=True)
```

## 2. Install build dependencies

```bash
pip install -q -U datasets huggingface_hub sentence-transformers faiss-cpu pyarrow pandas scikit-learn pyyaml
```

For a production hybrid BM25 index, additionally use an efficient sparse package such as `bm25s`.

## 3. Download only approved core data first

Core V3:
- MATH train
- NuminaMath-CoT train filtered to `olympiads` and `amc_aime`

Do not start by downloading 14M OpenMathInstruct rows.

## 4. Normalize every row into the V3 schema

Important:
- dense `retrieval_text` for solved problems should contain the problem + metadata/patterns;
- the solution remains in payload and is not part of the default embedding text.

## 5. Create benchmark fingerprints before indexing

At minimum:
- MATH test
- whichever external benchmarks will be reported in the paper

Then run:
- exact normalized hash check
- near duplicate checks
- semantic duplicate review

## 6. Build dense embeddings

Use `BAAI/bge-small-en-v1.5`.

Store the embedding model itself under:

```text
retriever_model/bge-small-en-v1.5/
```

so runtime can be fully offline.

## 7. Build per-store indexes

Do not mix everything into a single uncontrolled index.

Create:
- theorem.faiss
- problem.faiss
- formal.faiss

Create a corresponding metadata table containing the FAISS row -> doc_id mapping.

## 8. Build BM25/sparse indexes

Use the same separation by store.

## 9. Calibrate retrieval gate

Create 200–500 representative olympiad retrieval queries and manually label:
- useful
- weak
- harmful/irrelevant

Tune:
- hybrid weights
- ACCEPT/WEAK thresholds
- source priors

Do not tune gate parameters on final OlympiadBench/Omni-MATH test questions.

## 10. Publish private Kaggle Dataset

Proposed slug:

```text
leminhhung0101/olympiad-rag-corpus-v3
```

Runtime then uses:

```text
/kaggle/input/datasets/leminhhung0101/olympiad-offline-models
/kaggle/input/datasets/leminhhung0101/olympiad-rag-corpus-v3
```

with Internet OFF.
