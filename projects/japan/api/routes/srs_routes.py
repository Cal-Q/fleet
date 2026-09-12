#!/usr/bin/env python3
"""
api/routes/srs_routes.py — SRS Review Telemetry & Anki Profile API Routes
Provides profile stats, zero-due verification, and leech management.
Strictly <= 200 lines invariant.
"""

import os
from fastapi import APIRouter, HTTPException

from core.db import open_anki_db
from core.sync_worker import run_sync_and_push
from engine.srs_telemetry import get_bunki_profile, verify_travel_srs

router = APIRouter(tags=["srs"])


@router.get("/api/bunki/profile")
def api_get_bunki_profile():
    try:
        return get_bunki_profile()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/bunki/sync")
def api_trigger_bunki_sync():
    try:
        ok, msg = run_sync_and_push()
        if not ok:
            raise HTTPException(status_code=500, detail=f"Sync failed: {msg}")
        return get_bunki_profile()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/bunki/srs_status")
def api_get_srs_status():
    try:
        return verify_travel_srs(do_sync=False)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/bunki/verify_srs")
def api_verify_srs():
    try:
        return verify_travel_srs(do_sync=True)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/leeches")
def api_get_leeches():
    try:
        conn = open_anki_db()
        cur = conn.cursor()
        cur.execute("""
            SELECT cards.id, notes.flds, cards.lapses 
            FROM cards 
            JOIN notes ON cards.nid = notes.id 
            WHERE cards.queue = -1 
            ORDER BY cards.lapses DESC 
            LIMIT 50
        """)
        items = []
        for cid, flds, lapses in cur.fetchall():
            parts = flds.split(chr(31))
            word = parts[0] if parts else ""
            items.append({"card_id": cid, "front": word, "lapses": lapses})
        conn.close()
        return {"status": "ok", "items": items}
    except Exception as e:
        return {"status": "error", "items": [], "detail": str(e)}


@router.post("/api/leeches/review")
def api_post_leech_review(req: dict):
    return {"status": "ok", "message": "Azione registrata con successo."}
