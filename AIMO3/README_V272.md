# Olympiad AIMO3 Adaptive Reasoner T4x2 v2.7.2 — Target-Grounded Commit/Verify

This release refines v2.7.1 after a real P2 run exposed a new orchestration failure: the solver copied the output modulus `10^5` as an early answer (`100000`), and later proof-obligation calls proposed rough upper bounds (`1000`, `707`) that were incorrectly treated as answer corrections.

## Main changes

- **Target-spec grounding**: parse the requested output contract before solving. A remainder modulo `M` must be in `[0, M-1]`; the modulus itself is rejected before proof routing.
- **No blind early commit**: the solver must write a key reduction first and may commit only when it has a defensible candidate. `UNKNOWN` is allowed.
- **No auto-promotion of micro-proof guesses**: `CORRECTED_CANDIDATE` from an obligation verifier is only a hypothesis. It cannot become the final candidate automatically.
- **Refutation → dedicated repair state**: when an obligation refutes a target-valid candidate, the pipeline marks it dead, calls a separate candidate-repair stage, validates the repaired candidate against the target contract, and restarts obligations.
- **Evidence-grounded obligations**: self-declared `DONE` is not enough. Construction, upper-bound, and arithmetic obligations require family-appropriate evidence.
- **Safer finalization**: only target-valid, non-refuted candidates are eligible for `CANDIDATE_ONLY` or critic review.
- **Diagnostics**: output now records `target_spec`, per-candidate target validity/reasons, rejected candidate values, proof refutations, and repair candidates.

## Safety invariant

`candidate_answer != verified_answer`. An early commit, target-valid integer, proof-obligation suggestion, or critic preference is not mathematical verification by itself.

## Kaggle quick start

```bash
python scripts/preflight_v272.py
python tests/test_target_grounding_v272.py
python tests/test_invalid_modulus_commit_v272.py
python tests/test_refutation_repair_v272.py
```

Then run P2:

```bash
python run_pdf_pipeline.py \
  --input "$PDF" \
  --problem-number 2 \
  --benchmark-reference \
  --preload \
  --config config_v2_7_2.yaml
```

## What to inspect in the JSON

- `analysis.target_spec` / top-level `target_spec`
- `metrics.candidate_target_validity`
- `metrics.candidate_target_reasons`
- `metrics.rejected_candidate_values`
- `proof_completion.refutations`
- `proof_completion.repair_candidates`
- `proof_completion.final_missing`
- `candidate_answer`, `verified_answer`, `verification_level`

## Runtime note

The package has CPU regression tests for routing, target grounding, refutation repair, proof obligations, parsing, verification guards, PDF math fidelity, and legacy v2.6/v2.7 behavior. Real three-model inference still requires Kaggle T4×2 validation.
