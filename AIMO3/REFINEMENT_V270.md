# Refinement plan — v2.7.0

## Evidence from v2.6.4 reference runs

- Problem 1: semantic compiler path succeeded with one model call and exact verification.
- Problems 2, 3, and 5: the PDF layout extraction visibly lost superscripts; the old pipeline passed that corrupted text to the solver even though the math-aware retrieval text was correct.
- Problems 2–5: the Instruct solver repeatedly reached its exact output-token cap without a final marker. Restart-style recovery repeated work instead of exploiting progress.
- Problem 4: the solver discovered the multiplicative change of variables but then made a conceptual error about completely additive arithmetic functions.
- Weak/irrelevant RAG and generic proposer calls consumed calls without yielding answers.

## v2.7.0 changes

### P0 — input correctness
- `InputProblem.solver_text` is now explicit.
- PDF solver input uses the math-aware semantic view.
- `run_pdf_pipeline.py` stores both layout and solver text in `input_fidelity`.
- Regression tests assert exponent recovery and no Answer/Solution leakage.

### P0 — compute routing
- family classification and family-specific hints;
- functional equations, extremal partitions, Euclidean geometry, and combinatorial processes receive a minimum medium compute envelope;
- proposer disabled by default;
- one quick Instruct attempt + continuation; then Thinking escalation if still unresolved.

### P1 — RAG precision
- seed analyzer has structural cues for functional equations, extremal tilings, and binary score processes;
- only `ACCEPT` context is injected;
- no-answer cases send accepted context directly to Thinking rather than paying for `RAG1` first;
- RAG reports `attempted` separately from `used`.

### P1 — truncation recovery
- continuation prompt consumes only the tail of prior output;
- Thinking output is parsed only after a closed `</think>`;
- if Thinking is truncated before a final answer, a short Instruct finisher can use the thinking tail.

### P1 — evaluation integrity
- benchmark answers remain post-hoc evaluation only;
- reference solutions are not added to runtime RAG;
- external RAG V3 remains non-operational until a real hybrid adapter/index loader is implemented and validated.

## Next experiments

1. P2: confirm fixed PDF exponent, continuation, and extremal RAG behavior.
2. P4: verify family floor routes it to medium and deep escalation can correct the completely-additive-function misconception.
3. P5: confirm powers-of-two input fidelity and binary-process RAG context.
4. P3 last: geometry is the hardest test of the 4B model; inspect whether radical-axis/coordinate hints produce a derived condition rather than guessed triples.
5. Only after those smoke tests, run all ten and compare v2.6.4 vs v2.7.0 on accuracy, verified accuracy, tokens, calls, latency, truncations, RAG use, and verification false positives.
