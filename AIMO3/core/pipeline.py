from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import time

from rag.analyzer import analyze, aimo_structure_features
from rag.system import OlympiadRAG

from .budget import BudgetManager, BudgetExhausted
from .controller import (
    estimate_difficulty, apply_family_difficulty_floor, choose_budget, candidate_score,
    should_trigger_rag, answer_disagreement, should_use_constraint_first,
)
from .parsing import (
    parse_solver_output, parse_strategy_output, parse_critic_output,
    parse_constraint_formalization, formalization_is_usable,
    parse_thinking_solver_output, parse_obligation_output,
)
from .prompts import (
    direct_solver_prompt, strategy_proposer_prompt, strategy_solver_prompt,
    rag_retry_prompt, critic_prompt, revision_prompt, rescue_solver_prompt,
    constraint_extractor_prompt, solve_from_constraints_prompt,
    repair_semantic_formalization_prompt, deep_thinking_solver_prompt, deep_finish_prompt,
    obligation_proof_prompt, candidate_only_deep_prompt, deep_candidate_finish_prompt,
    candidate_repair_after_refutation_prompt,
)
from .verification import verify_candidate, critic_verification
from .semantic_constraints import (
    compile_semantic_formalization, solve_compiled_system, deterministic_candidate,
    semantic_certificate_ok,
)
from .problem_family import classify_problem_family, family_hint
from .target_spec import extract_target_spec, validate_candidate_for_target
from .answer_contract import AIMO3AnswerContract
from .proof_obligations import (
    required_obligations, obligation_description, assess_candidate_obligations,
    candidate_progress_score,
)
from .family_engines import try_family_engine, family_engine_candidate


class FullOlympiadPipeline:
    """
    v2.6 design:
      - Easy: solve first, verify, stop early.
      - Medium/Hard: proposer only when useful.
      - RAG is conditional AFTER an insufficient first attempt.
      - Thinking critic is escalation-only.
      - Candidate answer is never erased merely because verification failed.
    """

    def __init__(self, cfg: dict, manager):
        self.cfg = cfg
        self.manager = manager
        self.root = Path(cfg.get("_project_root", Path.cwd()))
        self.rag = OlympiadRAG(self.root, cfg=cfg)
        self.calls: list[dict] = []
        self.budget: BudgetManager | None = None

    def _call(self, role: str, prompt: str, stage: str, overrides: dict | None = None):
        if self.budget is None:
            raise RuntimeError("Budget manager not initialized")
        allowance = self.budget.generation_allowance()
        effective_overrides = dict(overrides or {})
        effective_overrides["_budget_remaining_tokens"] = allowance["remaining_tokens"]
        effective_overrides["_budget_remaining_seconds"] = allowance["remaining_seconds"]
        r = self.manager.generate(role, prompt, overrides=effective_overrides)
        self.budget.register(r.input_tokens, r.output_tokens)
        record = {
            "stage": stage,
            "role": role,
            "input_tokens": r.input_tokens,
            "output_tokens": r.output_tokens,
            "max_new_tokens": r.max_new_tokens,
            "total_tokens": r.input_tokens + r.output_tokens,
            "latency_sec": r.latency_sec,
            "gpu": r.gpu,
            "peak_allocated_gb": r.peak_allocated_gb,
            "free_before_gb": r.free_before_gb,
            "free_after_gb": r.free_after_gb,
            "do_sample": r.do_sample,
            "finish_reason": r.finish_reason,
            "truncated": r.truncated,
            "timed_out": getattr(r, "timed_out", False),
            "ended_with_eos": r.ended_with_eos,
            "raw_output": r.raw_text,
            "decoded_output": r.text,
        }
        self.calls.append(record)
        return r, record

    @staticmethod
    def _analysis_dict(problem: str) -> dict:
        a = analyze(problem)
        base = {
            "domain": a.domain,
            "keywords": a.keywords,
            "query": a.query,
            "structure_features": aimo_structure_features(problem),
        }
        base["family"] = classify_problem_family(problem, base)
        base["family_hint"] = family_hint(problem, base)
        base["proof_obligations"] = required_obligations(base["family"])
        base["target_spec"] = extract_target_spec(problem)
        base["target_instruction"] = base["target_spec"].get(
            "instruction", "Return the exact integer requested by the problem."
        )
        return base

    @staticmethod
    def _annotate_candidate_target(candidate: dict, analysis: dict) -> dict:
        candidate["target_spec"] = dict(analysis.get("target_spec") or {})
        answer = candidate.get("candidate_answer")
        aimo = AIMO3AnswerContract.check(answer)
        target = validate_candidate_for_target(answer, analysis.get("target_spec"))
        valid = bool(aimo.valid and target.get("valid"))
        reason = "OK" if valid else (
            target.get("reason") if not target.get("valid") else aimo.reason
        )
        candidate["target_valid"] = valid
        candidate["target_check"] = {
            "valid": valid,
            "reason": reason,
            "aimo_contract": {
                "valid": aimo.valid, "value": aimo.value, "reason": aimo.reason,
            },
            "requested_output": target,
        }
        return candidate

    @classmethod
    def _annotate_candidates_target(cls, candidates: list[dict], analysis: dict) -> None:
        for c in candidates:
            cls._annotate_candidate_target(c, analysis)

    @staticmethod
    def _valid_viable_candidates(candidates: list[dict]) -> list[dict]:
        return [
            c for c in candidates
            if c.get("candidate_answer") is not None
            and c.get("target_valid") is True
            and c.get("candidate_refuted") is not True
        ]

    def _extract_constraints(self, problem: str) -> dict:
        r, rec = self._call(
            "solver",
            constraint_extractor_prompt(problem),
            "formalize_constraints",
            overrides={
                "max_new_tokens": int(
                    self.cfg.get("constraint_first", {}).get("formalizer_max_new_tokens", 420)
                ),
                "do_sample": False,
                "repetition_penalty": 1.0,
            },
        )
        formalization = parse_constraint_formalization(r.text)
        formalization["stage"] = rec["stage"]
        formalization["truncated"] = bool(r.truncated)
        return formalization

    def _repair_semantic_formalization(self, problem: str, previous: dict, errors: list[dict]) -> dict:
        r, rec = self._call(
            "solver",
            repair_semantic_formalization_prompt(problem, previous, errors),
            "repair_semantics",
            overrides={
                "max_new_tokens": int(
                    self.cfg.get("constraint_first", {}).get("repair_max_new_tokens", 420)
                ),
                "do_sample": False,
                "repetition_penalty": 1.0,
            },
        )
        formalization = parse_constraint_formalization(r.text)
        formalization["stage"] = rec["stage"]
        formalization["truncated"] = bool(r.truncated)
        return formalization

    def _deterministic_semantic_candidate(self, problem: str, formalization: dict) -> tuple[dict | None, dict, dict]:
        compiled_obj = compile_semantic_formalization(problem, formalization)
        compiled = compiled_obj.to_dict()
        solved = solve_compiled_system(compiled)
        if not (compiled.get("ok") and solved.get("ok") and solved.get("unique_answer")):
            return None, compiled, solved
        c = deterministic_candidate(compiled, solved, cid="DET1")
        c["constraint_formalization"] = formalization
        c["verification"] = verify_candidate(c, self.cfg).to_dict()
        return c, compiled, solved

    def _solve_from_constraints(
        self, problem: str, formalization: dict, cid: str = "CF1"
    ) -> dict:
        r, rec = self._call(
            "solver",
            solve_from_constraints_prompt(problem, formalization),
            f"solve_{cid}",
            overrides={
                "max_new_tokens": int(
                    self.cfg.get("constraint_first", {}).get("solver_max_new_tokens", 950)
                ),
                "do_sample": False,
                "repetition_penalty": 1.0,
            },
        )
        c = parse_solver_output(r.text, truncated=r.truncated)
        c["id"] = cid
        c["stage"] = rec["stage"]
        c["constraint_formalization"] = formalization
        c["verification"] = verify_candidate(c, self.cfg).to_dict()
        return c

    def _solve_direct(self, problem: str, analysis: dict, rag_context: str = "", cid: str = "A") -> dict:
        r, rec = self._call(
            "solver",
            direct_solver_prompt(problem, analysis, rag_context),
            f"solve_{cid}",
        )
        c = parse_solver_output(r.text, truncated=r.truncated)
        c["id"] = cid
        c["stage"] = rec["stage"]
        v = verify_candidate(c, self.cfg).to_dict()
        c["verification"] = v
        return c

    def _solve_strategy(
        self, problem: str, analysis: dict, strategy: dict,
        rag_context: str = "", cid: str = "A",
    ) -> dict:
        r, rec = self._call(
            "solver",
            strategy_solver_prompt(problem, analysis, strategy, rag_context, cid),
            f"solve_{cid}",
        )
        c = parse_solver_output(r.text, truncated=r.truncated)
        c["id"] = cid
        c["strategy"] = strategy
        c["stage"] = rec["stage"]
        c["verification"] = verify_candidate(c, self.cfg).to_dict()
        return c

    def _rescue_missing_answer(
        self,
        problem: str,
        analysis: dict,
        previous: dict,
        cid: str = "REC1",
    ) -> dict:
        """Short second solve used only when the previous call yielded no integer answer."""
        r, rec = self._call(
            "solver",
            rescue_solver_prompt(
                problem,
                previous.get("raw_output", ""),
                analysis,
            ),
            f"solve_{cid}",
            overrides={
                "max_new_tokens": int(
                    self.cfg.get("recovery", {}).get("max_new_tokens", 900)
                ),
                # Qwen3-Instruct-2507's checkpoint generation config is sampling-based.
                "do_sample": True,
                "temperature": float(
                    self.cfg.get("recovery", {}).get("temperature", 0.7)
                ),
                "top_p": float(
                    self.cfg.get("recovery", {}).get("top_p", 0.8)
                ),
                "top_k": int(
                    self.cfg.get("recovery", {}).get("top_k", 20)
                ),
            },
        )
        c = parse_solver_output(r.text, truncated=r.truncated)
        c["id"] = cid
        c["stage"] = rec["stage"]
        c["recovery_of"] = previous.get("id")
        c["verification"] = verify_candidate(c, self.cfg).to_dict()
        return c

    def _repair_refuted_candidate(
        self,
        problem: str,
        analysis: dict,
        rejected_candidate: dict,
        refutation_evidence: str,
        rag_context: str = "",
        cid: str = "CR1",
    ) -> dict:
        r, rec = self._call(
            "solver",
            candidate_repair_after_refutation_prompt(
                problem=problem,
                analysis=analysis,
                rejected_candidate=int(rejected_candidate["candidate_answer"]),
                refutation_evidence=refutation_evidence,
                rag_context=rag_context,
            ),
            f"candidate_repair_{cid}",
            overrides={
                "max_new_tokens": int(
                    self.cfg.get("candidate_repair", {}).get("max_new_tokens", 420)
                ),
                "do_sample": True,
                "temperature": float(
                    self.cfg.get("candidate_repair", {}).get("temperature", 0.7)
                ),
                "top_p": float(self.cfg.get("candidate_repair", {}).get("top_p", 0.8)),
                "top_k": int(self.cfg.get("candidate_repair", {}).get("top_k", 20)),
                "repetition_penalty": 1.0,
            },
        )
        c = parse_solver_output(r.text, truncated=r.truncated)
        c["id"] = cid
        c["stage"] = rec["stage"]
        c["repair_of"] = rejected_candidate.get("id")
        c["repair_refutation"] = refutation_evidence[-5000:]
        self._annotate_candidate_target(c, analysis)
        c["verification"] = verify_candidate(c, self.cfg).to_dict()
        return c

    def _prove_obligation(
        self,
        problem: str,
        analysis: dict,
        candidate: dict,
        obligation: str,
        existing_evidence: str = "",
        rag_context: str = "",
        oid: str = "O1",
        use_thinking: bool = False,
    ) -> dict:
        role = "critic" if use_thinking else "solver"
        max_new = int(
            self.cfg.get("proof_completion", {}).get(
                "thinking_obligation_max_new_tokens" if use_thinking else "micro_max_new_tokens",
                900 if use_thinking else 420,
            )
        )
        prompt = obligation_proof_prompt(
            problem=problem,
            analysis=analysis,
            candidate_answer=int(candidate["candidate_answer"]),
            obligation=obligation,
            obligation_description=obligation_description(obligation),
            existing_evidence=existing_evidence,
            rag_context=rag_context,
        )
        r, rec = self._call(
            role,
            prompt,
            f"prove_{obligation}_{oid}",
            overrides={
                "max_new_tokens": max_new,
                "do_sample": bool(use_thinking),
                "temperature": float(self.cfg.get("models", {}).get(role, {}).get("temperature", 0.6 if use_thinking else 0.7)),
                "top_p": float(self.cfg.get("models", {}).get(role, {}).get("top_p", 0.95 if use_thinking else 0.8)),
                "top_k": int(self.cfg.get("models", {}).get(role, {}).get("top_k", 20)),
                "repetition_penalty": 1.0,
            },
        )
        text = r.text
        if use_thinking:
            # For the Thinking model, only its public final content is eligible as evidence.
            from .parsing import split_qwen_thinking
            split = split_qwen_thinking(r.raw_text, truncated=r.truncated)
            text = split.get("final_content", "")
            if not text:
                return {
                    "obligation": obligation,
                    "status": "UNRESOLVED",
                    "candidate_valid": "UNKNOWN",
                    "corrected_candidate": None,
                    "evidence": "",
                    "parse_ok": False,
                    "truncated": True,
                    "raw_output": r.raw_text,
                    "stage": rec["stage"],
                    "source_role": role,
                    "thinking_closed": bool(split.get("thinking_closed")),
                }
        out = parse_obligation_output(text, truncated=r.truncated)
        out["stage"] = rec["stage"]
        out["source_role"] = role
        return out

    def _deep_candidate_discovery(
        self,
        problem: str,
        analysis: dict,
        candidates: list[dict],
        rag_context: str = "",
        cid: str = "TD1",
    ) -> dict:
        prior = "\n\n".join((c.get("raw_output", "") or "")[-2500:] for c in candidates[-3:])
        r, rec = self._call(
            "critic",
            candidate_only_deep_prompt(problem, analysis, prior=prior, rag_context=rag_context),
            f"deep_candidate_{cid}",
            overrides={
                "max_new_tokens": int(self.cfg.get("deep_escalation", {}).get("candidate_max_new_tokens", 1400)),
                "do_sample": True,
                "temperature": float(self.cfg.get("deep_escalation", {}).get("temperature", 0.6)),
                "top_p": float(self.cfg.get("deep_escalation", {}).get("top_p", 0.95)),
                "top_k": int(self.cfg.get("deep_escalation", {}).get("top_k", 20)),
            },
        )
        c = parse_thinking_solver_output(r.raw_text, truncated=r.truncated)
        c["id"] = cid
        c["stage"] = rec["stage"]
        c["verification"] = verify_candidate(c, self.cfg).to_dict()
        c["deep_candidate_discovery"] = True
        return c

    def _finish_deep_candidate(
        self,
        problem: str,
        analysis: dict,
        deep_candidate: dict,
        cid: str = "TDF1",
    ) -> dict:
        source = deep_candidate.get("thinking_content") or deep_candidate.get("raw_output", "")
        r, rec = self._call(
            "solver",
            deep_candidate_finish_prompt(problem, analysis, source),
            f"deep_candidate_finish_{cid}",
            overrides={
                "max_new_tokens": int(self.cfg.get("deep_escalation", {}).get("candidate_finish_max_new_tokens", 260)),
                "do_sample": False,
                "repetition_penalty": 1.0,
            },
        )
        c = parse_solver_output(r.text, truncated=r.truncated)
        c["id"] = cid
        c["stage"] = rec["stage"]
        c["deep_finish_of"] = deep_candidate.get("id")
        c["verification"] = verify_candidate(c, self.cfg).to_dict()
        return c

    def _assemble_review_candidate(
        self,
        base: dict,
        analysis: dict,
        obligation_results: list[dict],
        cid: str = "ASM1",
    ) -> dict:
        """Deterministically aggregate proof evidence for critic review.

        This does NOT mathematically verify the answer. It only creates a complete
        machine protocol after every required obligation has focused evidence.
        """
        required = required_obligations(analysis.get("family", "general"))
        initial = assess_candidate_obligations(base, analysis.get("family", "general"))
        evidence = dict(initial.evidence)
        resolved = set(initial.present)
        for item in obligation_results:
            name = item.get("obligation")
            if item.get("status") == "PROVED" and item.get("evidence"):
                resolved.add(name)
                evidence[name] = item.get("evidence", "")

        # v2.7.2 safety rule: a proof-obligation call may REFUTE a candidate,
        # but its CORRECTED_CANDIDATE field is only a hypothesis. It is never
        # promoted here. Candidate changes must pass the dedicated repair stage.
        answer = base.get("candidate_answer")

        missing = [x for x in required if x not in resolved]
        blocks = []
        for name in required:
            ev = evidence.get(name, "")
            if ev:
                blocks.append(f"[{name}]\n{ev}")
        if base.get("proof"):
            blocks.insert(0, "[initial_solution]\n" + base.get("proof", "")[-4500:])

        assembled = {
            "id": cid,
            "stage": "assemble_for_review",
            "interpretation": base.get("interpretation", ""),
            "key_reduction": base.get("key_reduction", ""),
            "proof": "\n\n".join(blocks),
            "check": base.get("check", ""),
            "tool_requests": list(base.get("tool_requests", []) or []),
            "tool_reports": list(base.get("tool_reports", []) or []),
            "self_confidence": min(0.90, max(0.45, float(base.get("self_confidence", 0.5)))),
            "commit_answer": answer,
            "commit_parse_mode": "PIPELINE_ASSEMBLY",
            "commit_conflict": False,
            "candidate_answer": answer,
            "final_answer": "" if answer is None else str(answer),
            "answer_parse_mode": "PIPELINE_ASSEMBLED",
            "protocol_complete": bool(answer is not None and not missing),
            "truncated": False,
            "ambiguity_detected": bool(base.get("ambiguity_detected", False)),
            "ambiguity_text": base.get("ambiguity_text", ""),
            "raw_output": "PIPELINE_ASSEMBLED_FROM_FOCUSED_OBLIGATIONS",
            "parse_status": "OK" if answer is not None and not missing else "PARTIAL",
            "obligation_evidence": evidence,
            "required_obligations": required,
            "missing_obligations": missing,
            "assembled_from": base.get("id"),
            "obligation_results": obligation_results,
        }
        assembled["verification"] = verify_candidate(assembled, self.cfg).to_dict()
        return assembled

    def _complete_candidate_proof(
        self,
        problem: str,
        analysis: dict,
        base: dict,
        budget_name: str,
        accepted_context: str,
        candidates: list[dict],
    ) -> dict | None:
        """Complete proof obligations with explicit candidate invalidation/repair.

        A focused obligation is allowed to refute the current candidate, but it can
        never promote its own suggested correction. Candidate repair is a separate
        stage with target-contract validation, preventing cascades such as
        modulus -> rough upper bound -> another rough upper bound.
        """
        micro_key = f"max_micro_calls_{budget_name}"
        micro_default = {"easy": 1, "medium": 3, "hard": 4}.get(budget_name, 2)
        max_micro = int(self.cfg.get("proof_completion", {}).get(micro_key, micro_default))
        max_repairs = int(self.cfg.get("candidate_repair", {}).get("max_rounds", 1))
        rejected_values: set[int] = set()
        repair_round = 0

        while True:
            self._annotate_candidate_target(base, analysis)
            if not base.get("target_valid") or base.get("candidate_answer") is None:
                return None
            if int(base["candidate_answer"]) in rejected_values:
                return None

            assessment = assess_candidate_obligations(base, analysis.get("family", "general"))
            if repair_round == 0:
                self.proof_completion.update({
                    "base_candidate_id": base.get("id"),
                    "initial_present": assessment.present,
                    "initial_missing": assessment.missing,
                })

            obligation_results: list[dict] = []
            evidence_blob = (base.get("proof", "") or "") + "\n" + (base.get("check", "") or "")
            used_micro = 0
            refutation: dict | None = None

            for obligation in list(assessment.missing):
                if used_micro >= max_micro:
                    break
                try:
                    item = self._prove_obligation(
                        problem, analysis, base, obligation,
                        existing_evidence=evidence_blob,
                        rag_context=accepted_context,
                        oid=f"R{repair_round+1}O{used_micro+1}",
                        use_thinking=False,
                    )
                except BudgetExhausted:
                    break
                obligation_results.append(item)
                used_micro += 1
                if item.get("evidence"):
                    evidence_blob += "\n" + item["evidence"]
                if item.get("status") == "REFUTED" or item.get("candidate_valid") == "NO":
                    refutation = item
                    break

            if refutation is None:
                assembled = self._assemble_review_candidate(
                    base, analysis, obligation_results, cid=f"ASM{repair_round+1}"
                )

                if (
                    assembled.get("missing_obligations")
                    and len(assembled["missing_obligations"]) == 1
                    and bool(self.cfg.get("proof_completion", {}).get("thinking_for_last_missing", True))
                    and budget_name in {"medium", "hard"}
                ):
                    target = assembled["missing_obligations"][0]
                    try:
                        item = self._prove_obligation(
                            problem, analysis, base, target,
                            existing_evidence=evidence_blob,
                            rag_context=accepted_context,
                            oid=f"R{repair_round+1}T1",
                            use_thinking=True,
                        )
                        obligation_results.append(item)
                        if item.get("status") == "REFUTED" or item.get("candidate_valid") == "NO":
                            refutation = item
                        elif item.get("status") != "PROVED" and item.get("raw_output"):
                            try:
                                finish_item = self._prove_obligation(
                                    problem, analysis, base, target,
                                    existing_evidence=(
                                        evidence_blob + "\n" + item.get("raw_output", "")[-4500:]
                                    ),
                                    rag_context=accepted_context,
                                    oid=f"R{repair_round+1}F1",
                                    use_thinking=False,
                                )
                                obligation_results.append(finish_item)
                                if (
                                    finish_item.get("status") == "REFUTED"
                                    or finish_item.get("candidate_valid") == "NO"
                                ):
                                    refutation = finish_item
                            except BudgetExhausted:
                                pass
                    except BudgetExhausted:
                        pass

                    if refutation is None:
                        assembled = self._assemble_review_candidate(
                            base, analysis, obligation_results, cid=f"ASM{repair_round+1}"
                        )

                if refutation is None:
                    self.proof_completion["micro_results"].extend(obligation_results)
                    self.proof_completion["assembled_candidate_id"] = assembled.get("id")
                    self.proof_completion["final_missing"] = assembled.get("missing_obligations", [])
                    return assembled

            # Candidate was refuted. Mark it as dead and repair in a separate stage.
            rejected = int(base["candidate_answer"])
            rejected_values.add(rejected)
            reason = (refutation or {}).get("evidence", "") or "focused proof refuted candidate"
            base["candidate_refuted"] = True
            base["candidate_refutation_reason"] = reason
            base["verification"] = verify_candidate(base, self.cfg).to_dict()
            self.proof_completion.setdefault("refutations", []).append({
                "candidate_id": base.get("id"),
                "candidate_answer": rejected,
                "obligation": (refutation or {}).get("obligation"),
                "evidence": reason,
                "suggested_correction": (refutation or {}).get("corrected_candidate"),
            })
            self.proof_completion["micro_results"].extend(obligation_results)

            if repair_round >= max_repairs:
                self.proof_completion["final_missing"] = required_obligations(
                    analysis.get("family", "general")
                )
                return None

            try:
                repaired = self._repair_refuted_candidate(
                    problem, analysis, base, reason,
                    rag_context=accepted_context,
                    cid=f"CR{repair_round+1}",
                )
            except BudgetExhausted:
                return None
            candidates.append(repaired)
            self.proof_completion.setdefault("repair_candidates", []).append({
                "candidate_id": repaired.get("id"),
                "candidate_answer": repaired.get("candidate_answer"),
                "target_valid": repaired.get("target_valid"),
                "target_reason": (repaired.get("target_check") or {}).get("reason"),
            })

            new_answer = repaired.get("candidate_answer")
            if (
                repaired.get("target_valid") is not True
                or new_answer is None
                or int(new_answer) in rejected_values
            ):
                self.proof_completion["final_missing"] = required_obligations(
                    analysis.get("family", "general")
                )
                return None

            base = repaired
            repair_round += 1

    def _deep_solve(
        self,
        problem: str,
        analysis: dict,
        candidates: list[dict],
        rag_context: str = "",
        cid: str = "T1",
    ) -> dict:
        previous_outputs = [c.get("raw_output", "") for c in candidates]
        r, rec = self._call(
            "critic",
            deep_thinking_solver_prompt(
                problem, analysis, previous_outputs, rag_context=rag_context
            ),
            f"deep_solve_{cid}",
            overrides={
                "max_new_tokens": int(
                    self.cfg.get("deep_escalation", {}).get("max_new_tokens", 3200)
                ),
                "do_sample": True,
                "temperature": float(
                    self.cfg.get("deep_escalation", {}).get("temperature", 0.6)
                ),
                "top_p": float(
                    self.cfg.get("deep_escalation", {}).get("top_p", 0.95)
                ),
                "top_k": int(
                    self.cfg.get("deep_escalation", {}).get("top_k", 20)
                ),
            },
        )
        c = parse_thinking_solver_output(r.raw_text, truncated=r.truncated)
        c["id"] = cid
        c["stage"] = rec["stage"]
        c["verification"] = verify_candidate(c, self.cfg).to_dict()
        c["deep_escalation"] = True
        return c

    def _finish_deep_attempt(
        self,
        problem: str,
        analysis: dict,
        deep_candidate: dict,
        rag_context: str = "",
        cid: str = "TF1",
    ) -> dict:
        source = deep_candidate.get("thinking_content") or deep_candidate.get("raw_output", "")
        r, rec = self._call(
            "solver",
            deep_finish_prompt(problem, analysis, source, rag_context=rag_context),
            f"deep_finish_{cid}",
            overrides={
                "max_new_tokens": int(self.cfg.get("deep_escalation", {}).get("finish_max_new_tokens", 550)),
                "do_sample": True,
                "temperature": float(self.cfg.get("models", {}).get("solver", {}).get("temperature", 0.7)),
                "top_p": float(self.cfg.get("models", {}).get("solver", {}).get("top_p", 0.8)),
                "top_k": int(self.cfg.get("models", {}).get("solver", {}).get("top_k", 20)),
            },
        )
        c = parse_solver_output(r.text, truncated=r.truncated)
        c["id"] = cid
        c["stage"] = rec["stage"]
        c["deep_finish_of"] = deep_candidate.get("id")
        c["verification"] = verify_candidate(c, self.cfg).to_dict()
        return c

    def _best(self, candidates: list[dict]) -> dict | None:
        if not candidates:
            return None
        return max(
            candidates,
            key=lambda c: candidate_score(c, c.get("verification")),
        )

    @staticmethod
    def _exact_verified(candidates: list[dict]) -> dict | None:
        passed = [
            c for c in candidates
            if c.get("verification", {}).get("passed")
            and c.get("verification", {}).get("level") == "EXACT_TOOL"
        ]
        if not passed:
            return None
        return max(passed, key=lambda c: float(c.get("self_confidence", 0.5)))

    def _run_rag(self, retrieval_problem: str) -> dict:
        return self.rag.query(
            retrieval_problem,
            top_k=int(self.cfg.get("rag", {}).get("top_k", 8)),
        )

    def _run_critic(self, problem: str, candidates: list[dict]) -> dict:
        tool_reports = {c.get("id"): c.get("tool_reports", []) for c in candidates}
        r, rec = self._call(
            "critic",
            critic_prompt(problem, candidates, tool_reports),
            "critic",
        )
        crit = parse_critic_output(r.text, truncated=r.truncated)
        crit["stage"] = rec["stage"]
        return crit

    def _finalize(
        self,
        *,
        problem: str,
        problem_id: str,
        retrieval_problem: str,
        analysis: dict,
        difficulty: float,
        budget_name: str,
        budget_cfg: dict,
        strategies: list[dict],
        candidates: list[dict],
        rag_result: dict | None,
        critic: dict,
        verified_candidate: dict | None,
        verified_by: dict | None,
        budget_error: str | None,
        started: float,
    ) -> dict:
        valid_output_candidates = [
            c for c in candidates
            if c.get("candidate_answer") is not None
            and c.get("target_valid") is True
            and c.get("candidate_refuted") is not True
        ]
        best = verified_candidate or (
            self._best(valid_output_candidates) if valid_output_candidates else None
        )
        candidate_answer = best.get("candidate_answer") if best else None
        verified_answer = candidate_answer if verified_candidate is not None else None
        verified = verified_candidate is not None

        if verified:
            status = "VERIFIED_PASS"
        elif budget_error:
            status = "BUDGET_EXHAUSTED"
        elif candidate_answer is not None:
            status = "CANDIDATE_ONLY"
        else:
            status = "UNRESOLVED"

        snapshot = self.budget.snapshot() if self.budget else None
        verification = verified_by or (
            best.get("verification") if best else {
                "level": "NONE", "passed": False, "reason": "no candidate", "checks": []
            }
        )

        final_solution = {
            "candidate_id": best.get("id") if best else None,
            "interpretation": best.get("interpretation", "") if best else "",
            "proof": best.get("proof", "") if best else "",
            "check": best.get("check", "") if best else "",
            "candidate_answer": candidate_answer,
            "verified_answer": verified_answer,
            "final_answer": "" if candidate_answer is None else str(candidate_answer),
            "self_confidence": best.get("self_confidence", 0.0) if best else 0.0,
            "protocol_complete": best.get("protocol_complete", False) if best else False,
            "answer_parse_mode": best.get("answer_parse_mode", "NONE") if best else "NONE",
            "ambiguity_detected": best.get("ambiguity_detected", False) if best else False,
        }

        tool_reports = {c.get("id"): c.get("tool_reports", []) for c in candidates}
        return {
            "problem_id": problem_id,
            "problem": problem,
            "retrieval_problem": retrieval_problem,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "analysis": analysis,
            "target_spec": analysis.get("target_spec"),
            "difficulty": difficulty,
            "budget": {"name": budget_name, **budget_cfg},
            "rag": {
                "attempted": rag_result is not None,
                "used": bool(getattr(self, "rag_context_used", False)),
                "final": rag_result,
                "health": self.rag.health(),
            },
            "strategies": strategies,
            "constraint_formalization": getattr(self, "constraint_formalization", None),
            "semantic_compilation": getattr(self, "semantic_compilation", None),
            "semantic_exact_solution": getattr(self, "semantic_exact_solution", None),
            "family_engine": getattr(self, "family_engine_result", None),
            "proof_completion": getattr(self, "proof_completion", None),
            "candidates": candidates,
            "tool_reports": tool_reports,
            "critic": critic,
            "verification": verification,
            "candidate_answer": candidate_answer,
            "verified_answer": verified_answer,
            "final_solution": final_solution,
            "metrics": {
                "model_calls": len(self.calls),
                "input_tokens": sum(c["input_tokens"] for c in self.calls),
                "output_tokens": sum(c["output_tokens"] for c in self.calls),
                "total_tokens": sum(c["total_tokens"] for c in self.calls),
                "latency_sec": time.perf_counter() - started,
                "calls": self.calls,
                "rag_attempted": rag_result is not None,
                "rag_used": bool(getattr(self, "rag_context_used", False)),
                "verified_pass": verified,
                "verification_level": verification.get("level"),
                "budget_error": budget_error,
                "budget_snapshot": None if snapshot is None else snapshot.__dict__,
                "solver_truncations": sum(
                    1 for c in self.calls if c["role"] == "solver" and c.get("truncated")
                ),
                "critic_used": critic.get("verdict") not in {"NOT_RUN", "NOT_NEEDED"},
                "critic_parse_ok": (
                    bool(critic.get("parse_ok"))
                    if critic.get("verdict") not in {"NOT_RUN", "NOT_NEEDED"}
                    else None
                ),
                "answer_recovery_used": any(
                    c.get("recovery_of") is not None for c in candidates
                ),
                "candidate_answers": [
                    c.get("candidate_answer") for c in candidates
                ],
                "candidate_parse_modes": [
                    c.get("answer_parse_mode") for c in candidates
                ],
                "candidate_target_validity": [
                    c.get("target_valid") for c in candidates
                ],
                "candidate_target_reasons": [
                    (c.get("target_check") or {}).get("reason") for c in candidates
                ],
                "rejected_candidate_values": [
                    c.get("candidate_answer") for c in candidates
                    if c.get("candidate_answer") is not None
                    and (c.get("target_valid") is False or c.get("candidate_refuted") is True)
                ],
                "candidate_committed_early": any(
                    c.get("commit_parse_mode") == "EARLY_COMMIT" for c in candidates
                ),
                "answer_commit_survived_truncation": any(
                    c.get("commit_parse_mode") == "EARLY_COMMIT" and c.get("truncated")
                    for c in candidates
                ),
                "proof_obligations_required": (
                    getattr(self, "proof_completion", {}) or {}
                ).get("required", []),
                "proof_obligations_initial_missing": (
                    getattr(self, "proof_completion", {}) or {}
                ).get("initial_missing", []),
                "proof_obligations_final_missing": (
                    getattr(self, "proof_completion", {}) or {}
                ).get("final_missing", []),
                "proof_micro_calls": len(
                    (getattr(self, "proof_completion", {}) or {}).get("micro_results", [])
                ),
                "constraint_first_used": getattr(self, "constraint_formalization", None) is not None,
                "constraint_formalization_ok": formalization_is_usable(
                    getattr(self, "constraint_formalization", None) or {}
                ),
                "semantic_compilation_ok": bool(
                    getattr(self, "semantic_compilation", None)
                    and getattr(self, "semantic_compilation", {}).get("ok")
                ),
                "semantic_certificate_ok": semantic_certificate_ok(
                    getattr(self, "semantic_compilation", None) or {}
                ),
                "semantic_repairs": int(getattr(self, "semantic_repairs", 0)),
                "deterministic_semantic_solve": bool(
                    getattr(self, "semantic_exact_solution", None)
                    and getattr(self, "semantic_exact_solution", {}).get("unique_answer")
                ),
                "deterministic_family_solve": bool(
                    getattr(self, "family_engine_result", None)
                    and getattr(self, "family_engine_result", {}).get("ok")
                ),
                "family_engine_name": (getattr(self, "family_engine_result", None) or {}).get("engine"),
                "hard_retry_after_refutation": any(
                    bool(c.get("hard_retry_after_refutation")) for c in candidates
                ),
            },
            "status": status,
        }

    def run(self, problem: str, problem_id: str = "problem_001", retrieval_problem: str | None = None) -> dict:
        started = time.perf_counter()
        self.calls = []
        retrieval_problem = retrieval_problem or problem
        analysis = self._analysis_dict(retrieval_problem)
        difficulty_raw = estimate_difficulty(retrieval_problem, analysis)
        difficulty = apply_family_difficulty_floor(difficulty_raw, analysis)
        analysis["difficulty_raw"] = difficulty_raw
        analysis["difficulty_after_family_floor"] = difficulty
        budget_name, budget_cfg = choose_budget(self.cfg, difficulty)
        self.budget = BudgetManager(budget_cfg)

        strategies: list[dict] = []
        candidates: list[dict] = []
        rag_result = None
        self.rag_context_used = False
        self.constraint_formalization = None
        self.semantic_compilation = None
        self.semantic_exact_solution = None
        self.semantic_repairs = 0
        self.family_engine_result = None
        self.proof_completion = {
            "required": required_obligations(analysis.get("family", "general")),
            "base_candidate_id": None,
            "initial_present": [],
            "initial_missing": [],
            "micro_results": [],
            "refutations": [],
            "repair_candidates": [],
            "assembled_candidate_id": None,
            "final_missing": [],
        }
        critic = {
            "verdict": "NOT_RUN", "confidence": 0.0, "parse_ok": None,
            "summary": "no viable candidate has required critic review yet",
            "error": "", "revision_instruction": "",
        }
        verified_candidate = None
        verified_by = None
        budget_error = None

        try:
            # 0) Deterministic family engines run before any LLM call. They are
            # fail-closed: an engine may recognize a family yet decline exact
            # certification. Only a mechanically certified exact result can stop early.
            if bool(self.cfg.get("family_engines", {}).get("enabled", True)):
                fam = try_family_engine(problem, analysis, analysis.get("target_spec"))
                self.family_engine_result = fam.to_dict()
                if fam.ok and fam.answer is not None:
                    c = family_engine_candidate(fam, analysis.get("target_spec"), cid="FAM1")
                    self._annotate_candidate_target(c, analysis)
                    if c.get("target_valid") is True:
                        c["verification"] = {
                            "level": "FAMILY_EXACT",
                            "passed": True,
                            "reason": fam.reason or "deterministic family certificate passed",
                            "checks": [
                                {"type": "family_engine", "passed": True, "engine": fam.engine},
                                {"type": "family_certificate", "passed": True, "certificate": fam.certificate},
                                {"type": "target_contract", "passed": True, "target_spec": analysis.get("target_spec")},
                            ],
                        }
                        candidates.append(c)
                        critic = {
                            "verdict": "NOT_NEEDED", "confidence": None, "parse_ok": None,
                            "summary": f"FAMILY_EXACT verification passed via {fam.engine}",
                            "error": "", "revision_instruction": "",
                        }
                        verified_by = c["verification"]
                        return self._finalize(
                            problem=problem, problem_id=problem_id, retrieval_problem=retrieval_problem,
                            analysis=analysis, difficulty=difficulty, budget_name=budget_name,
                            budget_cfg=budget_cfg, strategies=strategies, candidates=candidates,
                            rag_result=rag_result, critic=critic, verified_candidate=c,
                            verified_by=verified_by, budget_error=None, started=started,
                        )

            # 1) Strategy stage only for medium/hard.
            if budget_cfg.get("use_proposer", False):
                target_n = 3 if budget_name == "hard" else 2
                r, _ = self._call(
                    "proposer",
                    strategy_proposer_prompt(problem, analysis, target_n=target_n),
                    "propose_strategies",
                )
                strategies = parse_strategy_output(r.text, target_n=target_n)
                if not strategies:
                    strategies = [{
                        "id": "S1", "name": "Direct reasoning",
                        "core_idea": "Translate constraints carefully and solve directly.",
                        "why_it_fits": "fallback strategy", "risks": "none", "confidence": 0.5,
                    }]

            # 2) First solve(s), WITHOUT RAG.
            # Short relational algebra word problems get a compact constraint pass first.
            # This prevents a long solver generation from spending its entire budget
            # debating the English wording, which happened in the real Problem 1 run.
            attempts = int(budget_cfg.get("initial_solver_attempts", 1))
            constraint_first = bool(
                self.cfg.get("constraint_first", {}).get("enabled", False)
                and budget_name == "easy"
                and should_use_constraint_first(problem, analysis)
            )

            if constraint_first:
                self.constraint_formalization = self._extract_constraints(problem)

                if formalization_is_usable(self.constraint_formalization):
                    det, compiled, solved = self._deterministic_semantic_candidate(
                        problem, self.constraint_formalization
                    )
                    self.semantic_compilation = compiled
                    self.semantic_exact_solution = solved

                    # If syntax was valid but the deterministic semantic validator rejects
                    # the structure, repair the SEMANTICS once before any solver/RAG call.
                    if (
                        det is None
                        and not compiled.get("ok", False)
                        and int(self.cfg.get("constraint_first", {}).get("max_repairs", 1)) > 0
                    ):
                        errors = [c for c in compiled.get("checks", []) if c.get("passed") is False]
                        try:
                            repaired = self._repair_semantic_formalization(
                                problem, self.constraint_formalization, errors
                            )
                            self.semantic_repairs += 1
                            self.constraint_formalization = repaired
                            if formalization_is_usable(repaired):
                                det, compiled, solved = self._deterministic_semantic_candidate(
                                    problem, repaired
                                )
                                self.semantic_compilation = compiled
                                self.semantic_exact_solution = solved
                        except BudgetExhausted:
                            det = None

                    if det is not None:
                        candidates.append(det)
                    elif self.semantic_compilation and self.semantic_compilation.get("ok"):
                        # Semantic structure is validated but exact symbolic solving did not
                        # settle the goal; only then ask Qwen to reason from compiled constraints.
                        working = {
                            "constraints": self.semantic_compilation.get("equations", []),
                            "goal": self.semantic_compilation.get("goal_expr", ""),
                            "ambiguity": "NONE",
                        }
                        candidates.append(self._solve_from_constraints(problem, working, cid="CF1"))
                    else:
                        # Validator still rejects the semantic structure after one repair.
                        # One direct solve is safer than repeatedly solving poisoned equations.
                        candidates.append(self._solve_direct(problem, analysis, cid="A"))
                else:
                    candidates.append(self._solve_direct(problem, analysis, cid="A"))
            elif budget_name == "easy":
                candidates.append(self._solve_direct(problem, analysis, cid="A"))
            else:
                for i in range(attempts):
                    cid = chr(ord("A") + i)
                    if strategies:
                        strategy = strategies[min(i, len(strategies) - 1)]
                        candidates.append(self._solve_strategy(
                            problem, analysis, strategy, cid=cid
                        ))
                    else:
                        candidates.append(self._solve_direct(problem, analysis, cid=cid))

            # Ground every candidate against the ACTUAL requested-output contract
            # before it is allowed to steer recovery/proof completion. In particular,
            # a remainder problem must never treat the modulus itself as a viable answer.
            self._annotate_candidates_target(candidates, analysis)

            # 2b) Recovery for a missing OR target-invalid answer BEFORE RAG.
            # A simple formatting/target-grounding failure should not poison later proof calls.
            best_initial = self._best(candidates)
            if (
                best_initial is not None
                and not self._valid_viable_candidates(candidates)
                and bool(self.cfg.get("recovery", {}).get("enabled", True))
            ):
                try:
                    if self.semantic_compilation is not None and self.semantic_compilation.get("ok"):
                        working = {
                            "constraints": self.semantic_compilation.get("equations", []),
                            "goal": self.semantic_compilation.get("goal_expr", ""),
                            "ambiguity": "NONE",
                        }
                        candidates.append(self._solve_from_constraints(problem, working, cid="CF2"))
                    else:
                        candidates.append(
                            self._rescue_missing_answer(
                                problem,
                                analysis,
                                best_initial,
                                cid="REC1",
                            )
                        )
                except BudgetExhausted:
                    pass

            self._annotate_candidates_target(candidates, analysis)

            # A supported semantic template can be certified without an LLM critic when:
            # (1) text-derived event/relation cross-checks pass, (2) transfer conservation
            # passes, (3) SymPy finds a unique integer goal value, and (4) the answer-bound
            # exact equality certificate passes. This is much stronger than a random true identity.
            det_exact = next((
                c for c in candidates
                if c.get("id") == "DET1"
                and c.get("verification", {}).get("passed")
                and c.get("verification", {}).get("level") == "EXACT_TOOL"
            ), None)
            if (
                det_exact is not None
                and bool(self.cfg.get("verification", {}).get("accept_semantic_exact_without_critic", True))
                and semantic_certificate_ok(self.semantic_compilation or {})
            ):
                verified_candidate = det_exact
                critic = {
                    "verdict": "NOT_NEEDED", "confidence": None, "parse_ok": None,
                    "summary": "SEMANTIC_EXACT verification already passed",
                    "error": "", "revision_instruction": "",
                }
                verified_by = {
                    "level": "SEMANTIC_EXACT",
                    "passed": True,
                    "reason": "text-crosschecked semantic compiler + unique exact integer solution",
                    "checks": (self.semantic_compilation or {}).get("checks", [])
                    + det_exact.get("verification", {}).get("checks", []),
                }
                return self._finalize(
                    problem=problem, problem_id=problem_id, retrieval_problem=retrieval_problem,
                    analysis=analysis, difficulty=difficulty, budget_name=budget_name,
                    budget_cfg=budget_cfg, strategies=strategies, candidates=candidates,
                    rag_result=rag_result, critic=critic, verified_candidate=verified_candidate,
                    verified_by=verified_by, budget_error=None, started=started,
                )

            # Exact deterministic verification gets immediate early stop only under the
            # general policy; v2.6.4 keeps it false by default except for SEMANTIC_EXACT.
            exact = self._exact_verified(candidates)
            if exact and self.cfg.get("verification", {}).get("accept_exact_tool_without_critic", True):
                verified_candidate = exact
                verified_by = exact["verification"]
                return self._finalize(
                    problem=problem, problem_id=problem_id, retrieval_problem=retrieval_problem,
                    analysis=analysis, difficulty=difficulty, budget_name=budget_name,
                    budget_cfg=budget_cfg, strategies=strategies, candidates=candidates,
                    rag_result=rag_result, critic=critic, verified_candidate=verified_candidate,
                    verified_by=verified_by, budget_error=None, started=started,
                )

            # 3) Conditional RAG is retrieval-only in v2.7.1.
            # We no longer spend a full solver call re-solving from RAG. Accepted
            # context is injected only into focused proof obligations or deep
            # candidate discovery.
            best = self._best(candidates)
            disagreement = answer_disagreement(candidates)
            accepted_context = ""
            allow_rag = not (
                budget_name == "easy" and self.constraint_formalization is not None
            )
            if best and allow_rag and should_trigger_rag(self.cfg, best, disagreement=disagreement):
                rag_result = self._run_rag(retrieval_problem)
                gate = rag_result.get("gate", {}).get("status")
                if gate == "ACCEPT" and rag_result.get("context"):
                    accepted_context = rag_result.get("context", "")

            # 4) If no numeric candidate exists, discover ONLY the candidate rather
            # than asking the Thinking model to write a full olympiad proof. This
            # prevents a 3k-token hidden chain from consuming the whole time budget.
            self._annotate_candidates_target(candidates, analysis)
            viable = self._valid_viable_candidates(candidates)
            if (
                not viable
                and bool(self.cfg.get("deep_escalation", {}).get("enabled", True))
                and budget_name in set(self.cfg.get("deep_escalation", {}).get("budgets", ["medium", "hard"]))
            ):
                try:
                    if accepted_context:
                        self.rag_context_used = True
                    deep = self._deep_candidate_discovery(
                        problem, analysis, candidates,
                        rag_context=accepted_context,
                        cid="TD1",
                    )
                    candidates.append(deep)
                    if (
                        deep.get("candidate_answer") is None
                        and bool(self.cfg.get("deep_escalation", {}).get("finish_with_instruct", True))
                    ):
                        try:
                            candidates.append(
                                self._finish_deep_candidate(
                                    problem, analysis, deep, cid="TDF1"
                                )
                            )
                        except BudgetExhausted:
                            pass
                except BudgetExhausted:
                    pass
                self._annotate_candidates_target(candidates, analysis)
                viable = self._valid_viable_candidates(candidates)

            # 4b) Target-grounded commit-and-verify. Only candidates that satisfy
            # the actual requested-output contract can enter proof completion.
            complete_viable_before_proof = [
                c for c in viable
                if c.get("protocol_complete") is True
                and c.get("truncated") is not True
                and c.get("ambiguity_detected") is not True
                and c.get("target_valid") is True
                and c.get("candidate_refuted") is not True
            ]
            if (
                viable
                and not complete_viable_before_proof
                and bool(self.cfg.get("proof_completion", {}).get("enabled", True))
            ):
                if accepted_context:
                    self.rag_context_used = True
                base = max(
                    viable,
                    key=lambda c: candidate_progress_score(c, analysis.get("family", "general")),
                )
                assembled = self._complete_candidate_proof(
                    problem=problem,
                    analysis=analysis,
                    base=base,
                    budget_name=budget_name,
                    accepted_context=accepted_context,
                    candidates=candidates,
                )
                if assembled is not None:
                    self._annotate_candidate_target(assembled, analysis)
                    assembled["verification"] = verify_candidate(assembled, self.cfg).to_dict()
                    candidates.append(assembled)
                elif (
                    budget_name == "hard"
                    and bool(self.cfg.get("hard_hybrid_retry", {}).get("enabled", True))
                    and bool((self.proof_completion or {}).get("refutations"))
                ):
                    # v2.10: after a cheap candidate and its repair are both
                    # refuted, spend one genuine Thinking solve on the original
                    # problem instead of terminating on a sequence of guesses.
                    # This is deliberately escalation-only and therefore does not
                    # tax easy/medium or deterministic-family problems.
                    try:
                        if accepted_context:
                            self.rag_context_used = True
                        deep_retry = self._deep_solve(
                            problem, analysis, candidates,
                            rag_context=accepted_context, cid="HR1",
                        )
                        deep_retry["hard_retry_after_refutation"] = True
                        candidates.append(deep_retry)
                        self._annotate_candidate_target(deep_retry, analysis)

                        retry_base = deep_retry
                        if (
                            deep_retry.get("candidate_answer") is None
                            and bool(self.cfg.get("hard_hybrid_retry", {}).get("finish_with_instruct", True))
                        ):
                            try:
                                finished = self._finish_deep_attempt(
                                    problem, analysis, deep_retry,
                                    rag_context=accepted_context, cid="HRF1",
                                )
                                finished["hard_retry_after_refutation"] = True
                                candidates.append(finished)
                                self._annotate_candidate_target(finished, analysis)
                                if finished.get("target_valid") is True:
                                    retry_base = finished
                            except BudgetExhausted:
                                pass

                        if (
                            retry_base.get("candidate_answer") is not None
                            and retry_base.get("target_valid") is True
                            and retry_base.get("candidate_refuted") is not True
                        ):
                            retry_assembled = self._complete_candidate_proof(
                                problem=problem, analysis=analysis, base=retry_base,
                                budget_name=budget_name, accepted_context=accepted_context,
                                candidates=candidates,
                            )
                            if retry_assembled is not None:
                                retry_assembled["hard_retry_after_refutation"] = True
                                self._annotate_candidate_target(retry_assembled, analysis)
                                retry_assembled["verification"] = verify_candidate(
                                    retry_assembled, self.cfg
                                ).to_dict()
                                candidates.append(retry_assembled)
                    except BudgetExhausted:
                        pass

            # Only candidates with a complete machine protocol are eligible for a
            # final critic PASS. Early commits remain visible as CANDIDATE_ONLY but
            # cannot be promoted merely because a model guessed the right integer.
            reviewable = [
                c for c in candidates
                if c.get("candidate_answer") is not None
                and c.get("target_valid") is True
                and c.get("candidate_refuted") is not True
                and c.get("protocol_complete") is True
                and c.get("ambiguity_detected") is not True
                and c.get("truncated") is not True
            ]
            # 5) Final critic reviews only protocol-complete candidates.
            if reviewable:
                critic = self._run_critic(problem, reviewable)
                threshold = float(self.cfg["controller"].get("critic_pass_threshold", 0.88))
                best_id = critic.get("best_candidate_id")
                selected = next((c for c in reviewable if c.get("id") == best_id), None) if best_id else None
                cv = critic_verification(critic, threshold, selected_candidate=selected).to_dict()
                if cv["passed"]:
                    if selected and selected.get("candidate_answer") is not None:
                        verified_candidate = selected
                        verified_by = cv
                        return self._finalize(
                            problem=problem, problem_id=problem_id, retrieval_problem=retrieval_problem,
                            analysis=analysis, difficulty=difficulty, budget_name=budget_name,
                            budget_cfg=budget_cfg, strategies=strategies, candidates=candidates,
                            rag_result=rag_result, critic=critic, verified_candidate=verified_candidate,
                            verified_by=verified_by, budget_error=None, started=started,
                        )

                # 5) One targeted revision, not an unlimited loop.
                if (
                    critic.get("verdict") == "REVISE"
                    and int(budget_cfg.get("max_revisions", 1)) > 0
                    and critic.get("thinking_status") != "TRUNCATED_THINKING"
                ):
                    best = selected or self._best(reviewable)
                    if best:
                        r, rec = self._call(
                            "solver",
                            revision_prompt(
                                problem, best, critic,
                                rag_result.get("context", "") if (rag_result and rag_result.get("gate", {}).get("status") == "ACCEPT") else "",
                            ),
                            "revision_1",
                        )
                        revised = parse_solver_output(r.text, truncated=r.truncated)
                        revised["id"] = "REV1"
                        revised["stage"] = rec["stage"]
                        self._annotate_candidate_target(revised, analysis)
                        revised["verification"] = verify_candidate(revised, self.cfg).to_dict()
                        candidates.append(revised)

                        auto_accept_exact = bool(
                            self.cfg.get("verification", {}).get("accept_exact_tool_without_critic", False)
                        )
                        if revised["verification"].get("passed") and auto_accept_exact:
                            verified_candidate = revised
                            verified_by = revised["verification"]
                        else:
                            # Exact arithmetic evidence is not a semantic proof by itself.
                            # Re-critic the revised candidate unless the configured policy explicitly
                            # allows answer-bound exact certificates to auto-pass.
                            try:
                                critic2 = self._run_critic(problem, [revised])
                                selected2 = revised if critic2.get("best_candidate_id") == revised.get("id") else None
                                cv2 = critic_verification(
                                    critic2,
                                    float(self.cfg["controller"].get("critic_pass_threshold", 0.88)),
                                    selected_candidate=selected2,
                                ).to_dict()
                                critic = critic2
                                if cv2["passed"] and revised.get("candidate_answer") is not None:
                                    verified_candidate = revised
                                    verified_by = cv2
                            except BudgetExhausted:
                                pass

        except BudgetExhausted as e:
            budget_error = str(e)

        return self._finalize(
            problem=problem, problem_id=problem_id, retrieval_problem=retrieval_problem,
            analysis=analysis, difficulty=difficulty, budget_name=budget_name,
            budget_cfg=budget_cfg, strategies=strategies, candidates=candidates,
            rag_result=rag_result, critic=critic, verified_candidate=verified_candidate,
            verified_by=verified_by, budget_error=budget_error, started=started,
        )
