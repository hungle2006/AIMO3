# AIMO3 Adaptive Reasoner T4x2 — v2.7.1 Commit + Verify

v2.7.1 refines v2.7.0 around the real failure mode observed on Problem 2: correct input and useful reasoning were present, but every generation ended at the output cap before a final answer was emitted.

## Main changes

1. **Early candidate commitment** — preserve an integer candidate even if the proof later truncates.
2. **Family-specific proof obligations** — complete only the missing proof component instead of restarting the problem.
3. **Focused Thinking escalation** — use Qwen Thinking for candidate discovery or one missing obligation, not a 3k-token full rewrite.
4. **Tiny finisher** — if focused Thinking does not close, finish the same task with Instruct rather than restarting.
5. **RAG top-hit dominance** — suppress unrelated lower-ranked contexts when one hit clearly dominates.
6. **Conservative verification** — early candidates remain `CANDIDATE_ONLY` until proof/protocol and critic requirements are met.

See `REFINEMENT_V271.md` for the design rationale.

## Kaggle run

```bash
python scripts/preflight_v271.py
```

Inspect PDF fidelity without loading models:

```bash
python run_pdf_pipeline.py \
  --input "$PDF" \
  --problem-number 5 \
  --benchmark-reference \
  --inspect-only \
  --config config_v2_7_1.yaml
```

Run Problem 2:

```bash
python run_pdf_pipeline.py \
  --input "$PDF" \
  --problem-number 2 \
  --benchmark-reference \
  --preload \
  --config config_v2_7_1.yaml
```

Recommended smoke-test order:

```text
P2 → P4 → P5 → P3 → all 10
```

## New diagnostics

Look for these fields in the JSON output:

```text
analysis.proof_obligations
proof_completion.initial_missing
proof_completion.micro_results
proof_completion.final_missing
metrics.candidate_committed_early
metrics.answer_commit_survived_truncation
metrics.proof_micro_calls
metrics.candidate_answers
metrics.candidate_parse_modes
```

A useful partial result now looks like:

```text
status: CANDIDATE_ONLY
candidate_answer: <integer>
verified_answer: None
answer_commit_survived_truncation: true
```

This is intentionally different from `VERIFIED_PASS`: preserving a candidate is not the same as proving it.

## Tests

Run:

```bash
python tests/run_all.py
```

For a quick targeted check:

```bash
python tests/test_commit_parser_v271.py
python tests/test_rag_dominance_v271.py
python tests/test_commit_verify_pipeline_v271.py
python tests/test_deep_candidate_v271.py
python tests/test_pdf_math_fidelity_v27.py
```

## Verification status

The package has been compiled and CPU regression-tested in the build environment. GPU inference with the three local checkpoints still needs confirmation on Kaggle T4x2; no claim is made that Problems 2–5 are solved until those runs are observed.
