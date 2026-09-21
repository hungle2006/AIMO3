from pathlib import Path
import subprocess, sys, os

ROOT = Path(__file__).resolve().parents[1]
TESTS = [
    'test_parsing.py','test_tools.py','test_safe_tools.py','test_verification_guards.py',
    'test_budget.py','test_generation_budget.py','test_evaluation.py','test_rag_runtime.py',
    'test_pipeline_problem1_mock.py','test_recovery_pipeline.py','test_constraint_parser.py',
    'test_semantic_compiler_guards.py','test_semantic_repair_pipeline.py',
    'test_implicit_ambiguity.py','test_constraint_first_pipeline.py','test_pdf_reader.py',
    'test_deep_escalation_v27.py','test_deep_finish_v27.py','test_rag_refinement_v27.py','test_thinking_solver_parser_v27.py','test_problem_family_v27.py',
    'test_pdf_math_fidelity_v27.py',
    'test_commit_parser_v271.py','test_rag_dominance_v271.py',
    'test_commit_verify_pipeline_v271.py','test_deep_candidate_v271.py',
    'test_target_grounding_v272.py','test_invalid_modulus_commit_v272.py','test_refutation_repair_v272.py',
    'test_family_engine_extremal_v280.py','test_family_engine_functional_v280.py','test_family_engine_tournament_v280.py',
    'test_family_engine_fail_closed_v280.py','test_pipeline_family_exact_v280.py','test_pipeline_family_exact_all_v280.py',
    'test_run_pdf_scope_v281.py','test_run_pdf_normal_path_v281.py',
    'test_family_engine_geometry_v290.py','test_family_engine_geometry_fail_closed_v290.py','test_pipeline_family_exact_geometry_v290.py',
    'test_pdf_math_recovery_v210.py','test_family_engine_asymptotic_v210.py','test_family_engine_asymptotic_fail_closed_v210.py',
    'test_pipeline_family_exact_asymptotic_v210.py','test_hard_retry_after_refutation_v210.py',
    'test_family_engine_floor_v211.py','test_family_engine_digit_dynamics_v211.py',
    'test_family_engine_correlation_v211.py','test_family_engine_norwegian_v211.py',
    'test_family_engines_fail_closed_v211.py','test_pdf_math_recovery_p9_v211.py',
    'test_pipeline_exact_hard_families_v211.py','test_problem_family_v211.py','test_pdf_reference_exact_v211.py',
]

failed=[]
for name in TESTS:
    try:
        p=subprocess.run(
            [sys.executable, str(ROOT/'tests'/name)],
            env=os.environ.copy(),
            timeout=45,
            capture_output=True,
            text=True,
        )
        if p.stdout:
            print(p.stdout.rstrip())
        if p.returncode != 0:
            failed.append(name)
            if p.stderr:
                print(p.stderr.rstrip(), file=sys.stderr)
    except subprocess.TimeoutExpired:
        failed.append(name)
        print(f'{name}: TIMEOUT after 45s', file=sys.stderr)

if failed:
    raise SystemExit('FAILED: '+', '.join(failed))
print('ALL V2.11.0 TESTS PASS')
