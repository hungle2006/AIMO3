# Olympiad AIMO3 Adaptive Reasoner — v2.6.4

Main change: **structured semantics -> deterministic compiler -> exact solver** for short relational algebra word problems.

Use `config_v2_6_4.yaml`.

## Kaggle smoke test

```bash
python tests/test_semantic_compiler_guards.py
python tests/test_semantic_repair_pipeline.py
python tests/test_constraint_first_pipeline.py
```

Then:

```bash
python run_pdf_pipeline.py \
  --input "$PDF" \
  --problem-number 1 \
  --benchmark-reference \
  --preload \
  --config config_v2_6_4.yaml
```

Useful result fields:

```text
constraint_formalization
semantic_compilation
semantic_exact_solution
metrics.semantic_compilation_ok
metrics.semantic_certificate_ok
metrics.semantic_repairs
metrics.deterministic_semantic_solve
```

A supported exact run can finish as `VERIFIED_PASS` with verification level `SEMANTIC_EXACT` without spending a long Qwen solver generation.


> New default runtime: see `README_V270.md` and `config_v2_7_0.yaml`.
