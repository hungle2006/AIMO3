from __future__ import annotations

import json


SOLVER_PROTOCOL = r"""
Use this exact compact protocol. The goal is to preserve useful progress without forcing a guess.

[KEY_REDUCTION]
At most 4 concise lines. State the decisive structure/invariant/reduction. Do not restate the problem.

[COMMIT]
After the compact reduction, commit ONLY if you have a defensible integer for the ACTUAL requested output.
This section should appear within roughly the first 350 generated tokens. Never copy a modulus, bound,
or conspicuous constant merely to fill this field. If the answer is a remainder, reduce the proved quantity first.
CANDIDATE_ANSWER: <integer>
If you do not yet have a defensible requested-output integer, write:
CANDIDATE_ANSWER: UNKNOWN

[OBLIGATIONS]
Return ONLY a compact JSON object mapping the required proof obligations named in the prompt to
"DONE", "PARTIAL", or "MISSING". This is self-assessment metadata only; the pipeline will independently
check whether substantive evidence exists.

[SOLUTION]
Give only the proof details needed to discharge the obligations. Do not repeat setup already stated.

[CHECK]
Check the decisive equations/cases and the proposed integer once. State any remaining risk.

[TOOL_REQUESTS]
Return a JSON array. Use [] if no exact check is useful.
For algebraic assignments, prefer an answer-bound certificate:
{"op":"check_equalities","assignments":{"x":1},"equalities":[{"lhs":"x+1","rhs":"2"}],"answer_expr":"x","expected_answer":1}
A true but unrelated identity does NOT verify the answer.

[CONFIDENCE]
A single number from 0 to 1.

[FINAL]
If the proof obligations are actually complete, the LAST non-empty line must be:
FINAL_ANSWER: <same integer as CANDIDATE_ANSWER>
If important proof obligations remain incomplete, use:
FINAL_ANSWER: UNKNOWN

Never change a committed answer silently. If later reasoning refutes it, explicitly state the correction in
[SOLUTION] and make FINAL_ANSWER the corrected integer; the parser will flag any conflict for review.
"""


def direct_solver_prompt(problem: str, analysis: dict, rag_context: str = "") -> str:
    context = rag_context.strip() or "RAG_STATUS: NOT_USED"
    return f"""You are the main solver for an AIMO/olympiad mathematics problem.
Solve the exact problem stated by the user. Do not rely on unstated assumptions.
For an answer-only problem, the final answer must be an integer when the problem determines one.
A computational check can verify algebra/arithmetic but cannot replace a missing proof.

Problem domain hint: {analysis.get('domain','general')}
Problem family: {analysis.get('family','general')}
Requested-output contract: {analysis.get('target_instruction','Return the exact integer requested.')}
Family-specific reasoning hint: {analysis.get('family_hint','')}
Preserve every exponent, modulus, and numeric constant EXACTLY as written in the Problem.
Problem:
{problem}

Optional retrieved context (may be irrelevant; ignore it if it does not exactly fit):
{context}

Required proof obligations for this family: {analysis.get('proof_obligations', [])}

{SOLVER_PROTOCOL}
Keep visible reasoning under about 450 words. Spend tokens on the missing proof, not on restating the statement.
"""


def strategy_proposer_prompt(problem: str, analysis: dict, target_n: int = 3) -> str:
    return f"""Propose {target_n} distinct solution strategies for this olympiad problem.
Do NOT solve the problem and do NOT give a final answer.
Prefer mathematically different approaches, not paraphrases.
Return ONLY a JSON array. Each item must contain:
- id
- name
- core_idea
- why_it_fits
- risks
- confidence (0..1)

Domain hint: {analysis.get('domain','general')}
Problem:
{problem}
"""


def strategy_solver_prompt(
    problem: str,
    analysis: dict,
    strategy: dict,
    rag_context: str = "",
    attempt_label: str = "A",
) -> str:
    context = rag_context.strip() or "RAG_STATUS: NOT_USED"
    return f"""You are the main solver for an AIMO/olympiad mathematics problem.
Use the proposed strategy as a starting point, but abandon it if it is invalid.
This is attempt {attempt_label}.

Problem:
{problem}

Domain hint: {analysis.get('domain','general')}
Problem family: {analysis.get('family','general')}
Requested-output contract: {analysis.get('target_instruction','Return the exact integer requested.')}
Family-specific reasoning hint: {analysis.get('family_hint','')}
Preserve every exponent, modulus, and numeric constant EXACTLY as written in the Problem.
Proposed strategy:
{json.dumps(strategy, ensure_ascii=False)}

Optional retrieved context (may be wrong; use only when conditions match):
{context}

Required proof obligations for this family: {analysis.get('proof_obligations', [])}

{SOLVER_PROTOCOL}
Keep the proof concise and prioritize a committed candidate plus missing obligations.
"""


def rag_retry_prompt(
    problem: str,
    analysis: dict,
    previous: dict,
    rag_context: str,
) -> str:
    return f"""Re-solve the exact problem using the retrieved context only as a hint.
The previous candidate was not sufficiently verified. Correct it rather than defending it.

Problem:
{problem}

Previous interpretation / candidate answer:
{json.dumps({
    'interpretation': previous.get('interpretation',''),
    'candidate_answer': previous.get('candidate_answer'),
    'check': previous.get('check',''),
}, ensure_ascii=False)}

Retrieved context:
{rag_context or 'RAG_STATUS: NO_RELEVANT_CONTEXT'}

{SOLVER_PROTOCOL}
"""


def critic_prompt(problem: str, candidates: list[dict], tool_reports: dict) -> str:
    compact = []
    for c in candidates:
        compact.append({
            "id": c.get("id"),
            "interpretation": c.get("interpretation", "")[:1800],
            "proof": c.get("proof", "")[:5000],
            "check": c.get("check", "")[:1800],
            "candidate_answer": c.get("candidate_answer"),
            "target_valid": c.get("target_valid"),
            "target_spec": c.get("target_spec"),
            "self_confidence": c.get("self_confidence"),
            "protocol_complete": c.get("protocol_complete"),
            "ambiguity_detected": c.get("ambiguity_detected"),
            "required_obligations": c.get("required_obligations", []),
            "missing_obligations": c.get("missing_obligations", []),
            "obligation_evidence": c.get("obligation_evidence", {}),
        })

    return f"""You are the final mathematical critic. Internally reason as needed, but the FINAL RESPONSE
must be short. Judge whether one candidate completely solves the exact stated problem.
Check semantic interpretation, theorem conditions, missing cases, algebra, arithmetic, and final answer.
Treat ANY failed exact tool check on a candidate as disqualifying. A PASS is forbidden for a candidate
with ok=false or verified=false in its tool evidence. Also reject any candidate that violates its requested-output
contract (for example, a remainder equal to its modulus). Do not reward a candidate merely because two attempts agree.
A true calculation that is unrelated to the candidate answer is supporting evidence only, not certification.
For an assembled candidate, every required proof obligation must have substantive evidence. If a construction,
classification, extremal-attainment, geometry-condition, or counting-formula obligation is missing or hand-wavy,
do NOT PASS. Focus on the weakest obligation rather than re-solving the whole problem from scratch.

Problem:
{problem}

Candidates:
{json.dumps(compact, ensure_ascii=False)}

Exact tool reports:
{json.dumps(tool_reports, ensure_ascii=False)}

After thinking, output exactly these lines in the final answer portion:
VERDICT: PASS|REVISE|REJECT
CONFIDENCE: <0..1>
BEST_CANDIDATE: <candidate id or NONE>
ERROR: <one concise error or NONE>
REVISION: <one concise instruction or NONE>
"""


def revision_prompt(problem: str, candidate: dict, critic: dict, rag_context: str = "") -> str:
    return f"""Revise the candidate solution to fix the critic's specific error. Do not restart with a
new interpretation unless the critic identified an interpretation error.

Problem:
{problem}

Candidate:
{json.dumps({
    'interpretation': candidate.get('interpretation',''),
    'proof': candidate.get('proof',''),
    'check': candidate.get('check',''),
    'candidate_answer': candidate.get('candidate_answer'),
}, ensure_ascii=False)}

Critic feedback:
{json.dumps({
    'verdict': critic.get('verdict'),
    'error': critic.get('error'),
    'revision_instruction': critic.get('revision_instruction'),
}, ensure_ascii=False)}

Optional retrieved context:
{rag_context or 'RAG_STATUS: NOT_USED'}

{SOLVER_PROTOCOL}
"""


def rescue_solver_prompt(problem: str, previous_output: str, analysis: dict) -> str:
    """Candidate-discovery recovery: do not rewrite the full proof."""
    tail = (previous_output or "")[-5000:]
    return f"""The previous olympiad attempt ended before committing a usable integer answer.
Do NOT restart the proof and do NOT write a polished solution. Inspect the partial work, correct at most one
critical mistake, then determine the best current candidate.

Problem family: {analysis.get('family','general')}
Requested-output contract: {analysis.get('target_instruction','Return the exact integer requested.')}
Family hint: {analysis.get('family_hint','')}
Required proof obligations: {analysis.get('proof_obligations', [])}
Exact problem:
{problem}

Tail of previous attempt:
{tail}

Use at most about 180 words. Output exactly:
[KEY_REDUCTION]
<2-5 lines of decisive work>
[COMMIT]
CANDIDATE_ANSWER: <integer or UNKNOWN>
[CONFIDENCE]
<0..1>

Do not continue into a full proof. This call only discovers/repairs the candidate answer. If the target contract is not yet satisfied, return UNKNOWN rather than copying a modulus or bound.
"""


def obligation_proof_prompt(
    problem: str,
    analysis: dict,
    candidate_answer: int,
    obligation: str,
    obligation_description: str,
    existing_evidence: str = "",
    rag_context: str = "",
) -> str:
    return f"""Prove exactly ONE missing obligation for an olympiad candidate. Do not solve the whole problem again.
Do not restate the statement. Be concise and adversarial: if the committed candidate cannot satisfy this
obligation, say so and give a corrected candidate only if you can justify it.

Problem family: {analysis.get('family','general')}
Requested-output contract: {analysis.get('target_instruction','Return the exact integer requested.')}
Committed candidate: {candidate_answer}
Target obligation: {obligation}
What this obligation requires: {obligation_description}

Problem:
{problem}

Existing evidence (may be incomplete or wrong):
{existing_evidence[-4000:] if existing_evidence else 'NONE'}

Accepted retrieval context (use only if directly relevant):
{rag_context or 'RAG_STATUS: NOT_USED'}

Output exactly these fields, with EVIDENCE <= 220 words:
OBLIGATION: {obligation}
STATUS: PROVED|REFUTED|UNRESOLVED
EVIDENCE: <rigorous focused argument>
CANDIDATE_VALID: YES|NO|UNKNOWN
CORRECTED_CANDIDATE: <integer or UNKNOWN>

Important: CORRECTED_CANDIDATE is only a hypothesis for a later candidate-repair stage. It does NOT become the new answer merely because this one obligation suggests it.
"""


def candidate_only_deep_prompt(problem: str, analysis: dict, prior: str = "", rag_context: str = "") -> str:
    return f"""You are the deep-reasoning model. Find a defensible candidate integer for this olympiad problem.
This is NOT a polished proof request. Focus only on the decisive structure and candidate value.
After your internal thinking closes, the public final response must contain exactly:
CANDIDATE_ANSWER: <integer or UNKNOWN>
CONFIDENCE: <0..1>
KEY_REASON: <one sentence>

Problem family: {analysis.get('family','general')}
Requested-output contract: {analysis.get('target_instruction','Return the exact integer requested.')}
Family hint: {analysis.get('family_hint','')}
Problem:
{problem}

Prior progress (may be wrong):
{prior[-5000:] if prior else 'NONE'}

Accepted retrieval context:
{rag_context or 'RAG_STATUS: NOT_USED'}
"""


def deep_candidate_finish_prompt(problem: str, analysis: dict, thinking_tail: str) -> str:
    return f"""Extract the most defensible candidate integer from the unfinished deep reasoning below.
Do not restart the proof. Do not explain background. Use at most 100 words.

Requested-output contract: {analysis.get('target_instruction','Return the exact integer requested.')}
Problem:
{problem}

Reasoning tail:
{(thinking_tail or '')[-6000:]}

Output exactly:
[KEY_REDUCTION]
<1-3 concise lines>
[COMMIT]
CANDIDATE_ANSWER: <integer or UNKNOWN>
[CONFIDENCE]
<0..1>
"""


def assemble_candidate_prompt(candidate_answer: int, family: str, obligation_evidence: dict[str, str]) -> str:
    """Kept for diagnostics/tests; runtime assembly is deterministic."""
    return f"Candidate {candidate_answer}; family={family}; evidence={json.dumps(obligation_evidence, ensure_ascii=False)}"


def deep_thinking_solver_prompt(problem: str, analysis: dict, previous_outputs: list[str], rag_context: str = "") -> str:
    tails = []
    for i, out in enumerate(previous_outputs[-3:], 1):
        tails.append(f"--- attempt tail {i} ---\n{(out or '')[-3500:]}")
    prior = "\n".join(tails) if tails else "No prior attempt."
    return f"""Solve this olympiad problem carefully. You are the deep-reasoning escalation model.
Think internally as long as useful, but after your thinking closes, give a SHORT final response using the exact
sections below. Do not merely continue a bad argument: identify the decisive structure and solve it.

Problem family: {analysis.get('family','general')}
Requested-output contract: {analysis.get('target_instruction','Return the exact integer requested.')}
Family-specific hint: {analysis.get('family_hint','')}
Preserve every exponent, modulus, and numeric constant EXACTLY as written.

Problem:
{problem}

Previous attempt tails (may contain mistakes):
{prior}

Retrieved context (use only if clearly relevant):
{rag_context or 'RAG_STATUS: NOT_USED'}

Final response after thinking must be:
[SOLUTION]
<concise rigorous solution>

[CHECK]
<decisive checks>

[TOOL_REQUESTS]
<JSON array or []>

[CONFIDENCE]
<0..1>

[FINAL]
FINAL_ANSWER: <integer>
"""



def deep_finish_prompt(problem: str, analysis: dict, thinking_tail: str, rag_context: str = "") -> str:
    return f"""A deep reasoning attempt was cut off or did not emit a usable final answer.
Use the useful mathematical progress in its tail, correct any explicit contradiction, and FINISH the problem concisely.
Do not restart from the statement and do not repeat background.

Problem family: {analysis.get('family','general')}
Requested-output contract: {analysis.get('target_instruction','Return the exact integer requested.')}
Family hint: {analysis.get('family_hint','')}
Problem:
{problem}

Tail from the deep reasoning attempt:
{(thinking_tail or '')[-7000:]}

Accepted retrieval context (may be empty):
{rag_context or 'RAG_STATUS: NOT_USED'}

Output at most about 350 words and end with:
[CHECK]
<decisive check>

[TOOL_REQUESTS]
<JSON array or []>

[CONFIDENCE]
<0..1>

[FINAL]
FINAL_ANSWER: <integer>

If no defensible integer can be reached, use FINAL_ANSWER: UNKNOWN.
"""


def constraint_extractor_prompt(problem: str) -> str:
    """Extract semantic roles/events; equations are compiled deterministically later."""
    return f"""Extract ONLY the structured mathematical semantics of this short algebra word problem.
Do NOT solve it. Do NOT write equations. Do NOT narrate uncertainty or self-corrections.

Represent each person's quantities by owner and kind. Represent transfers as an EVENT, not as an equation.
If addition and multiplication are applied to the same two quantities, keep the same operands.
If after an event two people's sums and products are equal, list TWO post equalities.

Return ONLY one compact JSON object with exactly this schema:
{{
  "entities": ["Person1", "Person2"],
  "variables": [
    {{"name":"a","owner":"Person1","kind":"sweets","domain":"integer"}},
    {{"name":"x","owner":"Person1","kind":"age","domain":"positive integer"}}
  ],
  "pre_relations": [
    {{"type":"sum_ratio","left":"Person1","right":"Person2","factor":2,"operands":["age","sweets"]}},
    {{"type":"product_ratio","left":"Person1","right":"Person2","factor":4,"operands":["age","sweets"]}}
  ],
  "events": [
    {{"type":"transfer","asset":"sweets","amount":5,"from":"Person1","to":"Person2"}}
  ],
  "post_equalities": [
    {{"type":"sum_equal","left":"Person1","right":"Person2","operands":["age","sweets"]}},
    {{"type":"product_equal","left":"Person1","right":"Person2","operands":["age","sweets"]}}
  ],
  "goal": {{"type":"product","terms":["Person1.age","Person2.age"]}},
  "ambiguity": "NONE"
}}

Use the actual entity names and numbers from the problem.
If genuinely ambiguous, put a short explanation in ambiguity instead of NONE.

Problem:
{problem}
"""


def repair_semantic_formalization_prompt(problem: str, previous: dict, errors: list[dict]) -> str:
    return f"""Repair the structured semantics below. Do NOT solve the problem and do NOT write equations.
The deterministic validator found these issues:
{json.dumps(errors, ensure_ascii=False)}

Previous structure:
{json.dumps(previous, ensure_ascii=False)}

Problem:
{problem}

Return ONLY a corrected JSON object using the exact same schema as before.
Pay special attention to transfer direction, amount, conserved asset, owner/kind roles, and post-event equality types.
"""

def solve_from_constraints_prompt(problem: str, formalization: dict) -> str:
    """Solve from a compact formalization so the solver does not burn tokens reinterpreting prose."""
    return f"""Solve the olympiad problem from the extracted structure below.
Treat the extracted constraints as the working interpretation. Do NOT re-debate the English wording
unless the constraints are internally inconsistent. Do NOT narrate alternative readings.

Problem:
{problem}

Extracted structure:
{json.dumps(formalization, ensure_ascii=False)}

Use this compact protocol:

[SOLUTION]
Solve directly from the constraints. Keep the derivation concise.

[CHECK]
Check the decisive equations and the proposed final integer once.

[TOOL_REQUESTS]
Return a JSON array. Use [] if no exact check is useful.
For a concrete algebraic solution, prefer an answer-bound certificate such as:
{{"op":"check_equalities","assignments":{{"x":1}},
 "equalities":[{{"lhs":"x+1","rhs":"2"}}],
 "answer_expr":"x","expected_answer":1}}

[CONFIDENCE]
A single number from 0 to 1.

[FINAL]
The LAST non-empty line must be exactly one of:
FINAL_ANSWER: <integer>
FINAL_ANSWER: UNKNOWN

Keep the whole response under about 450 words and reach the final line before the token limit.
"""


def candidate_repair_after_refutation_prompt(
    problem: str,
    analysis: dict,
    rejected_candidate: int,
    refutation_evidence: str,
    rag_context: str = "",
) -> str:
    return f"""The current candidate was REFUTED by a focused proof check. Find a NEW defensible candidate
for the exact requested output. Do not defend the rejected value and do not write a full proof.

Problem family: {analysis.get('family','general')}
Requested-output contract: {analysis.get('target_instruction','Return the exact integer requested.')}
Rejected candidate: {rejected_candidate}

Problem:
{problem}

Refutation evidence:
{(refutation_evidence or '')[-5000:]}

Accepted retrieval context:
{rag_context or 'RAG_STATUS: NOT_USED'}

Use at most about 220 words. Output exactly:
[KEY_REDUCTION]
<2-5 decisive lines that address the refutation>
[COMMIT]
CANDIDATE_ANSWER: <integer or UNKNOWN>
[CONFIDENCE]
<0..1>

The candidate must satisfy the requested-output contract. Never output the modulus itself as a remainder.
"""
