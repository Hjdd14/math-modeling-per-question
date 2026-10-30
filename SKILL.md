---
name: math-modeling-per-question
description: 用于数学建模竞赛或类似多阶段建模任务，并且需要按小问分别交付、让论文手在后续小问求解期间即可并行写作已完成小问的场景。触发条件：用户提供题目 PDF/DOCX/Markdown/TXT 与 Excel/CSV 附件，要求对每个小问分别完成题意审计、建模方案、Python 或 MATLAB 代码、输出数据、建模解答文档、写作交接提示词、结果验证和评委审查，并在全部小问结束后统一绘制图表。不要用于普通单题解答、PDF 翻译、只写正式论文正文、只写一段代码，或不需要按小问拆分的整题一次性交付任务（后者请用 math-modeling skill）。
---

# 数学建模竞赛按小问分别交付 Skill（math-modeling 分支）

本 skill 是 math-modeling skill 的分支版本，执行数学建模竞赛中的建模与代码交付流程：题目理解、按小问的并行建模共识、创新筛选、可运行代码、输出数据、每问建模解答文档、证据验证、评委审查、合规复现和写作交接提示词。它不生成正式写作正文；正式论文正文应交给论文手或后续独立写作 skill。

与原版 math-modeling 的唯一核心差异：**整题一次性交付改为每个小问独立完整交付**。每完成一个小问，立即产出该问独立的建模解答 md、写作交接提示词、代码和输出数据，经完整检验与评委评分通过后在对话中宣告完成，论文手可立即开始该问写作；全部小问的建模代码结束后，再统一绘制图表（图尽可能多且美观）。

## 必读引用

执行前先读取这些文件：

1. `references/workflow.md`：完整 Phase 0 → 小问循环 → Phase F → Phase 5 流程，包含并行 Agent prompt、输入、输出和汇总规则。
2. `references/templates.md`：固定产物模板，包括 `question_queue.json`、`modeling_answer.md`、每问与总装 `writer_prompt.md`、`innovation_register.json`、`judge_panel_review.json` 和 `compliance_record.json`。
3. `references/tools.md`：所有 CLI 工具命令、JSON 字段和失败判定。
4. `references/competition_sources.json`：权威竞赛来源分层、官方入口和可信度规则。
5. `references/award_playbook.md`：权威竞赛案例方法谱系和题型方法卡片。
6. `references/evaluator_panel.md`：多评委并行审查角色、评分字段和 chair judge 汇总规则。
7. `references/evals.md`：本地 eval、Claude 实跑 eval、触发描述优化流程。
8. `docs/DESIGN_GATE_PLAN.md`：设计闸门（Phase 0.5）的完整规格、确认码机制、交叉校验、时间线校验，以及本分支的分小问适配（§21）。

如果引用文档与本主文件冲突，以本主文件的核心约束为准；如果用户的显式要求更具体，以用户要求为准。

## 核心约束

1. `problem_brief.md` 是唯一真实来源；模型、代码、结果、图表、建模解答文档和写作交接提示词都必须对照它核查。
2. 并行子 Agent 是核心能力，不能被 Python CLI、workflow runner 或引用文档替代。
3. Python CLI 只做确定性编排、状态管理和验证；不得把多 Agent 建模降级为单脚本假推理。
4. **每个小问独立完整走完 Phase 1-Q → Phase 2/3-Q → Phase 4-Q 全流程；五视角并行建模 Agent 是每问的硬性 gate，任何小问都不得省略或降级。**
5. **小问严格串行：只有当前小问通过全部工具验证与评委审查、并在对话中宣告"第 N 小问已完成"之后，才允许开始下一个小问；不得并行求解多个小问。**
6. **图表统一延后：小问循环期间代码只产出数据结果（CSV/JSON），不绘制任何图表；全部小问完成后进入 Phase F 统一绘制，图必须尽可能多且美观。**
7. 每个小问的产物独立成目录 `questions/qN/`，建模解答 `modeling_answer.md`、写作交接 `writer_prompt.md`、代码 `solution.py/.m`、输出 `results/` 齐备即取即用，论文手无需等待后续小问。
8. `modeling_answer.md` 是该小问建模过程与结果的完整解答记录，供论文手取用；它不是正式论文正文，正式正文由论文手或写作 skill 完成。
9. 所有小问阶段工具验证使用 `pipeline_check.py --stage question`；整题最终交付使用 `--stage final`。
10. 验证失败时回溯到对应阶段修正，而不是在后续阶段打补丁；某小问的验证失败不得靠后续小问的产物掩盖。
11. 难题必须保留可证伪证据链：题意审计、baseline、oracle 或等价小例验证、solver 交叉验证、敏感性分析和独立复现记录——每个小问各自独立保留一份。
12. 未解决的 high severity 歧义必须写入 `modeling_memory.md`，不能静默进入小问循环。
13. 难题或完整验证必须使用 `pipeline_check.py --evidence-mode strict`。
14. 奖项级交付必须使用题意完成度、模型选择审计、优化证书、不确定性预算、题型 profile、数据泄漏、统计验证、模型规范、数据契约、自动测试、数值鲁棒性、图表语义证据、多评委并行审查、创新筛选、合规复现和写作交接闭环；每个小问在其工作区运行 `pipeline_check.py --stage question --quality-mode excellence`，整题交付前在根工作区运行 `--stage final --quality-mode excellence`。
15. 每个小问的 `model_spec.json`、`model_selection_audit.json`、`validation_profile.json`、`symbol_table.json`、`solver_strategy.json`、`innovation_register.json` 和 `writer_prompt.md` 是该问模型、代码、验证器和后续写作之间的对齐基准。
16. 小问之间允许单向依赖：后求解的小问可以读取已宣告完成小问的 `final_solution.json` 与 `results/` 作为输入，但不得修改已完成小问的任何产物。
17. **Phase 0.5 是框架闸门（A 闸门）**：`question_queue.json` 建立后、进入小问循环之前，必须先产出一块覆盖全部小问的 `design_board.json`（schema v2：每问 3–5 个 `paradigm_set` + `paradigm_selection`，至少 1 个异质族）并渲染，由用户确认；**确认之前不允许写任何代码**（包括 `questions/qN/solution.py`）。A 板**不锁定模型选型**。
17b. **Phase 1.5-Q 是方案择定闸门（B 闸门，每问一次）**：每个小问在 Phase 1-Q 五视角与真实试算之后，必须产出该问 `questions/qN/model_advice.json`、`questions/qN/perspective_trials.json` 与 `questions/qN/design_board_gate_b.json`，由用户在该问 B 板上选定模型并 `confirm`；**B 板确认前不得进入 Phase 2-Q/3-Q，不得写该问 `solution.py` / `solution.m` / `solution_tests.*`**。
18. `design_board.py confirm --apply`（A 板一次、每问 B 板各一次）必须由用户本人在真实终端执行并输入该板 4 位确认码；AI 不得代跑、不得代填，也不得用 `--skip-interactive` 冒充人工确认（那会留 `confirm_not_attested` 痕迹，excellence 判不通过）。
19. 若某问在 Phase 1-Q 发现 **A 板范式集合本身不成立** → 走 `reopen_gate_request.json`（`gate: "a"`）重开 A 闸门；若用户在 B 板选定的方案不可行 → 走 `reopen_gate_request.json`（`gate: "b"`）重开该问 B 闸门。**不允许改板后直接写代码，也不允许 AI 自行换方案。**
20. `problem_brief.md`（根与每问）**不得**出现"已锁定选型 / 不得更换 / user_locked=true / 主模型已由…闸门"这类措辞；模型选择只能由该问 B 板的 `user_choice` 决定。

## 固定产物

工作区内固定维护以下文件或目录，分为全局产物、每问产物、统一绘图与总装产物三组：

### 全局产物（工作区根目录）

| 产物 | 阶段 | 说明 |
|------|------|------|
| `problem_brief.md` | Phase 0 | 题目、目标、约束、附件摘要（全局唯一真实来源） |
| `ambiguity_register.json` | Phase 0 | 题意歧义、单位、隐藏约束和评分要求审计 |
| `assumption_ledger.md` | Phase 0+ | 假设来源、影响和验证状态 |
| `scoring_strategy.md` | Phase 0 | 题目小问、评分点、数值答案和图表支撑策略 |
| `question_queue.json` | Phase 0+ | 小问队列、依赖关系、每问状态与完成记录 |
| `data_schema.json` | Phase 0/3 | 附件字段、类型、单位、缺失率、范围和主键契约（全局共享，逐问扩充） |
| `symbol_table.json` | Phase 1/2 | 符号、单位和代码变量映射（全局共享，逐问扩充） |
| `modeling_state.json` | 全程 | 机器可读状态（整题进度） |
| `modeling_memory.md` | 全程 | 人类可读过程记忆（整题进度） |
| `case_retrieval.json` | Phase 1 | 全局相似题型检索（各小问检索的公共参考，可选） |
| `design_board.json` | **Phase 0.5** | **A 板**：一块板覆盖全部小问，每题 `paradigm_set` + `paradigm_selection`（schema v2，不锁定模型） |
| `design_rounds/round_NNN.json` | **Phase 0.5** | A 板每轮回执：用户改了什么、回传来源与 nonce |
| `design_board.md` / `.html` / `design_choices.xlsx` | **Phase 0.5** | A 板渲染视图（导图 + 范式表 + 4 位确认码） |
| `mini_trials.json` | **Phase 0.5** | 可选：A 阶段小样本试算；B 闸门改用每问的 `perspective_trials.json` |

### 每问产物（`questions/qN/`，每个小问一份）

| 产物 | 阶段 | 说明 |
|------|------|------|
| `questions/qN/problem_brief.md` | Phase 1-Q | 该问简报：全局上下文摘要 + 该问目标（供工具硬检查与独立阅读） |
| `questions/qN/problem_taxonomy.json` | Phase 1-Q | 该问题型分类 |
| `questions/qN/case_retrieval.json` | Phase 1-Q | 该问定向检索的相似题型与可借鉴方法 |
| `questions/qN/baseline_solution.json` | Phase 1-Q | 简单、可运行、可解释的基线模型 |
| `questions/qN/model_spec.json` | Phase 1-Q+ | 变量、目标函数、约束、参数、单位、数据映射和验证计划 |
| `questions/qN/model_selection_audit.json` | Phase 1-Q | 候选模型、评分、拒绝理由和最终选择证据 |
| `questions/qN/optimization_certificate.json` | Phase 1-Q/3-Q | 可行性残差、上下界、gap、替代求解器或枚举 oracle |
| `questions/qN/uncertainty_budget.json` | Phase 1-Q/4-Q | 数据、参数、模型和随机误差预算及影响 |
| `questions/qN/validation_profile.json` | Phase 1-Q/4-Q | 按题型记录验证证据 |
| `questions/qN/data_validation.json` | Phase 3-Q | 数据切分、目标泄漏和预处理记录（涉及时） |
| `questions/qN/statistical_validation.json` | Phase 3-Q/4-Q | 指标、残差、区间、稳健性和过拟合风险（涉及时） |
| `questions/qN/solver_strategy.json` | Phase 1-Q/3-Q | 首选求解器、备选求解器、fallback、超时和交叉验证 |
| `questions/qN/ablation_study.json` | Phase 1-Q/3-Q | baseline、简化模型、完整模型和消融实验 |
| `questions/qN/innovation_register.json` | Phase 1-Q | 创新点、题目痛点、baseline 增益、证据和风险 |
| `questions/qN/final_solution.json` | Phase 1-Q | 该问最终建模方案 |
| `questions/qN/model_decision.md` | Phase 1-Q | 共识过程和裁决理由（记录用户选择与建议推荐的差异） |
| `questions/qN/design_board_gate_b.json` | **Phase 1.5-Q** | **B 板**：该问候选分数/优缺点/数据对比/用户选择/确认状态 |
| `questions/qN/design_rounds_gate_b/round_NNN.json` | **Phase 1.5-Q** | B 板回执 |
| `questions/qN/design_board_gate_b.md/.html` / `design_choices_gate_b.xlsx` | **Phase 1.5-Q** | B 板渲染视图（含 4 位确认码） |
| `questions/qN/model_advice.json` | **Phase 1.5-Q** | 建议 Agent 产出：1 建议 + 其余不建议 + 打分 + 多组数据对比 |
| `questions/qN/perspective_trials.json` | **Phase 1.5-Q** | 每视角真实试算（只能由 `tools/perspective_trial_runner.py` 写入） |
| `questions/qN/perspective_trials/*.py` | **Phase 1.5-Q** | 每视角试算脚本（试算代码，不是交付代码） |
| `questions/qN/reopen_gate_request.json` | Phase 1.5-Q+ | 重开闸门申请（范式不成立或所选方案不可行），可选 |
| `questions/qN/modeling_answer.md` | Phase 3-Q 后 | 该小问建模解答文档（问题分析、假设、符号、模型建立、求解、结果、检验、结论） |
| `questions/qN/writer_prompt.md` | Phase 2-Q/4-Q | 该小问写作交接提示词（Phase 2-Q 草稿 + Phase 4-Q 后定稿） |
| `questions/qN/solution.py` 或 `solution.m` | Phase 3-Q | 可运行代码 |
| `questions/qN/solution_tests.py` 或 `solution_tests.m` | Phase 3-Q | 代码 Agent 先写的契约测试 |
| `questions/qN/results/` | Phase 3-Q+ | 该问 CSV/JSON 输出（不产 PNG，图表延后） |
| `questions/qN/results/validation_summary.json` | Phase 3-Q+ | baseline、oracle、交叉验证、敏感性和不变量证据 |
| `questions/qN/judge_panel_review.json` | Phase 4-Q | 该问多评委并行审查和 chair judge 汇总 |
| `questions/qN/decision_insights.md` | Phase 4-Q | 该问结果解释、工程/管理含义、风险提示和可执行策略 |
| `questions/qN/defense_questions.md` | Phase 4-Q | 该问评委质询 Agent 问题和修正建议 |
| `questions/qN/modeling_state.json` | 该问全程 | 该问机器可读状态 |
| `questions/qN/agent_outputs/` | 该问全程 | 该问各 Agent 运行摘要 |

### 统一绘图与总装产物（工作区根目录）

| 产物 | 阶段 | 说明 |
|------|------|------|
| `figure_style.json` | Phase F | 图表风格规范（统一 DPI、字体、色板） |
| `figure_storyboard.md` | Phase F | 图表叙事板，每张图包含 file、claim、source_data、x_unit、y_unit 和 supports_question |
| `results/result_*.png` | Phase F | 统一绘制的全部图表，每问至少 5 张证据图 + 跨问对比图 + 整题概览图 |
| `results/figure_quality_report.json` | Phase F | 图表清晰度、叙事支撑和出版级质量审计 |
| `writer_prompt.md` | Phase 5 | 整题总装写作交接提示词（汇总各问提示词、图表清单、合规与复现） |
| `compliance_record.json` | Phase 5 | AI 使用、匿名性、资料引用、官方规则和最终提交约束 |
| `reproducibility_manifest.json` | Phase 5 | OS、Python/MATLAB、求解器、依赖、随机库、耗时、输入/输出 hash |

## 执行入口

首次开始（全局工作区）：

```bash
python "tools/workflow_runner.py" scaffold --workspace "." --language python
```

建立小问队列（Phase 0 评分策略确认小问清单后，示例为三个小问）：

```bash
python "tools/workflow_runner.py" scaffold --workspace "." --language python --questions q1,q2,q3
# 或用独立队列工具：
python "tools/question_queue.py" init --workspace "." --questions q1,q2,q3
```

小问循环期间常用：

```bash
python "tools/question_queue.py" next --workspace "."        # 取出下一个待求解小问并标记 in_progress
python "tools/question_queue.py" status --workspace "."      # 查看队列进度
python "tools/question_queue.py" complete --workspace "." --question q1 --score 87   # 宣告完成后登记
python "tools/pipeline_check.py" --workspace "questions/q1" --language python --stage question
```

恢复任务：

```bash
python "tools/workflow_runner.py" resume --workspace "." --language python
python "tools/question_queue.py" status --workspace "."
```

整题最终交付验证（难题、完整交付、竞赛正式结果必须使用）：

```bash
python "tools/pipeline_check.py" --workspace "." --language python --stage final --evidence-mode strict --quality-mode excellence
```

标准模式只做结构自检，缺失的质量闭环产物只报 warning；`passed: true` 仅表示没有硬性错误，
产物齐备情况见返回值中的 `artifact_completeness` 与 `status` 字段。最终交付一律以严格/卓越模式为准。

把 `python` 换成 `matlab` 即使用 MATLAB 分支。`workflow_runner.py` 只初始化、恢复和验证文件状态；并行 Agent 推理仍必须由执行者按 `references/workflow.md` 发起。

## Phase Gates

### Phase 0: 题目与数据提取（与原 math-modeling 完全相同）

读取题目文件和附件，使用 `tools/input_parser.py` 与 `tools/data_analyzer.py` 生成 `problem_brief.md`。启动题意审计 Agent、问题拆解与评分策略 Agent，并根据题目领域和数据类型读取 `references/competition_sources.json` 完成竞赛来源匹配：电力、电路、电磁场优先参考电工杯；统计调查和社会经济数据优先参考统计建模大赛；行业数据和大数据题优先参考 MathorCup；工程真实问题优先参考深圳杯。生成 `ambiguity_register.json`、`assumption_ledger.md` 与 `scoring_strategy.md`。建立 `data_schema.json` 初稿，向用户确认题目目标、附件摘要、关键歧义、评分重点和编程语言。

确认后**额外执行一步**：根据 `scoring_strategy.md` 的小问清单，用 `--questions` 或 `tools/question_queue.py init` 建立 `question_queue.json`（含小问依赖关系），与用户确认求解顺序，然后更新 `modeling_state.json` 与 `modeling_memory.md`。

### Phase 0.5: 框架与探索边界闸门（A 闸门，整题一次，代码编写前）

`question_queue.json` 建立并确认后进入本阶段。目标是让用户在写任何代码前确认：**题目读对了吗、高危假设接不接受、每个小问要探索哪些方法范式**，并亲自确认。本阶段与主仓库 Phase 0.5 同源，差别只有一处：**一块板覆盖全部小问**（每题一个 entry，`id` 与队列一致）。**本阶段不选模型**——选模型在每个小问的 Phase 1.5-Q。

1. 为每个小问产 **3–5 个 `paradigm_set`**：每项带 `paradigm_id`、`name`、`family`（方法族）、`source_ref`（含 tier 与 verified）、`why_explore`、`explore_cost`；同一问内至少 1 个范式与其他范式**异质**（`family` 不同）。
2. 每题写 `paradigm_selection`（≥2 项、覆盖 ≥2 个族）、`options: []`、`user_choice: null`、`user_locked: false`。`mini_trial` 在本阶段可选。
3. 运行 `python "tools/design_board.py" render --workspace "." --format all`（默认 `--gate a`）生成 `design_board.md` / `.html` / `design_choices.xlsx`（含导图、范式表、4 位确认码）。
4. 交给用户改（增删范式、调整要探索的集合、写批注）。三条通道任选其一，语义等价：页面直选（`serve`）/ Excel（`ingest --from design_choices.xlsx`）/ 下载 JSON（`ingest --from design_board_submission.json`）。
5. 重复至连续 2 轮无修改、无待决项、`board_sha256` 与内容一致。
6. **由用户本人**运行 `python "tools/design_board.py" confirm --workspace "." --apply` 并输入 4 位确认码。AI 不得代跑。
7. 运行 `python "tools/design_board_checker.py" --workspace "." --gate a --mode excellence` 验证范式集合、异质性与时间线。
8. 确认通过后才允许进入小问循环。五视角以该问 `paradigm_selection` 为**探索边界**，不得被任何预设选型锁定；范式本身不成立时走 `reopen_gate_request.json`（`gate: "a"`）。

> 确认只做**一次**、且在所有小问的代码之前——这正是本分支"逐问交付 + 论文手并行写作"能成立的前提：闸门开一次，之后每问完成即可交论文手，不再二次阻塞。
> 若某问在 Phase 1-Q 发现候选不成立：改板 → 重新 render → 重新收敛 → **用户重新确认**（确认码会变），之后才能继续写代码。
> 旧项目先跑 `python "tools/migrate_workspace.py" --workspace "."`（dry-run）再 `--apply` 生成骨架；骨架**不会**伪造确认状态，用户必须自己走完 render → confirm。
> 若宿主支持 hook，装 `hooks/pre_tool_use_guard.py`（见 `hooks/README.md`）可在 AI 试图写 `solution.py` 时硬拦——这是 L5 防线，前四层在 skill 内部。

### 小问循环：对 `question_queue.json` 中每个小问顺序执行

#### Phase 1-Q: 该问并行建模共识

本问的建模以 A 板里该问的 `paradigm_selection` 为**探索边界**：五视角各自在边界内独立提出最优方案，**不得被任何预设选型锁定**（A 板不承载模型选择）；若认为范式集合本身不成立，走 `reopen_gate_request.json`（`gate: "a"`）。

> **禁止**把"主模型已锁定 / user_locked=true / 不得更换"写进 `questions/qN/problem_brief.md`：`brief_completeness_checker.py` 会扫这类字样并判 `brief_contains_locked_selection`。选型只能由本问 Phase 1.5-Q 的 `user_choice` 决定。

为该问写入 `questions/qN/problem_brief.md`（全局上下文摘要 + 该问目标）与 `problem_taxonomy.json`，再由该问资料库检索 Agent 读取 `competition_sources.json` 和 `award_playbook.md` 输出该问 `case_retrieval.json`。五个视角 Agent 并行生成方案（硬性 gate），按题型最多追加 3 个动态专家 Agent，随后并行批评、并行修正，创新筛选 Agent 生成该问 `innovation_register.json`，最后由裁决 Agent 生成该问 `baseline_solution.json`、`model_spec.json`、`solver_strategy.json`、`ablation_study.json`、`final_solution.json` 与 `model_decision.md`。本阶段不生成正式写作正文。有依赖的小问可读取已完成小问的 `final_solution.json` 与 `results/` 作为输入。

五视角建模 Agent 包括（每问同轮并行，缺一不可）：

- 优化视角 Agent
- 统计视角 Agent
- 物理机理 Agent
- 工程实践 Agent
- 创新方法 Agent

#### Phase 1.5-Q: 该问方案择定闸门（B 闸门）

Phase 1-Q 的五视角并行、批评与修正完成后进入本阶段。**每问一块 B 板、逐问确认**；本阶段只回答：这一问用哪个模型。

1. 每视角产出可跑试算脚本 `questions/qN/perspective_trials/<perspective>.py`（stdout 打印一个 JSON 对象作为 metrics）。
2. 用 `python "tools/perspective_trial_runner.py" open/run --workspace "questions/qN" --slices slices.json ...` 真跑 **≥2 组数据切片**（无数据集的小问用 `--axis parameter|scenario`）。**禁止手填**：`perspective_trials.json` 只能由 runner 写入（`executed_by: "tool"` + `exit_code` + `stdout_sha256`）。
3. 建议 Agent 写 `questions/qN/model_advice.json`：恰好 1 个 `recommended` + 其余 `not_recommended`；候选 5–8；每个候选 `pros`/`cons` 各 ≥2；不推荐项 `why_not` ≥2 + `when_better`；`data_comparison` ≥2 slice × 全候选且数值回溯到 trials；`is_judge_panel: false`。
4. `python "tools/model_advice_builder.py" assemble --workspace "questions/qN"` 生成骨架 → Agent 只填判断字段 → `validate --workspace "questions/qN" --mode excellence` 必须 `passed: true`。
5. `python "tools/design_board.py" render --gate b --workspace "questions/qN" --format all` 生成该问 `design_board_gate_b.md/.html` 与 `design_choices_gate_b.xlsx`。
6. 用户用同一套通道选定该问模型（serve / Excel / JSON），`ingest --gate b` 写 `questions/qN/design_rounds_gate_b/`。
7. **由用户本人**运行 `python "tools/design_board.py" confirm --gate b --workspace "questions/qN" --apply` 并输入该问 B 板确认码。
8. `python "tools/design_board_checker.py" --gate b --workspace "questions/qN" --mode excellence`：校验建议 8 条规则、trials 工具执行与数值一致、`user_choice`、双时间线（该问 `solution.*` 不得早于 B 板确认）。
9. 裁决 Agent 读该问 B 板 `user_choice`，**无条件采用用户所选方案**，产出该问 `model_selection_audit.json`（`selected_by: "user"`、`user_choice_id`、`advice_recommended_id`、`diverged_from_advice`）与 `model_spec.json`、`solver_strategy.json`、`optimization_certificate.json`、`uncertainty_budget.json`、`validation_profile.json`、`ablation_study.json`、`innovation_register.json`、`final_solution.json`、`model_decision.md`。
10. 所选方案不可行 → 产出 `questions/qN/reopen_gate_request.json`（`gate: "b"`）并停下等用户重新确认；**不得自行换方案，也不得绕过 B 板写码**。

> 每问一次 B 闸门是本分支的刻意取舍：论文手可以并行写作，但**每个小问的模型都必须由人拍板**。B 板的打分不是评委结论（评委审查在 Phase 4-Q，`is_judge_panel` 硬约束为 false）。

#### Phase 2-Q/3-Q: 该问写作交接文档 Agent 与代码 Agent 并行

> **前置条件**：该问 B 板已确认（`questions/qN/design_board_gate_b.json` 的 `confirmed: true` 且 `user_choice` 非空）。未确认前不得写该问 `solution.*`；hook 守卫与 checker 会同时拦。

文档 Agent 只生成该问 `questions/qN/writer_prompt.md` 草稿，不生成正式写作正文。代码 Agent 先生成 `solution_tests.py` 或 `solution_tests.m`，再生成 `solution.py` 或 `solution.m`，并把该问所有结果和 `results/validation_summary.json` 写入 `questions/qN/results/`。**该阶段只产数据，不绘制任何 PNG 图表。**

验证证据必须由真实计算产生。模板默认的 `status: "NOT_VALIDATED"` 与 `passed: null` 会被 `evidence_checker.py` 和 `robustness_checker.py` 判为失败；确定性模型可对随机性相关条目声明 `{"status": "not_applicable", "rationale": ..., "alternative_validation": ...}`，但必须同时给出理由和替代验证方式。

代码与验证通过后，由建模解答撰写 Agent 基于该问 `final_solution.json`、`model_spec.json`、`results/` 和验证证据撰写 `questions/qN/modeling_answer.md`（模板见 `references/templates.md`）。

#### Phase 4-Q: 该问多评委并行审查、独立复现与工具验证

先并行启动技术审查组（语法、逻辑、输出审查 Agent），同时启动独立复现 Agent（只读该问 `problem_brief.md`、`baseline_solution.json`、`final_solution.json` 和代码输出）。再启动五评委并行审查：国赛建模评委、美赛评委、代码复现评委、图表证据评委（该轮只审数据可图性与图表叙事规划，正式图表在 Phase F 复审）、工程/业务解释评委；chair judge 汇总为该问 `judge_panel_review.json`。然后启动结果解释与决策建议 Agent、评委质询 Agent，输出该问 `decision_insights.md` 与 `defense_questions.md`，并把 `writer_prompt.md` 定稿补入审查与验证摘要。

汇总问题后运行 `pipeline_check.py --workspace "questions/qN" --stage question --board-root "."`（标准 → `--evidence-mode strict` → 奖项级 `--quality-mode excellence` 逐级），任何失败都必须修正并重新验证。`--board-root` 用于从根工作区解析 A 板。任一 high severity 未解决，必须回溯修正，不得宣告完成。

#### 完成宣告（硬性 gate）

该问全部验证通过后：

1. 运行 `question_queue.py complete` 登记该问状态、评委总分和产物路径；
2. 更新全局 `modeling_state.json` 与 `modeling_memory.md`；
3. 在对话中按固定格式宣告（模板见 `references/workflow.md`）："✅ 第 N 小问已完成"，包含评委总分与通过结论、关键结果数值、产物清单完整路径、遗留风险，并明确提示论文手可立即开始该问写作；
4. 运行 `question_queue.py next` 进入下一小问。

### Phase F: 统一图表绘制（全部小问完成后）

可视化设计 Agent 与图表代码 Agent 读取全部 `questions/q*/results/` 数据，生成全局 `figure_style.json` 与 `figure_storyboard.md`，统一绘制全部图表写入根目录 `results/`。图表必须**尽可能多且好看**：

- 每个小问至少 5 张证据图：数据质量图、模型结构/流程图、baseline vs final 对比图、敏感性/误差残差诊断图、不确定性区间图；按题型补充 Pareto 前沿图、路径规划图、仿真收敛图、地理/网络可视化等。
- 另加跨小问对比图与整题综合概览图。
- 每张图回答一个明确问题，标题写成发现而不是"图1"；`figure_storyboard.md` 每图含 `file`、`claim`、`source_data`、`x_unit`、`y_unit`、`supports_question`。
- 统一 DPI 300（导出 600）、字体、字号、线宽、色盲友好色板、黑白打印可辨性、图例位置、网格和留白。

运行 `figure_checker.py` 与 `figure_auditor.py` 审计，产出 `results/figure_quality_report.json`。图表证据评委对正式图表做复审。绘图后如需补充数据计算，回溯对应小问补充（只补图，不改已宣告的结论）。最后把各问图表清单增量补入对应 `questions/qN/writer_prompt.md`，并在对话中告知论文手图表已就位。

### Phase 5: 最终交付

确认固定产物齐全（全局 + 每问 + 绘图总装三组），生成或更新总装 `writer_prompt.md`、`compliance_record.json` 与 `reproducibility_manifest.json`，运行 `pipeline_check.py --stage final --evidence-mode strict --quality-mode excellence`，归档 `modeling_memory.md`，把验证摘要写入 `modeling_state.json`。最终摘要必须逐项说明每个小问的完成状态，以及 baseline 对比、oracle、 solver 交叉验证、敏感性、不变量、数值鲁棒性、图表审计、创新筛选、评委组审查、合规复现和独立复现是否通过。如果本 skill 自身被修改，还要更新 `audit_memory.md`。

## MATLAB 支持等级

MATLAB 是正式支持分支。使用 MATLAB 时：

- 代码文件为各小问目录下的 `solution.m`。
- 所有输出仍写入各小问 `results/`；统一图表写入根目录 `results/`。
- 图表保存为 PNG。
- 能检测到 MATLAB 且启用运行测试时，可用 `tools/code_runner.py --lang matlab` 实测；否则执行静态模板和产物检查。

## 验证清单

完成前必须至少运行：

```bash
python -m compileall tools
python -m pytest tests -q
python tests/run_all_tests.py
python "tools/pipeline_check.py" --workspace "tests/test_data" --language python
python "tools/pipeline_check.py" --workspace "tests/test_data" --language python --evidence-mode strict --quality-mode excellence
python "tools/pipeline_check.py" --workspace "tests/test_data" --language python --stage question
python "tools/design_board.py" status --workspace "tests/test_data"
python "tools/design_board_checker.py" --workspace "tests/test_data" --mode excellence
python "tools/mini_trial.py" status --workspace "tests/test_data"
python "tools/tools_sync_checker.py" --primary "../../../C/Users/PC/.agents/skills/math-modeling" --branch "."
python "hooks/selftest.py"
python "tools/question_queue.py" status --workspace "tests/test_data/per_question_workspace"
python "tools/source_registry_checker.py" --skill-root "." --mode excellence
python "tools/source_freshness_checker.py" --workspace "." --mode excellence
python "tools/award_readiness_checker.py" --workspace "tests/test_data" --mode excellence
python "tools/mini_benchmark_checker.py" --benchmark "evals/mini_contest_benchmark.json" --mode strict
python "tools/mini_benchmark_runner.py" --benchmark "evals/mini_contest_benchmark.json" --mode strict
python "tools/workflow_runner.py" resume --workspace "tests/test_data" --language python
Get-ChildItem workflows -Filter *.js | ForEach-Object { node --check $_.FullName }
```

验证结果与本次修改摘要必须追加到 `audit_memory.md`。
