#!/usr/bin/env python3
"""
academic/exam_provider.py — Question Provider & Deterministic Daily Rotator for MEXT Drills
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
    """Returns a lookup dict {id: question} combining both standard db and drill pool."""
    q_map: Dict[str, Dict[str, Any]] = {}
    for q in _load_json_list(EXAM_DB_FILE):
        if "id" in q:
            q_map[q["id"]] = q
    for q in _load_json_list(DRILL_POOL_A_FILE):
        if "id" in q:
            q_map[q["id"]] = q
    return q_map


def _rotate_daily_slice(items: List[Dict[str, Any]], count: int = 12) -> List[Dict[str, Any]]:
    """Deterministically selects `count` items based on the current date seed."""
    if not items or len(items) <= count:
        return items
    today_str = datetime.now().strftime("%Y-%m-%d")
    seed = int(hashlib.md5(today_str.encode()).hexdigest(), 16)
    start_idx = seed % len(items)
    # Circular slice
    rotated = []
    for i in range(count):
        idx = (start_idx + i) % len(items)
        rotated.append(items[idx])
    return rotated


def get_questions_for_session(
    section: Optional[str] = None,
    category: Optional[str] = None,
    limit: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Returns questions for a study session.
    If section == 'A', prioritizes the rich unseen drill pool with daily rotation.
    """
    sec_upper = section.upper() if section else None

    if sec_upper == "A":
        pool_a = _load_json_list(DRILL_POOL_A_FILE)
        if not pool_a:
            pool_a = [q for q in _load_json_list(EXAM_DB_FILE) if q.get("section") == "A"]
        
        if category:
            pool_a = [q for q in pool_a if q.get("category", "").lower() == category.lower()]
        
        target_count = limit or 12
        selected = _rotate_daily_slice(pool_a, count=target_count)
    else:
        db_questions = _load_json_list(EXAM_DB_FILE)
        selected = db_questions
        if sec_upper and sec_upper != "ALL":
            selected = [q for q in selected if q.get("section") == sec_upper]
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
