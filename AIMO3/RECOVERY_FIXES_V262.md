# v2.6.2 Recovery Patch

Observed Kaggle failure:
- models loaded successfully on T4x2;
- solver produced no parseable candidate answer;
- result became UNRESOLVED / verification NONE;
- Transformers emitted sampling-flag warnings.

Fixes:
1. Per-call private GenerationConfig prevents checkpoint sampling parameters from
   conflicting with deterministic calls.
2. Qwen3-4B-Instruct-2507 solver now uses its checkpoint-style sampling defaults:
   temperature=0.7, top_p=0.8, top_k=20.
3. Solver output is shortened (1100 tokens default) to improve chance of reaching
   the final marker within time budget.
4. Candidate parser accepts boxed/final-answer fallback forms without pretending
   the protocol is complete.
5. If the first solver attempt has no integer answer, a short rescue solve runs
   BEFORE RAG.
6. Metrics explicitly record answer recovery, candidate answers, and parse modes.
7. Verification safeguards from v2.6.1 remain unchanged: fallback candidates are
   not automatically VERIFIED.
