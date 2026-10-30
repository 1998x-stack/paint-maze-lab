import random
import unittest
from collections import deque
from paintmaze import Maze, SlidingGraph, assess, solve, simulate, generate, generate_validated, ALGORITHMS
from paintmaze.generate import spanning_edges, RANDOM_ALGORITHMS

SINGLE = Maze.from_ascii('''
#####
#S..#
#####
''')
CONNECTED_UNSOLVABLE = Maze.from_ascii('''
#########
#S......#
####.####
#.......#
#########
''')
DISCONNECTED = Maze.from_ascii('''
#########
#S..#...#
#########
''')

def independent_bruteforce(maze):
    """Independent explicit frozenset solver: no bitmasks, no pruning."""
    start = (maze.start, frozenset((maze.start,)))
    todo = deque([(start, 0)])
    visited = {start}
    target = set(maze.cells)
    for_move = [(-1,0),(0,1),(1,0),(0,-1)]
    while todo:
        (pos, visited_tiles), steps = todo.popleft()
        if visited_tiles == target: return steps
        for dr, dc in for_move:
            r,c = pos
            paint = set(visited_tiles)
            while maze.floor(r+dr,c+dc):
                r,c = r+dr,c+dc
                paint.add((r,c))
            nxt = ((r,c),frozenset(paint))
            if nxt not in visited:
                visited.add(nxt)
                todo.append((nxt,steps+1))
    return None

class CoreTests(unittest.TestCase):
    def test_straight(self):
        a = assess(SINGLE)
        self.assertTrue(a['solvable'])
        self.assertEqual(a['reachable_stop_count'], 2)
        r = solve(SINGLE)
        self.assertEqual((r['steps'],r['moves']), (1,'R'))
        self.assertTrue(simulate(SINGLE,'R')['won'])
        self.assertEqual(simulate(SINGLE,'LRR')['painted'], 3)

    def test_static_connected_but_unsolvable(self):
        self.assertTrue(assess(CONNECTED_UNSOLVABLE)['static_connected'])
        self.assertFalse(assess(CONNECTED_UNSOLVABLE)['solvable'])
        self.assertEqual(len(assess(CONNECTED_UNSOLVABLE)['unpaintable']), 8)
        self.assertFalse(solve(CONNECTED_UNSOLVABLE)['solvable'])

    def test_disconnected(self):
        a=assess(DISCONNECTED)
        self.assertFalse(a['static_connected'])
        self.assertFalse(a['solvable'])

    def test_bad_maze_rejected(self):
        for text in ['##\n##', '#S#\n##', '###\n#.#\n###', '#S#\n#X#']:
            with self.assertRaises(ValueError):Maze.from_ascii(text)

    def test_slide_cover_intermediate(self):
        g=SlidingGraph(SINGLE)
        self.assertEqual(g.step(SINGLE.start,g.start_mask,'R')[0], (1,3))
        self.assertEqual(g.step(SINGLE.start,g.start_mask,'R')[1].bit_count(),3)
        self.assertEqual(g.step(SINGLE.start,g.start_mask,'U')[0], SINGLE.start)

    def test_algorithm_reproducibility(self):
        for alg in ALGORITHMS:
            x=generate(5,5,alg,31415,.2)
            y=generate(5,5,alg,31415,.2)
            self.assertEqual(x,y)
            self.assertTrue(assess(x)['static_connected'])

    def test_tree_edge_counts(self):
        for h,w in [(2,2),(3,4),(6,5)]:
            for alg in RANDOM_ALGORITHMS:
                edges=list(spanning_edges(h,w,alg,random.Random(123)))
                self.assertEqual(len(edges), h*w-1, (h,w,alg))
                self.assertEqual(len({tuple(sorted(e)) for e in edges}), len(edges))

    def test_solver_differential_random(self):
        # Exhaustive small-grid oracle catches wrong sliding, A*, pruning, BFS optimality.
        for alg in ALGORITHMS:
            for seed in range(35):
                maze=generate(2,3,alg,seed,extra_loops=(seed%3)*.2)
                oracle=independent_bruteforce(maze)
                fast=assess(maze)
                self.assertEqual(fast['solvable'],oracle is not None, (alg,seed))
                for method in ('bfs','astar'):
                    for dominance in (False,True):
                        result=solve(maze,method=method,dominance=dominance,max_states=100_000)
                        self.assertTrue(result['exact'],(alg,seed,method,dominance))
                        self.assertEqual(result['steps'], oracle, (alg,seed,method,dominance))
                        if oracle is not None:
                            self.assertTrue(simulate(maze,result['moves'])['won'])

    def test_budget_indicator(self):
        maze=generate(4,4,'wilson',2746317213,.12)
        if assess(maze)['solvable']:
            result=solve(maze,max_states=1)
            self.assertFalse(result['exact'])
            self.assertEqual(result['reason'],'state_budget')

    def test_snake_constructive(self):
        for width,height in ((2,2),(4,4),(8,9)):
            maze=generate(width,height,'snake',123)
            self.assertTrue(assess(maze)['solvable'])
            result=solve(maze,max_states=80000)
            self.assertTrue(result['exact'])
            self.assertEqual(result['steps'],2*height-1)
            self.assertTrue(simulate(maze,result['moves'])['won'])

    def test_verified_generation(self):
        for alg in ALGORITHMS:
            result=generate_validated(coarse_width=4,coarse_height=4,algorithm=alg,seed=42,
                                      extra_loops=.12,attempts=120)
            self.assertTrue(result['assessment']['solvable'])
            self.assertTrue(result['solution']['exact'])
            self.assertTrue(simulate(result['maze'],result['solution']['moves'])['won'])

if __name__=='__main__':unittest.main()
