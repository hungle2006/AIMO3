# v2.8.1 — Runtime Scope Fix

This is a hotfix over v2.8.0.

## Fixed Kaggle crash

Normal GPU runs could fail after model preload with:

```text
UnboundLocalError: cannot access local variable 'FullOlympiadPipeline'
where it is not associated with a value
```

Root cause: `run_pdf_pipeline.py` imported `FullOlympiadPipeline` both at module scope and again inside the `if args.engine_only:` branch. In Python, an import inside a function is an assignment, so that second import made `FullOlympiadPipeline` a local variable throughout `main()`. The normal branch then referenced it before the engine-only branch had assigned it.

v2.8.1 removes the inner import and adds `tests/test_run_pdf_scope_v281.py` so the same scoping regression is caught before upload.

## Recommended Kaggle preflight

```bash
python scripts/preflight_v281.py --pdf "$PDF"
```

## Full P2 run

```bash
python run_pdf_pipeline.py \
  --input "$PDF" \
  --problem-number 2 \
  --benchmark-reference \
  --config config_v2_8_1.yaml
```

For P2/P4/P5, omit `--preload`; the deterministic family engine runs before any LLM call and should return an exact certificate without loading the models.

## Fail-fast startup

v2.8.1 constructs `FullOlympiadPipeline` before `manager.preload()`. Therefore Python/configuration regressions fail before the two 4B checkpoints spend time loading.

A corrected `Kaggle_v281_Run.ipynb` is included; the old v2.8.0 notebook contained a stale source-folder name.
