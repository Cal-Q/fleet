#!/usr/bin/env python3
"""
tools/routes/exam_routes.py — API routes for MEXT Past Exams, Analytics & Mock Interview
Strictly <= 200 lines invariant.
"""

import json
import os
from typing import Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from academic.exam_analytics import get_analytics, record_session
from academic.exam_notes import get_user_notes, save_user_note, save_bulk_notes
from academic.exam_provider import get_questions_for_session, get_all_questions_map

router = APIRouter(tags=["exams"])

WORKSPACE_DIR = "/opt/japan"
EXAMS_DIR = os.path.join(WORKSPACE_DIR, "exams")
EXAM_HIST_FILE = os.path.join(EXAMS_DIR, "history.json")


class ExamSubmitRequest(BaseModel):
    answers: dict  # {question_id: selected_option}
    comments: Optional[dict] = None  # {question_id: comment_text}
    time_spent_seconds: int
    mode: Optional[str] = "practice"


class NoteSaveRequest(BaseModel):
    question_id: str
    comment: str
    answer: Optional[str] = None


@router.get("/api/exams/questions")
def get_exam_questions(section: Optional[str] = None, category: Optional[str] = None):
    """Returns questions filtered by section and category, dynamically rotated and enriched with saved notes."""
    return get_questions_for_session(section=section, category=category)


@router.get("/api/exams/notes")
def get_notes_endpoint():
    """Returns all user notes and reasoning saved per question."""
    return get_user_notes()


@router.post("/api/exams/notes")
def save_note_endpoint(req: NoteSaveRequest):
    """Saves or updates a user note/reasoning for a question."""
    return save_user_note(req.question_id, req.comment, req.answer)


@router.post("/api/exams/submit")
def submit_exam(req: ExamSubmitRequest):
    """Evaluates answers, logs granular question-level records, and returns analysis."""
    q_map = get_all_questions_map()

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

        comment_text = req.comments.get(qid, "") if req.comments else ""
        details.append({
            "id": qid,
            "question": q["question"],
            "category": cat,
            "level": q.get("level", ""),
            "user_answer": user_ans,
            "correct_answer": correct_ans,
            "is_correct": is_correct,
            "explanation": q.get("explanation", ""),
            "section": sec,
            "user_comment": comment_text
        })

    if req.comments or req.answers:
        save_bulk_notes(req.comments or {}, req.answers)

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


@router.get("/api/exams/omr-sheet", response_class=HTMLResponse)
def get_omr_sheet():
    """Serves printable A4 MEXT OMR Answer Sheet."""
    omr_path = os.path.join(WORKSPACE_DIR, "templates", "omr_sheet.html")
    if os.path.exists(omr_path):
        with open(omr_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>OMR Sheet Not Found</h1>"

