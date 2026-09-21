from __future__ import annotations
from pathlib import Path
import argparse, json, sys
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from core.config import load_config, prepare_environment
from core.model_manager import ModelManager
from core.pipeline import FullOlympiadPipeline
from core.reporting import save_result


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--input',required=True,help='JSONL with id/problem fields')
    ap.add_argument('--config',default=str(ROOT/'config_v2_11_0.yaml'))
    ap.add_argument('--preload',action='store_true')
    args=ap.parse_args()
    cfg=load_config(args.config); prepare_environment(cfg)
    manager=ModelManager(cfg)
    pipe=FullOlympiadPipeline(cfg,manager)
    if args.preload: manager.preload()
    rows=[]
    with open(args.input,encoding='utf-8') as f:
        for line in f:
            if line.strip(): rows.append(json.loads(line))
    summary=[]
    for i,row in enumerate(rows):
        pid=str(row.get('id') or f'problem_{i:04d}')
        problem=str(row['problem'])
        r=pipe.run(problem,problem_id=pid)
        save_result(r,cfg['project']['output_dir'])
        summary.append({
            'id':pid,'status':r['status'],'candidate_answer':r.get('candidate_answer'),
            'verified_answer':r.get('verified_answer'),'calls':r['metrics']['model_calls'],
            'tokens':r['metrics']['total_tokens'],'latency_sec':r['metrics']['latency_sec'],
        })
        print(summary[-1])
    p=Path(cfg['project']['output_dir'])/'batch_summary.json'
    p.write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print('Saved',p)
if __name__=='__main__': main()
