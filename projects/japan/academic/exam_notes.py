#!/usr/bin/env python3
"""
academic/exam_notes.py — Persistent User Notes & Reasoning per Exam Question
Strictly <= 200 lines invariant.
"""

import os
import json
from datetime import datetime
from typing import Any, Dict, Optional

EXAMS_DIR = "/opt/japan/exams"
NOTES_FILE = os.path.join(EXAMS_DIR, "user_notes.json")


def get_user_notes() -> Dict[str, Any]:
    """Loads all persistent user notes from disk."""
    if not os.path.exists(NOTES_FILE):
        return {}
    try:
        with open(NOTES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_user_note(question_id: str, comment: str, answer: Optional[str] = None) -> Dict[str, Any]:
    """Saves or updates a single question note with timestamp."""
    os.makedirs(EXAMS_DIR, exist_ok=True)
    notes = get_user_notes()
    entry = notes.get(question_id, {})
    entry["question_id"] = question_id
    entry["comment"] = comment.strip()
    if answer is not None:
        entry["selected_answer"] = answer
    entry["updated_at"] = datetime.now().isoformat()
    notes[question_id] = entry

    with open(NOTES_FILE, "w", encoding="utf-8") as f:
        json.dump(notes, f, indent=2, ensure_ascii=False)
    return entry


def save_bulk_notes(comments: Dict[str, str], answers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Batch updates notes from an exam submission or sync."""
    os.makedirs(EXAMS_DIR, exist_ok=True)
    notes = get_user_notes()
    now = datetime.now().isoformat()
    for qid, comment in comments.items():
        if not comment and qid not in notes:
            continue
        entry = notes.get(qid, {})
        entry["question_id"] = qid
        if comment:
            entry["comment"] = comment.strip()
        if answers and qid in answers and answers[qid]:
            entry["selected_answer"] = answers[qid]
        entry["updated_at"] = now
        notes[qid] = entry

    with open(NOTES_FILE, "w", encoding="utf-8") as f:
        json.dump(notes, f, indent=2, ensure_ascii=False)
    return notes
