from __future__ import annotations
from pathlib import Path
import argparse, os, subprocess, sys, json

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

CORE_TESTS=[
    'test_verification_guards.py',
    'test_target_grounding_v272.py',
    'test_family_engine_geometry_v290.py',
    'test_pdf_math_recovery_v210.py',
    'test_family_engine_asymptotic_v210.py',
    'test_family_engine_asymptotic_fail_closed_v210.py',
    'test_pipeline_family_exact_asymptotic_v210.py',
    'test_hard_retry_after_refutation_v210.py',
]

def run_test(name:str, env:dict):
    p=subprocess.run([sys.executable,str(ROOT/'tests'/name)],env=env,text=True,capture_output=True,timeout=60)
    if p.stdout: print(p.stdout.rstrip())
    if p.returncode:
        if p.stderr: print(p.stderr.rstrip(),file=sys.stderr)
        raise SystemExit(f'FAILED: {name}')

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--pdf',default=None)
    args=ap.parse_args()
    env=os.environ.copy()
    if args.pdf:
        env['AIMO_REFERENCE_PDF']=str(Path(args.pdf).resolve())
    for t in CORE_TESTS:
        run_test(t,env)

    if args.pdf:
        from core.pdf_reader import AIMOReferencePDFReader
        from core.pipeline import FullOlympiadPipeline
        from core.family_engines import try_family_engine
        rs=AIMOReferencePDFReader(args.pdf,benchmark_mode=True).read()
        by={r.problem_number:r for r in rs}
        for n in (2,3,4,5,7):
            r=by[n]
            a=FullOlympiadPipeline._analysis_dict(r.semantic_text)
            out=try_family_engine(r.semantic_text,a,a.get('target_spec'))
            if not (out.ok and out.answer==r.expected_answer):
                raise SystemExit(f'PDF engine check failed for P{n}: {out.to_dict()} expected={r.expected_answer}')
            print(f'P{n}: {out.engine} -> {out.answer} PASS')
        for n in (6,7,8,9,10):
            rec=by[n].math_recovery or {}
            print(f'P{n} math recovery: applied={rec.get("applied")} rules={rec.get("rules")}')
    print('v2.10.0 PREFLIGHT PASS')

if __name__=='__main__':
    main()
