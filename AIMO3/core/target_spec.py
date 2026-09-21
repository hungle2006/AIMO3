from __future__ import annotations

import re
from dataclasses import dataclass, asdict


@dataclass
class TargetSpec:
    kind: str = "direct_integer"
    modulus: int | None = None
    quantity_text: str = ""
    min_value: int | None = None
    max_value: int | None = None
    instruction: str = "Return the exact integer requested by the problem."

    def to_dict(self) -> dict:
        return asdict(self)


def _parse_simple_int_expr(text: str) -> int | None:
    if not text:
        return None
    s = text.strip()
    s = s.replace("−", "-").replace("×", "*")
    # common LaTeX powers such as 10^{5}, 2^20
    m = re.fullmatch(r"\s*(\d+)\s*\^\s*\{?\s*(\d+)\s*\}?\s*", s)
    if m:
        base, exp = int(m.group(1)), int(m.group(2))
        if 0 <= exp <= 12:
            return base ** exp
        return None
    if re.fullmatch(r"\d+", s):
        return int(s)
    return None


def extract_target_spec(problem: str) -> dict:
    """Extract the requested output contract without solving the mathematics.

    This is deliberately narrow. It handles the common AIMO phrasing around
    remainders/moduli and otherwise falls back to a direct integer target.
    """
    text = " ".join((problem or "").split())

    # "What is the remainder when K is divided by 10^{5}?"
    m = re.search(
        r"(?i)remainder\s+when\s+(.+?)\s+is\s+divided\s+by\s+"
        r"((?:\d+\s*\^\s*\{?\s*\d+\s*\}?)|\d+)",
        text,
    )
    if not m:
        # "remainder of X modulo M"
        m = re.search(
            r"(?i)remainder\s+of\s+(.+?)\s+(?:modulo|mod)\s+"
            r"((?:\d+\s*\^\s*\{?\s*\d+\s*\}?)|\d+)",
            text,
        )
    if not m:
        # "Find M modulo 1000" / "What is X mod 99991?"
        m = re.search(
            r"(?i)(?:find|determine|what\s+is)\s+(.+?)\s+(?:modulo|mod)\s+"
            r"((?:\d+\s*\^\s*\{?\s*\d+\s*\}?)|\d+)",
            text,
        )
    if m:
        quantity = m.group(1).strip(" .,:;?")
        modulus_text = m.group(2)
        modulus = _parse_simple_int_expr(modulus_text)
        if modulus and modulus > 0:
            spec = TargetSpec(
                kind="remainder",
                modulus=modulus,
                quantity_text=quantity,
                min_value=0,
                max_value=modulus - 1,
                instruction=(
                    f"Return ONLY the requested remainder of ({quantity}) modulo {modulus}. "
                    f"The final candidate must satisfy 0 <= answer < {modulus}. "
                    f"Do not output the modulus {modulus} itself and do not output the unreduced quantity."
                ),
            )
            return spec.to_dict()

    spec = TargetSpec()
    return spec.to_dict()


def validate_candidate_for_target(value, target_spec: dict | None) -> dict:
    if isinstance(value, bool) or value is None:
        return {"valid": False, "value": None, "reason": "missing integer candidate"}
    try:
        n = int(value)
    except Exception:
        return {"valid": False, "value": None, "reason": "candidate is not an integer"}

    spec = target_spec or {}
    kind = spec.get("kind", "direct_integer")
    if kind == "remainder":
        modulus = spec.get("modulus")
        try:
            modulus = int(modulus)
        except Exception:
            modulus = None
        if modulus and not (0 <= n < modulus):
            return {
                "valid": False,
                "value": n,
                "reason": f"remainder target requires 0 <= answer < {modulus}; got {n}",
            }
    return {"valid": True, "value": n, "reason": "OK"}


def normalize_requested_output(raw_value: int, target_spec: dict | None) -> int:
    """Convert an already-proved raw target value to the requested output form.

    This must only be called on a value that the proof has established as the
    underlying mathematical quantity. It is NOT a repair for arbitrary model guesses.
    """
    n = int(raw_value)
    spec = target_spec or {}
    if spec.get("kind") == "remainder" and spec.get("modulus"):
        return n % int(spec["modulus"])
    return n
