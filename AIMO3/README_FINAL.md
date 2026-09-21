# Olympiad AIMO3 Adaptive Reasoner — Latest Release

Latest unified release: **v2.11.0 EXACT HARD FAMILIES**.

See `README_V211.md` and `REFINEMENT_V211.md`.

Default config: `config_v2_11_0.yaml`.

Recommended Kaggle preflight:

```bash
python scripts/preflight_v211.py --pdf "$PDF"
```

Recommended full run:

```bash
python run_pdf_pipeline.py --input "$PDF" --all --benchmark-reference --preload --config config_v2_11_0.yaml
```
