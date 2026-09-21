# Final Architecture — v2.11.0

```text
Problem
  -> leakage-safe PDF math recovery
  -> target specification
  -> fine-grained family router
  -> deterministic family engine when structurally supported
       -> exact reduction
       -> independent certificate checks
       -> exact target normalization
       -> FAMILY_EXACT / VERIFIED_PASS
  -> otherwise adaptive neural path
       -> Instruct candidate
       -> conditional RAG
       -> proof obligations
       -> candidate repair / hard Thinking retry
       -> deterministic/tool checks
       -> final critic
```

Deterministic engines currently cover the reference-style families for P2–P10. P1 keeps the semantic compiler/SymPy route.

Knowledge RAG and experience memory remain conceptually separate; the packaged runtime seed RAG is still the local TF-IDF seed store, not the proposed full external V3 hybrid index.
