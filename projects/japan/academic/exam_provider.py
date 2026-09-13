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

WORKSPACE_DIR = "/opt/japan"
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


def _rotate_daily_slice(items: List[Dict[str, Any]], count: int = 12, salt: str = "") -> List[Dict[str, Any]]:
    """Deterministically selects `count` items based on the date seed and optional salt."""
    if not items or len(items) <= count:
        return items
    today_str = datetime.now().strftime("%Y-%m-%d") + salt
    seed = int(hashlib.md5(today_str.encode()).hexdigest(), 16)
    start_idx = seed % len(items)
    rotated = []
    for i in range(count):
        idx = (start_idx + i) % len(items)
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

    if sec_upper in ["A", "B", "C"]:
        pool = _get_pool_for_section(sec_upper)
        if category:
            pool = [q for q in pool if q.get("category", "").lower() == category.lower()]
        target_count = limit or (8 if sec_upper == "C" else 12)
        selected = _rotate_daily_slice(pool, count=target_count, salt=sec_upper)
    else:
        # Balanced mock battery across all 3 sections
        pool_a = _rotate_daily_slice(_get_pool_for_section("A"), count=5, salt="A_all")
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
