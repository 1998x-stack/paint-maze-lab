"""Reproducible study of exact difficulty curation, without cherry-picked wins.

Run: python benchmarks/difficulty_eval.py --samples 20 --width 4 --height 4
"""
from __future__ import annotations
import argparse
import json
import sys
import time
from pathlib import Path
from statistics import mean

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from paintmaze.difficulty import curate


def run(samples=20, width=4, height=4, candidates=5, seed=2026, budget=40000):
    output=[]
    for tier in ('relaxed','standard','challenging','expert'):
        cases=[]
        for i in range(samples):
            t=time.perf_counter()
            try:
                result=curate(coarse_width=width,coarse_height=height, algorithm='evolve',
                              difficulty=tier, seed=seed+i, candidates=candidates,
                              max_states=budget, attempts=20)
                cases.append({'seed':seed+i,'success':True,'steps':result['solution']['steps'],
                              'score':result['difficulty']['score'],
                              'actual_tier':result['difficulty']['tier'],
                              'hit':result['generation']['curation']['tier_preference_met'],
                              'unique_candidates':result['generation']['curation']['unique_valid_candidates'],
                              'elapsed_ms':round((time.perf_counter()-t)*1000,3)})
            except RuntimeError as err:
                cases.append({'seed':seed+i,'success':False,'error':str(err),
                              'elapsed_ms':round((time.perf_counter()-t)*1000,3)})
        successes=[x for x in cases if x['success']]
        output.append({'requested':tier,'samples':samples,'generated':len(successes),
            'tier_hit_rate':round(100*sum(x['hit'] for x in successes)/len(successes),2) if successes else None,
            'mean_optimal_steps':round(mean(x['steps'] for x in successes),2) if successes else None,
            'mean_score':round(mean(x['score'] for x in successes),2) if successes else None,
            'mean_latency_ms':round(mean(x['elapsed_ms'] for x in cases),2),
            'cases':cases})
    return {'config':{'samples':samples,'width':width,'height':height,'candidates':candidates,
            'seed':seed,'solver_budget':budget},'tiers':output,
            'warning':'Scores are heuristic, not validated against human completion rates. Tier selection is best-effort.'}

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--samples',type=int,default=20)
    p.add_argument('--width',type=int,default=4)
    p.add_argument('--height',type=int,default=4)
    p.add_argument('--candidates',type=int,default=5)
    p.add_argument('--seed',type=int,default=2026)
    p.add_argument('--budget',type=int,default=40000)
    p.add_argument('--output',default='results/v3_difficulty_eval.json')
    args=p.parse_args()
    data=run(args.samples,args.width,args.height,args.candidates,args.seed,args.budget)
    target=Path(args.output);target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for tier in data['tiers']:
        print(tier['requested'],':',tier['generated'],'/',tier['samples'],
              'tier hit',tier['tier_hit_rate'],'mean steps',tier['mean_optimal_steps'],
              'mean ms',tier['mean_latency_ms'])
    print('Saved',target)
