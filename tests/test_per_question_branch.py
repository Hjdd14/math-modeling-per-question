#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""按小问分别交付分支：小问队列、scaffold --questions 与 pipeline_check --stage 测试"""

import json
import os
import shutil

import pytest

from tools import pipeline_check, question_queue, workflow_runner


SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEST_DATA = os.path.join(SKILL_DIR, "tests", "test_data")


def make_queue(tmp_path, questions="q1,q2,q3", depends=None):
    question_ids = [q.strip() for q in questions.split(",") if q.strip()]
    return question_queue.init_queue(
        str(tmp_path),
        question_ids,
        question_queue.parse_depends(depends or []),
        "python",
    )


def test_init_creates_queue_and_question_workspaces(tmp_path):
    queue = make_queue(tmp_path)

    assert (tmp_path / "question_queue.json").exists()
    assert [q["id"] for q in queue["questions"]] == ["q1", "q2", "q3"]
    assert all(q["status"] == "pending" for q in queue["questions"])
    for qid in ["q1", "q2", "q3"]:
        assert (tmp_path / "questions" / qid / "results").is_dir()
        assert (tmp_path / "questions" / qid / "modeling_state.json").exists()
    assert queue["questions"][0]["artifacts"]["modeling_answer"] == "questions/q1/modeling_answer.md"


def test_init_rejects_duplicate_and_invalid_ids(tmp_path):
    with pytest.raises(ValueError):
        make_queue(tmp_path, "q1,q1")

    with pytest.raises(ValueError):
        make_queue(tmp_path / "other", "../q1")

    make_queue(tmp_path / "third")
    with pytest.raises(FileExistsError):
        make_queue(tmp_path / "third")


def test_depends_must_point_backwards(tmp_path):
    with pytest.raises(ValueError):
        make_queue(tmp_path, "q1,q2", ["q1:q2"])

    with pytest.raises(ValueError):
        make_queue(tmp_path / "second", "q1,q2", ["q2:q9"])

    queue = make_queue(tmp_path / "third", "q1,q2", ["q2:q1"])
    assert queue["questions"][1]["depends_on"] == ["q1"]


def test_queue_is_strictly_serial(tmp_path):
    make_queue(tmp_path)

    first = question_queue.next_question(str(tmp_path))
    assert first["question"]["id"] == "q1"
    assert first["question"]["status"] == "in_progress"
    assert first["queue_finished"] is False

    with pytest.raises(ValueError):
        question_queue.next_question(str(tmp_path))


def test_complete_advances_queue_and_finishes(tmp_path):
    make_queue(tmp_path)

    with pytest.raises(ValueError):
        question_queue.complete_question(str(tmp_path), "q1")

    question_queue.next_question(str(tmp_path))
    done = question_queue.complete_question(str(tmp_path), "q1", score=87)
    assert done["question"]["status"] == "completed"
    assert done["question"]["judge_overall_score"] == 87
    assert done["question"]["completed_at"]
    assert done["remaining_pending"] == ["q2", "q3"]
    assert done["queue_finished"] is False

    question_queue.next_question(str(tmp_path))
    question_queue.complete_question(str(tmp_path), "q2", score=85)
    question_queue.next_question(str(tmp_path))
    final = question_queue.complete_question(str(tmp_path), "q3", score=90)
    assert final["queue_finished"] is True

    finished = question_queue.next_question(str(tmp_path))
    assert finished["queue_finished"] is True
    assert finished["question"] is None


def test_next_skips_questions_with_unmet_dependencies(tmp_path):
    make_queue(tmp_path, "q1,q2,q3", ["q3:q1"])

    # q3 依赖 q1，因此在 q1 完成前只能推进 q1、q2
    assert question_queue.next_question(str(tmp_path))["question"]["id"] == "q1"
    question_queue.complete_question(str(tmp_path), "q1")
    assert question_queue.next_question(str(tmp_path))["question"]["id"] == "q2"
    question_queue.complete_question(str(tmp_path), "q2")
    assert question_queue.next_question(str(tmp_path))["question"]["id"] == "q3"


def test_status_summarizes_progress(tmp_path):
    make_queue(tmp_path)
    question_queue.next_question(str(tmp_path))
    question_queue.complete_question(str(tmp_path), "q1", score=88)

    status = question_queue.queue_status(str(tmp_path))
    assert status["total"] == 3
    assert status["summary"] == {"pending": 2, "in_progress": 0, "completed": 1}
    assert status["queue_finished"] is False
    assert status["questions"][0]["judge_overall_score"] == 88


def test_status_requires_existing_queue(tmp_path):
    with pytest.raises(FileNotFoundError):
        question_queue.queue_status(str(tmp_path / "missing"))


def test_scaffold_with_questions_builds_queue(tmp_path):
    result = workflow_runner.scaffold_workspace(str(tmp_path / "ws"), "python", "q1,q2")

    assert (tmp_path / "ws" / "question_queue.json").exists()
    assert (tmp_path / "ws" / "questions" / "q1" / "results").is_dir()
    assert (tmp_path / "ws" / "questions" / "q2" / "modeling_state.json").exists()
    assert result["question_queue"]["questions"] == ["q1", "q2"]
    assert "小问队列" in result["message"]


def test_scaffold_without_questions_keeps_original_behaviour(tmp_path):
    result = workflow_runner.scaffold_workspace(str(tmp_path / "ws"), "python")

    assert not (tmp_path / "ws" / "question_queue.json").exists()
    assert (tmp_path / "ws" / "results").is_dir()
    assert (tmp_path / "ws" / "modeling_memory.md").exists()
    assert "question_queue" not in result


def copy_workspace_without_figures(tmp_path):
    for name in ["problem_brief.md", "model_decision.md", "writer_prompt.md", "solution.py"]:
        shutil.copy2(os.path.join(TEST_DATA, name), tmp_path / name)
    shutil.copytree(os.path.join(TEST_DATA, "results"), tmp_path / "results")
    for png in (tmp_path / "results").glob("*.png"):
        png.unlink()
    return tmp_path


def test_pipeline_check_question_stage_defers_figures(tmp_path):
    workspace = copy_workspace_without_figures(tmp_path)

    result = pipeline_check.run_checks(str(workspace), "python", stage="question")

    assert result["stage"] == "question"
    assert result["checks"]["figure_checker"]["total"] == 0
    assert result["checks"]["figure_checker"]["warning"] is True
    assert result["checks"]["figure_checker"]["deferred_figures"] is True
    assert any("figures_deferred" in issue for issue in result["checks"]["figure_checker"]["issues"])
    assert result["passed"] is True


def test_pipeline_check_final_stage_still_fails_without_figures(tmp_path):
    workspace = copy_workspace_without_figures(tmp_path)

    result = pipeline_check.run_checks(str(workspace), "python", stage="final")

    assert result["stage"] == "final"
    assert result["checks"]["figure_checker"]["total"] == 0
    assert result["passed"] is False


def test_question_stage_skips_root_phase_products_in_completeness(tmp_path):
    workspace = copy_workspace_without_figures(tmp_path)

    result = pipeline_check.run_checks(str(workspace), "python", stage="question")
    missing = result["artifact_completeness"]["recommended_missing"]

    for name in pipeline_check.QUESTION_STAGE_EXCLUDED_ARTIFACTS:
        assert name not in missing
    assert "model_spec.json" in missing
    assert "judge_panel_review.json" in missing


def test_final_stage_counts_root_phase_products(tmp_path):
    workspace = copy_workspace_without_figures(tmp_path)

    result = pipeline_check.run_checks(str(workspace), "python", stage="final")
    missing = result["artifact_completeness"]["recommended_missing"]

    assert "compliance_record.json" in missing
    assert "figure_style.json" in missing


def test_question_queue_json_matches_documented_schema(tmp_path):
    make_queue(tmp_path, "q1,q2", ["q2:q1"])
    payload = json.loads((tmp_path / "question_queue.json").read_text(encoding="utf-8"))

    assert payload["schema_version"] == 1
    assert payload["language"] == "python"
    assert payload["updated_at"]
    for question in payload["questions"]:
        assert {"id", "title", "status", "depends_on", "workspace", "artifacts", "judge_overall_score", "completed_at"} <= set(question)
        assert question["workspace"].startswith("questions/")

# ---------------------------------------------------------------------------
# 设计闸门在分小问分支上的 4 处专属适配（A1–A4）
# 这些用例锁住"照抄主仓库会做错"的地方，改动前先读 docs/DESIGN_GATE_PLAN.md §21
# ---------------------------------------------------------------------------

def _board_module():
    from tools import design_board

    return design_board


def _board_checker():
    from tools import design_board_checker

    return design_board_checker


def make_board_with_questions(question_ids, option_names=("整数规划", "贪心启发式")):
    """一块板、每题一个 entry；候选名与审计对得上。"""
    options = [
        {
            "id": f"O{i + 1}",
            "name": name,
            "tier": "recommended" if i == 0 else "alternative",
            "rationale": f"{name} 的理由",
            "source_ref": {"type": "method_card", "ref": f"OPT-0{i + 1}", "tier": "tier_a", "verified": True},
            "complexity": "O(1)",
            "dependencies": [],
            "risk": "无",
            "mini_trial": {"sample": "全量", "output": {"objective": 100 + i}, "seconds": 0.001},
        }
        for i, name in enumerate(option_names)
    ]
    return {
        "schema_version": 1,
        "board_id": "b-test-per-question",
        "language": "python",
        "created_at": "2026-06-28T10:00:00+00:00",
        "revision": 1,
        "problem_summary": {"title": "分小问测试题", "questions": list(question_ids), "key_ambiguities": []},
        "mindmap": {"format": "mermaid", "source": "graph LR\n  P[题目] --> Q1[q1]"},
        "questions": [
            {
                "id": qid,
                "goal": f"{qid} 的目标",
                "options": [dict(o) for o in options],
                "user_choice": "O1",
                "user_locked": False,
                "user_comment": "",
                "confirmed": False,
            }
            for qid in question_ids
        ],
        "pending_decisions": [],
        "no_change_rounds": 2,
    }


def seed_confirmed(workspace, question_ids, confirmed_at="2026-06-28T12:00:00+00:00"):
    """落地一份"已确认"的板，哈希与确认码都用权威实现算。"""
    module = _board_module()
    board = make_board_with_questions(question_ids)
    board.update(
        confirmed=True,
        confirmed_at=confirmed_at,
        confirmed_by="user",
        receipt_origin="browser-submit",
        confirm_attested=True,
    )
    for question in board["questions"]:
        question["confirmed"] = True
    sha = module.compute_board_sha256(board)
    board["board_sha256"] = sha
    board["confirm_code"] = sha[:4].upper()
    path = workspace / "design_board.json"
    path.write_text(json.dumps(board, ensure_ascii=False, indent=2), encoding="utf-8")
    rounds = workspace / "design_rounds"
    rounds.mkdir(exist_ok=True)
    for index in (1, 2):
        (rounds / f"round_{index:03d}.json").write_text(
            json.dumps(
                {
                    "round": index,
                    "at": f"2026-06-28T1{index}:00:00+00:00",
                    "board_id": board["board_id"],
                    "board_sha256": sha,
                    "user_edited": False,
                    "changes": [],
                    "receipt_origin": "browser-submit",
                    "receipt_nonce": f"n{index}",
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    return board


def test_timeline_covers_question_workspaces(tmp_path):
    """A1：时间线必须扫 questions/qN/，否则分支上这条防线完全失效。"""
    checker = _board_checker()
    board = seed_confirmed(tmp_path, ["q1"])
    q1 = tmp_path / "questions" / "q1"
    (q1 / "results").mkdir(parents=True)
    (q1 / "solution.py").write_text("print(1)\n", encoding="utf-8")
    (q1 / "results" / "output.csv").write_text("a,b\n1,2\n", encoding="utf-8")

    # 代码 mtime 回退到确认之前 1 天
    stale = 1782648000 - 86400  # confirmed_at 对应的 epoch 再减一天
    import os as _os

    _os.utime(q1 / "solution.py", (stale, stale))
    _os.utime(q1 / "results" / "output.csv", (stale, stale))

    result = checker.check_design_board(str(tmp_path), "excellence")

    assert result["passed"] is False
    codes = {issue["code"] for issue in result["issues"]}
    assert "code_written_before_confirm" in codes
    messages = " ".join(str(issue.get("message", "")) for issue in result["issues"])
    assert "questions/q1/solution.py" in messages, "issue 必须指出是哪个小问的哪个文件"


def test_cross_audit_reads_per_question_audit(tmp_path):
    """A2：交叉校验按题读 questions/qN/model_selection_audit.json。"""
    checker = _board_checker()
    seed_confirmed(tmp_path, ["q1"])
    q1 = tmp_path / "questions" / "q1"
    q1.mkdir(parents=True)
    write_audit = {
        "candidates": [
            {"name": "整数规划", "score": 0.9, "rejection_reason": "", "evidence": ["oracle"]},
            {"name": "贪心启发式", "score": 0.7, "rejection_reason": "无最优性保证", "evidence": ["baseline"]},
        ],
        "final_selection": {"name": "整数规划", "score": 0.9, "evidence": ["gap=0"]},
    }
    (q1 / "model_selection_audit.json").write_text(
        json.dumps(write_audit, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    ok = checker.check_design_board(str(tmp_path), "excellence")
    assert ok["passed"] is True
    layouts = [c.get("layout") for c in ok["checks"] if c.get("name") == "board_audit_candidates"]
    assert "per_question" in layouts

    # 把审计的最终选择改成另一个候选 → 必须对不上账
    write_audit["final_selection"]["name"] = "贪心启发式"
    (q1 / "model_selection_audit.json").write_text(
        json.dumps(write_audit, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    bad = checker.check_design_board(str(tmp_path), "excellence")
    assert bad["passed"] is False
    assert "board_audit_selection_mismatch" in {issue["code"] for issue in bad["issues"]}


def test_missing_per_question_audit_is_pending_not_error(tmp_path):
    """A2：确认时小问审计还没产出（Phase 1-Q 才产）→ pending warning，不阻断。"""
    checker = _board_checker()
    seed_confirmed(tmp_path, ["q1", "q2"])

    result = checker.check_design_board(str(tmp_path), "excellence")

    codes = {issue["code"] for issue in result["issues"]}
    assert "board_audit_pending" in codes
    assert "board_audit_missing" not in codes
    assert result["passed"] is True, "确认阶段不因为审计未产出而失败"


def test_question_stage_skips_design_board_without_board(tmp_path):
    """A3：--stage question 在小问工作区没有板时必须跳过，不能误伤逐问交付。"""
    workspace = tmp_path / "questions" / "q1"
    workspace.mkdir(parents=True)
    (workspace / "problem_brief.md").write_text("# q1\n", encoding="utf-8")

    result = pipeline_check.run_checks(
        str(workspace), "python", evidence_mode="strict", quality_mode="excellence", stage="question"
    )

    gate = result["checks"]["design_board_checker"]
    assert gate.get("skipped") is True
    assert gate.get("skip_reason") == "design_board_gate_scope_root_only"
    assert gate["passed"] is True


def test_final_stage_requires_design_board(tmp_path):
    """A3：--stage final 必须强制校验决策板，最终交付不能被绕开。"""
    workspace = tmp_path
    (workspace / "problem_brief.md").write_text("# 题目\n", encoding="utf-8")

    result = pipeline_check.run_checks(
        str(workspace), "python", evidence_mode="strict", quality_mode="excellence", stage="final"
    )

    gate = result["checks"]["design_board_checker"]
    assert gate.get("skipped") is not True
    assert gate["passed"] is False
    assert "missing_design_board" in {issue["code"] for issue in gate["issues"]}


def test_board_question_ids_must_match_queue(tmp_path):
    """A4 配套：板里的 question id 必须与 question_queue.json 对得上，防止板漂移。"""
    make_queue(tmp_path, questions="q1,q2")
    board = seed_confirmed(tmp_path, ["q1", "q2"])

    queue = json.loads((tmp_path / "question_queue.json").read_text(encoding="utf-8"))
    queue_ids = [item["id"] for item in queue["questions"]]
    board_ids = [item["id"] for item in board["questions"]]

    assert board_ids == queue_ids, "板的小问清单必须与队列一致，否则用户确认的和实际交付的不是同一组小问"
