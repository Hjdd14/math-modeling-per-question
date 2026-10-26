<div align="center">

# math-modeling-per-question

**面向数学建模竞赛的 AI Agent Skill（math-modeling 分支）—— 按小问逐个交付：每个小问独立产出建模解答、代码、输出数据与写作交接，做完一问宣告一问，全部小问结束再统一绘制图表**

> **分支版 1.1.0** · MIT License · Python ≥ 3.10 · Windows / Linux / macOS

![Version](https://img.shields.io/badge/version-1.1.0--per--question-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Python](https://img.shields.io/badge/python-%E2%89%A5_3.10-blue)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)
![Status](https://img.shields.io/badge/status-branch-yellow)

[功能](#-核心功能) ·
[安装](#-安装) ·
[快速开始](#-快速开始) ·
[使用方式](#-使用方式) ·
[固验产物](#-固定产物) ·
[架构](#-项目结构) ·
[贡献](#-贡献)

</div>

---

## 📖 项目简介

`math-modeling-per-question` 是 `math-modeling` 的**按小问分别交付分支**，为 **数学建模竞赛**（CUMCM、美赛 MCM/ICM、研究生赛、MathorCup、电工杯、深圳杯、统计建模大赛等）量身打造。它能接入 Claude Code、OpenCode、Codex 等支持 Skill 协议的 Agent 宿主，把原本需要人手工完成的建模工程流程**结构化并自动化**。

与原版的唯一核心差异：**整题一次性交付改为每个小问独立完整交付**。Phase 0.5「设计闸门」与原版完全同源（`question_queue.json` 建立后、任何代码之前，用户确认一次），确认之后即进入逐问串行交付：每问完成 → 立即宣告 → 论文手开始写该问，不必等其余小问。每完成一个小问就立即产出该问独立的 `modeling_answer.md`（建模解答）、`writer_prompt.md`（写作提示词）、`solution.py/.m`（代码）与 `results/`（输出数据），经完整检验与多评委评分通过后在对话中宣告"第 N 小问已完成"，论文手可立即开始该问写作，无需等待其余小问；全部小问的建模代码结束后，统一绘制全部图表（每问至少 5 张证据图 + 跨问对比图 + 整题概览图）。Phase 0（题目复现、题意审计、评分策略）与原版完全一致。

### 它做什么 ✅

- **题目解析**：从 PDF / DOCX / Markdown / TXT 题目 + Excel / CSV 附件自动生成 `problem_brief.md`
- **题意审计**：暴露歧义、单位坑、隐藏约束，生成 `ambiguity_register.json` 与 `assumption_ledger.md`
- **小问队列**：按评分策略建立 `question_queue.json`，严格串行推进，支持小问间单向依赖
- **逐问并行建模共识**：每个小问都独立跑 5 个建模 Agent（优化/统计/物理机理/工程实践/创新方法）并行出方案、并行批评、并行修正、最终裁决
- **逐问创新筛选**：每个创新点必须有题目痛点、baseline 增益、验证证据和失败风险
- **逐问代码交付**：每个小问生成独立的 `solution.py` 或 `solution.m`，先写契约测试再实现，保证可复现
- **逐问结果验证**：baseline、oracle 小例验证、solver 交叉验证、敏感性分析、独立复现，每问一份
- **建模解答文档**：每问输出 `modeling_answer.md`，论文手可直接取用其中的公式、数值与结论
- **多评委审查**：每个小问独立经过国赛建模评委、美赛评委、代码复现评委、图表证据评委、工程/业务解释评委并行评审
- **完成宣告**：该问通过全部检验与评审后，Agent 在对话中明确宣告"第 N 小问已完成"并列出产物路径，之后才进入下一问
- **统一图表绘制**：全部小问结束后进入 Phase F，按统一风格绘制尽可能多且美观的证据图，并登记 `figure_storyboard.md`
- **写作交接**：每问 `writer_prompt.md` + 整题总装 `writer_prompt.md`，把模型、代码、结果、验证证据交给后续写作 Skill 或论文手

### 它不做什么 ❌

- **不生成正式论文正文** —— 它只产出现实的"建模 + 代码 + 验证 + 交接提示词"，正式论文由后续独立写作 Skill 基于 `writer_prompt.md` 完成
- **不替代真实并行 Agent** —— Python CLI 只做确定性编排、状态管理和结构化验证；并行 Agent 推理仍必须由 Agent 宿主真实派发

### 适用场景

- 数学建模竞赛（CUMCM、MCM/ICM 等各级别赛事）
- 课程项目中的多阶段数学建模任务
- 工业研究中需要可审计建模 + 代码交付 + 证据链的复杂问题

---

## ✨ 核心功能

| 阶段 | 做什么 | 关键产物 |
|------|--------|----------|
| **Phase 0** 题目与数据 | 解析题目与附件，建立数据契约与题意审计，建立小问队列（与原版相同 + 队列建立） | `problem_brief.md`、`ambiguity_register.json`、`assumption_ledger.md`、`data_schema.json`、`question_queue.json` |
| **Phase 0.5** 设计闸门 | 一块板覆盖全部小问：每题 2+ 候选算法 + 推荐理由 + 真实试算；用户改选/批注后，**由用户本人**输入 4 位确认码放行，确认前不允许写任何小问的代码 | `design_board.json`、`design_rounds/`、`design_board.md/.html`、`design_choices.xlsx`、`mini_trials.json` |
| **小问循环 · Phase 1-Q** 并行建模共识 | 每个小问独立跑 5 视角建模 + 动态专家 + 资料库检索，并行批评与修正，最终裁决 | `questions/qN/baseline_solution.json`、`final_solution.json`、`model_decision.md`、`innovation_register.json` |
| **小问循环 · Phase 2-Q/3-Q** 写作交接 + 代码 | 该问写作交接文档 Agent 与代码 Agent 并行，生成契约测试与可运行代码；随后撰写建模解答；**只产数据不绘图** | `questions/qN/writer_prompt.md`、`modeling_answer.md`、`solution.py/.m`、`results/validation_summary.json` |
| **小问循环 · Phase 4-Q** 评审验证 | 语法/逻辑/输出三 Agent 并行，独立复现，五评委并行审查，`pipeline_check --stage question` 工具 gate，通过后在对话宣告完成 | `questions/qN/judge_panel_review.json`、`decision_insights.md`、`defense_questions.md` |
| **Phase F** 统一图表绘制 | 读取全部小问结果统一绘图（每问 ≥5 张证据图 + 跨问对比 + 整题概览），审计图表质量 | `figure_style.json`、`figure_storyboard.md`、`results/result_*.png`、`results/figure_quality_report.json` |
| **Phase 5** 最终交付 | 总装写作提示词、合规审计、复现清单、状态归档，`pipeline_check --stage final` 总控 | `writer_prompt.md`（总装）、`compliance_record.json`、`reproducibility_manifest.json` |

伴随 24 个结构化 checker 把"模型 / 数据 / 代码 / 图表 / 复现 / 合规"全链路连成证据簿；小问工作区直接作为 `--workspace questions/qN` 运行，无需改动任何 checker。

---

## 📦 安装

### 前置条件

- **Git** ≥ 2.20：[安装指南](https://git-scm.com/downloads)
- **Python** ≥ 3.10：[安装指南](https://www.python.org/downloads/)
- **（可选）Node.js**：用于 `node --check workflows/*.js` 静态检查
- **（可选）MATLAB**：用于运行 `solution.m` 的真实集成测试
- **（可选）Claude CLI**：用于 `tools/claude_eval_runner.py` 的真实对比 eval

### 通用安装（任何 Agent 都适用的两条命令）

本 Skill 通过 `SKILL.md` 协议接入。安装本质就两步：① 把本分支目录放到 Agent 找得到的位置，② 让依赖 Python 的验证工具链可用。

本分支不自带远程仓库（它是 `math-modeling` 的本地分支副本，位于 `math_modeling_eq/math-modeling-per-question`），因此用"复制或建立符号链接"而不是 `git clone`：

**Linux / macOS / Git Bash：**

```bash
# 1) 把本分支目录链接到 Agent 的 skills 目录（下表任选其一）
ln -s "/d/Code_Work/My_Projects/math_modeling_eq/math-modeling-per-question" ~/.claude/skills/math-modeling-per-question

# 2) 进入目录并运行安装脚本（自动 pip 依赖 + 自检 + 尝试符号链接到 skills 目录）
cd "/d/Code_Work/My_Projects/math_modeling_eq/math-modeling-per-question"
bash install.sh
```

**Windows PowerShell：**

```powershell
# 1) 把本分支目录链接到 Claude Code 的 skills 目录（需管理员权限；也可直接复制目录）
New-Item -ItemType SymbolicLink -Path "$env:USERPROFILE\.claude\skills\math-modeling-per-question" `
  -Target "D:\Code_Work\My_Projects\math_modeling_eq\math-modeling-per-question"

# 2) 进入目录并运行安装脚本
cd "D:\Code_Work\My_Projects\math_modeling_eq\math-modeling-per-question"
.\install.ps1
```

> **一行命令完成所有（推荐）：**

```bash
bash "D:/Code_Work/My_Projects/math_modeling_eq/math-modeling-per-question/install.sh" \
  --skills-dir ~/.claude/skills
```

`install.sh` / `install.ps1` 会自动检测常见 Agent 的 skills 目录（Claude Code、OpenCode 等），尝试创建符号链接。若自动检测失败，按表手动指定 `--skills-dir` 即可（见下方示例）。

### 不同 Agent 的 skills / rules 目录

下面是主流 Agent 读取 skills 或 rules 文件的位置。把仓库放到对应目录即可，**仅当你使用了非默认的目录时**才需要显式传 `--skills-dir`。

| Agent | 全局 skills 目录 | 项目级 skills 目录 | 备注 |
|-------|-----------------|------------------|------|
| **Claude Code** (Anthropic) | `~/.claude/skills/` | `.claude/skills/` | 原生支持 `SKILL.md` 的 front-matter 触发 |
| **OpenCode** | `~/.config/opencode/skills/` | `.opencode/skills/` | 原生支持 `SKILL.md` |
| **Cursor** | n/a | `.cursor/rules/*.mdc` | 用 rules 而非 skill，可在 rule 里 `@import` 本仓库的 `SKILL.md` |
| **Continue** | `~/.continue/rules/` | `.continue/rules/` | 同步仅做规则匹配，可参考 SKILL.md 触发段 |
| **Codex CLI** (Microsoft) | n/a | `AGENTS.md` 于项目根 | 把 skill 触发段写入 `AGENTS.md`，工具用绝对路径调用 |
| **Roo Code / Cline** | n/a | `.roo/rules/` 或 `cline_rules/` | 项目级 rules 目录，用 `@import` 引用本仓库文件 |
| **Aider** | n/a | `.aider.conf.yml` | 在配置里引用本仓库 `SKILL.md` 与 tools 路径 |

> **注意**：只原生支持 `SKILL.md` 的是 Claude Code 和 OpenCode，其它 Agent 通常需要你在其 rule 文件中通过 `@import` 引用本仓库的 `SKILL.md` 与 `references/` 目录。

### 按 Agent 配置的安装示例

**安装到 Claude Code 全局目录：**

```bash
ln -s "/d/Code_Work/My_Projects/math_modeling_eq/math-modeling-per-question" ~/.claude/skills/math-modeling-per-question
bash "/d/Code_Work/My_Projects/math_modeling_eq/math-modeling-per-question/install.sh"
```

**安装到 OpenCode 全局目录：**

```bash
ln -s "/d/Code_Work/My_Projects/math_modeling_eq/math-modeling-per-question" ~/.config/opencode/skills/math-modeling-per-question
bash "/d/Code_Work/My_Projects/math_modeling_eq/math-modeling-per-question/install.sh"
```

**自定义 skills 目录（任意 Agent）：**

```bash
# Linux / macOS / Git Bash
bash install.sh --skills-dir ~/your-agent-skills-dir

# Windows PowerShell
.\install.ps1 -SkillsDir "$env:USERPROFILE\your-agent-skills-dir"
```

**项目级安装（仅当前项目生效）：**

```bash
# 在你的项目根目录下复制或链接
ln -s "/d/Code_Work/My_Projects/math_modeling_eq/math-modeling-per-question" .claude/skills/math-modeling-per-question

# 进入并运行安装（注意：项目级 install 通常不需要 --skills-dir）
cd .claude/skills/math-modeling-per-question && bash install.sh --no-doctor
```

### 手动安装（完全可控）

```bash
# 1) 进入本分支目录（无需 clone，它已在本地）
cd "D:/Code_Work/My_Projects/math_modeling_eq/math-modeling-per-question"

# 2) 安装 Python 依赖
python -m pip install -r requirements.txt

# 3) 运行本地体检
python tools/doctor.py --workspace .
```

### 安装脚本参数

两个脚本支持相同的参数语义：

| 参数（bash） | 参数（PowerShell） | 含义 |
|------|------|------|
| `--skills-dir <path>` | `-SkillsDir <path>` | 指定 skills 目录，会尝试创建符号链接 |
| `--no-pip` | `-NoPip` | 跳过 `pip install` |
| `--no-doctor` | `-NoDoctor` | 跳过 doctor 健康检查 |

也可以通过环境变量 `SKILLS_DIR=...` 设置 skills 目录。

### 安装后验证

无论用哪种方式安装，完成后可运行体检：

```bash
python tools/doctor.py --workspace .
```

输出 JSON 中 `summary.failed = 0` 即可视为安装就绪。

---

## 🚀 快速开始

### 1. 用 Agent 触发 skill

将 `SKILL.md` 触发它。在你的 Agent 中输入：

> 我有一道数学建模题，三个小问，请按小问分别求解：每做完一问就给我这一问的建模解答、代码和输出数据，我队友要先写论文；全部小问做完再统一画图。

或更具体：

> 帮我做这题，按小问分别交付。题目文件：`path/to/problem.pdf`，数据：`path/to/data.xlsx`

Agent 会扫描到 skill 描述匹配，自动加载 `SKILL.md` 并按 `references/workflow.md` 执行 Phase 0 → 小问循环 → Phase F → Phase 5。

### 2. 用 CLI 工具手动驱动

如果你想自己跑流程，而不是通过 Agent 派发并行任务：

```bash
# 初始化工作区，并一次性建立三个小问的队列与迷你工作区
python tools/workflow_runner.py scaffold --workspace runs/my_case --language python --questions q1,q2,q3

# 解析题目 + 数据，生成 problem_brief
python tools/input_parser.py brief \
  --problem path/to/problem.pdf \
  --data path/to/data.xlsx \
  --out runs/my_case/problem_brief.md

# 小问循环：取下一问 → 求解 → 登记完成 → 再取下一问
python tools/question_queue.py next --workspace runs/my_case
python tools/question_queue.py complete --workspace runs/my_case --question q1 --score 87
python tools/question_queue.py status --workspace runs/my_case

# 单个小问工作区的工具验证（小问阶段图表延后，零 PNG 不判失败）
python tools/pipeline_check.py --workspace runs/my_case/questions/q1 --language python --stage question

# 恢复已有工作区
python tools/workflow_runner.py resume --workspace runs/my_case --language python

# 整题最终总控验证
python tools/pipeline_check.py --workspace runs/my_case --language python --stage final
```

### 3. 跑一个公开合成样例

仓库自带合成示例，便于快速验证安装是否成功：

```bash
# Quickstart 样例：题目 + 数据 + brief 生成
python tools/workflow_runner.py scaffold --workspace runs/quickstart --language python
python tools/input_parser.py brief \
  --problem examples/quickstart/problem.md \
  --data examples/quickstart/production_data.csv \
  --out runs/quickstart/problem_brief.md
```

完整 solved example 见 [`examples/solved-python/`](examples/solved-python/)，展示了所有固定产物的理想结构。

### 4. 难题与奖项级交付

```bash
# 难题使用严格证据模式
python tools/pipeline_check.py --workspace runs/my_case \
  --language python --evidence-mode strict

# 奖项级完整交付使用严格证据 + 卓越质量模式
python tools/pipeline_check.py --workspace runs/my_case \
  --language python --evidence-mode strict --quality-mode excellence
```

---

## 🎯 使用方式

### Agent 宿主如何接入

支持 Skill 协议的 Agent（如 Claude Code、OpenCode 等）按以下方式接入：

1. 安装本 skill 到 skills 目录（见上文）
2. 重启 Agent，让它重新扫描 skills 目录
3. 在 Agent 中发出与数学建模相关的请求，它会自动触发

### 给其他 Agent 的使用约定

1. **先读 `SKILL.md`**，再按其要求读取并执行 `references/workflow.md`
2. **不要把 `workflow_runner.py` 当成建模推理替代品** —— 它只负责 scaffold、resume、verify 和状态文件维护
3. **并行 Agent 步骤必须真实执行或明确记录为外部已执行步骤** —— 把摘要写入 `modeling_state.json`
4. **小问必须严格串行**：同一时刻最多一个小问 `in_progress`；当前小问未通过检验与评委审查、未在对话中宣告完成前，不得开始下一问
5. **每个小问都要独立跑完整流程**：五视角并行建模、并行批评、并行修正、创新筛选、裁决、代码契约测试、独立复现、五评委审查，任何小问都不得降级
6. 使用 `tools/state_manager.py agent-run` 记录 Agent 运行，使用 `tool-run` 记录工具运行；小问进度以 `question_queue.json` 为准
7. Phase 1-Q 只产出建模决策和方案产物，不生成正式写作正文；`modeling_answer.md` 是该问建模解答记录，正式论文正文由论文手或写作 skill 完成
8. 小问阶段代码只产 CSV/JSON 数据，**不绘制任何 PNG 图表**；图表统一在 Phase F 绘制
9. 难题或完整交付必须保留每问的 `validation_summary.json`、baseline、oracle/小例验证、solver 交叉验证、敏感性分析和独立复现摘要
10. 奖项级交付额外运行 `pipeline_check.py --stage question --quality-mode excellence`（逐问）与 `--stage final --quality-mode excellence`（整题）

### 仓库结构

```
math-modeling-per-question/
├── SKILL.md                  # 主入口：触发条件、核心约束、小问循环 Phase Gates
├── install.sh                # Linux/macOS/Git Bash 一键安装
├── install.ps1               # Windows PowerShell 一键安装
├── references/               # 详细文档（降低上下文负担）
│   ├── workflow.md           # 完整 Phase 0 → 小问循环 → Phase F → Phase 5 流程
│   ├── templates.md          # 固定产物模板（含 question_queue.json、modeling_answer.md）
│   ├── tools.md              # 所有 CLI 工具命令与失败判定
│   ├── competition_sources.json  # 权威竞赛来源总索引
│   ├── award_playbook.md     # 题型方法卡谱系
│   ├── evaluator_panel.md   # 多评委并行审查规则（按小问各评一次）
│   └── evals.md              # 本地 eval 与触发评估
├── tools/                    # Python CLI 工具（40 个，含 24 个 checker）
│   ├── question_queue.py     # 【分支新增】小问队列 init/next/complete/status
│   ├── workflow_runner.py    # scaffold（支持 --questions）/resume/verify
│   ├── pipeline_check.py     # 总控验证入口（支持 --stage question|final）
│   ├── input_parser.py       # PDF/DOCX/MD/TXT + Excel/CSV 解析
│   ├── state_manager.py     # 原子状态维护
│   ├── doctor.py             # 本地依赖与仓库体检
│   └── ...                   # 详见 references/tools.md
├── workflows/                # 宿主 workflow 模板（JS，按小问循环派发骨架）
├── evals/                    # 本地 eval 与 mini benchmark
├── examples/                # 公开合成样例
│   ├── quickstart/           # 最小可跑样例
│   └── solved-python/        # 完整理想产物样例
├── tests/                    # pytest 测试套件（220+ 用例）
└── docs/                     # 安装、发布、可移植性指南
```

---

## 📋 固定产物

每个建模工作区分为**全局产物**、**每问产物（`questions/qN/`）**、**统一绘图与总装产物**三组：

<details>
<summary><b>全局产物（工作区根目录）</b></summary>

| 产物 | 阶段 | 说明 |
|------|------|------|
| `problem_brief.md` | Phase 0 | 题目、目标、约束、附件摘要（唯一真实来源） |
| `ambiguity_register.json` | Phase 0 | 题意歧义、单位、隐藏约束审计 |
| `assumption_ledger.md` | Phase 0+ | 假设来源、影响和验证状态 |
| `scoring_strategy.md` | Phase 0 | 题目小问、评分点与图表支撑策略 |
| `question_queue.json` | Phase 0+ | 小问队列、依赖关系、完成状态与评委总分 |
| `data_schema.json` | Phase 0 | 字段契约（全局共享，逐问扩充） |
| `symbol_table.json` | Phase 1 | 符号-单位-代码变量映射（全局共享，逐问扩充） |
| `modeling_state.json` | 全程 | 机器可读状态（整题进度） |
| `modeling_memory.md` | 全程 | 人类可读过程记忆（整题进度） |

</details>

<details>
<summary><b>每问产物（<code>questions/qN/</code>，每个小问一份，论文手即取即用）</b></summary>

| 产物 | 阶段 | 说明 |
|------|------|------|
| `problem_brief.md` | Phase 1-Q | 该问简报（全局上下文 + 该问目标） |
| `problem_taxonomy.json` | Phase 1-Q | 该问题型分类 |
| `case_retrieval.json` | Phase 1-Q | 该问定向检索的相似题型与可借鉴方法 |
| `baseline_solution.json` | Phase 1-Q | 该问可解释基线 |
| `model_spec.json` | Phase 1-Q+ | 变量、目标、约束、单位、验证计划 |
| `model_selection_audit.json` | Phase 1-Q | 候选模型评分与拒绝理由 |
| `optimization_certificate.json` | Phase 1-Q/3-Q | 可行性残差、上下界、gap、oracle |
| `uncertainty_budget.json` | Phase 1-Q/4-Q | 各类误差预算 |
| `validation_profile.json` | Phase 1-Q/4-Q | 按题型的验证证据 |
| `data_validation.json` / `statistical_validation.json` | Phase 3-Q | 数据切分、泄漏检查、指标与稳健性（涉及时） |
| `solver_strategy.json` | Phase 1-Q/3-Q | 求解器策略与 fallback |
| `ablation_study.json` | Phase 1-Q/3-Q | 消融实验 |
| `innovation_register.json` | Phase 1-Q | 该问创新点证据链 |
| `final_solution.json` | Phase 1-Q | 该问最终建模方案 |
| `model_decision.md` | Phase 1-Q | 该问共识与裁决理由 |
| `modeling_answer.md` | Phase 3-Q 后 | **该问建模解答文档（论文手直接取用）** |
| `writer_prompt.md` | Phase 2-Q/4-Q | **该问写作交接提示词** |
| `solution.py` / `solution.m` | Phase 3-Q | 该问可运行代码 |
| `solution_tests.py` / `solution_tests.m` | Phase 3-Q | 该问契约测试 |
| `results/` | Phase 3-Q+ | 该问 CSV/JSON 输出（不产 PNG） |
| `results/validation_summary.json` | Phase 3-Q+ | 该问验证证据汇总（12 项） |
| `judge_panel_review.json` | Phase 4-Q | 该问多评委并行审查与 chair judge 汇总 |
| `decision_insights.md` / `defense_questions.md` | Phase 4-Q | 该问决策建议与评委质询准备 |
| `modeling_state.json` | 该问全程 | 该问独立状态 |

</details>

<details>
<summary><b>统一绘图与总装产物（工作区根目录）</b></summary>

| 产物 | 阶段 | 说明 |
|------|------|------|
| `figure_style.json` | Phase F | 图表风格规范（统一 DPI、字体、色板） |
| `figure_storyboard.md` | Phase F | 图表叙事板（file、claim、source_data、x_unit、y_unit、supports_question） |
| `results/result_*.png` | Phase F | 全部图表：每问 ≥5 张证据图 + 跨问对比图 + 整题概览图 |
| `results/figure_quality_report.json` | Phase F | 图表质量审计 |
| `writer_prompt.md` | Phase 5 | 整题总装写作交接（汇总各问提示词、图表清单、合规与复现） |
| `compliance_record.json` | Phase 5 | 合规与匿名审计 |
| `reproducibility_manifest.json` | Phase 5 | OS、库、hash、耗时 |

</details>

---

## 🔀 与原版 math-modeling 的差异

| 维度 | math-modeling（原版） | math-modeling-per-question（本分支） |
|------|----------------------|--------------------------------------|
| 交付节奏 | 整题一次性完成后再交付 | 每个小问独立完成并宣告，论文手立即开写 |
| 产物组织 | 工作区根目录平铺一套产物 | 根目录放全局产物，`questions/qN/` 放每问全套产物 |
| 建模共识 | 整题一次五视角共识 | 每个小问各跑一次五视角共识（硬性 gate 不降级） |
| 评委审查 | 整题一次五评委审查 | 每个小问各审查一次，chart 类评委在 Phase F 复审图表 |
| 图表 | 代码阶段直接产出图表 | 小问阶段只产数据，全部小问结束后 Phase F 统一绘制（更多更美观） |
| 新增工具 | — | `tools/question_queue.py`；`workflow_runner scaffold --questions`；`pipeline_check --stage` |
| 新增产物 | — | `question_queue.json`、每问 `modeling_answer.md`、每问 `writer_prompt.md`、Phase 5 总装 `writer_prompt.md` |
| 不变的部分 | Phase 0 题目复现与题意审计、五视角/批评/修正/创新/裁决机制、12 项验证证据、评委角色与判定规则、合规与复现要求 | 完全一致 |

---

## 🔍 验证边界

默认工具链检查覆盖：代码执行、图表、brief 对齐、可信度证据、权威来源索引 (`source_registry_checker.py`)、案例检索 (`case_retrieval_checker.py`)、奖项级产物 (`award_readiness_checker.py`)、模型选择 (`model_selection_checker.py`)、优化证书 (`optimization_certificate_checker.py`)、不确定性预算 (`uncertainty_budget_checker.py`)、题型验证 profile (`validation_profile_checker.py`)、数据泄漏 (`data_leakage_checker.py`)、统计验证 (`statistical_validation_checker.py`)、数据契约 (`schema_checker.py`)、模型规范 (`model_spec_checker.py`)、符号单位 (`unit_checker.py`)、数值鲁棒性 (`robustness_checker.py`)、图表证据 (`figure_auditor.py`)、创新筛选 (`innovation_checker.py`)、评委组审查 (`judge_panel_checker.py`)、合规记录 (`compliance_checker.py`)、写作交接提示词 (`writer_prompt_checker.py`) 与可复现清单 (`manifest_checker.py`)。题目对齐与可信度证据由 `evidence_checker.py` 与 `consistency_checker.py` 把关，权威资料来源分层由 `competition_sources.json` 索引。

**`--stage question|final`（分支新增，默认 `final` 与原版一致）**：`question` 用于 `questions/qN/` 小问工作区——零 PNG 图表只报 warning 不判失败（图表统一延后到 Phase F），Phase F/5 根产物不计入该问缺失项；`final` 用于整题最终交付。

**重要边界**：所有 checker 都是**结构化检查，不等价于数学证明**。真实任务仍需要 Phase 4 的并行审查 Agent、独立复现 Agent、评委质询 Agent 和问题级断言共同验证。

资料内容读取需显式运行 `source_material_reader.py`，或在总控中加 `--online-source-materials` 做发布前联网深扫。

---

## 🧪 测试

```bash
# 编译检查
python -m compileall tools

# 单元 + 集成测试
python -m pytest tests -q

# 完整测试编排
python tests/run_all_tests.py
```

完整验证清单见 [`docs/RELEASE_CHECKLIST.md`](docs/RELEASE_CHECKLIST.md)。

---

## ⚙️ 项目结构

- **`SKILL.md`** —— 短主入口，明确触发条件、核心约束与 Phase Gates
- **`references/`** —— 降低上下文负担的详细文档：`references/workflow.md`（完整流程）、`references/templates.md`（产物模板）、`references/tools.md`（CLI 字段说明）、`references/competition_sources.json`（权威来源）、`references/award_playbook.md`（题型方法卡）、`references/evaluator_panel.md`（评委规则）、`references/evals.md`（eval 流程）
- **`tools/`** —— Python CLI 工具（39 个，其中 24 个 *_checker.py），全部可独立运行
- **`workflows/`** —— 宿主 workflow JS 模板，用于派发并行 Agent
- **`evals/`** —— 本地 eval、触发评估、mini contest benchmark
- **`examples/`** —— 公开合成样例，便于其他 Agent 与开源用户对齐
- **`tests/`** —— pytest 测试套件，200+ 用例

---

## 🛡️ 安全

请勿在公开 issue 中贴出敏感数据、未公开竞赛题、API key 或个人信息。详见 [`SECURITY.md`](SECURITY.md)。

---

## 🤝 贡献

欢迎贡献。开发前请阅读 [`CONTRIBUTING.md`](CONTRIBUTING.md) 与 [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md)。本地开发流程：

```bash
python -m compileall tools
python -m pytest tests -q
python tests/run_all_tests.py
python tools/pipeline_check.py --workspace tests/test_data --language python
python tools/workflow_runner.py resume --workspace tests/test_data --language python
```

---

## 📄 许可证

本项目使用 **MIT License** 开源。详见 [`LICENSE`](LICENSE)。

## 📜 变更历史

详见 [`CHANGELOG.md`](CHANGELOG.md)。

---

<div align="center">

**Made with care for the math modeling community.**

If this skill helps your team, please ⭐ the repo to help others discover it.

</div>