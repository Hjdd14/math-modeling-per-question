# Changelog

## 1.1.0-per-question（math-modeling 按小问分别交付分支）

- **分支核心变更**：整题一次性交付改为**每个小问独立完整交付**。每个小问各自走完整的 Phase 1-Q（五视角并行建模、动态专家、并行批评、并行修正、创新筛选、最终裁决）→ Phase 2-Q/3-Q（写作交接与代码并行、建模解答撰写）→ Phase 4-Q（技术审查三人组、独立复现、五评委并行审查、修正循环），通过后在对话中宣告"第 N 小问已完成"，论文手即可开始该问写作。
- 新增固定产物 `question_queue.json`：小问队列、依赖关系、每问状态、chair judge 总分与完成时间；小问严格串行，同一时刻最多一个 `in_progress`，依赖未满足不允许推进。
- 新增每问产物目录 `questions/qN/`：该问独立的 `problem_brief.md`、全套 Phase 1-Q 产物、`solution.py/.m`、`solution_tests.py/.m`、`results/`、`judge_panel_review.json`、`modeling_state.json` 等；所有 `--workspace` 类 checker 可直接指向该目录运行，无需改动 checker。
- 新增每问建模解答文档 `questions/qN/modeling_answer.md`（问题分析、假设、符号、模型建立、求解方法、结果、检验、结论；声明非正式论文正文），以及每问 `writer_prompt.md`（Phase 2-Q 草稿 + Phase 4-Q 定稿）和 Phase 5 整题总装 `writer_prompt.md`。
- **图表统一延后**：小问循环期间代码只产出 CSV/JSON 数据，不绘制任何 PNG；全部小问完成后进入新的 **Phase F 统一图表绘制**，要求每问至少 5 张证据图加跨问对比图与整题概览图，统一 DPI/字体/色板，标题写成发现，并审计 `results/figure_quality_report.json`。
- 新增 `tools/question_queue.py`：`init`（含 `--depends qN:qM` 依赖声明与迷你工作区骨架）/`next`/`complete`/`status`，文件锁 + 原子写入，与 `state_manager.py` 同风格。
- `tools/workflow_runner.py scaffold` 新增 `--questions q1,q2,...`（与可选 `--depends`），一次创建全部小问骨架与队列；不传该参数时行为与原版完全一致。
- `tools/pipeline_check.py` 新增 `--stage question|final`（默认 `final` 与旧行为一致）：`question` 模式下 `results/` 内零 PNG 图表只报 warning 不判失败（附 `deferred_figures` 标记），且 `figure_style.json`、`figure_storyboard.md`、`results/figure_quality_report.json`、`compliance_record.json`、`reproducibility_manifest.json` 等 Phase F/5 根产物不计入该问缺失项。
- Phase 0（题目 md 复现、题意审计、评分策略、竞赛来源匹配、用户确认）与原版完全一致，仅额外建立小问队列并与用户确认求解顺序。
- `references/workflow.md` 重写为 Phase 0 → 小问循环 → Phase F → Phase 5；`references/templates.md` 新增 `question_queue.json`、`modeling_answer.md`、每问与总装 `writer_prompt.md` 模板；`references/evaluator_panel.md` 明确每个小问独立评审、图表证据评委在 Phase F 复审图表；`references/tools.md` 补充新命令与失败判定。
- `workflows/*.js` 全部改写为按小问串行循环的 DEMO 派发骨架（保留 DEMO ONLY 警告，不替代正式流程）。
- 测试：新增 `tests/test_per_question_branch.py`（队列状态机、依赖校验、scaffold --questions、`--stage` 行为），并适配原有硬编码原版阶段编号/名称的用例；全套 226 passed。
- 原版 `math-modeling` skill 文件未被修改；本分支为其本地副本（位于 `math_modeling_eq/math-modeling-per-question`）。

## Unreleased（继承自上游 1.0.0 之后的开发线）

- 新增 `award_readiness_checker.py` 并接入 excellence pipeline，用于硬审计 `ambiguity_register.json`、`assumption_ledger.md`、`scoring_strategy.md`、`ablation_study.json`、`decision_insights.md` 和 `defense_questions.md`，防止高风险歧义、评分策略、消融证据、决策解释或评委质询准备缺失时仍被放行。
- 新增奖项级 excellence gate：`brief_completeness_checker.py`、`model_selection_checker.py`、`optimization_certificate_checker.py`、`uncertainty_budget_checker.py`、`validation_profile_checker.py`、`data_leakage_checker.py`、`statistical_validation_checker.py`、`source_freshness_checker.py` 和 `mini_benchmark_runner.py`，并接入 `pipeline_check.py --quality-mode excellence`、CI 与 release checklist。
- 强化图表、合规和复现：`figure_storyboard.md` 每图必须含 `file`、`claim`、`source_data`、`x_unit`、`y_unit`、`supports_question`；`writer_prompt.md` 必须交接每图结论和提交复核清单；`compliance_record.json` 检查匿名、AI 披露、引用、页数、附件、代码提交和官方规则；`reproducibility_manifest.json` 增加 OS、求解器、随机库、耗时和输入/输出 hash。
- `solution_test_generator.py` 与 `robustness_checker.py` 统一奖项级阈值：随机种子至少 3 个、多初值至少 3 次、bootstrap/置信区间置信水平至少 0.95；`code_runner.py` 改为递归追踪结果文件和 sha256。
- 新增 `references/competition_sources.json`，把资料库扩展为权威竞赛来源分层索引，首版覆盖 7 个 tier_a 来源和 7 个 tier_b 来源，并记录官方入口、年份范围、材料类型和可信度说明。
- 扩容 `references/award_playbook.md`，按比赛维度和 10 类题型沉淀 40 张方法卡；每张方法卡标注来源比赛、年份、题号、适用条件、误用风险、推荐验证和来源链接。
- 新增 `tools/source_registry_checker.py`、`tools/case_retrieval_checker.py` 和 `tools/writer_prompt_checker.py`，并在 `pipeline_check.py --quality-mode excellence` 中纳入来源库、案例检索和写作交接提示词检查。
- 新增 `case_retrieval.json` 为固定产物，用于记录相似题型、可借鉴模型、不能照搬风险和推荐验证；电工、统计调查、大数据题会检查首选来源是否匹配。
- Eval 扩展覆盖 MathorCup 大数据题、电工杯电力题、统计建模社会经济题、深圳杯工程题、研究生赛工业题、APMCM 综合题和五一杯规划题。
- 规划为奖项级建模与代码交付增强：正式流程不再生成正式写作正文，改为输出 `writer_prompt.md`，把模型、代码、结果、图表、验证证据、复现信息和合规注意事项交给后续写作 skill。
- 新增 `references/award_playbook.md` 和 `references/evaluator_panel.md`，沉淀国赛/美赛题型方法谱系、验证方式、图表证据和多评委并行审查规则。
- 新增 `tools/innovation_checker.py`、`tools/judge_panel_checker.py` 和 `tools/compliance_checker.py`，并在 `pipeline_check.py --quality-mode excellence` 中纳入创新筛选、多评委审查、合规记录和 `writer_prompt.md` 检查。
- `tools/solution_test_generator.py` 生成的契约测试增加约束不变量、oracle、baseline 和随机种子稳定性检查。
- `tools/robustness_checker.py` 在严格/卓越模式下检查约束残差、最优性 gap、多初值、随机种子数量、置信区间和扰动稳定性阈值，不再只信任 `passed=true`。
- 规划为 `1.2.0`：新增奖项级交付质量闭环，包括 `model_spec.json`、`data_schema.json`、`symbol_table.json`、`solver_strategy.json`、`solution_tests.py`、`figure_style.json`、`figure_storyboard.md`、`writer_prompt.md`、`decision_insights.md`、`defense_questions.md` 和 `reproducibility_manifest.json`。
- 新增 `tools/schema_checker.py`、`tools/model_spec_checker.py`、`tools/unit_checker.py`、`tools/robustness_checker.py`、`tools/figure_auditor.py`、`tools/manifest_checker.py` 和 `tools/solution_test_generator.py`。
- `tools/pipeline_check.py` 新增 `--quality-mode standard|strict|hard|complete|full|excellence`，默认 standard 兼容增量工作区，excellence 要求完整模型、数据、代码、图表、写作交接和复现证据链。
- 新增 `examples/solved-python/`，展示完整合成样例的理想产物结构，方便其他 Agent 和开源用户对齐输出。
- 工作流新增问题拆解与评分策略 Agent、可视化设计 Agent、竞赛论文表现力 Agent、结果解释与决策建议 Agent、评委质询 Agent。
- 规划为 `1.1.0`：新增难题准确性增强链路，包括题意审计、假设台账、题型分类、动态专家 Agent、baseline、模型评分矩阵、`validation_summary.json` 和独立复现 gate。
- 新增 `tools/evidence_checker.py`，并在 `pipeline_check.py` 中集成 `--evidence-mode standard|strict`；普通旧工作区缺证据给 warning，难题/完整模式缺证据失败。
- Python 与 MATLAB 模板补齐 `run_baseline()`、`run_known_case_tests()`、`run_sensitivity_analysis()` 和 `write_validation_summary()` / 等价 JSON 输出。
- eval 覆盖多目标优化、缺失数据预测、图路径规划、随机仿真和非线性约束等难题场景。
- 新增 `tools/doctor.py`，用于本地依赖、仓库结构、可选工具和 quickstart 示例体检。
- 新增 `examples/quickstart/` 合成公开样例，帮助新用户先跑通题目解析和状态恢复。
- 修正 README 中 `input_parser.py` 的错误 quickstart 命令。
- 补齐 `requirements.txt` 与 `pyproject.toml` 的运行依赖：`matplotlib`、`scipy`、`Pillow`。
- 降低 `consistency_checker.py` 对 Python 容器/函数长变量名的 `code_only_symbol` 噪声。
- CI 增加 doctor 检查。

## 1.0.0 - 2026-06-23

正式版发布。

- 将长 `SKILL.md` 拆为短主入口和 `references/` 引用文档。
- 保留并强化 Phase 1、Phase 2/3、Phase 4 的并行 Agent gate。
- 新增 `workflow_runner.py`、`pipeline_check.py`、`input_parser.py` 和 `state_manager.py`。
- 新增可恢复 `modeling_state.json`，记录 phase、artifact、tool run、agent run 和 issues。
- 修复状态文件相对路径解析、并发写入覆盖和 `resume` 抹除历史的问题。
- 优化 `consistency_checker.py`，避免 Python AST 结构词造成误报，并支持机器可读 `passed` 字段。
- 明确 MATLAB 为正式支持分支，提供模板、夹具和可选集成测试。
- 新增 eval 文件、触发评估和开源发布文档。

## 0.2.0 - 2026-06-22

- 新增短主 skill 架构、引用文档、输入解析、状态管理、总控验证和工作流入口。
- 测试基线提升到 `99 passed, 1 skipped`。

## 0.1.0 - 2026-06-13

- 修复早期工具链假通过问题。
- 增补 LaTeX、图表、代码运行、brief 和一致性检查测试。
