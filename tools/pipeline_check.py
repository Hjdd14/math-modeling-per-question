#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数学建模交付物总控验证工具（分小问分支）。

双闸门语义（契约 §1 / §8.5）：A 闸门是**整题一块** ``design_board.json``，
B 闸门是**每问一块** ``questions/qN/design_board_gate_b.json``。

本文件在主仓库版本的基础上保留分支四个专属特性：

1. ``--stage {question,final}``（默认 final）：小问工作区零 PNG 不判失败、
   不计 Phase F/5 根产物；
2. ``--board-root``：小问工作区里 ``--workspace`` 是 ``questions/qN``，
   A 板在题根，必须靠它解析（默认从 workspace 向上 ≤5 层找 ``design_board.json``）；
3. ``figure_checker`` 的 deferred_figures 语义（图表统一延后到 Phase F）；
4. ``_artifact_completeness(..., stage)``：stage=question 不计 Phase F/5 根产物。

B 闸门按问校验：stage=final 逐问跑 ``check_design_board(qN, mode, gate="b")``，
结果以 ``design_board_gate_b_q1`` 这类键并入 checks；stage=question 只校验当前小问。
"缺 B 板 + 有交付代码" 的严重性由 checker 判定，这里不重复实现。
"""

import argparse
import json
import sys
from pathlib import Path

try:
    from tools.award_readiness_checker import check_award_readiness
    from tools.brief_completeness_checker import check_brief_completeness
    from tools.brief_validator import validate_against_brief
    from tools.code_runner import run_code
    from tools.consistency_checker import check_formula_consistency
    from tools.data_leakage_checker import check_data_leakage
    from tools.evidence_checker import check_evidence
    from tools.figure_auditor import audit_figures
    from tools.figure_checker import batch_check
    from tools.innovation_checker import check_innovations
    from tools.judge_panel_checker import check_judge_panel
    from tools.latex_validator import validate_latex_file
    from tools.manifest_checker import check_manifest
    from tools.model_selection_checker import check_model_selection
    from tools.model_spec_checker import check_model_spec
    from tools.optimization_certificate_checker import check_optimization_certificate
    from tools.robustness_checker import check_robustness
    from tools.schema_checker import check_schema
    from tools.source_freshness_checker import check_source_freshness
    from tools.source_material_reader import check_source_materials
    from tools.source_registry_checker import check_source_registry
    from tools.statistical_validation_checker import check_statistical_validation
    from tools.uncertainty_budget_checker import check_uncertainty_budget
    from tools.unit_checker import check_units
    from tools.validation_profile_checker import check_validation_profile
    from tools.case_retrieval_checker import check_case_retrieval
    from tools.compliance_checker import check_compliance
    from tools.writer_prompt_checker import check_writer_prompt
    from tools.design_board_checker import check_design_board
except ImportError:
    from award_readiness_checker import check_award_readiness
    from brief_completeness_checker import check_brief_completeness
    from brief_validator import validate_against_brief
    from code_runner import run_code
    from consistency_checker import check_formula_consistency
    from data_leakage_checker import check_data_leakage
    from evidence_checker import check_evidence
    from figure_auditor import audit_figures
    from figure_checker import batch_check
    from innovation_checker import check_innovations
    from judge_panel_checker import check_judge_panel
    from latex_validator import validate_latex_file
    from manifest_checker import check_manifest
    from model_selection_checker import check_model_selection
    from model_spec_checker import check_model_spec
    from optimization_certificate_checker import check_optimization_certificate
    from robustness_checker import check_robustness
    from schema_checker import check_schema
    from source_freshness_checker import check_source_freshness
    from source_material_reader import check_source_materials
    from source_registry_checker import check_source_registry
    from statistical_validation_checker import check_statistical_validation
    from uncertainty_budget_checker import check_uncertainty_budget
    from unit_checker import check_units
    from validation_profile_checker import check_validation_profile
    from case_retrieval_checker import check_case_retrieval
    from compliance_checker import check_compliance
    from writer_prompt_checker import check_writer_prompt
    from design_board_checker import check_design_board


# 决策产物硬门：这两个是"AI 到底选了哪个模型、为什么"的唯一载体，缺了就不算交付。
DECISION_ARTIFACTS = ("final_solution.json", "model_decision.md")
STRICT_MODES = {"strict", "hard", "complete", "full", "excellence"}

# 双闸门板文件名与题根上溯层数（与 hooks/pre_tool_use_guard.py 保持一致）。
GATE_A_FILENAME = "design_board.json"
GATE_B_FILENAME = "design_board_gate_b.json"
BOARD_ROOT_FILENAME = GATE_A_FILENAME
MAX_BOARD_ROOT_LEVELS = 5

# 交付代码白名单：只有这些文件才触发"缺板 + 有代码"的硬规则。
DELIVERY_CODE_NAMES = ("solution.py", "solution.m", "solution_tests.py", "solution_tests.m")

STAGE_CHOICES = ("question", "final")
DEFAULT_STAGE = "final"


def _check_decision_artifacts(root: Path, quality_mode: str) -> dict:
    """决策产物硬门：`final_solution.json` 与 `model_decision.md` 必须存在。

    standard 模式只 warning（保持旧工作区兼容），strict/excellence 判 error。
    """
    mode = (quality_mode or "standard").lower()
    strict = mode in STRICT_MODES
    severity = "error" if strict else "warning"
    missing = [name for name in DECISION_ARTIFACTS if not (root / name).is_file()]
    issues: list[dict] = []
    for name in missing:
        issues.append(
            {
                "code": "missing_decision_artifact",
                "severity": severity,
                "message": f"缺少决策产物 {name}：模型选择与裁决理由必须落盘，否则无法复核 AI 到底选了什么。",
                "file": name,
            }
        )
    passed = not any(issue["severity"] == "error" for issue in issues)
    return {
        "workspace": str(root),
        "mode": mode,
        "passed": passed,
        "warning": any(issue["severity"] == "warning" for issue in issues),
        "checks": [{"name": "decision_artifacts", "passed": not missing, "missing": missing}],
        "issues": issues,
    }


def _resolve_board_root(workspace: Path, explicit: str | None = None) -> Path | None:
    """定位 A 板所在的"题根"目录。

    分小问分支里 A 板永远是**整题一块**，落在题根；而 `--workspace` 常常是
    `questions/qN`。因此 `--stage question` 必须靠这个解析找到题根，否则会在小问
    工作区里永远报 missing_design_board。

    优先用显式 `--board-root`；否则从 workspace 向上最多 5 层找
    `design_board.json`（与 host hook 的上溯层数一致）。找不到返回 None。
    """
    if explicit:
        candidate = Path(explicit).expanduser()
        if not candidate.is_absolute():
            candidate = workspace / candidate
        return candidate.resolve()
    current = workspace
    for _ in range(MAX_BOARD_ROOT_LEVELS + 1):
        if (current / BOARD_ROOT_FILENAME).is_file():
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    return None


def _design_board_gate_a(
    workspace: Path, quality_mode: str, stage: str, board_root: Path | None
) -> dict:
    """A 闸门（框架与探索边界）：**整题一块板**，按 stage 决定校验范围。

    分小问分支的特殊性：一个题只有一块板，`design_board.json` 落在**题根**；
    而 `--stage question` 跑的是 `questions/qN/` 小问工作区，那里本来就不该有板。
    若照主仓库那样无条件挂载，小问工作区的 excellence 会永久红在
    `missing_design_board` 上，等于把"逐问交付、论文手并行写作"这条分支价值直接锁死。

    因此：

    - `stage=final` → 一定校验（题根找到 A 板就用题根，否则用 workspace 自己）；
    - `stage=question` 且题根**有** A 板 → 直接校验题根那块板；
    - `stage=question` 且题根没有 A 板 → 返回"已跳过（scope 在根工作区）"的中性结果。
    """
    target = board_root if board_root is not None else workspace
    if stage == "question" and not (target / BOARD_ROOT_FILENAME).exists():
        return {
            "workspace": str(workspace),
            "board_root": str(target),
            "mode": quality_mode,
            "gate": "a",
            "path": str(target / BOARD_ROOT_FILENAME),
            "passed": True,
            "warning": True,
            "skipped": True,
            "skip_reason": "design_board_gate_scope_root_only",
            "checks": [
                {
                    "name": "design_board",
                    "passed": True,
                    "skipped": True,
                    "note": "小问工作区不校验决策板：一个题只有一块板，位于工作区根目录；--stage final 处强制。",
                }
            ],
            "issues": [],
        }
    return check_design_board(str(target), quality_mode, gate="a")


def _question_dirs(workspace: Path) -> list[tuple[str, Path]]:
    """列出 `questions/<qid>/` 目录（按名字排序），返回 [(qid, 目录)]。"""
    questions_dir = workspace / "questions"
    if not questions_dir.is_dir():
        return []
    found: list[tuple[str, Path]] = []
    for child in sorted(questions_dir.iterdir(), key=lambda item: item.name):
        if child.is_dir():
            found.append((child.name, child))
    return found


def _has_delivery_code(directory: Path) -> bool:
    """该问目录里是否已经有交付代码（solution.* / solution_tests.*）。"""
    return any((directory / name).is_file() for name in DELIVERY_CODE_NAMES)


def _design_board_gate_b(workspace: Path, quality_mode: str, stage: str) -> dict:
    """B 闸门（方案择定）：**每问一块板**，逐问校验。

    - `stage=question`：只校验当前小问工作区自己的
      `questions/qN/design_board_gate_b.json`（键名 `design_board_gate_b`）；
    - `stage=final`：逐问跑 `check_design_board(qN, mode, gate="b")`，键名
      `design_board_gate_b_q1`，全部结果并入总报告。

    哪些小问要跑：**已经有 B 板**的，以及**已经写了交付代码**的（后者交给 checker
    报 "缺板 + 有代码"，这里不重复判严重性）。既没板也没代码的小问跳过，
    避免把"还没做到"当成"做错了"。
    """
    results: dict[str, dict] = {}
    checked: list[str] = []
    skipped: list[str] = []

    if stage == "question":
        results["design_board_gate_b"] = check_design_board(
            str(workspace), quality_mode, gate="b"
        )
        return {
            "workspace": str(workspace),
            "mode": quality_mode,
            "stage": stage,
            "passed": results["design_board_gate_b"]["passed"],
            "results": results,
            "questions": [workspace.name] if workspace.name else [],
            "skipped_questions": [],
            "note": "stage=question：只校验当前小问工作区的 B 板。",
        }

    for qid, qdir in _question_dirs(workspace):
        board = qdir / GATE_B_FILENAME
        if not board.is_file() and not _has_delivery_code(qdir):
            skipped.append(qid)
            continue
        results[f"design_board_gate_b_{qid}"] = check_design_board(
            str(qdir), quality_mode, gate="b"
        )
        checked.append(qid)

    failed = [name for name, item in results.items() if item.get("passed") is False]
    return {
        "workspace": str(workspace),
        "mode": quality_mode,
        "stage": stage,
        "passed": not failed,
        "results": results,
        "questions": checked,
        "skipped_questions": skipped,
        "failed": failed,
        "note": "stage=final：逐问校验 B 板；缺板与「代码早于确认」的严重性由 checker 判定。",
    }


def output(result: dict):
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


# Phase 5 固定产物清单，取自 references/workflow.md 的归档要求。
# 仅用于生成 artifact_completeness 提示，不参与 passed 判定：
# standard 模式必须保持对旧工作区的兼容（warning-only）。
#
# --stage question（按小问分支）：小问工作区在 Phase F/Phase 5 才产生的
# 根目录产物不参与该问的齐备统计；小问阶段图表统一延后，零 PNG 不判失败。
QUESTION_STAGE_EXCLUDED_ARTIFACTS = (
    "figure_style.json",
    "figure_storyboard.md",
    "results/figure_quality_report.json",
    "compliance_record.json",
    "reproducibility_manifest.json",
)

RECOMMENDED_ARTIFACTS = (
    "ambiguity_register.json",
    "assumption_ledger.md",
    "scoring_strategy.md",
    "data_schema.json",
    "symbol_table.json",
    "modeling_state.json",
    "modeling_memory.md",
    "baseline_solution.json",
    "case_retrieval.json",
    "design_board.json",
    "model_selection_audit.json",
    "model_spec.json",
    "optimization_certificate.json",
    "uncertainty_budget.json",
    "validation_profile.json",
    "data_validation.json",
    "statistical_validation.json",
    "solver_strategy.json",
    "ablation_study.json",
    "innovation_register.json",
    "writer_prompt.md",
    "figure_style.json",
    "figure_storyboard.md",
    "results/validation_summary.json",
    "results/figure_quality_report.json",
    "judge_panel_review.json",
    "decision_insights.md",
    "defense_questions.md",
    "compliance_record.json",
    "reproducibility_manifest.json",
)


def _artifact_completeness(root: Path, language: str, required_missing: list, stage: str = "final") -> dict:
    """汇总固定产物齐备情况，让"standard 模式通过"不等于"产物齐全"。"""
    code_name = "solution.m" if language == "matlab" else "solution.py"
    tests_name = "solution_tests.m" if language == "matlab" else "solution_tests.py"
    required = ["problem_brief.md", code_name, "results"]
    recommended = list(RECOMMENDED_ARTIFACTS) + [tests_name]
    if stage == "question":
        recommended = [item for item in recommended if item not in QUESTION_STAGE_EXCLUDED_ARTIFACTS]

    present, missing = [], []
    for rel in recommended:
        if (root / rel).exists():
            present.append(rel)
        else:
            missing.append(rel)
    return {
        "required": required,
        "required_missing": [str(item) for item in required_missing],
        "recommended_total": len(recommended),
        "recommended_present": present,
        "recommended_missing": missing,
        "recommended_present_count": len(present),
        "note": (
            "recommended_missing 不影响 passed。standard 模式只做兼容性自检；"
            "完整交付请使用 --evidence-mode strict --quality-mode excellence。"
        ),
    }


def error(message: str, code: int = 1):
    print(json.dumps({"error": message}, ensure_ascii=False), file=sys.stderr)
    sys.exit(code)


def _safe(name: str, checks: dict, func):
    try:
        checks[name] = func()
    except Exception as exc:
        checks[name] = {"passed": False, "error": str(exc)}
    return checks[name]


def _latex_advisory(model_decision: Path) -> dict:
    """对 model_decision.md 中的 LaTeX 公式做提示性检查。

    该检查只产出 warning：LaTeX 校验是启发式的，不足以作为总控失败依据，
    但此前 validate_latex_file 被导入却从未调用，模型文档里的公式完全没被看过。
    需要判失败时请单独运行 tools/latex_validator.py。
    """
    result = {"passed": True, "warning": False, "advisory_only": True, "issues": []}
    try:
        report = validate_latex_file(str(model_decision))
    except Exception as exc:
        result["warning"] = True
        result["issues"].append({"code": "latex_check_skipped", "severity": "warning", "detail": str(exc)})
        return result

    result.update({
        "total_formulas": report.get("total_formulas", 0),
        "valid": report.get("valid", 0),
        "invalid": report.get("invalid", 0),
        "score": report.get("score"),
    })
    invalid_details = [item for item in report.get("details", []) if not item.get("valid")]
    if invalid_details:
        result["warning"] = True
        for item in invalid_details[:10]:
            result["issues"].append({
                "code": "latex_formula_issue",
                "severity": "warning",
                "line": item.get("line"),
                "detail": "; ".join(str(x) for x in item.get("issues", [])) or "公式可能存在语法问题",
            })
    return result


def run_checks(
    workspace: str,
    language: str = "python",
    timeout: int = 300,
    evidence_mode: str = "standard",
    quality_mode: str = "standard",
    online_source_materials: bool = False,
    stage: str = DEFAULT_STAGE,
    board_root: str | None = None,
) -> dict:
    root = Path(workspace)
    stage = (stage or DEFAULT_STAGE).lower()
    if stage not in STAGE_CHOICES:
        stage = DEFAULT_STAGE
    resolved_board_root = _resolve_board_root(root, board_root)
    brief = root / "problem_brief.md"
    model_decision = root / "model_decision.md"
    code = root / ("solution.m" if language == "matlab" else "solution.py")
    results_dir = root / "results"

    required_paths = [brief, code, results_dir]
    missing = [str(path) for path in required_paths if not path.exists()]
    checks = {
        "required_files": {
            "passed": not missing,
            "missing": missing,
        }
    }

    if code.exists():
        _safe("code_runner", checks, lambda: run_code(str(code), language, timeout, str(root)))

    if results_dir.exists():
        def figure_step():
            result = batch_check(str(results_dir), "*.png")
            if stage == "question" and result.get("total", 0) == 0:
                result["warning"] = True
                result["deferred_figures"] = True
                result["issues"].append(
                    "figures_deferred: 小问阶段图表统一延后到 Phase F 绘制，零 PNG 不判失败"
                )
            return result
        _safe("figure_checker", checks, figure_step)

    if model_decision.exists() and code.exists():
        def consistency_step():
            result = check_formula_consistency(str(model_decision), str(code), language)
            result.setdefault("passed", "error" not in result)
            return result
        _safe("consistency_checker", checks, consistency_step)

    if model_decision.exists():
        checks["latex_advisory"] = _latex_advisory(model_decision)

    if brief.exists() and model_decision.exists():
        _safe("brief_model", checks, lambda: validate_against_brief(str(brief), "model", str(model_decision)))
    if brief.exists() and code.exists():
        _safe("brief_code", checks, lambda: validate_against_brief(str(brief), "code", str(code)))
    if brief.exists() and results_dir.exists():
        _safe("brief_output", checks, lambda: validate_against_brief(str(brief), "output", str(results_dir)))

    _safe("evidence_checker", checks, lambda: check_evidence(str(root), evidence_mode))
    _safe("brief_completeness_checker", checks, lambda: check_brief_completeness(str(root), quality_mode))
    _safe("schema_checker", checks, lambda: check_schema(str(root), quality_mode))
    _safe("model_spec_checker", checks, lambda: check_model_spec(str(root), quality_mode))
    _safe("unit_checker", checks, lambda: check_units(str(root), quality_mode))
    _safe("model_selection_checker", checks, lambda: check_model_selection(str(root), quality_mode))
    _safe("optimization_certificate_checker", checks, lambda: check_optimization_certificate(str(root), quality_mode))
    _safe("uncertainty_budget_checker", checks, lambda: check_uncertainty_budget(str(root), quality_mode))
    _safe("validation_profile_checker", checks, lambda: check_validation_profile(str(root), quality_mode))
    _safe("data_leakage_checker", checks, lambda: check_data_leakage(str(root), quality_mode))
    _safe("statistical_validation_checker", checks, lambda: check_statistical_validation(str(root), quality_mode))
    _safe("robustness_checker", checks, lambda: check_robustness(str(root), quality_mode))
    _safe("figure_auditor", checks, lambda: audit_figures(str(root), quality_mode))
    _safe("manifest_checker", checks, lambda: check_manifest(str(root), quality_mode))
    _safe("source_registry_checker", checks, lambda: check_source_registry(str(Path(__file__).resolve().parents[1]), quality_mode))
    _safe("source_freshness_checker", checks, lambda: check_source_freshness(str(Path(__file__).resolve().parents[1]), quality_mode, online=False))
    if online_source_materials:
        _safe("source_material_reader", checks, lambda: check_source_materials(str(Path(__file__).resolve().parents[1]), quality_mode))
    _safe("decision_artifacts", checks, lambda: _check_decision_artifacts(root, quality_mode))
    # 双闸门：A 板整题一块（题根），B 板每问一块（逐问）。
    _safe(
        "design_board_checker",
        checks,
        lambda: _design_board_gate_a(root, quality_mode, stage, resolved_board_root),
    )
    gate_b_bundle = _safe(
        "design_board_gate_b",
        checks,
        lambda: _design_board_gate_b(root, quality_mode, stage),
    )
    # 逐问结果并入 checks（键名 design_board_gate_b_q1 …），任一问失败即整体失败。
    if isinstance(gate_b_bundle, dict) and isinstance(gate_b_bundle.get("results"), dict):
        for sub_name, sub_result in gate_b_bundle["results"].items():
            checks[sub_name] = sub_result
    _safe("award_readiness_checker", checks, lambda: check_award_readiness(str(root), quality_mode))
    _safe("case_retrieval_checker", checks, lambda: check_case_retrieval(str(root), quality_mode))
    _safe("innovation_checker", checks, lambda: check_innovations(str(root), quality_mode))
    _safe("judge_panel_checker", checks, lambda: check_judge_panel(str(root), quality_mode))
    _safe("compliance_checker", checks, lambda: check_compliance(str(root), quality_mode))
    _safe("writer_prompt_checker", checks, lambda: check_writer_prompt(str(root), quality_mode))

    passed = checks["required_files"]["passed"]
    for name, result in checks.items():
        if name == "required_files":
            continue
        if result.get("success") is False or result.get("passed") is False:
            passed = False
        if name == "figure_checker":
            if result.get("total", 0) == 0:
                # batch_check 对空目录返回 passed_all=False；小问阶段图表延后绘制，零图表不算失败。
                if stage != "question":
                    passed = False
            elif result.get("passed_all") is False:
                passed = False

    completeness = _artifact_completeness(root, language, missing, stage)
    warned = sorted(
        name for name, result in checks.items()
        if isinstance(result, dict) and (result.get("warning") or result.get("issues"))
    )
    if not passed:
        status = "fail"
    elif warned or completeness["recommended_missing"]:
        status = "pass_with_warnings"
    else:
        status = "pass"

    return {
        "workspace": str(root),
        "language": language,
        "evidence_mode": evidence_mode,
        "quality_mode": quality_mode,
        "online_source_materials": online_source_materials,
        "stage": stage,
        "board_root": str(resolved_board_root) if resolved_board_root is not None else None,
        "passed": passed,
        "status": status,
        "warned_checks": warned,
        "artifact_completeness": completeness,
        "checks": checks,
    }


def main():
    parser = argparse.ArgumentParser(description="数学建模交付物总控验证工具")
    parser.add_argument("--workspace", required=True, help="建模工作区")
    parser.add_argument("--language", default="python", choices=["python", "matlab"])
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument(
        "--evidence-mode",
        default="standard",
        choices=["standard", "strict", "hard", "complete", "full"],
        help="standard 兼容旧工作区；strict/hard/complete/full 缺证据即失败",
    )
    parser.add_argument(
        "--quality-mode",
        default="standard",
        choices=["standard", "strict", "hard", "complete", "full", "excellence"],
        help="standard 兼容旧工作区；strict/excellence 要求质量闭环产物完整",
    )
    parser.add_argument(
        "--online-source-materials",
        action="store_true",
        help="显式联网抽检竞赛资料内容；默认关闭，避免普通 CI 受外部网站波动影响。",
    )
    parser.add_argument(
        "--stage",
        default=DEFAULT_STAGE,
        choices=list(STAGE_CHOICES),
        help="question 用于 questions/qN 小问工作区（零图表不判失败、不计 Phase F/5 根产物）；final 用于整题最终交付（默认，与旧行为一致）。",
    )
    parser.add_argument(
        "--board-root",
        default=None,
        help=(
            "A 板（design_board.json）所在的题根目录；默认从 --workspace 向上最多 5 层查找。"
            "--stage question 必须靠它找到整题那块 A 板，否则小问工作区会误报缺板。"
            "B 板是每问一块，仍在 questions/qN/ 下就地校验。"
        ),
    )
    args = parser.parse_args()

    try:
        result = run_checks(
            args.workspace,
            args.language,
            args.timeout,
            args.evidence_mode,
            args.quality_mode,
            args.online_source_materials,
            args.stage,
            args.board_root,
        )
        output(result)
        sys.exit(0 if result["passed"] else 1)
    except Exception as exc:
        error(str(exc))


if __name__ == "__main__":
    main()
