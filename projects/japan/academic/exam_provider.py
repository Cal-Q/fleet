#!/usr/bin/env python3
"""
academic/exam_provider.py — MEXT Question Provider & Tri-Section Rotator.
Strictly <= 200 lines invariant.
"""

import hashlib
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from academic.exam_notes import get_user_notes
from academic.exam_formatter import clean_question_text, derive_task_type

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKSPACE_DIR = os.environ.get("WORKSPACE_DIR") or BASE_DIR
EXAMS_DIR = os.path.join(WORKSPACE_DIR, "exams")
EXAM_DB_FILE = os.path.join(EXAMS_DIR, "exam_database.json")
DRILL_POOL_A_FILE = os.path.join(EXAMS_DIR, "drill_pool_part_a.json")
DRILL_POOL_B_FILE = os.path.join(EXAMS_DIR, "drill_pool_part_b.json")
DRILL_POOL_C_FILE = os.path.join(EXAMS_DIR, "drill_pool_part_c.json")

_POOL_CACHE: Dict[str, List[Dict[str, Any]]] = {}


def _load_json_list(file_path: str) -> List[Dict[str, Any]]:
    if file_path in _POOL_CACHE:
        return _POOL_CACHE[file_path]
    if not os.path.exists(file_path):
        return []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            res = data if isinstance(data, list) else []
            _POOL_CACHE[file_path] = res
            return res
    except Exception:
        return []


def get_all_questions_map() -> Dict[str, Dict[str, Any]]:
    """Returns a lookup dict {id: question} across all standard and drill pools."""
    q_map: Dict[str, Dict[str, Any]] = {}
    for fp in [EXAM_DB_FILE, DRILL_POOL_A_FILE, DRILL_POOL_B_FILE, DRILL_POOL_C_FILE]:
        for raw in _load_json_list(fp):
            if "id" in raw:
                q = dict(raw)
                q["question"] = clean_question_text(q.get("question", ""))
                q["task_type"] = derive_task_type(q)
                q_map[q["id"]] = q
    return q_map


def _stratified_part_a(
    items: List[Dict[str, Any]],
    count: int = 12,
    salt: str = "",
    today_str: str = "",
    batch: int = 0
) -> List[Dict[str, Any]]:
    """Invariant 25: Stratified Blueprint Quota for Part A with batch rotation."""
    traps, grammar, writing, reading = [], [], [], []
    for q in items:
        cat = q.get("category", "")
        qid = q.get("id", "")
        try:
            qnum = int(qid.split("-")[-1])
        except Exception:
            qnum = 0
        if "熟字訓" in cat or qnum >= 111:
            traps.append(q)
        elif any(k in cat for k in [
            "Grammar", "Particle", "Form", "Conditional", "Request",
            "Transitive", "Conjunction"
        ]):
            grammar.append(q)
        elif any(k in cat for k in ["Writing", "Homophone", "Lookalike"]):
            writing.append(q)
        else:
            reading.append(q)

    base_date = today_str or datetime.now().strftime("%Y-%m-%d")
    date_key = f"{base_date}_{salt}_b{batch}"

    def _sample(bucket: List[Dict[str, Any]], n: int, b_salt: str) -> List[Dict[str, Any]]:
        if not bucket or n <= 0:
            return []
        seed = int(hashlib.md5((date_key + b_salt).encode()).hexdigest(), 16)
        start = seed % len(bucket)
        return [bucket[(start + i * 7) % len(bucket)] for i in range(n)]

    if count == 12:
        return (
            _sample(grammar, 5, "g")
            + _sample(writing, 3, "w")
            + _sample(reading, 3, "r")
            + _sample(traps, 1, "t")
        )
    elif count <= 6:
        return (
            _sample(grammar, 2, "gs") +
            _sample(writing, 1, "ws") +
            _sample(reading, 2, "rs")
        )
    return _rotate_daily_slice(items, count=count, salt=salt, today_str=base_date, batch=batch)


def _rotate_daily_slice(
    items: List[Dict[str, Any]],
    count: int = 12,
    salt: str = "",
    today_str: str = "",
    batch: int = 0
) -> List[Dict[str, Any]]:
    """Deterministically selects count items with coprime stride and batch offset."""
    if not items or len(items) <= count:
        return items
    base_date = today_str or datetime.now().strftime("%Y-%m-%d")
    date_key = f"{base_date}_{salt}_b{batch}"
    seed = int(hashlib.md5(date_key.encode()).hexdigest(), 16)
    start_idx = seed % len(items)
    stride = 13
    return [items[(start_idx + i * stride) % len(items)] for i in range(count)]


def _get_pool_for_section(sec: str) -> List[Dict[str, Any]]:
    fp_map = {"A": DRILL_POOL_A_FILE, "B": DRILL_POOL_B_FILE, "C": DRILL_POOL_C_FILE}
    pool = _load_json_list(fp_map.get(sec, ""))
    if pool:
        return pool
    return [q for q in _load_json_list(EXAM_DB_FILE) if q.get("section") == sec]


def get_questions_for_session(
    section: Optional[str] = None,
    category: Optional[str] = None,
    limit: Optional[int] = None,
    target_date: Optional[str] = None,
    batch: int = 0
) -> List[Dict[str, Any]]:
    """Returns questions for a study session with deterministic batch rotation."""
    sec_upper = section.upper() if section else "ALL"
    t_date = target_date or datetime.now().strftime("%Y-%m-%d")

    if sec_upper == "A":
        pool = _get_pool_for_section("A")
        if category:
            cat_pool = [q for q in pool if q.get("category", "").lower() == category.lower()]
            selected = _rotate_daily_slice(
                cat_pool, count=limit or 12, salt="A_cat", today_str=t_date, batch=batch
            )
        else:
            selected = _stratified_part_a(
                pool, count=limit or 12, salt="A", today_str=t_date, batch=batch
            )
    elif sec_upper in ["B", "C"]:
        pool = _get_pool_for_section(sec_upper)
        if category:
            pool = [q for q in pool if q.get("category", "").lower() == category.lower()]
        lim = limit or (8 if sec_upper == "C" else 12)
        selected = _rotate_daily_slice(
            pool, count=lim, salt=sec_upper, today_str=t_date, batch=batch
        )
    elif sec_upper == "MOCK":
        pa = _stratified_part_a(
            _get_pool_for_section("A"), count=12, salt="MOCK_A", today_str=t_date, batch=batch
        )
        pb = _rotate_daily_slice(
            _get_pool_for_section("B"), count=10, salt="MOCK_B", today_str=t_date, batch=batch
        )
        pc = _rotate_daily_slice(
            _get_pool_for_section("C"), count=8, salt="MOCK_C", today_str=t_date, batch=batch
        )
        selected = pa + pb + pc
    else:
        pa = _stratified_part_a(
            _get_pool_for_section("A"), count=5, salt="A_all", today_str=t_date, batch=batch
        )
        pb = _rotate_daily_slice(
            _get_pool_for_section("B"), count=5, salt="B_all", today_str=t_date, batch=batch
        )
        pc = _rotate_daily_slice(
            _get_pool_for_section("C"), count=4, salt="C_all", today_str=t_date, batch=batch
        )
        all_sel = pa + pb + pc
        selected = all_sel[:limit] if limit else all_sel

    user_notes = get_user_notes()
    res = []
    for raw in selected:
        q = dict(raw)
        q["question"] = clean_question_text(q.get("question", ""))
        q["task_type"] = derive_task_type(q)
        n = user_notes.get(q.get("id"), {})
        q["saved_comment"] = n.get("comment", "")
        q["saved_answer"] = n.get("selected_answer", "")
        res.append(q)
    return res
