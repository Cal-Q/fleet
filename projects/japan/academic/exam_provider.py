#!/usr/bin/env python3
"""
academic/exam_provider.py — MEXT Question Provider & Tri-Section Daily Rotator
Strictly <= 200 lines invariant.
"""

import hashlib
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from academic.exam_notes import get_user_notes

WORKSPACE_DIR = os.environ.get("WORKSPACE_DIR") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAMS_DIR = os.path.join(WORKSPACE_DIR, "exams")
EXAM_DB_FILE = os.path.join(EXAMS_DIR, "exam_database.json")
DRILL_POOL_A_FILE = os.path.join(EXAMS_DIR, "drill_pool_part_a.json")
DRILL_POOL_B_FILE = os.path.join(EXAMS_DIR, "drill_pool_part_b.json")
DRILL_POOL_C_FILE = os.path.join(EXAMS_DIR, "drill_pool_part_c.json")


def _load_json_list(file_path: str) -> List[Dict[str, Any]]:
    if not os.path.exists(file_path):
        return []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []


def get_all_questions_map() -> Dict[str, Dict[str, Any]]:
    """Returns a lookup dict {id: question} across all standard and drill pools."""
    q_map: Dict[str, Dict[str, Any]] = {}
    for fp in [EXAM_DB_FILE, DRILL_POOL_A_FILE, DRILL_POOL_B_FILE, DRILL_POOL_C_FILE]:
        for q in _load_json_list(fp):
            if "id" in q:
                q_map[q["id"]] = q
    return q_map


def _stratified_part_a(items: List[Dict[str, Any]], count: int = 12, salt: str = "") -> List[Dict[str, Any]]:
    """
    Invariant 25: Stratified Blueprint Quota for Part A.
    Guarantees balanced pedagogical distribution:
    - 5x Grammar & Particles (N5/N4 core)
    - 3x Kanji Orthography / Writing (N5/N4 core)
    - 3x Core Kanji Reading & Common Vocab (N5/N4 core)
    - 1x Advanced Phonetic / Jukujikun Trap (N3 limit)
    Strictly eliminates category clustering and limits traps to <= 1 per session.
    """
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
        elif any(k in cat for k in ["Grammar", "Particle", "Form", "Conditional", "Request", "Transitive", "Conjunction"]):
            grammar.append(q)
        elif any(k in cat for k in ["Writing", "Homophone", "Lookalike"]):
            writing.append(q)
        else:
            reading.append(q)

    today_str = datetime.now().strftime("%Y-%m-%d") + salt

    def _sample(bucket: List[Dict[str, Any]], n: int, b_salt: str) -> List[Dict[str, Any]]:
        if not bucket or n <= 0:
            return []
        seed = int(hashlib.md5((today_str + b_salt).encode()).hexdigest(), 16)
        start = seed % len(bucket)
        return [bucket[(start + i * 7) % len(bucket)] for i in range(n)]

    if count == 12:
        return _sample(grammar, 5, "g") + _sample(writing, 3, "w") + _sample(reading, 3, "r") + _sample(traps, 1, "t")
    elif count <= 6:
        return _sample(grammar, 2, "gs") + _sample(writing, 1, "ws") + _sample(reading, 2, "rs")
    return _rotate_daily_slice(items, count=count, salt=salt)


def _rotate_daily_slice(items: List[Dict[str, Any]], count: int = 12, salt: str = "") -> List[Dict[str, Any]]:
    """Deterministically selects `count` items with coprime stride to prevent category clustering."""
    if not items or len(items) <= count:
        return items
    today_str = datetime.now().strftime("%Y-%m-%d") + salt
    seed = int(hashlib.md5(today_str.encode()).hexdigest(), 16)
    start_idx = seed % len(items)
    stride = 13  # Coprime with 125, 90, 50 to uniformly sample across pool categories
    rotated = []
    for i in range(count):
        idx = (start_idx + i * stride) % len(items)
        rotated.append(items[idx])
    return rotated


def _get_pool_for_section(sec: str) -> List[Dict[str, Any]]:
    if sec == "A":
        pool = _load_json_list(DRILL_POOL_A_FILE)
        return pool if pool else [q for q in _load_json_list(EXAM_DB_FILE) if q.get("section") == "A"]
    if sec == "B":
        pool = _load_json_list(DRILL_POOL_B_FILE)
        return pool if pool else [q for q in _load_json_list(EXAM_DB_FILE) if q.get("section") == "B"]
    if sec == "C":
        pool = _load_json_list(DRILL_POOL_C_FILE)
        return pool if pool else [q for q in _load_json_list(EXAM_DB_FILE) if q.get("section") == "C"]
    return []


def get_questions_for_session(
    section: Optional[str] = None,
    category: Optional[str] = None,
    limit: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Returns questions for a study session with deterministic daily rotation.
    Supports sections A, B, C or a balanced ALL mock set.
    """
    sec_upper = section.upper() if section else "ALL"

    if sec_upper == "A":
        pool = _get_pool_for_section("A")
        if category:
            pool = [q for q in pool if q.get("category", "").lower() == category.lower()]
            selected = _rotate_daily_slice(pool, count=limit or 12, salt="A_cat")
        else:
            selected = _stratified_part_a(pool, count=limit or 12, salt="A")
    elif sec_upper in ["B", "C"]:
        pool = _get_pool_for_section(sec_upper)
        if category:
            pool = [q for q in pool if q.get("category", "").lower() == category.lower()]
        target_count = limit or (8 if sec_upper == "C" else 12)
        selected = _rotate_daily_slice(pool, count=target_count, salt=sec_upper)
    elif sec_upper == "MOCK":
        pool_a = _stratified_part_a(_get_pool_for_section("A"), count=12, salt="MOCK_A")
        pool_b = _rotate_daily_slice(_get_pool_for_section("B"), count=10, salt="MOCK_B")
        pool_c = _rotate_daily_slice(_get_pool_for_section("C"), count=8, salt="MOCK_C")
        selected = pool_a + pool_b + pool_c
    else:
        # Balanced daily mock battery across all 3 sections
        pool_a = _stratified_part_a(_get_pool_for_section("A"), count=5, salt="A_all")
        pool_b = _rotate_daily_slice(_get_pool_for_section("B"), count=5, salt="B_all")
        pool_c = _rotate_daily_slice(_get_pool_for_section("C"), count=4, salt="C_all")
        selected = pool_a + pool_b + pool_c
        if category:
            selected = [q for q in selected if q.get("category", "").lower() == category.lower()]
        if limit and len(selected) > limit:
            selected = selected[:limit]

    # Enrich with user notes
    user_notes = get_user_notes()
    for q in selected:
        n = user_notes.get(q.get("id"), {})
        q["saved_comment"] = n.get("comment", "")
        q["saved_answer"] = n.get("selected_answer", "")

    return selected
