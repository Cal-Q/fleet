#!/usr/bin/env python3
"""
api/routes/anki_web_routes.py — AnkiDroid & AnkiWeb Native Engine Routes
Provides accurate Anki due queries, deck tree hierarchy, and review submission.
Strictly <= 200 lines invariant.
"""

import os
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from core.db import open_anki_db
from core.anki_scheduler import apply_card_review
from core.anki_engine import fetch_anki_decks_data, get_deck_cards
from core.anki_settings_store import get_persisted_settings, save_persisted_settings
from core.anki_leech_service import run_leech_lifecycle
from core.anki_changelog import ANKI_CHANGELOG
from core.version import get_version_info

router = APIRouter(tags=["anki_web"])
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)
_last_leech_check = 0.0


class ReviewPayload(BaseModel):
    card_id: int
    grade: int
    time_ms: int = 0
    review_time: Optional[int] = None


class BatchReviewPayload(BaseModel):
    reviews: List[ReviewPayload]


@router.api_route("/anki", methods=["GET", "HEAD"], response_class=HTMLResponse)
def get_anki_web_page(request: Request):
    try:
        data = fetch_anki_decks_data()
        decks = data.get("decks", [])
    except Exception:
        decks = []
    settings = get_persisted_settings(BASE_DIR)
    ver_info = get_version_info()
    headers = {"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache"}
    ctx = {
        "decks": decks,
        "settings": settings,
        "version": ver_info.get("version", "v2.10.16"),
        "build": ver_info.get("build", "20260930_v2116"),
    }
    return templates.TemplateResponse(
        request=request, name="anki.html", context=ctx, headers=headers
    )


@router.get("/api/anki/decks")
def get_anki_decks() -> Dict[str, Any]:
    global _last_leech_check
    import time
    if time.time() - _last_leech_check > 3600:
        try:
            conn = open_anki_db()
            run_leech_lifecycle(conn, cooldown_days=30, threshold=8)
            conn.close()
            _last_leech_check = time.time()
        except Exception:
            pass
    try:
        return fetch_anki_decks_data()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/anki/leech/cycle")
def execute_leech_cycle(cooldown_days: int = 30, threshold: int = 8) -> Dict[str, Any]:
    try:
        conn = open_anki_db()
        result = run_leech_lifecycle(conn, cooldown_days=cooldown_days, threshold=threshold)
        conn.close()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/anki/deck_cards")
def get_deck_cards_endpoint(did: int, limit: int = 0, full: bool = False) -> Dict[str, Any]:
    try:
        return get_deck_cards(did, limit, full_sync=full)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/anki/review")
def submit_anki_review(payload: ReviewPayload) -> Dict[str, Any]:
    try:
        conn = open_anki_db()
        result = apply_card_review(
            conn, payload.card_id, payload.grade, payload.time_ms, payload.review_time or 0
        )
        conn.close()
        if result.get("status") != "ok":
            raise HTTPException(status_code=400, detail=result.get("message", "Review failed"))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/anki/sync_offline_reviews")
def sync_offline_reviews(payload: BatchReviewPayload) -> Dict[str, Any]:
    if not payload.reviews:
        return {"status": "ok", "synced": 0, "errors": []}
    conn = open_anki_db()
    applied = 0
    errors = []
    try:
        for r in payload.reviews:
            res = apply_card_review(conn, r.card_id, r.grade, r.time_ms, r.review_time or 0)
            if res.get("status") == "ok":
                applied += 1
            else:
                errors.append({"card_id": r.card_id, "error": res.get("message")})
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))
    conn.close()
    return {"status": "ok", "synced": applied, "errors": errors}


@router.get("/api/anki/settings")
def get_anki_settings() -> Dict[str, Any]:
    return {"status": "ok", "settings": get_persisted_settings(BASE_DIR)}


@router.post("/api/anki/settings")
def save_anki_settings(payload: Dict[str, Any]) -> Dict[str, Any]:
    current = get_persisted_settings(BASE_DIR)
    if "deck_timers" in payload and isinstance(payload["deck_timers"], dict):
        cur_timers = current.get("deck_timers", {})
        cur_timers.update(payload["deck_timers"])
        payload["deck_timers"] = cur_timers
    current.update(payload)
    ok = save_persisted_settings(BASE_DIR, current)
    return {"status": "ok" if ok else "error", "settings": current}


@router.get("/api/anki/version")
def get_anki_version() -> Dict[str, Any]:
    ver_info = get_version_info()
    return {
        "status": "ok",
        "version": ver_info.get("version", "v2.10.16"),
        "build": ver_info.get("build", "20260930_v2116"),
        "release_date": "2026-09-30",
        "changelog": ANKI_CHANGELOG,
    }



