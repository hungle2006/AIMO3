# v2.6.3 Constraint-First Fix

Root cause from the real Kaggle Problem 1 log:
- A, REC1 and RAG1 all returned no integer answer.
- all three solver calls were truncated.
- the critic never ran because the easy call budget was exhausted.
- the first solver output spent most of its generation repeatedly debating the meaning of “product”.

Changes:
1. Short relational algebra word problems first get a 420-token JSON constraint extraction.
2. The solver then works from those constraints and is explicitly told not to reinterpret the prose.
3. If the first constrained solve truncates, CF2 retries from the same compact formalization.
4. RAG is disabled for this easy constraint-first route; it does not repair semantic translation failures.
5. Self-correction language is treated as implicit ambiguity even when the AMBIGUITY marker is missing.
6. The easy envelope permits one reserve call, while the normal successful path still uses 3 calls.
