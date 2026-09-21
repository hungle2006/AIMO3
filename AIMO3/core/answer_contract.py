from __future__ import annotations
from dataclasses import dataclass
import re


@dataclass
class AIMOAnswerCheck:
    valid: bool
    value: int | None
    reason: str


class AIMO3AnswerContract:
    """
    AIMO3 answer-only contract:
      - integer
      - 0 <= answer <= 99999
      - no implicit mod 100000 is applied
    """

    MIN_VALUE = 0
    MAX_VALUE = 99999

    @classmethod
    def extract_integer(cls, value) -> int | None:
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value
        if value is None:
            return None

        text = str(value).strip()
        # Prefer a boxed integer.
        boxed = re.findall(r"\\boxed\s*\{\s*(-?\d+)\s*\}", text)
        if boxed:
            return int(boxed[-1])

        # If the final answer string itself is just an integer, accept.
        if re.fullmatch(r"[-+]?\d+", text):
            return int(text)

        # Conservative fallback: look for an explicit "answer" declaration.
        matches = re.findall(
            r"(?i)(?:final\s+answer|answer)\s*[:=]\s*([-+]?\d+)",
            text
        )
        if matches:
            return int(matches[-1])
        return None

    @classmethod
    def check(cls, value) -> AIMOAnswerCheck:
        n = cls.extract_integer(value)
        if n is None:
            return AIMOAnswerCheck(False, None, "No unambiguous integer final answer found.")
        if not (cls.MIN_VALUE <= n <= cls.MAX_VALUE):
            return AIMOAnswerCheck(
                False, n,
                f"Answer {n} is outside the AIMO3 range 0..99999."
            )
        return AIMOAnswerCheck(True, n, "OK")
