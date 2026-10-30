<div align="center">

# math-modeling-per-question

### 按小问交付的数学建模 AI Agent Skill

**做完一问，论文手立刻就能写这一问 —— 不必等整题跑完**

![Version](https://img.shields.io/badge/version-1.2.0--per--question-purple)
![Tests](https://img.shields.io/badge/tests-346%20passed-brightgreen)
![Checkers](https://img.shields.io/badge/checkers-26-orange)
![Python](https://img.shields.io/badge/python-%E2%89%A5_3.10-blue)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)
![License](https://img.shields.io/badge/license-MIT-green)

[和原版的区别](#-和原版的区别) · [你会得到什么](#-你会得到什么) · [双闸门](#-两道闸门a-一次b-每问一次) · [工作流](#-小问循环) · [快速开始](#-快速开始) · [产物](#-每问产物)

</div>

---

## 🎯 这是什么

它是 [math-modeling](https://github.com/Hjdd14/math-modeling) 的**按小问交付分支**，面向"多小问、要交付论文"的竞赛题。

同一道题，原版是**一次性做完再一起交**；这个版本是**把每个小问当成一个独立小项目**：建模、代码、结果、验证、评审、写作交接全在 `questions/qN/` 里闭环，做完就宣告、立刻交给论文手写。

> 一句话：**建模与写作真正并行起来，而不是"等 AI 全部做完才开始写"。**

---

## 🔀 和原版的区别

| | 原版 math-modeling | **本分支** |
|---|---|---|
| 交付粒度 | 整题一次性交付 | **每问独立完整交付** |
| 工作区 | 根目录一套产物 | 每题 `questions/qN/` 一套产物 |
| 节奏 | 全部做完再统一评审 | **严格串行：做完一问 → 宣告 → 下一问** |
| 写作 | 最后统一交接 | **每问完成即可交给论文手**，无需等待 |
| 闸门 B | 整题一块板、一次确认 | **每问一块板、逐问确认** |
| 图表 | 随流程产出 | **统一延后到 Phase F**，风格与叙事一次到位 |
| 依赖 | — | 后问可读前问结果，但**不得修改已完成小问的任何产物** |

---

## ✨ 你会得到什么

| 能力 | 你拿到的东西 |
|---|---|
| **逐问闭环** | 每个小问独立走完 建模 → 选型 → 代码 → 结果 → 评审，产物自包含 |
| **可并行写作** | 第 1 问宣告完成后，论文手立即开始写第 1 问，建模继续跑第 2 问 |
| **真实选型对比** | 每问 5–8 个候选模型，在 ≥2 组数据切片上真跑，给出成本/误差/稳定性与优缺点 |
| **每问代码与测试** | `questions/qN/solution.py/.m` + 契约测试 + `results/`，即取即用 |
| **每问评审** | 五评委 + 独立复现，按问打分并给出质询清单 |
| **统一图表** | 全部小问结束后一次性绘制：每问 ≥5 张证据图 + 跨问对比 + 整题概览 |
| **写作交接** | 每问 `writer_prompt.md` + 整题总装提示词，直接对接写作 Skill |

**它不做什么**：不生成正式论文正文；不并行求解多个小问（串行是硬规则）；不替代 Agent 宿主的并行推理。

---

## 🚪 两道闸门：A 一次，B 每问一次

| | **闸门 A：框架与探索边界** | **闸门 B：该问方案择定** |
|---|---|---|
| 次数 | 整题 **1 次** | **每个小问 1 次** |
| 什么时候 | 建完 `question_queue.json` 后、任何代码之前 | 该问五视角跑完、试算落盘之后 |
| 问你什么 | 题目读对了吗？高危假设接受吗？每问要探索哪几个方法族？ | **这一问最终用哪个模型？** |
| 你看到 | 全题范式集合（每问 3–5 个，含异质族与探索成本） | 该问候选的分数、优缺点、真实数据对比，1 建议 + 其余不建议 |
| 放行 | 你本人输入 4 位确认码 | 该问独立确认码，逐问输入 |
| 拦截效果 | A 板未确认：不得进入小问循环 | B 板未确认：**该问 `solution.*` 既写不进也过不了校验** |

> 为什么 B 要按问做？因为**模型选择本来就是逐问的**，而且只有该问的五视角与试算跑完，才有做决定的证据。代价是每问一次打断，换来的是"每个小问的模型都由你基于真实数据拍板"。

---

## 🔄 小问循环

```text
Phase 0    读题 · 拆小问 · 建 question_queue.json
   │
   ▼
Phase 0.5  【闸门 A】题意框架 + 每问待探索范式            ← 整题确认一次
   │
   ▼
┌────────────── 对每个小问 qN 串行执行 ──────────────┐
│  Phase 1-Q    五视角并行 → 批评 → 修正 → 真实试算     │
│      │                                              │
│  Phase 1.5-Q  【闸门 B】建议 + 打分 + 数据对比         │ ← 你选定该问模型
│      │                                              │
│  Phase 2/3-Q  写作交接 + 代码/测试/结果               │
│      │                                              │
│  Phase 4-Q    技术审查 + 独立复现 + 五评委评分         │
│      │                                              │
│  完成宣告 "第 N 小问已完成" → 论文手可立即开写         │
└─────────────────────────────────────────────────────┘
   │
   ▼
Phase F    统一绘制全部图表（每问 ≥5 张 + 跨问对比 + 整题概览）
   │
   ▼
Phase 5    整题总装：写作提示词汇总 · 合规 · 复现清单
```

**硬规则**：同一时刻只允许一个小问处于"进行中"；上一问未宣告完成，不得开始下一问；已完成小问的产物只读。

---

## 🚀 快速开始

需要 **Python ≥ 3.10** 与 **Git**。

```bash
# 1) 安装
git clone https://github.com/Hjdd14/math-modeling-per-question.git ~/.claude/skills/math-modeling-per-question
bash ~/.claude/skills/math-modeling-per-question/install.sh
```

```powershell
# Windows
git clone https://github.com/Hjdd14/math-modeling-per-question.git $env:USERPROFILE\.claude\skills\math-modeling-per-question
cd $env:USERPROFILE\.claude\skills\math-modeling-per-question
.\install.ps1
```

在 Agent 里直接说：

> 用 math-modeling-per-question skill 做这道题：`A题.pdf` + `data.xlsx`，按小问分别交付。

它会先拆小问、生成全局决策板，然后停下来等你输入 A 板确认码；进入小问循环后，**每问都会再停一次**让你在 B 板上选模型。

手动命令（可选）：

```bash
python tools/workflow_runner.py scaffold --workspace . --language python --questions q1,q2,q3
python tools/question_queue.py next --workspace .
python tools/design_board.py render --gate b --workspace questions/q1 --format all
python tools/design_board.py confirm --gate b --workspace questions/q1 --apply
python tools/pipeline_check.py --workspace questions/q1 --stage question --board-root .
```

---

## 🗂 每问产物

每个 `questions/qN/` 都是一套自包含交付物：

| 类别 | 文件 | 用途 |
|---|---|---|
| 该问简报 | `problem_brief.md`、`problem_taxonomy.json`、`case_retrieval.json` | 该问目标、题型与可借鉴方法 |
| 选型证据 | `perspective_trials.json`、`model_advice.json`、`design_board_gate_b.json` | 怎么比、比出什么、你选了谁 |
| 模型规范 | `model_spec.json`、`solver_strategy.json`、`optimization_certificate.json`、`uncertainty_budget.json` | 模型写清、求解可查、不确定性有预算 |
| 结论 | `final_solution.json`、`model_decision.md` | 该问最终方案与决策记录 |
| 代码与结果 | `solution.py/.m`、`solution_tests.*`、`results/` | 可运行、可复现（阶段内不产图） |
| 评审 | `judge_panel_review.json`、`decision_insights.md`、`defense_questions.md` | 五评委意见与质疑清单 |
| 写作 | `modeling_answer.md`、`writer_prompt.md` | 该问解答文档 + 交接提示词 |

全局产物：`question_queue.json`、`design_board.json`（A 板）、Phase F 的图表与 `results/figure_quality_report.json`、Phase 5 的总装与合规文件。

---

## ✅ 质量与证据

| 层 | 机制 | 用户感受 |
|---|---|---|
| 结构 | 26 个 checker，逐问校验模型/数据/代码/评审 | 缺项或对不上账立即报错 |
| 数值 | 试算只能由工具执行留痕，手填判假 | 对比表里每个数都可复跑 |
| 时序 | 每问代码必须晚于该问 B 板确认 | "先写码后补板"过不了 |
| 事中 | 宿主 hook 拒绝写未确认小问的 `solution.*` | 确认前根本写不进去 |
| 串行 | 队列状态机校验"上一问完成才允许下一问" | 不会出现半成品抢跑 |
| 自检 | 346 项自动化测试 + 全流程/对抗探针 | 改动不会悄悄改坏行为 |

---

## ⚠️ 边界与取舍

- **串行是刻意的**：不并行求解多个小问，换来的是一问一闭环、随时可交稿。
- **每问一次确认**：打断次数变多，但每次都有真实数据支撑；可用 `serve --gate b` 批量复核减少来回。
- **图表后置**：小问阶段只产数据，Phase F 统一绘制，保证整题风格一致。
- **不写论文正文**：只交付建模、代码、证据与写作提示词。

---

## 🆕 1.2.0-per-question 更新要点

- 升级为 **双闸门**：A 框架闸门整题一次，B 方案择定闸门**每问一次**。
- 每问新增 **真实试算 + 选型建议 + B 板确认**，确认前写不出该问代码。
- 支持 `--stage question` 逐问验证与 `--board-root` 跨工作区取证。
- 图表仍然统一延后到 Phase F；每问完成即可交付论文手。
- 测试 346 项全绿，含全流程与对抗探针。

---

## 📄 License

MIT © math-modeling contributors

> 上游项目：**[math-modeling](https://github.com/Hjdd14/math-modeling)** —— 整题一次性交付的通用版本。
