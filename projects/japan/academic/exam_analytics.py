#!/usr/bin/env python3
"""
tools/exam_analytics.py — MEXT Exam Practice Analytics & Session Logger
Strictly <= 200 lines invariant.
"""

import os
import json
import time
from datetime import datetime
from typing import Any, Dict, List

EXAMS_DIR = "/opt/japan/exams"
LOG_FILE = os.path.join(EXAMS_DIR, "practice_log.jsonl")
HIST_FILE = os.path.join(EXAMS_DIR, "history.json")


def record_session(
    score: int,
    total: int,
    time_spent_seconds: int,
    section_breakdown: Dict[str, Dict[str, int]],
    category_breakdown: Dict[str, Dict[str, int]],
    details: List[Dict[str, Any]],
    mode: str = "practice"
) -> Dict[str, Any]:
    """Persists a practice session to both practice_log.jsonl and history.json."""
    os.makedirs(EXAMS_DIR, exist_ok=True)
    pct = round((score / total * 100) if total > 0 else 0.0, 1)
    session_id = f"sess_{int(time.time())}"
    timestamp = datetime.now().isoformat()

    session_entry = {
        "session_id": session_id,
        "timestamp": timestamp,
        "mode": mode,
        "score": score,
        "total": total,
        "percentage": pct,
        "time_seconds": time_spent_seconds,
        "seconds_per_question": round(time_spent_seconds / total, 1) if total > 0 else 0.0,
        "section_breakdown": section_breakdown,
        "category_breakdown": category_breakdown,
        "details": details,
    }

    # Append to jsonl
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(session_entry, ensure_ascii=False) + "\n")

    # Update summary in history.json
    hist = {"sessions": []}
    if os.path.exists(HIST_FILE):
        try:
            with open(HIST_FILE, "r", encoding="utf-8") as f:
                hist = json.load(f)
        except Exception:
            pass

    summary_entry = {
        "session_id": session_id,
        "timestamp": timestamp,
        "score": score,
        "total": total,
        "percentage": pct,
        "time_seconds": time_spent_seconds,
        "breakdown": section_breakdown,
        "category_breakdown": category_breakdown
    }
    hist["sessions"].append(summary_entry)
    with open(HIST_FILE, "w", encoding="utf-8") as f:
        json.dump(hist, f, indent=2, ensure_ascii=False)

    return session_entry


def get_analytics() -> Dict[str, Any]:
    """Computes aggregate analytics, category strengths/weaknesses, and pacing."""
    if not os.path.exists(LOG_FILE):
        return {
            "total_sessions": 0,
            "total_questions": 0,
            "total_correct": 0,
            "total_time_seconds": 0,
            "total_time_minutes": 0.0,
            "overall_accuracy": 0.0,
            "avg_seconds_per_question": 0.0,
            "section_accuracy": {},
            "category_accuracy": {},
            "strengths": [],
            "weaknesses": [],
            "recent_sessions": []
        }

    total_sessions = 0
    total_questions = 0
    total_correct = 0
    total_time_seconds = 0
    cat_stats: Dict[str, Dict[str, int]] = {}
    sec_stats: Dict[str, Dict[str, int]] = {"A": {"correct": 0, "total": 0}, "B": {"correct": 0, "total": 0}, "C": {"correct": 0, "total": 0}}
    recent_sessions = []

    with open(LOG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                s = json.loads(line)
            except Exception:
                continue

            total_sessions += 1
            total_questions += s.get("total", 0)
            total_correct += s.get("score", 0)
            total_time_seconds += s.get("time_seconds", 0)

            for d in s.get("details", []):
                cat = d.get("category", "Uncategorized")
                is_c = d.get("is_correct", False)
                if cat not in cat_stats:
                    cat_stats[cat] = {"correct": 0, "total": 0}
                cat_stats[cat]["total"] += 1
                if is_c:
                    cat_stats[cat]["correct"] += 1

                sec = d.get("section", "A")
                if sec in sec_stats:
                    sec_stats[sec]["total"] += 1
                    if is_c:
                        sec_stats[sec]["correct"] += 1

            recent_sessions.append({
                "session_id": s.get("session_id"),
                "timestamp": s.get("timestamp"),
                "score": s.get("score"),
                "total": s.get("total"),
                "percentage": s.get("percentage"),
                "time_seconds": s.get("time_seconds")
            })

    overall_acc = round((total_correct / total_questions * 100) if total_questions > 0 else 0.0, 1)
    avg_sec_per_q = round((total_time_seconds / total_questions) if total_questions > 0 else 0.0, 1)

    category_acc = {}
    strengths = []
    weaknesses = []

    for cat, data in cat_stats.items():
        c_tot = data["total"]
        c_cor = data["correct"]
        pct = round((c_cor / c_tot * 100) if c_tot > 0 else 0.0, 1)
        category_acc[cat] = {"correct": c_cor, "total": c_tot, "percentage": pct}
        if c_tot >= 2:
            if pct >= 80.0:
                strengths.append({"category": cat, "percentage": pct, "total": c_tot})
            elif pct < 65.0:
                weaknesses.append({"category": cat, "percentage": pct, "total": c_tot})

    strengths.sort(key=lambda x: x["percentage"], reverse=True)
    weaknesses.sort(key=lambda x: x["percentage"])

    section_acc = {}
    for sec, data in sec_stats.items():
        s_tot = data.get("total", 0)
        s_cor = data.get("correct", 0)
        section_acc[sec] = {
            "correct": s_cor,
            "total": s_tot,
            "percentage": round((s_cor / s_tot * 100) if s_tot > 0 else 0.0, 1)
        }

    return {
        "total_sessions": total_sessions,
        "total_questions": total_questions,
        "total_correct": total_correct,
        "total_time_seconds": total_time_seconds,
        "total_time_minutes": round(total_time_seconds / 60, 1),
        "overall_accuracy": overall_acc,
        "avg_seconds_per_question": avg_sec_per_q,
        "section_accuracy": section_acc,
        "category_accuracy": category_acc,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "recent_sessions": recent_sessions[-10:]
    }
