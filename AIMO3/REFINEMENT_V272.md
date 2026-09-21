# Refinement v2.7.2

## Real failure observed in v2.7.1

The P2 run showed that output-preservation worked, but the preserved answer was wrong for a new reason:

1. Solver copied the modulus `10^5` and committed `100000`.
2. The AIMO global range rejected it, but proof-completion still treated it as a candidate anchor.
3. A construction micro-call refuted `100000` and suggested `1000`; another later suggested `707`.
4. The pipeline promoted a proof-side suggestion into the main candidate, producing `CANDIDATE_ONLY: 1000` instead of finding a fresh answer.

This is an orchestration error, not an input-fidelity error.

## v2.7.2 design

### Target grounding
Before model inference, derive a narrow target contract. For remainder questions, the target carries the modulus and legal range. Invalid commits are rejected before proof completion. The pipeline intentionally does **not** apply `% modulus` to arbitrary model guesses because that could conceal a semantic mistake.

### Refutation-safe candidate state machine
A focused proof call can return `REFUTED`, but any `CORRECTED_CANDIDATE` is only metadata. The old candidate is marked dead and a separate repair prompt must produce a new candidate. That candidate is target-validated, checked against previously rejected values, and then receives a fresh proof-obligation audit.

### Evidence-aware proof obligations
The pipeline no longer trusts the model's `DONE` declaration alone. Construction requires constructive/geometric evidence; upper bound requires actual bound evidence; arithmetic check requires concrete numeric/modular checking.

### Finalization guard
A candidate is finalizable only if it is an integer, satisfies the global AIMO contract, satisfies the problem target contract, and has not been refuted.

## Non-goals

This release does not hard-code P2's benchmark answer or official construction. It fixes generic failure classes: modulus copying, invalid early commits, correction drift, and proof-status hallucination.
