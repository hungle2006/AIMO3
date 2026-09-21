from __future__ import annotations

from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from core.config import load_config, prepare_environment
from core.pipeline import FullOlympiadPipeline
from core.reporting import save_result
from core.input_adapter import AIMOInputAdapter
from core.answer_contract import AIMO3AnswerContract
from core.evaluation import benchmark_record


def main():
    ap = argparse.ArgumentParser(description="Run v2.10 reasoner on CSV/PDF/TXT input.")
    ap.add_argument("--input", required=True)
    ap.add_argument("--config", default=str(ROOT / "config_v2_11_0.yaml"))
    ap.add_argument("--problem-number", type=int, default=None)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--benchmark-reference", action="store_true")
    ap.add_argument("--preload", action="store_true")
    ap.add_argument("--inspect-only", action="store_true")
    ap.add_argument("--engine-only", action="store_true", help="Run deterministic family engines only; no transformers/GPU required.")
    args = ap.parse_args()

    problems = AIMOInputAdapter.load(args.input, benchmark_mode=args.benchmark_reference)
    if args.problem_number is not None:
        problems = [
            p for p in problems
            if (p.metadata or {}).get("problem_number") == args.problem_number
        ]
        if not problems:
            raise SystemExit(f"Problem {args.problem_number} not found")
    elif not args.all:
        problems = problems[:1]

    print(f"Parsed {len(problems)} selected problem(s).")
    for p in problems:
        meta = p.metadata or {}
        print(
            f"- {p.problem_id}: pages={meta.get('page_start')}-{meta.get('page_end')} "
            f"engine={meta.get('extraction_engine')} "
            f"statement_visual={meta.get('has_statement_images', False)}"
        )

    if args.inspect_only:
        for p in problems:
            print("\n" + "=" * 80)
            print(p.problem_id)
            print("[layout/display text]")
            print(p.problem_text)
            print("\n[solver text]")
            print(p.solver_text)
            print("solver_text_source:", (p.metadata or {}).get("solver_text_source"))
            if args.benchmark_reference:
                print("[held-out expected answer]", p.expected_answer)
        return

    if args.engine_only:
        from core.family_engines import try_family_engine
        rows = []
        for p in problems:
            analysis = FullOlympiadPipeline._analysis_dict(p.semantic_text)
            out = try_family_engine(p.solver_text, analysis, analysis.get("target_spec"))
            row = {
                "problem_id": p.problem_id,
                "family": analysis.get("family"),
                "supported": out.supported,
                "ok": out.ok,
                "engine": out.engine,
                "raw_value": out.raw_value,
                "answer": out.answer,
                "reason": out.reason,
                "expected_answer": p.expected_answer if args.benchmark_reference else None,
                "correct": (out.answer == p.expected_answer) if (args.benchmark_reference and out.answer is not None) else None,
                "certificate": out.certificate,
            }
            rows.append(row)
            print("\n" + "=" * 80)
            print(p.problem_id, "family=", row["family"], "engine=", out.engine)
            print("supported:", out.supported, "ok:", out.ok)
            print("raw value:", out.raw_value, "answer:", out.answer)
            print("reason:", out.reason)
            if args.benchmark_reference:
                print("expected:", p.expected_answer, "correct:", row["correct"])
        out_path = Path("/kaggle/working/family_engine_summary.json") if Path("/kaggle/working").exists() else ROOT / "family_engine_summary.json"
        out_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
        print("\nSaved engine summary:", out_path)
        return

    cfg = load_config(args.config)
    prepare_environment(cfg)
    # Lazy import keeps --inspect-only usable in lightweight CPU environments
    # where transformers/bitsandbytes are intentionally not installed.
    from core.model_manager import ModelManager
    manager = ModelManager(cfg)
    # Construct the orchestration object before expensive GPU preload so
    # Python/configuration errors fail fast instead of wasting model-load time.
    pipe = FullOlympiadPipeline(cfg, manager)
    if args.preload:
        manager.preload()

    summary = []
    for p in problems:
        result = pipe.run(
            p.solver_text,
            problem_id=p.problem_id,
            retrieval_problem=p.semantic_text,
        )
        # Keep the layout/plain extraction only for audit. The model sees solver_text.
        meta = p.metadata or {}
        result["input_fidelity"] = {
            "solver_text_source": (p.metadata or {}).get("solver_text_source", "unknown"),
            "layout_differs_from_solver": p.problem_text.strip() != p.solver_text.strip(),
            "layout_problem": p.problem_text,
            "solver_problem": p.solver_text,
            "raw_semantic_problem": meta.get("raw_semantic_text"),
            "math_recovery": meta.get("math_recovery"),
        }
        result["input_metadata"] = {
            "source": str(args.input),
            "type": Path(args.input).suffix.lower(),
            "problem_number": meta.get("problem_number"),
            "page_start": meta.get("page_start"),
            "page_end": meta.get("page_end"),
            "extraction_engine": meta.get("extraction_engine"),
            "has_statement_images": meta.get("has_statement_images", False),
            "solver_text_source": meta.get("solver_text_source"),
        }

        candidate_check = AIMO3AnswerContract.check(result.get("candidate_answer"))
        verified_check = AIMO3AnswerContract.check(result.get("verified_answer"))
        result["aimo_answer_contract"] = {
            "candidate": {
                "valid": candidate_check.valid,
                "value": candidate_check.value,
                "reason": candidate_check.reason,
            },
            "verified": {
                "valid": verified_check.valid,
                "value": verified_check.value,
                "reason": verified_check.reason,
            },
        }

        if args.benchmark_reference and p.expected_answer is not None:
            result["benchmark"] = benchmark_record(result, p.expected_answer)

        save_result(result, cfg["project"]["output_dir"])
        row = {
            "problem_id": p.problem_id,
            "status": result["status"],
            "candidate_answer": candidate_check.value,
            "verified_answer": verified_check.value,
            "verification": result.get("verification", {}).get("level"),
            "expected_answer": p.expected_answer if args.benchmark_reference else None,
            "candidate_correct": result.get("benchmark", {}).get("candidate_correct") if args.benchmark_reference else None,
            "verified_correct": result.get("benchmark", {}).get("verified_correct") if args.benchmark_reference else None,
            "verification_false_positive": result.get("benchmark", {}).get("verification_false_positive") if args.benchmark_reference else None,
            "candidate_correct_but_unverified": result.get("benchmark", {}).get("candidate_correct_but_unverified") if args.benchmark_reference else None,
            "model_calls": result["metrics"].get("model_calls"),
            "tokens": result["metrics"].get("total_tokens"),
            "latency_sec": result["metrics"].get("latency_sec"),
        }
        summary.append(row)

        print("\n" + "=" * 80)
        print(p.problem_id)
        print("status:", result["status"])
        print("candidate answer:", candidate_check.value)
        print("verified answer:", verified_check.value)
        print("verification:", result.get("verification", {}).get("level"))
        if args.benchmark_reference:
            print("expected:", p.expected_answer)
            print("candidate correct:", row["candidate_correct"])
            print("verified correct:", row["verified_correct"])
            print("verification false positive:", row["verification_false_positive"])

    out = Path(cfg["project"]["output_dir"]) / "pdf_batch_summary.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("\nSaved summary:", out)


if __name__ == "__main__":
    main()
