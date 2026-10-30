import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {advance, newGame} from '../web/engine.js';
const fixtures=JSON.parse(fs.readFileSync(new URL('./js_parity_cases.json',import.meta.url),'utf8'));
for(const f of fixtures) {
  test(`Python/JS parity: ${f.name}`,()=>{
    let state=newGame(f.maze);
    for(const [i,move] of Array.from(f.moves).entries()){
      state=advance(f.maze,state,move).session;
      assert.deepEqual([state.r,state.c],f.trace[i+1].pos);
      assert.equal(state.paint.size,f.trace[i+1].painted);
    }
    assert.equal(state.paint.size===f.maze.floor_count,f.won);
  });
}
test('invalid movement preserves session and state',()=>{
  const maze={rows:['#####','#...#','#####'],start:[1,1]};
  const s=newGame(maze);
  const t=advance(maze,s,'U');
  assert.equal(t.moved,false);assert.strictEqual(t.session,s);
  assert.equal(s.paint.size,1);
  assert.throws(()=>advance(maze,s,'X'));
});
