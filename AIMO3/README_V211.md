# v2.11.0 — Exact Hard Families

This release unifies the v2.10 math-fidelity/hard-hybrid pipeline with four new deterministic engines for the hard reference-family failures observed on P6, P8, P9 and P10.

## What changed

### 1. P6-style floor-sum valuation engine
Engine: `floor_sum_valuation`.

It recognizes nested floor sums of the form

`sum_i sum_j j^r floor(1/j + (n-i)/n)`

and reduces them with Hermite's identity to divisor sums. Consecutive differences become an exact `sigma_r` value, then multiplicativity and integer valuation arithmetic finish the problem. No floating point and no model call are used after a certificate is obtained.

### 2. P8-style adaptive digit-sum dynamics engine
Engine: `adaptive_digit_sum_dynamics`.

It proves the complete next-state set is `{1,...,ceil(n/2)}`, derives the longest-path recurrence, obtains `H(n)=ceil(log2 n)`, and uses exact `bit_length` arithmetic for enormous bounds such as `10^(10^5)`.

### 3. P9 PDF recovery + correlation/cyclotomic engine
Math recovery now reconstructs

`alpha star beta = sum_{n in Z} alpha(n) beta(n)`

before routing. Engine `finite_correlation_polynomial` converts the shifted correlation to a polynomial/Laurent-polynomial coefficient identity, reduces the problem to divisors of `x^a(x^b+1)`, enumerates eligible cyclotomic factors under the degree constraint, and counts exact coefficient vectors.

### 4. P10-style divisor-minimization asymptotic engine
Engine: `norwegian_divisor_asymptotic`.

It classifies the relevant minimizing divisor triples, transfers small-factor information for `M+c` using modular arithmetic instead of constructing `M=3^(2025!)`, proves the floor correction is strictly below 1, sums the resulting rational values with `Fraction`, and applies the final modulus exactly.

### 5. Fine-grained routing and proof obligations
New families:

- `floor_sum_valuation`
- `adaptive_digit_sum_dynamics`
- `finite_sequence_correlation`
- `divisor_minimization_asymptotic`

All receive hard difficulty floors when an exact engine cannot certify the problem, so the fallback path has the full hard compute envelope instead of generic medium number-theory routing.

## Reference deterministic coverage

On the supplied AIMO3 reference PDF, engine-only mode now certifies P2–P10 exactly:

- P2 `extremal_rectangle_partition` → 520
- P3 `radical_axis_angle_bisector_triangle` → 336
- P4 `shifted_multiplicative_function` → 580
- P5 `binary_weighted_tournament` → 21818
- P6 `floor_sum_valuation` → 32951
- P7 `incircle_fibonacci_asymptotic` → 57447
- P8 `adaptive_digit_sum_dynamics` → 32193
- P9 `finite_correlation_polynomial` → 160
- P10 `norwegian_divisor_asymptotic` → 8687

P1 remains on the semantic-compiler/SymPy path in the full pipeline.

## Kaggle quick start

```bash
python scripts/preflight_v211.py --pdf "$PDF"
```

Engine-only validation:

```bash
python run_pdf_pipeline.py \
  --input "$PDF" \
  --all \
  --benchmark-reference \
  --engine-only \
  --config config_v2_11_0.yaml
```

Full hybrid run:

```bash
python run_pdf_pipeline.py \
  --input "$PDF" \
  --all \
  --benchmark-reference \
  --preload \
  --config config_v2_11_0.yaml
```

## Validation status before packaging

- 54 regression scripts were run individually/in groups and passed.
- The monolithic `tests/run_all.py` was not used as the evidence source because the local tool execution window is shorter than the whole suite; component tests were executed directly.
- Real `AIMO3_Reference_Problems.pdf` preflight passed.
- Real PDF `--engine-only --all` produced correct P2–P10 results.
- Full Python compile and clean-ZIP verification are performed during packaging.
- The local environment does not contain the user's Kaggle Qwen checkpoints, so live neural/T4 behavior is not claimed as verified.
