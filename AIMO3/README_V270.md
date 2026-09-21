# AIMO3 Adaptive Reasoner T4x2 — v2.7.0 Fidelity + Adaptive

This revision is based on the real reference runs for Problems 1–5. It keeps the v2.6.4 semantic compiler that solved Problem 1, but fixes the failure modes that dominated Problems 2–5.

## What changed

1. **PDF math-fidelity is now a hard invariant.** The solver receives the math-aware semantic view, not the plain PDF layout text. This preserves superscripts such as `2^{20}`, `10^{k}`, and `10^{5}`. The plain extraction is retained only for audit/display.
2. **Family-aware routing.** Problems are classified into relational algebra, functional equations, extremal partitions, Euclidean geometry, combinatorial processes, number theory, or general. Family difficulty floors prevent deceptively short functional equations from being routed as cheap/easy.
3. **Continuation instead of restart.** If the Instruct solver reaches its token cap, the recovery call continues from the tail instead of repeating the full derivation.
4. **Deep Thinking escalation.** When Instruct still has no answer, `Qwen3-4B-Thinking-2507` is used once as a deep solver. Only its public content after `</think>` can produce an answer. If the thinking generation itself is cut off, a short Instruct finisher can continue from its tail.
5. **RAG is stricter and cheaper.** Retrieval is CPU-side. `WEAK` context is never injected. For no-answer cases, an `ACCEPT` context goes directly into the Thinking escalation instead of spending an extra full Instruct solve. Seed RAG remains the actual runtime; external RAG V3 is not claimed as operational.
6. **Proposer is optional.** It is disabled in the default medium/hard budgets and no longer preloaded. This saves GPU0 memory and avoids spending a call on generic/truncated strategy JSON. It remains available for ablations.
7. **Problem-family seed knowledge.** The bundled 60-document seed store includes general, answer-free patterns for completely additive arithmetic functions, extremal tilings, binary-weighted processes, and coordinate/cyclic-geometry search. Reference answers are never injected into prompts or RAG.

## Default T4x2 roles

- GPU0: Qwen3-4B-Instruct-2507 solver
- GPU1: Qwen3-4B-Thinking-2507 deep solver / critic
- DeepSeek-R1-Distill-Qwen-1.5B: on-demand proposer only
- CPU: PDF parser, sparse RAG, SymPy/Python verification

## Recommended Kaggle smoke test

```bash
python scripts/preflight_v27.py
python tests/test_pdf_math_fidelity_v27.py
python tests/test_problem_family_v27.py
python tests/test_rag_refinement_v27.py
python tests/test_thinking_solver_parser_v27.py
python tests/test_deep_escalation_v27.py
python tests/test_deep_finish_v27.py
```

Then inspect the PDF representation before spending GPU time:

```bash
python run_pdf_pipeline.py --input "$PDF" --problem-number 5 --benchmark-reference --inspect-only --config config_v2_7_0.yaml
```

The solver text for Problem 5 should contain `2^{20}`, `2^{20−i}`, `10^{k}`, and `10^{5}`.

Run one problem:

```bash
python run_pdf_pipeline.py --input "$PDF" --problem-number 2 --benchmark-reference --preload --config config_v2_7_0.yaml
```

Do not run all ten until Problems 2, 4, 5, then 3 have been smoke-tested.

## Validation status

CPU regression tests, parser/verification tests, seed-RAG tests, and PDF fidelity tests pass in the build environment. Real T4x2 inference for v2.7.0 must still be confirmed on Kaggle; no claim is made that Problems 2–5 are solved until those GPU runs are observed.
