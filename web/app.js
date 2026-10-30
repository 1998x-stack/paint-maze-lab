import {advance, newGame} from "./engine.js";
const $ = id => document.getElementById(id);
let state = null;
let initial = null;
let movesHistory = [];
let autoTimer = null;
let canvas = $('maze'), ctx = canvas.getContext('2d');
let pointerStart = null;
const dirs = {U:[-1,0],R:[0,1],D:[1,0],L:[0,-1]};
let showStops = false;
function toast(msg) { const node=$('toast'); node.textContent=msg; node.classList.add('show'); clearTimeout(toast.timer); toast.timer=setTimeout(()=>node.classList.remove('show'),3100); }
async function send(payload) {
  const response = await fetch('/api', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
  return data;
}
function stopAuto(){ if(autoTimer!==null){clearInterval(autoTimer);autoTimer=null;} }
function setLevel(data){
  stopAuto(); initial=data; movesHistory=[];
  state=newGame(data.maze);
  $('levelLabel').textContent = data.generation ? `${data.generation.algorithm.toUpperCase()} · #${data.generation.seed}` : 'CUSTOM';
  $('winOverlay').classList.add('hidden'); render();
  if(data.generation && data.generation.attempts>1) toast(`已筛选 ${data.generation.attempts} 个候选，找到可解关卡`);
}
function slide(action){
  if(!state || !dirs[action]) return false;
  const next=advance(initial.maze,state,action);
  if(!next.moved)return false;
  movesHistory.push({r:state.r,c:state.c,paint:new Set(state.paint),moves:state.moves});
  state=next.session;
  render();
  if(state.paint.size===maze.floor_count){
    $('winMoves').textContent=`${state.moves} 次滑动 · 最优 ${initial.solution.exact ? initial.solution.steps : '未知'} 次`;
    $('winOverlay').classList.remove('hidden');stopAuto();
  }
  return true;
}
function render(){
  if (!state) return;
  const {rows,start,width,height,floor_count}=initial.maze;
  const size=640,pad=26,step=Math.min((size-pad*2)/width,(size-pad*2)/height);
  const boardW=step*width,boardH=step*height,ox=(size-boardW)/2,oy=(size-boardH)/2;
  ctx.clearRect(0,0,size,size);ctx.fillStyle='#0a151a';ctx.fillRect(0,0,size,size);
  const bg=ctx.createRadialGradient(size/2,size/2,50,size/2,size/2,size*.65);bg.addColorStop(0,'rgba(75,117,108,.09)');bg.addColorStop(1,'rgba(12,21,25,0)');ctx.fillStyle=bg;ctx.fillRect(0,0,size,size);
  for(let r=0;r<height;r++) for(let c=0;c<width;c++){
    const x=ox+c*step,y=oy+r*step;
    if(rows[r][c]==='#'){
      ctx.fillStyle='#122126';ctx.fillRect(x,y,step,step);
      ctx.strokeStyle='rgba(135,183,165,.065)';ctx.strokeRect(x+.5,y+.5,step-1,step-1);
    }else{
      const painted=state.paint.has(`${r},${c}`);
      ctx.fillStyle=painted?'#72bba8':'#e0c89a';ctx.fillRect(x+1,y+1,step-2,step-2);
      if(painted){ctx.fillStyle='rgba(192,254,202,.18)';ctx.fillRect(x+3,y+3,step-6,Math.max(1,step*.12));}
      else {ctx.fillStyle='rgba(111,80,41,.08)';ctx.beginPath();ctx.arc(x+step/2,y+step/2,step*.1,0,Math.PI*2);ctx.fill();}
      if(showStops && initial.analysis.reachable_stops.some(p=>p[0]===r&&p[1]===c)){
        ctx.fillStyle='rgba(42,64,56,.8)';ctx.beginPath();ctx.arc(x+step*.5,y+step*.5,Math.max(2,step*.08),0,Math.PI*2);ctx.fill();
      }
    }
  }
  const x=ox+(state.c+.5)*step,y=oy+(state.r+.5)*step,rad=step*.32;
  ctx.save();ctx.shadowColor='#b3ffd9';ctx.shadowBlur=23;
  const ball=ctx.createRadialGradient(x-rad*.35,y-rad*.42,rad*.06,x,y,rad*1.2);
  ball.addColorStop(0,'#f0fff7');ball.addColorStop(.15,'#b9fce4');ball.addColorStop(.48,'#4bd1be');ball.addColorStop(1,'#17665f');
  ctx.fillStyle=ball;ctx.beginPath();ctx.arc(x,y,rad,0,2*Math.PI);ctx.fill();ctx.restore();
  ctx.strokeStyle='rgba(236,255,228,.65)';ctx.lineWidth=Math.max(1,rad*.08);ctx.stroke();
  $('paintPercent').textContent=Math.round(state.paint.size/floor_count*100)+'%';
  $('paintBar').style.width=(state.paint.size/floor_count*100)+'%';
  $('floorCount').textContent=floor_count;
  $('moveCount').textContent=state.moves;
  $('stopCount').textContent=initial.analysis.reachable_stop_count;
  $('optimalSteps').textContent=initial.solution.exact?initial.solution.steps:'?';
  $('verdict').textContent=initial.analysis.solvable?'✓ 可完全染色':'✕ 不可完全染色';
  $('verdict').style.color=initial.analysis.solvable?'#c6f76c':'#ffa284';
  $('reason').textContent=initial.analysis.solvable
    ? `静态连通：${initial.analysis.static_connected?'是':'否'} · ${initial.analysis.reachable_painted_count} / ${floor_count} 格可覆盖`
    : `静态连通：${initial.analysis.static_connected?'是':'否'} · ${initial.analysis.unpaintable.length} 格无法覆盖`;
  $('solveMeta').textContent=initial.solution.exact?'EXACT':'BUDGET';
  $('solverOutput').textContent=[`solver: ${initial.solution.method.toUpperCase()}`,
    `exact: ${initial.solution.exact}`,`expanded: ${initial.solution.expanded}`,
    `minimum: ${initial.solution.steps ?? 'unknown'}`,
    `solution: ${initial.solution.moves ?? '—'}`,
    `unpaintable: ${initial.analysis.unpaintable.length}`].join('\n');
}
function infoForGenerate(){return {op:'generate',algorithm:$('algorithm').value,width:Number($('width').value),height:Number($('height').value),seed:Number($('seed').value),loops:Number($('loops').value)/100,min_steps:Number($('minsteps').value),verified:$('verified').checked,budget:60000,attempts:120};}
async function generateLevel(){
  $('generate').disabled=true;$('generate').textContent='正在搜索关卡…';
  try{setLevel(await send(infoForGenerate()));}
  catch(e){toast(`生成失败：${e.message}`);}
  finally{$('generate').disabled=false;$('generate').innerHTML='生成新关卡 <span>↗</span>';}
}
$('generate').onclick=generateLevel;
$('randomseed').onclick=()=>{$('seed').value=Math.floor(Math.random()*4294967295);};
$('loops').oninput=()=>{$('loopLabel').textContent=$('loops').value+'%';};
$('restart').onclick=()=>{if(initial)setLevel(initial);};
$('undo').onclick=()=>{stopAuto();if(!movesHistory.length)return;const prev=movesHistory.pop();state={...prev,paint:new Set(prev.paint)};$('winOverlay').classList.add('hidden');render();};
function currentPayload(){
  return {op:'hint',maze:initial.maze,position:[state.r,state.c],
    painted:[...state.paint].map(v=>v.split(',').map(Number)),budget:60000};
}
async function remainingSolution(){
  if(!initial || !state) return null;
  return (await send(currentPayload())).solution;
}
$('hint').onclick=async()=>{
  if(!initial)return;
  try{
    const answer=await remainingSolution();
    if(!answer.solvable){toast('当前位置无法完成剩余染色；请撤销或重置');return;}
    if(!answer.exact){toast('当前状态搜索超出预算，无法证明最优解');return;}
    const dir=({U:'上',R:'右',D:'下',L:'左'})[answer.moves?.[0]];
    toast(dir?`建议向${dir}滑动 · 剩余最少 ${answer.steps} 步`:'已完成全部染色');
  }catch(e){toast('提示失败：'+e.message);}
};
$('auto').onclick=async()=>{
  stopAuto();
  try{
    const answer=await remainingSolution();
    if(!answer.solvable){toast('当前状态无法完成剩余染色');return;}
    if(!answer.exact || answer.moves===null){toast('剩余路径超出搜索预算');return;}
    let idx=0;
    if(!answer.moves.length){toast('本关已经完成');return;}
    autoTimer=setInterval(()=>{
      if(!initial || idx>=answer.moves.length){stopAuto();return;}
      slide(answer.moves[idx++]);
    },360);
  }catch(e){toast('演示失败：'+e.message);}
};
$('showPreset').onclick=async ()=>{
  // Entire grid is connected, but the junction cannot be used as a stopping position from the start.
  const ascii=`#########\n#S......#\n####.####\n#.......#\n#########`;
  try {setLevel(await send({op:'analyze',ascii}));toast('反例：连通 ≠ 滑动可解');}
  catch(e){toast(e.message);}
};
window.addEventListener('keydown',e=>{
  if(['INPUT','SELECT','TEXTAREA'].includes(document.activeElement.tagName)) return;
  const action=({ArrowUp:'U',ArrowRight:'R',ArrowDown:'D',ArrowLeft:'L',w:'U',d:'R',s:'D',a:'L',W:'U',D:'R',S:'D',A:'L'})[e.key];
  if(action){e.preventDefault();stopAuto();slide(action);}
});
canvas.addEventListener('pointerdown',e=>{pointerStart={x:e.clientX,y:e.clientY};});
canvas.addEventListener('pointerup',e=>{
  if(!pointerStart)return;
  const dx=e.clientX-pointerStart.x,dy=e.clientY-pointerStart.y;pointerStart=null;
  if(Math.max(Math.abs(dx),Math.abs(dy))<22)return;
  stopAuto();slide(Math.abs(dx)>Math.abs(dy)?(dx>0?'R':'L'):(dy>0?'D':'U'));
});
$('compare').onclick=async()=>{
  $('compare').disabled=true;$('compare').textContent='正在计算…';
  try{
    const o=infoForGenerate(),d=await send({op:'compare',width:o.width,height:o.height,seed:o.seed,loops:o.loops,samples:Number($('samples').value),budget:15000});
    $('bars').innerHTML=d.results.map(r=>`<div class="barrow"><span>${r.algorithm.toUpperCase()}</span><div class="track"><div class="fill" style="width:${r.solvable_rate}%"></div></div><b>${r.solvable_rate}%</b></div>`).join('');
    $('benchRows').innerHTML=d.results.map(r=>`<tr><td>${r.algorithm.toUpperCase()}</td><td>${r.solvable}/${r.samples}</td><td>${r.exact}</td><td>${r.mean_steps??'—'}</td><td>${r.elapsed_ms} ms</td></tr>`).join('');
    toast(`基准测试完成：${d.samples_per_algorithm*d.results.length} 个候选关卡`);
  }catch(e){toast('基准测试失败：'+e.message);}
  finally{$('compare').disabled=false;$('compare').textContent='运行基准测试 ↗';}
};
generateLevel();
