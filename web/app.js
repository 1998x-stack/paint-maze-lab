import {advance, newGame, analyzeProgress} from './engine.js';

const $ = id => document.getElementById(id);
const board = $('maze');
const ctx = board.getContext('2d');
const names = {U:'上', R:'右', D:'下', L:'左'};
let state = null;
let initial = null;
let history = [];
let animation = null;
let playbackId = 0;
let hintMove = null;
let pointerStart = null;
let startedAt = null;
let finishedSeconds = null;
let loadingId = 0;
const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
const colors = {floor:'#e0c89a', painted:'#72bba8', wall:'#122126'};

function toast(message) {
  const el=$('toast'); el.textContent=message; el.classList.add('show');
  clearTimeout(toast.timeout);
  toast.timeout=setTimeout(()=>el.classList.remove('show'),3200);
}
async function send(payload) {
  const res=await fetch('/api',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
  const json=await res.json();
  if (!res.ok) throw new Error(json.error || `HTTP ${res.status}`);
  return json;
}
function stopPlayback() {
  playbackId++;
  if(animation) {
    cancelAnimationFrame(animation.frame);
    const pending=animation;
    animation=null;
    pending.resolve(false);
  }
}
function restore(snapshot) {
  state={r:snapshot.r,c:snapshot.c,moves:snapshot.moves,paint:new Set(snapshot.paint)};
}
function stopClock() {
  finishedSeconds=startedAt===null?0:Math.max(0,Math.floor((Date.now()-startedAt)/1000));
}
function clockText(seconds) {
  const mm=Math.floor(seconds/60).toString().padStart(2,'0');
  const ss=(seconds%60).toString().padStart(2,'0');
  return `${mm}:${ss}`;
}
function elapsedSeconds() {
  return finishedSeconds!==null?finishedSeconds:startedAt===null?0:Math.floor((Date.now()-startedAt)/1000);
}
function setLevel(data) {
  stopPlayback(); initial=data; history=[]; state=newGame(data.maze);
  hintMove=null; startedAt=null; finishedSeconds=null;
  $('winOverlay').classList.add('hidden');
  $('levelLabel').textContent=data.generation?`${data.generation.algorithm.toUpperCase()} · #${data.generation.seed}`:'CUSTOM';
  const d=data.difficulty;
  $('difficultyScore').textContent=d?`${d.score} / 100 · ${({relaxed:'休闲',standard:'标准',challenging:'挑战',expert:'专家'})[d.tier]}`:'—';
  const request=data.generation?.curation;
  $('difficultyDetails').textContent=d?`最优 ${d.optimal_steps} 步 · 转向 ${d.turns} 次 · 重复行进 ${(d.repeated_travel_ratio*100).toFixed(0)}%${request && !request.tier_preference_met?' · 未命中预设档位（已选择最接近候选）':''}`:'需要精确解才能评分';
  if(request && request.unique_valid_candidates===0) toast('没有可用的精确求解关卡');
  if(request && request.target_distance>0) toast(`已选择距目标最接近的关卡，偏差 ${request.target_distance} 步`);
  render();
}
function boardGeometry(maze) {
  const size=640, pad=24;
  const step=Math.min((size-pad*2)/maze.width,(size-pad*2)/maze.height);
  return {size,step, ox:(size-step*maze.width)/2,oy:(size-step*maze.height)/2};
}
function render(view=state, ballAt=null) {
  if(!state || !initial) return;
  const maze=initial.maze;
  const {size,step,ox,oy}=boardGeometry(maze);
  ctx.clearRect(0,0,size,size);
  ctx.fillStyle='#091519';ctx.fillRect(0,0,size,size);
  const hintPath=hintMove?advance(maze, state, hintMove).path:[];
  const hinted=new Set(hintPath.map(([r,c])=>`${r},${c}`));
  for(let r=0;r<maze.height;r++) for(let c=0;c<maze.width;c++) {
    const x=ox+c*step,y=oy+r*step;
    if(maze.rows[r][c]==='#') {
      ctx.fillStyle=colors.wall;ctx.fillRect(x,y,step,step);
      ctx.strokeStyle='rgba(135,183,165,.065)';ctx.strokeRect(x+.5,y+.5,step-1,step-1);
    } else {
      const painted=view.paint.has(`${r},${c}`);
      ctx.fillStyle=painted?colors.painted:colors.floor;
      ctx.fillRect(x+1,y+1,Math.max(0,step-2),Math.max(0,step-2));
      if(painted) {
        ctx.fillStyle='rgba(192,254,202,.2)';
        ctx.fillRect(x+3,y+3,Math.max(0,step-6),Math.max(1,step*.12));
      } else {
        ctx.fillStyle='rgba(111,80,41,.1)';ctx.beginPath();ctx.arc(x+step/2,y+step/2,step*.1,0,2*Math.PI);ctx.fill();
      }
      if(hinted.has(`${r},${c}`)) {
        ctx.fillStyle='rgba(255,255,145,.38)';ctx.fillRect(x+step*.14,y+step*.14,step*.72,step*.72);
      }
    }
  }
  const y=ballAt?ballAt[0]:view.r, x=ballAt?ballAt[1]:view.c;
  const px=ox+(x+.5)*step,py=oy+(y+.5)*step,rad=Math.max(3,step*.3);
  ctx.save();ctx.shadowColor='#b3ffd9';ctx.shadowBlur=18;
  const grad=ctx.createRadialGradient(px-rad*.3,py-rad*.4,1,px,py,rad*1.2);
  grad.addColorStop(0,'#eafff8');grad.addColorStop(.2,'#b9fce4');grad.addColorStop(.6,'#4bd1be');grad.addColorStop(1,'#17665f');
  ctx.fillStyle=grad;ctx.beginPath();ctx.arc(px,py,rad,0,2*Math.PI);ctx.fill();ctx.restore();
  const progress=view.paint.size/maze.floor_count*100;
  $('paintPercent').textContent=`${Math.round(progress)}%`;
  $('paintBar').style.width=`${progress}%`;
  $('floorCount').textContent=maze.floor_count;
  $('moveCount').textContent=view.moves;
  $('optimalSteps').textContent=initial.solution?.exact?initial.solution.steps:'?';
  const live=analyzeProgress(maze,view);
  $('stopCount').textContent=live.reachableStops;
  const won=view.paint.size===maze.floor_count;
  $('verdict').textContent=won?'✓ 全部染色完成':live.solvable?'✓ 剩余区域仍可染色':'✕ 当前位置已无法染完';
  $('verdict').style.color=live.solvable?'#c6f76c':'#ffa284';
  $('reason').textContent=live.solvable?`当前可覆盖 ${live.possiblePainted} / ${live.total} 格`:`当前有 ${live.unreachableRemaining} 格无法再经过，请撤销或重置`;
  $('liveStatus').textContent=won?'已通关！':live.solvable?`剩余 ${maze.floor_count-view.paint.size} 格 · 可继续完成`:'走入不可逆区域！建议撤销';
  $('liveStatus').classList.toggle('danger',!live.solvable);
  $('solveMeta').textContent=initial.solution.exact?'EXACT':'UNPROVEN';
  $('solverOutput').textContent=[`solver: ${initial.solution.method.toUpperCase()}`,`exact: ${initial.solution.exact}`,`expanded: ${initial.solution.expanded}`,`minimum: ${initial.solution.steps ?? 'unknown'}`,`solution: ${initial.solution.moves ?? '—'}`,`current_pos: ${view.r},${view.c}`,`live_solvable: ${live.solvable}`].join('\n');
  $('clock').textContent=clockText(elapsedSeconds());
}
function completeIfWon() {
  if(state.paint.size!==initial.maze.floor_count)return;
  stopClock();
  const opt=initial.solution.exact?initial.solution.steps:null;
  const ratio=opt!==null&&state.moves>0?Math.round(100*opt/state.moves):null;
  $('winMoves').textContent=`${state.moves} 次滑动 · 最优 ${opt??'未知'} 次 · 效率 ${ratio??'—'}% · 用时 ${clockText(elapsedSeconds())}`;
  $('winOverlay').classList.remove('hidden');
  stopPlayback();
}
/** Animate paint tile-by-tile while preserving deterministic logical transitions. */
function slide(action) {
  if(!initial || !state || animation || !names[action] || state.paint.size===initial.maze.floor_count)return Promise.resolve(false);
  const next=advance(initial.maze,state,action);
  if(!next.moved)return Promise.resolve(false);
  const before={r:state.r,c:state.c,paint:new Set(state.paint),moves:state.moves};
  hintMove=null;
  if(startedAt===null)startedAt=Date.now();
  const finish=()=>{
    history.push(before);
    state=next.session;
    render();
    const live=analyzeProgress(initial.maze,state);
    if(!live.solvable)toast('这一步会进入无法完成的区域；点击「撤销」返回');
    completeIfWon();
    return true;
  };
  if(reducedMotion.matches || !globalThis.requestAnimationFrame)return Promise.resolve(finish());
  const duration=Math.min(620,140+next.path.length*48);
  return new Promise(resolve=>{
    const started=performance.now();
    const anim={frame:null,resolve};
    animation=anim;
    function tick(now) {
      if(animation!==anim)return;
      const t=Math.min(1,(now-started)/duration);
      const traveled=t*next.path.length;
      const whole=Math.min(next.path.length,Math.floor(traveled));
      const paint=new Set(before.paint);
      for(let i=0;i<whole;i++)paint.add(`${next.path[i][0]},${next.path[i][1]}`);
      const first=whole===0?[before.r,before.c]:next.path[whole-1];
      const second=next.path[Math.min(whole,next.path.length-1)];
      const u=t===1?1:traveled-whole;
      const ballAt=[first[0]+(second[0]-first[0])*u,first[1]+(second[1]-first[1])*u];
      render({r:before.r,c:before.c,paint,moves:before.moves},ballAt);
      if(t<1){anim.frame=requestAnimationFrame(tick);return;}
      animation=null;
      resolve(finish());
    }
    anim.frame=requestAnimationFrame(tick);
  });
}
function infoForGenerate() {
  const p={op:'generate',algorithm:$('algorithm').value,width:Number($('width').value),height:Number($('height').value),seed:Number($('seed').value),loops:Number($('loops').value)/100,min_steps:Number($('minsteps').value),verified:$('verified').checked,budget:60000,attempts:100};
  if(p.verified) {
    p.difficulty=$('difficulty').value;
    p.candidates=Number($('candidates').value);
    if($('maxsteps').value!=='')p.max_steps=Number($('maxsteps').value);
    if($('targetsteps').value!=='')p.target_steps=Number($('targetsteps').value);
  }
  return p;
}
async function generateLevel() {
  const id=++loadingId;
  stopPlayback();$('generate').disabled=true;$('generate').textContent='正在校验候选…';
  try {const result=await send(infoForGenerate());if(id===loadingId)setLevel(result);}
  catch(e){if(id===loadingId)toast(`生成失败：${e.message}`);}
  finally{if(id===loadingId){$('generate').disabled=false;$('generate').textContent='生成新关卡 ↗';}}
}
function hintPayload() {
  return {op:'hint',maze:initial.maze,position:[state.r,state.c],painted:[...state.paint].map(v=>v.split(',').map(Number)),budget:60000};
}
async function remainingSolution() {return (await send(hintPayload())).solution;}
function resetLevel() {if(initial){stopPlayback();setLevel(initial);}}
function undo() {
  stopPlayback();if(!history.length)return;
  restore(history.pop()); hintMove=null;finishedSeconds=null;
  $('winOverlay').classList.add('hidden');render();
}
async function hint() {
  if(!initial || animation)return;
  const level=initial, before=state;
  try {
    const a=await remainingSolution();
    if(level!==initial || before!==state)return;
    if(!a.solvable){toast('当前状态无法染完，请撤销或重新开始');return;}
    if(!a.exact){toast('搜索预算耗尽，无法提供可靠的最优提示');return;}
    hintMove=a.moves[0]??null;
    render();
    toast(hintMove?`建议向${names[hintMove]}滑动 · 最少还需 ${a.steps} 步`:'已全部完成');
  } catch(e){toast(`提示失败：${e.message}`);}
}
async function autoSolve() {
  stopPlayback(); if(!initial)return;
  const id=playbackId, level=initial, snapshot=state;
  try {
    const answer=await remainingSolution();
    if(id!==playbackId || level!==initial || snapshot!==state)return;
    if(!answer.solvable){toast('当前状态已经无法通关');return;}
    if(!answer.exact || answer.moves===null){toast('搜索预算不足，无法自动演示');return;}
    if(!answer.moves.length){toast('全部地板已经染色');return;}
    for(const action of answer.moves) {
      if(id!==playbackId || level!==initial)break;
      const worked=await slide(action);
      if(!worked)break;
    }
  } catch(e){toast(`演示失败：${e.message}`);}
}
$('generate').onclick=generateLevel;
$('nextLevel').onclick=()=>{$('seed').value=(Number($('seed').value)+1)>>>0;generateLevel();};
$('randomseed').onclick=()=>{$('seed').value=Math.floor(Math.random()*2**32);};
$('loops').oninput=()=>{$('loopLabel').textContent=`${$('loops').value}%`;};
$('verified').onchange=()=>{if(!$('verified').checked)toast('未验证关卡可能无解，难度筛选也会停用');};
$('restart').onclick=resetLevel;
$('undo').onclick=undo;
$('hint').onclick=hint;
$('auto').onclick=autoSolve;
$('showPreset').onclick=async()=>{
  try {
    const data=await send({op:'analyze',ascii:'#########\n#S......#\n####.####\n#.......#\n#########'});
    setLevel(data);toast('此反例静态连通，却不能滑到所有区域');
  } catch(e){toast(`载入失败：${e.message}`);}
};
function moveManual(action){stopPlayback();slide(action);}
for(const button of document.querySelectorAll('[data-dir]')) button.addEventListener('click',()=>moveManual(button.dataset.dir));
window.addEventListener('keydown',e=>{
  if(['INPUT','SELECT','TEXTAREA'].includes(document.activeElement?.tagName))return;
  const action=({ArrowUp:'U',ArrowRight:'R',ArrowDown:'D',ArrowLeft:'L',w:'U',a:'L',s:'D',d:'R',W:'U',A:'L',S:'D',D:'R'})[e.key];
  if(action){e.preventDefault();moveManual(action);}
});
board.addEventListener('pointerdown',e=>{pointerStart={x:e.clientX,y:e.clientY};board.setPointerCapture?.(e.pointerId);});
board.addEventListener('pointercancel',()=>{pointerStart=null;});
board.addEventListener('pointerup',e=>{
  if(!pointerStart)return;
  const dx=e.clientX-pointerStart.x,dy=e.clientY-pointerStart.y;pointerStart=null;
  if(Math.max(Math.abs(dx),Math.abs(dy))<20)return;
  moveManual(Math.abs(dx)>Math.abs(dy)?(dx>0?'R':'L'):(dy>0?'D':'U'));
});
document.addEventListener('visibilitychange',()=>{if(document.hidden)stopPlayback();});
setInterval(()=>{if(state && !animation)$('clock').textContent=clockText(elapsedSeconds());},1000);
$('compare').onclick=async()=>{
  $('compare').disabled=true;$('compare').textContent='正在计算…';
  try {
    const p=infoForGenerate();
    const result=await send({op:'compare',width:p.width,height:p.height,seed:p.seed,loops:p.loops,samples:Number($('samples').value),budget:15000});
    $('bars').innerHTML=result.results.map(r=>`<div class="barrow"><span>${r.algorithm.toUpperCase()}</span><div class="track"><div class="fill" style="width:${r.solvable_rate}%"></div></div><b>${r.solvable_rate}%</b></div>`).join('');
    $('benchRows').innerHTML=result.results.map(r=>`<tr><td>${r.algorithm.toUpperCase()}</td><td>${r.solvable}/${r.samples}</td><td>${r.exact}</td><td>${r.mean_steps??'—'}</td><td>${r.elapsed_ms} ms</td></tr>`).join('');
    toast(`已验证 ${result.samples_per_algorithm*result.results.length} 个候选`);
  } catch(e){toast(`基准测试失败：${e.message}`);}
  finally{$('compare').disabled=false;$('compare').textContent='运行基准测试 ↗';}
};
generateLevel();
