"""End-to-end HTTP response and content contract, without using a browser."""
import json
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from server import Handler

class HTTPContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()
        cls.base=f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(2)

    def test_homepage_and_module(self):
        with urllib.request.urlopen(self.base+'/') as r:
            self.assertEqual(r.status,200)
            self.assertIn('PAINT MAZE',r.read().decode())
        with urllib.request.urlopen(self.base+'/engine.js') as r:
            self.assertEqual(r.status,200)
            self.assertIn('export function advance',r.read().decode())

    def test_generated_level_http(self):
        payload={'op':'generate','algorithm':'snake','width':4,'height':4,'verified':True}
        req=urllib.request.Request(self.base+'/api',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(req) as r:
            out=json.load(r)
        self.assertEqual(out['solution']['steps'],7)
        self.assertTrue(out['analysis']['solvable'])
        self.assertTrue(out['solution']['exact'])

    def test_live_hint_http(self):
        payload={'op':'hint', 'maze': {'rows': ['######', '#...##','##.###', '######'],
                'start': [1,2]}, 'position':[1,3], 'painted': [[1,2],[1,3]]}
        req=urllib.request.Request(self.base+'/api',data=json.dumps(payload).encode(),
                                   headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(req) as r:
            data=json.load(r)
        self.assertFalse(data['solution']['solvable'])
        self.assertEqual(data['solution']['reason'],'unreachable_remaining')

    def test_no_path_traversal(self):
        from urllib.error import HTTPError
        with self.assertRaises(HTTPError) as e:
            urllib.request.urlopen(self.base+'/does-not-exist')
        self.assertEqual(e.exception.code,404)

if __name__=='__main__':unittest.main()
