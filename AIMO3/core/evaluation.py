from __future__ import annotations

from .answer_contract import AIMO3AnswerContract


def benchmark_record(result: dict, expected_answer: int) -> dict:
    """Post-hoc benchmark comparison. Expected answer must never enter the solver pipeline."""
    candidate = AIMO3AnswerContract.check(result.get("candidate_answer"))
    verified = AIMO3AnswerContract.check(result.get("verified_answer"))
    candidate_correct = bool(candidate.valid and candidate.value == int(expected_answer))
    verified_correct = bool(verified.valid and verified.value == int(expected_answer))
    runtime_verified = bool(result.get("metrics", {}).get("verified_pass", False))
    return {
        "expected_answer": int(expected_answer),
        "candidate_answer": candidate.value,
        "candidate_correct": candidate_correct,
        "verified_answer": verified.value,
        "verified_correct": verified_correct,
        "runtime_verified": runtime_verified,
        "verification_false_positive": bool(runtime_verified and not verified_correct),
        "candidate_correct_but_unverified": bool(candidate_correct and not runtime_verified),
        "answer_was_not_exposed_to_model": True,
    }
