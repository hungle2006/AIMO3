# v2.6.4 — Semantic Compiler + Exact Algebra

## Root cause proven by the real Kaggle run

v2.6.3 succeeded syntactically but failed semantically. The formalizer emitted a JSON object that parsed correctly, yet the post-transfer equations were wrong. The solver then spent two 950-token calls trying to solve a poisoned system and both generations hit the length limit.

## Architectural correction

v2.6.4 no longer asks the 4B model to write post-event equations directly.

The semantic model now outputs:

- entities
- owner/kind variables
- pre-event relation types and factors
- transfer events
- post-event equality types
- structured goal

A deterministic semantic compiler then constructs the equations.

For a transfer event `Alice -> Bob, amount=5, asset=sweets`, the compiler itself applies:

- Alice sweets: `a -> a-5`
- Bob sweets: `b -> b+5`

so the model cannot accidentally forget the receiver's `+5` or multiply the wrong operands.

## Deterministic guards

The compiler checks:

1. owner/kind variable mapping;
2. transfer direction/amount against high-confidence text patterns;
3. lexical relation factors (`double`, `four times`, `sum and product equal`);
4. conservation of the transferred asset;
5. supported relation structure;
6. exact integer solution with SymPy;
7. answer-bound equality certificate.

If semantic validation fails, the formalization is repaired once before any reasoning call.

## Efficient path for supported word problems

```text
Problem
  -> short structured semantic extraction (LLM)
  -> deterministic semantic validation/compiler
  -> exact SymPy solve
  -> answer-bound certificate
  -> SEMANTIC_EXACT
```

For AIMO3 reference Problem 1, the deterministic compiler produces:

```text
(x+a) = 2*(y+b)
(x*a) = 4*(y*b)
x+(a-5) = y+(b+5)
x*(a-5) = y*(b+5)
```

and SymPy gives the unique positive-integer solution:

```text
a=10, b=5, x=10, y=5
answer = x*y = 50
```

## Fallback

If the semantic template is valid but symbolic solving cannot settle the problem, Qwen solves only the compiled equations. If the semantic template itself is rejected after one repair, the pipeline falls back to direct reasoning instead of repeatedly solving invalid equations.
