# v2.6 Architecture

```text
Problem
  ↓
Light Analyzer + Difficulty
  ↓
┌──────────────── EASY ────────────────┐
│ Qwen4B Instruct: interpret+solve     │
└──────────────────┬───────────────────┘
                   ↓
            Solver Parser
                   ↓
       Deterministic Verification
                   ↓
          exact PASS? ── yes → STOP
                   │ no
                   ↓
       conditional RAG if weak
                   ↓
          optional retry
                   ↓
        Qwen4B Thinking Critic
                   ↓
       PASS → STOP / REVISE once
```

Medium/Hard adds the 1.5B proposer before solver; hard can run two initial solver attempts.

## GPU placement

- GPU0: DeepSeek 1.5B proposer + Qwen3-4B-Instruct solver
- GPU1: Qwen3-4B-Thinking critic
- CPU: analyzer, seed RAG, SymPy/exact tools, PDF parser

## Reliability principles

1. Do not force an answer before reasoning ends.
2. Do not parse critic hidden thinking as final output.
3. Preserve candidate answers separately from verified answers.
4. A failed exact check blocks verification.
5. RAG and critic are escalation tools, not mandatory stages.
6. Compute budgets are hard limits, not documentation-only settings.
