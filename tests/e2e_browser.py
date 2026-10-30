"""Real browser acceptance; requires `pip install playwright` and installed Chromium.

Run from repository root: python tests/e2e_browser.py
This is separate from the dependency-free unit tests.
"""
from __future__ import annotations
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import urlopen

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def main():
    port=free_port()
    server=subprocess.Popen([sys.executable,'server.py','--port',str(port)],
                            cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    try:
        for _ in range(60):
            if server.poll() is not None:
                raise RuntimeError('Game server stopped before E2E started')
            try:
                with urlopen(f'http://127.0.0.1:{port}/',timeout=1) as response:
                    if response.status==200:break
            except OSError:
                time.sleep(.1)
        else: raise RuntimeError('Game server did not become ready')
        with sync_playwright() as play:
            browser=play.chromium.launch(headless=True)
            page=browser.new_page(viewport={'width':1365,'height':900}, reduced_motion='reduce')
            errors=[]
            page.on('pageerror',lambda e: errors.append(str(e)))
            page.goto(f'http://127.0.0.1:{port}/', wait_until='networkidle',timeout=30000)
            page.locator('#floorCount').get_by_text('—').count() # ensure selector exists
            page.locator('#algorithm').select_option('snake')
            page.locator('#difficulty').select_option('any')
            page.locator('#width').fill('3')
            page.locator('#height').fill('3')
            page.locator('#generate').click()
            page.wait_for_function("document.querySelector('#floorCount').textContent !== '—'",timeout=20000)
            initial_moves=page.locator('#moveCount').inner_text()
            assert initial_moves=='0',f'expected zero moves, got {initial_moves}'
            page.locator('#hint').click()
            page.wait_for_function("document.querySelector('#toast').textContent.includes('建议')",timeout=20000)
            page.locator('#auto').click()
            page.locator('#winOverlay').wait_for(state='visible',timeout=30000)
            assert '全部染色完成' in page.locator('#winOverlay').inner_text()
            assert int(page.locator('#moveCount').inner_text())>0
            page.locator('#undo').click()
            page.locator('#winOverlay').wait_for(state='hidden',timeout=5000)
            page.locator('#restart').click()
            assert page.locator('#moveCount').inner_text()=='0'
            page.screenshot(path=str(ROOT/'browser-smoke.png'),full_page=True)
            assert not errors,'Unexpected browser exceptions: '+'; '.join(errors)
            print('Browser E2E passed: generate → hint → auto-win → undo → reset')
            browser.close()
    finally:
        server.terminate()
        try: server.wait(timeout=5)
        except subprocess.TimeoutExpired: server.kill()


if __name__=='__main__':
    main()
