"""V2 regression: evolving generator and live-game (not initial-only) solver."""
import unittest
from paintmaze import Maze, SlidingGraph, assess, generate, generate_validated, solve, simulate
from paintmaze.evolve import evolve_maze, transform
from server import api

TRAP = Maze.from_ascii('''
######
#.S.##
##.###
######
''')

class DynamicSolverTests(unittest.TestCase):
    def test_start_solvable_but_move_can_trap_player(self):
        self.assertTrue(assess(TRAP)['solvable'])
        baseline = solve(TRAP, method='astar')
        self.assertTrue(baseline['exact'])
        self.assertEqual(baseline['steps'], 4)
        graph=SlidingGraph(TRAP)
        pos,mask,path = graph.step(TRAP.start,graph.start_mask,'R')
        result=solve(TRAP, method='astar',start_position=pos,painted=[TRAP.start,*path])
        self.assertFalse(result['solvable'])
        self.assertTrue(result['exact'])
        self.assertEqual(result['reason'],'unreachable_remaining')

    def test_arbitrary_progress_uses_current_mask(self):
        m=Maze.from_ascii('#####\n#S..#\n#####')
        result=solve(m,start_position=(1,3),painted=[(1,1),(1,2),(1,3)])
        self.assertEqual(result['steps'],0)
        self.assertEqual(result['moves'],'')

    def test_state_validation(self):
        m=Maze.from_ascii('#####\n#S..#\n#####')
        for kwargs in ({'start_position':(0,0)}, {'painted':[(0,0)]},
                       {'painted':[(1,2)]}):
            with self.assertRaises(ValueError):solve(m,**kwargs)

    def test_hint_api_uses_current_game_state(self):
        data={'rows':list(TRAP.rows),'start':list(TRAP.start)}
        good=api({'op':'hint','maze':data,'position':list(TRAP.start),
                  'painted':[list(TRAP.start)]})
        self.assertTrue(good['solution']['solvable'])
        bad=api({'op':'hint','maze':data,'position':[1,3],
                 'painted':[[1,2],[1,3]]})
        self.assertEqual(bad['solution']['reason'],'unreachable_remaining')

    def test_hint_bad_request(self):
        with self.assertRaises(ValueError): api({'op':'hint','maze':{'rows':['###'],'start':[0,0]},'position':[0,0],'painted':[[0,0]]})

class EvolvedGeneratorTests(unittest.TestCase):
    def test_seed_reproducibility_and_diversity(self):
        samples=[generate(4,4,'evolve',seed) for seed in range(12)]
        self.assertGreaterEqual(len(set(samples)), 8)
        for seed,maze in enumerate(samples):
            self.assertEqual(maze,generate(4,4,'evolve',seed))
            self.assertEqual((maze.width, maze.height), (9,9))
            self.assertTrue(assess(maze)['solvable'])

    def test_all_evolved_cases_have_valid_exact_winning_solutions(self):
        for w,h in ((2,3),(3,3),(4,4),(5,4)):
            for seed in range(18):
                result=evolve_maze(w,h,seed,18,60000)
                self.assertEqual((result.maze.width,result.maze.height),(2*w+1,2*h+1))
                self.assertTrue(assess(result.maze)['solvable'])
                self.assertTrue(result.solution['exact'])
                self.assertTrue(simulate(result.maze,result.solution['moves'])['won'])
                self.assertLessEqual(result.accepted,result.attempted)

    def test_min_steps_target(self):
        result=generate_validated(coarse_width=4,coarse_height=4,algorithm='evolve',
                                  seed=2,min_steps=10,attempts=50,extra_loops=.35)
        self.assertGreaterEqual(result['solution']['steps'],10)
        self.assertGreater(result['generation']['accepted_mutations'],0)
        with self.assertRaises(RuntimeError):
            generate_validated(coarse_width=4,coarse_height=4,algorithm='evolve',
                               seed=2,min_steps=100,attempts=12)

    def test_geometry_transform_preserves_paintability(self):
        m=generate(3,4,'snake',10)
        for h in (False,True):
            for v in (False,True):
                for t in (False,True):
                    candidate=transform(m,h,v,t)
                    self.assertTrue(assess(candidate)['solvable'])
                    self.assertEqual(len(m.cells),len(candidate.cells))

if __name__=='__main__': unittest.main()
