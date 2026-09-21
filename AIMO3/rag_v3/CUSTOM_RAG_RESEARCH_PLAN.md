# Olympiad RAG Custom V3 — Research Plan

## Target system

Runtime models:
- Strategy proposer: DeepSeek-R1-Distill-Qwen-1.5B
- Solver/Reviser: Qwen3-4B-Instruct-2507
- Critic: Qwen3-4B-Thinking-2507

Primary deployment:
- Kaggle T4 x2
- Runtime inference offline
- Model dataset:
  `/kaggle/input/datasets/leminhhung0101/olympiad-offline-models`
- Proposed RAG dataset:
  `/kaggle/input/datasets/leminhhung0101/olympiad-rag-corpus-v3`

## Main design decision

Do not build one giant undifferentiated math index.

Use three independent knowledge stores plus one experience store:

1. theorem_store
2. problem_store
3. formal_store
4. experience_memory (kept separate from static knowledge)

Benchmarks are never indexed.

## Recommended core corpus

### A. Theorem / method store
Use the project-authored theorem and strategy records as the seed.
Expand manually with conditions, `use_when`, common errors, and source provenance.

Target:
- 500–3,000 high-quality theorem/method records over time.
- One theorem/method per document.
- No arbitrary token chunking across theorem boundaries.

### B. Solved-problem store — primary RAG corpus

#### MATH TRAIN
Use all 7,500 training examples.
Never index the 5,000 MATH test examples if MATH test is evaluated.

#### NuminaMath-CoT
Default V3 filters only:
- `olympiads`
- `amc_aime`

Do not index by default:
- aops_forum
- cn_k12
- gsm8k
- orca_math
- synthetic_math
- synthetic_amc
- math

Rationale:
- preserve olympiad focus;
- reduce duplicated/synthetic examples;
- avoid flooding the index with easy school problems;
- avoid direct overlap with MATH through Numina's `math` source.

Expected selected Numina records from the published source breakdown:
- olympiads: 150,581
- amc_aime: 4,072
- total: 154,653

With MATH train:
- ~162,153 primary solved problems before deduplication.

### C. Formal store

Use Lean Workbook base only when a clearly identifiable base record is available.
Do not ingest `lean_workbook_plus_*` by default.

Store fields:
- natural language statement
- answer
- formal statement
- proof status
- short tactic/proof evidence when reliable

Do not place large tactic traces in the normal Solver prompt.
Formal context is retrieved mainly for Critic/theorem-condition verification.

### D. NaturalProofs
Use primarily for:
- training/evaluating theorem-reference retrieval;
- learning what references a theorem needs;
- future retrieval-gate/reranker supervision.

Do not dump the entire NaturalProofs corpus into every solver query.

### E. LeanDojo
Phase-2 formal subsystem only.
Use for formal premise retrieval and a future formal critic, not the primary natural-language olympiad RAG.

### F. OpenMathInstruct-2
Keep OUT of the default primary RAG index.

It contains ~14M synthetically generated problem-solution pairs originating from MATH/GSM8K training problems and augmentations. It is much more useful here for:
- SFT;
- generating hard negatives;
- strategy augmentation;
- optional small diversity sample.

Optional V3 experiment:
- sample <= 25k–50k examples;
- quality filter;
- deduplicate against core corpus and all benchmarks;
- assign lower retrieval prior than real competition problems.

## Benchmark firewall

Never index:
- MATH test
- OlympiadBench
- Omni-MATH
- miniF2F test
- PutnamBench
- FIMO
- formal-IMO
- any benchmark selected for final paper evaluation

Keep only hashes/fingerprints of benchmark questions inside the build workspace.

Leakage checks:
1. normalized exact SHA-256
2. whitespace/LaTeX canonicalization
3. MinHash or token-Jaccard near-duplicate screen
4. semantic similarity screen
5. manual review for high-similarity candidates

## Retrieval document design

### problem_store embedding text
Embed:
- problem statement
- domain/subdomain tags
- normalized symbolic pattern
- short strategy tags if available

Do NOT embed the full solution by default.

Keep solution in payload so a retrieved analogue can return it after the document is selected.

Reason:
query-time input contains the problem, not its solution. Embedding solutions can cause retrieval to be dominated by answer wording and can increase benchmark contamination risk.

### theorem_store embedding text
Embed:
- theorem name
- statement
- conditions
- use_when
- common failure modes

### formal_store embedding text
Embed:
- natural statement
- normalized formal statement
- domain tags

Do not include long tactic traces in the dense embedding text.

## Math-aware query normalization

Keep two query forms:

1. original text
2. normalized math view

Examples:
- `abc = 1` -> `positive variables fixed product`
- `a^n - b^n` -> `difference of powers divisibility valuation`
- `x^4 + 4 y^4` -> `Sophie Germain factorization pattern`
- `p | a-b` -> `prime divisor congruence valuation`
- tangent/secant -> `power of a point`
- repeated moves/parity -> `invariant monovariant parity`

Do not replace the original query; append these semantic features.

## Hybrid retrieval

Use:
- dense: BAAI/bge-small-en-v1.5
- sparse: BM25
- domain match
- symbolic-pattern match

Initial scoring:
`0.45*dense + 0.30*bm25 + 0.15*domain + 0.10*symbol`

These are initial engineering weights, not final scientific values.
Calibrate on a held-out retrieval relevance set.

BGE-small-en-v1.5 is chosen because it is lightweight:
- hidden/embedding dimension 384
- max sequence length 512
- MIT license

This keeps the retriever cheap enough to run CPU-side while the T4 GPUs are occupied by the reasoning models.

## Separate index policy

Query:
- theorem index: top 8
- problem index: top 16
- formal index: top 6 only when needed

Then merge and gate.

Final context sent to a 4B model:
- max 1 theorem/method record
- max 1 analogous solved problem
- max 1 formal support record
- maximum RAG context target: 1,200–1,800 tokens

Do not dump top-10 full solutions into a 4B model.

## Retrieval Gate

Statuses:
- ACCEPT
- WEAK
- CONFLICT
- NO_CONTEXT

Gate features:
- hybrid top-1
- top1-top2 margin
- domain match
- symbol-pattern match
- source quality prior
- agreement across dense/BM25
- contradiction flags

Initial rule-based gate is acceptable.
Final paper should calibrate a small logistic-regression/XGBoost gate on held-out relevance labels.

Only one query rewrite is allowed:
`q0 -> retrieve -> NO_CONTEXT -> rewrite q1 -> retrieve -> still weak -> SKIP_RAG`

## Source priors

Suggested initial priors:
- authored theorem/method: 1.00
- MATH train: 1.00
- Numina olympiads: 0.95
- Numina AMC/AIME: 0.90
- Lean Workbook base: 0.85
- optional synthetic material: 0.55–0.70

These priors should affect tie-breaking and gating, not override semantic relevance.

## Runtime routing

Problem
-> Analyzer
-> query theorem_store + problem_store
-> Gate
-> Proposer 1.5B
-> Strategy search
-> Solver 4B
-> Python/SymPy when useful
-> optional formal_store retrieval when critic needs proof support
-> Thinking Critic 4B
-> Revision
-> Final

Formal retrieval is conditional. It should not add overhead to easy algebra/arithmetic problems.

## Expected practical corpus size

Primary problem store:
- ~162k records before dedup (MATH train + filtered Numina)

Optional Lean base formal records:
- up to ~57k according to the published dataset description, but use only records actually present and passing quality checks in the pinned snapshot.

Total target:
- roughly 160k–220k static RAG documents before optional NaturalProofs/other extensions.

For 220k documents with 384-dimensional FP16 dense embeddings:
- raw embedding matrix ~169 MB.
- FAISS plus metadata/BM25/solutions should still fit comfortably in a few GB.

This is intentionally far smaller and cleaner than a 14M-document index.

## Kaggle dataset layout

`/kaggle/input/datasets/leminhhung0101/olympiad-rag-corpus-v3/`

```text
corpus/
  theorem_store.parquet
  problem_store.parquet
  formal_store.parquet

index/
  theorem.faiss
  problem.faiss
  formal.faiss
  bm25/
  doc_metadata.parquet

retriever_model/
  bge-small-en-v1.5/

metadata/
  source_manifest.json
  corpus_stats.json
  leakage_report.json
  build_config.yaml
  dataset_snapshot.json

benchmark_fingerprints/
  holdout_hashes.parquet
```

Do not place raw benchmark questions in the RAG dataset.

## Build vs runtime

Build phase:
- Internet ON
- download approved datasets
- normalize
- filter
- dedup
- leakage scan
- embed
- build FAISS/BM25
- save retriever model
- publish a private Kaggle Dataset

Runtime:
- Internet OFF
- attach two Kaggle datasets:
  1. olympiad-offline-models
  2. olympiad-rag-corpus-v3
- load all models/indexes locally.

## First experiment matrix

RAG ablation:
1. No RAG
2. Always RAG
3. Sparse-only RAG
4. Dense-only RAG
5. Hybrid RAG
6. Hybrid + Gate (proposed)

Corpus ablation:
1. theorem only
2. theorem + MATH
3. theorem + MATH + Numina Olympic
4. + formal store
5. + optional synthetic sample

Report:
- answer accuracy
- retrieval Recall@K on manually labeled retrieval queries
- retrieval precision@K
- Retrieval Utility
- Retrieval Harm
- RAG skip rate
- tokens/problem
- GPU seconds/problem
- revision success
