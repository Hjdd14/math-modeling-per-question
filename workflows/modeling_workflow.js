// workflows/modeling_workflow.js（math-modeling-per-question 分支版）
// ⚠️ DEMO ONLY —— 按小问串行循环的并行派发骨架示例，不是本 skill 的正式流程。
// 本文件只演示"如何按 question_queue 逐问派发五视角建模 Agent、并行批评修正、
// 代码与写作交接并行、每问评委审查与完成宣告"，刻意保持精简。
// 它不实现 Phase 0、小问循环、Phase F、Phase 5 完整流程，缺少：problem_brief 生成、
// 题意审计与歧义登记、题型分类、资料库检索、baseline、固定 JSON 产物、契约测试、
// 独立复现、chair judge 汇总、合规复现、状态持久化、统一图表审计。
// 不得把本文件的执行结果当作交付依据或验证证据。
// 正式流程见 references/workflow.md；产物清单见 SKILL.md「固定产物」。
// 定位：可选宿主 Workflow 模板，依赖宿主提供 bash/agent/parallel/phase/log 全局函数。
// 调用方式：通过 Workflow 工具执行；不要承诺可用 node 直接运行。

export const meta = {
  name: 'math-modeling-per-question-demo',
  description: '【DEMO】按小问串行循环的并行派发骨架：每问完整求解+宣告，最后统一绘图（非完整流程）',
  phases: [
    { title: 'Phase 0: 数据提取与小问队列' },
    { title: '小问循环: Phase 1-Q/2-Q/3-Q/4-Q + 完成宣告' },
    { title: 'Phase F: 统一图表绘制' },
    { title: 'Phase 5: 归档' }
  ]
}

// 工具运行辅助函数
async function runTool(workdir, tool, ...args) {
  const toolPath = `${workdir}/tools/${tool}.py`
  const result = await bash(`python "${toolPath}" ${args.join(' ')}`)
  if (result.exitCode !== 0) {
    throw new Error(`Tool ${tool} failed: ${result.stderr}`)
  }
  return JSON.parse(result.stdout)
}

// 五视角 Agent 角色定义（每个小问都同轮并行，硬性 gate）
const AGENTS = [
  { id: 'optimizer', name: '优化视角Agent', prompt: '你是优化视角的建模专家。擅长线性规划、非线性规划、整数规划、动态规划。优先考虑计算效率和全局最优性。' },
  { id: 'statistician', name: '统计视角Agent', prompt: '你是统计视角的建模专家。擅长回归分析、时间序列、贝叶斯方法、蒙特卡洛。优先考虑统计显著性和置信区间。' },
  { id: 'physicist', name: '物理视角Agent', prompt: '你是物理视角的建模专家。擅长微分方程、动力系统、守恒定律。优先考虑物理可解释性和量纲一致性。' },
  { id: 'engineer', name: '工程视角Agent', prompt: '你是工程视角的建模专家。擅长仿真建模、离散事件系统、排队论。优先考虑实现难度和鲁棒性。' },
  { id: 'innovator', name: '创新视角Agent', prompt: '你是创新视角的建模专家。擅长机器学习、深度学习、混合模型。优先考虑可验证创新和表达亮点。' }
]

// 共识度评估
function evaluateConsensus(solutions) {
  const methods = Object.values(solutions).map(s => s.model_name || '')
  const unique = new Set(methods)
  const n = methods.length
  let score
  if (unique.size === 1) score = 100
  else if (unique.size === 2) score = 70
  else if (unique.size <= n / 2) score = 50
  else score = 30
  return { consensus_score: score, unique_methods: [...unique] }
}

function shouldContinue(roundNum, consensusHistory, maxRounds = 5, threshold = 80, stagnation = 2) {
  if (roundNum >= maxRounds) return false
  if (consensusHistory.length > 0 && consensusHistory[consensusHistory.length - 1] >= threshold) return false
  if (consensusHistory.length >= stagnation) {
    const recent = consensusHistory.slice(-stagnation)
    const diffs = recent.slice(1).map((v, i) => Math.abs(v - recent[i]))
    if (diffs.every(d => d < 2)) return false
  }
  return true
}

// 单个小问的完整求解（DEMO 骨架）
async function solveOneQuestion(workdir, language, question, priorResults) {
  const qid = question.id
  phase(`小问循环: ${qid} Phase 1-Q 并行建模共识`)

  const questionContext = `小问 ${qid}：${question.title}\n已完成小问结果（可引用，不得修改）：${JSON.stringify(priorResults)}`

  // 五视角同轮并行（DEMO 省略资料库检索与动态专家）
  const initialSolutions = await parallel(
    AGENTS.map(a => () => agent(
      `${a.prompt}\n\n针对以下小问生成建模方案，输出 JSON：\n${questionContext}`,
      { label: `${qid}_initial_${a.id}` }
    ))
  )
  let solutions = {}
  AGENTS.forEach((a, i) => { solutions[a.id] = initialSolutions[i] })
  let consensusHistory = []
  let round = 0

  while (shouldContinue(round, consensusHistory)) {
    round++
    phase(`${qid} 共识循环 Round ${round}`)
    const criticisms = await parallel(
      AGENTS.map(a => () => agent(
        `作为${a.name}，批评小问 ${qid} 的以下全部方案并评分：\n${JSON.stringify(solutions)}`,
        { label: `${qid}_critic_${a.id}` }
      ))
    )
    const updated = await parallel(
      AGENTS.map((a, i) => () => agent(
        `作为${a.name}，回应批评并修正小问 ${qid} 的方案（必须含 responses 字段）：\n批评：${JSON.stringify(criticisms[i])}\n原方案：${JSON.stringify(solutions[a.id])}`,
        { label: `${qid}_update_${a.id}` }
      ))
    )
    AGENTS.forEach((a, i) => { solutions[a.id] = updated[i] })
    const consensus = evaluateConsensus(solutions)
    consensusHistory.push(consensus.consensus_score)
    log(`${qid} Round ${round} 共识度: ${consensus.consensus_score}%`)
  }

  const finalSolution = await agent(
    `综合小问 ${qid} 的全部方案和讨论，裁决最终建模方案：\n${JSON.stringify({ solutions, consensusHistory })}`,
    { label: `${qid}_final_decision` }
  )

  // Phase 2-Q/3-Q 并行（DEMO 省略契约测试与 validation_summary 真实计算）
  phase(`小问循环: ${qid} Phase 2-Q/3-Q 并行`)
  const [writerPrompt, code] = await parallel([
    () => agent(
      `根据小问 ${qid} 的最终方案生成 questions/${qid}/writer_prompt.md 写作交接提示词草稿（不写正式论文正文）：\n${JSON.stringify(finalSolution)}`,
      { label: `${qid}_writer_prompt_agent` }
    ),
    () => agent(
      `根据小问 ${qid} 的最终方案编写 ${language} 代码，所有数据输出写入 questions/${qid}/results/（只产 CSV/JSON，不绘制任何图表）：\n${JSON.stringify(finalSolution)}`,
      { label: `${qid}_code_agent` }
    )
  ])

  // 建模解答撰写（分支新增）
  const modelingAnswer = await agent(
    `基于小问 ${qid} 的方案与代码结果撰写 questions/${qid}/modeling_answer.md 建模解答文档（问题分析、假设、符号、模型建立 LaTeX、求解方法、结果、检验、结论；声明非正式论文正文）：\n方案：${JSON.stringify(finalSolution)}\n代码：${code}`,
    { label: `${qid}_modeling_answer_agent` }
  )

  // Phase 4-Q 审查（DEMO 只演示技术审查三人组；正式流程还有独立复现与五评委）
  phase(`小问循环: ${qid} Phase 4-Q 并行审查`)
  const [syntaxCheck, logicCheck, outputCheck] = await parallel([
    () => agent(`语法审查小问 ${qid} 的代码：\n${code}`, { label: `${qid}_syntax_check` }),
    () => agent(`逻辑审查小问 ${qid} 代码与方案一致性：\n代码：${code}\n方案：${JSON.stringify(finalSolution)}`, { label: `${qid}_logic_check` }),
    () => agent(`输出审查小问 ${qid} 结果完整性与可图性数据：\n代码：${code}`, { label: `${qid}_output_check` })
  ])

  // 小问工作区工具验证（--stage question：零图表不判失败）
  await runTool(workdir, 'pipeline_check', '--workspace', `questions/${qid}`, '--language', language, '--stage', 'question')

  return { qid, finalSolution, writerPrompt, code, modelingAnswer, reviews: { syntaxCheck, logicCheck, outputCheck } }
}

// 主工作流
async function main(args) {
  const { problem_files, language, workdir, questions } = args
  if (!workdir) throw new Error('workdir is required')
  if (!language) throw new Error('language is required (python or matlab)')
  if (!problem_files || !problem_files.data) throw new Error('problem_files.data is required')
  if (!questions || !questions.length) throw new Error('questions is required, e.g. ["q1","q2","q3"]')

  // Phase 0: 数据提取 + 小问队列（DEMO 省略题意审计与评分策略 Agent）
  phase('Phase 0: 数据提取与小问队列')
  const dataStructure = await runTool(workdir, 'data_analyzer', 'read', '--file', problem_files.data)
  log(`数据结构: ${dataStructure.sheets[0].rows} 行, ${dataStructure.sheets[0].columns} 列`)
  await runTool(workdir, 'question_queue', 'init', '--workspace', '.', '--questions', questions.join(','), '--language', language)

  // 小问循环：严格串行，宣告一个再做一个
  const completed = {}
  for (const qid of questions) {
    const next = await runTool(workdir, 'question_queue', 'next', '--workspace', '.')
    const question = next.question || { id: qid, title: qid }
    const result = await solveOneQuestion(workdir, language, question, completed)

    // 完成登记与对话内宣告（正式流程还须先通过五评委审查与修正循环）
    await runTool(workdir, 'question_queue', 'complete', '--workspace', '.', '--question', qid)
    log(`✅ 第 ${qid} 小问已完成：建模解答 questions/${qid}/modeling_answer.md、写作提示词、代码与 results/ 已就位，论文手可立即开始该问写作。`)
    completed[qid] = result.finalSolution
  }

  // Phase F: 统一图表绘制（DEMO 只演示派发动作）
  phase('Phase F: 统一图表绘制')
  const figures = await agent(
    `读取全部 questions/*/results/ 数据，按全局 figure_style.json 统一绘制全部图表到根 results/：每小问至少 5 张证据图（数据质量、模型结构、baseline vs final、敏感性、不确定性），加跨问对比图与整题概览图；DPI 300、色盲友好、标题写成发现；每图登记 figure_storyboard.md 的 file/claim/source_data/x_unit/y_unit/supports_question。`,
    { label: 'figure_agent' }
  )
  await runTool(workdir, 'figure_checker', 'batch', '--dir', 'results', '--pattern', '*.png')

  // Phase 5: 归档（DEMO 只演示总装与总控验证）
  phase('Phase 5: 归档')
  const finalCheck = await runTool(workdir, 'pipeline_check', '--workspace', '.', '--language', language, '--stage', 'final')
  log(`最终总控验证: ${finalCheck.status}`)

  return {
    demo_only: true,
    demo_note: '本工作流仅演示按小问串行循环的并行派发骨架，未执行完整流程，不得作为交付依据。',
    completed_questions: Object.keys(completed),
    figures: figures,
    final_check_status: finalCheck.status
  }
}
