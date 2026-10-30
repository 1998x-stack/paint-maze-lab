"""Seeded perfect maze algorithms + post-verified sliding-paint levels."""
from __future__ import annotations
import random
from collections import deque
from .core import Maze, assess, solve

RANDOM_ALGORITHMS = ('dfs', 'prim', 'kruskal', 'wilson')
ALGORITHMS = RANDOM_ALGORITHMS + ('snake', 'evolve')

def neighbors(y, x, h, w):
    for dy, dx in ((-1, 0), (0, 1), (1, 0), (0, -1)):
        yy, xx = y + dy, x + dx
        if 0 <= yy < h and 0 <= xx < w: yield yy, xx


def spanning_edges(h: int, w: int, algorithm: str, rng: random.Random):
    if algorithm not in RANDOM_ALGORITHMS: raise ValueError('Unsupported spanning-tree algorithm')
    nodes = [(r, c) for r in range(h) for c in range(w)]
    root = rng.choice(nodes)
    if algorithm == 'dfs':
        seen = {root}
        stack = [root]
        while stack:
            p = stack[-1]
            choices = [v for v in neighbors(*p, h, w) if v not in seen]
            if not choices:
                stack.pop()
                continue
            v = rng.choice(choices)
            seen.add(v)
            stack.append(v)
            yield p, v
    elif algorithm == 'prim':
        seen = {root}
        frontier = [(root, v) for v in neighbors(*root, h, w)]
        while frontier:
            k = rng.randrange(len(frontier))
            p, v = frontier.pop(k)
            if v in seen: continue
            seen.add(v)
            yield p, v
            frontier.extend((v, nxt) for nxt in neighbors(*v, h, w) if nxt not in seen)
    elif algorithm == 'kruskal':
        parent = {p: p for p in nodes}
        rank = {p: 0 for p in nodes}
        def find(p):
            while parent[p] != p:
                parent[p] = parent[parent[p]]
                p = parent[p]
            return p
        edges = [(p, v) for p in nodes for v in neighbors(*p, h, w) if p < v]
        rng.shuffle(edges)
        for p, v in edges:
            a, b = find(p), find(v)
            if a == b: continue
            if rank[a] < rank[b]: a, b = b, a
            parent[b] = a
            if rank[a] == rank[b]: rank[a] += 1
            yield p, v
    else:  # Wilson: loop-erased random walk, unbiased spanning tree
        visited = {root}
        pending = [x for x in nodes if x != root]
        while pending:
            start = pending[0]
            path = [start]
            index = {start: 0}
            while path[-1] not in visited:
                nxt = rng.choice(list(neighbors(*path[-1], h, w)))
                if nxt in index:
                    idx = index[nxt]
                    path = path[:idx+1]
                    index = {p: i for i, p in enumerate(path)}
                else:
                    path.append(nxt)
                    index[nxt] = len(path) - 1
            for p, v in zip(path, path[1:]):
                visited.add(p)
                yield p, v
            pending = [p for p in pending if p not in visited]


def snake_maze(coarse_width, coarse_height):
    """Construct a nonbranching serpentine corridor with a guaranteed slide solution."""
    h, w = 2 * coarse_height + 1, 2 * coarse_width + 1
    grid = [['#'] * w for _ in range(h)]
    for band in range(coarse_height):
        r = 2 * band + 1
        for c in range(1, w-1): grid[r][c] = '.'
        if band < coarse_height-1:
            connector = w-2 if band % 2 == 0 else 1
            grid[r+1][connector] = '.'
    return Maze(tuple(''.join(row) for row in grid), (1,1))

def generate(coarse_width=5, coarse_height=5, algorithm='dfs', seed=42,
             extra_loops=0.0, start_policy='corner') -> Maze:
    if not (2 <= coarse_width <= 32 and 2 <= coarse_height <= 32):
        raise ValueError('Coarse dimensions must be 2..32')
    if not 0 <= extra_loops <= 1: raise ValueError('extra_loops must be 0..1')
    if start_policy not in ('corner', 'random'): raise ValueError('invalid start_policy')
    if algorithm == 'snake':
        return snake_maze(coarse_width, coarse_height)
    if algorithm == 'evolve':
        from .evolve import evolve_maze
        return evolve_maze(coarse_width, coarse_height, seed,
                           trials=max(4, round(8 + extra_loops * 120))).maze
    rng = random.Random(seed)
    h, w = 2 * coarse_height + 1, 2 * coarse_width + 1
    grid = [['#'] * w for _ in range(h)]
    for r in range(coarse_height):
        for c in range(coarse_width): grid[2*r+1][2*c+1] = '.'
    tree_edges = set()
    for p, v in spanning_edges(coarse_height, coarse_width, algorithm, rng):
        a, b = (2*p[0]+1, 2*p[1]+1), (2*v[0]+1, 2*v[1]+1)
        grid[(a[0]+b[0])//2][(a[1]+b[1])//2] = '.'
        tree_edges.add(tuple(sorted((p, v))))
    for r in range(coarse_height):
        for c in range(coarse_width):
            p = (r, c)
            for v in neighbors(r, c, coarse_height, coarse_width):
                edge = tuple(sorted((p, v)))
                if edge not in tree_edges and p < v and rng.random() < extra_loops:
                    grid[1 + p[0]+v[0]][1 + p[1]+v[1]] = '.'
    start = (1, 1) if start_policy == 'corner' else (2*rng.randrange(coarse_height)+1, 2*rng.randrange(coarse_width)+1)
    return Maze(tuple(''.join(row) for row in grid), start)


def generate_validated(*, coarse_width=5, coarse_height=5, algorithm='dfs', seed=42,
                       extra_loops=0.0, attempts=200, min_steps=0, max_states=40000):
    if not 1 <= attempts <= 5000: raise ValueError('attempts must be 1..5000')
    if algorithm == 'evolve':
        from .evolve import evolve_maze
        rng = random.Random(seed)
        rejected = 0
        mutation_budget = max(4, round(8 + extra_loops * 120))
        for attempt in range(attempts):
            candidate_seed = seed if attempt == 0 else rng.randrange(2**32)
            try:
                result = evolve_maze(coarse_width, coarse_height, candidate_seed,
                                     trials=mutation_budget, max_states=max_states,
                                     min_steps=min_steps)
            except RuntimeError:
                rejected += 1
                continue
            maze = result.maze
            return {'maze': maze, 'assessment': assess(maze), 'solution': result.solution,
                    'generation': {'algorithm': algorithm, 'seed': candidate_seed,
                                   'requested_seed': seed, 'attempts': attempt + 1,
                                   'attempted_mutations': result.attempted,
                                   'accepted_mutations': result.accepted,
                                   'initial_steps': result.initial_steps,
                                   'rejected': rejected, 'unknown': 0}}
        raise RuntimeError(f'No evolved level meeting {min_steps} steps in {attempts} candidate seeds; increase mutation strength or reduce target')
    if algorithm == 'snake':
        maze = snake_maze(coarse_width, coarse_height)
        decision = assess(maze)
        answer = solve(maze, method='astar', max_states=max_states)
        if not decision['solvable'] or not answer['exact'] or answer['steps'] < min_steps:
            raise RuntimeError('Constructive snake cannot meet the exact-step target or solver budget; increase height')
        return {'maze': maze, 'assessment': decision, 'solution': answer,
                'generation': {'algorithm': algorithm, 'seed': seed, 'attempts': 1,
                               'rejected': 0, 'unknown': 0}}
    rng = random.Random(seed)
    rejected = 0
    unknown = 0
    for _ in range(attempts):
        candidate_seed = rng.randrange(2**32)
        maze = generate(coarse_width, coarse_height, algorithm, candidate_seed, extra_loops)
        decision = assess(maze)
        if not decision['solvable']:
            rejected += 1
            continue
        answer = solve(maze, method='astar', max_states=max_states)
        if not answer['exact']:
            unknown += 1
            continue
        if answer['steps'] < min_steps:
            rejected += 1
            continue
        return {'maze': maze, 'assessment': decision, 'solution': answer,
                'generation': {'algorithm': algorithm, 'seed': candidate_seed,
                               'attempts': rejected + unknown + 1,
                               'rejected': rejected, 'unknown': unknown}}
    raise RuntimeError(f'No verified level in {attempts} attempts (rejected={rejected}, unknown={unknown}); try smaller size or min_steps')
