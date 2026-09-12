#!/usr/bin/env python3
"""
api/routes/study_routes.py — Daily Study Batch & Curriculum API Routes
Handles batch staging for Kanji, Vocab, and Grammar.
Strictly <= 200 lines invariant.
"""

from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from engine.study_queue import get_next_items, load_daily_stats
from engine.study_batch import add_kanji_batch, add_vocab_batch, add_grammar_batch

router = APIRouter(tags=["study"])


class StudyBatchRequest(BaseModel):
    category: str
    items: List[Dict[str, Any]]


class StudyAddRequest(BaseModel):
    category: str
    item_id: str
    payload: Dict[str, Any]


@router.get("/api/study/status")
def get_study_status():
    try:
        return {"status": "ok", "today": load_daily_stats()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/study/next")
def get_study_next():
    try:
        return get_next_items(kanji_limit=5, vocab_limit=20, grammar_limit=5)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/study/add_batch")
def post_study_add_batch(req: StudyBatchRequest):
    try:
        cat = req.category.lower()
        if cat == "kanji":
            return add_kanji_batch(req.items)
        elif cat == "vocab":
            return add_vocab_batch(req.items)
        elif cat == "grammar":
            return add_grammar_batch(req.items)
        else:
            raise HTTPException(status_code=400, detail=f"Categoria non valida: {cat}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/study/add")
def post_study_add(req: StudyAddRequest):
    try:
        cat = req.category.lower()
        if cat == "kanji":
            return add_kanji_batch([req.payload])
        elif cat == "vocab":
            return add_vocab_batch([req.payload])
        elif cat == "grammar":
            return add_grammar_batch([req.payload])
        else:
            raise HTTPException(status_code=400, detail=f"Categoria non valida: {cat}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
