# Refinement v2.10.0

## Root cause addressed

The v2.9 full run exposed a new failure mode on hard reference problems: the PDF text layer could preserve ordinary prose while corrupting the decisive mathematical object (stacked ratios, floor delimiters, nested powers, and large operators). Once the target expression was malformed, the neural solver guessed from surface cues and focused proof calls correctly refuted those guesses, but the pipeline had no high-quality recovery path.

## New execution order

```text
Input
  ↓
Leakage-safe PDF statement extraction
  ↓
Math-fidelity recovery / audit
  ↓
Family router + target grounding
  ↓
Exact family engine available?
  ├─ yes → exact certificate → FAMILY_EXACT → stop
  └─ no  → Instruct → RAG when accepted → proof obligations
                                  ↓
                       candidate/repair refuted twice?
                                  ↓
                       hard-only full Thinking retry
                                  ↓
                      focused proof + final critic
```

## Safety invariants

- Expected benchmark answers never enter model context.
- PDF recovery is bounded to problem-statement text before `Answer:` / `Solution:`.
- Exact family engines must fail closed if any structural signal or certificate check is missing.
- A proof micro-call may refute a candidate but cannot directly promote its own proposed correction.
- Target-format validity does not imply mathematical validity.
- A candidate is not `VERIFIED_PASS` without an answer-bound exact certificate or final critic pass.

## P7-style exact path

For the matched incircle/Fibonacci family the engine establishes:

```text
geometry → target ratio = CT/CD
Fibonacci lengths → a_n = F_{n+2}/F_{n-1}
Binet / characteristic root → even subsequence tends to phi^3 from below
symbolic simplification → alpha = p + sqrt(q)
exact integer power + modulus → requested output
```

The final integer is computed at runtime from the symbolic certificate; it is not embedded as a benchmark answer.
