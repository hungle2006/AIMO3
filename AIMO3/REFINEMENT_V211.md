# Refinement v2.11.0

## Failure evidence addressed

The v2.10 full run exposed four distinct failures behind one generic `number_theory` fallback:

- P6: incorrect floor-threshold reasoning produced candidate 0; the critic detected the flaw but truncated.
- P8: three generations truncated while repeatedly guessing a base-2 repunit heuristic, despite remaining compute budget.
- P9: the PDF text layer broke the bilateral sum defining `star`, causing the solver/verifier to misread a correlation problem as support counting.
- P10: the solver replaced an exact floor/divisor minimization problem by the unsupported approximation `f(M+c) ≈ M`, producing candidate 7.

## Architectural response

v2.11 moves these patterns ahead of the neural pipeline:

`math recovery -> fine family router -> deterministic reduction -> exact certificate -> target normalization -> FAMILY_EXACT`

Only if the structural matcher or certificate fails does the problem return to the hard neural/RAG fallback.

## Safety against benchmark lookup

Runtime engines do not store the reference answers. They parse parameters from the problem statement and derive outputs by exact arithmetic. Reference answers appear only in regression tests/benchmark evaluation material.
