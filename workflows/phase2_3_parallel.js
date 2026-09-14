// Phase 2-Q & 3-Q: 并行执行某小问的写作交接提示词、代码编写与建模解答撰写（按小问分支版）
// ⚠️ DEMO —— 单步并行派发模板，只覆盖一个小问的 Phase 2-Q/3-Q 派发动作；不产出固定 JSON 产物、
// 不做契约测试与验证，不能替代 references/workflow.md 的完整流程，不得作为交付依据。
// 定位：可选宿主 Workflow 模板，依赖宿主提供 agent/parallel 全局函数。
// 调用方式：Workflow({scriptPath: "workflows/phase2_3_parallel.js", args: {question_id: "q1", final_solution: {...}, language: "python"}})

export const meta = {
  name: 'phase2q-3q-parallel',
  description: '并行执行单个小问的写作交接与代码编写（只产数据不绘图）',
  phases: [{ title: '该问写作交接与代码并行' }, { title: '该问建模解答撰写' }]
}

async function main(args) {
  const { question_id, final_solution, language } = args
  if (!question_id) throw new Error('args.question_id is required')
  if (!final_solution) throw new Error('args.final_solution is required')
  if (!language) throw new Error('args.language is required (python or matlab)')

  const codeFile = language === 'matlab' ? 'solution.m' : 'solution.py'

  // 文档 Agent 与代码 Agent 并行；本 skill 不生成正式写作正文。
  const [writerPrompt, code] = await parallel([
    () => agent(
      `根据小问 ${question_id} 的最终建模方案，生成 questions/${question_id}/writer_prompt.md 写作交接提示词草稿（不要生成正式论文正文、不要生成 LaTeX 文档；图表清单填"Phase F 统一绘制后补入"）：\n${JSON.stringify(final_solution)}`,
      { label: `${question_id}_writer_prompt_agent` }
    ),
    () => agent(
      `根据小问 ${question_id} 的最终建模方案编写 ${language} 代码 questions/${question_id}/${codeFile}：先写契约测试再写实现；所有数据输出写入 questions/${question_id}/results/（output.csv、summary.json、validation_summary.json）；只产 CSV/JSON 数据，不绘制任何 PNG 图表，图表所需数据（敏感性曲线、收敛序列等）必须落盘供 Phase F 统一绘图：\n${JSON.stringify(final_solution)}`,
      { label: `${question_id}_code_agent` }
    )
  ])

  // 建模解答撰写 Agent（分支新增）：代码与验证证据产出后撰写该问建模解答文档
  const modelingAnswer = await agent(
    `基于小问 ${question_id} 的最终方案与代码结果，撰写 questions/${question_id}/modeling_answer.md：问题重述与分析、模型假设、符号说明、模型建立（LaTeX 公式）、求解方法、结果与分析（数值必须来自真实输出）、模型检验、该问结论；图表位置用占位标注；声明本文档不是正式论文正文。\n方案：${JSON.stringify(final_solution)}\n代码：${code}`,
    { label: `${question_id}_modeling_answer_agent` }
  )

  return { question_id, writer_prompt: writerPrompt, code, modeling_answer: modelingAnswer }
}
