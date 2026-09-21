# v2.6.1 Verification Audit

This revision focuses on preventing false claims of mathematical verification.

## Fixed

1. **Unrelated exact checks no longer certify an answer.**
   A true identity such as `2+2=4` cannot verify candidate answer `999`.
   Automatic exact evidence requires an answer-bound `check_equalities` certificate with
   at least one verified equality and a verified `answer_expr` whose expected value equals
   the parsed candidate answer.

2. **Critic PASS cannot override failed tools.**
   If the selected candidate has any exact report with `ok=false` or `verified=false`,
   `critic_verification()` rejects PASS regardless of critic confidence.

3. **Strict Qwen Thinking parsing.**
   Critic final fields are parsed only after the last `</think>`. If no closing delimiter
   exists, `VERDICT: PASS` text inside unfinished reasoning is never trusted.

4. **Generation is capped inside `generate()`.**
   The remaining global token budget caps `max_new_tokens`; the remaining time budget is
   propagated to Transformers `max_time`. This is stronger than checking budget only before
   and after a model call.

5. **Qwen effective EOS uses model generation config.**
   The model's `generation_config.eos_token_id` is preferred over a single tokenizer EOS,
   preserving Qwen's configured EOS list when available.

6. **Qwen Thinking role follows its released generation defaults.**
   Critic config uses sampling with temperature 0.6, top-p 0.95, top-k 20; generation remains
   bounded by global token/time limits.

7. **SymPy tool input no longer uses `sympify`/eval on model-generated strings.**
   Expressions are parsed through a small Python AST whitelist supporting exact arithmetic,
   safe symbols, powers, and a small function allowlist.

8. **Benchmark correctness is separate from runtime verification.**
   `benchmark_record()` adds `verification_false_positive` and
   `candidate_correct_but_unverified`. Expected answers are compared only after pipeline
   completion and are never exposed to the model.

9. **Default exact-tool policy is conservative.**
   `accept_exact_tool_without_critic: false`. Exact arithmetic can establish strong evidence,
   but a semantic critic confirms that the certificate actually solves the stated problem.

## CPU tests actually run in this environment

- `test_parsing.py` PASS
- `test_tools.py` PASS
- `test_safe_tools.py` PASS
- `test_verification_guards.py` PASS
- `test_budget.py` PASS
- `test_generation_budget.py` PASS
- `test_evaluation.py` PASS
- `test_rag_runtime.py` PASS (55 seed documents)
- `test_pipeline_problem1_mock.py` PASS
- `test_pdf_reader.py` PASS against the 10-problem AIMO3 reference PDF
- Python compilation PASS for `core/`, `rag/`, and runners

## Not claimed as tested here

This environment does not contain the user's local model checkpoints or Kaggle T4x2 GPUs.
The following must still be validated on Kaggle:

- real NF4 loading of all three checkpoints
- real solver/critic generation behavior
- GPU memory peaks
- per-problem latency
- Qwen Thinking delimiter behavior under the local checkpoint/tokenizer pair
- all 10 reference problems and final AIMO3 competition runner

## Recommended Kaggle smoke test

Run Problem 1 first with `config_v2_6_1.yaml`. A trustworthy success should have:

- `candidate_answer = 50`
- `verified_answer = 50` only after critic PASS
- no failed tool report
- `benchmark.verified_correct = true`
- `benchmark.verification_false_positive = false`

Then test Problems 4 and 8 before running all 10.
