/** A dependency-free, deterministic browser game transition.
 * Cells are encoded in a Set as "row,column". Matches paintmaze.core.SlidingGraph.step.
 */
export const DIRECTIONS = Object.freeze({U:[-1,0],R:[0,1],D:[1,0],L:[0,-1]});
export function advance(maze, current, direction) {
  const delta=DIRECTIONS[direction];
  if(!delta) throw new RangeError('Direction must be U, R, D, L');
  const [dr,dc]=delta;
  let r=current.r,c=current.c;
  if(maze.rows[r+dr]?.[c+dc]!=='.') return {moved:false,session:current,path:[]};
  const paint=new Set(current.paint);
  const path=[];
  while(maze.rows[r+dr]?.[c+dc]==='.') {
    r+=dr;c+=dc;
    paint.add(`${r},${c}`);
    path.push([r,c]);
  }
  return {moved:true,session:{r,c,paint,moves:current.moves+1},path};
}
export function newGame(maze) {
  const [r,c]=maze.start;
  if(maze.rows[r]?.[c]!=='.') throw new TypeError('Start must be a floor cell');
  return {r,c,paint:new Set([`${r},${c}`]),moves:0};
}
