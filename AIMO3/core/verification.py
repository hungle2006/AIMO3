from __future__ import annotations

from dataclasses import dataclass, asdict

from .answer_contract import AIMO3AnswerContract
from .tools import run_tool_requests
from .target_spec import validate_candidate_for_target


@dataclass
class VerificationResult:
    level: str
    passed: bool
    reason: str
    checks: list[dict]

    def to_dict(self) -> dict:
        return asdict(self)


def _tool_failure(reports: list[dict]) -> bool:
    """Any explicit tool execution/verification failure is disqualifying evidence."""
    for r in reports or []:
        if not r.get("ok", False):
            return True
        if r.get("verified") is False:
            return True
    return False


def _answer_bound_certificate(reports: list[dict], candidate_answer: int) -> tuple[bool, str]:
    """
    Conservative deterministic certificate test.

    A random true identity (e.g. 2+2=4) must NOT certify an unrelated answer.
    For automatic exact certification we require a check_equalities report that:
      - verified at least one equality,
      - includes an explicit answer_check,
      - binds expected_answer to the parsed candidate answer,
      - and verifies that answer expression.

    Other exact tool results remain useful evidence for the critic, but are not by
    themselves sufficient to certify a general olympiad solution.
    """
    for r in reports or []:
        if not r.get("ok", False) or r.get("verified") is not True:
            continue
        if r.get("op") != "check_equalities":
            continue
        checks = r.get("checks") or []
        answer_check = r.get("answer_check")
        if not checks or not isinstance(answer_check, dict):
            continue
        if not all(c.get("verified") is True for c in checks):
            continue
        if answer_check.get("verified") is not True:
            continue
        try:
            expected = int(answer_check.get("expected_answer"))
        except Exception:
            continue
        if expected != int(candidate_answer):
            continue
        return True, "answer-bound equality certificate passed"
    return False, "no answer-bound decisive certificate"


def verify_candidate(candidate: dict, cfg: dict) -> VerificationResult:
    """
    Verification hierarchy:
      NONE < FORMAT < CONSISTENCY < EXACT_TOOL < CRITIC

    Deterministic verification never treats an unrelated true calculation as proof
    of the submitted answer. Exact tools can provide a decisive certificate only
    when the certificate explicitly binds verified problem constraints to the
    candidate answer.
    """
    answer = candidate.get("candidate_answer")
    contract = AIMO3AnswerContract.check(answer)
    checks: list[dict] = [{
        "type": "answer_contract",
        "passed": contract.valid,
        "reason": contract.reason,
        "value": contract.value,
    }]

    if not contract.valid:
        return VerificationResult("NONE", False, contract.reason, checks)

    target_check = validate_candidate_for_target(answer, candidate.get("target_spec"))
    checks.append({
        "type": "target_contract",
        "passed": bool(target_check.get("valid")),
        "reason": target_check.get("reason"),
        "value": target_check.get("value"),
        "target_spec": candidate.get("target_spec"),
    })
    if not target_check.get("valid"):
        return VerificationResult("NONE", False, str(target_check.get("reason")), checks)

    if candidate.get("candidate_refuted"):
        checks.append({
            "type": "candidate_refuted",
            "passed": False,
            "reason": candidate.get("candidate_refutation_reason") or "focused proof refuted this candidate",
        })
        return VerificationResult("FORMAT", False, "candidate was refuted by focused proof", checks)

    if candidate.get("commit_conflict"):
        checks.append({
            "type": "commit_conflict",
            "passed": False,
            "reason": "early committed answer conflicts with final answer",
            "commit_answer": candidate.get("commit_answer"),
            "candidate_answer": candidate.get("candidate_answer"),
        })
        return VerificationResult("FORMAT", False, "committed/final answer conflict", checks)

    if candidate.get("ambiguity_detected"):
        checks.append({
            "type": "semantic_ambiguity",
            "passed": False,
            "reason": candidate.get("ambiguity_text") or "solver reported ambiguity",
        })
        return VerificationResult("FORMAT", False, "semantic ambiguity remains", checks)

    if not candidate.get("protocol_complete"):
        checks.append({
            "type": "protocol",
            "passed": False,
            "reason": "FINAL_ANSWER sentinel was not the completed final line",
        })
        return VerificationResult("FORMAT", False, "output protocol incomplete", checks)

    checks.append({"type": "protocol", "passed": True, "reason": "complete final sentinel"})

    tool_cfg = cfg.get("tools", {})
    requests = candidate.get("tool_requests") or []
    if tool_cfg.get("enabled", True) and requests:
        reports = run_tool_requests(
            requests,
            max_requests=int(tool_cfg.get("max_requests_per_solution", 6)),
            allowed_ops=list(tool_cfg.get("allowed_ops", [])),
        )
        candidate["tool_reports"] = reports
        checks.append({"type": "tool_reports", "reports": reports})

        if _tool_failure(reports):
            return VerificationResult(
                "EXACT_TOOL", False,
                "one or more exact tool checks failed",
                checks,
            )

        bound, reason = _answer_bound_certificate(reports, int(contract.value))
        checks.append({
            "type": "answer_bound_certificate",
            "passed": bound,
            "reason": reason,
        })
        if bound:
            return VerificationResult(
                "EXACT_TOOL", True,
                reason,
                checks,
            )

    return VerificationResult(
        "CONSISTENCY",
        False,
        "format is complete, but no answer-bound decisive certificate was established",
        checks,
    )


def critic_verification(
    critic: dict,
    threshold: float,
    selected_candidate: dict | None = None,
) -> VerificationResult:
    """Critic PASS is hard-blocked by malformed candidates or failed exact evidence."""
    checks: list[dict] = []

    base_pass = (
        critic.get("verdict") == "PASS"
        and float(critic.get("confidence", 0.0)) >= float(threshold)
        and bool(critic.get("parse_ok", False))
    )
    checks.append({
        "type": "critic_protocol",
        "passed": base_pass,
        "verdict": critic.get("verdict"),
        "confidence": critic.get("confidence"),
        "parse_ok": critic.get("parse_ok"),
    })

    if not base_pass:
        reason = (
            f"critic verdict={critic.get('verdict')} confidence={critic.get('confidence')} "
            f"parse_ok={critic.get('parse_ok')}"
        )
        return VerificationResult("CRITIC", False, reason, checks)

    if selected_candidate is None:
        checks.append({"type": "selected_candidate", "passed": False, "reason": "missing candidate"})
        return VerificationResult("CRITIC", False, "critic PASS did not identify a valid candidate", checks)

    target_check = validate_candidate_for_target(
        selected_candidate.get("candidate_answer"), selected_candidate.get("target_spec")
    )
    candidate_ok = (
        selected_candidate.get("candidate_answer") is not None
        and selected_candidate.get("protocol_complete") is True
        and selected_candidate.get("ambiguity_detected") is not True
        and selected_candidate.get("truncated") is not True
        and selected_candidate.get("candidate_refuted") is not True
        and bool(target_check.get("valid"))
    )
    checks.append({
        "type": "candidate_protocol",
        "passed": candidate_ok,
        "candidate_id": selected_candidate.get("id"),
    })
    if not candidate_ok:
        return VerificationResult("CRITIC", False, "selected candidate is incomplete or ambiguous", checks)

    reports = selected_candidate.get("tool_reports") or []
    failed_tools = [r for r in reports if (not r.get("ok", False)) or r.get("verified") is False]
    checks.append({
        "type": "failed_tool_guard",
        "passed": not failed_tools,
        "failed_reports": failed_tools,
    })
    if failed_tools:
        return VerificationResult(
            "CRITIC", False,
            "critic PASS blocked because selected candidate has failed exact tool evidence",
            checks,
        )

    return VerificationResult(
        "CRITIC", True, "critic passed candidate with no disqualifying tool failures", checks
    )
