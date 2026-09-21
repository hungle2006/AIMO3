# Refinement plan — v2.7.1 Commit + Verify

## Failure observed in the real v2.7.0 Problem 2 run

v2.7.0 fixed the PDF fidelity bug and correctly routed the problem to `extremal_partition`, but it still spent four model calls writing long proofs:

- initial Instruct solve hit its output cap,
- recovery hit its output cap,
- Thinking deep solve consumed a long hidden chain and hit its cap,
- the Instruct finisher restarted the derivation and hit its cap again.

The result had no parseable candidate despite substantial useful mathematical progress. The core failure was therefore **late answer commitment + whole-proof regeneration**, not PDF parsing.

## v2.7.1 design

```text
Problem
  ↓
Family router + difficulty envelope
  ↓
Short Instruct solve
  ↓
EARLY COMMIT: CANDIDATE_ANSWER
  ↓
candidate exists?
 ┌───────────────┴───────────────┐
 YES                              NO
  ↓                                ↓
RAG retrieval only          short candidate recovery
  ↓                                ↓
proof-obligation audit       candidate exists?
  ↓                                ↓ NO
fill only missing proof       focused Thinking candidate search
obligations                        ↓
  ↓                           tiny Instruct candidate finisher
assemble review candidate          ↓
  ↓                           proof-obligation audit
final critic
  ↓
VERIFIED_PASS / CANDIDATE_ONLY
```

### 1. Early answer commitment

The solver protocol now asks for `CANDIDATE_ANSWER` near the beginning. A truncated generation can therefore preserve the candidate instead of collapsing to `None`.

An early commitment is **not verification**. `protocol_complete=False` until a complete final response or deterministic assembly exists.

### 2. Proof obligations by problem family

The controller decomposes proof completeness into family-specific obligations.

Examples:

- `extremal_partition`: `upper_bound`, `construction`, `arithmetic_check`
- `functional_equation`: `structural_transform`, `solution_class`, `bounded_constraints`, `target_count`
- `euclidean_geometry`: `exact_geometry_relation`, `configuration_conditions`, `integer_extremum`
- `combinatorial_process`: `state_invariant`, `counting_formula`, `valuation_or_final_count`

A missing construction no longer causes the entire problem to be re-solved. The next call asks only for the construction.

### 3. Focused micro-proof calls

Micro calls are capped and target one missing obligation. They output:

```text
OBLIGATION: construction
STATUS: PROVED|REFUTED|UNRESOLVED
EVIDENCE: ...
CANDIDATE_VALID: YES|NO|UNKNOWN
CORRECTED_CANDIDATE: <integer or UNKNOWN>
```

A focused call may refute a candidate, but corrections become a **new candidate** rather than silently overwriting the old answer.

### 4. Thinking model is no longer a default full-proof writer

When no candidate exists, Qwen Thinking is asked only to discover a defensible candidate. If one proof obligation remains, it may be used once on that obligation.

If the focused Thinking call fails to close `</think>`, a small Instruct finisher receives only that obligation and the unfinished reasoning tail.

### 5. RAG context de-noising

If the top retrieval hit dominates the second hit by at least the configured margin, only top-1 context is injected. This prevents a strong extremal-tiling hint from being diluted by lower-ranked geometry/process patterns.

RAG remains retrieval-only in the weak/incomplete path: v2.7.1 does not spend a whole model call on a generic `RAG1` re-solve.

### 6. Conservative verification remains

- Early committed answers cannot auto-pass.
- Incomplete/truncated candidates cannot receive critic verification.
- Failed exact tool checks still hard-block a PASS.
- Semantic exact verification for the supported relational-algebra compiler remains unchanged.
- An assembled candidate only becomes reviewable after all required obligations have evidence; the final critic still decides mathematical validity.

## Compute policy

Default v2.7.1 caps are intentionally smaller than the failed v2.7.0 run:

- Solver: 850 output tokens
- Candidate recovery: 280
- Focused proof: 420
- Focused Thinking candidate: 1300
- Focused Thinking obligation: 900
- Candidate finisher: 240
- Critic: 1400

The objective is **more calls with narrow jobs, fewer tokens spent rewriting the same derivation**.

## What is verified in the build environment

CPU/unit tests cover:

- early-commit parsing and conservative verification,
- commit survival under truncation,
- focused proof-obligation routing,
- RAG top-hit dominance filtering,
- deep candidate fallback,
- semantic-compiler verification guards,
- existing PDF math-fidelity regression tests.

Real T4x2 inference for v2.7.1 is **not claimed verified** until it is run on Kaggle. The next recommended smoke test is Problem 2, followed by Problems 4, 5, and 3.
