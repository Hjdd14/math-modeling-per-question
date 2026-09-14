// Phase 1-Q.6: 主Agent综合某小问的所有方案和讨论，做出最终裁决（按小问分支版）
// ⚠️ DEMO —— 单步派发模板，只覆盖一个小问的裁决动作；不产出 model_spec/solver_strategy/
// optimization_certificate 等固定产物，不能替代 references/workflow.md 的 Phase 1-Q，不得作为交付依据。
// 定位：可选宿主 Workflow 模板，依赖宿主提供 agent 全局函数。
// 调用方式：Workflow({scriptPath: "workflows/phase1_final_decision.js", args: {question_id: "q1", all_solutions: {...}, all_criticisms: [...], consensus_history: [...]}})

export const meta = {
  name: 'phase1q-final-decision',
  description: '裁决单个小问的最终建模方案',
  phases: [{ title: '最终裁决' }]
}

async function main(args) {
  const { question_id, all_solutions, all_criticisms, consensus_history } = args
  if (!question_id) throw new Error('args.question_id is required')
  if (!all_solutions) throw new Error('args.all_solutions is required')

  const decision = await agent(
    `你是最终裁决 Agent。综合小问 ${question_id} 的全部候选方案、批评、修正与共识历史，选定最终建模方案。必须输出 JSON：{"question_id":"${question_id}","selected_model":"...","score_matrix":[{"model_name":"...","problem_fit":90,"interpretability":85,"computability":80,"data_requirement":75,"robustness":80,"validation_difficulty":40,"paper_presentation":88,"decision":"selected|rejected"}],"validation_plan":{"baseline_comparison":"...","oracle_tests":"...","solver_cross_checks":"...","sensitivity_analysis":"...","invariants":["..."]},"rationale":"裁决理由"}\n\n全部方案：\n${JSON.stringify(all_solutions)}\n\n批评历史：\n${JSON.stringify(all_criticisms || [])}\n\n共识历史：\n${JSON.stringify(consensus_history || [])}`,
    { label: `${question_id}_final_decision` }
  )

  return decision
}
