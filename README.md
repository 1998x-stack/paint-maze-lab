# Paint Maze Algorithm Lab v2

一套 **可直接在本机运行的滚珠染色迷宫**，包含 Canvas 游戏、Python 规则/求解器、6 种生成算法、实时提示、精确解回放与可复现实验。独立实现，不使用原游戏源码与美术素材。

## 运行（零运行时依赖）

要求：Python 3.10+；如需 JS 单测，另需 Node 18+。

```bash
python3 server.py --host 127.0.0.1 --port 8765
```

打开 **http://127.0.0.1:8765**。默认监听本机，不需要部署服务器。界面支持键盘方向键/WASD、触屏滑动、撤销、重置、提示和自动演示。

首次进入默认使用 `Evolution` 随机保解生成器。滑杆在四种传统生成树算法下控制额外环路概率；在 Evolution 下控制尝试变异的次数，Snake 忽略该参数。可设置尺寸、种子和最小最优滑动步数；无法满足约束时会返回错误，而非伪造成功。

## 目录

```text
paintmaze/core.py        # 确定性滑动规则、可解性证明、BFS/A*、状态支配剪枝
paintmaze/generate.py    # DFS、Prim、Kruskal、Wilson、Snake、Evolution 对外接口
paintmaze/evolve.py      # 保解蛇形基线 + 八种几何变换 + 可解性校验的随机变异
server.py                # HTTP 静态服务、/api generate/analyze/hint/compare
web/                     # HTML、CSS、Canvas 游戏与独立 JS 规则引擎
benchmarks/run.py        # 逐关卡可复现的生成算法与 BFS/A* 基准
results/V2_REPORT.md     # v2 完整实验与局限说明
results/v2_*.json        # 原始案例及汇总
results/v2_algorithm_comparison.png # 可解率图
 tests/                   # Python、HTTP、JS/Python 规则一致性测试
```

## CLI 与验收

```bash
python3 -m paintmaze --algorithm evolve --width 4 --height 4 --seed 42 --verified
python3 -m paintmaze --algorithm dfs --width 4 --height 4 --seed 42
python3 -m unittest discover -s tests -p 'test_*.py' -v
npm test
npm run check
python3 benchmarks/run.py --samples 120 --width 4 --height 4 --seed 2026 \
  --budget 40000 --output results/v2_benchmark_4x4.json
```

运行时 Python 只使用标准库；测试使用标准库 unittest、Node 内置 test runner（也可选择 pytest）。

## 关键数学规则

- 墙格 `#`，地板格 `.`，起点 `S`；小球每次沿 U/R/D/L **滑至墙前**。
- 已染色格可反复穿过；不限制滑动次数；地图静态、不包含机关。
- **是否可以通关**：从当前可达停靠位置构成有向滑动图，计算其所有可执行滑动的经过格子之并集，加上已经染色的格子。如果覆盖所有地板，则可解，反之不可解。
- **最少还需几步**：以 `(当前停靠位置, 当前染色位掩码)` 为状态，采用 BFS 或 A*，支持安全状态支配剪枝。
- 精确解必须有 `exact: true`；`state_budget` 表示预算用完，不能当成无解。
- **动态提示**：真正使用当前球位置和已染色集合；因此能够识别「关卡初始可解，但玩家错误移动后无法继续」的状态。

## 六种生成算法

| 生成器 | 类型 | 可解保障 | 种子多样性 |
|---|---|---|---|
| dfs | 随机生成树 | 无，需筛选 | 有 |
| prim | 随机生成树 | 无，需筛选 | 有 |
| kruskal | 随机生成树 | 无，需筛选 | 有 |
| wilson | 均匀生成树 | 无，需筛选 | 有 |
| snake | 构造式长路径 | 有 | 无（相同尺寸同布局） |
| evolve | 构造式 + 可验证的随机变异 | 有（成功生成时） | 有 |

Evolution 从保解通道起步，随机变换对称方向，再对内部格子进行开墙/封墙变异。只接受可通过完整覆盖判定、且在搜索预算内求得精确解的候选；不通过则回滚。设置最少步数时，会尝试不同种子，直到满足目标或明确失败。

## API 示例

```bash
curl -s http://127.0.0.1:8765/api -H 'Content-Type: application/json' \
  -d '{"op":"generate","algorithm":"evolve","width":4,"height":4,"seed":42,"verified":true}'
```

获取当前位置的最优提示：

```json
{
  "op": "hint",
  "maze": {"rows": ["#####", "#...#", "#####"], "start": [1, 1]},
  "position": [1, 3],
  "painted": [[1, 1], [1, 2], [1, 3]],
  "budget": 60000
}
```

支持 `op: generate / analyze / hint / compare`，接口在 `server.py`。本服务仅用于本机实验，不应直接开放到公网。

## 本轮验收与限制

- Python 回归测试 **27 项通过**；Node 规则一致性测试 **10 项通过**；JS 语法检查通过。
- 4×4 每算法 120 个、5×5 每算法 80 个，共 **1200 个候选生成案例**，详见 `results/V2_REPORT.md`。
- 在获得共同精确解的案例上，BFS 与 A* 最优步数不冲突；大关卡可能超过搜索预算。
- 当前环境 Chromium 对本地地址导航返回 `ERR_BLOCKED_BY_ADMINISTRATOR`，因此无法在该环境完成浏览器级 E2E；已完成 HTTP 集成测试、Python/JS 一致性测试。用户本机可自行打开页面验证视觉与交互。
- 没有多球、动态墙、传送门、逐格行走模式；前端是 Canvas 2D 视觉，未做 3D 渲染。
