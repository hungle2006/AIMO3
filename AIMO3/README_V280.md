# Olympiad AIMO3 Adaptive Reasoner T4x2 — v2.8.0

v2.8.0 adds deterministic family engines ahead of the Qwen solver/critic while preserving the v2.7.2 target-grounded, fail-closed verification path.

## Recommended Kaggle smoke test

```bash
python scripts/preflight_v280.py --pdf "$PDF"
```

CPU-only deterministic audit (does not load transformers/models):

```bash
python run_pdf_pipeline.py \
  --input "$PDF" \
  --all \
  --benchmark-reference \
  --engine-only \
  --config config_v2_8_0.yaml
```

Then run a full problem with models:

```bash
python run_pdf_pipeline.py \
  --input "$PDF" \
  --problem-number 2 \
  --benchmark-reference \
  --preload \
  --config config_v2_8_0.yaml
```

For a supported exact family, the result should have `verification=FAMILY_EXACT` and `model_calls=0`. Unsupported problems fall back to the existing semantic compiler / Qwen Instruct / focused proof / Thinking escalation pipeline.
