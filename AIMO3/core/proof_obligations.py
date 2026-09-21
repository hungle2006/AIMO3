from __future__ import annotations

import re
from dataclasses import dataclass, asdict


FAMILY_OBLIGATIONS = {
    "floor_sum_valuation": [
        "floor_sum_reduction", "divisor_sum_identity", "valuation_computation", "target_arithmetic",
    ],
    "adaptive_digit_sum_dynamics": [
        "transition_characterization", "longest_path_recurrence", "extremal_bound", "target_arithmetic",
    ],
    "finite_sequence_correlation": [
        "correlation_polynomial_transform", "cyclotomic_classification", "degree_enumeration", "target_count",
    ],
    "divisor_minimization_asymptotic": [
        "divisor_triple_classification", "small_factor_transfer", "floor_stabilization", "rational_sum",
    ],
    "relational_algebra": [
        "equation_model",
        "integer_solution",
        "answer_check",
    ],
    "extremal_partition": [
        "upper_bound",
        "construction",
        "arithmetic_check",
    ],
    "functional_equation": [
        "structural_transform",
        "solution_class",
        "bounded_constraints",
        "target_count",
    ],
    "euclidean_geometry": [
        "exact_geometry_relation",
        "configuration_conditions",
        "integer_extremum",
    ],
    "geometry_sequence_asymptotic": [
        "exact_geometry_reduction",
        "sequence_formula",
        "asymptotic_limit",
        "target_arithmetic",
    ],
    "combinatorial_process": [
        "state_invariant",
        "counting_formula",
        "valuation_or_final_count",
    ],
    "number_theory": [
        "structural_reduction",
        "exact_arithmetic",
        "edge_cases",
    ],
    "general": [
        "main_argument",
        "edge_cases",
        "final_check",
    ],
}


OBLIGATION_DESCRIPTIONS = {
    "floor_sum_reduction": "Collapse the nested floor sum exactly, with all threshold cases justified; no asymptotic approximation is allowed.",
    "divisor_sum_identity": "Convert the reduced sum to an exact divisor-sum expression and justify multiplicativity/factorization.",
    "valuation_computation": "Compute the requested p-adic valuation exactly with theorem hypotheses checked.",
    "transition_characterization": "Prove the complete set of possible next states for one digit-sum move, including both achievability and the upper bound.",
    "longest_path_recurrence": "Derive the exact recurrence for the maximum remaining number of moves and solve it.",
    "extremal_bound": "Prove that the chosen starting value attains the global maximum under the stated upper bound.",
    "correlation_polynomial_transform": "Translate the shifted inner product into a coefficient identity for a polynomial times a Laurent polynomial.",
    "cyclotomic_classification": "Classify all integer polynomial divisors of the required binomial using cyclotomic factors, including sign and monomial shifts.",
    "degree_enumeration": "Enumerate all admissible cyclotomic subsets and shifts under the support-degree constraint without double counting.",
    "divisor_triple_classification": "Classify the divisor triples that can minimize the n-Norwegian integer and justify that omitted cases are larger.",
    "small_factor_transfer": "Use modular arithmetic to determine the relevant small divisors of M+c without constructing M.",
    "floor_stabilization": "Prove the residual term in the floor lies in the exact interval required to extract the rational coefficient.",
    "rational_sum": "Sum the resulting rational values exactly, reduce p/q, and compute the requested final remainder.",
    "equation_model": "Translate every relational clause and event into the correct equations with owner/quantity roles preserved.",
    "integer_solution": "Solve the resulting integer system and justify that the required solution/goal value is unique under the stated domains.",
    "answer_check": "Substitute the solution back into the decisive original constraints and check the requested quantity exactly.",
    "upper_bound": "Prove a rigorous upper bound. A numerical heuristic or area estimate alone is insufficient unless every inequality is justified.",
    "construction": "Give an explicit realizable construction attaining the claimed bound; for tilings/partitions, explain why the pieces actually tile the board and satisfy all distinctness/integrality constraints.",
    "arithmetic_check": "Check the final arithmetic and requested modulus exactly.",
    "structural_transform": "Derive the decisive change of variables / algebraic transformation exactly and state its valid domain.",
    "solution_class": "Characterize the full family of solutions allowed by the transformed functional equation; do not replace a classification by an unjustified special form.",
    "bounded_constraints": "Translate all positivity/bounded-input conditions into exact constraints on the solution parameters.",
    "target_count": "Determine the complete set/count of possible target values and compute the requested answer.",
    "exact_geometry_relation": "Derive an exact geometric/algebraic relation from the incidences, circles, collinearities, and equal lengths; do not guess a triangle.",
    "configuration_conditions": "Check that the derived configuration satisfies side/angle/incidence/second-intersection conditions and excludes degenerate cases.",
    "integer_extremum": "Use the exact relation to determine the required integer side/extremal solution and prove minimality/uniqueness if required.",
    "exact_geometry_reduction": "Derive the exact geometric identity that reduces the constructed configuration to the target length/ratio; do not infer it from a diagram or analogy.",
    "sequence_formula": "Use the recurrence data to derive an exact closed formula or exact ratio for a_n; every index shift must be justified.",
    "asymptotic_limit": "Prove the eventual bound and limiting value for the required subsequence, including the direction of approach when the problem asks for the smallest eventual upper bound.",
    "target_arithmetic": "Extract p and q from the proved algebraic value and compute the final floor/power/modulus exactly.",
    "state_invariant": "Compress the process into exact states, histories, recurrences, or invariants and justify how pairings evolve.",
    "counting_formula": "Derive the exact counting formula for the possible outcomes/orderings before evaluating divisibility.",
    "valuation_or_final_count": "Compute the requested valuation/count/modulus exactly from the derived formula.",
    "structural_reduction": "Give the key number-theoretic reduction with theorem conditions checked.",
    "exact_arithmetic": "Perform the decisive exact divisibility/congruence/valuation computation.",
    "edge_cases": "Check exceptional cases, parity/domain restrictions, and boundary values that could invalidate the argument.",
    "main_argument": "Give the decisive rigorous derivation linking the assumptions to the committed answer.",
    "final_check": "Check the final integer against the exact target quantity.",
}


@dataclass
class ObligationAssessment:
    required: list[str]
    present: list[str]
    missing: list[str]
    evidence: dict[str, str]

    def to_dict(self) -> dict:
        return asdict(self)


def required_obligations(family: str) -> list[str]:
    return list(FAMILY_OBLIGATIONS.get(family, FAMILY_OBLIGATIONS["general"]))


def obligation_description(name: str) -> str:
    return OBLIGATION_DESCRIPTIONS.get(name, "Prove this missing part rigorously and concisely.")


def _has_any(text: str, needles: list[str]) -> bool:
    low = text.lower()
    return any(n.lower() in low for n in needles)


def _evidence_window(text: str, needles: list[str], limit: int = 900) -> str:
    low = text.lower()
    for n in needles:
        idx = low.find(n.lower())
        if idx >= 0:
            start = max(0, idx - 180)
            return text[start:start + limit].strip()
    return ""


def assess_candidate_obligations(candidate: dict, family: str) -> ObligationAssessment:
    """Heuristic routing only; this never verifies mathematical correctness.

    The purpose is to avoid restarting an entire proof when a truncated attempt has
    already developed one useful component. A later critic/verifier still decides
    whether the evidence is actually correct.
    """
    text = "\n".join([
        str(candidate.get("interpretation", "")),
        str(candidate.get("proof", "")),
        str(candidate.get("check", "")),
        str(candidate.get("raw_output", "")),
    ])
    low = text.lower()
    req = required_obligations(family)
    evidence: dict[str, str] = {}
    declared = candidate.get("declared_obligations", {}) or {}

    patterns = {
        "floor_sum_reduction": ["hermite", "floor", "inner sum", "floor(n/j)", "threshold"],
        "divisor_sum_identity": ["sigma", "divisor sum", "multiplicative", "geometric sum"],
        "valuation_computation": ["valuation", "v_2", "lte", "adic"],
        "transition_characterization": ["outgoing", "neighbour", "digit sum", "ceil(n/2)", "reachable"],
        "longest_path_recurrence": ["longest path", "recurrence", "h(n)", "log2"],
        "extremal_bound": ["maximum", "global", "upper bound", "attain"],
        "correlation_polynomial_transform": ["laurent", "p_alpha", "q_beta", "coefficient", "correlation"],
        "cyclotomic_classification": ["cyclotomic", "phi_", "x^b+1", "factorization"],
        "degree_enumeration": ["degree", "enumerate", "subset", "count"],
        "divisor_triple_classification": ["three divisors", "p = 1", "q = 2", "minimum", "norwegian"],
        "small_factor_transfer": ["euler", "m ≡ 1", "m=1 mod", "small divisors", "mod 6"],
        "floor_stabilization": ["floor", "correction", "less than 1", "0 <"],
        "rational_sum": ["fraction", "p/q", "coprime", "sum", "remainder"],
        "equation_model": ["equation", "constraints", "let ", "sum", "product", "transfer"],
        "integer_solution": ["solving", "solution", "integer", "unique", "hence"],
        "answer_check": ["check", "substitute", "constraints hold", "verify"],
        "upper_bound": ["upper bound", "at most", "cannot exceed", "≤", "<=", "bound"],
        "construction": ["explicit construction", "construction", "construct", "attain", "achieve", "tile the", "tiling by"],
        "arithmetic_check": ["mod", "remainder", "arithmetic", "check", "therefore"],
        "structural_transform": ["change of variables", "let g", "g(ab)", "(m+1)(n+1)", "transform"],
        "solution_class": ["values on primes", "prime weights", "completely additive", "all solutions", "classification"],
        "bounded_constraints": ["bounded", "≤1000", "<=1000", "positive", "constraint"],
        "target_count": ["possible values", "how many", "count", "target"],
        "exact_geometry_relation": ["power of a point", "radical axis", "coordinates", "cyclic", "exact relation", "equation"],
        "configuration_conditions": ["acute", "second intersection", "nondegenerate", "lies on", "condition"],
        "integer_extremum": ["integer sides", "minimal perimeter", "minimality", "unique", "search"],
        "exact_geometry_reduction": ["power of a point", "spiral similarity", "cyclic", "tangent", "ratio", "exact relation"],
        "sequence_formula": ["fibonacci", "f_{n", "a_n", "a_{n}", "recurrence", "binet", "ratio"],
        "asymptotic_limit": ["limit", "sufficiently large", "eventual", "approaches", "from below", "limsup", "phi"],
        "target_arithmetic": ["p =", "q =", "floor", "mod", "remainder", "99991", "power"],
        "state_invariant": ["state", "history", "invariant", "equal score", "recurrence", "block"],
        "counting_formula": ["number of orderings", "counting formula", "product", "factorial", "ways"],
        "valuation_or_final_count": ["v_2", "v_5", "valuation", "10^", "mod", "remainder"],
        "structural_reduction": ["factor", "gcd", "valuation", "congruence", "reduction"],
        "exact_arithmetic": ["mod", "valuation", "gcd", "factorial", "remainder", "exact"],
        "edge_cases": ["case", "edge", "exception", "parity", "boundary"],
        "main_argument": ["solution", "therefore", "hence", "we get", "implies"],
        "final_check": ["check", "verify", "therefore", "final"],
    }

    present: list[str] = []
    for name in req:
        declared_status = str(declared.get(name, "")).strip().upper()
        # Explicit PARTIAL/MISSING from the model is useful routing metadata. It is
        # not a mathematical truth claim, but it should prevent a keyword heuristic
        # from falsely declaring the obligation complete.
        if declared_status in {"MISSING", "PARTIAL", "INCOMPLETE"}:
            continue

        needles = patterns.get(name, [name.replace("_", " ")])
        ev = _evidence_window(text, needles)
        low_ev = ev.lower()

        # Self-declared DONE is never proof. Dangerous obligations need structural
        # evidence, not just one routing keyword in a truncated answer.
        if name == "construction":
            negative = any(x in low_ev for x in [
                "construction still needs", "needs to be shown", "construction missing",
                "not constructed", "construction not", "without a construction",
                "no explicit construction", "fails to construct",
            ])
            meaningful = (
                bool(ev) and len(ev) >= 140 and not negative
                and _has_any(ev, ["construct ", "take ", "cut ", "partition ", "strip", "tile ", "arrange ", "place "])
                and bool(re.search(r"\d", ev))
            )
        elif name == "upper_bound":
            meaningful = (
                bool(ev) and len(ev) >= 70
                and _has_any(ev, ["at most", "cannot exceed", "upper bound", "<=", "≤", "contradiction"])
                and bool(re.search(r"\d|[=<>≤≥]|sum|\\sum", ev, flags=re.I))
            )
        elif name == "arithmetic_check":
            meaningful = (
                bool(ev) and len(ev) >= 60
                and _has_any(ev, ["mod", "remainder", "check", "=", "therefore"])
                and bool(re.search(r"\d", ev))
            )
        elif name in {"solution_class", "counting_formula", "exact_geometry_relation", "exact_geometry_reduction", "sequence_formula", "asymptotic_limit"}:
            meaningful = bool(ev) and len(ev) >= 120
        else:
            meaningful = bool(ev) and len(ev) >= 50
        if meaningful:
            present.append(name)
            evidence[name] = ev

    missing = [x for x in req if x not in present]
    return ObligationAssessment(req, present, missing, evidence)


def candidate_progress_score(candidate: dict, family: str) -> float:
    assessment = assess_candidate_obligations(candidate, family)
    req = max(1, len(assessment.required))
    obligation_fraction = len(assessment.present) / req
    answer_bonus = 0.35 if candidate.get("candidate_answer") is not None else 0.0
    protocol_bonus = 0.15 if candidate.get("protocol_complete") else 0.0
    trunc_penalty = 0.08 if candidate.get("truncated") else 0.0
    invalid_penalty = 0.55 if candidate.get("target_valid") is False else 0.0
    refuted_penalty = 0.65 if candidate.get("candidate_refuted") else 0.0
    return max(0.0, min(1.0,
        0.5 * obligation_fraction + answer_bonus + protocol_bonus
        - trunc_penalty - invalid_penalty - refuted_penalty
    ))
