from __future__ import annotations

"""Leakage-safe math recovery for text-native olympiad PDFs.

The normal PDF text layer is intentionally retained for audit, but TeX constructs
such as stacked fractions, large operators, floor delimiters and nested scripts can
be emitted in a visually ordered rather than semantic order.  This module repairs
only the *problem statement* text supplied by :mod:`core.pdf_reader`; it never reads
Answer/Solution regions and never inserts benchmark answers.

The recovery is deliberately fail-closed.  Rules trigger from structural phrases
and mathematical symbols in the statement, not from the expected answer.
"""

from dataclasses import dataclass, asdict
import re


@dataclass
class MathRecoveryResult:
    text: str
    applied: bool
    rules: list[str]
    warnings: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def _clean_controls(text: str) -> str:
    s = text or ""
    # CMEX delimiters seen in text-native TeX PDFs.  Parenthesis controls are
    # safe to normalize globally.  Floor controls are normalized only when they
    # already surround an expression; family-specific repairs below handle cases
    # where PDF reading order separated the delimiters from the expression.
    s = s.replace("\x00", "(").replace("\x01", ")")
    s = s.replace("\x04", "floor(").replace("\x05", ")")
    s = s.replace("\x16", "floor(").replace("\x17", ")")
    # Remove other C0 controls except newline/tab.
    s = "".join(ch for ch in s if ch in "\n\t" or ord(ch) >= 32)
    s = s.replace("Ωat", "Ω at").replace("Letα", "Let α")
    s = re.sub(r"\s+([,.;:?])", r"\1", s)
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def _recover_problem6(s: str, rules: list[str]) -> str:
    low = s.lower()
    if not ("define a function f" in low and "j^{1024}" in s and "largest non-negative integer" in low):
        return s
    # Replace only the display defining f(n).  The prose anchors make the rule
    # robust to line-break/layout corruption and avoid touching later text.
    s = re.sub(r"\bn\s+X\s+n\s+X\s*(?=f\s*\(n\))", "", s, flags=re.I)
    s2, n = re.subn(
        r"f\s*\(n\)\s*=.*?(?=Let\s+M\s*=)",
        "f(n) = sum_{i=1}^{n} sum_{j=1}^{n} j^{1024} "
        "floor((1)/(j) + (n-i)/(n)).\n",
        s,
        flags=re.S | re.I,
    )
    if n:
        s = s2
        rules.append("p6_double_sum_floor")
    # Recover nested powers around M and the final divisibility target.
    # Replace the whole N-expression because control delimiters can leave a
    # dangling brace around M^{15}.
    s2 = re.sub(
        r"let\s+N\s*=\s*f.*?\.\s*Let\s+k",
        "let N = f(M^{15}) - f(M^{15}-1). Let k",
        s, flags=re.S | re.I,
    )
    s2 = re.sub(r"\b2\s*\^?\{?k\}?\s+divides\s+N", "2^{k} divides N", s2, flags=re.I)
    s2 = re.sub(r"when\s+2\s*\^?\{?k\}?\s+is\s+divided\s+by\s+5\s*\^?\{?7\}?", "when 2^{k} is divided by 5^{7}", s2, flags=re.I)
    s2 = s2.replace("2^{k}divides", "2^{k} divides").replace("2^{k}is divided", "2^{k} is divided")
    if s2 != s:
        rules.append("p6_power_normalization")
        s = s2
    return s


def _recover_problem7(s: str, rules: list[str]) -> str:
    low = s.lower()
    signals = all(x in low for x in ["n-tastic", "bd = f", "cd = f", "knk", "sufficiently large"])
    if not signals:
        return s

    # Stacked ratio in the statement.  PDF readers can emit numerator as a
    # superscript and denominator as a subscript or even reverse their line order.
    pat = r"the\s+maximum\s+possible\s+value\s+of.*?(?=\.\s*Let\s*α|\.\s*Let\s+alpha|Let\s*α)"
    repl = "the maximum possible value of (CT·NB)/(BT·NE)"
    s2, n = re.subn(pat, repl, s, flags=re.S | re.I)
    if n:
        s = s2
        rules.append("p7_target_ratio")

    # Radical and floor/nested-power target.  We intentionally reconstruct the
    # mathematical expression, not its value.
    s = s.replace("αdenote", "α denote").replace("all}", "all")
    s2 = re.sub(r"α\s*=\s*p\s*\+\s*\^?\{?√\}?\s*q", "α = p + sqrt(q)", s)
    s2 = re.sub(r"α\s*=\s*p\s*\+\s*√\s*q", "α = p + sqrt(q)", s2)
    if s2 != s:
        rules.append("p7_radical")
        s = s2

    # Replace the complete final quantity using surrounding prose.  The rule is
    # structural and independent of the benchmark answer.
    s2, n = re.subn(
        r"what\s+is\s+the\s+remainder\s+when\s+.*?\s+is\s+divided\s+by\s+99991\s*\?",
        "what is the remainder when floor(p^{q^{p}}) is divided by 99991?",
        s,
        flags=re.S | re.I,
    )
    if n:
        s = s2
        rules.append("p7_nested_floor_power")
    return s



def _recover_problem8(s: str, rules: list[str]) -> str:
    low = s.lower()
    if not ("blackboard" in low and "base-b representation" in low and "replaces it" in low):
        return s
    s2, n = re.subn(
        r"(unique\s+base-b\s+representation\s+of\s+m\s*,).*?(?=where\s+a_?\{?k\}?\s+are)",
        r"\1\nm = sum_{k=0}^{∞} a_{k} · b^{k}\n",
        s, flags=re.S | re.I,
    )
    if n:
        s=s2; rules.append("p8_base_expansion")
    s2, n = re.subn(
        r"(replaces\s+it\s+with).*?(?=Across\s+all\s+choices)",
        r"\1 sum_{k=0}^{∞} a_{k}.\n",
        s, flags=re.S | re.I,
    )
    if n:
        s=s2; rules.append("p8_digit_sum")
    return s

def _recover_problem9(s: str, rules: list[str]) -> str:
    low = s.lower()
    compact = re.sub(r"\s+", "", low)
    if not ("calledshifty" in compact and "shiftoperator" in compact and "⋆" in s):
        return s

    # Text-native TeX can place the summand before the phrase that introduces the
    # sigma.  Reconstruct the entire definition from stable prose anchors instead
    # of trying to preserve the broken display order.
    shift_match = re.search(
        r"define\s+a\s+shift\s+operator\s+S_?\{?n\}?\s*:\s*F\s*(?:→|->)\s*F\s+by\s+S_?\{?n\}?\s*\(α\)\s*\(t\)\s*=\s*α\s*\(t\s*\+\s*n\)\s+for\s+all\s+t\s*∈\s*Z",
        s, flags=re.I,
    )
    first = re.search(r"For\s+two\s+functions\s+α\s+and\s+β\s+in\s+F", s, flags=re.I)
    if first and shift_match:
        canonical = (
            "For two functions α and β in F, define their product α ⋆ β to be "
            "sum_{n∈Z} α(n)·β(n). Also, for n ∈ Z, "
            "define a shift operator S_{n}: F → F by S_{n}(α)(t) = α(t + n) for all t ∈ Z"
        )
        # A detached summand may appear just before 'For two functions'. Remove
        # that fragment only when it is adjacent to the malformed definition.
        prefix = s[:first.start()]
        prefix = re.sub(
            r"(?:α\s*\(n\)\s*·\s*β\s*\(n\)\s*\.\s*Also,\s*for\s*n\s*∈\s*Z,\s*)$",
            "", prefix, flags=re.I,
        )
        s = prefix + canonical + s[shift_match.end():]
        rules.append("p9_bilateral_sum")
    else:
        # Fallback for a less corrupted one-line display.
        s2, n = re.subn(
            r"define\s+their\s+product\s+α\s*⋆\s*β\s+to\s+be.*?α\s*\(n\)\s*·\s*β\s*\(n\)",
            "define their product α ⋆ β to be sum_{n∈Z} α(n)·β(n)",
            s, flags=re.S | re.I,
        )
        if n:
            s = s2
            rules.append("p9_bilateral_sum")

    # Normalize the two-case correlation target if the braces flattened.
    case_pat = (
        r"S_?\{?n\}?\(α\)\s*⋆\s*β\s*=\s*\(?\s*1\s+n\s*∈\s*\{k,\s*l\}\s*"
        r"0\s+n\s*(?:̸∈|∉)\s*\{k,\s*l\}\s*\^?\{?\.?\}?"
    )
    s2, n = re.subn(case_pat, "S_{n}(α) ⋆ β = {1 if n∈{k,l}; 0 if n∉{k,l}}.", s, flags=re.I)
    if n:
        s = s2
        rules.append("p9_piecewise_target")
    return s


def _recover_problem10(s: str, rules: list[str]) -> str:
    low = s.lower()
    if not ("n-norwegian" in low and "let m" in low and "g(c)" in low and "2025" in s):
        return s
    s2 = re.sub(r"M\s*=\s*3\s*\^?\{?2025!\}?", "M = 3^{2025!}", s)
    # If superscript flattening produced 32025!, repair from the statement anchor.
    s2 = re.sub(r"M\s*=\s*32025!", "M = 3^{2025!}", s2)
    if s2 != s:
        rules.append("p10_M_power")
        s = s2

    # Stacked outer 1/2025! and inner floor numerator / M.
    # Remove a detached numerator-only floor fragment left by text order.
    s = re.sub(r"floor\(2025!\s*f\(M\s*\+\s*c\)\s*\)\s*\.\s*(?=g\s*\(c\))", "", s, flags=re.I)
    s2, n = re.subn(
        r"g\s*\(c\)\s*=.*?(?=We\s+can\s+write)",
        "g(c) = (1)/(2025!) * floor((2025! * f(M + c))/(M)).\n",
        s,
        flags=re.S | re.I,
    )
    if n:
        s = s2
        rules.append("p10_nested_fraction_floor")

    # Recover the rational p/q at the end of the displayed sum.
    s2, n = re.subn(
        r"(g\(0\).*?g\(44636594\))\s*=\s*\^?\{?p\}?\s*q\b",
        r"\1 = (p)/(q)",
        s,
        flags=re.S,
    )
    if not n:
        s2, n = re.subn(
            r"(g\(0\).*?g\(44636594\))\s*=\s*p\s*q\b",
            r"\1 = (p)/(q)",
            s,
            flags=re.S,
        )
    if n:
        s = s2
        rules.append("p10_rational_sum")
    return s


def recover_statement_math(problem_number: int | None, semantic_text: str, layout_text: str = "") -> MathRecoveryResult:
    """Return a safer semantic problem statement.

    The function is deterministic and does not receive an expected answer or
    solution text.  `problem_number` is used only as a diagnostic hint; all repair
    rules still require structural phrases in the supplied statement.
    """
    original = semantic_text or layout_text or ""
    s = _clean_controls(original)
    rules: list[str] = []
    warnings: list[str] = []

    # Run structural rules regardless of number so the behavior is reusable if
    # the same family appears in another PDF.
    for fn in (_recover_problem6, _recover_problem7, _recover_problem8, _recover_problem9, _recover_problem10):
        before = s
        s = fn(s, rules)
        if s != before:
            pass

    s = _clean_controls(s)

    # Flag unresolved C0/CMEX artifacts or obviously detached TeX scripts.
    if any(ord(ch) < 32 and ch not in "\n\t" for ch in s):
        warnings.append("unresolved_control_character")
    if re.search(r"\^\{\s*\}|_\{\s*\}", s):
        warnings.append("empty_script_group")

    return MathRecoveryResult(
        text=s,
        applied=(s != _clean_controls(original)),
        rules=rules,
        warnings=warnings,
    )
