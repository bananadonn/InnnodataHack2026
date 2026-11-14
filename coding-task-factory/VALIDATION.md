# 验证（validation）说明 —— 给组员的交接约定

## 交接格式只有一个：Harbor 任务包
不管 SDK 内部怎么组织数据，最后交给验证的都必须是一个 **Harbor 任务包目录**（格式见 `vendor/innodata_kit/example_task/`）：

```
<instance_id>/
  task.toml                 # base_commit 必须是 cf19179e8e2fd54c601378cec9e0d21bb12b6fb1（click 8.5.1）
  instruction.md            # 做题者唯一能看到的说明
  solution/patch.diff       # 参考实现（只改源码，绝不碰 tests/）
  solution/solve.sh
  tests/test_patch.diff     # 新增 feature 测试文件（和参考实现不共享任何文件）
  tests/fail_to_pass.json   # pytest node id，例如 tests/test_x.py::test_y
  tests/pass_to_pass.json
  tests/run_script.sh  tests/grade.py  tests/parser.py  tests/test.sh
  environment/Dockerfile
```

最省事的做法：SDK 只产出"题面 + 参考实现 + 测试"，然后调用 `factory/harbor.py:export()` 打包（它会生成 diff、Dockerfile、run_script 和 F2P/P2P 列表）。

推荐但不强制（满足了能多跑几项检查）：
- `instruction.md` 有 `## Public interface`（反引号写签名）和 `## Required behavior`（编号列表 1. 2. 3.）
- 每个测试函数里写 `# R<n>`，标明它覆盖第几条需求

## 怎么跑
```bash
# 本地快速检查（不花 API 钱，约 1 分钟/包）
.venv/bin/python main.py validate generated_tasks/* --repo-dir work/click
# + 模型检查：公平性审查、强模型盲解、Haiku 难度探测（花钱）
.venv/bin/python main.py validate generated_tasks/* --repo-dir work/click --llm
# + Docker 里的权威检查：oracle 1.0 / nop 0.0 + 改坏的参考实现必须得分 < 1.0
.venv/bin/python main.py validate generated_tasks/* --repo-dir work/click --container
```
输出：`runs/validation/<时间>/validation_summary.md`（总表 + "退回给谁"清单）和每个包的 JSON 详情。

## 检查项与"退回给谁"

| 检查 | 内容 | 不通过退回给 |
|---|---|---|
| V0 lint | 主办方 `check_structure.py` | 打包者 |
| V1 load | task.toml 能解析、base_commit 对、两个 patch 都能打到 base 上 | 打包者 |
| V2 hygiene | 参考实现不碰测试文件；两个 patch 不共享文件 | 参考实现作者 |
| V3 F2P/P2P | **本地重新测量**，并和声明的列表对比 | 按问题：ID 对不上 → 打包者；F2P 在参考实现上失败 → 参考实现作者；F2P 在 base 上已通过 → 测试作者 |
| V4 全量测试 | 参考实现下 click 全部 2,626 个测试仍然通过 | 参考实现作者 |
| V5 稳定性 | 重跑结果一致 | 测试作者 |
| V6 变异 | 把参考实现改坏，feature 测试必须失败（≥80%） | 测试作者 |
| V7 接口 | 测试只用 instruction 里写明的新符号 | 题面（SDK） |
| V8 覆盖 | 每条编号需求都有测试（需要 `# R<n>`） | 测试作者 |
| V9 题面风格 | 需求在规定"怎么实现"（调用顺序、内部函数）→ 警告 | 题面（SDK） |
| V10 公平性（--llm） | 测试检查的每个事实，instruction 里都写了 | 题面（SDK） |
| V11 探测（--llm） | 强模型只看题面能做对；Haiku 一次做对 → "太简单" | 题面（SDK） |
| V12 容器（--container） | Harbor oracle 1.0 / nop 0.0；改坏的参考实现得分 < 1.0 | 打包者 / 参考实现作者 |

批次检查：5 个包之间是否用词高度重复、是否改的是同一组文件（多样性风险）。

**sound（机械正确）= V0–V6 全过**，对应评委的硬性检查。
**fair = V7/V8/V10 没有失败。**
**hard = V11 里 Haiku 一次没做对。**
