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
