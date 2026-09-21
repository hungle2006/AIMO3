# v2.8.0 — Deterministic Family Engines + Virtual Audit

## Why this version exists
v2.7.x fixed PDF fidelity, target grounding, and candidate drift, but real runs showed that a 4B model can still waste compute on structures that admit exact algorithmic treatment. v2.8.0 moves three recognizable problem families to fail-closed deterministic engines before any LLM call.

## New exact engines

### 1. Extremal integer-rectangle partition
Recognizes a rectangular board tiled by integer-sided rectangles with pairwise-distinct perimeters.

- Computes a rigorous area lower bound for each possible semiperimeter.
- Derives an exact numerical upper bound on the number of rectangles.
- Searches a generic two-zone strip construction parametrically.
- Mechanically verifies integer coordinates, board coverage, no overlap, and pairwise-distinct perimeters.
- Certifies only when construction lower bound equals the rigorous upper bound.

The construction search contains no benchmark answer constant.

### 2. Shifted multiplicative functional equation
Recognizes
`f(m)+f(n)=f(m+n+mn)` under a finite bound on `f(n)` and a target value-count query.

- Uses `g(n)=f(n-1)` to obtain `g(ab)=g(a)+g(b)`.
- Factors the shifted target.
- Treats prime values as positive integer weights.
- Compresses all bounded-input constraints by target-prime exponent vector.
- Exactly enumerates feasible target-prime weights and counts distinct target values.

### 3. Binary-weighted equal-score tournament
Recognizes `2^R` runners, `R` equal-score pairing rounds, and binary point weights `2^(R-i)`.

- Uses the equal-history state decomposition.
- Counts valid winner sets with Catalan numbers.
- Computes `v2` and `v5` of the product exactly via factorial valuations.
- Applies requested target normalization only after proving the raw quantity.

## Safety / anti-overfit rules
- Engines are pattern-gated and fail closed.
- Exact certification requires a mechanical certificate.
- No reference-benchmark expected-answer list is present in `core/`.
- If an engine recognizes a family but cannot close its certificate, the normal LLM pipeline runs.
- Unsupported geometry/number-theory problems continue through the adaptive LLM path.

## CPU virtual audit
The package includes `scripts/virtual_regression_v280.py` and `--engine-only` mode in `run_pdf_pipeline.py`.

Reference-PDF CPU test (no transformers/GPU):
- Problem 2 -> 520, exact deterministic certificate
- Problem 4 -> 580, exact deterministic certificate
- Problem 5 -> 21818, exact deterministic certificate
- Other problems -> unsupported, not guessed

All legacy verification, parsing, budget, RAG, semantic-compiler and new family-engine regression tests are retained.
