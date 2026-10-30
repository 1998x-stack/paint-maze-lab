"""Pure, deterministic rules: slide to obstacle; paint every traversed floor tile.

Solvability: union of footprints from all reachable stopping positions. This
is sufficient when paint is monotone, unlimited moves and walls never change.
"""
from __future__ import annotations
from dataclasses import dataclass
from collections import deque
from heapq import heappush, heappop
from itertools import count
from typing import Any

DIRECTIONS = ((-1, 0, 'U'), (0, 1, 'R'), (1, 0, 'D'), (0, -1, 'L'))

@dataclass(frozen=True)
class Maze:
    rows: tuple[str, ...]
    start: tuple[int, int]

    def __post_init__(self):
        if not self.rows or not self.rows[0] or any(len(row) != len(self.rows[0]) for row in self.rows):
            raise ValueError('Invalid grid size')
        if any(set(row) - set('#.') for row in self.rows):
            raise ValueError('Only # and . allowed')
        if not self.floor(*self.start):
            raise ValueError('Start must be on floor')

    @property
    def height(self): return len(self.rows)

    @property
    def width(self): return len(self.rows[0])

    @property
    def cells(self):
        return tuple((r, c) for r, row in enumerate(self.rows) for c, val in enumerate(row) if val == '.')

    def floor(self, r, c):
        return 0 <= r < len(self.rows) and 0 <= c < len(self.rows[0]) and self.rows[r][c] == '.'

    @classmethod
    def from_ascii(cls, text: str):
        rows = [x.strip() for x in text.strip().splitlines() if x.strip()]
        starts = [(r, c) for r, row in enumerate(rows) for c, val in enumerate(row) if val == 'S']
        if len(starts) != 1: raise ValueError('Expected exactly one S')
        start = starts[0]
        return cls(tuple(row.replace('S', '.') for row in rows), start)

    def ascii(self):
        return '\n'.join(''.join('S' if (r, c) == self.start else ch for c, ch in enumerate(row))
                         for r, row in enumerate(self.rows))

    def data(self):
        return {'rows': list(self.rows), 'start': list(self.start), 'width': self.width,
                'height': self.height, 'floor_count': len(self.cells)}


class SlidingGraph:
    def __init__(self, maze: Maze):
        self.maze = maze
        self.cells = maze.cells
        self.cell_index = {cell: i for i, cell in enumerate(self.cells)}
        self.all_mask = (1 << len(self.cells)) - 1
        self.start_mask = 1 << self.cell_index[maze.start]
        # Cache every position, including intermediate floor tiles, for debugging and parity.
        self.moves: dict[tuple[int, int], dict[str, tuple[tuple[int, int], int, tuple[tuple[int,int],...]]]] = {}
        for p in self.cells:
            self.moves[p] = {}
            for dr, dc, name in DIRECTIONS:
                r, c = p
                path = []
                mask = 0
                while maze.floor(r + dr, c + dc):
                    r, c = r + dr, c + dc
                    path.append((r, c))
                    mask |= 1 << self.cell_index[(r, c)]
                if path:
                    self.moves[p][name] = ((r, c), mask, tuple(path))

    def step(self, pos, mask, direction):
        motion = self.moves[pos].get(direction)
        if motion is None: return pos, mask, ()
        new_pos, path_mask, path = motion
        return new_pos, mask | path_mask, path

    def reachable(self, position=None):
        """Reachable stops and union of all swept cells, starting at any floor cell."""
        position = self.maze.start if position is None else position
        if position not in self.cell_index:
            raise ValueError("Position must be a floor tile")
        reachable = {position}
        q = deque([position])
        coverage = 1 << self.cell_index[position]
        while q:
            p = q.popleft()
            for dest, footprint, _ in self.moves[p].values():
                coverage |= footprint
                if dest not in reachable:
                    reachable.add(dest)
                    q.append(dest)
        return reachable, coverage

    def connected(self):
        reached = {self.maze.start}
        q = deque([self.maze.start])
        while q:
            r, c = q.popleft()
            for dr, dc, _ in DIRECTIONS:
                p = (r + dr, c + dc)
                if self.maze.floor(*p) and p not in reached:
                    reached.add(p)
                    q.append(p)
        return len(reached) == len(self.cells)

    def assess(self):
        stops, covered = self.reachable()
        missing = [list(p) for p in self.cells if not (covered >> self.cell_index[p]) & 1]
        return {
            'solvable': covered == self.all_mask,
            'static_connected': self.connected(),
            'reachable_stop_count': len(stops),
            'reachable_stops': [list(p) for p in sorted(stops)],
            'reachable_painted_count': covered.bit_count(),
            'floor_count': len(self.cells),
            'unpaintable': missing,
            'directed_edges': sum(len(self.moves[p]) for p in stops),
        }


def assess(maze: Maze):
    return SlidingGraph(maze).assess()


def simulate(maze: Maze, moves: str):
    g = SlidingGraph(maze)
    pos, mask = maze.start, g.start_mask
    trace = [{'pos': list(pos), 'painted': mask.bit_count()}]
    for action in moves:
        if action not in 'URDL': raise ValueError('Invalid direction')
        pos, mask, footprint = g.step(pos, mask, action)
        trace.append({'move': action, 'pos': list(pos), 'painted': mask.bit_count(),
                      'path': [list(p) for p in footprint]})
    return {'won': mask == g.all_mask, 'painted': mask.bit_count(), 'total': len(g.cells), 'trace': trace}


def solve(maze: Maze, method='bfs', max_states=120_000, dominance=True,
          start_position=None, painted=None) -> dict[str, Any]:
    """Shortest remaining slide count from the current position and painted tiles.

    Returns exact=False on budget exhaustion.

    Dominance: at same stop, (paint superset, <= cost) dominates another state.
    """
    if method not in ('bfs', 'astar'): raise ValueError('method must be bfs/astar')
    graph = SlidingGraph(maze)
    position = maze.start if start_position is None else tuple(start_position)
    if position not in graph.cell_index:
        raise ValueError('Current position must be on floor')
    if painted is None:
        paint_mask = graph.start_mask
    else:
        paint_mask = 0
        for cell in painted:
            cell = tuple(cell)
            if cell not in graph.cell_index:
                raise ValueError('Painted tile must be on floor')
            paint_mask |= 1 << graph.cell_index[cell]
    if not paint_mask & (1 << graph.cell_index[position]):
        raise ValueError('Current position must already be painted')
    # Important: an originally winnable maze may be trapped in an irreversible
    # stopping component after a poor move. Start coverage from the CURRENT stop.
    _, cover = graph.reachable(position)
    if (cover | paint_mask) != graph.all_mask:
        return {'solvable': False, 'exact': True, 'moves': None, 'steps': None,
                'expanded': 0, 'method': method, 'reason': 'unreachable_remaining'}
    begin = (position, paint_mask)
    max_cover = max((mask.bit_count() for adj in graph.moves.values() for _, mask, _ in adj.values()), default=1)
    max_cover = max(1, max_cover)
    def h(state):
        return (graph.all_mask ^ state[1]).bit_count() // max_cover + int(((graph.all_mask ^ state[1]).bit_count() % max_cover) > 0)

    serial = count()
    heap = []
    heappush(heap, (h(begin) if method == 'astar' else 0, next(serial), 0, begin))
    best = {begin: 0}
    parent = {}
    frontiers: dict[tuple[int,int], list[tuple[int,int]]] = {position: [(paint_mask, 0)]}
    expanded = 0
    while heap:
        _, _, cost, state = heappop(heap)
        if best.get(state) != cost: continue
        pos, mask = state
        if dominance and not any(m == mask and d == cost for m, d in frontiers.get(pos, [])):
            continue
        if mask == graph.all_mask:
            moves = []
            cur = state
            while cur != begin:
                prev, action = parent[cur]
                moves.append(action)
                cur = prev
            moves.reverse()
            return {'solvable': True, 'exact': True, 'moves': ''.join(moves),
                    'steps': len(moves), 'expanded': expanded, 'method': method}
        if expanded >= max_states:
            return {'solvable': True, 'exact': False, 'moves': None, 'steps': None,
                    'expanded': expanded, 'method': method, 'reason': 'state_budget'}
        expanded += 1
        for action, (dest, footprint, _) in graph.moves[pos].items():
            next_state = (dest, mask | footprint)
            if next_state == state: continue
            next_cost = cost + 1
            if next_cost >= best.get(next_state, 10**12): continue
            if dominance:
                frontier = frontiers.setdefault(dest, [])
                # Any same/cheaper state with a superset of paint dominates this one.
                if any((m | next_state[1]) == m and d <= next_cost for m, d in frontier):
                    continue
                survivors = [(m, d) for m, d in frontier
                             if not ((m | next_state[1]) == next_state[1] and next_cost <= d)]
                survivors.append((next_state[1], next_cost))
                frontiers[dest] = survivors
            best[next_state] = next_cost
            parent[next_state] = (state, action)
            priority = next_cost + (h(next_state) if method == 'astar' else 0)
            heappush(heap, (priority, next(serial), next_cost, next_state))
    return {'solvable': True, 'exact': False, 'steps': None, 'moves': None,
            'expanded': expanded, 'method': method, 'reason': 'unexpected_exhaustion'}
