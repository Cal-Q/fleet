#!/usr/bin/env python3
"""
tools/routes/exam_routes.py — API routes for MEXT Past Exams, Analytics & Mock Interview
Strictly <= 200 lines invariant.
"""

import json
import os
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from academic.exam_analytics import get_analytics, record_session

router = APIRouter(tags=["exams"])

WORKSPACE_DIR = "/opt/japan"
EXAMS_DIR = os.path.join(WORKSPACE_DIR, "exams")
EXAM_DB_FILE = os.path.join(EXAMS_DIR, "exam_database.json")
EXAM_HIST_FILE = os.path.join(EXAMS_DIR, "history.json")


class ExamSubmitRequest(BaseModel):
    answers: dict  # {question_id: selected_option}
    time_spent_seconds: int
    mode: Optional[str] = "practice"


@router.get("/api/exams/questions")
def get_exam_questions(section: Optional[str] = None, category: Optional[str] = None):
    """Returns questions filtered by section (A, B, C) and/or category."""
    if not os.path.exists(EXAM_DB_FILE):
        raise HTTPException(status_code=404, detail="Database esami non trovato.")
    with open(EXAM_DB_FILE, "r", encoding="utf-8") as f:
        questions = json.load(f)

    if section and section.upper() != "ALL":
        questions = [q for q in questions if q.get("section") == section.upper()]
    if category:
        questions = [q for q in questions if q.get("category", "").lower() == category.lower()]
    return questions


@router.post("/api/exams/submit")
def submit_exam(req: ExamSubmitRequest):
    """Evaluates answers, logs granular question-level records, and returns analysis."""
    if not os.path.exists(EXAM_DB_FILE):
        raise HTTPException(status_code=404, detail="Database esami non trovato.")
    with open(EXAM_DB_FILE, "r", encoding="utf-8") as f:
        questions = json.load(f)
    q_map = {q["id"]: q for q in questions}

    total = len(req.answers)
    score = 0
    sec_breakdown = {"A": {"correct": 0, "total": 0}, "B": {"correct": 0, "total": 0}, "C": {"correct": 0, "total": 0}}
    cat_breakdown = {}
    details = []

    for qid, user_ans in req.answers.items():
        if qid not in q_map:
            continue
        q = q_map[qid]
        sec = q.get("section", "A")
        cat = q.get("category", "General")
        correct_ans = q.get("answer", "")
        is_correct = (user_ans.strip().upper() == correct_ans.strip().upper())

        if is_correct:
            score += 1
            sec_breakdown[sec]["correct"] += 1
        sec_breakdown[sec]["total"] += 1

        if cat not in cat_breakdown:
            cat_breakdown[cat] = {"correct": 0, "total": 0}
        cat_breakdown[cat]["total"] += 1
        if is_correct:
            cat_breakdown[cat]["correct"] += 1

        details.append({
            "id": qid,
            "question": q["question"],
            "category": cat,
            "level": q.get("level", ""),
            "user_answer": user_ans,
            "correct_answer": correct_ans,
            "is_correct": is_correct,
            "explanation": q.get("explanation", ""),
            "section": sec
        })

    session_data = record_session(
        score=score,
        total=total,
        time_spent_seconds=req.time_spent_seconds,
        section_breakdown=sec_breakdown,
        category_breakdown=cat_breakdown,
        details=details,
        mode=req.mode or "practice"
    )

    return {
        "session_id": session_data["session_id"],
        "score": score,
        "total": total,
        "percentage": session_data["percentage"],
        "seconds_per_question": session_data["seconds_per_question"],
        "breakdown": sec_breakdown,
        "category_breakdown": cat_breakdown,
        "details": details
    }


@router.get("/api/exams/analytics")
def get_exam_analytics_endpoint():
    """Returns aggregate performance analytics, pacing, category strengths and weaknesses."""
    return get_analytics()


@router.get("/api/exams/history")
def get_exam_history():
    """Returns historical summary of sessions."""
    if os.path.exists(EXAM_HIST_FILE):
        with open(EXAM_HIST_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"sessions": []}


@router.get("/api/interview/questions")
def get_interview_questions():
    """Returns mock interview questions with model answers."""
    from academic.interview_simulator import QUESTIONS
    return QUESTIONS
