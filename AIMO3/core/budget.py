from __future__ import annotations

from dataclasses import dataclass
import time


class BudgetExhausted(RuntimeError):
    pass


@dataclass
class BudgetSnapshot:
    calls: int
    total_tokens: int
    elapsed_sec: float
    max_calls: int
    max_total_tokens: int
    max_seconds: float
    remaining_calls: int
    remaining_tokens: int
    remaining_seconds: float


class BudgetManager:
    """Runtime budget enforced before a call and propagated into generation."""

    def __init__(self, budget_cfg: dict):
        self.max_calls = int(budget_cfg.get("max_calls", 6))
        self.max_total_tokens = int(budget_cfg.get("max_total_tokens", 20000))
        self.max_seconds = float(budget_cfg.get("max_seconds", 900))
        self.started = time.perf_counter()
        self.calls = 0
        self.total_tokens = 0

    def elapsed(self) -> float:
        return time.perf_counter() - self.started

    def remaining_calls(self) -> int:
        return max(0, self.max_calls - self.calls)

    def remaining_tokens(self) -> int:
        return max(0, self.max_total_tokens - self.total_tokens)

    def remaining_seconds(self) -> float:
        return max(0.0, self.max_seconds - self.elapsed())

    def can_call(self) -> tuple[bool, str]:
        if self.calls >= self.max_calls:
            return False, f"model call budget exhausted ({self.calls}/{self.max_calls})"
        if self.total_tokens >= self.max_total_tokens:
            return False, f"token budget exhausted ({self.total_tokens}/{self.max_total_tokens})"
        if self.elapsed() >= self.max_seconds:
            return False, f"time budget exhausted ({self.elapsed():.1f}/{self.max_seconds:.1f}s)"
        return True, "OK"

    def require_call(self) -> None:
        ok, reason = self.can_call()
        if not ok:
            raise BudgetExhausted(reason)

    def generation_allowance(self) -> dict:
        """Values passed into ModelManager so a single generate() cannot ignore the global budget."""
        self.require_call()
        return {
            "remaining_tokens": self.remaining_tokens(),
            "remaining_seconds": self.remaining_seconds(),
        }

    def register(self, input_tokens: int, output_tokens: int) -> None:
        self.calls += 1
        self.total_tokens += int(input_tokens) + int(output_tokens)

    def snapshot(self) -> BudgetSnapshot:
        return BudgetSnapshot(
            calls=self.calls,
            total_tokens=self.total_tokens,
            elapsed_sec=self.elapsed(),
            max_calls=self.max_calls,
            max_total_tokens=self.max_total_tokens,
            max_seconds=self.max_seconds,
            remaining_calls=self.remaining_calls(),
            remaining_tokens=self.remaining_tokens(),
            remaining_seconds=self.remaining_seconds(),
        )


def cap_generation_budget(
    *,
    input_tokens: int,
    configured_max_new: int,
    remaining_total_tokens: int | None,
    remaining_seconds: float | None,
    safety_seconds: float = 1.0,
) -> tuple[int, float | None]:
    """Cap one generate() call by the remaining global token/time budget."""
    max_new = int(configured_max_new)
    if remaining_total_tokens is not None:
        available = int(remaining_total_tokens) - int(input_tokens)
        if available <= 0:
            raise BudgetExhausted(
                f"token budget cannot fit prompt ({input_tokens} prompt tokens, "
                f"{remaining_total_tokens} tokens remaining)"
            )
        max_new = min(max_new, available)

    max_time = None
    if remaining_seconds is not None:
        available_sec = float(remaining_seconds) - float(safety_seconds)
        if available_sec <= 0:
            raise BudgetExhausted(
                f"time budget cannot start generation ({remaining_seconds:.2f}s remaining)"
            )
        max_time = available_sec

    return max(1, max_new), max_time
