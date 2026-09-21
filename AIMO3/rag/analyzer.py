from __future__ import annotations
import re
from dataclasses import dataclass

@dataclass
class Analysis:
    domain: str
    keywords: list[str]
    query: str

DOMAIN_HINTS = {
    "geometry": ["triangle","circle","angle","tangent","cyclic","collinear","concurrent","circumcircle","incenter","orthocenter"],
    "number_theory": ["integer","prime","divisible","divisibility","mod","modulo","gcd","congru","valuation","factorial","diophantine"],
    "combinatorics": ["graph","coloring","subset","permutation","combination","pigeonhole","arrange","count","moves","game"],
    "algebra": ["inequality","polynomial","positive real","real numbers","symmetric","homogeneous","sum","product","roots"]
}

def analyze(problem: str) -> Analysis:
    low = problem.lower()
    scores = {d: sum(1 for h in hs if h in low) for d, hs in DOMAIN_HINTS.items()}
    domain = max(scores, key=scores.get)
    if scores[domain] == 0:
        domain = "general"

    # Structural overrides for mixed-domain olympiad problems. These avoid routing
    # a combinatorial tiling problem to pure Euclidean-geometry theorems merely
    # because it contains words like square/rectangle.
    if (
        ("rectangle" in low or "rectangles" in low or "tiling" in low)
        and any(x in low for x in ["largest possible", "maximum", "divided into", "partition"])
        and any(x in low for x in ["perimeter", "area", "distinct"])
    ):
        domain = "combinatorics"
    elif (
        ("tournament" in low or "runners" in low or "rounds" in low)
        and any(x in low for x in ["ordering", "paired", "score", "rank"])
    ):
        domain = "combinatorics"

    tokens = re.findall(r"[A-Za-z][A-Za-z\-]{2,}", low)
    stop = {"the","and","for","with","that","this","from","prove","find","show","given","such","where","which","there","exists"}
    keywords = []
    for t in tokens:
        if t not in stop and t not in keywords:
            keywords.append(t)
    keywords = keywords[:16]
    # Structural math cues: turn symbolic olympiad constraints into retrieval language.
    structural = []
    compact = re.sub(r"\s+", "", low)
    if domain == "algebra":
        if "positive" in low or "nonnegative" in low:
            structural += ["positive variables"]
        # Detect genuine fixed-product constraints. The word "product" alone is
        # NOT enough (e.g. age/sweets word problems).
        if (
            re.search(r"[a-z]{2,6}=1(?:\b|$)", compact)
            or "fixed product" in low
            or re.search(r"product\s+(?:is|equals|equal to)\s+(?:a\s+)?constant", low)
        ):
            structural += ["fixed product"]

        # AIMO-style equal-sum/equal-product integer word problems.
        if (
            "integer" in low
            and "sum" in low
            and "product" in low
            and any(w in low for w in ["age", "sweets", "holds", "holding"])
        ):
            structural += [
                "integer word problem",
                "equal sum equal product",
                "quadratic roots",
                "small diophantine system",
            ]
        if any(op in problem for op in [">=", "≥", "<=", "≤"]):
            structural += ["inequality", "lower bound sum"]
        if re.search(r"[a-z](?:\s*\+\s*[a-z]){1,}", low):
            structural += ["sum of variables"]
    elif domain == "number_theory":
        if "divid" in low or "valuation" in low:
            structural += ["divisibility valuation"]
        if "^" in problem or "power" in low:
            structural += ["powers"]
        if "function" in low and ("for all" in low or "f(" in low):
            structural += [
                "functional equation",
                "operation conjugacy",
                "completely additive arithmetic function",
                "prime factorization determines values",
            ]
    elif domain == "geometry":
        if "circle" in low:
            structural += ["circle theorem"]
        if "tangent" in low or "secant" in low:
            structural += ["tangent secant power of a point"]
        if ("circle" in low or "circles" in low) and ("intersect" in low or "second time" in low):
            structural += ["radical axis", "power of a point"]
    elif domain == "combinatorics":
        if "move" in low or "operation" in low:
            structural += ["invariant monovariant"]
        if ("rectangle" in low or "tiling" in low or "partition" in low) and "perimeter" in low:
            structural += [
                "extremal tiling",
                "upper bound and explicit construction",
                "integer side cap piecewise area bound",
            ]
        if ("tournament" in low or "round" in low) and ("score" in low or "paired" in low):
            structural += [
                "binary weighted process",
                "score history tree",
                "powers of two unique encoding",
                "counting valuation",
            ]

    query_parts = keywords + structural
    # preserve order while removing duplicates
    query_parts = list(dict.fromkeys(query_parts))
    query = " ".join(query_parts) if query_parts else problem[:400]
    return Analysis(domain=domain, keywords=query_parts, query=query)


def aimo_structure_features(problem: str) -> list[str]:
    """
    Lightweight AIMO-oriented semantic features. These are appended to retrieval
    queries; they never replace the original statement.
    """
    import re
    t = problem.lower()
    feats = []

    checks = [
        (r"\bremainder\b|\bmod(?:ulo)?\b|≡", "modular arithmetic exact remainder"),
        (r"\bfactorial\b|!", "factorial valuation combinatorial arithmetic"),
        (r"\bdivides\b|∣|\|", "divisibility valuation"),
        (r"\bprime\b", "prime number theory"),
        (r"\bgcd\b|coprime", "gcd coprimality"),
        (r"\bfibonacci\b|\bf_[nN]\b|F_n", "linear recurrence fibonacci"),
        (r"\btriangle\b|circumcircle|incircle|cyclic|tangent|angle bisector", "euclidean geometry"),
        (r"\bfunction\b.*\bfor all\b|f\(", "functional equation"),
        (r"\btournament\b|catalan|ordering|pair", "combinatorics counting"),
        (r"floor|⌊|ceil|⌈", "floor ceiling discrete analysis"),
        (r"base-\w|base b|digit", "digit sum numeral base"),
        (r"cyclotomic|polynomial|irreducible", "polynomial cyclotomic factorization"),
        (r"largest possible|smallest|minimal|maximal|maximum|minimum", "extremal optimization"),
        (r"sum of divisors|sigma|σ", "divisor sum multiplicative function"),
    ]
    for pat, tag in checks:
        if re.search(pat, t):
            feats.append(tag)

    # symbolic patterns
    if re.search(r"\b[a-z]\s*\^\s*[a-z0-9]+", problem, flags=re.I):
        feats.append("power expression")
    if re.search(r"10\s*\^\s*\{?5\}?|99991|100000", problem):
        feats.append("large exact integer arithmetic")

    return sorted(set(feats))
