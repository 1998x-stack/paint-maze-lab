"""Controlled generators and solver comparison. Run from project root."""
import argparse
import json
import csv
import sys
import statistics
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from paintmaze import generate, assess, solve, ALGORITHMS

def run(samples=100,width=4,height=4,seed=2026,loops=.12,budget=60000):
    rows=[]
    solver_rows=[]
    for algo in ALGORITHMS:
        results=[]
        t0=time.perf_counter()
        for n in range(samples):
            m=generate(width,height,algorithm=algo,seed=seed+n,extra_loops=loops)
            a=assess(m)
            results.append({'solvable':a['solvable'],'stops':a['reachable_stop_count'],
                            'paintable':a['reachable_painted_count'],'floor':a['floor_count']})
            if a['solvable']:
                for method in ('bfs','astar'):
                    t1=time.perf_counter()
                    answer=solve(m,method=method,max_states=budget)
                    ms=(time.perf_counter()-t1)*1000
                    solver_rows.append({'algorithm':algo,'seed':seed+n,'method':method,
                                        'exact':answer['exact'],'optimal_steps':answer['steps'],
                                        'expanded':answer['expanded'],'elapsed_ms':round(ms,4)})
        elapsed_ms=(time.perf_counter()-t0)*1000
        possible=[x for x in solver_rows if x['algorithm']==algo and x['method']=='astar' and x['exact']]
        rows.append({'algorithm':algo,'samples':samples,
                     'solvable':sum(r['solvable'] for r in results),
                     'solvable_rate_pct':round(100*sum(r['solvable'] for r in results)/samples,2),
                     'mean_reachable_stops':round(statistics.mean(r['stops'] for r in results),2),
                     'exact_astar':len(possible),
                     'conditional_mean_optimal_steps':round(statistics.mean(x['optimal_steps'] for x in possible),2) if possible else None,
                     'elapsed_ms':round(elapsed_ms,2)})
    methods=[]
    for method in ('bfs','astar'):
        entries=[x for x in solver_rows if x['method']==method]
        exact=[x for x in entries if x['exact']]
        methods.append({'method':method,'cases':len(entries),'exact':len(exact),
                        'mean_expanded_exact':round(statistics.mean(x['expanded'] for x in exact),2) if exact else None,
                        'mean_elapsed_ms_exact':round(statistics.mean(x['elapsed_ms'] for x in exact),3) if exact else None})
    # Pair exact answers only; show if discrepancy occurs.
    by_case={}
    for s in solver_rows:
        by_case.setdefault((s['algorithm'],s['seed']),{})[s['method']]=s
    mismatches=[{'algorithm':k[0],'seed':k[1],'bfs':v['bfs']['optimal_steps'],'astar':v['astar']['optimal_steps']}
                for k,v in by_case.items() if v['bfs']['exact'] and v['astar']['exact'] and v['bfs']['optimal_steps'] != v['astar']['optimal_steps']]
    return {'parameters':{'samples_per_algorithm':samples,'width':width,'height':height,'seed':seed,'loops':loops,'budget':budget},
            'generators':rows,'solvers':methods,'mismatches':mismatches,'solver_cases':solver_rows,
            'notes':['Average optimal steps is conditional on exact solutions and not an unconditional difficulty ranking.',
                     'Elapsed times include different amounts of work; hardware dependent.',
                     'BFS/A* state budgets create censored observations, not proof of no solution.']}

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--samples',type=int,default=50)
    parser.add_argument('--width',type=int,default=4)
    parser.add_argument('--height',type=int,default=4)
    parser.add_argument('--seed',type=int,default=2026)
    parser.add_argument('--loops',type=float,default=.12)
    parser.add_argument('--budget',type=int,default=60000)
    parser.add_argument('--output',default='results/benchmark.json')
    args=parser.parse_args()
    d=run(args.samples,args.width,args.height,args.seed,args.loops,args.budget)
    path=Path(args.output);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
    with path.with_suffix('.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(d['generators'][0]));writer.writeheader();writer.writerows(d['generators'])
    print('Parameters:', d['parameters'])
    for row in d['generators']: print('GEN',row)
    for row in d['solvers']: print('SOLVER',row)
    print('BFS/A* discrepancies:',len(d['mismatches']))
    print('Output:',path)
