# Olympiad AIMO3 Adaptive Reasoner

A hybrid mathematical reasoning system for advanced Olympiad-style problems.

The project combines **small and medium open-weight language models**, **deterministic mathematical engines**, **retrieval**, **adaptive compute**, and **verification** to improve both reasoning accuracy and inference efficiency.

> **Current release:** `v2.11.0 — EXACT HARD FAMILIES`  
> **Primary platform:** Kaggle  
> **Target hardware:** 2 × NVIDIA Tesla T4  
> **Execution mode:** Offline inference

---

## Table of Contents

- [1. Project Goal](#1-project-goal)
- [2. Main Idea](#2-main-idea)
- [3. System Architecture](#3-system-architecture)
- [4. Models](#4-models)
- [5. Hardware and Runtime](#5-hardware-and-runtime)
- [6. Math Fidelity](#6-math-fidelity)
- [7. Fine-Grained Problem Routing](#7-fine-grained-problem-routing)
- [8. Deterministic Exact Engines](#8-deterministic-exact-engines)
- [9. Semantic Compiler](#9-semantic-compiler)
- [10. Retrieval-Augmented Reasoning](#10-retrieval-augmented-reasoning)
- [11. Adaptive Compute](#11-adaptive-compute)
- [12. Candidate Verification](#12-candidate-verification)
- [13. AIMO3 Reference Coverage](#13-aimo3-reference-coverage)
- [14. Development Lessons](#14-development-lessons)
- [15. Installation](#15-installation)
- [16. Running the Project](#16-running-the-project)
- [17. Output and Metrics](#17-output-and-metrics)
- [18. Research Evaluation](#18-research-evaluation)
- [19. Limitations](#19-limitations)
- [20. Future Work](#20-future-work)

---

## 1. Project Goal

The central research question is:

> **Can a smaller open-weight language model become competitive with a larger model when reasoning is supported by structured routing, exact tools, retrieval, verification, and adaptive computation?**

The working hypothesis is:

```text
Accuracy(adaptive hybrid) >= Accuracy(fixed reasoning)
Compute(adaptive hybrid)  < Compute(fixed reasoning)
```

A stronger long-term target is:

```text
4B adaptive system > 7B standard reasoning
with lower inference cost
```

The project therefore focuses on **reasoning-system design**, not only model scaling.

---

## 2. Main Idea

A language model should not be forced to solve every mathematical problem from beginning to end.

Different components should handle different responsibilities:

| Component | Responsibility |
|---|---|
| LLM | Understand the statement, identify structure, propose strategies |
| Router | Select the mathematical family and solver |
| RAG | Retrieve relevant theorems and strategy patterns |
| SymPy / Python | Perform exact symbolic or numerical computation |
| Family engine | Solve supported mathematical structures deterministically |
| Proof checker | Verify required mathematical obligations |
| Critic | Detect remaining logical inconsistencies |
| Target validator | Check answer format and modulus constraints |

The main design principle is:

> **Use language models where language and strategy matter. Use exact computation where mathematics can be computed exactly.**

---

## 3. System Architecture

```text
                         INPUT PROBLEM
                              |
                              v
                   +----------------------+
                   |   Math Fidelity      |
                   |   / Input Recovery   |
                   +----------------------+
                              |
                              v
                   +----------------------+
                   |   Problem Analysis   |
                   +----------------------+
                              |
                              v
                   +----------------------+
                   | Fine-Grained Router  |
                   +----------------------+
                              |
               +--------------+--------------+
               |                             |
               v                             v
      Exact engine available?               No exact engine
               |                             |
              YES                            v
               |                    +------------------+
               v                    | RAG + LLM Solver |
      +------------------+          +------------------+
      | Exact Reduction  |                   |
      +------------------+                   v
               |                    Candidate Generation
               v                             |
      +------------------+                   v
      | Exact Certificate|          Proof Obligations
      +------------------+                   |
               |                             v
               v                      Repair / Thinking
      Target Normalization                    |
               |                             v
               v                         Verification
         VERIFIED_PASS                        |
                                              v
                                            Critic
```

The system is **fail-closed**. If a result cannot be certified, it is not marked as verified.

---

## 4. Models

### 4.1 Lightweight Proposer

```text
deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B
```

Typical responsibilities:

- inexpensive problem decomposition;
- initial strategy proposals;
- lightweight candidate generation;
- optional fallback support.

### 4.2 Main Solver / Reviser

```text
Qwen/Qwen3-4B-Instruct-2507
```

Responsibilities:

- structured mathematical solving;
- semantic compilation;
- answer commitment;
- proof repair;
- focused micro-proofs;
- final response formatting.

Recommended decoding:

```text
temperature = 0.7
top_p       = 0.8
top_k       = 20
```

### 4.3 Thinking Critic / Deep Reasoner

```text
Qwen/Qwen3-4B-Thinking-2507
```

Responsibilities:

- difficult reasoning;
- deep fallback;
- candidate critique;
- contradiction detection;
- high-cost reasoning only when necessary.

Recommended decoding:

```text
temperature = 0.6
top_p       = 0.95
top_k       = 20
```

---

## 5. Hardware and Runtime

### Target Hardware

```text
2 × NVIDIA Tesla T4
```

Recommended device mapping:

```text
GPU 0
  - DeepSeek-R1-Distill-Qwen-1.5B
  - Qwen3-4B-Instruct-2507

GPU 1
  - Qwen3-4B-Thinking-2507

CPU
  - PDF processing
  - RAG
  - SymPy
  - exact arithmetic
  - deterministic family engines
  - verification utilities
```

Models can be loaded with 4-bit NF4 quantization to reduce VRAM usage.

### Offline Environment

```python
import os

os.environ["CUDA_VISIBLE_DEVICES"] = "0,1"
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
```

Example offline installation:

```bash
pip install -q   --no-index   --find-links=/kaggle/input/datasets/leminhhung0101/arc-qlora-offline-wheels   "transformers==4.55.4"   "peft==0.17.1"   "accelerate==1.10.1"   "bitsandbytes==0.50.1"
```

---

## 6. Math Fidelity

Mathematical PDFs are difficult to parse reliably.

Common extraction failures include:

- superscripts becoming normal text;
- fractions being split across lines;
- summation limits being detached;
- square roots being malformed;
- piecewise expressions being reordered;
- Unicode symbols becoming corrupted;
- control characters appearing inside formulas.

The project therefore introduces a dedicated **Math Fidelity Layer**:

```text
PDF
 |
 v
Raw extracted text
 |
 v
Layout-aware math recovery
 |
 v
Normalized mathematical statement
 |
 v
Fidelity validation
 |
 v
Reasoning pipeline
```

If a critical formula cannot be recovered safely, the pipeline should **fail closed** instead of solving a corrupted problem.

This became particularly important for problems involving:

- nested fractions;
- sums over integers;
- high powers;
- piecewise definitions;
- geometric ratios;
- floor expressions.

---

## 7. Fine-Grained Problem Routing

Early versions used broad categories such as:

```text
number_theory
geometry
combinatorics
```

This was too coarse.

The current router uses method-level mathematical families:

```text
extremal_rectangle_partition
radical_axis_angle_bisector_triangle
shifted_multiplicative_function
binary_weighted_tournament
floor_sum_valuation
geometry_sequence_asymptotic
adaptive_digit_sum_dynamics
finite_correlation_polynomial
norwegian_divisor_asymptotic
```

Fine-grained routing improves:

- exact solver selection;
- theorem retrieval;
- prompt construction;
- proof obligations;
- difficulty estimation;
- compute allocation.

---

## 8. Deterministic Exact Engines

The current system contains multiple deterministic mathematical solvers.

A family engine is allowed to return an exact result only when it can also produce a valid certificate.

If the pattern is uncertain, the engine returns:

```text
supported = false
```

or:

```text
ok = false
```

and the problem falls back to the neural pipeline.

### 8.1 Extremal Rectangle Partition

Used for rectangular partition problems with pairwise-distinct perimeters.

Main checks:

- exact minimum-area bounds;
- global area upper bound;
- constructive strip arrangement;
- positive integer dimensions;
- board containment;
- no overlap;
- exact area coverage;
- distinct perimeters.

Exact certification requires:

```text
construction_count == proven_upper_bound
```

### 8.2 Exact Geometry

Used for the integer-sided triangle/circle configuration.

Let:

```text
a = BC
b = CA
c = AB
```

The geometry is reduced to:

```text
a^2 * b = (b + c)^2 * (b - c)
```

The engine checks:

- integer sides;
- triangle inequalities;
- acute triangle;
- `AB < AC`;
- exact geometry relation;
- minimum perimeter.

No floating-point geometry is required.

### 8.3 Shifted Multiplicative Function

For:

```text
f(m) + f(n) = f(m + n + mn)
```

use:

```text
g(n) = f(n - 1)
```

which gives:

```text
g(ab) = g(a) + g(b)
```

The engine then:

- represents the function using prime weights;
- converts restrictions into exact linear constraints;
- enumerates feasible assignments;
- evaluates the target exactly.

### 8.4 Binary Weighted Tournament

Designed for tournament structures with:

- `2^R` competitors;
- same-score pairing;
- binary round weights;
- history equivalence;
- combinatorial counting;
- prime valuations.

The solver uses exact combinatorial arithmetic and valuation formulas.

### 8.5 Floor-Sum Valuation

Used for floor-sum problems such as P6.

A key reduction is Hermite's identity:

```text
sum_{i=1..n} floor(x + (n-i)/n) = floor(n*x)
```

For the reference structure:

```text
f(n)
= sum_{j=1..n} j^1024 * floor(n/j)
= sum_{m=1..n} sigma_1024(m)
```

Therefore:

```text
f(N) - f(N-1) = sigma_1024(N)
```

The engine then applies:

- multiplicativity;
- prime factorization;
- exact 2-adic valuation;
- LTE when its conditions are verified;
- modular exponentiation.

### 8.6 Fibonacci / Geometry Asymptotic

Used for a geometry problem coupled with a Fibonacci sequence.

The solver combines:

- exact geometric reduction;
- Fibonacci identities;
- symbolic rational expressions;
- asymptotic analysis;
- exact algebraic-number simplification;
- modular arithmetic.

For the reference structure:

```text
a_n = F_(n+2) / F_(n-1)
```

The relevant subsequence is then analyzed exactly.

### 8.7 Adaptive Digit-Sum Dynamics

Used for variable-base digit-sum processes.

The exact reachable set from `n` is:

```text
{1, 2, ..., ceil(n/2)}
```

This gives:

```text
H(1) = 0

H(n) =
1 + max(H(r))
for 1 <= r <= ceil(n/2)
```

The exact closed form is:

```text
H(n) = ceil(log2(n))
```

For extremely large integers, the implementation uses exact integer operations such as `bit_length()` instead of floating-point logarithms.

### 8.8 Finite Correlation Polynomial

Used for finite-support integer sequence correlation.

Define:

```text
P_alpha(x) = sum alpha(t) * x^t
Q_beta(x)  = sum beta(t)  * x^(-t)
```

The shifted correlation condition becomes:

```text
P_alpha(x) * Q_beta(x) = x^k + x^l
```

The problem is therefore converted into polynomial divisibility:

```text
P(x) divides x^a * (x^b + 1)
```

The solver uses:

- Laurent-polynomial normalization;
- cyclotomic factorization;
- Euler totient bounds;
- finite exact enumeration;
- sign and monomial-shift counting.

### 8.9 Norwegian Divisor Asymptotic

Used for divisor-minimization problems with huge structured integers.

The engine performs:

- exact classification of candidate divisor triples;
- symbolic formulas for the minimum;
- modular small-factor transfer;
- factorization of manageable integers such as `1 + c`;
- exact floor stabilization;
- rational arithmetic with `Fraction`;
- final modular reduction.

The solver does not accept unproved approximations such as:

```text
f(M+c) ≈ M
```

as a certificate.

---

## 9. Semantic Compiler

Not every problem requires a hand-written family engine.

For suitable algebraic problems, the semantic compiler extracts:

```text
entities
variables
relations
equalities
constraints
target quantity
```

Pipeline:

```text
Natural-language statement
        |
        v
Semantic extraction
        |
        v
Deterministic validation
        |
        v
Equation compilation
        |
        v
SymPy exact solve
        |
        v
Certificate
```

A semantic answer is accepted only when the target is mathematically connected to the exact certificate.

---

## 10. Retrieval-Augmented Reasoning

The project distinguishes two different retrieval sources:

```text
Knowledge RAG != Experience Memory
```

### Knowledge RAG

Stores:

- theorem summaries;
- mathematical identities;
- proof strategies;
- analogous problems;
- formal mathematics resources.

### Experience Memory

Stores:

- previous reasoning trajectories;
- successful strategies;
- failed strategies;
- verification outcomes;
- compute cost;
- family-specific lessons.

These sources have different purposes and should not be mixed blindly.

### Current Runtime Retrieval

The lightweight runtime currently uses TF-IDF features.

Example health indicators:

```text
documents     : ~60
word features : ~3248
char features : ~10479
```

A larger planned retrieval stack may combine:

```text
Dense similarity
BM25
Domain agreement
Symbol agreement
Source quality
Contradiction signals
```

Example future hybrid score:

```text
0.45 * dense
+ 0.30 * BM25
+ 0.15 * domain
+ 0.10 * symbol
```

---

## 11. Adaptive Compute

The system does not allocate the same inference budget to every problem.

Typical behavior:

```text
Exact-supported problem
    -> deterministic engine
    -> 0 model calls

Moderate problem
    -> short Instruct solve
    -> verification

Hard unsupported problem
    -> RAG
    -> Instruct
    -> focused proof repair
    -> Thinking model
    -> critic
```

The goal is to spend expensive GPU compute only where it is useful.

---

## 12. Candidate Verification

A model-generated answer is not automatically trusted.

Candidate lifecycle:

```text
Candidate
   |
   v
Target validation
   |
   v
Proof obligations
   |
   v
Exact / tool checks
   |
   v
Critic
   |
   v
Final verification
```

Possible statuses:

```text
CANDIDATE_ONLY
REFUTED
UNRESOLVED
VERIFIED_PASS
```

### Early Candidate Commit

A model can emit:

```text
[COMMIT]
CANDIDATE_ANSWER: 520
```

before finishing the explanation.

This protects a candidate from generation truncation.

However:

> **Early commitment preserves an answer candidate. It does not verify it.**

### Refutation and Repair

If a proof obligation refutes a candidate:

```text
candidate_refuted = true
```

that candidate can no longer be promoted to a verified answer.

A suggested correction from a checker is treated only as a new hypothesis and must pass the full validation pipeline again.

### Thinking Output Safety

Incomplete Thinking output is not accepted.

Example invalid state:

```text
TRUNCATED_THINKING
thinking_closed = false
parse_ok = false
```

A critic must expose a complete final verdict before the pipeline can use it.

---

## 13. AIMO3 Reference Coverage

| Problem | Main Route | Reference Answer |
|---|---|---:|
| P1 | Semantic compiler + SymPy | 50 |
| P2 | Extremal rectangle partition | 520 |
| P3 | Exact geometry | 336 |
| P4 | Shifted multiplicative function | 580 |
| P5 | Binary weighted tournament | 21818 |
| P6 | Floor-sum valuation | 32951 |
| P7 | Geometry + Fibonacci asymptotic | 57447 |
| P8 | Adaptive digit-sum dynamics | 32193 |
| P9 | Finite correlation polynomial | 160 |
| P10 | Norwegian divisor asymptotic | 8687 |

For a successful deterministic route:

```text
status                     = VERIFIED_PASS
verification               = FAMILY_EXACT
deterministic_family_solve = true
model_calls                = 0
```

---

## 14. Development Lessons

### 14.1 Input Fidelity Is Part of Reasoning

A model cannot solve the correct problem if the mathematical statement is corrupted before inference.

### 14.2 Fine-Grained Routing Matters

A label such as `number_theory` is often too broad.

The system performs better when routing identifies the actual mathematical mechanism.

### 14.3 More Tokens Do Not Automatically Mean Better Reasoning

Increasing generation length alone often caused:

- longer hallucinations;
- repeated assumptions;
- truncated reasoning;
- increased latency.

Structured reasoning was more valuable than simply increasing token budgets.

### 14.4 Verification Must Be Independent

A second language model agreeing with the first model is not a formal certificate.

Preferred structure:

```text
candidate
-> exact evidence
-> deterministic certificate
-> optional critic
```

### 14.5 Fail-Closed Behavior Is Important

An unresolved answer is safer than an incorrect answer marked as verified.

Earlier versions correctly rejected incorrect candidates such as:

```text
P3  -> 2002
P6  -> 0
P9  -> 36
P10 -> 7
```

rather than converting them into false `VERIFIED_PASS` results.

### 14.6 Exact Tools Can Reduce Compute

When a problem can be reduced to:

```text
symbolic algebra
finite enumeration
dynamic programming
modular arithmetic
valuation
polynomial factorization
```

a deterministic solver can be both more reliable and cheaper than long free-form language-model reasoning.

---

## 15. Installation

### Expected Kaggle Model Root

```text
/kaggle/input/datasets/leminhhung0101/olympiad-offline-models
```

Expected model directories:

```text
deepseek-r1-distill-qwen-1.5b/
qwen3-4b-instruct-2507/
qwen3-4b-thinking-2507/
```

### Copy the Project to Working Storage

```bash
rm -rf /kaggle/working/AIMO3_V2110

cp -a "/kaggle/input/datasets/leminhhung0101/olympiad-offline-models/Olympiad_AIMO3_Adaptive_Reasoner_T4x2_v2_11_0_EXACT_HARD_FAMILIES" "/kaggle/working/AIMO3_V2110"

cd /kaggle/working/AIMO3_V2110
```

In a Kaggle notebook, prefix shell commands with `!` when needed.

---

## 16. Running the Project

### 16.1 Find the Reference PDF

```python
from pathlib import Path

PDF = str(
    next(
        Path("/kaggle/input").rglob("AIMO3_Reference_Problems.pdf")
    )
)

print(PDF)
```

### 16.2 Run Preflight

```bash
python scripts/preflight_v211.py --pdf "$PDF"
```

Expected final message:

```text
v2.11.0 PREFLIGHT PASS
```

### 16.3 Run All Exact Engines

```bash
python run_pdf_pipeline.py   --input "$PDF"   --all   --benchmark-reference   --engine-only   --config config_v2_11_0.yaml
```

### 16.4 Run the Full 10-Problem Pipeline

```bash
python run_pdf_pipeline.py   --input "$PDF"   --all   --benchmark-reference   --preload   --config config_v2_11_0.yaml
```

### 16.5 Run a Single Problem

```bash
python run_pdf_pipeline.py   --input "$PDF"   --problem-number 8   --benchmark-reference   --config config_v2_11_0.yaml
```

### 16.6 Run a Single Exact Engine

```bash
python run_pdf_pipeline.py   --input "$PDF"   --problem-number 9   --benchmark-reference   --engine-only   --config config_v2_11_0.yaml
```

---

## 17. Output and Metrics

Result JSON files may contain:

```text
problem_id
problem
analysis
target_spec
difficulty
budget
rag
family_engine
candidates
proof_completion
critic
verification
candidate_answer
verified_answer
metrics
benchmark
```

Important metrics include:

```text
model_calls
input_tokens
output_tokens
total_tokens
latency_sec
solver_truncations
verification_level
deterministic_family_solve
family_engine_name
```

These diagnostics support:

- debugging;
- ablation studies;
- efficiency analysis;
- paper tables;
- failure analysis.

---

## 18. Research Evaluation

A strong scientific evaluation should compare the adaptive system with fixed-compute baselines.

| Method | Accuracy | Verified Accuracy | Avg. Calls | Avg. Tokens | Avg. Latency | Exact Coverage |
|---|---:|---:|---:|---:|---:|---:|
| 4B Fixed Reasoning | TBD | TBD | TBD | TBD | TBD | 0% |
| 4B + RAG | TBD | TBD | TBD | TBD | TBD | 0% |
| 4B + Tools | TBD | TBD | TBD | TBD | TBD | TBD |
| 4B Adaptive Hybrid | TBD | TBD | TBD | TBD | TBD | TBD |
| 7B Fixed Reasoning | TBD | TBD | TBD | TBD | TBD | 0% |

Recommended metrics:

```text
Accuracy
Verified Accuracy
False Verification Rate
Average Model Calls
Input Tokens
Output Tokens
Total Tokens
Wall-Clock Latency
GPU Inference Time
Exact-Solver Coverage
```

Recommended ablations:

```text
No RAG
No Exact Engines
No Critic
No Adaptive Compute
No Math Recovery
Solver Only
Thinking Only
```

---

## 19. Limitations

The AIMO3 reference problems were actively used during development.

Therefore:

> **10/10 on the reference set should be interpreted as engineering validation, not as an unbiased estimate of generalization performance.**

Several exact engines were developed after studying failures on these problems.

A scientifically stronger evaluation should:

```text
1. Freeze the v2.11 architecture.
2. Stop adding benchmark-specific fixes.
3. Evaluate on unseen Olympiad problems.
4. Compare against fixed-compute baselines.
5. Report both accuracy and compute.
```

The current version should therefore be treated as a **proof of concept for hybrid adaptive mathematical reasoning**.

---

## 20. Future Work

### Generalized Exact Solvers

Develop reusable engines such as:

```text
general floor-sum compiler
generic valuation engine
automatic recurrence solver
general polynomial divisibility engine
geometry coordinate compiler
integer-programming extremal solver
```

### Learned Router

Learn:

```text
P(problem family | problem)
P(exact solver applicable | problem)
```

instead of relying only on rules.

### Learned Retrieval Gate

Possible features:

```text
retrieval score
score margin
domain agreement
symbol overlap
dense/BM25 agreement
source quality
contradiction signals
```

### Experience Memory

Store:

```text
problem family
strategy
success/failure
verification outcome
compute cost
failure type
```

### Formal Verification

Potential integrations:

```text
Lean
SMT solvers
proof-producing symbolic solvers
formal algebra systems
```

### Unseen Benchmark Evaluation

Highest-priority next experiment:

```text
freeze v2.11
-> evaluate unseen problems
-> compare with fixed reasoning
-> measure accuracy and compute
```

---

## Reproducibility Principles

1. Keep inference offline whenever possible.
2. Use fixed model checkpoints.
3. Record decoding parameters.
4. Save structured JSON diagnostics.
5. Prefer exact arithmetic over unnecessary floating-point computation.
6. Use deterministic tools whenever possible.
7. Do not expose reference answers to the solver.
8. Do not hard-code benchmark answers into runtime logic.
9. Preserve failed verification as failed.
10. Never accept incomplete Thinking output as a valid verdict.

---

## Final Research Conclusion

The project evolved from a conventional LLM solver into a hybrid mathematical reasoning system.

The main conclusion is:

> **Mathematical reasoning performance depends on the architecture around the language model, not only on the size of the model itself.**

A strong system can combine:

```text
language understanding
+ strategy selection
+ retrieval
+ symbolic computation
+ exact algorithms
+ adaptive inference
+ independent verification
```

to obtain more reliable results with less unnecessary model computation.

The long-term research question is:

> **How far can small and medium open-weight language models be pushed when mathematical reasoning is treated as a complete system-design problem rather than only a model-scaling problem?**

---

## Current Project Status

```text
Version          : v2.11.0 EXACT HARD FAMILIES
Platform         : Kaggle
Target Hardware  : 2 × NVIDIA Tesla T4
Main Solver      : Qwen3-4B-Instruct-2507
Thinking Critic  : Qwen3-4B-Thinking-2507
Light Proposer   : DeepSeek-R1-Distill-Qwen-1.5B
Runtime          : Offline
Benchmark        : AIMO3 Reference Problems
```

---

## Acknowledgements

This project builds on ideas from:

- Retrieval-Augmented Generation;
- symbolic mathematical computation;
- adaptive inference;
- verifier-based reasoning;
- Olympiad problem-solving systems;
- the AIMO benchmark ecosystem;
- Qwen;
- DeepSeek;
- Hugging Face Transformers;
- SymPy.

Please review the licenses of all models, datasets, and dependencies separately before redistribution or commercial use.

---

## Disclaimer

This repository is a research prototype.

Correct performance on the AIMO3 reference benchmark does not by itself establish general mathematical intelligence or unbiased benchmark performance.

The project is intended for:

- research;
- experimentation;
- reproducibility studies;
- mathematical reasoning architecture evaluation.
