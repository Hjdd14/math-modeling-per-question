// Phase 1-Q.5 Round N: 5个视角Agent并行回应批评并修正某小问的方案（按小问分支版）
// ⚠️ DEMO —— 单步并行派发模板，只覆盖一个小问的并行修正；不能替代 references/workflow.md 的
// Phase 1-Q 完整共识流程，不得作为交付依据。
// 定位：可选宿主 Workflow 模板，依赖宿主提供 agent/parallel 全局函数。
// 调用方式：Workflow({scriptPath: "workflows/phase1_update.js", args: {question_id: "q1", my_solution: {...}, all_criticisms: {...}, all_solutions: {...}}})

export const meta = {
  name: 'phase1q-update',
  description: '并行修正单个小问的候选方案',
  phases: [{ title: '并行修正' }]
}

const AGENTS = [
  { id: 'optimizer', name: '优化视角Agent' },
  { id: 'statistician', name: '统计视角Agent' },
  { id: 'physicist', name: '物理视角Agent' },
  { id: 'engineer', name: '工程视角Agent' },
  { id: 'innovator', name: '创新视角Agent' }
]

async function main(args) {
  const { question_id, my_solution, all_criticisms, all_solutions } = args
  if (!question_id) throw new Error('args.question_id is required')
  if (!all_criticisms) throw new Error('args.all_criticisms is required')

  const updated = await parallel(
    AGENTS.map(a => () => agent(
      `作为${a.name}，回应针对小问 ${question_id} 方案的批评并修正。要求：每个修正方案必须包含 responses 字段，逐条说明接受或拒绝批评的理由；必须补充验证计划和创新证据，不能只美化措辞。\n\n你的原方案：\n${JSON.stringify(my_solution || (all_solutions || {})[a.id])}\n\n全部批评：\n${JSON.stringify(all_criticisms)}`,
      { label: `${question_id}_update_${a.id}` }
    ))
  )

  const result = {}
  AGENTS.forEach((a, i) => { result[a.id] = updated[i] })
  return result
}
