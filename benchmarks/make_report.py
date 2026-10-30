"""Produce a local Markdown report and one-axes generator comparison from measured JSON."""
import json
from pathlib import Path
from datetime import datetime,timezone
base=Path(__file__).resolve().parents[1]/'results'
a=json.loads((base/'benchmark_4x4_300.json').read_text())
b=json.loads((base/'benchmark_5x5_200.json').read_text())
names={r['algorithm'] for r in a['generators']}
md=['# Paint Maze Lab：算法基准测试', '',
    '所有数值均为当前环境实际运行后写入 JSON 的结果，未使用理论估计填充。', '',
    '## 实验参数', '',
    '| 参数 | 实验 A | 实验 B |', '|---|---|---|',
    f"| 粗网格 | {a['parameters']['width']}×{a['parameters']['height']} | {b['parameters']['width']}×{b['parameters']['height']} |",
    f"| 每算法候选数 | {a['parameters']['samples_per_algorithm']} | {b['parameters']['samples_per_algorithm']} |",
    f"| 种子起点 | {a['parameters']['seed']} | {b['parameters']['seed']} |",
    f"| 额外环路率 | {a['parameters']['loops']} | {b['parameters']['loops']} |",
    f"| 搜索状态上限 | {a['parameters']['budget']} | {b['parameters']['budget']} |",
    '', '## 生成器可解率', '',
    '| 生成器 | 4×4 可解率 | 4×4 数量 | 5×5 可解率 | 5×5 数量 |',
    '|---|---:|---:|---:|---:|']
for x,y in zip(a['generators'],b['generators']):
    md.append(f"| {x['algorithm']} | {x['solvable_rate_pct']}% | {x['solvable']}/{x['samples']} | {y['solvable_rate_pct']}% | {y['solvable']}/{y['samples']} |")
md += ['', '> Snake 是完全确定性的构造式基线：同一尺寸下每个所谓“样本”都是相同布局，因此 100% 不应解释成随机抽样得到的置信区间。',
       '', '## 最优求解器对比', '',
       '| 指标 | 4×4 BFS | 4×4 A* | 5×5 BFS | 5×5 A* |',
       '|---|---:|---:|---:|---:|']
ma={i['method']:i for i in a['solvers']};mb={i['method']:i for i in b['solvers']}
for name,key in [('可解候选数','cases'),('获得精确解','exact'),('精确案例平均展开节点数','mean_expanded_exact'),('精确案例平均耗时（毫秒）','mean_elapsed_ms_exact')]:
    md.append(f"| {name} | {ma['bfs'][key]} | {ma['astar'][key]} | {mb['bfs'][key]} | {mb['astar'][key]} |")
md += ['', f"- 4×4 BFS/A* 最优解冲突数量：**{len(a['mismatches'])}**。",
       f"- 5×5 BFS/A* 最优解冲突数量：**{len(b['mismatches'])}**。",
       '- 均值只针对获得精确解的案例；方法和尺寸间的样本构成可能不同，且大部分小图本来就容易，因此不能据此认定 A* 在任何规模都更快。',
       '', '## 数学证明范围', '',
       '定义可达停靠点集合 R。对每个 p∈R，枚举其四个方向的滑动覆盖集合 footprint(p,a)。令 C 为起点与全部 footprint 的并集。',
       '', '在静态墙体、单球、单调染色、可重复滑动且无限步的规则下，**迷宫可解 ⇔ C 包含全部目标地板**。',
       '', '必要性：所有可执行动作都来自可达停靠点，其染色点必属于 C。',
       '', '充分性：每个 C 内的地板至少位于一条从某可达停靠点出发的滑动路径。由于染色不影响运动，可逐次完成这些路径并覆盖所有目标。',
       '', '## 实际决策', '',
       '1. 初级关卡使用 Snake 保解、低操作复杂度。',
       '2. 中级关卡使用 DFS + 验证筛选，提高随机多样性。',
       '3. Prim、Kruskal、Wilson 在当前模型下筛选接受率低，宜搭配结构修改和二次优化，不能直接发布。',
       '4. 大型关卡仍需要提升构造式生成复杂性，不能只增加粗网格尺寸；当前 Snake 的最优操作固定为 2×粗网格高度−1。',
       '', '## 验收及限制', '',
       '- Python 规则和求解器通过独立穷举 Oracle 的随机差分测试；Node 规则与 Python fixture 做跨语言一致性验证。',
       '- `exact=false` 是搜索预算不足，不等于无解。',
       '- 只模拟静态二维网格最大滑动涂色，不包含真实三维物理、多人、机关。',
       '- 浏览器 GUI 代码已实现并通过 JS 语法检查，但本次容器的受限 Chromium 环境拒绝页面导航，因此不能声称浏览器 E2E 已通过。',
       '- 数据依赖样本种子、设备性能；所有中间求解记录保存在 JSON。',
       '', '## 参考', '',
       '- https://github.com/john-science/mazelib',
       '- https://github.com/will2dye4/labyrinth',
       '- https://www.yau-science-awards.org/upload/202007/06/202007061605593421/202007061605593421.pdf',
       '']
(base/'REPORT.md').write_text('\n'.join(md),encoding='utf-8')
try:
 import matplotlib.pyplot as plt
 alg=[r['algorithm'].upper() for r in a['generators']]
 x=list(range(len(alg)));width=.36
 fig,ax=plt.subplots(figsize=(10.8,5.8))
 ax.bar([i-width/2 for i in x],[r['solvable_rate_pct'] for r in a['generators']],width,label='4×4 (300 trials)')
 ax.bar([i+width/2 for i in x],[r['solvable_rate_pct'] for r in b['generators']],width,label='5×5 (200 trials)')
 ax.set_xticks(x,alg)
 ax.set_ylabel('Solvable generated mazes (%)')
 ax.set_title('Sliding Paint Maze: Generation Feasibility Comparison')
 ax.set_ylim(0,113)
 ax.legend()
 ax.text(.5,-.17,'Snake is a deterministic guaranteed-solvable baseline, not independent random draws.',
         ha='center',transform=ax.transAxes,fontsize=9)
 fig.tight_layout()
 fig.savefig(base/'generator_comparison.png',dpi=160,bbox_inches='tight')
 plt.close(fig)
 print('Generated',base/'generator_comparison.png')
except ImportError:
 print('matplotlib absent, skipped plot')
print('Generated',base/'REPORT.md')
