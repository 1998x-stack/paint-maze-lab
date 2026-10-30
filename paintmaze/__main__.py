import argparse
import json
from .core import Maze, assess, solve
from .generate import generate, generate_validated, ALGORITHMS

p = argparse.ArgumentParser(description='Paint Maze Lab')
p.add_argument('--algorithm', choices=ALGORITHMS, default='dfs')
p.add_argument('--width', type=int, default=4)
p.add_argument('--height', type=int, default=4)
p.add_argument('--seed', type=int, default=42)
p.add_argument('--loops', type=float, default=0.1)
p.add_argument('--verified', action='store_true')
p.add_argument('--max-states', type=int, default=100000)
p.add_argument('--min-steps', type=int, default=0)
p.add_argument('--method', choices=['bfs', 'astar'], default='astar')
a = p.parse_args()
if a.verified:
    out = generate_validated(coarse_width=a.width, coarse_height=a.height, algorithm=a.algorithm,
                             seed=a.seed, extra_loops=a.loops, min_steps=a.min_steps,
                             max_states=a.max_states)
    m = out['maze']
    analysis = out['assessment']
    ans = out['solution']
else:
    m = generate(a.width, a.height, a.algorithm, a.seed, a.loops)
    analysis = assess(m)
    ans = solve(m, method=a.method, max_states=a.max_states)
print(m.ascii())
print(json.dumps({'assessment': analysis, 'solution': ans}, ensure_ascii=False, indent=2))
