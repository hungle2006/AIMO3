from __future__ import annotations
from pathlib import Path
import argparse, os, subprocess, sys

ROOT=Path(__file__).resolve().parents[1]

def run(cmd, env=None):
    print('+',' '.join(map(str,cmd)))
    p=subprocess.run(cmd,cwd=ROOT,env=env)
    if p.returncode:
        raise SystemExit(p.returncode)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--pdf',default='')
    args=ap.parse_args()
    required=['config_v2_8_1.yaml','core/family_engines.py','run_pdf_pipeline.py']
    for rel in required:
        p=ROOT/rel
        if not p.exists(): raise SystemExit(f'MISSING: {p}')
    tests=[
        'test_run_pdf_scope_v281.py',
        'test_run_pdf_normal_path_v281.py',
        'test_family_engine_extremal_v280.py',
        'test_family_engine_functional_v280.py',
        'test_family_engine_tournament_v280.py',
        'test_family_engine_fail_closed_v280.py',
        'test_pipeline_family_exact_all_v280.py',
        'test_target_grounding_v272.py',
        'test_verification_guards.py',
    ]
    env=os.environ.copy()
    if args.pdf:
        env['AIMO_REFERENCE_PDF']=args.pdf
        tests.append('test_family_engine_pdf_reference_v280.py')
    for t in tests:
        run([sys.executable,str(ROOT/'tests'/t)],env=env)
    if args.pdf:
        # This path is intentionally CPU-only and exercises run_pdf_pipeline.py.
        run([sys.executable,str(ROOT/'run_pdf_pipeline.py'),'--input',args.pdf,'--all','--benchmark-reference','--engine-only','--config','config_v2_8_1.yaml'],env=env)
    print('v2.8.1 PREFLIGHT PASS')
if __name__=='__main__': main()
