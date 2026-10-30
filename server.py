"""Zero-third-party-dependency local web server. python server.py --port 8765"""
from __future__ import annotations
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlsplit
from pathlib import Path
import json
import argparse
import mimetypes
import time
from paintmaze import Maze, assess, solve, generate, generate_validated, ALGORITHMS
from paintmaze.difficulty import curate, measure, TIERS

WEB = Path(__file__).resolve().parent / 'web'

def as_int(obj, name, default, lo, hi):
    value = int(obj.get(name, default))
    if not lo <= value <= hi: raise ValueError(f'{name} out of range: {lo}..{hi}')
    return value

def as_float(obj, name, default, lo, hi):
    value = float(obj.get(name, default))
    if not lo <= value <= hi: raise ValueError(f'{name} out of range: {lo}..{hi}')
    return value

def result_for(maze, method='astar', budget=60000):
    return {'maze': maze.data(), 'analysis': assess(maze),
            'solution': solve(maze, method=method, max_states=budget)}

def api(payload):
    op = payload.get('op')
    if op == 'generate':
        w = as_int(payload, 'width', 4, 2, 9)
        h = as_int(payload, 'height', 4, 2, 9)
        seed = as_int(payload, 'seed', 42, 0, 2**32-1)
        loops = as_float(payload, 'loops', 0.12, 0, 1)
        alg = payload.get('algorithm', 'dfs')
        if alg not in ALGORITHMS: raise ValueError('Unsupported algorithm')
        verified = payload.get('verified', True) is True
        if verified:
            attempts = as_int(payload, 'attempts', 120, 1, 500)
            min_steps = as_int(payload, 'min_steps', 0, 0, 150)
            budget = as_int(payload, 'budget', 60000, 100, 150000)
            preset = payload.get('difficulty', 'any')
            if not isinstance(preset, str) or preset not in ('any', *TIERS):
                raise ValueError('Unsupported difficulty preset')
            max_steps = as_int(payload, 'max_steps', 150, 0, 150) if 'max_steps' in payload else None
            target_steps = as_int(payload, 'target_steps', 0, 0, 150) if 'target_steps' in payload else None
            if max_steps is not None or target_steps is not None or preset != 'any':
                if attempts * as_int(payload,'candidates',5,1,24) > 1200:
                    raise ValueError('Curation work budget exceeded (attempts × candidates > 1200)')
                r = curate(coarse_width=w, coarse_height=h, algorithm=alg, seed=seed,
                           extra_loops=loops, attempts=attempts, min_steps=min_steps,
                           max_steps=max_steps, target_steps=target_steps, difficulty=preset,
                           candidates=as_int(payload, 'candidates', 5, 1, 24), max_states=budget)
            else:
                r = generate_validated(coarse_width=w, coarse_height=h, algorithm=alg, seed=seed,
                                       extra_loops=loops, attempts=attempts,
                                       min_steps=min_steps, max_states=budget)
                r['difficulty'] = measure(r['maze'], r['solution'])
            output = result_for(r['maze'], budget=60000)
            output['solution'] = r['solution']
            output['generation'] = r['generation']
            output['difficulty'] = r['difficulty']
            return output
        m = generate(w, h, alg, seed, loops)
        output = result_for(m)
        output['generation'] = {'algorithm': alg, 'seed': seed, 'attempts': 1}
        if output['solution']['exact'] and output['solution']['solvable']:
            output['difficulty'] = measure(m, output['solution'])
        return output
    if op == 'analyze':
        text = str(payload.get('ascii', ''))
        if len(text) > 5000: raise ValueError('Maze too large')
        maze = Maze.from_ascii(text)
        if maze.height > 40 or maze.width > 40: raise ValueError('Maze too large')
        return result_for(maze, method=payload.get('method','astar'))
    if op == 'hint':
        # Stateless hint: validate entire client-supplied state; no trusted
        # mutable sessions, and never silently reset to original start.
        data = payload.get('maze')
        if not isinstance(data, dict): raise ValueError('Missing maze')
        rows = data.get('rows')
        start = data.get('start')
        if not isinstance(rows, list) or len(rows) > 40 or not all(isinstance(r,str) for r in rows):
            raise ValueError('Invalid maze rows')
        if len(rows) * max(map(len, rows), default=0) > 1600:
            raise ValueError('Maze too large')
        maze = Maze(tuple(rows), tuple(start))
        pos = payload.get('position')
        painted = payload.get('painted')
        if not isinstance(pos, list) or len(pos)!=2 or not isinstance(painted,list):
            raise ValueError('Invalid current state')
        if len(painted) > 1600: raise ValueError('Too many painted tiles')
        return {'solution': solve(maze, method=payload.get('method','astar'),
                max_states=as_int(payload,'budget',60000,100,150000),
                start_position=pos, painted=painted)}
    if op == 'compare':
        samples = as_int(payload, 'samples', 20, 1, 80)
        width = as_int(payload, 'width', 4, 2, 8)
        height = as_int(payload, 'height', 4, 2, 8)
        seed = as_int(payload, 'seed', 42, 0, 2**32-1)
        loops = as_float(payload, 'loops', 0.12, 0, 1)
        results = []
        for alg in ALGORITHMS:
            t0 = time.perf_counter()
            solved, exact, best_steps, expanded, static_connected = 0, 0, [], [], 0
            for i in range(samples):
                m = generate(width, height, alg, seed + i, loops)
                assessment = assess(m)
                static_connected += assessment['static_connected']
                if assessment['solvable']:
                    solved += 1
                    ans = solve(m, method='astar', max_states=as_int(payload, 'budget', 15000, 100, 100000))
                    if ans['exact']:
                        exact += 1
                        best_steps.append(ans['steps'])
                        expanded.append(ans['expanded'])
            ms = 1000 * (time.perf_counter() - t0)
            results.append({'algorithm': alg, 'samples': samples, 'connected': static_connected,
                            'solvable': solved, 'solvable_rate': round(solved/samples*100, 1),
                            'exact': exact, 'mean_steps': round(sum(best_steps)/len(best_steps),2) if best_steps else None,
                            'mean_expanded': round(sum(expanded)/len(expanded),1) if expanded else None,
                            'elapsed_ms': round(ms, 1)})
        return {'results': results, 'seed_start': seed, 'width':width, 'height':height,
                'samples_per_algorithm': samples, 'loops': loops,
                'note': 'Mean steps computed only on solvable cases solved exactly, so it is conditional and can be selection-biased.'}
    raise ValueError('Unknown op')

class Handler(BaseHTTPRequestHandler):
    def send_bytes(self, code, content, content_type):
        self.send_response(code)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(content)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(content)

    def do_POST(self):
        if urlsplit(self.path).path != '/api':
            return self.send_bytes(404,b'not found','text/plain')
        try:
            length = int(self.headers.get('Content-Length','0'))
            if not 0 < length <= 10000: raise ValueError('Body size invalid')
            payload = json.loads(self.rfile.read(length))
            result = api(payload)
            self.send_bytes(200,json.dumps(result,ensure_ascii=False).encode(),'application/json; charset=utf-8')
        except (ValueError, RuntimeError, KeyError, TypeError, RecursionError) as e:
            self.send_bytes(400,json.dumps({'error':str(e)},ensure_ascii=False).encode(),'application/json; charset=utf-8')

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == '/': path = '/index.html'
        path = Path(path.lstrip('/'))
        if '..' in path.parts or len(path.parts)>2:
            return self.send_bytes(404,b'not found','text/plain')
        file = (WEB/path).resolve()
        if not file.is_relative_to(WEB.resolve()) or not file.is_file():
            return self.send_bytes(404,b'not found','text/plain')
        mime = mimetypes.guess_type(str(file))[0] or 'application/octet-stream'
        if mime.startswith('text/') or mime == 'application/javascript': mime += '; charset=utf-8'
        self.send_bytes(200,file.read_bytes(),mime)

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--host', default='127.0.0.1')
    p.add_argument('--port', type=int, default=8765)
    a = p.parse_args()
    print(f'Paint Maze Lab -> http://{a.host}:{a.port}',flush=True)
    ThreadingHTTPServer((a.host,a.port), Handler).serve_forever()
