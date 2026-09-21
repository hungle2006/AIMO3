from __future__ import annotations
from pathlib import Path
import argparse, json, os, subprocess, sys, time

ROOT=Path(__file__).resolve().parents[1]

def run_test(py, test):
    t=time.perf_counter()
    p=subprocess.run([py,str(test)],capture_output=True,text=True,env=os.environ.copy())
    return {'test':test.name,'returncode':p.returncode,'seconds':time.perf_counter()-t,'stdout':p.stdout[-2000:],'stderr':p.stderr[-2000:]}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--pdf',default=os.environ.get('AIMO_REFERENCE_PDF',''))
    ap.add_argument('--report',default=str(ROOT/'virtual_regression_v280.json'))
    args=ap.parse_args()
    if args.pdf:
        os.environ['AIMO_REFERENCE_PDF']=args.pdf
    tests=sorted((ROOT/'tests').glob('test_*.py'))
    results=[]
    for t in tests:
        r=run_test(sys.executable,t)
        results.append(r)
        print(('PASS' if r['returncode']==0 else 'FAIL'),t.name,f"{r['seconds']:.2f}s")
    report={'python':sys.version,'pdf':args.pdf or None,'total':len(results),'passed':sum(r['returncode']==0 for r in results),'failed':[r['test'] for r in results if r['returncode']!=0],'results':results}
    Path(args.report).write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({k:report[k] for k in ['total','passed','failed']},indent=2))
    if report['failed']:
        raise SystemExit(1)
if __name__=='__main__':main()
