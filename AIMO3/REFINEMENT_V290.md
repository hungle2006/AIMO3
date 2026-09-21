# Refinement v2.9.0

The P3 failure in v2.8.1 was traced to a missing deterministic geometry engine. The family router was correct, PDF fidelity was correct, and target grounding was correct, but geometry fell back to LLM prose. The solver guessed familiar integer triangles, the focused verifier also made unsupported geometric assertions, candidate repair guessed again, and the Thinking critic truncated before producing a valid verdict.

v2.9.0 removes that failure mode for this structural family. Exact geometry is reduced to a rational side equation and integer search, with independent certificates. If any structural signal is absent, the engine reports unsupported; if the reduction is recognized but no unique exact minimum is certified, it reports supported-but-not-ok and the normal LLM pipeline remains available. No guessed candidate from the family engine is ever emitted.
