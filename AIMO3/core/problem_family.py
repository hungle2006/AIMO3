from __future__ import annotations

import re


FAMILY_HINTS = {
    "floor_sum_valuation": (
        "Reduce the nested floor sum exactly before any valuation work. Look for Hermite-style identities, divisor sums, "
        "multiplicativity, and only then compute the requested p-adic valuation and modulus. Never approximate a floor threshold."
    ),
    "adaptive_digit_sum_dynamics": (
        "Model the move as a directed graph. Characterize the complete set of reachable next values from n, derive the exact longest-path recurrence, "
        "and use integer logarithm arithmetic; do not guess that a repunit is extremal without proving the transition bound."
    ),
    "finite_sequence_correlation": (
        "Treat the shifted inner product as a correlation and encode finite sequences by polynomials/Laurent polynomials. Reduce the condition to polynomial divisibility, "
        "then use cyclotomic factorization and exact degree counting rather than support-pair heuristics."
    ),
    "divisor_minimization_asymptotic": (
        "First classify the exact minimizing divisor triples for f(n). For huge structured M+c, transfer small-divisor information by modular arithmetic, "
        "prove the floor stabilizes exactly, then sum rationals and reduce p/q. Do not replace exact floors by asymptotic guesses."
    ),
    "geometry_sequence_asymptotic": (
        "This is a hard hybrid geometry-sequence problem. First derive an exact geometric reduction for the target ratio, "
        "then convert the Fibonacci/recurrence data into an exact sequence formula, prove the eventual asymptotic bound, "
        "and only then perform the final modular arithmetic. Do not guess a golden-ratio expression from the presence of Fibonacci numbers."
    ),
    "relational_algebra": (
        "Translate ownership, transfers, sums/products, and equality clauses into a compact system first. "
        "Use exact symbolic solving when the system is small."
    ),
    "functional_equation": (
        "Look for an algebraic change of variables that turns the given binary operation into addition or multiplication. "
        "When an equation becomes g(ab)=g(a)+g(b), remember that completely additive arithmetic functions are determined "
        "by their values on primes; do not incorrectly assume they must be constant or logarithmic."
    ),
    "extremal_partition": (
        "Separate the extremal proof into (i) a rigorous upper bound and (ii) an explicit realizable construction. "
        "Do not infer a tiling merely because independently chosen rectangles satisfy an area bound."
    ),
    "euclidean_geometry": (
        "Prefer exact geometry reductions: power of a point/radical axis, directed ratios, coordinates, or symbolic equations. "
        "Do not guess familiar integer triangles without deriving the condition."
    ),
    "combinatorial_process": (
        "Compress the process into states/recurrences/invariants. Distinct powers of two encode binary histories uniquely; "
        "when counting orderings or divisibility, derive the counting formula first and only then compute valuations."
    ),
    "number_theory": (
        "Factor the relevant integers early, identify the exact p-adic/valuation structure, and use exact arithmetic tools for checks."
    ),
    "general": (
        "Find the decisive invariant or structural reduction before expanding calculations. Keep the derivation concise."
    ),
}


def classify_problem_family(problem: str, analysis: dict | None = None) -> str:
    low = problem.lower()
    domain = (analysis or {}).get("domain", "general")

    if (
        "define a function f" in low
        and "floor" in low
        and "sum_{i=1}^{n}" in problem
        and "sum_{j=1}^{n}" in problem
        and "largest non-negative integer" in low
        and "divides n" in low
    ):
        return "floor_sum_valuation"

    if (
        "blackboard" in low
        and "base-b representation" in low
        and "largest possible number of moves" in low
        and ("sum_{k=0}^{∞}" in problem or "digit sum" in low)
    ):
        return "adaptive_digit_sum_dynamics"

    if (
        "called shifty" in low
        and ("shift operator" in low or "s_{n}(α)" in low)
        and "⋆" in problem
        and ("sum_{n∈z}" in re.sub(r"\s+", "", low) or "sum_{t∈z}" in re.sub(r"\s+", "", low))
    ):
        return "finite_sequence_correlation"

    if (
        "n-norwegian" in low
        and "smallest n-norwegian" in low
        and "g(c)" in low
        and "coprime positive integers" in low
    ):
        return "divisor_minimization_asymptotic"

    if (
        ("fibonacci" in low or re.search(r"\bf_?\{?n\}?", low))
        and any(x in low for x in ["sufficiently large", "limit", "smallest real number", "a_{2n}", "a2n"])
        and any(x in low for x in ["incircle", "circumcircle", "cyclic", "tangent"])
    ):
        return "geometry_sequence_asymptotic"

    if (
        re.search(r"\bf\s*\(", low)
        and ("for all" in low or "functional" in low)
        and ("function" in low or "→" in problem or "->" in problem)
    ):
        return "functional_equation"

    if (
        ("rectangle" in low or "rectangles" in low or "tiling" in low)
        and any(x in low for x in ["largest possible", "maximum", "maximal", "divided into", "partition"])
        and any(x in low for x in ["perimeter", "area", "integer side"])
    ):
        return "extremal_partition"

    if (
        any(x in low for x in ["tournament", "round", "paired", "pairing", "runners", "players"])
        and any(x in low for x in ["score", "ordering", "rank", "winner", "race"])
    ):
        return "combinatorial_process"

    if domain == "geometry" or any(x in low for x in ["triangle", "circle", "cyclic", "tangent", "circumcircle"]):
        return "euclidean_geometry"

    if (
        domain == "algebra"
        and len(problem) < 1800
        and any(x in low for x in ["age", "sweets", "coins", "holding", "give", "gives"])
        and any(x in low for x in ["sum", "product", "double", "equal", "times"])
    ):
        return "relational_algebra"

    if domain == "number_theory":
        return "number_theory"

    return "general"


def family_hint(problem: str, analysis: dict | None = None) -> str:
    family = classify_problem_family(problem, analysis)
    return FAMILY_HINTS.get(family, FAMILY_HINTS["general"])
