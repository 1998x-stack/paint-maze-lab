"""Verified procedural mutation of a constructive sliding-paint maze.

Unlike random spanning trees, the initial seed is always soluble. Each
mutation is independently checked against the true slide-coverage model.
A seeded geometric symmetry supplies layout diversity even if all optional
mutations fail, and full audit fields make fallback behaviour visible.
"""
from __future__ import annotations
import random
from dataclasses import dataclass
from .core import Maze, SlidingGraph, solve


def transform(maze: Maze, mirror_horizontal=False, mirror_vertical=False, transpose=False) -> Maze:
    rows = [list(row) for row in maze.rows]
    start = maze.start
    if mirror_horizontal:
        rows = [row[::-1] for row in rows]
        start = (start[0], len(rows[0]) - 1 - start[1])
    if mirror_vertical:
        rows = rows[::-1]
        start = (len(rows) - 1 - start[0], start[1])
    if transpose:
        rows = [list(row) for row in zip(*rows)]
        start = (start[1], start[0])
    return Maze(tuple(''.join(row) for row in rows), start)


def mutate(maze: Maze, position: tuple[int, int]) -> Maze:
    r, c = position
    if (r,c) == maze.start or not (0 < r < maze.height-1 and 0 < c < maze.width-1):
        raise ValueError('Cannot mutate start or boundary')
    rows = [list(row) for row in maze.rows]
    rows[r][c] = '.' if rows[r][c] == '#' else '#'
    return Maze(tuple(''.join(row) for row in rows), maze.start)


@dataclass(frozen=True)
class EvolutionResult:
    maze: Maze
    solution: dict
    attempted: int
    accepted: int
    initial_steps: int


def evolve_maze(coarse_width: int, coarse_height: int, seed: int,
                trials: int = 28, max_states: int = 60000,
                min_steps: int = 0) -> EvolutionResult:
    from .generate import snake_maze
    rng = random.Random(seed)
    transpose = bool(rng.getrandbits(1))
    base = snake_maze(coarse_height, coarse_width) if transpose else snake_maze(coarse_width, coarse_height)
    maze = transform(base, bool(rng.getrandbits(1)), bool(rng.getrandbits(1)), transpose)
    initial = solve(maze, method='astar', max_states=max_states)
    if not initial['exact']:
        raise RuntimeError('Constructive baseline exceeded the search budget')
    answer = initial
    accepted = 0
    # Try single-wall modifications; the legality test is about full slide
    # footprints, NOT static connectivity. Preserve best reachable variant.
    interior = [(r, c) for r in range(1, maze.height-1)
                for c in range(1, maze.width-1) if (r,c) != maze.start]
    rng.shuffle(interior)
    for i in range(min(trials, len(interior))):
        pos = interior[i]
        try:
            candidate = mutate(maze, pos)
        except ValueError:
            continue
        graph = SlidingGraph(candidate)
        _, coverage = graph.reachable()
        if coverage != graph.all_mask:
            continue
        result = solve(candidate, method='astar', max_states=max_states)
        if not result['exact'] or result['steps'] < min(answer['steps'], min_steps):
            continue
        maze, answer = candidate, result
        accepted += 1
    if answer['steps'] < min_steps:
        raise RuntimeError(f'No evolved level meeting {min_steps} steps after {min(trials,len(interior))} mutations; achieved {answer["steps"]}')
    return EvolutionResult(maze, answer, min(trials, len(interior)), accepted,
                           initial['steps'])


def tutorial_maze(coarse_width: int, coarse_height: int, seed: int) -> Maze:
    """Seeded short corridor/L-shape. Always slide-completable in 1 or 2 moves.

    Intended for the easy learning curve, not as a substitute for evolution.
    """
    rng = random.Random(seed)
    transpose = bool(rng.getrandbits(1))
    # Build in the inverse orientation so the final dimensions remain exact.
    raw_width, raw_height = (coarse_height, coarse_width) if transpose else (coarse_width, coarse_height)
    h, w = 2*raw_height+1, 2*raw_width+1
    rows = [['#']*w for _ in range(h)]
    r = rng.randrange(1,h-1)
    for c in range(1,w-1): rows[r][c]='.'
    if rng.getrandbits(1):
        # A single vertical branch starting only at the right end; it is
        # traversable from that stopping corner, not an inaccessible fork.
        for rr in range(r+1,h-1): rows[rr][w-2]='.'
    maze=Maze(tuple(''.join(row) for row in rows),(r,1))
    return transform(maze,bool(rng.getrandbits(1)),bool(rng.getrandbits(1)),transpose)
