# Olympiad AIMO3 Adaptive Reasoner T4x2 — v2.6 Full Rewrite

This version replaces the repeated semantic-gate patches with a simpler adaptive pipeline.

## Main changes

- Easy problems: direct Qwen3-4B-Instruct solve first; no proposer/RAG/critic unless needed.
- Medium/Hard: proposer is used selectively.
- RAG is conditional and runs after a weak/incomplete/disagreeing first attempt.
- Qwen3-4B-Thinking critic is escalation-only.
- Solver output is section-based, not long JSON.
- `FINAL_ANSWER` must be the final line.
- Candidate answers are preserved even when not verified.
- Verification levels: NONE, FORMAT, CONSISTENCY, EXACT_TOOL, CRITIC.
- Exact algebra check tool `check_equalities` supports word problems such as AIMO3 Reference Problem 1.
- Qwen Thinking output has its own parser using `</think>`.
- Hard call/token/time budgets are actually enforced.
- Seed RAG rebuilds TF-IDF in the current sklearn runtime, eliminating cross-version pickle warnings.
- PDF remains a leakage-safe reference/debug adapter; CSV/text is preferred for competition input.

## Kaggle paths

Models:

```text
/kaggle/input/datasets/leminhhung0101/olympiad-offline-models/
├── deepseek-r1-distill-qwen-1.5b
├── qwen3-4b-instruct-2507
└── qwen3-4b-thinking-2507
```

Project after upload:

```text
/kaggle/input/datasets/leminhhung0101/olympiad-offline-models/Olympiad_AIMO3_Adaptive_Reasoner_T4x2_v2_6_FULL_REWRITE
```

## Kaggle setup

```python
!pip install -q \
    --no-index \
    --find-links=/kaggle/input/datasets/leminhhung0101/arc-qlora-offline-wheels \
    "transformers==4.55.4" \
    "peft==0.17.1" \
    "accelerate==1.10.1" \
    "bitsandbytes==0.50.1"
```

If PyMuPDF is not preinstalled:

```python
!pip install -q PyMuPDF
```

Copy project to writable storage:

```bash
!rm -rf /kaggle/working/AIMO3_V26
!cp -a \
"/kaggle/input/datasets/leminhhung0101/olympiad-offline-models/Olympiad_AIMO3_Adaptive_Reasoner_T4x2_v2_6_FULL_REWRITE" \
"/kaggle/working/AIMO3_V26"
```

```python
%cd /kaggle/working/AIMO3_V26
```

Environment:

```python
import os
os.environ["CUDA_VISIBLE_DEVICES"]="0,1"
os.environ["HF_HUB_OFFLINE"]="1"
os.environ["TRANSFORMERS_OFFLINE"]="1"
os.environ["TOKENIZERS_PARALLELISM"]="false"
os.environ["PYTORCH_CUDA_ALLOC_CONF"]="expandable_segments:True"
```

## Tests

```bash
!python scripts/preflight_v26.py
!python tests/test_parsing.py
!python tests/test_tools.py
!python tests/test_budget.py
!python tests/test_rag_runtime.py
!python tests/test_pipeline_problem1_mock.py
```

PDF test:

```python
from pathlib import Path
PDF=str(next(Path('/kaggle/input').rglob('AIMO3_Reference_Problems.pdf')))
print(PDF)
```

```bash
!AIMO_REFERENCE_PDF="$PDF" python tests/test_pdf_reader.py
```

## Run AIMO3 Reference Problem 1

```bash
!python run_pdf_pipeline.py \
    --input "$PDF" \
    --problem-number 1 \
    --benchmark-reference \
    --preload \
    --config config_v2_6.yaml
```

Expected fields in the result JSON:

```text
candidate_answer
verified_answer
verification.level
status
metrics.calls[*].raw_output
metrics.calls[*].truncated
metrics.calls[*].finish_reason
```

A correct exact-tool path for Problem 1 should ideally end with:

```text
candidate_answer = 50
verified_answer = 50
verification.level = EXACT_TOOL
status = VERIFIED_PASS
```

## Output policy

`candidate_answer` is never deleted merely because verification failed.

Examples:

```json
{"candidate_answer":50,"verified_answer":50,"status":"VERIFIED_PASS"}
```

or

```json
{"candidate_answer":50,"verified_answer":null,"status":"CANDIDATE_ONLY"}
```

This is important for research because reasoning accuracy and verifier accuracy can be measured separately.

## v2.6.3 Constraint-First update

The real Kaggle Problem 1 log showed three solver calls, all truncated, with no integer candidate. The first call spent nearly all output tokens repeatedly reinterpreting the word problem, then REC1 and RAG1 repeated the failure and exhausted the easy call budget before the critic could run.

v2.6.3 adds a short constraint-first route for short relational algebra word problems:

1. `formalize_constraints` (Qwen solver, <=420 new tokens, JSON only)
2. `solve_CF1` from the extracted constraints (<=950 new tokens)
3. exact-tool evidence
4. critic only if needed
5. `CF2` is reserved only if the first constrained solve still fails

RAG is intentionally skipped on this easy route because retrieval did not address the semantic/truncation failure observed in the real run.

Run with:

```bash
python run_pdf_pipeline.py \
  --input "$PDF" \
  --problem-number 1 \
  --benchmark-reference \
  --preload \
  --config config_v2_6_3.yaml
```
