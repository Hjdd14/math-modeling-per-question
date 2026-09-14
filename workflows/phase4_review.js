// Phase 4-Q: 并行启动某小问的3个审查Agent（语法/逻辑/输出）（按小问分支版）
// ⚠️ DEMO —— 单步并行派发模板，只覆盖一个小问的技术审查三人组；不含独立复现 Agent、
// 五类评委并行审查与 chair judge 汇总、question_queue 完成登记，不能替代
// references/workflow.md 的 Phase 4-Q 与完成宣告 gate，不得作为交付依据。
// 定位：可选宿主 Workflow 模板，依赖宿主提供 agent/parallel 全局函数。
// 调用方式：Workflow({scriptPath: "workflows/phase4_review.js", args: {question_id: "q1", code: "...", modeling_answer: "...", problem_brief: "..."}})

export const meta = {
  name: 'phase4q-review',
  description: '并行审查单个小问的代码与结果',
  phases: [{ title: '该问技术审查三人组' }]
}

async function main(args) {
  const { question_id, code, modeling_answer, problem_brief } = args
  if (!question_id) throw new Error('args.question_id is required')
  if (!code) throw new Error('args.code is required')

  const [syntaxCheck, logicCheck, outputCheck] = await parallel([
    () => agent(
      `语法审查小问 ${question_id} 的代码：检查语法错误、缩进、变量命名、依赖导入、主入口。\n\n代码：\n${code}`,
      { label: `${question_id}_syntax_check` }
    ),
    () => agent(
      `逻辑审查小问 ${question_id}：检查公式、约束、数据引用、算法逻辑是否与该问 problem_brief 和模型规范一致。\n\n代码：\n${code}\n\n该问简报：\n${problem_brief || '（未提供）'}\n\n建模解答：\n${modeling_answer || '（未提供）'}`,
      { label: `${question_id}_logic_check` }
    ),
    () => agent(
      `输出审查小问 ${question_id}：检查输出是否覆盖该问所有目标、结果是否合理、Phase F 统一绘图所需的数据（敏感性曲线、收敛序列等）是否已以 CSV/JSON 落盘（该阶段不应存在 PNG 图表）。\n\n代码：\n${code}`,
      { label: `${question_id}_output_check` }
    )
  ])

  return { question_id, syntax_check: syntaxCheck, logic_check: logicCheck, output_check: outputCheck }
}
