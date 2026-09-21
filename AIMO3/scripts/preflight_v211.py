from __future__ import annotations
from pathlib import Path
import argparse, os, subprocess, sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

CORE_TESTS=[
    'test_verification_guards.py',
    'test_target_grounding_v272.py',
    'test_pdf_math_recovery_p9_v211.py',
    'test_family_engines_fail_closed_v211.py',
    'test_pipeline_exact_hard_families_v211.py',
    'test_problem_family_v211.py',
]

def run_test(name:str, env:dict):
    p=subprocess.run([sys.executable,str(ROOT/'tests'/name)],env=env,text=True,capture_output=True,timeout=90)
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
        for n in range(2,11):
            r=by[n]
            a=FullOlympiadPipeline._analysis_dict(r.semantic_text)
            out=try_family_engine(r.semantic_text,a,a.get('target_spec'))
            if not (out.ok and out.answer==r.expected_answer):
                raise SystemExit(f'PDF exact-engine check failed for P{n}: {out.to_dict()} expected={r.expected_answer}')
            print(f'P{n}: {out.engine} -> {out.answer} PASS')
        p9=by[9]
        rec=p9.math_recovery or {}
        if 'p9_bilateral_sum' not in rec.get('rules',[]):
            raise SystemExit(f'P9 math recovery did not reconstruct bilateral sum: {rec}')
        print('P9 math recovery bilateral-sum guard: PASS')
    print('v2.11.0 PREFLIGHT PASS')

if __name__=='__main__':
    main()
