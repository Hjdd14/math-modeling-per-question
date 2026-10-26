#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""旧工作区迁移：为 Phase 0 之前就存在的项目补出最小可用的 design_board.json 骨架。

背景
----
新增的"设计闸门"要求工作区里存在已确认的 ``design_board.json``，否则
``tools/design_board_checker.py`` 在 excellence 模式判 error。旧项目在升级 skill 后
会突然全部变红，因此本工具负责把已有产物（``problem_brief.md``、
``model_selection_audit.json``）翻译成一份**未确认**的板骨架，让用户能接着走
``render → 补全 → ingest → confirm`` 流程。

行为约定
--------
1. **绝不覆盖**：``design_board.json`` 已存在时直接报错退出（两个模式都一样），
   提示"已存在，无需迁移"。
2. **绝不伪造确认**：不写 ``confirmed`` / ``confirm_code`` / ``confirmed_at`` /
   ``confirmed_by`` / ``receipt_*``，确认必须由用户自己输入确认码完成。
3. **可被权威校验加载**：写盘前用 ``tools/design_board.py`` 的 ``validate_board``
   （含 ``mindmap.source``）自检，写盘后再用 ``load_board`` 读回验证一次。
4. **占位值必须可读**：每个候选的 ``rationale`` / ``risk`` / ``source_ref`` /
   ``mini_trial`` 都带占位文本，且 ``source_ref.verified = False`` +
   ``unverified_reason = "迁移生成，未核验来源"``，checker 会据此给出可读待办，
   而不是让人以为来源已经核验过。
5. 默认 dry-run，只打印将要写入的 JSON；``--apply`` 才落盘。

用法
----
    python tools/migrate_workspace.py --workspace .            # 预览
    python tools/migrate_workspace.py --workspace . --apply    # 写入骨架

推断规则
--------
- 题目：``problem_brief.md`` 存在时取首个非空行（去掉行首 Markdown 标题记号），
  截断到 120 字作为 ``problem_summary.title``；否则用 ``"（迁移占位，请补充）"``。
- 候选：``model_selection_audit.json`` 存在时把 ``candidates[].name`` 依次转成
  options，``final_selection.name`` 对应的那个标 ``recommended``，其余标
  ``alternative``；候选不足 2 个时补占位候选，保证"推荐 + 备选"的基本形态。
- 两者都没有：生成 1 个空题 ``Q1`` 带 2 个占位候选（``待补充候选 A`` / ``B``）。

本工具零第三方依赖，只读工作区已有产物，不做任何建模推理。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


BOARD_FILE = "design_board.json"
BRIEF_FILE = "problem_brief.md"
AUDIT_FILE = "model_selection_audit.json"
# 分小问分支：小问清单与每问工作区
QUEUE_FILE = "question_queue.json"
QUESTIONS_DIR = "questions"
TITLE_LIMIT = 120
PLACEHOLDER_TITLE = "（迁移占位，请补充）"
PLACEHOLDER_OPTION_NAMES = ("待补充候选 A", "待补充候选 B")
UNVERIFIED_REASON = "迁移生成，未核验来源"
MIN_OPTIONS = 2
GOAL_PLACEHOLDER = "（迁移占位）请补充该小问的目标、输入输出与判定标准。"
RATIONALE_PLACEHOLDER = "（迁移占位）请补充选择该候选的理由：为什么它比其它候选更适合本题。"
RISK_PLACEHOLDER = "（迁移占位）请补充该候选的主要风险：什么条件下会失败、假设被破坏后会发生什么。"
COMPLEXITY_PLACEHOLDER = "（迁移占位）未评估，请补充时间复杂度与空间复杂度。"
TRIAL_SAMPLE_PLACEHOLDER = "（迁移占位）未做试算，请用真实数据跑一遍最小可行样例。"
TRIAL_REPRODUCE_PLACEHOLDER = "（迁移占位）请补充复跑命令，例如 python solution.py --sample 20"
NEXT_STEP_RENDER = (
    "渲染决策板：python tools/design_board.py render --workspace . "
    "（生成 design_board.md，并在板顶写出 4 位确认码）"
)
NEXT_STEP_FILL = (
    "补全占位项：把 design_board.md 里标了「待补充 / 迁移占位」的题目、候选、理由、"
    "风险、来源与试算换成真实内容，然后重新 render"
)
NEXT_STEP_CONFIRM = (
    "走确认流程：按回执格式填写 submission.json 后运行 "
    "python tools/design_board.py ingest --workspace . --from submission.json；"
    "连续两轮无修改后运行 python tools/design_board.py confirm --workspace . --apply 输入确认码"
)


def output(result: dict):
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


def error(message: str, code: int = 1):
    print(json.dumps({"error": message}, ensure_ascii=False), file=sys.stderr)
    sys.exit(code)


def _load_board_module():
    """按"包内导入 → 同目录导入"两种方式加载权威校验实现。

    直接 `python tools/migrate_workspace.py` 运行时 ``sys.path[0]`` 是 tools 目录，
    而 `python -m pytest` 时是仓库根目录；两种入口都要能用同一个 ``design_board``。
    """
    import importlib

    for module_name in ("tools.design_board", "design_board"):
        try:
            return importlib.import_module(module_name)
        except ImportError:
            continue
    return None


# ---------------------------------------------------------------------------
# 文本与推断辅助
# ---------------------------------------------------------------------------


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _truncate(text: str, limit: int = TITLE_LIMIT) -> str:
    """截断到 limit 字（含省略号），用于标题这种不该无限长的字段。"""
    text = " ".join(str(text).split())
    if len(text) <= limit:
        return text
    return text[: max(limit - 1, 1)].rstrip() + "…"


def _strip_markdown_heading(line: str) -> str:
    """去掉行首的 Markdown 标题/引用记号，留下真正的标题文本。"""
    text = line.strip()
    text = re.sub(r"^#{1,6}\s*", "", text)
    text = re.sub(r"^[>*\-\s]+", "", text)
    return text.strip()


def _read_text(path: Path) -> str:
    """宽松读文本：编码异常不致命，旧工作区里什么编码都可能出现。"""
    return path.read_text(encoding="utf-8-sig", errors="replace")


def _infer_title(root: Path) -> tuple[str, str]:
    """从 problem_brief.md 取标题；返回 (标题, 来源说明)。"""
    brief = root / BRIEF_FILE
    if brief.is_file():
        try:
            text = _read_text(brief)
        except OSError:
            text = ""
        for line in text.splitlines():
            title = _strip_markdown_heading(line)
            if title:
                return _truncate(title), f"{BRIEF_FILE} 的首个非空行"
    return PLACEHOLDER_TITLE, f"未找到可用的 {BRIEF_FILE}，使用迁移占位标题"


def _normalize_name(name) -> str:
    text = str(name or "").strip().lower()
    text = re.sub(r"[（(].*?[)）]", "", text)
    return re.sub(r"[\s\-_]+", "", text)


def _infer_candidates(root: Path) -> tuple[list[dict], str | None, str | None, list[str]]:
    """从 model_selection_audit.json 取候选名单。

    返回 ``(candidates, final_name, 来源说明, warnings)``；candidates 已去重，
    每项至少含 ``name`` 与可选的 ``score`` / ``evidence`` / ``source_index``。
    """
    audit_path = root / AUDIT_FILE
    if not audit_path.is_file():
        return [], None, None, []

    try:
        payload = json.loads(_read_text(audit_path))
    except (ValueError, OSError):
        return [], None, None, [f"{AUDIT_FILE} 不是合法 JSON，已回退到占位候选。"]

    if not isinstance(payload, dict):
        return [], None, None, [f"{AUDIT_FILE} 顶层不是 JSON 对象，已回退到占位候选。"]

    warnings: list[str] = []
    raw_candidates = payload.get("candidates")
    raw_candidates = raw_candidates if isinstance(raw_candidates, list) else []
    candidates: list[dict] = []
    seen: set[str] = set()
    for index, item in enumerate(raw_candidates):
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        if not isinstance(name, str) or not name.strip():
            continue
        name = name.strip()
        key = _normalize_name(name)
        if key in seen:
            warnings.append(f"审计里出现同名候选 {name!r}，迁移时只保留第一次出现的那个。")
            continue
        seen.add(key)
        candidates.append(
            {
                "name": name,
                "score": item.get("score"),
                "evidence": item.get("evidence"),
                "source_index": index,
            }
        )

    final_name = None
    final_selection = payload.get("final_selection")
    if isinstance(final_selection, dict):
        value = final_selection.get("name")
        if isinstance(value, str) and value.strip():
            final_name = value.strip()

    if not candidates:
        warnings.append(f"{AUDIT_FILE} 里没有可用的 candidates[].name，已回退到占位候选。")
        return [], final_name, f"{AUDIT_FILE}（未读到候选）", warnings
    if final_name is None:
        warnings.append("审计缺少 final_selection.name，所有候选只能标 alternative，请人工指定推荐项。")
    return candidates, final_name, AUDIT_FILE, warnings


# ---------------------------------------------------------------------------
# 板骨架构造
# ---------------------------------------------------------------------------


def _source_ref(kind: str, ref: str, note: str) -> dict:
    """迁移生成的来源登记：一律未核验，避免让人误以为已经查过出处。"""
    return {
        "type": kind,
        "ref": ref,
        "verified": False,
        "unverified_reason": UNVERIFIED_REASON,
        "note": note,
    }


def _mini_trial_placeholder() -> dict:
    return {
        "sample": TRIAL_SAMPLE_PLACEHOLDER,
        "output": {"status": "not_run"},
        "reproduce_cmd": TRIAL_REPRODUCE_PLACEHOLDER,
    }


def _audit_option(index: int, candidate: dict, recommended: bool) -> dict:
    """把一个审计候选翻译成板里的 option，理由字段带上可读的溯源信息。"""
    name = candidate["name"]
    source_index = candidate.get("source_index", index)
    rationale_parts = [f"（迁移占位）来自 {AUDIT_FILE} candidates[{source_index}] 的候选「{name}」"]
    score = candidate.get("score")
    if isinstance(score, (int, float)) and not isinstance(score, bool):
        rationale_parts.append(f"审计得分 {score:g}")
    evidence = candidate.get("evidence")
    if isinstance(evidence, list):
        evidence_text = "、".join(str(item) for item in evidence if str(item).strip())
        if evidence_text:
            rationale_parts.append(f"证据 {evidence_text}")
    rationale = "；".join(rationale_parts) + "。请补充选择理由与适用条件。"
    return {
        "id": f"O{index + 1}",
        "name": name,
        "tier": "recommended" if recommended else "alternative",
        "rationale": rationale,
        "complexity": COMPLEXITY_PLACEHOLDER,
        "dependencies": [],
        "risk": RISK_PLACEHOLDER,
        "source_ref": _source_ref(
            "audit",
            f"{AUDIT_FILE}#candidates[{source_index}]",
            "迁移脚本按审计候选名生成，未回查原始文献 / 方法卡编号",
        ),
        "mini_trial": _mini_trial_placeholder(),
    }


def _placeholder_option(index: int, name: str) -> dict:
    return {
        "id": f"O{index + 1}",
        "name": name,
        "tier": "alternative",
        "rationale": RATIONALE_PLACEHOLDER,
        "complexity": COMPLEXITY_PLACEHOLDER,
        "dependencies": [],
        "risk": RISK_PLACEHOLDER,
        "source_ref": _source_ref(
            "placeholder",
            "待补充（例如 references/award_playbook.md#方法卡编号）",
            "迁移脚本生成的占位候选，没有对应的方法来源",
        ),
        "mini_trial": _mini_trial_placeholder(),
    }


def _mermaid_label(text: str, limit: int = 40) -> str:
    """把任意文本塞进 mermaid 的 `[label]` 里：转义方括号/引号并截断。"""
    label = " ".join(str(text or "").split())
    # 中文全角替换既保留可读性，又不会破坏 mermaid 的节点语法。
    for raw, safe in (("[", "［"), ("]", "］"), ("(", "（"), (")", "）"), ("{", "｛"), ("}", "｝"), ('"', "'")):
        label = label.replace(raw, safe)
    return _truncate(label, limit) or "待补充"


def _build_mindmap(title: str, options: list[dict]) -> str:
    question_label = "Q1 迁移占位小问"
    lines = [
        "graph LR",
        f"  P[{_mermaid_label(title, 30)}] --> Q1[{question_label}]",
    ]
    for option in options:
        lines.append(
            f"  Q1 --> {option['id']}[{option['id']} {_mermaid_label(option.get('name'), 30)}]"
        )
    return "\n".join(lines)


def _build_question(options: list[dict], audit_used: bool, *, question_id: str = "Q1", goal: str = "") -> dict:
    resolved_goal = goal or (
        "（迁移占位）请确认该小问的目标：从现有审计候选里选定最终模型，并说明适用条件。"
        if audit_used
        else GOAL_PLACEHOLDER
    )
    return {
        "id": question_id,
        "goal": resolved_goal,
        "options": options,
        # 用户选择与确认一律留空：迁移不替用户做决定。
        "user_choice": None,
        "user_locked": False,
        "user_comment": "",
    }


def _bigrams(text: str) -> list[str]:
    """把中文小问标题拆成二字组，用于在 problem_brief 里粗略匹配目标描述。"""
    cleaned = "".join(ch for ch in str(text or "") if ch.strip())
    return [cleaned[i : i + 2] for i in range(len(cleaned) - 1)]


def _queue_questions(root: Path) -> list[dict]:
    """读取 `question_queue.json` 的小问清单；没有或格式不对就返回空列表。

    分小问分支的迁移必须按队列建板：一个题一块板、每题一个 entry，
    否则迁出来的板只有一题，checker 会判 `insufficient_options`，
    而真正的小问在 `questions/qN/` 里根本没被覆盖。
    """
    path = root / QUEUE_FILE
    if not path.is_file():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    raw = payload.get("questions") if isinstance(payload, dict) else None
    if not isinstance(raw, list):
        return []
    questions: list[dict] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        qid = str(item.get("id") or "").strip()
        if not qid:
            continue
        questions.append(
            {
                "id": qid,
                "title": str(item.get("title") or "").strip(),
                "depends_on": item.get("depends_on") if isinstance(item.get("depends_on"), list) else [],
            }
        )
    return questions


def _options_from_candidates(candidates: list[dict], final_name: str | None, warnings: list[str]) -> tuple[list[dict], list[str], int]:
    """把审计候选转成板里的 options（复用主路径的同一套规则）。"""
    options: list[dict] = []
    recommended_names: list[str] = []
    recommended_index: int | None = None
    if candidates and final_name is not None:
        for index, candidate in enumerate(candidates):
            if candidate["name"] == final_name:
                recommended_index = index
                break
        if recommended_index is None:
            target = _normalize_name(final_name)
            for index, candidate in enumerate(candidates):
                if _normalize_name(candidate["name"]) == target:
                    recommended_index = index
                    break
        if recommended_index is None:
            warnings.append(
                f"审计 final_selection.name={final_name!r} 与 candidates[].name 对不上，"
                "没有候选被标为 recommended，请人工核对。"
            )
    for index, candidate in enumerate(candidates):
        recommended = index == recommended_index
        option = _audit_option(index, candidate, recommended)
        options.append(option)
        if recommended:
            recommended_names.append(option["name"])

    padded = 0
    if len(options) < MIN_OPTIONS:
        needed = MIN_OPTIONS - len(options)
        for _ in range(needed):
            name = PLACEHOLDER_OPTION_NAMES[min(len(options), len(PLACEHOLDER_OPTION_NAMES) - 1)]
            options.append(_placeholder_option(len(options), name))
            padded += 1
        if candidates:
            warnings.append(
                f"审计只有 {len(candidates)} 个候选，已补 {needed} 个占位候选以满足“至少 2 个候选”。"
            )
    return options, recommended_names, padded


def _build_multi_question_board(root: Path, queue: list[dict], title: str, title_source: str) -> tuple[dict, dict]:
    """按 question_queue 逐问建板（分小问分支的迁移主路径）。"""
    warnings: list[str] = []
    questions: list[dict] = []
    recommended_all: list[str] = []
    audit_sources: list[str] = []
    total_options = 0

    for item in queue:
        qid = item["id"]
        qdir = root / QUESTIONS_DIR / qid
        candidates, final_name, audit_source, child_warnings = (
            _infer_candidates(qdir) if qdir.is_dir() else ([], None, None, [])
        )
        warnings.extend(f"{qid}: {msg}" for msg in child_warnings)
        if audit_source:
            audit_sources.append(f"{qid}:{audit_source}")
        options, recommended_names, _padded = _options_from_candidates(candidates, final_name, warnings)
        total_options += len(options)
        recommended_all.extend(f"{qid}:{name}" for name in recommended_names)
        goal = item.get("title") or GOAL_PLACEHOLDER
        if not item.get("title"):
            warnings.append(f"{qid} 没有 title，请补上该小问的目标描述。")
        questions.append(_build_question(options, audit_used=bool(candidates), question_id=qid, goal=goal))

    if not questions:
        raise ValueError("question_queue.json 里没有可用小问")

    board = {
        "schema_version": 1,
        "board_id": f"b-migrated-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "language": "python",
        "created_at": _now_utc_iso(),
        "revision": 0,
        "problem_summary": {
            "title": title,
            "source": title_source,
            "questions": [f"{q['id']}：{q['goal']}" for q in questions],
            "key_ambiguities": [],
        },
        "mindmap": {"format": "mermaid", "source": _build_mindmap(title, [])},
        "questions": questions,
        "pending_decisions": [],
        "no_change_rounds": 0,
    }
    inference = {
        "title": title,
        "title_source": title_source,
        "layout": "per_question",
        "audit_source": ", ".join(audit_sources) if audit_sources else None,
        "questions": len(questions),
        "options": total_options,
        "recommended": recommended_all,
        "padded_options": 0,
        "warnings": warnings,
    }
    return board, inference


def _build_board(root: Path) -> tuple[dict, dict]:
    """构造骨架 + 推断报告（不写盘）。

    两种形态：

    - **分小问形态**：工作区有 `question_queue.json` → 一块板、每题一个 entry，
      每题从 `questions/qN/model_selection_audit.json` 推断候选；
    - **整题形态**：无队列 → 沿用单题逻辑，从根 `model_selection_audit.json` 推断。
    """
    title, title_source = _infer_title(root)
    queue = _queue_questions(root)
    if queue:
        return _build_multi_question_board(root, queue, title, title_source)

    candidates, final_name, audit_source, warnings = _infer_candidates(root)

    options: list[dict] = []
    recommended_names: list[str] = []
    if candidates:
        recommended_index: int | None = None
        if final_name is not None:
            for index, candidate in enumerate(candidates):
                if candidate["name"] == final_name:
                    recommended_index = index
                    break
            if recommended_index is None:
                target = _normalize_name(final_name)
                for index, candidate in enumerate(candidates):
                    if _normalize_name(candidate["name"]) == target:
                        recommended_index = index
                        break
            if recommended_index is None:
                warnings.append(
                    f"审计 final_selection.name={final_name!r} 与 candidates[].name 对不上，"
                    "没有候选被标为 recommended，请人工核对。"
                )
        for index, candidate in enumerate(candidates):
            recommended = index == recommended_index
            option = _audit_option(index, candidate, recommended)
            options.append(option)
            if recommended:
                recommended_names.append(option["name"])

    padded = 0
    if len(options) < MIN_OPTIONS:
        # 保证"至少 2 个候选"的基本形态，否则 checker 会直接判 insufficient_options。
        needed = MIN_OPTIONS - len(options)
        for offset in range(needed):
            name = PLACEHOLDER_OPTION_NAMES[min(len(options), len(PLACEHOLDER_OPTION_NAMES) - 1)]
            options.append(_placeholder_option(len(options), name))
            padded += 1
        if candidates:
            warnings.append(
                f"审计只有 {len(candidates)} 个候选，已补 {needed} 个占位候选以满足“至少 2 个候选”。"
            )

    if not candidates and not (root / BRIEF_FILE).is_file():
        warnings.append("工作区既没有 problem_brief.md 也没有 model_selection_audit.json，生成的是纯占位板。")
    elif not candidates:
        warnings.append(f"未从 {AUDIT_FILE} 推断出候选，候选部分为占位值。")

    question = _build_question(options, audit_used=bool(candidates))
    board = {
        "schema_version": 1,
        "board_id": f"b-migrated-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "language": "python",
        "created_at": _now_utc_iso(),
        "revision": 0,
        "problem_summary": {
            "title": title,
            "source": title_source,
            "questions": [f"{question['id']}：{question['goal']}"],
            "key_ambiguities": [],
        },
        "mindmap": {"format": "mermaid", "source": _build_mindmap(title, options)},
        "questions": [question],
        "pending_decisions": [],
        "no_change_rounds": 0,
    }

    inference = {
        "title": title,
        "title_source": title_source,
        "audit_source": audit_source,
        "questions": len(board["questions"]),
        "options": len(options),
        "recommended": recommended_names,
        "padded_options": padded,
        "warnings": warnings,
    }
    return board, inference


# ---------------------------------------------------------------------------
# 校验与写盘
# ---------------------------------------------------------------------------


def _local_problems(board: dict) -> list[str]:
    """退路校验：与 design_board.validate_board(for_render=True) 的必填项保持一致。"""
    problems: list[str] = []
    questions = board.get("questions")
    if not isinstance(questions, list) or not questions:
        return ["questions 必须是非空数组"]
    for index, question in enumerate(questions):
        if not isinstance(question, dict):
            problems.append(f"questions[{index}] 必须是对象")
            continue
        if not isinstance(question.get("id"), str) or not question["id"].strip():
            problems.append(f"questions[{index}].id 缺失")
        options = question.get("options")
        if not isinstance(options, list) or not options:
            problems.append(f"questions[{index}].options 必须是非空数组")
            continue
        for option_index, option in enumerate(options):
            if not isinstance(option, dict):
                problems.append(f"questions[{index}].options[{option_index}] 必须是对象")
                continue
            for field in ("id", "name"):
                value = option.get(field)
                if not isinstance(value, str) or not value.strip():
                    problems.append(f"questions[{index}].options[{option_index}].{field} 缺失")
    mindmap = board.get("mindmap")
    source = mindmap.get("source") if isinstance(mindmap, dict) else None
    if not isinstance(source, str) or not source.strip():
        problems.append("mindmap.source 缺失（渲染导图必需）")
    return problems


def _validate_skeleton(board: dict) -> str:
    """写盘前自检，确保生成物一定能被 load_board(for_render=True) 接受。"""
    module = _load_board_module()
    if module is not None:
        problems = module.validate_board(board, for_render=True)
    else:
        problems = _local_problems(board)
    if problems:
        raise ValueError("迁移生成的骨架未通过校验（这是迁移脚本的 bug，请报告）：" + "；".join(problems))
    return "design_board.validate_board" if module is not None else "builtin"


def _atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    try:
        temp.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        os.replace(temp, path)
    finally:
        if temp.exists():
            try:
                temp.unlink()
            except OSError:
                pass


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------


def migrate_workspace(workspace: str, apply: bool = False) -> dict:
    """为旧工作区生成 design_board.json 骨架。

    ``apply=False``（默认）只返回预览，不写任何文件；``apply=True`` 落盘。
    ``design_board.json`` 已存在时抛 ``ValueError``，绝不覆盖。
    """
    root = Path(workspace)
    if not root.exists():
        raise ValueError(f"工作区不存在: {root}")
    if not root.is_dir():
        raise ValueError(f"工作区不是目录: {root}")
    root = root.resolve()

    path = root / BOARD_FILE
    if path.exists():
        raise ValueError(
            f"{BOARD_FILE} 已存在，无需迁移：{path}。"
            "若确实要重新生成，请先备份并手动删除该文件（迁移脚本不会覆盖已有决策板）。"
        )

    board, inference = _build_board(root)
    validator = _validate_skeleton(board)

    report: dict = {
        "action": "migrate",
        "apply": bool(apply),
        "workspace": str(root),
        "path": str(path),
        "written": False,
        "inferred": inference,
        "validated_with": validator,
        "next_steps": [NEXT_STEP_RENDER, NEXT_STEP_FILL, NEXT_STEP_CONFIRM],
    }

    if not apply:
        report["board_preview"] = board
        return report

    _atomic_write_json(path, board)
    module = _load_board_module()
    if module is not None:
        # 写盘后再读回一次：确认落盘文件真能被权威实现加载，而不只是内存里的对象合法。
        module.load_board(root, for_render=True)
    report["written"] = True
    return report


def main():
    parser = argparse.ArgumentParser(
        description="旧工作区迁移：生成最小可用的 design_board.json 骨架（默认只预览）"
    )
    parser.add_argument("--workspace", required=True, help="建模工作区目录")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="真正写入 design_board.json（默认 dry-run，只打印将要写入的内容）",
    )
    args = parser.parse_args()
    try:
        result = migrate_workspace(args.workspace, apply=args.apply)
        output(result)
        sys.exit(0)
    except SystemExit:
        raise
    except Exception as exc:
        error(str(exc))


if __name__ == "__main__":
    main()
