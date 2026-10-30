import unittest
from paintmaze import Maze, solve, simulate, assess
from paintmaze.difficulty import measure, curate
from server import api

class DifficultyTests(unittest.TestCase):
    def test_metrics_prove_exact_solution(self):
        maze = Maze.from_ascii('#####\n#S..#\n#####')
        sol = solve(maze)
        stats = measure(maze, sol)
        self.assertEqual(stats['optimal_steps'], 1)
        self.assertEqual(stats['turns'], 0)
        self.assertEqual(stats['travel_tiles'], 2)
        self.assertEqual(stats['repeated_travel_ratio'], 0)
        self.assertIn(stats['tier'], ('relaxed','standard','challenging','expert'))
        self.assertEqual(stats, measure(maze, sol))

    def test_reject_nonexact(self):
        maze = Maze.from_ascii('#####\n#S..#\n#####')
        with self.assertRaises(ValueError): measure(maze, {'exact':False})
        with self.assertRaises(ValueError): measure(maze, {'exact':True,'solvable':True,'moves':'L'})

    def test_curate_reproducible_and_win(self):
        args = dict(coarse_width=3, coarse_height=3, algorithm='evolve', seed=41,
                    difficulty='standard', candidates=3, attempts=2, max_states=25000)
        a = curate(**args); b = curate(**args)
        self.assertEqual(a['maze'], b['maze'])
        self.assertEqual(a['difficulty'], b['difficulty'])
        self.assertTrue(simulate(a['maze'], a['solution']['moves'])['won'])
        self.assertTrue(assess(a['maze'])['solvable'])
        self.assertTrue(a['solution']['exact'])
        self.assertIn('tier_preference_met', a['generation']['curation'])

    def test_step_constraints(self):
        result = curate(coarse_width=3, coarse_height=3, algorithm='snake', seed=3,
                        candidates=3, max_steps=100, target_steps=6)
        self.assertGreaterEqual(result['solution']['steps'], 1)
        self.assertEqual(result['generation']['curation']['candidate_count'],3)
        with self.assertRaises(RuntimeError):
            curate(coarse_width=3, coarse_height=3, algorithm='snake',
                   candidates=2, max_steps=1)
        with self.assertRaises(ValueError):
            curate(max_steps=2, min_steps=3)
        with self.assertRaises(ValueError):
            curate(target_steps=10, max_steps=5)

    def test_api_difficulty_and_invalid_params(self):
        result = api({'op':'generate','algorithm':'evolve','width':3,'height':3,
                      'seed':5,'difficulty':'standard','candidates':3})
        self.assertTrue(result['solution']['exact'])
        self.assertIn('difficulty',result)
        with self.assertRaises(ValueError):
            api({'op':'generate','difficulty':'impossible'})
        with self.assertRaises(ValueError):
            api({'op':'generate','difficulty':'standard','candidates':250})
        with self.assertRaises(RuntimeError):
            api({'op':'generate','algorithm':'snake','width':3,'height':3,'max_steps':1})

class TutorialTests(unittest.TestCase):
    def test_seeded_tutorial_is_one_or_two_slides(self):
        from paintmaze.evolve import tutorial_maze
        for w,h in ((2,3),(4,5),(5,2)):
            for seed in range(30):
                maze=tutorial_maze(w,h,seed)
                self.assertEqual((maze.width,maze.height),(2*w+1,2*h+1))
                s=solve(maze)
                self.assertTrue(s['exact'])
                self.assertTrue(assess(maze)['solvable'])
                self.assertLessEqual(s['steps'],2)
                self.assertTrue(simulate(maze,s['moves'])['won'])

    def test_relaxed_candidates_hit_tier(self):
        result=curate(coarse_width=4,coarse_height=4,algorithm='evolve',
                      difficulty='relaxed',seed=42,candidates=6)
        self.assertEqual(result['difficulty']['tier'],'relaxed')
        self.assertEqual(result['generation']['template'],'tutorial')
        self.assertTrue(result['generation']['curation']['tier_preference_met'])

    def test_work_budget_rejects_excessive_queries(self):
        with self.assertRaises(ValueError):
            api({'op':'generate','difficulty':'standard','attempts':500,'candidates':24})
