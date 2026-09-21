# v2.8.1 refinement

- Fixes Python local-name shadowing in `run_pdf_pipeline.main()`.
- Removes redundant branch-local import of `FullOlympiadPipeline`.
- Adds an AST/code-object regression test for the exact `UnboundLocalError` seen on Kaggle.
- Adds `preflight_v281.py` and `config_v2_8_1.yaml`.
- Changes default run config to v2.8.1 and output directory to `/kaggle/working/olympiad_runs_v281`.
- No mathematical engine logic was changed from v2.8.0.

- Moves pipeline construction before GPU preload to fail fast.
- Updates `run_batch.py` default config to v2.8.1.
- Adds a corrected `Kaggle_v281_Run.ipynb` with the actual v2.8.1 folder/config names.
