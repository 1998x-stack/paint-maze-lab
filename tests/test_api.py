import unittest
from server import api

class ApiTests(unittest.TestCase):
    def test_generation_api(self):
        result = api({'op':'generate','algorithm':'dfs','width':4,'height':4,'seed':42,'verified':True})
        self.assertTrue(result['analysis']['solvable'])
        self.assertTrue(result['solution']['exact'])

    def test_compare_api(self):
        result=api({'op':'compare','width':3,'height':3,'seed':20,'samples':3})
        self.assertEqual(len(result['results']),6)
        for item in result['results']:
            self.assertEqual(item['connected'],3)
            self.assertLessEqual(item['exact'],item['solvable'])

    def test_invalid_limits(self):
        with self.assertRaises(ValueError):api({'op':'generate','width':999})
        with self.assertRaises(ValueError):api({'op':'analyze','ascii':'S'*10001})

if __name__=='__main__':unittest.main()
