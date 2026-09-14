#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数学建模按小问分支：小问队列确定性管理工具"""

import argparse
import json
import os
import re
import sys
import time
import uuid
from pathlib import Path

try:
    from tools.state_manager import init_state, now_iso
except ImportError:
    from state_manager import init_state, now_iso


QUEUE_FILE = "question_queue.json"
LOCK_TIMEOUT_SECONDS = 10
LOCK_STALE_SECONDS = 60
VALID_STATUSES = {"pending", "in_progress", "completed"}
QUESTION_WORKSPACE_PATTERN = "questions/{qid}"
QUESTION_ARTIFACTS = {
    "modeling_answer": "modeling_answer.md",
    "writer_prompt": "writer_prompt.md",
    "solution": "solution.py",
    "results": "results",
}
ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


def output(result: dict):
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


def error(message: str, code: int = 1):
    print(json.dumps({"error": message}, ensure_ascii=False), file=sys.stderr)
    sys.exit(code)


def workspace_root(workspace: str) -> Path:
    return Path(workspace).resolve()


def queue_path(workspace: str) -> Path:
    return workspace_root(workspace) / QUEUE_FILE


def lock_path(workspace: str) -> Path:
    return Path(str(queue_path(workspace)) + ".lock")


class QueueLock:
    """跨进程文件锁，避免并行工具同时覆盖 question_queue.json。"""

    def __init__(self, workspace: str, timeout: int = LOCK_TIMEOUT_SECONDS):
        self.workspace = workspace
        self.timeout = timeout
        self.path = lock_path(workspace)
        self.fd = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        deadline = time.monotonic() + self.timeout
        payload = f"pid={os.getpid()} time={now_iso()}\n".encode("utf-8")
        while True:
            try:
                self.fd = os.open(str(self.path), os.O_CREAT | os.O_EXCL | os.O_RDWR)
                os.write(self.fd, payload)
                return self
            except (FileExistsError, PermissionError):
                self._remove_stale_lock()
                if time.monotonic() >= deadline:
                    raise TimeoutError(f"等待队列文件锁超时: {self.path}")
                time.sleep(0.05)

    def __exit__(self, exc_type, exc, tb):
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None
        try:
            self.path.unlink()
        except (FileNotFoundError, PermissionError):
            pass

    def _remove_stale_lock(self):
        try:
            age = time.time() - self.path.stat().st_mtime
            if age > LOCK_STALE_SECONDS:
                self.path.unlink()
        except (FileNotFoundError, PermissionError):
            pass


def _atomic_write_json(path: Path, data: dict):
    temp_path = path.with_name(f"{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    temp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temp_path, path)


def load_queue(workspace: str) -> dict:
    path = queue_path(workspace)
    if not path.exists():
        raise FileNotFoundError(f"小问队列不存在: {path}；请先运行 init 或 workflow_runner scaffold --questions")
    return json.loads(path.read_text(encoding="utf-8"))


def save_queue(workspace: str, queue: dict) -> dict:
    queue["updated_at"] = now_iso()
    _atomic_write_json(queue_path(workspace), queue)
    return queue


def validate_question_id(qid: str) -> str:
    if not ID_PATTERN.match(qid or ""):
        raise ValueError(f"非法小问 id: {qid!r}；只允许字母、数字、下划线和连字符")
    return qid


def parse_depends(pairs: list) -> dict:
    """把 ["q2:q1", "q3:q1,q2"] 解析为 {"q2": ["q1"], "q3": ["q1", "q2"]}。"""
    depends = {}
    for pair in pairs or []:
        if ":" not in pair:
            raise ValueError(f"--depends 格式应为 qN:qM 或 qN:qM,qK，收到: {pair}")
        qid, deps_raw = pair.split(":", 1)
        qid = validate_question_id(qid.strip())
        deps = [validate_question_id(d.strip()) for d in deps_raw.split(",") if d.strip()]
        if not deps:
            raise ValueError(f"--depends {pair} 没有声明任何依赖对象")
        depends.setdefault(qid, [])
        for dep in deps:
            if dep not in depends[qid]:
                depends[qid].append(dep)
    return depends


def question_artifacts(qid: str, language: str) -> dict:
    artifacts = dict(QUESTION_ARTIFACTS)
    if language == "matlab":
        artifacts["solution"] = "solution.m"
    base = QUESTION_WORKSPACE_PATTERN.format(qid=qid)
    return {name: f"{base}/{rel}" for name, rel in artifacts.items()}


def scaffold_question_workspace(workspace: str, qid: str, language: str) -> dict:
    """为小问创建迷你工作区骨架：questions/qN/、results/ 与独立 modeling_state.json。"""
    qdir = workspace_root(workspace) / QUESTION_WORKSPACE_PATTERN.format(qid=qid)
    qdir.mkdir(parents=True, exist_ok=True)
    state = init_state(str(qdir), language)
    return {"workspace": str(qdir), "state_initialized": bool(state)}


def init_queue(workspace: str, question_ids: list, depends: dict = None, language: str = "python") -> dict:
    root = workspace_root(workspace)
    root.mkdir(parents=True, exist_ok=True)
    if queue_path(workspace).exists():
        raise FileExistsError(f"小问队列已存在: {queue_path(workspace)}；如需重建请先删除")
    if not question_ids:
        raise ValueError("至少需要一个小问 id")
    ids = [validate_question_id(q.strip()) for q in question_ids if q.strip()]
    if len(ids) != len(set(ids)):
        raise ValueError(f"小问 id 重复: {question_ids}")
    depends = depends or {}
    order_index = {qid: rank for rank, qid in enumerate(ids)}
    for qid, deps in depends.items():
        if qid not in order_index:
            raise ValueError(f"--depends 声明了未知小问: {qid}")
        for dep in deps:
            if dep not in order_index:
                raise ValueError(f"小问 {qid} 依赖了未知小问: {dep}")
            if order_index[dep] >= order_index[qid]:
                raise ValueError(f"小问 {qid} 的依赖 {dep} 必须排在它之前（不允许循环或前向依赖）")
        if qid in deps:
            raise ValueError(f"小问 {qid} 不能依赖自身")

    questions = []
    for qid in ids:
        questions.append({
            "id": qid,
            "title": qid,
            "status": "pending",
            "depends_on": list(depends.get(qid, [])),
            "workspace": QUESTION_WORKSPACE_PATTERN.format(qid=qid),
            "artifacts": question_artifacts(qid, language),
            "judge_overall_score": None,
            "completed_at": None,
        })

    queue = {
        "schema_version": 1,
        "workspace": str(root),
        "language": language,
        "questions": questions,
        "updated_at": now_iso(),
    }
    with QueueLock(workspace):
        scaffolded = [scaffold_question_workspace(workspace, qid, language) for qid in ids]
        save_queue(workspace, queue)
    queue["scaffolded"] = scaffolded
    queue["action"] = "init"
    return queue


def _find_question(queue: dict, qid: str) -> dict:
    for question in queue.get("questions", []):
        if question.get("id") == qid:
            return question
    raise ValueError(f"队列中不存在小问: {qid}")


def _completed_ids(queue: dict) -> set:
    return {q["id"] for q in queue.get("questions", []) if q.get("status") == "completed"}


def next_question(workspace: str) -> dict:
    with QueueLock(workspace):
        queue = load_queue(workspace)
        in_progress = [q["id"] for q in queue["questions"] if q.get("status") == "in_progress"]
        if in_progress:
            raise ValueError(f"小问 {', '.join(in_progress)} 仍在进行中；小问严格串行，请先 complete 后再取下一问")
        completed = _completed_ids(queue)
        for question in queue["questions"]:
            if question.get("status") != "pending":
                continue
            missing = [dep for dep in question.get("depends_on", []) if dep not in completed]
            if missing:
                continue
            question["status"] = "in_progress"
            save_queue(workspace, queue)
            return {
                "action": "next",
                "question": question,
                "queue_finished": False,
            }
        if all(q.get("status") == "completed" for q in queue["questions"]):
            return {
                "action": "next",
                "question": None,
                "queue_finished": True,
                "message": "全部小问已完成，进入 Phase F 统一图表绘制阶段。",
            }
        blocked = {
            q["id"]: [dep for dep in q.get("depends_on", []) if dep not in completed]
            for q in queue["questions"]
            if q.get("status") == "pending"
        }
        raise ValueError(f"没有可推进的小问；依赖未满足: {blocked}")


def complete_question(workspace: str, qid: str, score=None) -> dict:
    with QueueLock(workspace):
        queue = load_queue(workspace)
        question = _find_question(queue, qid)
        if question.get("status") != "in_progress":
            raise ValueError(f"小问 {qid} 当前状态为 {question.get('status')}；只能 complete 处于 in_progress 的小问")
        question["status"] = "completed"
        question["judge_overall_score"] = score
        question["completed_at"] = now_iso()
        question["artifacts"] = question_artifacts(qid, queue.get("language", "python"))
        save_queue(workspace, queue)
    remaining = [q["id"] for q in queue["questions"] if q.get("status") == "pending"]
    return {
        "action": "complete",
        "question": question,
        "remaining_pending": remaining,
        "queue_finished": not remaining,
        "message": (
            f"第 {qid} 小问已登记完成；"
            + (f"下一小问：{remaining[0]}。" if remaining else "全部小问完成，进入 Phase F 统一图表绘制阶段。")
        ),
    }


def queue_status(workspace: str) -> dict:
    queue = load_queue(workspace)
    questions = queue.get("questions", [])
    summary = {"pending": 0, "in_progress": 0, "completed": 0}
    for question in questions:
        status = question.get("status")
        if status in summary:
            summary[status] += 1
    return {
        "action": "status",
        "workspace": queue.get("workspace"),
        "language": queue.get("language"),
        "total": len(questions),
        "summary": summary,
        "queue_finished": bool(questions) and summary["completed"] == len(questions),
        "questions": [
            {
                "id": q.get("id"),
                "title": q.get("title"),
                "status": q.get("status"),
                "depends_on": q.get("depends_on", []),
                "judge_overall_score": q.get("judge_overall_score"),
                "completed_at": q.get("completed_at"),
                "artifacts": q.get("artifacts", {}),
            }
            for q in questions
        ],
        "updated_at": queue.get("updated_at"),
    }


def main():
    parser = argparse.ArgumentParser(description="数学建模按小问分支：小问队列管理工具")
    subparsers = parser.add_subparsers(dest="action", help="可用操作")

    p_init = subparsers.add_parser("init", help="初始化小问队列")
    p_init.add_argument("--workspace", required=True)
    p_init.add_argument("--questions", required=True, help="逗号分隔的小问 id 列表，顺序即求解顺序，如 q1,q2,q3")
    p_init.add_argument("--depends", action="append", default=[], help="依赖声明，格式 qN:qM 或 qN:qM,qK，可重复")
    p_init.add_argument("--language", default="python", choices=["python", "matlab"])

    p_next = subparsers.add_parser("next", help="取出下一个待求解小问")
    p_next.add_argument("--workspace", required=True)

    p_complete = subparsers.add_parser("complete", help="登记小问完成")
    p_complete.add_argument("--workspace", required=True)
    p_complete.add_argument("--question", required=True)
    p_complete.add_argument("--score", type=float, default=None, help="该问 chair judge 总分")

    p_status = subparsers.add_parser("status", help="查看队列进度")
    p_status.add_argument("--workspace", required=True)

    args = parser.parse_args()
    if not args.action:
        parser.print_help()
        sys.exit(1)

    try:
        if args.action == "init":
            question_ids = [q.strip() for q in args.questions.split(",") if q.strip()]
            output(init_queue(args.workspace, question_ids, parse_depends(args.depends), args.language))
        elif args.action == "next":
            output(next_question(args.workspace))
        elif args.action == "complete":
            output(complete_question(args.workspace, args.question, args.score))
        elif args.action == "status":
            output(queue_status(args.workspace))
    except Exception as exc:
        error(str(exc))


if __name__ == "__main__":
    main()
