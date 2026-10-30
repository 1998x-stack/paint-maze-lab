"""Deterministic, explainable level metrics and bounded candidate curation.

The score is an engineering heuristic, NOT calibrated human difficulty.  The
shortest solution is an exact result only when the solver says exact=True.
"""
from __future__ import annotations
from math import sqrt
from statistics import mean
from .core import Maze, SlidingGraph, solve, assess

TIERS = {
    'relaxed': 24,
    'standard': 40,
    'challenging': 56,
    'expert': 74,
}


def measure(maze: Maze, solution: dict) -> dict:
    if not solution.get('exact') or not solution.get('solvable') or solution.get('moves') is None:
        raise ValueError('A verified exact winning solution is required for difficulty metrics')
    g = SlidingGraph(maze)
    pos, mask = maze.start, g.start_mask
    steps = solution['moves']
    turns = sum(a != b for a, b in zip(steps, steps[1:]))
    travel = 0
    decisions = []
    for action in steps:
        options = len(g.moves[pos]); decisions.append(options)
        if action not in g.moves[pos]:
            raise ValueError('Solution includes an impossible slide')
        dest, _, path = g.moves[pos][action]
        travel += len(path)
        pos, mask, _ = g.step(pos, mask, action)
    if mask != g.all_mask:
        raise ValueError('Solution does not cover the maze')
    n = len(g.cells)
    surplus = max(0, travel - (n-1))
    revisit_ratio = surplus / max(1, travel)
    # Use bounded quantities so this stays interpretable across grid sizes.
    step_load = min(1, max(0, (len(steps) / sqrt(n) - 0.8) / 1.4))
    turn_load = turns / max(1, len(steps) - 1)
    branch_load = mean((min(1, max(0, d - 1) / 3) for d in decisions)) if decisions else 0
    score = round(100 * (0.57 * step_load + 0.16 * turn_load + 0.14 * branch_load + 0.13 * revisit_ratio), 2)
    if score < 30: label = 'relaxed'
    elif score < 48: label = 'standard'
    elif score < 65: label = 'challenging'
    else: label = 'expert'
    return {
        'score': score, 'tier': label,
        'optimal_steps': len(steps), 'turns': turns,
        'branch_decisions': sum(d >= 3 for d in decisions),
        'average_available_actions': round(mean(decisions), 2) if decisions else 0,
        'repeated_travel_ratio': round(revisit_ratio, 4),
        'travel_tiles': travel, 'floor_count': n,
        'model': 'v1_heuristic_not_human_calibrated',
    }


def curate(*, coarse_width=4, coarse_height=4, algorithm='evolve', seed=42,
           extra_loops=.12, attempts=70, candidates=5, min_steps=0,
           max_steps=None, target_steps=None, difficulty='any', max_states=60000):
    """Choose among distinct verified levels. Explicit bounds are mandatory.

    Difficulty tier is a best-effort preference, clearly reported as such.
    All candidates must carry exact shortest solutions; budget exhaustion is
    never misreported as an unsolvable candidate.
    """
    from .generate import generate_validated
    from .evolve import tutorial_maze
    import random
    if difficulty != 'any' and difficulty not in TIERS:
        raise ValueError('Unknown difficulty preset')
    if not 1 <= candidates <= 24:
        raise ValueError('candidates must be 1..24')
    if max_steps is not None and (max_steps < min_steps or max_steps < 0):
        raise ValueError('max_steps must be >= min_steps')
    if target_steps is not None and target_steps < 0:
        raise ValueError('target_steps must be >= 0')
    if target_steps is not None and (target_steps < min_steps or (max_steps is not None and target_steps > max_steps)):
        raise ValueError('target_steps must lie inside explicit step bounds')
    rng = random.Random(seed)
    seen = set()
    matches = []
    failed = 0
    for i in range(candidates):
        choice_seed = seed if i == 0 else rng.randrange(2**32)
        try:
            if difficulty == 'relaxed' and algorithm == 'evolve' and i < max(1, candidates // 2):
                maze = tutorial_maze(coarse_width, coarse_height, choice_seed)
                answer = solve(maze, method='astar', max_states=max_states)
                if not answer['exact'] or answer['steps'] < min_steps:
                    raise RuntimeError('Tutorial candidate does not meet constraints')
                result = {'maze':maze,'assessment':assess(maze),
                          'solution':answer,
                          'generation':{'algorithm':'evolve','template':'tutorial',
                                        'seed':choice_seed,'requested_seed':seed,'attempts':1,
                                        'rejected':0,'unknown':0}}
            else:
                result = generate_validated(coarse_width=coarse_width, coarse_height=coarse_height,
                     algorithm=algorithm, seed=choice_seed, extra_loops=extra_loops,
                     attempts=attempts, min_steps=min_steps, max_states=max_states)
        except RuntimeError:
            failed += 1
            continue
        maze, answer = result['maze'], result['solution']
        key = (maze.rows, maze.start)
        if key in seen or not answer.get('exact') or answer['steps'] is None:
            continue
        seen.add(key)
        if max_steps is not None and answer['steps'] > max_steps:
            continue
        stats = measure(maze, answer)
        target_score = TIERS.get(difficulty)
        tier_miss = int(difficulty != 'any' and stats['tier'] != difficulty)
        if target_steps is not None:
            # Explicit target steps take precedence over a soft tier preference.
            distance = abs(answer['steps']-target_steps)
            secondary = tier_miss
        elif target_score is not None:
            distance = tier_miss
            secondary = abs(stats['score']-target_score)
        else:
            distance = 0
            secondary = 0
        # Prefer more decision diversity when the primary objective ties.
        matches.append(((distance, secondary, -stats['branch_decisions'], i), result, stats))
    if not matches:
        raise RuntimeError(f'No exact verified level satisfies the requested constraints; tried {candidates} candidates ({failed} generation failures). Increase candidate count, solver budget or relax limits.')
    _, selected, stats = min(matches, key=lambda x: x[0])
    selected['difficulty'] = stats
    selected['generation']['curation'] = {
        'requested_difficulty': difficulty, 'target_steps': target_steps,
        'min_steps': min_steps, 'max_steps': max_steps,
        'candidate_count': candidates, 'unique_valid_candidates': len(matches),
        'failed_generations': failed,
        'tier_preference_met': difficulty == 'any' or stats['tier'] == difficulty,
        'target_distance': abs(stats['optimal_steps']-target_steps) if target_steps is not None else None,
        'selection': 'closest_verified_candidate',
    }
    return selected
