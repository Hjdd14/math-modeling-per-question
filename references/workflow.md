# 数学建模按小问并行 Agent 工作流（math-modeling-per-question 分支）

本文件保存完整 Phase 0 → 小问循环（Phase 1-Q / 2-Q / 3-Q / 4-Q）→ Phase F → Phase 5 流程。短主 `SKILL.md` 只是入口，并不削减这里的并行子 Agent 要求。所有 Python CLI 只做确定性解析、状态管理和验证，不能替代建模方案生成、批评、修正、代码实现、图表设计或审查推理。

本轮边界：本 skill 负责建模、代码、输出数据、每问建模解答文档、图表、验证证据、合规复现和写作交接提示词；不生成正式写作正文。每个小问的硬产物是 `questions/qN/modeling_answer.md` 与 `questions/qN/writer_prompt.md`，整题的硬产物是总装 `writer_prompt.md`。

与原版 math-modeling 的根本差异：**整题一次性交付改为按小问独立完整交付**。每个小问各自拥有完整的迷你工作区 `questions/qN/`、完整的 Phase 1-Q→4-Q 流程、完整的检验与评委审查；小问严格串行，宣告一个完成一个；图表统一延后到 Phase F。

## Phase 0: 题目与数据提取、题意审计和评分策略（与原版相同）

1. 使用 `tools/input_parser.py extract --file <题目文件>` 提取 PDF/DOCX/MD/TXT 题目文本。
2. 使用 `tools/input_parser.py brief --problem <题目文件> --data <附件...> --out problem_brief.md` 生成初版 brief。
3. 使用 `tools/state_manager.py init --workspace . --language python|matlab` 初始化状态。
4. 启动题意审计 Agent，输出 `ambiguity_register.json` 与 `assumption_ledger.md`。
5. 启动问题拆解与评分策略 Agent，输出 `scoring_strategy.md`。
6. 读取 `references/competition_sources.json`，做竞赛来源匹配：电力、电路、电磁场优先电工杯；统计调查和社会经济数据优先统计建模大赛；行业数据和大数据题优先 MathorCup；工程真实问题优先深圳杯；国际开放式表达参考 COMAP。
7. 建立 `data_schema.json` 初稿，记录附件列名、类型、单位、缺失率、异常值、主键和范围；建立 `symbol_table.json` 初稿，记录符号、单位和代码变量映射。两者为全局共享文件，小问循环中逐问扩充。
8. 向用户确认 `problem_brief.md` 中的题目目标、约束、附件摘要、关键歧义、评分重点、假设和编程语言。
9. **分支新增**：根据 `scoring_strategy.md` 的小问清单建立小问队列，并与用户确认求解顺序和依赖关系：

```bash
python "tools/question_queue.py" init --workspace "." --questions q1,q2,q3
# 或在 scaffold 时一并建立：
python "tools/workflow_runner.py" scaffold --workspace "." --language python --questions q1,q2,q3
```

队列中小问的默认顺序即用户确认的顺序；`depends_on` 记录"该问需要哪些已完成小问的结果作为输入"。依赖必须指向队列中排在该问之前的小问，不允许循环依赖。

### 0.1 题意审计 Agent

题意审计 Agent 专门找"读错题会导致后续全错"的风险，不能提出正式模型。它读取 `problem_brief.md` 和附件摘要，检查：

- 目标函数和评分要求是否完整。
- 单位、量纲、时间尺度、坐标系、编号、字段含义是否明确。
- 是否存在隐藏约束、边界条件、缺失数据、异常值、重复字段或不可用附件。
- 输出格式、图表、精度、排名规则是否遗漏。
- 用户确认前不能擅自把 high severity 歧义当作已解决。

`ambiguity_register.json` 格式：

```json
{
  "items": [
    {
      "id": "A1",
      "severity": "high",
      "source": "problem_brief.md:约束条件",
      "issue": "产能约束单位未说明是每天还是整个周期",
      "impact": "会改变约束右端项和最优解",
      "resolution": "pending",
      "assumption_if_unresolved": "按整个周期处理"
    }
  ]
}
```

`assumption_ledger.md` 必须记录每条假设的来源、影响、验证方式和状态。未解决的 high severity 歧义必须同步写入 `modeling_memory.md`，不能静默进入小问循环。

### 0.2 问题拆解与评分策略 Agent

该 Agent 专门判断"真正拿分的点"，不能跳过。它读取 `problem_brief.md`、题意审计结果和附件摘要，输出 `scoring_strategy.md`：

- 题目有哪些小问，每问必须回应什么。这份小问清单就是 `question_queue.json` 的来源。
- 哪些地方必须给出具体数值、排名、路径、预测区间或方案。
- 哪些图表最能支撑结论。
- 哪些地方适合突出模型创新。
- 哪些要求属于格式、精度、匿名性、AI 使用披露或解释性扣分点。

## 小问循环总规则

对 `question_queue.json` 中的每个小问，按队列顺序串行执行 Phase 1-Q → Phase 2-Q/3-Q → Phase 4-Q → 完成宣告。硬性规则：

1. **不得并行求解多个小问**：同一时刻最多一个小问处于 `in_progress`。
2. **每问都是完整迷你工作区**：`questions/qN/` 内含该问自己的 `problem_brief.md`、全套 Phase 1-Q 产物、代码、`results/`、评委审查和状态文件，所有 `--workspace` 类工具直接指向该目录运行。
3. **五视角并行建模 Agent 是每问的硬性 gate**，任何小问不得省略或降级为单 Agent。
4. **单向依赖**：当前小问可以读取任何已宣告完成小问的 `final_solution.json`、`results/` 与 `modeling_answer.md` 作为输入；严禁修改已完成小问的任何产物。
5. **宣告才能前进**：只有完成宣告（见"完成宣告"节）的小问才算完成；宣告之前不得开始下一问。
6. **小问循环期间不绘制任何 PNG 图表**；代码只写 CSV/JSON 数据结果。每问工具验证使用 `pipeline_check.py --stage question`，该模式下零图表不判失败。

每问开始时运行：

```bash
python "tools/question_queue.py" next --workspace "."
```

取出下一个待求解小问并标记 `in_progress`，同时校验其 `depends_on` 指向的小问均已 `completed`。

## Phase 1-Q: 该问并行建模共识

每个小问的 Phase 1-Q 都必须使用五视角建模 Agent。先由调度者基于全局 `problem_brief.md`、`scoring_strategy.md` 和题意审计结果，写入该问的 `questions/qN/problem_brief.md`（全局上下文摘要 + 该问求解目标、必答结果、输出要求）和 `questions/qN/problem_taxonomy.json`；再由该问资料库检索 Agent 读取 `references/competition_sources.json` 和 `references/award_playbook.md`，输出该问 `case_retrieval.json`，列出与该问相关的相似题型、可借鉴模型、推荐验证和不能照搬的风险（可引用全局 `case_retrieval.json` 的公共案例，但必须补充该问定向判断）。五个 Agent 并行生成方案时必须参考该问 `case_retrieval.json`，但不得直接套用不匹配模型。按该问题型最多追加 3 个动态专家 Agent，随后并行批评、并行修正，再由创新筛选 Agent 和最终裁决 Agent 选定方案。本阶段输出该问 `baseline_solution.json`、`case_retrieval.json`、`model_selection_audit.json`、`model_spec.json`、`solver_strategy.json`、`optimization_certificate.json`、`uncertainty_budget.json`、`validation_profile.json`、`ablation_study.json`、`innovation_register.json`、`final_solution.json` 与 `model_decision.md`，全部写入 `questions/qN/`，不生成正式写作正文。

### 1-Q.0 题型分类 problem_taxonomy

在五视角并行前，先由调度者基于该问简报写入 `questions/qN/problem_taxonomy.json`：

```json
{
  "question_id": "q1",
  "primary_types": ["optimization", "multi_objective"],
  "secondary_types": ["simulation", "sensitivity_analysis"],
  "data_regime": "small_structured_table",
  "uncertainty_sources": ["missing_field_semantics", "parameter_variation"],
  "recommended_dynamic_experts": ["multi_objective_optimizer", "robustness_validator"]
}
```

可选题型包括：优化调度、预测统计、图网络路径、随机仿真、物理机理、政策决策、多目标鲁棒、机器学习混合模型、非线性约束、网络流、博弈和聚类分类。

### 1-Q.0b 该问资料库检索 Agent

该 Agent 在该问五视角建模 Agent 之前执行。它读取该问 `problem_brief.md`、`problem_taxonomy.json`、`competition_sources.json` 和 `award_playbook.md`，输出 `questions/qN/case_retrieval.json`：

```json
{
  "question_id": "q1",
  "problem_domain": "电力调度",
  "matched_problem_types": ["电力电工", "优化调度"],
  "matched_cases": [
    {
      "rank": 1,
      "source_competition": "中国电机工程学会杯全国大学生电工数学建模竞赛",
      "year": "2026",
      "problem_id": "A/B",
      "problem_type": "电力电工",
      "similarity_reason": "题目领域、数据结构和约束形式相近",
      "borrowable_methods": ["负荷预测", "潮流约束", "鲁棒调度"],
      "cannot_copy_risks": ["工况、电网拓扑和参数口径不同，不能照搬变量定义"],
      "validation_needed": ["物理约束检查", "小例 oracle", "敏感性分析"]
    }
  ],
  "candidate_methods": ["robust_dispatch", "scenario_analysis"],
  "cannot_copy_risks": ["公开案例只提供题型和验证启发，不复制原作品正文"]
}
```

防乱套规则与原版相同：电力、电路、电磁场题的首个匹配应优先电工杯或电力相关案例；统计调查和社会经济数据题的首个匹配应优先统计建模大赛或数据洞察类案例；行业大数据题的首个匹配应优先 MathorCup 大数据或可核验行业数据案例。`tools/case_retrieval_checker.py` 会检查这些匹配关系（对每个小问工作区分别运行）。

### 1-Q.1 五视角建模 Agent 并行生成方案

在同一轮中并行启动以下 Agent，并要求每个 Agent 输出 JSON。动态专家是追加，必须保留原五视角，最多追加 3 个动态专家 Agent，不能替换任何一个五视角 Agent。

- `initial_optimizer`：优化视角 Agent。关注线性规划、非线性规划、整数规划、动态规划、全局最优性和计算效率。
- `initial_statistician`：统计视角 Agent。关注回归、时间序列、贝叶斯、蒙特卡洛、不确定性和置信区间。
- `initial_physicist`：物理机理 Agent。关注微分方程、动力系统、守恒定律、量纲一致性和可解释性。
- `initial_engineer`：工程实践 Agent。关注实现难度、鲁棒性、仿真、排队论和可部署性。
- `initial_innovator`：创新方法 Agent。关注混合模型、启发式算法、可验证创新和表达亮点。

动态专家示例：

- `graph_path_expert`：图路径、网络流、最短路、连通性。
- `forecasting_expert`：缺失数据、时间序列、holdout 验证、naive baseline。
- `stochastic_simulation_expert`：随机仿真、方差控制、置信区间。
- `multi_objective_expert`：Pareto、加权和、约束法和鲁棒权衡。
- `nonlinear_solver_expert`：非凸性、局部最优、初值敏感性。

统一 prompt：

```text
你是[角色]。请基于 questions/qN/problem_brief.md、全局 ambiguity_register.json、assumption_ledger.json、questions/qN/problem_taxonomy.json、questions/qN/case_retrieval.json 和 award_playbook.md，针对第 N 小问提出一个完整数学建模方案。该问依赖的已完成小问结果见 questions/qM/final_solution.json 与 questions/qM/results/（如有）。
必须输出 JSON：
{
  "agent_id": "...",
  "question_id": "qN",
  "model_name": "...",
  "problem_fit": "...",
  "variables": [{"name": "...", "meaning": "...", "range": "..."}],
  "objective_function": "...",
  "constraints": ["..."],
  "solution_method": "...",
  "assumptions": ["..."],
  "candidate_innovations": ["..."],
  "validation_plan": {
    "baseline": "...",
    "oracle_or_known_case": "...",
    "solver_cross_check": "...",
    "sensitivity_analysis": "..."
  },
  "pros": ["..."],
  "cons": ["..."],
  "complexity": "..."
}
```

### 1-Q.2 baseline_solution.json

并行方案产生后，必须生成该问 `baseline_solution.json`。baseline 应简单、可运行、可解释，不追求最好，但要能作为该问结果可信度下限。

```json
{
  "question_id": "q1",
  "baseline_name": "naive_feasible_solution",
  "rationale": "用贪心/均值/最短路/上一期值等简单规则构造可解释基线",
  "inputs_required": ["questions/q1/problem_brief.md"],
  "method": "...",
  "expected_outputs": ["questions/q1/results/output.csv", "questions/q1/results/summary.json"],
  "limitations": ["不追求最优，只用于可信度对比"]
}
```

### 1-Q.3 创新筛选 Agent

创新筛选 Agent 读取该问全部候选方案、baseline、`award_playbook.md` 和评分策略中该问的行，输出该问 `innovation_register.json`。每个创新点必须说明：

- 解决的该问痛点。
- 相对 baseline 的增益，或消融/敏感性分析证据。
- 实现成本和可解释性。
- 可验证证据与失败风险。
- 进入最终方案、保留为备选或拒绝的理由。

"为了高级而高级"的方法不得进入最终模型；创新必须被 baseline、消融或敏感性分析支撑。

### 1-Q.4 并行批评

把五视角方案、动态专家方案、`baseline_solution.json` 和 `innovation_register.json` 合并为 `all_solutions` 后，在同一轮中启动批评 Agent。每个批评 Agent 必须批评所有方案，而不只批评自己的方案。

输出 JSON：

```json
{
  "target_agent_id": {
    "criticisms": ["问题"],
    "suggestions": ["建议"],
    "score": 75,
    "severity": "medium"
  }
}
```

### 1-Q.5 并行修正

把批评意见返回给原 Agent，并行修正方案。每个修正方案必须包含 `responses` 字段，说明接受或拒绝每条批评的理由。修正时必须补充验证计划和创新证据，不能只美化措辞。

### 1-Q.6 共识判断与最终裁决

记录每轮共识度：

- 五个核心 `model_name` 完全一致：100
- 两类模型：70
- 不超过半数类别：50
- 高度分散：30

达到 80 分、连续两轮变化小于 2 分，或达到 5 轮时停止。动态专家意见参与裁决，但不改变"五视角建模 Agent 是硬性 gate"的要求。

启动 `final_decision` Agent，综合该问全部方案、批评、修正、题意审计、baseline、创新筛选和共识历史，输出该问 `final_solution.json`、`model_selection_audit.json`、`model_spec.json`、`solver_strategy.json`、`optimization_certificate.json`、`uncertainty_budget.json`、`validation_profile.json`、`ablation_study.json` 与 `model_decision.md`。

`final_solution.json` 必须包含模型评分矩阵：

```json
{
  "question_id": "q1",
  "selected_model": "...",
  "problem_taxonomy": {},
  "score_matrix": [
    {
      "model_name": "...",
      "problem_fit": 90,
      "interpretability": 85,
      "computability": 80,
      "data_requirement": 75,
      "robustness": 80,
      "validation_difficulty": 40,
      "paper_presentation": 88,
      "decision": "selected"
    }
  ],
  "validation_plan": {
    "baseline_comparison": "...",
    "oracle_tests": "...",
    "solver_cross_checks": "...",
    "sensitivity_analysis": "...",
    "invariants": ["..."]
  }
}
```

## Phase 2-Q: 该问写作交接文档 Agent

文档 Agent 与该问代码 Agent 并行执行。文档 Agent 不写正式论文正文，只整理该问论文手可直接使用的 `questions/qN/writer_prompt.md` 草稿。它读取全局 `problem_brief.md`、`scoring_strategy.md`、`ambiguity_register.json`、`assumption_ledger.json`、`symbol_table.json` 和该问 `case_retrieval.json`、`model_selection_audit.json`、`model_spec.json`、`optimization_certificate.json`、`uncertainty_budget.json`、`validation_profile.json`、`baseline_solution.json`、`innovation_register.json`、`final_solution.json`，输出首轮草稿。

该问 `results/validation_summary.json` 由并行的 Phase 3-Q 产出：**Phase 2-Q 首轮允许它缺省**，不要为等待它而阻塞并行；图表清单在 Phase F 统一绘图后增量补入（见 Phase F 节）；该问 `writer_prompt.md` 在 Phase 4-Q 审查通过后定稿，补入该问 `judge_panel_review.json` 摘要、验证证据摘要和遗留风险。

输出内容包括：

- 该问应答要点、模型主线和结论数值。
- 该问代码与结果文件路径。
- 该问计划图表清单（Phase F 后替换为实际图表清单）、每张图支撑的结论、建议放置位置。
- baseline、oracle、solver 交叉验证、敏感性和数值鲁棒性证据摘要。
- 创新点是否进入最终模型及其证据。
- AI 使用、匿名性、外部资料引用、复现命令和 hash 提醒。
- 明确声明：本 skill 不生成正式写作正文，只生成写作交接提示词与建模解答文档。

`writer_prompt.md` 不能包含队伍、学校、姓名等身份信息；不能复制优秀论文原文；只能抽象方法、验证方式和图表结构。

## Phase 3-Q: 该问代码 Agent

代码 Agent 与该问文档 Agent 并行执行。代码 Agent 读取该问 `final_solution.json`、`baseline_solution.json`、`model_spec.json`、`solver_strategy.json` 与 `problem_brief.md`（以及依赖小问的 `results/`，如有），不等待 Phase 2-Q 创建 `writer_prompt.md`。代码必须根据语言选择生成 `questions/qN/solution.py` 或 `questions/qN/solution.m`，所有输出必须写入 `questions/qN/results/`。

代码要求：

- 先根据 `model_spec.json`、`solver_strategy.json` 和验证计划生成 `solution_tests.py` 或 `solution_tests.m`，再写正式代码。
- 契约测试必须包含输出存在、约束不变量、小规模 oracle、baseline 不劣化、随机种子复现、输出字段与单位一致。
- 生成 `results/output.csv` 或同等结构化结果。
- 生成 `results/summary.json` 或同等摘要。
- 生成 `results/validation_summary.json`，记录 baseline 对比、小规模 oracle 测试、solver 交叉验证、敏感性分析、关键不变量、失败模式、约束残差、最优性 gap、多初值不少于 3 次、随机种子不少于 3 个、bootstrap/置信区间置信水平至少 0.95 和参数扰动排名稳定性。
- 每一项证据都必须由真实计算产生。模板默认的 `status: "NOT_VALIDATED"` 与 `passed: null` 会被 `evidence_checker.py`、`robustness_checker.py` 在所有模式下判为失败，不允许照抄模板充当验证结果。
- 随机性相关要求（多初值、随机种子、bootstrap 区间、扰动排名稳定）按题型条件化：确定性精确枚举、确定性线性规划、最短路、解析解 ODE 等模型可显式声明不适用，格式为
  `{"status": "not_applicable", "rationale": "为什么不适用", "alternative_validation": "改用哪种验证替代"}`。
  两个字段缺任一即判失败；`constraint_residuals` 与 `optimality_gap` 对任何模型都可核验，不允许声明不适用。
- 生成或更新该问 `data_validation.json`、`statistical_validation.json`、`optimization_certificate.json` 和 `validation_profile.json`，确保预测/机器学习题无目标泄漏、时间序列不用随机切分、预处理只在训练集拟合。
- **不生成任何 PNG 图表**；图表所需数据（如敏感性曲线、收敛序列、Pareto 点集）必须以 CSV/JSON 形式落入 `results/`，供 Phase F 统一绘图使用。
- Python 必须包含 `def main()`、`run_baseline()`、`run_known_case_tests()`、`run_sensitivity_analysis()`、`write_validation_summary()` 和 `if __name__ == "__main__": main()`。
- MATLAB 必须创建 `results` 目录，包含 `run_baseline()`、`run_known_case_tests()`、`run_sensitivity_analysis()`，并使用 `writetable`、`writecell` 或等价函数输出结果。

### 3-Q.1 建模解答撰写 Agent（分支新增）

该问代码与验证证据产出后，启动建模解答撰写 Agent。它读取该问 `problem_brief.md`、`final_solution.json`、`model_spec.json`、`model_decision.md`、`innovation_register.json`、`results/`（含 `validation_summary.json`），撰写 `questions/qN/modeling_answer.md`。

`modeling_answer.md` 是该小问的完整建模解答记录，供论文手直接取用写作；它必须：

- 按模板组织：该问问题重述与分析、模型假设（引用全局 `assumption_ledger.md` 中相关条目）、符号说明（与全局 `symbol_table.json` 一致）、模型建立（完整 LaTeX 公式）、求解方法与算法步骤、结果与分析（引用 `results/` 中的真实数值）、模型检验（baseline 对比、oracle、交叉验证、敏感性等证据摘要）、该问结论。
- 所有数值必须来自 `results/` 真实计算输出，禁止编造。
- 明确标注图表占位（如"【图：敏感性分析图，Phase F 统一绘制后插入】"），不写"图1"式空话。
- 声明本文档不是正式论文正文，正式正文由论文手或写作 skill 完成。

## Phase 4-Q: 该问多评委并行审查、独立复现与工具验证

Phase 4-Q 必须先并行启动技术审查组：

- 语法审查 Agent：检查语法错误、缩进、变量命名、依赖导入、主入口。
- 逻辑审查 Agent：检查公式、约束、数据引用、算法逻辑是否与该问 `problem_brief.md` 和模型规范一致。
- 输出审查 Agent：检查输出是否覆盖该问所有目标、结果是否合理、图表所需数据是否已落盘。

同时启动独立复现 Agent：

- 只读取该问 `problem_brief.md`、`baseline_solution.json`、`final_solution.json` 和代码输出。
- 不读取正式写作措辞，不读取 `modeling_answer.md` 的叙述性文字。
- 独立复算核心结论、关键约束和至少一个小规模 oracle/known case。
- 输出 `questions/qN/agent_outputs/independent_reproduction.json` 或写入状态中的 Agent run 摘要。

再启动多评委并行审查，至少包含：

- 国赛建模评委
- 美赛评委
- 代码复现评委
- 图表证据评委（该轮只审该问数据可图性、图表叙事规划和 storyboard 草案；正式图表在 Phase F 复审）
- 行业评委或工程/业务解释评委

每个评委独立输出结构化评分、high/medium/low 问题清单和是否通过；chair judge 汇总为 `questions/qN/judge_panel_review.json`。任一 high severity 未解决，必须回溯修正。

再启动结果解释与决策建议 Agent，输出该问 `decision_insights.md`。再启动评委质询 Agent，输出该问 `defense_questions.md`。最后把该问 `writer_prompt.md` 定稿：补入 `judge_panel_review.json` 摘要、`validation_summary.json` 证据摘要、遗留风险和复现命令。

汇总问题后运行：

```bash
python "tools/pipeline_check.py" --workspace "questions/qN" --language python --stage question
python "tools/pipeline_check.py" --workspace "questions/qN" --language python --stage question --evidence-mode strict
python "tools/pipeline_check.py" --workspace "questions/qN" --language python --stage question --evidence-mode strict --quality-mode excellence
```

难题、完整交付或竞赛正式结果必须使用 `--evidence-mode strict`；奖项级交付使用 `--quality-mode excellence`。

## Phase 4-Q: 修正循环

1. 修正 high severity 模型逻辑、代码错误、创新证据和合规问题。
2. 重新运行相关工具。
3. 修正 medium severity 问题。
4. 重新运行 `pipeline_check.py --stage question`，难题使用 `--evidence-mode strict`。
5. 奖项级交付额外运行 `source_registry_checker.py`、`source_freshness_checker.py`、`case_retrieval_checker.py`、`brief_completeness_checker.py`、`model_selection_checker.py`、`optimization_certificate_checker.py`、`uncertainty_budget_checker.py`、`validation_profile_checker.py`、`data_leakage_checker.py`、`statistical_validation_checker.py`、`schema_checker.py`、`model_spec_checker.py`、`unit_checker.py`、`robustness_checker.py`、`innovation_checker.py`、`judge_panel_checker.py`、`writer_prompt_checker.py`（均带 `--workspace questions/qN`；合规与复现清单类检查留待 Phase 5 在根工作区运行）。
6. 直到所有关键检查通过。

## 完成宣告（分支新增硬性 gate）

该问全部验证与审查通过后，按顺序执行：

1. 登记队列：

```bash
python "tools/question_queue.py" complete --workspace "." --question qN --score <chair_judge_overall_score>
```

2. 用 `tools/state_manager.py phase --workspace . --phase phase4 --status completed` 等方式更新全局 `modeling_state.json`（phase 名沿用原枚举；每问进度明细以 `question_queue.json` 为准），并在全局 `modeling_memory.md` 追加该问完成记录（完成时间、评委总分、产物路径、遗留风险）。
3. 在对话中输出固定格式宣告：

```text
✅ 第 N 小问已完成

- 评委组：总分 <overall_score>，chair judge 结论 <decision>；high severity 问题 <数量> 个（必须已全部解决）
- 关键结果：<该问 1-3 个最重要数值结论，注明出处 results/ 文件>
- 产物清单：
  - 建模解答：questions/qN/modeling_answer.md
  - 写作提示词：questions/qN/writer_prompt.md
  - 代码：questions/qN/solution.py（测试：solution_tests.py）
  - 输出数据：questions/qN/results/（output.csv、summary.json、validation_summary.json）
  - 评委审查：questions/qN/judge_panel_review.json
- 遗留风险：<medium/low 未解决项或"无">
- 论文手提示：第 N 小问的写作素材已齐备，可立即开始论文对应章节写作，无需等待后续小问。正式图表将在全部小问结束后的 Phase F 统一绘制并补入。
```

4. 运行 `python "tools/question_queue.py" next --workspace "."` 进入下一小问；若返回 `queue_finished: true`，进入 Phase F。

## Phase F: 统一图表绘制（分支新增阶段，全部小问完成后）

小问队列全部 `completed` 后进入本阶段。先启动可视化设计 Agent，读取全局 `problem_brief.md`、`scoring_strategy.md`、全部 `questions/q*/results/` 和各问 `writer_prompt.md`，输出全局 `figure_style.json` 与 `figure_storyboard.md`；再由图表代码 Agent 生成绘图代码（如 `make_figures.py` 或 `figures.m`）读取各问数据统一绘制，全部 PNG 写入根目录 `results/`。

图表硬要求（尽可能多且好看）：

- **数量下限**：每个小问至少 5 张证据图——数据质量图、模型结构/流程图、baseline vs final 对比图、敏感性/误差残差诊断图、不确定性区间图；按题型必须补充：优化题加约束利用率图与 Pareto 前沿图（多目标时）、预测题加拟合/残差/预测区间图、图网络题加路径规划图、仿真题加收敛图与分布图、机理题加相图/场分布图。另加至少 1 张跨小问对比图和 1 张整题综合概览图。
- **美观要求**：统一 DPI 300（导出 600）、字体、字号、线宽、色盲友好色板、黑白打印可辨性、图例位置、网格和留白；子图布局整齐，坐标轴标签与单位齐全，图题写成发现（如"负荷低谷集中在 02:00-05:00"）而不是"图1"。
- 每张图回答一个明确问题；`figure_storyboard.md` 中每张图必须包含 `file`、`claim`、`source_data`、`x_unit`、`y_unit` 和 `supports_question`。
- 所有图的数据来源必须是 `questions/q*/results/` 中的真实计算输出，禁止为绘图重新发明数据。

绘图与审计：

```bash
python "tools/figure_checker.py" batch --dir "results" --pattern "*.png"
python "tools/figure_auditor.py" --workspace "." --mode excellence
```

产出 `results/figure_quality_report.json`。图表证据评委对正式图表做复审（评分与问题写入根目录 `agent_outputs/phase_f/figure_judge_review.json`）。如绘图暴露数据缺口，回溯对应小问的代码补充计算（只补数据与图，不改已宣告的结论与 `judge_panel_review.json` 评分）。

图表全部通过审计后：

1. 把各问实际图表清单（文件名、claim、建议位置）增量补入对应 `questions/qN/writer_prompt.md` 的图表交接节；
2. 在 `questions/qN/modeling_answer.md` 中把图表占位替换为实际图文件名引用；
3. 在对话中告知用户与论文手："全部图表已统一绘制完成，各问图表清单已补入对应写作提示词"，并给出图表目录 `results/` 与叙事板 `figure_storyboard.md` 路径。

## Phase 5: 归档与交付

最终交付前确认固定产物：

- 全局：`problem_brief.md`、`ambiguity_register.json`、`assumption_ledger.md`、`scoring_strategy.md`、`question_queue.json`、`data_schema.json`、`symbol_table.json`、`modeling_state.json`、`modeling_memory.md`
- 每问（逐问核对 `questions/qN/`）：`problem_brief.md`、`problem_taxonomy.json`、`case_retrieval.json`、`baseline_solution.json`、`model_selection_audit.json`、`model_spec.json`、`optimization_certificate.json`、`uncertainty_budget.json`、`validation_profile.json`、`solver_strategy.json`、`ablation_study.json`、`innovation_register.json`、`final_solution.json`、`model_decision.md`、`modeling_answer.md`、`writer_prompt.md`、`solution.py/.m`、`solution_tests.py/.m`、`results/`、`results/validation_summary.json`、`judge_panel_review.json`、`decision_insights.md`、`defense_questions.md`
- 绘图与总装：`figure_style.json`、`figure_storyboard.md`、`results/result_*.png`、`results/figure_quality_report.json`、`writer_prompt.md`、`compliance_record.json`、`reproducibility_manifest.json`

生成总装 `writer_prompt.md`（模板见 `references/templates.md`）：汇总各问 `writer_prompt.md` 的路径与要点、整题图表清单、`compliance_record.json` 与 `reproducibility_manifest.json` 摘要路径，确保论文手或后续写作 skill 能看到来源匹配、各问评委审查、风险提示和合规提示。

运行总控验证并把结果写入 `modeling_memory.md` 和 `modeling_state.json`：

```bash
python "tools/pipeline_check.py" --workspace "." --language python --stage final --evidence-mode strict --quality-mode excellence
```

最终摘要必须逐项说明：每个小问的完成状态与评委总分，以及 baseline 对比、oracle 或等价小例验证、solver 交叉验证、敏感性分析、不变量、数值鲁棒性、图表审计、创新筛选、评委组审查、合规复现和独立复现是否通过。
