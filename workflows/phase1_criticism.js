// Phase 1-Q.4 Round N: 5个视角Agent并行批评某小问的所有方案（按小问分支版）
// ⚠️ DEMO —— 单步并行派发模板，只覆盖一个小问的并行批评；不能替代 references/workflow.md 的
// Phase 1-Q 完整共识流程，不得作为交付依据。
// 定位：可选宿主 Workflow 模板，依赖宿主提供 agent/parallel 全局函数。
// 调用方式：Workflow({scriptPath: "workflows/phase1_criticism.js", args: {question_id: "q1", all_solutions: {...}}})

export const meta = {
  name: 'phase1q-criticism',
  description: '并行批评单个小问的全部候选方案',
  phases: [{ title: '并行批评' }]
}

const AGENTS = [
  { id: 'optimizer', name: '优化视角Agent' },
  { id: 'statistician', name: '统计视角Agent' },
  { id: 'physicist', name: '物理视角Agent' },
  { id: 'engineer', name: '工程视角Agent' },
  { id: 'innovator', name: '创新视角Agent' }
]

async function main(args) {
  const { question_id, all_solutions } = args
  if (!question_id) throw new Error('args.question_id is required')
  if (!all_solutions) throw new Error('args.all_solutions is required')

  const criticisms = await parallel(
    AGENTS.map(a => () => agent(
      `作为${a.name}，批评小问 ${question_id} 的以下全部候选方案（必须批评所有方案，而不只是自己的方案）。对每个方案输出：{"criticisms":["问题"],"suggestions":["建议"],"score":75,"severity":"medium"}\n\n全部方案：\n${JSON.stringify(all_solutions)}`,
      { label: `${question_id}_critic_${a.id}` }
    ))
  )

  const result = {}
  AGENTS.forEach((a, i) => { result[a.id] = criticisms[i] })
  return result
}
