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

import {analyzeProgress} from '../web/engine.js';
test('live graph: still-possible corridor',()=>{
  const maze={rows:['#####','#...#','#####'],start:[1,1]};
  assert.equal(analyzeProgress(maze,newGame(maze)).solvable,true);
});
test('live graph: soft-lock after a poor move',()=>{
  const maze={rows:['######','#....#','##.###','######'],start:[1,2]};
  const initial=newGame(maze);
  assert.equal(analyzeProgress(maze,initial).solvable,true);
  const after=advance(maze,initial,'R').session;
  const analysis=analyzeProgress(maze,after);
  assert.equal(analysis.solvable,false);
  assert.equal(analysis.unreachableRemaining,1);
});
test('live graph counts swept cells that cannot be stopping points',()=>{
  const maze={rows:['#######','#.....#','#######'],start:[1,1]};
  const stats=analyzeProgress(maze,newGame(maze));
  assert.equal(stats.reachableStops,2);
  assert.equal(stats.possiblePainted,5);
});
