# v2.10.0 — Math Fidelity + Hard Hybrid

This release is a reliability refinement of v2.9.0 for AIMO-style offline reasoning on 2×T4.

## Main changes

1. **Leakage-safe PDF math recovery** (`core/pdf_math_recovery.py`)
   - repairs statement-only TeX extraction for stacked fractions, floors, sums and nested powers;
   - includes structural recovery for the difficult reference styles in Problems 6–10;
   - never reads the `Answer:` or `Solution:` region.
2. **Hard geometry-sequence family router**
   - new family: `geometry_sequence_asymptotic`;
   - difficulty floor 0.78 → hard budget;
   - proof obligations: exact geometry reduction, exact sequence formula, asymptotic limit, target arithmetic.
3. **Exact P7-style family engine**
   - engine: `incircle_fibonacci_asymptotic`;
   - derives the target ratio, Fibonacci ratio, dominant root and eventual upper bound symbolically;
   - evaluates the requested modular target exactly;
   - fail-closed structural matching; no reference answer is stored in runtime code.
4. **Hard retry after refutation**
   - if a hard neural candidate and its repair are both refuted, the pipeline spends one real Thinking solve on the original problem instead of terminating on cheap guesses;
   - optional Instruct finisher remains available when Thinking output is incomplete.
5. **Runtime diagnostics**
   - PDF results now include raw semantic text and math-recovery diagnostics;
   - metrics include `hard_retry_after_refutation`.

## Exact engines currently available

- relational P1: semantic compiler + SymPy path (full pipeline)
- extremal rectangle partition
- radical-axis / angle-bisector integer triangle
- shifted multiplicative functional equation
- binary weighted tournament
- incircle + Fibonacci asymptotic geometry

Unsupported families fail closed and fall back to the neural/RAG pipeline.

## Kaggle quick start

```bash
python scripts/preflight_v210.py --pdf "$PDF"
```

Inspect deterministic coverage without loading models:

```bash
python run_pdf_pipeline.py \
  --input "$PDF" \
  --all \
  --benchmark-reference \
  --engine-only \
  --config config_v2_10_0.yaml
```

Full hybrid run:

```bash
python run_pdf_pipeline.py \
  --input "$PDF" \
  --all \
  --benchmark-reference \
  --preload \
  --config config_v2_10_0.yaml
```

## Validation performed before packaging

- 45 regression tests: PASS
- 93 Python files: compile clean
- real AIMO3 reference PDF preflight: PASS
- exact reference engine checks: P2, P3, P4, P5, P7 PASS
- statement math recovery checks: P6, P7, P8, P9, P10 PASS
- distinctive benchmark-answer literal scan over runtime code: PASS
- cache scan (`__pycache__`, `.pyc`, `.pyo`): clean

The local validation environment does not contain the user's Kaggle model checkpoints, so neural GPU behavior for unsupported families remains to be verified on Kaggle/T4. Deterministic engines and CPU orchestration were executed locally.
