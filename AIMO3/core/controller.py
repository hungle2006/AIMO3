from __future__ import annotations

import re


def estimate_difficulty(problem: str, analysis: dict) -> float:
    """Cheap static estimate used only to select a compute envelope."""
    low = problem.lower()
    score = 0.20
    score += min(0.18, len(problem) / 3000.0)

    domain = analysis.get("domain", "general")
    if domain == "geometry":
        score += 0.10
    if any(k in low for k in [
        "functional equation", "diophantine", "valuation", "for all integers",
        "necessary and sufficient", "classify all", "prove that for every",
    ]):
        score += 0.16
    if any(k in low for k in [
        "factorial", "prime", "modulo", "remainder", "fibonacci",
        "invariant", "monovariant", "cyclotomic",
    ]):
        score += 0.08

    symbol_count = len(re.findall(r"[=<>≤≥∑∏√^]", problem))
    score += min(0.12, symbol_count * 0.008)

    # Short finite algebra word problems should stay cheap.
    simple_word = (
        domain == "algebra"
        and len(problem) < 1200
        and any(w in low for w in ["age", "sweets", "coins", "people", "integer number"])
        and any(w in low for w in ["sum", "product", "double", "times", "equal"])
        and not any(w in low for w in ["for all", "prove", "prime", "factorial", "modulo"])
    )
    if simple_word:
        score -= 0.12

    return max(0.0, min(1.0, score))


def apply_family_difficulty_floor(difficulty: float, analysis: dict) -> float:
    """
    Raise clearly structured families out of the cheap/easy envelope when the
    static lexical score underestimates their reasoning cost. This is a floor,
    never a downgrade. The values are routing heuristics, not claims of actual
    mathematical difficulty.
    """
    family = analysis.get("family", "general")
    floors = {
        "floor_sum_valuation": 0.78,
        "adaptive_digit_sum_dynamics": 0.78,
        "finite_sequence_correlation": 0.82,
        "divisor_minimization_asymptotic": 0.84,
        "functional_equation": 0.46,
        "extremal_partition": 0.46,
        "euclidean_geometry": 0.52,
        "geometry_sequence_asymptotic": 0.78,
        "combinatorial_process": 0.50,
        "number_theory": 0.40,
    }
    floor = float(floors.get(family, 0.0))
    return max(float(difficulty), floor)


def choose_budget(cfg: dict, difficulty: float) -> tuple[str, dict]:
    c = cfg["controller"]
    if difficulty < float(c.get("easy_threshold", 0.35)):
        name = "easy"
    elif difficulty >= float(c.get("hard_threshold", 0.70)):
        name = "hard"
    else:
        name = "medium"
    return name, dict(c["budgets"][name])


def candidate_score(candidate: dict, verification: dict | None = None) -> float:
    score = float(candidate.get("self_confidence", 0.5))
    if candidate.get("protocol_complete"):
        score += 0.08
    if candidate.get("ambiguity_detected"):
        score -= 0.25
    if candidate.get("truncated"):
        score -= 0.20
    if candidate.get("candidate_answer") is None:
        score -= 0.25
    if candidate.get("target_valid") is False:
        score -= 1.00
    if candidate.get("candidate_refuted"):
        score -= 1.00
    if verification:
        if verification.get("passed"):
            score += 0.40
        elif verification.get("level") == "EXACT_TOOL" and not verification.get("passed"):
            score -= 0.40
    return score


def should_trigger_rag(cfg: dict, candidate: dict, disagreement: bool = False) -> bool:
    rag = cfg.get("rag", {})
    if not rag.get("enabled", True):
        return False
    if disagreement and rag.get("trigger_on_answer_disagreement", True):
        return True
    threshold = float(rag.get("trigger_confidence_below", 0.72))
    return (
        candidate.get("candidate_answer") is None
        or candidate.get("ambiguity_detected", False)
        or float(candidate.get("self_confidence", 0.0)) < threshold
        or not candidate.get("protocol_complete", False)
    )


def answer_disagreement(candidates: list[dict]) -> bool:
    answers = [c.get("candidate_answer") for c in candidates if c.get("candidate_answer") is not None]
    return len(set(answers)) > 1



def should_use_constraint_first(problem: str, analysis: dict) -> bool:
    """Cheap router for short algebra word problems with several relational clauses."""
    low = problem.lower()
    if analysis.get("domain") != "algebra" or len(problem) >= 1800:
        return False
    entity_hits = sum(x in low for x in [
        "age", "sweets", "coins", "holding", "holds", "give", "gives", "each"
    ])
    relation_hits = sum(x in low for x in [
        "sum", "product", "double", "times", "equal", "added", "multiply"
    ])
    return entity_hits >= 2 and relation_hits >= 2
