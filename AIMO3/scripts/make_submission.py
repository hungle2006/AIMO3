from pathlib import Path
import argparse,csv,json

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--results-dir',default='/kaggle/working/olympiad_runs_v26')
    ap.add_argument('--output',default='/kaggle/working/submission.csv')
    ap.add_argument('--allow-candidate',action='store_true',help='Use unverified candidate only if explicitly requested')
    args=ap.parse_args()
    rows=[]
    for p in sorted(Path(args.results_dir).glob('*.json')):
        if p.name.endswith('summary.json'): continue
        try: d=json.loads(p.read_text(encoding='utf-8'))
        except Exception: continue
        ans=d.get('verified_answer')
        if ans is None and args.allow_candidate:
            ans=d.get('candidate_answer')
        if ans is None: continue
        rows.append({'id':d.get('problem_id'),'answer':int(ans)})
    with open(args.output,'w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['id','answer']); w.writeheader(); w.writerows(rows)
    print('Saved:',args.output,'rows=',len(rows))
if __name__=='__main__': main()
